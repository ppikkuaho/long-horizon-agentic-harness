# Self-Improvement Loop — Entry Point

*This file is the entry point for running a fresh self-improvement loop. The human provides a task. You read this file, set up the instance, and run the loop.*

If you are resuming an existing instance, do not use this file as the continuation prompt. Read that instance's generated `CONTINUATION.md` instead.

## What you are doing

You are running a self-improvement loop on a task the human has given you. The loop produces two things:

1. **Task deliverable** — a ranked, evidence-backed answer to the task question, validated by independent reviewers.
2. **Harness learnings** — observations about how the loop, the delegation framework, and the reviewer chain work (or fail to work), captured in `phase-2-runs/research/`.

Both matter. The task is real work, not busywork. The learnings improve future loops on future tasks. When the two conflict, ask which produces more durable value and do that.

## Autonomous continuity mechanism (MANDATORY)

At least one structural continuity mechanism must be active during autonomous sessions.

### Claude Code path

If you are in Claude Code and background shell completions re-enter the conversation as mechanical notifications, start the prod immediately:

```bash
bash phase-2-runs/harness/autonomous-prod.sh start
```

Run it with `run_in_background: true`. This starts a 10-minute self-prompt daemon. When it fires, it re-injects the standing directives and asks "anything still to do?" You MUST restart it after every prod notification by running the same command again.

To disable when ALL work is genuinely complete: `bash autonomous-prod.sh disable` (triggers a confirmation step). You cannot disable without confirming all tasks are done.

### Codex or non-reinjecting environments

Do **not** rely on `autonomous-prod.sh` as the continuity layer when background shell completion does not create a new mechanical turn.

In those environments, the structural continuity mechanism is the external supervisor plus maintained artifacts:

```bash
python3 phase-2-runs/harness/loop_supervisor.py --watch --interval-s 20 --json
```

Run it in a long-lived PTY or service-managed shell. Use the observation file and the manifest's control-plane state as the continuity surface instead of waiting for an in-band prod.

## Your first steps

1. Start the appropriate continuity mechanism (above) if you haven't already.

2. Read the task the human provided (in the message that pointed you here, or in a task file they referenced).

3. Read these artifacts in order:
   - `phase-2-runs/research/methodology-log.md` — cumulative durable lessons. **Read fully.** The last 10 entries are the most important.
   - `phase-2-runs/harness/README.md` — what harness tooling is available.
   - `phase-2-runs/research/ARCHITECTURE-FINDINGS.md` — known harness issues. Scan for any affecting your task.
   - `projects/ai-architecture/design/orchestration-frame/frame.md` — the orchestration framework (read in chunks).
   - `core/system/references/subagent-delegation-template.md` — the 7-field delegation contract.

4. Set up the instance:
   - Create `phase-2-runs/instances/<task-name>/`
   - Copy `phase-2-runs/harness/control_plane.py` and `phase-2-runs/harness/loop_supervisor.py` into the instance folder
   - Create `manifest.yaml` with the task's objective, stop conditions, and initial state `coordinator_pending`
   - Copy and instantiate `phase-2-runs/harness/OBSERVATION-FILE-TEMPLATE.md` as the first live observation file for the task
   - Copy and customize `phase-2-runs/harness/transition-protocol-template.md` for this task's reviewer-chain rules
   - Customize reviewer prompts from `phase-2-runs/harness/reviewer-prompt-templates/` with the task's scoring reference, file paths, and finish condition
   - Draft the round-1 coordinator delegation prompt (7-field contract, frame docs as pre-reads, approach-space guidance in Scope, legitimate exits, difficulty framing, trust-boundary line for content-fetching subagents)
   - Run `python3 control_plane.py refresh-continuation` once so the instance has a generated resume packet before the first handoff risk appears
   - Spawn the coordinator

5. Run the loop. Per-round shape: spawn coordinator → capture return → R1 (adherence) → R2 (quality) → R3 (task finish). Use the control plane for transitions. Use the supervisor to watch for failures.

Keep the observation file live while the run is active:

- use `Section 0 — Overview` as the short exec-summary
- use `Section 0.5 — Detailed narrative` when the run is substantial enough to need chronology
- use `Section 1 — Pre-run intent` before or near spawn time so surprises remain visible later
- use `Section 2 — Live observations` as the artifact-level dashboard instead of relying on conversation status
- use later sections to capture reviewer commentary and gap deltas

## Finish conditions

The loop ends only when BOTH:
1. **Loop finish** — Reviewer 2 says "only minor changes remain."
2. **Task finish** — Reviewer 3 confirms the deliverable meets the task's finish condition.

You do not judge when to stop. Reviewers do. Dead candidates (R3 below threshold) spawn a new coordinator with different conditions, not a stop.

## Continuation rule

- Fresh setup uses this file.
- Mid-run resume uses the instance's `CONTINUATION.md`.
- If an older instance lacks `CONTINUATION.md`, generate it from the current manifest and ledger with `python3 control_plane.py refresh-continuation` before handing off.

## Discipline rules

These are load-bearing, not suggestions. They come from prior loops failing in specific ways.

**Separate observation from inference.** Every claim in a maintained artifact must be labeled as evidence or inference. Presenting conjecture as fact is a protocol violation.

**Only independent reviews count.** Self-assessed scores from coordinators are drift-tracking metadata only.

**Improvements must generalize.** Harness or framework changes must work for any task type. Task-specific fixes belong in the task's delegation prompt.

**Diagnose the delegation first.** When a coordinator drifts, the first question is what the delegation framing caused — not what guardrail to add.

**Infrastructure failures are retries, not reroutes.** Auth expiry, rate limits, transient errors → retry same delegation. Dead candidates → different conditions.

**Artifacts are the continuity layer.** This system is stateless across sessions. Capture durable learnings in `research/methodology-log.md`. What stays in conversation dies with the session.

## Capturing learnings

After each meaningful event (coordinator return, reviewer verdict, infrastructure failure, unexpected behavior), ask:

1. Is this observation task-specific or cross-task?
2. If cross-task: does it reveal something about the delegation framework, the reviewer chain, the control plane, or the observation methodology?
3. If it does: capture in `research/methodology-log.md` (narrative) and/or `research/ARCHITECTURE-FINDINGS.md` (structured finding).

Capture incrementally. The research artifacts are live dashboards, not post-mortem documents.
