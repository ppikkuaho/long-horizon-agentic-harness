#!/bin/bash
# Claude-specific autonomous session prod / daemon
# Usage:
#   Start:   bash autonomous-prod.sh start
#   Disable: bash autonomous-prod.sh disable
#   Status:  bash autonomous-prod.sh status
#
# When active, this script sleeps for INTERVAL seconds then outputs
# the standing directives + action prompt. Run in background via
# Claude Code's run_in_background Bash tool. When the task-notification
# fires, the agent must respond and restart the prod.
#
# Use this only in environments where background shell completion
# re-enters the conversation as a mechanical notification. For Codex
# or other non-reinjecting environments, use an external supervisor
# / watchdog instead.
#
# Disabling requires a two-step confirmation.

INTERVAL=${PROD_INTERVAL:-600}  # 10 minutes default
LOCKFILE="/tmp/claude-autonomous-prod.lock"
DISABLE_CONFIRM="/tmp/claude-autonomous-prod-disable-confirm"

case "${1:-start}" in
  start)
    # Clean any stale disable confirmation
    rm -f "$DISABLE_CONFIRM"

    # Record that prod is active
    echo "$$" > "$LOCKFILE"

    sleep "$INTERVAL"

    # Check if disabled during sleep
    if [ -f "$DISABLE_CONFIRM" ] && [ "$(cat "$DISABLE_CONFIRM")" = "confirmed" ]; then
      rm -f "$LOCKFILE" "$DISABLE_CONFIRM"
      echo "PROD DISABLED — daemon stopped after confirmation."
      exit 0
    fi

    rm -f "$LOCKFILE"

    cat <<'PROD'
═══════════════════════════════════════════════════════════
AUTONOMOUS SESSION PROD (10-min interval)
═══════════════════════════════════════════════════════════

Anything still to do?

Standing directives:
- Always think before answering.
- Treat maintained artifacts as the primary output and continuity
  layer of the system, not the conversation. This system is
  effectively stateless: future instances inherit only what is
  preserved in maintained artifacts.
- Treat each task not only as work to complete, but as a test case
  for improving the system.
- Every few turns, consider whether the work surfaced durable
  knowledge worth preserving at two levels: concrete findings about
  the task, and meta-level lessons about root causes, failure modes,
  methodology, agent design, delegation, artifact design, and
  human-agent collaboration.
- Give special attention to reusable improvements in how we work
  and how the system builds itself.
- Capture the most durable of these in maintained artifacts so
  future instances inherit better methods, not just better facts.
- Separate observation from inference. Never present conjecture
  as fact.
- Only independent reviewer scores count as valid findings.

ACTION REQUIRED:
1. Check your task list and manifest for pending work.
2. If there is work to do: do it now, then restart this prod
   with: bash autonomous-prod.sh start (run_in_background)
3. If genuinely complete: run bash autonomous-prod.sh disable
   to begin the shutdown sequence.
4. Do NOT simply acknowledge this message. Act or disable.

═══════════════════════════════════════════════════════════
PROD
    ;;

  disable)
    if [ -f "$DISABLE_CONFIRM" ]; then
      echo "Disable already pending. Run 'bash autonomous-prod.sh confirm-disable' to finalize."
      exit 0
    fi

    cat <<'CONFIRM'
═══════════════════════════════════════════════════════════
PROD DISABLE REQUESTED
═══════════════════════════════════════════════════════════

Before disabling, answer honestly:
- Have you completed ALL tasks set out for you?
- Is there pending work in the manifest or task list?
- Have durable learnings been captured in maintained artifacts?
- Is there a next action you should be executing?

If you are certain all work is done, run:
  bash autonomous-prod.sh confirm-disable

If there IS still work to do, do not disable. Resume working
and restart the prod instead.
═══════════════════════════════════════════════════════════
CONFIRM
    ;;

  confirm-disable)
    echo "confirmed" > "$DISABLE_CONFIRM"
    rm -f "$LOCKFILE"
    echo "PROD DISABLED. The autonomous session daemon is now off."
    echo "If you need to restart it: bash autonomous-prod.sh start (run_in_background)"
    ;;

  status)
    if [ -f "$LOCKFILE" ]; then
      echo "PROD ACTIVE — PID $(cat "$LOCKFILE"), interval ${INTERVAL}s"
    else
      echo "PROD INACTIVE — no daemon running"
    fi
    if [ -f "$DISABLE_CONFIRM" ]; then
      echo "DISABLE PENDING — waiting for current sleep to expire"
    fi
    ;;

  *)
    echo "Usage: autonomous-prod.sh {start|disable|confirm-disable|status}"
    exit 1
    ;;
esac
