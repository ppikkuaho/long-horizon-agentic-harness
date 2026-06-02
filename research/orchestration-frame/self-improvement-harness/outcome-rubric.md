# Outcome Rubric — Self-Improvement Harness

Use this when judging whether the harness itself has improved as a harness, not merely as a body of prose.

## Scoring scale

- `Pass`
- `Partial`
- `Fail`

## Criteria

### O1. Loop control is explicit

Question:

Can a fresh orchestrator tell who is allowed to continue, pass, or stop without reconstructing intent from narrative docs?

### O2. Stop condition is machine-usable

Question:

Are stop and continue decisions normalized into structured fields and severity thresholds?

### O3. Artifact flow is explicit

Question:

Does each round have a minimal artifact set with clear roles and handoffs?

### O4. Source of truth is explicit

Question:

Can a future session distinguish control-plane truth from commentary?

### O5. Independence is structural

Question:

Does the harness require independent reviewer sessions rather than relying on goodwill?

### O6. Change unit is bounded

Question:

Does each round define target artifacts and intended effect, rather than vaguely "improving methodology"?

### O7. Resume semantics exist

Question:

Can the loop be resumed from manifest + ledger + round artifacts without rereading the whole project?

### O8. Runtime operability is real

Question:

Can the harness be run with the available local runtime and supervision surfaces?

### O9. Reviewer output drives action

Question:

Do reviewer verdicts produce deterministic next actions?

### O10. Remaining gaps are visible

Question:

Does the harness make unresolved structural gaps explicit rather than burying them in long narrative?

### O11. Abstraction boundary is clean

Question:

Does the harness encode reusable operators and task-class adapters rather than hardcoded domain-specific interventions?

### O12. Anti-rigidity is structural

Question:

Does the harness make basin lock-in visible and provide frame-breaking operators structurally, rather than relying on exhortations to "be flexible"?

### O13. Global continuation is explicit

Question:

When a child branch or task instance converges, does the harness still make the top-level next action explicit instead of silently treating local completion as global stop?

## Use rule

Reviewer 1 and Reviewer 2 should score each criterion as `Pass`, `Partial`, or `Fail` in their working notes even if they do not reproduce the full table in the final verdict.

Any criterion that is effectively `Fail` for loop operability should influence severity upward rather than being left as an unweighted note.
