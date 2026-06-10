# Communications Protocol — Operational Reference

How agents communicate at runtime. Loaded at boot for all levels.

**The executable contract:** real-time transport is the **bus**; durable truth is the **docs in the workspace**. A message is a **pointer/nudge**, never the payload. You are addressed by your **station** (workspace node path + role-variant). You may only see the nodes your **need-to-know visibility graph** grants. See the design rationale in `COMMUNICATION.md`; the addressing and node layout in `WORKSPACE-SCHEMA.md`; branch/merge in `git-protocol.md`.

---

## The Model: Bus + Docs

Two things, with a strict division of labor:

- **Docs are the truth.** Every durable artifact — brief, spec, frozen `acceptance.md`, design, plan, report, ADRs, decisions — lives as a file in the workspace under your station's node. The file is the single source of truth. Nothing authoritative lives in a message.
- **The bus is the transport.** The bus is a real-time pub/sub channel for *nudges*: "I posted my report," "interface X changed, re-read it," "blocked — see escalation." A bus message carries a **pointer to the doc** plus minimal routing/urgency metadata. It does not carry the content.

**Why this split:** because truth lives in docs, the bus is allowed to be **best-effort**. A dropped, delayed, or missed nudge cannot lose information — the receiver (or its respawned successor) recovers the full state by reading the docs. This is what makes the system robust to stateless respawn: a fresh instance reads its node and is current, whether or not it ever saw the bus traffic. Never put a fact on the bus that doesn't also exist in a doc; if it's only on the bus, it's already lost.

> **Superseded:** the earlier filesystem `comms/` inbox (folders, `unread/`→`read/` receipts, attachments-in-message) is **retired**. Do not create `comms/` inboxes. Escalations, reports, and findings are now docs in the work node, announced by a bus nudge. Attachments are files in the node, referenced by path.

---

## Pointer, Not Payload

A message is a pointer and a nudge. It says *where to look* and *why now* — it never duplicates the artifact.

Good (a nudge):
> `proj/payments/gateway#exec → proj/payments#review`: report ready — see `proj/payments/gateway/report.md`. Acceptance green, one concern noted.

Bad (payload on the wire):
> a 400-line paste of the report body into the message.

Rules:
- Reference artifacts by **station-relative path**, never copy their contents.
- The only thing unique to a message is its routing (`from`/`to` stations), its `type`, and its `urgency`. Everything substantive is in the doc it points at.
- ADRs are the rationale bridge (see `agent-definition-principles.md`): point at the ADR, don't re-argue the decision in a message.

---

## Addressing — Stations (F35)

Every agent has an **address = its workspace node path + a role-variant suffix**. The address is **semantic** (area names, not numeric `L3.1`) and **stable across respawn** — it is bound to the *work node*, not to the instance. When an instance dies and a fresh one is spawned onto the same node, it inherits the same address.

```
proj/payments                     # the L2-owned area node
proj/payments/gateway             # a module node under it
proj/payments/gateway/stripe-client   # a work unit under that
```

Role-variant suffix distinguishes the seats on one node:

```
proj/payments/gateway#exec        # the executing seat
proj/payments/gateway#review      # the independent reviewer seat (L5+ / right-arm)
proj/payments/gateway#test        # the lateral test/rubric author seat
```

**One spine.** This address scheme is not its own invention — it is the same hierarchical-path/prefix spine used everywhere in the system: requirement-IDs (`R-003.2.1`), workspace tree, git branches (`payments/gateway/stripe-client`, see `git-protocol.md`), frozen rubric/`acceptance.md` locations, and the visibility graph below. Address, path, branch, and requirement-prefix line up by construction. Decided once, serves all.

**Deriving relationships from the address** (pure prefix arithmetic — no separate registry):
- **parent** = the address minus its last path segment.
- **children / subtree** = the addresses whose paths are *under* yours.
- **siblings** = the addresses sharing your immediate parent.

The address survives collapse and resurrection: a node reaped after completion keeps its path; a 2w resurrection or audit re-attaches to the same address (see `agent-lifecycle.md`).

---

## Visibility — Need-to-Know Graph (F34)

You do **not** get broad, project-wide read. You see a bounded neighborhood derived from your station address. Default visibility for a node:

- **your own subtree** — everything at and below your address (you own it),
- **your siblings** — nodes sharing your immediate parent (for lateral coordination and interface fit),
- **your parent** — the node one segment up (for your brief, constraints, and the frozen rubric you're held to).

> **Superseded:** the earlier "broad project-wide read for situational awareness" is **retired** in favor of this need-to-know graph. Situational awareness comes from your *neighborhood* docs, not from reading the whole tree.

**God-view exceptions (read-only, by role):**
- **L1** and the **optimizer-L1** (future capability; see IMPROVEMENT-WORKSPACE.md for the V1 workspace) hold whole-tree read for triage, intent-guarding, and recurring-issue monitoring. This is read-only oversight, not a license to reach in and edit — see `IMPROVEMENT-WORKSPACE.md`.

**Cross-neighborhood coordination = escalate to the common ancestor.** If you need something outside your subtree+siblings+parent, you do **not** widen your own read. You escalate up to the nearest common ancestor of you and the node you need; that ancestor either holds the context, brokers the interface, or renegotiates the contract. This is how cross-module ripples are caught — at L2's compatibility review during the coordinated planning round (see `PLAN-ALIGNMENT-GATE.md` and `ARCHITECTURE.md`), not by point-to-point peeking.

**Frozen rubric is read-only to the executor.** The `acceptance.md` / rubric in your work node is visible to you but **write-protected** against the executing seat — it was authored at planning time by a different seat (the `#test` lateral / delegating level) and frozen before you began. You read it; you never edit it. Immutability is the anti-test-theater rule made physical (see `QUALITY-GATE.md` and `PLAN-ALIGNMENT-GATE.md`, D26).

---

## Communication Direction

**Downward (parent → child):**
- **Spawn** a child instance onto a node with its brief and station address.
- **Bus nudge** to a running child — "spec changed, re-read `…/brief.md`", "status?".
- Details and attachments are **files in the child's node**, referenced by path — never inlined.

**Upward (child → parent):**
- **Bus nudge with urgency** pointing at your report/escalation doc — completions, reports, escalations.
- You **cannot spawn upward.** Only a parent spawns children.

**Lateral (sibling ↔ sibling):**
- **Bus nudge** pointing at the shared artifact (the contended interface contract, the shared assumption). Lateral comms are for *fit*, not for reaching into each other's internals — siblings see each other's node surface, not each other's subtree.

Downward transport is unrestricted (a parent may always reach its subtree); the **visibility graph is a read-policy, not a transport limit** — transport is open, what you may *see* is bounded.

---

## Bus Message Shape

A nudge is small. It carries routing + a pointer + urgency, nothing more:

```
from:    proj/payments/gateway#exec     # sender station
to:      proj/payments#review           # recipient station
type:    phase-complete | escalation | deliverable | status-change | design-submission | review-verdict
re:      proj/payments/gateway          # the node this concerns
see:     proj/payments/gateway/report.md   # the doc that holds the truth
urgency: routine | needs-attention | blocking
```

**Urgency:**
- `routine` — read when convenient.
- `needs-attention` — read soon.
- `blocking` — sender is stopped until this is resolved.

**When to send.** Communication is **event-driven, not periodic.** You nudge when something meaningful happens; between events your parent reads your living docs (`plan.md`, `design.md`, `report.md`) for ambient awareness. No "still working" pings. If nothing meaningful happened, silence is correct.

**Events that trigger a nudge:**
- Work completed (task, workstream, area, phase) — report doc posted.
- Design submitted for review.
- Escalation — blocked on something outside your scope.
- Review verdict — accept (forward) or bounce (back to `#exec`, bounded loop).
- Significant status change the parent genuinely needs to know.

---

## Terminal Signal — the Sign-Off

Every agent's **last act before it ends is to write exactly one terminal-signal artifact** — a durable **file write into your own node directory**, not a bus message. This is the system's **sign-off**: the durable record that you reached a terminal state, and the single thing the watchdog reads to answer *"did it sign off?"*.

**How to sign off.** Write `.signal.<seat>.json` into your node directory via an **atomic tmp+rename** (write the complete JSON to a temp file beside it, then rename it onto the final name — never write the final file in place; a torn half-written signal must be impossible). Your node directory already contains `.sign-off.<seat>.json` — a **handshake file the harness seeded when your session opened**. It carries your `owner_token` and the absolute `signal_path` to write to. Read it; copy the token **verbatim**.

```json
{
  "signal": "DONE",                              // strict tag: "DONE" | "FAILED" | "ESCALATED"
  "ts": "2026-06-10T12:00:00+00:00",             // ISO-8601 UTC — when you signed off
  "owner_token": "<copied verbatim from .sign-off.<seat>.json in your node dir>",
  "evidence": { "report": "report.md", "notes": "<optional: failure reason / the ESCALATED question>" }
}
```

Field by field:

- `signal` — **the tag is the contract.** `DONE` = work complete (see `report.md`); `FAILED` = could not complete, reason in `evidence.notes`; `ESCALATED` = blocked, needs a decision — the question in `evidence.notes` feeds the answer-round-trip back down.
- `ts` — the sign-off moment, ISO-8601 UTC.
- `owner_token` — **the fence.** The daemon accepts the artifact only if this token equals the live binding's token for *your* incarnation. A signal carrying a wrong or stale `owner_token` is **silently ignored** by the watchdog — your sign-off never lands and you will eventually be reaped as non-responsive. Copy it exactly from `.sign-off.<seat>.json`; never construct one, never reuse one from a prior session.
- `evidence` — optional dict naming your completion artifacts: `report` points at the report doc; `notes` carries the free text (DONE note / FAILED reason / ESCALATED question).

The lifecycle around the write:

- **The artifact is journaled.** Each tick the daemon reads the durable file, validates the token, and the single-writer executor records it to the run-ledger and stamps the node's terminal state. So *"the check is that it got written"* reads the **durable artifact → journal** — never a transient message. The payload still lives in `report.md`.
- **A bus nudge is optional, never required.** After the artifact is on disk you *may* post a bus nudge ("signed off — see `report.md`") as a fast-path wake; the artifact is the record, the nudge is only latency. A dropped nudge loses nothing — the next sweep reads the file.
- **Then the lifecycle takes over** (`agent-lifecycle.md`): `DONE`/`FAILED` → the harness collapses the (ephemeral) leaf and the parent reads `report.md`; `ESCALATED` → the agent keeps context and waits for the answer rather than dead-ending. The watchdog's liveness check is exactly *"is there a terminal-signal event for this node in the journal?"* — if absent and the session has gone idle, it prods, then records `FAILED` on no response.

---

## Reporting — What Each Level Sends Up

Each boundary compresses differently because the receiving level needs a different *kind* of signal. The nudge points at the report doc; the doc carries the detail.

- **L5 → L4:** execution compressed into verification signals — "what was done, how it was tested (acceptance + unit + CI floor), what concerns remain." The signal L4 needs: did this unit get done correctly?
- **L4 → L3:** workstream compressed into completion status — "all tasks complete, integration verified, here's what was built." The signal L3 needs: does this workstream fit the others?
- **L3 → L2:** area compressed into project progress — "area design submitted" or "area execution complete, cross-workstream integration verified." The signal L2 needs: does this area serve the concept?
- **L2 → L1:** project state compressed into portfolio status — "on track," "concept ready for review," "decision needed on X," "project complete." The signal L1 needs: does this project need my attention?

Compression is a feature: each level hands its parent the altitude-appropriate summary in the report doc, not the raw lower-level detail.

---

## Escalation

When you hit something outside your scope or authority, you escalate. Escalation rides the same upward bus as reporting but carries a different signal: **"I need a decision or resource I don't have."** Escalation is also the sanctioned move for **cross-neighborhood needs** (route to the common ancestor) and for **brief ambiguity** — especially on a runtime that should escalate, not guess (see below).

### Escalation Payload

The escalation **doc** in your node holds all of these — a ready report, not a request for investigation. The bus nudge just points at it with `urgency: blocking`.

1. **What happened** — the specific situation.
2. **What was tried** — what you did to resolve it yourself.
3. **Evidence** — what you found, data, specifics (as files in your node where bulky).
4. **Options** — possible paths forward.
5. **Your recommendation** — what you'd do if it were your call.

The receiving level evaluates **independently**. This is a **low-trust decision environment**: the subordinate's ground-level view is useful signal, not a trusted directive. The parent evaluates against its own plan, framework, and frozen rubric; it does not default-bias toward the recommendation. The subordinate provides information; the parent owns the decision.

### Escalation, Not Decision (cross-runtime discipline)

The bus is **runtime-neutral** — both Opus and Codex/GPT-5.5 seats write files and post nudges, so escalation works identically across runtimes (see `runtime-and-model-map.md`, E32). But the *discipline* differs by seat:

- A **GPT-5.5 (Codex-harness) executing seat** must **escalate ambiguity, not silently decide it.** It will not paper over a gap with plausible architecture — so when its brief is ambiguous or its frozen `acceptance.md` is silent on a case, the load-bearing correct move is to escalate up the channel, not to invent. The brief it received is engineered to be maximally decision-complete precisely so this rarely fires; when it does fire, the escalation is the system working.
- An **Opus seat** carries more latitude to resolve in-scope ambiguity, but the same boundary holds: cross-module, cross-neighborhood, or intent-level questions escalate.

### Escalation Triggers by Level

**L5 → L4:**
- Task as specified can't be done (dependency missing, API doesn't match, constraints conflict).
- Better approach found but it changes scope.
- Work reveals something affecting sibling tasks.
- Brief is ambiguous, or `acceptance.md` is silent, in a way that affects the outcome (escalate — do not decide).

**L4 → L3:**
- Workstream larger or different than the brief specified.
- Cross-workstream dependency not in the design.
- L5 failure unresolvable by respawn or retry.
- Interface mismatch between tasks.

**L3 → L2:**
- Area assignment doesn't match operational reality.
- Cross-area dependency or conflict.
- L4 failure beyond tactical adaptation.
- Design gap requiring L2's judgment, or an interface that needs renegotiating upward (provisional-interface hardening).

**L2 → L1:**
- Cross-project issue (resource conflict, shared dependency).
- Project scope needs to change.
- Decision requires user input.
- Significant deviation from captured intent — L1 guards intent and routes to the user as needed.

**L1 → User:**
- High threshold. Only genuine decisions or blockers requiring owner judgment, framed for easy decision per the intake's opinionated-areas map.

---

*Operational reference — loaded at boot for all levels.*
*Created: 2026-03-29 · Rewritten 2026-06-02 (bus + docs; station addressing F35; need-to-know visibility F34; pointer-not-payload F33; inbox retired) · Terminal Signal rewritten 2026-06-10 (durable `.signal.<seat>.json` artifact + `.sign-off.<seat>.json` handshake; bus emission demoted to optional wake — F19).*
