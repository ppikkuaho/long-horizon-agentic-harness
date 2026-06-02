# AI Architecture — Project Planning Process

How work flows from intent to built software. The process is derived from real-world professional services — architecture firms, management consulting, software solution design. These disciplines independently converged on the same pattern: intent is captured, a concept is designed, the concept is validated, the concept is detailed, the details are executed. The pattern is universal because the problem is universal: turning an idea into a built thing through coordinated expert effort.

This document defines the planning spine — how intent becomes a *validated plan*, and how that plan becomes built software. It is deliberately altitude-stable: the per-unit operating mechanics live in the level docs and the methodology docs, and are cross-referenced here.

**V1 scope:** the process described here is for **building software**. General task-type breadth (ML pipelines, market studies, design-led products) is the long-term destination, not the V1 beachhead. Where this doc says "the thing being built," read "software."

**Two anchors this doc points to, never duplicates:**
- `DECOMPOSITION-METHODOLOGY.md` — *how* L2 and the planning-L3s carve the system (C4 + DDD + SDD + hexagonal ports as the backbone; deep-modules as the rubric that pressure-tests a carving, not the backbone itself).
- `PLAN-ALIGNMENT-GATE.md` — the single hard checkpoint between designing and building, and the requirements-traceability spine that makes it work.

---

## The Shape of the Process

The whole process is **two nested `Plan → Execute → Review` cycles joined at one boundary** — not a single global waterfall:

```
  INTAKE                 ── structured intent capture (L1 + parallel grilling session)
    │
  DESIGN CYCLE           ── L2 architect process → planning cascade → validated plan
    │
  ══ PLAN-ALIGNMENT GATE ══  ← the one hard checkpoint; the vertex of the V
    │
  BUILD CYCLE            ── fresh execution-L3s → L4 → L5 write code against the frozen plan
```

The design cycle produces a *validated plan* and never a line of code. The build cycle produces validated code and never re-opens the architecture. The **plan-alignment gate is the only boundary between them** (full design in `PLAN-ALIGNMENT-GATE.md`).

This is **front-loaded design with rolling per-phase execution-planning**, not a waterfall. The architecturally-significant decisions are made up front, before building starts, because concept errors cascade and are cheap to fix only at plan-time. But execution-planning is *rolling*: each unit's detailed plan is produced just before that unit is built, so real information from earlier phases feeds the later ones. Architecture is committed early; task decomposition stays just-in-time.

Underneath, every unit of work runs its own small `Plan → Execute → Review` cycle, separated from its neighbors by clean context (see the per-unit operating cycle in `DESIGN-PRINCIPLES.md` and the level docs). The big-picture cascade below is how those per-unit cycles compose into a project.

---

## Phase 1: Structured Intake (L1 + User)

The user owns the idea — what, why, for whom, the problem being solved. L1 (System Orchestrator) runs a **structured intake** to turn that idea into a precise, tagged intent spec. This is not requirements-gathering by checklist; it is an opinionated elicitation process whose goal is to find exactly where the user is opinionated and exactly how technically fluent they are in each area, so the rest of the system knows what to decide *for* the user and what to bring *back* to the user.

### The intake method

- **Outcomes-first.** Start from what success looks like in the user's own terms — the outcomes and the must-never-fails — not from a feature list or a tech stack.
- **Tradeoff-probing to detect opinionated vs delegated.** People reveal their real opinions when shown a *fork*, not when asked "do you care about X?". L1 surfaces concrete tradeoffs ("A biases toward cost, B toward latency — which way?") and reads which forks the user has a stake in. The ones they engage with are *opinionated*; the ones they wave off are *delegated*.
- **Variable-depth drilling.** Drill **deep** on opinionated and risky areas; stay **shallow** on delegated ones. Depth is spent where the user has a stake or where getting it wrong is expensive — not uniformly.
- **Capture technical fluency per area, alongside opinionated/delegated.** For each area, L1 records not just *does the user have an opinion* but *how technically fluent are they here*. This second axis is load-bearing downstream: it determines whether the plan-alignment gate later surfaces something to the user as a technical claim or as a plain-language implication (intake-calibrated render-depth — see `PLAN-ALIGNMENT-GATE.md`).
- **A tagged living spec.** Every requirement is tagged **`decided`** (the user resolved it), **`delegated`** (left to professional judgment below), or **`deferred`** (resolved later, at the last responsible moment). The spec is living during intake and frozen as the signed brief at the end. Must-never-fail requirements are flagged and **decomposed to atomic, individually-testable obligations** at intake — a compound must-never-fail minted whole is the highest-stakes place for silent loss.
- **Reflect-back.** L1 plays the captured intent back to the user — including the tags and the must-never-fail decomposition — and the user confirms or corrects.

### The parallel grilling session

The deep elicitation is heavy work that would clog L1's context. So the drilling runs in a **separate, parallel session**: L1 dispatches the user (and/or a dedicated intake session) to do the heavy lifting of producing the spec artifacts (SDD or whatever artifacts fit, in the right order), and **only the finished spec returns to L1.** L1 ingests the spec with a clean context. This is the same clean-context discipline the whole system uses — the producer of a heavy artifact and the steward of the thin distilled result are separated.

### L1 as intent guardian

L1 does not just capture intent and hand it off. L1 **writes it down** (the tagged spec becomes the signed brief) and then **guards** it for the life of the project: when L2 proposes a concept, L1 checks it against the captured intent *before* surfacing anything to the user, and frames any divergence concretely ("you said X; the concept does Y instead, because Z"). The **user remains the ultimate reviewer of intent fidelity** — L1 is the guardian who keeps the bar honest and keeps noise off the user's desk, not the final judge.

**Output:** the **tagged intent spec** (the signed brief). Each requirement gets a stable hierarchical ID at intake (`R-001`, `R-002`, …) carrying its tag, priority, parent outcome, must-never-fail flag, a verbatim **ID→intent-span map** so the prose→ID minting is inspectable downstream, and a **`reflect-back` status** (`pending` until the user confirms it at the Phase 1 reflect-back — or at Phase 3 concept validation for L1-derived requirements — then `confirmed`). The `reflect-back` field is the producer of the stamp the plan-alignment gate's Check 1 reads to forbid freezing on unconfirmed foundations. IDs are minted **only** here; everything below either traces to an intake ID or is sanctioned scope (see Requirements Traceability in `PLAN-ALIGNMENT-GATE.md`). This ID spine is one and the same as the agent-address spine and the workspace-path spine (see "One Spine," below).

---

## Phase 2: The L2 Architect Process (Concept Design)

L2 (Project Architect) receives the tagged intent spec and runs the **real architect's decision-process** — the actual workflow a senior architect uses, copied deliberately. L2 produces the fundamental shape of the solution as a *design artifact* (a coherent picture of how the thing works), not a list of options.

### What L2 actually does

- **Identify the architecturally-significant decisions.** Not every decision — the ones that are expensive to reverse, cross module boundaries, or constrain everything below. Those are L2's to make.
- **Decompose to components + responsibilities + interfaces, then stop at sufficient resolution to delegate.** L2 carves down only until each piece is well-enough specified to hand to an L3 — and no further. Over-resolving robs the L3 of the decisions that are properly theirs.
- **Last Responsible Moment + subsidiarity.** Decide cross-module and expensive-to-reverse things **now**; **defer module-internal and domain-deep decisions downward, with constraints.** A deferred decision is not a gap — it is delegated *with the constraints that bound it*, and those constraints are exactly the rubric the L3 is later held to (D26). Subsidiarity: the decision is made at the lowest level that has the context to make it well.
- **Recognize and apply known patterns.** Where the problem matches a known shape, name and reuse the pattern instead of re-deriving it.
- **De-risk with spikes.** Where a decision turns on something unknown, run a spike to learn before committing. The **walking skeleton is the first and largest such spike** — an ungated, early end-to-end thread that proves the connections before the gated build starts (see "Walking Skeleton," below).
- **DDD is the carving sub-method inside this**, not a replacement for it. Domain-driven design is how L2 (and the planning-L3s) *find the seams* — bounded contexts, aggregates, where to cut. It sits inside the architect process, not above it. The full carving methodology is `DECOMPOSITION-METHODOLOGY.md`.

### Why L2 delegates (and why it isn't about capability)

L2 delegates downward for **role separation and context/bandwidth preservation, not capability.** The model below is the same model; an L2 *could* do an L3's detailed design, just as a director *can* do an associate's work — it's simply not the director's job, and doing it would clog the bandwidth the role exists to protect. **Domain expertise loads per-domain into the owning L3's loadset**, not into L2. L2 holds the cross-cutting architectural picture; each L3 holds the deep domain knowledge for its area.

### The substrate is established first

Before the feature areas, L2 establishes the **substrate**: the cross-cutting stable core that every feature area depends on — Money/value types, IDs, events, audit, the idempotency primitive, the base data model. This is **not a peer feature module**; it is the foundation the rest is built on, and it is **built first via the walking skeleton** (resolution B14). Dependencies point toward this stable core; nothing volatile sits at the center. The substrate's interfaces are the sockets the feature areas plug into.

### L2's output: ADR-style

L2's concept is delivered as:
- a **component map** (the major areas of work and how they connect),
- **interface contracts** between areas (the sockets, defined by the core),
- **ADRs** — one per architecturally-significant decision: the decision, its rationale, and a status (`decided` / `deferred`), and
- **per-module specs** in which the deferred decisions appear as **constraints** — i.e., the frozen rubric each L3 is held to (D26).

ADRs pull quadruple duty: they are the **handoff contract** to the level below, the **anti-drift anchor** the gate and reviewers check against, the **audit/optimizer substrate** (the optimizer-L1 reads decision history), and the **statelessness rationale-preservation** layer (a fresh instance recovers *why* from the ADRs, not just *what*). Each ADR and module is tagged with the intent IDs it serves (the trace-block obligation; see `PLAN-ALIGNMENT-GATE.md`).

### Provisional interfaces, progressive hardening

L2 is not the domain expert for every area, and upfront interface design is fragile — one mechanism resolves both. L2 proposes **coarse, provisional interfaces.** The domain-deep planning-L3 pressure-tests them against the area's real constraints and **renegotiates upward** where the coarse interface won't hold. The **walking skeleton runs early on these provisional interfaces** (not on negotiated/frozen ones) and feeds its findings back into the cascade — reopening the relevant ADR and the compatibility review where reality contradicts the concept (see "The Walking Skeleton," below). Interfaces are therefore **FLUID during the planning cascade and FROZEN only after the plan-alignment gate PASSes** — fluid exactly long enough to get them right, candidate-locked at the compatibility review, and frozen by the gate before any code is written against them.

**Pressure-test before freeze (not just prose).** A provisional interface is not made safe by labelling it "provisional." Before it can be frozen, the contract's **enums and ports must survive a pressure-test against execution reality** — the async flows and real keyspaces the build will actually exercise — performed by the planning-L3 renegotiation and the walking skeleton. A checker can observe this: the candidate contract carries evidence that each enum value and each port was exercised (a skeleton thread that traversed it, or a renegotiation note that revised it), not merely a "provisional" tag. The sim's lesson was concrete: an enum that could not express "accepted, pending confirmation" and a missing intent→order port both surfaced only under build pressure, after a premature freeze. Full statement in `DECOMPOSITION-METHODOLOGY.md` (Contract-first / provisional-interface hardening).

---

## Phase 3: Concept Validation (L2 → L1 → User)

L2 sends the concept back to L1. L1 evaluates it for **fidelity to intent** — does this serve what the user described? — not for technical quality, which is L2's domain. L1 guards: it checks the concept against the captured intent before anything reaches the user, and frames divergences concretely ("you said X; the concept does Y, because Z").

L1 surfaces to the user what the user asked to see (calibrated by the per-area fluency captured at intake — technical detail for fluent/opinionated areas, plain-language implications elsewhere) plus any genuine divergence from stated intent. The user approves, corrects, or redirects. This validation gate exists because a flawed concept produces flawed details at every level below, and no excellence in execution rescues a misconceived design.

This is a *concept-level* check on intent fidelity — it is **not** the plan-alignment gate. The plan-alignment gate (Phase 5) validates the fully assembled, distributed plan as a whole, after the planning cascade has detailed every area.

---

## Phase 4: The Planning Cascade (a coordinated round)

The approved concept is detailed by the L3 layer in a **single coordinated round**, not an open-ended fan-out. This is the design cycle's *Execute* phase: it produces the detailed plan, never code.

### Planning-L3s design in parallel

L2 spawns a **temporary planning-L3** per area. Each planning-L3 takes its area assignment (scope, constraints, the provisional interfaces, the resolved decisions that bound it) plus the full concept for context, and produces the area's detailed design as a `plan/area-{name}.md` in L2's planning workspace. It carries the domain-deep expertise for its area — this is where per-domain knowledge loads. The planning-L3 pressure-tests L2's provisional interfaces and renegotiates upward where needed.

**Threshold-gated split.** A *substantial* area warrants the planning-L3 / execution-L3 split — the planning-L3 collapses after producing the design, and a **fresh execution-L3** is spawned later to own and build it (clean-context separation of planning from execution). A *trivial* area collapses the split: no separate planning-L3 is worth the overhead. Depth is variable at the planning layer too (resolution M53; the split mechanics are C21).

### L2 compatibility review (the round closes here)

The planning-L3s submit their detailed designs together, and **L2 reviews them as a set** — this is the step that catches what parallel design cannot:
- Do interface contracts **match across areas**? If area A emits X and area B expects Y, it is caught here.
- Are there **gaps** — work no area claims?
- Are there **conflicting decisions** — area-level choices that contradict each other or the concept?
- Does the combination still **serve the concept** — do internally-sound areas collectively drift?

Cross-module interface ripples and renegotiations surface in this review. (This is the `parallel design → L2 compatibility review → lock` pattern confirmed in `ARCHITECTURE.md` §"Execution Strategy.")

### Candidate-lock the interfaces (freeze is a post-gate act)

Once the compatibility review clears, the interfaces are **candidate-locked, not frozen.** The compatibility review produces *candidate* interfaces — negotiated and cross-area-checked, but not yet contracts execution is held to. The **freeze is a distinct, later act that happens only after the plan-alignment gate (Phase 5) emits PASS.** A checker can tell the two states apart: a candidate interface lives in L2's planning workspace and is still editable by renegotiation; a frozen interface is the read-only `design.md` contract inherited by the fresh execution-L3, written only once the gate has PASSed. Sequencing is strict: **reflect-back confirmation (Phase 3) and the plan-alignment gate (Phase 5) both precede freeze.**

**Prohibition (no building on unconfirmed foundations).** Do **not** freeze, and do **not** let any area build on, a requirement that is still **reflect-back-pending** — i.e., not yet confirmed by the user in the Phase 3 reflect-back. A requirement in reflect-back-pending state is observable in the trace (it carries no `confirmed` mark); any candidate interface that depends on such a requirement is blocked from freeze until the dependency clears. This is the ordering bug the sim surfaced: interfaces were frozen before the gate ran, on unconfirmed foundations. The correct order is **reflect-back confirm → plan-alignment gate PASS → freeze.**

### Tests and rubrics are authored here, before any code

The planning cascade is also where the **anti-theater temporal rule** is enforced. Every level, during its plan phase, authors the **acceptance tests and review rubric for the level below — at planning time, before the work, from the spec, by an agent that is not the worker.** A level's Plan phase is not "done" until it has emitted spec + acceptance tests + gate rubric (the **Plan-phase output contract**). This anchors the work to the tests, never the tests to the work. The acceptance/rubric artifact is **frozen, per-unit, and read-only to the executor** (D26) — immutability is the anti-test-theater enforcement made physical, and the tests/rubrics live in the work node (see `WORKSPACE-SCHEMA.md`, `QUALITY-GATE.md`). At the L4→L5 junction this means an L4-tester lateral authors L5's acceptance tests from L4's spec before L5 codes.

The cascade's output is the **validated plan**: the frozen architecture doc + the N area designs + the workstream/task plans + the acceptance-test suites + the rubrics, plus the generated RTM. That bundle is what the plan-alignment gate consumes.

---

## Phase 5: The Plan-Alignment Gate

The single hard checkpoint between designing and building. It reads the **assembled plan as a whole** against the user's tagged intent and asks the one question per-level reviews structurally cannot: *does local fidelity at every step compose into global fidelity to intent?* It catches the three drift classes that survive local review — **gaps** (dropped requirements), **scope creep** (unrequested additions), and **semantic drift** (requirements traced but subtly wrong) — and it inspects its own first translation (intent prose → requirement IDs) rather than treating it as axiomatic.

Its success output is a **signed validated-plan artifact**, and its sign-off is **warm human sign-off** by the user — the one gate that cannot be delegated upward or automated away. No execution-L3 is spawned and no build harness is unlocked until the gate emits PASS. **The interface freeze is one of the acts the PASS authorizes:** the candidate interfaces from Phase 4 become the frozen, read-only `design.md` contracts only on PASS. Before PASS they remain candidate-locked and editable; freezing earlier (as the sim did) builds on foundations the gate has not yet validated. A checker observes the boundary as a state transition on the gate's signal: candidate (pre-PASS) → frozen (post-PASS).

The full design — dual cycles, requirements traceability and the generated RTM, the eight checks (atomization-completeness, forward/backward coverage, tag well-formedness, two-window blind reconstruction, adversarial comparison, evidence-specificity, whole-portfolio coherence, L1-triage-with-conflict-of-interest-fences, warm sign-off), incremental subtree re-gating, human-gate health monitoring, and the deliberate refusal of any fake alignment score — lives in `PLAN-ALIGNMENT-GATE.md`. This document does not duplicate it; it is the gate's place in the planning spine.

---

## Phase 6: The Build Cycle (Execution)

On PASS, the **build cycle** begins. A **fresh execution-L3** (a different agent from the planning-L3) takes its frozen, gate-approved area design and drives the build down through L4 and L5.

- **L3** owns the area: `design.md` is the frozen contract, `plan.md` is the living execution layer. It sequences workstreams by dependency and risk, mostly sequentially (2–4 L4s active), parallel only where areas are genuinely independent. Later work benefits from earlier results.
- **L4** decomposes its workstream into tasks against the area design. The **L4-tester lateral** (a separate agent — not the L4 coordinator, not the L5 coder) authored L5's acceptance tests from the spec during the plan phase; those tests are now frozen and read-only to L5.
- **L5** is an **execute–review pair.** The executor (Codex *harness* + GPT-5.5 *model*) writes the code and runs the pre-written acceptance tests + its own unit tests + **CI (the automated floor).** **L5+** — a *separate* reviewer agent on a **different runtime** (Opus) for judgment diversity — does its own testing and reviews against spec, then **accepts** (forward; both collapse) or **bounces** (the executor keeps its context and continues; bounded loop). Reviewers verify code against the *same* acceptance tests and rubrics frozen during the design cycle — they cannot be edited to match the code.

Cross-runtime briefing follows the runtime-neutral task contract + thin runtime adapter pattern: the semantic brief is identical across runtimes; only the tool manifest, harness invocation, and output format are runtime-specific, injected by the adapter at spawn. GPT-5.5 seats get maximally decision-complete briefs (they will not fill gaps with good architecture), acceptance tests as the primary anchor, and an explicit **escalate-ambiguity-don't-decide** rule. Full treatment in `runtime-and-model-map.md`. The model rule throughout: **Opus 4.8 for generative/architecture seats; GPT-5.5 (Codex harness) for pedantic/checking/execution seats.**

Each level's right-arm review gate verifies what it received against the frozen design and rubric it set (review at altitude — composition + fidelity, not re-doing the level below). Independent review at each level is **in for V1**, not deferred — it is integrated into each level's process (the L5/L5+ pair, the L4 right-arm gate, the L3 gate rubric). Detailed mechanics live in `QUALITY-GATE.md`, the level docs (`operational/L3/`, `operational/L4/`, `operational/L5/` — their `role.md` / `config.md`), and `runtime-and-model-map.md`.

---

## Phase 7: Integration and Delivery

Results flow up through the frozen contracts. Each level evaluates what it received against the design it set; artifacts are written at each level; the visibility graph and the bus carry the notifications (a message is a pointer/nudge — durable truth lives in the docs; see `COMMUNICATION.md`). When a parent has received all results from its children, it collapses them and synthesizes.

L2 does the final cross-area integration review — the areas were designed to compose; this confirms they actually do. L2 reports to L1: what was built, how it maps to the original intent, where the implementation departed from the concept and why. L1 shapes the delivery for the user — they receive the result framed for their needs, not a project report. The loop that opened at intake closes here.

---

## The Walking Skeleton (an early de-risking spike, not gated execution)

The walking skeleton is an **ungated, early de-risking spike** that threads one thin path end-to-end — through the substrate and across the area interfaces — to prove the connections hold before the architecture is frozen. It is **distinct from gated execution**: it *informs* the plan; the build cycle is the *gated* construction that follows PASS.

**Owner.** The **Project Architect (L2) spawns it** as a dedicated **throwaway spike thread** — a short-lived agent whose only job is to run the skeleton and report back. It is not a planning-L3 and not an execution-L3; it has a named owner so the feedback path and the discard rule have someone accountable to them.

**Address and workspace.** The spike gets a real **one-spine address** (e.g. `proj/_skeleton`) and a **workspace path** under L2's planning tree (e.g. `plan/_skeleton/`), same as any other node — so its findings, threads, and discard are all observable in the tree, not ad-hoc.

**When it runs — EARLY, on provisional interfaces.** The skeleton runs **after the concept (Phase 2), against the *provisional* interfaces** — *not* after the cascade against negotiated/frozen ones. This corrects the earlier self-contradiction: the skeleton does not "validate the negotiated interfaces" after they settle; it runs *before* they settle and is one of the forces that makes them settle correctly. Running early is the whole point — it surfaces integration reality while the contracts are still cheap to change.

**Feedback channel (defined, not implied).** Skeleton findings have a defined path back into the cascade: a finding **reopens the relevant ADR** and **feeds the L2 compatibility review / interface renegotiation** (Phase 4). A checker can observe the loop: a skeleton finding produces an ADR re-open entry and/or a renegotiation note on the affected candidate interface. The skeleton is a producer of pressure-test evidence for the enums/ports (see Phase 2's "Pressure-test before freeze").

**Throwaway / discard rule.** Skeleton code is a spike: **it is discarded and never enters the gated build.** No frozen `design.md`, no execution-L3, and no L5 commit inherits skeleton code; only its *findings* (ADR re-opens, renegotiation notes, de-risked decisions) survive. The workspace path is torn down or archived as throwaway after the cascade absorbs its findings.

**A separate store-backed spike for scary decisions.** The walking skeleton is typically **in-memory** and therefore cannot de-risk decisions that depend on real infrastructure behavior — concurrency, unique-constraint enforcement, transactional isolation, real keyspaces. For those, L2 spawns a **separate, store-backed spike** that exercises the real mechanism (e.g. a real DB enforcing a unique constraint under concurrent writes). Same owner/address/discard discipline; different fidelity. Do not assume the in-memory skeleton has cleared a decision that only the store-backed spike can clear.

(Building the AI-architecture system itself is being done walking-skeleton-first via the tabletop dry-run.)

---

## One Spine (requirement-IDs = addresses = paths = branches = rubrics = visibility)

A single hierarchical-path scheme runs through the entire process. The dotted requirement ID minted at intake (`R-003.2.1`), the agent's address (`proj/payments/gateway`), the workspace tree, the git branch, the rubric-file location, and the need-to-know visibility graph are **all the same hierarchical-path/prefix scheme.** A child ID is its parent dotted with a local index; a parent is recoverable by truncation; the visibility graph derives directly from the address (subtree = paths under; siblings = same-parent; parent = path minus last segment). Decided once, it serves the whole system. See `WORKSPACE-SCHEMA.md`, `PLAN-ALIGNMENT-GATE.md` (traceability), and `runtime-and-model-map.md` (addressing).

---

## Design Principles

### Each phase produces a design artifact, not a task list

Tasks emerge from designs. The tagged intent spec is an artifact. The L2 concept (component map + interface contracts + ADRs) is an artifact. Each area's detailed design is an artifact. Task decomposition happens at execution time, rolling, derived from the designs — not as the primary output of any planning phase. A task list with no design behind it has no coherence check; a design is a testable claim about how the thing works.

### Each artifact is validated before the next phase begins — and the whole plan once, as a unit

Intent is agreed before concept design. The concept is approved before the planning cascade. The detailed designs pass cross-area compatibility to produce *candidate* interfaces. And the assembled plan passes the **plan-alignment gate** as a whole before any code is written — and the **interface freeze happens only on that PASS**, never at the close of the compatibility review. Per-level fidelity does not compose into global fidelity, and catching drift at plan-time is the only point where the fix is cheap; freezing before the gate (as the sim did) locks in foundations the gate has not yet validated.

### Front-loaded design, rolling execution-planning — not a waterfall

The architecturally-significant decisions are made up front; the rest is deferred to the last responsible moment and planned just before it is built, so real information from earlier phases shapes later ones. Architecture is committed early and expected to *hold*; detailed plans are produced rolling and expected to *evolve*.

### Plan and execute are separated by clean context

Planning-L3 and execution-L3 are different agents; the parallel grilling session keeps L1's intake context clean; the gate is a contextual firewall the build cycle inherits the frozen plan through, never the design conversation. The producer of a heavy artifact and the steward of its distilled result are kept apart throughout (pointer-not-payload briefs: every level gets the distilled brief — spec + constraints + interface + ADRs — with raw upstream intent referenced, pullable on demand, not carried).

### Decisions are delegated, with constraints, to the lowest level that can make them well

Subsidiarity + Last Responsible Moment. A deferred decision travels downward as a *constraint*, and that constraint is the frozen rubric the level below is held to. Delegation is about role and bandwidth, not capability — the model below is the same model.

### Spawn-time role identity at every level

Every agent is spawned with a specific professional role identity, set by the level above — not to inject knowledge (the model already has it) but to inject a *lens*: which aspects to foreground, which best practices to default to, which risks to watch for. Positive boundary framing over persona ("soul") elaboration; the framing principles live in `agent-definition-principles.md`. Domain expertise carries default priorities that the user or the level above can override but need not specify.

### Derived from real-world professional services

Architecture firms, management consulting, software solution design — the source disciplines, not analogies. They independently evolved the same pattern because they solve the same problem: turning a client's intent into a built thing through coordinated expert effort. The agent hierarchy instantiates this pattern with LLM agents instead of human professionals; the cognitive sequence is the same.

---

*Created: 2026-03-29*
*Reframed: 2026-06-02 — intake / L2-architect-process / planning-cascade / dual-cycles + plan-alignment gate; 5-level model; front-loaded design with rolling execution-planning. See `working-notes/consolidation-plan-2026-06-02.md`.*
*Anchors: `DECOMPOSITION-METHODOLOGY.md`, `PLAN-ALIGNMENT-GATE.md`.*
