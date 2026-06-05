"""Pure per-node admission discipline — ``validate(candidate, wal_tail)``.

Authoritative source: DAEMON §4.2 (validate-before-commit) + IMPLEMENTATION-PLAN
§2.7 + the recovered ``validate()`` L618 discipline. This is the per-node
GENERALIZE of that recovered function: we keep ONLY its discipline — the flat
``(errors, warnings)`` contract, errors-block / warnings-allow, candidate +
wal-tail inputs — and DROP the 400-line reviewer-loop / workboard schema (no
cross-file workboard checks, no reviewer vocabulary).

Contract (frozen, IMPLEMENTATION-PLAN §2.7)::

    validate(candidate_binding: dict, wal_tail: list[dict]) -> (errors, warnings)

  * PURE. It WRITES NOTHING and MUTATES NOTHING (neither the candidate nor the
    wal_tail). It only inspects and returns the two flat lists of strings.
  * ``errors`` BLOCK commit (DAEMON §4.2 line 635: "if errors: abort —
    validate-before-commit: NOTHING written"). ``warnings`` ALLOW commit.

Call site (executor.transition, §2.6) hands ``wal_tail + [entry]``: the LAST WAL
record is the about-to-commit entry, carrying ``from_state`` / ``to_state`` /
``expected_generation`` / ``generation`` for THIS transition. The candidate is
the post-mutation node record (``state == entry.to_state``,
``generation == expected_generation + 1``).

The check-set (grounded in §4.2 + the recovered discipline):

  ERROR — an ILLEGAL lifecycle transition: ``states.is_legal(from_state,
          to_state)`` is False. The headline "illegal transition rejected before
          any write". EXCEPTION: a ``from_state == to_state`` no-op is NOT an
          illegal forward edge — it is the §3.6 ESCALATED slot-hold (the agent
          stamps a terminal_signal but legitimately keeps its slot; ``running``
          stays ``running``). A no-op is admitted (no error) but, when it carries
          a signal stamp, SURFACED as a WARNING rather than silently passed.

  ERROR — a MALFORMED candidate: a required §3.2 binding field is missing.

  ERROR — the per-node CAS post-condition (§4.2): ``candidate.generation`` MUST
          equal ``entry.expected_generation + 1``. A mismatch is a malformed
          candidate (a stale / wrong generation step) and blocks commit.

  WARNING — lesser issues that still ALLOW commit (the §3.6 ESCALATED no-op
          signal-stamp is the canonical per-node warning trigger).

FORK (disclosed, not silently chosen): §4.2 / §3.6 fix the legality-error and the
generation CAS post-condition as the load-bearing ERRORS, and route "lesser
issues" to warnings WITHOUT enumerating an exact lesser-issue set for per-node
v1. This module therefore pins exactly those two normative ERROR classes (plus
the missing-required-field structural error the tests mandate), admits a valid
candidate with empty errors, and routes the ESCALATED no-op signal-stamp to the
warnings channel. A benign unrecognized field is treated as fully benign (no
error, no warning) — it is not a transition violation. Other anomalies a future
builder wants to surface can be added to ``warnings`` without breaking this
contract.
"""

from __future__ import annotations

import harnessd.states as states

# The §3.2 binding fields that are LOAD-BEARING for the per-node CAS / lifecycle.
# A candidate missing any of these is structurally malformed for admission: the
# executor cannot CAS-fence (owner_token / generation), cannot address the node
# (node_address), and cannot resolve legality (state). This is intentionally the
# minimal CAS-bearing set, NOT the full §3.2 schema — per-node admission ports
# the DISCIPLINE, not the 400-line schema (IMPLEMENTATION-PLAN §2.7).
_REQUIRED_BINDING_FIELDS: tuple[str, ...] = (
    "node_address",
    "state",
    "generation",
    "owner_token",
)


def validate(
    candidate_binding: dict,
    wal_tail: list[dict],
) -> tuple[list[str], list[str]]:
    """Per-node admission check. PURE: returns ``(errors, warnings)``; writes nothing.

    ``errors`` block commit; ``warnings`` allow it (DAEMON §4.2). The last record
    of ``wal_tail`` is the about-to-commit entry for THIS transition.
    """
    errors: list[str] = []
    warnings: list[str] = []

    # ------------------------------------------------------------------
    # 1. Structural: required §3.2 binding fields must be present.
    #    (A missing field is a malformed candidate -> admission deny.)
    # ------------------------------------------------------------------
    for field in _REQUIRED_BINDING_FIELDS:
        if field not in candidate_binding:
            errors.append(
                f"malformed candidate: missing required binding field {field!r} (§3.2)"
            )

    # The about-to-commit entry is the LAST wal_tail record (executor hands
    # ``wal_tail + [entry]``). Without it there is no transition to validate.
    if not wal_tail:
        errors.append(
            "malformed wal_tail: no about-to-commit entry (executor passes wal_tail + [entry])"
        )
        return errors, warnings

    entry = wal_tail[-1]
    from_state = entry.get("from_state")
    to_state = entry.get("to_state")
    expected_generation = entry.get("expected_generation")

    # ------------------------------------------------------------------
    # 2. Legality gate (DAEMON §4.2 legality gate; the headline error).
    #    A from==to no-op is NOT an illegal forward edge: it is the §3.6
    #    ESCALATED slot-hold (signal stamped, lifecycle state unchanged).
    #    We admit the no-op but flag a signal-bearing no-op as a WARNING.
    # ------------------------------------------------------------------
    if from_state == to_state:
        # The ONLY legitimate self-loop is the §3.6 ESCALATED slot-hold: `running`
        # stays `running` while terminal_signal=ESCALATED is stamped (the agent keeps
        # its slot and waits for the answer round-trip). Admit exactly THAT and flag it
        # as a benign signal-stamp no-op (warnings-allow).
        if from_state == "running" and candidate_binding.get("terminal_signal") == "ESCALATED":
            warnings.append(
                f"ESCALATED slot-hold: no-op {from_state!r} -> {to_state!r} with "
                "terminal_signal=ESCALATED — admitted (§3.6: running stays running, lifecycle "
                "state unchanged), flagged as a benign signal-stamp no-op"
            )
        else:
            # Any OTHER self-loop is NOT a legal forward edge: a DONE/FAILED no-op (which must
            # change state to done/failed, not stay put), or an unmotivated self-loop, is a
            # malformed transition — is_legal returns False for self-loops, so this blocks commit.
            errors.append(
                f"illegal no-op transition {from_state!r} -> {to_state!r}: only the §3.6 "
                "ESCALATED slot-hold (running stays running with terminal_signal=ESCALATED) "
                f"admits a self-loop; got terminal_signal={candidate_binding.get('terminal_signal')!r}"
            )
    elif not states.is_legal(from_state, to_state):
        errors.append(
            f"illegal lifecycle transition {from_state!r} -> {to_state!r} "
            "(not in ALLOWED_TRANSITIONS; rejected before any write — DAEMON §4.2)"
        )

    # ------------------------------------------------------------------
    # 3. Per-node CAS post-condition (§4.2): candidate.generation MUST equal
    #    entry.expected_generation + 1. A mismatch is a malformed candidate.
    #    (Skipped if `generation` is absent — already reported above as missing.)
    # ------------------------------------------------------------------
    if "generation" in candidate_binding and expected_generation is not None:
        candidate_generation = candidate_binding["generation"]
        if candidate_generation != expected_generation + 1:
            errors.append(
                "malformed candidate: generation must equal expected_generation + 1 "
                f"(expected {expected_generation + 1}, got {candidate_generation!r}) "
                "— per-node CAS post-condition (§4.2)"
            )

    return errors, warnings
