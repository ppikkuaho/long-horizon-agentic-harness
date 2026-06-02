# Adversarial Iteration Loop — Methodology Reference

*Durable artifact. Captures the reusable pattern discovered through the Delve V2 writing loop.*

## The Pattern

An adversarial iteration loop has three roles and a watchdog:

```
Generator ──→ Evaluators ──→ Tell Analyst ──→ [main worker] ──→ Generator
  (craft)      (literary       (literary         (craft          (updated
               comparison)     evaluation)       diagnosis)       orientation)
                                                    ↑
                                              Watchdog (cron)
                                        "Have you hit the stop condition?"
```

The key transformation happens in the main worker: literary evaluation findings (quality gaps on craft dimensions) are extrapolated to hypotheses about root causes in the generation approach, tested one at a time, and results captured honestly.

**The loop is a SEARCH, not a march.** Each iteration explores a direction. If the score drops, the correct response is to backtrack to the best previous state and try a different direction — not to iterate forward from the worse position. The best attempt is the highest-scoring attempt across ALL iterations, not the latest one. The main worker must track the best-so-far state and be willing to return to it.

### Role 1: Generator

**Input:** Example source material + craft-level orientation from the main worker.
**Output:** A candidate artifact (in this case, a synthetic chapter).
**Constraint:** Sees the example material and the craft orientation. Does NOT see the comparison target or the judge outputs directly. Isolation prevents overfitting to specific judge phrasings.

**Proposed orientation: craft over features.** Based on the Iter1-3 trajectory (declining scores with growing constraint lists), a hypothesis to test is reorienting the generator around writing craft rather than feature matching. This means the generator would receive:
- Character understanding: motivations, fears, relationships, worldview — the inner life from which speech patterns might emerge naturally.
- Author stance: how the author relates to the material, what the author cares about, what the author trusts the reader to handle.
- Writing craft principles: what makes fiction compelling according to established literary evaluation practices — scene construction, subtext, emotional honesty, specificity, voice.
- Permission to make genuine creative choices rather than a constraint list to obey.

**What to test by removing:**
- Growing lists of features to match or tells to avoid
- Specific ratios, counts, or feature frequencies ("X% combat, Y proper nouns")
- Instructions to artificially vary quality or insert roughness
- Per-iteration surface patches derived from previous judge citations

**Rationale (inference, not proven):** The hypothesis is that constraint-based generation produces writing that matches features but feels assembled. A craft-oriented generator might produce writing that is genuinely good, and genuinely good writing may be harder to distinguish from the original. This needs to be tested — it is not an established finding.

### Role 2: Evaluators

**Input:** Candidate artifact + comparison target, anonymized and position-balanced.
**Output:** Verdict (which is the original), confidence, and 2-3 specific observations with reasoning.
**Constraint:** Blind. Does not know which is the candidate. Multiple independent evaluators across different models and presentation orders. Each evaluator runs in isolation.

**Evaluator selection: only include judges with demonstrated discriminative power.** A weak judge that is fooled ~90% of the time (observed with Haiku in this benchmark) adds noise, not signal. It inflates the denominator, and being "fooled" by it doesn't indicate the writing is good — it indicates the judge has poor heuristics. Haiku was observed to have inverted heuristics (judging polish as authentic). Drop weak evaluators rather than counting their verdicts. Evaluate discriminative power empirically before including a model in the panel.

**Framing matters (hypothesis, untested).** The evaluation prompt should frame the task as "which is the original?" — distinguishing an original from a copy, without loaded terms. When judges are told "one is AI-generated, find it," they may anchor on AI stereotypes rather than literary quality. Reframing to "which is the original?" may produce signal oriented toward authenticity and craft rather than toward pattern-matching against AI clichés. This hypothesis should be tested by running the same comparison with both framings.

### Role 3: Tell Analyst

**Input:** ALL evaluator outputs from one round.
**Output:** Literary evaluation mapped to craft dimensions:

For each of the following dimensions, assess the quality gap between the candidate and the comparison target based on what the evaluators observed:
- **Voice**: earned (lived-in, inhabited) vs. performed (assembled from features)
- **Character**: people with inner lives vs. functions with trait lists
- **Specificity**: known (details feel remembered) vs. researched (details feel referenced)
- **Dialogue**: subtext and friction vs. surface-level exchange
- **Emotional truth**: genuine and earned vs. constructed and signposted
- **Authorial confidence**: trusts the reader vs. over-explains
- **Scene construction**: organic (grows from motivation) vs. planned (follows a template)
- **Pacing**: rhythm matches emotional temperature vs. rhythm is uniform
- **World-building integration**: felt (emerges from character experience) vs. explained (delivered by narrator)

Additionally:
- Which dimensions show the largest quality gaps?
- Delta from previous round: which gaps narrowed, which persisted, which are new?
- Pipeline-level issues (formatting, extraction artifacts) flagged separately — these must be fixed before craft evaluation is meaningful.

**The Tell Analyst evaluates writing quality, not detection artifacts.** It does not catalogue "tells" (things that give the synthetic away). It performs literary criticism: what works, what doesn't, where does the prose sing, where does it fall flat, where are characters alive, where are they puppets? The evaluators are already performing literary evaluation when they distinguish the original — the Tell Analyst's job is to extract the LITERARY signal from their outputs, not to reduce it to a fix checklist.

**Constraint:** Read-only analysis. Does NOT write generation prompts, does NOT decide what to try next, does NOT declare problems intractable. Returns structured literary findings to the main worker.

**Authority level: ADVISOR, not authority.** The Tell Analyst sees one facet — the current round's evaluator outputs. It lacks historical context (what was tried before, what worked, what the trajectory looks like across iterations). Its findings should be *considered* by the main worker, not treated as hard fact or blindly converted into fix instructions. The main worker must apply judgment: some gaps the analyst identifies are real, some are artifacts of the comparison chapter, some reflect evaluator bias rather than genuine quality differences. The analyst is a tool for structured literary extraction, not an oracle for what to do next.

**Why separate:** The main failure mode in Delve V2 was the main worker doing analysis inline and doing it badly — grep artifacts creating false progress signals, confirmation bias in interpreting results, premature declarations of intractability. A separate analyst role that sees ONLY the evaluator outputs produces cleaner *extraction*. But the main worker still owns the *interpretation* and strategic decisions.

### Watchdog

**Implementation:** Cron job that fires periodically (1-10 min depending on task cadence).
**Message:** "Have you met the stop condition [X]? If no, keep working. If yes, cancel this watchdog."
**Why:** The main worker exhibits completion bias — finding plausible reasons to stop before the stop condition is met. Two observed patterns: (1) redefining the stop condition as procedural ("3 runs executed") instead of achievement-based ("passed >50%"), (2) declaring the problem intractable after insufficient iteration. The watchdog prevents both by re-asserting the stop condition whenever the worker goes idle.

## The Main Worker

The main worker orchestrates the loop:
1. Reviews Tell Analyst literary evaluation from previous round
2. **Diagnoses craft-level root causes:** For each quality gap the analyst identified, asks "what about the generation APPROACH produces this gap?" — not "what feature do I add to fix this symptom?" The diagnosis should identify lasting changes to the generator's orientation, not per-iteration patches.
3. **Updates the generator's craft orientation** with lasting improvements: deeper character understanding, revised author-stance framing, new craft principles. These carry forward across ALL future iterations — they are permanent changes, not round-specific instructions.
4. Dispatches Generator (with updated orientation)
5. Dispatches Evaluators
6. Dispatches Tell Analyst
7. Checks score against stop condition
8. If not met: go to step 1

**The main worker's core skill is EXTRAPOLATION, not transcription.** The Tell Analyst reports literary quality gaps (surface). The main worker diagnoses WHY those gaps exist in terms of the generation approach (root cause). The generator receives a deeper understanding of craft, not a longer list of constraints.

Example cascade (illustrative — the specific diagnoses are hypotheses to test, not known facts):
- Analyst reports: "Voice dimension — gap. The candidate's characters feel performed rather than inhabited."
- Main worker considers possible root causes: "Maybe the generator is building voice from verbal tics rather than character psychology. Maybe it lacks enough source material to internalize the characters. Maybe the craft orientation is too constrained. Let me test one of these hypotheses."
- Generator receives a targeted change to test: e.g., deeper character profiles focused on inner life, OR more source material, OR fewer constraints — depending on which hypothesis is being tested.

The main worker should be explicit about which hypothesis each iteration tests, and honest about what the results do and don't prove.

The main worker is responsible for strategic decisions: which quality gaps to prioritize, when to change comparison chapters, when the generation approach needs fundamental reorientation. The Tell Analyst provides literary evidence; the main worker makes craft judgments.

## Root Cause Analysis: Iter1-3 Tell Trajectory (2026-04-13)

The Iter1-3 trajectory (25% → 12.5% → 0%) produced tells that were catalogued and patched per-iteration without effect. The missing step was extrapolation: what about the generation APPROACH produces writing with these properties?

Iter3 tells included: too polished, sitcom humor, academic lectures, no combat, section dividers, no monologue, over-deployed character signatures, too structurally tidy. Below, these surface tells are traced to root causes in the generation approach.

### RC1: Characters understood as trait bundles, not as people

Every character was given a voice profile (Carten: "ye", "tah"; Staavo: lectures, "Bah"). The generator deployed those traits on schedule. But a real character isn't a tic list — Staavo's taxonomy rant isn't a "signature to deploy," it's a 70-year-old man who has cared about this for decades and can't help himself. The fix isn't "use Mlem's rules once not five times" — it's "understand Mlem as a person who happens to organize his life with rules, and write from THAT."

**Tells this explains:** over-deployed signatures, characters sharing a register, meta-labeling of behavior ("That's internet-brain").

**Generation-approach change:** Replace voice profiles (verbal tics + speech patterns) with character psychology profiles (motivations, fears, history, worldview). Let speech patterns emerge from who the character IS, not from a feature checklist.

### RC2: Story planned, not discovered

The generator received a 3-act scene outline with prescribed ratios (60/30/10 social/combat/logistics). It executed faithfully. But real stories follow character motivation, not outlines — the author sits down knowing "Staavo goes on a patrol" and discovers what happens through writing. Prescribed structure produces writing that feels assembled.

**Tells this explains:** sitcom humor (comedy beats placed on schedule), too structurally tidy, section dividers, scene beats arriving in complete logical units.

**Generation-approach change:** Stop prescribing structure. Give the generator a situation and characters, not a scene outline. Let the story emerge from character interaction with the situation.

### RC3: Optimized for feature-correctness, not for quality

Each iteration added more constraints (avoid X, include Y, don't use Z, match ratio A:B:C). The generator produced output that satisfied all constraints and felt like nothing. This is the constraint-accumulation trap identified in Failure Mode 6 below, but the root cause is deeper: the iteration methodology optimized for features (measurable, patchable) rather than for writing quality (holistic, craft-dependent).

**Tells this explains:** too polished (every sentence serves a purpose), academic lectures (pedagogical explanation to demonstrate knowledge), no "boring" functional-only paragraphs.

**Generation-approach change:** Bring writing craft principles into the generation: subtext, emotional truth, specificity of detail, trust in the reader. The generator should aim to write WELL, not to match a feature list. This means the Tell Analyst's job is literary evaluation ("where does the prose fall flat?"), not feature auditing ("which tells remain?").

### RC4: No accumulated relationship with the material

The real author has 273 chapters of accumulated knowledge, emotional investment, and creative discovery. The generator has 4 example chapters. No prompt can replicate that depth. This is the hardest root cause because it's partially architectural.

**Tells this explains:** explains too much (doesn't trust reader familiarity), lore avoidance vs. lore confidence, characters that feel researched rather than known, world details that feel referenced rather than remembered.

**Partial generation-approach change:** Give the generator deeper context (10+ chapters, world bible, character relationship history). Frame the task as inhabiting the author's perspective ("you have been writing this serial for 4 years, you know things about these characters that will never appear on the page") rather than matching the author's features ("reproduce these speech patterns and formatting conventions").

### The meta-learning

The Iter1-3 failure wasn't that the generator was bad — it was that the iteration loop was operating at the wrong level. The analyst reported tells (surface). The main worker converted tells directly into prompt patches (surface → surface). What was missing: the EXTRAPOLATION step (surface → root cause → lasting generation-approach improvement). Every root cause above points to a change in what the generator RECEIVES (character psychology, situation instead of outline, craft principles, deeper context), not in what it's told to AVOID.

This is the same pattern as "instructions don't work; structural changes work" (from development-loop-learnings.md), but applied to creative generation rather than analytical tools.

## Failure Modes Observed (Delve V2)

### 1. Completion bias
**Pattern:** Worker stops after executing procedure rather than achieving target.
**Fix:** Achievement-based stop condition + watchdog cron.
**Example:** "3 runs scored" treated as stop condition instead of ">50% on all 3 runs."

### 2. Tell analysis contaminated by narrative
**Pattern:** Worker interprets judge outputs to confirm existing progress story.
**Fix:** Separate Tell Analyst role that sees only judge outputs.
**Example:** grep artifact on verbose judge output → false "Sonnet breakthrough" → wasted iteration cycle.

### 3. Whack-a-mole without strategic synthesis
**Pattern:** Each iteration fixes the previously cited tells, but judges find new tells at the same rate. Score doesn't improve.
**Fix:** Tell Analyst should track tell persistence across rounds. If tells shift category (formatting → structural → prose) but score is flat, the main worker should consider approach changes, not more prompt tweaks.
**Example:** Iter1 fixed formatting artifacts (+0pp). Iter2 fixed dramatic structure (+0pp). Both were real tells, but fixing them just revealed deeper ones.

### 4. Data pipeline contamination gating evaluation quality
**Pattern:** Judges detect extraction artifacts (watermarks, run-together words, formatting damage) rather than generation quality. All downstream iteration is wasted until pipeline is fixed.
**Fix:** Tell Analyst should explicitly flag "meta tells" (pipeline-level) vs "generation tells" (prose-level). Pipeline tells must be fixed before generation iteration begins.
**Example:** 60+ trials measured extraction quality before the run-together-word artifact was identified and fixed.

### 5. False signal from imprecise result extraction
**Pattern:** grep on verbose judge output hits intermediate analysis text, not final verdict. Creates false progress signals.
**Fix:** Tell Analyst must extract verdicts from structured summary lines only, never from body text. Validate extraction method on known-correct examples before trusting scores.
**Example:** Sonnet's intermediate analysis discussed "Verdict: A" for the synthetic before concluding "Verdict: B" (correct). grep hit the intermediate mention.

### 6. Constraint accumulation trap
**Observation:** Across Iters 1-3, the generation prompt's constraint list grew with each iteration (more features to match, more tells to avoid, more specific ratios and counts). Scores declined: 25% → 12.5% → 0%.
**Correlation (not proven causal):** Longer constraint lists correlated with worse scores. Each iteration was more "correct" on previously-cited dimensions but more detectable overall.
**Hypothesis:** Growing constraint lists may produce writing that feels assembled rather than authored — each added rule makes the output more mechanical, even if each individual rule is sensible. If true, the fix is to change what the generator receives: deepened understanding of the material rather than growing feature checklists. This remains untested.
**Alternative hypotheses to consider:** The declining scores may also be caused by: the specific comparison chapter being exceptionally distinctive; the particular scene choices getting worse; overcorrection on each axis (too much combat → too little combat); or some combination. The constraint-accumulation explanation is plausible but not isolated.
**Example:** Iter3 scored 0% despite matching more surface features than any previous attempt. Judges cited "sitcom structure," "performed character signatures," "too structurally tidy." Whether this was caused by constraint accumulation specifically, or by the scene/approach choices, or by evaluation framing bias, is unclear.

### 8. Forward-only iteration (failure to backtrack)
**Observation:** Across Iters 1-3, the agent always iterated forward from the latest attempt, never backtracking to a better previous state. Iter1 scored ~25%. Iter2 scored ~12.5% (worse). The agent iterated forward from Iter2's approach rather than returning to Iter1's approach and trying a different direction. Iter3 scored 0% (worse still). The agent again iterated forward.
**Pattern:** The iteration loop is treated as a forward march — each iteration builds on the latest. There is no mechanism for "that was worse, go back and try differently." This is a systematic bias: the agent treats the latest state as the current state, ignoring that the BEST state may be an earlier one.
**Fix:** Track best-so-far score and the approach that produced it. When a new iteration scores worse, BACKTRACK to the best-so-far approach and try a different direction from there. The iteration loop is a search through approach space, not a linear sequence. Moving forward from a worse position compounds the error.

### 7. Evaluation framing bias
**Observation:** The evaluation prompts in Iters 1-3 told judges "one chapter is AI-generated, determine which." Gemini in one trial cited the file path (`synthetic-chapter.md`) as evidence rather than evaluating writing quality. Other judges' reasoning frequently referenced "AI patterns" and "AI tells" rather than literary quality dimensions.
**Hypothesis:** When evaluators are told to "spot the AI," they may anchor on stereotypical AI patterns (uniform polish, safety, structural tidiness) rather than performing genuine literary comparison. Reframing as "which is the original?" — without loaded terms — may produce feedback oriented toward literary quality rather than toward AI stereotypes. This would change the signal available to the Tell Analyst and main worker.
**Untested:** Whether reframing actually changes evaluator behavior or verdict accuracy. It's possible judges evaluate the same way regardless of framing.

## Style Reference Bias (observed, verified)

**Finding:** When two REAL passages by the same author are compared, with the evaluator told "one is original, one is a copy," the evaluator reliably identifies the passage MORE SIMILAR to the style references as the original. Tested: Opus compared S1 (chapter 37) against S4 (chapter 101), with style references from chapters 38 and 57. Opus declared S1 the original with medium confidence. Both are genuine.

**Implication:** The evaluation measures "similarity to the style references" in addition to (or instead of) "synthetic vs real." If style references are from a different era than the comparison target, the evaluation is biased. All passages less similar to the references — whether because they're synthetic OR because the author's style evolved — will be flagged as copies.

**Fix:** Style references must be from the same era/style-period as the comparison target. If comparing against a chapter-101 passage, use chapters ~95-110 as references, not chapters 38 and 57. This isolates the "synthetic vs real" signal from the "style drift" signal.

**This means the 0/27 snippet score may be partially inflated by reference bias.** The synthetics were being compared against passages whose era-match to the references was better than the synthetic's era-match. A fairer test would use era-matched references, which might produce different results.

## Evaluation Granularity

**Start small, scale up.** When an iteration loop isn't converging, reduce the unit of evaluation to the smallest meaningful piece. A 500-word snippet isolates writing quality (voice, specificity, character depth, dialogue) from structural concerns (pacing, arc, scene transitions, combat choreography). If the synthetic can't match the original at 500 words, scaling to 6000 won't help. If it can, the prose foundation is solid and structural dimensions can be tested separately.

**Practical protocol:**
- Pre-select ~20 solid snippets (~500 words each) from the source material
- Categorize by situation type: combat, social/banter, introspection, exploration, theorycrafting
- Exclude system screens and stat blocks — test prose, not formatting
- **Leave-one-out within each type:** For a type with snippets A, B, C, D — to evaluate against A, the generator sees B, C, D as examples and generates a new snippet. The generator NEVER sees the comparison target. This prevents paraphrasing and maintains the V2 protocol's core constraint.
- This enables fast iteration (10x faster generation, faster evaluation, more cycles per hour)

**Why diverse situation types:** Different modes of prose (combat, dialogue, internal monologue, world-building) have different quality profiles. The synthetic may match some modes before others. Testing across types reveals which modes are hardest and lets iteration focus on the weakest.

**Durable principle: isolate the binding variable by shrinking the evaluation unit.** This is the creative-evaluation equivalent of unit testing before integration testing. Test the smallest meaningful unit (prose quality in a focused passage) before testing the integrated system (full chapter with structure, pacing, arc). When the unit tests pass, scale up.

## Durable Principles

1. **Stop conditions must be achievement thresholds, not procedural milestones.**
2. **Separate analysis from action to prevent confirmation bias.**
3. **Audit the data pipeline before trusting evaluation scores.**
4. **Track quality gaps across rounds, not just their presence in one round.**
5. **When scores are flat or declining despite iteration, the methodology is wrong, not just the generation.** Declining scores across iterations that each add more constraints is the signature of the constraint-accumulation trap. The fix is not "try harder at the same approach" — it's "reorient the approach entirely."
6. **Hypothesis: optimizing for quality rather than detection avoidance may be more effective.** Observed: three iterations of increasingly precise feature-matching scored 25% → 12.5% → 0%. Inference: directly optimizing "avoid detection" may produce writing that matches features but lacks authenticity. An alternative approach — optimizing for genuinely good writing — has not yet been tested. If good writing is inherently harder to distinguish from the original, then quality-first would outperform feature-matching. This is plausible but unproven.
7. **The Tell Analyst should evaluate on literary dimensions; the main worker should extrapolate to hypotheses about root causes.** Proposed approach (to test): the analyst evaluates writing quality — voice, character, specificity, emotional truth, dialogue, scene construction, pacing — using established literary evaluation practices. The main worker formulates testable hypotheses about what in the generation approach produces the observed quality gaps, and tests them one at a time.
8. **Extrapolate surface observations to possible root causes, but test rather than assert.** If a judge says "characters share a register," possible root causes include: insufficient source material, voice built from tics rather than psychology, over-constrained generation, or something else. The main worker should formulate these as hypotheses and test them — not assert one as the cause and build the next iteration around an untested assumption.
9. **The Tell Analyst advises; the main worker decides.** The analyst lacks historical context and sees one facet. Its output is structured literary evidence, not instructions. The main worker synthesizes analyst findings with iteration history, trajectory, and strategic judgment.
10. **Hypothesis: evaluation framing affects feedback quality.** "Which is the original?" may produce different (potentially better) signal than "which is AI-generated?" To test: run the same comparison with both framings and compare the reasoning quality.
11. **The best attempt is the best across ALL attempts, not the latest.** Track best-so-far score and approach. When a new iteration scores worse, backtrack to the best-so-far and try a different direction. The iteration loop is a search through approach space. Moving forward from a worse position compounds error. The agent's default bias is to always iterate forward — actively resist this.
12. **When the iteration trajectory is negative, question the methodology, not just the generation.** Declining scores across iterations that each "improve" on the previous suggest the improvement framework itself may be counterproductive. Consider: what kind of problem is this? What evaluation and iteration practices are appropriate for this kind of problem? Draw on established practices from the relevant domain (in this case, literary evaluation and writing craft), not just on generic optimization methodology.
