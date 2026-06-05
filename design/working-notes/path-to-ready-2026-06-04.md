# Doc-Health Verdict + Path-to-Ready — 2026-06-04

Source: doc-audit workflow `wf_519e6d6e-6b7` (5 slice-audits + synthesis, findings verified against actual files). Companion to `arch-gap-review-2026-06-04.md` and `runtime-decisions-and-commissioning-2026-06-04.md`.

## Verdict: SIGNIFICANT DRIFT (recoverable)
Semantic layer is largely canon-aligned. But the just-locked **interactive-tmux mechanism layer is unwritten** (`tmux`, `watchdog` appear **0×** in canonical docs), and **three superseded models are still live across ~12 docs**, several with cross-reference chains that can resurrect dissolved concepts:
1. **Review Department** — a 3-doc chain: NOTES.md:707 → **QUALITY-GATE.md:29 (the hub)** ← GUI-DESIGN.md:61, git-protocol.md:52. Cut at the hub, then fix the pointers.
2. **Deterministic Active/Parked/Waiting liveness** — OBSERVABILITY.md:22-29, NOTES.md:856/867-885 ("deterministic infrastructure-tracked", self-waking Parked, "blocking command wrapper").
3. **"Internal Affairs" naming** — pervasive (~8 docs); IMPROVEMENT-WORKSPACE.md is *still titled* "Internal Affairs" (filename/title mismatch).

## Build-blockers (must fix before building) — verified
- **NOTES.md** — most build-dangerous artifact (cited as authority by DESIGN-PRINCIPLES.md:57). Add "IDEAS LOG, NOT SPEC" banner + per-section superseded banners (Review-Dept §707, agent-state §856-885).
- **QUALITY-GATE.md:29** — reconcile the review-room/department hub → per-level review (per-unit L5+ + whole-set L4-level). Fixing this breaks 3 inbound references at once.
- **GUI-DESIGN.md:61** + **shared/git-protocol.md:52** — delete/rewrite the review-department-room / parallel review-coordinator language.
- **GIT-INTEGRATION.md** — whole doc on dissolved review dept + old L3/L4 roles; rewrite or supersede.
- **shared/agent-lifecycle.md** (:27/:131/:133) — reconcile kill-authority + supervision scope to: evidence-lease + detector liveness; watchdog detect-and-notify (reap only non-signing ephemeral leaves, no blind-kill of live agents); live-descendant roll-up (not direct-children-only).
- **ARCHITECTURE.md:156** — "Life-OS bus" → own bus + transport stub. **:372/374** — "force-kill any depth" → detect-and-notify / scoped leaf-reap + fenced transfer.
- **OBSERVABILITY.md:22-29** — Active/Parked → working/waiting/idle/dead; "deterministic" → "deterministic for transitions, inferred-with-bounded-confidence for working/idle" on the v1 floor signals.
- **operational/L5/{spawn-template,config,role}.md** — **WRITE the L5 terminal-signal semantics (DONE/FAILED/ESCALATED durable artifact)** — verified ABSENT (only report.md + bus nudge). Gap-review blocking #2c.
- **ROADMAP.md** / **PROJECT-GUIDE.md** — strip/annotate post-V1 Review Dept, "Program Manager", Active/Parked, Internal Affairs; PROJECT-GUIDE encodes a stale **FOUR-level** model (canon = 5 + L5+).

## Should-fix
- Rename **"Internal Affairs" → "Improvement Workspace"** everywhere (IMPROVEMENT-WORKSPACE.md incl. H1, ARCHITECTURE.md:434/503, OBSERVABILITY.md, DESIGN-PRINCIPLES.md:203/313, WORKSPACE-SCHEMA.md:57, runtime-and-model-map.md:47, agent-definition-principles.md:28/114).
- Scope **Optimizer-L1 as FUTURE/not-v1** at every god-view mention (L1/role.md:61, WORKSPACE-SCHEMA.md:57, PROJECT-PLANNING.md:91, PROJECT-GUIDE.md).
- **L4/role.md:33** "manage agents, not tasks" → deliverable-ledger-primary (gap-review contradiction #8).
- **COMMUNICATION.md:109** — "L5 keeps its context and continues" → don't imply persistence (ephemeral one-shot; same-spawn bounce OK).
- Fix OBSERVABILITY.md §4.1 "72-Hour" header vs "2 weeks" body; DOCUMENT-HIERARCHY.md stale nav map (lists ARCHITECTURE as "planned", omits live notes).

## Clutter / navigation (the "things get lost" risk)
- **working-notes/ has NO index** — the 2 LIVE notes are buried among 9 stale Mar-2026 notes. **Add working-notes/INDEX.md** naming the 2 live notes as canon-superseding; list the rest as archived/historical.
- Mark **consolidation-plan-2026-06-02.md** superseded-where-overlapping (its runtime/liveness rows are superseded by the 06-04 notes).
- **Archive** (→ working-notes/archive/): SESSION-2026-03-10.md (72KB dump), gmail-notes-scan-2026-03-16.md, PROPOSAL-deferred-ideas-consolidation.md, workflow-diagram-learnings.md + workflow-diagram.html, compute-time-bounded-tasks.md.
- **L1/L2-config-design-notes.md** — their target files L1-CONFIG.md/L2-CONFIG.md don't exist; the real files are operational/L*/config.md. Check if propagated; archive or label pending.
- Relocate **code-review-dimensions-research.md** to a reference/ area (keep — underpins per-level review).
- **Canon-precedence rule** (put in a refreshed DOCUMENT-HIERARCHY.md or new design/INDEX.md): the two 2026-06-04 notes OVERRIDE the Jun-02 docs where they conflict; Jun-02 docs canonical for semantics they cover. Builder reading order: runtime-decisions → arch-gap-review → ARCHITECTURE (post-reconcile) → cluster docs; NOTES.md last, only with banners.

---

## PATH TO READY (8 phases)

**Phase 0 — Doc reconciliation** (depends: none; target = the 2 live notes). Kill the 3 superseded models + all build-blockers above; rename Internal Affairs→Improvement Workspace; scope Optimizer-L1 future; write the L5 terminal signal; add working-notes/INDEX + canon-precedence; archive clutter.
*Done when:* grep for banned terms returns only annotated hits — no "Life-OS bus" transport, no "review department/room", no "Active/Parked" or "deterministic infrastructure-tracked", no "Internal Affairs" name, no unscoped "force-kill any depth"; L5 terminal-signal documented; NOTES banners in place; working-notes INDEX names the 2 live notes.

**Phase 1 — Cluster ① Harness-as-a-process** (depends: Phase 0). design/DAEMON.md + binding-ledger schema (node→uuid+deliverable-state+liveness-state+owner+lease_epoch+owner_token); single-writer + ledger atomicity (close the lost state-ledger-races lens here); reconcile-on-restart + continuous; spawn chokepoint; genesis. Adapt recovered control_plane.py (1706 lines) — cite the adaptation source per section.

**Phase 2 — Cluster ② Liveness & lifecycle** (depends: Phase 1). design/WATCHDOG.md from recovered watchdog-design-01.md + F-011/012/014: evidence-lease (persistent coordinators) + sign-off-or-fail (ephemeral leaves); thin detector behind liveness(node) interface (JSONL-growth + pane-alive day-one); coordinator process-death probe; fencing wired into transitions; W/W2 windows KNOWN-OPEN.

**Phase 3 — Cluster ③ Transports** (depends: Phase 1+2). Own bus wire (append-only inbox per node + tail/inotify); wake contract (send-keys+Enter, verify-turn-via-JSONL, prompt-string gate); escalation-answer-down (alive vs collapsed); three human channels (sign-off transport, out-of-band L1→user alert, human control surface) — plausibly hosted by the harness app.

**Phase 4 — Cluster ④ Scale-as-resource** (depends: Phase 1+2). Admission gate IN the spawn chokepoint (claim-before-spawn); per-runtime sub-ceilings; 429/backoff/backpressure; cap denomination. Mostly DEFERRED-with-triggers → "done" = designed + trigger recorded.

**Phase 5 — Walking-skeleton build** (depends: Phases 1-2 designed, 3 minimal-wake, 4 gate-seat). The 11 INCLUDE-in-v1 items wired together, nothing more.
*Done when:* daemon boots, spawns L1, ledger reconciles on restart, one agent spawned/detected/signed-off/collapsed through the single writer with fencing active, and `kill -9` daemon + relaunch recovers from ledger.

**Phase 6 — Connectivity smoke** (depends: Phase 5). ~5-min trivial one-spawn/one-sign-off/one-collapse, fully visible in ledger/trace. Prove pipes wired before the real job.

**Phase 7 — Real-job commissioning + pressure-up** (depends: Phase 6 + cluster ③/④ designs). Run a real non-trivial job slow + heavily traced, expecting breakage; freeze-and-examine joint leaks; settle empirical KNOWN-OPENs (W/W2, false-idle rate, Codex pane-warmth, resource envelope, H40 spike); then pressure-up for load leaks, pulling DEFERRED items as their joints leak.
