# Structural Options Review 01

Current baseline: the harness already has a persisted `manifest.yaml` + `run-ledger.jsonl` control plane, but the anti-idle / no-user-dependency behavior still lives mostly in prose (`PROGRAM.md`, `TRANSITION-PROTOCOL.md`). That is good for resume, but weak as structural enforcement. The live mousepad-loop findings also show that liveness and progress are not the same thing.

## Comparison

| Option | Resilience strengths | Failure modes | Implementation cost | Adopt now vs later |
| --- | --- | --- | --- | --- |
| 1. Persisted manifest + ledger only | Durable source of truth, resumable by a fresh session, easy to inspect, already implemented. | No enforcement of next action; stale `pending` states can sit forever; silent idle still looks "valid"; semantic stall is invisible; concurrent actors can race or double-advance. | Low | Keep as baseline only. Not sufficient as the anti-idle mechanism. |
| 2. Manifest + ledger + validator/checker | Catches illegal transitions, missing artifacts, malformed verdicts, manifest/ledger drift, and stale states. Fails closed before bad advances. Improves trust in the control plane without changing the whole architecture. | Mostly detects, not recovers. If nobody or nothing runs the checker, the loop can still idle. Can only validate explicit signals, not real learning density. | Low to medium | Adopt now, but not alone. Best used as a guard layer around option 5. |
| 3. Lease / watchdog model | Introduces external liveness ownership. A TTL + heartbeat can mark abandoned work, detect stuck waits, and trigger reroute or takeover without user intervention. Good fit for long-running live branches. | Heartbeats can be healthy while work is low-value. Bad TTLs cause false expiry during long tool calls. Needs atomic lease renewal and split-brain prevention. | Medium | Adopt after the executor path is in place. High value for the live mousepad-loop once state transitions are executable. |
| 4. Small control-loop daemon or queue | Strongest true no-user-dependency model. A dedicated control process can schedule roles, retry, back off, and dispatch next actions even when no interactive session is active. Natural place for watchdogs and concurrency limits. | Highest engineering and ops overhead. Adds another critical runtime to debug. Risks hardening the wrong state model too early. | High | Later. Only worth it after the transition rules are stable and multiple unattended loops justify it. |
| 5. Resumable transition executor | Converts "what happens next" from prose into code. Can inspect manifest, ledger, verdicts, and runtime handles, then apply exactly one valid transition atomically and idempotently. Fits the existing artifact-driven harness with minimal conceptual churn. | Does not self-trigger by itself. If transition predicates are weak, it can still advance on shallow signals. Needs lock/version discipline for atomic writes. | Medium | Top recommendation now. Pair immediately with option 2; pair later with option 3. |

## Decision

Adopt **option 5 as the core mechanism now**, with an **option 2 validator/checker built into the same control surface**.

Reason:

- The current weakness is not lack of recorded state; it is lack of executable transition ownership.
- Option 5 preserves the existing manifest/ledger/reviewer-verdict design instead of replacing it.
- It turns anti-idle from "follow the protocol" into "run the transition engine."
- It creates the right attachment point for later watchdoging without forcing a daemon rewrite first.

## Recommended rollout

### Adopt now

Implement a small resumable transition executor that:

- reads `manifest.yaml`, `run-ledger.jsonl`, and the current round artifacts
- validates allowed transition preconditions before advancing
- writes manifest + ledger updates atomically
- is idempotent when re-run after partial failure
- emits the next required action as a concrete packet, not a narrative instruction

Add a validator/checker in the same phase that:

- rejects illegal state transitions
- rejects missing or malformed structured verdicts
- flags stale states by age
- flags manifest/ledger disagreement before any new action starts

### Adopt next

Add a lease/watchdog layer for long-running coordinator or reviewer jobs:

- lease owner = active role/session
- lease TTL tied to observed runtime state
- watchdog checks both runtime state and transition age
- watchdog invokes the transition executor on completion, expiry, or invalid pending state

This is the first step that materially reduces dependence on a foreground orchestrator staying attentive.

### Defer

Defer the full daemon/queue model until at least one of these is true:

- more than one unattended loop must run concurrently
- retries/backoff/scheduling logic becomes substantial
- watchdog + executor polling overhead becomes operationally messy

Building the daemon before the executor would harden policy prose into infrastructure too early.

## Bottom line

- **Not enough:** option 1
- **Useful guard layer:** option 2
- **Best immediate structural upgrade:** option 5
- **Best next anti-idle hardening:** option 3
- **Best eventual autonomy model:** option 4
