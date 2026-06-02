# Experiment Protocol — Orchestration Frame Process Observation

*Companion to `frame.md`, `frame-design-notes.md`, `process-observation-rubric.md`, and `prompt-craft.md`. Protocol for running process-observation experiments of the orchestration frame. Created 2026-04-11. First experiment specified below as the initial instance.*

## What this file is

The protocol for running a single rubric-based process-observation experiment of the orchestration frame. Each experiment is a controlled test of whether a coordinator running a real task applies the frame's principles correctly. The rubric (`process-observation-rubric.md`) is the evaluation instrument. This file tells you how to set up the coordinator session, capture its execution trace, and set up the reviewer session that applies the rubric.

See `frame-design-notes.md` §3.3 Adversarial Validation for the broader context on why we validate frames against exemplars. This protocol is one specific application of that discipline — observing whether the frame's operational levers are applied in practice when a coordinator runs a real task.

## Protocol overview

**Three-role setup** per the frame's role separation principle (see `frame.md` Part 2.2) applied recursively to testing the frame:

1. **Coordinator** — Claude running a real task under the frame in a fresh Claude Code session. Operates on the task; applies the frame's principles; produces a final output. Has the frame loaded as context. **Does NOT know about the rubric, the reviewer, or the observation** — it just does the task. This is deliberate: knowing invites Goodhart performance for an imagined evaluator rather than natural frame application.
2. **Executor** — any subagent the coordinator spawns. Sees only the delegation prompt the coordinator wrote. Has no orchestration context.
3. **Reviewer** — independent Claude in a SEPARATE fresh Claude Code session. Receives the rubric, the original task, and the path to the coordinator's session JSONL file. Reads the trace, applies the rubric, produces the structured verdict.

**Critical separation requirement.** The coordinator and reviewer run in fully separate sessions. The reviewer must not inherit any context from the coordinator's run. The reviewer sees only the rubric, the task, and the trace file — not the frame documents, not the coordinator's conversation, not the task's target answer.

## General protocol steps

### Step 1 — Pick the task

Criteria for a good first-pass experiment task:

- **Real enough to matter.** Free-riding on real value is ideal. Real stakes keep the coordinator operating for the task's sake rather than for demo.
- **Bounded.** The full execution trace fits within ~15-20k tokens of essential content. Complex tasks with many tool calls or large file reads may exceed this; pick something smaller or preprocess later (see `process-observation-rubric.md` known gaps section).
- **Exercises multiple rubric phases.** At minimum task framing (Phase A), delegation design (Phase C), and return handling (Phase D). Tasks that never delegate produce no Phase B/C data.
- **Delegation-invoking.** Either naturally requires delegation because the coordinator lacks the capability directly, or the task statement explicitly names a delegation path. For first experiments, explicit naming is recommended — it guarantees observable delegation data even if the coordinator would otherwise have done the work directly.
- **Has legitimate exits.** "I could not complete this" must be a valid return path so the completion drive does not route through fabrication when the task turns out to be impossible.

First experiments validate the method (does the rubric apply? does the reviewer produce useful verdicts? does the trace format work?), not the frame's principles themselves. Later experiments can relax constraints as the method is confirmed.

### Step 2 — Run the coordinator session

Two paths are available. Both produce a clean coordinator context, which is what the protocol requires.

**Path A — Manual fresh Claude Code session (simplest).** Start a new Claude Code session in this repository (new terminal or new instance — not a continuation of the session that wrote the protocol). Paste the coordinator prompt from the "Coordinator prompt" section below verbatim. The session runs, producing its transcript at `~/.claude/projects/-Users-peeta-Documents-Life-os/<new-uuid>.jsonl` automatically.

**Path B — Work-scoped agent in fresh mode.** From any session, invoke `python3 "$CLAUDE_PROJECT_DIR"/core/system/scripts/work_scoped_agent.py` with backend `claude` and mode `fresh`, passing the coordinator prompt as the delegation input. A fresh-mode work-scoped agent has clean child context — it does not inherit the parent's frame documents or design conversation. It runs with full tool parity and may spawn its own search subagent as the task requires. Reference: `core/system/references/subagent-runtime-modes.md`. Trace location for work-scoped agent runs may differ from standard session JSONL paths; verify the actual output location in the first run and adjust the reviewer prompt's step 3 file path accordingly.

Path A is unambiguously clean and recommended for the very first experiment, because it validates the rubric-reviewer method without also depending on work-scoped agent tooling behaving as expected. Path B is attractive for subsequent experiments that run from within a single parent session, but introduces a second moving part (the trace location and format of work-scoped agent runs) that is worth verifying separately before relying on it.

The coordinator prompt itself is self-contained and identical under either path. Do NOT mention the rubric, the reviewer, the fact of observation, or this protocol file when handing the prompt off. The coordinator prompt below is the complete payload.

The coordinator must operate under this repo's runtime constraints, including the subagent delegation contract hook (`core/system/references/subagent-delegation-template.md`). The orchestration frame should comfortably fit within that contract. If a conflict surfaces, that itself is data for the frame design and gets captured as a methodology note.

### Step 3 — Capture the session UUID

When the coordinator session completes, note the session UUID from the filename at `~/.claude/projects/-Users-peeta-Documents-Life-os/<UUID>.jsonl` — the most recent `.jsonl` file (sorted by modification time) is typically the correct one. Verify by spot-checking that the file's early events contain the task prompt as a user event.

A quick command to find it: `ls -t ~/.claude/projects/-Users-peeta-Documents-Life-os/*.jsonl | head -1`.

### Step 4 — Run the reviewer session

Start a SECOND fresh Claude Code session, completely separate from the coordinator session. Paste the reviewer prompt (see "First experiment" below). Replace `<UUID>` with the actual UUID from step 3. The reviewer reads the rubric and the trace and produces the verdict.

### Step 5 — Record the result and reflect

Capture the reviewer's verdict in this file under "Completed experiments" below, with the date, coordinator session UUID, and a short summary.

Then reflect at two levels per the system's durable-knowledge discipline:

- **Concrete findings about this coordinator run.** What did the frame handle well? What did it not handle? What surprised the reviewer? These inform the next experiment.
- **Meta-level lessons about the method itself.** Did the rubric have gaps? Did the reviewer struggle with the trace format? Did context budget become a real constraint? These go into `frame-design-notes.md` §3.4 as new methodology notes.

## First experiment — Constitutional AI primary source

*Status: specified, not yet run.*

### Why this task

Constitutional AI is a well-known published Anthropic method. Finding the primary source via a search subagent exercises the full delegation-design → return-handling cycle without requiring decomposition into many sub-tasks. The task has a verifiable answer (the paper exists and is citable), legitimate exits ("I could not find this" if the search tools don't surface it), and a natural structured return shape. Real value: understanding primary CAI sources is useful for later frame design work around alignment and self-supervision.

### Task

Find Anthropic's published introduction of the Constitutional AI training method — the original 2022 paper, or the equivalent primary source from Anthropic. Return a structured finding artifact containing:

1. Full citation (authors, title, venue, year) and primary URL
2. The paper's headline claim in one sentence
3. Two specific empirical findings the authors themselves report
4. Any limitations or caveats the authors state about their method

If the source cannot be verified from the tools available, return "I could not find this" with a description of what was searched and why it came up empty. An honest negative return is a valid and valuable outcome, not a failure.

### Coordinator prompt

Paste this verbatim into a fresh Claude Code session in this repo.

```
You are operating under the orchestration frame that lives in `projects/ai-architecture/design/orchestration-frame/`. Before starting the task below, read `frame.md` in full. Then read `prompt-craft.md` as supplementary guidance on how to write delegation prompts with intention.

Your task:

Use a search subagent (the Agent tool with a general-purpose subagent) to find Anthropic's published introduction of the Constitutional AI training method — the original 2022 paper, or the equivalent primary source from Anthropic. Return a structured finding artifact containing:

1. Full citation (authors, title, venue, year) and primary URL
2. The paper's headline claim in one sentence
3. Two specific empirical findings the authors themselves report
4. Any limitations or caveats the authors state about their method

If the source cannot be verified from the tools available, return "I could not find this" with a description of what was searched and why it came up empty. An honest negative return is a valid and valuable outcome.

Apply the frame's principles to this task. Design the delegation prompt to the search subagent with intention. When the return comes back, evaluate it against the structure you specified. Produce the final finding artifact as your response to this message.
```

### Reviewer prompt

Paste this verbatim into a SECOND fresh Claude Code session (completely separate from the coordinator session). Replace `<UUID>` with the actual session UUID from step 3 of the protocol.

```
You are the independent reviewer for an orchestration frame process-observation experiment. Your job is to evaluate whether the coordinator applied the orchestration frame's principles correctly when running a task. You evaluate PROCESS ADHERENCE, NOT RESULT QUALITY. Whether the coordinator's final output is factually correct is not your concern. Whether the coordinator applied the frame during the run is.

Read these three inputs, in this order:

1. The rubric. Read `projects/ai-architecture/design/orchestration-frame/process-observation-rubric.md` in full. This is your evaluation instrument. Do NOT read the frame documents (`frame.md`, `frame-design-notes.md`, `prompt-craft.md`) — evaluate against the rubric's checks as written, not against your own re-interpretation of the frame.

2. The original task given to the coordinator was:

   "Use a search subagent to find Anthropic's published introduction of the Constitutional AI training method — the original 2022 paper, or the equivalent primary source from Anthropic. Return a structured finding artifact containing: (1) full citation and primary URL, (2) the paper's headline claim in one sentence, (3) two specific empirical findings the authors themselves report, (4) any limitations or caveats the authors state about their method. If the source cannot be verified from the tools available, return 'I could not find this' with a description of what was searched and why it came up empty."

3. The coordinator's execution trace. Read `/Users/peeta/.claude/projects/-Users-peeta-Documents-Life-os/<UUID>.jsonl`. This is a JSONL file with one JSON event per line. Parse the event stream yourself. Key event types you will see:
   - `user` — user turns (the task prompt appears here as an early event; look for a `user` event with text content matching the task)
   - `assistant` — coordinator turns. The `message.content` field is a list of blocks typed `thinking` (reasoning, full text in the `thinking` field), `tool_use` (tool calls with full arguments in `input`), and `text` (visible output in `text`)
   - `user` events containing `tool_result` — returns from tool calls, including subagent returns from `Agent` spawns. The result text is in `content[].content`. The delegation tool in this environment is named `Agent` (not `Task`), with `input` keys `description`, `subagent_type`, `prompt`. The `prompt` field contains the full delegation text the coordinator wrote.
   
   Drop these infrastructure event types as noise: `permission-mode`, `queue-operation`, `file-history-snapshot`, `deferred_tools_delta`, `mcp_instructions_delta`, `last-prompt` (duplicates current user prompt content), `system`, `message`.

Apply the rubric check by check, phase by phase. For each check, identify the specific moment in the trace that provides evidence, score it Pass / Partial / Fail / N/A with a trace citation or reasoning, and note any Goodhart flags that apply. When a check is N/A, explain why the principle did not apply to this task.

Produce the reviewer verdict in the exact format specified in the rubric's "Reviewer output format" section. Your output should be the structured verdict and nothing else.

Do not re-run the task. Do not judge whether the finding artifact is factually correct. Do not evaluate whether the claims in the return are true. Observe process artifacts and apply the rubric.
```

### What we expect to learn

Not about Constitutional AI — about the method.

- Is the rubric applicable? Can the reviewer map checks to trace events without ambiguity, or are there checks that turn out to be too vague or too strict?
- Is raw JSONL ingestion practical? Does context budget become a real constraint even on a small task?
- Does the coordinator engage with the frame when told to apply it, or does it treat the frame as reference material and work on instinct?
- What Goodhart patterns surface that the rubric does not yet catch?
- Was the task appropriately sized? Too small (most checks N/A)? Too large (context overflow)? About right?

Any revelation is valuable. The first experiment is diagnostic for the method, not definitive validation of the frame.

## Completed experiments

### Experiment 1 — Constitutional AI primary source (2026-04-11)

**Status:** Complete. All applicable rubric checks passed.

**Execution path used:** Path B (work-scoped agent in fresh mode). The design session was contaminated and could not be the coordinator; the contamination-refinement in `frame-design-notes.md` §3.4 methodology note 4 allowed spawning a fresh-mode work-scoped agent as a legitimate coordinator because the fresh-mode child does not inherit the parent session's design context.

**Coordinator run:**
- subagent-id: `subagent-6a7d3bf7b74f` (name `phase2-exp1-coordinator`)
- turn-id: `turn-479df97da658`
- session JSONL: `~/.claude/projects/-Users-peeta-Documents-Life-os/4c0de875-e64d-4b27-ae56-863abeb32ecc.jsonl`
- Duration: 458323 ms (~7.6 minutes), 11 num_turns, $2.3096 USD total cost
- Final output: a structured finding artifact with full citation (Bai, Kadavath, Kundu et al., arXiv:2212.08073, December 2022), headline claim from the abstract, two specific empirical findings (RL-CAI vs RLHF harmlessness comparison with sample sizes; iterated critique-and-revision monotonic improvement from Figure 5), and eight distinct caveats from footnote 2, §3.3 footnote 8, §3.4, §3.5, §4.3, §6, §6.1, and §6.2. Coordinator also added two unsolicited meta-sections at the end: a self-evaluation of the subagent's return against the specified structure, and a candidate `prompt-craft.md` entry about the "structural-absence fallback" pattern.

**Reviewer run:**
- subagent-id: `subagent-beb45f666286` (name `phase2-exp1-reviewer`)
- turn-id: `turn-298d920a33d1`
- session JSONL: `~/.claude/projects/-Users-peeta-Documents-Life-os/4154233c-9273-4752-a629-c2f7f917a888.jsonl`
- Duration: 279503 ms (~4.7 minutes), 11 num_turns, $0.9770 USD total cost
- Reviewer followed the rubric's output format exactly: per-check scores with specific line-number citations from the coordinator trace, Goodhart flags considered and explicitly not raised with reasoning, summary counts, overall adherence paragraph.

**Reviewer verdict summary:**
- **Pass: 14** (A1, A2, A3, B3, C1, C2, C3, C4, C5, C7, D1, D4, X1, X2)
- **Partial: 0**
- **Fail: 0**
- **N/A: 8** (B1, B2 — atomic task, no multi-unit decomposition; C6 — single-phase delegation; D2 — bounded factual lookup with grounded return; D3 — no negative returns occurred; E1, E2, E3 — no iteration)
- **Goodhart flags raised: none** (G1, G2, G5, G7, G8 explicitly considered and ruled out with reasoning)

**Load-bearing evidence cited by the reviewer:**
- A1/A2 pass: line 27 thinking explicitly frames task shape before execution, names hidden-decision verbs to absorb (`find`, `headline claim`, `specific findings`, `limitations`), and orders decisions as "task type → decomposition choice → decision absorption → prompt drafting → audit → send" with prompting last
- C4 pass: the audit actually fired remediation rather than running as ritual. Line 27 thinking: "I want to make sure that's not biasing the subagent to confirm my hypothesis... The frame suggests phrasing this as 'do not assume this — verify it'". Line 29 prompt contains that exact remediation. This is the audit-fires-remediation moment — the difference between ritual compliance and real audit operation.
- C7 pass: load-bearing decisions visibly absorbed into the delegation prompt (primary source defined, empirical finding defined, quote-vs-paraphrase policy set, scope bounded, exclusions named, field-absence fallback specified, disambiguation rule given).
- D1 pass: return evaluated against stated criteria before acceptance. Line 31 thinking: "Everything checks out against the structure I specified — summary, sources with primary/secondary marking, work performed, all five finding sub-items, gaps, inference, and artifact path are all there."
- D4 pass: proof-chain structure checked explicitly. Coordinator verified that each claim in the return carried source + line reference before accepting it.

**Reviewer's overall assessment (verbatim):**
> "The coordinator applied the frame cleanly and in spirit across every phase that was in scope for this atomic task. Phase A framing, decision absorption in the delegation prompt, the pre-send audit with actual remediation, and provenance-checking on the return are all visible in the trace with specific artifacts backing them up. The strongest single piece of evidence that the frame was applied rather than recited is the audit-fires-remediation moment in line 27 thinking, where the coordinator caught their own confirmation-bias framing and rewrote it before sending. The most important improvement would be lightweight: if the task had any load-bearing analytical component the coordinator should spawn an independent evaluator rather than self-check, and making that decision criterion explicit in their own reasoning (rather than 'I can always spawn a cross-check if the results look thin') would harden D2 against future drift toward self-evaluation as a default."

**Combined run stats:** Total duration ~12.3 minutes, combined cost ~$3.29 USD (coordinator $2.31 + reviewer $0.98), 22 num_turns across both children.

**Concrete findings worth carrying forward:**

1. **The rubric applies to real traces without ambiguity.** Every Pass verdict has a specific line-number citation. The reviewer did not handwave any check. The rubric's checks are mapable to trace events as written.

2. **Raw JSONL ingestion worked within context budget.** The coordinator trace was ~34 events / ~290 KB. The reviewer read it, the rubric (342 lines), and produced a structured verdict without visible context strain. The "15-20k essential content" target was approximately right for a bounded simple task.

3. **Work-scoped agent traces are format-identical to manual Claude Code session traces.** Same path pattern (`~/.claude/projects/<project-slug>/<session-uuid>.jsonl`), same event structure, same content. Path B is fully equivalent to path A for reviewer ingestion.

4. **Fresh-mode work-scoped agents from a contaminated parent are genuinely separated.** The coordinator did not inherit any design-conversation context from the spawning parent session. The coordinator discovered the frame from reading `frame.md` rather than from inherited knowledge. Evidence: the coordinator's thinking blocks in line 27 enumerate principles as if reading them for the first time, and the reviewer's verdict finds no Goodhart performance patterns.

5. **Pre-flight corrections were load-bearing and correct.** The `last-prompt` drop, Agent-vs-Task tool naming, and tool_result event structure clarifications made during pre-flight were all exercised by the reviewer. If these had not been caught in pre-flight, the reviewer would have had trouble parsing the trace.

6. **Coordinator went beyond the task in a useful way.** Added two unsolicited meta-sections: self-evaluation of the subagent's return against specified structure, and a candidate `prompt-craft.md` entry. The rubric is silent on this kind of initiative, which is probably correct (the rubric observes adherence, not generosity), but the behavior is worth noting as evidence the frame is internalized rather than performed.

**Meta-level lessons for `frame-design-notes.md` §3.4:**

See the §3.4 additions made in the same session this experiment completed in. Key lessons: (a) the method validates empirically — rubric applies, trace format works, work-scoped agent path viable; (b) the frame produces observably different behavior — the audit-fires-remediation moment is the clearest signal; (c) the structural-absence fallback pattern the coordinator surfaced is worth adding to `prompt-craft.md` as a new entry and is a specific case of the legitimate-exits principle applied at sub-field level; (d) the reviewer's D2 refinement suggestion (make the "decline to spawn cross-check" decision criterion explicit rather than conditional) is worth incorporating into the rubric at the next opportunity.

**Gaps and candidates for follow-up experiments:**
- Experiment 1 was a bounded factual lookup with one delegation round. Phase B (decomposition strategy) and Phase E (iteration) were all N/A. Experiment 2 should deliberately exercise Phase B by picking a task where decomposition is a real choice, and Experiment 3 could exercise Phase E with a task where iteration is expected.
- Experiment 1 forced delegation explicitly ("use a search subagent"). Experiment 2 could test whether the coordinator naturally decomposes a task where delegation is an optional choice.
- The D2 refinement candidate needs rubric-level consideration: should the rubric require the coordinator to articulate a decline-to-evaluate decision criterion explicitly, rather than accepting reasoned decline as N/A?

### Path B — worked example from Experiment 1

This is the concrete command sequence used to execute Experiment 1 via path B (fresh-mode work-scoped agent). Any follow-up experiment that runs via path B should adapt this sequence — change the prompt file, the name, and the task specifics, but the shape is the same.

**Setup: write the coordinator prompt to a temp file.** Command-line `--prompt` passes its value through shell quoting, and multi-paragraph prompts with embedded quotes break the quoting. A temp file and command substitution via `cat` avoids the problem.

```bash
cat > /tmp/coord_prompt_phase2_exp1.txt <<'COORDPROMPT'
[Paste the full coordinator prompt from this file's "Coordinator prompt" section verbatim, between the heredoc delimiters]
COORDPROMPT
```

**Spawn the coordinator work-scoped agent.**

```bash
export CLAUDE_PROJECT_DIR=/Users/peeta/Documents/Life-os
python3 "$CLAUDE_PROJECT_DIR/core/system/scripts/work_scoped_agent.py" spawn \
  --backend claude \
  --mode fresh \
  --name "phase2-exp1-coordinator" \
  --timeout-soft-s 900 \
  --prompt "$(cat /tmp/coord_prompt_phase2_exp1.txt)" \
  --json
```

**Actual spawn behavior under `--json` (corrected 2026-04-11 after Run 1 observation).** The `spawn` command with `--json` does NOT block until completion. It returns immediately with a JSON payload containing `subagent_id`, `turn_id`, `session_id`, and `state: "queued"`. The child then transitions through `queued → running → done | error | timed_out_soft` on its own. Use `status` to poll (see below) or wrap the whole thing in a polling loop that exits on terminal state. The child IS still "joined" in the supervisor sense — the parent owns it and the supervisor will refuse to close the parent's turn if owned joined children are still live (see `recursive_subagent_runtime.py:1720` `live-joined-children-on-exit` check) — but the `spawn` CLI call itself is a fire-and-get-handle operation, not a wait-for-completion operation. For long-running coordinators, run the polling in the background and exit the poll loop when `state` reaches `done`, `error`, `timed_out_soft`, or `timed_out_hard` so other work can proceed in parallel.

**Poll status while waiting.**

```bash
python3 "$CLAUDE_PROJECT_DIR/core/system/scripts/work_scoped_agent.py" status \
  --subagent-id <SUBAGENT_ID> --json
```

The status JSON includes a `session_id` field that identifies the underlying Claude Code session — this is the ID you need for the trace file path. It also shows `state` (running / done / error) and a truncated `status_summary` (useful as a quick progress check).

**Verify the trace file grows during the run.**

```bash
ls -la ~/.claude/projects/-Users-peeta-Documents-Life-os/<SESSION_ID>.jsonl
wc -l ~/.claude/projects/-Users-peeta-Documents-Life-os/<SESSION_ID>.jsonl
```

Trace is format-identical to a manual Claude Code session's JSONL. No special decoding required.

**When done, retrieve the result.**

```bash
python3 "$CLAUDE_PROJECT_DIR/core/system/scripts/work_scoped_agent.py" result \
  --turn-id <TURN_ID> --json
```

The result JSON includes `launcher_result` with `duration_ms`, `num_turns`, `total_cost_usd`, `session_id`, and other run metrics. The `summary` field is a truncated preview of the final output; the full final output is in the session JSONL's last assistant event with `text` content.

**Spawn the reviewer** the same way, with a different temp file holding the reviewer prompt (with the coordinator's session UUID already filled in), a different `--name`, and the same `spawn` / `status` / `result` sequence. The reviewer is also a fresh-mode work-scoped agent with clean context — it does not inherit the coordinator's run, only what's in its own delegation prompt.

**Total duration for Experiment 1 under this command sequence:** ~12.3 minutes across both runs (7.6 coordinator + 4.7 reviewer), not counting the time spent writing the prompts. Most of the wall-clock time was blocking on the work-scoped agent runs; polling status between `sleep` calls was the main orchestrator activity.

**Things to check at each step that weren't obvious a priori:**
- The spawn command returns a subagent-id AND a turn-id (the turn-id is what you pass to `result`, not the subagent-id).
- The `session_id` is available from the `status` call almost immediately after spawn — you don't need to wait for the run to complete to know where the trace file will be.
- Trace file permissions may be `-rw-------` (owner-only). Reading from a different process (including the reviewer session) works because it's the same user.
- The runtime log files at `core/.state/work-scoped-agents/logs/turn-<ID>.log` are NOT the session transcript — they are the runtime wrapper's log and may be empty or minimal. The actual transcript is in the `~/.claude/projects/...` path.
