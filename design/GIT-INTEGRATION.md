# AI Architecture — Git Integration (Process Design)

Level 4 process design document. Defines how git maps onto the approval hierarchy: branch strategy, merge flow, quality gate at merge points. Constrained by: `ARCHITECTURE.md`, `DESIGN-PRINCIPLES.md`, and the Quality Gate design (`QUALITY-GATE.md`).

---

## Core Insight

Git maps naturally onto the approval hierarchy — branch/PR/merge IS the review mechanism. The version control workflow and the organizational approval workflow are the same structure, not parallel systems that need synchronization.

## Branch Strategy

- **Task branches** — L4 works on task branches. L3 reviews and merges them into the workstream branch.
- **Workstream branches** — L3 owns these. Reviewed and merged by L2 into main.
- **Main** — source of truth. Only receives merges that have cleared the L2 gate.

## PR as Vehicle for the Review Department

The diff shows what was done. The PR is the mechanism through which the quality gate (review department) operates — the gate coordinator opens the PR, spawns dimension-specific reviewers against it, and manages it through to merge or rejection. The producing level doesn't review its own PR; the review department does.

PR descriptions reference `report.md` by path for the producer's account of the work, and carry the gate's reviewer reports and merge decision.

## Code Review as Execution-Level Work

Reviewing code is L4-class cognitive work — reading implementation, evaluating against a specific dimension, producing a judgment. This is why review is not L3's job. L3 manages the workstream; the review department spawns L4-class reviewer agents who do the actual evaluation. The gate coordinator synthesizes their reports into a merge decision. Management and evaluation are separate functions.

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

The review department sits at merge points:

- **L3 gate** — L4 task branches are reviewed before merging into the workstream branch.
- **L2 gate** — workstream branches are reviewed before merging into main.

No level reviews its own code — review is a separate department function. Each reviewer evaluates one dimension on right-sized code units (principle 17). PR descriptions carry the reviewer reports, not the raw diff assessment by the producing level.

## End-to-End Merge Flow

1. L4 works on a task branch, commits as it goes.
2. L4 finishes, writes `report.md`, reports completion to L3.
3. L3's quality gate activates — the gate coordinator opens a PR from the task branch to the workstream branch, spawns dimension-specific L4-class reviewers against it.
4. Gate clears → gate coordinator merges the task branch into the workstream branch. Gate rejects → producing L4 receives specific issues, iterates on the task branch.
5. When the workstream is complete, L2's quality gate activates — the gate coordinator opens a PR from the workstream branch to main, spawns integration-level reviewers.
6. Gate clears → gate coordinator merges the workstream branch into main.

The gate coordinator — not the producing level — opens and manages the PR. The producing level's job ends at reporting completion. From that point, the review department owns the merge process.

## Design Advantages

Adds robustness and reduces fragility with minimal overhead. LLMs already handle git well.

---

*Created: 2026-03-17*
*Status: Design-in-progress. Extracted from NOTES.md into standalone process design document.*
