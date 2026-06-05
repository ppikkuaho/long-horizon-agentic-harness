# TRANSPORTS — The Bus Wire, Wakes, and Human Channels (Cluster ③ spec)

Status: design, v1 cut. This sits **on top of** cluster ① (`DAEMON.md` — the substrate) and
cluster ② (`WATCHDOG.md` — the detector/recovery state-machine). It builds the **wire**; ① and ②
own the seats it plugs into.

This document specifies the harness's **own bus** and the keystroke-level **wake wire**, plus the
**escalation-answer round-trip down** and the **three human channels**. It is the cluster-③
deliverable named in `working-notes/runtime-decisions-and-commissioning-2026-06-04.md` and closes
the gap-review blockers it owns:

- **#5** — bus transport never specified + the parked-coordinator wake undefined (the
  `ARCHITECTURE.md` §Communication-and-Visibility "Transport-spec stub" is reconciled to the
  own-bus at the doc level; this doc fleshes that stub into an actual wire).
- **#6** — the escalation-answer round-trip **back down** (alive child vs collapsed child).
- **#7** — the three human channels, all previously content-without-a-channel.
- **IMPORTANT #4** — the nudge/transition race (`send-keys` has no ack and no ordering guarantee).
- **IMPORTANT #5** — the pull-visibility read-path + its direct-children-vs-subtree scope.

It **consumes** ①'s seats (the spawn chokepoint, the single-writer executor, the binding-ledger
tree, the durable `.signal.json`→sweep→journal terminal-signal path, the fencing tokens, the
genesis/harness-app path) and ②'s seats (the prod preconditions, the roll-up race rule, the closed
gate-detection trigger set, the events it may carry). **It redesigns none of them.** Every seat is
named at its exact ①/② address.

---

## 1. Charter + Scope

### 1.1 The locked transport model ③ inherits (do not re-litigate)

The model is fixed upstream (`ARCHITECTURE.md` §Communication-and-Visibility F33;
`COMMUNICATION.md`; `comms-protocol.md`; runtime-decisions §6) and ③ builds **under** it:

- **Truth lives in files; the bus carries pointers/nudges, never payload.** "Never put a fact on
  the bus that doesn't also exist in a doc; if it's only on the bus, it's already lost"
  (`comms-protocol.md`).
- **Delivery is best-effort.** A dropped/duplicated/delayed nudge costs a little latency, never
  correctness — the receiver, or its respawned successor, re-derives state from the durable doc.
- **The harness owns its OWN bus.** The Life-OS bus is a reference to *study*, not a transport to
  reuse as-is (`ARCHITECTURE.md` §F33).
- **Upward visibility is PULL** (a parent reads its subtree roll-up on demand); only milestones are
  promoted. Vertical read-DOWN into a node's own subtree is open; lateral/upward coordination-WRITE
  stays scoped (F34).
- **The one load-bearing best-effort exception is NOT ③'s to own.** The terminal-signal's
  *fact-of-being-sent* is journaled — but that journaling is **cluster ①'s** (the sweep journals
  from the durable `<node>/.signal.json`, `DAEMON.md` §3.5). The bus carries only the best-effort
  **wake**. ③ must never re-own the sign-off.

### 1.2 What cluster ③ OWNS (v1 INCLUDE — the sufficiency cut)

| ③ owns | Section |
|---|---|
| **The bus wire** — the transport (per-node append-only inbox file under the node's address + tail) with delivery/liveness semantics, keeping truth-in-files / pointer-not-payload / best-effort | §2 |
| **The wake contract** — how a PARKED coordinator idle at a TUI prompt is woken (`tmux send-keys` + Enter), the wake-says-why message, verify-new-turn-via-JSONL, re-prod, non-prompt-modal defer, honoring ②'s prompt-string gate + owner-token fence; `send-keys` carries NO ordering guarantee | §3 |
| **Escalation-answer-DOWN** — alive child (decision doc + downward wake) vs collapsed child (resume via ①'s §6.4 chokepoint, decision as a named delta-brief payload class) | §4 |
| **The three human channels** — (a) human sign-off transport for the plan-alignment gate; (b) the out-of-band L1→user attention channel; (c) the human control surface | §5 |
| **The pull-visibility read-path** — the concrete deterministic glob, scope reconciled | §6 |
| **Nudge routing + addressing** — nudges address the one-spine node-address; the quiesce-then-reap interlock | §7 |

### 1.3 What cluster ③ CONSUMES (bind, do NOT duplicate)

Every seat below is named at its exact ①/② address. ③ wires them together; it invents nothing in
the keystroke layer, the ledger, or the fencing.

| ③ needs | ①/② seat (exact name) | Source |
|---|---|---|
| (Re)spawn / carry an answer down to a collapsed child | the spawn chokepoint `spawn()` / `claim` / `transition` — resume is the §6.4 variant | DAEMON §6.1, §6.4 |
| The only mutator (human-kill + any gate-state flip route THROUGH it) | the single-writer executor + one serialization domain | DAEMON §4.1 |
| The substrate for nudge routing + pull-visibility | the binding-ledger tree keyed on the one-spine `node_address` (parent = truncate last segment; subtree = prefix) | DAEMON §3.1, §3.2 |
| The terminal-signal truth (③ adds only the best-effort wake) | `<node>/.signal.json` → reconcile sweep → run-ledger `signal_*` row | DAEMON §3.5 |
| The nudge/kill-race interlock | the fencing CAS — `lease_epoch` / `owner_token` / `generation` | DAEMON §4.2, §8 |
| The host for the human control surface | the genesis app → daemon → L1 path (the harness app) | DAEMON §7, §9 |
| The detached pane to send-keys into | `tmux_target: harness:<collapsed-address>` + `tmux capture-pane` readback | DAEMON §6.2 |
| The prod preconditions a wake must satisfy | (1) prompt-string gate, (2) owner-token fence, (3) verify-new-turn-via-JSONL-growth | WATCHDOG §4.3, §11.1 |
| The roll-up race rule + quiesce-then-reap interlock policy | the COLD roll-up + no-`slot_claimed`/`spawned`-in-W gate; one CAS-guarded writer to the kill decision | WATCHDOG §5.4 (FORK A) |
| The closed gate-detection trigger set that flips the gate field | `gate_crossed_at` (② flips via `watchdog-checkpoint`; ① enforces) | WATCHDOG §9 |
| The events ③ may carry best-effort | the watchdog-imposed `FAILED` + recovery/escalation events | WATCHDOG §11.1 |

**Exact binding fields ③ touches** (read-only, or written ONLY via the executor — never directly):

- `terminal_signal`, `terminal_signal_at`, `terminal_note`, `signal_artifact_seen_at` — the
  escalation answer-round-trip + the sign-off (read-only; ③ never writes them).
- `gate_crossed_at` — the human sign-off gate state (② flips, ① enforces, **③ surfaces** the human
  verdict that triggers the flip).
- `deliverable_state` (`planned|active|waiting|completed|blocked|cancelled`) — the workboard half
  the sign-off package reads/reflects.
- `owner_token` + `lease_epoch` + `generation` + `session_uuid` + lifecycle `state` — **read by the
  SENDER from the live binding immediately before a wake** for the sender-side fence (token-freshness
  AND incarnation-match AND not-collapsing, §3.2 precond-2). The wake message itself carries **no**
  token field and the receiving agent never validates a token — the fence is entirely the sender
  refusing to send a stale/collapsing/mismatched wake. (The kill path, by contrast, presents
  `expected_owner_token` + `expected_generation` into the executor CAS — a different, ledger-mutating
  operation.)
- `liveness_state` with the **`waiting` vs `idle`** split — load-bearing for the roll-up read.
- `node_address` / `parent_address` — one-spine addressing + the prefix-glob pull read.
- `tmux_target`, `session_uuid` — the wake target + the incarnation a wake must match.

### 1.4 What cluster ③ DEFERS (named out-of-scope)

| Deferred item | Owner |
|---|---|
| Admission control / 429-backoff / per-runtime ceilings / resource envelope | ④ |
| The detector internals, multi-signal fusion, lease recovery, the wedge (W2) detector | ② |
| The daemon/executor/ledger/spawn-chokepoint/genesis/atomicity/fencing schema | ① |
| The GUI dashboard **rendering** (the pixels) — ③ specifies the **data** the control surface reads/writes, not how it is drawn | a later GUI pass |

> **Hard boundary (mirror of WATCHDOG §1.3).** ③ specifies the WIRE — the `send-keys` mechanics, the
> bus, the channels. ② owns **what** a prod must satisfy; ① owns the ledger/spawn/fence. ③ must not
> redesign any of them.

---

## 2. The Bus Wire

### 2.1 The chosen transport

> **FORK — for user review (the bus transport choice).** Best-effort means *opposite* failure modes
> for a socket vs a file-watch (`arch-gap-review` #5: "load-bearing because best-effort means
> opposite failure modes"), so the choice is load-bearing and recorded explicitly rather than
> asserted.
>
> - **Option A (RECOMMENDED): per-node append-only inbox file + tail.** Each node gets an
>   append-only `<node>/.inbox.jsonl` inside its node folder, keyed on the collapsed one-spine
>   address. A nudge is **one line**: a pointer, never payload. The inbox file **is itself
>   recoverable on respawn** — it sits in the durable work node, so it matches docs-as-truth: a
>   reader that missed a tail event re-derives by reading the inbox file (and, behind it, the
>   `report.md`/`plan.md`/`status.md` it points at). Liveness/delivery mechanism: tail the
>   node-folder inbox (see §2.3 for the macOS caveat).
>
>   **The inbox is MULTI-writer (unlike the single-writer ledger) — its atomicity rule is stated
>   explicitly, not borrowed.** Any node in the subtree can nudge any addressable node, so
>   `<node>/.inbox.jsonl` is written by **many** senders, bypassing the executor — the **opposite** of
>   ①'s run-ledger, which has exactly one writer (the single-writer executor, DAEMON §4.1: "one
>   writer, no second mutator"). So the run-ledger's single-writer append discipline does **NOT**
>   transfer, and ①'s `<node>/.signal.json` `tmp+rename` does **not** fit either (rename-replace is
>   for a single-author whole-file artifact, not a shared append log). The actual rule for a
>   multi-writer append log: rely on **POSIX `O_APPEND` write atomicity**, which holds **only for a
>   whole-line write whose byte length ≤ `PIPE_BUF`**. Two requirements on the writer make this
>   safe: (1) **one `write()` per nudge line** (format the full line in memory, single `write()` —
>   never a partial flush); (2) **cap the line size** — a nudge is a pointer (from/to/type/re/see/
>   urgency, §2.2), trivially a few hundred bytes, comfortably under `PIPE_BUF`. Best-effort makes a
>   rare torn line just a **dropped nudge** (recovered from the durable docs the `see:` pointer
>   names), but the writer rule must still be honored so a builder gets concurrent-append atomicity
>   right rather than producing interleaved/torn lines.
> - **Option B: a socket / Redis pub-sub.** Pro: instant push, no poll. Con: **loses truth-in-files**
>   — a socket message that is dropped while the receiver is down is *gone* (no durable backing file
>   to re-derive from), which reintroduces exactly the durable-queue the model deliberately rejected;
>   and it adds a daemon dependency the best-effort model is designed to NOT need. A dropped
>   socket-nudge is a *different and worse* failure mode than a missed file-tail (which the file
>   itself heals).
> - **Recommendation: A.** The append-only per-node inbox file is the only option that preserves
>   truth-in-files / pointer-not-payload / best-effort and is self-healing on respawn. The
>   cluster prompt and `arch-gap-review` #5's RESOLVED line both pre-commit to this; the trade is
>   recorded here so the choice is justified, not asserted.

This inbox file is a **NEW best-effort wake surface**, distinct from the retired `comms/`
inbox-as-transport. **Do NOT** resurrect the `comms/` `unread/`→`read/` model — it is explicitly
superseded (`COMMUNICATION.md` §Supersession; `comms-protocol.md`: "Do not create comms/ inboxes";
`WORKSPACE-SCHEMA.md`). The `comms/` folder, where it survives, is only a **durable mailbox / audit
copy** read at boot reconciliation, **not** the live channel.

### 2.2 The nudge message shape (reused verbatim from comms-protocol)

③ reuses the bus message shape `comms-protocol.md` already fixes — it invents no new fields:

```
from:    <sender station — a one-spine address + #role suffix>
to:      <recipient station — a one-spine address + #role suffix>
type:    phase-complete | escalation | deliverable | status-change | design-submission | review-verdict
re:      <the node this concerns — a one-spine address>
see:     <station-relative doc path that holds the truth (NEVER the contents)>
urgency: routine | needs-attention | blocking
```

The only thing unique to a message is its **routing, its type, and its urgency**
(`comms-protocol.md`). `see:` is a pointer — a station-relative path, never copied contents
(pointer-not-payload). Reporting is **event-driven, not periodic**: a nudge fires only when
something meaningful happens (work complete, design submitted, escalation, review verdict,
significant status change) — no "still working" pings; silence is correct.

### 2.3 Delivery + liveness semantics

- **There is ONE delivery mechanism to a coordinator, not two.** A coordinator TUI — whether parked
  (idle at the prompt) or busy (mid-turn) — is **not** running its own inbox tail loop: a parked TUI
  is blocked on its input prompt, and a busy LLM agent in a tool-use turn is not running a watcher
  either. So **every** delivery to a coordinator goes through the **same reconcile-driven §3
  send-keys wake at its next prompt**, and the inbox is **re-read by the agent on each new turn** (the
  wake message tells it to re-read `<node>/.inbox.jsonl`). There is no separate active-tail process to
  own. (This retires the `NOTES.md` "Parked = self-waking via blocking command" framing: a `send-keys`
  TUI has no blocking-command analog.) The **only** thing that tails the inbox file is `harnessd`'s
  own reconcile loop (it watches inbox writes to decide *when* to fire a §3 wake), not the receiving
  agent.
- **macOS caveat (the launchd `harnessd` runtime, genesis §4).** `inotify` is Linux-only; the runtime
  is the launchd-hosted resident `harnessd` (DAEMON §2.6). The tail/watch mechanism `harnessd` uses to
  notice an inbox write is **fsevents/kqueue, with a bounded poll-tail fallback**. Because delivery is
  best-effort and the durable truth is the file, a *poll* watch is fully acceptable — a slightly later
  poll only adds latency, never loses a row.

### 2.4 Relationship to ①'s journaled terminal-signal (the firewall ③ must not cross)

The wire carries **only a best-effort wake**. It is an **optimization, not a correctness
dependency** (WATCHDOG §11.1). Concretely:

- The durable terminal fact lives in `<node>/.signal.json` (the agent's atomic last act) → the
  reconcile sweep journals it (validating `session_uuid` against the live binding, idempotent via
  `signal_artifact_seen_at`) → the run-ledger `signal_*` row + `terminal_signal` field → the work
  node's `report.md` (DAEMON §3.5).
- A bus wake at most triggers an **immediate sweep** of that node instead of waiting for the timer.
  A dropped wake **delays journaling to the next sweep — it can never lose the row or cause a false
  sign-off failure**.
- **The sign-off check reads the JOURNAL, not the nudge.** Any phrasing like "did we receive the
  terminal nudge?" is a direct contradiction of the contract and is **forbidden** (WATCHDOG §4.1).
  ③ never re-owns the terminal signal; it adds only the wake.

> **Open seam (DAEMON §10, recorded not resolved).** Whether terminal-signal entries are mirrored
> into the project `log.md` or kept strictly in the run-ledger is open; the in-source recommendation
> leans strictly-run-ledger. This affects whether ③'s wake/notification surfaces point a reader at
> `log.md` vs the run-ledger. ③ points readers at the **durable work-node doc** named in the
> nudge's `see:` field regardless, so it is insensitive to this seam.

---

## 3. The Wake Contract

A wake is how a **parked coordinator** (idle at a TUI prompt, not attached by the user) is told to
look at something. ② owns **what** a prod/wake must satisfy; ③ builds the wire.

### 3.1 The wire — `tmux send-keys` + Enter

The target is the **detached tmux session** the spawn chokepoint created, named from the one-spine
address: `tmux_target: harness:<collapsed-address>` (e.g. `harness:payments/gateway/stripe-client#exec`,
DAEMON §6.2). The mechanic is `tmux send-keys <wake-msg> Enter` into that pane. The readback/observe
channel is `tmux capture-pane` (the same surface the reconcile loop uses, DAEMON §6.2).

**The wake message says WHY it woke and WHERE to look** — it is itself pointer-not-payload: "decision
posted on your escalation, re-read `<node>/decision.md` and resume" / "new message in your inbox,
re-read `<node>/.inbox.jsonl`". The agent then reads the durable doc; the keystroke carries no fact.

### 3.2 The three preconditions ③ honors (② owns them — WATCHDOG §4.3)

1. **Prompt-string gate.** Deliver the wake **only when `tmux capture-pane` shows the idle input
   prompt** (a prompt-string match against the captured pane). `send-keys` **can** land mid-tool-call
   and corrupt the input line; the prompt-string gate stops the keystroke interleaving with an
   in-flight tool call. If the pane is **not** at the prompt, the node is either still `working`
   (don't wake) or `wedged` (②'s §6 path — kill+escalate, don't wake). The exact prompt-detection
   *signal* (capture-pane text-match vs the H40 outbound-payload capture surface,
   `OBSERVABILITY.md` §124–130) is **behind ②'s detector interface** — ③ specifies the `send-keys`
   mechanic and defers the prompt-state evidence source to ②.
2. **Owner-token fence — a SENDER-SIDE freshness check, NOT the executor CAS.** This is the
   load-bearing distinction the wake path must get right. `send-keys` is a raw keystroke into a tmux
   pane; it does **NOT** pass through the executor's CAS the way the kill-side `transition`
   (`expected_owner_token` + `expected_generation`) does. Nothing in the pane or the executor compares
   a sender's token to the live binding's token before a keystroke lands — so the fence is **not** "the
   same CAS as the kill path." The fence that actually works is a **read-and-compare the SENDER
   performs immediately before emitting `send-keys`**:
     - **Re-read the live binding** for the target `node_address`.
     - **Abort the wake** if the observed `owner_token` / `lease_epoch` **≠** the binding's current
       value (the seat was respawned — a higher `lease_epoch` means a fresh instance took it).
     - **Also check `tmux_target`'s `session_uuid`** matches the binding's `session_uuid` (§1.3: the
       incarnation a wake must match) — a pane reused by a new session is caught even if the epoch read
       raced.
     - **Also abort if the binding's lifecycle `state` is in the collapsing/terminal set**
       `{failed, dead}` (or `condition = terminal`) — see §7.2 for *why this is required and not
       redundant*: the epoch is re-minted by a **new claim** (DAEMON §8), not by the kill transition,
       so between a collapse-CAS landing and a successor claim re-minting the epoch the binding still
       holds the **old, non-stale** token; only a state-read closes that mid-collapse window.
   The fence is therefore **token-freshness AND incarnation-match AND not-collapsing**, all read from
   the binding at send time. The agent never needs to see a token — the check is entirely
   sender-side; the keystroke that lands is just the free-text "re-read your inbox / decision, resume."
   Contrast with the kill path (§7.2): that is a **CAS-fenced ledger mutation**; this is a
   **sender-side-checked keystroke**. They are not the same mechanism — do not equate them.
3. **Verify-new-turn-via-JSONL-growth, no blind trust.** `send-keys` is **fire-and-forget — it has
   NO ack** (gap-review IMPORTANT #4). Confirm the wake "worked" **only** by observing a new turn in
   the transcript JSONL (forward progress), never by assuming the keystroke landed. **Re-prod** if
   no new turn appears. **Which grace budget bounds a re-prod depends on what was woken:** a
   woken **leaf** uses the leaf's own `stale_check_count` ladder (WATCHDOG §4.3); a woken
   **coordinator** is **not** a leaf and has no leaf prod-ladder — its re-prod is bounded by the
   coordinator's lease-machine grace (WATCHDOG §3.5 `stale_check_count` for coordinators).
   **Independently of budget, every re-prod must itself re-pass precondition 1 (the prompt-string
   gate) before it fires** — so a re-prod can never land mid-tool-call even if the agent legitimately
   took a long quiet turn after the first wake succeeded (re-reading a large `decision.md`, then a
   long tool call). The **count, reset rule, and gate are ②'s**; the *grading content* of the re-prod
   (gentle → firmer) is ③'s wire concern.

### 3.3 Defer when the TUI is at a non-prompt modal

If `capture-pane` shows a non-prompt **modal** (e.g. an un-pre-seeded trust/permission dialog) the
wake is **deferred** — `send-keys` into a modal does not wake the agent, it answers the modal. This
is exactly why first-boot trust must be **deterministic / pre-seeded** at spawn, **NOT a `send-keys`
race against the trust dialog** (DAEMON §6.2). The prompt-string gate (precondition 1) is what
distinguishes a clean idle prompt from a modal: no prompt-string match ⇒ no wake.

### 3.4 No ordering guarantee (state explicitly)

**`send-keys` carries NO ordering guarantee and NO ack.** Two wakes can land out of order; a wake
can land on a pane being concurrently collapsed; a wake can land on a **fresh** instance that took
the seat (addresses survive respawn, F35). The **sender-side freshness check** (precondition 2 —
token-freshness AND incarnation-match AND not-collapsing, read from the binding immediately before
`send-keys`) and the quiesce-then-reap interlock (§7) are what make this safe: a wake whose
pre-send read shows a stale token, a mismatched `session_uuid`, or a collapsing/terminal `state` is
**aborted before the keystroke is emitted**, and the receiver/its successor re-derives from the
durable inbox + docs regardless of wake ordering. (Note: this is a *pre-send abort by the sender*,
not a CAS the executor enforces — a raw keystroke has no executor hop to fence it, so the safety is
the sender refusing to send, §3.2 precond-2.)

> **Codex/L5 pane (flagged, inherits the same contract).** The `send-keys` wake mechanics are
> measured only for the **Claude-Code** pane (H40). How a Codex-harness L5 pane is woken /
> capture-pane'd / prompt-gated is **owed** (the Codex adapter is underspecified, DAEMON §6.3). The
> Codex pane inherits the **same neutral wake contract** (detached tmux session, send-keys, prompt
> gate, owner-token fence, verify-new-turn) but with an **adapter-supplied prompt-string + capture
> surface**. ③ flags this as an adapter port, not a separate wake design.

---

## 4. Escalation-Answer DOWN — the return path (gap-review #6)

The forward escalation is already specified upstream: a blocked agent does **not** dead-end and does
**not** collapse — it **keeps its context** and escalates *decidable options* to its parent (G37,
`agent-lifecycle.md`). The escalation **payload is a doc** in the work node (the five-field body:
What happened / What was tried / Evidence / Options / Recommendation); the bus carries only the
`urgency: blocking` nudge pointing at it (`COMMUNICATION.md`). The parent evaluates independently —
low-trust, **does not default-bias toward the recommendation**.

③ owns only the **return path** — the answer back down. It has exactly **two branches**, keyed on
the child's **lifecycle `state`**, NOT on `terminal_signal`.

> **The asymmetry ③ must honor (DAEMON §3.6).** `ESCALATED` **sets** `terminal_signal = ESCALATED`
> but lifecycle `state` **stays `running`** and the node is **NOT collapsed** — the agent keeps
> context and waits. So `terminal_signal != null` does **NOT** mean "collapsed." Gate the
> alive-vs-collapsed decision on `state ∈ {done, failed, dead}`; an `ESCALATED` child is **alive**
> and reachable by a downward wake into its still-running session.

### 4.1 Branch A — the child is ALIVE and waiting (`state = running`, `terminal_signal = ESCALATED`)

The still-running instance retains its loaded brief, frozen `acceptance.md`, work-in-progress, and
reasoning. The answer-down is:

1. The parent **writes the decision into a durable doc in the child's node** — e.g.
   `<node>/decision.md` (the answer to the question the child posted in its escalation doc / the
   `terminal_note` field). Pointer-not-payload: the decision is a file, not a bus message.
2. The parent sends a **downward wake nudge** (`see: <node>/decision.md`, message "decision posted,
   re-read, resume") via the §3 wake wire — `send-keys` into the child's `tmux_target`, honoring the
   §3.2 sender-side fence (prompt-string gate + token-freshness/incarnation/not-collapsing read +
   verify-new-turn). **This downward wake is subject to §3.2 precondition 3:** verify a new turn via
   JSONL growth and **re-prod** (bounded by the child's `stale_check_count` grace budget; each re-prod
   re-passes the prompt-string gate) if the child does not re-read `decision.md`. **A dropped single
   wake must not strand a posted decision** — the parent does not fire-once and move on; the answer-down
   is as robust as the leaf prod ladder. (Because the decision lives durably in `decision.md`, even a
   fully-lost wake is ultimately recovered: a re-prod, or the child's own next-turn inbox re-read,
   surfaces it. The wake is the fast path, the file is the truth.)
3. The waiting instance re-reads the decision and resumes **in its retained context**.

The `terminal_note` (the ESCALATED question) is what the decision responds to; the binding
`session_uuid` / `owner_token` bind the wake to the right incarnation.

### 4.2 Branch B — the child is COLLAPSED / reaped (`state ∈ {failed, dead}`)

This is **NOT a separate code path.** ③ does not build a resume mechanism — it **carries the
decision INTO ①'s spawn-chokepoint resume variant** (DAEMON §6.4) and invokes the chokepoint:

1. **Re-adopt the address** via `claim` with `expected_state ∈ {running, dead}` (the re-adopt edge,
   NOT fresh-claim's `expected_state = planned`), bumping `lease_epoch` + re-minting `owner_token`
   (fencing the prior incarnation).
2. **Assemble the delta brief** (DAEMON §6.4 step 2). The decision rides as a **named delta-brief
   payload class** — DAEMON §6.4 already names "**parent answers to an `ESCALATED`**" as a delta
   payload — pointing at the durable work node the fresh instance re-reads (`status.md`, `log.md`,
   `report.md`, frozen `acceptance.md`).
3. **Boot via §6.2**, recording the new `session_uuid`.

The binding uuid (`session_uuid` / `owner_token`) binds the answer to the right node.

### 4.3 The gate firewall both branches honor

If the child's `gate_crossed_at` is **set**, the chokepoint **REFUSES `--resume`** and falls back to
a **fresh spawn with a delta brief** (DAEMON §6.4, LOCKED). For Branch B this is automatic (the
chokepoint enforces it). For Branch A, a node that has crossed a gate would not be a plain
resume-in-place — it routes through the chokepoint's fresh-spawn-with-delta path, never a raw resume
of the pre-gate context.

> **Dependency on the DAEMON author — CONFIRMED PRESENT in ① (no longer owed).** The re-adopt edge
> Branch B depends on — `claim` admitting `expected_state ∈ {running, dead}` — is now a **first-class
> member of ①'s schema**: DAEMON §3.3 lists `running ──re-adopt(claim, expected_state=running)──▶
> claimed` and `dead ──re-adopt(claim, expected_state=dead)──▶ claimed` as legality-table edges,
> states "the `claim` primitive therefore takes an `expected_state` parameter," and §6.4 step 1 does
> the re-adopt with `expected_state ∈ {running, dead}`. **Branch B type-checks in ① as written.**
> (Regression note: the binding must hold — if a later ① revision narrowed `claim` back to
> `expected_state = planned`, Branch B would un-build. WATCHDOG §10/§12 still describe this as an
> owed/blocking dependency against an earlier DAEMON revision; that is ②'s stale note to reconcile,
> not ③'s — see §10.)

---

## 5. The Three Human Channels (gap-review #7)

All three are plausibly hosted by **the harness app** (the genesis path, DAEMON §7, §9). ③
specifies the **data** the control surface reads/writes — **not the pixels** (GUI rendering is
deferred to a later GUI pass). The L1-vs-L2 dashboard *altitude* of rendering is left to that pass;
③ specifies the primitives as **data-layer ops addressable by node**.

> **Host note.** `GUI-DESIGN.md` is pre-Phase-0-reconciliation (it still calls Claude Code "the
> backbone" and leaves the ring-vs-spatial paradigm unintegrated). ③ uses its **room/dashboard host
> model** and its **dual-rendering data-vs-pixels split** only, and binds the actual transport/host
> mechanics to DAEMON §7 (harness app + genesis), **not** to its backbone framing.

### 5.1 Channel (a) — the human sign-off transport (the plan-alignment GATE)

This is the one gate that **cannot be delegated upward or automated away** (`PLAN-ALIGNMENT-GATE.md`
Check 8); PASS unlocks the build cycle. ③ wires the transport between the gate and ①'s
deliverable-ledger; it does **not** own the ledger.

**Forward: the sign-off package** is a **single digestible file** (never the raw distributed plan),
with the four ordered sections `PLAN-ALIGNMENT-GATE.md` fixes: (1) The Playback (triangulated
three-column claim/acceptance-test/intent-span per outcome+MNF; two-window disagreements surfaced as
"we are unsure what this will do"); (2) The Findings Ledger (**deltas only**, each one line of
intent-language with a proposed disposition); (3) The Must-Never-Fail Roster (**always
force-expanded**, never collapsed); (4) The Residual (judgment calls inside `delegated` areas).
**Re-gating re-presents only the deltas since the human's last view**, never the whole package
again.

**Verdict: the surface flips the deliverable-ledger gate state.** The verdict is **not a bare
boolean** — it is a set of typed dispositions plus a PASS edge:

- Findings-ledger dispositions are the named set `accept` / `fix-and-route-to-level-N` / `defer`
  (`PLAN-ALIGNMENT-GATE.md`). The `route-to-level` value uses the **one-spine node address** — the
  same address ③'s nudge routing addresses (§7), so a disposition routes a fix down the tree with no
  parallel scheme.
- The **PASS edge** is what flips the **deliverable-ledger gate state**. ③'s transport surfaces the
  human verdict; the **executor stamps** the flip (single-writer path, §5.3) — ③ never writes the
  ledger directly. The flip sets the gate field (reconciled to `gate_crossed_at`, §5.4 below) and is
  what triggers freeze (the `candidate` → `frozen` transition that occurs **only** on the PASS edge).
  **`candidate`/`frozen` is the plan-artifact's OWN state (`PLAN-ALIGNMENT-GATE.md` vocabulary), NOT
  an ① binding field** — none of ①'s enums (`deliverable_state` `planned|active|waiting|completed|
  blocked|cancelled`, lifecycle `state`, the `gate_crossed_at` flag) contain `candidate`/`frozen`. ③
  surfaces only the **verdict that triggers** the freeze; the freeze itself is owned by the gate/plan
  layer — the same way ③ disclaims owning the deliverable-ledger. Any change touching an MNF or a
  user-confirmed `delegated` default **re-enters the HUMAN gate specifically** — so the
  answer-injection slot (§5.3) and this sign-off transport overlap for those classes.

**The telemetry back-channel (the dwell/expand events the health monitor reads).** Channel (a) is a
**two-way** transport, not just a forward package + verdict. The monitor (`OBSERVABILITY.md` §7;
`PLAN-ALIGNMENT-GATE.md`) tracks two proxies **per gate run**: (1) **sign-off dwell time**
(*engaged-attention* time on the playback/findings-ledger/force-expanded-MNF roster, **not**
wall-clock); (2) **expansion rate** (the fraction of flagged-drift / residual-judgment /
force-expanded-MNF items the human actually **opens** vs approves collapsed). So the surface must
emit **per-item open/collapse events + engaged-attention timing** back to the monitor — not only a
final verdict. Two consumers: a **surface-only warning** to the user (a collapse in either proxy is
pointed out, **no forcing, no override** — respect autonomy), and a **passive feed** to the
system-improvement workspace for cross-run degradation patterns. Deliberately **no** automated
alignment score and **no** human-reliability score. The **green-collapse rule** governs what renders
collapsed-vs-expanded: a requirement may be collapsed **only** if both fully covered **and** it
carried a falsifiable intent-keyed reconstruction claim the adversarial comparator actively tried to
break and could not; MNFs and thin/ambiguous spans are **force-expanded**; "absence of a flag is
never rendered as presence of alignment."

> **Open question (instrumentation, flagged).** Neither `PLAN-ALIGNMENT-GATE.md` nor
> `OBSERVABILITY.md` specifies **how** a parked-TUI / GUI sign-off surface captures *engaged
> attention* (vs wall-clock) when the user may not be attached to the L1 pane. ③ records the
> capture mechanism as a **data-contract** (per-item `opened`/`collapsed` events + an
> attention-timing event stream keyed by the one-spine address), and defers the exact capture signal
> (GUI focus events vs explicit-expand-clicks-only) to the later GUI pass. The docs assert the
> metric; ③ pins the event shape, not the focus-detection.

### 5.2 Channel (b) — the out-of-band L1→user attention channel (no silent degradation)

A parked L1 TUI the user isn't attached to must **NOT** be the only alert path — this is the
**no-silent-degradation** requirement. This channel is distinct from the bus: it pushes **off the
harness** to the human.

**This channel has no seat in ① or ② — it is wholly ③'s to design net-new.** ① only guarantees the
events exist and are journaled (`FAILED`, `coordinator_died`, `died_*`, the spawn-failure
escalation); ② emits them. There is no existing push mechanism in the source docs to bind to.

**Severity → channel mapping (③ authors this; the docs fix only the anchor points):**

| Severity | Channel | Source-fixed? |
|---|---|---|
| **Blocking** — spawn-failure / model-runtime mismatch (E32), any MNF-touching change, the severity ③ assigns to ②'s `FAILED`/`died_*` events | **PUSH** (off-harness) | **only** the E32 spawn-failure is source-fixed as L1-terminal + blocking. ②'s `FAILED`/`died_*` arrive **UNtagged** — ② journals neutral events with no severity field; **③ assigns the severity.** |
| **Routine** — normal status / non-blocking escalation (the normal escalate-options channel) | **PULL-inbox** (the bus inbox, §2) | routine = pull is fixed |

> **Provenance precision (③ owns the severity classification).** ② emits its events
> (`FAILED`, `stale_suspect_opened`, `recovery_probe_started`, `ownership_replaced`,
> `coordinator_died`, `died_*` — WATCHDOG §11.1) **untagged**: none of them carries a severity field.
> The **one** source-fixed blocking anchor is the **E32 spawn-failure** (an ①/genesis-stamped
> escalation, DAEMON §6.3/§7). For everything else, **③ owns the severity → channel assignment** — do
> not read the table as ② pre-classifying its events as blocking; ② journals neutral facts, ③ maps
> them to a channel.

The **spawn-failure payload is fully spec'd and is the template for all blocking pushes** (E32,
`runtime-and-model-map.md`): `{child address, configured(model/runtime), actual(model/runtime) the
endpoint would have served — or "none — runtime down", which of the three failure classes fired}`,
rendered as the concrete sentence "could not run `<address>` on its configured `<model>/<runtime>`
(reason: `<class>`); the endpoint would have served `<actual>` instead. No work was run on a
substitute." The user's decision set is `{retry / re-config the level / accept a different model
explicitly}`. A trace-checker enforces the invariant (every spawned child's `model_used` ==
configured, **else** a corresponding L1 spawn-failure escalation + user alert must exist) — **③'s
push channel is what makes that invariant satisfiable.**

> **FORK — for user review (the v1 push transport floor).** The docs fix the *principle*
> (no-silent-degradation) and the *payload*, but name **no concrete push transport** (Hue / ntfy /
> OS-notify / email appear only in the cluster prompt, not the source docs). At least one working
> push path must exist in v1 for the no-silent-degradation requirement to hold.
> - **Option A (RECOMMENDED): `ntfy` (or an equivalent HTTP push-to-phone) as the v1 floor**, with
>   the alert as a structured payload (the E32 sentence + decision set + the one-spine address). It
>   is a single outbound HTTP POST from the harness app, no inbound listener, no extra daemon, works
>   while the user is away from the machine, and degrades to the pull-inbox if it fails. The push is
>   itself **best-effort** — the durable escalation already lives in the journal + work-node doc, so
>   a missed push is recovered by the pull-inbox (the channel obeys the same truth-in-files model).
> - **Option B: a desktop OS-notification (macOS notification) as the floor.** Pro: zero external
>   dependency. Con: useless when the user is away from the machine — weak against the
>   parked-TUI-isn't-the-only-path requirement.
> - **Option C: Hue light signal as the floor.** Pro: ambient, non-intrusive. Con: carries no
>   payload (a color is not a decision set) — it can only *summon* the user to the pull-inbox, so it
>   is a complement, not a sufficient floor on its own.
> - **Recommendation: A as the v1 floor (a payload-carrying push that reaches the user off-machine),
>   with B/C available as additional ambient complements.** All are best-effort over the durable
>   journal; the push never carries the only copy of the fact.

### 5.3 Channel (c) — the human control surface

Three primitives, all resting on ①'s single-writer path, hosted by the harness app. ③ specifies them
as **data-layer ops addressable by node** (the rendering altitude is the deferred GUI pass's call).

1. **Pause-subtree** — a **flag** the spawner/watchdog **respect** (not a kill). ③ specifies it as a
   binding/control field keyed on the one-spine address prefix. ③ defines the data op (the field +
   that it is checked before spawn/prod under the flagged prefix). **The enforcing READERS are owed
   from ①/② — they are not yet seated** (DAEMON §9's "Seats Provided to ③" lists only terminal-signal
   journaling + human-kill + the answer slot, **not** a pause flag the chokepoint reads; WATCHDOG
   never mentions pause). ③ flags two owed read-points exactly the way `gate_crossed_at` and the
   re-adopt edge were owed before they landed (§10.2): (a) a pre-step in ①'s spawn chokepoint
   (the §6.1 claim-slot pre-step is the natural site — check the flagged prefix before claiming) and
   (b) a check in ②'s recovery loop (hold off prodding/respawning under the flagged prefix). **Until
   both land, pause-subtree is a written flag with no enforcing reader.**
2. **Human-kill** — routed **THROUGH the single-writer executor's stamping path, NEVER raw tmux** (a
   raw `tmux kill` desyncs the ledger). It is a CAS-guarded `transition` presenting
   `expected_owner_token` + `expected_generation` (DAEMON §4.1). ②'s **reap policy still applies on
   ③'s channel**: leaves-only for routine reap; **only L1 may force-reap at any depth** (the
   emergency override — destructive, requires explicit confirmation, `agent-lifecycle.md` §135); the
   god-view layer is read-only and cannot kill. The same CAS is the **double-kill interlock** — a
   second killer's stale token aborts (§7).
3. **Answer-injection slot** — where a human-supplied escalation answer enters. It **rides
   `terminal_signal = ESCALATED` + `terminal_note`** (DAEMON §9) and feeds the §4 answer-down path
   (Branch A decision doc + downward wake, or Branch B delta-brief payload class). **The human sits
   ABOVE the parent, so the answer has a first hop that §4 does not by itself cover** (§4's both
   branches are a PARENT acting on a CHILD; writing `terminal_note` onto the escalating child's
   binding does not, by itself, re-activate the parent coordinator that must run §4 — and that parent
   may be a parked, unattended L1, the exact actor §5.2 says you cannot assume is attached). So the
   answer-injection slot, **after stamping the answer through the executor, fires a §3 wake at the
   PARENT coordinator that owns the escalation** — the next-up node by prefix-truncation of the
   escalating child's address — with the wake message "human answer posted for `<child>`, execute the
   decision-down." On wake the parent reads the answer and runs Branch A or B normally. This reuses
   the **same §3 send-keys wake + prompt-gate + sender-side fence** — no new mechanism, just the
   missing human→parent hop named. For MNF / user-confirmed-`delegated` changes this slot overlaps
   with the §5.1 sign-off transport (those re-enter the human gate specifically).

**Control-surface data model (the dual-rendering split).** The control surface reads the **same
underlying data** the GUI will render: per-node `liveness_state` (`working|waiting|idle|dead`) +
lifecycle `state` — **rendered as DAEMON §3.3's actual enum**
`planned|claimed|spawning|running|blocked|done|failed|dead`, **not** as raw `collapsed`/`resurrected`
values (those are not ①-owned states). Two pins the surface must honor so it does not surface state
values ① does not own:

- **"collapsed" is a DERIVED predicate, not a state value.** Per DAEMON §3.6 the node is collapsed
  iff `state ∈ {done, failed, dead}` — and **specifically NOT** the `ESCALATED`-but-alive case
  (`terminal_signal = ESCALATED` while `state` stays `running`). The control surface must compute
  "collapsed?" from `state`, never read a raw `collapsed` state, or it will mis-render an
  ESCALATED-but-alive node as collapsed — the precise §3.6 trap (`terminal_signal != null` does
  **not** imply collapsed) and the exact asymmetry §4 spends a callout defending.
- **`resurrected` is out-of-scope (owed OBSERVABILITY vocab), not an extant binding value.** It
  appears nowhere in DAEMON's lifecycle enum and is flagged by WATCHDOG §12 as an unreconciled
  `resurrected`-vs-`recovered` audit-vocab item (`OBSERVABILITY.md` §23). ③ does **not** surface it as
  a state; it is named here only as an owed OBSERVABILITY reconciliation, not a value the control
  surface reads.

Plus gate status and the deliverable-ledger state. Per
`GUI-DESIGN.md`'s dual-rendering principle, ③ designs the **structured-text/data path** (what the
surface reads/writes); the visual path is the deferred GUI pass. Everything the surface touches is
**addressable by the one-spine node address** — the universal routing key across all of ③'s channels
(`OBSERVABILITY.md` §2: every event is filterable by dotted-ID/address prefix).

### 5.4 The gate-field seam (③ must not invent a parallel gate field)

Channel (a)'s PASS verdict flips a "deliverable-ledger gate state." ③ must **reconcile this with
`gate_crossed_at`** — the field **② flips** (via `watchdog-checkpoint`, on the closed trigger set:
review-gate + plan-alignment-gate approval) and **① enforces** (the resume firewall reads it). ③
must **NOT invent a parallel gate field.**

> **Dependency on the DAEMON author — CONFIRMED PRESENT in ① (no longer owed).** `gate_crossed_at`
> is now **in the DAEMON §3.2 binding yaml** (line 329: `gate_crossed_at: null  # resume-firewall
> flag (§6.4) … ② maintains it; ① reads it to REFUSE --resume`). The field is in the schema; the
> §5.4↔gate handshake is wireable. The ①↔③ handshake stands: **③ surfaces the human PASS verdict;
> the executor stamps the `gate_crossed_at` flip + the `candidate`→`frozen` freeze; ③ never writes
> the ledger.** (WATCHDOG §9/§12 still frame the field name as a fork/owed addition against an
> earlier DAEMON revision — ②'s stale note, not ③'s; see §10.)

---

## 6. Pull-Visibility Read-Path (gap-review IMPORTANT #5)

Upward visibility is **PULL**: a parent reads its subtree roll-up **on demand**; only milestones are
promoted (event-driven). Between events the parent reads the child's **living docs** for ambient
awareness — that is the pull substrate.

### 6.1 The concrete read op — a deterministic glob, no aggregate

The read-path is a **deterministic newest-mtime-first glob of `status.md` / `plan.md` / `report.md`
under the parent's address PREFIX**. **No agent maintains a separate aggregate** — an
agent-maintained roll-up doc would be a **second source of truth** (forbidden). The binding-ledger
tree's one-spine key (DAEMON §3.1) makes the prefix arithmetic exact: parent = truncate last
segment; subtree = prefix match. The "Living Docs as Navigation Layer" rule (`WORKSPACE-SCHEMA.md`)
guarantees **files never move**, so prefix-glob paths stay stable; collapsed-node roll-ups are
readable too within the 2-week resurrection window (the frozen brief + report + transcript are
keyed by the stable address).

Concrete file locations (`WORKSPACE-SCHEMA.md`): project-level `status.md` (the central
area+workstream board, not task detail) + `log.md` (append-only); per-area / per-workstream
`plan.md` (living status); per-task `report.md` (templated, living-then-immutable). The glob over
the parent's prefix, newest-mtime first, **is** the subtree roll-up — with no aggregate maintained.

### 6.2 Scope — reconciled (direct-children vs full-subtree)

The source docs contradict on scope (CONTRADICTION #9: `agent-lifecycle.md` "monitors only DIRECT
children" vs `comms-protocol.md` / `COMMUNICATION.md` "your subtree"). The reconciliation
(`agent-lifecycle.md` §Cascading-Failure settles it, and ②'s roll-up confirms it):

- **The ACTION scope is direct children.** A level *acts* on (spawns, reaps, gates) its **direct
  children** only.
- **The VISIBILITY scope is the full subtree.** The read-DOWN roll-up globs the **whole subtree
  prefix** — this is what lets a coordinator never be judged idle while live work exists two levels
  down (the harness keeps a `liveness_state = waiting` distinct from `idle` precisely so the roll-up
  can tell a quiet-with-live-descendants coordinator from an actionable one, DAEMON §3.2 / WATCHDOG
  §5.4).

So ③'s pull read op is a **full-subtree-prefix glob** (visibility); the **act-on-direct-children**
constraint is a policy ① / ② enforce, not a transport restriction. F34 keeps the read scope to
own-subtree + parent + same-parent siblings; cross-neighborhood need escalates to the common
ancestor, it does **not** widen the read.

---

## 7. Nudge Routing + the Quiesce-Then-Reap Interlock (IMPORTANT #4)

### 7.1 Addressing

Nudges address the **one-spine node-address** (DAEMON's binding-ledger tree) — the same key as
workspace-path / requirement-ID / git-branch / visibility-scope (`OBSERVABILITY.md` §2). The
**`#role` suffix** (`#exec` / `#review` / `#test`) routes to **co-located seats** at one node, so the
bus can address "the reviewer at the gateway node" without knowing which instance holds the seat. The
address is **stable across respawn** (F35) — bound to the node, not the instance.

**Transport vs policy stay separate (B16/B17/B18).** The bus *can* deliver between any two addresses
(transport capability); whether a message is *allowed* is a policy decision the visibility/spawn-
scoping layer enforces, **not** the bus. Downward messaging within the subtree is unrestricted
(authority flows down, F36); the bus stays a **dumb gauge** that knows nothing about levels, roles,
or correctness.

### 7.2 The quiesce-then-reap interlock (the nudge/transition race)

A wake/nudge can land on a pane being concurrently collapsed, or on a **fresh** instance that took
the seat (addresses survive respawn). Two killers can race (a parent-collapse + a watchdog-reap).
The interlock **reuses ②'s policy and ①'s CAS for the kill side, and a sender-side binding-read for
the wake side — ③ adds no new lock domain.** The two sides are fenced by **different** mechanisms
(CAS-fenced mutation vs sender-side-checked keystroke), spelled out below so a builder does not
conflate them:

- **The kill decision (a ledger mutation) is CAS-fenced by the executor.** Every reap/collapse is a
  CAS-guarded `transition` presenting `expected_owner_token` + `expected_generation` (WATCHDOG §5.4
  FORK Option A — RECOMMENDED). A second killer's stale token **aborts** — the same fencing that
  solves split-brain solves double-kill. ② issues the reap through the executor; whoever's CAS lands
  first wins, the loser aborts cleanly. **This is a CAS the executor enforces** — the kill genuinely
  passes through the one-writer mutation path.
- **The wake (a raw keystroke) is fenced DIFFERENTLY — by a sender-side pre-send read, not the CAS.**
  `send-keys` does **not** route through the executor, so there is no CAS to abort it. The wake is
  made safe by the §3.2 precond-2 check: **before** emitting the keystroke the sender re-reads the
  live binding and **aborts the send** if the `owner_token`/`lease_epoch` is stale, the `session_uuid`
  doesn't match, **or** the lifecycle `state` is in the collapsing/terminal set `{failed, dead}`. The
  state-read is the part that closes the **mid-collapse window** the epoch-bump alone leaves open: the
  `lease_epoch` is re-minted by a **new claim** (DAEMON §8), **not** by the kill transition — so
  between (1) a collapse/reap CAS landing on the current instance and (2) a successor claim re-minting
  the epoch, the binding still holds the **old, non-stale** `owner_token`. A wake observed-and-sent in
  that window would carry a token that is *not* stale, pass a token-only check, and land `send-keys`
  on a pane that is logically dead but possibly still at the prompt. Because the kill transition stamps
  `state ∈ {failed, dead}` through the single-writer executor **before** the pane is torn down, the
  sender-side **state-read** aborts the wake even while the epoch is momentarily still fresh. So the
  interlock = **token-freshness AND incarnation-match AND not-collapsing**, all read from the binding
  immediately before send (§3.2 precond-2). The fresh instance, if one already took the seat, re-derives
  its state from the durable inbox + docs regardless. **Do not call this "the same CAS" as the kill
  path — it is a sender-side-checked keystroke, deliberately contrasted with the CAS-fenced mutation.**
- **The roll-up race rule near a collapse (WATCHDOG §5.4) ③ must honor:** a kill/collapse on a
  coordinator's idle requires **BOTH** (1) the live-descendant roll-up is **COLD** (no live
  descendants) **AND** (2) **no `slot_claimed` / `spawned` run-ledger row for any descendant within
  the last W**. Condition 2 closes the race where a grandchild spawns just after the roll-up read but
  before the action lands. ③'s nudge routing must not assume a node is collapsible just because its
  roll-up read cold a moment ago — the executor's CAS + the no-spawn-in-W gate are the authority.

This is the IMPORTANT #4 resolution: `send-keys` has no ack and no ordering, but the owner-token
fence + the single-CAS-writer-to-the-kill-decision + the no-spawn-in-W gate make a misrouted or
out-of-order nudge a clean no-op rather than a corruption.

---

## 8. What ③ Provides to ④ (Scale-as-resource)

③ provides ④ **nothing new in the mutation path** — same as ②. Everything ④ governs (admission
control / 429-backoff / per-runtime ceilings / resource envelope) wedges at ①'s **claim-slot
pre-step** in the spawn chokepoint (DAEMON §6.1), between claim-accepted and actor-open, without
re-opening the CAS. ③'s two paths that (re)spawn — the escalation-answer-down to a collapsed child
(§4.2) and any fresh-spawn-on-gate-firewall (§4.3) — both route through that same chokepoint, so ④'s
ceilings/backoff gate them **automatically**.

What ③ *does* expose for ④'s eventual use:

- **The severity → channel mapping (§5.2)** is the natural place a ④-driven "deferred due to resource
  ceiling" notice would surface to the user (routine = pull-inbox; a ceiling that blocks required
  work = a blocking push). ③ defines the channel; ④ defines when to use it.
- **The pull-visibility read op (§6)** is the read-path ④'s resource accounting reads node state
  from (it is a glob, not a privileged API) — ④ adds no parallel read channel.

③ defines no admission policy, no ceilings, no backoff — those are ④'s, named out-of-scope here.

---

## 9. Forks Recorded for User Review

1. **§2.1 — the bus transport.** Per-node append-only inbox file + tail (RECOMMENDED) vs socket/Redis
   pub-sub. Recommendation: the inbox file — it is the only option that preserves truth-in-files /
   pointer-not-payload / best-effort and self-heals on respawn.
2. **§5.2 — the v1 out-of-band push transport floor.** `ntfy`/HTTP-push-to-phone (RECOMMENDED) vs
   macOS OS-notification vs Hue. Recommendation: a payload-carrying push that reaches the user
   off-machine, with OS-notify/Hue as ambient complements; all best-effort over the durable journal.

(The `gate_crossed_at` field name itself is a fork **already owned by ② / WATCHDOG §9** — ③ binds to
its RECOMMENDED Option A, it is not re-opened here.)

## 10. Dependencies ③ Flags

### 10.1 SATISFIED in ① (re-verified against the current DAEMON revision — no longer owed)

- **The re-adopt edge** (§4.2): `claim` admits `expected_state ∈ {running, dead}`. **CONFIRMED
  present** — DAEMON §3.3 lists the `running → claimed` / `dead → claimed` re-adopt edges as
  first-class legality-table members and states `claim` takes an `expected_state` parameter; §6.4
  step 1 re-adopts with `expected_state ∈ {running, dead}`. Branch B type-checks. (Regression note:
  the binding must hold across later ① revisions. WATCHDOG §10/§12 still carry this as an
  owed/blocking dependency against an earlier DAEMON revision — a ② stale-note to reconcile; see the
  feedback hand-back below.)
- **`gate_crossed_at` in the §3.2 schema** (§5.4): **CONFIRMED present** — DAEMON §3.2 line 329
  declares `gate_crossed_at: null` (`② maintains it; ① reads it to REFUSE --resume`). The
  human-sign-off PASS flip is wireable. (WATCHDOG §9/§12 still frame it as a fork/owed addition — a ②
  stale-note; see the feedback hand-back.)

### 10.2 STILL OWED from ① / ② (not buildable until the seat lands)

- **The pause-subtree read-points** (§5.3 primitive 1): ③ defines the **flag** (a binding/control
  field keyed on the one-spine prefix) but the *enforcing readers* are not yet seated in ①/②. DAEMON
  §9 "Seats Provided to ③" enumerates only terminal-signal journaling + human-kill-through-executor +
  the answer slot — **not** a pause flag the spawn chokepoint reads; WATCHDOG never mentions pause.
  ③'s pause-subtree therefore needs **two read-points owed from the DAEMON/WATCHDOG authors**: (a) a
  pre-step in ①'s spawn chokepoint (the §6.1 claim-slot pre-step is the natural site — check the
  flagged prefix before claiming) and (b) a check in ②'s recovery loop (hold off prodding/respawning
  under the flagged prefix). **Until both land, pause-subtree is a written flag with no enforcing
  reader.** This is owed exactly the way the re-adopt edge and `gate_crossed_at` were before they
  landed — see the feedback hand-back.
- **The Codex/L5 pane wake** (§3.4): the `send-keys` wake is measured only for the Claude-Code pane
  (H40); the Codex adapter's prompt-string + capture surface is owed (DAEMON §6.3). The Codex pane
  inherits the same neutral wake contract via an adapter-supplied capture surface.

---

## 11. ARCHITECTURE.md hand-back

On completion, `ARCHITECTURE.md` §Communication-and-Visibility (the "Transport-spec stub") should
point at **this document** rather than carrying the stub inline — the stub
(own-bus / truth-in-files / pointer-not-payload / best-effort / terminal-signal-fact-journaled) is
now fully specified here. This closes the doc-level half of gap-review #5.
