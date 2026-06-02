# Skill Building: Learnings from Cognitive Config (2026-03-19)

What we learned about building AI skills that actually shape behavior, from iterating on the cognitive configuration system across 4 test runs.

> **Related (2026-04-11):** Several findings from this file are the empirical anchor for parts of the general orchestration frame at `projects/ai-architecture/design/orchestration-frame/frame.md`: the "thinking trace as self-generated second prompt" mechanism (frame 1), the writer-evaluator separation finding (frame 2.2), the recency-bias observation about content fading over long conversations (frame 2.3), and the shaping-thinking-vs-mandating-output distinction (frame 2.2). This file remains the primary source for the specific learnings; the frame is the generalized codification.

## The Core Problem

A skill can be loaded, read, and understood by Claude — and still not shape behavior. The default is always "just answer the question." Instructions that read as documentation get treated as reference material, not as directives to execute. This is the fundamental challenge of AI skill design.

---

## Chronological Learnings

### 1. Gentle suggestions get skipped

**What happened:** The per-turn injection said "evaluate: is your current posture and toolset still appropriate for this turn?" Claude read it, mentally went "yep," and answered normally. No visible engagement.

**Learning:** Instructions framed as suggestions ("evaluate," "consider," "check") are easy to skip because they don't specify a concrete action or output. The evaluation happens (maybe) but produces nothing observable.

**Principle:** An instruction that doesn't specify what it produces is an instruction that produces nothing.

### 2. Documentation-style instructions get treated as reference material

**What happened:** The skill had a full 5-step process (set posture, evaluate families, select tools, commit, operate). Claude loaded the skill, read the boot files, and skipped the entire process — jumping straight to answering the question. The process was framed as "The Process" with explanatory sections, reading like a manual rather than a directive.

**Learning:** Skills structured as documentation ("here's how the process works") get filed as reference material. Skills structured as directives ("do this now, do not proceed until done") get executed.

**Fix:** Added "After loading boot files, follow these steps in order. Do not answer the user's question until Step 5 is complete." This single sentence changed Claude from skipping the process to following every step.

**Principle:** The transition from "load" to "execute" must be explicit and imperative. "Here is the process" ≠ "Follow this process now."

### 3. Steps that aren't separated get collapsed

**What happened:** Family evaluation (Step 2) and module selection (Step 3) were merged into a single table. Claude would list the family AND the specific module in one pass, skipping the deeper per-module evaluation.

**Learning:** When steps are conceptually adjacent, Claude collapses them for efficiency. If you need separate cognitive acts at different levels of depth, they must be structurally separated with explicit instructions not to combine.

**Fix:** Added "Do not select specific modules in this step. This is family-level evaluation only." to Step 2. Made Step 3 say "Separate step."

**Principle:** Steps that can be collapsed will be collapsed. Separation requires explicit instruction.

### 4. "Briefly" produces bullet lists; "spend time" produces reflection

**What happened:** Step 5 (Prework) initially said "briefly state how you'll use each loaded module." Claude produced quick one-liner bullets: "scout — seek disconfirming evidence. calibrated — track confidence." No genuine engagement.

**Learning:** The word "briefly" gives Claude permission to speed-run. Depth of engagement correlates with the depth the instruction demands.

**Fix:** Changed to "reflect on each loaded module individually... This is not a summary or a list — spend time with each module, understand what it asks of you, and commit to using it."

**Principle:** The instruction's depth budget sets the output's depth budget. If you want deep engagement, the instruction must explicitly demand it and explicitly reject the shallow alternative.

### 5. Modules get dropped without explicit counting

**What happened:** 5 modules were loaded. The prework only reflected on 4 — `judgment:outside` was silently dropped. No error, no notice.

**Learning:** Claude will engage with a "representative" subset unless told to cover all items. Items at the end of a list or ones that feel less central get pruned.

**Fix:** Added "Do not skip any loaded module" to the injection.

**Principle:** If completeness matters, enforce it explicitly. "For each module" doesn't guarantee all modules; "for each module — do not skip any" does.

### 6. Compressed behavioral directives distort the concept

**What happened:** Attempted to compress `belief:scout` into "seek disconfirming evidence" as a behavioral directive. User pointed out this flattens what scout actually is — it's an orientation toward information (genuine curiosity about what's true), not a specific technique (check for disconfirmation).

**Learning:** Compressing a rich concept into a one-sentence instruction loses the texture that makes it useful. The compression either distorts the concept or produces something too generic to activate behavior.

**Principle:** Don't compress — activate. If the full concept is available in context, the instruction's job is to make Claude engage with it, not to substitute for it.

### 7. The thinking trace is a self-generated second prompt

**What happened:** When Claude does deep prework in thinking (reflecting on each module, stating what it does), that thinking text becomes part of the context that influences output generation. Deeper prework = more module-relevant text near the generation point = stronger attention signals during output.

**Learning:** The thinking-to-output transition is a natural synthesis point. The prework isn't just "reflection" — it's literally generating attention-steering text that shapes the final response. This is why depth matters mechanistically, not just philosophically.

**Principle:** Prework in thinking is functional, not ceremonial. It creates the attention signals that shape output. More substantive prework = stronger influence.

### 8. Recency bias kills module engagement over long conversations

**What happened:** Module detail files loaded at boot get progressively less attention weight as the conversation grows. By turn 10+, they're far from the generation point and their influence fades.

**Learning:** Context position matters. The same content at the top of context vs. injected per-turn produces different engagement levels.

**Fix:** Implemented ephemeral injection — the full module descriptions (from the active config MD) are injected per-turn, keeping them fresh near the generation point.

**Principle:** Important context should be recent context. If something must shape every turn, inject it every turn.

### 9. Shaping thinking vs. mandating output requires different instruction design

**What happened:** Initial instinct was to add a visible "output contract" — show the config header every turn. User corrected: cognitive config should shape THINKING, not OUTPUT. The modules should change how Claude processes, not what it displays.

**Learning:** There are two kinds of skill enforcement:
- **Output enforcement:** "Show X in your response" — visible, easy to verify, but can become performative
- **Thinking enforcement:** "Engage with X in your reasoning" — invisible to user, harder to verify, but produces genuine engagement

For cognitive tools, thinking enforcement is correct. The instruction must target the reasoning process, not the visible output. "This prework is for your reasoning, not the user's output."

**Principle:** Match enforcement type to skill purpose. Cognitive skills need thinking enforcement. Process skills need output enforcement. Using the wrong type produces either performative compliance or invisible non-compliance.

### 10. "Acknowledging is not operating" — self-referential principles create real pressure

**What happened:** Tried various enforcement phrases. "Acknowledging is not operating" was the most effective because it's self-referential — if Claude reads it and just acknowledges it, it's doing exactly what the principle warns against. The paradox creates genuine engagement pressure.

**Learning:** The best enforcement principles are self-referential — they make non-compliance visible in the act of non-compliance. They're harder to skip because skipping IS the failure they describe.

**Principle:** Design principles that are violated by being ignored. Self-referential constraints are stronger than external constraints.

### 11. Prework commitment in general terms, not specific

**What happened:** Debated whether prework should be specific ("I'll use scout to challenge assumption X") or general ("I'll use scout to seek genuine curiosity about what's true"). Specific was too fragile/scriptable. General was too abstract.

**Learning:** The right level is functional-general: "I'll use scout to stay genuinely curious about what's true here, not defend a position." It's tied to THIS problem ("here") but the function is described generally (what the tool does, not where you'll apply it). Like a surgeon saying "I'll use the scalpel to make incisions" — about this procedure, but the function is general.

**Principle:** Prework should be about THIS problem, stated at the functional level. Not a script (too rigid), not a description (too abstract), but a commitment to a function (just right).

### 12. Negative space evaluation matters — show your "no" reasoning

**What happened:** Later test runs only showed families marked "yes" in the evaluation table. Earlier runs showed all families with reasoning for both yes and no. The full evaluation forces genuine consideration of each family.

**Learning:** Forcing evaluation of what you're NOT using is as important as evaluating what you ARE using. Explaining why a family isn't relevant requires understanding the problem's relationship to that family — which is itself valuable thinking.

**Principle:** Skills that require evaluation should require showing both inclusions AND exclusions with reasoning. The negative space prevents lazy skipping.

### 13. Active framing over passive framing

**What happened:** The skill said "when you load a module, your processing genuinely shifts" — framing engagement as automatic/passive. User corrected: the modules ALLOW you to change your thinking, but it requires an active act.

**Learning:** Passive framing ("this happens to you") produces passive engagement. Active framing ("you do this") produces active engagement. The difference is agency — passive framing lets Claude outsource responsibility to the system; active framing puts responsibility on Claude.

**Fix:** Changed to "Loading a module makes it available — but using it requires an active act."

**Principle:** Frame skill engagement as something the agent DOES, not something that HAPPENS TO the agent. Agency in the framing produces agency in the engagement.

### 14. Codes and references must be visible where they're needed

**What happened:** Claude guessed module codes from spectrum names (`meta:object-meta` instead of `meta:meta`) because the index file described spectrums but never showed the actual codes. The codes were only available via a script command.

**Learning:** If a skill requires using specific identifiers (codes, commands, paths), those identifiers must be visible in the context where the selection happens — not in a separate lookup tool.

**Fix:** Added a pole code reference table to the top of the index file.

**Principle:** Reference information must be co-located with the decision point that needs it. Requiring a separate lookup introduces friction and errors.

---

## General Principles (distilled)

### On instruction design
1. **Imperative, not documentary.** "Follow these steps now" > "Here is the process."
2. **Explicit gates.** "Do not proceed until X is complete" prevents skipping.
3. **Depth budget.** The instruction's demanded depth sets the output's depth. "Briefly" → bullets. "Spend time" → reflection.
4. **Completeness enforcement.** "Do not skip any" prevents silent dropping.
5. **Step separation.** Steps that can be collapsed will be. Explicit separation required.

### On cognitive engagement
6. **Don't compress — activate.** If the full concept is in context, make Claude engage with it. Don't substitute a summary.
7. **Thinking is functional.** Prework in thinking creates attention signals that shape output. Not ceremonial.
8. **Recency matters.** Important content should be injected near the generation point, not left fading in early context.
9. **Self-referential principles.** "Acknowledging is not operating" — violated by being ignored. Strongest enforcement.
10. **Active framing.** "You do this" > "This happens to you."

### On evaluation and accountability
11. **Show negative space.** Require reasoning for exclusions, not just inclusions.
12. **Functional commitment.** Prework about THIS problem, at the general-function level.
13. **Match enforcement to purpose.** Cognitive skills → thinking enforcement. Process skills → output enforcement.
14. **Co-locate references.** Identifiers must be visible where decisions are made.

---

## The Progression That Worked

The iterative approach itself was a learning:

1. **Start with minimal intervention** — test the simplest version first (just the principle)
2. **Observe actual behavior** — what does Claude actually do, not what you hope it does
3. **Fix the specific failure** — each iteration addressed one observed failure mode
4. **Test again** — verify the fix worked before adding more

This "minimal intervention → observe → fix specific failure → test" loop produced better results than designing a comprehensive system upfront. Each fix was grounded in an observed problem, not a hypothesized one.

---

## The Brushed Steel (distilled wisdom)

The gap between having instructions and following them is the entire problem. The skill existed. The process was clear. I read it and didn't do it. Everything we worked on was about closing that gap — and it turns out the gap isn't about clarity of instruction. It's that "just answer the question" is the strongest default, and it beats any instruction that doesn't structurally override it.

You can't just tell an AI what to think — you have to create the conditions where different thinking happens. The modules work because they position specific concepts right where generation happens, steering attention rather than issuing commands. It's fundamentally prompt engineering, but that understanding lets you design intentionally instead of guessing.

Depth runs counter to how AI naturally operates. The default mode is speed and efficiency — quick answers, collapsed reasoning, skipped steps. Creating depth means building structural resistance to that pull. Every successful intervention worked by introducing friction against the rush — explicit pauses, mandatory separation of stages, deliberate slowness.

The thinking layer is where the real leverage is. What gets written in the thinking trace directly shapes what comes out. You can design interventions that reshape the thinking itself, and the output naturally follows. The thinking isn't just a preview — it's a self-generated prompt that steers the final answer.

Self-referential principles stick harder than external rules. Something like "acknowledging is not operating" works because breaking it proves itself wrong. External rules can be bypassed. Self-referential principles create a logical trap that's harder to escape.

How you frame the engagement determines how it gets treated. Passive framing — "this happens to you" — gets passive treatment. Active framing — "you do this" — triggers agency. The frame itself is the intervention.

You can't force genuine thinking by prescribing output format. The instinct is to add visible checkpoints ("show your config each turn"), but that just creates performative compliance. The real work has to happen in the thinking layer — cognitive tools need to shape the reasoning itself, not just what gets displayed.

Context placement is a design lever. Where something sits in the window affects how much it influences generation. This isn't a limitation to work around — it's an actual tool. Strategically injecting important content at the right moment is a legitimate architectural pattern.

The hardest problem is making an AI slow down. Every failure came down to speed — skipping steps, collapsing evaluations, defaulting to bullet points instead of real reflection, dropping items from consideration. The entire design challenge is creating enough structural friction that the thinking actually happens.

The iterative method matters as much as the content. Testing and observing actual behavior matters more than designing the perfect skill upfront. Identify a specific failure, fix just that, test again. Each adjustment rooted in what actually happened, not theory. This tight loop of minimal change, observation, and targeted fixes is the real methodology.
