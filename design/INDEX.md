# L1-L5 Harness — Active Doc Index

**This is the build doc set.** Point the build (and any agent) at the files listed here as ACTIVE. Anything not listed is historical — see the archive locations at the bottom. Supersedes the stale `DOCUMENT-HIERARCHY.md`.

## Canon-precedence
1. The **LIVE decision notes** (`working-notes/runtime-decisions-and-commissioning-2026-06-04.md`, `working-notes/arch-gap-review-2026-06-04.md`) are SOURCE OF TRUTH for the runtime / liveness / transport / scale model and **OVERRIDE the specs below where they conflict**.
2. The design specs below are canonical for the semantics they cover. **Several still carry drift pending Phase-0 reconciliation** (see `working-notes/path-to-ready-2026-06-04.md`) — until reconciled, the live notes win.
3. `NOTES.md` is an IDEAS LOG, not spec — read last.

## Builder reading order
1. `working-notes/runtime-decisions-and-commissioning-2026-06-04.md`
2. `working-notes/arch-gap-review-2026-06-04.md`
3. `working-notes/path-to-ready-2026-06-04.md`
4. `ARCHITECTURE.md` (semantic spine — post-reconciliation)
5. cluster docs: `OBSERVABILITY` / `COMMUNICATION` / `QUALITY-GATE` / `WORKSPACE-SCHEMA` / `PLAN-ALIGNMENT-GATE` / `DECOMPOSITION-METHODOLOGY`
6. `operational/` (the agent-facing runtime docs)

## ACTIVE — design specs (`design/`)
`ARCHITECTURE`, `DESIGN-PRINCIPLES`, `DECOMPOSITION-METHODOLOGY`, `COMMUNICATION`, `OBSERVABILITY`, `WORKSPACE-SCHEMA`, `PLAN-ALIGNMENT-GATE`, `PROJECT-PLANNING`, `QUALITY-GATE`, `IMPROVEMENT-WORKSPACE`, `VISION`. (`NOTES.md` = idea-log.)
**Reconciliation status: pending Phase 0** (the live notes override on conflict).

## ACTIVE — agent-facing runtime docs (`operational/`) — what spawned agents actually load
`operational/L1..L5/{role,config,soul,spawn-template}.md` (+ L1 handbook/intake/skills, L3 planning-template, L5 swe-handbook) and `operational/shared/{agent-lifecycle, comms-protocol, git-protocol, runtime-and-model-map, agent-definition-principles, intent-spec-contract, user-profile-schema}.md`.
The **runtime workspace folder structure** agents create/work in is defined by `WORKSPACE-SCHEMA.md`.

## Build substrate (`research/` — SUSPECT: adapt, don't trust)
Clusters ①②: `research/orchestration-frame/self-improvement-harness/{control_plane.py, watchdog.py, test_watchdog.py, CONTROL-PLANE.md, WATCHDOG.md}`; `research/orchestration-frame/phase-2-runs/research/{watchdog-design-01.md, ARCHITECTURE-FINDINGS.md}`.

## Pending supersede-decision (Phase 0)
- `GIT-INTEGRATION.md` — built on the dissolved review-dept + old L3/L4 roles → rewrite or fold into `shared/git-protocol.md`.
- `ROADMAP.md` — annotate superseded entries (Review Dept, Program Manager, Active/Parked, Internal Affairs).
- `DOCUMENT-HIERARCHY.md` — stale nav map → superseded by this INDEX.
- `PROJECT-GUIDE.md` — stale 4-level model → reconcile to 5 levels + L5+.

## Archives
- `design/working-notes/archive/` — stale notes (see `working-notes/INDEX.md`).
- Substrate prune record: `MOVE-MANIFEST.md`, `manifest.json`.
- Suspect prior art to mine: `PRIOR-ART-SUSPECT.md`. Pinned CC substrate: `PINNED-CC.md`. H40 research task: `H40-RESEARCH-TASK.md`.
