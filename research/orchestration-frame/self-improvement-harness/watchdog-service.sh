#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNTIME_DIR="$ROOT/.watchdog"
PID_FILE="$RUNTIME_DIR/watchdog.pid"
LOG_FILE="$RUNTIME_DIR/watchdog.log"
WATCHDOG_PY="$ROOT/watchdog.py"
RUNTIME_STATUS_FILE="$RUNTIME_DIR/runtime.json"
LOCK_FILE="$ROOT/.watchdog.lock"

mkdir -p "$RUNTIME_DIR"

usage() {
  cat <<'EOF'
Usage: bash watchdog-service.sh {run-once|run-foreground|start|stop|restart|status|logs} [--run-recovery] [--interval-s N]

Commands:
  run-once        Run one watchdog poll synchronously.
  run-foreground  Run watchdog.py --watch in the foreground.
  start           Start watchdog.py --watch in the background and record a pid file.
  stop            Stop the background watchdog if running.
  restart         Stop then start the background watchdog.
  status          Show whether the background watchdog appears to be running.
  logs            Tail the watchdog log file.

Notes:
  - Background start is intended for a real user shell or service manager.
  - In this sandbox, background children may be reaped when the parent exits.
EOF
}

read_pid() {
  if [[ -f "$PID_FILE" ]]; then
    cat "$PID_FILE"
  fi
}

is_running() {
  local pid="${1:-}"
  [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
}

COMMAND="${1:-status}"
if [[ $# -gt 0 ]]; then
  shift
fi

EXTRA_ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --run-recovery)
      EXTRA_ARGS+=("--run-recovery")
      shift
      ;;
    --interval-s)
      if [[ $# -lt 2 ]]; then
        echo "--interval-s requires a value" >&2
        exit 1
      fi
      EXTRA_ARGS+=("--interval-s" "$2")
      shift 2
      ;;
    *)
      echo "Unknown flag: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

case "$COMMAND" in
  run-once)
    if [[ ${#EXTRA_ARGS[@]} -gt 0 ]]; then
      exec python3 "$WATCHDOG_PY" --json "${EXTRA_ARGS[@]}"
    fi
    exec python3 "$WATCHDOG_PY" --json
    ;;
  run-foreground)
    if [[ ${#EXTRA_ARGS[@]} -gt 0 ]]; then
      exec python3 "$WATCHDOG_PY" --watch --json "${EXTRA_ARGS[@]}"
    fi
    exec python3 "$WATCHDOG_PY" --watch --json
    ;;
  start)
    existing_pid="$(read_pid || true)"
    if is_running "$existing_pid"; then
      echo "watchdog already running: pid=$existing_pid"
      exit 0
    fi
    rm -f "$PID_FILE"
    if [[ ${#EXTRA_ARGS[@]} -gt 0 ]]; then
      nohup python3 "$WATCHDOG_PY" --watch --json "${EXTRA_ARGS[@]}" >>"$LOG_FILE" 2>&1 &
    else
      nohup python3 "$WATCHDOG_PY" --watch --json >>"$LOG_FILE" 2>&1 &
    fi
    echo "$!" >"$PID_FILE"
    echo "watchdog started: pid=$(cat "$PID_FILE") log=$LOG_FILE"
    ;;
  stop)
    existing_pid="$(read_pid || true)"
    if ! is_running "$existing_pid"; then
      echo "watchdog not running"
      rm -f "$PID_FILE"
      exit 0
    fi
    kill "$existing_pid"
    rm -f "$PID_FILE"
    echo "watchdog stopped: pid=$existing_pid"
    ;;
  restart)
    "$0" stop
    if [[ ${#EXTRA_ARGS[@]} -gt 0 ]]; then
      "$0" start "${EXTRA_ARGS[@]}"
    else
      "$0" start
    fi
    ;;
  status)
    existing_pid="$(read_pid || true)"
    if is_running "$existing_pid"; then
      echo "watchdog running: pid=$existing_pid log=$LOG_FILE"
    elif [[ -f "$RUNTIME_STATUS_FILE" ]]; then
      lock_state="$(python3 - <<'PY' "$LOCK_FILE"
import fcntl, sys
from pathlib import Path
path = Path(sys.argv[1])
path.parent.mkdir(parents=True, exist_ok=True)
with path.open("a+", encoding="utf-8") as handle:
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("held")
    else:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        print("free")
PY
)"
      runtime_pid="$(python3 - <<'PY' "$RUNTIME_STATUS_FILE"
import json, sys
from pathlib import Path
path = Path(sys.argv[1])
try:
    payload = json.loads(path.read_text(encoding="utf-8"))
except Exception:
    print("")
    raise SystemExit(0)
print(payload.get("pid", ""))
PY
)"
      runtime_mode="$(python3 - <<'PY' "$RUNTIME_STATUS_FILE"
import json, sys
from pathlib import Path
path = Path(sys.argv[1])
try:
    payload = json.loads(path.read_text(encoding="utf-8"))
except Exception:
    print("")
    raise SystemExit(0)
print(payload.get("mode", ""))
PY
)"
      runtime_checked_at="$(python3 - <<'PY' "$RUNTIME_STATUS_FILE"
import json, sys
from pathlib import Path
path = Path(sys.argv[1])
try:
    payload = json.loads(path.read_text(encoding="utf-8"))
except Exception:
    print("")
    raise SystemExit(0)
print(payload.get("last_checked_at", ""))
PY
)"
      if is_running "$runtime_pid" || [[ "$lock_state" == "held" ]]; then
        echo "watchdog running: pid=$runtime_pid mode=$runtime_mode runtime=$RUNTIME_STATUS_FILE last_checked_at=$runtime_checked_at"
      else
        echo "watchdog not running"
        echo "stale runtime status present: $RUNTIME_STATUS_FILE"
        if [[ -f "$ROOT/.watchdog/status.json" ]]; then
          echo "last sidecar status: $ROOT/.watchdog/status.json"
        fi
      fi
    else
      echo "watchdog not running"
      if [[ -f "$PID_FILE" ]]; then
        echo "stale pid file present: $PID_FILE"
      fi
      if [[ -f "$ROOT/.watchdog/status.json" ]]; then
        echo "last sidecar status: $ROOT/.watchdog/status.json"
      fi
    fi
    ;;
  logs)
    if [[ -f "$LOG_FILE" ]]; then
      exec tail -n 50 -f "$LOG_FILE"
    fi
    echo "no watchdog log at $LOG_FILE" >&2
    exit 1
    ;;
  *)
    usage >&2
    exit 1
    ;;
esac
