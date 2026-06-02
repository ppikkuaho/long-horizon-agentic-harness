# Orchestration Framework Research

Cross-task learnings from running self-improvement loops. This folder is the cumulative knowledge base — what we know about how orchestration works, what makes delegations produce good or bad coordinators, and where the framework fails.

A fresh session doing framework improvement work reads this folder. A fresh session running a specific task loop reads `harness/` for tooling and creates under `instances/` for its run data.

## What's here

### Primary artifacts

- `methodology-log.md` — the main cumulative learning artifact. 25+ durable lessons covering delegation design, evidence discipline, observation methodology, control-plane design, reviewer architecture, and meta-improvement methodology. **Read fully before any framework work.** The last entries capture the most important lessons from the most recent sessions.

- `ARCHITECTURE-FINDINGS.md` — structured findings ledger with status/implementation tracking. 18+ findings across runtime, observability, control-plane, loop-design, delegation-prompt, and artifact-design buckets. Each finding has evidence, risk, candidate improvement, status, and cross-task durability judgment.

- `synthesis.md` — Run 1 iteration synthesis: top-5 high-leverage iterations ranked with rationale and promotion plan.

### Design proposals and analyses

- `rubric-v2-proposal.md` — proposed multi-level rubric with Section S (subagent-level checks) + P1 precondition. Not yet integrated into the rubric.
- `run-01-multi-level-analysis.md` — first multi-level observation data: what subagent traces look like, instrument asymmetry between coordinator and subagent layers.
- `watchdog-design-01.md` — watchdog/lease design exploration.
- `structural-options-review-01.md` — structural prevention options review.
- `untested-failure-modes-review-01.md` — catalog of untested failure modes in the harness.
- `resilience-options-review-02.md` — resilience and recovery design options.
- `EXPANSION-BRANCHES.md` — success-path widening branches and comparative analysis plans.

## Relationship to other folders

- `../harness/` — reusable loop tooling. Research findings feed into harness improvements.
- `../instances/` — specific task runs. Instances produce evidence that feeds into research.
- `../../frame.md`, `../../frame-design-notes.md`, `../../prompt-craft.md`, `../../process-observation-rubric.md` — the framework itself. Research findings may propose changes to these; changes require MD approval.
