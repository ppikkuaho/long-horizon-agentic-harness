# What Makes an Instruction Actionable

Discovered through iterating on 67 cognitive module files across 5 rubric versions and ~100 subagent evaluations, then cross-validated against exemplars and different instruction formats. This is the specification for writing instructions that produce behavior — in LLMs, in humans, in any system that reads instructions and is supposed to act on them.

## The Chain

Every actionable instruction completes a chain: **trigger → action → result.**

- **Trigger:** When does this fire? A specific moment, condition, or signal. Not "generally" or "as a practice" — a recognizable situation that activates the instruction.
- **Action:** What do you do? A concrete operation that produces something observable — a question that yields an answer, a transformation that changes output, a procedure that generates an artifact, a decision with branches.
- **Result:** What does the action produce? If the action asks a question, the result specifies what to do with the answer. If it detects a condition, the result specifies the response. If it branches, both branches have concrete next steps.

An instruction that stops before completing the chain is direction, not instruction. "Ask yourself X" without saying what to do with the answer is a dangling question. "Notice whether Y" without saying what to do if yes is a dangling detection. "Look for Z" without saying what to do when you find it is a dangling search. These are A-tier at best — they point in the right direction but don't hand you the operation.

One common and legitimate pattern: **asymmetric branching.** Many useful instructions have a YES path that's implicit ("proceed") and a NO path that's explicit ("take corrective action"). This isn't incomplete — it's efficient. The NO clause must be complete, but when the YES answer means "you're on track, keep going," leaving it implicit is fine. Example: "Ask 'Am I changing what the system does, or just how much?' If only adjusting quantities, escalate to rules/goals/information flows." The YES case (you ARE changing system behavior) implicitly means: proceed.

**Diagnostics without remediation** are acceptable when the failure mode is self-evident enough that the reader knows what to do: "If you can't articulate the old and new assumption, you haven't actually shifted frames" — the remediation (go back and actually do the shift) is obvious from context. Diagnostics that expose non-obvious failure modes SHOULD include explicit remediation.

## What Counts as Action

The critical distinction we kept running into: the difference between observation and action.

**Action verbs that produce results (S-tier):**
- "Ask: 'What's the base rate?'" → produces an answer
- "Replace hedge words with numbers" → produces transformed text
- "List three assumptions" → produces an artifact
- "Commit to approach X for 10 minutes" → produces an attempt
- "Write down your reasoning before learning the outcome" → produces a record
- "State the rule you're breaking and the outcome that justifies it" → produces an articulation (forcing yourself to articulate is itself an action — it produces a commitment that's harder to reverse than an unspoken decision)
- "Compare the two explicitly before committing" → produces a comparison

**Observation verbs that don't produce results (A-tier at best):**
- "Notice whether X" → you've observed, but then what?
- "Be aware of Y" → awareness without procedure
- "Recognize that Z" → fact acknowledged, no operation
- "Be suspicious of W" → stance adopted, no follow-through

The test: after executing the instruction, can you point to something that exists now that didn't exist before? An answer, an artifact, a decision, a changed text, a comparison, a commitment? If yes, it's action. If the only result is that you now "know" or "are aware of" something, it's observation.

**Two important nuances:**

Observation verbs are banned as the ACTION, not as the TRIGGER. "When you notice defensiveness rising, restate the opposing view" is S-tier — the trigger is observation, but the action is concrete. "Notice whether the disagreement matters" as the entire move is A-tier — the observation IS the action, and there's no follow-through.

Observation verbs in decision contexts can work when anchored. "Ask: 'Is this a case where consequences should override?'" is technically an observation verb ("ask"), but when it's anchored by a clear trigger ("when following a rule produces harmful outcome") AND a decision-forcing result ("if you can't name the specific harm, keep following it"), the question becomes a forced decision point, not optional reflection. The key: the result clause must close the chain by forcing a concrete next step regardless of the answer.

## What Counts as Trigger

The trigger needs to be a recognizable moment — something you can actually notice happening.

**Clear triggers (S-tier):**
- "When you feel very confident" — internal signal, recognizable
- "Before estimating anything" — temporal, clear moment
- "Every 20-30 minutes during extended work" — scheduled/periodic
- "When a fix creates a new problem" — event-based
- "After finishing a challenging task" — temporal, clear boundary
- "When you feel a strong immediate reaction — certainty, defensiveness, obviousness" — metacognitive discomfort as trigger (intensity is a reliable proxy for "your default is firing")

**Weak triggers (A-tier):**
- "For practical work" — domain, not moment
- "Practice X" — ongoing orientation, no when
- "Deliberately seek Y" — aspiration, no activation point
- "Every few uses" — vague frequency
- "For any important belief" — broad standing instruction (works as a general policy but lacks the moment-specificity of S-tier triggers)

**No trigger (B-tier or below):**
- "Build habits of X" — life advice
- "Focus on principles" — priority, not trigger

## System Coherence

Three instructions that individually complete the chain can still be three unrelated tips. The difference between tips and a system: the instructions cover different parts of the problem lifecycle, and together they provide complete coverage.

Patterns that work:
- **Temporal workflow:** pre-action / during-action / post-action
- **Branch-and-respond:** diagnose type → if A, do X → if B, do Y
- **Escalation:** detect → accumulate evidence → trigger response at threshold (theoretical — emerged from analysis but not yet demonstrated in an exemplar)
- **Diagnosis-monitoring-improvement:** test → track → calibrate
- **Redundant detection:** same failure mode caught via different triggers (e.g., reasoning check + emotion check both catch "resulting")
- **Multi-angle attack:** same threat model addressed from different angles (e.g., moral rationalization caught via evasion check, confidence check, and articulation check)

Each instruction addresses a different aspect. Together they cover the problem. You can tell it's a system because removing any one instruction leaves an operational gap — something you could do before that you can't do now.

Instructions can share the same failure mode (redundant detection) but must address it from different angles or temporal positions. Two instructions that fire at the same moment and do the same thing are redundant. Two instructions that catch the same problem via different triggers or at different times are reinforcing.

Sub-patterns that strengthen coherence: moves addressing different threat models (bias, denial, defensiveness), moves layering prevention + detection + recovery, moves forming a closed loop (diagnosis → action → learning → diagnosis).

## Self-Diagnostic

The strongest instructions include a test that tells you whether you're failing. "If you can't answer, the belief is floating." "If you never assign anything below 70%." "If your answer changes depending on the outcome, you're evaluating luck."

The self-diagnostic makes the instruction self-enforcing. Without it, you can follow the instruction and not know whether it worked. With it, the instruction tells you.

In practice, every file that reaches the highest quality tier has at least one self-diagnostic. They're not optional for excellence — they're the mechanism that closes the loop.

Self-diagnostics vary in strength:
- **Time-bound** ("if you never flag anything across a week of decisions") is more actionable than vague ("if you can't")
- **Quantified** ("if aware >5 minutes without changing") gives a concrete threshold
- **Nested** diagnostics — a diagnostic about your diagnostics — are the strongest theoretical form: "If you never flag anything in a week, your interception threshold is set too high" tells you not just that you failed, but that your failure-detection system itself is miscalibrated. In practice this is rare and aspirational — most S+ files achieve excellence without nesting
- **Redundant detection** (same diagnostic reachable via different triggers) is more robust than single-point detection

## Separation of Concerns

Instructions deploy the concept. They don't explain it. The explanation belongs in a different section (in our case, "What This Is"). If the instruction is still teaching you what the concept means, it's doing two jobs and doing both badly. Explanation creates understanding. Instructions create action. Keep them separate.

## Brevity Is Functional

Each instruction should be 1-2 sentences. This isn't a stylistic preference — it's a design constraint that forces:
- Single-operation focus (not compound procedures that blur the chain)
- Explicit triggers (no room for vague "generally" or "as a practice")
- Clear results (no trailing implications or secondary advice)

Branch-and-respond patterns can fit within 2 sentences when branches are alternative paths through the same decision. The test: do all branches share the same trigger and decision point? If yes, they belong together. Two-branch cases fit cleanly in 2 sentences. Three-branch cases (e.g., "do I need episteme, techne, or phronesis?") may need 3-4 sentences to give each branch a concrete action — that's acceptable when the branches are exhaustive alternatives through a single diagnostic question. The constraint isn't sentence count per se; it's single-operation focus. Multiple branches of one decision are one operation.

## Format Classes

The chain requirements vary by instruction format. The spec was derived from steering moves (short, discrete instructions), but the principles apply with different severity to other formats:

| Format | Chain requirement | Why |
|--------|------------------|-----|
| **Steering moves** | Complete chain mandatory | Single operation, must fire and produce result |
| **Process files** | Each step completes chain; steps form system | Multi-step workflow, each step is a chain |
| **Per-turn injections** | Partial chain OK if delegating to external procedure | Job is behavioral reminder, not full operationalization |
| **Nudges/briefs** | Trigger + direction sufficient; can point to external checklist | Job is to remind, not to teach |

The core criteria (trigger clarity, action vs observation, chain completion) are format-independent. But the severity of violations varies: a per-turn injection that says "reflect on modules" is acceptable as a nudge (it's supposed to be a compass, not a manual), while the same text as a steering move would be A-tier at best (dangling observation).

## Where This Applies

This specification is about any instruction that's supposed to produce behavior:
- Checklists and procedures
- Agent prompts and system instructions
- Skill files and behavioral briefs
- Process documentation
- Teaching materials (the exercises, not the exposition)
- Any place where someone reads a sentence and is supposed to DO something

The test is always the same: does the instruction complete the chain? Trigger → action → result. If it does, it will produce behavior. If it doesn't, it will produce awareness at best and nothing at worst.

For different format classes, adjust the severity of chain requirements (see Format Classes above), but never abandon the underlying principle: instructions exist to produce action, not awareness.

## How We Got Here

We didn't design this specification. We discovered it by:
1. Rating 67 files against a rubric and finding the rubric couldn't distinguish quality consistently
2. Studying the 8 files that all evaluators agreed were excellent and asking what they shared
3. Finding the common patterns (chain, trigger clarity, action vs observation, system coherence)
4. Encoding those patterns into the rubric
5. Testing until different evaluators produced the same scores
6. Using the rubric to refactor all 67 files
7. Validating independently that the refactored files actually improved
8. Cross-validating the spec against different exemplar sets and different instruction formats
9. Finding gaps (observation verbs in decision contexts, branching within brevity, format classes, diagnostic nesting) and updating

The specification emerged from the data, not from theory. Each criterion exists because its absence produced a measurable quality drop that independent evaluators consistently caught. The cross-validation rounds caught criteria that were too broad (observation verb ban needed nuance) and areas the spec was silent on (format classes, diagnostic time-bounds, branching patterns).
