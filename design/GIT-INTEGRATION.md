# AI Architecture — Git Integration (Process Design)

> **SUPERSEDED — historical.** This document predates the 5-level model and the dissolution of the "Review Department." Two things drifted and are now wrong here:
> 1. **Review is a per-level *function*, not a department.** There is no standing review-department/coordinator that owns the merge. Review is an independent `#review` seat co-located at each node (per-unit L5+ review + whole-set L4-level review), structurally separate from the producer. Code review is **L5-class work integrated at each level**, not a separate org-unit.
> 2. **The level/branch roles below are stale.** The current model is five levels (System Orchestrator L1, Project Architect L2, Module Designer L3, Workstream Coordinator L4, Task Executor L5) + the L5+ reviewer. The branch spine is **task = L5, workstream = L4, area merge-gate = L3, trunk = project** — not the L3/L4 mapping used below.
>
> **The valid, current git mechanics live in `operational/shared/git-protocol.md`** (branch spine, merge topology, conflict protocol, commit format). Reconcile any conflict TO that document and to `QUALITY-GATE.md`. The sections below are retained for history; read them through this banner.

Level 4 process design document. Defines how git maps onto the approval hierarchy: branch strategy, merge flow, quality gate at merge points. Constrained by: `ARCHITECTURE.md`, `DESIGN-PRINCIPLES.md`, and the Quality Gate design (`QUALITY-GATE.md`).

---

## Core Insight

Git maps naturally onto the approval hierarchy — branch/PR/merge IS the review mechanism. The version control workflow and the organizational approval workflow are the same structure, not parallel systems that need synchronization.

## Branch Strategy

- **Task branches** — L4 works on task branches. L3 reviews and merges them into the workstream branch.
- **Workstream branches** — L3 owns these. Reviewed and merged by L2 into main.
- **Main** — source of truth. Only receives merges that have cleared the L2 gate.

## PR as Vehicle for the Per-Level Review Function

The diff shows what was done. The PR is the mechanism through which the quality gate (the per-level review function) operates — the review function opens the PR, spawns dimension-specific reviewers against it, and manages it through to merge or rejection. The producing seat doesn't review its own PR; the independent `#review` seat does.

PR descriptions reference `report.md` by path for the producer's account of the work, and carry the gate's reviewer reports and merge decision.

## Code Review as Execution-Level Work

Reviewing code is L5-class cognitive work — reading implementation, evaluating against a specific dimension, producing a judgment. It is **integrated at each level as a function**, not handed to a separate department. The producing seat does not review itself; an independent `#review` seat (clean context, judged at altitude) does the actual evaluation, and the review function synthesizes the reports into a merge decision. Producing and reviewing are separate seats, not separate org-units.

## Link, Don't Copy for Git Context

PR descriptions should reference workspace artifacts by path (`L4/{workstream}/{task}/report.md`, `L2/decisions/003_api-design.md`), not duplicate their content. Same principle as inbox messages — single source of truth, no divergent copies. The PR carries the gate's synthesis and verdict; the supporting evidence lives in the workspace files it points to.

## Concurrency and Conflict Resolution

- **File locking replaced by git merge** — concurrent edits handled through merge. Conflicts surface problems explicitly rather than silently overwriting.
- **Merge conflict protocol** — conflicts are resolved by the level that owns the branch:
  - L4 resolves conflicts on its task branch (typically against the workstream branch it will merge into).
  - L3 resolves conflicts on the workstream branch (e.g., when merging multiple L4 task branches that touch overlapping files).
  - Cross-workstream conflicts — where two L3 workstream branches conflict on merge to main — are escalated to L2, which has the architectural context to decide which approach wins.

## Integrity Properties

- **Immutability enforcement** — git tracks edits to decision records. Silent modifications are visible in history.
- **Append-only verification** — log diffs show only additions. Easy to verify no old entries were edited.

## What Stays Outside Git

Status board and inbox (infrastructure, high-frequency updates) probably don't belong in git.

## Agent Git Instructions

Branch naming conventions, commit message format, when to push — included in spawn config.

## Quality Gate Integration

The per-level review function sits at merge points:

- **L3 gate** — L4 task branches are reviewed before merging into the workstream branch.
- **L2 gate** — workstream branches are reviewed before merging into main.

No seat reviews its own code — review is an independent per-level function, structurally separate from the producer. Each reviewer evaluates one dimension on right-sized code units (principle 17). PR descriptions carry the reviewer reports, not the raw diff assessment by the producing level.

## End-to-End Merge Flow

1. L4 works on a task branch, commits as it goes.
2. L4 finishes, writes `report.md`, reports completion to L3.
3. L3's quality gate activates — the gate coordinator opens a PR from the task branch to the workstream branch, spawns dimension-specific L4-class reviewers against it.
4. Gate clears → gate coordinator merges the task branch into the workstream branch. Gate rejects → producing L4 receives specific issues, iterates on the task branch.
5. When the workstream is complete, L2's quality gate activates — the gate coordinator opens a PR from the workstream branch to main, spawns integration-level reviewers.
6. Gate clears → gate coordinator merges the workstream branch into main.

The review function — not the producing seat — opens and manages the PR. The producing seat's job ends at reporting completion. From that point, the independent per-level review function owns the merge process.

## Design Advantages

Adds robustness and reduces fragility with minimal overhead. LLMs already handle git well.

---

*Created: 2026-03-17*
*Status: Design-in-progress. Extracted from NOTES.md into standalone process design document.*
