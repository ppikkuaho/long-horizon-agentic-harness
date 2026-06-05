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
- **`SECURITY.md`** — containment floor (cross-cutting): the `sandbox-exec` write/read-jail, secret protection, skip-perms-in-jail posture, fleet HALT. Wires into the spawn chokepoint (the seatbelt is the pane launch command). Decisions locked 2026-06-05 (Option A).
- **`ROLE-RESOLUTION.md`** — how a role is resolved at boot (cross-cutting): the H40 split — one shared minimal `--system-prompt-file` (constant) vs role-as-read-in-place-documents (the per-seat load-manifest), refs resolving under the read-allow graph (no flatten), `role_file` → `system_prompt_file` + `role_variant`. Reconciles §4 + Decision B; rides the spawn chokepoint. Created 2026-06-05.
- **`INTAKE-TO-DELIVERY.md`** — the end-to-end application arc (cross-cutting): user request → L1 intake/intent-spec → project genesis → L2 spawn → execution → L1 final-accept → **control-plane promotion** of the product out of the gitignored `/runtime/` to the intake-captured destination (the ONE sanctioned cross-write-jail action, gated on accept — never an agent write). Rides the substrate; the new build code is IMPL-PLAN Increment 17. Closes register V3. Created 2026-06-05.

*Internally consistent post cross-cluster reconciliation (2026-06-05). The recovered `research/` files below are the SUSPECT adaptation source, NOT these specs.*

## ACTIVE — the build (`harnessd/`)
- **`harnessd/IMPLEMENTATION-PLAN.md`** — code architecture + the ordered **0–16 build-increment queue** (Phase 5a). OAuth-subscription-only invariant. Code lands in `harnessd/`; per-build project trees in the gitignored `/runtime/`.

## ACTIVE — older design specs (`design/`)
`ARCHITECTURE`, `DESIGN-PRINCIPLES`, `DECOMPOSITION-METHODOLOGY`, `COMMUNICATION`, `OBSERVABILITY`, `WORKSPACE-SCHEMA`, `PLAN-ALIGNMENT-GATE`, `PROJECT-PLANNING`, `QUALITY-GATE`, `IMPROVEMENT-WORKSPACE`, `VISION`. (`NOTES.md` = idea-log.) **Phase-0 reconciliation: DONE.**

## ACTIVE — agent-facing runtime docs (`operational/`) — what spawned agents load
`operational/L1..L5/{role,config,soul,spawn-template}.md` (+ L1 handbook/intake/skills, L3 planning-template, L5 swe-handbook) and `operational/shared/{system-prompt, agent-lifecycle, comms-protocol, git-protocol, runtime-and-model-map, agent-definition-principles, intent-spec-contract, user-profile-schema}.md`.
- **`operational/shared/system-prompt.md`** — the ONE shared minimal `--system-prompt-file` content, identical L1–L5 (H40, resolved). REPLACES base block 2; the role is NOT here (delivered as read-at-boot documents). Promoted 2026-06-05.
> **ROLE-RESOLUTION (DONE, 2026-06-05):** the boot model is reconciled. The shared system prompt is promoted (above); the role is delivered as documents the agent reads in place under the read-allow graph (NOT inlined — write-jail-not-read-jail). The canonical boot model + per-seat load-manifest is specified in **`design/ROLE-RESOLUTION.md`**, and Decision B is propagated into all the former bake-sites — DAEMON §6.2/§6.1/§6.4/§7 + §3.2 (`role_file` → `system_prompt_file` + `role_variant`), SECURITY §1.1/§1.4/§4.1/§9, IMPLEMENTATION-PLAN adapter+genesis+tests, and the spawn-template/intake load-manifests — all now pass the shared `system-prompt.md` (not `role.md`). Adversarial-reviewed + orchestrator-grep-verified. Tracked in `DEFERRED-REGISTER.md` (Decision B, DONE).

## Build substrate (`research/` — SUSPECT: adapt, don't trust)
The recovered prior art the build adapts FROM (NOT the `design/` specs): `research/orchestration-frame/self-improvement-harness/{control_plane.py, watchdog.py, test_watchdog.py, CONTROL-PLANE.md, WATCHDOG.md}`; `research/orchestration-frame/phase-2-runs/research/{watchdog-design-01.md, ARCHITECTURE-FINDINGS.md}`. *(The `WATCHDOG.md` here is the recovered draft; the canonical spec is `design/WATCHDOG.md`.)*

## Supersede-decisions — RESOLVED in Phase 0 (bannered/annotated, not deleted)
`GIT-INTEGRATION.md` (superseded-bannered; mechanics → `shared/git-protocol.md`), `ROADMAP.md` (superseded entries annotated), `DOCUMENT-HIERARCHY.md` (superseded by this INDEX), `PROJECT-GUIDE.md` (reconciled to 5 levels + L5+).

## Records & archives
- Pinned CC: `PINNED-CC.md`. H40 in-role boot: `H40-RESEARCH-TASK.md` (**RESOLVED**).
- `design/working-notes/archive/` — stale notes (see `working-notes/INDEX.md`). Prune/integrity: `MOVE-MANIFEST.md`, `manifest.json`. Suspect-art map: `PRIOR-ART-SUSPECT.md`.
