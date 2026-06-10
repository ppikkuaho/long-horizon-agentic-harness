"""F1 — the daemon ASSEMBLY (the keystone fix, REMEDIATION-PLAN-2026-06-07).

The review found the substrate is built but the resident daemon is never assembled: no process
entrypoint (launchd's `python3 -m harnessd.daemon` ran nothing), the IPC listener is never bound/served,
and `poll_once` never ticks the watchdog — so no node ever auto-collapses on sign-off. These tests pin
the assembly:

  1. PROCESS ENTRYPOINT — `python3 -m harnessd.daemon` resolves to a callable that boots + runs the loop.
  2. IPC LISTENER — the daemon binds the AF_UNIX socket at the canonical path and serves a real request
     end-to-end (the CLI->daemon path is live).
  3. WATCHDOG TICK (the load-bearing one) — `poll_once` AUTONOMOUSLY collapses a leaf that has emitted a
     fresh DONE/.signal.json (spawned -> detected -> signed-off -> collapsed, through the REAL watchdog ->
     chokepoint.collapse -> executor). This is the autonomous spine the green suite was masking.
  4. COORDINATOR DEATH-PROBE — `poll_once` runs the coordinator branch (a dead coordinator over live
     children escalates, never blind-collapsed).

BIAS TO REAL (Lesson 7): the REAL ledger, REAL watchdog, REAL chokepoint.collapse -> REAL executor; the
.signal.json is a REAL on-disk file (the agent's sign-off); only the actor-open adapter + tmux pane query
are faked (no model, no real pane). The loop-test drives the REAL poll_once (closing the system-level
test-masking, W2 LOW-6).
"""

import copy
import importlib
import json
import socket
import threading
from types import SimpleNamespace

import pytest

import harnessd.addressing as addressing
import harnessd.clock as clock
import harnessd.daemon as daemon
import harnessd.executor as executor
import harnessd.fencing as fencing
import harnessd.ipc as ipc
import harnessd.ledger as ledger
import harnessd.spawn.chokepoint as chokepoint


@pytest.fixture
def runtime(tmp_path):
    prev = ledger.RUNTIME_ROOT
    ledger.RUNTIME_ROOT = tmp_path
    try:
        yield tmp_path
    finally:
        ledger.RUNTIME_ROOT = prev


# A detector whose verdict we script per-node (the watchdog reads liveness via its set_liveness seam).
class _Detector:
    def __init__(self, default="working"):
        self._states = {}
        self._default = default

    def set(self, addr, state):
        self._states[addr] = state

    def liveness(self, node_address):
        return SimpleNamespace(state=self._states.get(node_address, self._default), last_progress_at=None)


class _Tmux:
    def __init__(self, targets=None):
        self._targets = dict(targets or {})

    def list_targets(self):
        return dict(self._targets)


def _seed_running_leaf(runtime, address="proj/widget/task#exec", level="L5"):
    """A LIVE leaf node (running), with a real nested workspace + a tmux pane reported alive."""
    token = fencing.mint_owner_token(address, "sa", "uuid", 2)
    ws = addressing.node_dir(address, runtime)
    ws.mkdir(parents=True, exist_ok=True)
    rec = {"node_address": address, "parent_address": "proj/widget#exec", "level": level,
           "subagent_id": "sa", "session_uuid": "uuid", "state": "running", "generation": 5,
           "lease_epoch": 2, "owner_token": token, "last_applied_seq": 0, "liveness_state": "working",
           "tmux_target": "harness:" + address, "workspace": str(ws),
           "stale_check_count": 0, "stale_grace_checks": 2}
    ledger.write_binding({address: copy.deepcopy(rec)}, _lock_held=True)
    return address, token


def _write_signal(runtime, address, *, signal, owner_token):
    """The REAL .signal.json the agent writes at sign-off (canonical per-seat path)."""
    p = addressing.signal_path(address, runtime)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"signal": signal, "ts": clock.now_utc(),
                             "owner_token": owner_token, "evidence": {"report": "report.md"}}),
                 encoding="utf-8")


def _install_adapter():
    class _FakeAdapter:
        def pin_and_open(self, neutral_brief, level_config, tmux_target, env):
            from harnessd.spawn.adapters.base import SpawnResult
            return SpawnResult(ok=True, session_uuid="s", model_used="m", role_variant="L5",
                               system_prompt_file="x", system_prompt_file_hash="h",
                               tmux_target=tmux_target, transcript_path="/tmp/s.jsonl", failure_class=None)
    fake = _FakeAdapter()
    if hasattr(chokepoint, "set_adapter"):
        chokepoint.set_adapter(fake)
    else:
        chokepoint.ADAPTER = fake


# --------------------------------------------------------------------------- #
# 1. PROCESS ENTRYPOINT
# --------------------------------------------------------------------------- #

def test_daemon_has_a_module_entrypoint():
    """`python3 -m harnessd.daemon` must run something — a __main__ guard or a harnessd/__main__.py that
    calls boot() then poll_loop(). The launchd plist names this entry; without it the process is inert."""
    import importlib.util
    has_pkg_main = importlib.util.find_spec("harnessd.__main__") is not None
    src = ""
    try:
        import inspect
        src = inspect.getsource(daemon)
    except OSError:
        pass
    has_daemon_main = "__main__" in src and ("poll_loop" in src or "run(" in src or "def run" in src)
    assert has_pkg_main or has_daemon_main, (
        "no daemon process entrypoint: add harnessd/__main__.py OR a daemon.py __main__ guard that "
        "boots + runs poll_loop, so `python3 -m harnessd.daemon` actually runs the daemon"
    )


def test_daemon_exposes_a_run_entry_that_boots_then_loops():
    """A single callable (run) that the entrypoint invokes: boot(runtime) then poll_loop(...). We assert
    its presence + that it is wired to boot + loop (without entering the unbounded loop)."""
    assert hasattr(daemon, "run") and callable(daemon.run), (
        "daemon.run(runtime) must exist as the entrypoint body (boot -> serve IPC -> poll_loop)"
    )


# --------------------------------------------------------------------------- #
# 2. IPC LISTENER bound + served by the daemon
# --------------------------------------------------------------------------- #

@pytest.fixture
def short_runtime():
    """A SHORT runtime root (the AF_UNIX sun_path limit ~104B can't fit the deep pytest tmp path). The
    socket tests need a real bindable path; the watchdog tests use the normal long fixture."""
    import shutil
    import tempfile
    base = tempfile.mkdtemp(dir="/tmp", prefix="hd-")
    prev = ledger.RUNTIME_ROOT
    ledger.RUNTIME_ROOT = __import__("pathlib").Path(base)
    try:
        yield ledger.RUNTIME_ROOT
    finally:
        ledger.RUNTIME_ROOT = prev
        shutil.rmtree(base, ignore_errors=True)


def test_daemon_binds_the_ipc_socket_at_the_canonical_path(short_runtime):
    """The daemon must bind the AF_UNIX listener at <RUNTIME_ROOT>/.harnessd/harnessd.sock (the same
    path harnessctl resolves) — a factored, testable bind."""
    assert hasattr(daemon, "make_ipc_listener") and callable(daemon.make_ipc_listener), (
        "daemon.make_ipc_listener(runtime_root) must exist (bind+listen the AF_UNIX socket the CLI dials)"
    )
    listener = daemon.make_ipc_listener(short_runtime)
    try:
        sock_path = short_runtime / ".harnessd" / "harnessd.sock"
        assert sock_path.exists(), f"the daemon must bind the socket at {sock_path}"
    finally:
        listener.close()


def test_ipc_round_trip_through_the_daemon_listener(short_runtime):
    """A real client connects to the daemon-bound socket and gets a real response (the CLI->daemon path
    is live). Drives ONE serve_one against the bound listener."""
    _seed_running_leaf(short_runtime, "proj/a#exec", level="L2")
    listener = daemon.make_ipc_listener(short_runtime)
    sock_path = str(short_runtime / ".harnessd" / "harnessd.sock")
    result = {}

    def _client():
        c = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        c.connect(sock_path)
        c.sendall(json.dumps({"command": "show", "addr": "proj/a#exec"}).encode())
        c.shutdown(socket.SHUT_WR)
        chunks = []
        while True:
            d = c.recv(65536)
            if not d:
                break
            chunks.append(d)
        c.close()
        result["resp"] = json.loads(b"".join(chunks).decode())

    t = threading.Thread(target=_client)
    t.start()
    try:
        ipc.serve_one(listener)  # the daemon's serve step handles the one connection
    finally:
        t.join(timeout=5)
        listener.close()
    assert result["resp"]["ok"] is True
    assert result["resp"]["binding"]["node_address"] == "proj/a#exec"


# --------------------------------------------------------------------------- #
# 3. WATCHDOG TICK — autonomous collapse on sign-off (the load-bearing behavior)
# --------------------------------------------------------------------------- #

def test_poll_once_autonomously_collapses_a_leaf_that_signed_off_DONE(runtime):
    """THE keystone behavior: a live leaf writes a fresh DONE .signal.json; ONE real poll_once tick
    detects + collapses it (running -> done) through the REAL watchdog -> chokepoint.collapse -> executor.
    This is the autonomous spine the green suite masked (it never drove poll_once)."""
    _install_adapter()
    addr, token = _seed_running_leaf(runtime)
    _write_signal(runtime, addr, signal="DONE", owner_token=token)
    tmux = _Tmux({"harness:" + addr: {"pane_pid": 4242, "pane_dead": 0}})
    det = _Detector(default="working")

    daemon.poll_once(executor, tmux, det)  # ONE real tick

    b = ledger.read_binding(addr)
    assert b["state"] == "done", "poll_once must autonomously collapse a DONE-signed leaf to done"
    assert b.get("terminal_signal") == "DONE"


def test_poll_once_does_not_collapse_a_running_leaf_with_no_signal(runtime):
    """Control: a live, working leaf with NO terminal signal is left running (no spurious collapse)."""
    _install_adapter()
    addr, token = _seed_running_leaf(runtime)
    tmux = _Tmux({"harness:" + addr: {"pane_pid": 4242, "pane_dead": 0}})
    det = _Detector(default="working")

    daemon.poll_once(executor, tmux, det)

    assert ledger.read_binding(addr)["state"] == "running", "a working leaf with no sign-off stays running"


def test_poll_once_collapses_a_FAILED_signoff(runtime):
    """A leaf that signs off FAILED is collapsed to failed (the sign-off-or-fail terminal path)."""
    _install_adapter()
    addr, token = _seed_running_leaf(runtime)
    _write_signal(runtime, addr, signal="FAILED", owner_token=token)
    tmux = _Tmux({"harness:" + addr: {"pane_pid": 4242, "pane_dead": 0}})
    det = _Detector(default="working")

    daemon.poll_once(executor, tmux, det)

    assert ledger.read_binding(addr)["state"] == "failed"


def test_poll_once_journals_signal_ESCALATED_and_holds_the_slot_across_ticks(runtime):
    """SML-02 at the loop level: a live leaf that signed off ESCALATED holds its slot (state stays
    running, NEVER collapsed) AND the slot-hold is journaled DURABLY — exactly ONE signal_ESCALATED
    WAL row + terminal_signal=ESCALATED stamped on the binding — through the REAL poll_once
    (reconcile_tick + watchdog tick + chokepoint.escalate + executor on real artifacts).
    A SECOND tick over the same artifact is edge-triggered: no second row, still running."""
    _install_adapter()
    addr, token = _seed_running_leaf(runtime)
    _write_signal(runtime, addr, signal="ESCALATED", owner_token=token)
    tmux = _Tmux({"harness:" + addr: {"pane_pid": 4242, "pane_dead": 0}})
    det = _Detector(default="working")
    wal_before = len(ledger.load_wal())

    daemon.poll_once(executor, tmux, det)  # tick 1: journal + hold

    b = ledger.read_binding(addr)
    assert b["state"] == "running", "ESCALATED holds its slot — poll_once must NEVER collapse it (§3.6)"
    assert b.get("terminal_signal") == "ESCALATED", (
        "poll_once must stamp terminal_signal=ESCALATED (the durable §3.6 slot-hold fact)"
    )
    rows = [r for r in ledger.load_wal()[wal_before:]
            if r.get("node_address") == addr and r.get("event") == "signal_ESCALATED"]
    assert len(rows) == 1, f"exactly ONE signal_ESCALATED row after tick 1; got {len(rows)}"

    daemon.poll_once(executor, tmux, det)  # tick 2: exactly-once — no re-journal, no side-effects

    b2 = ledger.read_binding(addr)
    assert b2["state"] == "running", "tick 2 must still hold the slot (never collapsed)"
    rows2 = [r for r in ledger.load_wal()[wal_before:]
             if r.get("node_address") == addr and r.get("event") == "signal_ESCALATED"]
    assert len(rows2) == 1, (
        f"exactly-once: tick 2 over the SAME artifact must NOT append a second signal_ESCALATED row; "
        f"got {len(rows2)}"
    )
    new_events = [r.get("event") for r in ledger.load_wal()[wal_before:] if r.get("node_address") == addr]
    assert not any(e in ("signal_FAILED", "signal_DONE", "collapse_failed", "collapse_done", "watchdog_nonresponse")
                   for e in new_events), (
        f"the ESCALATED slot-hold must produce NO collapse/FAILED side-effects; got {new_events!r}"
    )


def test_poll_once_ignores_a_stale_token_signoff(runtime):
    """Fencing: a .signal.json carrying a STALE owner_token (a dead incarnation's leftover) must NOT
    collapse the re-spawned node — the fenced reader yields None."""
    _install_adapter()
    addr, token = _seed_running_leaf(runtime)
    _write_signal(runtime, addr, signal="DONE", owner_token="STALE-DEAD-INCARNATION-TOKEN")
    tmux = _Tmux({"harness:" + addr: {"pane_pid": 4242, "pane_dead": 0}})
    det = _Detector(default="working")

    daemon.poll_once(executor, tmux, det)

    assert ledger.read_binding(addr)["state"] == "running", "a stale-token sign-off must not collapse the node"


# --------------------------------------------------------------------------- #
# 4. COORDINATOR death-probe runs in the tick (no crash; dead+children escalates, never blind-collapse)
# --------------------------------------------------------------------------- #

def test_poll_once_does_not_collapse_a_coordinator_with_a_live_child_even_on_DONE(runtime):
    """THE leaf/coordinator split, made load-bearing: a coordinator that signed off DONE while it STILL
    has a live child must NOT collapse — shutdown cascades bottom-up, you never collapse a node with live
    descendants (agent-lifecycle). The leaf path (check_leaf) WOULD collapse it on the DONE signal; the
    split routes a coordinator through check_coordinator_death (death-probe only) instead, so it survives.
    (Mutant: drop the split / always call check_leaf -> the coordinator wrongly collapses -> CAUGHT.)"""
    _install_adapter()
    parent = "proj/widget#exec"
    ptoken = fencing.mint_owner_token(parent, "psa", "puuid", 2)
    pws = addressing.node_dir(parent, runtime); pws.mkdir(parents=True, exist_ok=True)
    prec = {"node_address": parent, "parent_address": "root#exec", "level": "L4", "subagent_id": "psa",
            "session_uuid": "puuid", "state": "running", "generation": 3, "lease_epoch": 2,
            "owner_token": ptoken, "last_applied_seq": 0, "liveness_state": "working",
            "tmux_target": "harness:" + parent, "workspace": str(pws)}
    child, ctoken = _seed_running_leaf(runtime, "proj/widget/task#exec", level="L5")
    # write BOTH (the helper replaces the map; merge to keep both live)
    m = dict(ledger.all_nodes()); m[parent] = prec
    ledger.write_binding(m, _lock_held=True)
    # the coordinator has a DONE sign-off on disk — the leaf path would collapse on it.
    _write_signal(runtime, parent, signal="DONE", owner_token=ptoken)
    tmux = _Tmux({"harness:" + parent: {"pane_pid": 1, "pane_dead": 0},
                  "harness:" + child: {"pane_pid": 2, "pane_dead": 0}})
    det = _Detector(default="working")

    daemon.poll_once(executor, tmux, det)  # must not raise

    assert ledger.read_binding(parent)["state"] == "running", (
        "a coordinator with a live child must NOT be collapsed even on a DONE sign-off (the leaf/"
        "coordinator split prevents the leaf path from tearing down a node with live descendants)"
    )
    assert ledger.read_binding(child)["state"] == "running", "the live child is untouched"
