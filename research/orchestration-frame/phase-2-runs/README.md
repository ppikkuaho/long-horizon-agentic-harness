# Phase 2 Runs — Self-Improvement Loop Program

This folder contains the operational program for iterating on the orchestration framework through live task stress-testing.

## Structure

```
phase-2-runs/
  research/        Cross-task learnings. What we know about orchestration.
  harness/         Reusable loop tooling. How to run a self-improvement loop.
  instances/       Specific task runs. Evidence for the research.
```

### research/

The cumulative knowledge base. A session doing framework-improvement work reads this first.

- `methodology-log.md` — main learning artifact (25+ durable lessons)
- `ARCHITECTURE-FINDINGS.md` — structured findings ledger
- Design proposals, analyses, and expansion plans

### harness/

Task-independent operational tooling. A session running a new task loop reads this.

- Control plane (state machine, supervisor, transition protocol template)
- Generated continuation packet (`CONTINUATION.md`) derived from manifest + ledger for mid-run resume
- Reviewer prompt templates (R1 adherence, R2 quality, R3 task-finish)
- Instantiation instructions

### instances/

Each subfolder is one task run. Instance data is evidence for research, not methodology knowledge.

- `mousepad-loop/` — first live instance (2026-04-12)
- `run-01*` — pre-harness Run 1 artifacts

## The framework being improved

Lives in the parent directory:
- `frame.md` — the orchestration frame (theory + operational levers)
- `frame-design-notes.md` — design notes (how the frame works)
- `prompt-craft.md` — delegation prompt patterns
- `process-observation-rubric.md` — process evaluation rubric

Research findings may propose changes to these; changes require MD approval.
