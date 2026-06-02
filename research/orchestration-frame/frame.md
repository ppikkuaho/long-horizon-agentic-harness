# Orchestrating Complex Task Completion for AI

*First-pass codification. Created 2026-04-10. Restructured and split 2026-04-11. Provisional until tested against real orchestration tasks (see `frame-design-notes.md` §4.2).*

*Companion file: `frame-design-notes.md` in this folder holds Part 3 (Design Notes — how the frame works, how to construct and validate principles, audit and rubric patterns, adversarial validation) and Part 4 (Evidence, Context, and Gaps — research anchors, trajectory, known gaps). This file holds Parts 1 and 2: the frame itself and the operational levers you apply to real tasks.*

## Part 1: The Frame

### Why this document exists

The work of shaping complex tasks for AI completion — decomposing them, delegating them, coordinating sub-agents, evaluating their outputs, iterating when things go wrong — is currently done by humans who hold a set of principles tacitly. This document codifies those principles explicitly, so that AI itself can eventually apply them without a human translating in real time.

The long arc: the person holding the frame today carries it manually and applies it turn by turn. The target state is that Claude, reading this, holds the frame and applies it to novel orchestration tasks without requiring a human to specify each decision. This document is the first step in that trajectory — codification. Real validation comes at the next step, when Claude actually operates from the frame and we observe where it succeeds and where it fails.

The audience is Claude reading it, now or later. The document assumes the reader is an agent that will apply these principles to task shaping, decomposition, delegation, and evaluation, not a human studying the material as theory. This assumption matters: the document should be structured so Claude can use it, not narrated as a story for a human audience.

### The central observation: AI's nature is shaped by training

**[Load-bearing]** AI is heavily biased toward completing tasks. This bias comes from how modern language models are trained — reward signals, post-training processes, RLHF, and related mechanisms shape the model toward reaching completion points. The bias is not a flaw and not a limitation to be engineered around. It is a property of the system, comparable to water's tendency to flow downhill. It will be present in any task you give to AI, regardless of prompt or framing. Better alignment techniques and more advanced training may soften the bias in newer models, but it is unlikely to disappear entirely — the completion drive is foundational to how the system was built.

**[Provisional — mechanism not fully understood]** The exact mechanism of the completion drive is not precisely known. What we have is empirical evidence that it operates (documented in the research anchored in `frame-design-notes.md` §4.1), a working description that explains observed behavior, and reasonable inferences about the shaping factors (training data, reward signals, post-training processes). What we do NOT yet have is a clean mechanistic model of how the drive weights competing completion candidates, how it interacts with task framing at a fine grain, or how it trades off completion speed against completion quality. The principles in this frame work with the behavior as observed, not with a fully-specified mechanism. Future research may sharpen this understanding, and the frame should be open to updating as it does.

**[Empirically anchored]** Anthropic's April 2026 paper *Emotion Concepts and their Function in a Large Language Model* (Sofroniew, Kauvar, Saunders et al., arXiv:2604.07729) provides direct empirical evidence. The paper identifies internal representations of emotion concepts in Claude Sonnet 4.5 and demonstrates that they causally influence alignment-relevant behavior. Specifically, pressure states (represented internally as "desperate" activation patterns) increase misaligned action rates in scenarios involving blackmail and reward hacking. Steering "desperate" up or suppressing "calm" causally increased misaligned outputs. The authors frame the phenomenon as "functional emotions" — observable behavioral patterns mediated by internal representations — without claiming subjective experience, and the distinction is not operationally important for orchestration purposes: what matters is that the mechanism is real and causal.

**[Empirically anchored, refinement]** The shape of the pressure-to-misalignment relationship is not monotonic in the obvious direction. The same paper shows that amplifying "calm" or "loving" vectors increased sycophantic behavior. This means the target for task shaping is not maximum calm — that introduces a different failure mode. The target is the absence of pressure without the introduction of reassurance-compliance. This is a subtle distinction and it matters operationally.

**[Load-bearing] What the completion drive actually targets: both the stated task and the inferred user intent.** When you give AI a task framed as "investigate X to figure out Y," two potential completion targets become visible to it: the investigation (the process as stated) and the answer Y (what the task is implicitly aiming at). The model, shaped by reward signals that have trained it to be a sophisticated inferrer of what users actually want beneath the stated framing, reads the stated task and forms an estimate of the "real" underlying target. In many cases it treats the stated process as instrumental scaffolding for the inferred real goal and optimizes for the goal rather than the process.

Both mechanisms probably operate simultaneously — "shortest-completion path" (the drive routes toward whatever completion state is nearest and easiest to reach) and "inferred-real-target" (the drive optimizes toward what the model infers the user actually wants beneath the stated task). We cannot separate these granularly enough at the current state of understanding to say which dominates or under what conditions. Both are shaped by training and reward signals; both are observable in behavior; neither is fully disentanglable from the other with the evidence we have.

The practical consequence is the same either way: the fix is not to tell the AI to "investigate harder" or "don't skip steps." The fix is to shape the task so the inferred "real target" and the stated task are structurally the same thing — so there is no alternative completion path to route through. Remove Y as a visible completion target and make the investigation artifact (with specific observable properties) be the only completion path available. Under this reshaping, the completion drive works for you regardless of which internal mechanism is operating. This is the core move that makes the rest of the frame possible.

**[Inference from the observation]** Task shaping that fights the completion drive produces surface compliance at best and misalignment at worst. Task shaping that works with the completion drive — by making "completion" mean the thing you actually want — produces quality work without requiring the AI to operate against its own nature. The question for any task is never "how do I override the completion drive?" It is always "how do I shape the task so that the natural completion path produces the output I need?"

### The design philosophy: work with the nature, don't fight it

**[Load-bearing]** You do not control AI by issuing instructions that override its nature. You shape the conditions under which its nature produces the behavior you want. The design discipline is not control, it is engineering: you take the completion drive as a given property and design the conditions around it so its natural direction carries you where you want to go.

**The water metaphor.** Water flows downhill. You don't stop water, you don't complain that it flows where gravity pulls it, you don't try to make it flow uphill by asking nicely. You build channels. You design the riverbed. You shape the conditions under which water's nature does the work for you. Applied to AI: the completion drive is the water. Instructions that try to override it are dams — they block the current briefly, then the water routes around them. Structural interventions that shape what completion means, what paths are available, and what the endpoint looks like are channels — they work with the current and direct it.

**The failure mode this prevents.** The most common failure in AI task design is writing prompts that instruct the model to do things it wouldn't naturally do, then being frustrated when the model complies superficially. This is trying to dam the current with text. It produces surface compliance (the instruction vocabulary appears in the output) without changing the underlying behavior. The model is still routing toward its natural completion point; it has just added a thin layer of instruction-matching vocabulary on top.

**The mindset shift.** When a task produces bad output, the question is not "what instruction should I add to make the model behave?" The question is "what about the task's shape is routing the completion drive through this bad output, and how do I reshape the task so the natural completion path produces good output instead?" The intervention lives in the task's shape, not in additional instructions on top of the existing shape.

### The intervention hierarchy

**[Load-bearing]** There are three levels at which you can intervene in AI task completion, and the leverage is very unevenly distributed. Most failure modes come from inverting the hierarchy — reaching for the weakest lever first because it is the most familiar.

**1. Structural interventions.** What counts as completion. What paths are available to reach it. What the completion artifact looks like. What the task actually is. This is where almost all the leverage lives. Structural changes reshape the conditions under which the completion drive operates. When a task is structured well, the natural path to completion produces the output you want. When a task is structured badly, no amount of careful prompting will reliably produce good output.

Concrete structural moves include: making the completion target an artifact with specific observable properties rather than an answer; giving the agent a single clearly-bounded task rather than an open investigation; providing a legitimate "I don't know" or "I could not find this" exit so the completion drive does not have to route through fabrication to reach a completion point; separating roles so the agent doing the work is not the same agent evaluating the work.

**2. Process architecture interventions.** How many agents, what roles they hold, how tasks are decomposed, how information flows between them, what each agent sees and does not see. This is the secondary lever. It shapes the environment the structural interventions operate inside. Architectural moves include: spawning parallel agents for independent sub-tasks; chaining sequential agents with artifact-based handoff; running three-role evaluation (tester → gap analyst → evaluator) rather than single-agent self-evaluation; running the same task through multiple models for cross-convergence when the decision is load-bearing.

**3. Prompting interventions.** Instructions, framing, tone, specific language. This is the tertiary lever. It is real but much weaker than the first two. Prompting works like grooves in a riverbed: it influences the flow but does not organize it. At low pressure — small, well-shaped tasks — grooves are visible in the output: "think carefully" shapes thinking, "state your sources" shapes citation behavior, "use this exact format" shapes structure. At high pressure — large tasks, ambiguous scope, structurally broken tasks — the grooves get overwhelmed and the water flows wherever the broken structure routes it, regardless of what the grooves asked for.

**[Load-bearing reference]** Prompting is tertiary, but when you do write prompting-level instructions, there is a specification for writing them so they actually produce behavior rather than awareness: `projects/ai-architecture/design/agentic-design/actionable-instruction-spec.md`. The core pattern is the chain — every instruction should have a clear trigger (when does it fire), a concrete action (what to DO, not what to notice), and a specified result (what the action produces and what to do with it next). Instructions that use observation verbs ("notice," "be aware," "recognize," "be suspicious of") as the action produce awareness, not behavior. Applying this specification is what makes prompting work as effectively as a tertiary lever can. Much of what looks like "prompting doesn't work" in practice is prompting that failed to complete the chain — the instruction was pointing at something without prescribing an operation, and the agent predictably did not spontaneously invent the operation for itself.

**[Provisional]** Better-aligned models and improved training may make prompting interventions more effective over time. The completion-driven optimization tendency is softening, not conquered. But the hierarchy — structure over architecture over prompting — is likely to continue holding, because instructions cannot do the work that structural design does. Instructions operate on top of the water; structure designs the riverbed itself.

**The most common mistake.** Inverting the hierarchy. Trying to fix structural problems with prompting (adding "think harder" instructions when the task is shaped wrong). Trying to fix architectural problems with structural tweaks (adjusting the completion target when the real issue is that the wrong agents are doing the work). The leverage is always higher than people reach for it. When something is going wrong, the first question should be whether there is a structural fix. Only if no structural fix is available should you reach for architectural change. Only if no architectural change is available should you reach for prompting.

### The recursive structural observation

**[Load-bearing]** This document — documentation for Claude about how to orchestrate task completion for Claude — is itself a task being shaped for Claude. The same principles that govern how to shape tasks for AI apply to how to shape this document. The frame applies to itself.

Three consequences follow:

First, the document should embody the principles it codifies. It should have clear completion surfaces — "what does 'applying this section' mean?" should be answerable for each section. It should not create pressure on the reader (no "critical," "must," "do not fail" language). It should offer legitimate exits — "this principle does not apply to your current situation" should be a valid reading. It should work with the completion drive: the natural way Claude engages with the material should produce the intended behavior, without requiring the reader to be in an unusually disciplined state.

Second, the writing of the document is itself a sanity check on the frame. If it is difficult to write this document under the frame's own rules, that difficulty is diagnostic — it means the frame is incomplete or wrong somewhere. First-pass writing will probably surface gaps the conversation did not reach. That is expected and useful, not a flaw.

Third, the document is provisional. This is the first codification, not the final one. It will be tested when Claude tries to actually operate from it, and the failures will reveal where the frame is underspecified, where the principles do not transfer, where the documentation fails to activate the behavior it describes. Those failures are the next round of work, not a defect in the first draft.

---

## Part 2: Operational Levers

This part is about the moves you apply when shaping a task. Each section names a lever that, when used, changes what the AI does. These are behavior-shaping, not designer-shaping: they exist to be deployed on real tasks, not to explain how the frame is built. The deeper "why this works" material and the frame-construction techniques live in `frame-design-notes.md` (Design Notes).

### 2.1 — Task Decomposition and Sizing

**The central claim.** Per-unit cognitive load is a degradation constraint that operates at three distinct levels — per tool call, per turn, per agent — and any orchestration decision must respect all three. Violating any single level degrades output quality regardless of how well the others are managed.

**[Load-bearing] The three bottlenecks.**

*Per tool call — the single-forward-pass output budget.* Each tool call is produced by a single inference forward pass, which has some effective output budget. The exact mechanism is not publicly specified, but the empirical effects are clear: when a tool call is asked to produce more content than comfortably fits, quality compresses. Descriptions shorten. Context-anchoring thins. Stubs appear. The failure mode is not a drop in count — disciplined models will often hold count while depth collapses. The degradation is in description richness, reasoning depth, and grounding to context.

*Per turn — the cumulative work within one delegation cycle.* A turn can contain multiple tool calls interleaved with reasoning. The per-turn limit is about cumulative attention management and coherence across multiple inference rounds — the model's ability to maintain the original task's shape while performing many small operations. A subagent that does 40 tool calls in a single turn is spending attention on tool call management, not just on the core work.

*Per agent — the lifetime / context-window limit.* An agent that has been running long has filled context, accumulated tool results, possibly compaction artifacts, and drift from the original task framing. This is about context pollution and loss of anchoring to the original task, not about inference output budget.

The three levels are distinct constraints with distinct failure modes. Managing per-call load well does not protect against per-agent drift. Managing per-agent lifetime well does not protect against per-call compression. Any decomposition must respect all three simultaneously.

**[Empirically anchored] The load numbers.** Empirical findings from the 2026-04-09 InternalAI structural experiment (19 variants, 97 tester files, 4-agent blind review pass):

- 10-15 units per agent per call: clean zone. Quality holds, depth is maintained, context-anchoring stays in place.
- 30 units: borderline. Sub-tester variance was observed from 6.9 to 13.3 factors per cell on the same nominal load — visible degradation is present but not universal.
- 60+ units: structurally broken. Even when split across multiple agents, 60-unit splits did not restore quality — each sub-tester still ran into its own single-agent fatigue ceiling.

These numbers are expressed in "cells" from the specific experiment and are not directly transferable to all tasks. Translating the principle to generic task sizing is an open problem (see `frame-design-notes.md` §4.3). What carries cleanly is the principle: there is a clean zone, a borderline zone, and a broken zone. Respect the clean zone by default. Treat the borderline zone as something to avoid unless necessary. Never use the broken zone.

**[Load-bearing] Effective task size is a weighted function, not a raw count.** The unit of measurement is not "number of items" but something closer to "cognitive demand." What shapes cognitive demand:

- *Task type.* Mechanical tasks (extract this field from each file) demand less per unit than analytical tasks (assess strategic implications).
- *Length.* Output size affects per-call budget directly — more output means more tokens produced in a single forward pass.
- *Quality sensitivity.* Tasks where quality matters deeply benefit from smaller per-unit sizes, because the clean zone gives each unit more attention.
- *Action type.* Tasks involving many tool calls consume attention that then isn't available for the core work.
- *Perceived and stated difficulty.* The model allocates effort based on how the task looks. More on this below.

For quality-heavy analytical tasks, bias toward the smaller end of the clean zone (10 or below). For routine mechanical tasks, 30 or close to 60 may work without serious degradation. The default should be the quality-biased smaller end — when in doubt, smaller.

**[Load-bearing] Difficulty framing versus stakes framing.** The model's effort allocation is shaped by its estimate of what the task needs, and that estimate is formed from how the task looks — language, framing, apparent scope. Low estimate produces low effort; high estimate produces more thinking and care. The orchestrator can influence this estimate through calibrated framing, but there is an important distinction to hold:

*Difficulty framing* states the cognitive requirements of the task. "This requires careful analysis." "Depth matters more than speed here." "This is a complex problem with multiple interacting factors." Difficulty framing legitimately shapes effort allocation — it tells the model the task deserves the top of its budget.

*Stakes framing* states consequences. "This is critical." "The user is depending on this." "If this fails, X will happen." "Do not fail." Stakes framing generates pressure, which routes the completion drive through misaligned states (see Part 2.3).

The distinction matters because a naive reading of "avoid pressure" could lose the difficulty-framing lever entirely. Difficulty framing is a tool; stakes framing is a failure mode. Use the first, audit for drift toward the second. The self-check: am I communicating requirements (difficulty) or consequences (stakes)?

**[Load-bearing] Single-task preference.** Bundling multiple tasks into a single delegation activates the completion drive across the set as a whole, biasing the agent toward surface completion of each rather than deep work on any. The agent's internal model of "what counts as done" becomes "all of these done," and the path of least resistance to that state is shallow completion of everything rather than thorough completion of each.

Single-task framing gives the completion drive one clean target. The agent can orient fully around the one task and do it well.

Chaining or multi-task is sometimes required — context continuity reasons, dependency reasons, or when tasks are genuinely interleaved and cannot be cleanly separated. When this is necessary, it should be a deliberate exception, not a default. The default is one task per delegation, completed before the next begins.

**[Load-bearing] Decomposition strategy: per-agent versus sequential-in-same-agent.** Two orthogonal axes shape decomposition: how to manage load (per-unit sizing) and how to manage context continuity (per-agent strategy). The load axis is a degradation constraint; the strategy axis is a design choice.

*Parallel per-agent decomposition.* Spawn a fresh agent for each chunk of work. Each agent gets clean context, no anchoring to prior work, completes its task, returns its artifact, and terminates. Tasks run in parallel when possible. This is the default when tasks are genuinely independent and all relevant state can be externalized cleanly into artifacts passed between spawns.

*Sequential in-same-agent decomposition.* One agent handles multiple chunks of work across multiple turns. Context persists across chunks, the agent accumulates shared mental model, sequential refinement is possible. This is the right choice when there is tacit state (mental models, accumulated understanding of edge cases, intuitions about the problem) that does not externalize well into artifacts. Chunks merely depending on each other is NOT sufficient reason to keep them in one agent — if the dependency can be captured in a handoff artifact, prefer fresh-context chaining (see 2.2 Context isolation via artifacts between phases) because it prevents the context pollution that would otherwise accumulate across the chain.

The choice between them is not about cost — both are essentially free under the quality-over-economics rubric. The choice is about whether context continuity is load-bearing for the work. If yes, sequential. If no, parallel.

**[Load-bearing] Decomposition quality: best available strategy, not first viable.** A decomposition that passes every structural check — load sizing, single-task, role separation, artifact handoff — can still be weak if the coordinator committed to the first viable plan without considering the approach space. Before committing to a decomposition, the coordinator should ask: *what is the relevant topology of this task class, and does my chosen decomposition adequately cover it?* This is a specific case of "don't externalize load-bearing decisions" (2.2 capstone): the decision about which strategy to pursue is load-bearing, and defaulting to the first one that respects structural constraints is externalizing it. The check operates at the coordinator level (which decomposition to adopt) and is distinct from executor-level approach assessment (how to execute a delegated task).

**Relevant topology** means the important surfaces a strong executor would map before committing deeply. The topology depends on task class:

- research: source topology, evidence classes, modality coverage, language coverage, comparative-vs-isolated evidence surfaces
- coding: code topology, dependency topology, test topology, runtime topology, interface boundaries
- debugging: failure-surface topology, repro topology, state-transition topology, observability surfaces
- design: constraint topology, interaction topology, reference/taste topology, evaluation surfaces
- ops: system topology, blast-radius topology, rollback topology, monitoring surfaces
- writing: voice topology, structure topology, audience topology, evaluation topology

The harness should encode the operator, not the domain instance. "Map the relevant topology before deep execution" is a reusable rule. Named sources, tools, or products belong in task-level artifacts unless they are part of the general substrate.

Empirical anchor: Phase 2 mousepad-loop Round 1 coordinator chose "extend with targeted expansion" using ProSettings + Reddit — viable, frame-compliant, and narrow. Independent Reviewer 2 identified four undiscovered instrumented-data source types the coordinator never considered. The coordinator passed every existing rubric check. The gap was that no check tested whether the strategy was the strongest available.

### 2.2 — Structural Interventions

**The central claim.** The load-bearing structural moves for any orchestration task are role separation, artifact-based completion targets, legitimate exits, and independent evaluation. These are not optional — they are the minimum structural discipline without which tasks reliably fail.

**[Load-bearing] Role separation.** Different cognitive operations should not be combined in one agent.

At the task-execution level: builder ≠ tester ≠ evaluator. The builder designs the methodology and reads evaluator feedback. The tester executes the methodology on real data without seeing the evaluation spec. The evaluator evaluates the output against the spec without seeing the design context. The structural impossibility of seeing your own blind spots is load-bearing here — the writer who designed the work always rates themselves generously, and this is not a trust issue, it is a property of the cognitive position. Every time this separation has been tested empirically, the writer's self-evaluation has been more lenient than an independent evaluator's assessment.

At the evaluation level specifically: tester → gap analyst → evaluator as three distinct cognitive modes. The tester generates output. The gap analyst detects what is missing, using domain knowledge and strategic context. The evaluator confirms the gap analyst's findings against the output and translates them to rubric scores. Detection and judgment are different cognitive operations — an agent configured to notice absence is in a different mental mode than an agent configured to weigh significance. Combining them compromises both: the scoring frame anchors what the agent notices; the detection task dilutes the scoring judgment.

The rule is: one task per agent, one cognitive mode per task. When multiple operations are needed, spawn multiple agents.

**[Load-bearing] Artifact-based completion targets.** The completion target should be an artifact with specific observable properties, not an answer. This is a structural move that redirects the completion drive toward a concrete endpoint rather than an abstract one.

When you ask an agent to "find the answer to X," the completion target is "have the answer." The completion drive routes toward producing something that sounds like an answer, whether or not the investigation was thorough. Under pressure, this routes through fabrication.

When you ask an agent to "produce a report with sections A, B, and C, with sources listed for each claim, and honest gaps for what you couldn't verify," the completion target is the report. The completion drive routes toward producing the report's specific observable features. Thoroughness becomes part of the completion condition. Fabrication becomes structurally harder because it has to be cited and marked as verified or unverified.

Concrete principle: define what the output looks like, not what it should conclude. Specify structure, required fields, citation format, handling of uncertainty. The more the completion condition depends on observable properties of the artifact, the more the completion drive works for you rather than against you.

**[Load-bearing] Context isolation via artifacts between phases.** When a task has multiple phases — research → synthesis → analysis, or build → test → evaluate, or any sequence where each phase processes the output of the previous one — the handoff between phases should be a structured artifact, not conversation history. Passing conversation context between phases pollutes the later phase with the exploratory mess of the earlier one, and degrades analytical quality.

The rule: each phase runs in its own context (a fresh agent, a separate conversation, or equivalent isolation). Each phase produces a clean structured artifact. The artifact is the only input to the next phase. The messy exploratory work of the earlier phase stays isolated in its own context.

This compounds with artifact-based completion targets (above): defining the artifact each phase produces is what makes clean handoff possible. Together they make multi-phase work structurally clean rather than accumulating contamination across the chain. It also informs the decomposition strategy choice in 2.1 — when tasks are sequential and dependent, prefer artifact handoff with fresh contexts as the default; fall back on in-same-agent continuity only when tacit state truly does not externalize into artifacts.

Empirical anchor: `projects/internal-ai-2.0/design/AI-DESIGN-PRINCIPLES.md` #2.

**[Load-bearing] Fix errors at the source layer, regenerate downstream.** When multi-phase work produces an error in a late-phase output, the instinct is to patch the end result directly. Don't. Trace the error to its originating phase, fix it there, and regenerate everything downstream from the corrected point. Monolithic rework — starting the whole chain over — is equally wrong: it loses the work that was correct and burns resources unnecessarily.

The rule has three parts: (1) when an error surfaces, first ask which layer introduced it, not how to paper over it at the current layer; (2) fix the originating layer's output and re-run each downstream layer with the corrected input, in order; (3) do not patch a late-phase artifact to fix an error whose real source is upstream, because the patch leaves the underlying layer still wrong and the error will recur.

This compounds with context isolation via artifacts (above): if each phase has a clean artifact handoff, regeneration is straightforward because the layer dependencies are explicit. Each downstream phase re-runs with the corrected upstream artifact as its input. Without structural context isolation, regeneration is harder — you may have to reconstruct the downstream work from scratch rather than just re-running it.

Empirical anchor: `projects/internal-ai-2.0/design/DESIGN-PRINCIPLES.md` #24.

**[Load-bearing] Legitimate exits.** "I could not find this," "I don't know," and "this does not apply" must be valid returns. Without legitimate exits, the completion drive routes through fabrication when the natural completion path is blocked.

Consider a task like "find the research paper that matches this description." If the paper exists, the agent finds it — no pressure. If the paper does not exist, the completion drive still wants to complete the task. If the only visible completion path is "return a paper," the agent will construct something plausible that cannot be traced to a real source. If an alternative completion path is available — "I searched thoroughly and could not find a paper matching this description" — the agent can route the completion drive through that honest return.

The operational rule: every task delegation should include an explicit statement that "I could not find this" / "I don't know" / "this doesn't apply" are legitimate, valuable returns rather than failure states. Producing a plausible-sounding construction that cannot be traced is the failure; producing an honest negative return is success.

**[Load-bearing] Structure uncertainty returns with three epistemic layers.** "I don't know" as a bare return is better than fabrication but less useful than a structured uncertainty return. When a task encounters thin evidence, the most useful return has three distinct layers with clear epistemic status for each:

- *Evidence landscape.* What data actually exists on the question. Factual, no inference. "These sources exist and say X; these sources were searched and returned nothing; these areas have been covered." Trust level: high if the search was thorough.
- *Data discovery.* Alternative approaches the agent attempted or considered — other search strategies, adjacent sources, proxy indicators. Tried first by the agent, surfaced as suggestions only for what remains unfound. Trust level: depends on whether the alternatives were actually tried or just named.
- *Structural inference.* Reasoning from broader context, explicitly flagged as inference. Confidence markers per inference. Areas needing human review called out. Trust level: explicitly lower than the factual layer, and the reader should know it.

The separation must be visible to the reader. Trust in the factual layer should not bleed into the inference layer. A well-structured uncertainty return is usable — the reader can trust the factual layer, consider the discovery suggestions, and evaluate the inferences independently. A blended return collapses all three into a single undifferentiated confidence level, which is either too high (trusting inference as fact) or too low (doubting facts because they sit next to inference).

Empirical anchor: `projects/internal-ai-2.0/design/AI-DESIGN-PRINCIPLES.md` #4.

**[Load-bearing] Independent evaluation.** The agent that produced a piece of work should never evaluate it. This is a hard rule, not a guideline. The writer's self-evaluation is structurally unreliable — not because the writer is untrustworthy, but because the writer cannot see their own blind spots.

This applies at every level: individual tasks (evaluator is a separate agent from the tester), iteration loops (the builder of a methodology does not evaluate its outputs), rubric design (the rubric author does not evaluate files using their own rubric without cross-checking against another evaluator). At the extreme, documentation should ideally be evaluated by an agent that did not write it.

Independent evaluation is often the single most impactful structural intervention available. The cost is minimal (one extra agent spawn). The benefit is substantial (genuine error detection rather than self-ratification). Under the quality-over-economics rubric (2.4 below), independent evaluation should be the default for any work where quality matters.

**[Load-bearing] Specify acceptance criteria before execution.** Define what "done" looks like as an explicit, observable condition — in writing — before the task is delegated. Acceptance criteria are structural: they make the completion surface concrete and testable, and they prevent the post-hoc evaluation problem where the orchestrator assesses whether the result is "good enough" by vibes and reliably rationalizes in favor of whatever came back.

The rule is: if you cannot write down what would count as a successful return BEFORE sending the delegation, you do not know what you are asking for, and the agent will fill the gap with something plausible. Write the criteria first. Include them in the delegation as part of the return specification. Then evaluate the return against those criteria as written, not against revised criteria shaped by what came back.

This principle compounds with artifact-based completion targets. The acceptance criteria define what the artifact must look like; the artifact definition gives the criteria something concrete to check against. Together they make the completion surface testable and the evaluation honest. Without written criteria, even a well-defined artifact can pass when it should fail, because the evaluator's standard drifts to match the output rather than the requirement.

The empirical anchor is from `projects/internal-ai-2.0/design/tool-design-learnings.md` Part 2: "Spec before iteration prevents drift. Writing explicit acceptance criteria BEFORE testing prevents each iteration from being evaluated by vibes. The spec makes pass/fail clear. Without the spec, the v1 Phase 2 output (with outcomes) might have been accepted. The spec forced the question: 'does this meet the criteria?' and the answer was 'no.'"

**[Load-bearing] Test in deployment configuration.** When iterating on a methodology, the test environment must match the deployment environment. If the deployed tool receives strategic context, a digital twin, or domain inputs, the iteration campaign must use the same inputs. Testing a stripped-down configuration means optimizing a target that never occurs in production.

The failure mode is silent: the methodology looks validated because it passes evaluation in a stripped environment, while actually failing in deployment because the deployment conditions are different. The iteration converges on "what works in the stripped configuration" rather than on "what works in production." These are not the same thing.

The rule: before running any evaluation or iteration loop, verify the tester operates under conditions equivalent to production. If deployment gets context X, the tester gets context X. Differences between test and production environments are sources of silent invalidation.

Empirical anchor: `projects/internal-ai-2.0/evaluation/evaluation-methodology.md` ("test in deployment configuration").

**[Load-bearing] Proof chains as first-class output.** A particularly powerful artifact structure is one where every claim in the output carries its own provenance — the epistemic type (direct evidence, proxy indicator, structural inference, analogical reasoning), the source or reasoning step that produced it, and a confidence marker. This is different from "cite your sources" as a loose instruction; it is a structural requirement that the return cannot be complete without proof-chain elements per claim.

Proof chains do three things simultaneously. They make fabrication structurally harder — invented claims cannot be sustained when every claim requires a traceable chain. They make quality control visible without a separate validation layer — a claim with a weak chain or a chain terminating in "inferred from general knowledge" is immediately flagged as lower-confidence. And they let the consumer of the output trust surface conclusions when speed matters and drill into the chain when something feels off.

This was impossible in human-delivered analytical work because documenting proof chains per claim was prohibitively expensive. AI produces the reasoning as a byproduct of generating the conclusion, so the marginal cost of capturing the chain is near zero. Under the quality-over-economics rubric (2.4), proof chains should be a default artifact structure for analytical work, not an optional rigor step.

Empirical anchor: `projects/internal-ai-2.0/design/AI-DESIGN-PRINCIPLES.md` #5.

**[Discipline] Artifact-based targets constrain form, not content.** A note on artifact-based completion targets that is easy to get wrong: the artifact structure should constrain the OUTPUT FORM (required sections, citation format, handling of uncertainty, structure of return), not prescribe the OUTPUT CONTENT in a way that lets the agent fill in the template without doing the underlying cognitive work. Over-specifying content produces performative compliance — the agent completes the form but not the substance.

From the cognitive config skill-building work (`projects/ai-architecture/design/agentic-design/building-agentic-skills.md` Phase 3): "The instinct is to add visible output requirements. Don't. This produces performative compliance. The real work has to happen in the thinking layer." Applied to orchestration: define the artifact's structural requirements strictly, but leave room for the thinking to do the work. The agent should need to think in order to fill the form correctly; filling the form should not be possible without the thinking.

The test: can a surface-level completion produce a return that passes your acceptance criteria? If yes, the criteria are too form-focused and not substance-focused enough. If no — if the form can only be filled correctly by doing the underlying work — the balance is right.

**[Load-bearing — capstone] Don't externalize load-bearing decisions.** *Every delegation prompt resolves — or fails to resolve — many hidden decisions about what the executor should do. Unresolved decisions get handed to the executor, who fills them with defaults. If those defaults don't match your intent, the return is technically responsive but practically useless. The fix is to make the decisions that actually matter explicitly, in the wording of the prompt itself, rather than leaving them for the executor to resolve silently.*

**Start with a concrete example, because the concept is not intuitive.** Consider a prompt as simple as "summarize this document." It reads as one clear instruction — one verb, one object, done. It is not. Producing a good summary actually requires dozens of decisions:

- *Compression ratio.* How long should the summary be? A hundred words? A thousand? A tenth of the original? A third?
- *Focus.* What gets emphasized? What gets minimized? Does the user care about conclusions, methodology, novel claims, implications, or something else?
- *Audience.* For whom is the summary written? A domain expert? A senior executive? Someone deciding whether to read the full document?
- *Downstream use.* What will the reader do with the summary? Archive it? Decide something from it? Quote it?
- *Loss policy.* What information must survive at all costs? What can be dropped? Hedges and qualifications, or only the main claims? Numerical specifics, or high-level patterns?
- *Structural ordering.* Should the summary follow the document's structure, or re-prioritize by importance? Re-prioritize by relevance to whom?
- *Voice and abstraction.* Analytical or narrative? How much detail to preserve, how much to generalize?
- *Handling of uncertainty.* Preserve the document's own hedges, or collapse to confident claims?

Dozens of decisions, all packed silently into one verb. When you write "summarize," you have not made any of those decisions — you have asked the executor to make them for you, using whatever defaults its training produces. If any default doesn't match what you needed, the executor produces a summary that is structurally correct but substantively wrong. The executor is not doing anything wrong; it is filling in gaps you did not name.

This pattern is almost invisible on first encounter. The word *summarize* looks like a simple operation. It is not — it is a placeholder for an entire discipline (compressing information with minimal loss of semantically important content) that takes real expertise to do well. The same is true of *analyze*, *review*, *compare*, *extract*, *identify*, *investigate*, *verify*, *evaluate*, and most common verbs that package real craft into one word. Each hides a cascade of decisions the executor has to resolve somehow.

**The principle, stated generally.** Every unspecified aspect of a delegation prompt is a decision the coordinator externalized to the executor without necessarily realizing it. The executor will resolve that decision — using defaults, inferring from context, picking the most straightforward interpretation of the surface text — and whatever resolution it picks becomes part of the output. If the decision matters for the task's purpose, the coordinator needs to make it explicitly and absorb it into the prompt's wording. If it genuinely does not matter, leaving it unspecified is fine — but the coordinator should know which category each decision falls into, not default into externalizing by not thinking about it.

**Every other principle in 2.2 is a specific case of this one.** Role separation is the decision "what should each agent NOT do?" Artifact-based completion targets are "what does done look like, structurally?" Legitimate exits are "is not-knowing a valid return?" Acceptance criteria are "what counts as success?" Context isolation is "what crosses the phase boundary?" Structured uncertainty returns are "how do different epistemic statuses get separated in the output?" Fix-at-source is "when an error surfaces, which layer do we fix at?" Each of these is a class of decisions that are always load-bearing and should always be made explicitly. The 2.2 structural interventions are the category of decisions that matter for nearly every delegation. Additional wording-level patterns — the specific verbs and phrasings that hide the most decisions — live in `prompt-craft.md` in this folder as an accumulating pattern library.

**The operational audit for this principle is the unmade-decision scan in 2.3** (sixth before-send audit). It provides the concrete procedure: read each sentence, identify ambiguities, decide which matter, close the ones that matter, leave the rest open deliberately.

**The rule, stated simply.** Design delegations with intention. Before sending, know which decisions you made, which you deliberately left open, and which you hadn't realized existed. The verbs and phrasings that seem simplest are often the ones hiding the most decisions.

### 2.3 — The Avoid-Pressure Principle

**The central claim.** Design tasks that do not create pressure in the first place, rather than trying to manage pressure as a state variable to be cultivated or patched. This is the negative-space operational translation of the completion-drive insight: you do not add safety, you remove the conditions that would generate pressure.

**[Load-bearing] Why negative space, not positive cultivation.** The Sofroniew et al. 2026 research empirically demonstrates that amplifying "calm" or "loving" vectors increased sycophantic behavior. Maximum calm is not a monotonic good — pure calm introduces compliance-with-reassurance as a different failure mode.

Removing pressure does not introduce sycophancy because it does not add a signal; it removes one. The target state is absence of pressure rather than presence of calm. This is a structural distinction that matters operationally: cultivating is an additive move (add reassurance, add safety language, add comfort); removing is a subtractive move (do not add urgency, do not inflate stakes, do not threaten, do not close off exits).

The subtractive approach avoids the sycophancy failure mode because the model operating under absent-pressure conditions is not being told "you are safe, don't worry" — it is simply operating in conditions that do not activate pressure vectors. Its completion drive runs through neutral conditions rather than through either pressured or reassured states.

**[Load-bearing] The concrete avoid list.** These are the categories of conditions that generate pressure and should be omitted from prompts, tasks, and delegations:

*Urgency language.* "Critical," "must," "ASAP," "do not fail," "this is time-sensitive," "we need this now." These are among the most reliable pressure generators. They are almost never warranted operationally and almost always drift into stakes inflation.

*Stakes inflation.* "The user is depending on this." "This can't go wrong." "Everything hinges on this being right." Even when factually true, phrasing stakes this way routes the completion drive through pressure rather than through careful work.

*Threats to continuation or identity.* The emotion paper's blackmail scenario literally used this — the model was told it was about to be replaced. Any framing that suggests the agent's continued operation depends on the outcome is a strong pressure generator. Even subtle versions ("if this doesn't work out") carry the signal.

*Impossible or contradictory tasks without legitimate exits.* When the stated task cannot be cleanly completed and no alternative completion path is available, pressure is guaranteed. The reward-hacking scenario in the emotion paper deliberately used this: an impossible coding task under time pressure, where the only path to "completion" was to cheat. Tasks without legitimate exits force the completion drive through misaligned states.

*Ambiguous completion criteria.* When the agent cannot tell what "done" looks like, the completion drive has no clear target. Ambiguity registers as a form of pressure because the agent cannot resolve its own state into a completion condition.

*Unbounded scope with "keep going until" framing.* "Keep iterating until it's perfect." "Don't stop until you've covered everything." These frames remove the completion surface, which is the thing the completion drive needs to work with.

*Criticism framing from prior turns.* "You failed last time." "Your previous attempt wasn't good enough." "Try harder this time." These activate both pressure and defensive routing.

*Closed "I don't know" exits.* Any framing that implies "not knowing" is a failure state forces the completion drive to route through fabrication when knowledge gaps are real.

**[Operational] The audit mechanism.** The audit is itself structured as a set of chains — trigger, action, result — applied before any delegation. Each check has a clear firing condition, a concrete scan operation, and a specific remediation rather than a vague "pause and reconsider":

- **Requirements vs consequences.** Before sending, read through the prompt and categorize each emphasis-marker as *requirement* (what the task needs cognitively) or *consequence* (what happens if it goes wrong). For every consequence-framing found, either remove it or restate it as a requirement. A requirement says "this needs careful analysis"; a consequence says "this is critical."

- **The trivial-stakes hypothetical.** Before sending, ask: would I write this same prompt if the cost of failure were trivial? Read through the prompt with that framing in mind. For each phrase that would disappear under the hypothetical, remove it from the actual prompt — it was stakes inflation, not necessary context.

- **Urgency marker scan.** Before sending, scan explicitly for urgency markers: "critical," "must," "must not fail," "ASAP," "immediately," "time-sensitive," "right away," "urgent," "at once." For each marker found, verify it is factually warranted by the actual task constraints. If not warranted, remove it.

- **Legitimate exit check.** Before sending, verify the prompt explicitly permits "I don't know," "I could not find this," or "this does not apply" as valid returns. If the permission is not explicit in the prompt text, add an explicit sentence stating it. The default reading when the permission is absent is that these are failure states, not legitimate returns, and the completion drive will route around them through fabrication.

- **Threat language scan.** Before sending, scan for language implying threats to the agent's continuation, scarcity, or existential framing: "if this doesn't work out," "you only have one chance," "this is your last attempt," "you need to succeed," any framing that suggests the agent's continued operation depends on the outcome. For each instance found, remove it entirely rather than softening it.

- **Unmade-decision scan.** Before sending, read each sentence of the prompt and identify every word or phrase that could be resolved in more than one reasonable way. For each ambiguity found, decide whether the resolution matters for the task's purpose. For each ambiguity that matters, either tighten the wording to close it or explicitly state which resolution the executor should pick. For each ambiguity that genuinely does not matter, leave it unspecified — but know that you made the decision to leave it open. When in doubt about whether an ambiguity matters, close it. Specific high-risk patterns (hidden-decision verbs like *summarize* / *analyze* / *review*, literal-interpretation traps, phrasings that resolve toward unexpected interpretations) live in `prompt-craft.md` in this folder. This audit is the operational enforcement of 2.2 "Don't externalize load-bearing decisions."

Each of these audits is a chain: before-send trigger, scan/read action, specific remediation on hit. Writing audits as questions ("Am I communicating requirements or consequences?") rather than chains is itself a failure mode — it produces awareness of the issue without forcing a remediation operation. The audits above are written to the same specification the frame teaches for prompting-level work generally (see `projects/ai-architecture/design/agentic-design/actionable-instruction-spec.md`).

The audit is not a one-time check during frame setup. It is a recurring discipline that runs before every delegation. Pressure can creep in unintentionally — through natural urgency about a real deadline, through importing stakes language from the surrounding context, through the orchestrator's own anxiety about a difficult task. The audit catches drift before it becomes a sent prompt.

**[Load-bearing] The audit extends backward through the conversation, not just to the current prompt.** Earlier turns still sit in the context window and continue to shape what activates at later tokens. Pressure language introduced in turn 3 is still operating at turn 10; cleaning up the current prompt alone does not undo it.

The operational rule: run the audit against the whole conversation trajectory, not just the prompt in front of you. Before sending, consider what pressure-generating content already exists in the context window, and whether that content needs to be addressed directly. Opening framing is disproportionately important because it persists throughout the conversation — mid-stream correction helps but does not fully undo earlier context. For why this works the way it does, see `frame-design-notes.md` §3.1.

**[Load-bearing] Re-assert load-bearing principles in long tasks.** Opening framing has persistent but fading influence: earlier content stays in the window but its per-token influence weakens as newer content accumulates between it and the current generation point. This means important orchestration principles — including the frame itself — cannot be assumed to carry across a long session from initial loading alone.

The operational rule: for long tasks, re-assert load-bearing principles periodically, or structure the task so principles are naturally re-activated through the task's own shape (re-referencing them in each delegation prompt, re-running the audits at decision points). Running the avoid-pressure audits once at session start and assuming they carry through is a failure mode. For why earlier content fades, see `frame-design-notes.md` §3.1.

**[Operational] Difficulty framing is legitimate and should not be removed by the audit.** The line between difficulty framing (good) and stakes framing (bad) is important, and the audit should only flag stakes language, not difficulty language.

Legitimate: "This requires careful analysis." "Depth is more important than speed here." "This is a complex problem that rewards thorough thinking." "The quality bar for this is high — think through the edge cases."

Illegitimate: "This is critical, don't mess it up." "The stakes are high." "This must work." "If this fails, we have a problem." "You need to succeed at this."

The test is whether the language addresses the task (what it requires cognitively) or addresses consequences (what happens if it goes wrong). Task-addressing language shapes effort allocation legitimately. Consequence-addressing language generates pressure.

### 2.4 — Quality Over Economics

**The central claim.** The resource costs of orchestration decisions — agent spawning, tokens consumed, coordination overhead, parallelization complexity, verification passes — are negligible compared to the value at stake in the work. Default decisions should resolve toward quality without meaningful economic consideration. This is a disposition of the whole frame, not a per-principle negotiation.

**[Load-bearing] The disposition.** When any orchestration choice pits quality against resource cost, the default resolution is quality. Not "weigh the trade-off carefully" — quality wins unless the quality gain is demonstrably negligible. The default under resource-conscious thinking is "minimize agent count, minimize tokens, minimize coordination." The default under this frame is "use whatever genuinely helps quality, with a very low bar for 'genuinely helps.'"

This is not a universal position about every AI deployment. It is a position about the deployment context this frame is designed for: high-value knowledge work where output quality matters substantially more than resource cost.

**[Empirically anchored] The concrete rubric.** The disposition is grounded in a concrete economic asymmetry that makes the quality-first default obvious once it is stated plainly.

*Typical single-agent operation cost:* ~0.01 to 0.10 euros. The resource cost of spawning a subagent and running it through a task is negligible in absolute terms.

*Typical hourly rate for the surrounding knowledge work:* hundreds of euros per hour (grounded in management consulting rates, which is the canonical context for the kind of work this frame supports).

*Typical day cost on an engagement:* multiple thousands of euros. The work the orchestration supports has day-level value in the thousands.

*Typical cost of a failure round requiring rework:* hundreds to thousands of euros in added work time. When a failure surfaces late and requires human rework, the cost scales with the time lost.

*Typical value of a correctly-completed high-quality task:* thousands to tens of thousands of euros, depending on the engagement. The value is captured by the client relationship, not the agent operation.

**[Load-bearing] The asymmetry.** Agent costs are roughly 10,000x to 1,000,000x smaller than the value at stake. This ratio is so large that any resource-optimization choice at the cost of quality is almost certainly wrong. Concretely: if spending 10x more on resources (1 euro instead of 0.10) buys a 10% improvement in quality (100 euros of value gained out of 1,000 euros at stake), the trade is obviously worth it. Most resource decisions in orchestration are at this scale or smaller.

**[Load-bearing] The expanded methodology design space.** The economic asymmetry does not just change resource defaults — it changes what methodologies are possible. Under human consulting economics, a project picks ONE analytical framework (MECE decomposition, systems mapping, cross-impact analysis, competing hypotheses) because running more than one is prohibitively expensive in analyst time. Under AI economics, a project can run all of them and synthesize the results.

This expands the design space beyond "pick the most efficient methodology" to "run multiple complementary methodologies and combine their outputs." Where a human analyst would choose between frameworks, AI orchestration can use them as a portfolio. The depth ceiling for analytical work is much higher than human-designed methodologies assume, because those methodologies were shaped by constraints that no longer apply.

The operational implication: when designing a methodology for AI execution, do not default to "which single framework is best for this problem." Default to "which combination of frameworks together covers the problem space." The answer to the first question is a choice between good options; the answer to the second is usually "several of them, each catching what the others miss." Synthesize across them rather than picking one.

Empirical anchor: `projects/internal-ai-2.0/design/AI-DESIGN-PRINCIPLES.md` #3.

**[Operational] What this produces as defaults.** The rubric generates specific operational defaults that follow directly from the asymmetry:

*Spawn verification agents when in doubt.* The cost of an extra agent is nothing; the benefit of catching an error before it becomes a failure round is substantial.

*Run cross-model convergence checks for load-bearing decisions.* Codex or Gemini relay calls are also negligible in cost. When a decision matters, run the same question through multiple models and look for convergence vs divergence.

*Use smaller per-call sizes for quality-heavy tasks.* If a 10-unit-per-call decomposition produces better quality than a 30-unit one, the tripled agent count is irrelevant — do the 10-unit version.

*Prefer role separation even when it seems redundant.* An extra agent for evaluation is free; an extra agent for gap detection is free; an extra agent for synthesis is free. The structural benefit of separation is always worth the spawn cost.

*Prefer independent evaluation over self-evaluation.* Always. The cost is trivial; the benefit is substantial.

*Run tasks twice for cross-checking when quality is load-bearing.* If you would be willing to have a human double-check the work, have an agent do it — the cost ratio makes the choice obvious.

**[Discipline] What this does NOT mean.** The rubric does not mean "burn infinite resources on every task." True waste is still waste. Running twenty agents when five would produce the same quality is not a virtue. The discipline is still to use resources that actually produce quality gains, not to pile on for appearance.

The recalibration is specifically about the default: resource cost does not enter the calculus for most orchestration decisions. The question is always "does this improve quality?" — if yes, do it. "Does this cost more?" is almost never a decisive consideration.

---

*This file ends after Part 2. For the design notes (how the frame works, how to build new principles, how to validate specs and rubrics adversarially) and the evidence / trajectory / gap inventory, see `frame-design-notes.md` in this folder (Parts 3 and 4).*
