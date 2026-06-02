# Mousepad Loop — Architecture Findings Ledger

This file captures durable harness findings surfaced by the live mousepad run.

Rule:
- every meaningful issue gets classified
- only cross-task findings should influence the harness
- task-specific noise should be explicitly marked as such

## Classification buckets

- `runtime`
- `observability`
- `reviewer-structure`
- `delegation-prompt`
- `loop-design`
- `control-plane`
- `artifact-design`
- `task-specific-noise`

## Findings

### F-001 — Coordinator explored outside its delegation scope — a delegation-design signal, not an access-control problem

- First seen: 2026-04-12 round 1 observation
- Bucket: `delegation-prompt` (reframed from `artifact-design` after MD correction)
- Evidence: coordinator read `iteration-log.md` and `dead-candidates.md`, which are loop-runner state artifacts outside its declared scope
- Root-cause analysis (MD correction 2026-04-12): the coordinator exploring the parent directory is a role-drift signal. A well-delegated coordinator should trust its delegates and audit only reported process — not do its own filesystem archaeology. If it needs to audit actual work beyond returns, it should send a subagent for that with intentional framing. The initial response (add read-surface allowlist) was symptom-patching: enforcement after drift rather than preventing the drift. The correct fix is in the delegation's framing of the coordinator's role and trust relationship with its context.
- ~~Candidate improvement: move loop-runner control files into a sibling `_runner-state/` area or explicitly exclude them in coordinator delegations~~ (this is the access-control patch, not the root fix)
- Corrected candidate improvement: improve the delegation so the coordinator has no reason to explore — clean role framing, sufficient context in the delegation, and explicit guidance that exploring beyond provided context is not part of the coordinator's job. If the coordinator still drifts, that's a frame-level role-separation activation failure, not a permissions problem. See methodology-log.md "coordinator role drift is a delegation-design signal."
- Status: reframed; partial fix in Round 2 delegation (added role-boundary instruction), but the deeper delegation-quality fix needs further iteration
- Durability judgment: cross-task; generalizes to any multi-layer orchestration where coordinators share context space with other layers

### F-002 — Supervisor-level observation is necessary but insufficient

- First seen: 2026-04-12 round 1 observation
- Bucket: `observability`
- Evidence: `observe` shows health, heartbeat, and log growth, but not enough semantic progress to tell what the coordinator is doing without deeper trace access
- Risk: false confidence in "healthy" runs that are making low-value progress or drifting internally
- Candidate improvement: standardize a richer loop-runner observation cadence combining supervisor observe + targeted session trace checks
- Status: open
- Durability judgment: cross-task

### F-003 — Health state and semantic state are distinct

- First seen: 2026-04-12 round 1 observation
- Bucket: `observability`
- Evidence: supervisor surface reports the coordinator as healthy/running while the coordinator session trace shows it is currently blocked inside a foreground `Agent` tool call for Phase 2 Pair B
- Risk: a loop runner can misread "running" as "actively advancing its own reasoning" when the real state is "waiting on a delegated child"
- Candidate improvement: define an observation vocabulary with at least `healthy`, `reasoning`, `waiting_on_child`, `waiting_on_io`, `suspect_stalled`
- Status: open
- Durability judgment: cross-task

### F-004 — Execution claims can diverge from actual tool actions

- First seen: 2026-04-12 round 1 observation
- Bucket: `observability`
- Evidence: coordinator text said it was spawning Pair B and Pair C in parallel, but the trace showed only the Pair B `Agent` tool call had actually happened at that point; the coordinator later explicitly self-corrected this mismatch
- Risk: loop runners or reviewers can over-credit decomposition quality or parallelism if they trust natural-language status summaries without checking tool-level trace evidence
- Candidate improvement: add a verification rule for live observation and later review: execution summaries must be checked against actual tool calls before being treated as fact
- Status: open
- Durability judgment: cross-task

### F-005 — Reviewer stop authority is structurally important but still unvalidated in this live loop

- First seen: 2026-04-12 side-branch review
- Bucket: `reviewer-structure`
- Evidence: the loop's stop authority has been moved into Reviewer 2 and Reviewer 3, but Round 1 has not yet exercised either reviewer path; the current evidence is still mostly coordinator-side
- Risk: apparent convergence can be false if reviewers inherit the same framing, omissions, or meta-context rather than independently pressure-testing the deliverable
- Candidate improvement: once Round 1 returns, run the canonical reviewer chain and add a shadow reviewer-independence branch if the main path appears to converge quickly
- Status: open
- Durability judgment: cross-task

### F-006 — Success-path widening exists in principle but is not yet operationally exercised

- First seen: 2026-04-12 side-branch review
- Bucket: `loop-design`
- Evidence: `PROGRAM.md` says early convergence should widen the work rather than end it, but no success-path widening branch has yet been executed
- Risk: one strong coordinator run can create false confidence about architecture robustness if no opposing decomposition or stricter review branch is forced
- Candidate improvement: precommit at least one widening branch when the first apparent convergence signal appears
- Status: open
- Durability judgment: cross-task

### F-007 — Dead-candidate recovery logic is specified, but not yet evidence-backed

- First seen: 2026-04-12 side-branch review
- Bucket: `loop-design`
- Evidence: the handoff defines a dead-candidate cycle, but no Reviewer 3 rejection has happened yet, so the reroute logic has not been tested under pressure
- Risk: on the first rejection, the loop may perform local prompt edits while preserving the same search surface instead of taking a materially different branch
- Candidate improvement: prepare an explicit reroute menu with orthogonal restart conditions before the first dead-candidate event occurs
- Status: open
- Durability judgment: cross-task

### F-008 — Artifact-boundary leakage is observed, but clean-room behavior remains untested

- First seen: 2026-04-12 round 1 observation + side-branch review
- Bucket: `artifact-design`
- Evidence: the coordinator did read loop-runner state files; no sibling clean-room branch has yet been run to measure how much that changed behavior
- Risk: role contamination can stay hidden because the contaminated branch may still look disciplined and high-quality
- Candidate improvement: run at least one clean-room coordinator or reviewer branch with loop-runner state artifacts excluded from the readable surface
- Status: open
- Durability judgment: cross-task

### F-009 — The observation stack tracks liveness better than learning density

- First seen: 2026-04-12 side-branch review
- Bucket: `observability`
- Evidence: current observation can separate health from semantic state, but it still requires manual judgment to decide whether a run is producing enough architecture signal per hour
- Risk: the loop can stay healthy and busy while under-testing the harness
- Candidate improvement: add a standing diversification checkpoint at major gates and treat "too little new signal per hour" as an explicit branch-opening condition
- Status: open
- Durability judgment: cross-task

### F-010 — Prose-only anti-idle rules are not structural prevention

- First seen: 2026-04-12 direct user critique during the live run
- Bucket: `loop-design`
- Evidence: the no-user-dependency section in `PROGRAM.md` was policy text only; it depended on obedient execution rather than a machine-usable state surface
- Risk: a fresh session can still pause, drift, or ask the user simply because the control plane does not force a next action
- Candidate improvement: persisted manifest + append-only ledger + executable transition helper now; lease/watchdog layer next
- Status: in progress
- Durability judgment: cross-task

### F-011 — Long semantic-silence windows need a `stale_suspect` state, not a timeout kill

- First seen: 2026-04-12 mousepad-loop Round 1 synthesis window
- Bucket: `observability`
- Evidence: the coordinator remained heartbeat-healthy for more than 10 minutes after the last semantic trace event while still presenting no result artifact and no supervisor-visible children
- Risk: binary "healthy vs failed" surfaces force either complacency or premature termination
- Candidate improvement: watchdog evidence lease with `healthy`, `stale_suspect`, `recovery_in_progress`, and `failed_confirmed` conditions
- Status: in progress
- Durability judgment: cross-task

### F-012 — Watchdog ownership must rotate when the active actor changes

- First seen: 2026-04-12 transition from coordinator to Reviewer 1
- Bucket: `runtime`
- Evidence: after the control plane advanced from `coordinator_done` to `reviewer_1_pending`, the watchdog block still pointed at the completed coordinator until explicitly repaired
- Risk: recovery logic can act against the wrong owner token, making the watchdog worse than useless during multi-actor loops
- Candidate improvement: rotate lease epoch and owner token automatically on actor-changing transitions
- Status: in progress
- Durability judgment: cross-task

### F-013 — Observation windows need durable checkpoints, not just live stdout

- First seen: 2026-04-12 Reviewer 2 live observation
- Bucket: `observability`
- Evidence: before the new probe path, a fresh session could inspect Reviewer 2 with `work_scoped_agent.py observe`, but that evidence lived only in transient command output; the persisted control plane still reflected older observation data until manually rewritten
- Risk: resume sessions can make recovery and branching decisions from stale evidence, or re-do the same observation work because the latest runtime state was never committed
- Candidate improvement: checkpoint the observation window structurally with a single probe command that writes heartbeat, progress, child visibility, result path, and watchdog evidence back into manifest + ledger
- Status: in progress
- Durability judgment: cross-task

### F-014 — Stale sessions can replay old branch steps and duplicate actors unless transitions are compare-and-set guarded

- First seen: 2026-04-12 live Reviewer 2 duplication incident
- Bucket: `control-plane`
- Evidence: after Round 1 Reviewer 2 had already been spawned and completed, a second loop-runner session replayed the Reviewer 1 -> Reviewer 2 branch step and spawned another Reviewer 2 into the same round and artifact namespace; the duplicate later terminated cancelled without result
- Risk: split-brain execution, artifact-path collisions, stale-owner confusion, and duplicate work that looks superficially valid because each individual spawn is well-formed
- Candidate improvement: require explicit transition preconditions (expected state plus optional active-subagent / owner-token / ledger-length guards) and claim the next spawn slot in control-plane state before opening a new actor
- Status: in progress
- Durability judgment: cross-task

### F-015 — Round advancement must move round metadata and resume surfaces, not just actor state

- First seen: 2026-04-12 Round 2 coordinator spawn
- Bucket: `control-plane`
- Evidence: the control plane successfully moved from Reviewer 2 continuation into a live Round 2 coordinator, but `current_round`, `current_round_path`, and resume-oriented artifact pointers initially still described Round 1 until explicitly repaired
- Risk: a fresh resume session can land on the right actor but the wrong round packet, mixing active and stale artifacts in exactly the moment where the loop most needs clarity
- Candidate improvement: round/iteration metadata must advance in the same transaction as round spawn, and the resume packet should be refreshed to include the reviewer evidence and new prompt that shaped the active round
- Status: in progress
- Durability judgment: cross-task

### F-016 — Sleep-rule interpretation: "between rounds" is ambiguous and was over-applied

- First seen: 2026-04-12 Round 1 → Round 2 R2-substantial handoff
- Bucket: `loop-design`
- Evidence: The initial user instruction was "Between each round, do a sleep for 30 minutes." The loop runner initialized this as an iteration-log rule stating "30-minute sleep between each round, applies after round N's final reviewer decision." The user's TRANSITION-PROTOCOL.md then refined the rule: the 30-min sleep appears only in the R3-<90% dead-candidate branch, NOT in the R2-substantial branch. When R2 returned "substantial changes" in Round 1, the loop runner started a 30-min background sleep as a round boundary, but the correct interpretation (per TRANSITION-PROTOCOL) was to respawn the coordinator immediately with R2 feedback embedded — no sleep. The control plane advanced to Round 2 coordinator while the sleep was still running. The loop runner's broader interpretation was an over-strict reading.
- Risk: broad operational rules stated at the conversation level may not map to the refined state-machine semantics the protocol encodes. If the loop runner defaults to the broader reading, it will add unnecessary latency at every round boundary — which is exactly the kind of drift the program's architecture-first framing is trying to prevent.
- Candidate improvement: the broader rule should be encoded in machine-readable form in `TRANSITION-PROTOCOL.md` (which it is) and the loop runner should parse the protocol rather than re-derive rules from the conversation. When an instruction references a "round boundary," verify which state-machine edge the instruction applies to before enforcing.
- Status: open (methodology observation, not a runtime fix)
- Durability judgment: cross-task; general lesson about conversation-level rules vs protocol-level rules

### F-017 — Auth token expiry during long coordinator runs needs a distinct recovery path

- First seen: 2026-04-12 Round 2 coordinator failure at T+35 min
- Bucket: `runtime`
- Evidence: Round 2 coordinator (subagent-dffd889d7225) ran for 35 min, completed Phase 1 source-landscape mapping and spawned Phase 2A + 2B, then hit API 401 "Invalid authentication credentials" at turn 21. The coordinator was doing correct methodology work; the failure was infrastructure. The same delegation prompt, re-executed with valid credentials, would resume the same research plan.
- Risk: if the control plane treats infrastructure failures identically to methodology failures (dead candidates), the loop may reroute rather than retry — wasting the good delegation work and potentially introducing condition-change noise when no condition change is needed.
- Candidate improvement: add `failed_infrastructure` as a distinct state in the control plane with recovery path = "retry same delegation." Separate from `reviewer_3_dead_candidate` which means "same direction failed, try different conditions."
- Status: **implemented** — `coordinator_failed_infrastructure` added to KNOWN_STATES and ALLOWED_TRANSITIONS in control_plane.py. Recovery path: → `coordinator_pending` or `coordinator_in_progress` (retry same delegation). Cannot transition to reviewer states (methodology wasn't the failure).
- Durability judgment: cross-task; generalizes to any long-running coordinator subject to auth expiry, rate limits, or transient API errors

### F-018 — Session-coupled supervision is not real supervision

- First seen: 2026-04-12 after the missed Round 2 coordinator auth failure
- Bucket: `control-plane`
- Evidence: the last on-time manual checkpoint was 2026-04-12 02:56:43 +0300, but the coordinator actually failed at 2026-04-12 03:28:07 +0300 with API 401 invalid credentials. The loop remained in `coordinator_in_progress` until a later manual investigation around 10:40 because `probe-active` existed only as a foreground action, not as an autonomous watcher.
- Risk: the loop can present a healthy-looking waiting state for hours after the active actor has already terminated, and no amount of prompt-level "don't idle" text fixes that.
- Candidate improvement: run an external supervisor that observes the active actor on a cadence, checkpoints healthy progress durably, and reconciles terminal states exactly once into explicit control-plane states.
- Status: **implemented for the mousepad loop** — `loop_supervisor.py` now exists, is fixture-tested against the exact stale auth-failure case, is idempotent on already-reconciled terminal states, and uses a filesystem lock to prevent duplicate supervisors. Deployment persistence remains environment-specific because this sandbox reaps shell-backgrounded children.
- Durability judgment: cross-task; any orchestration loop that depends on manual probes is vulnerable to the same stale-wait failure

### F-019 — Timezone misreads can manufacture false stall diagnoses

- First seen: 2026-04-12 Round 2 retry post-hoc diagnosis
- Bucket: `observability`
- Evidence: the Round 2 retry session JSONL used UTC (`Z`) timestamps, but the loop runner read `2026-04-12T08:13:30Z` as if it were `08:13 local` rather than `11:13 +0300`. That produced a false "3+ hours stale" narrative even though the coordinator later completed normally and the external supervisor reconciled it at `2026-04-12 11:22:21 +0300`.
- Risk: operators can convert healthy or recently-active runs into false failure stories, then take destructive recovery actions from a bad diagnosis.
- Candidate improvement: every observation surface that cites session-trace time should either normalize to local time explicitly or print raw UTC plus converted local time side by side. Diagnostic prose should never mention "stale by X" without stating the timezone basis.
- Status: open
- Durability judgment: cross-task; any harness that mixes local-wall-clock supervision with UTC trace artifacts is exposed

### F-020 — Reviewer packets must be rebound after coordinator retries

- First seen: 2026-04-12 Round 2 Reviewer 1 respawn
- Bucket: `control-plane`
- Evidence: the first Round 2 Reviewer 1 packet pointed at the failed attempt-1 coordinator trace (`f80cd254-...`) while the deliverable and captured return being reviewed came from the successful retry (`b812004d-...`). That would have produced an adherence verdict against the wrong execution history.
- Risk: the reviewer chain can certify or reject the wrong coordinator run after infrastructure retries, making downstream branch decisions invalid even when the reviewer itself behaves correctly.
- Candidate improvement: reviewer prompt generation must bind trace/session identifiers from the active coordinator record in the control plane at spawn time, not from an earlier drafted prompt. If a reviewer is invalidated and rerun, give the corrected rerun a distinct artifact path so stale output cannot collide with the authoritative verdict.
- Status: **partially implemented** — the invalid reviewer was superseded, the packet was rebound to the successful Round 2 retry trace, the corrected rerun writes to `round-2/reviewer-1-adherence-respawn.md`, and `control_plane.py validate` now checks reviewer prompt binding when the manifest carries `coordinator_session_id`, `coordinator_trace_jsonl`, and the active reviewer prompt path. Full prevention still requires reviewer prompt generation to consume that metadata automatically at spawn time rather than relying on pre-written files.
- Durability judgment: cross-task; any loop with retries, restarts, or multiple attempts per round needs artifact/trace binding discipline

### F-021 — `blocked` must be a repair junction, not a terminal dead end

- First seen: 2026-04-12 Reviewer 1 invalidation recovery
- Bucket: `control-plane`
- Evidence: once the invalid Reviewer 1 was cancelled, the supervisor escalated the loop to `blocked`. The state machine then refused the legitimate recovery transition back into `reviewer_1_pending` because `blocked` only allowed `blocked` or `cancelled`.
- Risk: the loop can correctly detect a bad actor yet still force out-of-band manifest edits to continue, which defeats the point of having a structural control plane.
- Candidate improvement: allow `blocked` to transition into any explicitly chosen recovery state after investigation, with the actual safety coming from compare-and-set preconditions plus the repair decision itself rather than from a dead-end state restriction.
- Status: **implemented** — `control_plane.py` now treats `blocked` as a repair junction by allowing explicit transitions to any known state.
- Durability judgment: cross-task; recovery states must preserve structural resumability instead of trapping the orchestrator

### F-022 — User-report decisions need their own structural gate

- First seen: 2026-04-12 after an unnecessary progress report during the live program
- Bucket: `control-plane`
- Evidence: the loop already had a structural next-action surface for work execution, but "should I tell the user?" still lived in local judgment plus prose rules. That allowed a mid-run checkpoint to be mistaken for a report-worthy boundary even though the approved protocol was "treat the user as absent unless an extraordinary condition occurs or the full program is meaningfully done."
- Risk: the orchestrator can silently reintroduce user-dependency through status reporting even when it never explicitly asks for input. This is a protocol breach and also a drift vector: report-worthy feeling becomes a substitute for structural stop conditions.
- Candidate improvement: add a separate reporting policy to the manifest, derive contact permission from manifest state plus extraordinary-condition status, expose it via an executable `contact-check` command, and reject any control-plane state that tries to set `next_action.kind=report_to_user` when that gate is closed.
- Status: **implemented in the shared harness and canonical self-improvement harness** — manifests now carry `reporting_policy`, both control-plane helpers derive `contact_permission`, and `contact-check` exists as the preflight gate for any user-facing communication. The mousepad instance uses an empty `terminal_states` list, so ordinary loop milestones never authorize reporting.
- Durability judgment: cross-task; any long-running autonomous loop needs a structural communication gate, not just a work-continuation gate

### F-023 — Observation-file discipline must be scaffolded in the harness, not left as a research-note memory

- First seen: 2026-04-12 comparative merge against the older Claude batch-style mousepad line
- Bucket: `artifact-design`
- Evidence: the older Claude line was materially better at artifact-level legibility during long runs because it explicitly maintained overview, narrative, pre-run intent, and live-observation sections in its run files. The current loop research corpus already contains the lesson ("three output formats" and "artifact is the status surface"), but the reusable harness had no observation-file template or launch-step requiring it. Fresh instances could still omit the structure unless the operator remembered the older methodology notes.
- Risk: long-running loops regress back into either silent execution or undifferentiated narrative dumps, making resume, oversight, and comparison harder even when the runtime control plane is sound.
- Candidate improvement: add an observation-file template to the harness and require it during instance setup so overview, narrative, pre-run intent, and live observations become standard maintained artifacts rather than optional good habits.
- Status: **implemented** — added `harness/OBSERVATION-FILE-TEMPLATE.md` and wired it into `harness/README.md` and `harness/LAUNCH-TEMPLATE.md`.
- Durability judgment: cross-task; any long-running self-improvement loop benefits from a reusable observation-file scaffold

### F-024 — Stale-session replay recurred despite compare-and-set guards when manifest was modified externally

- First seen: 2026-04-12 during mousepad-loop comparative stream + harness-generalization-loop R1→R2 handoff
- Bucket: `control-plane`
- Evidence: a fresh session read the harness-generalization manifest at `reviewer_1_pass` (which it had set via a transition), then attempted to spawn Reviewer 2. Meanwhile, a prior session had already advanced the manifest to `reviewer_2_pending` and spawned R2 with a different subagent-id. The fresh session's spawn created a duplicate R2 (`subagent-8380921889e9`) that had to be cancelled. The compare-and-set guard caught the stale state on the transition attempt, but the spawn happened via `work_scoped_agent.py spawn` which does not check control-plane state.
- Risk: spawning an actor is a side-effecting operation that cannot be un-done by a rejected transition. If the spawn happens before the transition, the guard fires too late.
- Candidate improvement: the spawn-slot claim pattern (transition first, spawn second) must be enforced in the loop runner's operational sequence, not just documented. The claim-before-spawn discipline exists in the methodology log, but the fresh session did not follow it because it read a manifest snapshot and assumed it was authoritative.
- Status: open; discipline enforcement, not a code fix
- Durability judgment: cross-task; any multi-session orchestration system where spawning is decoupled from the state machine

### F-025 — R2 "substantial changes" on code/architecture tasks can identify bounded, precisely scoped fixes

- First seen: 2026-04-12 during harness-generalization-loop Round 1 R2 review
- Bucket: `reviewer-structure`
- Evidence: R2 identified four substantial changes, all concretely bounded. S1 and S2 are specific hardcoded patterns with exact file/line references. S3 and S4 are structural design choices with clear fix shapes. R2 explicitly predicted that S1+S2 fixes alone would bring the verdict to "only minor changes remain." This contrasts with the mousepad R2 (Round 1), which identified a broad source-landscape gap requiring a methodology restructure.
- Observation (not inference): code/architecture tasks produce more precisely scoped R2 feedback than research-synthesis tasks. The feedback-to-fix path is shorter and more deterministic.
- Risk: none identified — this is a positive observation about R2 operating well on a different task class.
- Durability judgment: cross-task; evidence about R2 reviewer behavior across task classes

### F-026 — Comparative-stream analysis reveals that independent parallel investigation predictions align well with what was actually built

- First seen: 2026-04-12 during mousepad-loop comparative stream
- Bucket: `artifact-design`
- Evidence: the Codex parallel investigation (pre-harness, independent assessment) identified 8 gaps. Of these, 4 were fully addressed, 2 partially addressed, 1 unaddressed, and 1 confirmed as a positive finding — without the harness builder having read the Codex assessment. The strongest unaddressed gap (loop-governance rubric) was also the Codex's most structurally distinct proposal (the others overlapped with the control-plane work the harness naturally produced).
- Observation: parallel independent investigation produces actionable gap-finding even when the main line converges without consulting it. The value is in identifying structural blind spots the main line naturally skips.
- Status: observation; the governance-rubric import has been partially applied to the R2 template
- Durability judgment: cross-task; evidence for the value of parallel independent investigation streams in iterative improvement programs

### F-027 — Fresh-mode parent/child coordination is safe when descendants are supervisor-visible and joined

- First seen: 2026-04-12 during harness-generalization-loop Round 2 live observation
- Bucket: `runtime`
- Evidence: the round-2 coordinator (`subagent-07b136a2bfaf`) spawned verifier child `subagent-764992d87d90` as a runtime-visible descendant. The parent then transitioned to `waiting on joined child` rather than finishing its turn or relying on invisible background notifications. `work_scoped_agent.py observe` showed `child_states={"subagent-764992d87d90":"running"}` and the parent remained healthy with fresh heartbeat/progress while waiting.
- Risk if absent: fresh-mode coordinators can recreate the earlier deadlock pattern by farming work to invisible background agents and then collapsing before results arrive.
- Candidate improvement: prefer joined descendants for verifier or decomposition work inside fresh mode; make supervisor-visible child state part of the standard observation and checkpoint surface.
- Status: **verified in live run** — this is the positive counterpart to the earlier failure case, and it shows the runtime can structurally preserve parent liveness while child work is still active.
- Durability judgment: cross-task; any fresh-turn orchestration runtime needs observable joined-child waiting semantics to support safe delegation

### F-028 — R2 "minor" and R3 "fail" can evaluate the same residual differently — and both be correct

- First seen: 2026-04-12 during harness-generalization-loop Round 2 reviewer chain
- Bucket: `reviewer-structure`
- Evidence: R2 classified the `validate()` artifact-key hardcoding (`coordinator_return_capture`, `coordinator_artifact`) as minor item M1 because it "produces warnings only when those keys exist, so it can't break non-mousepad instances." R3 scored the same item as a structural contamination failure contributing to an 82% score (below 90% threshold), because the task-finish condition asks whether the harness can support non-mousepad instances "without relying on mousepad-specific control-plane state wiring" — and the hardcoded keys are mousepad-specific wiring by definition.
- Root-cause analysis: R2 and R3 are asking different questions. R2 asks "what would a professional team still change?" (quality lens — is this a big deal to fix?). R3 asks "does this meet the task's finish condition?" (threshold lens — is this residual compatible with the stated standard?). A one-line fix can be minor from a quality perspective yet load-bearing from a threshold perspective. Both assessments are correct for their respective lenses.
- Risk: the loop runner may be surprised when R2 passes and R3 fails on the same round, creating a false impression of inconsistency. The reviewer chain is working as designed — R2 gates on effort remaining, R3 gates on standard achieved.
- Candidate improvement: when R2 identifies minor items that touch the task-finish condition's core criterion, flag them explicitly as "minor to fix but potentially threshold-relevant" so the loop runner and coordinator don't treat R2-pass as a strong predictor of R3-pass.
- Status: observation; no code fix needed, but worth awareness for future loop runners
- Durability judgment: cross-task; any two-stage quality-then-threshold review chain can exhibit this divergence

### F-029 — A self-improvement loop can be trapped in path-improvement mode while still looking rigorous

- First seen: 2026-04-12 during harness-generalization-loop Round 2 -> Round 3 transition
- Bucket: `loop-design`
- Evidence: Round 2 had a live joined-child verifier, passed Reviewer 1, passed Reviewer 2, and still failed Reviewer 3 at 82% because the work stayed inside the current abstraction basin and missed one residual shared-runtime blind spot. The loop was active, artifact-rich, and reviewer-governed, but the remaining work required reopening the path, not just polishing inside it.
- Root-cause analysis: reviewer structure and artifact discipline are necessary but not sufficient. A loop can have strong local rigor while still failing to challenge the governing frame that shaped the local work. The failure mode is not sloppiness. It is basin lock-in.
- Risk: operators may mistake high local rigor for high global search quality. The loop can appear professional while still failing to evaluate nearby alternative basins.
- Candidate improvement: make anti-rigidity structural. Round briefs should name path-lock risk, builders should surface alternatives considered, reviewers should explicitly judge whether the strongest remaining improvement would reopen path selection itself.
- Status: promoted into the self-improvement-harness docs via `anti-rigidity.md`, template updates, and rubric imports
- Durability judgment: cross-task; any iterative improvement loop that reuses prior-round ontology is exposed

### F-030 — Prompting for flexibility is weaker than explicit perturbation operators

- First seen: 2026-04-12 after reviewing the cognitive-rigidity import against the live harness behavior
- Bucket: `loop-design`
- Evidence: the existing harness already contained broad exhortations toward rigor and reviewer independence, yet the observed failure mode remained path lock-in. The missing element was not more encouragement to think broadly. It was a required mechanism for surfacing alternate framings and breaking out of the current basin when fixation signals appeared.
- Root-cause analysis: an agent inside a frame is poorly positioned to escape that frame using more of the same reasoning. The effective interventions are external perturbations: alternate framings, assumption surfacing, pre-mortems, orthogonal verification surfaces, and fresh independent branches.
- Risk: if anti-rigidity remains a stylistic preference, stronger agents may still get trapped by the first viable path while believing they are evaluating broadly.
- Candidate improvement: encode anti-rigidity into round briefs, builder outputs, reviewer templates, and future control-plane surfaces rather than leaving it as prompt advice.
- Status: promoted into the self-improvement-harness docs and process-observation rubric; future control-plane instrumentation remains open
- Durability judgment: cross-task; any agentic system vulnerable to premature closure or fixation benefits from explicit perturbation operators

### F-031 — Reviewer context isolation is not the same as evaluation independence

- First seen: 2026-04-12 during MD review of the harness-generalization convergence claim
- Bucket: `reviewer-structure`
- Evidence: all three reviewers are spawned as fresh-mode agents with no shared context — structurally isolated. However, the evaluation instruments have different provenance:
  - R1 uses `process-observation-rubric.md`, a pre-existing maintained artifact authored before the loop. This is genuinely independent criteria.
  - R2 uses a template-level professional-team benchmark question. Context-isolated, but the evaluation frame (what to review, what code to inspect, what "trying to achieve" means) is authored by the loop runner into the delegation prompt.
  - R3's 5-criterion scoring reference (shared runtime decoupling, non-mousepad path, validation reality, compatibility, residual contamination) and the 20-points-each weighting were composed during instance setup — not from a pre-existing rubric. The loop runner authored both the work direction and the scoring instrument.
- Root-cause analysis: the system provides structural independence (context isolation) but not methodological independence (independently designed evaluation criteria). The loop runner controls what the reviewer sees, what question it answers, and what scoring frame it uses. For R1, this is mitigated by the pre-existing rubric. For R3, the scoring criteria and the work direction share the same author.
- Contrast: the mousepad loop's R3 had stronger methodological independence because the scoring reference (Scarab experiential definition) came from the human principal — genuinely external to the loop. The harness-generalization R3 criteria did not.
- Risk: a loop can produce numerically clean convergence (92% PASS) while the evaluation frame was shaped by the same system that produced the work. The numbers are real (the reviewer genuinely scored from fresh context against the provided criteria), but the criteria themselves were not stress-tested for whether they're the right criteria.
- Candidate improvement: for task-finish conditions, the scoring reference should come from or be approved by a source external to the loop runner — either the human principal, a pre-existing maintained rubric, or an independently authored evaluation frame. Loop-runner-authored R3 criteria should be explicitly marked as "self-authored scoring reference" so future sessions and human reviewers know the independence boundary.
- Status: observation; applies retroactively to the harness-generalization convergence claim
- Durability judgment: cross-task; any reviewer-governed loop where the same agent designs both the work and the evaluation criteria has this structural gap

### F-032 — Reviewer output-path mismatches are a silent handoff failure class

- First seen: 2026-04-12 during planner-builder-evaluator Round 1 reviewer handoff
- Bucket: `control-plane`
- Evidence: the live manifest initially bound reviewer outputs to `reviewer-1-adherence.md`, `reviewer-2-quality.md`, and `reviewer-3-task-finish.md`, while the actual reviewer prompts instructed `reviewer-1-output.md`, `reviewer-2-output.md`, and `reviewer-3-output.md`. The reviewer could therefore finish correctly and still look missing to the orchestrator.
- Risk: false-negative capture. A correct reviewer return becomes invisible because the parent is watching the wrong artifact path.
- Candidate improvement: treat reviewer output locations as control-plane-owned bindings. Prompt generation should derive them from manifest artifact keys, and validation should reject prompt packets whose instructed output path disagrees with the bound artifact path.
- Status: **mostly implemented** — reviewer artifact bindings were normalized to `reviewer-N-output.md`, strict prompt-binding enforcement now blocks active reviewer states whose prompt omits the bound output artifact, and prompt-binding valid/violation fixtures now prove the guard. Full prompt-generation-from-manifest remains open.
- Durability judgment: cross-task; any reviewer chain with separately authored prompts and manifest bindings is exposed

### F-033 — Observation windows need a first-class semantic status, not just watchdog condition

- First seen: 2026-04-12 during planner-builder-evaluator Round 1 reviewer wait plus trace-audit branch
- Bucket: `observability`
- Evidence: the branch could prove reviewer liveness through heartbeat/progress and supervisor probes, but before the control-plane patch it could not state whether the active reviewer was reasoning, waiting on a child, or merely alive. The new `observation_window` block now carries `status`, `observed_at`, `progress_at`, `artifact_delta_at`, `child_states`, `blocker_class`, and `evidence_tail_ref`.
- Risk if absent: long waits look semantically blank, which encourages either complacency or premature stall diagnosis without a shared vocabulary.
- Candidate improvement: keep `watchdog.condition` for lease/recovery health and use `observation_window.status` for semantic waiting/reasoning state. Extend later with `waiting_on_io` and deeper semantic-event capture.
- Status: **implemented in shared and live control-plane copies** for the planner-builder-evaluator branch; broader harness rollout remains open.
- Durability judgment: cross-task; any long-running orchestrator or reviewer wait benefits from separate health and semantic-status surfaces

### F-034 — Saturation needs control-plane accounting of directions, not prose claims

- First seen: 2026-04-12 during the planner-builder-evaluator widening branch and compute-saturation side investigation
- Bucket: `loop-design`
- Evidence: the side investigation converged on a strict requirement: a direction only counts if it has a distinct surface, objective, stop condition, write target, and persisted manifest/ledger record. This matches the repeated live failure mode where prose claimed "parallel work" that did not yet exist as trace-backed state.
- Risk: the loop can believe it is using four directions while actually running one main branch plus commentary about future branches.
- Candidate improvement: add a `saturation` block plus per-direction records to the control plane, and make branch-open operations claim a slot in state before any spawn.
- Status: design complete in `compute-saturation-enforcement-design.md`; not yet implemented in the harness control plane.
- Durability judgment: cross-task; any autonomy loop that wants compute saturation without fake parallelism needs this accounting

### F-035 — Resume packets drift unless they are generated from control-plane truth

- First seen: 2026-04-12 during the canonical self-improvement-harness review loop, then re-confirmed while repairing the active Delve instance
- Bucket: `control-plane`
- Evidence: multiple branches accumulated stale human-written resume surfaces after real state transitions. The canonical harness explicitly failed reviewer checks when `CONTINUATION.md` still described a builder phase after the manifest had advanced to reviewer ownership. The Delve instance separately carried stale surrounding surfaces even though the manifest already encoded the correct Round 6 next action.
- Risk: a fresh resume session can follow the wrong branch, re-run exhausted work, or miss the authoritative next action even when the manifest and ledger are already correct.
- Candidate improvement: make the continuation packet a derived artifact owned by the control plane. Mutating control-plane commands should regenerate `CONTINUATION.md`, and fresh-session handoff rules should tell resumptions to read that generated packet instead of reusing the fresh-launch template.
- Status: **implemented in the shared harness source** — `phase-2-runs/harness/control_plane.py` now supports `refresh-continuation` and regenerates `CONTINUATION.md` on mutating writes. Broader rollout to copied instance-local control-plane files remains open.
- Durability judgment: cross-task; any long-running autonomy program with handoffs or resumed sessions is exposed

### F-036 — Blind-evaluation packet integrity is load-bearing, not clerical

- First seen: 2026-04-12 during the Delve writing loop Round 7 closure
- Bucket: `evaluation-protocol`
- Evidence: the first mixed-backend Round 7 reviewer batch used a prompt packet that exposed the mapping between `A/B` and real/generated chapters. That contaminated batch unanimously read as negative and would have pushed the loop toward an unnecessary Round 8 recovery branch. After replacing it with protocol-valid randomized unlabeled trial packs, the authoritative 10-trial panel finished at `4/10 correct`, which satisfied the task stop condition. The leaked packet and the valid packet did not merely differ in confidence. They differed in direction.
- Root-cause analysis: "blind review" is not guaranteed by reviewer freshness alone. Packet construction is part of the evaluation mechanism. If the candidate/authentic mapping leaks through filenames, prompt text, or fixed placement, the evaluator is no longer testing the intended question.
- Risk: loops can spend additional rounds "fixing" a task that has already crossed its threshold, or can learn from contaminated evaluator commentary as if it were score-valid evidence.
- Candidate improvement: generate blinded trial packs mechanically, write unlabeled `chapter-a.md` / `chapter-b.md` copies, keep the hidden mapping in separate metadata, and record contaminated shadow reads explicitly as non-scoring.
- Status: **implemented at the Delve-instance level** via `round-7/make_trial_pack.py`, repaired prompt packets, and `round-7/trial-ledger.md`; shared-harness promotion remains open.
- Durability judgment: cross-task; any blind comparison, adversarial review, or A/B evaluation loop is exposed
