"""Generic per-node lifecycle state machine — the static legality table + enums.

Authoritative source: DAEMON §3.3 (generic per-node lifecycle) + §2.3 (the
``ALLOWED_TRANSITIONS`` shape) + §3.6 (terminal-vocabulary mapping). Frozen
interface per IMPLEMENTATION-PLAN §2.3:

    KNOWN_STATES
    ALLOWED_TRANSITIONS: dict[str, set[str]]
    def is_terminal(state: str) -> bool
    def is_legal(from_state: str, to_state: str) -> bool

v1 keeps the *mechanism* recovered from the reviewer-loop control plane (a static
legality table + a CAS legality gate) but replaces the reviewer-loop *contents*
(``builder``/``reviewer_1_pending``/…) with the generic node lifecycle below.

The lifecycle (DAEMON §3.3)::

    planned ──claim──▶ claimed ──spawn-ok──▶ spawning ──actor-open──▶ running
    claimed ──release (admission-deny / E32-pin-fail)──▶ planned          (ROLLBACK; §6.1)
    spawning ──actor-open-fails──▶ planned                                (ROLLBACK; §6.1)
    spawning ──unrecoverable-spawn-error──▶ failed                        (give up the slot)
    running ──block──▶ blocked ──unblock──▶ running
    running ──DONE──▶ done
    running ──FAILED/DIED──▶ failed
    {any non-terminal} ──reconcile-finds-dead──▶ dead                     (reconcile-driven)
    running ──re-adopt(claim, expected_state=running)──▶ claimed          (RESUME live; §6.4)
    dead    ──re-adopt(claim, expected_state=dead)──▶ claimed             (necro;       §6.4/§5)
    done | failed | dead = terminal

The rollback edges (claimed→planned, spawning→planned, spawning→failed) and the
re-adopt edges (running→claimed, dead→claimed) are FIRST-CLASS members of the
table: without them the §4.2 legality gate would reject the very claim-release
the spawn chokepoint depends on (leaking an un-reclaimable ``claimed`` slot) and
abort every adopt/resume on its CAS precondition.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# The eight generic per-node lifecycle states (DAEMON §3.3 / §2.3).
# ---------------------------------------------------------------------------

KNOWN_STATES: frozenset[str] = frozenset(
    {
        "planned",
        "claimed",
        "spawning",
        "running",
        "blocked",
        "done",
        "failed",
        "dead",
    }
)

# Terminal states (DAEMON §3.3: "done | failed | dead = terminal"). Note: `dead`
# is terminal for the FORWARD machine yet keeps its sole re-adopt/necro departure
# (dead→claimed) — see ALLOWED_TRANSITIONS and the §3.6 reconciliation note.
TERMINAL_STATES: frozenset[str] = frozenset({"done", "failed", "dead"})

# Non-terminal states — every one of these can be driven to `dead` by the
# reconcile loop ("reconcile-finds-dead", DAEMON §3.3) without an actor signal.
NON_TERMINAL_STATES: frozenset[str] = KNOWN_STATES - TERMINAL_STATES


# ---------------------------------------------------------------------------
# liveness_state enum — CANONICAL 4-value (agent-lifecycle.md owns it; the ②
# detector writes it from ACTUAL tmux). working/waiting MUST stay distinct
# (the waiting-vs-idle split is load-bearing for the §5.4 coordinator roll-up).
# ---------------------------------------------------------------------------

LIVENESS_STATES: tuple[str, ...] = ("working", "waiting", "idle", "dead")


# ---------------------------------------------------------------------------
# The static legality table (DAEMON §2.3 + §3.3).
#
# Built so every edge the spawn chokepoint / reconcile loop can traverse is
# enumerated. The reconcile-driven {non-terminal} -> dead edges are folded in
# programmatically so the table is the single source of truth and cannot drift
# from NON_TERMINAL_STATES.
# ---------------------------------------------------------------------------

# Explicit forward / rollback / re-adopt edges, transcribed from DAEMON §2.3.
_EXPLICIT_TRANSITIONS: dict[str, set[str]] = {
    "planned": {"claimed"},                               # claim
    "claimed": {"spawning", "planned"},                   # spawn-ok; planned = release-rollback (§6.1)
    "spawning": {"running", "planned", "failed"},         # actor-open; planned = rollback; failed = give-up
    "running": {"blocked", "done", "failed", "claimed"},  # block; DONE; FAILED/DIED; claimed = re-adopt/resume (§6.4)
    "blocked": {"running"},                               # unblock
    "done": set(),                                        # terminal dead-end
    "failed": set(),                                      # terminal dead-end
    "dead": {"claimed"},                                  # re-adopt/necro (§6.4/§5) — sole departure
}


def _build_allowed_transitions() -> dict[str, frozenset[str]]:
    """Assemble ALLOWED_TRANSITIONS = explicit edges + reconcile-driven →dead.

    The {any non-terminal} → dead edges are reconcile-driven (DAEMON §3.3); fold
    them in here so they can never drift out of sync with NON_TERMINAL_STATES.

    Values are FROZEN (frozenset): this is the single authoritative legality table
    the §4.2 CAS gate, reconcile, and the chokepoint all read on every transition.
    A stray ``ALLOWED_TRANSITIONS['running'].add(...)`` at any of those call sites
    would silently corrupt the legality table process-wide — frozen values make
    that a TypeError instead. ``is_legal`` does membership-only reads, unaffected.
    """
    table: dict[str, set[str]] = {state: set(targets) for state, targets in _EXPLICIT_TRANSITIONS.items()}
    for state in NON_TERMINAL_STATES:
        table[state].add("dead")  # reconcile-finds-dead
    # Defensive: every known state is a key (terminals included).
    for state in KNOWN_STATES:
        table.setdefault(state, set())
    return {state: frozenset(targets) for state, targets in table.items()}


ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = _build_allowed_transitions()


# ---------------------------------------------------------------------------
# Predicates (IMPLEMENTATION-PLAN §2.3 frozen interface).
# ---------------------------------------------------------------------------

def is_terminal(state: str) -> bool:
    """True iff `state` is a terminal lifecycle state (done | failed | dead).

    Terminal here means "in the terminal SET" (DAEMON §3.6). `dead` is terminal
    by this predicate even though it keeps the single re-adopt/necro departure.
    """
    return state in TERMINAL_STATES


def is_legal(from_state: str, to_state: str) -> bool:
    """True iff `from_state` → `to_state` is a legal transition.

    The static ALLOWED_TRANSITIONS table is authoritative: an edge is legal iff
    `to_state` is listed among `from_state`'s allowed targets. Unknown source
    states (and therefore terminal self-loops, which are never listed) are
    rejected. This is the predicate the §4.2 CAS legality gate consults before
    any binding write.
    """
    return to_state in ALLOWED_TRANSITIONS.get(from_state, frozenset())
