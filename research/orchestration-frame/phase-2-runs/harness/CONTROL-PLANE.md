# Self-Improvement Harness — Control Plane

This loop now has a structural control plane. The authoritative next action is no longer "remembered from prose."

## Source of truth

In precedence order:

1. `manifest.yaml`
2. `run-ledger.jsonl`
3. `control_plane.py`
4. generated `CONTINUATION.md`
5. narrative files (`PROGRAM.md`, `TRANSITION-PROTOCOL.md`, `CURRENT-STATE.md`, `iteration-log.md`)

If the narrative files disagree with the manifest or ledger, repair the control plane first.

The manifest is also the write target for the live observation-window surface and for any reviewer output paths that are bound to a specific round. `CONTINUATION.md` is a derived resume surface, not an independent source of truth.

## Purpose

The control plane exists to prevent two specific failures:

1. idle pauses caused by "no immediate next step" confusion
2. accidental dependence on user replies for routine round transitions
3. unnecessary user-facing status reports caused by local judgment rather than structural permission

## Structural guarantee

The loop is only considered valid when all of the following are true:

- `manifest.yaml` names the current state
- `manifest.yaml` preserves `state_entered_at` for the current state
- `manifest.yaml` separately records the latest control-plane checkpoint/update time
- `manifest.yaml` records the current observation_window for the active work-scoped agent, and `probe-active` keeps it current
- `manifest.yaml` names the next action
- `manifest.yaml` records whether user input is allowed
- `manifest.yaml` records the reporting policy and `control_plane.py contact-check` can derive whether any user-facing report is allowed
- `manifest.yaml` treats reviewer output paths as manifest-bound artifacts: round-scoped reviewer verdict/output keys must live under `artifact_paths` and point at the current round path
- `CONTINUATION.md` is regenerated from manifest + ledger whenever the control plane mutates, or via an explicit refresh
- `run-ledger.jsonl` records the latest transition or checkpoint
- `control_plane.py validate` passes

If any of those fail, the defect is in the control plane and should be repaired before more content work.

## Commands

Read current truth:

```bash
python3 control_plane.py show
```

Emit the concrete next-action packet:

```bash
python3 control_plane.py next
```

Validate the control plane:

```bash
python3 control_plane.py validate
```

Check whether user-facing communication is structurally allowed:

```bash
python3 control_plane.py contact-check
```

Refresh the generated continuation packet:

```bash
python3 control_plane.py refresh-continuation
```

Advance state structurally:

```bash
python3 control_plane.py transition ...
```

Checkpoint the active work-scoped agent's observation window into the manifest and ledger:

```bash
python3 control_plane.py probe-active
```

Run the external supervisor once:

```bash
python3 loop_supervisor.py --json
```

Run the external supervisor continuously:

```bash
python3 loop_supervisor.py --watch --interval-s 20 --json
```

## Adopt now vs later

Adopted now:

- persisted manifest
- append-only ledger
- executable validator
- resumable transition helper with explicit allowed-transition checks
- compare-and-set transition preconditions (`expected-state`, with optional actor / owner / ledger guards)
- machine-readable next-action packet emission
- generated continuation packet derived from the control plane rather than maintained manually
- watchdog evidence block with non-destructive condition states
- supervisor-driven runtime probe that converts `work_scoped_agent.py observe` output into durable control-plane evidence
- spawn-slot claim pattern (`reviewer_2_continue` -> `coordinator_pending` before actual actor creation)
- external supervisor (`loop_supervisor.py`) that:
  - probes healthy active actors on a cadence
  - reconciles terminal states exactly once
  - converts auth failures into `coordinator_failed_infrastructure` instead of leaving the loop in a stale wait
  - uses a filesystem lock so only one supervisor instance owns the loop at a time

Deferred for later hardening:

- deployment wrapper for the external supervisor outside this sandbox (launchd/systemd/user shell runner)
- backend-specific semantic taps richer than heartbeat/progress alone
- durable parent-child mailbox for repair and coordination across longer waits
- queue-backed transition executor
- separate control-loop daemon that can auto-open widening branches

Those stronger options may still be worth adding, but the current loop now has a concrete, machine-checkable next-step surface, guarded transitions, a minimal transition executor, and a stale-suspect layer that does not equate age with failure.

## Deployment note

The supervisor is structurally implemented, but sandbox backgrounding is not a valid deployment test here: child processes launched with shell-background patterns are reaped when the sandboxed command exits. In this environment, continuous verification should use a long-lived PTY session. For real unattended use, run `loop_supervisor.py --watch` under a service manager or an actual user shell that will keep the process alive.
