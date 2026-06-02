# Saturation Implementation Plan

This plan targets the current phase-2 harness shape:
- canonical harness code in `harness/`
- vendored instance copies under `instances/<name>/`
- `manifest.yaml` + `run-ledger.jsonl` as the live state surface

The saturation layer must stay orthogonal to the task lifecycle state machine. Do not add saturation states to `task_model.yaml`; keep saturation under `manifest.saturation` and derive it from manifest + ledger.

## Files To Touch

- [harness/control_plane.py](/Users/peeta/Documents/Life-os/projects/ai-architecture/design/orchestration-frame/phase-2-runs/harness/control_plane.py)
- [harness/loop_supervisor.py](/Users/peeta/Documents/Life-os/projects/ai-architecture/design/orchestration-frame/phase-2-runs/harness/loop_supervisor.py)
- [harness/CONTROL-PLANE.md](/Users/peeta/Documents/Life-os/projects/ai-architecture/design/orchestration-frame/phase-2-runs/harness/CONTROL-PLANE.md)
- [harness/README.md](/Users/peeta/Documents/Life-os/projects/ai-architecture/design/orchestration-frame/phase-2-runs/harness/README.md)
- [harness/transition-protocol-template.md](/Users/peeta/Documents/Life-os/projects/ai-architecture/design/orchestration-frame/phase-2-runs/harness/transition-protocol-template.md)
- [instances/planner-builder-evaluator-loop/control_plane.py](/Users/peeta/Documents/Life-os/projects/ai-architecture/design/orchestration-frame/phase-2-runs/instances/planner-builder-evaluator-loop/control_plane.py)
- [instances/planner-builder-evaluator-loop/loop_supervisor.py](/Users/peeta/Documents/Life-os/projects/ai-architecture/design/orchestration-frame/phase-2-runs/instances/planner-builder-evaluator-loop/loop_supervisor.py)
- [instances/planner-builder-evaluator-loop/manifest.yaml](/Users/peeta/Documents/Life-os/projects/ai-architecture/design/orchestration-frame/phase-2-runs/instances/planner-builder-evaluator-loop/manifest.yaml)
- [instances/planner-builder-evaluator-loop/run-ledger.jsonl](/Users/peeta/Documents/Life-os/projects/ai-architecture/design/orchestration-frame/phase-2-runs/instances/planner-builder-evaluator-loop/run-ledger.jsonl)
- [instances/planner-builder-evaluator-loop/CONTROL-PLANE.md](/Users/peeta/Documents/Life-os/projects/ai-architecture/design/orchestration-frame/phase-2-runs/instances/planner-builder-evaluator-loop/CONTROL-PLANE.md)
- [instances/planner-builder-evaluator-loop/TRANSITION-PROTOCOL.md](/Users/peeta/Documents/Life-os/projects/ai-architecture/design/orchestration-frame/phase-2-runs/instances/planner-builder-evaluator-loop/TRANSITION-PROTOCOL.md)
- [instances/mousepad-loop/manifest.yaml](/Users/peeta/Documents/Life-os/projects/ai-architecture/design/orchestration-frame/phase-2-runs/instances/mousepad-loop/manifest.yaml)
- [instances/mousepad-loop/run-ledger.jsonl](/Users/peeta/Documents/Life-os/projects/ai-architecture/design/orchestration-frame/phase-2-runs/instances/mousepad-loop/run-ledger.jsonl)
- [instances/harness-generalization-loop/manifest.yaml](/Users/peeta/Documents/Life-os/projects/ai-architecture/design/orchestration-frame/phase-2-runs/instances/harness-generalization-loop/manifest.yaml)
- [instances/harness-generalization-loop/run-ledger.jsonl](/Users/peeta/Documents/Life-os/projects/ai-architecture/design/orchestration-frame/phase-2-runs/instances/harness-generalization-loop/run-ledger.jsonl)
- [harness/test-fixtures/planner-builder-valid/manifest.yaml](/Users/peeta/Documents/Life-os/projects/ai-architecture/design/orchestration-frame/phase-2-runs/harness/test-fixtures/planner-builder-valid/manifest.yaml)
- [harness/test-fixtures/planner-builder-valid/run-ledger.jsonl](/Users/peeta/Documents/Life-os/projects/ai-architecture/design/orchestration-frame/phase-2-runs/harness/test-fixtures/planner-builder-valid/run-ledger.jsonl)
- [harness/test-fixtures/planner-builder-violation/manifest.yaml](/Users/peeta/Documents/Life-os/projects/ai-architecture/design/orchestration-frame/phase-2-runs/harness/test-fixtures/planner-builder-violation/manifest.yaml)
- [harness/test-fixtures/planner-builder-violation/run-ledger.jsonl](/Users/peeta/Documents/Life-os/projects/ai-architecture/design/orchestration-frame/phase-2-runs/harness/test-fixtures/planner-builder-violation/run-ledger.jsonl)
- [harness/test-fixtures/single-reviewer-task/manifest.yaml](/Users/peeta/Documents/Life-os/projects/ai-architecture/design/orchestration-frame/phase-2-runs/harness/test-fixtures/single-reviewer-task/manifest.yaml)
- [harness/test-fixtures/single-reviewer-task/run-ledger.jsonl](/Users/peeta/Documents/Life-os/projects/ai-architecture/design/orchestration-frame/phase-2-runs/harness/test-fixtures/single-reviewer-task/run-ledger.jsonl)

## Implementation Shape

Use this manifest shape as the rollout target:

```yaml
saturation:
  round_id: 1
  target_live_count: 4
  minimum_live_count: 3
  maximum_live_count: 4
  live_count: 1
  distinct_surface_count: 1
  status: underutilized
  last_checked_at: 2026-04-12T15:27:00+03:00
  live_direction_ids:
    - D-001
  blocked_surface_reasons: []
  directions:
    D-001:
      direction_id: D-001
      branch_kind: verification
      owner: loop_runner
      spawn_epoch: 1
      surface_id: surf-001
      surface_fingerprint: sha256:...
      objective: verify the current candidate surface
      stop_condition: explicit result or dead-candidate decision
      write_target: round-1/branch-d-001.md
      countable: true
      duplication_class: unique
      state: live
      opened_at: 2026-04-12T15:05:00+03:00
      last_semantic_event_at: 2026-04-12T15:21:10+03:00
      completion_gate: artifact_committed_and_acknowledged
```

Keep the top-level `status` field for the task lifecycle. Saturation health lives in `manifest.saturation.status`.

## Sequence Of Changes

1. Update [harness/control_plane.py](/Users/peeta/Documents/Life-os/projects/ai-architecture/design/orchestration-frame/phase-2-runs/harness/control_plane.py) first.
   Add saturation parsing, normalization, and derivation helpers near the manifest/ledger I/O layer.
   Add `validate()` checks that compare manifest-derived saturation against ledger-derived saturation.
   Expose saturation in `show`, `next`, and the JSON summaries so callers can see `live_count`, `distinct_surface_count`, and `status`.
   Add explicit control-plane commands for `branch-open`, `branch-close`, and `saturation-check`.
   Keep branch-open atomic: classify surface, compute novelty, claim slot, persist manifest, append ledger, then let the caller launch the branch.

2. Update [harness/loop_supervisor.py](/Users/peeta/Documents/Life-os/projects/ai-architecture/design/orchestration-frame/phase-2-runs/harness/loop_supervisor.py).
   After each probe, refresh or validate the saturation block so a live instance cannot drift into a stale "looks healthy" state while the ledger says otherwise.
   Surface saturation degradation as a blocker class in the observation window instead of burying it in prose.
   Keep terminal-state reconciliation unchanged except for preserving the new saturation fields.

3. Update the harness docs in [harness/CONTROL-PLANE.md](/Users/peeta/Documents/Life-os/projects/ai-architecture/design/orchestration-frame/phase-2-runs/harness/CONTROL-PLANE.md), [harness/README.md](/Users/peeta/Documents/Life-os/projects/ai-architecture/design/orchestration-frame/phase-2-runs/harness/README.md), and [harness/transition-protocol-template.md](/Users/peeta/Documents/Life-os/projects/ai-architecture/design/orchestration-frame/phase-2-runs/harness/transition-protocol-template.md).
   Document that manifest state and ledger state are the authority for saturation.
   Document the branch-open ordering and the rejection cases for duplicate surfaces, oversubscription, and degraded rounds.
   Document that a shadow review or reroute only counts if it owns a distinct evidence surface and stop condition.

4. Propagate the canonical harness scripts into the active instance copy under [instances/planner-builder-evaluator-loop/](/Users/peeta/Documents/Life-os/projects/ai-architecture/design/orchestration-frame/phase-2-runs/instances/planner-builder-evaluator-loop/).
   This instance is the live canary for the new branch-accounting path.
   Treat the copy as generated from the harness source, not as an independent fork.

5. Backfill the current instance manifests and ledgers in [instances/planner-builder-evaluator-loop/manifest.yaml](/Users/peeta/Documents/Life-os/projects/ai-architecture/design/orchestration-frame/phase-2-runs/instances/planner-builder-evaluator-loop/manifest.yaml), [instances/mousepad-loop/manifest.yaml](/Users/peeta/Documents/Life-os/projects/ai-architecture/design/orchestration-frame/phase-2-runs/instances/mousepad-loop/manifest.yaml), [instances/harness-generalization-loop/manifest.yaml](/Users/peeta/Documents/Life-os/projects/ai-architecture/design/orchestration-frame/phase-2-runs/instances/harness-generalization-loop/manifest.yaml), and the corresponding `run-ledger.jsonl` files.
   Translate any legacy `active_branches` text into structured direction records.
   For converged instances, keep the saturation block empty and truthful rather than inventing live directions.
   For the active planner-builder-evaluator instance, seed only the directions that are actually backed by current branch packets and ledger evidence.

6. Backfill the fixture manifests and ledgers under [harness/test-fixtures/planner-builder-valid/](/Users/peeta/Documents/Life-os/projects/ai-architecture/design/orchestration-frame/phase-2-runs/harness/test-fixtures/planner-builder-valid/), [harness/test-fixtures/planner-builder-violation/](/Users/peeta/Documents/Life-os/projects/ai-architecture/design/orchestration-frame/phase-2-runs/harness/test-fixtures/planner-builder-violation/), and [harness/test-fixtures/single-reviewer-task/](/Users/peeta/Documents/Life-os/projects/ai-architecture/design/orchestration-frame/phase-2-runs/harness/test-fixtures/single-reviewer-task/).
   Use these as the regression set for empty saturation, valid branch claims, and duplicate-surface rejection.

## Migration Notes

- Roll out in a backward-compatible order.
- First pass: accept missing `manifest.saturation` as a legacy case, derive a transient saturation view from the ledger, and warn instead of hard-failing.
- Second pass: backfill the live instance manifests and fixture manifests.
- Cutover pass: make missing or inconsistent saturation a validation error for new runs.
- Do not rewrite historical ledger rows unless you are rebuilding a fixture from scratch.
- Prefer append-only normalization events when the current ledger can reconstruct the truth.
- If the ledger cannot reconstruct the truth, mark the round degraded and leave the direction uncounted.
- Preserve `active_branches` only as migration input for `instances/mousepad-loop/manifest.yaml`; do not keep it as the long-term source of truth.
- Do not treat `manifest.status` as a saturation state. The task lifecycle and the branch-accounting layer must remain separate.

## Minimum Verification

- Run `python3 harness/control_plane.py validate` against the updated harness copy and every touched manifest/ledger pair.
- Run `python3 harness/control_plane.py show --json` on `instances/planner-builder-evaluator-loop/` and confirm the saturation summary matches the ledger-derived live count.
- Run one happy-path branch-open check and one duplicate-surface rejection check against `harness/test-fixtures/planner-builder-valid/` and `harness/test-fixtures/planner-builder-violation/`.
- Run `python3 harness/control_plane.py validate` against `harness/test-fixtures/single-reviewer-task/` to confirm the empty-saturation case stays valid.
- Run `python3 harness/loop_supervisor.py --json` on the active planner-builder-evaluator instance after a probe to confirm the watcher preserves saturation metadata and still reconciles the live actor.
