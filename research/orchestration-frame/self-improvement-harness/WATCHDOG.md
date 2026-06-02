# Self-Improvement Harness — Watchdog

`watchdog.py` is the external observer for the top-level self-improvement harness.

It runs outside any live Claude/Codex session and checkpoints three things:

- whether the harness currently has an active lease
- whether that lease is healthy, stale, inactive, or terminal
- what the next recovery move should be if the active session silently dies

## Why it exists

The lease surface inside `manifest.yaml` is necessary but not sufficient.

If the active session disappears, no in-band agent remains to notice. The watchdog closes that gap by polling from outside the session and writing durable state back through `control_plane.py watchdog-checkpoint`.

## Commands

One-shot poll:

```bash
python3 watchdog.py --json
```

Service wrapper:

```bash
bash watchdog-service.sh start
bash watchdog-service.sh status
bash watchdog-service.sh stop
```

Continuous polling:

```bash
python3 watchdog.py --watch --json
```

Allow configured auto-resume commands when stale grace is exceeded:

```bash
python3 watchdog.py --watch --run-recovery --json
```

Repeatable smoke test against cloned fixtures:

```bash
python3 test_watchdog.py
```

## Artifacts

- `manifest.yaml`
  The watchdog block and observation window are updated here.
- `run-ledger.jsonl`
  The watchdog appends a ledger row when the watchdog condition changes.
- `watchdog-service.sh`
  Operator wrapper for foreground/background watchdog management.
- `.watchdog/status.json`
  External sidecar status for operators even if they do not inspect the manifest directly.
- `.watchdog/runtime.json`
  Runtime metadata for the currently running watchdog process, including foreground/PTY-owned sessions that do not use the pid-file daemon path.
- `.watchdog/recovery-*.log`
  Recovery command stdout/stderr when `--run-recovery` is enabled and a recovery command is launched.

## Condition model

- `never_checked`
  Watchdog has not yet polled this harness.
- `healthy`
  Lease is active and within freshness bounds.
- `inactive`
  No active lease is held. The harness is parked, not stalled.
- `stale_suspect`
  Lease is stale on this poll, but grace has not yet been exceeded.
- `recovery_required`
  Lease stayed stale past grace and no recovery command was launched.
- `recovery_in_progress`
  Lease stayed stale past grace and the watchdog launched the configured recovery command.
- `terminal`
  Harness is already in a terminal state.
- `invalid`
  Control-plane state is malformed enough that the watchdog cannot safely reconcile it.

## Auto-resume contract

Auto-resume is intentionally two-keyed:

- `manifest.yaml` may provide `watchdog.auto_resume_command`
- the watchdog process must also be launched with `--run-recovery`

Both are required. If either is missing, stale grace escalates to `recovery_required` rather than silently executing commands.

## Verification

`test_watchdog.py` is the default regression surface for the watchdog.

- it clones fixtures into a temporary directory instead of mutating the baselines
- it verifies inactive, healthy, stale-recovery, and terminal watchdog behavior
- it verifies that repeated healthy polls do not spam the ledger

## Default operating path

Use `RUNBOOK.md` as the startup sequence. The intended order is:

1. validate control plane
2. start the watchdog
3. confirm watchdog status
4. execute `manifest.yaml` `next_action`

The operator dashboard is intentionally split across durable surfaces:

- `.watchdog/status.json` for the latest poll result
- `.watchdog/runtime.json` for the live watchdog process and mode
- `manifest.yaml` `watchdog` plus `observation_window` for canonical state
- `python3 control_plane.py show` and `python3 workboard.py show` for reconciled summaries

If these surfaces disagree, repair the control plane before trusting prose.

## Load-bearing rules

- Repeated healthy or inactive polls do not spam the ledger.
- Condition changes are durable.
- Stale active leases are warning-level control-plane findings, not fatal validator errors.
- The watchdog writes a sidecar status file on every poll, even when the ledger does not change.
- The watchdog also writes `.watchdog/runtime.json` so service status can confirm foreground liveness instead of only pid-file daemons.
- An inactive lease with unresolved work is not "healthy inactivity"; it is an unowned-open-work condition that must remain visible to operators.
- Control-plane writes still fail closed: if the candidate checkpoint is invalid, it is not committed.
