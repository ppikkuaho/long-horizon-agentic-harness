# Compute Saturation Policy 01

This policy applies to the manager/orchestrator role. It is a structural policy, not a reminder policy: if a rule cannot be represented in manifest state, ledger events, branch packets, or watchdog state, it does not count as load-bearing.

## Operating definition

- `primary actor` means the current coordinator, builder, or other top-level work owner.
- `side-work` means a parallel branch that advances a distinct evidence surface, not a duplicate of the primary path.
- `saturated` means the orchestrator has assigned all reachable independent work surfaces to live branches or has explicitly marked why a surface cannot be branched.
- Duplicate branches on the same surface do not count toward saturation unless one is intentionally a shadow review or clean-room comparison.

## Saturation targets

- Minimum target: 2 active streams whenever a primary actor is live and there is at least one independent side question available.
- Preferred target: 3 active streams during any wait, convergence window, or review gate. The default mix is 1 primary stream, 1 widening or orthogonal branch, and 1 verification or shadow-review branch.
- Upper bound for a single round: 4 concurrent streams. Beyond that, the manager should either split the work into a new round or collapse redundant branches.
- Saturation is counted only when each stream has its own objective, owner, stop condition, and artifact path in the manifest or ledger.

## Minimum parallel side-work expectation

- If the primary actor is actively computing and not waiting, open 1 orthogonal side branch as soon as the first independent subquestion exists.
- If the primary actor is waiting on a child, fetch, reviewer, or long synthesis step, open 2 side branches.
- If the primary path has already produced a strong candidate, the side work must be a widening branch or a shadow-review branch, not another refinement of the same candidate.
- If no valid side-work exists, the orchestrator must record that fact in the manifest and ledger. It may not represent silence as progress.

## Automatic branch-open rules

- Open a widening branch at the first apparent convergence signal, not after the round is already being treated as done.
- Open a shadow-review branch if Reviewer 2 is trending toward stop authority before the architecture has been pressure-tested by an alternate packet or evidence surface.
- Open a clean-room branch when role contamination, read-surface leakage, or artifact-boundary leakage is suspected.
- Open a reroute branch on the first dead candidate. The reroute must change the search surface or decomposition, not just the wording.
- Open a diversification branch when 30 minutes pass with no new cross-task signal, evidence class, or path choice.
- Open a trace-audit branch whenever a prose summary claims parallelism or completion that is not yet confirmed by tool-level trace.

## Catastrophic idle signals

- A live primary actor has no active side branch for more than 5 minutes while more work is available.
- Heartbeat remains healthy but no semantic event and no artifact delta appear for two checkpoints or roughly 10 minutes.
- `stale_suspect` repeats without a recovery decision.
- The manifest says work is live but the next-action surface is blank or unchanged.
- A round is waiting on the user without an extraordinary-condition trigger.
- The orchestrator counts claimed parallel work that is not actually present in the trace.

## Catastrophic underutilization signals

- Fewer than 2 active streams exist while at least 2 independent unresolved surfaces remain.
- A primary actor spends multiple checkpoints on one surface while orthogonal verification surfaces remain unopened.
- The same candidate family is being refined in place after a convergence signal instead of being widened or challenged.
- The orchestration layer sequentializes work that could have been branched without added coordination risk.
- Side branches exist, but they are redundant in evidence, role, and stop condition.

## Structural remedies

- Claim the next spawn slot in the control plane before launching a branch; never spawn first and validate later.
- Materialize every branch in the manifest and ledger before work begins.
- Attach a branch packet to every side branch with role, objective, read surface, write target, and stop authority.
- Treat heartbeat as liveness only; require trace plus artifact delta before counting work as progressing.
- Use `healthy`, `stale_suspect`, `recovery_in_progress`, and `failed_confirmed` as explicit control-plane states for stalled or degraded work.
- Use `stale_suspect` and recovery states for silent waits; do not hide silence inside prose.
- Keep Reviewer 1 for adherence, Reviewer 2 for quality, and Reviewer 3 for task finish; do not collapse stop authority into the manager.
- Use the first convergence signal to widen, not to conclude.
- Use orthogonal branch types: shadow review, clean-room contamination test, dead-candidate reroute, or alternate decomposition. Do not count a second copy of the same path as saturation.
- If a branch is done but the top-level decision is not committed, the program remains live.

## Enforcement rule

- The orchestrator must satisfy this policy through state changes, spawn packets, and control-plane checks.
- If the only defense is a prompt reminder, the defense is too weak and the branch remains underutilized.
