# AI Architecture — Inter-Level Communication System (Process Design)

Level 5 process design document. Defines how levels communicate: transport, addressing, message contracts, visibility, reporting, and escalation. Constrained by `ARCHITECTURE.md` (Section 2: Inter-Level Relationships). Companion operational reference: `operational/shared/comms-protocol.md`. Addressing and the workspace tree it derives from: `WORKSPACE-SCHEMA.md`. Visibility-as-need-to-know also governs what each level reads, see `agent-definition-principles.md`.

---

## Supersession: filesystem-inbox → bus + docs (F33)

The earlier design modeled the inbox itself as the transport — a per-level `comms/` folder of message directories that *was* the message and *was* the channel. **That model is superseded.** It conflated two things that must be separated: the durable record of truth, and the act of getting someone's attention. When the same artifact is both, you pay for durability on every nudge and you lose messages whenever the filesystem write is the only copy of the fact.

The communication system now has two clearly-separated layers:

- **Durable truth lives in docs.** The living docs (`project.md`, `design.md`, `plan.md`, `report.md`), the decision records, the frozen briefs and acceptance rubrics, the RTM — these are the source of truth. They are versioned, owned, and edit-policed (see `WORKSPACE-SCHEMA.md`). Nothing that matters lives only in a message.
- **Real-time transport is the bus.** The bus carries pointers and nudges between live agents: "design submitted, read `L3/auth/design.md`"; "you're blocked, see escalation"; "approved, proceed." A bus message is a **pointer + a nudge**, not a payload.

Because the truth is in the docs, **bus delivery can be best-effort.** A dropped or duplicated nudge is recoverable: the receiving agent re-derives state by reading the doc it points at. This is the inversion that makes the system robust — losing a message can never lose a fact, because the message was never the fact. A missed nudge degrades latency (the parent notices later, on its next read or boot reconciliation), never correctness.

This supersedes the inbox `unread/`→`read/` folder model, the message-as-folder-with-attachments structure, and "the inbox is the primary channel." Attachments that are genuinely message-local (a run-specific error log, a one-off screenshot) are written into the work node and **referenced by path** in the bus message — link, don't copy — same single-source-of-truth discipline as before, now without a message-folder to host them.

---

## The Three-Layer Model: gauge / stations / cargo

Communication decomposes into three independent layers. Keeping them separate is what lets each evolve without breaking the others (B16 transport-vs-contract; B18 routing-vs-ownership).

### Layer 1 — Bus = the gauge (transport)

The bus is the rail gauge: the shared physical transport every agent rides, indifferent to what it carries. Real-time, in-process, best-effort. It moves pointers and nudges between live agents. It knows nothing about levels, roles, intent, or correctness — it only delivers a small message from one address to another, when both ends are live, and shrugs if it can't (the docs hold the truth).

Properties:
- Best-effort delivery — no durable queue semantics, no read-receipt bookkeeping. Truth is reconstructed from docs, not replayed from the bus.
- Carries **pointers, not payloads** — `re:` a doc path, plus the nudge. The body is the smallest thing that gets the recipient to read the right artifact.
- Stateless about content — the bus does not store the message as the record. If you need the record, it is already in a doc.

### Layer 2 — Addressing = the stations (F35)

The bus needs stops to route between. **An address is a workspace node path plus a role-variant suffix** — the F35 station grammar:

```
proj/payments                       # the L2-owned project node
proj/payments/gateway               # an L3 area node
proj/payments/gateway/stripe-client # an L4 workstream / L5 task node
proj/payments/gateway#exec          # the execution role-variant at the gateway node
proj/payments/gateway#review        # the reviewer role-variant at the same node
```

The address is **semantic** (area/module names, not numeric `L3.1`) and **stable across respawn** — it is bound to the work *node*, not to the instance currently occupying it. When an agent collapses and a fresh one is spawned onto the same node (a resurrection, an execution-L3 replacing a planning-L3), the address is unchanged; messages route to whoever currently holds the seat. The `#role` suffix disambiguates co-located seats on one node — `#exec` (the worker), `#review` (the L5+ reviewer or gate seat) — so the bus can address "the reviewer at the gateway node" without knowing which instance that is.

This is the same hierarchical-path spine that runs through the whole system. There is **one** path scheme, and addressing is one of its faces:

> requirement-IDs (`R-003.2.1`) = agent-addresses (`proj/payments/gateway`) = workspace-paths (`L3/payments/L4/gateway/`) = git-branches = rubric-file locations = the visibility graph.

Decided once in the consolidation, it serves all of them. A parent is recoverable by truncating the last segment; a subtree is everything under a prefix. (Full rationale: `WORKSPACE-SCHEMA.md` for the workspace tree, `PLAN-ALIGNMENT-GATE.md` for the requirement-ID/RTM face.)

### Layer 3 — Agent-contracts = the cargo

What actually rides the rails between stations is the **contract**, not free-form chatter. The durable contracts are the briefs, the frozen acceptance/rubric artifacts (read-only to the executor, per D26), the reports, and the escalation payloads — all docs. The bus message is the manifest that says "this cargo is ready at this station; come read it."

The cargo classes, by where their truth lives:

| Cargo | Truth lives in | Bus carries |
|-------|----------------|-------------|
| Brief / task contract (downward) | `briefs/` doc at the child node (frozen once sent) | "brief ready, read it, begin" |
| Acceptance tests / rubric (downward) | dedicated frozen `acceptance.md` in the work node, READ-ONLY to the executor (D26) | reference only — never a payload |
| Report / deliverable (upward) | `report.md` / `plan.md` (living, then immutable on completion) | "complete, read report" + urgency |
| Escalation (upward) | the escalation payload written into the work node | "blocking, read escalation" |
| Quick coordination | nothing durable — ephemeral | the whole message ("status?", "approved, proceed", "hold") |

Only the last class is bus-only with no backing doc; it is the synchronous, throwaway tier (the old "direct message"), and it carries nothing that would be a loss if dropped.

---

## Visibility = the Comms Graph = Need-to-Know (F34)

The earlier model granted broad, project-wide read access — any agent could see the whole tree. **That is superseded by a need-to-know visibility graph.** Visibility and communication are the *same* graph: an agent can message exactly the nodes it can see, and it can see exactly the nodes it needs to do its job. This is the addressing layer with a read-policy on top.

The default need-to-know set for any node, derived purely from its address:

- **Its own subtree** — everything under its path. A node owns and reads down into what it delegates.
- **Its parent** — the path minus the last segment. It reads up one level for the spec/brief/constraints it is held to, and reports up to it.
- **Its same-parent siblings** — peers under the same parent, for the interface contracts they share. (Cross-*parent* coordination is not lateral; it routes up to the common ancestor. This keeps the graph a tree, not a mesh, and is the F34 owed-question's working default.)

Everything else is off the read-table by default — tightening read scope is the point, not an afterthought. Narrow visibility keeps context clean (a node loads only what it needs), keeps coupling honest (you cannot quietly depend on a module you cannot see), and makes the blast radius of any single agent small.

**The optimizer-L1 / Internal-Affairs seat is the sanctioned exception:** a read-only god-view across the whole portfolio, for recurring-issue monitoring and audit (I42). It can see everything; it writes nothing into the work tree. (See `IMPROVEMENT-WORKSPACE.md`.)

Because the graph derives mechanically from addresses (F35), it does not need to be hand-maintained: subtree = paths under the prefix, siblings = same parent, parent = truncate one segment, god-view = the optimizer seat. Enforcement is spawn-time path-scoping — an agent is handed its visibility set at spawn and the harness scopes it there — rather than a convention an agent could ignore.

---

## Downward Messaging Is Unrestricted Within the Subtree (F36)

A parent may message any node in its own subtree directly — it is not forced to route through intermediate levels. An L2 can nudge a specific L5 task seat to redirect or hold it without bouncing through L3 and L4, when the situation warrants. This is a deliberate asymmetry: authority flows down, so downward reach within one's own subtree is unrestricted, while upward and lateral reach is constrained to parent + siblings.

**Transport and policy are separate concerns (F36).** The bus *can* deliver a message between any two addresses — that is a transport capability. Whether a given message is *allowed* is a policy decision layered on top, expressed by the visibility graph. The bus does not enforce org rules; the visibility/spawn-scoping layer does. Keeping them separate means policy can tighten or loosen (e.g., a future skip-level audit channel) without re-engineering the transport, and the transport stays a dumb gauge (B17: keep the router dumb; routing ≠ ownership ≠ policy).

The downward-unrestricted rule is therefore a *policy* statement (a parent's visibility includes its whole subtree, so it may address any node in it), not a transport feature. The default still expects routine traffic to flow level-by-level; direct skip-level downward messaging is for the cases where going through the chain would lose time the situation can't afford.

---

## Reporting Protocol

Event-driven, not periodic. Each level reports when something meaningful happens — completion, escalation, significant status change. No scheduled check-ins, no "still working" pings. Between events, the parent reads the child's living docs (`plan.md`, `design.md`, `report.md`) for ambient awareness — and because those docs are the truth (not a message), the parent is never blocked on having received a nudge. A missed report degrades to "the parent learns it on its next read," never to a lost fact.

The reporting message is, like everything on the bus, a pointer + urgency: "complete, read `report.md`." The compression that happens at each boundary is in the *doc*, not the message.

### Per-Boundary Patterns

**L5 → L4:** `report.md` in the task node is the living progress tracker during execution and the immutable handoff on completion. L4 reads it anytime. On completion or escalation, L5 posts a bus nudge to the `#exec` parent (the L4 node) with urgency. The reviewer seat (`#review`, the L5+ reviewer) accepts → forward, or bounces → L5 keeps its context and continues (bounded loop).

**L4 → L3:** `plan.md` for the workstream is continuously updated; L3 reads it for status. L4 posts on workstream completion, escalation, or significant status change — events, not progress.

**L3 → L2:** Same event-driven pattern. The planning-L3 posts "design submitted, read `design.md`" for the cross-area coherence review; the execution-L3 posts on area-deliverable-ready, decision-needed, or blocked/unblocked. L2 reads `design.md` / `plan.md` for ambient awareness.

**L2 → L1:** Same pattern. Posts on deliverable ready, decision needed, project blocked/unblocked, significant change. L1 reads `project.md` for ambient awareness; it does not need a separately-compressed report because the doc top *is* the status.

Per-boundary compression detail (what each level distills upward) lives in `operational/shared/comms-protocol.md`.

---

## Escalation Dynamics

When a level escalates, it provides a complete report: what happened, what was tried, evidence, options, and recommendation. The receiving level critically evaluates — a **low-trust decision environment.** The subordinate's ground-level view is useful signal, not a trusted directive. The receiving level evaluates against its own plan, framework, and knowledge, and does not default-bias toward the subordinate's recommendation.

Analogy: a good PM (not egotistical, genuinely cares about getting it right) receiving a consultant's "the plan is wrong" — listens seriously, evaluates from their own frame, owns the decision.

### Escalation Payload

The payload is a **doc** written into the work node; the bus carries only the `blocking` nudge that points at it. Body includes:

- What happened
- What was tried
- Evidence
- Options
- Recommendation

Everything needed for the recipient to decide — a ready report, not a request for investigation. Urgency rides the nudge: `routine` (check when convenient), `needs-attention` (check soon), `blocking` (sender is stopped until resolved).

**Escalate, don't decide — at the runtime boundary especially.** A node that receives a brief it cannot place, an ambiguity that affects the outcome, or a constraint conflict must raise it rather than silently fill the gap with its own judgment. This is load-bearing for the cross-runtime case: a GPT-5.5 (Codex-harness) execution seat is briefed to be maximally decision-complete precisely because, when the brief *is* ambiguous, the correct move is to escalate up the L5→L4 channel, not to invent architecture (it is weak at greenfield design). The escalate-don't-decide channel is what makes a thin runtime adapter safe. See `runtime-and-model-map.md` (E32) for the cross-runtime brief contract.

### Escalation Triggers by Level

- **L5 → L4:** Task as specified can't be done (dependency missing, API doesn't match the brief, constraint conflict). Better approach found but it changes scope. Work reveals something affecting sibling tasks. Brief is ambiguous in a way that affects the outcome.
- **L4 → L3:** L3's approach appears wrong or suboptimal. Operational surprise that changes the shape of the work (not just a task failure). Cross-task dependency not in the plan.
- **L3 → L2:** Area direction appears wrong or suboptimal. Cross-workstream/cross-area issue not in the plan (routes to the common ancestor — here L2). Scope or resource question exceeding L3's authority.
- **L2 → L1:** Cross-project issue (resource conflict, shared dependency). Project scope needs to change. Decision requires user input that L1 should mediate.
- **L1 → user:** High threshold. Only genuine decisions or blockers requiring owner judgment — and surfaced as a neutral, decidable choice grounded in the user's own stated values (see `PLAN-ALIGNMENT-GATE.md`, human sign-off).

---

## Relationship to the Plan-Alignment Gate

Communication is the live transport; the **plan-alignment gate** is the durable verification checkpoint that consumes what the docs hold. The gate reads the frozen artifacts (briefs, acceptance rubrics, the generated RTM) — never a bus conversation — exactly because truth lives in docs, not in messages. The bus nudges that flow during planning ("design submitted," "co-sign requested," "deltas ready for human sign-off") are pointers into those gate artifacts. The clean-context boundary the gate depends on is only possible because no fact lives in a transient message that a fresh agent would miss. See `PLAN-ALIGNMENT-GATE.md`.

---

*Created: 2026-03-17*
*Updated: 2026-06-02 — Superseded inbox-as-transport with bus (real-time, best-effort) + docs (durable truth) per F33. Added the three-layer model (bus=gauge / addressing=stations per F35 / agent-contracts=cargo), the need-to-know visibility graph (F34), and downward-unrestricted / transport-vs-policy separation (F36). Folded the one hierarchical-path spine and escalate-don't-decide (E32). Source: working-notes/consolidation-plan-2026-06-02.md.*
