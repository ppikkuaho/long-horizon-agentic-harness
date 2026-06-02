# Watchdog Design 01

Top choice: an externally renewed evidence lease with a `stale_suspect` layer, not a self-authorizing timeout kill.

## Position in the control plane

The watchdog is not a second scheduler. `manifest.yaml` remains the source of truth, `run-ledger.jsonl` remains the append-only history, and `control_plane.py transition` remains the only state-changing executor. The watchdog only:

- records lease ownership
- classifies liveness as `healthy`, `stale_suspect`, `recovery_in_progress`, or `failed_confirmed`
- triggers either renewal, recovery, or a normal executor transition

Use the same shape for mousepad-loop and the broader work-scoped-agent harness so every long-running role has one control surface.

## Lease owner

Lease owner = the current `active_actor` plus a monotonic `lease_epoch`.

Recommended manifest addition:

```yaml
watchdog:
  lease_epoch: 3
  owner_token: coordinator:subagent-656084b18b2e:9bca3f79-6517-4991-b041-37607fbc0da4:3
  condition: healthy
  renewed_at: 2026-04-12T02:30:48+03:00
  suspect_since: null
  recovery_attempts: 0
  last_evidence:
    source: supervisor_observe_plus_trace
    heartbeat_at: 2026-04-12T02:30:36.796013
    progress_at: 2026-04-12T02:27:36.594811
    semantic_event_at: 2026-04-11T23:23:16.050Z
```

The lease belongs to the work unit, not to the watchdog process. A restarted watchdog can resume from manifest state.

## Renewal source

Renewal must come from an observer, not from the child self-reporting success to itself. Primary renewal source:

- `work_scoped_agent.py observe`
- a targeted session-trace check
- optional artifact-delta check for the declared output files

Heartbeat alone is an input, never sufficient by itself. This preserves the current human-style observation model and matches the existing rule: never infer semantic progress from heartbeat alone.

## Stale detection signals

Mark `stale_suspect`, not failed, when renewal is overdue and one or more signals weaken:

- heartbeat stops advancing
- progress timestamp stops advancing
- semantic trace stays unchanged for too long relative to the declared runtime state
- runtime handle disappears from `observe`
- expected output artifact is missing after a terminal runtime report
- manifest state age grows while no ledger checkpoint or lease renewal appears

Use state-sensitive suspicion windows rather than one global timeout. Example: `waiting_on_child` can tolerate longer semantic silence than `writing_final_output`.

## Split-brain prevention

Prevent double ownership with generation-based authority:

- every spawn, adoption, or respawn increments `watchdog.lease_epoch`
- `control_plane.py transition` should require `--expected-lease-epoch` or `--expected-owner-token` before advancing an in-progress actor
- `next` should emit the current owner token so any helper acts against the right generation
- if an old actor returns after a respawn, record `stale_return_ignored` in the ledger and keep the newer owner authoritative

This is non-destructive. The old actor is de-authorized, not auto-killed.

## Recovery path

1. Lease renewal becomes overdue.
2. Watchdog writes a same-state checkpoint: `condition=stale_suspect`, `suspect_since=...`, ledger event `stale_suspect_opened`.
3. Run recovery probes: `observe`, trace check, artifact check.
4. If the actor is clearly live and still canonical, renew the lease and append `lease_renewed`.
5. If the actor is clearly done and the output trigger is satisfied, call `control_plane.py transition` and auto-advance normally.
6. If the actor is missing, terminal, or ownership is ambiguous, mark `recovery_in_progress`.
7. If one canonical live actor can be adopted, write a new owner token and continue.
8. Otherwise respawn from `resume_packet` under a new epoch and log `ownership_replaced`.

Only move to `failed_confirmed`, `blocked`, or `cancelled` after explicit evidence, not elapsed time alone.

## When to escalate vs auto-advance

Auto-advance when:

- the declared trigger is satisfied by durable evidence such as a finished coordinator return or reviewer verdict
- recovery finds a single canonical live actor and renewal is enough
- respawn can happen from the existing resume packet without destructive cleanup

Escalate when:

- authoritative artifacts conflict
- more than one live claimant exists for the same work unit and local evidence cannot pick one safely
- abandoning or cleaning up a live actor would be destructive or irreversible
- repeated `stale_suspect` cycles show no semantic movement and no safe respawn path
- a true external blocker or safety/compliance issue appears

## Executor and ledger integration

Minimal executor additions:

- `control_plane.py transition`: add expected-owner/generation guards and optional watchdog fields
- `control_plane.py lease-checkpoint`: append a ledger event and mutate only the `watchdog` block plus observed evidence
- `control_plane.py next`: include the watchdog packet so a fresh session can recover correctly

Recommended new ledger events:

- `lease_renewed`
- `stale_suspect_opened`
- `recovery_probe_started`
- `lease_recovered`
- `ownership_replaced`
- `stale_return_ignored`
- `failure_confirmed`

## Why this avoids timeout rigidity

The lease expiry does not mean "kill the worker" or even "declare failure." It means "the control plane now suspects staleness and must observe." That keeps long tool calls, slow synthesis, and human-style repair viable while still giving the harness a structural way to detect abandoned work, avoid silent idle, and recover without depending on a foreground operator staying perfectly attentive.
