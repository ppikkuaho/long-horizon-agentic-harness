# Self-Improvement Loop Harness

Reusable operational tooling for running iterative self-improvement loops. Task-independent — instantiate on any task by creating a new folder under `instances/` and configuring a task-specific manifest.

## What's here

- `control_plane.py` — generic state machine: manifest validation, compare-and-set transitions, next-action packet emission, probe-active observation checkpointing, and `contact-check` reporting-gate derivation. Task-specific states and transitions are loaded from `task_model.yaml` at startup. Copy into each instance folder alongside the instance's task model and manifest.
- `CONTINUATION.md` — generated per-instance by `control_plane.py refresh-continuation` and by every mutating control-plane command. This is the resume packet for existing instances; it is derived from manifest + ledger, not maintained manually.
- `loop_supervisor.py` — generic external watcher: periodic observation of the active actor, durable checkpointing into the control plane, detection and reconciliation of terminal states. Role-to-state mappings are loaded from `task_model.yaml`. Same CWD requirement as control_plane.py.
- `task-model-template.yaml` — defines the state machine for an instance: states, transitions, roles, and repair-junction semantics. Copy as `task_model.yaml` into each instance and customize for the task's reviewer chain and lifecycle.
- `CONTROL-PLANE.md` — usage documentation for the control plane tools.
- `transition-protocol-template.md` — state-machine edge rules template. Copy into each instance and customize the reviewer-chain rules, reroute menus, and sleep/throttle policies for the specific task.
- `OBSERVATION-FILE-TEMPLATE.md` — reusable run-observation scaffold. Use it to preserve overview, narrative, pre-run intent, and live-dashboard observations as maintained artifacts during long runs.
- `reviewer-prompt-templates/` — generalized R1 (adherence), R2 (quality elevation), R3 (match/task-finish) reviewer skeletons. Fill in task-specific details per instance.
- `test-fixtures/` — validation fixtures proving the harness works with non-default task models (e.g., `single-reviewer-task/` uses a 2-phase single-reviewer state machine with non-mousepad state names).
- `autonomous-prod.sh` — Claude-specific in-band prod helper. Use only in environments where background shell completion re-enters the conversation as a mechanical notification. It is not the generic continuity mechanism for Codex or other environments.

## Roles

- **Loop runner** — owns the loop lifecycle: spawns coordinators and reviewers, manages the control plane, captures results, makes transition decisions. Does not author the judged deliverable.
- **Coordinator** — executes the task work. May decompose into subagents. Cannot self-stop the loop. Produces a deliverable and a 7-field return.
- **Reviewer 1 (adherence)** — checks whether the coordinator followed the frame's structural principles. Fresh context, no deliverable authorship.
- **Reviewer 2 (quality elevation)** — checks whether the deliverable meets a professional-team benchmark. Holds loop-finish stop authority ("only minor changes remain"). In multi-round instances, also checks governance: did the coordinator address prior feedback?
- **Reviewer 3 (task finish)** — checks whether the top candidate meets the task's explicit finish condition. Holds task-finish stop authority. Independent — no frame context, no loop context.
- **External supervisor** — watches the active actor on a cadence, checkpoints healthy progress, reconciles terminal states. Not a role in the reviewer chain — infrastructure only.

## How to instantiate on a new task

1. Create `instances/<task-name>/`
2. Copy `control_plane.py` and `loop_supervisor.py` into the instance folder
3. Copy `task-model-template.yaml` as `task_model.yaml` and customize the states, transitions, and roles for your task
4. Create `manifest.yaml` with the task's objective, stop conditions, and initial state
5. Copy and instantiate `OBSERVATION-FILE-TEMPLATE.md`
6. Copy and customize `transition-protocol-template.md`
7. Copy and customize reviewer prompt templates
8. Write the round-1 coordinator delegation prompt
9. The harness runs from there — the control plane manages state, the supervisor watches for failures, the transition protocol governs the reviewer chain, and the observation file acts as the maintained status surface
10. After initialization, run `python3 control_plane.py refresh-continuation` once so the instance has a generated resume packet before any handoff

## Fresh launch vs continuation

- Use `LAUNCH-TEMPLATE.md` only for a fresh instance or fresh task setup.
- For an existing instance, read that instance's generated `CONTINUATION.md` first. Do not reuse the launch template as a continuation prompt.
- If `CONTINUATION.md` is missing or stale after importing older artifacts, run `python3 control_plane.py refresh-continuation`.

## Status

Prototype. Extracted from the first live instance (mousepad-loop, 2026-04-12), then generalized (2026-04-12). Core machinery works (state transitions, compare-and-set guards, probe-active checkpointing, infrastructure-failure recovery path). State machines and role mappings are now loaded from `task_model.yaml`, not hardcoded.

Validated on:
- 3-reviewer chain (mousepad-loop and harness-generalization-loop instances)
- Single-reviewer chain with non-mousepad state names (test-fixtures/single-reviewer-task)

Known gaps:
- loop_supervisor.py was tested against one failure mode (auth expiry stale-wait). Needs more stress testing.
- The reviewer prompt templates are first-pass generalizations from mousepad-specific prompts. May need iteration after being used on a different task type.
- Observation-file structure was previously only a research-note lesson; `OBSERVATION-FILE-TEMPLATE.md` is the first explicit harness-level generalization and still needs use on non-research tasks.
- No automated instantiation script. Manual copy-and-configure for now.
- The `validate` function enforces `user_contact_policy.mode = "extraordinary_only"` and `reporting_policy.mode = "extraordinary_or_terminal"` as the only valid modes. These are harness-level invariants, not task-specific, but future task classes might want different policy modes.
- Shared harness copies prior to the continuation import may not regenerate `CONTINUATION.md` yet. Existing instances need either a refreshed local control-plane copy or a one-time manual migration.

## Round-3 generalization changes (2026-04-12)

- **Artifact-path round validation generalized.** `validate()` no longer hardcodes `coordinator_return_capture` and `coordinator_artifact` as artifact key names. Round-scoped artifact keys are declared via `round_scoped_artifact_keys` in `task_model.yaml`. Instances list which `artifact_paths` keys should be validated against `current_round_path`. Instances without the field produce no artifact-path warnings — clean default for tasks that don't use round-scoped artifacts.
- **Single-reviewer fixture strengthened.** The fixture's `manifest.yaml` now has non-empty `artifact_paths` with non-mousepad key names (`deliverable_output`, `review_verdict`), and its `task_model.yaml` declares matching `round_scoped_artifact_keys`. The validation path is now exercised on the fixture — both positive (correct round path) and negative (mismatched round path produces expected warning).

## Round-2 generalization changes (2026-04-12)

- **Prompt-binding warnings generalized** (was S1). `reviewer_prompt_binding_warnings()` renamed to `prompt_binding_warnings()` and driven by an optional `prompt_binding_checks` field in the role definition. Roles without the field produce no warnings; roles with it declare their prompt artifact key and required artifact keys in the task model. No silent degradation on non-mousepad instances.
- **Active-actor validation generalized** (was S2). `validate()` now checks a `requires_active_actor` list from the task model instead of the `_in_progress` suffix convention. Falls back to the suffix heuristic only when the field is absent.
- **Fixture drift eliminated** (was S3). Test fixture Python files replaced with symlinks to harness originals. `ROOT` changed from `Path(__file__).resolve().parent` to `Path(__file__).absolute().parent` so symlinked invocations find instance-local data files.
- **Role schema validated at load time** (was S4). `_derive_role_map()` now requires `active_state` and `done_state` for every role and validates that referenced states exist. Malformed roles fail loudly at import time instead of silently at reconciliation.
