# Consolidation Plan & Decision Log — 2026-06-02

**Purpose:** Capture the design decisions, insights, and doc-change plan produced in the 2026-06-02 design conversation, and drive the consolidation of those insights into the L1–L5 architecture docs.

**Status:** Planning. WS0 decision-spikes in progress (via tabletop dry-run). Foundation docs not yet written.

**How to use:** The Decision Log is the settled state. The Owed Decisions gate finalization of specific docs. The Inventory (A1–L47) is the full set of insights to capture; the Workstreams map them to docs. Sequence is WS0 → foundation → propagation → meta → de-staling.

---

## 1. Decision Log (settled)

Resolved 2026-06-02:

- **C21 — L3 dual-spec → SPLIT.** A *temporary planning-L3* produces the area/module design as `plan/area-{name}.md` in L2's planning workspace during the planning phase, then collapses. A *fresh execution-L3* is spawned later and owns that design as `design.md` in `L3/{area}/`, adding `plan.md` as the living execution layer. Both templates must state the handoff explicitly (planning-L3 output → execution-L3 input). Justified by C19/C20 (clean-context planning vs execution).
- **A1 — V1 scope → SOFTWARE ONLY.** ML-research-pipelines, market-studies-with-code-deliverables, etc. are OUT of V1. Portfolio breadth is the long-term destination; software-building is the V1 beachhead. Retires "handles any task type / flexibility is a core requirement" as a V1 claim.
- **K45 — Intent elicitation → user profile + L1 discussion + dispatched parallel session.** L1 elicits intent through conversation grounded in the user profile, identifying the areas the user is opinionated about. L1 then **dispatches the user to their own parallel session** to do the heavy work of producing the spec docs (SDD or whatever artifacts make most sense, in the right order); only the *results* return to L1, so **L1's context stays clean.** L1 ingests the produced spec.
- **L1 intent-fidelity review → the USER reviews; L1 guards.** L1 captures intent (conversation + the mechanism above), writes it down as the intent spec, and then **guards** it — e.g., checks whether what L2 proposes is in line with captured intent *before* passing to the user. The user is the ultimate reviewer of client-intent fidelity.
- **Acceptance-test ownership → AT ALTITUDE; L4 authors L5's executable tests (V1).** Each delegating level authors the pass-conditions for the level below at its own altitude (D26). The executable acceptance tests L5's code must pass are authored by **L4** (directly above L5 → tester ≠ producer; holds the task spec). L5 makes them pass + writes unit tests. Mature design adds a dedicated lateral test-writer (post-V1); V1 = L4 direct. **To validate at the L4→L5 junction in the dry-run.**

---

## 2. Owed Decisions (WS0 — gate finalization; several resolvable via the dry-run)

- **F34 — visibility-graph mechanism + enforcement:** does "same-level siblings" mean same-parent only (cousins excluded)? cross-parent coordination = escalate-to-common-ancestor vs deferred? optimizer-L1 god-view read-only or read+write? enforcement = filesystem-ACL vs spawn-time path-scoping vs convention?
- **F35 — addressing/station grammar:** how `proj/L3.1` derives from the workspace path; sibling-index assignment + stability across respawn; address survival through collapse/resurrection.
- **D26 — rubric format/storage:** section-in-brief vs separate `rubric.md` per task vs gate loadset vs part of client-brief.
- **E32 — cross-runtime brief/spawn contract:** how an opus L4 briefs a codex L5 (brief shape, per-runtime tool manifest, completion signaling, result flow). Plus the L4+L5 codex audit (an action not yet performed).
- **I42 — optimizer-L1 development methodology:** how it detects recurring issues + proposes/tests interventions; binding to the `ai-driven-autonomous-iterative-improvement` investigation.
- **H40 — Claude-base-prompt patch:** patch text, delivery mechanism (wrapper vs runtime injection), interaction with codex levels (no Claude base prompt). Capture as intention; ties to `dev/patches/claude-code/`.
- **B5/B14 — methodology integration:** how SDD's fidelity spine + WBS 100%-rule interact; how hexagonal ports map onto DDD bounded contexts per C4 level; whether the platform/foundation cross-cutting context = a dedicated L3 area vs an L2-owned shared-kernel vs a cross-area contract.
- **Review free-parameters (D24/D28/D29/G37/J43):** which CI checks are mandatory per language/runtime + CI-in-session vs external hook; bounce-back loop-cap N; what the 72h window enables (read-only replay vs live re-spawn vs re-run) + who triggers reap; the concrete first drift-verification loop (what it checks, which boundary first, pass-condition).

---

## 3. Insight Inventory (A1–L47)

**Scope/framing:** A1 V1 = software-building (general-task → post-V1) · A2 levels = separation by *kind of thinking*, not a permission ladder · A3 finish-design-before-infra is intentional.

**Decomposition methodology:** B4 deep-modules = *rubric, not backbone* · B5 backbone = C4 + DDD + SDD + hexagonal ports (WBS + vertical-slices at exec) · B6 connections > boxes (carve where thin) · B7 carve by co-change/coupling; DDD = seam-finder; target = isolate change · B8 dependencies toward stability (the "sun"); never volatile at center · B9 deep-modules / depth-ratio / collapse shallow levels · B10 rich-inside/thin-across, fractal membranes · B11 boundary-pays-for-itself (glob vs confetti) · B12 cohesion = "name it honestly"; utils = generic-not-infrequent, watched · B13 misfits-are-information taxonomy · B14 module ≠ work ≠ org (Conway); cross-cutting → named platform/foundation context · B15 build core-out + walking-skeleton-first; design ≠ build; build by dependency/risk; contract-first · B16 interfaces = core-defined sockets + many adapters; talk only through interfaces; optional shared transport; transport vs contract · B17 router-vs-direct (default direct; router only at boundaries/dynamic/async; keep dumb) · B18 hub-router OK vs central-data-store anti-pattern; separate routing from ownership; single source of truth; queries/commands.

**Operating cycle:** C19 separate plan/exec by clean context, per-increment (not waterfall); architecture front-loaded, exec-planning rolling · C20 P→E→R per-unit, recursive (the operating-cycle resolution) · C21 L3 dual-phase justified; dual-spec resolved (see Decision Log) · C22 walking-skeleton applies to building the system (→ dry-run).

**Review/quality:** D23 independent review per level (P4) · D24 review at *altitude* (composition + fidelity; don't re-do lower) · D25 big-bang gate per level + parallel exec below + escalation/early-warning channel · D26 rubrics + pass-conditions authored at *planning time* by the delegating level · D27 two axes: quality + fidelity (drift dominant) · D28 CI/CD = automated floor · D29 bounded bounce-backs; neutral/tentative findings · D30 Review Dept = IN.

**Models:** E31 model+runtime = per-level, config-time, swappable; spawn abstracts runtime; per-runtime tool manifest · E32 L1–L3 opus / L4 open / L5 codex; cross-runtime committed; L5 docs need codex audit.

**Comms:** F33 bus + docs (truth in docs); inbox superseded; best-effort OK because docs are truth · F34 need-to-know visibility graph (subtree + siblings + parent; L1/optimizer god-view; tighten read-table) · F35 addressing schema (bus=gauge / stations / contracts=cargo) · F36 downward-unrestricted; transport vs policy.

**Lifecycle:** G37 collapse + 72h resurrect/audit; keep-context-on-block + escalate options · G38 statelessness backstop; persistence = optimization.

**Agent definition:** H39 souls deprioritized; clear positive boundary framing; measure via optimizer-L1 · H40 possible CC base-prompt patch · H41 briefs thin-but-decision-complete; calibrated guidance.

**Audit:** I42 optimizer-L1 elevated to parallel-important (recurring-issue monitoring + own dev-methodology; 72h feeds it; ties to `ai-driven-autonomous-iterative-improvement`; god-view).

**Verification:** J43 #1 target = spec-faithfulness/drift; verification-loop-first; defer exec-quality optimization · J44 single execution agent per level for now + independent reviewers.

**Intent capture:** K45 L1 drills user for opinionated areas (see Decision Log for mechanism); intent-on-paper = the heavy part.

**Meta:** L46 LLM-design-principles held softly at this scale (mechanisms transfer, prescriptions re-express) · L47 deep-modules vocabulary kept, criterion corrected.

---

## 4. Workstreams (dependency spine)

- **WS0 — Owed Design Decisions** *(decision spikes; do first)*. Resolve/bound §2. Most-blocking: C21 (done), acceptance-test ownership (done), A1 (done), K45 (done), then F34/F35/D26/E32/I42/H40/B5-B14/review-free-params. Record each in this log.
- **WS1 — Decomposition Methodology** *(large; new doc `DECOMPOSITION-METHODOLOGY.md` + DESIGN-PRINCIPLES summary + PROJECT-PLANNING refs)*. B4–B18, L47. Fixes the false pointer (ARCHITECTURE item 15 claims the method is in PROJECT-PLANNING; it isn't). Dep: WS0.
- **WS2 — Operating Cycle** *(medium; ARCHITECTURE, PROJECT-PLANNING, DESIGN-PRINCIPLES, NOTES, ROADMAP)*. C19–C22, A2, A3. Lands P→E→R per-unit as resolution. Dep: WS0.
- **WS3 — Comms + Visibility supersession** *(large; COMMUNICATION, WORKSPACE-SCHEMA, comms-protocol, git-protocol, ARCHITECTURE, DESIGN-PRINCIPLES)*. F33–F36, B16–B18. Inbox→bus+docs; broad-read→need-to-know. Dep: WS0.
- **WS4 — Models + Runtime** *(medium; new doc `operational/shared/runtime-and-model-map.md` + ARCHITECTURE)*. E31–E32. Dep: WS0.
- **WS5 — Review Dept / Quality / Observability / Lifecycle** *(large; QUALITY-GATE, OBSERVABILITY, optional `REVIEW-DEPARTMENT.md`, agent-lifecycle, ARCHITECTURE, DESIGN-PRINCIPLES, VISION, ROADMAP)*. D23–D30, G37–G38, J43–J44, I42. Dep: WS0, WS2.
- **WS6 — Per-level operational propagation** *(large; all operational/L1–L5 + new `operational/shared/agent-definition-principles.md`)*. Propagate foundation; apply C21; codex-audit L5; fix stale paths. Dep: WS1–WS5.
- **WS7 — Optimizer-L1 / Internal Affairs elevation** *(medium; INTERNAL-AFFAIRS, optional `OPTIMIZER-L1.md`, OBSERVABILITY, ROADMAP)*. I42. Dep: WS0, WS5.
- **WS8 — Scope / Framing / Vision / Principles meta** *(medium; VISION, DESIGN-PRINCIPLES, ARCHITECTURE, PROJECT-PLANNING)*. A1–A3, L46–L47, K45, J43, D30. Dep: WS0, WS1.
- **WS9 — Navigational de-staling + 4→5 migration** *(large; ROADMAP, PROJECT-GUIDE, DOCUMENT-HIERARCHY, GIT-INTEGRATION, GUI-DESIGN, workflow-diagram.html)*. Do LAST. Dep: WS1–WS8.

### New docs
1. `design/DECOMPOSITION-METHODOLOGY.md` (definite) — home for B4–B18.
2. `operational/shared/runtime-and-model-map.md` (definite) — E31/E32 + cross-runtime + codex-audit status.
3. `operational/shared/agent-definition-principles.md` (definite) — H39/H40/H41/L46; lets soul.md files stay one-line pointers.
4. `design/REVIEW-DEPARTMENT.md` (optional) — split from QUALITY-GATE if it outgrows single-read.
5. `design/OPTIMIZER-L1.md` (optional) — if optimizer material outgrows INTERNAL-AFFAIRS.

### Major supersessions resolved
4-level → 5-level (finish migration everywhere) · filesystem-inbox → bus + docs · broad project-wide read → need-to-know visibility graph · deep-modules-as-backbone → deep-modules-as-rubric (C4+DDD+SDD+ports is the backbone) · Review Dept deferred → in-V1 · operating cycle parked → committed (per-unit P→E→R) · optimizer-L1 deferred/passive → parallel-important · souls first-class → deprioritized · any-domain → software-only V1.

---

## 5. Recommended Sequence

1. **Phase 0 — WS0 decision spikes** (via the tabletop dry-run; log each here).
2. **Phase 1 — Foundation docs** (WS1–WS5, parallel where independent; WS5 after WS2).
3. **Phase 2 — Operational propagation** (WS6).
4. **Phase 3 — Optimizer-L1 + scope/framing/meta** (WS7, WS8).
5. **Phase 4 — Navigational de-staling + 4→5 migration** (WS9), last.

*Coverage: all 47 inventory IDs (A1–L47) have at least one workstream home; none orphaned.*

---

## 6. Dry-Run Session Decisions (2026-06-02)

Settled via the tabletop dry-run (Payments slice of an e-commerce backend). These extend the inventory; new items numbered M48+.

**Intake / L1**
- **L1 intake methodology:** outcomes-first → *tradeoff-probing* to detect opinionated vs delegated (people reveal opinions when shown a fork, not when asked "do you care") → variable-depth drilling (deep on opinionated/risky, shallow on delegated) → a **tagged living spec** (each requirement `decided`/`delegated`/`deferred`) → reflect-back. The deep grill runs in a **separate parallel session**; only the spec returns, so L1's context stays clean.
- **L1 = intent guardian:** captures intent → writes it down → *guards* it (checks L2's proposals against intent before surfacing to the user). The **user is the ultimate fidelity reviewer**.

**L2**
- **L2 methodology = the real-architect decision-process** (the workflow to copy): identify *architecturally-significant* decisions; decompose to "components + responsibilities + interfaces" then **stop at sufficient resolution to delegate**; **Last Responsible Moment + subsidiarity** — decide cross-module/expensive *now*, defer module-internal/domain-deep *downward with constraints*; recognize/apply known patterns; de-risk with spikes. **DDD is the carving sub-method inside this**, not a replacement for it.
- **Why L2 delegates** = role separation + context/bandwidth preservation, **NOT capability** (same model; same reason in human orgs — a director *can* do the associate's work, it's just not his job and would clog his bandwidth). **Domain expertise loads per-domain into the owning L3's loadset**, not L2.
- **L2 output = ADR-style:** component map + interface contracts + **ADRs** (decision + rationale + status `decided`/`deferred`) + per-module specs where deferred decisions appear as **constraints** (= the D26 rubric L3 is held to). ADRs pull quadruple duty: handoff contract + anti-drift anchor + audit/optimizer substrate + statelessness rationale-preservation.
- **Provisional interfaces / progressive hardening:** L2 proposes *coarse* interfaces; the domain-deep planning-L3 pressure-tests + **renegotiates upward**; the walking skeleton validates; interfaces are **FLUID during the planning cascade, FROZEN for execution.** One mechanism resolves both "L2 isn't a domain expert" and "upfront planning is fragile."

**Planning-L3 split**
- **Threshold-gated:** the planning-L3 / execution-L3 split fires only when a module's design is *substantial*; trivial modules collapse it (variable depth at the planning layer).

**L4 / tests (the anti-theater core)**
- **L4-tester lateral:** a *separate* agent (≠ L4 coordinator, ≠ L5 coder) authors L5's acceptance tests from L4's spec, **before L5 codes**. Independent second reading of the spec + keeps L4's context clean.
- **Temporal anti-theater rule:** acceptance tests + review rubrics are authored at **PLANNING time, BEFORE the work, FROM the spec, by ≠ the worker** — so the work is anchored to the tests, never the tests to the work. **Generalizes up the cascade:** every level, during its plan phase, authors the criteria for the level below *before that level executes*. A level's Plan phase isn't "done" until it has emitted spec + acceptance tests + gate rubric (the Plan-phase output contract).

**L5**
- **L5 = execute-review pair:** **L5** (Codex *harness* + GPT-5.5 *model*) writes code, runs the pre-written acceptance tests + unit tests + **CI (the automated floor)**. **L5+** (a *separate* agent — opus or GPT-5.5) does its own testing + reviews against spec, then **accepts** (→ forward, both collapse) or **bounces** (L5 keeps its context, continues; bounded loop).
- **Terminology:** Codex = the harness; GPT-5.5 = the model. (OpenAI no longer ships "codex" *models*.)

**Briefs**
- **Pointer-not-payload:** every level gets the *distilled* brief loaded (spec + constraints + interface + ADRs); raw upstream intent is *referenced* (pullable on demand), not carried. ADRs are the rationale bridge.

**Plan-alignment gate (NEW major mechanism — full design in `design/PLAN-ALIGNMENT-GATE.md`)**
- Dual nested cycles: **design cycle → validated plan → THE GATE → build cycle.** Requirements traceability (hierarchical dotted IDs, *generated* RTM). Gate checks: atomization-completeness (Check 0, inspects the intent→ID minting seam) + forward/backward coverage (hard) + **two-window blind reconstruction** + adversarial comparator + evidence-specificity + whole-portfolio coherence + L1-triage-with-conflict-of-interest-fences + **warm triangulated human sign-off**; **incremental subtree re-gating**; **human-gate health monitoring**; **no fake alignment score**. This is the system's core anti-drift / alignment mechanism.

**Trace clarifications**
- **Planning is a coordinated round:** parallel planning-L3s → **L2 compatibility review** (catches cross-module interface ripples/renegotiations) → lock interfaces → execution. (Confirms ARCHITECTURE §5.)
- **Walking skeleton = a de-risking spike** (ungated, early, proves connections) — distinct from gated execution. Delineate the two cleanly.

**Future refinement (noted, not yet designed)**
- **Human-escalation filter:** not "can we ask the human" but "ask the human only about what he's *genuinely opinionated on*, framed so it's *easy to decide*." Key the human-review surface off the intake's opinionated-areas map + decidability; reduces gate human-load and counters human-gate slack over time. (Relates to gate open-questions 2/3.)

### New inventory items (extend A1–L47)
- **M48** — Plan-alignment gate + dual design/build cycles + requirements traceability (RTM); core anti-drift mechanism. Doc: `design/PLAN-ALIGNMENT-GATE.md`.
- **M49** — L2 = real-architect process (significant decisions / LRM / subsidiarity / defer-with-constraints / patterns / spikes), DDD as carving sub-method; ADR output; provisional-interface progressive hardening.
- **M50** — L1 intake methodology (outcomes-first / tradeoff-probing / variable-depth / tagged spec) + parallel grilling session; L1 as intent guardian.
- **M51** — L4-tester lateral + tests-authored-at-planning-before-code-by-≠-worker (anti-theater temporal rule, generalized up the cascade as the Plan-phase output contract).
- **M52** — L5/L5+ execute-review pair; Codex=harness / GPT-5.5=model.
- **M53** — planning-L3 split is threshold-gated (collapses for trivial modules).
- **M54** — pointer-not-payload briefs (ADRs carry rationale; raw intent referenced).
- **M55** — coordinated planning round (parallel design → L2 compatibility review → lock) + walking-skeleton-as-spike delineation.
- **M56** *(future)* — human-escalation filter (opinionated-ness + decidability).

### Gate open questions (owed; from the adversarial design pass)
1. Atomization auditor (Check 0): one agent, or two / a different model — it's the seam the whole promise leaks through.
2. Must-never-fail decomposition: how much the user reviews per gate; lighter confirmation for low-risk MNFs.
3. Human-gate health monitoring: the *response* when dwell/expansion degrade (soft intervention vs surface-only).
4. Two-window cost: gate it on portfolio size (single window below a threshold)?
5. The "user misspoke" residual: is the warm three-column playback enough, or add an explicit "is this still what you want?" prompt distinct from the fidelity check?

### Gate open questions — RESOLVED (2026-06-02)
1. **Atomization auditor → run on BOTH Opus 4.8 + GPT-5.5** (union of findings). The pedantic-literal "name every obligation not carried" task suits GPT-5.5's engineering-brain pedantry; Opus catches the semantic/intent gaps GPT-5.5 glosses. **Generalizes (E31/E32 refinement): generative/architecture seats → Opus; pedantic/adversarial/checking seats → GPT-5.5.** In the gate: atomization auditor + adversarial comparator lean GPT-5.5; reconstruction (needs broad intent understanding, user's language) leans Opus.
2. **MNF decomposition / human review → the user confirms plain-language IMPLICATIONS, not technical sub-obligations.** Bad (theater for non-technical users): "idempotency-key on POST /charge, dedup window ≥24h on webhook replays…". Good: "if the app retries, still charged once; if the provider double-confirms, still once; if two staff hit charge together, still once — anything missing?" The user owns the *meaning*; the auditors (Opus+GPT-5.5) own *technical completeness*. Render-depth is calibrated per-user/per-area from the intake (see M58).
3. **Human-gate health degradation → surface to the user only.** Point it out; no forcing, no override; respect autonomy. Passive feed to optimizer-L1 retained for cross-run pattern-spotting.
4. **Two-window cost → full send in V1**, no size/stakes gating. Principle: **make it work first (full rigor), make it cheap second**; cost-scaling is optimizer-L1's later job, not a V1 design compromise.
5. **"Is this still what you want?" prompt → build it in.** A distinct "right goal?" beat, separate from "did we capture it right?", scoped to **top-level outcomes + must-never-fails** (asking on every leaf would be noise). Catches user misspeak.

### New principles / inventory (extend M48+)
- **M57 — Neutral tradeoff framing for human decisions.** Present choices as balanced options ("A biases toward X, B toward Y") + an honest recommendation **grounded in the user's OWN stated values from intake** ("given you said you care most about cost, we'd lean A; the tradeoff is…") — never the loaded/pressuring form ("are you sure you wouldn't rather compromise?"). The dark-pattern is banned; help-them-decide (contextualize + recommend-from-their-values + no pressure) is the standard. Applies P10/P11 to the human-facing surface. Don't abdicate either — a user often wants the expert read.
- **M58 — Intake-calibrated render-depth.** How much / how technically the gate surfaces things to the user is **per-user, per-area, derived from the intake**, along two dimensions: **OPINION** (opinionated → ask; delegated → don't — drives the M56 escalation filter) × **FLUENCY** (technical → technical render; non-technical → plain-language implications — drives rendering). The opinionated-areas map does double duty. → **Intake (M50/K45) refinement: also capture technical fluency per area, not just opinionated/delegated.**

### Owed WS0 decisions — RESOLVED (2026-06-02)
- **B14 — Foundation = SUBSTRATE.** Cross-cutting (Money, IDs, events, audit, idempotency primitive, base data model) is a substrate L2 establishes *before* the feature areas — the stable core, built first via the walking skeleton. Not a peer feature module.
- **E32 — Cross-runtime brief = runtime-neutral task contract + thin runtime adapter** (hexagonal: brief content = core, runtime envelope = adapter). The semantic brief (identity + spec + frozen acceptance tests + interface contracts + constraints + workspace + reporting) is identical across runtimes; only tool-manifest + harness-invocation + output-format are runtime-specific, injected by the adapter at spawn. **Result-flow is runtime-neutral for free** (docs-as-truth + bus — both runtimes write files + post). **GPT-5.5 brief discipline:** maximally decision-complete (won't fill gaps with good architecture); acceptance tests as primary anchor; explicitly **escalate ambiguity, not decide** (L5→L4 channel load-bearing). L5+ reviewer on a *different* runtime (Opus) for judgment diversity. Delivers E31 swappability (swap runtime = swap adapter). Home: `operational/shared/runtime-and-model-map.md`.
- **F35 — Address = workspace node path + role-variant suffix** (e.g. `proj/payments`, `proj/payments/gateway`, `…/stripe-client#exec` / `#review`). Semantic (area names, not numeric `L3.1`), stable across respawn (bound to the work node, not the instance); the F34 visibility graph derives from it (subtree = paths under; siblings = same-parent; parent = path minus last segment).
- **D26 — Rubric/acceptance = a dedicated, FROZEN, per-unit artifact in the work node** (e.g. `…/stripe-client/acceptance.md`), separate from `brief.md` + `report.md`. **Write-once at planning, READ-ONLY to the executor** — immutability is the anti-test-theater enforcement made physical. Authored by the delegating level / L4-tester; ID-tagged (feeds RTM); read by worker + L5+ reviewer. Same pattern for each level's gate rubric.
- **UNIFICATION — one hierarchical-path spine:** requirement-IDs (`R-003.2.1`), agent-addresses (`proj/payments/gateway`), workspace tree, git branches, rubric-file locations, and the visibility graph are ALL the same hierarchical-path/prefix scheme. Decided once, serves all.
- **Model-perspective rule (E31/E32):** generative/architecture seats → Opus 4.8; pedantic/adversarial/checking/execution seats → GPT-5.5 (literal, engineering-brain, weak at greenfield/architecture).
