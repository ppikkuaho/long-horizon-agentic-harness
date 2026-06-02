# Session Handoff — Orchestration Frame

*This file is a handoff prompt. It is meant to be passed to a fresh Claude Code session as its opening orientation — paste its contents, or reference it via `@projects/ai-architecture/design/orchestration-frame/HANDOFF.md`, as the new session's first message. When the new session finishes reading this single file, it will know what project it is working on, where that project stands, what its likely job is, and which other files to read next. A more detailed internal bridge for in-folder exploration lives at `CONTINUATION.md` in the same folder.*

## 30-second orientation

You are picking up work on the **orchestration frame** at `projects/ai-architecture/design/orchestration-frame/`. The orchestration frame is a design frame for how AI should orchestrate complex task completion — how to decompose tasks, delegate to subagents, evaluate returns, and iterate when things go wrong. The central insight is that AI is heavily biased toward completing tasks (shaped by training, RLHF, and related reward signals) and successful orchestration works WITH that nature rather than against it: shape the task so the natural completion path produces what you want. Water metaphor — build the riverbed, don't fight the current. Details in `frame.md` Parts 1 and 2.

## Current state

**Phase 1 — frame codification: complete.** The frame exists as the core design documents in this folder.

**Phase 2 — experimentation is now a live program, not just Experiment 1.** The center of gravity has moved into `phase-2-runs/`:

- `phase-2-runs/research/` — the cumulative methodology and architecture learnings
- `phase-2-runs/harness/` — the reusable self-improvement-loop machinery
- `phase-2-runs/instances/` — concrete live task branches

Historical note: Experiment 1 (Constitutional AI primary-source lookup, 2026-04-11) still matters because it validated the rubric-reviewer method cleanly: **Pass 14 / Partial 0 / Fail 0 / N/A 8, zero Goodhart flags raised.** But it is no longer the whole story.

**Current operational picture (2026-04-12):**

- the canonical `self-improvement-harness/` branch is converged and structurally stopped under independent-review authority
- the reusable harness has been generalized under `phase-2-runs/harness/`
- the active live branch is `phase-2-runs/instances/delve-writing-loop/`, a Round 5 creative-writing generalization stress test

## Your likely job

Ask the user to confirm, but it is most likely one of:

1. **Continue the phase-2 live program.** This usually means one of:
   - continuing the active instance under `phase-2-runs/instances/`
   - promoting a converged branch finding into the reusable harness or research artifacts
   - opening a new instance to stress a different part of the architecture

2. **Apply the frame to real orchestration work.** The frame is not just for meta-experiments. If you are given a substantive task that involves multiple steps, delegation, evaluation, or iteration, applying the frame to that real work is a legitimate use. Read `frame.md` Parts 1 and 2 and follow the principles.

3. **Refine the reusable harness or its control surfaces.** The active work now includes control-plane behavior, continuation/handoff surfaces, reviewer governance, and observation machinery under `phase-2-runs/harness/` and `phase-2-runs/research/`.

4. **Extend the `prompt-craft.md` pattern library** with new entries from failure modes or working patterns you encounter while applying the frame. Entry format is in the file.

5. **Something else the user specifies.** Ask.

## Reading order

Read in this order, stopping when you have enough context for the task:

1. **`CONTINUATION.md`** — internal bridge with more detail than this handoff file. Covers the same ground but with in-folder framing.
2. **`phase-2-runs/README.md`** — the live-program structure. Read this first if you are doing harness or instance work.
3. **`phase-2-runs/research/methodology-log.md`** and **`phase-2-runs/research/ARCHITECTURE-FINDINGS.md`** — the durable lessons and structured findings ledger for the live program.
4. **`phase-2-runs/harness/README.md`** — the reusable loop machinery. Read if you are touching control-plane, supervisor, continuation, or reviewer-template behavior.
5. **`frame.md`** Parts 1 and 2 — the frame itself. Read if you will apply the frame to real work or reason about what it does.
6. **`experiment-protocol.md`** — historical reference for Experiment 1 and for the original rubric-reviewer method.
7. **`process-observation-rubric.md`** — read in full if you will be setting up a reviewer session or modifying evaluator structure.
8. **`frame-design-notes.md`** §3.4 — methodology notes accumulated from building and testing the frame.
9. **`prompt-craft.md`** — pattern library. Skim entry headings to find a pattern relevant to any delegation prompt you are writing.

## Critical execution constraints

**The subagent delegation contract hook is active.** Any subagent spawn via the Agent tool in this repo must follow the seven-field delegation contract (Mode / Artifact / Type / Task / Context / Scope / Return) specified in `core/system/references/subagent-delegation-template.md`. The hook blocks spawns that do not comply. Read the template before your first delegation. The evidence protocol at `core/system/references/subagent-evidence-protocol.md` is the child-side companion.

**Work-scoped agents are available as a supercapability path alongside the built-in Agent tool.** Reference: `core/system/references/subagent-runtime-modes.md`. CLI entrypoint: `python3 "$CLAUDE_PROJECT_DIR"/core/system/scripts/work_scoped_agent.py`. Fresh-mode spawns have clean child context with full tool parity and can spawn their own subagents recursively. Experiment 1 used this path for both the coordinator and the reviewer — the exact command sequence is preserved in `experiment-protocol.md` under "Path B — worked example from Experiment 1" and is the recommended reference for any follow-up experiment that also runs via path B.

**The contamination constraint applies to phase-2 experiments.** If you design the rubric or write the task for a new experiment, you cannot also be the coordinator or reviewer for that experiment — you are Goodhart-contaminated for the coordinator role (you know what the rubric checks) and frame-aware-contaminated for the reviewer role (the reviewer must see only the rubric, not the frame). Spawn the coordinator and reviewer as separate fresh-mode work-scoped agents, each seeing only its own prompt. Full reasoning in `frame-design-notes.md` §3.4 methodology note 4, including the work-scoped-agent refinement paragraph that explains why spawning from a contaminated parent is legitimate when the parent passes only self-contained prompts.

## What contamination means for you as the handed-off session

Reading this handoff file and `CONTINUATION.md` gives you rubric-adjacent awareness (phase letters, Goodhart categories, D2 by name) even if you never read the rubric itself. That is enough mild contamination that you should NOT be a direct coordinator or reviewer for any new phase-2 experiment you set up. The clean pattern is the one Experiment 1 used: the parent session (which was itself contaminated) spawns coordinators and reviewers as separate fresh-mode work-scoped agents, each receiving only its own self-contained prompt. Fresh-mode children inherit none of the parent's context, so they are clean regardless of what the parent session has read. You are the orchestrator/observer of the experiment, not a direct participant.

For **applying the frame to real orchestration work** (option 2 in "Your likely job" above), contamination does not apply — real work is not a rubric-scored experiment. Reading the frame and then applying it to a real task is the intended use case.

For **extending the rubric or the frame itself** (options 3 and 4), reading `process-observation-rubric.md` in full is appropriate since you are not going to be a coordinator or reviewer; you are the designer modifying the instrument.

The rule, stated simply: read what the job requires. If the job is experiment orchestration, read `experiment-protocol.md` but don't plan to be the coordinator or reviewer yourself — spawn them as fresh-mode children. If the job is real work under the frame, read `frame.md` Parts 1 and 2 and apply normally. If the job is frame or rubric development, read everything.

## First move

1. Read this file (you just did).
2. Read `CONTINUATION.md` for more context if needed.
3. Ask the user to confirm your job (follow-up experiment, applying the frame to real work, refinement, pattern library extension, or something else).
4. Proceed from there, reading the additional files relevant to the confirmed task.

If the task is to run a follow-up experiment, also read `experiment-protocol.md` and `process-observation-rubric.md` before spawning anything. If the task is to apply the frame to real work, read `frame.md` Parts 1 and 2 before starting. If the task is unclear, ask.
