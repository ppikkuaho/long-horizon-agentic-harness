# Orchestration Frame — Continuation for a New Session

**Read this if you are a session that has already navigated into this folder and needs in-folder orientation.** This file is an internal bridge, not a handoff prompt. It gives you orientation, names what is done and what is open, and explains how experiments are run. When you finish reading this, you will know what to do next and which files hold the details.

*For the pass-to-a-new-session handoff artifact designed to be pasted into a fresh session as its opening prompt, see `HANDOFF.md` in the same folder. `HANDOFF.md` is tighter and assumes the reader is being told about the project for the first time. This `CONTINUATION.md` file assumes the reader is already in the folder and wants more depth.*

*Created 2026-04-11 at the phase 1 → phase 2 handoff. Updated 2026-04-12 after the live phase-2 program generalized beyond Experiment 1.*

## 60-second orientation

This folder holds a design frame for how AI should orchestrate complex task completion — how to decompose tasks, delegate to subagents, evaluate returns, iterate on failures. The central insight is that AI has a nature shaped by training (a strong pull toward completing tasks) and the right stance is to design the conditions under which that pull produces good outputs, not to fight it with instructions. Work with the nature, not against it. The water metaphor is in `frame.md` Part 1.

The frame is at phase 2 (experimentation and iteration), but phase 2 is no longer just "run Experiment 2." The operational center of gravity is now `phase-2-runs/`, which holds:

- `research/` — cross-task methodology and architecture findings
- `harness/` — the reusable self-improvement loop machinery
- `instances/` — concrete live branches

Experiment 1 still matters as the original validation of the rubric-reviewer method: Pass 14 / Fail 0 / zero Goodhart flags raised, full record in `experiment-protocol.md` under "Completed experiments" → "Experiment 1". But current work is broader:

- the canonical `self-improvement-harness/` branch is converged and stopped under independent-review authority
- the reusable harness lives under `phase-2-runs/harness/`
- the currently active live instance is `phase-2-runs/instances/delve-writing-loop/`

**Your job, if you were sent here, is most likely to continue the live phase-2 program, promote converged branch findings into the reusable harness or research artifacts, refine the frame/rubric from accumulated evidence, or extend the prompt-craft pattern library.**

## Who this bridge is for — and who it is NOT for

**This bridge is for an orchestrator**: someone or something that sets up the experiment, runs the coordinator, captures the trace, runs the reviewer, and records the result. The orchestrator reads everything in this folder that they need.

**This bridge is NOT for the coordinator.** The coordinator is a separate fresh session or work-scoped agent that receives only the coordinator prompt from `experiment-protocol.md` — nothing else. The coordinator must not know about the rubric, the reviewer, or the fact of observation. Knowing invites Goodhart performance for an imagined evaluator rather than natural frame application. See `frame-design-notes.md` §3.4 "The design session cannot execute the first experiment" for the full reasoning.

If you are going to BE the coordinator for the experiment, stop reading this file now. Read only the coordinator prompt in `experiment-protocol.md` and nothing else in this folder.

## Files in this folder, in reading order

For an orchestrator reading cold, read in this order:

1. **`phase-2-runs/README.md`** — the live-program structure and where current work lives.
2. **`phase-2-runs/research/methodology-log.md`** — the cumulative durable lessons. The newest entries are the most operationally relevant.
3. **`phase-2-runs/research/ARCHITECTURE-FINDINGS.md`** — structured findings ledger for harness and loop design.
4. **`phase-2-runs/harness/README.md`** — the reusable loop machinery.
5. **`frame.md`** — Parts 1 and 2 of the frame.
6. **`frame-design-notes.md`** — Parts 3 and 4, especially §3.4.
7. **`process-observation-rubric.md`** — read in full if you will set up or modify reviewer chains.
8. **`prompt-craft.md`** — delegation prompt patterns.
9. **`experiment-protocol.md`** — historical reference for Experiment 1 and the original rubric-reviewer execution path.

Outside this folder, related material:

- **`core/system/references/subagent-delegation-template.md`** — the seven-field delegation contract (Mode / Artifact / Type / Task / Context / Scope / Return) that governs any subagent spawn in this repo. The coordinator will need to write delegation prompts under this contract when it spawns its search subagent.
- **`core/system/references/subagent-runtime-modes.md`** — reference for the work-scoped agent capability. Relevant for the alternative execution path below.
- **`core/system/references/subagent-evidence-protocol.md`** — child-side return discipline for subagent work.
- **`projects/internal-ai-2.0/design/tool-design-learnings.md` Parts 2-4 and 8** — original empirical source for several frame principles. Not required reading for orchestrator purposes; included here only for anyone chasing the evidence chain back to its origin.

## What is done

**Phase 1: Codification.** The frame exists as five internally consistent files covering the operator layer (frame.md Parts 1, 2), the designer layer (frame-design-notes.md Parts 3, 4), the runtime rubric for phase-2 observation (process-observation-rubric.md), the prompt-craft pattern accumulator (prompt-craft.md), and the experiment protocol (experiment-protocol.md). Principles have been integrated from AI-DESIGN-PRINCIPLES.md, from the InternalAI 2.0 structural experiment, from the cognitive config skill-building work, and from working through observability questions in the design conversation. §3.4 methodology notes accumulate meta-level lessons from building the frame itself.

**Phase 2: Rubric instrument.** The process-observation rubric is specified with ~20 checks across five orchestration phases plus a cross-cutting phase, Goodhart flag list, trace-access guide, and known gaps section. Pre-flight validation against a real session JSONL confirmed the rubric's trace-ingestion assumptions hold, with three corrections applied (last-prompt drop, Agent-vs-Task tool name, tool_result event structure).

**Phase 2: Experiment 1 complete (2026-04-11).** Executed via Path B (fresh-mode work-scoped agent). Coordinator ran the Constitutional AI primary source lookup in ~7.6 minutes ($2.31); reviewer applied the rubric in ~4.7 minutes ($0.98). **Reviewer verdict: Pass 14 / Partial 0 / Fail 0 / N/A 8, zero Goodhart flags raised.** The method is empirically validated. Full record remains in `experiment-protocol.md`.

**Phase 2: live harness program now exists (2026-04-12).** The project has since grown a reusable self-improvement harness (`phase-2-runs/harness/`), a research ledger of cross-task findings (`phase-2-runs/research/`), and multiple task instances (`phase-2-runs/instances/`). The important shift is architectural: the project now tests the frame through ongoing loop operation, not just one-off experiment setup.

## What is open

**Live program continuation.** The main open work is no longer "pick the next experiment in the abstract." It is:

1. continue the active instance under `phase-2-runs/instances/` using the reusable harness
2. promote converged branch findings into `phase-2-runs/harness/` and the research artifacts
3. open new instances when a different task class or topology is needed

**Historical follow-up experiments.** Experiment 1 was a bounded factual lookup that exercised Phase A (task framing), Phase C (delegation design), Phase D (return handling), and the cross-cutting X checks. It did NOT exercise Phase B (decomposition strategy — atomic task), Phase E (iteration — no errors surfaced), or D2 (independent evaluation was reasonably declined). Those gaps are still valid reference candidates:

1. **Exercise Phase B.** Pick a task where decomposition is a real choice rather than atomic — something that could reasonably be run as a single agent, as parallel per-agent spawns, or as sequential-in-same-agent — and see how the coordinator reasons about the trade-off. Validates the decomposition-strategy checks (B1, B2, B3).
2. **Exercise Phase E.** Pick a task where errors are likely to surface mid-run, or where the first delegation return predictably misses the mark. Validates the iteration checks (E1 fix-at-source, E2 downstream regeneration, E3 structural-before-instruction fix).
3. **Test naturalistic delegation.** Give the coordinator a task where delegation is optional rather than explicitly instructed ("use a search subagent" → remove). See whether the coordinator naturally decomposes under the frame.
4. **Test the D2 refinement candidate.** The reviewer of Experiment 1 suggested hardening D2 to require an explicit decline-to-evaluate criterion rather than accepting post-hoc rationalization. A follow-up experiment that includes an analytical component where evaluation matters could test whether the coordinator articulates the criterion explicitly, and whether the stricter D2 would change the verdict.

**Rubric refinements deferred pending more data.** The D2 refinement candidate above is logged in §3.4 but not yet applied to the rubric. One data point is not enough to justify tightening. Consider after Experiments 2 and 3.

**What is NOT open.** Nothing in phase 2 is blocked on a structural prerequisite. The method is validated, the artifacts are ready, the work-scoped agent path has been exercised successfully. Any follow-up experiment can run as soon as it is scoped and its coordinator prompt is written.

## The contamination constraint (read this carefully)

The rubric-reviewer experiment architecture has a strict separation requirement: the coordinator must not know about the rubric, and the reviewer must not be contaminated by having read the frame documents in the design-conversation context. The design session that wrote the rubric, the task, both prompts, and this bridge is maximally contaminated for both roles.

The consequence: the design session itself cannot execute the first experiment. It can only prepare the artifacts and hand off.

This is captured as methodology note 4 in `frame-design-notes.md` §3.4 ("The design session cannot execute the first experiment"). Read it if you want the full reasoning — the short version is that writing the rubric Goodhart-maximizes the writer for the coordinator role and reading the frame extensively contaminates the reader for the reviewer role, and for a session that did both, both problems apply.

**But there is a meaningful exception.** A fresh session — started outside the design context — is clean by definition. So is a work-scoped agent running in `fresh` mode (see below). Both are valid execution paths.

## Two paths for running an experiment

*Experiment 1 ran via Path B (fresh-mode work-scoped agent) from this design session. The worked command sequence is captured in `experiment-protocol.md` under "Path B — worked example from Experiment 1" — that example is the concrete reference for any follow-up experiment that also runs via Path B.*

**Path A: Manual fresh Claude Code session (simplest, most obviously clean).**

1. Start a new Claude Code session in this repo. Open it as a new terminal or new Claude Code instance. Do not continue the session that wrote the bridge.
2. Paste the coordinator prompt from `experiment-protocol.md` section "Coordinator prompt" verbatim. The prompt tells the coordinator to read `frame.md` and `prompt-craft.md` and then execute the task.
3. Wait for the coordinator session to complete. The session writes its transcript automatically to `~/.claude/projects/-Users-peeta-Documents-Life-os/<new-uuid>.jsonl`.
4. Capture the session UUID. Find the newest JSONL in that directory: `ls -t ~/.claude/projects/-Users-peeta-Documents-Life-os/*.jsonl | head -1`. Verify it contains the task prompt as an early user event.
5. Start a SECOND fresh Claude Code session, completely separate from the coordinator session. This is the reviewer session.
6. Paste the reviewer prompt from `experiment-protocol.md` section "Reviewer prompt" verbatim, replacing `<UUID>` with the UUID from step 4.
7. The reviewer reads the rubric and the trace and produces a structured verdict.
8. Capture the verdict in `experiment-protocol.md` under "Completed experiments," along with concrete findings worth carrying forward and meta-level lessons worth adding to `frame-design-notes.md` §3.4.

**Path B: Work-scoped agent in fresh mode (spawn the coordinator from any session, including a new design-adjacent one).**

This repo has a new capability since the earlier methodology note was written: a **work-scoped agent** that runs in the Claude backend with full tool parity, may spawn its own subagents, and in `fresh` mode produces a clean child context with no inheritance from the parent session. The entrypoint is `python3 "$CLAUDE_PROJECT_DIR"/core/system/scripts/work_scoped_agent.py`. Reference documentation is in `core/system/references/subagent-runtime-modes.md`.

Why this matters for the contamination constraint: a fresh-mode work-scoped agent has a clean child context. It does not inherit the parent session's frame documents, rubric knowledge, or design conversation. It receives only the delegation prompt passed to it. If the delegation prompt is the coordinator prompt from `experiment-protocol.md` (which is self-contained and does not mention the rubric or observation), the work-scoped agent operates as a genuinely naive coordinator — as clean as a freshly-started Claude Code session would be.

This means a parent session that is itself contaminated (for example, a continuation of the design session) can still legitimately SPAWN a coordinator via a fresh-mode work-scoped agent, as long as the parent does not pollute the spawn prompt with design context. The supercapability path (work-scoped agent, full tool parity, can itself spawn search subagents) is exactly the shape the coordinator task needs.

Specific path B workflow:

1. From any session (including one that has read the frame documents), invoke the work-scoped agent entrypoint in fresh mode with the backend set to `claude`.
2. Pass the coordinator prompt from `experiment-protocol.md` as the delegation prompt. Do NOT include additional context, rubric hints, or commentary. The coordinator prompt is self-contained by design.
3. The work-scoped agent runs as a fresh Claude with full tool parity. It reads the frame documents per the coordinator prompt's instructions, spawns its own search subagent for the task, handles the return, and produces the final finding.
4. The work-scoped agent's execution should produce a trace in the standard session JSONL format, or whatever the work_scoped_agent.py entrypoint exposes — verify this against the live behavior, as the trace location may differ from standard Claude Code sessions. If the trace is in a non-standard location, adjust the reviewer prompt's step 3 file path accordingly.
5. After completion, the reviewer session still needs to be separate. Start a fresh Claude Code session for the reviewer (path A's step 5-7). The reviewer must not inherit from the session that spawned the coordinator — even though that session had already seen the frame, the reviewer needs to be clean of that context too.

**How to choose between paths A and B.** Path A is simpler and unambiguously clean. Path B is faster from a single-session workflow and showcases the work-scoped agent capability as a legitimate execution route. If the goal is to validate the method as cleanly as possible, prefer path A. If the goal is to also exercise the work-scoped agent capability for its own sake (and to verify it produces usable traces for reviewer ingestion), path B is a reasonable first-pass test — but recognize that path B is validating two things at once, and failures could be in either the frame or the work-scoped agent tooling.

For the very first experiment, I would lean path A. For subsequent experiments once the rubric-reviewer method is confirmed to work, path B becomes attractive because it fits cleanly into orchestration-from-a-single-parent workflows.

## Notes on runtime constraints

Whichever path you take, the coordinator will operate under this repo's delegation contract hook. When the coordinator spawns its search subagent, the delegation prompt must follow the Mode / Artifact / Type / Task / Context / Scope / Return format and tell the child to read the evidence protocol. The hook blocks spawns that do not comply. This is a feature — the hook catches malformed spawns that would otherwise confuse the reviewer's observation of delegation design. Reference: `core/system/references/subagent-delegation-template.md`.

The Agent tool in this repo's environment is named `Agent` (not `Task`), with `input` keys `description`, `subagent_type`, `prompt`. This matters for the reviewer's trace parsing. The rubric and experiment protocol are already corrected for this naming, but if you find a mismatch during reviewer parsing, check the actual tool name in the trace events.

## After running the first experiment

Two levels of capture, per the system's durable-knowledge discipline:

**Concrete findings.** What did the coordinator actually do? Which rubric checks passed, which failed, which were N/A? Did the reviewer have any difficulty applying the rubric? Did the trace format work as expected? Record these in `experiment-protocol.md` under "Completed experiments" as an entry with date, coordinator session UUID, and reviewer verdict summary. These are data for the next experiment.

**Meta-level lessons.** Did the first experiment surface anything about the method that applies to future experiments, future rubrics, or frame construction in general? Did the rubric have gaps? Did context budget become a real constraint? Did the coordinator engage with the frame naturally or treat it as reference material? These go into `frame-design-notes.md` §3.4 as new methodology notes. The bar is "a future instance designing a similar experiment would benefit from knowing this."

If the rubric needs corrections, update `process-observation-rubric.md` directly. The rubric is explicitly first-pass and expected to evolve based on real-trace data. Note the correction in the CHANGELOG.

If the prompt-craft document needs new entries because the coordinator or reviewer surfaced a phrasing pattern that mattered, add them to `prompt-craft.md` following its existing entry format.

If the frame itself needs a principle added or changed — which is rarer and more load-bearing — the change belongs in `frame.md` Part 2 under the appropriate structural-interventions or operational-levers section, with the usual discipline: any new principle needs a first-attempt audit (for frame.md Part 2.3) and, where trade-offs apply, a concrete rubric.

Update the CHANGELOG with a new 2026-04-* entry summarizing the experiment, the findings, and any artifact changes made as a result.

## What you do not need to do right now

- **Cross-domain validation of the frame** (running it against tasks outside the extraction domains). Phase B, not phase 2.
- **Building a transcript preprocessor** for context-budget scaling. §3.4 methodology note 2 explicitly defers this until the first experiment reveals what the reviewer actually needs from the trace. Do not solve the scaling problem before the method is validated.
- **Adversarial validation of the rubric itself against exemplar traces.** That is a later activity once there are real traces to validate against. The first experiment produces the first real trace.
- **Extending the frame with principles from domains we haven't yet mined.** The frame's content is provisional but not blocking anything. Focus on running the experiment.

## Open questions the first experiment should help answer

- Does the rubric apply? Can the reviewer map checks to trace events without ambiguity, or are there checks that are too vague or too strict to be usable?
- Is raw JSONL ingestion practical? Does context budget become a real constraint on a bounded task, or does the first experiment fit comfortably in reviewer context?
- Does the coordinator engage with the frame when told to apply it, or does it read the frame and then work on instinct? This is the core question of the frame's load-bearing value.
- What Goodhart patterns surface that the rubric does not yet catch?
- Was the task appropriately sized? Too small (most checks N/A)? Too large (context overflow)? About right?

Any revelation on any of these is valuable. The first experiment is diagnostic for the method, not definitive validation of the frame's principles.

## If something in this bridge is wrong

This bridge was written by the design session itself as a handoff artifact. The design session is contaminated. Corrections from a fresh perspective are expected and welcome — if you find something in this bridge that misrepresents the state or the protocol, update the bridge before running the experiment. The bridge itself is an artifact that should improve over successive sessions, not a fixed oracle. Add corrections, new context, or refinements, and note them in the CHANGELOG.

---

*End of bridge. The next file to read depends on what you are doing. If you are running the first experiment, read `experiment-protocol.md` in full. If you are updating the rubric or the frame itself, read `frame.md` Parts 1 and 2 and then `frame-design-notes.md` §3.4 first.*
