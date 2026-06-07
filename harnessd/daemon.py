"""daemon — the harnessd resident loop: boot (lock + runtime.json + genesis) + the reconcile timer.

The daemon is the ROOT of the supervision-tree custody chain — it starts L1, which has no parent
agent (DAEMON §7: "L1 has no parent agent — the daemon is what starts L1"). It is launchd-hosted
(KeepAlive/RunAtLoad, §2.2): relaunch = recovery. Three responsibilities (IMPLEMENTATION-PLAN §3
module table, daemon.py row):
  * ``boot`` — write the §2.3 runtime.json descriptor, then run genesis end-to-end (lock ->
    runtime.json -> preconditions -> reconcile_on_restart -> spawn-or-resume L1, Integration A).
  * ``poll_loop`` — reconcile_tick on a timer (an unbounded NoReturn resident loop), with the body
    FACTORED into a single drivable iteration (``poll_once``) so a test can drive exactly ONE tick.
  * ``write_status`` — the lock-FREE status sidecar (the ONE deliberate atomicity carve-out, §4.4):
    a best-effort liveness mirror written every poll WITHOUT the EX lock (taking the lock would
    serialize a non-event against real mutations every tick). Recovery NEVER trusts it (the ledger is
    truth).

Authoritative sources:
  - IMPLEMENTATION-PLAN §2.12 (``boot(runtime) -> None`` / ``poll_loop(interval_s) -> NoReturn``),
    §3 module table (daemon.py row, L64), §3 on-disk tree (runtime.json L459 / status.json L460).
  - DAEMON §2.2 (service-manager-hosted), §2.3 (runtime.json / status.json), §4.4 (the lock-free
    status carve-out), §5.2 (continuous reconciliation), §7 (the genesis sequence boot drives).

BUILDER DECISIONS (the §2.12 details the frozen tests leave open — stated in the build report):

  * THE ``runtime`` DESCRIPTOR SHAPE — §2.12 names ``boot(runtime)``; the test threads a permissive
    SimpleNamespace carrying ``runtime_root`` / ``build_id`` / ``config`` (the genesis config) /
    ``adapter`` (the RuntimeAdapter to wire into the chokepoint) / ``tmux`` / ``executor``. boot reads
    them defensively. FORK-DAEMON-RUNTIME: the precise carrier is the caller's; the load-bearing facts
    (boot writes runtime.json AND runs genesis end-to-end) are pinned by the tests.

  * THE ADAPTER WIRING — production boot wires the concrete adapter into the chokepoint via the
    module-level seam (``chokepoint.set_adapter``), exactly the ledger.RUNTIME_ROOT precedent. The
    test pre-installs its FakeAdapter, so boot wires the runtime's adapter ONLY when one is supplied
    (it does NOT clobber a pre-installed test adapter with None).

  * status.json SHAPE + PATH — the §2.3 liveness fields (``pid`` / ``started_at`` / ``incarnation``
    + a best-effort ``runtime_root``), written to ``<runtime_root>/.harnessd/status.json`` (the §3
    on-disk tree, L460). Written via ``store.atomic_replace`` (tmp + fsync + os.replace) so the
    sidecar is never torn — but CRUCIALLY WITHOUT the EX lock (the §4.4 carve-out): the writer never
    enters ``store.file_lock``. It is NOT control state — it appends ZERO WAL rows.

  * THE SINGLE-ITERATION FACTOR — ``poll_once`` is the loop body (ONE ``reconcile.reconcile_tick``);
    ``poll_loop`` is the unbounded NoReturn resident loop that calls ``poll_once`` on the timer. The
    factor lets a test drive exactly one iteration; the unbounded loop is never run in a test path.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import NoReturn, Optional

from harnessd import clock as _clock
from harnessd import genesis as _genesis_mod
from harnessd import ipc as _ipc_mod
from harnessd import ledger, states, store
from harnessd import reconcile as _reconcile_mod
from harnessd import watchdog as _watchdog_mod
from harnessd.spawn import chokepoint
from harnessd.spawn import outbox as _outbox_mod


# ---------------------------------------------------------------------------
# boot — the daemon entry: write runtime.json, then run genesis end-to-end (§2.12).
# ---------------------------------------------------------------------------

def _runtime_root(runtime) -> Path:
    """Resolve the runtime root from the runtime descriptor (falls back to ledger.RUNTIME_ROOT)."""
    root = getattr(runtime, "runtime_root", None)
    if root is None:
        cfg = getattr(runtime, "config", None)
        root = getattr(cfg, "runtime_root", None)
    if root is not None:
        return Path(root)
    if ledger.RUNTIME_ROOT is not None:
        return Path(ledger.RUNTIME_ROOT)
    raise RuntimeError(
        "daemon runtime_root is not configured: pass runtime.runtime_root or bind ledger.RUNTIME_ROOT"
    )


def boot(runtime) -> None:
    """Daemon boot (§2.12): write the §2.3 runtime.json descriptor, then run genesis end-to-end.

    (a) Wire the concrete RuntimeAdapter into the ONE spawn chokepoint (the module-level seam) WHEN
        the runtime supplies one — production wires the real adapter; a test pre-installs its fake and
        passes no adapter (so boot does not clobber it).
    (b) Write ``runtime.json`` (the §2.3 daemon runtime descriptor: build-id / started_at / pid) so a
        crash between here and the first genesis write still leaves the descriptor on disk.
    (c) Run genesis END-TO-END (lock -> runtime.json -> preconditions -> reconcile_on_restart ->
        spawn-or-resume L1) through the REAL chokepoint + REAL reconcile + REAL on-disk ledger
        (Integration A) — so on first boot the L1 root is spawned in-role.

    genesis itself re-writes runtime.json inside its held EX lock (§7 step 3); writing it here too is
    deliberate (boot owns the descriptor independent of whether genesis reaches its own write) and is
    idempotent (the same atomic-replace target).
    """
    runtime_root = _runtime_root(runtime)
    build_id = getattr(runtime, "build_id", None)
    cfg = getattr(runtime, "config", None)
    if build_id is None and cfg is not None:
        build_id = getattr(cfg, "build_id", None)

    # (a) Wire the supplied adapter into the chokepoint (do NOT clobber a pre-installed test adapter).
    adapter = getattr(runtime, "adapter", None)
    if adapter is not None:
        chokepoint.set_adapter(adapter)

    # (b) Write the §2.3 runtime descriptor.
    _genesis_mod.write_runtime_json(runtime_root, build_id=build_id)

    # (c) Run genesis end-to-end (the REAL chokepoint + reconcile + on-disk ledger).
    executor = getattr(runtime, "executor", None)
    if executor is None:
        from harnessd import executor as executor  # noqa: F811 — production default
    tmux = getattr(runtime, "tmux", None)
    if cfg is None:
        raise RuntimeError("daemon.boot requires runtime.config (the genesis config) to run genesis")
    _genesis_mod.run_genesis(executor, tmux, cfg)
    return None


# ---------------------------------------------------------------------------
# poll_once / poll_loop — the continuous reconcile sweep (§5.2). poll_once is the SINGLE-iteration
# factor a test drives; poll_loop is the unbounded NoReturn resident loop (NEVER run in a test).
# ---------------------------------------------------------------------------

def poll_once(executor, tmux, detector) -> None:
    """ONE poll-loop iteration: run exactly ONE ``reconcile.reconcile_tick`` (§5.2, edge-triggered).

    The factored loop body (§2.12: "factor it so a test can drive a SINGLE iteration"). One tick
    re-derives liveness via the detector and applies the §5.1 resolutions edge-triggered — only a
    state/condition CHANGE appends a run-ledger row. poll_loop calls this on the timer; a test drives
    it exactly once.

    The SAME tick also drains the spawn-request OUTBOXES (FORK-SPAWN-CHANNEL): every live non-leaf
    node's pending child-spawn requests are adjudicated + spawned through the chokepoint. This is how a
    PARENT AGENT's spawn-request becomes a live child — the agent drops a request in its workroot, the
    next poll services it. Best-effort + isolated: an outbox error NEVER aborts the reconcile sweep
    (the supervision tree's liveness must keep advancing even if one node's request is malformed).
    """
    _reconcile_mod.reconcile_tick(executor, tmux, detector)
    _watchdog_tick(executor, tmux, detector)
    _service_outboxes_best_effort()
    return None


def _service_outboxes_best_effort() -> None:
    """Drain all spawn-request outboxes; swallow any error so it never aborts the reconcile sweep."""
    try:
        _outbox_mod.service_all_outboxes()
    except Exception:  # noqa: BLE001 — the reconcile sweep must advance regardless of one bad outbox
        pass


# ---------------------------------------------------------------------------
# _watchdog_tick — the §2.9 watchdog as a verdict+policy invoked by ①'s in-process sweep (WATCHDOG.md
# L214: "② is a verdict + policy function invoked by ①'s in-process sweep, NOT a separate polling
# daemon"). THE keystone wiring the review found missing: without this, no node ever auto-collapses on
# sign-off, no idle leaf ever fails-loud, no coordinator-death is probed.
# ---------------------------------------------------------------------------

def _is_coordinator(node_address: str, bindings: dict) -> bool:
    """A COORDINATOR has at least one (live-or-any) descendant binding (§5.4). Mirrors reconcile's split:
    primary = another binding names this node as ``parent_address``; fallback = address-prefix arithmetic
    on the one-spine path (a descendant's path begins with ``<this-path>/``)."""
    this_path = node_address.split("#", 1)[0]
    for other_address, other in bindings.items():
        if other_address == node_address:
            continue
        if other.get("parent_address") == node_address:
            return True
        other_path = other_address.split("#", 1)[0]
        if other_path.startswith(this_path + "/"):
            return True
    return False


def _watchdog_tick(executor, tmux, detector) -> None:
    """Run the §2.9 watchdog verdict+policy over every LIVE node, edge-triggered, leaf/coordinator-split.

    LEAF (ephemeral L5/L5+): ``watchdog.check_leaf`` — terminal-signal-FIRST collapse (a fenced DONE/
    FAILED ``.signal.json`` routes through ``chokepoint.collapse`` -> the REAL executor) then the
    idle->prod->FAILED ladder. ``check_leaf`` ENACTS its action and returns a WatchdogAction.
    COORDINATOR (persistent): ``watchdog.check_coordinator_death`` — the dead-pid+live-children ->
    ESCALATE probe (never blind-collapsed; the full evidence-lease recovery machine is DEFERRED, per
    WATCHDOG.md §1). A coordinator is NOT run through the leaf sign-off/ladder (the §5.4 split: do not
    auto-fail a coordinator for idle — it may be waiting on children).

    Liveness is injected into the watchdog via its ``set_liveness`` seam so ``check_leaf`` reads THIS
    sweep's detector verdict. Each node is isolated: one node's watchdog error never aborts the sweep
    (the supervision tree must keep advancing — the same best-effort discipline as the outbox drain).
    """
    if detector is not None:
        _watchdog_mod.set_liveness(lambda addr: detector.liveness(addr))
    try:
        now = _clock.now_utc()
        bindings = ledger.all_nodes()
        for address, binding in list(bindings.items()):
            if states.is_terminal(binding.get("state")):
                continue
            # The watchdog's ``node`` arg is the node OBJECT (a dict carrying node_address / tmux_target /
            # transcript_path — read by read_terminal_signal + pane_alive), NOT the bare address string.
            # The binding dict carries those fields, so it serves as both ``node`` and ``binding``.
            try:
                if _is_coordinator(address, bindings):
                    _watchdog_mod.check_coordinator_death(binding, binding, ledger)
                else:
                    _watchdog_mod.check_leaf(binding, binding, now=now)
            except Exception:  # noqa: BLE001 — one node's watchdog fault must not abort the whole sweep
                continue
    finally:
        if detector is not None:
            _watchdog_mod.set_liveness(None)  # restore the default detector.liveness seam


def poll_loop(interval_s, executor=None, tmux=None, detector=None) -> NoReturn:
    """The unbounded resident reconcile loop (§2.12 / §5.2): ``reconcile_tick`` on a timer, forever.

    NoReturn — an always-on resident loop (the daemon is always-on; relaunch is recovery, §2.2). The
    body is FACTORED into ``poll_once`` (the single-iteration factor a test drives) so the unbounded
    loop is never exercised in a test path: each iteration runs ONE ``poll_once`` then sleeps
    ``interval_s``, and (best-effort) writes the lock-free status sidecar.

    The production defaults wire the real executor + tmux + detector; this signature keeps them
    injectable (the daemon assembles them at boot). This function is NEVER called in a test — the test
    asserts only its declared shape and drives ``poll_once`` directly.
    """
    if executor is None:
        from harnessd import executor as executor  # noqa: F811 — production default
    while True:  # NoReturn — the always-on resident loop (never driven unbounded in a test)
        poll_once(executor, tmux, detector)
        try:
            write_status(ledger.RUNTIME_ROOT)
        except Exception:
            # The status sidecar is best-effort (§4.4) — a write hiccup must not kill the resident loop.
            pass
        time.sleep(interval_s)


# ---------------------------------------------------------------------------
# write_status — the lock-FREE status sidecar (the ONE deliberate atomicity carve-out, §4.4).
# ---------------------------------------------------------------------------

def write_status(runtime_root, status: Optional[dict] = None) -> Optional[Path]:
    """Write the best-effort liveness sidecar ``status.json`` — LOCK-FREE (the §4.4 carve-out).

    The ONE deliberate carve-out: status.json is written every poll WITHOUT the EX serialization lock
    (taking the lock would serialize a non-event against real mutations every tick). This writer NEVER
    enters ``store.file_lock`` — it writes the sidecar via the lock-free ``store.atomic_replace`` (tmp
    + fsync + os.replace, so the sidecar is never TORN, but no lock is taken). It is NOT durable
    control state: it appends ZERO WAL rows (recovery NEVER trusts the sidecar — the ledger is truth).

    Path: ``<runtime_root>/.harnessd/status.json`` (the §3 on-disk tree). Carries the §2.3 liveness
    fields (pid / started_at / incarnation, whatever the caller supplies) + a best-effort runtime_root.
    Returns the written path, or None when no runtime_root is resolvable (best-effort).
    """
    import os

    from harnessd import clock

    if runtime_root is None:
        runtime_root = ledger.RUNTIME_ROOT
    if runtime_root is None:
        return None
    runtime_root = Path(runtime_root)

    payload = dict(status or {})
    # Fill the §2.3 liveness fields the caller did not supply (best-effort defaults).
    payload.setdefault("pid", os.getpid())
    payload.setdefault("started_at", clock.now_utc())
    payload.setdefault("runtime_root", str(runtime_root))

    path = runtime_root / ".harnessd" / "status.json"

    import json

    def render(handle):
        json.dump(payload, handle, ensure_ascii=True, sort_keys=True, indent=2)
        handle.write("\n")

    # LOCK-FREE: atomic_replace is tmp+fsync+os.replace — it NEVER takes store.file_lock (§4.4).
    store.atomic_replace(path, render)
    return path


# ---------------------------------------------------------------------------
# IPC listener — bind+serve the AF_UNIX control socket the CLI dials (FORK-IPC / FORK-SOCKET-PATH). The
# review found serve_forever had NO production caller: the whole CLI->daemon path was dead. The daemon
# binds the listener at boot and serves it in a thread alongside poll_loop.
# ---------------------------------------------------------------------------

# Mirror harnessctl's resolution so client + daemon agree on the path WITHOUT importing the CLI here.
_IPC_DIRNAME = ".harnessd"
_IPC_SOCKET_FILENAME = "harnessd.sock"


def ipc_socket_path(runtime_root) -> Path:
    """The canonical IPC socket path: ``<runtime_root>/.harnessd/harnessd.sock`` (harnessctl's default)."""
    if runtime_root is None:
        runtime_root = ledger.RUNTIME_ROOT
    return Path(runtime_root) / _IPC_DIRNAME / _IPC_SOCKET_FILENAME


def make_ipc_listener(runtime_root) -> "socket.socket":
    """Bind + listen the AF_UNIX control socket at the canonical path; return the listening socket.

    A STALE socket file (a prior daemon's leftover after a crash) is unlinked before bind (AF_UNIX bind
    fails EADDRINUSE on an existing path even if no listener holds it). The caller owns the socket
    lifecycle (close on shutdown); ``serve_forever`` loops ``serve_one`` over it.
    """
    import os
    import socket

    path = ipc_socket_path(runtime_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        if path.exists():
            os.unlink(path)  # clear a stale leftover socket file so bind() succeeds
    except OSError:
        pass
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sp = str(path)
    # AF_UNIX sun_path is ~104 bytes (FORK-IPC-SOCKET-LEN). A deeply-nested RUNTIME_ROOT can exceed it.
    # Fallback: chdir to the socket's parent + bind the BASENAME (a short relative path), then restore.
    # Safe here because make_ipc_listener runs ONCE at boot, single-threaded, before the serve thread.
    if len(sp.encode("utf-8")) < 100:
        listener.bind(sp)
    else:
        old_cwd = os.getcwd()
        try:
            os.chdir(str(path.parent))
            listener.bind(path.name)
        finally:
            os.chdir(old_cwd)
    listener.listen(64)
    return listener


# ---------------------------------------------------------------------------
# run — THE process entrypoint body (the keystone): boot -> serve IPC (thread) -> poll_loop. Invoked by
# the __main__ guard so ``python3 -m harnessd.daemon`` actually runs the resident daemon.
# ---------------------------------------------------------------------------

def run(runtime, *, interval_s: float = 5.0) -> NoReturn:
    """Assemble + run the resident daemon: (1) ``boot(runtime)`` (runtime.json + genesis end-to-end);
    (2) bind the IPC listener + serve it forever in a DAEMON THREAD (the CLI->daemon control plane);
    (3) enter the unbounded ``poll_loop`` (reconcile + watchdog + outbox on the timer). NoReturn — the
    always-on resident process (relaunch is recovery, §2.2).

    The IPC serve runs in a separate thread so a blocking ``accept()`` never stalls the reconcile/watchdog
    sweep, and the sweep never stalls request handling. Both route every MUTATION through the ONE
    executor under the ONE EX lock (the single-writer invariant holds across the two threads — fcntl
    serializes them).
    """
    import threading

    boot(runtime)

    runtime_root = _runtime_root(runtime)
    listener = make_ipc_listener(runtime_root)
    serve_thread = threading.Thread(
        target=_ipc_mod.serve_forever, args=(listener,), name="harnessd-ipc", daemon=True
    )
    serve_thread.start()

    # Resolve the sweep collaborators (production defaults; a test never calls run()).
    from harnessd import executor as _executor
    from harnessd.spawn import tmux as _tmux
    from harnessd import detector as _detector
    poll_loop(interval_s, executor=_executor, tmux=_tmux, detector=_detector)


if __name__ == "__main__":  # pragma: no cover — the launchd-hosted process entry
    # `python3 -m harnessd.daemon`: assemble the runtime descriptor from config + run the daemon. The
    # concrete RuntimeAdapter + config wiring is the commissioning seam; run() boots, serves, and loops.
    from harnessd import config as _config

    _runtime_descriptor = _config.build_runtime_descriptor() if hasattr(_config, "build_runtime_descriptor") else None
    if _runtime_descriptor is None:
        raise SystemExit(
            "harnessd.daemon: no runtime descriptor — commissioning must supply config.build_runtime_descriptor() "
            "(the OAuth env + L1 address/level + pinned binary + adapter). See DAEMON §2.12 / genesis."
        )
    run(_runtime_descriptor)
