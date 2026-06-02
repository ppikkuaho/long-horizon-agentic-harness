# Self-Improvement Loop Playbook

This folder turns the orchestration-frame project into a runnable LLM self-improvement harness.

The harness is for work where:

- a builder improves an artifact set
- the builder is not allowed to decide when the loop stops
- independent reviewers govern continuation
- the work should converge only when remaining improvements are smaller than medium

This playbook is the operator-facing entrypoint. It tells each role what to read, what to produce, and how a round moves forward.

## Task-class boundary

The harness is domain-agnostic.

It should encode reusable operators and control surfaces, not hardcoded domain interventions. In practice:

- general harness layer: topology discovery, decomposition choice, verification design, reviewer structure, control-plane rules, retry taxonomy
- task layer: the domain-specific surfaces those operators resolve into for this round

Examples:

- research task: source topology and evidence diversity
- coding task: code/test/runtime topology
- debugging task: repro and observability topology
- design task: constraint and evaluation topology
- writing task: voice/structure/evaluation topology

Do not promote named domain sources or tools into the harness unless they are part of the harness substrate itself.

## Roles

### Orchestrator

Owns the loop but does not author the judged content.

Responsibilities:

- create the round brief
- keep the manifest and ledger current
- keep the next-action surface current
- spawn or route builder and reviewer sessions
- hand each role only the inputs it should see
- advance state only according to reviewer verdicts

### Builder

Edits the target artifact set for the current round.

The builder:

- may propose improvements
- may not stop the loop
- must produce a builder output artifact describing what changed and why
- must target declared artifacts, not drift into commentary expansion

### Reviewer 1

Checks adherence to:

- maintained orchestration-frame documents
- this harness contract
- the current round brief

Reviewer 1 decides whether the work is ready for Reviewer 2.

### Reviewer 2

Evaluates the stronger question:

"For this task class, to reach the quality and thoroughness a strong professional team could achieve under the stated constraints, what still needs to change?"

Reviewer 2 is the stop authority.

### Human Principal

Sets the objective, can redirect strategically, and can intervene on true external blockers. The human does not adjudicate routine round transitions.

## Required files

- `self-improvement-loop-contract.md`
- `stop-policy.md`
- `adjudication-policy.md`
- `outcome-rubric.md`
- `anti-rigidity.md`
- `builder-template.md`
- `reviewer-1-template.md`
- `reviewer-2-template.md`
- `round-template.md`
- `reference-map.md`
- `manifest.yaml`
- `run-ledger.jsonl`
- `control_plane.py`
- `CONTROL-PLANE.md`
- `WORKBOARD.yaml`
- `workboard.py`
- `continuation-template.md`

## Round artifact set

Each round lives under `iterations/iteration-NN/` and should contain:

- `brief.md`
- `builder-output.md`
- `reviewer-1-verdict.md`
- `reviewer-2-verdict.md`
- optional supporting notes or diffs

The orchestrator may add more files, but these are the minimum control-plane artifacts.

## Round-brief minimums

Every `brief.md` should make these explicit if they are not obvious from context:

- task class
- relevant topology to map or validate
- quality benchmark appropriate to the task class
- path-lock risk for the round
- preferred perturbation if the current path proves too narrow
- verification surfaces that matter for this round

## Anti-rigidity posture

For non-trivial rounds, the harness should resist basin lock-in explicitly.

Default rule:

- separate path generation from path selection
- treat the first workable path as a fixation risk, not proof it is the right path
- when lock-in signals appear, use a perturbation operator rather than only adding more effort inside the current frame

Preferred perturbation operators:

- assumption surfacing
- pre-mortem on the current path
- inversion or constraint shift
- alternate decomposition
- independent fresh-context review
- orthogonal verification surface

## Reading order by role

### Orchestrator reads

1. `self-improvement-loop-playbook.md`
2. `self-improvement-loop-contract.md`
3. `stop-policy.md`
4. `adjudication-policy.md`
5. `anti-rigidity.md`
6. `reference-map.md`
7. `manifest.yaml`
8. current round `brief.md`

### Builder reads

1. `builder-template.md`
2. `anti-rigidity.md`
3. current round `brief.md`
4. target artifacts named in the brief
5. current round prior reviewer verdicts, if any
6. `reference-map.md`

The builder should not read reviewer templates as instructions for how to game review.

### Reviewer 1 reads

1. `reviewer-1-template.md`
2. `anti-rigidity.md`
3. current round `brief.md`
4. current round `builder-output.md`
5. target artifacts
6. referenced maintained docs from `reference-map.md`

Reviewer 1 should not read Reviewer 2 materials before issuing its own verdict.

### Reviewer 2 reads

1. `reviewer-2-template.md`
2. `anti-rigidity.md`
3. current round `brief.md`
4. current round `builder-output.md`
5. current round `reviewer-1-verdict.md`
6. target artifacts
7. `reference-map.md`

## Default round flow

1. Orchestrator creates `brief.md` from `round-template.md`.
2. Orchestrator marks `manifest.yaml` state as `builder_in_progress`.
3. Builder edits only the target artifact set and writes `builder-output.md`.
4. Orchestrator marks state as `reviewer_1_pending`.
5. Reviewer 1 writes `reviewer-1-verdict.md`.
6. Orchestrator applies `adjudication-policy.md`.
7. If Reviewer 1 says `continue`, next round starts.
8. If Reviewer 1 says `pass`, Reviewer 2 runs.
9. Reviewer 2 writes `reviewer-2-verdict.md`.
10. Orchestrator applies `stop-policy.md`.
11. If Reviewer 2 says `continue`, next round starts.
12. If Reviewer 2 says `stop`, the loop ends.

At every checkpoint, the orchestrator must also keep `manifest.yaml`'s `next_action` block current, keep the `global_completion` gate honest, maintain the `activity_lease` if a session is actively working, leave `control_plane.py validate` passing, keep the external watchdog runnable, and treat `control_plane.py contact-check` as the only authority for whether user-facing communication is allowed.
At every checkpoint, the orchestrator must also keep `WORKBOARD.yaml` current so branch ownership, evidence surfaces, and saturation state are explicit rather than reconstructed from memory.

## Local Versus Global Convergence

The harness may use local task instances, side investigations, or shadow branches as evidence-producing work units.

Structural rule:

- local convergence is evidence, not top-level stop authority
- a converged child branch must be consumed by an explicit top-level decision written into the canonical manifest and ledger
- `next_action.kind: local_loop_stopped` belongs in `global_reconciliation_pending`, not `stopped`
- valid follow-up decisions are: absorb findings into the current round, open a new round, open a new branch, mark blocked, or stop under reviewer authority
- if none of those has been committed, the program is still live even if a child branch is finished

If a reusable live harness exists outside this folder, divergence between the canonical harness and that live harness must trigger an explicit reconciliation round rather than a silent handoff.

The split is intentional:

- this folder is the canonical, reviewer-governed harness specification
- `../phase-2-runs/harness/` is the reusable live proving ground
- the live harness can produce candidate lessons faster than the canonical harness can safely absorb them
- promotion happens only when the canonical round updates this folder's maintained docs or control-plane code

A drafted future round also does not become active by implication. The active round is whatever the manifest currently names through `current_iteration`, `current_iteration_path`, `current_round_brief`, and the active round artifact pointers.

## External Watchdog

`watchdog.py` is the external observer for this harness.

- it polls the lease from outside the live session
- it updates `watchdog` and `observation_window` through `control_plane.py watchdog-checkpoint`
- it writes `.watchdog/status.json` on every poll
- it does not auto-run recovery commands unless both `watchdog.auto_resume_command` and the runtime `--run-recovery` flag are present
- stale leases become `stale_suspect`, `recovery_required`, or `recovery_in_progress`; they do not silently disappear
- the default operator path is `RUNBOOK.md`, which starts the watchdog before resuming `next_action`

## Structured outputs

Every role artifact must begin with a YAML frontmatter block.

The frontmatter is the machine-usable control surface. Prose below it is explanatory. If they disagree, the frontmatter wins.

Required frontmatter-bearing artifacts:

- `builder-output.md`
- `reviewer-1-verdict.md`
- `reviewer-2-verdict.md`

## Resume procedure

Use this when a fresh session takes over.

1. Read `manifest.yaml`.
2. Run `python3 control_plane.py next`.
3. Run `python3 control_plane.py contact-check`.
4. Read the last 20 lines of `run-ledger.jsonl`.
5. Read the current round `brief.md`.
6. Read the most recent reviewer verdict for the active round, if it exists.
7. Read only the target artifacts listed in the brief plus any required maintained docs from `reference-map.md`.
8. Continue from the manifest state and next-action packet rather than reconstructing the entire project history.

If the manifest and ledger disagree, pause and repair the control-plane truth before doing content work.

Fresh launch and continuation are different artifact classes. A resumed session should inherit a continuation packet such as `CONTINUATION.md` that states current state, completed work, live ownership, and the exact next action from control-plane truth. Do not reuse a launch brief as a continuation packet.

## Role packet rule

Each spawned role should receive an explicit packet containing:

- role name
- objective
- exact files to read
- exact file to write
- decision authority limits
- the current iteration number

Do not launch a role with only conversational summary if a packet can be written instead.

If the round depends on task-class-specific judgment, the packet should explicitly name the task class and the relevant topology for that round.

## Structural rules

- Builder cannot terminate the loop.
- Reviewer 1 cannot stop the program; Reviewer 1 can only gate progression to Reviewer 2.
- Reviewer 2 is the only role allowed to stop the loop.
- Reviewers must be independent sessions.
- Builder and reviewers must write the required YAML frontmatter before any narrative analysis.
- Non-trivial rounds must make path-lock risk and preferred perturbation explicit in the brief.
- The orchestrator updates `manifest.yaml` and `run-ledger.jsonl` after every state change.
- The orchestrator updates `manifest.yaml` and `run-ledger.jsonl` after every checkpoint that changes the committed next action.
- `manifest.yaml` must expose the machine-readable next action and user-contact policy.
- `manifest.yaml` must expose the reporting policy, and no user-facing report is allowed unless `control_plane.py contact-check` says it is.
- Local branch or instance convergence does not terminate the top-level loop by implication.
- Narrative notes are allowed, but control-plane truth lives in the manifest, ledger, and reviewer verdict files.

## Preferred execution path

Use structurally separate sessions.

In this repo, the preferred path is a fresh-mode work-scoped agent or equivalent separate session for each role. If a session can inherit builder context into the reviewer, it is not independent enough for this harness.

## Stop condition

The loop stops only when Reviewer 2 explicitly states that the highest remaining improvement severity is smaller than medium.

See `stop-policy.md` for the exact rule.
