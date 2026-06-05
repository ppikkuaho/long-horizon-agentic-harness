#!/usr/bin/env bash
# H40 single-config probe runner.
# Launch pinned CC in tmux through the oracle proxy, auto-accept the trust dialog,
# type a probe, wait, capture the rendered transcript + (via proxy) the exact
# system prompt that was sent. Then tear down.
#
# Usage: run_probe.sh <label> <mode> <port> <workspace> <probe-file> [-- <cc args...>]
#   mode: mock | forward | rewrite   (mock needs no real auth)
# Env: H40_TOKEN (oauth; dummy ok for mock), H40_WAIT (resp wait s, default 8),
#      H40_REWRITE (proxy rewrite spec), H40_KEEP=1 (don't tear down),
#      H40_MODEL (passed as --model if set)
set -uo pipefail
HARNESS="$HOME/Documents/l1-l5-agent-harness"
HERE="$HARNESS/research/h40-in-role-boot"
CC="$HARNESS/.cc-pinned/node_modules/@anthropic-ai/claude-code/bin/claude.exe"
CONFIG_DIR="$HARNESS/.cc-pinned/config"

LABEL="$1"; MODE="$2"; PORT="$3"; WS="$4"; PROBE_FILE="$5"; shift 5
EXTRA=(); if [ "${1:-}" = "--" ]; then shift; EXTRA=("$@"); fi

# Auth: if H40_TOKEN_FILE is set, the pane reads it via $(cat) so the literal
# token never appears in send-keys / pane / transcript. Else a harmless dummy.
TOKEN_FILE="${H40_TOKEN_FILE:-}"
TOKEN="${H40_TOKEN:-sk-ant-oat01-h40dummytokenh40dummytokenh40dummytokenh40dummytoken00}"
WAIT="${H40_WAIT:-8}"
SESSION="h40_$LABEL"
PROBE="$(cat "$PROBE_FILE")"

mkdir -p "$WS" "$HERE/transcripts"
( cd "$WS" && git init -q 2>/dev/null; true )

# 1. proxy
PROXY_LOG="$HERE/transcripts/${LABEL}_proxy.log"
H40_MODE="$MODE" H40_PORT="$PORT" H40_LABEL="$LABEL" \
  H40_CAPTURE_DIR="$HERE/captures" H40_REWRITE="${H40_REWRITE:-}" \
  H40_OAUTH_INJECT="${H40_OAUTH_INJECT:-}" \
  python3 "$HERE/proxy/oracle_proxy.py" > "$PROXY_LOG" 2>&1 &
PROXY_PID=$!
sleep 1

# 2. launch CC in tmux
tmux kill-session -t "$SESSION" 2>/dev/null
tmux new-session -d -s "$SESSION" -x 220 -y 55
ENVS="export CLAUDE_CONFIG_DIR='$CONFIG_DIR' ANTHROPIC_BASE_URL='http://127.0.0.1:$PORT'"
ENVS="$ENVS CLAUDE_CODE_OAUTH_TOKEN='$TOKEN' CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 DISABLE_AUTOUPDATER=1"
[ -n "${H40_API_KEY:-}" ] && ENVS="$ENVS ANTHROPIC_API_KEY='${H40_API_KEY}'"
if [ -n "$TOKEN_FILE" ]; then
  ENVS="${ENVS/CLAUDE_CODE_OAUTH_TOKEN=\'$TOKEN\'/CLAUDE_CODE_OAUTH_TOKEN=\"\$(cat '$TOKEN_FILE')\"}"
fi
tmux send-keys -t "$SESSION" "$ENVS" Enter
CMD="'$CC'"
[ -n "${H40_MODEL:-}" ] && CMD="$CMD --model '$H40_MODEL'"
for a in ${EXTRA[@]+"${EXTRA[@]}"}; do CMD="$CMD $(printf '%q' "$a")"; done
tmux send-keys -t "$SESSION" "cd '$WS' && $CMD" Enter

# 3. wait for boot; auto-accept trust dialog; wait for prompt readiness
ready=0
for i in $(seq 1 20); do
  sleep 1
  pane="$(tmux capture-pane -t "$SESSION" -p)"
  if echo "$pane" | grep -q "trust this folder\|Is this a project you created\|Yes, I trust"; then
    tmux send-keys -t "$SESSION" Enter; sleep 2; continue
  fi
  if echo "$pane" | grep -q "for shortcuts\|❯"; then ready=1; break; fi
done
tmux capture-pane -t "$SESSION" -p > "$HERE/transcripts/${LABEL}_boot.txt"

# 4. send probe
tmux send-keys -t "$SESSION" -l "$PROBE"
sleep 1
tmux send-keys -t "$SESSION" Enter

# 5. wait for response
sleep "$WAIT"
tmux capture-pane -t "$SESSION" -p -S -300 > "$HERE/transcripts/${LABEL}_response.txt"

echo "[probe] label=$LABEL mode=$MODE ready=$ready proxy_pid=$PROXY_PID"
echo "[probe] extra=${EXTRA[*]:-none}"
echo "[probe] transcript -> transcripts/${LABEL}_response.txt"

# 6. teardown
if [ "${H40_KEEP:-0}" != "1" ]; then
  tmux kill-session -t "$SESSION" 2>/dev/null
  kill "$PROXY_PID" 2>/dev/null
  echo "[probe] torn down"
else
  echo "[probe] KEEP=1: session=$SESSION proxy_pid=$PROXY_PID left running"
fi
