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
  5. F14 (daemon-1 / COMP-5) — `poll_once` stamps `runtime.json.last_tick_at` every tick, lock-free
     (§4.4) and best-effort: the §2.6 hang-detector surface the external harnessd-pinger reads.

BIAS TO REAL (Lesson 7): the REAL ledger, REAL watchdog, REAL chokepoint.collapse -> REAL executor; the
.signal.json is a REAL on-disk file (the agent's sign-off); only the actor-open adapter + tmux pane query
are faked (no model, no real pane). The loop-test drives the REAL poll_once (closing the system-level
test-masking, W2 LOW-6).
"""

import copy
import importlib
import json
import os
import socket
import threading
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

import harnessd.addressing as addressing
import harnessd.clock as clock
import harnessd.config as config
import harnessd.daemon as daemon
import harnessd.executor as executor
import harnessd.fencing as fencing
import harnessd.genesis as genesis
import harnessd.ipc as ipc
import harnessd.ledger as ledger
import harnessd.states as states
import harnessd.store as store
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
            # Mirrors the REAL adapter's post-F18 contract: tmux_target is the CANONICAL
            # '<session>:<window>.<pane>' triple create_detached returns (not the raw address).
            return SpawnResult(ok=True, session_uuid="s", model_used="m", role_variant="L5",
                               system_prompt_file="x", system_prompt_file_hash="h",
                               tmux_target=addressing.session_name_for(tmux_target) + ":0.0",
                               transcript_path="/tmp/s.jsonl", failure_class=None)
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


def test_agent_visible_signoff_collapses_through_real_tick(runtime):
    """F19, the 'real agent writes what the daemon reads' end-to-end proof: the node is spawned
    through the REAL chokepoint (which seeds the .sign-off.<seat>.json handshake post-claim), then a
    helper signs off using ONLY agent-visible inputs — it reads the handshake in its own node dir,
    writes .signal.<seat>.json {signal, ts, owner_token: <from handshake>, evidence} via tmp+rename,
    and NEVER touches the ledger. ONE real poll_once tick collapses the node to done through the REAL
    watchdog -> chokepoint.collapse -> executor, and the run-ledger row appears. Mirrors the
    _write_signal keystone above but sources the token the way a real agent must (the keystone
    helper reads the token off the ledger — a channel no real agent has)."""
    _install_adapter()
    addr = "proj/widget/task#exec"
    registered_token = fencing.mint_owner_token(addr, "sa", "uuid", 1)
    ws = addressing.node_dir(addr, runtime)
    ws.mkdir(parents=True, exist_ok=True)
    rec = {"node_address": addr, "parent_address": "proj/widget#exec", "level": "L5",
           "subagent_id": "sa", "session_uuid": "uuid", "state": "planned", "generation": 0,
           "lease_epoch": 1, "owner_token": registered_token, "last_applied_seq": 0,
           "liveness_state": "claimed", "gate_crossed_at": None, "paused_at": None,
           "tmux_target": "harness:" + addr, "workspace": str(ws),
           "stale_check_count": 0, "stale_grace_checks": 2}
    ledger.write_binding({addr: copy.deepcopy(rec)}, _lock_held=True)
    spawn = chokepoint.claim_and_spawn(
        addr, expected_state="planned", expected_generation=0,
        expected_owner_token=registered_token, level_config=config.LevelConfig.for_level("L5"),
    )
    assert spawn.ok, "the real spawn path must succeed (it seeds the handshake)"

    # ---- The "agent": ONLY agent-visible inputs (files in its own node dir; no ledger read). ----
    handshake = json.loads((ws / ".sign-off.exec.json").read_text(encoding="utf-8"))
    signal_path = Path(handshake["signal_path"])  # absolute, delivered by the handshake
    tmp = signal_path.with_name(signal_path.name + ".tmp")
    tmp.write_text(json.dumps({"signal": "DONE", "ts": clock.now_utc(),
                               "owner_token": handshake["owner_token"],
                               "evidence": {"report": "report.md"}}), encoding="utf-8")
    os.replace(tmp, signal_path)  # the agent's atomic last act

    # The fake tmux is keyed by the CANONICAL target STEP4 recorded on the binding (F18) — the
    # exact key the reconcile sweep / pane_alive look up against list_targets().
    live_target = ledger.read_binding(addr)["tmux_target"]
    tmux = _Tmux({live_target: {"pane_pid": 4242, "pane_dead": 0}})
    det = _Detector(default="working")
    wal_before = len(ledger.load_wal())

    daemon.poll_once(executor, tmux, det)  # ONE real tick

    b = ledger.read_binding(addr)
    assert b["state"] == "done", (
        "an agent signing off from ONLY agent-visible files (handshake -> signal artifact) must "
        "collapse through one real poll_once tick — the daemon must read what the agent wrote"
    )
    assert b.get("terminal_signal") == "DONE"
    done_event = states.TERMINAL_VOCAB["signal_DONE"].event
    events = [r.get("event") for r in ledger.load_wal()[wal_before:] if r.get("node_address") == addr]
    assert done_event in events, f"the {done_event} run-ledger row must land; got {events!r}"


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


def test_poll_once_collapses_a_coordinator_whose_children_are_all_terminal(runtime):
    """THE 2026-06-11 LIVE-RUN WEDGE: the leaf/coordinator split silently dropped terminal-signal
    processing for coordinators ENTIRELY — an L4/L2 that signed off DONE after all its children
    finished was never collapsed, never woke its parent, and the upward path froze with the whole
    subtree green. The correct semantics: live-child protection (the test above) PLUS terminal-
    signal-first once every descendant is terminal. (Mutant: keep the death-probe-only coordinator
    branch -> the parent stays running forever -> CAUGHT.)"""
    _install_adapter()
    parent = "proj/widget#exec"
    ptoken = fencing.mint_owner_token(parent, "psa", "puuid", 2)
    pws = addressing.node_dir(parent, runtime); pws.mkdir(parents=True, exist_ok=True)
    prec = {"node_address": parent, "parent_address": "root#exec", "level": "L4", "subagent_id": "psa",
            "session_uuid": "puuid", "state": "running", "generation": 3, "lease_epoch": 2,
            "owner_token": ptoken, "last_applied_seq": 0, "liveness_state": "working",
            "tmux_target": "harness:" + parent, "workspace": str(pws)}
    child, ctoken = _seed_running_leaf(runtime, "proj/widget/task#exec", level="L5")
    m = dict(ledger.all_nodes()); m[parent] = prec
    m[child]["state"] = "done"  # the child already collapsed — ALL descendants terminal
    m[child]["terminal_signal"] = "DONE"
    ledger.write_binding(m, _lock_held=True)
    _write_signal(runtime, parent, signal="DONE", owner_token=ptoken)
    tmux = _Tmux({"harness:" + parent: {"pane_pid": 1, "pane_dead": 0}})
    det = _Detector(default="working")

    daemon.poll_once(executor, tmux, det)  # ONE real tick

    b = ledger.read_binding(parent)
    assert b["state"] == "done", (
        "a coordinator whose descendants are ALL terminal and who signed off DONE must collapse "
        "(terminal-signal-first applies to every node; only the idle ladder is leaf-only) — "
        "the 2026-06-11 live run wedged exactly here"
    )
    assert b.get("terminal_signal") == "DONE"
    assert ledger.read_binding(child)["state"] == "done", "the terminal child is untouched"


# --------------------------------------------------------------------------- #
# 5. F14 — runtime.json.last_tick_at stamped on EVERY poll_once (findings daemon-1 / COMP-5).
#    The DAEMON §2.6 hang-detector surface: the external harnessd-pinger reads last_tick_at and
#    kills a wedged-but-alive daemon when the stamp goes stale (3 missed ticks). Without the
#    stamp, the third death mode (hang: process alive, loop wedged) is INVISIBLE — launchd's
#    exit-only KeepAlive never fires. The stamp follows the §4.4 lock-free sidecar carve-out
#    exactly: read-merge the §2.3 boot descriptor, atomic_replace, NEVER store.file_lock,
#    ZERO WAL rows, best-effort (a stamp hiccup never aborts the reconcile sweep).
# --------------------------------------------------------------------------- #

def _tick_fixture(runtime):
    """One seeded live leaf + alive pane + working detector — the minimal drivable real tick."""
    _install_adapter()
    addr, token = _seed_running_leaf(runtime)
    tmux = _Tmux({"harness:" + addr: {"pane_pid": 4242, "pane_dead": 0}})
    det = _Detector(default="working")
    return addr, token, tmux, det


def test_poll_once_stamps_runtime_json_last_tick_at(runtime):
    """THE headline F14 fact: ONE real poll_once tick leaves a tz-aware UTC last_tick_at in
    <runtime_root>/runtime.json. Mutant killed: no stamp -> the §2.6 pinger has no surface — a
    wedged-but-alive daemon is undetectable (daemon-1 / COMP-5)."""
    addr, token, tmux, det = _tick_fixture(runtime)

    daemon.poll_once(executor, tmux, det)  # ONE real tick

    rj = runtime / "runtime.json"
    assert rj.is_file(), (
        "poll_once must stamp runtime.json (self-healing a missing descriptor) — the §2.6 "
        "hang-detector surface the external harnessd-pinger reads"
    )
    data = json.loads(rj.read_text(encoding="utf-8"))
    assert "last_tick_at" in data, (
        "runtime.json must carry last_tick_at after a tick (DAEMON §2.3/§2.6 — the field the "
        "pinger keys its staleness bound on)"
    )
    stamped = datetime.fromisoformat(data["last_tick_at"])
    assert stamped.tzinfo is not None, (
        "last_tick_at must be a tz-AWARE UTC instant (the single canonical clock, DAEMON §4.6)"
    )


def test_last_tick_stamp_preserves_the_boot_descriptor_fields(runtime):
    """The stamp is a READ-MERGE of the §2.3 boot descriptor, not a wholesale rewrite: build_id /
    started_at / lock_path written by the REAL genesis.write_runtime_json must survive the tick
    (the pinger and `service status` read them too). Also pins the F6-deferred descriptor-schema
    change: write_runtime_json accepts + writes the lock_path field (§2.3 self-report; the kwarg
    was deferred from commit 355feae into F14 per the conflict report). Mutant killed: a wholesale
    {last_tick_at: ...} rewrite that clobbers the boot fields."""
    lock_path = str(genesis.instance_lock_path(runtime))
    genesis.write_runtime_json(runtime, build_id="b-14", lock_path=lock_path)
    boot_descriptor = json.loads((runtime / "runtime.json").read_text(encoding="utf-8"))
    assert boot_descriptor.get("lock_path") == lock_path, (
        "write_runtime_json must write the §2.3 lock_path field naming the INSTANCE lock (the "
        "F6-deferred descriptor-schema change, folded into F14)"
    )
    started_at = boot_descriptor["started_at"]

    addr, token, tmux, det = _tick_fixture(runtime)
    daemon.poll_once(executor, tmux, det)

    data = json.loads((runtime / "runtime.json").read_text(encoding="utf-8"))
    assert data.get("build_id") == "b-14", (
        "the last_tick_at stamp must PRESERVE the boot descriptor's build_id (read-merge, not a "
        "wholesale rewrite of runtime.json)"
    )
    assert data.get("started_at") == started_at, (
        "the stamp must not disturb started_at — the pinger discriminates 'just-booted' from "
        "'wedged' on it"
    )
    assert data.get("lock_path") == lock_path, (
        "the stamp must preserve the §2.3 lock_path self-report field"
    )
    assert "last_tick_at" in data, "the stamp itself must land alongside the preserved boot fields"


def test_last_tick_stamp_is_lock_free_and_appends_zero_wal_rows(runtime, monkeypatch):
    """The §4.4 carve-out, held to the letter: the stamp NEVER enters store.file_lock (poisoned
    here — any acquisition raises) and appends ZERO WAL rows (a liveness mirror, not control
    state; recovery never trusts it). Mutant killed: stamping under the EX serialization lock
    (serializes a non-event against real mutations every tick) or journaling the stamp."""
    def _poisoned_lock(*_args, **_kwargs):
        raise AssertionError(
            "the last_tick_at stamp must be LOCK-FREE (DAEMON §4.4) — it must NOT take the EX "
            "serialization lock (that would serialize a non-event against real mutations every tick)"
        )

    monkeypatch.setattr(store, "file_lock", _poisoned_lock)
    wal_before = len(ledger.load_wal())

    path = daemon.stamp_last_tick(runtime)  # must succeed with the lock poisoned

    assert path == runtime / "runtime.json", "stamp_last_tick returns the written descriptor path"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "last_tick_at" in data, "the lock-free stamp must still land on disk (atomic_replace)"
    assert len(ledger.load_wal()) == wal_before, (
        "the stamp is a best-effort MIRROR, not the durable journal — it must append ZERO WAL "
        "rows (DAEMON §4.4: recovery NEVER trusts the sidecar surfaces)"
    )


def test_last_tick_at_advances_on_every_tick(runtime, monkeypatch):
    """The stamp OVERWRITES every tick (never setdefault/write-once): with the canonical clock
    scripted to t1 then t2, runtime.json carries t1 after tick 1 and t2 after tick 2. Mutant
    killed: write-once semantics — a stamp that never advances looks permanently fresh-then-stale
    and defeats the §2.6 staleness-bound math (3 missed ticks)."""
    t1 = "2026-06-10T12:00:00+00:00"
    t2 = "2026-06-10T12:00:05+00:00"
    cell = {"now": t1}
    monkeypatch.setattr(clock, "now_utc", lambda: cell["now"])
    addr, token, tmux, det = _tick_fixture(runtime)

    daemon.poll_once(executor, tmux, det)  # tick 1 at t1
    data1 = json.loads((runtime / "runtime.json").read_text(encoding="utf-8"))
    assert data1.get("last_tick_at") == t1, (
        f"after tick 1 the stamp must be t1 ({t1}); got {data1.get('last_tick_at')!r}"
    )

    cell["now"] = t2
    daemon.poll_once(executor, tmux, det)  # tick 2 at t2
    data2 = json.loads((runtime / "runtime.json").read_text(encoding="utf-8"))
    assert data2.get("last_tick_at") == t2, (
        f"the stamp must ADVANCE on every tick (overwrite, not setdefault): after tick 2 it must "
        f"be t2 ({t2}); got {data2.get('last_tick_at')!r}"
    )


def test_poll_once_survives_a_failed_stamp(runtime, monkeypatch):
    """Best-effort isolation (the same §4.4 discipline poll_loop applies to write_status): a stamp
    that raises must NOT abort the tick — poll_once returns cleanly and the tick's REAL work (the
    watchdog collapse of a DONE-signed leaf) still lands. Mutant killed: an unguarded stamp call
    whose disk hiccup aborts the reconcile sweep."""
    addr, token, tmux, det = _tick_fixture(runtime)
    _write_signal(runtime, addr, signal="DONE", owner_token=token)

    def _raising_stamp(*_args, **_kwargs):
        raise OSError("disk hiccup — the runtime root is briefly unwritable")

    monkeypatch.setattr(daemon, "stamp_last_tick", _raising_stamp)

    daemon.poll_once(executor, tmux, det)  # must NOT raise

    b = ledger.read_binding(addr)
    assert b["state"] == "done", (
        "the tick's reconcile/watchdog work must still land when the stamp fails — the stamp is "
        "best-effort, never load-bearing for the sweep"
    )
