# Anti-Rigidity — Preventing Iteration Basin Lock-In

This note defines how the self-improvement harness should resist path lock-in.

The problem is not only that a builder may choose a bad idea. The deeper problem is that once a viable path appears, the loop can become very good at improving inside that path while failing to reopen path selection itself.

That is basin lock-in:

- the current path becomes the local search basin
- later work optimizes within the basin instead of challenging it
- the loop can still look disciplined, reviewer-driven, and productive while remaining trapped

## Multi-level failure modes

The same mechanism appears at different levels.

### 1. Local reasoning lock-in

The builder keeps refining the first plausible frame instead of evaluating competing frames.

Examples:

- first decomposition becomes the decomposition
- first likely root cause becomes the lens for all later evidence
- first promising artifact shape becomes the only artifact shape considered

### 2. Decomposition lock-in

The builder repeatedly uses the same work split, validation style, or coordination topology without re-judging whether it is still the right one.

Examples:

- always patching the same files
- always using the same reviewer/evaluator pattern
- always choosing local fixes over topology changes

### 3. Program lock-in

Later rounds inherit the prior round's ontology, residual list, and language so strongly that they become repair passes inside the old basin instead of genuine reroutes.

Examples:

- every round speaks in the same defect vocabulary
- reviewer feedback is translated into local patches only
- reroutes are nominally different but still explore the same search basin

## Design principle

Prompting "be flexible" is not enough.

Anti-rigidity must be structural:

- visible in round briefs
- expected in builder outputs
- checked by reviewers
- preserved in the artifact trail

The harness should not rely on the builder spontaneously escaping its own frame.

## Detection signals

The harness should treat these as basin-lock signals, not just ordinary imperfections.

### Builder-side signals

- no alternate framing is surfaced before commitment on a medium-or-harder task
- the same rationale or decomposition language repeats across rounds
- a partial solution exists and all subsequent work is local optimization around it
- the builder keeps editing the same artifact cluster without reopening topology
- the builder says the remaining work is "just cleanup" while reviewers still see structural uncertainty

### Reviewer-side signals

- the artifact set is improving, but the search surface is not widening
- suggested changes are all local patches to the current path
- the strongest remaining improvement would reopen path selection, not deepen the current path
- a round passes quality checks yet still fails the finish condition because the wrong basin was refined

### Program-side signals

- reroutes reuse the previous round's assumptions almost verbatim
- independent reviewers keep finding "missed but nearby" alternatives
- validation is deep inside one frame but shallow across adjacent frames

## Structural anti-rigidity operators

These are the preferred frame-breaking operators for the harness.

### 1. Divergence before convergence

On medium-or-harder tasks, separate path generation from path selection.

Minimum standard:

- surface at least 2-3 materially different framings, decompositions, or attack paths
- then choose one and explain why

The first viable idea is not enough evidence that the right basin has been chosen.

### 2. Assumption surfacing

Before committing, list the assumptions embedded in the current framing.

Typical questions:

- what am I assuming the task really is?
- what constraints am I treating as fixed?
- what evidence type am I privileging?
- what artifact shape am I assuming is best?

Assumption surfacing is especially important after a partial solution appears.

### 3. Pre-mortem on the chosen path

Before deepening the current path, force a failure narrative:

- if this round fails, why did it fail?
- what nearby alternative did we probably under-explore?
- what would make this look like local optimization inside the wrong basin?

### 4. Orthogonal perturbation

When lock-in signals appear, do not only add more effort inside the current path.

Use an orthogonal perturbation such as:

- inversion
- constraint shift
- perspective shift
- alternate decomposition
- fresh independent reviewer
- parallel branch with a different model or worker
- different verification surface

The perturbation should come from outside the current frame.

### 5. Path-reopening review

Reviewers should check not only "is this high quality?" but also:

- are we in the right basin at all?
- would a strong improvement require reopening the path rather than polishing inside it?

If yes, that remaining work is often at least `medium`, even when the local patch itself looks small.

### 6. Reroute with real orthogonality

A reroute is not just a fresh round. It must materially change the search basin.

Good reroutes change one or more of:

- topology
- decomposition
- verification surface
- role structure
- model/backend
- artifact boundary
- assumptions carried forward

## Where this belongs in the harness

### Round brief

Every non-trivial round should name:

- the main basin-lock risk
- what would count as evidence that the current path is too narrow
- which perturbation operators are preferred if that happens

### Builder output

The builder should make visible:

- alternatives considered
- why the chosen path won
- which anti-rigidity moves were used, if any

This prevents invisible path commitment.

### Reviewer 1

Reviewer 1 should treat unexamined path lock-in as an adherence defect when the task is not trivial.

### Reviewer 2

Reviewer 2 should ask whether the strongest remaining improvement would reopen path selection itself. If yes, the residual is often not "minor," even if the local fix is short.

### Future control-plane candidates

These are future structural candidates, not current requirements:

- manifest field for current basin-lock risk
- ledger events for perturbation operators used
- next-action kinds for path-reopen steps
- stale-novelty triggers when several checkpoints show no new framing

## Non-goal

Do not turn the harness into constant meta-monitoring.

The system should not obsessively ask whether it is stuck. That itself becomes a new rigidity.

The correct pattern is:

- detect a real signal
- apply a practiced perturbation
- continue work

## Operational rule

For medium-or-harder rounds:

1. do not trust the first workable path by default
2. make alternatives visible before commitment
3. when lock-in signals appear, introduce an external perturbation
4. require reviewers to judge path quality, not only local artifact quality

This is a harness feature, not a coaching note.
