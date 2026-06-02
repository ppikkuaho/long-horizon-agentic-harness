# Observation Window Hardening

This document proposes a concrete manager-facing observation and intervention surface for work-scoped agents.

It is based on the current phase-2 runtime/control-plane pattern:

- persisted `manifest.yaml`
- append-only `run-ledger.jsonl`
- executable `control_plane.py`
- external watcher / supervisor
- `probe-active` style checkpointing of the live observation window

The design generalizes that pattern so it can apply to any work-scoped agent tree, not just the current phase-2 loop.

## Design Goal

The manager needs three things at all times:

1. A truthful status surface for the active work unit.
2. A way to distinguish healthy waiting from real stalling.
3. A recovery path that preserves work whenever recovery is still structurally possible.

The key rule is that elapsed time is an input to suspicion, not a terminal condition. A long-running child can be healthy, waiting on IO, waiting on a joined child, or genuinely stuck. The control plane must distinguish those cases before it intervenes.

## Baseline Shape

The phase-2 runtime already has the right core mechanics. The generalized design keeps those mechanics and adds a manager-oriented observation layer on top:

- `manifest.yaml` is the current control snapshot.
- `run-ledger.jsonl` is the durable history.
- `control_plane.py` is the only state-changing executor.
- `loop_supervisor.py` or an equivalent watcher is the external observer.
- `probe-active` turns live runtime observation into durable state.

That is the correct base because it separates live observation from durable authority. The observation surface can be refreshed often; the control plane remains the source of truth.

## Manager Observation Surface

The manager-facing surface should answer one question quickly:

> What is the active work unit doing, what is it waiting on, and what can the parent safely do next?

The observation surface should expose a compact status card with these fields:

- `owner_token` and `lease_epoch`
- current actor id and role
- current state
- `state_entered_at`
- latest control-plane checkpoint time
- latest semantic event time
- latest progress time
- latest artifact delta time
- visible child states
- blocker class
- contact permission
- next action packet
- recovery condition

### Recommended status vocabulary

Use a small vocabulary that separates liveness from semantics:

- `healthy`
- `reasoning`
- `waiting_on_child`
- `waiting_on_io`
- `suspect_stalled`
- `recovery_in_progress`
- `failed_confirmed`

The status should never collapse into a binary healthy / failed view until the control plane has actually checked the relevant evidence.

### Recommended evidence bundle

The manager should be able to inspect, in one view, the evidence that justifies the current status:

- last observed runtime heartbeat
- last semantic trace event
- current child visibility
- current artifact path or output target
- current ledger tail
- current owner generation

If the status claim and the evidence bundle disagree, the bundle wins and the status must be repaired.

## Stuck Detection

Stuck detection should be state-sensitive, not one global timeout.

### Healthy waiting patterns

These are not stuck:

- a parent waiting on a joined child that is still visible and active
- a child waiting on IO with a recent request or external dependency
- a coordinator in a long reasoning phase that still shows semantic movement or artifact progress

### Suspicion triggers

Mark the work unit `suspect_stalled` when one or more of these are true:

- heartbeat remains present but semantic progress stops for longer than the state-specific window
- artifact path does not change while the state implies active production
- child visibility disappears without a matching completion signal
- the owner token or lease epoch no longer matches the active actor
- repeated checkpoints show the same state with no new evidence
- the control-plane summary says one thing and the trace says another

The correct first move is not termination. The correct first move is a durable suspicion mark plus a probe.

### What not to do

Do not use a single global timeout as the failure definition.

That creates false kills for slow but valid work and does not distinguish between:

- long computation
- waiting on a child
- waiting on external IO
- infrastructure failure
- true abandonment

## Parent Intervention Surface

The parent should have a bounded intervention menu, ordered from least invasive to most invasive.

### Level 1: Observe again

Use when the evidence is incomplete or stale.

- run a fresh probe
- compare live trace to manifest state
- refresh the evidence bundle
- confirm contact permission

This is the default response to uncertainty.

### Level 2: Nudge the current actor

Use when the actor is likely healthy but needs coordination.

- request a checkpoint
- request a joined-child return
- request an explicit blocker classification
- request a resume packet refresh

These actions should not change ownership.

### Level 3: Repair the active work unit

Use when the current owner is no longer canonical or the runtime has gone stale.

- renew the lease for a still-live canonical actor
- rotate `lease_epoch` when the active actor changes
- respawn the same delegation under a new owner token
- ignore stale returns from de-authorized actors
- rebind reviewer or child prompts to the current control-plane record

This is structural repair, not punishment.

### Level 4: Reframe the work

Use when the current path is alive but the path itself is wrong.

- branch to a different candidate path
- reopen the search basin
- swap in an orthogonal verifier
- widen the candidate set
- restart from a different condition set

This is the non-timeout answer to dead-candidate behavior.

### Level 5: Escalate upward

Use when the manager cannot safely resolve the ambiguity.

- conflicting live claimants
- external blocker or compliance issue
- destructive cleanup required
- no safe respawn path

Escalation is a structural decision, not a sign that the control plane failed.

## Recovery Paths Without Timeouts

The design should preserve as many recovery paths as possible before it declares failure.

### 1. Same-actor recovery

If the actor is still canonical and merely stale in the observation surface:

- checkpoint the observation window
- renew the lease
- resume the same actor

This is the least disruptive path.

### 2. Joined-child recovery

If the parent is waiting on a visible child:

- keep the parent alive
- let the child finish
- merge the child return into the parent’s current state

This path should be the default for supervised decomposition work.

### 3. Infrastructure retry

If the failure is auth expiry, rate limit, or transient backend error:

- treat it as infrastructure, not a dead candidate
- retry the same delegation
- keep the work unit identity intact

This is the correct path when the methodology was sound but the runtime failed.

### 4. Generation replacement

If the active actor is lost, ambiguous, or de-authorized:

- increment `lease_epoch`
- write a new owner token
- respawn from the resume packet
- ignore stale returns from the old generation

This avoids split-brain without destroying the work unit.

### 5. Candidate replacement

If the path itself is wrong:

- close the current candidate
- open a new candidate with different conditions
- preserve the evidence that motivated the branch change

This is the right response to dead-candidate recovery, not a timeout kill.

## Control-Plane Fields

The manager surface should persist enough state to survive session loss.

Recommended additions or equivalents:

```yaml
observation_window:
  status: healthy | reasoning | waiting_on_child | waiting_on_io | suspect_stalled | recovery_in_progress | failed_confirmed
  observed_at: ...
  semantic_event_at: ...
  progress_at: ...
  artifact_delta_at: ...
  child_states: {}
  blocker_class: null
  evidence_tail_ref: ...

watchdog:
  lease_epoch: 0
  owner_token: ...
  condition: healthy | stale_suspect | recovery_in_progress | failed_confirmed
  renewed_at: ...
  suspect_since: null
  recovery_attempts: 0

manager_intervention:
  last_action: null
  last_action_at: null
  allowed_actions: []
  escalation_target: null
```

The exact field names can vary, but the information must exist somewhere durable.

## Intervention Rules

Use these rules to keep the surface from becoming ad hoc:

- Do not let the parent self-authorize a kill from silence alone.
- Do not let a fresh session overwrite a live actor without a generation change.
- Do not let a stale return claim authority after respawn.
- Do not let a reviewer or child prompt be rebound from a draft; bind it from the current control plane.
- Do not let user-facing communication become the default escape hatch. Keep it behind the separate contact gate.

## Generalization Notes

This design applies to any work-scoped agent hierarchy:

- coordinator / reviewer chains
- planner / builder / evaluator chains
- parent / child decomposition trees
- retained-mode long-running agents

The same structure should recurse at each level:

- each parent observes its current child set
- each parent has a generation-guarded ownership token
- each parent can mark `suspect_stalled`
- each parent can recover by checkpoint, retry, respawn, or branch change

That recursion is the point. The manager surface should not depend on a special-case loop. It should be the default topology for work-scoped agents.

## Bottom Line

The hardened observation window is not just "better status output."

It is a structural contract:

- visible work state
- evidence-backed stuck detection
- generation-guarded parent intervention
- non-timeout recovery paths

If those four properties exist, the manager can stay honest about what the work unit is doing and recover it without turning silence into failure by default.
