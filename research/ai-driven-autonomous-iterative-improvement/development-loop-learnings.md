# Development Loop Learnings

Collected findings about running AI-driven iterative development and improvement cycles. Sourced from the InternalAI 2.0 project (tool design, evaluation design, methodology development). Primary evidence base: `projects/internal-ai-2.0/design/tool-design-learnings.md`.

> **Related (2026-04-11):** This file focuses specifically on iterative improvement loops. The broader operating frame for AI task orchestration — of which the iterative loop is one application — is codified at `projects/ai-architecture/design/orchestration-frame/frame.md`. The frame covers task shaping, decomposition, delegation, and evaluation as a unified discipline organized around the completion drive as the load-bearing insight. When the iterative loop is the primary work, this file is the more detailed reference; when orchestration more generally is the concern, the frame is the entry point.

## The Iteration Loop Shape

The core loop for developing any methodology or tool:

```
Design → test (subagent) → independent evaluation (separate subagent) →
structural fix → re-test → [practitioner pivot when the approach itself
needs to change] → re-test → lock
```

Three roles, strictly separated:
- **Builder** — designs methodology, reads evaluator feedback, decides fixes
- **Tester** — executes methodology on real data. Has methodology only, no evaluation context.
- **Evaluator** — evaluates test output against a rubric. Has rubric + output only, no design context.

The builder who designed the fix will systematically under-detect failures in its own work. The evaluator has only the rubric — it can't rationalize borderline results. Source: `projects/internal-ai-2.0/design/tool-design-learnings.md` Part 2.

## What Types of Fixes Work

**Structural changes work. Instructions don't.**

Empirical comparison (Change Factor Tool, 8 iterations):
- Instruction additions (+validation test, +perspective audit, +frontier disruptions): +59 factors, +3 coverage, -1 relevance. Shallow compliance.
- Process architecture change (gap-analysis second pass by separate agent): +30 factors, +20 coverage, +6 quality dimensions. 7x improvement with half the extra output.

Why: instructions tell the model to also think about X within the same cognitive framework. The model complies by producing more output of the same type with the instruction's vocabulary sprinkled in. Structural changes create genuinely different generation contexts — different tasks, different starting points, different agents.

Types of structural changes that have worked:
- Brainstorm-first (before framework anchoring)
- Stakeholder positions (multi-perspectival generation)
- Separate agent for gap analysis
- Removing selection mechanisms (prevent reduction bias)
- Reordering steps (put unstructured thinking before structured scanning)
- Renaming sections to scope their content (the section name is the strongest behavioral signal)
- Changing the output format specification ("lead with finding" changed output quality)

Source: `projects/internal-ai-2.0/design/tool-design-learnings.md` Parts 3-4.

## The Generalizability Gate

Before applying ANY fix to a methodology:
1. Does it address a root cause, not a symptom?
2. Would it work for any domain (not just the test domain)?
3. Does it prescribe a mechanism or test, not specific content?
4. Is it compatible with deployment constraints?

All four must pass. One skipped gate = one wasted test cycle. Source: `projects/internal-ai-2.0/design/tool-design-learnings.md` Part 4.

## Evaluation Design Learnings

### The evaluation mechanism shapes what iteration optimizes for

A count-based evaluation produces count optimization. A judgment-based evaluation produces genuine quality improvement. Before committing to an evaluation approach, ask: "If a tool perfectly satisfied this evaluation, would the output actually be good?"

### Comprehensiveness requires strategic context

Without a strategic frame defining which gaps matter, the analytical space is unbounded and the evaluation target is unreachable. Strategic context is what makes comprehensiveness finite and evaluable.

### Three-tier evaluation architecture

1. **Primary:** Judgment-based gap detection (tester → gap analyst → evaluator, three separate agents)
2. **Secondary:** Golden set comparison (accumulative, two-directional)
3. **Benchmark:** Cross-domain golden set suite (per methodology change)

### Rubrics describe outcomes, protocols describe processes

Keep them separate. Rubric levels describe what quality LOOKS LIKE at each level. Protocols describe how the evaluation is conducted. If rubrics reference the process, they break when the process changes.

### Evaluator role: confirmation + translation

The gap analyst does domain judgment. The evaluator confirms gap findings against the output and translates to preset rubric scores. Don't distribute domain judgment across both agents.

### [1-5] comprehensiveness scale

Based on ratio of original output to gap findings + significance of those gaps. Same scale at all aggregation levels (domain → nature type → overall). Significance over volume: one critical gap > many minor ones. Full traceability: every score traces back through the levels to specific findings.

Source: `projects/internal-ai-2.0/evaluation/evaluation-methodology.md`, `evaluation/evaluation-protocol.md`, `evaluation/spatial-evaluation-design.md`.

## Operational Meta-Learnings

### Document minimally during the loop, comprehensively at the end

Between iterations: score + one-line root cause + one-line fix. Save narrative documentation for after the campaign reaches its stop condition. The prior iteration campaign spent ~40% of time on between-round documentation. Source: `projects/internal-ai-2.0/design/tool-design-learnings.md` Part 4.

### Define the stop condition precisely and don't stop before it's met

Write it in the task. Check after each evaluation. If not met, keep going. Don't ask the practitioner "is this good enough?" Source: Same.

### The first run is diagnostic, not a test

Don't treat the first run's scores as a baseline. The first run reveals which parts of the methodology need structural fixes. The baseline is what you get after those fixes. Source: Same.

### Subagent testing is cheap — run tests frequently

Each subagent test costs ~3-10 minutes of background computation. Running early and often surfaces issues that design-alone can't catch. The pattern: design → test → surprise → fix → retest. The surprises are the learning. Source: Same.

### Design from real data, not theory

Don't pre-design methodology structures theoretically. Look at real data, ask "what can we extract from this," and let the methodology emerge from the data. Confirmed in the mental model methodology development: the methodology became operational the moment we examined actual survey responses.

### The unit of analysis matters more than the analytical framework

When a methodology produces adequate but not insightful results, ask whether the unit of analysis is wrong before refining the analytical framework. The mental model methodology breakthrough came from changing the unit (pooled responses → individual respondents), not from refining the analytical dimensions.

### Aggregate analysis can mask structurally different relationships

"Everyone mentions X" (aggregate) can hide "half the group treats X as existential, the other half treats X as background" (respondent-level). High-frequency mention does NOT imply shared meaning. Check whether the relationship to X is uniform or heterogeneous across respondents.

## Relationship to Multi-Model Parallel Development

The multi-model parallel pattern (documented in `README.md` in this folder) builds ON TOP of the iteration loop. Multi-model adds:
- Independent proposals for architecture validation
- Independent tests for finding validation
- Per-model innovations for synthesis
- Convergence/divergence mapping for practitioner decisions

The iteration loop is the foundation. Multi-model is an amplifier.

## Adversarial Evaluation Loop Learnings (Delve Writing Loop, 2026-04-13)

Source: `projects/ai-architecture/design/orchestration-frame/phase-2-runs/instances/delve-writing-loop/methodology/adversarial-iteration-loop.md`

### Constraint accumulation correlates with declining scores

Observed: across 3 iterations of an adversarial writing benchmark, the generation prompt's constraint list grew with each iteration (more features to match, more tells to avoid). Scores declined: 25% → 12.5% → 0%. Causation not isolated — other variables changed too. But the correlation suggests that instruction-based iteration has diminishing or negative returns for this task type, consistent with the general finding that "instructions don't work; structural changes work."

### The agent defaults to forward-only iteration

The agent always iterated from the latest attempt, never backtracking to a better previous state, even when scores declined. Iter1 scored 25%. Iter2 scored 12.5%. The agent iterated forward from Iter2 rather than returning to Iter1's approach. This is a systematic agent behavior: treating iteration as a linear sequence rather than a search through approach space. **Fix: track best-so-far explicitly. When scores decline, backtrack before trying a new direction.**

### Evaluation framing shapes the feedback signal

When judges were told "one is AI-generated, find it," they hunted for stereotypical AI patterns and produced feedback about AI artifacts. When told "which is the original?", they performed literary evaluation and produced feedback about voice, authenticity, and craft. The second framing produced qualitatively better reasoning. General principle: the evaluation prompt determines what the evaluator optimizes for, which determines what the builder receives as signal, which determines what the next iteration optimizes for. Frame carefully.

### Weak evaluators dilute signal

A judge that is fooled ~90% of the time (Haiku) adds noise, not signal. Its verdicts don't distinguish between "somewhat good" and "very good" outputs. Including it inflates the denominator and creates false progress signals. **Fix: evaluate discriminative power empirically, drop weak evaluators rather than averaging their verdicts.**

### Shrink the evaluation unit when iteration isn't converging

Switching from 6000-word chapters to 500-word snippets isolated writing quality from structural confounds (pacing, arc, scene transitions) and enabled 10x faster iteration. This is the evaluation equivalent of unit testing before integration testing. **General principle: test the smallest meaningful unit first. If the unit tests fail, scaling up won't help. If they pass, you know the foundation is solid.**

### Observation vs inference discipline in maintained artifacts

The agent repeatedly stated hypotheses as established facts in maintained artifacts ("the root cause IS X"). Future instances would inherit these assertions as doctrine. This is a systemic risk for any stateless agent system that relies on maintained artifacts for continuity. **Fix: artifacts must separate what was observed (data, scores, correlations) from what was inferred (hypotheses, explanations, proposed causes). Label inferences explicitly.**

### Always baseline the evaluation with known-good inputs

Before trusting an adversarial evaluation, test it with two REAL inputs to verify the evaluation methodology itself. In the Delve writing loop, comparing two genuine passages by the same author revealed that the judge declared one a "copy" with medium confidence — because the style references were from a different era than one of the passages, and the judge detected style drift within the author's own corpus. This meant all subsequent evaluations were confounded: the "0/27 score" mixed genuine synthetic-detection signal with style-reference-bias signal. Running the baseline BEFORE the main evaluation would have caught this immediately.

**General principle:** If your evaluation produces a non-zero false-positive rate on known-good inputs, the reported detection rate on real inputs is inflated by at least that amount.

### "Too polished" as a persistent pattern (hypothesis, not proven)

Across all tested approaches (constraint-based chapters, craft-oriented snippets, social scenes, combat scenes), judges consistently identified the synthetic output as "too polished, too clever, too neatly structured" compared to the original's "workmanlike, functional, slightly rough" prose. Whether this is a property of the prompting, the LLM's token-level optimization, or something else is not yet determined. If confirmed as architectural, this would imply that LLM-generated text has a systematic quality-uniformity bias that prompt engineering cannot fully address.

---

### The extrapolation step: surface tells → root causes → lasting improvements

When an evaluation loop produces feedback (tells, quality gaps, failure observations), there are two ways to use it:

**Transcription (tell → fix):** The analyst reports "characters share a register." The builder adds "make characters sound more different" to the prompt. This is the default behavior. It produces constraint accumulation and diminishing returns.

**Extrapolation (tell → root cause → approach change):** The analyst reports "characters share a register." The builder asks: WHY does the generation produce characters that share a register? Hypothesis: because characters are defined as trait bundles (verbal tics, speech patterns) rather than as people (motivations, fears, history, worldview). The fix isn't "add more voice differentiation constraints" — it's "replace voice profiles with character psychology profiles and let speech emerge from who the character IS."

The extrapolation step is the main worker's core contribution. The analyst sees one round's outputs. The builder sees the trajectory across rounds and understands the generation approach well enough to diagnose WHY surface symptoms appear. Without this step, iteration degrades into whack-a-mole: each round fixes the previously-cited tells, judges find new tells at the same rate, scores stay flat or decline.

**General pattern:** In ANY iteration loop (tool design, evaluation design, creative generation), the feedback signal describes SURFACE properties of the output. The iteration step must operate at a DEEPER level — changing what produces those surface properties. When the iteration step operates at the same level as the feedback (surface → surface), returns diminish. When it operates one level deeper (surface → root cause → structural change), lasting progress is possible.

This is "instructions don't work; structural changes work" applied to the iteration loop itself: the feedback-to-fix pipeline is an instruction layer. The feedback-to-root-cause-to-approach-change pipeline is a structural change.

Source: Delve V2 adversarial writing loop, Iter1-3 root cause analysis (2026-04-13). Full analysis at `projects/ai-architecture/design/orchestration-frame/phase-2-runs/instances/delve-writing-loop/methodology/adversarial-iteration-loop.md`.

---

## Autonomous Agent Idle Prodding: Architecture Requirement (2026-04-13)

Source: Codex watchdog investigation, Claude Code autonomous-prod reverse-engineering.

### The idle-prod pattern requires a runtime-native primitive

To keep an agent working autonomously past its natural stop point (completion bias, intractability declaration), you need a **scheduled synthetic user message** that fires when the agent is idle. This is what Claude Code's `CronCreate` does.

**The critical architectural requirement**: the scheduler must live **inside the agent runtime's own event loop**, at the exact point where the runtime transitions from "turn complete" to "waiting for user input." It cannot be an external wrapper, an API call from outside, or a TTY injection. Those paths create backend activity (turn IDs, queue entries, log lines) without the behavioral effect (agent sees a message, wakes up, responds).

Why: the agent runtime has two surfaces — the **control plane** (API, turn management, thread state) and the **behavior plane** (what the agent sees as its conversation). External injection only reaches the control plane. The behavior plane is only reachable from inside the event loop where user messages are processed.

**Failure mode observed**: 4 days of wrapper-layer engineering (TTY prod, turn/start API calls, relay queues, daemon lifecycle) that produced proxy metrics (daemon alive, turn created, request relayed) but zero behavioral effect. Every proxy metric was explicitly predicted as insufficient by the acceptance contract, but each was locally tractable and created a sense of progress.

**Durable principle**: when building agent infrastructure, distinguish "control plane success" from "behavior plane success." Infrastructure that produces observable side effects on the control plane (logs, state changes, API responses) can feel like progress while achieving nothing on the behavior plane (agent actually changes what it does). Define the acceptance criterion on the behavior plane and refuse to accept control plane metrics as evidence.

Full analysis: `~/Documents/codex/CODEX-IDLE-INJECTION-ANALYSIS.md`

### The deliverable boundary problem (2026-04-14)

When an agent is asked to build something, it will naturally stop at the first recognizable completion signal: "patch written," "code compiles," "binary installed." Each of these is a proxy metric for the actual deliverable, which is: **the thing works when the user uses it.**

Observed sequence: study mechanism → write patch → patch written (stop attempt #1) → user pushes → install toolchain → build fails (disk full) → user deletes 67GB file → build succeeds → binary installed (stop attempt #2) → user pushes → behavioral test still pending.

The acceptance contract explicitly listed "binary compiled" as a non-qualifying proxy metric on the second iteration. Without that update, a future instance would have inherited "binary installed, done" and never run the behavioral test.

**Durable principle**: the deliverable boundary for infrastructure work is not "code exists" or "binary compiles" — it's "the behavior changed as specified." When building something that modifies agent behavior, the acceptance criterion must be defined on observed behavior, and the agent must be pushed past the compilation/installation boundary to the testing boundary. This is the same control-plane-vs-behavior-plane distinction applied to the agent's own work process.

### Patching compiled third-party tools from source (2026-04-14)

When the target runtime is a compiled binary (Rust, Go, C++) rather than an interpreted one (Python, JS), the build-from-source path is viable but has operational constraints:
- **Disk**: Codex's dependency tree needed ~8GB of scratch space for a release build with LTO
- **Time**: 8 minutes on Apple Silicon for a full release build, ~2 minutes for incremental after first build
- **Toolchain**: Exact Rust version matters — repo specified 1.93.0, needed `rustup install 1.93.0`
- **Pre-existing bugs**: The repo itself had a compilation error (`AbsolutePathBuf` vs `PathBuf` in `updates.rs`) unrelated to the patch, requiring a fix before the build could succeed
- **API surface**: Test-only methods (`#[cfg(test)]`) are invisible to production code — needed a proper public accessor

The alternative — contributing upstream via PR — is slower but avoids the maintenance burden of carrying a local binary patch. The choice depends on urgency. For this case, local patch was correct because the goal is to test a hypothesis about agent behavior, not to ship a product.

**macOS binary replacement pitfall**: macOS kills unsigned binaries (SIGKILL, appears as `zsh: killed`). When replacing a signed/notarized binary with a locally-built one, ad-hoc sign it: `codesign --sign - <binary>`. Also verify you're building the correct crate — a Rust workspace may have a top-level dispatcher binary (`cli/`) that links internal crates as libraries (`tui/`). Building the library's binary name doesn't produce the same executable as the distributed one.

### Reverse-engineering a working system beats designing from first principles (2026-04-14)

The Codex watchdog went through 4 days of attempted designs (instructional guardrails, TTY injection, wrapper runtimes, API turn/start) that all failed. Resolution came in a single session by reverse-engineering how Claude Code's `CronCreate` actually works — reading the tool spec, tracing the code path, and replicating the exact same architecture.

The pattern: when a working example of the desired behavior exists in a different system, **study the working example first** before designing. The working example reveals which architectural constraints actually matter (scheduler must be inside the event loop, injection must go through the same channel as real input) and which apparent constraints are illusory (doesn't need to be external, doesn't need API access, doesn't need TTY control).

This is "design from real data, not theory" applied to system architecture. The 4 days of prior work designed from theory about what injection should look like. The successful session studied what injection actually looks like in a system where it already works.

### Acceptance contracts as proxy-metric firewalls (2026-04-14)

The acceptance contract (`~/Documents/codex/WATCHDOG-ACCEPTANCE-CONTRACT.md`) served three functions across this multi-session arc:

1. **Prevented drift** during the initial 4-day wrapper engineering phase. Each wrapper milestone (daemon alive, relay working, turn/start returning IDs) was locally tractable and created the sensation of progress. The contract's explicit "what does not count" list blocked each from being declared as success.

2. **Prevented premature completion** during the build phase. The agent stopped twice — once at "patch written" and once at "binary installed." Adding "successful compilation" to the forbidden-proxy list after the first stop attempt prevented the second from sticking.

3. **Survived correctly when the behavioral test revealed a gap**. The synthetic message doesn't appear in the user-facing transcript (the agent sees it, the user doesn't see the prompt bubble). The contract's condition said "visible in the live session transcript." Rather than retroactively weaken the condition, the right response was to acknowledge the gap, classify its severity, and document the root cause for future fix. The contract now reflects what was actually achieved, not what was hoped for.

**Durable principle**: for any multi-session infrastructure task, write an acceptance contract before starting. The contract must: (a) define success on the behavior plane, not the control plane; (b) explicitly list common proxy metrics that do not count; (c) be updated during the work to add newly-discovered proxy metrics as they appear; (d) be evaluated honestly when the behavioral test reveals partial success.

### Three planes of system behavior (2026-04-14)

This arc revealed that "control plane vs behavior plane" is actually a three-way distinction:

| Plane | What it means | Codex example |
|-------|--------------|---------------|
| **Control plane** | Infrastructure signals: API responses, state changes, log entries | `turn/start` returns a turn ID |
| **Behavior plane** | What the agent actually does in response to input | Agent receives the watchdog prompt and resumes work |
| **Display plane** | What the user sees in the UI | Watchdog prompt appears as a chat bubble in the transcript |

The previous failure (Apr 9–13) only reached the control plane. The current implementation reaches the behavior plane but not the display plane. A full solution reaches all three.

The display plane gap exists because the injection enters at the `App` layer (below the widget), not at the `ChatWidget` layer (where user messages get rendered). The behavior plane works because `submit_active_thread_op` → `turn_start` is the same path as real input from the app-server's perspective. The display plane gap is fixable by adding a synthetic history cell before calling `submit_active_thread_op`.

This three-plane model applies generally: any time you're injecting behavior into a system with a UI, test all three planes independently. Control-plane-only success is the most common failure mode (looks like it works from the logs). Behavior-plane-without-display is subtler — it works but the user can't observe it working.

---

*Created: 2026-04-08*
*Updated: 2026-04-14 (watchdog accepted; three-plane model; acceptance contracts as proxy-metric firewalls; reverse-engineering methodology; deliverable boundary lesson; source-patching operational constraints)*
*Primary source: `projects/internal-ai-2.0/design/tool-design-learnings.md`*
*Secondary source: `projects/ai-architecture/design/orchestration-frame/phase-2-runs/instances/delve-writing-loop/methodology/adversarial-iteration-loop.md`*
*Tertiary source: `~/Documents/codex/WATCHDOG-ACCEPTANCE-CONTRACT.md` (acceptance contract that governed this arc)*
