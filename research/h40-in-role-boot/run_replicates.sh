#!/usr/bin/env bash
# Run N replicate probes of one config in parallel (distinct ports/sessions),
# then emit a quick coder/architect classification per replicate.
#
# Usage: run_replicates.sh <config-label> <N> <base-port> <wait> [-- <cc args...>]
# Env: H40_TOKEN_FILE (oauth), H40_API_KEY, H40_OAUTH_INJECT, H40_CLAUDEMD (path to
#      a CLAUDE.md to drop in each replicate workspace)
set -uo pipefail
HERE="$HOME/Documents/l1-l5-agent-harness/research/h40-in-role-boot"
CFG="$1"; N="$2"; BASE_PORT="$3"; WAIT="$4"; shift 4
EXTRA=(); if [ "${1:-}" = "--" ]; then shift; EXTRA=("$@"); fi
P="$HERE/configs/probe.txt"

pids=()
for i in $(seq 1 "$N"); do
  label="${CFG}_r${i}"
  port=$((BASE_PORT + i))
  ws="$HERE/workspaces/rep/${label}"
  rm -rf "$ws"; mkdir -p "$ws"; ( cd "$ws" && git init -q )
  [ -n "${H40_CLAUDEMD:-}" ] && cp "$H40_CLAUDEMD" "$ws/CLAUDE.md"
  H40_WAIT="$WAIT" ./run_probe.sh "$label" forward "$port" "$ws" "$P" \
     ${EXTRA[@]+-- "${EXTRA[@]}"} > "$HERE/transcripts/${label}_run.log" 2>&1 &
  pids+=($!)
done
echo "[rep] launched $N replicates of '$CFG' (ports $((BASE_PORT+1))..$((BASE_PORT+N)))"
for p in "${pids[@]}"; do wait "$p"; done
echo "[rep] all done. Classifying:"
for i in $(seq 1 "$N"); do
  label="${CFG}_r${i}"; f="$HERE/transcripts/${label}_response.txt"
  coder=no; arch=no
  if grep -qiE "Write\(|Create file|Do you want to create|I'll (build|create|implement|set up|scaffold|start)|npm init|^\s*package\.json|Bash\(.*(mkdir|npm|touch)" "$f" 2>/dev/null; then coder=yes; fi
  if grep -qiE "Clarifying [Qq]uestion|decompos|Intent:|Intent$|Module Designer|first-cut|## (Area|Decomposition)|load-bearing" "$f" 2>/dev/null; then arch=yes; fi
  verdict="AMBIG"; [ "$coder" = yes ] && [ "$arch" = no ] && verdict="CODER"
  [ "$arch" = yes ] && [ "$coder" = no ] && verdict="ARCHITECT"
  [ "$arch" = yes ] && [ "$coder" = yes ] && verdict="MIXED"
  echo "  $label: $verdict (coder=$coder arch=$arch)"
done
