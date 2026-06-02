# Mousepad Loop — Transition Protocol

This file exists to remove any hidden dependency on user replies during the live program.

Authoritative note:
- the actual next action lives in `manifest.yaml`
- `run-ledger.jsonl` records the latest committed checkpoint
- this file defines the transition semantics the control plane should encode

Rule:
- after every checkpoint, take the next action from this file
- if multiple actions are available, prefer the one that preserves momentum and observability
- if no action seems available, open an expansion branch instead of going idle

## Current live round control

### While the coordinator is still running

Do all of the following:

1. Observe via `work_scoped_agent.py observe`
2. Pair the supervisor snapshot with a targeted session-trace timestamp check
3. Record any durable architecture finding
4. Work one side branch in parallel if the coordinator is blocked on synthesis or a child

Never infer semantic progress from heartbeat alone.

### When the coordinator reaches `done`

Do all of the following immediately:

1. Capture the final text block verbatim into `round-1/coordinator-return.md`
2. Copy that same final text into `deliverable.md`
3. Record the completion in `iteration-log.md`
4. Spawn Reviewer 1 using the prepared delegation prompt

No user check-in is required.

## Reviewer chain protocol

### If Reviewer 1 finds non-adherence

1. Log the reviewer result
2. Spawn a new coordinator with amended delegation conditions
3. Preserve the failed artifact set for comparison

### If Reviewer 1 passes

1. Log the pass
2. Spawn Reviewer 2 immediately

### If Reviewer 2 says substantial changes remain

1. Log the reviewer result
2. Spawn a new coordinator with the reviewer feedback embedded as constraints
3. If the failure reveals a harness weakness, log it before respawning

### If Reviewer 2 says only minor changes remain

1. Log the pass
2. Spawn Reviewer 3 immediately
3. If convergence appears unusually early, prepare the shadow reviewer branch rather than trusting the main path alone

### If Reviewer 3 says the top candidate is below 90%

1. Log a dead-candidate event in `dead-candidates.md`
2. Choose one reroute mode from the precommitted menu below
3. Sleep 30 minutes at the round boundary
4. Spawn the next coordinator under materially different conditions

### If Reviewer 3 says the top candidate is at least 90%

1. Log the pass
2. Check whether the wider architecture program still has untested medium-or-larger gaps
3. If yes, widen through the prepared success-path branches before treating the broader program as converged
4. If not, proceed toward program consolidation

## Precommitted reroute menu for the first dead candidate

Choose the first option that has not yet been exercised:

1. `reroute-A`: clean-room rebuild
   Run a new coordinator with loop-runner state artifacts excluded from its readable surface.
2. `reroute-B`: decomposition inversion
   Replace the current extend-with-targeted-expansion strategy with a fresh rebuild from source discovery.
3. `reroute-C`: review-surface hardening
   Keep the candidate pool work but tighten evidence requirements and reviewer isolation before the next ranking.

Do not respond to the first dead candidate with a local prompt tweak that preserves the same branch shape.

## Success-path widening menu

If Round 1 appears to converge too quickly, open at least one of:

1. Reviewer-independence shadow branch
2. Clean-room contamination test branch
3. Alternate coordinator decomposition branch on the same task

The point is to widen the architecture test, not to relitigate the same answer.

## Extraordinary-condition bar

Only interrupt the user if one of these is true:

1. a destructive or irreversible action is needed beyond the approved program
2. authoritative artifacts conflict and cannot be locally resolved
3. a true external blocker prevents further progress
4. a safety or compliance issue requires human judgment

Everything else continues locally.
