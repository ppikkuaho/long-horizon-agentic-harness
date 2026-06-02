# Building Agentic Skills That Actually Work

A process guide for building AI skills that shape behavior, not just provide information. Based on building the cognitive configuration system from "injection fires but gets ignored" to consistent deep engagement across 67 modules, 5 rubric iterations, and ~100 subagent evaluations.

The other documents in this folder tell you WHAT makes instructions work (the spec) and WHAT we learned about skill design (the learnings). This document tells you HOW to actually do the work — the process, the iterations, the failures, and why each step matters.

> **Related (2026-04-11):** Skill building is one application of a broader operating frame for AI task shaping and orchestration. The general frame — completion drive as AI's nature, intervention hierarchy, role separation, avoid-pressure, quality-over-economics, audit mechanisms, adversarial validation — is codified at `projects/ai-architecture/design/orchestration-frame/frame.md`. Phase 4 (define good, then measure) and Phase 6 (cross-validate the spec) from this document are the empirical source for the adversarial validation pattern (frame 2.6) and the independent-evaluation principle (frame 2.2).

**Reading order for all documents in this folder:**
1. This guide (process overview)
2. `steering-moves-rubric.md` (see the quality tiers with concrete examples)
3. `actionable-instruction-spec.md` (the theory — makes sense now that you've seen the tiers)
4. `skill-building-learnings.md` (failure checklist — reference during testing phases)
5. `exemplar-skills/` (concrete S+ files — study before building your own)

**Three things to understand before starting:**
- The gap between having instructions and following them is the entire problem. "Just answer the question" is the strongest default — every skill design fights this.
- You can't tell an AI what to think. You create conditions where different thinking happens. The thinking layer is where the leverage is — not the output layer.
- Depth runs counter to how AI naturally operates. Every successful intervention works by introducing friction against the rush to answer.

## Phase 0: Concept Design

Before you can test and iterate, you need a concept worth building. This is the phase the testing loop can't help with — you need to get the starting point right enough that iteration can improve it.

**Is the concept ready for skill treatment?** A good concept has:
- Two clear poles (not good/bad, but genuinely different modes suited to different situations)
- Observable behavioral differences between the poles (you can tell which pole someone is operating from)
- Specific situations where being at the wrong pole produces identifiable failures
- A concept that's neither too broad ("think better") nor too narrow ("check for off-by-one errors")

**Decomposing into steering moves:** Start from the failure modes, not the concept description. Ask: what goes wrong when someone is at the wrong pole? Each failure mode suggests a steering move — a specific intervention that catches or corrects that failure. Three failure modes that cover different parts of the problem lifecycle (pre-action, during-action, post-action) give you a coherent system.

**The poles test:** Can you describe both poles as genuinely useful in different contexts? If one pole is just "bad thinking," it's not a spectrum — it's advice. Scout and soldier are both useful (soldier protects important beliefs under attack). Operationalized and floating are both sometimes appropriate (floating is fine during early exploration). If you can't make both poles legitimate, the concept isn't a spectrum.

**The steering moves test:** For each candidate move, apply the spec's chain test: does it have a clear trigger, a concrete action, and a result? If you can't write a move that completes the chain, the concept might be too abstract for skill treatment. Try decomposing it further.

**Writing the detail file:** Structure is fixed — What This Is (explain the concept and why it matters), Signs You're At Each Pole (recognition patterns), Steering Moves (3 moves forming a coherent system). The first two sections explain. The third deploys. Keep them separate — if your steering moves are still teaching the concept, they're doing two jobs.

## Phase 0.5: Skill Architecture

A finished skill has several files that serve different purposes:

| File | Purpose | When it fires |
|------|---------|---------------|
| **Skill file** (`skill.md`) | Full process — steps, gates, procedures | Once, when skill is invoked |
| **Agent file** (`agent.md`) | Boot context — persona, process, loaded at activation | Once, at agent activation |
| **Injection file** (`injection.md`) | Per-turn behavioral reminder | Every turn while active |
| **Detail files** (`families/*.md`) | Module descriptions with steering moves | Loaded when modules are selected |
| **Boot files** (manual, index) | Reference material — catalog, philosophy | Loaded at boot, re-injected after compact |
| **Script** (`cognitive-config.py`) | State management — persist config, output details | Called during process steps |

Not every skill needs all of these. A simple skill might just be a skill file. But if the skill needs to persist across turns, you need an injection. If it needs state, you need a script. Design the architecture based on what the skill requires, not what's maximally complete.

**Key architectural decision:** What fires per-turn vs what fires once? The boot context (full process, deep explanation) fires once and fades in context over time. The injection fires every turn and stays fresh. Put enforcement and activation in the injection. Put process and education in the boot.

## Wisdom First

This guide is full of structure — chains, rubrics, gates, protocols. It would be easy to read it and conclude that building skills is an engineering problem. It's not. It's a wisdom problem that requires engineering to deliver.

The cognitive config system started as wisdom. The deep manual is philosophy — what genuine thinking looks like, why the feeling of understanding betrays you, why seeking truth requires a different motivation than defending a position. That wisdom is the foundation. Without it, the 67 modules are just labels. With it, they're instruments that change what you notice, how you weigh evidence, and what questions you ask.

The wisdom came first. The structure came second, because the wisdom alone didn't fire — Claude read it, appreciated it, and skipped past it. Structure is how we made the wisdom operational. But structure without wisdom is empty scaffolding. A perfectly engineered chain protocol with nothing genuine behind it produces compliant, hollow responses — the AI follows the steps and misses the point.

So: cultivate the wisdom first. Before you think about triggers, actions, results, or rubrics — understand deeply what this concept means. Sit with it. Know why it matters. Know what goes wrong without it. Know the difference between someone who genuinely operates with this insight and someone who just knows the vocabulary. That understanding is the seed. Everything else — the steering moves, the injection, the process steps, the chain protocol — exists to make that seed grow in a context (LLM generation) where it would otherwise be read and forgotten.

The rest of this guide is about structure. Don't mistake the volume of structural guidance for a claim about what matters most. Structure is the larger part of the WORK. Wisdom is the larger part of the VALUE.

## The Shape of the Work

You don't design a working skill. You discover one. The process is:

1. Build something
2. Test it by watching what the AI actually does (not what you hope it does)
3. Identify the specific failure
4. Fix that one thing
5. Test again
6. Repeat until the failures stop being structural

This loop is the entire methodology. Everything below is detail on how to run it well.

## Phase 1: Build the First Version and Watch It Fail

Write the skill. Make it clear, make it reasonable. Then test it — not by reading it and thinking "this looks good" but by running it in a separate session and watching the AI's actual behavior. Look at the thinking traces. Look at the output.

The first version will fail. Ours did: Claude loaded the full 5-step process, read 300 lines of boot files, and then skipped the entire process and just answered the question. The process was right there in context and got ignored.

What you learn from the first failure tells you what kind of problem you have. In our case: the skill was written as documentation ("here's how the process works") not as directives ("follow these steps now, do not answer until step 5 is complete"). That single sentence — the gate — changed Claude from skipping the process to following every step.

The instinct is to redesign the whole skill after the first failure. Don't. Fix the specific failure. Test again. The next failure will be different and will teach you something new.

## Phase 2: Iterate on Observed Failures

Each test reveals one or two specific failure modes. Fix those, test again. The failures cascade — fixing one reveals the next.

Our cascade looked like this:

- **Test 1:** Process skipped entirely → fix: imperative language + gate
- **Test 2:** Process followed but family evaluation and module selection collapsed into one step → fix: explicit separation ("do not select modules in this step")
- **Test 2:** Prework speed-ran as bullet list → fix: "this is not a summary or a list — spend time with each module"
- **Test 2:** One module silently dropped from prework → fix: "do not skip any loaded module"
- **Test 3:** Codes guessed wrong → fix: added code reference table to boot file

Each fix was one change to one file. Each test was a separate session with the same question. The question matters — pick one that exercises the skill genuinely and use it consistently across tests so you can compare.

## Phase 3: The Harder Problem — Shaping Thinking vs Mandating Output

At some point the process works (Claude follows the steps) but the engagement is shallow. This is the harder problem. The skill runs but doesn't genuinely change how Claude thinks.

The instinct is to add visible output requirements — "show your config at the top of each response." Don't. This produces performative compliance. The real work has to happen in the thinking layer.

What worked for us: prework. Before operating on the problem, Claude reflects on each loaded module — what does it do as a cognitive operation, what does it ask of you, commit to using it. This isn't visible to the user. It happens in the thinking traces. But it works because the thinking trace is a self-generated second prompt — deeper prework creates stronger attention signals that shape the actual response.

The key design decisions at this stage:

- **Prework design.** Prework is the bridge between "I have these tools" and "I'm using them." It happens in the thinking layer — not visible to the user. For each loaded module, the AI reflects on what it does as a cognitive operation and commits to using it. The reflection should be in general terms (what the tool does) not specific terms (where it will apply) — like a surgeon naming instruments before operating, not scripting every cut. If the prework becomes a rote list, it's not working. It should be genuine engagement with what each tool asks of you for THIS question.

- **Active framing.** "The module works when you work with it" — not "your processing shifts when you load it." Agency in the framing produces agency in the engagement. Passive framing produces passive compliance.

- **Self-referential principles.** The strongest enforcement principles are violated by being ignored. "Acknowledging is not operating" — if Claude reads this and just acknowledges it, it's doing exactly what the principle warns against. Design your core principle so that non-compliance is self-demonstrating. This is harder than it sounds: most principles can be acknowledged without irony.

- **Don't prescribe output, shape thinking.** The instinct is to add visible checkpoints ("show your config each turn"). This produces performative compliance — text that looks like engagement without genuine cognitive change. The real work has to happen in the thinking layer. Design for thinking enforcement, not output enforcement.

## Phase 4: Define Good, Then Measure

Before changing anything at scale, you need two things: a definition of what good looks like, and a baseline measurement of where you are. We learned this the hard way — we refactored 10 files first, then realized we couldn't tell if they'd improved because we hadn't defined "improved" or measured the starting point.

The right order: define good → save a baseline copy → measure the baseline → change → measure again with the same tool.

**Use an independent evaluator.** This is non-negotiable and one of the most impactful decisions in the whole process. The agent that writes the content should never be the agent that scores it. Every time we had the writer self-score, it rated itself S+. Every time we sent the same file to an independent scorer, it found weaknesses the writer missed. This isn't about trust — it's about the structural impossibility of seeing your own blind spots. Separate writing from evaluation at every stage: rubric testing, refactoring validation, spec cross-validation.

This requires a rubric — explicit criteria that an independent evaluator can apply consistently.

The process of building a rubric:

1. **Start from exemplars.** Find the things that clearly work well. Study them. What do they share? For us: 8 files that all evaluators agreed were excellent. The common patterns became the rubric criteria.

2. **Test the rubric against known ratings.** Score files you've already evaluated manually. Does the rubric reproduce your ratings? Ours didn't — 4/8 matched on the first try.

3. **Fix the mismatches.** Each mismatch reveals either a rubric flaw or a rating error. The rubric might be too strict (calling an A a B) or too lenient (calling a B an A). Decide which: we chose strict, because false positives (passing weak work) are worse than false negatives (flagging decent work).

4. **Test again on a fresh set.** The rubric must work on files it wasn't calibrated against. If it only works on the training set, you've overfit.

5. **Repeat until evaluators agree.** The rubric is done when different evaluators (separate subagents who never saw each other's work) produce the same scores. Ours took 5 iterations.

The rubric development taught us something unexpected: the criteria that make instructions work aren't what we initially thought. We started with "is this concrete enough?" and ended with a precise specification: trigger → action → result chain, observation verbs banned as actions, self-diagnostics required for excellence, moves forming a coherent system not just three tips. Each criterion was discovered because its absence produced a measurable quality drop that independent evaluators caught.

## Phase 5: Refactor at Scale

Once the rubric is validated, use it to upgrade all the content. Our approach:

- **One subagent per file.** Focused attention produces better results than batching.
- **Each agent reads the rubric + 2 exemplar files.** The rubric tells them the criteria. The exemplars show them what excellence looks like. Both are necessary — rules without examples produce compliance without quality.
- **Include the specific known weakness in the prompt.** If validation found "move 3 has a weak trigger," tell the refactoring agent that. Targeted prompts produce targeted fixes.
- **The chain protocol.** Every move must complete: trigger → action → result. If a question is asked, specify what to do with the answer. If a condition is detected, specify the response. This single addition to the prompt improved all files — not just the weak ones.
- **Writer doesn't grade their own work.** Refactoring agents self-score, but the real validation is a separate subagent who only reads the rubric and scores the file cold. This catches things self-assessment misses — consistently.

Our numbers: 67 files, started at 8 S+ (12%), ended at 67 S+ (100%) after two passes. First pass got 56/67. Second pass with targeted fixes got the remaining 11.

## Phase 6: Cross-Validate the Spec Itself

The rubric measures files. But the understanding behind the rubric — the specification for what makes instructions work — also needs testing.

Run adversarial cross-validation: take the spec, apply it to exemplar files, and look for cracks. Where does the spec fail to explain why something works? Where does the spec claim something that an exemplar contradicts?

Our spec went through 4 rounds:
- **Round 1:** Built from exemplar analysis. ~70-75% coverage.
- **Round 2:** Tested against new exemplars + different instruction formats. Found: observation verbs work in decision contexts when anchored, format classes matter, self-diagnostics aren't optional.
- **Round 3:** Adversarial + edge cases. Found: the spec's own exemplars violated the 2-sentence rule, "none overlap" contradicted "redundant detection," asymmetric branching was real but unnamed.
- **Round 4:** Consistency check. All contradictions resolved, no new ones introduced.

Each round narrows the gap between what the spec claims and what the exemplars actually do. You stop when the rounds stop producing significant findings.

## Phase 7: Test the Whole System

Run the complete skill end-to-end in a fresh session. Compare to your earliest test. The difference should be visible and structural, not just cosmetic.

Our comparison: Test 1 skipped the entire process and produced a generic answer. Test 5 followed all 7 steps, engaged all modules visibly in the thinking traces, produced genuinely self-aware analysis, and identified specific insights that wouldn't have emerged without the modules.

The final test isn't "does it look good?" It's "does it do something it couldn't do before?"

## What the Process Teaches You

The process itself is a finding. Several things we learned that only emerge from doing the work:

**You can't design quality upfront.** The best criteria emerged from observing failures, not from theorizing about success. The chain protocol, the observation verb rule, the system coherence patterns — all of these were discovered by watching what went wrong, not by predicting what would go right.

**Separation of concerns between writing and evaluating is non-negotiable.** The writer always thinks their work is good. The evaluator catches what the writer missed. This isn't about trust — it's about the structural impossibility of seeing your own blind spots.

**Minimal intervention, maximum observation.** Fix one thing per test. If you change three things and the result improves, you don't know which change mattered. If you change one thing and it improves, you know exactly what worked and why.

**The harder the problem, the more the solution lives in the thinking layer, not the output layer.** Surface-level fixes (add a header, show a checklist) produce surface-level compliance. Deep fixes (prework, self-referential principles, ephemeral injection of module descriptions) produce deep engagement. You can't shortcut this by prescribing output format.

**Strict is better than lenient.** It's worse to pass weak work than to flag decent work for improvement. Err strict in every evaluation, every rubric, every quality gate. The cost of fixing something that was already good is low. The cost of shipping something that's broken is high.

## Files That Support This Process

- `actionable-instruction-spec.md` — what makes an instruction produce behavior (the gold)
- `skill-building-learnings.md` — specific learnings about skill design (the brushed steel)
- `steering-moves-rubric.md` — the measurement tool for scoring instruction quality
- `exemplar-skills/` — 4 reference S+ files to use as templates
- `cognitive-config-ideas.md` — backlog of improvements and future development
