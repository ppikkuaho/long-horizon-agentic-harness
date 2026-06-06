# Working Notes — Index

> **▶ RESUMING A COMPACTED SESSION? START AT [`BRIDGE-2026-06-06b.md`](BRIDGE-2026-06-06b.md)** — the CURRENT bridge: Phase-5 substrate DONE + OAuth/jail/deterministic-trust built; now in **Phase 6 behavioural validation** (the eval instrument + per-level results: L1✓ L2✓(find→fix→verify loop) L3✓ L4 in-flight L5/L5+ ready), the user directives (no-dummies, check-L5+, the full review-machinery run, per-level-methodology deferral), and next steps. *(`BRIDGE-2026-06-06.md` (the substrate-build bridge) and `BRIDGE-2026-06-05.md` are superseded.)*

**Canon-precedence:** the LIVE decision notes below are SOURCE OF TRUTH for the runtime / liveness / transport / scale model and **override the Jun-02 design specs wherever they conflict**. The Jun-02 specs remain canonical for the semantics they already cover.

## LIVE — source of truth (read first)
- `runtime-decisions-and-commissioning-2026-06-04.md` — the include/defer cut, the liveness/ownership synthesis (detector + lease + accounting + fencing), the commissioning method.
- `arch-gap-review-2026-06-04.md` — the 8 blocking gaps + 9 contradictions from the adversarial review.
- `path-to-ready-2026-06-04.md` — doc-health verdict + the 8-phase path to build.
- `DEFERRED-REGISTER.md` — the single consolidated owed/deferred/open register (the completeness-pair's other half with `design/INDEX.md`). Every concern not built in v1 lives here or is presumed dropped. **Maintenance rule:** a new deferral is added here in the same change.

## ACTIVE inputs (verify / consume, then archive)
- `L1-config-design-notes.md`, `L2-config-design-notes.md` — owed-work inputs; their stated targets `L1-CONFIG.md`/`L2-CONFIG.md` don't exist — verify whether they were propagated into `operational/L1|L2/config.md`, then archive.
- `code-review-dimensions-research.md` — reusable research underpinning **per-level** review (NOT a standalone review function); to relocate to a `reference/` area.

## ARCHIVED — historical, not current truth (in `archive/`)
Stored for traceability only: `SESSION-2026-03-10`, `gmail-notes-scan-2026-03-16`, `PROPOSAL-deferred-ideas-consolidation`, `workflow-diagram-learnings`, `compute-time-bounded-tasks`, `consolidation-plan-2026-06-02` (the 06-02 master consolidation record — superseded-where-overlapping by the 06-04 notes).
