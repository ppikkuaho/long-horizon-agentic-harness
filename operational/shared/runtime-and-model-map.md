# Runtime & Model Map — Operational Reference

Which model and which runtime each level runs on, and how a parent on one runtime briefs a child on another. Loaded at boot for all levels; consulted by the spawn machinery at every spawn.

The short version: **model + runtime is a per-level, config-time, swappable dimension** — it is not something an agent picks at runtime, and it is not baked into a level's identity. The spawn contract abstracts the runtime; the tool manifest is the only thing that varies per runtime. This is what makes the assignment table below a *configuration*, not an architecture.

*Decisions: E31 (config-time swappable dimension), E32 (cross-runtime brief). Siblings: `agent-definition-principles.md`, `agent-lifecycle.md`, `comms-protocol.md`, `git-protocol.md`. Upstream: `PLAN-ALIGNMENT-GATE.md`, `QUALITY-GATE.md`, `COMMUNICATION.md`.*

---

## Terminology — Codex is a harness, GPT-5.5 is a model

These are two separate dimensions and the docs keep them separate:

- **Runtime** = the *harness* an agent runs inside — its tool surface, its spawn/invocation mechanics, its output format. Today that's the **Claude Code** harness or the **Codex** harness.
- **Model** = the LLM doing the thinking inside that harness — today **Opus 4.8** or **GPT-5.5**.

"Codex" names the harness, never a model — OpenAI no longer ships models called "codex." When a level is described as "Codex + GPT-5.5," that is *harness + model*, two choices, not one. Keep the words straight: a sentence about tool manifests or spawn mechanics is about the runtime; a sentence about reasoning style or where work is generative-vs-pedantic is about the model.

---

## Model + Runtime Is a Config-Time Dimension (E31)

Three properties define how model/runtime is wired in:

1. **Per-level.** Each level has an assigned model and runtime (table below). The assignment is uniform within a level for V1.
2. **Config-time, not run-time.** The assignment lives in the level config and is read by the spawn machinery when a parent spawns a child. **No agent selects its own or its child's model/runtime mid-task.** A parent does not reason about "should this child be Opus or GPT-5.5"; it spawns the child for its level, and the level's config supplies the model/runtime. This keeps model choice out of the per-task decision surface — one less thing for an agent to get wrong, and a knob the system tunes globally rather than ad hoc.
3. **Swappable.** Because the assignment is config and the brief is runtime-neutral (next section), changing a level's runtime is a config edit plus an adapter swap — not a rewrite of the level's role, soul, or brief. The whole reason the brief is split into a neutral contract + a thin adapter is to make this swap cheap. If GPT-5.5 turns out to suit L4 better than Opus, that's a one-line config change and the L4 adapter; nothing about how L4 is briefed changes.

The spawn contract is the abstraction boundary: a parent emits a **runtime-neutral task contract**, and the adapter for the child's runtime turns it into a concrete spawn. The parent never writes harness-specific spawn code by hand.

---

## The Assignment Table (E32)

| Level | Model | Runtime | Why |
|-------|-------|---------|-----|
| **L1** (client interface / intent guardian) | Opus 4.8 | Claude Code | Generative, conversational, judgment-heavy: intake, tradeoff-framing, intent guarding, gate triage. |
| **L2** (architect) | Opus 4.8 | Claude Code | The most generative seat in the system — greenfield architecture, ADRs, carving (`DECOMPOSITION-METHODOLOGY.md`). |
| **L3** (area / module designer) | Opus 4.8 | Claude Code | Domain-deep design, interface renegotiation, pattern application — still generative. |
| **L4** (workstream planner + tester) | **Opus 4.8** | Claude Code | Planning/decomposition is the primary seat; Opus fits. The L4-tester lateral may later be moved to GPT-5.5 based on eval — but V1 default is Opus for the whole level. |
| **L5** (executor) | **GPT-5.5** | **Codex** | Execution: literal, spec-anchored coding against frozen acceptance tests. The pedantic engineering-brain is a fit. |
| **L5+** (reviewer, lateral to L5) | **Opus 4.8** (different runtime from L5) | Claude Code | Independent second reading against spec; placed on a *different* runtime from L5 on purpose — see judgment diversity below. |

**L1–L4 are Opus 4.8 on Claude Code.** These are the generative/architecture/planning seats. **L5 is GPT-5.5 on the Codex harness.** The L4-tester lateral (a separate agent within L4) may later be reassigned to GPT-5.5 based on evals — V1 default is Opus throughout L4.

This table is a config snapshot, not a law. It is expected to move as the system-improvement function (Internal Affairs workspace; in the future, an optimizer-L1 capability — a separate concept from that workspace — will perform this analysis systematically) learns where each model actually earns its seat.

---

## The Model-Perspective Rule (E31/E32)

The assignment isn't arbitrary preference — it follows one rule about where each model is strong:

- **Opus 4.8 → generative / architecture seats.** Greenfield design, decomposition, ADRs, intent elicitation, semantic judgment, reconstructing "what would a system built like this actually do." Work that requires inventing structure from a fuzzy goal.
- **GPT-5.5 → pedantic / adversarial / checking / execution seats.** Literal, engineering-brain, excellent at "name every obligation in this prose that no ID carries," "make these frozen tests pass," "find the case this assertion misses." **Weak at greenfield/architecture** — it will execute a spec faithfully but will *not* fill a gap in the spec with good architecture the way Opus tends to. That weakness is exactly why it's a good fit for seats where filling gaps silently is the failure mode you're trying to prevent.

This rule generalizes beyond the level table. Wherever the system needs a seat — including the **plan-alignment gate** (`PLAN-ALIGNMENT-GATE.md`) — apply it:

- The gate's **atomization auditor** and **adversarial comparator** are pedantic/adversarial → lean GPT-5.5. (The atomization auditor in fact runs on *both* Opus and GPT-5.5 and takes the union: GPT-5.5's pedantry names every uncarried obligation; Opus catches the semantic/intent gaps GPT-5.5 glosses.)
- The gate's **blind reconstruction** ("what would this system do, in the user's language") needs broad intent understanding and the user's own framing → leans Opus.

The rule is the reusable thing; the level table and the gate seating are two applications of it.

---

## The Cross-Runtime Brief (E32)

The architecture is mostly Opus-on-Claude-Code, but L5 is GPT-5.5-on-Codex — so an Opus L4 must brief a GPT-5.5/Codex L5 across a runtime boundary. The design that makes this clean is **hexagonal**: a runtime-neutral task contract is the core; a thin runtime adapter is the port.

### Neutral contract (the core) + thin adapter (the port)

The **semantic brief is identical across runtimes**. It is the agent's actual task and is runtime-agnostic:

- identity (address — workspace node path + role-variant, per F35; see `WORKSPACE-SCHEMA.md`)
- spec (the distilled, pointer-not-payload brief — spec + constraints + interface contracts + the ADRs that carry rationale; raw upstream intent is *referenced*, pullable on demand, not carried)
- the **frozen acceptance/rubric artifact** — read-only to the executor (D26; see `QUALITY-GATE.md`)
- interface contracts
- constraints
- workspace location
- reporting expectations

Only three things are runtime-specific, and the **adapter injects them at spawn**:

- **tool manifest** — which tools this runtime exposes (the Codex tool surface vs. the Claude Code tool surface)
- **harness invocation** — how this runtime is actually spawned/driven
- **output format** — how this runtime returns its result

Swapping a level's runtime = swapping its adapter. The neutral contract — the part a human or a reviewer cares about — does not change. That is E31's swappability, delivered concretely.

### Spawn-failure contract: no silent fallback, deterministic escalation (E32)

The adapter's job is to pin the **configured** model + runtime for the child's level. The failure mode this contract exists to forbid is **silent degradation** — the adapter quietly running the child on something other than what the config specifies and nobody noticing. This is not hypothetical: in the real dry-run a `gpt-5.x` model override was **silently rejected by a ChatGPT-account Codex and fell back** to whatever that account served, and the divergence surfaced only later. That is exactly the failure this contract makes impossible.

**The pinning obligation.** Before the child runs, the adapter must confirm it has pinned the configured model + runtime. The three ways this can fail:

1. **Model unavailable** — the configured model isn't served by the reachable endpoint/account.
2. **Override rejected** — the adapter requested a specific model (e.g. a `gpt-5.x` pin) and the runtime/account refused it or substituted another.
3. **Runtime down** — the harness itself (Codex, Claude Code) is unreachable or fails to spawn.

**Observable behavior on any of the three — deterministic escalation, never fallback:**

- The adapter does **not** spawn the child on a substitute model/runtime. It does **not** "best-effort" with whatever is available.
- It emits a **spawn-failure escalation to L1** carrying: the child's address, the *configured* model+runtime, the *actual* model+runtime the endpoint would have served (or "none — runtime down"), and which of the three failure classes fired. This rides the same escalate-options channel as any block (`agent-lifecycle.md`), but it terminates at **L1** because model/runtime is a config-time, system-level concern, not a per-task one — no intermediate level is authorized to pick a substitute.
- **L1 alerts the user.** The user sees: "could not run `<address>` on its configured `<model>/<runtime>` (reason: `<class>`); the endpoint would have served `<actual>` instead. No work was run on a substitute." L1 does not silently downgrade; the user decides (retry, re-config the level, or accept a different model explicitly).
- A checker can verify the contract held by asserting: for every spawned child, a **`model-used` record** exists in the work node and equals the configured model; any mismatch must have a corresponding L1 spawn-failure escalation and user alert in the trace. A child running on an unrecorded or mismatched model with no escalation is a contract violation.

**The actual model used is always recorded and surfaced.** Every spawn writes the actual model+runtime it ran on into the child's work node (a `model-used` field in the node's metadata/`status.md`), regardless of success or failure. The model in use is **never silently assumed** from the config — config is the *intent*, the recorded `model-used` is the *fact*, and the audit layer (`OBSERVABILITY.md`) can replay which model actually produced any artifact. When they match, that's the normal case; when they can't be made to match, the run does not proceed silently.

### Result-flow is runtime-neutral for free

Results do not need a runtime-specific return channel, because the system already carries truth in two runtime-neutral places (F33; supersedes the old filesystem-inbox model — see `COMMUNICATION.md`):

- **Docs are the durable truth.** Both runtimes write files into the work node (`report.md`, the code, test results). Truth lives in the docs, not in any message.
- **The bus is the real-time transport.** Both runtimes can post a pointer/nudge on the bus. Because the truth is in the docs, bus delivery is **best-effort** — a dropped nudge costs latency, not correctness; the parent re-reads the node.

So "how does a Codex L5 report back to an Opus L4" needs no special machinery: L5 writes its report and results into its work node and posts a bus nudge; L4 reads the node. Free, and identical regardless of which runtime produced the result.

---

## GPT-5.5 Brief Discipline

Briefing a GPT-5.5 child is not the same as briefing an Opus child. GPT-5.5 will faithfully execute what it's given and will **not** paper over an underspecified brief with good architecture. The brief discipline turns that property from a liability into the safety it's meant to be:

- **Maximally decision-complete.** Every decision the executor needs must be *in the brief*. A gap is not an invitation for GPT-5.5 to invent a reasonable answer — it is a hole it will either escalate or stumble on. Brief it as if every unstated assumption is a defect. (This sharpens the general "thin-but-decision-complete" brief rule from `agent-definition-principles.md` for the GPT-5.5 case specifically.)
- **Acceptance tests as the primary anchor.** The frozen acceptance artifact (D26) is the load-bearing definition of "done." For a GPT-5.5 executor, point it at the tests first; the prose spec is context, the tests are the contract.
- **Escalate ambiguity, don't decide it.** The brief must explicitly instruct: when something is ambiguous or missing, **raise it upward, do not fill it**. This makes the L5→L4 escalation channel load-bearing — it's the relief valve that keeps GPT-5.5's literalness from turning into silent wrong guesses. (`COMMUNICATION.md` carries the escalation payload format.)

### Judgment diversity: L5+ on a different runtime

The **L5+ reviewer runs on Opus (Claude Code), a different runtime from the L5 it reviews.** This is deliberate: an independent reading against spec is worth more when it doesn't share the producer's blind spots, and two different models share fewer correlated failure modes than two instances of one. The same logic seats the gate's reconstruction/adversarial roles across models (above). Where the architecture has a checker reading a producer's output, prefer a *different* model on the checking seat.

---

## L4/L5 Codex-Audit Checklist (neutralize Claude-isms)

L5 (and any other Codex-runtime level) runs on a harness that does **not** carry the Claude base prompt and was not written with Claude's instruction-following idioms in mind. Documents and briefs authored by Opus levels can leak "Claude-isms" — phrasings, conventions, and implicit harness assumptions that read fine to a Claude model and badly to GPT-5.5. The **codex audit** is the action of scrubbing those out of anything an L5 will consume.

> Status: the L4+L5 codex audit is **owed** — it is an action not yet performed against the current L5 docs (`operational/L5/role.md`, `config.md`, `soul.md`, `swe-handbook.md`, `spawn-template.md`). It is logged here so it isn't lost; perform it before the first real Codex L5 spawn.

When auditing an L5-facing doc or brief, neutralize:

1. **Claude-harness tool assumptions.** References to tools/affordances that exist on Claude Code but not on the Codex tool manifest. The brief's tool references must match the *runtime-specific tool manifest* the adapter injects, not the Claude default surface.
2. **Implicit base-prompt behavior.** Anything that relies on Claude's base prompt or default conventions to "just work" (tone defaults, refusal patterns, formatting habits, implicit safety scaffolding). Codex has no Claude base prompt — make the expectation explicit in the doc or it won't hold.
3. **Claude instruction-following idioms.** Phrasings tuned to how Opus reads directives (soft hedges, "you might consider," altitude cues). For GPT-5.5, convert to explicit, literal, decision-complete instructions — say exactly what to do and what to escalate.
4. **Filled gaps that assume good-architecture backfill.** Any place the doc leaves a decision implicit on the assumption the model will fill it well. GPT-5.5 won't; make it explicit or mark it escalate-don't-decide.
5. **Cross-runtime brief conformance.** Confirm the doc cleanly separates neutral-contract content from runtime-specific content, so the adapter (not the prose) owns the runtime-specific parts.

The audit's output is a cleaned doc plus, where relevant, a note for `agent-definition-principles.md` (so the Claude-ism doesn't get re-authored next time) and the Claude Code harness patch registry if the fix belongs at the base-prompt patch layer (H40).

---

## Open Items

- **L4 model/runtime** — V1 default is Opus throughout; the L4-tester lateral may be reassigned to GPT-5.5 after evals. Not blocking.
- **L4+L5 codex audit** — owed; perform before the first real Codex L5 spawn (checklist above).
- **Claude base-prompt patch (H40)** — captured as intention; ties to the Claude Code harness patch registry. Codex levels have no Claude base prompt, so the patch is Claude-runtime-only by construction.

---

*Operational reference — loaded at boot for all levels; consulted by the spawn machinery at every spawn.*
*Created: 2026-06-02*
