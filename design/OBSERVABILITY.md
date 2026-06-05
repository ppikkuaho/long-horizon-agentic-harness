# AI Architecture — Observability and Audit System (Process Design)

Process design document. Defines how system activity is recorded, traced, measured, and visualized for evaluation and improvement. Constrained by: ARCHITECTURE.md, DESIGN-PRINCIPLES.md (especially P11: Observability Without Disruption). Feeds the Improvement Workspace system-improvement workspace (see IMPROVEMENT-WORKSPACE.md) and, in the future, an optimizer-L1 capability that may operate out of that workspace. It is the measurement substrate behind the anti-drift mechanism in PLAN-ALIGNMENT-GATE.md and QUALITY-GATE.md.

---

## 1. Design Motivation

The system must be observable to be improvable. Both the user and the system-improvement function (in the future, optimizer-L1 operating out of the Improvement Workspace) need to evaluate how runs went, identify bottlenecks, measure drift, and propose improvements. The user needs to understand the system directly — not just trust reports.

Inspired by model train observation: being able to watch the system work is the foundation for understanding and improving it. If you can't see it, you can't fix it. If the system only reports summaries, the user loses the ability to form independent judgments about what's working and what isn't.

Observability is not monitoring. Monitoring asks "is it broken?" Observability asks "how is it working, and could it work better?" The system is designed for the second question.

**The #1 thing this system measures is drift — spec-faithfulness across the planning and execution cascade** (J43). Execution quality (speed, token cost, elegance) is measured too, but its optimization is explicitly deferred: drift is the dominant failure class because the cascade is a chain of translations (intent → minted requirement-IDs → L2 architecture → L3 designs → L4 plans → L5 code), each performed by a different agent, and local fidelity at every step does not compose into global fidelity to intent. The observability stack therefore treats every measurable seam in that chain as a drift-verification surface first, and a performance surface second. PLAN-ALIGNMENT-GATE.md is where drift is *caught at plan-time*; this document is where drift is *measured continuously across runs* so the system-improvement function can spot the recurring patterns the per-run gate cannot.

## 2. Audit Event Log

Infrastructure-produced structured data. Every infrastructure action emits an event:

- **Spawn events** — who spawned who, at what address (workspace node path + role-variant, e.g. `proj/payments/gateway#exec` — see F35 in WORKSPACE-SCHEMA.md), with what brief, session_id
- **Communication events** — bus messages between nodes, escalations (L5→L4 ambiguity raises), gate submissions. Per F33/COMMUNICATION.md the bus is the real-time transport and docs are the durable truth, so a comms event records the *pointer/nudge* and the doc it points at, not the payload; best-effort delivery is acceptable because the truth lives in the doc.
- **State transitions** — working, waiting, idle, dead, collapsed, resurrected
- **Gate outcomes** — the plan-alignment gate verdict and per-check defect lists (Check 0 atomization, forward/backward coverage, two-window reconstruction, adversarial drift findings — see PLAN-ALIGNMENT-GATE.md); per-level right-arm review gate outcomes (dimensions reviewed, pass/bounce, bounce reasons, bounce-count toward the loop cap)
- **Drift / spec-faithfulness signals** *(the #1 measured thing, J43)* — every emitted **trace-block** (each level tagging the requirement-IDs it serves), the generated RTM snapshot, atomization (`UNMINTED`) findings, semantic-drift findings (`DRIFT` / `SILENT-ASSUMPTION` / `SCOPE-SHIFT`), `TEST-DESIGN-SPLIT` two-window disagreements, and acceptance-test pass/fail against the **frozen, read-only acceptance artifact** (D26) in each work node. These are the raw rows from which spec-faithfulness is computed.
- **Resource usage** — time, token consumption, spawn count, bounce-loop count
- **File modifications** — linked to session_id and tool_call_id via manifest

No agent involvement required. Spawn/collapse/comms **transitions** are captured **deterministically** by hooks on infrastructure operations (spawn script, bus/communication layer, the return-contract/preflight hook that enforces trace-block emission, PostToolUse hooks on Edit/Write). The **working/idle** liveness state is not self-reported and not directly observable, so it is **inferred with bounded confidence** from floor signals — transcript-JSONL growth, tmux pane activity, node-file mtime, and process CPU. Agents don't decide what to log — the infrastructure logs everything by default.

Events are structured (JSON or similar), timestamped, and keyed by session_id and by node address. They form the raw data layer that feeds the narrative timeline, the drift metrics, and the system-improvement analysis. Because addresses, requirement-IDs, workspace paths, git branches, rubric locations, and the visibility graph are all the **one hierarchical-path spine**, every event is filterable by dotted-ID prefix — the same key the gate uses for subtree re-gating.

## 3. Narrative Timeline

Human-legible structured log of the run. Self-contained — readable without drilling down into transcripts or artifacts.

**Format:**
- Grouped by acting entity (L2-game, L3-dialogue, L4-branching, L5-implementation, Gate-L4, etc.)
- Action-first, timestamps at the end
- Decisions include reasoning
- Multi-line entries when needed for detail

**Example:**

```
L2-game
  Received brief: implement dialogue system                                    [14:23]
  Analyzed scope. Identified 3 workstreams: dialogue branching,                [14:24]
    NPC responses, save/load integration
  Chose approach: tree-based dialogue graph over linear scripting.              [14:24]
    Reasoning: supports non-linear player paths, extensible for
    future quest system integration
  Spawned L3-dialogue to own dialogue area (workstreams 1+2)                  [14:25]

L3-dialogue
  Loaded. Read project state and L2 brief.                                     [14:25]
  Scoped area. Identified 2 workstreams: branching engine, NPC responses       [14:25]
  Spawned L4-branching for workstream 1                                        [14:26]

L4-branching
  Loaded. Read area state and L3 brief.                                        [14:26]
  Decomposed into 4 tasks                                                      [14:26]
  Spawned L5-branching-core for task 1                                         [14:27]

L5-branching-core
  Started. Chose recursive tree with typed condition nodes.                     [14:27]
    Considered flat lookup table, rejected — poor extensibility
  Implemented core tree. 412 lines, 3 test files, 14 assertions passing        [14:32]
  Flagged concern: no circular reference detection                             [14:32]
  Reported to L4-branching: complete with concern                              [14:33]
```

The narrative can be produced incrementally during the run (agents append as they work) or synthesized after the fact from the audit event log and workspace artifacts. Filterable by entity — read just what L4-branching did, or the full interleaved timeline.

The key property: someone reading only the narrative should understand what happened, why decisions were made, and what was produced — without opening a single transcript.

## 4. Traceability Chain

Four layers, all cross-linked by session_id:

1. **Narrative timeline** — what happened, readable, self-contained. The entry point for understanding any run.
2. **Workspace artifacts** — what was produced (plan.md, report.md, code files). The tangible output of each agent's work.
3. **Edit manifest** — links each file edit to the exact session_id + tool_call_id. Produced by PostToolUse hook on Edit/Write. One entry per edit, so living documents (like plan.md rewritten across multiple sessions) have full edit history.
4. **Session transcripts** — full thinking traces (.jsonl archives). The raw reasoning behind every decision and action. The deepest layer, used only when you need to understand exactly why something happened.

Each layer links to the next: the narrative references artifacts by path, the manifest maps artifacts to session + tool_call, session transcripts contain the full context for each tool_call_id.

Git commits also carry session_id in trailers, connecting code changes to the agent that made them. This means `git log` and `git blame` participate in the traceability chain — you can trace a line of code back to the agent session that wrote it. Because git branches share the one hierarchical-path spine with agent-addresses and requirement-IDs, a branch name *is* a node address and a requirement-ID prefix.

## 4.1. The 2-Week Resurrection / Audit Window (G37)

When a node completes its unit of work (acceptance accepted, forwarded upward), it **collapses** to free context — statelessness is the backstop, persistence is an optimization (G38). But a collapsed node is not immediately reaped. For **2 weeks** its full state — frozen brief, frozen acceptance artifact (D26), report, transcript, edit-manifest slice, and trace-blocks — is held resurrectable in the work node, keyed by its stable address (which survives collapse, F35).

**"Resurrected" ≠ "recovered" (distinct layers).** *Resurrected* is this audit-layer concept: bringing a **collapsed** node back within the 2-week window for replay/interrogation/re-run, post-collapse and after its work is done. It is NOT WATCHDOG's live-run **recovered** outcome (renew / adopt / respawn a stale-or-dead lease back to healthy during an in-flight run, see WATCHDOG.md). Keep the two words for the two distinct things: recovered = live-run lease recovery; resurrected = post-collapse audit re-spawn.

This window exists to serve the audit and improvement layer, not the run:

- **Read-only replay** — the default. The narrative timeline, diagram replay, and drift metrics for that node are reconstructable from the held state without re-spawning anything. This is what the user and optimizer-L1 do most of the time: look back at how a now-collapsed node worked.
- **Live re-spawn** — a collapsed node can be brought back at its address with its exact frozen context, for interrogation ("why did L5-stripe-client choose this?") or to re-run a unit after an upstream fix without re-planning from scratch.
- **Re-run** — re-execute the unit against its unchanged frozen acceptance artifact, e.g. to confirm a drift finding reproduces or that a bounce-fix actually closed it.

**Who triggers reap:** after 2w the lifecycle reaper (infrastructure, not an agent) garbage-collects the resurrectable state; whatever the audit layer needed has by then been distilled into the durable narrative + drift metrics, which persist. The user (or, in the future, an optimizer-L1 capability operating with god-view) can pin a node to extend its window when a run is under active investigation. This window is the live feed into the audit layer below: the freshest, highest-fidelity material for drift analysis is whatever collapsed in the last 2 weeks.

## 4.5. Client-Side Prompt Assembly Oracle

For Claude/Codex-style runtimes, the cleanest client-side answer to "what did the model actually see?" is the final outbound request payload at the last query boundary before the API call.

This surface is more reliable than:

- UI rendering of hidden context
- transcript-side attachment display
- model self-report about what it can "see"
- reconstructed summaries of prompt assembly

Those surfaces are still useful diagnostics, but they are downstream views. The outbound request payload is the direct evidence of what the client actually sent.

Operationally, this means the observability stack should prefer:

1. final outbound request payload capture
2. prompt-assembly summary/debug rows
3. UI rendering and transcript inspection
4. model self-report

When debugging runtime context issues, capture the payload first and treat it as the primary oracle. Everything else is supporting evidence.

For Claude specifically, a useful pattern falls out of this:

- keep human interaction on a PTY/control wrapper if needed
- give agentic/LLM control a transcript-backed spawn/resume surface keyed by session id
- capture the outbound request payload for each managed turn at the shared query boundary

That combination lets the system self-iterate on runtime bugs without relying on model self-report or manual UI probing.

## 5. Dual Consumer Design

Same data, two consumers with different approaches:

**User** reads the narrative timeline and diagram replay to understand and evaluate. Drills down through the traceability chain when something looks wrong or interesting. Proposes improvements based on observation — "I watched L5 spend too long on X, we should restructure the brief" or "the gate is rejecting too aggressively on dimension Y."

**The system-improvement function** (in the future, an optimizer-L1 capability running out of the Improvement Workspace — see §6) reads the structured event log and drift signals to systematically analyze patterns. Computes metrics (spec-faithfulness/drift rates first, then time-per-task distributions, gate defect rates, bounce-loop counts, spawn-depth patterns). Proposes improvements based on data — "atomization (`UNMINTED`) findings cluster on compound must-never-fails, so the intake MNF-decomposition prompt is leaking" or "two-window `TEST-DESIGN-SPLIT` disagreements drop 40% after adding the acceptance-test template."

Both can propose improvements. Neither can implement them unilaterally. **All system changes require human approval — the system proposes, the human disposes** (QUALITY-GATE.md: an LLM modifying its own quality criteria is a self-referential loop that could drift standards). The two perspectives complement: the user catches things that feel wrong, optimizer-L1 catches things that are statistically wrong.

## 6. System-Improvement Audit Layer (I42)

**Important framing:** The Improvement Workspace (IMPROVEMENT-WORKSPACE.md) is the place where system observations land, patterns get logged, and improvement proposals get drafted. It is a workspace, not an agent. An **optimizer-L1** capability — a standing self-improvement agent with a god-view over the whole system — is a **separate, future concept** that may eventually operate out of that workspace. It is not a V1 deliverable. This section describes what that future capability would look like on the observability side; for V1 the audit layer is driven by the user and by whatever structured analysis is done within the Improvement Workspace manually or semi-manually.

The audit layer is **not** a passive metrics-reader bolted onto the side. It is a **first-class** function: a self-improvement capability with a god-view over the whole system and its own development methodology for proposing interventions. It is the second consumer above, but its role is substantial enough to warrant its own design treatment — not a standing organizational unit running alongside the levels, just a capability that reads across the whole tree and proposes. (The full design for optimizer-L1, when it is built, will live in a dedicated `OPTIMIZER-L1.md`; for now the Improvement Workspace is its holding location.)

**God-view, read-only by default.** Unlike ordinary nodes, which see only their need-to-know slice of the visibility graph (subtree + same-parent siblings + parent — F34), the audit layer reads the *whole* tree: every node's events, every trace-block, every gate defect, the full narrative and drift metrics across all runs. Its god-view is **read-only to the running system** — it observes and proposes, it does not edit live work — and write access is reserved for human-approved methodology changes, never unilateral self-modification (closes the self-referential loop QUALITY-GATE.md warns about). The 2-week window (§4.1) is its freshest input feed; the durable narrative + drift metrics are its long-horizon, cross-run feed.

**Drift is its primary target** (J43). The audit function's first job is not performance tuning; it is watching spec-faithfulness across the cascade — where `DRIFT` / `SILENT-ASSUMPTION` / `SCOPE-SHIFT` / `UNMINTED` / `TEST-DESIGN-SPLIT` findings recur, which translation seams leak most, whether a given level systematically drops or invents requirement-IDs. Execution-quality optimization (speed, token cost) is explicitly second — a later phase, after the verification loop is trusted.

**It monitors recurring issues across runs.** The per-run plan-alignment gate catches drift *within* a single plan; the audit function catches the *pattern across many plans* — the failure mode the gate structurally cannot see because each gate run starts clean. A single `UNMINTED` finding is a defect the gate routes to the human; the same finding recurring on every payments-shaped intake is a methodology bug the audit function surfaces.

**It has its own development methodology** — the structured-iteration loop from the `ai-driven-autonomous-iterative-improvement/` investigation, which this section binds to directly. The mechanics it inherits:

- **Structural changes over instruction tweaks.** Empirically, adding instructions ("also check X") produces shallow compliance; changing the *process architecture* (a separate gap-analysis agent, reordering plan/execute, renaming a section to scope its content) produces real improvement. The audit function proposes *structural* interventions to the architecture's own process, not more prose in briefs.
- **Builder/tester/evaluator separation.** The agent that proposes a fix systematically under-detects failures in its own fix; an independent evaluator with only the rubric cannot rationalize borderline results. The proposing seat is separate from the testing seat and the evaluation seat — never one agent grading its own change. (This is the same anti-self-grading discipline the gate and the right-arm reviews enforce on object-level work, applied to meta-level work.)
- **The generalizability gate before any fix lands** — root-cause-not-symptom, works-across-domains-not-just-the-observed-run, prescribes-a-mechanism-not-specific-content, compatible-with-deployment. One skipped check is one wasted intervention cycle.
- **Drift as the optimization signal.** Because the loop optimizes for whatever it measures, and the #1 measurement is spec-faithfulness, the intervention loop is pointed at closing drift first; performance metrics enter only once drift is under control.

**The intervention always returns to the human.** The audit function produces a proposed structural change + the cross-run evidence that motivates it + the test/evaluation result of trying it on held run-data. That package goes to the user for disposition. The autonomy is in the *detection and design* of interventions, not in their adoption.

The user is the seat for *judgment*; the audit function is the seat for *statistics*. Per the model-perspective rule, the pedantic, recurring-pattern-counting reading is a natural GPT-5.5 (Codex harness) job, while the methodology-design and structural-intervention proposing — generative, architectural — leans Opus 4.8; in practice the loop uses both, mirroring the gate's atomization-auditor-on-both-models pattern (PLAN-ALIGNMENT-GATE.md). When optimizer-L1 is eventually built, it will occupy this seat with a dedicated agent design; until then, this analysis is done by the user working within the Improvement Workspace.

## 7. Human-Gate Health Monitoring

The one checkpoint no machinery beneath it can replace is the human sign-off at the plan-alignment gate (PLAN-ALIGNMENT-GATE.md §Human Sign-off). It is also the one that silently degrades: a human signing off on warm diffs across many runs can drift toward "looks right, approve," and a rubber-stamping human nullifies the system's entire anti-drift promise no matter how good the machinery below them is. This is named in that doc as the single biggest residual; the observability stack is where it is *instrumented*.

Two proxies are tracked per gate run, because they are the only observable signals that the irreducible gate is still real:

- **Sign-off dwell time** — how long the human actually spends on the sign-off package (not just elapsed wall-clock; engaged-attention time on the playback, findings ledger, and force-expanded MNF roster).
- **Expansion rate on flagged / force-expanded items** — what fraction of the flagged drift items, residual judgment calls, and force-expanded must-never-fails the human actually opens and inspects versus approves collapsed.

A collapse in either (dwell time trending to near-zero, expansion rate falling toward "approve everything without opening") is surfaced as a warning that the human gate may have gone slack. Per the resolved gate open-question 3, the **response is surface-only**: point it out to the user, no forcing, no override, respect autonomy. A passive feed also goes to the system-improvement workspace (and, in the future, to an optimizer-L1 capability) so cross-run degradation patterns can be spotted (e.g. dwell time decaying steadily over a project's gate runs) — pattern-spotting, again never automated intervention.

This monitoring deliberately produces **no automated alignment score** and no "human reliability score." It is an honest residual instrument: the one observable proxy for the failure mode that lives above all the system's machinery, surfaced so a human can notice their own drift, not a number that launders the judgment call away.

## 8. Three Visualization Layers

Three views, one data layer, different cognitive purposes:

**1. GUI room view** — live operating interface. Navigate between agents, engage in conversation, manage the system. Answers: "Where do I go, what do I do." The workspace where the user lives during a run. (See GUI-DESIGN.md for full design.)

**2. Diagram / node graph view** — replay and system analysis. Nodes are agents at their addresses, edges are bus communications. Activity pulses through edges as the timeline plays. Scrubbable — drag to any point in the run and see the system state at that moment. Answers: "How is the system working, where are the bottlenecks." Used for post-run analysis and system improvement. Shows spawn trees, communication patterns, time spent, gate interactions, and — overlaid — where drift findings landed on the tree (the diagram is also the drift-map: requirement-IDs are node addresses, so a `DRIFT` finding has a place to render).

**3. Code visualizer** — understand the codebase a project produces. Visualize file structure, module connections, changes made by each workstream. Supplements the diagram by showing what was actually built rather than who built it. Answers: "What did they build, how does it fit together." Useful for understanding whether parallel workstreams produced coherent output.

Each serves a different cognitive need. They complement rather than compete: the diagram shows L5 was active for 5 minutes. The code visualizer shows what L5 produced during those 5 minutes. The GUI lets you go talk to L5 about it. Moving between views is moving between questions — from "how did it go" to "what was built" to "let's discuss it."

---

*Created: 2026-03-17*
*Updated: 2026-06-02 — folded in the 2w resurrection/audit window (G37), the first-class optimizer-L1 audit layer with its own development methodology (I42), drift/spec-faithfulness as the #1 measured thing (J43), and human-gate health monitoring (from PLAN-ALIGNMENT-GATE.md). Aligned to the one hierarchical-path spine, bus+docs comms, and the need-to-know visibility graph.*
*Status: Early design. Narrative format prototyped. Audit event log now specifies drift signals; the system-improvement audit layer is specified on the observability side (IMPROVEMENT-WORKSPACE.md is the system-improvement workspace; optimizer-L1 is a separate future capability whose full agent design will live in a future OPTIMIZER-L1.md). Infrastructure hooks, the 2w reaper, and visualization layers still need implementation design.*
