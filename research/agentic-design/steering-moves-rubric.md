# Steering Moves Quality Rubric

Scoring criteria for evaluating cognitive config module detail files. Derived from analysis of S+ exemplars and iterative testing across multiple evaluators.

## Per-Move Scoring

Each of the 3 steering moves is scored independently on three criteria: trigger, action, deployability.

### Criteria Definitions

**Trigger condition:** The move specifies WHEN to fire — a situation, moment, condition, or signal that activates it.
- Clear trigger: "When you feel very confident...", "Before estimating anything...", "Every 20-30 minutes...", "For any important belief..."
- Weak/implicit trigger: "For practical work..." (domain, not moment), "Deliberately..." (ongoing orientation)
- No trigger: "Practice X", "Build habits of Y" (no when specified)

**Specific action:** The move tells you to DO something that produces a concrete result — a question that yields an answer, a transformation that changes output, a procedure that generates an artifact, a decision with branches.
- Concrete actions (S-quality): Must use action verbs that produce a concrete, observable result. "Ask: 'What's the base rate?'" → produces an answer. "Replace hedge words with numbers" → produces transformed text. "Commit to any approach for a fixed time" → produces an attempt. "List the assumptions" → produces an artifact. Key test: can you point to what the action produced?
- Observation/awareness verbs are NOT concrete actions: "Notice whether X", "Be aware of Y", "Be suspicious of Z", "Recognize that X" — these ask you to observe or adopt a stance, not to do something that produces a result. They are A-tier at best, even when paired with a clear trigger.
- Directional but vague (A-quality): "Look for information flow interventions" → you know the category but not the method. "Build procedural fluency through practice" → goal without procedure. "Notice whether the disagreement matters" → observation without next step.
- Interpretive guidance (B-quality): "Treat X as diagnostic" → tells you how to think, not what to do. "Expect Y" → expectation-setting, not operation. EXCEPTION: interpretive guidance that includes concrete branching responses with actions ("if A → do X, if B → do Y") counts as a concrete action.
- Warnings without procedure (C-quality): "Don't jump to revolutionary mode prematurely" → constraint without trigger or alternative action. "Be suspicious of understanding that arrives too easily" → stance without procedure.
- Statements of fact (C-quality): "Phronesis is the hardest to develop" → no trigger, no action, no procedure. Could appear in a textbook's exposition.

**Immediately deployable:** Reading the move gives you everything you need to act right now — no additional interpretation, setup, or domain-specific knowledge required.

**Self-diagnostic (bonus):** The move tells you whether you're succeeding or failing. ("If you can't answer, the belief is floating." "If you never assign anything below 70%...") Not required for S-tier but marks exceptional moves.

### Tier Assignment

**S-tier:** Has all three — clear trigger + concrete action + immediately deployable. Additionally, the move must complete the full chain: trigger → action → result. If the move asks a question, it must specify what to do with the answer. If the move lists options, one must be concrete enough to execute. If the move detects a condition, it must specify the response. A move that stops before producing a result is A-tier at best.

**A-tier:** Has direction and substance but is missing exactly one criterion:
- Concrete action + deployable but no trigger ("Practice the ideological Turing test" — good technique, when do you use it?)
- Trigger + deployable but action is directional ("When planning an intervention, look for information flow changes" — good trigger, vague action)
- Trigger + concrete action but requires interpretation to deploy

**B-tier:** Missing two criteria. General advice, orienting principles, or interpretive guidance without concrete next steps:
- "Practice identifying which beliefs feel identity-laden" — no trigger, no specific procedure
- "For practical work, anti-realism is often more productive" — weak trigger, no action
- "Track anomalies" — no trigger, goal without method
- "Treat the inability to operationalize as diagnostic" — trigger present but action is interpretive without branching response

**C-tier:** Could appear in a textbook's exposition or a warning label, not in its exercises. No actionable content — you can't DO anything with it:
- Statements of fact: "Phronesis is the hardest to develop" — true, but what do you do?
- Expectation-setting: "Expect the transition to be disorienting" — prepares you emotionally but gives no operation
- Warnings without procedure: "Don't jump to revolutionary mode prematurely" — tells you what NOT to do without a trigger or alternative action
- Stance without follow-through: "Be suspicious of understanding that arrives too easily" — attitude without next step (suspicious of it, then what?)

The B/C boundary: B-tier moves give you a DIRECTION you can understand but not immediately execute ("Track anomalies", "Look for information flow interventions"). C-tier moves give you INFORMATION, WARNINGS, or STANCES with nothing to work with operationally ("Don't do X", "Expect Y", "Be suspicious of Z").

## File-Level Scoring

Err strict — it's worse to pass a weak file than to flag a decent one for improvement.

- All 3 moves S-tier → **S** (check S+ criteria below)
- 2 S-tier + 1 A-tier → **A**
- 3 A-tier → **A**
- 2 S-tier + 1 B-tier → **A** (two strong moves carry, but the B move needs fixing)
- 1 S-tier + 2 A-tier → **A**
- 1 S-tier + 1 A-tier + 1 B-tier → **B** (insufficient strength to compensate)
- Any other combination with B-tier moves → **B**
- Any C-tier move present → drop one tier from what it would otherwise be (e.g., ABB with one C becomes C)

## S+ Checklist (file-level excellence)

A file reaches S+ when:
1. All 3 moves are individually S-tier
2. The 3 moves **form a coherent system**, not just three independent tips — they cover different parts of the problem lifecycle in a way that provides complete coverage. Common patterns: temporal workflow (pre/during/post), branch-and-respond (diagnose → if A do X, if B do Y), sequential procedure (step 1 → 2 → 3), diagnosis-monitoring-improvement
3. **Separation of concerns** — steering moves deploy the concept, they don't re-explain it (that's What This Is's job)
4. At least one move includes a **self-diagnostic** that tells you if you're at the wrong pole

## Structural Rules

- Steering moves section has exactly 3 bullets
- Each bullet is 1-2 sentences (not a paragraph)
- The "What This Is" section does the explanatory work — steering moves are pure operation
- "Signs You're At Each Pole" provides the recognition patterns — steering moves provide the response patterns
