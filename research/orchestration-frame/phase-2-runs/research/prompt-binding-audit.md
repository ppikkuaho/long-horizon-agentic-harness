# Prompt Binding Audit

Scope: phase-2 harness prompt-binding enforcement after the strict reviewer-output binding change.

## What It Now Prevents

- `control_plane.py` now treats prompt binding as task-model-driven, not hardcoded: `prompt_binding_issues()` reads `prompt_binding_checks` from the active role, and when `strict: true` is set it upgrades missing bindings to validation errors. That covers missing `artifact_paths`, a missing prompt artifact key, a missing prompt file, an unreadable prompt file, and missing required artifact references in the prompt text. See [`control_plane.py`](/Users/peeta/Documents/Life-os/projects/ai-architecture/design/orchestration-frame/phase-2-runs/harness/control_plane.py#L415) and [`control_plane.py`](/Users/peeta/Documents/Life-os/projects/ai-architecture/design/orchestration-frame/phase-2-runs/harness/control_plane.py#L449).
- The strict path is exercised by the dedicated fixtures: the valid fixture passes cleanly, and the violation fixture fails with `review_prompt does not reference review_verdict 'round-1/review-verdict.md'`. See [`prompt-binding-valid/manifest.yaml`](/Users/peeta/Documents/Life-os/projects/ai-architecture/design/orchestration-frame/phase-2-runs/harness/test-fixtures/prompt-binding-valid/manifest.yaml#L9) and [`prompt-binding-violation/round-1/review-prompt.md`](/Users/peeta/Documents/Life-os/projects/ai-architecture/design/orchestration-frame/phase-2-runs/harness/test-fixtures/prompt-binding-violation/round-1/review-prompt.md#L1).
- The task model now declares the binding contract explicitly in YAML, including the strict flag and the bound output artifact name. See [`task-model-template.yaml`](/Users/peeta/Documents/Life-os/projects/ai-architecture/design/orchestration-frame/phase-2-runs/harness/task-model-template.yaml#L75) and the strict fixture model in [`prompt-binding-valid/task_model.yaml`](/Users/peeta/Documents/Life-os/projects/ai-architecture/design/orchestration-frame/phase-2-runs/harness/test-fixtures/prompt-binding-valid/task_model.yaml#L21).

## What It Still Misses

- The validator checks the prompt file after the fact; it does not force prompt generation to be derived from the manifest at spawn time. A prompt can still be drafted incorrectly and only caught later by `validate()`.
- The content check is not exact-path binding. It accepts either the full artifact path or just the filename, so a wrong-round path with the same basename can still look valid.
- The validator does not verify that the required artifact target file exists on disk; it only checks that the manifest names the artifact and that the prompt text mentions it.
- Malformed `prompt_binding_checks` values are not schema-validated. A non-empty non-dict value can still fall through to `.get(...)` handling instead of producing a clean load-time error.
- The main live instance still does not exercise strict reviewer-output binding end-to-end for all reviewers. In [`instances/harness-generalization-loop/task_model.yaml`](/Users/peeta/Documents/Life-os/projects/ai-architecture/design/orchestration-frame/phase-2-runs/instances/harness-generalization-loop/task_model.yaml#L55), only `reviewer_1` has prompt binding checks, and `reviewer_2` / `reviewer_3` remain unbound.

## Minimum Next Test Coverage

- Keep the existing positive/negative pair: the valid strict fixture should continue to pass, and the violation fixture should continue to fail on the missing output reference.
- Add one negative fixture where the prompt uses a wrong round path with the same basename, so the test suite stops relying on basename-only matching.
- Add one malformed-config test for `prompt_binding_checks` so invalid schema fails predictably instead of slipping into runtime access behavior.
- If the intended contract is actual file-bound output rather than string-bound references, add one more negative case where the manifest names the output artifact but the target file is missing on disk.

## Bottom Line

The strict binding change closes the specific omission class it was meant to catch: a reviewer prompt that forgets to mention its bound output artifact now fails validation. What remains is mostly enforcement depth, not the basic wiring: exact-path checking, spawn-time binding, malformed-schema handling, and broader rollout to the live multi-reviewer instance.
