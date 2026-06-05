# Git Protocol — Operational Reference

How agents use git. Loaded at boot for levels that produce code (L4, L5, and sometimes L3).

Git is one of the strands of the **single hierarchical-path spine**: requirement-IDs, agent-addresses, workspace-paths, git-branches, rubric-file locations, and the visibility graph are all the same dotted/path scheme. A branch name *is* a workspace path *is* an address. See `WORKSPACE-SCHEMA.md` (the tree), `runtime-and-model-map.md` (F35 addressing), and `COMMUNICATION.md` (the visibility graph).

---

## Branch Strategy

The branch structure mirrors the management hierarchy and is **isomorphic to the workspace path / station address (F35)**. A branch name is a node path with no level numbers in it — semantic segments only (area names, not `L3.1`):

- **Task branch** — L5 works here. The leaf. Path: `proj/{area}/{workstream}/{task}` (e.g. `proj/payments/gateway/stripe-client`).
- **Workstream branch** — L4 owns this. Path: `proj/{area}/{workstream}` (e.g. `proj/payments/gateway`).
- **Area branch** — L3 owns this; it is the **merge gate** into project trunk. Path: `proj/{area}` (e.g. `proj/payments`).
- **Main / trunk** — `proj` — project source of truth. Only receives merges that have cleared the area-level review gate.

So the mapping is: **task = L5, workstream = L4, area merge-gate = L3, trunk = the project.** A child branch is its parent branch dotted with one more semantic segment, exactly as a child workspace path is its parent path plus a segment and a child requirement-ID is its parent ID plus a local index. Truncate the last segment and you have the parent branch / parent address / parent node. This isomorphism is not cosmetic — it is what lets the visibility graph, the RTM trace, and the merge topology all derive from one scheme decided once.

**Substrate first.** The substrate (Money, IDs, events, audit, the idempotency primitive, the base data model — B14) is built before the feature areas, on its own area branch under `proj/substrate`, via the walking-skeleton spike. Feature-area branches fork *after* the substrate has merged to trunk, so every area builds on the stable core rather than racing it.

**Stations and branches are the same node.** A role-variant suffix (`#exec`, `#review`) addresses *who is acting on* a node, not a separate branch — the executor seat and the review seat both operate against the same task/workstream/area branch. The branch carries the code; the `#`-suffix carries the seat (see `runtime-and-model-map.md`).

## How You Work With Git

**L5 (Task Executor) — executor seat (`…#exec`):**
- Work on your task branch (`proj/{area}/{workstream}/{task}`).
- Commit frequently as you go — small, meaningful commits.
- Run the pre-written acceptance tests (the frozen `acceptance.md` rubric in your work node — read-only to you, D26), your own unit tests, and **CI — the automated floor — before reporting** (D28). A red CI floor means the task is not done; do not report green.
- When the task is complete, write `report.md` and signal L4 over the bus. You do **not** open PRs or merge, and you do **not** review your own work — the review path handles that (D23: the producing seat never signs off on itself).

**L5+ (review seat, `…#review`) — code review is L5-class work:**
- A *separate* agent (different seat, ideally a different runtime/model for judgment diversity — Opus for the review read; see `runtime-and-model-map.md`) does its own testing and reviews the L5 code **against the frozen `acceptance.md` and the spec** — never against the code-as-written.
- Review is **at altitude** (D24): judge fidelity to spec and the quality of *this* unit's composition; do not re-derive or re-decide the level below.
- **Accept** → the work is forwarded for merge and both L5 seats collapse. **Bounce** → typed, neutral findings return to L5, which keeps its context and continues. The bounce loop is **bounded** (loop-cap N; persistent failure escalates, it does not spin).

**L4 (Workstream Coordinator):**
- Create task branches for L5s at spawn (fork from the workstream branch).
- L4 (or its L4-tester lateral) authored the frozen `acceptance.md` for each task at planning time, *before* L5 coded — tester ≠ producer (D26 / anti-theater temporal rule).
- After a task clears L5+ review, route it through the **independent review gate** (below) and, on PASS, merge the task branch into the workstream branch.
- When the workstream is complete, signal L3.

**L3 (Module Designer) — owns the area merge gate:**
- Create workstream branches for L4s at spawn (fork from the area branch).
- After a workstream clears review, route it through the area-level independent review gate and merge the workstream branch into the area branch.
- The **area branch → trunk merge is the project's hard gate**: an area merges to `proj` only after the area-level independent review signs off. L3 resolves cross-workstream merge conflicts; cross-area conflicts escalate to L2.

## Independent Review Is the Default Merge Path (V1)

Independent review at each level is **in for V1** (D30) — it is the *normal* merge path at every level boundary, not a post-V1 toggle. There is no "direct merge" mode that bypasses it.

- Review is a **per-level function, not a standing coordinator parallel to the level**: an independent `#review` seat co-located at each node (P4: independent of the producing hierarchy), spun up against the same branch the producer acts on. Code review at each boundary is **L5-class work** — independent reviewer seats, clean context, judging at altitude (D23/D24). See `QUALITY-GATE.md` for the dimension presets and the per-level gate mechanics.
- **CI is the automated floor *beneath* the independent review function, not a substitute for it** (D28). CI must be green before a unit is eligible to enter the gate; the independent reviewer then does the judgment work CI cannot (architectural fit, interface-contract fidelity, drift against spec). Green CI alone never authorizes a merge.
- The two review surfaces are distinct and both run in V1: **CI floor** (automated, deterministic, per-commit) and the **independent review gate** (judgment, at the level boundary, before merge).

This is the merge topology, end to end:

> L5 commits → CI floor green + L5+ accept → L4 routes task through review gate → merge to workstream branch → workstream review gate → merge to area branch → **area review gate → merge to trunk.**

The plan-alignment gate (`PLAN-ALIGNMENT-GATE.md`) is a *different* checkpoint — it sits once, between the design cycle and the build cycle, and authorizes construction at all. These per-boundary merge gates run *during* the build cycle, on code. Do not conflate them.

## Commit Messages

```
[{node-path}] {what was done}

{why, if not obvious from the what}

Seat: {address}#{exec|review}   e.g. proj/payments/gateway/stripe-client#exec
Serves: {requirement-ID(s)}     e.g. R-003.2.1
```

Keep the first line under 72 characters. The body is optional but useful for decisions or non-obvious changes. `{node-path}` is the branch/address; the `Serves:` line feeds the RTM trace (`PLAN-ALIGNMENT-GATE.md`) — a commit names the requirement ID(s) it advances so code is traceable to intent.

## Merge Conflict Protocol

Conflicts are resolved by the level that owns the **target** branch — i.e. the parent node, since the target branch is always the conflict point's parent path:

- **L5** resolves conflicts on its task branch (against the workstream branch it will merge into).
- **L4** resolves conflicts on the workstream branch (when merging multiple L5 task branches that touch overlapping files).
- **L3** resolves cross-workstream conflicts — two workstream branches conflicting on merge to the area branch. L3 has the area context to decide which approach wins. If the conflict touches another area's work, escalate to L2.

The owner of the target path owns the conflict, at every level — same rule as the visibility graph (a node sees its subtree, siblings, and parent; conflicts live at the parent).

## What Stays Outside Git

- `status.md` — high-frequency updates, not versioned.
- **bus traffic** — real-time transport (nudges, signals, completion pings) is ephemeral and not in git; **the durable truth lives in the versioned docs the bus messages point at** (F33). A message is a pointer/nudge, best-effort by design, because the truth is in the docs.
- `status/` board — infrastructure-managed.
- `scratch/` folders — temporary work, cleaned on completion.

Everything else — code, designs, plans, briefs, the frozen `acceptance.md` rubrics, reports, decisions (ADRs), conventions — lives in git.

## Link, Don't Copy in Merge Requests

A merge request references workspace artifacts by their node path — `proj/payments/gateway/stripe-client/report.md`, `proj/payments/gateway/stripe-client/acceptance.md`, `proj/decisions/003_api-design.md` — it does not duplicate their content. Same principle as bus messages: the request carries the verdict and synthesis; the supporting evidence lives in the versioned files it points to. Because the branch path *is* the node path, the link and the branch are the same address.

## Integrity Properties

Git provides integrity guarantees the system relies on — and which underpin the audit/optimizer-L1 substrate:

- **Decision-record (ADR) immutability** — git history shows if a decision record or a frozen `acceptance.md` was modified after creation. The D26 read-only-to-the-executor property is enforced *physically* here: a diff to a frozen rubric is visible and is itself a defect.
- **Append-only verification** — `log.md` diffs should show only additions. Easy to verify no old entries were changed.
- **Traceability** — commits carry the seat address and the `Serves:` requirement-ID(s), connecting every code change to the agent that made it and the intent it advances.

## End-to-End Flow

1. L5 (`…#exec`) works on the task branch, commits as it goes.
2. L5 runs frozen acceptance tests + unit tests + **CI floor**; only on green does it write `report.md` and signal L4 over the bus.
3. L5+ (`…#review`) independently tests and reviews against `acceptance.md` + spec → **accept** (forward; both L5 seats collapse) or **bounce** (bounded loop; L5 keeps context).
4. L4 routes the accepted task through the **independent review gate** → on PASS, merges the task branch into the workstream branch.
5. Repeat for all tasks; L4 signals L3.
6. L3 routes the workstream through the review gate → merges into the area branch.
7. The **area branch clears the area-level review gate → merges into trunk (`proj`).** Repeat per area; cross-area conflicts escalate to L2.

The independent review function is on the path at steps 3–7 by default — it is how merges happen in V1, not an optional add-on.

---

*Operational reference — loaded at boot for code-producing levels.*
*Created: 2026-03-29 · Updated: 2026-06-02 (5-level branch spine; F35 branch/station isomorphism; CI floor D28; code-review-as-L5-class D23/D24; independent review default merge path D30; frozen acceptance.md D26; bus+docs).*
