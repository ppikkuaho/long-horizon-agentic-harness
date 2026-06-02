# Self-Improvement Loop Contract

This file is normative. If any other harness file is ambiguous, this file wins.

## Purpose

Define a reviewer-governed iterative loop that an LLM can run without self-authorizing stop.

## Loop objective

Improve the declared target artifact set until an independent Reviewer 2 says the remaining improvements are smaller than medium.

## Roles and authority

### Orchestrator

- owns scheduling and state
- does not author judged content
- may not override reviewer verdicts except to escalate true external blockers

### Builder

- edits the target artifact set
- may not decide stop
- must produce one builder output artifact per round
- must follow `builder-template.md`

### Reviewer 1

- evaluates adherence to maintained documents and harness contract
- may emit `continue` or `pass`
- may not emit `stop`

### Reviewer 2

- evaluates residual improvement size against the stronger quality bar
- may emit `continue` or `stop`
- is the only stop authority inside the loop

## States

- `planned`
- `builder_in_progress`
- `reviewer_1_pending`
- `reviewer_1_continue`
- `reviewer_1_pass`
- `reviewer_2_pending`
- `reviewer_2_continue`
- `global_reconciliation_pending`
- `stopped`
- `blocked`
- `cancelled`

## State transitions

1. `planned` -> `builder_in_progress`
2. `builder_in_progress` -> `reviewer_1_pending`
3. `reviewer_1_pending` -> `reviewer_1_continue | reviewer_1_pass | blocked`
4. `reviewer_1_continue` -> next round `planned`
5. `reviewer_1_pass` -> `reviewer_2_pending`
6. `reviewer_2_pending` -> `reviewer_2_continue | global_reconciliation_pending | stopped | blocked`
7. `reviewer_2_continue` -> next round `planned`
8. `global_reconciliation_pending` -> `planned | builder_in_progress | stopped | blocked`

## Required outputs

### Builder output

Must include:

- target artifacts changed
- summary of changes
- rationale for each material change
- known open issues
- proposed next moves if reviewers continue the loop
- YAML frontmatter matching the builder schema in `builder-template.md`

### Reviewer 1 verdict

Must follow `reviewer-1-template.md` and begin with required YAML frontmatter.

### Reviewer 2 verdict

Must follow `reviewer-2-template.md` and begin with required YAML frontmatter.

## Non-negotiable structural rules

- A role can only see what it needs.
- Reviewers must be independent sessions.
- The builder must not be told it can stop based on its own judgment.
- The orchestrator must not treat commentary as a verdict.
- Round truth must be written into `manifest.yaml` and `run-ledger.jsonl`.
- A converged task instance, side branch, or evidence run does not stop the top-level loop unless the top-level manifest and ledger commit that transition under reviewer authority.
- A drafted future round does not become active until the manifest moves `current_iteration`, `current_iteration_path`, and the active round artifact pointers onto that round in the same committed transition.
- `manifest.yaml` must carry the current state, `state_entered_at`, `last_control_plane_update_at`, `next_action`, `user_contact_policy`, and `extraordinary_condition_open`.
- `manifest.yaml` must carry a `global_completion` gate. `stopped` is only valid when that gate is explicitly satisfied.
- `global_completion.open_stream_ids` must match the unresolved stream ids in `WORKBOARD.yaml`; top-level open work may not float free of the tracked branch registry.
- `manifest.yaml` must carry an `activity_lease` surface so active, stale, and deliberately parked sessions are distinguishable without prose inference.
- `manifest.yaml` must carry a `watchdog` block and an `observation_window` so external supervision is durable instead of conversational.
- `WORKBOARD.yaml` must materialize open top-level work into explicit streams with owner, objective, stop condition, evidence refs, write targets, and next action.
- If the harness is active, `WORKBOARD.yaml` must show at least one active or waiting stream; open work may not exist only as prose in `global_completion.open_workstreams`.
- Actor creation must be claim-first and transition-guarded; do not spawn first and repair state later.
- Execution summaries about parallelism, completion, or spawn status are claims until backed by trace or artifact evidence.
- Every role packet must name the exact files to read and the exact file to write.
- Resume must be possible from manifest, ledger, current round brief, and the most recent verdict files.
- Continuation handoff must use a control-plane-generated continuation packet such as `CONTINUATION.md`, not a reused fresh-launch brief.
- Any committed mutation that changes state, next action, round pointers, or other resume-relevant surfaces must refresh `CONTINUATION.md` in the same mutation path so handoff cannot lag behind manifest and ledger truth.
- Maintained-document references must be supplied through `reference-map.md`, not left implicit.
- Same-state checkpoints must not rewrite `state_entered_at`.
- The next action must be machine-readable and validator-checkable, not only described in prose.
- Mutating control-plane operations must fail closed: if the candidate state does not validate, it must not be committed.
- Stale active leases are recoverable runtime findings. They must be checkpointed by the external watchdog, not silently ignored.
- If a reusable live harness exists elsewhere in the project tree, it is evidence and a promotion source, not a silent override of the canonical harness in this folder.

## Change unit

A valid round is one reviewed change set against one declared target artifact set.

Each round brief must specify:

- objective
- task class
- quality benchmark appropriate to the task class
- path-lock risk
- preferred perturbation if the current path proves too narrow
- target artifacts
- relevant topology
- verification surfaces
- explicit success condition for the round
- evidence expected from reviewers
- carry-forward required changes, if any

## Abstraction boundary

The harness should codify reusable operators and control surfaces, not named domain interventions.

- valid harness content: reviewer structure, topology-discovery rules, decomposition rules, verification operators, stop policy, control-plane semantics
- task-local content: named sources, named libraries, named tools, named products, domain-specific heuristics

Task-local content belongs in round briefs or task artifacts unless it is part of the general runtime substrate.

## Structured field precedence

For `builder-output.md`, `reviewer-1-verdict.md`, and `reviewer-2-verdict.md`:

1. YAML frontmatter
2. explicitly labeled body sections
3. other prose

If these layers conflict, the higher-precedence layer wins.

## Ledger schema

Each `run-ledger.jsonl` record must contain at least:

- `ts`
- `iteration`
- `event`
- `actor`
- `state`
- `summary`

Optional fields:

- `from_state`
- `artifacts`
- `required_changes`
- `notes`
- `next_action_kind`

## Required manifest fields

`manifest.yaml` must contain at least:

- `name`
- `status`
- `state_entered_at`
- `last_control_plane_update_at`
- `objective`
- `current_iteration`
- `current_iteration_path`
- `next_action`
- `user_contact_policy`
- `reporting_policy`
- `extraordinary_condition_open`
- `global_completion`
- `activity_lease`
- `watchdog`
- `observation_window`
- `resume_packet`

The `next_action` block must contain at least:

- `owner`
- `kind`
- `trigger`
- `on_trigger`
- `user_dependency`

## Failure handling

If a reviewer identifies a blocker external to the artifact set or available tooling, the reviewer may mark the round `blocked` with evidence. The orchestrator may then escalate to the human principal.

Routine uncertainty, disagreement, or difficulty is not a blocker.
