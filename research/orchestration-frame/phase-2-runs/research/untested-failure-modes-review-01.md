# Untested Failure Modes Review 01

Current evidence is still mostly a single live coordinator run. That is enough to expose some real weaknesses, but not enough to validate the loop architecture. The highest-risk remaining gaps are the ones where the design is specified in `HANDOFF.md` / `PROGRAM.md` but has not yet been forced through evidence.

## Top untested failure modes

### 1. Reviewer stop-authority may be nominal rather than real

Why it matters:
- The program's stop authority has been moved out of the loop runner and into Reviewer 2 plus Reviewer 3, but none of those reviewer packets has been exercised yet.
- If reviewer independence is weak, the system can produce false convergence: a deliverable can look "done" because the reviewers inherit the same framing, omissions, or meta-context rather than independently pressure-testing it.
- This is the most dangerous untested gap because the whole anti-completion-bias design depends on it.

Best next branch:
- After the first coordinator return, run the canonical reviewer chain, but also open one shadow review branch designed to test independence rather than task quality.
- Highest-leverage variant: keep Reviewer 3 fully blind and run an additional shadow Reviewer 3 or alternate-packet Reviewer 2 with stricter evidence isolation; compare whether the verdict meaningfully diverges.
- If the shadow branch diverges, treat reviewer architecture as not yet validated even if the main chain appears converged.

### 2. Early-success widening is defined in principle but untested in operation

Why it matters:
- `PROGRAM.md` explicitly says that fast convergence is a signal to widen the work, not stop early.
- The current live path is already at risk of converging on a strong candidate from an extend-from-Run-1 track before the harness has been forced through enough structural strain.
- Without an exercised widening branch on the success path, the program can mistake "one good narrow path" for architectural robustness.

Best next branch:
- If Round 1 reaches apparent convergence early, force at least one additional coordinator branch before treating the program as structurally persuasive.
- Highest-leverage variant: run an opposing decomposition branch on the same task, such as `build fresh` against the current `extend-with-targeted-expansion` path, or an alternate reviewer packet / review order branch with a stricter evidence surface.
- Require a comparative memo on what changed, not just a second answer.

### 3. Dead-candidate recovery logic is still only specified on paper

Why it matters:
- The handoff says dead candidates must trigger a new coordinator run with different conditions, but no dead-candidate cycle has happened yet.
- This means the program has not shown that it can actually escape a rejected top candidate instead of doing local prompt edits that preserve the same search surface.
- If Reviewer 3 rejects the current best candidate, the loop could easily become a disguised repetition machine.

Best next branch:
- When the first dead candidate happens, require a materially different reroute rather than incremental repair.
- Highest-leverage variant: use a predeclared reroute menu with orthogonal changes, for example fresh rebuild vs extension, different decomposition shape, or different source/evidence surface.
- Judge the next round on whether it explores a genuinely different branch, not just whether it produces a revised shortlist.

### 4. Artifact-boundary leakage is observed, but clean-room behavior is untested

Why it matters:
- The coordinator already read loop-runner state artifacts (`iteration-log.md`, `dead-candidates.md`) that were not meant to be part of its work input.
- That creates a real risk of role contamination: the coordinator or later reviewers can optimize toward loop meta-state, reviewer expectations, or apparent program goals rather than the task packet they were supposed to handle.
- A contaminated loop can look disciplined while actually becoming performative.

Best next branch:
- Run at least one clean-room coordinator or reviewer branch with loop-runner state explicitly excluded from the readable surface.
- Highest-leverage variant: compare the current branch against a sibling branch with `_runner-state` isolation or explicit exclusions in the delegation packet.
- If output shape or confidence changes materially, artifact design becomes a priority harness fix.

### 5. The observation stack can detect liveness, but not whether the run is learning enough

Why it matters:
- Current observation has already shown the health-vs-semantic-state split and execution-summary drift, but it still relies on manual trace inspection to notice that the run may be narrow, repetitive, or low-yield.
- A loop can remain healthy, busy, and even reviewer-passing while generating too little architecture signal per hour.
- This matters most on the success path, where "everything looks fine" is exactly when under-testing is easiest to miss.

Best next branch:
- At the first sign of convergence, spawn a side review focused only on untested failure modes and missing branches.
- Highest-leverage variant: make this a standing diversification checkpoint artifact, not an ad hoc reflection.
- The branch should answer whether the program has tested enough distinct failure surfaces to justify moving on.

## Recommended next interventions

1. Test reviewer independence before trusting any early convergence signal.
2. Force a success-path widening branch if Round 1 appears to converge quickly.
3. Precommit the first dead-candidate reroute to an orthogonal branch, not an in-place refinement.
4. Run one clean-room branch to test artifact-boundary contamination.

The live run is evidence that the loop can operate. It is not yet evidence that the loop is robust.
