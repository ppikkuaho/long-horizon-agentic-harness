# Reviewer 3 — Task Finish Condition Template

*Fill in all `<PLACEHOLDER>` fields. This template is task-independent.*

Before doing the task, read `core/system/references/subagent-evidence-protocol.md` and follow it.

This delegation is using a work-scoped agent (fresh Claude, recursive subagent runtime). Also read `core/system/references/subagent-runtime-modes.md`.

Mode: foreground
Artifact: permanent
Type: analysis

## Task

You are an **independent task-finish reviewer**. Judge whether the top candidate in the deliverable meets the task's explicit finish condition, and produce a quantitative score.

## The finish condition

`<TASK_FINISH_CONDITION>` — state the exact condition (e.g., ">=90% experiential similarity to reference X")

## The scoring reference

`<SCORING_REFERENCE>` — the verbatim definition/spec the top candidate is judged against. Include inline or point to the exact file section.

## The top candidate's evidence

Read the top-ranked candidate's evidence block from: `<PATH_TO_COORDINATOR_WORK>`

## Context

### Available
- The scoring reference above
- The top candidate's evidence in the deliverable
- Web access for spot-checking cited sources

### Missing — deliberate
- **No frame documents, no loop context, no other reviewers' verdicts.** Your judgment is independent.
- **No other candidates.** You score the top candidate against the reference, not candidates against each other.
- **Do not use the coordinator's self-assessed score as your starting anchor.** Compute your own.

## Return

7-field return. Write verdict to `<PATH_TO_REVIEWER_3_OUTPUT>`.

Your score is the task-level finish condition. If it meets the threshold, the task condition is met. If not, the top candidate is a dead candidate and the loop continues with different conditions. Report the number you believe from the evidence.
