"""detector.liveness — the thin liveness floor (Increment 6).

Authoritative sources:
  - IMPLEMENTATION-PLAN §2.8 (the FROZEN detector.py interface):
        liveness(node_address) -> Liveness(state, last_progress_at: str | None)
        state in working | waiting | idle | dead   (+ explicit 'unknown' fail-loud verdict)
  - IMPLEMENTATION-PLAN Increment-6 Done-test (L711-719): the five verdict cases + the
    false-idle hazard + transcript_path-absent fails loud.
  - IMPLEMENTATION-PLAN §4.1 "detector verdicts (fully mockable)" (L559-571).
  - WATCHDOG §2.4 / §3.3 + config.W / config.SUSPICION_WINDOWS (the W window; the
    working-vs-waiting-vs-idle boundary; the false-idle hazard).

THE v1 FLOOR (fuses ONLY jsonl_progress + pane_alive):
    pane_dead == 1 OR pane gone                                   -> dead   (wins; checked first)
    grew within W                                                 -> working
    flat but WITHIN the W window  (FALSE-IDLE HAZARD)             -> working
    flat BEYOND W + pane warm + LEGIT reason                      -> waiting
        (legit reason = terminal_signal == ESCALATED, OR a coordinator with a
         live-descendant roll-up — the roll-up is not wired in the v1 floor)
    flat BEYOND W + pane warm + NO reason                         -> idle   (the only actionable flat)

FAIL-LOUD: a binding with NO transcript_path makes the floor RAISE (MissingTranscriptPath
propagates from jsonl_progress) — NEVER a silent dead/idle. (The §2.8 contract also permits an
explicit 'unknown' verdict; we fail loud by raising, the louder of the two sanctioned outcomes.)

THE TMUX SEAM (§2.11): the detector reaches tmux ONLY through detector_signals.pane_alive (a
module-level function the tests monkeypatch). The detector calls it via the LIVE module
attribute (detector_signals.pane_alive), holding no rebindable local copy; the frozen test
patches detector_signals.pane_alive unconditionally (its `_patch_signals_everywhere`), so the
mock is always honored. See the Increment-6 builder report for how the seam (and the
coordinator-rollup fork) were wired.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import config, clock, ledger
from . import detector_signals

# THE SIGNAL SEAM: the detector calls the two floor readers THROUGH the detector_signals
# module object (detector_signals.jsonl_progress / .pane_alive) — NOT through a top-level
# `from ... import name` copy. Reading the live module attribute means a test that
# monkeypatches detector_signals.jsonl_progress is always honored, and the detector holds
# NO rebindable local copy that could leak a stale patch across tests. (The frozen test's
# _patch_signals_everywhere patches detector_signals.* unconditionally and only also patches
# detector.* when the name exists here — which it deliberately does not.)


# The legit-reason terminal signal that flips a flat-beyond-W warm pane to `waiting`
# instead of `idle` (an agent that ESCALATED holds its slot waiting for an answer; it
# is NOT idle — WATCHDOG §2.4 / DAEMON §3.6). v1 floor recognizes this single reason
# on the leaf leg; the coordinator live-descendant roll-up is the deferred second leg.
_ESCALATED = "ESCALATED"


@dataclass(frozen=True)
class Liveness:
    """The §2.8 liveness verdict.

    state in working | waiting | idle | dead, plus an explicit 'unknown' reserved for the
    sanctioned fail-loud return (this floor raises instead, but the field domain includes it).
    last_progress_at is surfaced from the binding so the watchdog's W(state) math has the
    instant it needs without a second ledger read.
    """

    state: str
    last_progress_at: str | None


def _w_window(binding) -> int:
    """The W(state) suspicion window (seconds) for this node — keyed by TASK TYPE (WATCHDOG §3.3).

    The window is keyed on the **task-type / suspicion-window vocabulary** (`working` /
    `waiting_on_child` / `writing_final`, `config.SUSPICION_WINDOWS`), which WATCHDOG §3.3 says
    "the spawning level sets at spawn time" — NOT the canonical 4-value `liveness_state` enum
    (working|waiting|idle|dead), whose only overlapping token is `working`. So this reads the
    dedicated `suspicion_window_key` binding field the spawn step populates.

    DEFERRED (named gap, FORK-W-KEYING): the spawn step that POPULATES `suspicion_window_key`
    lands in Increment 10 (the chokepoint). Until then the field is absent and this floors to the
    `working` window (120s) — the TIGHTEST, so it errs toward earlier suspicion (safe), never
    toward masking a stalled node. An unknown key also floors to `working` rather than raising.
    The longer windows become reachable the moment the chokepoint sets the field — no detector
    change needed. (Recorded in FORK-DECISIONS.md.)
    """
    key = binding.get("suspicion_window_key") or "working"
    return config.SUSPICION_WINDOWS.get(key, config.SUSPICION_WINDOWS["working"])


def _within_w(last_progress_at: str | None, window: int) -> bool:
    """True iff last_progress_at is RECENT — i.e. less than W seconds in the past (within W).

    Routes through the canonical clock (clock.age_seconds) so the freshness comparison is
    offset-invariant. A None/absent last_progress_at cannot be within W (no proof of recent
    progress) -> False, so the floor does not read a stamp-less binding as spuriously working.

    Boundary is spec-exact (WATCHDOG §3.3): overdue iff `age > W`, so within-W iff `age <= W`
    (at EXACTLY age == W the node is still working, not yet overdue).
    """
    if not last_progress_at:
        return False
    return clock.age_seconds(last_progress_at) <= window


def _has_legit_waiting_reason(node_address: str, binding) -> bool:
    """Does a flat-beyond-W warm node have a LEGIT reason to read `waiting` not `idle`? (§2.8).

    v1 floor reason: the live, fenced terminal_signal == ESCALATED (an agent parked waiting for
    an answer-round-trip — it holds its slot, never collapses). We read it through the FENCED
    reader so a stale prior-incarnation leftover never manufactures a phantom waiting-reason;
    we fall back to the binding's own terminal_signal field when the reader yields nothing (the
    field is the spawn<->detector contract carrier the seeded tests drive).

    DEFERRED (the second legit reason): a COORDINATOR with a live-descendant roll-up also reads
    waiting. The v1 floor has no live-descendant signal wired (that roll-up lands with reconcile/
    watchdog in later increments), so this leg is intentionally a no-op hook here — documented,
    not silently dropped. See the Increment-6 builder report (FORK note).
    """
    # Prefer the fenced on-disk signal (the producer side); a stale token yields None there.
    # Narrow the except to the EXPECTED unbound-RUNTIME_ROOT case only (RuntimeError): when the
    # runtime root isn't bound we fall back to the binding's terminal_signal field. A corrupt
    # .signal.json is CONTAINED inside the reader itself (RR-2: read_terminal_signal journals
    # ``signal_artifact_invalid`` + quarantines the artifact and returns None — agent-written
    # bytes must never crash the daemon's poll loop into a relaunch crash-loop); the binding's
    # own terminal_signal fallback below still carries an escalated node's waiting reason, so
    # the contained rejection does not silently degrade it to `idle`.
    node = {"node_address": node_address,
            "transcript_path": binding.get("transcript_path"),
            "tmux_target": binding.get("tmux_target")}
    try:
        sig = detector_signals.read_terminal_signal(node, binding)
    except RuntimeError:
        sig = None  # runtime root unbound -> fall back to the binding field below
    if sig is not None and sig.get("signal") == _ESCALATED:
        return True

    # Fall back to the binding's own terminal_signal field (the seeded contract carrier).
    return binding.get("terminal_signal") == _ESCALATED


def liveness(node_address: str) -> Liveness:
    """Fuse jsonl_progress + pane_alive into a working|waiting|idle|dead verdict (§2.8 floor).

    Resolution order (each step's precedence is load-bearing):
      1. Resolve the binding (ledger.read_binding). Absent binding -> raise (no such node).
      2. jsonl_progress(node) — this is ALSO the fail-loud gate: a missing transcript_path
         raises MissingTranscriptPath here, which propagates (NEVER a silent dead/idle).
      3. pane_alive(node): pane_dead / pane gone -> `dead` WINS over every JSONL signal.
      4. grew -> `working`.
      5. flat but WITHIN W -> `working` (the FALSE-IDLE HAZARD: W must ELAPSE before flat
         can read idle/waiting; a warm pane in a long quiet model turn is still working).
      6. flat BEYOND W + warm pane + LEGIT reason -> `waiting`.
      7. flat BEYOND W + warm pane + NO reason -> `idle` (the only actionable flat case).
    """
    binding = ledger.read_binding(node_address)
    if binding is None:
        raise KeyError(f"no binding for node_address {node_address!r}")

    last_progress_at = binding.get("last_progress_at")

    # The node shape the signal readers operate on (binding carries the same fields).
    node = {
        "node_address": node_address,
        "transcript_path": binding.get("transcript_path"),
        "tmux_target": binding.get("tmux_target"),
    }

    # (2) FAIL-LOUD gate: jsonl_progress raises MissingTranscriptPath on a no-transcript binding.
    #     Calling it FIRST means a contract violation cannot be masked by a (possibly mocked)
    #     pane reading — the violation surfaces before any verdict is formed.
    grew, _mtime_iso = detector_signals.jsonl_progress(node)

    # (3) DEAD wins: a dead/gone pane is dead regardless of the JSONL growth signal.
    alive, _pane_pid = detector_signals.pane_alive(node)
    if not alive:
        return Liveness(state="dead", last_progress_at=last_progress_at)

    # (4) Grew -> working.
    if grew:
        return Liveness(state="working", last_progress_at=last_progress_at)

    # (5) FALSE-IDLE HAZARD: flat but still WITHIN W reads working, not idle.
    if _within_w(last_progress_at, _w_window(binding)):
        return Liveness(state="working", last_progress_at=last_progress_at)

    # (6) Flat BEYOND W + warm pane + LEGIT reason -> waiting (NOT idle).
    if _has_legit_waiting_reason(node_address, binding):
        return Liveness(state="waiting", last_progress_at=last_progress_at)

    # (7) Flat BEYOND W + warm pane + NO reason -> idle (the only actionable flat case).
    return Liveness(state="idle", last_progress_at=last_progress_at)
