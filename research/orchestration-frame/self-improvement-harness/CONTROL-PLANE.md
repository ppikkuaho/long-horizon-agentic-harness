# Self-Improvement Harness — Control Plane

This harness now has a structural control plane. The authoritative next action is no longer left implicit in prose.

## Source of truth

In precedence order:

1. `manifest.yaml`
2. `run-ledger.jsonl`
3. `control_plane.py`
4. `CONTINUATION.md` as the generated human-readable handoff derived from control-plane truth
5. narrative docs (`self-improvement-loop-playbook.md`, `self-improvement-loop-contract.md`, round briefs, reviewer verdict prose)

If the narrative docs disagree with the manifest or ledger, repair the control plane first.
If `CONTINUATION.md` disagrees with the manifest or ledger, repair the source truth and regenerate it; do not hand-repair the packet.

`../phase-2-runs/harness/` is an empirical proving ground, not a higher-precedence control plane for this folder. Promote proven lessons from that live harness through an explicit canonical round here; do not silently treat live drift as canonical truth.

## Required guarantees

The harness is only considered structurally sound when all of the following are true:

- `manifest.yaml` names the current state
- `manifest.yaml` preserves `state_entered_at`
- `manifest.yaml` separately records `last_control_plane_update_at`
- `manifest.yaml` exposes the next action and user-contact policy
- `manifest.yaml` exposes the reporting policy
- `manifest.yaml` carries a `global_completion` gate so local convergence cannot silently become top-level stop
- `manifest.yaml` carries an `activity_lease` surface so a fresh observer can tell whether the harness is active, stale, or deliberately inactive
- `manifest.yaml` carries a `watchdog` block and `observation_window` so external supervision is durable and machine-readable
- `WORKBOARD.yaml` materializes open work into explicit streams with owners, evidence, write targets, and next actions
- `CONTINUATION.md` is regenerated from control-plane truth whenever a mutation changes resume-relevant state
- control-plane mutations are serialized through a shared lock, and manifest writes are atomic
- `run-ledger.jsonl` records the last committed transition or checkpoint
- `python3 control_plane.py validate` passes

## Commands

Show current control-plane summary:

```bash
python3 control_plane.py show
```

Emit the machine-readable next-action packet:

```bash
python3 control_plane.py next
```

Validate manifest and ledger:

```bash
python3 control_plane.py validate
python3 workboard.py validate
```

Check whether user-facing communication is structurally allowed:

```bash
python3 control_plane.py contact-check
```

Record an active-session heartbeat:

```bash
python3 control_plane.py heartbeat --owner orchestrator --summary "working on round packet" --progress
```

Release the active-session lease when the current session is intentionally parking:

```bash
python3 control_plane.py release-lease --summary "parking after handing off to the next session"
```

Checkpoint watchdog state explicitly:

```bash
python3 control_plane.py watchdog-checkpoint ...
```

Advance state structurally:

```bash
python3 control_plane.py transition ...
```

When a new round becomes active, the transition must move these surfaces together:

- `current_iteration`
- `current_iteration_path`
- `current_round_brief`
- any active round artifact pointers (`current_builder_output`, `current_reviewer_1_verdict`, `current_reviewer_2_verdict`)

Do not leave a future round only "on disk" while the manifest still points at an earlier round.

Inspect or update the tracked work streams:

```bash
python3 workboard.py show
python3 workboard.py set-stream --stream-id WS-002 --status active --owner orchestrator
```

## Current scope

Adopted now:

- persisted manifest
- append-only ledger
- executable validator
- machine-readable next-action packet
- resumable transition helper
- compare-and-set transition preconditions (`expected-state`, optional ledger generation guard)
- activity lease / heartbeat surface
- external watchdog (`watchdog.py`)
- sidecar watchdog status file at `.watchdog/status.json`

Deferred for later hardening:

- queue-backed executor
- autonomous retry / backoff logic

The current goal is not full daemonization. It is to make the existing reviewer-governed harness runnable and resumable without relying on instruction-following alone.

## Workboard

`WORKBOARD.yaml` is the explicit branch registry for the reopened top-level program.

- `global_completion.open_workstreams` says what remains open at the program level
- `global_completion.open_stream_ids` binds those open program claims to the unresolved stream ids in `WORKBOARD.yaml`
- `WORKBOARD.yaml` says which concrete streams currently own that work
- `workboard.py` validates the stream registry and derives whether the program is inactive, underutilized, saturated, or oversubscribed
- `control_plane.py show` and `next` now surface a workboard summary so the resume packet includes branch saturation information

If the manifest says work remains open but the workboard has no unresolved streams, treat that as a structural defect and repair the board before doing more content work.
If `global_completion.open_stream_ids` and the unresolved workboard stream ids differ, treat that as a structural defect and repair the binding before doing more content work.

## Mutation Discipline

- `control_plane.py` now serializes mutating commands behind `.control-plane.lock`
- `watchdog-checkpoint`, `heartbeat`, `release-lease`, and `transition` all acquire that shared writer boundary before they read, validate, and commit
- `manifest.yaml` is written via atomic replace, not in-place truncation
- `CONTINUATION.md` is written via the same mutation path and refreshed from candidate manifest-plus-ledger truth before the commit completes
- the workboard has a matching `.workboard.lock` and atomic-write path

These locks do not solve higher-level stale-plan replay by themselves, but they do remove blind concurrent overwrites between the orchestrator and watchdog. Divergence in `CONTINUATION.md` is no longer repaired by hand; it is fixed by repairing source truth and rerunning the control-plane mutation path that regenerates the packet.

## Canonical versus live harness

This folder is the canonical harness specification and top-level control plane.

- `../phase-2-runs/harness/` is the reusable operational harness and proving ground
- canonical promotion happens only when the lesson is written into this folder's maintained docs or control-plane code
- unresolved divergence between the two is round-worthy work, not an acceptable background mismatch

## Stop guard

`stopped` is now a globally terminal state, not a local-convergence synonym.

- `status: stopped` is only valid when `global_completion.satisfied: true`
- `status: stopped` requires `next_action.kind: done`
- `status: stopped` requires `global_completion.open_workstreams` to be empty
- `next_action.kind: local_loop_stopped` is only valid in `global_reconciliation_pending`

That means a converged child loop can no longer silently collapse the top-level program. It must first pass through explicit global reconciliation.

Mutating commands (`transition`, `heartbeat`, `release-lease`) validate the candidate manifest plus ledger entry before writing. Invalid transitions are rejected without committing partial state.

## Watchdog

The watchdog is now first-class:

```bash
python3 watchdog.py --json
python3 watchdog.py --watch --json
python3 watchdog.py --watch --run-recovery --json
bash watchdog-service.sh start
bash watchdog-service.sh status
bash watchdog-service.sh stop
python3 test_watchdog.py
```

Operational details live in `WATCHDOG.md`.
