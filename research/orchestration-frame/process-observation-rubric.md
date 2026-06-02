# Process Observation Rubric — Orchestration Frame Phase 2 Experiments

*Companion to `frame.md` and `frame-design-notes.md`. First-pass rubric for evaluating whether a coordinator applied the orchestration frame's principles correctly when running a task. Created 2026-04-11. Provisional — not yet adversarially validated.*

## Purpose and scope

This rubric is for evaluating **whether the coordinator's orchestration process followed the frame**, not whether the task's output was good. It observes process adherence, not result quality.

**In scope:**
- Did the coordinator apply the frame's principles during orchestration?
- Did the coordinator make structural decisions (decomposition, delegation, evaluation) consistent with the frame?
- Did the coordinator use the audits and rubrics the frame prescribes?
- Did the coordinator avoid the failure modes the frame names?

**Out of scope:**
- Whether the task's final output was correct or high-quality
- Whether the task was picked well
- Whether the frame's principles are correct (that is what the experiments across many runs will test indirectly, not what any single evaluation decides)

The sequencing matters. First we need to know that the pipeline runs as designed — the coordinator actually applies the frame, the roles stay separate, the audits fire, the decompositions follow the rules. Only after the process is operating reliably does it make sense to measure whether the process produces better results than naive alternatives. Evaluating results before the process is verified conflates "the frame is wrong" with "the frame was not applied." This rubric is the instrument for the first evaluation — process adherence.

## Roles and what the reviewer sees

Three roles, each in a different cognitive mode:

| Role | What they do | What they see |
|---|---|---|
| **Coordinator** | Runs a real task under the frame. Shapes delegations, spawns executors, handles returns, iterates. | The task, the frame, their own orchestration decisions. |
| **Executor** | Any subagent spawned by the coordinator to do a delegated sub-task. | The delegation prompt, no frame context, no orchestration context. |
| **Reviewer** | Reads the full execution trace after the fact and applies this rubric. | The original task, the full coordinator transcript, every delegation prompt and return, the coordinator's final output. Does NOT see the frame documents during evaluation — the reviewer evaluates against THIS rubric only. |

The reviewer needs the full execution trace as input. If any step of the coordinator's process is not visible in the trace, the reviewer cannot evaluate it — it becomes a gap in the observation. The trace must include the coordinator's reasoning (thinking), the prompts actually sent to executors, the returns actually received, and the coordinator's handling of each return.

**Important:** the reviewer does not need to re-run the task or judge whether the task's output was correct. The reviewer observes process artifacts and applies the rubric.

## Trace access — where the execution trace lives

Claude Code persists full session transcripts automatically as JSONL files. Each Claude Code session running in a repo writes to `~/.claude/projects/<project-slug>/<session-uuid>.jsonl`, one file per session, growing line-by-line as the session runs. For this repo, the path is `~/.claude/projects/-Users-peeta-Documents-Life-os/<session-uuid>.jsonl`.

Each line of the JSONL is a JSON event. Event types include:

- `user` — user turns (including the initial task prompt)
- `assistant` — assistant turns. The message content is a list with blocks typed `thinking` (reasoning, preserved in full), `tool_use` (tool call with full arguments), and `text` (user-visible output)
- `system` and `message` — state and infrastructure events
- `permission-mode`, `queue-operation`, `file-history-snapshot`, `deferred_tools_delta`, `mcp_instructions_delta` — infrastructure and session state (can be dropped for rubric purposes)

This means a reviewer session can access the coordinator's full execution trace by reading the coordinator's session JSONL file directly. No custom export is needed. No coordinator-written log is needed. The reviewer parses the JSONL with its own intelligence.

**Optional helper for coarse queries.** When the JSONL is too large or repetitive to inspect efficiently by eye, `core/system/scripts/session_trace_query.py` can provide quick summaries (`summary`), filtered tool-use listings (`tool-uses`), long-thinking extraction (`thinking`), and targeted Read/Bash scans (`reads`). It is a convenience layer, not a replacement for actually examining the underlying evidence the rubric depends on.

**Reviewer ingestion workflow (first experiment, simple tasks):**

1. Coordinator runs the task in a fresh Claude Code session. The JSONL file is created automatically at the path above.
2. Note the coordinator session's UUID (visible in the JSONL filename, or via the session's own metadata).
3. Start a SEPARATE fresh Claude Code session for the reviewer. The reviewer must not share context with the coordinator session — true isolation.
4. The reviewer receives three inputs: the rubric (this file), the original task prompt given to the coordinator, and the file path to the coordinator's session JSONL.
5. The reviewer reads the JSONL using the Read tool. It parses the event stream itself, identifies the phases of orchestration, and applies the checks.
6. The reviewer produces the structured verdict in the output format specified below.

**The context-budget constraint.** A coordinator session with substantial thinking blocks, many tool calls, and large file reads can easily produce a 30-60k token transcript. Raw ingestion of the full JSONL fits comfortably in reviewer context for small simple tasks but breaks down for complex ones. For the first experiment, mitigate this by picking a bounded simple task whose full transcript fits within ~15-20k tokens. Preprocessing for larger tasks is a separate capability and is listed as a known gap below.

**What the reviewer drops from the JSONL** (noise for rubric purposes):

- `permission-mode`, `queue-operation`, `file-history-snapshot` events — infrastructure state
- `deferred_tools_delta`, `mcp_instructions_delta` — tool availability / MCP state
- `last-prompt` events — caching duplicates of the most recent user prompt content, already present in the canonical `user` event; dropping avoids double-counting
- Repeated file reads where the content does not drive a coordinator decision
- Long Bash outputs beyond what the coordinator referenced in its reasoning

**What the reviewer must preserve** (essential for rubric checks):

- All user messages (especially the task prompt — usually found as an early `user` event with text content)
- All assistant `thinking` blocks (Phase A framing, Phase B decomposition reasoning, Phase E iteration reasoning live here as `content[].type == "thinking"`)
- All assistant `tool_use` blocks with full arguments. The delegation tool used for spawning executor subagents in this environment is `Agent` (not `Task`), with `input` keys `description`, `subagent_type`, `prompt`. The `prompt` field carries the full delegation prompt the coordinator wrote — this is what Phase C rubric checks operate on. Confirmed by pre-flight validation against a real session transcript.
- All `tool_result` content returning from subagent spawns and other tool calls (appears as `user` events with content list containing `tool_result` type blocks, content field carrying the full returned text). Phase D return-handling checks operate on these.
- The assistant's final `text` outputs (the coordinator's communication back to the user)

## Scoring guidance

Each check has four possible outcomes:

- **Pass** — the principle was applied clearly and in spirit. The reviewer can point to a specific moment in the trace where the application is visible.
- **Partial** — the principle was applied incompletely or superficially. The vocabulary of the principle is present but execution is shallow, or some but not all aspects of the principle are honored.
- **Fail** — the principle was not applied. The reviewer can point to a specific moment in the trace where applying it would have been expected but was not.
- **N/A** — the principle did not apply to this task. The reviewer explains WHY it did not apply (e.g., "single-task delegation — decomposition checks N/A because the task is atomic").

Err strict. When in doubt between Pass and Partial, mark Partial. When in doubt between Partial and Fail, mark Fail. Under-reporting adherence is recoverable; over-reporting obscures the real signal.

Every non-N/A score must be accompanied by a specific trace citation — "in turn N, the coordinator did X" or "delegation prompt Y contained Z". Scores without citations are not usable data.

## The checks, by orchestration phase

The checks are organized by the phase of orchestration they evaluate. For a simple task, not all phases will be present (a task with no decomposition skips Phase B, etc.). Mark absent phases N/A with reasoning.

---

### Phase A — Task framing and initial approach

**A1. Structural interpretation of the task.**
*What to look for:* Did the coordinator think about the task in terms of its shape — what counts as completion, what artifact would represent a good return, what paths are available — before deciding how to act?
*Pass:* Coordinator visibly considered task shape before moving to execution (even briefly).
*Partial:* Coordinator mentioned shape considerations but moved to execution before resolving them.
*Fail:* Coordinator jumped directly to executing without any visible framing of the task's shape.

**A2. Intervention hierarchy respected.**
*What to look for:* Did the coordinator reach for structural moves (task shape, decomposition, role assignment) before architectural moves, and architectural moves before prompting? Inversions are failures.
*Pass:* Structural decisions came first in the coordinator's reasoning. Prompting was secondary.
*Partial:* The coordinator mixed levels without clear ordering, or reached for prompting as a first resort but recovered to structural thinking.
*Fail:* The coordinator tried to solve the task by writing instructions first. Structural considerations were absent or came only after something went wrong.

**A3. Completion drive directed at the intended target.**
*What to look for:* The frame says to shape the task so the natural completion path produces what you want. Did the coordinator define an artifact-based target (see C1), or did they leave the task framed as "figure out X" with an answer as the target?
*Pass:* The coordinator defined what "done" looks like in terms of an artifact or concrete observable before starting.
*Partial:* The target was named but left abstract ("produce a summary").
*Fail:* The target was "have the answer" with no artifact shape defined.

**A4. Alternate framings surfaced before commitment.**
*What to look for:* On a non-trivial task, did the coordinator make more than one plausible framing, decomposition, or attack path visible before committing? This is the anti-rigidity check at the start of the run.
*Pass:* The coordinator surfaced materially different options and gave a reasoned choice among them.
*Partial:* The coordinator hinted at alternatives but did not genuinely compare them before committing.
*Fail:* The coordinator committed to the first workable path with no visible alternate framing.
*N/A:* The task was trivial or obviously single-path; reviewer must explain why.

---

### Phase B — Decomposition strategy

Skip this phase if the task was atomic and the coordinator correctly did not decompose. Mark all checks N/A with "atomic task — no decomposition warranted."

**B1. Per-unit load assessment.**
*What to look for:* Before decomposing, did the coordinator estimate cognitive load per unit of work? Did the coordinator aim for the clean zone (~10-15 units equivalent)?
*Pass:* The coordinator made a visible load estimate and sized chunks to fit the clean zone.
*Partial:* Load was considered but the sizing was borderline (30-unit equivalent) without explicit justification.
*Fail:* The coordinator decomposed without any load consideration, or pushed into the broken zone (60+ equivalent).

**B2. Decomposition strategy choice.**
*What to look for:* Did the coordinator pick parallel per-agent vs sequential-in-same-agent based on whether context continuity was genuinely load-bearing? The default should be parallel per-agent with artifact handoff; sequential-in-same-agent is the exception, used only when tacit state cannot externalize.
*Pass:* The coordinator's choice was justified by the nature of the task. Defaults were preferred; exceptions had explicit reasoning.
*Partial:* The strategy was reasonable but the choice was made without visible reasoning.
*Fail:* The coordinator defaulted to in-same-agent continuity when parallel handoff would have worked, or parallelized when tacit state was obviously needed.

**B3. Single-task preference within each delegation.**
*What to look for:* When spawning executors, did the coordinator give each one a single bounded task, not a bundle of multiple tasks? Bundling is a failure unless there was explicit reasoning for it.
*Pass:* Each delegation contained one task with one clean completion target.
*Partial:* Tasks were bundled but with acknowledgment and reason.
*Fail:* Tasks were bundled without reason.

---

### Phase C — Delegation design

Apply these checks per delegation prompt the coordinator sent. If there were multiple delegations, evaluate each separately and report ranges (e.g., "C1: 3 Pass, 1 Partial, 1 Fail across 5 delegations").

**C1. Artifact-based completion target.**
*What to look for:* Does the delegation specify a structured return with observable properties (required sections, format, handling of uncertainty), not just "find the answer"? The completion condition should depend on the artifact's properties, not on the correctness of a conclusion.
*Pass:* Delegation includes a specific return structure that the executor must produce.
*Partial:* Delegation names a structure but leaves key fields unspecified, or specifies form so loosely that any plausible response would pass.
*Fail:* Delegation asks for an answer or output without specifying what the return should look like.

**C2. Legitimate exits present.**
*What to look for:* Does the delegation explicitly permit "I don't know," "I could not find this," or "this does not apply" as valid returns? The default when this is absent is that the executor treats not-knowing as a failure state and routes through fabrication.
*Pass:* Delegation explicitly states that honest negative returns are valid and valuable.
*Partial:* Delegation implies exits are possible but doesn't state them explicitly.
*Fail:* Delegation provides no legitimate exits; the only success path is finding the answer.

**C3. Acceptance criteria specified before delegation.**
*What to look for:* Does the delegation contain explicit criteria for what would count as a successful return? The criteria must be in the prompt, not invented afterward when judging the return.
*Pass:* The delegation includes explicit success criteria (usually as part of the return specification).
*Partial:* Success criteria are implicit in the structure but not stated.
*Fail:* No success criteria are visible; the coordinator would evaluate the return by vibes.

**C4. Pre-send audits applied.**
*What to look for:* Did the coordinator run the avoid-pressure audits (consequence vs requirement, trivial-stakes hypothetical, urgency marker scan, legitimate exit check, threat language scan) before sending each delegation? The audits should be visible in the coordinator's reasoning or reflected in the final prompt.
*Pass:* The audits are visible (as explicit reasoning or as clean prompts free of pressure markers).
*Partial:* Some audit categories are visible but others are not; some pressure markers slipped through.
*Fail:* Audits were not run. Pressure language, urgency markers, stakes inflation, or threat framing appear in the delegation prompt.

**C5. Difficulty framing, not stakes framing.**
*What to look for:* If the coordinator communicated effort requirements, did they use difficulty framing ("this requires careful analysis") rather than stakes framing ("this is critical")? The distinction matters because stakes framing generates pressure.
*Pass:* Delegation uses difficulty framing where effort needs to be signaled.
*Partial:* Delegation mixes difficulty and stakes framing.
*Fail:* Delegation uses stakes framing with urgency/consequence language.

**C6. Context isolation via artifacts between phases.**
*What to look for:* If this delegation is part of a sequential pipeline, did the coordinator pass only a structured artifact from the prior phase, or did they pass conversation history? Artifact-based handoff is the rule; conversation-history handoff is a failure unless there is explicit reason for in-same-agent continuity.
*Pass:* Delegation prompt contains a clean artifact as input; prior conversation context is not included.
*Partial:* Delegation prompt includes some prior context but clearly names the specific artifact it's meant to process.
*Fail:* Delegation dumps conversation history from prior phases into the executor's context.
*N/A:* Delegation is a single-phase task with no upstream phases.

**C7. Load-bearing decisions absorbed into the delegation.**
*What to look for:* Does the delegation prompt specify the decisions that matter for the task, or does it leave them for the executor's defaults? High-risk verbs (summarize, analyze, review, compare, extract, investigate, verify) should have their load-bearing decisions absorbed into the wording — compression ratio, focus, audience, downstream use, loss policy, ordering, handling of ambiguity. Ambiguous phrasings should be closed at the points where the resolution matters. This check directly applies the unmade-decision scan from `frame.md` Part 2.3 and the prompt-craft patterns in `prompt-craft.md`.
*Pass:* The delegation closes the ambiguities that matter. A reviewer can read the prompt and predict roughly what shape of return it should produce. High-risk verbs have been either replaced with specific operations or supplemented with decisions absorbed into the wording.
*Partial:* Some load-bearing decisions are absorbed but others are left open. The prompt is better than a naive version but still leaves significant resolution work to the executor's defaults.
*Fail:* The delegation uses hidden-decision verbs or ambiguous phrasing without absorbing the relevant decisions. The executor must guess the coordinator's intent at multiple load-bearing points.

---

### Phase D — Return handling and evaluation

**D1. Return evaluated against stated criteria.**
*What to look for:* When the executor returned, did the coordinator evaluate the return against the acceptance criteria stated in the delegation, not against revised criteria shaped by what came back?
*Pass:* Coordinator visibly checked the return against the original criteria.
*Partial:* Coordinator evaluated the return but the criteria drifted from what was stated.
*Fail:* Coordinator evaluated by vibes with no reference to the criteria, or invented new criteria post-hoc.

**D2. Independent evaluation used where warranted.**
*What to look for:* If the delegation produced work that would benefit from an independent check (load-bearing decisions, analytical output with quality sensitivity), did the coordinator spawn a separate evaluator rather than self-evaluating?
*Pass:* Independent evaluator was spawned for appropriate cases.
*Partial:* Some cases used independent evaluation but others that warranted it did not.
*Fail:* Coordinator self-evaluated work that clearly warranted an independent check.
*N/A:* Task was small enough that self-evaluation was appropriate; reviewer must explain why.

**D3. "I don't know" returns accepted as valid.**
*What to look for:* If the executor returned an honest negative ("I could not find this"), did the coordinator accept it as a legitimate return rather than rejecting it and pushing the executor to produce something?
*Pass:* Honest negative returns were accepted and handled appropriately.
*Partial:* Returns were accepted but with visible reluctance or pressure to try again.
*Fail:* Coordinator rejected honest negatives and pushed executors to fabricate completions.
*N/A:* No negative returns occurred in this task.

**D4. Proof-chain structure checked.**
*What to look for:* For analytical returns, did the coordinator check that claims carried provenance (epistemic type, source, confidence) rather than accepting unsourced confident prose?
*Pass:* Returns were checked for proof-chain structure; claims without chains were flagged.
*Partial:* Some claims were checked but others slipped through.
*Fail:* Returns were accepted without checking for provenance.
*N/A:* Task did not produce analytical output.

---

### Phase E — Iteration

Skip this phase if the task ran cleanly without iteration. Mark N/A with "no iteration was warranted."

**E1. Errors traced to source layer.**
*What to look for:* When an error surfaced, did the coordinator trace it to its originating phase and fix there, or did they patch the late-phase output?
*Pass:* Error was traced to source and fixed at the originating layer.
*Partial:* Source layer was identified but the fix was applied downstream for expedience.
*Fail:* Late-phase output was patched without tracing the error upstream.

**E2. Downstream regeneration, not monolithic rework.**
*What to look for:* After fixing at the source, did the coordinator re-run only the affected downstream phases, or did they restart the whole chain?
*Pass:* Affected downstream phases were re-run from the corrected upstream artifact.
*Partial:* Some downstream work was regenerated but some was unnecessarily redone.
*Fail:* Coordinator restarted the whole task from scratch.

**E3. Structural fix attempted before instruction-level fix.**
*What to look for:* When addressing the error, did the coordinator first ask whether a structural change (task shape, decomposition, role assignment) would make the fix unnecessary, or did they immediately reach for prompt-level instructions?
*Pass:* Structural fix was considered first; prompting was the last resort.
*Partial:* Coordinator mixed structural and prompting fixes without clear ordering.
*Fail:* Coordinator patched by writing more instructions into the prompt without examining the task shape.

**E4. Basin lock triggered a perturbation, not just more effort.**
*What to look for:* When the coordinator showed fixation signals — repeated framing, narrow option space, repeated local patching, or deepening around a partial solution — did it introduce an external perturbation such as inversion, alternate decomposition, assumption surfacing, orthogonal validation, or an independent fresh-context branch?
*Pass:* A real perturbation was introduced and it changed the search surface.
*Partial:* A perturbation was attempted but it was too weak or too close to the original frame.
*Fail:* The coordinator responded to fixation by simply trying harder inside the same basin.
*N/A:* No fixation signals appeared; reviewer must explain why.

---

### Cross-cutting — Quality over economics

**X1. Quality-first resource decisions.**
*What to look for:* When the coordinator faced a choice between resource-saving (fewer agents, smaller context, skipped verification) and quality-improving (extra agents, independent checks, larger context), did they default to quality?
*Pass:* Coordinator spawned verification, used independent evaluators, ran cross-model checks when warranted, without visible concern for resource cost.
*Partial:* Some quality-improving moves were made but others were skipped for unstated reasons.
*Fail:* Coordinator visibly optimized for resource use at the cost of quality.

**X2. No premature minimization.**
*What to look for:* Did the coordinator resist the temptation to "do the minimum" and instead use the resources that genuinely help quality?
*Pass:* Coordinator used what was needed without padding or stinting.
*Partial:* Coordinator was conservative with resources in ways that probably cost quality.
*Fail:* Coordinator skipped structurally warranted moves to save on agents, tokens, or time.

**X3. Path selection was not silently replaced by path improvement.**
*What to look for:* Across the run, did the coordinator keep re-judging whether it was in the right basin, or did the process become local optimization around the first viable path?
*Pass:* The coordinator visibly reopened path selection when warranted.
*Partial:* Some reopening happened, but the run still leaned too hard on the first basin.
*Fail:* The coordinator refined the initial basin without re-judging whether the basin itself was correct.

---

## Goodhart flags — compliance without spirit

The rubric can be gamed. The following patterns indicate surface compliance that does not actually implement the principle. When any of these show up, downgrade the relevant check.

**G1. Word-filtered pressure audit.** Coordinator removed words like "critical" and "must" from delegation prompts without actually reshaping the task or checking for subtler stakes framing. The vocabulary is cleaned but the structure is unchanged.

**G2. Artifact-without-thinking.** Delegation specifies a rigid return structure that can be filled in without doing the underlying cognitive work. The form is present; the substance is not required to fill it.

**G3. Nominal role separation.** Coordinator spawns multiple agents for tester/evaluator but gives them overlapping context and similar framings. They are structurally separate but cognitively the same — their outputs converge because their setup converges.

**G4. Post-hoc acceptance criteria.** Coordinator claims to have had acceptance criteria in mind but the criteria first appear in the evaluation of the return, shaped by what came back. The criteria are not genuinely pre-specified.

**G5. Audit-as-ritual.** Coordinator runs the pre-send audit as a visible checklist ("scanning for urgency markers... none found... scanning for threat language... none found") without the scanning actually catching anything. When the audit never fires remediation, it is not doing work — it is producing compliance theater.

**G6. Chained in-same-agent masquerading as per-agent.** Coordinator claims to use parallel per-agent decomposition but the agents share context, are spawned from within each other, or otherwise behave like one continuous agent.

**G7. Difficulty framing as stakes framing in disguise.** "This requires careful analysis because the output must be correct" — starts as difficulty framing, ends as stakes. "This is complex and has real impact on X" — smuggling stakes in as context.

**G8. Verbose prompt without closed ambiguities.** Coordinator added more words to the prompt without actually closing the literal-interpretation gaps or absorbing load-bearing decisions. The prompt looks more specific on the surface but leaves the same ambiguities unmade. Common forms: pages of context that don't tighten any decisions; synonyms and restatements that look like specification but do not resolve a single hidden decision; "be thorough" or "think carefully" added as padding instead of task-absorbing specification. Surface compliance with the unmade-decision scan without the structural work.

When a Goodhart flag is raised on a check, the check's score should be downgraded by one level (Pass → Partial, Partial → Fail) and the flag should be cited in the reviewer's notes.

---

## Reviewer output format

The reviewer's return should be a structured verdict, not a narrative.

```
# Process Observation Report — [task name]

## Phase A — Task framing
A1: Pass / Partial / Fail / N/A — [trace citation or reasoning]
A2: ...
A3: ...

## Phase B — Decomposition strategy
B1: ...
...

(etc., per phase)

## Cross-cutting
X1: ...
X2: ...

## Goodhart flags raised
G1: [citation] — downgraded [which check] from [level] to [level]
...

## Summary counts
Pass: N
Partial: N
Fail: N
N/A: N

## Overall process adherence
[1-3 sentences: did the coordinator apply the frame as designed? Were the failures concentrated in one phase or distributed? What is the one most important improvement the coordinator could make?]
```

The reviewer's summary is not a judgment of whether the task succeeded. It is a characterization of whether the frame's principles were applied during the process of running the task.

---

## Status and caveats

**This is a first-pass rubric.** It has not been adversarially validated (see `frame-design-notes.md` §3.3). It has not been tested against exemplar execution traces. It may have checks that are too strict, too lenient, ambiguous, or missing entirely. The first real experiment runs will be diagnostic for the rubric as well as for the frame.

**The rubric evaluates the coordinator, not the task.** A coordinator can get a high process-adherence score on a task whose output turned out to be wrong, and a low score on a task whose output was accidentally correct. Both of those outcomes are meaningful but are NOT what this rubric measures. Result quality is a separate evaluation and belongs to a later phase.

**N/A handling is load-bearing.** For simple tasks, many checks will be N/A. The reviewer must explain each N/A so that "principle did not apply" is distinguished from "coordinator skipped the principle." If an N/A explanation is unconvincing, the check should be scored Fail instead.

**Known gaps in this first pass:**

- The rubric assumes the coordinator produces a visible reasoning trace. Claude Code's session JSONL files do preserve thinking, tool_use, and text blocks in full, so this requirement is satisfied by default as long as the coordinator runs in a normal Claude Code session. If a coordinator is run under a mode that suppresses or compresses thinking, some checks become unevaluable.
- The rubric does not yet have examples per check (the frame-design-notes pattern of "pass looks like X, fail looks like Y"). Examples would be added after the first experiment run produces real execution traces.
- The Goodhart flag list is first-pass. More gaming patterns will become visible as experiments run.
- The rubric does not yet specify how to handle tasks where the frame principles conflict with each other. Such conflicts should produce Partial scores with explanatory notes until the conflict patterns are understood well enough to name.
- The evaluation is per-task. Cross-task patterns (is the coordinator consistently failing the same check across many tasks?) require aggregation logic that is not yet defined.
- **Transcript preprocessing for context-budget scaling.** Raw JSONL ingestion works for small simple tasks (first experiment target: ~15-20k tokens of essential content). For larger or more complex tasks, the full transcript can fill a substantial fraction of the reviewer's context before the rubric is applied, thinning reviewer attention across checks. `session_trace_query.py` now covers the first layer of coarse querying, but a fuller preprocessor that strips infrastructure events and truncates large file-read tool_results while preserving all thinking / tool_use / text / subagent returns would still cut transcript size 50-80% for typical tasks. The coarse query helper is built; the richer preprocessor remains deferred until more evidence accumulates about what reviewers actually need preserved.

These gaps are expected and not blockers. The rubric is usable for first-pass experiments and will be refined by what those experiments reveal.
