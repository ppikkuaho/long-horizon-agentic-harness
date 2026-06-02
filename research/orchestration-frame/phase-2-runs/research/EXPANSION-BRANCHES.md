# Mousepad Loop — Expansion Branches

This file tracks deliberate side branches opened to avoid overfitting to a single successful path.

## Rule

Open a branch when:

- the live task is temporarily waiting and can be observed without active intervention
- the first working path may be creating false confidence
- a side branch can surface architecture findings without contaminating the main live round

## Active branches

### B-001 — Untested failure modes review

- Opened: 2026-04-12 02:12 +0300
- Purpose: identify architecture weaknesses still untested by the current mousepad run and propose the next widening interventions
- Trigger: explicit anti-Einstellung instruction from MD plus the early signal density from Round 1
- Status: completed
- Expected artifact: a short note listing the top remaining untested failure modes and highest-leverage intervention branches
- Output artifact: `untested-failure-modes-review-01.md`
- Main findings imported: reviewer-stop-authority still unvalidated, success-path widening untested, dead-candidate reroute untested, clean-room behavior untested, learning-density checks still manual

### B-002 — Reviewer-independence shadow branch

- Opened: 2026-04-12 02:25 +0300
- Purpose: if Round 1 appears to converge quickly, stress the reviewer architecture rather than trusting the canonical reviewer chain alone
- Trigger: B-001 finding F-005 plus the possibility that Superglide V2 clears Reviewer 3 early
- Status: planned
- Planned shape: run the canonical reviewer chain first, then add one shadow reviewer branch with stricter evidence isolation or alternate packet structure if the main path trends toward early convergence

### B-003 — Clean-room contamination test branch

- Opened: 2026-04-12 02:25 +0300
- Purpose: test whether excluding loop-runner state artifacts materially changes coordinator or reviewer behavior
- Trigger: observed leakage from `iteration-log.md` and `dead-candidates.md` into the coordinator's read surface
- Status: planned
- Planned shape: next suitable branch should either relocate runner-state artifacts or explicitly exclude them from the child-readable surface, then compare output shape and confidence against the current contaminated branch

### B-004 — Dead-candidate reroute menu precommit

- Opened: 2026-04-12 02:25 +0300
- Purpose: avoid improvising the first rejection response under pressure
- Trigger: B-001 finding F-007
- Status: planned
- Planned shape: predeclare 2-3 orthogonal reroute modes for the first dead-candidate event, so the next coordinator spawn is materially different rather than a local repair

### B-005 — Lease/watchdog hardening

- Opened: 2026-04-12 02:28 +0300
- Purpose: add a structural stale-state recovery layer on top of the manifest/ledger/executor control plane
- Trigger: structural-options-review-01 top recommendation sequence
- Status: in progress
- Output artifact: `watchdog-design-01.md`
- Current shape: added a watchdog block plus `watchdog-checkpoint` and `probe-active` commands to the mousepad-loop control plane; next step is to exercise `stale_suspect` and recovery behavior on a genuinely degraded or ambiguous live run

### B-006 — Resilient control-surface options review

- Opened: 2026-04-12 02:47 +0300
- Purpose: compare stronger structural options beyond the current probe/checkpoint layer so the loop does not harden prematurely around one local fix
- Trigger: live Reviewer 2 run still needs observation, and the architecture now has enough concrete evidence to compare next-step resilience options
- Status: completed
- Output artifact: `resilience-options-review-02.md`
- Main findings imported: probe-driven durable observation is the right immediate layer; strongest next candidates are an external poller, backend semantic taps, and a durable parent-child mailbox rather than more prompt text
