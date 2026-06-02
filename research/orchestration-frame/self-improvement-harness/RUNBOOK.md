# Self-Improvement Harness — Runbook

This is the default operating path for the top-level self-improvement harness.

## Startup

1. Validate the harness state.

```bash
python3 control_plane.py validate
python3 workboard.py validate
```

2. Start the watchdog before starting or resuming the orchestrator.

```bash
bash watchdog-service.sh start
```

If you want the watchdog to be allowed to launch a configured recovery command:

```bash
bash watchdog-service.sh start --run-recovery
```

3. Confirm the watchdog is live.

```bash
bash watchdog-service.sh status
python3 control_plane.py show
python3 workboard.py show
```

4. Read the generated `CONTINUATION.md` handoff, then execute `manifest.yaml` `next_action`.

If `CONTINUATION.md` conflicts with `manifest.yaml` or `python3 control_plane.py show`, the control plane wins; regenerate the packet by repairing source truth through the control-plane mutation path rather than editing the continuation file by hand.

If the harness is in `global_reconciliation_pending`, treat that as an active top-level program state, not an excuse to idle. Reconcile `global_completion.open_workstreams` against `WORKBOARD.yaml`, then reopen the next canonical round or branch explicitly through `control_plane.py transition`.

## During a live session

- While actively working, emit heartbeats with `python3 control_plane.py heartbeat ...`
- Keep `WORKBOARD.yaml` current with `python3 workboard.py set-stream ...` so open work is tied to explicit streams rather than prose-only notes
- If a new round is being opened, switch `current_iteration`, `current_iteration_path`, and the active round artifact pointers in the same control-plane transition
- Treat `CONTINUATION.md` as a generated handoff view, not a manual status note
- After a mutating control-plane action, verify that `CONTINUATION.md` matches `python3 control_plane.py show`; do not patch the packet directly
- Treat waits as build windows. If a reviewer, child, or fetch wait is live and independent work remains, open or continue orthogonal side-work instead of idling.
- When intentionally parking, release the lease with `python3 control_plane.py release-lease ...`
- Treat `.watchdog/status.json`, `.watchdog/runtime.json`, `manifest.yaml` `observation_window`, and `CONTINUATION.md` as the operator dashboard

## Verification

Run the standard watchdog regression surface after changes:

```bash
python3 test_watchdog.py
```

## Shutdown

When you intentionally stop external supervision:

```bash
bash watchdog-service.sh stop
```

Do not stop the watchdog merely because a local branch converged. Only stop it when the harness is genuinely parked, replaced by another supervisor, or globally complete.
