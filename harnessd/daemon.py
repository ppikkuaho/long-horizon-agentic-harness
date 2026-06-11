"""daemon — the harnessd resident loop: boot (instance-lock + runtime.json + genesis) + the
reconcile timer.

The daemon is the ROOT of the supervision-tree custody chain — it starts L1, which has no parent
agent (DAEMON §7: "L1 has no parent agent — the daemon is what starts L1"). It is launchd-hosted
(KeepAlive/RunAtLoad, §2.2): relaunch = recovery. Three responsibilities (IMPLEMENTATION-PLAN §3
module table, daemon.py row):
  * ``boot`` — acquire the PERSISTENT single-instance lock (`.harnessd.instance.lock`, §2.3 —
    held for the process lifetime; a second instance refuses LOUDLY before writing anything),
    then write the §2.3 runtime.json descriptor, then run genesis end-to-end (lock ->
    runtime.json -> preconditions -> reconcile_on_restart -> spawn-or-resume L1, Integration A).
  * ``poll_loop`` — reconcile_tick on a timer (an unbounded NoReturn resident loop), with the body
    FACTORED into a single drivable iteration (``poll_once``) so a test can drive exactly ONE tick.
  * ``write_status`` — the lock-FREE status sidecar (the ONE deliberate atomicity carve-out, §4.4):
    a best-effort liveness mirror written every poll WITHOUT the EX lock (taking the lock would
    serialize a non-event against real mutations every tick). Recovery NEVER trusts it (the ledger is
    truth). The SAME carve-out covers ``stamp_last_tick``: ``poll_once`` stamps
    ``runtime.json.last_tick_at`` lock-free every tick — the §2.6 hang-detector surface the external
    harnessd-pinger reads (best-effort, zero WAL rows, recovery never trusts it).

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

import fcntl
import time
from pathlib import Path
from typing import IO, NoReturn, Optional, Tuple

from harnessd import clock as _clock
from harnessd import genesis as _genesis_mod
from harnessd import ipc as _ipc_mod
from harnessd import ledger, states, store
from harnessd import reconcile as _reconcile_mod
from harnessd import watchdog as _watchdog_mod
from harnessd.spawn import chokepoint
from harnessd.spawn import outbox as _outbox_mod


# ---------------------------------------------------------------------------
# The §2.3 single-instance guard — a PERSISTENT flock on `.harnessd.instance.lock`, acquired
# non-blocking at boot and held for the process lifetime. DELIBERATELY a separate file from the
# §4.3 per-mutation `.harnessd.lock`: flock conflicts across fds even within one process, so a
# lifetime hold of the mutation-lock file would deadlock every executor mutation (the resolved
# DAEMON §2.3-vs-§4.3 conflict, review SWCAS-02; fork decided 2026-06-10: separate file).
# ---------------------------------------------------------------------------

class DaemonAlreadyRunning(RuntimeError):
    """The §2.3 single-instance refusal — another harnessd instance already holds the lock.

    Raised by ``acquire_instance_lock`` BEFORE boot writes anything (adapter wiring, runtime.json,
    genesis), so a refused second daemon clobbers NOTHING. launchd will not spawn two, but a
    manual launch must not race the service-managed one (DAEMON §2.3). Under launchd KeepAlive a
    duplicate plist would re-raise every ThrottleInterval (≥10s) — loud and throttled, by design.
    """


# The lifetime hold: (path, open handle). The flock dies with the fd/process; tests release it
# explicitly via release_instance_lock(). Module-global on purpose — the daemon process is the
# unit of single-instance-ness, not any one boot() call.
_INSTANCE_LOCK: Optional[Tuple[Path, IO]] = None


def acquire_instance_lock(runtime_root) -> Path:
    """Acquire the §2.3 PERSISTENT single-instance lock; hold it for the process lifetime.

    Non-blocking LOCK_EX|LOCK_NB via ``store.flock_exclusive_nb`` on
    ``genesis.instance_lock_path(runtime_root)``; the open handle is stashed in the module global
    so the flock survives until ``release_instance_lock`` / process exit. Raises
    ``DaemonAlreadyRunning`` (loud, names the path) when another instance holds it.

    IDEMPOTENT for the SAME path: an in-process re-boot of the same root is a no-op return —
    mandatory, because flock self-conflicts across fds, so a naive re-acquire would refuse against
    ITSELF. A hold on a DIFFERENT path (test tmp-root rebinding) is released first.
    """
    global _INSTANCE_LOCK
    path = _genesis_mod.instance_lock_path(runtime_root)
    if _INSTANCE_LOCK is not None:
        held_path, _handle = _INSTANCE_LOCK
        if held_path == path:
            return path  # same-path re-boot: the hold is already ours (idempotent no-op)
        release_instance_lock()  # a different root (test rebinding): drop the stale hold first
    try:
        handle = store.flock_exclusive_nb(path)
    except BlockingIOError as exc:
        raise DaemonAlreadyRunning(
            f"another harnessd instance already holds the lock at {path} — refusing to start "
            "(DAEMON §2.3)"
        ) from exc
    _INSTANCE_LOCK = (path, handle)
    return path


def release_instance_lock() -> None:
    """Release the lifetime instance-lock hold (LOCK_UN + close + clear the global).

    For tests and explicit shutdown paths; production never needs it — the flock dies with the
    process (§2.3). Safe to call when nothing is held (no-op).
    """
    global _INSTANCE_LOCK
    if _INSTANCE_LOCK is None:
        return
    _path, handle = _INSTANCE_LOCK
    _INSTANCE_LOCK = None
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    finally:
        handle.close()


# ---------------------------------------------------------------------------
# boot — the daemon entry: instance-lock, write runtime.json, then run genesis end-to-end (§2.12).
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
    """Daemon boot (§2.12): instance-lock -> runtime.json -> genesis end-to-end.

    (0) Acquire the §2.3 PERSISTENT single-instance lock (`.harnessd.instance.lock`) FIRST —
        non-blocking, held for the process lifetime. A second instance raises
        ``DaemonAlreadyRunning`` HERE, before the adapter wiring and the descriptor write, so the
        refused loser clobbers nothing.
    (a) Wire the concrete RuntimeAdapter into the ONE spawn chokepoint (the module-level seam) WHEN
        the runtime supplies one — production wires the real adapter; a test pre-installs its fake and
        passes no adapter (so boot does not clobber it). Then bind the REAL spawn env
        (``runtime.config.env`` -> ``chokepoint.set_spawn_env``, LT-1) so the commissioned 4-var
        OAuth env — not the structural placeholder — is what every production pane boots with.
    (b) Write ``runtime.json`` (the §2.3 daemon runtime descriptor: build-id / started_at / pid) so a
        crash between here and the first genesis write still leaves the descriptor on disk.
    (c) Run genesis END-TO-END (brief EX lock -> runtime.json -> preconditions ->
        reconcile_on_restart -> spawn-or-resume L1) through the REAL chokepoint + REAL reconcile +
        REAL on-disk ledger (Integration A) — so on first boot the L1 root is spawned in-role.

    genesis itself re-writes runtime.json inside its brief EX acquire (§7 step 3); writing it here
    too is deliberate (boot owns the descriptor independent of whether genesis reaches its own
    write) and is idempotent (the same atomic-replace target). Lock-acquire order is FIXED:
    instance lock first, always — the per-mutation `.harnessd.lock` is only ever taken while the
    instance lock is already held, so the two-lock ordering is deadlock-free by construction.
    """
    runtime_root = _runtime_root(runtime)

    # (0) THE single-instance gate (§2.3) — BEFORE anything is written or wired.
    acquire_instance_lock(runtime_root)

    build_id = getattr(runtime, "build_id", None)
    cfg = getattr(runtime, "config", None)
    if build_id is None and cfg is not None:
        build_id = getattr(cfg, "build_id", None)

    # (a) Wire the supplied adapter into the chokepoint (do NOT clobber a pre-installed test adapter).
    adapter = getattr(runtime, "adapter", None)
    if adapter is not None:
        chokepoint.set_adapter(adapter)

    # (a2) Bind the REAL spawn env into the chokepoint (LT-1, the set_adapter-mirroring seam):
    # commissioning assembled runtime.config.env (live OAuth token + pinned CLAUDE_CONFIG_DIR) for
    # the genesis credential precondition — without THIS binding it never reached a pane, and every
    # production spawn launched the structural placeholder env ('$HARNESS/...', '<oauth-token-file>').
    # Bound only when the runtime carries one (a sparse test descriptor leaves the fallback intact).
    spawn_env = getattr(cfg, "env", None) if cfg is not None else None
    if spawn_env:
        chokepoint.set_spawn_env(spawn_env)

    # (b) Write the §2.3 runtime descriptor (lock_path names the INSTANCE lock acquired in (0)).
    _genesis_mod.write_runtime_json(
        runtime_root, build_id=build_id,
        lock_path=str(_genesis_mod.instance_lock_path(runtime_root)),
    )

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

    The tick's LAST act stamps ``runtime.json.last_tick_at`` lock-free (§4.4) — the §2.6 hang-detector
    surface the external harnessd-pinger reads. End-of-body placement = completed-tick semantics: a
    wedge inside the tick body stops the stamp advancing IMMEDIATELY. Best-effort (the same isolation
    as the outbox drain), zero WAL rows; recovery never trusts it.

    THE RECONCILE REPORT IS CONSUMED (RR-4): the v1 escalation seat ("ship the detect+escalate
    loop in v1", DAEMON L859-866) was a dead end in the resident loop — an alive-but-unowned
    ORPHAN pane (the F35 double-spawn symptom) was detected and dropped every tick with zero
    trace, and a CAS-aborted leaf-necro's ``necro_failed`` escalation evaporated. Each escalation
    now lands ONE edge-triggered ``reconcile_escalation`` WAL row (keyed node+kind, the
    watchdog_checkpoint edge-trigger pattern: steady-state re-detection never spams).
    """
    report = _reconcile_mod.reconcile_tick(executor, tmux, detector)
    _route_reconcile_escalations(report)
    _watchdog_tick(executor, tmux, detector)
    _service_outboxes_best_effort()
    _stamp_last_tick_best_effort()
    return None


def _route_reconcile_escalations(report) -> None:
    """Journal each ReconcileReport escalation ONCE (edge-triggered on node+kind) — RR-4.

    Best-effort and isolated (the outbox-drain discipline): a journaling fault must never abort
    the sweep. The row is the v1 escalation seat's durable surface — an L1 reconcile reader (and
    the operator's WAL tail) sees orphan / necro_failed / coordinator_died with their evidence.
    """
    for escalation in (getattr(report, "escalations", None) or []):
        try:
            node = escalation.get("node_address")
            kind = escalation.get("kind") or "unknown"
            _journal_escalation_once(
                node,
                kind=kind,
                summary=(
                    f"reconcile escalation ({kind}) for {node}: "
                    f"{escalation.get('reason', 'no reason recorded')} (RR-4 — the v1 "
                    "detect+escalate seat, edge-triggered)"
                ),
                detail=dict(escalation),
            )
        except Exception:  # noqa: BLE001 — escalation routing must never abort the sweep
            continue


def _journal_escalation_once(node_address, *, kind: str, summary: str, detail: dict) -> None:
    """Append ONE ``reconcile_escalation`` row for (node, kind) — re-detection journals nothing.

    The dedup scans the WAL (the same pattern as watchdog._has_coordinator_died_event): a
    steady-state condition (an orphan pane nobody resolves; a persistently aborting necro) is
    re-detected every tick but journaled once. The journal rides ``executor.journal`` (SWL-01).
    NOTE: the row is keyed to the escalation's node identity — for an ORPHAN that identity is its
    tmux_target (no binding exists); journal rows are non-transition rows (expected_generation
    None), which boot replay deliberately never reconstructs a binding from.
    """
    for record in ledger.load_wal():
        if (
            record.get("event") == "reconcile_escalation"
            and record.get("node_address") == node_address
            and (record.get("binding_delta") or {}).get("kind") == kind
        ):
            return  # already journaled — the edge already fired
    try:
        from harnessd import executor as _executor_mod

        _executor_mod.journal(
            node_address,
            event="reconcile_escalation",
            binding_delta={"kind": kind, **{k: v for k, v in detail.items() if k != "node_address"}},
            summary=summary,
        )
    except Exception:  # noqa: BLE001 — best-effort visibility row
        pass


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
    idle->prod->FAILED ladder. ``check_leaf`` ENACTS its ledger-side action and returns a
    WatchdogAction; THIS sweep enacts the action's KEYSTROKE half — a PROD's
    ``detail['keystroke']`` is actually delivered via ``tmux.send_keys(binding tmux_target)``
    (the transport increment: an un-enacted PROD nudges nobody).
    COORDINATOR (persistent): ``watchdog.check_coordinator_death`` — the dead-pid+live-children ->
    ESCALATE probe (never blind-collapsed; the full evidence-lease recovery machine is DEFERRED, per
    WATCHDOG.md §1). A coordinator is NOT run through the leaf sign-off/ladder (the §5.4 split: do not
    auto-fail a coordinator for idle — it may be waiting on children).

    THE ③-WAKE (previously unwired — F16 noted the gap): EVERY live node (leaf AND coordinator —
    the answer verb wakes the PARENT's inbox) with a line appended past its acked watermark
    (``watchdog.inbox_has_unacked``) gets ONE pointer nudge (``watchdog.wake_keystroke`` — never
    the payload), gated by ``prod_precondition`` (never type into a mid-turn pane) and skipped
    for a PAUSED subtree (§3.4 STEP 0: no recovery actions). Only a DELIVERED nudge advances the
    edge-trigger watermark (``executor.ack_inbox``); a suppressed/failed send leaves it unmoved
    so the next tick retries — deferred, never lost.

    Liveness is injected into the watchdog via its ``set_liveness`` seam so ``check_leaf`` reads THIS
    sweep's detector verdict. Each node is isolated: one node's watchdog error never aborts the sweep
    (the supervision tree must keep advancing — the same best-effort discipline as the outbox drain).
    A failed keystroke SEND is never swallowed silently: it is journaled to the run-ledger
    (``prod_send_failed`` / ``wake_send_failed``) per the result-routing convention.
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
                    # ROUTE the verdict (RR-4): check_coordinator_death is PURE — its ESCALATE
                    # (the only carrier of target=parent_address + reason=recoverable_orphan)
                    # used to evaporate right here every tick. One edge-triggered row per
                    # (node, reason); WATCHDOG §5.5's v1 escalation seat is now actually wired.
                    cd_action = _watchdog_mod.check_coordinator_death(binding, binding, ledger)
                    if getattr(cd_action, "kind", None) == _watchdog_mod.ESCALATE:
                        detail = dict(getattr(cd_action, "detail", None) or {})
                        kind = detail.get("reason") or "coordinator_escalate"
                        detail["target"] = getattr(cd_action, "target", None)
                        _journal_escalation_once(
                            address, kind=kind,
                            summary=(
                                f"watchdog escalation ({kind}) for {address}: dead coordinator "
                                f"over live children -> escalate to "
                                f"{detail.get('target')!r} (WATCHDOG §5.1/§5.5; RR-4)"
                            ),
                            detail=detail,
                        )
                else:
                    action = _watchdog_mod.check_leaf(binding, binding, now=now)
                    # ENACT the keystroke half of a PROD (the ledger half — the stale-counter
                    # advance — check_leaf already routed through the executor). Fenced (LT-3):
                    # the live binding is re-read immediately before the send.
                    if getattr(action, "kind", None) == _watchdog_mod.PROD:
                        keystroke = (getattr(action, "detail", None) or {}).get("keystroke")
                        if keystroke:
                            live = _send_fence_open(address, binding)
                            if live is not None:
                                _deliver_keystroke(tmux, live, keystroke, kind="prod")
                # The ③-wake runs for EVERY live node (the answer verb wakes the PARENT inbox).
                _wake_on_unacked_inbox(executor, tmux, address, binding)
            except Exception as exc:  # noqa: BLE001 — one node's fault must not abort the whole sweep
                # RR-6: fault isolation per node is correct, but ZERO-journaling was the defect —
                # the deliberate fail-loud raises (e.g. MissingTranscriptPath) terminated in a
                # silent `continue`, permanently disabling STEP-A collapse, the idle ladder AND
                # the ③-wake for that node with no trace. Journal it (edge-triggered per node on
                # the error text, so a persistently-broken node is one row, not one per tick).
                _journal_sweep_error(binding, address, exc)
                continue
    finally:
        if detector is not None:
            _watchdog_mod.set_liveness(None)  # restore the default detector.liveness seam


# RR-6 edge-trigger memory: node_address -> the last journaled sweep-error text. A node whose
# watchdog evaluation throws the SAME error every tick is journaled ONCE per daemon incarnation
# (a changed error re-journals); in-memory on purpose — the row is a visibility aid, not control
# state, and a relaunch re-detecting the fault SHOULD re-journal it once.
_SWEEP_ERRORS_JOURNALED: dict = {}


def _journal_sweep_error(binding, address: str, exc: BaseException) -> None:
    """Best-effort, edge-triggered ``watchdog_sweep_error`` run-ledger row (RR-6)."""
    error = f"{type(exc).__name__}: {exc}"
    if _SWEEP_ERRORS_JOURNALED.get(address) == error:
        return  # steady-state re-detection of the same fault — already journaled
    try:
        from harnessd import executor as _executor_mod

        _executor_mod.journal(
            address,
            event="watchdog_sweep_error",
            from_state=binding.get("state"),
            to_state=binding.get("state"),
            lease_epoch=binding.get("lease_epoch"),
            binding_delta={"error": error},
            summary=(
                f"watchdog sweep error for {address}: {error} — node isolated this tick "
                "(STEP-A/ladder/③-wake skipped); fault journaled, sweep continues (RR-6)"
            ),
        )
        _SWEEP_ERRORS_JOURNALED[address] = error
    except Exception:  # noqa: BLE001 — the journal itself is best-effort
        pass


def _deliver_keystroke(tmux, binding, keystroke: str, *, kind: str) -> bool:
    """Deliver a watchdog keystroke into the binding's pane; journal a failed send (never silent).

    Best-effort transport: ``tmux.send_keys(tmux_target, keystroke)`` — the canonical F18 target.
    A transport without ``send_keys`` (the older test fakes) is a no-op miss. A send that RAISES
    or that RETURNS False (LT-2: the real ``tmux.send_keys`` now surfaces a non-zero rc — a
    dead/missing target between gate-capture and send) is journaled as a ``<kind>_send_failed``
    run-ledger row (the result-routing convention: a lost nudge must be visible, even though the
    ③-wake/next-tick retry is the actual healer). Returns True iff the send reported delivery;
    a legacy fake returning None is treated as delivered (it cannot know better).
    """
    target = binding.get("tmux_target")
    send = getattr(tmux, "send_keys", None)
    if not target or send is None:
        return False
    try:
        result = send(target, keystroke)
    except Exception as exc:  # noqa: BLE001 — journal, never crash the sweep
        _journal_send_failed(binding, target, kind, str(exc))
        return False
    if result is False:
        # The transport surfaced a delivery failure (non-zero tmux rc — LT-2). Journal it and
        # report undelivered so the caller leaves the wake watermark unmoved (next tick retries).
        _journal_send_failed(binding, target, kind, "send-keys exited non-zero (target gone?)")
        return False
    return True


def _journal_send_failed(binding, target, kind: str, error: str) -> None:
    """Best-effort ``<kind>_send_failed`` run-ledger row — a lost nudge is visible, never silent.

    Routed through ``executor.journal`` (SWL-01): the seq allocation + append run under the
    per-mutation EX lock, never racing the locked single writer on the other thread.
    """
    try:
        from harnessd import executor as _executor_mod

        _executor_mod.journal(
            binding.get("node_address"),
            event=f"{kind}_send_failed",
            from_state=binding.get("state"),
            to_state=binding.get("state"),
            lease_epoch=binding.get("lease_epoch"),
            binding_delta={"tmux_target": target, "error": error},
            summary=f"{kind} keystroke send to {target} failed: {error} (retried next tick)",
        )
    except Exception:  # noqa: BLE001 — the journal itself is best-effort
        pass


def _send_fence_open(address: str, snapshot: dict) -> Optional[dict]:
    """The SENDER-SIDE FENCE (TRANSPORTS §3.2 precondition 2, LT-3): re-read the LIVE binding
    immediately before a keystroke send; return it iff the send is still safe, else None (abort).

    The watchdog loop computes its actions off a pre-tick ``snapshot``; the SAME tick can collapse
    a signed-off leaf (STEP A) and then reach the ③-wake — without this re-read the daemon types
    'resume' into the pane of a node the ledger just recorded terminal, and acks the inbox on a
    terminal binding. Aborts when:
      * the binding is gone, or its lifecycle state is terminal (the collapsing/terminal set);
      * ``owner_token`` / ``lease_epoch`` drifted from the snapshot (a re-claim fenced it);
      * ``session_uuid`` drifted (a respawned incarnation — the nudge was computed for a pane
        that no longer exists).
    A None abort leaves the wake watermark unmoved — the next tick recomputes from durable truth.
    """
    live = ledger.read_binding(address)
    if live is None:
        return None
    if states.is_terminal(live.get("state")):
        return None
    if live.get("owner_token") != snapshot.get("owner_token"):
        return None
    if live.get("lease_epoch") != snapshot.get("lease_epoch"):
        return None
    if live.get("session_uuid") != snapshot.get("session_uuid"):
        return None
    return live


def _wake_on_unacked_inbox(executor, tmux, address: str, binding: dict) -> None:
    """The ③-wake delivery: unacked inbox line -> ONE gated+fenced pointer nudge -> ack the watermark.

    EDGE-TRIGGERED: ``inbox_has_unacked`` compares the inbox size to the binding's
    ``last_inbox_acked_offset``; only a DELIVERED nudge advances the watermark (executor.ack_inbox,
    the single writer), so a gate-closed pane or a failed send is retried next tick and an acked
    line is never re-nudged. PAUSED subtrees get no nudge (§3.4 STEP 0 — no recovery actions);
    the pointer (``wake_keystroke``) names the inbox re-read, NEVER the message payload.

    Two transport-correctness rules (the pre-live-run fixes):
      * SWL-03 — the inbox size is captured BEFORE the send and THAT size is acked: the inbox is
        a multi-writer append log (the IPC thread appends answer_posted/kickoff lines), so a line
        landing in the send->stat window must stay ABOVE the watermark and re-trigger next tick
        (at worst one duplicate nudge — tolerated by the edge-trigger design; a lost wake is not).
      * LT-3 — the sender-side fence (``_send_fence_open``, TRANSPORTS §3.2 P2) re-reads the live
        binding immediately before the send and aborts on terminal state / token / epoch /
        session_uuid drift — the same tick that collapses a signed-off leaf must NOT then nudge
        its pane 'resume' nor ack the inbox on the terminal binding.
    """
    from harnessd.spawn import chokepoint as _chokepoint

    try:
        if not _watchdog_mod.inbox_has_unacked(binding, binding):
            return
    except Exception:  # noqa: BLE001 — an unreadable inbox is "nothing to wake", not a crash
        return
    if _chokepoint.subtree_paused(address):
        return  # a paused subtree gets NO recovery nudge (WATCHDOG §3.4 STEP 0)
    if not _watchdog_mod.prod_precondition(binding):
        return  # pane mid-turn / unreadable -> defer; the un-acked watermark retries next tick
    # SWL-03: capture the ack watermark BEFORE the send (the size whose lines THIS nudge covers).
    try:
        inbox = _watchdog_mod._inbox_path(binding)
        size_before_send = inbox.stat().st_size
    except OSError:
        return  # no readable inbox -> nothing to ack/nudge
    # LT-3: the sender-side fence — re-read the live binding immediately before the send.
    live = _send_fence_open(address, binding)
    if live is None:
        return  # terminal/collapsing/re-claimed/respawned -> no nudge, watermark unmoved
    if not _deliver_keystroke(tmux, live, _watchdog_mod.wake_keystroke(live), kind="wake"):
        return  # failed/unsupported send -> watermark unmoved -> next tick retries
    # Delivered: advance the edge-trigger watermark to the PRE-send size (one nudge per line;
    # lines appended mid-send stay above the watermark and re-trigger next tick).
    executor.ack_inbox(address, acked_offset=size_before_send)


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


def stamp_last_tick(runtime_root=None) -> Optional[Path]:
    """Stamp ``runtime.json.last_tick_at`` — the §2.6 hang-detector surface, LOCK-FREE (§4.4).

    Called at the END of every ``poll_once`` (completed-tick semantics): the external
    harnessd-pinger (§2.6) reads ``last_tick_at`` and kills a wedged-but-alive daemon when the
    stamp is older than the staleness bound (~3 missed ticks) — the third death mode (hang) that
    launchd's exit-only KeepAlive cannot see (findings daemon-1 / COMP-5).

    READ-MERGE, not a wholesale rewrite: the §2.3 boot descriptor genesis wrote (build_id /
    started_at / pid / lock_path) is preserved; only ``last_tick_at`` is OVERWRITTEN (never
    setdefault — a write-once stamp would look permanently fresh-then-stale and defeat the §2.6
    staleness math). A missing/corrupt runtime.json is self-healed to a minimal descriptor — it
    is a liveness mirror, not control state. The lock-free read-modify-write is safe because the
    daemon's poll thread is the SOLE runtime.json writer post-boot (the instance lock excludes a
    second daemon; the IPC thread never writes it) — a future second writer would make this
    last-writer-wins, acceptable for a best-effort mirror.

    The same §4.4 carve-out as ``write_status``: written via the lock-free ``store.atomic_replace``
    (never torn), NEVER enters ``store.file_lock``, appends ZERO WAL rows (recovery never trusts
    it). Failures are swallowed by the best-effort wrapper: a daemon that persistently cannot
    write its runtime root looks wedged to the pinger and gets killed/relaunched — degraded IS
    the correct verdict there (relaunch = recovery, ThrottleInterval >= 10 keeps it benign).
    Returns the written path, or None when no runtime_root is resolvable (best-effort).
    """
    import json
    import os

    if runtime_root is None:
        runtime_root = ledger.RUNTIME_ROOT
    if runtime_root is None:
        return None
    runtime_root = Path(runtime_root)
    path = runtime_root / "runtime.json"

    try:
        descriptor = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(descriptor, dict):
            descriptor = {}  # coerce a non-dict liveness mirror back to a descriptor (self-heal)
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        descriptor = {}  # self-heal a missing/corrupt mirror — it is NOT control state
    descriptor.setdefault("pid", os.getpid())
    descriptor.setdefault("runtime_root", str(runtime_root))
    descriptor["last_tick_at"] = _clock.now_utc()  # OVERWRITE — the stamp must ADVANCE every tick

    def render(handle):
        json.dump(descriptor, handle, ensure_ascii=True, sort_keys=True, indent=2)
        handle.write("\n")

    # LOCK-FREE: atomic_replace is tmp+fsync+os.replace — it NEVER takes store.file_lock (§4.4).
    store.atomic_replace(path, render)
    return path


def _stamp_last_tick_best_effort() -> None:
    """Stamp last_tick_at; swallow any error so a sidecar hiccup never aborts the reconcile sweep."""
    try:
        stamp_last_tick(ledger.RUNTIME_ROOT)
    except Exception:  # noqa: BLE001 — §4.4 best-effort: the sweep must advance past a stamp failure
        pass


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

def _apply_global_seams(runtime) -> None:
    """Bind the process-global seams the substrate READS but ``boot`` does not set: ``ledger.RUNTIME_ROOT``
    (the genesis/executor/ledger anchor) + the dedicated tmux-server socket (so harness panes land on the
    daemon's OWN tmux server, isolated from the user's default — and the operator attaches there to watch:
    ``tmux -L <socket> attach -t harness-<collapsed-addr>``) + the detector's §2.11 tmux seam
    (``detector_signals._tmux`` — pane_alive RAISES un-bound; before this binding the seam was only
    ever bound inside tests, so a real tick could never read pane liveness). Must run BEFORE boot
    (genesis raises without RUNTIME_ROOT). Idempotent.
    """
    runtime_root = _runtime_root(runtime)
    ledger.RUNTIME_ROOT = runtime_root
    from harnessd import detector_signals as _detector_signals
    from harnessd.spawn import tmux as _tmux

    tmux_socket = getattr(runtime, "tmux_socket", None)
    if tmux_socket:
        _tmux.set_socket(tmux_socket)
    # The Increment-9 binding detector_signals' docstring promised: pane_alive reads the REAL
    # wrapper (on whatever socket is bound above). Without this, production liveness raises.
    _detector_signals._tmux = _tmux


def run(runtime, *, interval_s: float = 5.0) -> NoReturn:
    """Assemble + run the resident daemon: (0) bind the global seams (RUNTIME_ROOT + tmux socket);
    (1) ``boot(runtime)`` (runtime.json + genesis end-to-end); (2) bind the IPC listener + serve it
    forever in a DAEMON THREAD (the CLI->daemon control plane); (3) enter the unbounded ``poll_loop``
    (reconcile + watchdog + outbox on the timer). NoReturn — the always-on resident process (relaunch is
    recovery, §2.2).

    The IPC serve runs in a separate thread so a blocking ``accept()`` never stalls the reconcile/watchdog
    sweep, and the sweep never stalls request handling. Both route every MUTATION through the ONE
    executor under the ONE EX lock (the single-writer invariant holds across the two threads — fcntl
    serializes them).
    """
    import threading

    _apply_global_seams(runtime)
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
    # `python3 -m harnessd.daemon`: assemble the runtime descriptor (real adapter + OAuth env + L1
    # config, read from the pinned install) and run the daemon. run() binds the global seams, boots
    # genesis, serves IPC, and enters poll_loop.
    from harnessd import commissioning as _commissioning

    run(_commissioning.build_runtime())
