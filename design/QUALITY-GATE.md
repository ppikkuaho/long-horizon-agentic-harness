# AI Architecture — Quality Gate System (Process Design)

Level 5 process design document. Governs how **code-level output quality** is verified at each level boundary during the build cycle. Constrained by: ARCHITECTURE.md, DESIGN-PRINCIPLES.md (especially P4 and P17).

**Scope note — two review layers, one spine.** This document covers the **code-level review** that runs *inside the build cycle*: it verifies that produced work (code, integration, composition) is correct and faithful to its frozen spec. It sits *below* the **plan-level review** described in `PLAN-ALIGNMENT-GATE.md`, which validates the assembled *plan* against user intent *before any code is written*. The plan-alignment gate is the single design-cycle→build-cycle gate; the quality gates in this document are the per-boundary build-cycle gates. They share the same hierarchical-path spine: requirement-IDs = agent-addresses = workspace-paths = git-branches = rubric-locations = the visibility graph (`F35`, WORKSPACE-SCHEMA.md). The rubrics and acceptance tests these gates check against were authored and **frozen during the design cycle** — they cannot be edited to match the code (see `PLAN-ALIGNMENT-GATE.md`).

---

**General principle:** Every output passes through independent evaluation before it moves upward in the hierarchy. This is a structural function — an independent reviewer at each level boundary, not within the producing hierarchy. The producing level never signs off on its own work (`D23`, P4).

**Why:** Producers structurally cannot objectively evaluate their own work. This isn't about deception — agents report honestly. It's about competence: LLMs systematically overestimate their own output quality. The gap between "I think this is good" and "this is actually good" is where quality escapes. Independent evaluation closes that gap. **Reviewer ≠ producer at every boundary** is the load-bearing invariant.

## Review at Altitude (D24)

The five levels separate by **kind of thinking**, and review separates the same way. **Each level's gate reviews the composition the producing level actually performed — not the work of the levels beneath it.** A gate never re-does lower-level review; that work was already gated when it crossed its own boundary. Re-checking it is wasted cost and erodes the producing level's accountability.

What each boundary reviews:

- **L5 gate — unit + CI.** The leaf execution boundary. Does this single unit of code do what its frozen acceptance tests and rubric require? Unit tests pass, the automated CI floor is green (`D28`), the code meets the per-dimension standards for a single right-sized piece of work. This is the only level that reviews code *at the line*.
- **L4 gate — workstream integration.** L4 composed several L5 units into a workstream. The gate reviews *that composition*: do the units integrate, do interface contracts hold across them, is the workstream internally consistent, are there cross-task conflicts? It does **not** re-review each unit's lines — those passed the L5 gate.
- **L3 gate — module composition.** L3 composed workstreams into a coherent module/area. The gate reviews module-level coherence: internal consistency of the module, the interface contracts the module exposes, cross-workstream conflicts inside the module.
- **L2 gate — product composition.** L2 composed modules into the product. The gate reviews system-level integration: architectural fit, cross-module interface contracts, system coherence, cross-area conflicts, fit to the architecture L2 itself laid down.
- **L1 gate — client intent.** *(Authority ruling 2026-06-11: user-rendered verdict is the REAL-USE contract; during test/commissioning L1/operator renders it against the frozen intent-spec — see INTAKE-TO-DELIVERY §Stage-5 note.)* The top boundary. Does the assembled product do what the client actually wanted? This is **intent-fidelity**, and it is reviewed by the *user* — L1 guards intent and presents a triangulated playback; the user renders the verdict. (This is the build-side mirror of the design-side plan-alignment gate; the same warm-diff, no-fake-score discipline from `PLAN-ALIGNMENT-GATE.md` applies.)

Each gate reviews at its own altitude. The composition gets richer and the granularity coarser as you go up; the *fidelity* question stays sharp at every level because each level was handed a frozen spec to be faithful to.

## Reviewer ≠ Producer at Every Boundary (D23 / P4)

The independent reviewer at each boundary is **structurally separate** from the producing level — not spawned by it, not part of its hierarchy, not sharing its authoring lineage. Review is a **per-level function, not a department or parallel room**: it is a role-variant **`#review` seat co-located at the node**, addressed on the same spine via a suffix (e.g. `proj/payments/gateway#review` vs `…#exec`, per `F35`). The function has two instantiations — **per-unit L5+ review** (an independent Opus reviewer seat per task) and **whole-set L4-level review** (after all the L5 units in a workstream finish). It is not a standing coordinator that sits alongside the level; it is review work integrated at each boundary, spun up against the node the producing seat is acting on.

The reviewer at this boundary is:

- **Structurally independent** from the producing level (reviewer ≠ producer is the invariant, not a preference).
- **Persistent across reviews** (accumulates context — knows what's already been approved, sees patterns across the level).
- **Configurable per project** (which dimensions, what standards, how many reviewers).
- **Not antagonistic** (catching competence gaps, not deception).

When work arrives, the coordinator:

1. Selects which review dimensions apply (from project-configured presets).
2. Sizes the work into reviewable units — if the scope is too large, decompose further (`P17`).
3. Spawns individual reviewers: one agent, one dimension, one right-sized piece of work, clean context.
4. Collects reports, synthesizes into pass / fail / revise.
5. Clears the work upward or kicks it back to the producing level with specific, typed issues.

**Model assignment for review seats (E31/E32 model-perspective rule).** Checking, pedantic, adversarial, and execution-verification work is GPT-5.5's strength (literal, engineering-brain pedantry); generative/architecture judgment is Opus 4.8's. So pedantic dimension-reviewers and the L5+ execution-reviewer lean GPT-5.5, while composition/judgment review at the higher altitudes leans Opus. The L5+ reviewer is deliberately run on a **different runtime from L5** for judgment diversity (see `runtime-and-model-map.md`). Reviewers are spawned through the runtime-neutral spawn contract (`E32`): the dimension + rubric + code-under-review is the runtime-neutral core; the runtime adapter injects the tool manifest and harness invocation.

## Gate vs. Parent Evaluation (Separate Functions)

The gate handles **output quality verification** — does the work meet standards across configured dimensions? This is a structural check by an independent reviewer at the boundary.

The parent level's **own evaluative judgment is separate and continues independently.** When L4 receives gate-cleared L5 work, it still evaluates process, approach, steps taken, and decisions made from its own frame. When L3 receives gate-cleared workstream output from L4, it still assesses whether the approach was sound, whether the right tradeoffs were made, whether the work fits the area direction. When L2 receives gate-cleared area output from L3, it still assesses whether the work fits the product's strategic direction. The gate tells you the output meets quality standards. The parent tells you the work was done *well* — right approach, right priorities, right decisions along the way. Different questions, different evaluators.

The gate does not replace or reduce the parent's judgment role. A parent that defers to "the gate approved it" has abdicated its own function.

## The L5 / L5+ Execute-Review Pair (M52) and the L4-Tester Lateral (M51)

The leaf boundary has a specific, anti-theater shape that the higher gates generalize.

**L4-tester lateral (M51).** A *separate* agent — not the L4 coordinator, not the L5 coder — authors L5's executable acceptance tests **from L4's spec, before L5 writes any code**. This is a second independent reading of the spec and it keeps L4's coordinating context clean. For V1, L4 owns authoring the executable acceptance tests directly via this lateral; a fully-dedicated standing test-writer role is a post-V1 maturation. The tests + the review rubric become a **frozen, per-unit, read-only-to-the-executor artifact** in the work node (`…/stripe-client/acceptance.md`, separate from `brief.md` and `report.md`), ID-tagged so it feeds the RTM (`D26`).

**L5 = execute (M52).** L5 is the **Codex harness running the GPT-5.5 model** (terminology: Codex is the *harness*; GPT-5.5 is the *model* — OpenAI no longer ships "codex" *models*). L5 writes the code, then runs the pre-written acceptance tests + its own unit tests + **CI, the automated floor** (`D28`). L5 makes the frozen tests pass; it cannot edit them.

**L5+ = review.** A *separate* agent (Opus, on a different runtime from L5 for judgment diversity) does its own testing and reviews the code against the spec and the frozen rubric, then either:
- **accepts** → forwards upward; the L5/L5+ pair collapses, or
- **bounces** → L5 *keeps its context* and continues iterating (a bounded bounce-back loop, `D29`).

**Why L5+ is load-bearing — acceptance tests anchor only what they assert.** CI + the frozen acceptance suite verify exactly the assertions they encode and nothing else: a green suite proves the code satisfies the conditions someone thought to write down at planning time, not that the code is faithful to *every* locked constraint. An executor can therefore pass every test while diverging from a constraint the tests do not probe. This is not hypothetical — it was demonstrated in the finishing-pass end-to-end simulation: the L5 executor derived a key from the wrong source, **passed all 17 acceptance tests, and reported zero escalations**, because no test asserted *which* source the key had to come from. The divergence was invisible to CI and to the suite by construction; only the independent L5+ reviewer, reading the code against the frozen spec rather than against the test assertions, caught the contract-fidelity violation. **The behavioral claim:** L5+ checks what CI + acceptance tests structurally cannot — it reads the produced code against the full frozen constraint set (the spec, the locked decisions, the derived-requirement serves-links) and flags fidelity divergences in regions the assertions leave unprobed, producing a fidelity finding even when the entire suite is green and the executor's self-report is clean. Tests-as-anchor is **necessary but not sufficient**: the suite catches the asserted class deterministically; L5+ exists to verify contract fidelity *beyond* what the tests assert. A green suite with no L5+ finding means "passed every assertion *and* an independent reader confirmed the code honors the constraints the assertions don't cover" — a strictly stronger guarantee than CI green alone, and the one the gate actually certifies.

**The temporal anti-theater rule (M51), generalized up the cascade.** Acceptance tests and review rubrics are authored at **planning time, before the work, from the spec, by someone other than the worker** — so the work is anchored to the tests, never the tests to the work. This is not an L4-only habit: **every level, during its Plan phase, authors the pass-conditions for the level below before that level executes** (`D26`). A level's Plan phase is not "done" until it has emitted spec + acceptance criteria + gate rubric — that is the **Plan-phase output contract**. The rubric is frozen and read-only to the executor; immutability is the anti-test-theater enforcement made physical (`D26`).

## Rubrics + Pass-Conditions Authored at Planning Time (D26)

Each delegating level authors the pass-conditions for the level below **at planning time, at its own altitude**:

- L1 authors the intent-fidelity criteria the assembled product is judged against.
- L2 authors the system-composition rubric L3 is held to (the per-module specs where L2's deferred decisions appear as **constraints** — these are ADR-derived; see `agent-definition-principles.md`).
- L3 authors the module-composition rubric for its workstreams.
- L4 (via the L4-tester lateral) authors the executable acceptance tests + dimension rubric L5 is held to.

Each rubric is a **frozen, per-unit, read-only-to-the-executor artifact** living in the work node on the shared path spine (`D26`, `F35`). It is written once, at planning, and is immutable to the producer — the executor reads it but cannot revise it. The same rubric the producer reads is the rubric the gate's reviewers and the L5+ reviewer read; there is exactly one frozen standard per unit, ID-tagged into the RTM.

## Two Axes: Quality + Fidelity, Fidelity Dominant (D27)

Every gate scores on two independent axes:

- **Fidelity (drift) — dominant.** Does the output do what its frozen spec/rubric/acceptance tests require? Drift from spec is the system's #1 failure target (`J43`). A correct, well-crafted unit that solves the wrong problem fails fidelity, and fidelity dominates the verdict. This axis is why rubrics are frozen and authored by not-the-worker: fidelity can only be judged against a standard the producer could not move.
- **Quality.** Independent of fidelity — is the work itself good? Correctness, security, code quality, testing adequacy, performance, etc. A unit can be faithful to spec yet poor quality (or vice versa); the gate scores both.

When the two conflict, **fidelity wins**: a beautifully-built deviation is still a deviation. Exec-quality optimization is explicitly the *second* priority — get fidelity right first, then drive quality (`J43`).

**Coding-project dimension presets.** Quality decomposes into dimensions selected from a preset library — correctness, security, spec compliance, code quality, testing adequacy, performance, etc. Each dimension gets its own reviewer agent with a clean context, the code under review, and the standards for that single dimension. The coordinator synthesizes the independent reports into a merge decision. **Review dimensions are configurable presets** — L2 or the project config defines which apply; a security-critical system gets all dimensions, an internal tool gets a lighter profile. See `sources/code-review-dimensions-research.md` (17 dimensions identified, 9 genuinely independent, natural 4-tier preset structure).

**Generalizes to any domain** (post-V1; V1 is software-building): research output evaluated for methodology and sourcing; strategic plans for feasibility and coherence; documents for accuracy and completeness. Dimensions change, the two-axis structure doesn't.

## CI/CD = The Automated Floor (D28)

CI/CD is the **automated quality floor**, not the gate itself. Everything machine-checkable — compilation, the test suite, linters, type-checks, mandatory security scans — runs as CI and must be green *before* a human-or-agent reviewer spends judgment on the work. The floor catches the mechanical class of defect deterministically and cheaply, so the independent reviewers at each boundary spend their scarce judgment on what only judgment can catch (fidelity drift, design fit, subtle correctness).

CI is the L5 unit's first gate: L5 runs it in-session as part of the execute step before L5+ ever reviews. The exact CI check-set is per-language/per-runtime and configured at the project level (one of the owed free-parameters: mandatory checks per runtime, and in-session vs external-hook execution — see the runtime-and-model-map).

## Big-Bang Gates, Parallel Execution Below, Escalation Channel (D25)

Each level boundary is a **big-bang gate**: the producing level's composed output is reviewed as a unit when it crosses the boundary, not trickle-reviewed piece by piece (piecewise review at the wrong altitude re-does lower work and misses composition defects). **Below the gate, execution runs in parallel** — many L5 units, many workstreams proceed concurrently; the gate is the synchronization point where the parallel work is composed and checked together.

A pure big-bang gate would discover problems late, so it is paired with an **escalation / early-warning channel** (`D25`). Producers don't wait for the gate to surface a blocker: when an executing unit hits ambiguity, a contradiction in its spec, or a problem it cannot resolve at its altitude, it **escalates early** rather than guessing. For cross-runtime L5 (GPT-5.5), this channel is load-bearing: GPT-5.5 is briefed to **escalate ambiguity, not decide it** (it won't fill spec gaps with good architecture), so the L5→L4 escalation channel must be reliable (`E32`). Escalation and early-warning run over the **bus** (real-time transport) with the durable detail in **docs** (`F33`, COMMUNICATION.md) — a message is a pointer/nudge; truth lives in the docs, so best-effort delivery is fine.

## Bounded Bounce-Backs + Neutral/Tentative Findings (D29)

**Bounded bounce-backs.** When a gate rejects, it kicks back to the producing level with specific issues — but the bounce loop is **bounded** (loop-cap N, a configured free-parameter). The producer keeps its context across bounces (it doesn't re-spawn cold). If the loop-cap is hit without convergence, the issue **escalates** to the parent level rather than thrashing indefinitely — repeated failure to converge is itself information that the spec, the decomposition, or the unit sizing is wrong, and that is a parent-altitude decision.

**Neutral / tentative findings.** Reviewers report findings **neutrally and with calibrated confidence**, not as confident verdicts. A reviewer that is *unsure* says so — a tentative "this may violate the idempotency contract, low confidence" is a first-class finding, not noise to be suppressed. This counters two failure modes: false-confident rejections that waste bounce cycles, and false-confident passes that launder drift. Tentative findings route to the synthesizing coordinator (and, for fidelity-relevant uncertainty, surface upward as explicit uncertainty rather than being collapsed to a binary) — the same "never collapse genuine uncertainty into a confident summary" discipline the plan-alignment gate uses for two-window disagreement.

## Independent Review at Every Boundary IN for V1 (D30)

Independent review at every level boundary is **in scope for V1**, not deferred. The earlier "defer post-V1" stance is superseded. The reasoning: the system's entire value proposition is faithful, high-quality output at scale; deferring the independent-review structure would ship the exact failure mode (producers grading themselves) the architecture exists to prevent. V1 ships the reviewer-at-each-boundary structure with the configurable-preset dimension library and the L5/L5+ pair as the leaf instantiation.

## Citation Ledger and Incident Log

When a gate rejects work, two things happen:

**Citation ledger** — a persistent file per level, shared across all instances of that level within the project, loaded at spawn. Contains:
- Running count of gate rejections.
- Brief summary of each (what dimension/axis failed, one-liner).
- Pattern highlights ("3 of last 5 rejections were fidelity-drift").

The ledger creates behavioral pressure — an agent that sees "you have 7 citations, 4 for inadequate testing" pays more attention to testing. This leverages the LLM's training on accountability signals.

**Incident log** — linked file with full details of each rejection: the lesson learned, what the gate found, what should have been different. Available for deep study but not loaded at boot (keeps context light). New instances inherit accumulated lessons without repeating old mistakes (the statelessness backstop, `G38` — persistence is optimization; correctness must survive a cold instance).

## L1 / Optimizer-L1 Visibility

Gate rejections are escalated as **signals** to L1 and to optimizer-L1 — not prompts to act. Both receive notification with access to the rejection report via the bus, and can observe how the producing level handles it without intervening, or act if they see a pattern. Visibility follows the **need-to-know visibility graph** (`F34`), with L1 / optimizer-L1 holding the god-view across the portfolio: L1's dashboard collects all citation ledgers for system-level quality oversight; optimizer-L1 mines them for recurring-issue patterns (see IMPROVEMENT-WORKSPACE.md). This replaces the old broad project-wide read — non-god-view agents see only their subtree + siblings + parent.

## Pre-Submission Checklist (Quality at the Source)

Inspired by CI/CD pipelines and Toyota's "don't let the defect leave the station" principle. Each level runs a structured self-check before reporting work complete:

- Specific items per level: tests pass, CI green, spec/fidelity compliance verified, security considered, quality self-assessed against the frozen rubric.
- Part of the level's loadset — mandatory, not optional.
- Checklist output is included in the level's report to its parent.
- The goal: catch most issues at the source. The gate should ideally find nothing.

## Feedback Loop (Human-Overseen)

When the gate catches something, it generates two outputs:
1. The rejection (goes back to the producing level immediately, bounded per `D29`).
2. A **proposed process improvement** — e.g., "add concurrency edge-case check to L5's pre-submission checklist."

The proposal goes to the **user** (via L1 dashboard / escalation) and to optimizer-L1 as a pattern feed — it is **NOT implemented automatically**. Information accumulates freely (citation ledger, incident log). But changes to configuration, checklists, loadsets, or process require human approval and often human design.

**Why:** An LLM modifying its own quality criteria is a self-referential loop. It could tighten in wrong directions, add irrelevant checks, or drift standards. All system-level changes are human decisions. The system proposes, the human disposes.

## Anti-Pattern: Externalizing Quality to the Gate

The gate exists as a **safety net**, not as a substitute for quality. If producing levels start treating the gate as their QC department — lowering their own standards because "the gate will catch it" — the system has failed. This is the nightmare scenario.

Each level is **fully accountable for its own output quality.** The pre-submission checklist, the self-verification, the CI floor, the craft standards — these are the primary quality mechanisms. The gate is there for the cases where self-assessment misses something despite genuine effort. A well-functioning system has gate rejection rates approaching zero, because producers are doing their own QC seriously.

The moment a producing level externalizes quality responsibility to the gate, two things break simultaneously: the producer's output quality drops (they stop trying as hard), and the gate gets overwhelmed with issues that should never have reached it. The gate's value comes precisely from being a rarely-triggered backstop, not a routine filter.

**Detection signals:** Rising gate rejection rates, rejections for issues the pre-submission checklist should have caught, producers submitting work faster than quality self-checks would allow. The citation ledger makes this pattern visible — if citations are climbing, the question is whether the producer is learning from them or leaning on them. Optimizer-L1 watches this trend across the portfolio.

## Toyota Design Rationale

The quality gate borrows from the Toyota Production System:
- **Quality at the source** — the primary quality mechanism is the producing level's own QC (pre-submission checklist + CI), not the gate.
- **Gate findings are failures** — the goal is zero gate rejections. The gate catching something means the producing level's process failed. Not antagonistic, but accountable.
- **Poka-yoke (mistake-proofing)** — the frozen, read-only rubric and the automated CI floor make certain classes of error structurally impossible to miss, not dependent on the agent "remembering."
- **Continuous improvement** — gate findings feed back as proposals to improve upstream processes. The system gets better over time, but only with human oversight on changes.

## Related Documents and Principles

- `PLAN-ALIGNMENT-GATE.md` — the **plan-level (design-cycle) review** that sits *above* this code-level review; validates the assembled plan against intent before any code is written. Shares the hierarchical-path spine and the frozen rubrics this gate later checks against.
- `DECOMPOSITION-METHODOLOGY.md` — how work is carved into the units this gate reviews (deep-modules-as-rubric; C4 + DDD + SDD + hexagonal ports as the backbone).
- `runtime-and-model-map.md` — per-level model/runtime assignment, the model-perspective rule, and the cross-runtime spawn contract reviewers are spawned through.
- `agent-definition-principles.md` — ADR-derived constraints that become L2's rubric for L3; thin-but-decision-complete briefs.
- `WORKSPACE-SCHEMA.md` — the work-node layout where `acceptance.md` (frozen rubric), `brief.md`, and `report.md` live on the shared path spine.
- `COMMUNICATION.md` — the bus + docs transport the escalation/early-warning channel and gate signals run over.

These principles from DESIGN-PRINCIPLES.md are directly relevant:
- **Principle 4: Trust Intent, Verify Competence** — trust reporting, independently verify output quality (the reviewer ≠ producer invariant).
- **Principle 17: Right-Size Every Cognitive Task** — one agent, one task type, one dimension, right-sized for depth.

---

*Created: 2026-03-17. Rewritten: 2026-06-02 to the 5-level review-at-altitude model (D23–D30), with the L4-tester lateral (M51) and L5/L5+ execute-review pair (M52). Supersedes the 4-level framing, filesystem-inbox transport, broad-read visibility, and the "independent review deferred post-V1" stance.*
*Status: Standalone Level 5 process design document — the build-cycle quality layer, paired with PLAN-ALIGNMENT-GATE.md as the design-cycle alignment layer.*
