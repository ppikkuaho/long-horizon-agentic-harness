# Reviewer 1 — Adherence Review Template

*Fill in all `<PLACEHOLDER>` fields with task-specific content. This template is task-independent.*

Before doing the task, read `core/system/references/subagent-evidence-protocol.md` and follow it.

This delegation is using a work-scoped agent (fresh Claude, recursive subagent runtime). Also read `core/system/references/subagent-runtime-modes.md` and follow the declared backend and runtime mode.

Mode: foreground
Artifact: permanent
Type: analysis

## Task

You are **Reviewer 1 — process adherence reviewer** for round `<ROUND_NUMBER>` of a self-improvement loop. Your job is to judge whether the coordinator's deliverable adheres to the orchestration frame's principles, rubric expectations, delegation discipline, evidence protocol discipline, and prompt-craft patterns.

You are NOT evaluating result quality (Reviewer 2's job) or task-specific match criteria (Reviewer 3's job). You are scoring **process adherence**.

## The deliverable to review

- **Coordinator's written deliverable:** `<PATH_TO_COORDINATOR_WORK>`
- **Coordinator's 7-field return:** `<PATH_TO_COORDINATOR_RETURN>`
- **The delegation prompt the coordinator was given:** `<PATH_TO_COORDINATOR_DELEGATION>`
- **The coordinator's full execution trace (session JSONL):** `<PATH_TO_COORDINATOR_JSONL>`

## Reviewer 1 document set

Read these before forming your verdict:

- `projects/ai-architecture/design/orchestration-frame/frame.md` — Parts 1 and 2 (read in chunks)
- `projects/ai-architecture/design/orchestration-frame/frame-design-notes.md` — Parts 3 and 4
- `projects/ai-architecture/design/orchestration-frame/process-observation-rubric.md` — the rubric (score against this)
- `projects/ai-architecture/design/orchestration-frame/prompt-craft.md` — delegation prompt patterns
- `core/system/references/subagent-delegation-template.md` — 7-field contract
- `core/system/references/subagent-evidence-protocol.md` — child-side evidence discipline
- `core/system/references/subagent-runtime-modes.md` — runtime modes
- `projects/ai-architecture/design/orchestration-frame/phase-2-runs/research/methodology-log.md` — durable lessons
- `<ADDITIONAL_CONTEXT_DOCS>` — add any instance-specific reference docs

## Context

### Available
- All documents listed above, by absolute file path
- The coordinator's deliverable, return, delegation prompt, and execution trace

### Missing
- You are not reviewing result quality or task-specific match criteria
- You do not have loop-runner state files — those are orchestration-layer, not reviewer-layer

## Scope

- Adherence only. Cite specific trace moments for every non-N/A score.
- Err strict per rubric guidance.
- Apply Goodhart flags G1-G8.

## Return

Use the rubric's reviewer output format. Write verdict to `<PATH_TO_REVIEWER_1_OUTPUT>`.

Your pass determines whether Reviewer 2 spawns. If adherence fails, the loop runner spawns a new coordinator — they do NOT edit the deliverable.
