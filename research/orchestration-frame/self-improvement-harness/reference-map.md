# Reference Map

This file maps the maintained orchestration-frame documents that the harness sits on top of.

Use it to avoid vague instructions like "read the project docs."

## Core maintained docs

- `../frame.md`
  - Primary design document for the orchestration frame.
- `../frame-design-notes.md`
  - Design rationale, tradeoffs, and unresolved design logic around the frame.
- `../experiment-protocol.md`
  - How the frame should be evaluated and run experimentally.
- `../process-observation-rubric.md`
  - Baseline process-evaluation rubric for judging investigation quality.
- `../prompt-craft.md`
  - Prompting guidance and operator-facing prompt considerations.

## Harness-local maintained docs

- `anti-rigidity.md`
  - Basin-lock failure modes, detection signals, and preferred frame-breaking operators for self-improvement loops.
- `CONTROL-PLANE.md`
  - Operational contract for manifest, ledger, lease, watchdog, and next-action handling.
- `WATCHDOG.md`
  - External watchdog semantics, recovery contract, and verification surface.
- `RUNBOOK.md`
  - Default startup, verification, and shutdown sequence for the harness.
- `WORKBOARD.yaml`
  - Explicit branch registry for the top-level program: active streams, owners, evidence surfaces, and next actions.
- `CONTINUATION.md`
  - Current continuation packet for a fresh session taking over an already-running harness.
- `continuation-template.md`
  - Template for continuation packets; distinct from fresh-launch setup artifacts.

## Phase 2 empirical docs

- `../phase-2-runs/research/rubric-v2-proposal.md`
  - Proposed stronger rubric direction from the phase-2 work.
- `../phase-2-runs/research/synthesis.md`
  - Synthesized findings from the phase-2 investigation line.
- `../phase-2-runs/research/methodology-log.md`
  - Durable methodology findings and failure modes observed during runs.

## Live reusable harness comparison surfaces

- `../phase-2-runs/harness/README.md`
  - Reusable live harness architecture and role model. Use when checking whether canonical docs have absorbed proven operational lessons.
- `../phase-2-runs/harness/CONTROL-PLANE.md`
  - Operational semantics from the reusable harness. Use as comparison evidence during canonical reconciliation, not as a higher-precedence authority.

## Recommended minimum read by role

### Builder

- `../frame.md`
- `anti-rigidity.md`
- `../experiment-protocol.md`
- `../phase-2-runs/research/synthesis.md`
- any other maintained docs directly implicated by the current round brief

### Reviewer 1

- `../frame.md`
- `../frame-design-notes.md`
- `anti-rigidity.md`
- `../experiment-protocol.md`
- `../process-observation-rubric.md`
- any phase-2 empirical docs implicated by the current round brief

### Reviewer 2

- `anti-rigidity.md`
- `../phase-2-runs/research/synthesis.md`
- `../phase-2-runs/research/methodology-log.md`
- any maintained docs needed to assess whether remaining improvements are still medium or larger
