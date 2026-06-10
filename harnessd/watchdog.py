"""watchdog — the liveness lifecycle (Increment 11, cluster ②).

The §2.9 watchdog: terminal-signal-FIRST collapse, the leaf idle->prod->FAILED
ladder (the two-counter discipline), the ③-wake trigger, and the coordinator-death
probe. It is NOT a writer — every binding mutation funnels through the REAL
single-writer executor (a COLLAPSE routes through ``chokepoint.collapse``; a
watchdog-imposed FAILED routes through ``executor.transition``). The detector's
liveness verdict is the one injected seam (the within-W timing was validated for
real in Inc 6 + the Inc 9 tmux contract — see the module docstring fork note).

Authoritative sources:
  - IMPLEMENTATION-PLAN §2.9 (the FROZEN watchdog.py interface — transcribed into
    the signatures below) + the Increment-11 Done-test (L779-788) + §4.1 battery
    (L564-587).
  - design/WATCHDOG.md §4.1-§4.4 (the sign-off-or-fail path: the JOURNAL the check
    reads / the 3-step sequence / the prod gate (prompt-string match) / verify-new-
    turn / FAILED-via-executor + actor='harnessd' + reason watchdog_nonresponse),
    §3.5 (the two-counter discipline + stale-grace), §5.1/§5.5 (the coordinator
    process-death probe: dead-pid + live-children = recoverable orphan -> ESCALATE).
  - design/DAEMON.md §3.6 (the TERMINAL_VOCAB mapping) — states.TERMINAL_VOCAB.

REUSE (BIAS TO REAL, Lesson 7): the executor + on-disk ledger are REAL; the
.signal.json / .inbox.jsonl are REAL files read by the REAL
``detector_signals.read_terminal_signal`` / the REAL inbox tail; a COLLAPSE/FAILED
routes through the REAL executor (asserted via the REAL ledger). The ONLY injected
mock is the detector liveness verdict.

---------------------------------------------------------------------------------
RESOLVED DETAILS (unspecified by §2.9 / the frozen tests; decided spec-faithfully,
surfaced to the orchestrator — also recorded as forks in the build report):

  * WatchdogAction SHAPE (FORK-WDACTION) — §2.9 names ``WatchdogAction`` as a TAGGED
    action type but fixes no concrete shape (IMPLEMENTATION-PLAN L79 lists it among
    "result types … refinement"). v1 ships it as a frozen dataclass with a ``kind``
    tag (one of COLLAPSE / NOOP / PROD / FAILED / ESCALATE / WAKE / WAIT) plus the
    parent-directed ``target`` (the parent address an ESCALATE/FAILED is routed to)
    and a free-form ``detail`` dict. The frozen test reads the tag robustly
    (kind/tag/action/…); ``kind`` is the canonical field. A FAILED leaf's action
    carries BOTH kind='FAILED' AND target=<parent_address> so the parent-directed
    closing action is legible (the test asserts the parent address appears in the
    action repr/dict). FORK: a tagged-enum or a per-action subclass hierarchy would
    also satisfy §2.9; the single dataclass-with-kind reuses ONE result type, the
    precedent the codebase already follows for SpawnResult/ReconcileReport.

  * THE GOLDEN IDLE-PROMPT STRING (FORK-PROMPT) — §2.9 / WATCHDOG §4.3 pin the prod
    gate as "capture-pane shows the idle input prompt (golden string per CC version)"
    but leave the literal string KNOWN-OPEN (it is CC-version-specific and measured at
    commissioning). v1 carries the placeholder golden string ``FORK_PROMPT`` (the CC
    idle-prompt marker) and gates ``prod_precondition`` on a substring match against
    the captured pane. Because the real capture-pane wire is ③'s (not yet wired) and
    the tests drive ``prod_precondition`` through the module seam, the literal is a
    documented placeholder, swapped for the measured CC string at commissioning.

  * HOW LIVENESS IS INJECTED (FORK-LIVENESS-SEAM) — §2.9 has check_leaf read
    ``liveness(node)`` but fixes no injection style. Precedent in this codebase is a
    module-level injectable (``ledger.RUNTIME_ROOT``, ``chokepoint.set_adapter``). v1
    exposes BOTH a module-level ``set_liveness(fn)`` / ``LIVENESS`` seat AND, when no
    override is bound, calls the live ``detector.liveness`` attribute directly (the
    detector module is the production source). check_leaf accepts a node dict (or a
    bare address) and resolves the address before calling the verdict, so the frozen
    test's belt-and-suspenders monkeypatch of ``detector.liveness`` is honored too.

  * WAKE_KEYSTROKE PAYLOAD (FORK-WAKE) — §2.9 pins it as a POINTER ("re-read
    <node>/.inbox.jsonl, resume"), NEVER a fact. v1 returns exactly that pointer,
    naming the node's own .inbox.jsonl path so the agent's prompt loop does the
    per-turn re-read (TRANSPORTS §2.3). The message body is NEVER stuffed in.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from . import config, clock, detector, detector_signals, ledger
from .spawn import chokepoint


# ===========================================================================
# WatchdogAction — the §2.9 TAGGED result type (FORK-WDACTION; see module docstring).
# ===========================================================================

@dataclass(frozen=True)
class WatchdogAction:
    """A tagged watchdog action (§2.9). ``kind`` is the canonical tag.

    ``kind``   — one of COLLAPSE / NOOP / PROD / FAILED / ESCALATE / WAKE / WAIT.
    ``node``   — the node_address the action concerns.
    ``target`` — the parent address an ESCALATE/FAILED is routed to (None otherwise);
                 makes a FAILED/ESCALATE closing action legibly parent-directed.
    ``detail`` — a free-form dict carrying the action's evidence (terminal_signal,
                 liveness state, reason, …) for the journal / cluster-② handler.
    """

    kind: str
    node: Optional[str] = None
    target: Optional[str] = None
    detail: dict = field(default_factory=dict)


# Canonical tags (one place, so a typo at a construction site fails loud on the enum-ish set).
COLLAPSE = "COLLAPSE"
NOOP = "NOOP"
PROD = "PROD"
FAILED = "FAILED"
ESCALATE = "ESCALATE"
WAKE = "WAKE"
WAIT = "WAIT"


# ===========================================================================
# The liveness injection seam (FORK-LIVENESS-SEAM). A module-level override that,
# when unset, falls through to the live detector.liveness attribute.
# ===========================================================================

LIVENESS: Optional[Callable[[str], "detector.Liveness"]] = None


def set_liveness(fn: Optional[Callable[[str], "detector.Liveness"]]) -> None:
    """Inject the liveness verdict function (module-level seam; precedent: set_adapter)."""
    global LIVENESS
    LIVENESS = fn


def _liveness(node_address: str):
    """Resolve the liveness verdict for ``node_address`` through the seam, else detector.liveness."""
    if LIVENESS is not None:
        return LIVENESS(node_address)
    # No override: call the LIVE detector.liveness attribute (so a test that monkeypatches
    # detector.liveness is honored without this module holding a stale local copy).
    return detector.liveness(node_address)


# ===========================================================================
# The golden idle-prompt gate string (FORK-PROMPT) — MEASURED on the pinned CC v2.1.152
# (commissioning probe 2026-06-10; captured fixture tests/fixtures/cc-2.1.152-idle-pane.txt).
# The idle pane renders an input line beginning '❯' with a '? for shortcuts' status line
# below. Pinned per CC version (WATCHDOG §4.3 / §8): a CC bump re-measures this string.
# ===========================================================================

FORK_PROMPT: str = "❯"  # the CC v2.1.152 idle-input-prompt marker (measured, fixture-pinned)

# CC renders the '❯' input box even WHILE GENERATING (steering is allowed mid-run), so the
# prompt char alone cannot distinguish idle from busy. The working marker below is the busy
# signal CC shows during generation/tool-calls — its presence CLOSES the gate (§4.3
# Precondition 1: a send-keys nudge mid-turn corrupts the input line). Mirrors the proven
# interactive_eval._WORKING_MARKERS member.
_WORKING_MARKER: str = "esc to interrupt"

# CC's blocking DIALOGS (trust prompt, tool-approval prompt, bypass warning, selection menus)
# ALSO render '❯' as the selection cursor (probed live: the trust dialog shows '❯ 1. Yes, I
# trust this folder' / 'Enter to confirm · Esc to cancel'; the tool-approval dialog shows
# '❯ 1. Yes' / 'Esc to cancel · Tab to amend'). A nudge typed into a dialog would press Enter
# ON the selection — confirming whatever is highlighted. Deterministic trust + the jail's
# skip-permissions make dialogs structurally absent in production, but the gate refuses them
# anyway (belt-and-braces; both dialogs fixture-pinned).
_DIALOG_MARKERS: tuple[str, ...] = ("Enter to confirm", "Esc to cancel")


# ===========================================================================
# Small helpers — address extraction; the W(state) suspicion window; the
# capture-pane read (③'s wire, stubbed behind a module seam here).
# ===========================================================================

def _node_address(node_or_address) -> str:
    """The stable address from a node dict or a bare address string."""
    if isinstance(node_or_address, str):
        return node_or_address
    return node_or_address["node_address"]


def _w_window(binding: dict) -> int:
    """The W(state) suspicion window (seconds) for this node — keyed by suspicion_window_key (§3.3).

    Mirrors detector._w_window: read the dedicated ``suspicion_window_key`` the spawn step sets,
    floor to the tightest ``working`` window (earliest suspicion — safe) when absent/unknown.
    """
    key = binding.get("suspicion_window_key") or "working"
    return config.SUSPICION_WINDOWS.get(key, config.SUSPICION_WINDOWS["working"])


def _age_beyond_w(last_progress_at: Optional[str], window: int, *, now: Optional[str]) -> bool:
    """True iff last_progress_at is OVERDUE — strictly more than W seconds in the past (§3.3: age > W).

    A None/absent last_progress_at carries no proof of recent progress; treat it as overdue (the
    node has shown no forward progress to read as within-W). Routes through the canonical clock so
    the comparison is offset-invariant.
    """
    if not last_progress_at:
        return True
    return clock.age_seconds(last_progress_at, now=now) > window


def _capture_pane(node) -> str:
    """Capture the node's pane text (the prod-gate evidence) — the REAL ③ wire.

    Reads the live pane buffer via ``tmux.capture_pane(node["tmux_target"])`` — the canonical
    ``<session>:<window>.<pane>`` triple the F18 fix records on the binding. This stays the ONE
    module-level seam the tests monkeypatch (same name, same ``node -> str`` shape as the v1
    stub), so the existing prod-gate tests drive it unchanged.

    CONSERVATIVE on every failure mode: a node with no tmux_target, a gone pane, or a capture
    error reads as an EMPTY pane -> the gate stays CLOSED (never prod un-gated). The local
    import keeps the module import-light (the daemon binds the tmux socket seam at boot).
    """
    target = node.get("tmux_target") if isinstance(node, dict) else None
    if not target:
        return ""
    try:
        from .spawn import tmux as _tmux
        return _tmux.capture_pane(target) or ""
    except Exception:  # noqa: BLE001 — an unreadable pane is gate-closed evidence, not a crash
        return ""


# ===========================================================================
# STEP A + STEP B — check_leaf (the §2.9 leaf path).
# ===========================================================================

def check_leaf(node, binding, *, now) -> WatchdogAction:
    """The leaf liveness check (§2.9): terminal-signal FIRST, then the idle->prod->FAILED ladder.

    STEP A (TERMINAL-SIGNAL FIRST — the producer for INCLUDE-item #3):
        sig = detector_signals.read_terminal_signal(node, binding)
          * sig present & FENCED (owner_token matches):
              - DONE / FAILED  -> COLLAPSE (route to chokepoint.collapse through the REAL executor);
              - ESCALATED      -> journal signal_ESCALATED + stamp terminal_signal (exactly once,
                via chokepoint.escalate through the REAL executor), then NOOP — ESCALATED HOLDS ITS
                SLOT, never collapses (§2.3/§3.6 asymmetric). A failed journal write is routed
                (reason=escalate_journal_failed) and retried next tick.
          * sig present but STALE owner_token -> read_terminal_signal returns None (the fence): we
            fall through to STEP B (the live binding is UNCHANGED; the dead incarnation's leftover
            signal NEVER collapses the re-spawned node). The executor journals stale_return_ignored
            if a stale return is later presented; here the reader simply yields None.

    STEP 0 (WATCHDOG §3.4 — between STEP A and STEP B, the ratified placement): a PAUSED subtree
        (this node OR any ancestor carries paused_at) gets NO recovery action — no suspicion, no
        stale-counter advance, no prod, no watchdog-imposed FAILED -> NOOP (paused_subtree). The
        agent's own fenced terminal sign-off (STEP A, above) is still honored while paused:
        truth-recording is not a recovery action.

    STEP B (no actionable signal): read the liveness verdict.
        * idle + age>W + within grace -> PROD (gated by prod_precondition);
        * idle + age>W + AT/over grace -> FAILED (the ladder exhausted);
        * anything else (working/waiting/dead/within-W) -> NOOP.

    CLOSING ACTION on FAILED (v1 floor, INCLUDE-item #5): mark running->failed via the REAL
    executor (event='watchdog_nonresponse', reason carried so the row is distinguishable from an
    agent-self-emitted FAILED; actor='harnessd' is the executor's single-writer stamp) AND ESCALATE
    TO THE PARENT (the returned action carries kind='FAILED' + target=parent_address). v1 does NOT
    auto-respawn from harnessd (the lease-recovery state machine + auto_resume_command are DEFERRED;
    the auto_resume_command field is left UNREAD on the leaf leg).
    """
    node_address = _node_address(node)

    # ----- STEP A: terminal-signal FIRST (fenced reader; a stale token yields None) -----
    sig = detector_signals.read_terminal_signal(node, binding)
    if sig is not None:
        signal = sig.get("signal")
        if signal == "ESCALATED":
            # ESCALATED holds its slot — NEVER collapses (§3.6 asymmetric). But the slot-hold is
            # JOURNALED (SML-02): chokepoint.escalate stamps terminal_signal=ESCALATED + appends the
            # signal_ESCALATED running->running row through the single-writer executor, exactly once
            # (idempotent across ticks via the binding stamp). ROUTE THE RESULT: a fenced/CAS-aborted
            # journal write must NOT read as a clean slot-hold — the next tick retries against the
            # still-present .signal artifact (mirrors the collapse_failed routing below).
            result = chokepoint.escalate(node_address, expected_owner_token=binding.get("owner_token"))
            if result is not None and getattr(result, "ok", True) is False:
                return WatchdogAction(
                    kind=NOOP, node=node_address,
                    detail={"reason": "escalate_journal_failed", "terminal_signal": signal,
                            "errors": list(getattr(result, "errors", []) or [])},
                )
            return WatchdogAction(
                kind=NOOP, node=node_address,
                detail={"reason": "escalated_holds_slot", "terminal_signal": signal,
                        "journaled": result is not None},
            )
        if signal in ("DONE", "FAILED"):
            # Route the terminal collapse through the REAL chokepoint/executor (running -> done/failed).
            # ROUTE THE RESULT (review watchdog-2): a FAILED terminal transition (a CAS miss / fencing
            # rejection) must NOT be reported as a clean COLLAPSE — that would tell the daemon the node
            # is gone when it is not. On a failed collapse we return a NOOP (collapse_failed) so the next
            # tick retries against the still-present .signal.json; only a SUCCESSFUL collapse is a COLLAPSE.
            result = chokepoint.collapse(
                node_address,
                signal,
                expected_owner_token=binding.get("owner_token"),
            )
            if result is not None and getattr(result, "ok", True) is False:
                return WatchdogAction(
                    kind=NOOP, node=node_address,
                    detail={"reason": "collapse_failed", "terminal_signal": signal,
                            "errors": list(getattr(result, "errors", []) or [])},
                )
            return WatchdogAction(
                kind=COLLAPSE, node=node_address,
                detail={"terminal_signal": signal, "evidence": sig.get("evidence")},
            )
        # An unrecognized fenced signal kind is not actionable here -> fall through to liveness.

    # ----- STEP 0 (WATCHDOG §3.4): a PAUSED subtree (this node OR any ancestor) gets NO recovery
    # actions — no suspicion, no stale-counter advance, no prod, no watchdog-imposed FAILED.
    # Placed AFTER STEP A (the ratified §3.4 placement): the agent's own fenced terminal sign-off
    # is truth-recording, not a recovery action, and is still honored while paused. Reuses the
    # chokepoint's ONE node-or-ancestor predicate so the two read-points cannot drift. -----
    if chokepoint.subtree_paused(node_address):
        return WatchdogAction(
            kind=NOOP, node=node_address,
            detail={"reason": "paused_subtree"},
        )

    # ----- STEP B: the idle -> prod -> FAILED ladder (no actionable terminal signal) -----
    verdict = _liveness(node_address)
    state = getattr(verdict, "state", None)
    last_progress_at = getattr(verdict, "last_progress_at", None)

    # Only an IDLE verdict is actionable (working/waiting/dead are NOT prodded/failed here):
    #   - working / waiting -> the node is fine / holding its slot -> NOOP;
    #   - dead              -> the process is gone; the leaf-necro is ①'s mechanical reconcile reap
    #                          (WATCHDOG §4.4) — the watchdog does NOT prod a dead pane -> NOOP here.
    if state != "idle":
        # Reset-on-recovery (the two-counter discipline): a node that recovered to working/waiting
        # must drop its accrued stale_check_count so a later idle spell starts the ladder fresh — a
        # node that blips idle-then-recovers must NOT march toward FAILED on stale prods. The
        # executor.watchdog_checkpoint resets the counter to 0 on a healthy observation (edge-triggered:
        # a no-op when the counter is already 0).
        if state in ("working", "waiting") and (binding.get("stale_check_count") or 0) != 0:
            _checkpoint(node_address, binding, liveness_state=state, last_progress_at=last_progress_at)
        return WatchdogAction(
            kind=NOOP, node=node_address,
            detail={"reason": "not_idle", "liveness_state": state},
        )

    # Idle: only ACT once W has elapsed (the false-idle guard is already inside the liveness verdict;
    # this is the watchdog-side age>W gate the §2.9 ladder names explicitly).
    if not _age_beyond_w(last_progress_at, _w_window(binding), now=now):
        return WatchdogAction(
            kind=NOOP, node=node_address,
            detail={"reason": "idle_within_w", "liveness_state": state},
        )

    # The two-counter ladder (§3.5 / §4.3): bounded prods, THEN FAILED at grace.
    stale_check_count = binding.get("stale_check_count", 0) or 0
    stale_grace_checks = binding.get("stale_grace_checks", 2)
    if stale_grace_checks is None:
        stale_grace_checks = 2

    if stale_check_count >= stale_grace_checks:
        # The prod ladder is exhausted -> the terminal rung: mark FAILED + escalate to the parent.
        return _fail_and_escalate(node_address, binding)

    # Within grace: PROD (gated on the idle-prompt string). A gate-closed pane is NOT prodded (a
    # send-keys nudge mid-tool-call corrupts the input line — §4.3 Precondition 1). A gate-closed
    # node does NOT advance the counter (we only count UNANSWERED PRODS, not un-prodded idleness).
    if not prod_precondition(node):
        return WatchdogAction(
            kind=NOOP, node=node_address,
            detail={"reason": "prod_gate_closed", "liveness_state": state},
        )

    # PROD: PERSIST the ladder advance (stale_check_count += 1) via the single-writer
    # watchdog_checkpoint so the NEXT poll reads a higher count and the ladder converges to FAILED.
    # Without this the counter never grows and an unresponsive leaf is prodded forever (the §3.5 bug).
    _checkpoint(node_address, binding, liveness_state="idle", last_progress_at=last_progress_at)

    return WatchdogAction(
        kind=PROD, node=node_address,
        detail={
            "reason": "idle_within_grace",
            "stale_check_count": stale_check_count + 1,
            "stale_grace_checks": stale_grace_checks,
            "keystroke": wake_keystroke(node),
        },
    )


def _checkpoint(node_address, binding, *, liveness_state, last_progress_at):
    """Persist a watchdog observation (the two-counter advance/reset) via the single-writer executor.

    Routes through ``executor.watchdog_checkpoint`` (the ONE writer): an ``idle`` observation
    INCREMENTS ``stale_check_count`` (the ladder rung toward FAILED), a ``working``/``waiting``
    observation RESETS it to 0. Edge-triggered — a steady-healthy poll appends nothing. Fenced on
    the live ``owner_token`` (a stale actor's observation cannot move the counter).
    """
    from . import executor  # local import: avoid a module-load cycle
    executor.watchdog_checkpoint(
        node_address,
        condition=("idle" if liveness_state == "idle" else "healthy"),
        liveness_state=liveness_state,
        last_progress_at=last_progress_at,
        last_evidence=None,
        expected_owner_token=binding.get("owner_token"),
    )


def _fail_and_escalate(node_address: str, binding: dict) -> WatchdogAction:
    """The FAILED closing action (v1 floor): mark running->failed via the REAL executor + escalate.

    Marks the leaf failed THROUGH the single-writer executor with event='watchdog_nonresponse' (so
    the run-ledger row is distinguishable from an agent-self-emitted FAILED — actor='harnessd' is the
    executor's single-writer stamp, and the reason rides the event/summary/delta). Then ESCALATES TO
    THE PARENT (the returned action carries target=parent_address): the parent coordinator re-claims at
    the stable address (WATCHDOG §4 L444/L489). v1 does NOT auto-respawn from harnessd — no fresh
    spawn/claim/resume row is emitted for the leaf (the deferred lease-recovery machine owns that).
    """
    from . import executor  # local import: avoid a module-load cycle (executor imports nothing here)

    parent_address = binding.get("parent_address")

    # Mark running -> failed through the REAL executor. event='watchdog_nonresponse' + a reason in
    # the delta/summary so the row is NOT conflated with an agent-self-emitted FAILED. NOT a collapse
    # call (collapse journals the §3.6 signal_FAILED event); this is the watchdog-imposed,
    # non-response FAILED.
    executor.transition(
        node_address,
        expected_state=binding["state"],
        expected_generation=binding["generation"],
        expected_owner_token=binding.get("owner_token"),
        target_state="failed",
        binding_delta={
            "terminal_signal": "FAILED",
            "terminal_note": "watchdog_nonresponse",
        },
        event="watchdog_nonresponse",
        summary=(
            "watchdog-imposed FAILED: idle-but-pane-warm leaf exhausted the prod ladder with no "
            "sign-off (reason=watchdog_nonresponse); the parent re-claims at the stable address "
            "(v1 does NOT auto-respawn from harnessd — §4.4 / §2.9 INCLUDE-item #5)"
        ),
    )

    return WatchdogAction(
        kind=FAILED, node=node_address, target=parent_address,
        detail={
            "reason": "watchdog_nonresponse",
            "parent_address": parent_address,
            "escalate_to_parent": True,
            "auto_respawn": False,  # v1: the parent acts; harnessd does NOT respawn.
        },
    )


# ===========================================================================
# Prod helpers — the gate (prompt-string match) + verify-new-turn (no blind trust).
# ===========================================================================

def prod_precondition(node) -> bool:
    """The prod gate (§4.3 Precondition 1): True iff the captured pane shows the IDLE input prompt.

    A send-keys prod can land mid-tool-call and corrupt the input line; the prompt-string gate is
    what stops a nudge interleaving with an in-flight tool call. Two-part match against the REAL
    captured pane (the ③ wire behind ``_capture_pane``):

      * the golden idle-prompt marker (``FORK_PROMPT`` — the '❯' input line, MEASURED on the
        pinned CC v2.1.152, fixture-pinned) must be PRESENT, and
      * the working marker (``_WORKING_MARKER`` — 'esc to interrupt', what CC shows while
        generating) must be ABSENT — CC renders the '❯' box even mid-generation, so the prompt
        char alone would open the gate on a busy pane.

    An empty/unreadable pane reads gate-CLOSED (the conservative no-prod-un-gated posture), and
    so does a pane showing a blocking DIALOG (``_DIALOG_MARKER`` — a nudge's Enter would press
    the highlighted dialog option; probed live on the trust dialog, which also renders '❯').
    """
    pane = _capture_pane(node)
    if not pane:
        return False
    if _WORKING_MARKER in pane:
        return False  # mid-generation/tool-call — never type into an in-flight turn (§4.3 P1)
    if any(marker in pane for marker in _DIALOG_MARKERS):
        return False  # a blocking dialog — Enter would CONFIRM the highlighted option
    return FORK_PROMPT in pane


def confirm_prod_worked(node, jsonl_size_before) -> bool:
    """Verify-new-turn (§4.3 Precondition 3): True iff the JSONL grew since the prod (forward progress).

    send-keys is fire-and-forget (no ack); the watchdog confirms a prod "worked" ONLY by observing a
    NEW turn (a grown transcript), never by assuming the keystroke landed. Re-reads the transcript's
    current byte size and compares it to the pre-prod size. An absent/unreadable transcript reads as
    no-progress (False) — no blind trust.
    """
    import os

    path = node.get("transcript_path") if isinstance(node, dict) else None
    if not path:
        return False
    try:
        size_now = os.stat(path).st_size
    except FileNotFoundError:
        return False
    return size_now > jsonl_size_before


# ===========================================================================
# The ③-wake battery — EDGE-TRIGGERED trigger + the pointer payload.
# ===========================================================================

def inbox_has_unacked(node, binding) -> bool:
    """The ③-wake TRIGGER (§2.9): True iff a line was appended to <node>/.inbox.jsonl AFTER the watermark.

    EDGE-TRIGGERED (one nudge per NEW line, no per-poll storm): tail the node's .inbox.jsonl and
    compare its current byte size to ``binding.last_inbox_acked_offset``. A line appended past the
    acked offset is UNACKED -> the trigger fires (True). When the watermark is already at end-of-file
    (everything acked), a re-poll with nothing new returns False. The agent's prompt loop does the
    actual per-turn re-read; this only decides WHEN to nudge (TRANSPORTS §2: the inbox is a MULTI-
    writer append log harnessd TAILS — the opposite of the single-writer ledger).
    """
    import os

    inbox_path = _inbox_path(node)
    try:
        size_now = os.stat(inbox_path).st_size
    except FileNotFoundError:
        return False  # no inbox file -> nothing to ack -> no nudge
    acked = binding.get("last_inbox_acked_offset", 0) or 0
    return size_now > acked


def wake_keystroke(node) -> str:
    """The ③-wake send-keys PAYLOAD (§2.9): a POINTER, never a fact/payload.

    Returns a pointer that names the node's OWN .inbox.jsonl re-read + a resume nudge — the message
    BODY is NEVER stuffed in (the agent's prompt loop does the actual per-turn re-read on its next
    turn, TRANSPORTS §2.3). A mutant that carries the message content is caught by the frozen test
    asserting the pointer names the inbox re-read, not a payload.
    """
    node_address = _node_address(node)
    return (
        f"new message in your inbox — re-read {node_address}/.inbox.jsonl and resume"
    )


def _inbox_path(node):
    """Resolve the per-SEAT wake inbox ``<nested-node-dir>/.inbox.<seat>.jsonl`` (``addressing.inbox_path``)
    — the same nested node dir as ``.signal.<seat>.json``, seat-qualified so the L5/L5+ pair don't share
    a wake surface."""
    from . import addressing

    root = ledger.RUNTIME_ROOT
    if root is None:
        raise RuntimeError(
            "inbox path is not configured: bind ledger.RUNTIME_ROOT (the runtime tree root where "
            "nodes/<nested-path>/.inbox.<seat>.jsonl lives)"
        )
    return addressing.inbox_path(_node_address(node), root)


# ===========================================================================
# The coordinator-death probe (§5.1 / §5.5).
# ===========================================================================

def check_coordinator_death(node, binding, ledger) -> WatchdogAction:
    """The coordinator process-death probe (§2.9 / §5.1): dead-pid + live children -> ESCALATE.

    Reads the run-ledger for a ``coordinator_died`` EVENT (an event, NOT a standing binding field —
    §5.1) OR ``state == 'dead'``. Then:

      * dead-pid + LIVE children -> RECOVERABLE ORPHAN -> ESCALATE (recover-vs-reap is DEFERRED to
        cluster ②'s policy, §5.2/§5.5; v1 NEVER reaps a coordinator with a live subtree — a dead
        coordinator over live descendants is recovered from the ledger, never blind-killed).
      * quiet pane-alive (no coordinator_died event, state not dead) + live children -> WAITING (the
        coordinator merely went quiet with live descendants — NOT an orphan; the pane_pid probe is
        the disambiguator between quiet-vs-dead).

    NOTE: ``ledger`` is the module passed by the caller (the §2.9 signature threads it explicitly);
    we read it for the coordinator_died event + the live-children roll-up so the probe keys off the
    REAL run-ledger, not a phantom field.
    """
    node_address = _node_address(node)

    # Is the coordinator process dead? Two legible signals (§5.1): a coordinator_died EVENT in the
    # run-ledger, OR a lifecycle state already at 'dead'.
    state = binding.get("state")
    died = state == "dead" or _has_coordinator_died_event(ledger, node_address)

    # Are there LIVE children below it? (the disambiguator that makes a dead coordinator an orphan).
    live_children = _has_live_children(ledger, node_address)

    if died and live_children:
        # WATCHDOG §3.4 STEP 0 on the ESCALATE branch: a PAUSED subtree gets no recovery action —
        # the recoverable-orphan ESCALATE is DEFERRED until resume (the verdict is recomputed from
        # durable state every tick; the next tick after resume escalates normally, nothing lost).
        if chokepoint.subtree_paused(node_address):
            return WatchdogAction(
                kind=NOOP, node=node_address,
                detail={"reason": "paused_subtree", "coordinator_dead": died, "live_children": True},
            )
        # A RECOVERABLE ORPHAN: dead process, live subtree -> ESCALATE (recover-vs-reap deferred).
        return WatchdogAction(
            kind=ESCALATE, node=node_address, target=binding.get("parent_address"),
            detail={
                "reason": "recoverable_orphan",
                "coordinator_dead": True,
                "live_children": True,
                "recover_vs_reap": "deferred",
            },
        )

    if not died and live_children:
        # Quiet but pane-alive with live children -> WAITING (not dead, not actionable).
        return WatchdogAction(
            kind=WAIT, node=node_address,
            detail={"reason": "quiet_alive_with_children", "coordinator_dead": False},
        )

    # Dead with no live children -> ①'s mechanical reconcile reap covers it (nothing to recover); a
    # live coordinator with no children is just a (childless) waiting/working node. Benign NOOP here.
    return WatchdogAction(
        kind=NOOP, node=node_address,
        detail={"reason": "no_live_subtree", "coordinator_dead": died},
    )


def _has_coordinator_died_event(ledger_mod, node_address: str) -> bool:
    """True iff the run-ledger carries a ``coordinator_died`` event for ``node_address`` (§5.1)."""
    for record in ledger_mod.load_wal():
        if record.get("node_address") == node_address and record.get("event") == "coordinator_died":
            return True
    return False


def _has_live_children(ledger_mod, node_address: str) -> bool:
    """True iff some binding names ``node_address`` as parent AND is in a live (non-terminal) state.

    Reuses the reconcile coordinator/leaf discriminator shape: a child is a binding whose
    ``parent_address`` is this node (the §3.1 denormalized reconcile-speed pointer), or whose address
    is a strict descendant path (the prefix-arithmetic fallback). A child is LIVE iff its lifecycle
    state is non-terminal (running/claimed/spawning/blocked/planned) — a child already done/failed/
    dead is not a live descendant that makes the parent a recoverable orphan.
    """
    from . import states

    this_path = node_address.split("#", 1)[0]
    for child_address, child in ledger_mod.all_nodes().items():
        if child_address == node_address:
            continue
        is_child = (
            child.get("parent_address") == node_address
            or child_address.split("#", 1)[0].startswith(this_path + "/")
        )
        if not is_child:
            continue
        if not states.is_terminal(child.get("state", "")):
            return True
    return False
