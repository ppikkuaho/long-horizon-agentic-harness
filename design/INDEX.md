# L1-L5 Harness — Active Doc Index

**This is the build doc set.** Point the build (and any agent) at the files listed ACTIVE here. Anything not listed is historical — see archives at the bottom. Supersedes the stale `DOCUMENT-HIERARCHY.md`.

> **MAINTENANCE RULE (do not skip):** adding or superseding a design/build doc **updates this index in the same change.** A doc that exists on disk but is not listed here is invisible to anyone — human or agent — who trusts the map. That is exactly how the four cluster specs got "lost" by the 2026-06-05 completeness audit: they were authored after this index and never added to it. This index + `working-notes/DEFERRED-REGISTER.md` are the **completeness pair** — every concern appears in one of them or is presumed dropped.

## Canon-precedence
1. The four **runtime cluster specs** + the two **LIVE decision notes** are the current source of truth for the runtime model (post-Phase-0 reconciliation + cross-cluster reconcile); they override the older Jun-02 specs where they conflict.
2. The older Jun-02 design specs are canonical for the semantics they cover.
3. `NOTES.md` is an IDEAS LOG, not spec — read last.

## Builder reading order
1. `working-notes/runtime-decisions-and-commissioning-2026-06-04.md` (the include/defer cut + commissioning method)
2. `working-notes/arch-gap-review-2026-06-04.md` (blocking gaps + contradictions)
3. `working-notes/path-to-ready-2026-06-04.md` (the 8-phase plan)
4. The **runtime cluster specs**: `DAEMON.md` ① → `WATCHDOG.md` ② → `TRANSPORTS.md` ③ → `SCALE.md` ④
5. `harnessd/IMPLEMENTATION-PLAN.md` (the code architecture + the 0–16 build-increment queue)
6. `ARCHITECTURE.md` (semantic spine) + the older specs (`OBSERVABILITY`, `COMMUNICATION`, `QUALITY-GATE`, `WORKSPACE-SCHEMA`, `PLAN-ALIGNMENT-GATE`, `DECOMPOSITION-METHODOLOGY`)
7. `operational/` (the agent-facing runtime docs)

## ACTIVE — runtime cluster specs (`design/`) — the build-defining design
- **`DAEMON.md`** ① — harness-as-a-process: daemon, single-writer executor, binding ledger + intent-first WAL, reconcile, claim-before-spawn chokepoint, genesis, fencing.
- **`WATCHDOG.md`** ② — liveness & lifecycle: evidence-lease recovery, detector, leaf/coordinator split, wedge detector, sign-off-or-fail.
- **`TRANSPORTS.md`** ③ — own bus, wake contract, escalation-answer-down, the user-authorized human channels.
- **`SCALE.md`** ④ — admission gate, per-runtime ceilings, OAuth-subscription usage model (mostly deferred-with-triggers).

*Internally consistent post cross-cluster reconciliation (2026-06-05). The recovered `research/` files below are the SUSPECT adaptation source, NOT these specs.*

## ACTIVE — the build (`harnessd/`)
- **`harnessd/IMPLEMENTATION-PLAN.md`** — code architecture + the ordered **0–16 build-increment queue** (Phase 5a). OAuth-subscription-only invariant. Code lands in `harnessd/`; per-build project trees in the gitignored `/runtime/`.

## ACTIVE — older design specs (`design/`)
`ARCHITECTURE`, `DESIGN-PRINCIPLES`, `DECOMPOSITION-METHODOLOGY`, `COMMUNICATION`, `OBSERVABILITY`, `WORKSPACE-SCHEMA`, `PLAN-ALIGNMENT-GATE`, `PROJECT-PLANNING`, `QUALITY-GATE`, `IMPROVEMENT-WORKSPACE`, `VISION`. (`NOTES.md` = idea-log.) **Phase-0 reconciliation: DONE.**

## ACTIVE — agent-facing runtime docs (`operational/`) — what spawned agents load
`operational/L1..L5/{role,config,soul,spawn-template}.md` (+ L1 handbook/intake/skills, L3 planning-template, L5 swe-handbook) and `operational/shared/{agent-lifecycle, comms-protocol, git-protocol, runtime-and-model-map, agent-definition-principles, intent-spec-contract, user-profile-schema}.md`.
> **OWED (completeness-audit 2026-06-05):** these role docs are the AUTHORING form, NOT runtime `--system-prompt-file` inputs — a role-resolution step (compose soul+role+config, inline repo-relative refs) is owed before the real-boot increment. Tracked in `DEFERRED-REGISTER.md`.

## Build substrate (`research/` — SUSPECT: adapt, don't trust)
The recovered prior art the build adapts FROM (NOT the `design/` specs): `research/orchestration-frame/self-improvement-harness/{control_plane.py, watchdog.py, test_watchdog.py, CONTROL-PLANE.md, WATCHDOG.md}`; `research/orchestration-frame/phase-2-runs/research/{watchdog-design-01.md, ARCHITECTURE-FINDINGS.md}`. *(The `WATCHDOG.md` here is the recovered draft; the canonical spec is `design/WATCHDOG.md`.)*

## Supersede-decisions — RESOLVED in Phase 0 (bannered/annotated, not deleted)
`GIT-INTEGRATION.md` (superseded-bannered; mechanics → `shared/git-protocol.md`), `ROADMAP.md` (superseded entries annotated), `DOCUMENT-HIERARCHY.md` (superseded by this INDEX), `PROJECT-GUIDE.md` (reconciled to 5 levels + L5+).

## Records & archives
- Pinned CC: `PINNED-CC.md`. H40 in-role boot: `H40-RESEARCH-TASK.md` (**RESOLVED**).
- `design/working-notes/archive/` — stale notes (see `working-notes/INDEX.md`). Prune/integrity: `MOVE-MANIFEST.md`, `manifest.json`. Suspect-art map: `PRIOR-ART-SUSPECT.md`.
