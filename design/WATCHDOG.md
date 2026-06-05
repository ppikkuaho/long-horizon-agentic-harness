# WATCHDOG — Liveness & Lifecycle (Cluster ② spec)

Status: design, v1 cut. This is the **liveness & lifecycle** layer. It **sits on** the cluster-①
substrate (`design/DAEMON.md`, DONE) and uses its seats; it does **not** redesign them.

This document specifies the watchdog *body*: the detector, the evidence-lease recovery
state-machine for persistent coordinators, the light sign-off-or-fail path for ephemeral leaves,
the leaf/coordinator split and recover-vs-reap choice, the wedge detector, L5+ reviewer liveness,
the state-sensitive suspicion windows, gate detection, and the fencing-into-recovery wiring.

It **promotes to canon** the recovered evidence-lease design
(`research/orchestration-frame/phase-2-runs/research/watchdog-design-01.md`) and mines the recovered
partial impl (`research/orchestration-frame/self-improvement-harness/watchdog.py` + its `WATCHDOG.md`)
for the concrete grace-counter and observer-writes-through-the-executor mechanics. The daemon
(cluster ①) **already carries every field** the lease machine reads/writes (DAEMON.md §3.2, §9);
this doc binds to those exact names and writes them **through the executor**, never directly.

> **The prime directive (locked, falsified-by-research timeout-kill is OUT).** Liveness expiry
> does **not** mean "kill" or even "declare failed." It means *"the control plane now suspects
> staleness and must OBSERVE"* (`watchdog-design-01.md` L121). A node moves to a confirmed-failed
> condition **only on explicit evidence, not on elapsed time alone** (`watchdog-design-01.md` L83).
> The repo's own research (watchdog-design-01.md + ARCHITECTURE-FINDINGS F-011/F-012) already
> falsified the timeout-kill model; this doc does not re-introduce it.

---

## 1. Charter & Scope

### 1.1 What cluster ② OWNS (the v1 INCLUDE / sufficiency cut)

1. The **evidence-lease recovery state-machine** for **persistent coordinators** — the full machine
   (`healthy → stale_suspect → recovery_in_progress → failed_confirmed`), observer-renewal,
   state-sensitive suspicion windows, the `observe → renew / adopt / respawn` recovery path,
   and the failed-only-on-evidence rule (§3).
2. The **light sign-off-or-fail path** for **ephemeral leaves** (L5 / L5+): idle + non-terminal →
   prompt-string-gated graded prod → bounded retries (reset on resumed activity) → record `FAILED`
   via the executor (§4).
3. The **thin detector** behind the stable interface `liveness(node) -> {working|waiting|idle|dead,
   last_progress}` — day-one floor = transcript-JSONL growth + tmux pane-alive; the multi-signal
   fusion is deferred **behind** this interface (§2).
4. The **leaf/coordinator split**: the coordinator process-death probe (consume ①'s `coordinator_died`
   **run-ledger event** — keyed off the event / lifecycle `state = dead`, **not** a standing field),
   the **recover-vs-reap choice** on a dead coordinator (adopt / respawn-from-ledger / escalate), and
   **subtree-quiescence gating** (act on a coordinator's idle only when ①'s live-descendant roll-up is
   cold) (§5).
5. The **wedge detector** (W2), **leaf-only**: pane-warm-but-(JSONL + mtime + `pane_pid` CPU all flat)
   → wedged → kill + escalate (un-proddable). Requires `pane_pid` CPU, promoted to the v1 floor for
   the wedge path only (§2.3 signal 3 / §6 DECISION); armed only after W2 is commissioned (§6/§8) —
   escalates-not-kills until then (§6).
6. **L5+ reviewer liveness** — the reviewer is a real spawned ephemeral seat; its terminal artifact
   is the verdict file; on its death, cold-respawn against the frozen rubric (§7).
7. The **state-sensitive W / W2 suspicion windows** — *how* they are set (per task type + liveness
   state, set at spawn, settled empirically in commissioning); the numbers are KNOWN-OPEN (§8).
8. **Gate detection** → maintaining ①'s `gate_crossed_at` field (the resume firewall reads it) (§9).
9. **Fencing wired into recovery** — bump `lease_epoch` / re-mint `owner_token` on adopt/respawn via
   ①'s `claim`/`transition` executor commands (§10).

### 1.2 What cluster ② CONSUMES from cluster ① (the seats — bind, do NOT duplicate)

② is the **loop body / detector / recovery state-machine**. ① owns the loop *scheduling*, the
*fields*, and the *write path*. Every seat below is named at its exact DAEMON.md address.

| ② needs | ① seat (exact name) | DAEMON.md |
|---|---|---|
| Write the liveness verdict | `liveness_state` (`working\|waiting\|idle\|dead`), `last_progress_at`, `last_heartbeat_at` | §3.2 |
| Carry the lease condition | `condition`, `suspect_since`, `stale_check_count` (schema addition requested of ① — see §3.5), `recovery_attempts`, `stale_grace_checks`, `last_evidence` | §3.2 |
| Read/write a state change | `transition` (CAS) and `watchdog-checkpoint` executor commands | §4.2, §4.5 |
| Read the sign-off | `terminal_signal`, `terminal_signal_at`, `terminal_note`, `signal_artifact_seen_at` | §3.2, §3.5 |
| Branch recovery on death class | run-ledger events `coordinator_died`, `died_infrastructure`, `died_methodology`, `stale_return_ignored` | §3.5, §3.6 |
| Carry the auto-resume interlock | `auto_resume_command` (carried) + `allow_recovery` (`--run-recovery`) | §9 |
| Gate the resume firewall | `gate_crossed_at` (② flips, ① enforces) — *schema addition requested of ① (see §9 FORK); §6.4/§9 carry it as a concept, not yet in the §3.2 yaml* | §6.4, §9 |
| Gate coordinator idle | the live-descendant roll-up (prefix scan over the one-spine key) | §5.4 |
| Fence on adopt/respawn | `lease_epoch` + composite `owner_token` rotated by `claim`/`transition` | §8 |
| Run the sweep | the per-node read-tmux-vs-ledger reconcile pass (② plugs `liveness(node)` in) | §5.2 |

**Two-surface discipline (DAEMON.md §3.2).** `liveness_state` + `condition` is the **lease/health**
surface ② writes from tmux; `deliverable_state` + `terminal_signal` is the **semantic/work** surface
the executor writes from terminal signals. ② must not conflate them.

**Single-writer discipline (DAEMON.md §4.1).** *Even the watchdog and the detector write through
the executor.* ② issues **every** state change through `watchdog-checkpoint` (own-slice + one
run-ledger row) or `transition` (lifecycle state change) — never a direct ledger write. Every
mutator presents `expected_owner_token` (DAEMON.md §4.5).

### 1.3 What cluster ② DEFERS (named out-of-scope; owned elsewhere)

| Deferred item | Owner | ② provides |
|---|---|---|
| The bus transport, the actual **send-keys wire**, the wake contract, human channels | ③ | the *preconditions* a prod/nudge must satisfy (prompt-string gate, verify-new-turn-via-JSONL-growth) + the FAILED/escalation events it journals (§11) |
| Admission control / 429-backoff / per-runtime ceilings / resource envelope | ④ | nothing — ④ wedges at ①'s claim-slot pre-step |
| The detector's **full multi-signal fusion** | ② (later) | the day-one thin floor behind the stable `liveness(node)` interface (§2) |
| The continuous-reconciliation **controller** auto-resolution of ambiguous cases | ② (later) | v1 ① escalates ambiguous cases; ② adds auto-resolution at the one escalation seat later (§5.5) |
| The reconcile **sweep loop**, run-ledger format, WAL/atomicity, binding schema, spawn chokepoint, genesis, the **2-week resurrection GC reaper** | ① / infra | ② supplies only the liveness verdict + recovery policy the sweep consumes |

> **Hard boundary on the send-keys wire (③).** This doc specifies *what a prod must do and its
> preconditions* — it does **not** build the wire. Where text below says "prod via send-keys," read
> it as "request a prod from the ③ wire, with these preconditions"; ③ owns the keystroke mechanics
> and the bus.

---

## 2. The Detector

### 2.1 The stable interface

```
liveness(node) -> { state: working | waiting | idle | dead,  last_progress: ISO-8601-UTC }
```

This is the canonical signature and the canonical 4-value enum (DAEMON.md §3.2 `liveness_state`,
confirmed at DAEMON.md §5.2). ② writes the result into the binding `liveness_state` +
`last_progress_at` fields **through `watchdog-checkpoint`** on every reconcile tick.

> **Bind to the 4-value enum, not the 3-value shape.** `runtime-decisions §1` wrote the interface
> loosely as `{alive, working|idle, last_progress}`. The canon is the **4-value**
> `working|waiting|idle|dead`. **`working` and `waiting` are NOT folded** — the waiting-vs-idle
> split is load-bearing for the §5.4 coordinator subtree-quiescence roll-up (DAEMON.md §3.2).
> Optional bookkeeping values `claimed` (pre-spawn) and `terminal` (post-signal) are ①'s.

### 2.2 Liveness is OBSERVED + INFERRED, never self-reported, never wall-clock

Two locked invariants, quoted from the corpus:

- **Observed, not self-reported** (`agent-lifecycle.md` §119; `watchdog-design-01.md` L46:
  *"Heartbeat alone is an input, never sufficient by itself… never infer semantic progress from
  heartbeat alone."*). The detector reads evidence; it never trusts an agent's claim of liveness.
- **Inferred from evidence of progress, not elapsed time** — a legitimately long task stays
  `working` because it is still producing output/file activity (`agent-lifecycle.md` §119).

**Deterministic-vs-inferred split (the demoted promise).** Per gap-review BLOCKING #4: the detector
is **deterministic only for spawn / collapse / comms transitions** (captured by ①'s hooks);
`working` vs `idle` liveness is **inferred with bounded confidence** from the floor signals. This
doc does not claim deterministic `working/idle`. The confidence bound is stated where it bites: the
**false-idle edge** (§2.4) and the prod gate (§4.3) are the explicit guards against acting on a
wrong inference.

### 2.3 The day-one thin floor (v1) and the deferred fusion (behind the interface)

**v1 floor (INCLUDE):**

1. **transcript-JSONL growth** *(general detector)* — the strong Claude-side forward-progress signal.
   JSONL size/mtime advancing ⇒ `working`; flat ⇒ candidate for `idle`/`waiting`/`wedged`
   (disambiguated below).
2. **tmux pane-alive** *(general detector)* — `pane_dead` / `pane_pid` liveness. Pane gone ⇒ `dead`
   (consume ①'s process-death path; for a coordinator this is `coordinator_died`, §5.1).
3. **`pane_pid` CPU** *(wedge path ONLY — promoted from the deferred-fusion set by the §6 DECISION)* —
   a single `ps` on the one pane's pid, used **only** by the wedge verdict (§6) to separate a long
   quiet model turn (CPU spikes during generation) from a hung syscall (CPU ≈ 0). It is **not** part
   of the general working/idle floor — the general detector still keys off signals 1–2 only.

**Deferred fusion (behind the interface, NOT the general v1 floor):** `window_activity` +
node-file mtime + `pane_pid` CPU *as a general working/idle signal* (CPU is in the v1 floor for the
wedge path **only**, signal 3 above — it is **not** fused into the general working/idle verdict in
v1), and the **H40 outbound-payload oracle** (`OBSERVABILITY.md` §4.5 — the final outbound request
payload at the query boundary, the cleanest "what did the model see" signal) as a prompt/activity
source. These are *examples the detector MAY fuse* (DAEMON.md §5.2), not the general v1 floor. The OTEL / LLM-API-call signal (old `NOTES.md:869` "Active-vs-Waiting from API calls in
progress") is **deferred** — the documented detector cannot run in v1; the floor is JSONL-growth +
pane-alive. Which signals are fused and how is ②-internal; ① owns only the interface + the field.

> **FORK — for user review.** `semantic_event_at` (the `last_evidence` sub-field reserved for ②'s
> semantic detector, DAEMON.md §3.2, null in v1).
> - **Option A (RECOMMENDED): keep `semantic_event_at` null in v1; treat JSONL-growth as the
>   forward-progress floor and the semantic-trace renewal as deferred behind the interface.** The
>   thin floor (JSONL-growth + pane-alive) is sufficient to renew the lease (a successful liveness
>   read showing forward progress *is* the renewal); semantic-event detection (parsing the transcript
>   for meaningful work vs spinning) is a fusion upgrade, not a v1 floor dependency.
> - **Option B: promote a semantic-trace probe to v1** (parse JSONL for tool-call/edit events, not
>   just byte growth), writing `semantic_event_at`. Pro: catches a "growing-but-spinning" transcript
>   the byte-growth floor would read as `working`. Con: it is exactly the fusion the sufficiency cut
>   defers, and it adds a transcript-parser dependency the floor avoids.
> - **Recommendation: A.** Byte-growth + pane-alive is the agreed v1 floor; `semantic_event_at`
>   stays null and the semantic detector lands behind the interface when the false-read rate bites
>   (the runtime-decisions §3 pull-trigger).

### 2.4 The false-idle edge (the working-vs-waiting-vs-idle boundary)

The corpus names the boundary but leaves the leaf case to ② (open question across all three
operational docs). The detector must distinguish three flat-JSONL cases for a **leaf**:

- **`working`** — JSONL still growing (or grew within W). Never acted on.
- **`waiting`** — flat JSONL but a legitimate reason to be quiet: the leaf is blocked on an
  answer-round-trip (`terminal_signal == ESCALATED`, DAEMON.md §3.6) or, for a coordinator, has live
  descendants (§5.4). `waiting` is **not** actionable.
- **`idle`** — flat JSONL, pane warm, **no** legitimate reason (not escalated, no live descendants):
  the candidate-stalled state the sign-off-or-fail path acts on (§4).

> **The false-idle hazard (gap-review IMPORTANT #9/#10).** The spinner/TUI keeps a pane **warm**
> through a long, quiet model turn — pane-warmth alone gives a **false-idle** read. This is exactly
> why the v1 floor uses **JSONL-growth** (not pane-warmth) as the forward-progress signal, why the
> wedge detector (§6) requires JSONL **+ mtime + CPU all flat**, and why Codex/L5 (a long-quiet
> single-turn) is the most exposed seat. **Commissioning gate (§8):** Codex pane-warmth is
> ASSUMED-not-verified — if first-run measurement shows Codex panes do not stay warm the way
> Claude's do, the Codex session-log probe is promoted to a v1 requirement.

---

## 3. The Evidence-Lease Recovery State-Machine (persistent coordinators)

> **Adapted from `watchdog-design-01.md`: reused / changed.**
> *Reused, verbatim in model:* the four-condition machine `healthy → stale_suspect →
> recovery_in_progress → failed_confirmed` (L10) with **`stale_suspect` as a same-state OBSERVE
> buffer, not a kill**; observer-based renewal + the heartbeat-insufficient rule (L40–46); the
> **state-sensitive suspicion windows** keyed on runtime state (`waiting_on_child` tolerates longer
> silence than `writing_final_output`, L59); the **8-step recovery path** (L72–83) as
> `observe → renew / adopt / respawn`; the **failed-only-on-evidence** rule (L83); the **escalate-vs-
> auto-advance** boundary (L85–99); the **stale-grace counter** (`stale_check_count >=
> stale_grace_checks` before escalation, default 2; `watchdog.py` L205–266); the new ledger-event
> vocabulary (L109–117).
> *Changed for the tmux/daemon runtime:* (a) **renewal source** — the design's
> `work_scoped_agent.py observe` (a process-registry handle) has no tmux analog; replace with the
> `liveness(node)` read over JSONL-growth + pane-alive (§2); the "runtime handle disappears from
> observe" stale signal becomes "`pane_pid` dead" = consume ①'s `coordinator_died`. (b) **scheduler
> ownership** — drop the standalone `watchdog.py` `main()/--watch` loop + its `fcntl` single-instance
> lock; ② is a **verdict + policy function invoked by ①'s in-process sweep**, not a separate polling
> daemon (DAEMON.md §1.2, §4.1). (c) **do not re-declare fields** — the design *proposed*
> `manifest.watchdog.*`; DAEMON.md §3.2 **already carries** every one as a per-node binding seat. ②
> binds to ①'s names and writes through `watchdog-checkpoint`/`transition` — no `manifest.watchdog`
> block, no parallel state. (d) **terminal vocabulary** — the impl's
> `TERMINAL_STATES={stopped,blocked,cancelled}` (loop lifecycle) is remapped to ①'s `terminal_signal`
> enum and the §3.6 mapping table.

### 3.1 The four conditions — the canon machine, mapped onto ①'s carried `condition` field

The canon machine is the design's four conditions. ①'s `condition` field (DAEMON.md §3.2) carries a
**superset** enum (`never_checked | healthy | inactive | stale_suspect | recovery_required |
recovery_in_progress | terminal | invalid`). ② canons the **four** and maps the impl's extra values
as sub-states. The naming seam (`failed_confirmed` has no exact 1:1 value in ①'s enum) is closed
below.

| Canon condition (② machine) | `condition` value(s) written | Meaning | Action |
|---|---|---|---|
| **healthy** | `healthy` | renewal current; forward progress observed | renew on each successful read; no ledger spam (edge-triggered) |
| **stale_suspect** | `stale_suspect` | renewal overdue, ≥1 stale signal weakened — **same-state observe buffer, NOT a kill** | open suspicion (`suspect_since`, event `stale_suspect_opened`); re-check next poll |
| **recovery_in_progress** | `recovery_in_progress` (or `recovery_required` if no `auto_resume_command` available) | past the grace window; running probes / adopting / respawning | run the recovery path (§3.4) |
| **failed_confirmed** | **`terminal`** + a `died_*` `terminal_signal` (see FORK) | recovery exhausted **on explicit evidence** | stamp the death class; lifecycle → `failed`/`dead`; escalate to parent |

`inactive` (an unowned lease with open downstream work) is carried as a distinct ①-value, treated as
the **unowned-open-work** blocker (the design's `inactive != idle` rule, `watchdog.py` L182–203,
`blocker_class: unowned_open_work`): a node with **no owner** but **unresolved descendants** stays
**operator-visible**, not silently parked. **Its recovery-path entry (§3.4 / §5.5):** when the
detector classifies a node `inactive` (no owner + unresolved-descendants — distinct from `idle`,
which is owned-but-quiet), ② routes it to the **escalation seat** (§5.5) — the same conservative v1
stance taken for every ambiguous case ("don't auto-recover past a break — freeze and examine"). It is
**not** prodded (no owner to prod) and **not** auto-reaped (live downstream work). This is the
concrete prototype for the subtree-quiescence gate (§5.4): "unowned + live descendants ⇒ surface, do
not park" is exactly the gate's logic at a single node. `invalid` is the fail-closed validation state
(carried by ①).

> **FORK — for user review (the naming seam ① flagged).** How to express **`failed_confirmed`**,
> which has no exact 1:1 value in ①'s `condition` enum.
> - **Option A (RECOMMENDED): express it as `condition = terminal` + a `died_*` `terminal_signal`**
>   (`DIED_INFRA` / `DIED_METHODOLOGY`) + lifecycle `state ∈ {failed, dead}`. No new `condition`
>   value; uses ①'s existing carried set and the §3.6 mapping table; "confirmed-failed" is then a
>   *derived* predicate (`condition == terminal AND terminal_signal IN died_*`), not a fifth raw
>   value to keep in sync. Matches DAEMON.md's own open-question note (the closest is `condition =
>   terminal` + a `died_*` signal).
> - **Option B: add `failed_confirmed` as a literal `condition` value.** Pro: the field reads
>   exactly like the design's vocabulary. Con: requires the DAEMON author to extend the enum; creates
>   two places that mean "confirmed failed" (the `condition` value and the `terminal_signal`),
>   inviting drift — the precise anti-pattern DAEMON.md §3.6 warns against ("do not unify by
>   renaming; translate through the table").
> - **Recommendation: A.** Keep `condition` as the lease-health surface and let the **terminal**
>   condition + `died_*` `terminal_signal` carry "confirmed failed." This honors the two-surface
>   split and the §3.6 normative table. *(Requires confirmation from the DAEMON author only that
>   `condition = terminal` is the agreed terminal-lease value — no enum extension needed.)*

### 3.2 Observer-based renewal (the load-bearing invariant, reused verbatim)

> **Renewal MUST come from an observer, never from the child self-reporting**
> (`watchdog-design-01.md` L40–46). Heartbeat alone is an input, never sufficient; never infer
> semantic progress from heartbeat alone.

In the tmux runtime the **observer is the `liveness(node)` detector** (§2). A **renewal** is a
successful liveness read that shows **forward progress** (`last_progress_at` advanced: JSONL grew).
On a renewal, ② writes `condition = healthy`, refreshes `last_evidence` (`{source: reconcile_sweep,
heartbeat_at, progress_at, semantic_event_at: null}`), and appends `lease_renewed` — **through
`watchdog-checkpoint`**, edge-triggered (no append on a steady healthy poll, DAEMON.md §3.5).

### 3.3 State-sensitive suspicion windows (the mechanism; numbers in §8)

A renewal is **overdue** when `now − last_progress_at > W(state)` — where `W` is a **per-state**
window, not one global timeout (`watchdog-design-01.md` L59). All freshness math uses the **single
canonical UTC clock** (DAEMON.md §4.6 — F-019 manufactured a false 3-hour-stale diagnosis by mixing
UTC and local time). The qualitative ordering is fixed; the numbers are KNOWN-OPEN (§8):

```
W(waiting_on_child)      >  W(working / generic)  >  W(writing_final_output)
```

A node `waiting` on a child or an answer-round-trip tolerates longer silence than one that should be
mid-output. The window is keyed on **task type + liveness state, set by the spawning level at spawn
time** (`agent-lifecycle.md` §127 — task type, **not** level identity).

### 3.4 The recovery path (observe → renew / adopt / respawn) — the 8 steps, retmuxed

Adapted from `watchdog-design-01.md` L72–83, with the tmux substitutions from §3 and bound to ①'s
executor commands:

```
1. Renewal overdue (now − last_progress_at > W(state)).
2. OPEN SUSPICION (same-state, NOT a kill): watchdog-checkpoint sets condition=stale_suspect,
   suspect_since=now, appends stale_suspect_opened. Increment stale_check_count (the grace counter, §3.5).
3. PROBE (observe): re-run liveness(node) + read the binding's terminal_signal + the live-descendant
   roll-up. Evidence sources: JSONL-growth, pane_pid liveness, .signal.json presence.
4. ACTOR LIVE + canonical → RENEW: condition=healthy, append lease_renewed (§3.2). Reset
   stale_check_count (the grace counter); recovery_attempts is left intact unless this renewal
   confirms a recovery converged (§3.5). (The stale was transient — a long quiet turn.)
5. ACTOR DONE + durable trigger satisfied (terminal_signal=DONE + signal_artifact_seen_at, OR a
   coordinator_completed row) → AUTO-ADVANCE: transition running → done via the executor. (NOT a
   loop status=stopped — bind to ①'s terminal_signal, §3.6.)
6. ACTOR missing / pane_pid dead / ownership ambiguous → condition=recovery_in_progress,
   append recovery_probe_started.
7. ONE canonical live actor proven (identity test, §3.6 below) → ADOPT: claim the existing address
   (bump lease_epoch, re-mint owner_token via the executor, §10), append lease_recovered. Continue.
8. ELSE → RESPAWN from the durable work node under a NEW epoch via the resume chokepoint (§10),
   increment recovery_attempts, append ownership_replaced.  IF respawn is unsafe/ambiguous OR
   recovery_attempts >= recovery_attempt_ceiling (§3.5) → ESCALATE (§3.5).
```

**Adopt-vs-respawn identity test (the recovered design assumed an `observe` handle; tmux must
reconstruct it).** Before writing a new owner token onto a live pane (step 7 ADOPT), ② must **prove
the pane IS the canonical actor**, in priority order:

1. **`session_uuid` match** — the binding's `session_uuid` appears in the live pane's transcript-JSONL
   path / session id (strongest; the address survives respawn but the session-uuid is per-incarnation,
   DAEMON.md §3.2).
2. **`owner_token` epoch** — the pane's last `watchdog-checkpoint` carried the current `lease_epoch`
   (not a stale one).
3. **`role_file_hash`** — the running role file matches the binding (drift check; DAEMON.md §3.2 open
   surface).

If the identity test is **inconclusive** (no uuid match, ambiguous epoch) → do **not** adopt →
escalate (adopting the wrong pane is the F-012 failure: recovery acting against the wrong owner).

### 3.5 Failed-only-on-evidence + the stale-grace counter (bounded, reset on resumed activity)

> **The F-011 thesis, quoted as the watchdog's prime directive** (`watchdog-design-01.md` L83):
> *"Only move to failed_confirmed, blocked, or cancelled after explicit evidence, not elapsed time
> alone."* Lease expiry → **observe**, never → kill (L121).

**Two distinct counters (do NOT overload one field — the recovered impl keeps them separate).** The
recovered `watchdog.py` carries `stale_check_count` (L132/L206–207 — the **consecutive-stale-poll**
counter, the escalation gate) and `recovery_attempts` (L219/L244 — incremented **only when a recovery
command is actually launched**, the recovery-cycle budget) as **two distinct quantities**. This spec
binds to both, and does **not** collapse them onto one field:

- **`stale_check_count` — the consecutive-stale-poll counter (the grace gate).** A stale lease does
  **not** escalate on first sight. `stale_check_count` increments each consecutive stale poll
  (`watchdog.py` L206: `stale_count + 1 if current_condition in STALE_FAMILY else 1`); first stale
  poll → `stale_suspect` with action "re-check next poll before forcing recovery." Only when
  `stale_check_count >= stale_grace_checks` (DAEMON.md §3.2, default 2) does ② escalate to
  `recovery_in_progress` (`watchdog.py` L211 gate). **Reset rule:** ② zeroes `stale_check_count` on
  **any renewal** (§3.4 step 4 — a liveness read showing forward progress); resumed activity resets
  the grace ladder so the node is not penalized for a prior transient quiet. *(This is the field the
  recovered impl plumbs at L309–310; DAEMON.md §3.2 carries `recovery_attempts` + `stale_grace_checks`
  but NOT this per-poll counter — so `stale_check_count` is the **one carried-field schema addition**
  ② requests of the DAEMON author for the lease machine, alongside `gate_crossed_at`, §12.)*
- **`recovery_attempts` — the recovery-CYCLE budget (how many times the recovery path LAUNCHED).**
  This increments **only when recovery is actually launched** (`watchdog.py` L219/L244 — inside the
  recovery branch, not per stale poll), i.e. once per adopt/respawn attempt in §3.4 steps 7–8. It is
  the **bound on step 8 respawns** (below). It is **NOT** zeroed on a transient renewal — a successful
  adopt must not make the machine forget it already respawned twice; it is reset only on
  **confirmed-healthy-after-recovery** (the recovery converged) so a fresh, clean lease starts the
  budget over. Keeping it separate from `stale_check_count` means "transiently quiet for 2 polls" and
  "recovery has run twice and is not converging" are distinguishable — they are different conditions
  with different actions.

**The respawn-attempt bound (step 8) is `recovery_attempts`, not unbounded.** §3.4 step 8's
RESPAWN-or-ESCALATE is bounded by `recovery_attempts >= recovery_attempt_ceiling` (a per-node
ceiling set at spawn like W, §8; KNOWN-OPEN default — the recovered impl had no explicit ceiling, so
this is a v1 floor ② adds): once the respawn budget is spent without a converged lease, step 8
**ESCALATES** rather than respawning again — closing the respawn-loop hazard a single overloaded
counter would otherwise leave open.

**`failed_confirmed` is reached only via the recovery path exhausting on evidence** (step 8 with no
safe adopt/respawn AND explicit death evidence: `pane_pid` dead + no resumable work node, or a
conflicting-authority escalation that resolves to failure, OR `recovery_attempts` ceiling reached
with explicit death evidence). It is **never** reached by W elapsing.
When reached, ② stamps the death class — `DIED_INFRA` vs `DIED_METHODOLOGY` are **distinct** terminal
classes (F-017) the executor journals as `died_infrastructure` / `died_methodology`; recovery
policy branches on which.

**Escalate (not auto-advance) when** (`watchdog-design-01.md` L93–99): authoritative artifacts
conflict; >1 live claimant and local evidence can't safely pick; abandoning a live actor would be
destructive; repeated `stale_suspect` cycles show no semantic movement and no safe respawn; a true
external blocker appears. In v1 these land at ①'s **escalation seat** (§5.5).

### 3.6 Translating sign-off through ①'s normative table (do NOT rename/unify)

The sign-off the recovery path reads is **the journal**, not loop status. ② translates through
DAEMON.md §3.6's normative mapping table:

- agent tag `DONE/FAILED/ESCALATED` → `terminal_signal` value → run-ledger `signal_*` event →
  lifecycle `state` → collapsed?
- The spelling split is deliberate: binding uses SCREAMING `DIED_INFRA` (value); run-ledger uses
  snake `died_infrastructure` (event); lifecycle uses lowercase `failed`/`dead` (state). **Translate
  through the table; never unify by renaming.**

---

## 4. The Sign-Off-or-Fail Path (ephemeral leaves: L5 / L5+)

The **light** path (vs the full lease machine for coordinators). It is the canonical 3-step
sign-off-or-fail sequence (`agent-lifecycle.md` §121–124), made concrete with the prod gate.

### 4.1 The sign-off the check reads — the JOURNAL, never the nudge

> **The watchdog's liveness check is exactly:** *"is there a terminal-signal event for this node in
> the journal?"* (`comms-protocol.md` §146). It reads the **durable journal** — the `signal_*`
> run-ledger event / the `terminal_signal` field stamped by the reconcile sweep from the durable
> `<node>/.signal.json` (DAEMON.md §3.5) — **not** the transient bus nudge.

A dropped bus nudge can therefore **never** cause a false sign-off failure; it only delays journaling
to the next sweep (DAEMON.md §3.5). Any phrasing like "did we receive the terminal nudge" is a
**direct contradiction** of the contract and is forbidden.

The sign-off tags are exactly the strict 3-set (`comms-protocol.md` §138–142), cited verbatim:

```
signal:  DONE | FAILED | ESCALATED            # strict tag — the only field the sign-off check reads
re:      <node>                               # the node signing off
notes:   <optional, free text>                # DONE note / FAILED reason / ESCALATED question
```

**`ESCALATED` does NOT collapse the leaf** (DAEMON.md §3.6): `terminal_signal` is set but lifecycle
`state` stays `running` and the node is not collapsed — it keeps context and `waits` for the
answer-round-trip. ② must gate any collapse/reap on **lifecycle `state ∈ {done, failed, dead}`**,
**not** on `terminal_signal != null`. An `ESCALATED` leaf reads as `waiting` (§2.4), not `idle`, and
is **never prodded as if stalled**.

### 4.2 The 3-step sequence

```
1. The leaf's loop ends ONLY by emitting a terminal signal (the journaled sign-off) or escalating.
2. IDLE + non-terminal (liveness_state=idle per §2.4 AND no terminal-signal event in the journal AND
   no progress within W) → graded PROD (bounded retry, §4.3), gated on the prompt-string match.
3. Still no sign-off after bounded retries → record FAILED via the executor (§4.4); parent respawns
   or escalates.
```

### 4.3 The prod — preconditions ② owns (the WIRE is ③'s)

A prod is a downward nudge that asks an idle-but-promptable leaf to either resume or sign off. ②
specifies **what it must do and its preconditions**; ③ builds the send-keys wire and the bus.

**Precondition 1 — prompt-string gate (the prod-mid-tool-call guard, the new requirement with no
loop-impl precedent).** A prod is issued **only when the pane shows the idle input prompt** (a
prompt-string match against the captured pane). `send-keys` **can** land mid-tool-call and corrupt
the input line; the prompt-string gate is what stops a nudge interleaving with an in-flight tool
call. If the pane is not at the prompt, the node is **not idle-promptable** — it is either still
`working` (do not prod) or `wedged` (§6, kill+escalate, do not prod). *(The prompt-state evidence
may be drawn from the H40 outbound-payload capture surface, `OBSERVABILITY.md` §124–130, behind the
detector interface.)*

**Precondition 2 — graded, bounded retries, reset on resumed activity.** The prod ladder uses the
**same grace-counter mechanism shape** as §3.5 (count-up, compare against `stale_grace_checks`,
reset on activity) but on the leaf's **own `stale_check_count`** (the consecutive-stale/prod-retry
counter) — **not** `recovery_attempts` (which is the coordinator recovery-cycle budget, §3.5, and is
not spent by leaf prods). A bounded number of prods (the `stale_grace_checks` budget), each verifying
via **JSONL-growth** whether the prod produced a new turn. **Any resumed activity (a new JSONL turn)
resets `stale_check_count`** — the leaf is back to `working`. The retries are *graded* (e.g. a gentle
"are you still working? sign off or continue" first; firmer on subsequent prods) — the grading
content is ③'s wire concern; the **count, the reset rule, and the gate** are ②'s. (A leaf does not run
the coordinator adopt/respawn recovery path, so `recovery_attempts` is untouched on the leaf prod
path — the two counters never share a slot.)

**Precondition 3 — verify-new-turn, no blind trust of the prod.** A prod has **no ack** (`send-keys`
is fire-and-forget, gap-review IMPORTANT #4). ② confirms the prod "worked" only by **observing a new
JSONL turn** (forward progress), never by assuming the keystroke landed.

### 4.4 Record FAILED via the executor — and mark it watchdog-imposed

On exhausted prods with no sign-off, ② records `FAILED` **through the executor** (`transition`
running → failed, which sets `terminal_signal = FAILED`). Two disciplines:

- **Distinguish watchdog-imposed FAILED from agent-self-emitted FAILED** (closing the audit-trail
  conflation the corpus flags). An agent-emitted `FAILED` comes from a `<node>/.signal.json` the
  agent wrote; a watchdog-imposed `FAILED` has **no `.signal.json`** and is stamped by the executor
  on the leaf's behalf for **non-response**. The run-ledger row records `actor: harnessd` and a
  `reason: watchdog_nonresponse` note in `terminal_note`, so the journal does not conflate "agent
  said it failed" with "watchdog declared it failed for silence."
- **Then the parent acts** — respawn (cold, at the stable address — `agent-lifecycle.md` Recovery
  §1–3) or escalate. This prod-then-reap is the **only `prod`-then-reap unilateral kill** ② performs,
  and **only** on an **idle-but-pane-warm non-signing** ephemeral leaf after the bounded prod ladder
  (§5.3). It is **not** the only kill class — §6 wedge-kill is a second sanctioned class (un-proddable
  wedged leaf), and the **process-dead** leaf (`pane_pid` dead) is reaped **mechanically by ①'s
  reconcile sweep → `FAILED`** (DAEMON.md §5.4, the unambiguous resolution); ② does **not** prod a
  process-dead leaf — there is nothing at the prompt to prod. ②'s prod-then-reap is specifically the
  *pane-warm-but-silent* case ①'s mechanical dead-pane reap does not cover.

---

## 5. Leaf/Coordinator Split, Recover-vs-Reap, Subtree-Quiescence

### 5.1 The split — process-liveness probe for coordinators

- **Ephemeral leaf (L5 / L5+):** gets the **light** sign-off-or-fail path (§4). Idle + non-signing →
  prod → FAILED-reap.
- **Persistent coordinator (L1–L4):** gets the **full** lease machine (§3). It is **never** subjected
  to the leaf prod-then-reap path. Its death is detected by the **process-liveness probe**:
  `pane_pid` dead → ①'s daemon stamps `coordinator_died` (which fires on `pane_pid` death
  **regardless of subtree activity** — the cheap orphan-killer, DAEMON.md §5.4). ② **reads**
  `coordinator_died` from the run-ledger (it is an **event**, not a standing binding field — ② keys
  off the run-ledger event / lifecycle `state = dead`, **not** a phantom `coordinator_died` boolean).

**Critical case — dead-pid-but-live-children = a RECOVERABLE ORPHAN, not a healthy-waiting node**
(gap-review BLOCKING #2). A coordinator that has merely gone *quiet* with live descendants is
`waiting` (§5.4). A coordinator whose **process has died** with live descendants below is an
**orphan** — recovered from the ledger, never left hanging (`agent-lifecycle.md` §125). The
`pane_pid` probe is the disambiguator between the two.

### 5.2 The recover-vs-reap CHOICE (cluster ② decides; ① only detects + escalates)

On a `coordinator_died` event, ① has stamped the death + escalated; the **choice** is ②'s
(DAEMON.md §5.4 explicitly defers it). The choice is the §3.4 recovery path applied to a dead
coordinator:

| Evidence | ② choice |
|---|---|
| Durable work node + resume packet intact, no live canonical actor | **respawn-from-ledger** (cold) under a new epoch (§10); append `ownership_replaced` |
| One canonical live actor proven (identity test §3.4) | **adopt** (bump epoch, re-mint token); append `lease_recovered` |
| Authoritative artifacts conflict / >1 live claimant / destructive-to-clean / repeated no-movement | **escalate** (§5.5) — do not guess |

> **Never blind-kill a live coordinator.** A coordinator is **recovered** (adopt / respawn-from-
> ledger / escalate), never reaped (`agent-lifecycle.md` §27, §125). The leaf/coordinator
> kill-authority asymmetry (§5.3) is the locked invariant: only non-signing *leaves* are reaped.

### 5.3 Kill-authority — the locked model

> **FORK — for user review (the gap-review left this as an explicit OR, BLOCKING #3b).** The
> watchdog's kill authority.
> - **Option A (RECOMMENDED): a sanctioned third infra-kill class — "watchdog-reap of a NON-SIGNING
>   LEAF" — scoped to ephemeral L5/L5+ with stated preconditions, plus detect-and-notify-parent for
>   everything else.** The watchdog may **collapse only an ephemeral leaf that went idle WITHOUT
>   emitting its terminal signal**, after the bounded prod ladder exhausted, recorded as `FAILED`
>   (watchdog-imposed, §4.4) — *"a bounded, evidence-based reap of a non-signing leaf… never a blind
>   kill of a live, working session"* (`agent-lifecycle.md` §27, §135). Persistent coordinators are
>   **recovered, never reaped** (§5.2). Everything ambiguous is **detect-and-notify-parent / escalate**.
> - **Option B: detect-and-notify-parent ONLY (zero unilateral kill).** The watchdog never collapses
>   anything; it records FAILED and asks the parent to reap. Pro: simplest authority story; the
>   "only your parent can collapse your session" invariant (`agent-lifecycle.md` §27, ARCHITECTURE.md
>   §325) is literally never bent. Con: a non-signing leaf whose parent is *itself* slow/blocked sits
>   un-reaped — the watchdog can see the stall but can't end it; reintroduces the un-collapsed-leaf
>   hang the sign-off-or-fail path exists to close.
> - **Recommendation: A.** The reconciled lifecycle doc already sanctions the bounded leaf-reap
>   (`agent-lifecycle.md` §27/§135 names it explicitly), and it is the minimal authority that closes
>   the non-signing-leaf hang.
>
> **The two — and only two — sanctioned unilateral-kill classes ② performs (both leaf-only):**
> 1. **Prod-then-reap of an idle-but-pane-warm non-signing leaf** — after the bounded prod ladder
>    exhausts on a **journaled** non-sign-off, recorded as watchdog-imposed `FAILED` (§4.4). Scope:
>    the *pane-warm-but-silent* case; a **process-dead** leaf (`pane_pid` dead) is **not** ②'s — it is
>    reaped mechanically by ①'s reconcile sweep → `FAILED` (DAEMON.md §5.4), the unambiguous
>    resolution; ② does not prod a process-dead leaf.
> 2. **Wedge-kill of an un-proddable wedged leaf** (§6) — evidence-gated on the multi-flat
>    conjunction (`pane_pid` CPU-flat load-bearing), recorded as `DIED_INFRA` / `died_infrastructure`,
>    armed only after the §6/§8 commissioning floor (escalate-not-kill until W2 is measured). It is a
>    kill, not a prod, precisely because the pane is not at the prompt (the prod gate fails by design).
>
> **Hard limits on both classes:** (1) ephemeral L5/L5+ leaves **only** — **never** a coordinator
> (a wedged-presenting coordinator is recovered/escalated under §3/§5.2, with the §5.4 roll-up +
> no-spawn-in-W gate; it is never wedge-killed, §6); (2) evidence-gated (a journaled non-sign-off for
> class 1; the continuously-held activity-resettable multi-flat conjunction for class 2 — never
> elapsed-time-alone); (3) recorded through the executor with the right death class (`FAILED` vs
> `DIED_INFRA`, §4.4/§6); (4) everything ambiguous is **detect-and-notify-parent / escalate**, never
> killed; (5) **only L1** may force-reap at any depth (emergency override, destructive, explicit
> confirmation — `agent-lifecycle.md` §135); (6) the god-view/system-improvement layer is **read-only
> and cannot kill** (`agent-lifecycle.md` §135).

### 5.4 Subtree-quiescence gating + the roll-up race rule

A coordinator's `idle` is **actionable only when its whole subtree is also quiet** (DAEMON.md §5.4;
`agent-lifecycle.md` §133). ② **consumes** ①'s **live-descendant roll-up** (computed by prefix scan
over the one-spine ledger key — parent = truncate last segment, children = prefix match; DAEMON.md
§3.1/§5.4). ② does **not** compute or own the roll-up; it gates on it.

This is **why `liveness_state` must keep `waiting` distinct from `idle`** (DAEMON.md §3.2): a quiet
coordinator with live descendants is `waiting` (roll-up warm), not `idle` (roll-up cold). Folding
them would break the gate.

> **The roll-up race rule (gap-review IMPORTANT #3 — a grandchild can spawn between the roll-up read
> and the kill).** A kill/collapse action on a coordinator's idle requires **BOTH**:
> 1. the live-descendant roll-up is **COLD** (no live descendants), **AND**
> 2. **no spawn-event in the last W** (no `slot_claimed` / `spawned` run-ledger row for any
>    descendant within the suspicion window).
>
> Condition 2 closes the race where a grandchild spawns just after the roll-up read but before the
> action lands. If either fails, the coordinator is `waiting`, not actionable.

> **FORK — for user review (the quiesce-then-reap interlock; gap-review IMPORTANT #4).** Two killers
> can race: a parent-collapse and a watchdog-reap can both target the same pane; a prod can land on a
> pane being concurrently collapsed, or on a **fresh** instance that took the seat (addresses survive
> respawn, F35).
> - **Option A (RECOMMENDED): one writer to the kill decision — the executor's CAS is the interlock.**
>   Every reap/collapse is a CAS-guarded `transition` presenting `expected_owner_token` +
>   `expected_generation` (DAEMON.md §4.2). A second killer (or a prod aimed at a now-fenced
>   incarnation) **aborts** because its token is stale — the same fencing that solves split-brain
>   solves double-kill. ② issues the reap through the executor; whoever's CAS lands first wins, the
>   loser aborts cleanly. The prod is similarly fenced: a prod carries the `owner_token` it observed;
>   if the seat was respawned, the token is stale and the prod is a no-op against the fresh instance.
> - **Option B: a dedicated quiesce-then-reap lock distinct from the CAS.** Pro: explicit. Con:
>   reinvents the serialization the single-writer executor already provides; a second lock domain is
>   exactly what DAEMON.md §4.3 collapsed away.
> - **Recommendation: A.** The fencing CAS is already the single-writer interlock; route every reap
>   and every prod-with-owner-token through it. The *wire-level* ack/no-ack of the prod is ③'s, but
>   **the interlock policy (one CAS-guarded writer to the kill decision) is ②'s and is stated here.**

### 5.5 The v1 escalation seat (auto-resolution deferred)

v1 ① **escalates** ambiguous cases (alive-but-unowned orphan, dead-pid-but-live-children that can't
be safely auto-resolved, and the **`inactive` no-owner-with-unresolved-descendants** case routed here
from §3.1); ② adds **auto-resolution behind the same escalation seat** later (DAEMON.md §5.3 — a
one-site add). v1 posture is the conservative commissioning stance: *"don't auto-recover past a break
— freeze and examine."* The unambiguous resolutions (live → renew, dead leaf → FAILED-reap, done →
auto-advance) run in v1; the ambiguous ones — including `inactive` — escalate.

---

## 6. The Wedge Detector (W2)

A new detector with no loop-impl precedent (the loop watchdog only saw lease staleness; it never
typed into a live session, so it never needed to tell idle-promptable from wedged).

**Scope — leaf-only (L5 / L5+).** Wedge-kill applies **only to ephemeral leaves**. A *coordinator*
that presents as wedged (tool hung, pane warm, subtree below it) is **never** wedge-killed — that
would violate the locked "persistent coordinators are recovered, never reaped" invariant
(§5.2; `agent-lifecycle.md` §27/§125) and could orphan a live subtree. A wedged-presenting coordinator
is routed to the §3/§5.2 recovery path (recover-vs-reap: adopt / respawn-from-ledger / escalate), and
the §5.4 subtree-quiescence roll-up + no-spawn-in-W gate still applies before any coordinator-scoped
action. Wedge-kill is the §5.3 **second sanctioned unilateral-kill class**, enumerated there.

**The wedge case:** a tool hung on network or stdin is **process-alive + pane-warm + CPU ≈ 0 +
JSONL-flat** and reads "still working" forever. The prod path **cannot reach it** — it is not at the
input prompt (prompt-string gate fails, §4.3), so a prod can't land, and it is not dead, so the
process probe doesn't fire.

**Detection rule (W2):**

```
pane WARM (pane_pid alive)  AND  JSONL flat  AND  node mtime flat  AND  pane_pid CPU flat
  held continuously across the wedge window W2,  with NO JSONL/mtime/CPU tick inside W2
  →  liveness_state = (wedged)  →  KILL + ESCALATE   [leaf only]
```

A wedged tool **cannot be prodded** (unlike a prompt-idle leaf) — so the action is **kill +
escalate**, not prod. The kill is recorded via the executor as a `died_*` terminal class
(`DIED_INFRA` if the wedge is a hung network/IO tool — infrastructure; the executor journals
`died_infrastructure`), distinct from a non-signing-leaf `FAILED`.

> **Why this is evidence-based, not an elapsed-time kill (reconciling §6 against the prime directive,
> lines 21/§3.5/§3.4).** The prime directive forbids `failed_confirmed` on **elapsed time alone**.
> The wedge verdict is **not** elapsed-time-alone, and the load-bearing reason is **CPU-flat**:
> - **`pane_pid` CPU-flat is the load-bearing distinguisher, not a confirming nicety.** A
>   legitimately long single tool-call / model turn **spikes CPU during generation**; a syscall hung
>   on network/stdin sits at **CPU ≈ 0**. CPU-flat is therefore *positive evidence* that the pane is
>   wedged on a syscall rather than mid-work — it is what converts "quiet for W2" into "demonstrably
>   not computing." This is why §2.3 promotes `pane_pid` CPU to the v1 floor **for the wedge path**;
>   without it the verdict WOULD be elapsed-time-alone and would be forbidden. (mtime-flat is a
>   confirming, not required, signal — a defence-in-depth on file activity.)
> - **The verdict is activity-resettable, identical to the prod ladder (§4.3).** Any JSONL turn,
>   node-mtime tick, or CPU spike **within W2 aborts the wedge verdict and resets** — exactly the
>   bounded-retries-reset-on-activity discipline every other path uses (§3.5/§4.3). The wedge is
>   **not** a one-shot timer; it is a *continuously-held* multi-flat conjunction, and the first sign
>   of life cancels it.
> - **Commissioning floor — escalate-not-kill until W2 is measured.** W2 is KNOWN-OPEN (§8). Until
>   first-run measurement establishes the **longest legitimate single-tool-call quiet-with-flat-CPU
>   span per task type** and W2 is set above it (§8), the wedge path **ESCALATES rather than kills** —
>   the kill is armed only after that floor exists. This prevents a too-short W2 from killing a
>   legitimately long syscall (a large file write, a slow model turn on a quiet pane) before the
>   measurement that would distinguish them exists.

> **W2 requires JSONL + mtime + CPU ALL flat — by design.** This is precisely the multi-flat
> conjunction the false-idle hazard (§2.4) demands: pane-warmth alone is a false-busy/false-idle
> read, so the wedge verdict needs the CPU (+ confirming mtime) signal. **DECISION (was a FORK):**
> `pane_pid` CPU is a **v1 requirement scoped to the wedge path only** (§2.3 signal 3) — reading one
> pane's CPU is a single cheap `ps`, a small bounded exception to the thin-floor cut; mtime stays
> confirming-not-required. The general working/idle detector floor stays two-signal (JSONL + pane-
> alive). A wedged leaf hanging silently is too close to the core failure the watchdog exists to
> prevent to defer (the gap-review IMPORTANT #10 residual). Settle the W2 window empirically in
> commissioning (§8); until then the path escalates, per the commissioning floor above.

---

## 7. L5+ Reviewer Liveness

The L5+ reviewer (`#review` seat) is a **real spawned ephemeral seat** (DAEMON.md §3.2 `level: L5+
(#review)`) that can hang with nothing catching it — and an L5 collapsed-pending-accept is **stuck
forever** if its L5+ dies (gap-review IMPORTANT #2). It is co-located on the node via the `#review`
suffix (DAEMON.md §3.1 — seats co-locate; single-owner is per-seat).

Resolution (locked by the gap-review):

- **L4 owns the L5+ reviewer under the SAME watchdog** — the reviewer is an ephemeral leaf and gets
  the **light** sign-off-or-fail path (§4), watched exactly like the L5 it reviews.
- **Its terminal artifact = the verdict file** — the verdict file is the reviewer's sign-off /
  terminal signal (its `<node>#review/.signal.json` + the verdict artifact). The sign-off check
  reads the journal for the `#review` seat's terminal signal, same as any leaf.
- **On L5+ death → cold-respawn a fresh L5+ against the FROZEN RUBRIC.** Review is **stateless vs the
  spec** (the frozen acceptance rubric, `acceptance_ref`, DAEMON.md §3.2, is read-only), so a
  cold-respawn is **safe** — the fresh reviewer re-reads the frozen rubric + the artifact under
  review and re-renders the verdict. The recovered design's **manual** reviewer-pointer repair
  (F-012) is the anti-pattern this **automates**: respawn through the §10 fencing path (new epoch),
  never a manual pointer edit.
- **Partial/torn verdict from the dead incarnation — fenced, not adopted.** A reviewer that died
  mid-write may have left a **torn or partial** verdict artifact (its `<node>#review/.signal.json` +
  the verdict file). Because the sign-off check reads the durable artifact via the sweep (§4.1), a
  stale/partial verdict is exactly the kind of artifact the sweep could mis-journal. The guard reuses
  the existing fencing seat: the **fresh** L5+ writes its verdict under the **new `lease_epoch` /
  `owner_token`** (§10), and the sweep **fences verdict-artifact journaling by `session_uuid`** — the
  same guard DAEMON.md §3.5 already applies to `.signal.json` (it validates the artifact's
  `session_uuid` against the live binding before journaling). A partial verdict from the dead
  incarnation carries the **old** session_uuid / epoch and is therefore **rejected, not adopted**. No
  new mechanism — the partial-artifact gap is closed by the fencing already in ①.

---

## 8. W / W2 Suspicion Windows — How They're Set (values KNOWN-OPEN)

The windows are **state-sensitive and KNOWN-OPEN** — the *mechanism* is specified here; the
**numbers are deliberately unset and settled empirically in commissioning** (the cluster-② brief;
gap-review DEFERRABLE; runtime-decisions §3 pull-trigger: "a single conservative W proves too
coarse"). DAEMON.md fixes `stale_grace_checks` default = 2 as a carried field but sets no window
values — that is ②'s to specify *how*, not the numbers.

**How W is set:**

1. **Per task type, not per level** (`agent-lifecycle.md` §127) — a research/spike legitimately runs
   longer than a code fix. The **spawning level sets W at spawn time** based on the child's task
   type.
2. **Per liveness/deliverable state** (`watchdog-design-01.md` L59) — within a node, the window is
   keyed on state: `W(waiting_on_child) > W(working) > W(writing_final_output)` (§3.3).
3. **Observer-renewed** — W bounds *how long without an observed renewal* before opening
   `stale_suspect`; a renewal (forward progress) resets the clock.
4. **UTC math** (DAEMON.md §4.6) — all `now − last_progress_at` math on the single canonical UTC
   clock.

**W2** (the wedge window) is **longer than any W** — wedge is the last-resort verdict, reached only
after the multi-flat conjunction holds across a window deliberately wider than a legitimate long
quiet turn.

**Commissioning gates (the empirical settle, runtime-decisions §5):**

- Run a real non-trivial job **slow + heavily traced**, failure-finding stance ("a clean run is
  suspicious"); measure the **false-idle rate** and the longest legitimate quiet turn per task type;
  set W above that, conservatively, then pressure-up.
- **Codex/L5 pane-warmth is ASSUMED-not-verified** (gap-review IMPORTANT #9). First-run measurement
  must confirm Codex panes stay warm the way Claude's do; **if not, promote the Codex session-log
  probe to a v1 requirement** for the only ephemeral level. This is a named commissioning gate, not
  an assumption to ship on.

---

## 9. Gate Detection → `gate_crossed_at`

The **resume firewall** is a LOCKED correctness invariant: **NEVER `--resume` a session across a
quality-gate boundary** (DAEMON.md §6.4; runtime-decisions §2.8) — carrying pre-gate conversational
context past a gate re-introduces the contamination the gate exists to stop.

**The enforcement is ①'s; the signal is ②'s** (DAEMON.md §6.4, §9): cluster ① *enforces* the
firewall by **reading** `gate_crossed_at` and refusing a `--resume` when it is set (falling back to a
fresh spawn with a delta brief). Cluster ② **owns gate detection** — it **maintains/flips**
`gate_crossed_at`.

**② sets `gate_crossed_at`** (through the executor) when it detects a node crossing a quality-gate
boundary. Because the firewall is a LOCKED correctness invariant, a **missed** trigger is a *silent
correctness failure* (pre-gate context leaks past the gate). The trigger set is therefore a **closed,
enumerable list keyed to concrete journal signals**, not an open-ended clause:

1. **Review gate** — the `#review` seat for a node becomes active (a `slot_claimed` / `spawned`
   run-ledger row for `<node>#review`), OR the node's `#exec` seat emits a `terminal_signal`
   routing work to review. Either journal event fires `gate_crossed_at` on the reviewed node.
2. **Plan-alignment gate** — a specific run-ledger event recording `PLAN-ALIGNMENT-GATE` approval on
   the node (the plan-approved journal row). That event fires `gate_crossed_at`.

**Fail-closed semantics (the silent-failure guard).** If gate-crossing detection is **ambiguous**
(a signal that *might* be a gate crossing but cannot be confirmed against the closed list),
`gate_crossed_at` **SHOULD be set** — fail-closed toward fresh-spawn. A spurious fresh-spawn is cheap
(a delta-brief re-boot); a **missed** gate is a correctness breach (the contamination the gate exists
to stop happens anyway). The asymmetry is deliberate: bias the detector toward over-firing. Once set,
the firewall is armed; ① reads it on every resume attempt.

> **FORK — for user review (the exact field name).** DAEMON.md §6.4/§9 pins the concept but writes
> the field name as "`gate_crossed_at` / equivalent" — it is **not** enumerated in the §3.2 binding
> yaml block (it appears as a concept at DAEMON.md ~§6.4/§9, not in the schema). ② must **pin the
> exact key** when it specifies gate detection.
> - **Option A (RECOMMENDED): pin the name as `gate_crossed_at`** (ISO-8601-UTC timestamp, null until
>   the node crosses a gate). A timestamp (not a bool) so the firewall can also tell *which* resume
>   attempts post-date the crossing, and so the audit log gets a `when`. ② writes it through
>   `watchdog-checkpoint`; ① reads it.
> - **Option B: a richer `gate_crossed: {at, gate_id, kind}` sub-record.** Pro: names *which* gate.
>   Con: more than the firewall needs in v1 (the firewall only needs "has any gate been crossed").
> - **Recommendation: A** — a single `gate_crossed_at` timestamp field, **to be added to the §3.2
>   binding schema by the DAEMON author** (the one schema addition this doc requests of ①). ②
>   maintains it; ① enforces on it.

---

## 10. Fencing Wired Into Recovery

② does **not** redesign fencing (lease_epoch / owner_token / CAS / stale_return_ignored / FENCED are
①'s, DAEMON.md §8). ② **wires recovery into** it: every **adopt / respawn / ownership-transfer** goes
through ①'s `claim` / `transition` executor commands, which **bump `lease_epoch` and re-mint
`owner_token`** in the **same atomic transaction** as the actor-changing transition (DAEMON.md §8,
§6.1 — F-012 fix: no window where state advanced but ownership didn't).

- **On ADOPT (§3.4 step 7 / §5.2):** re-adopt the existing address through ①'s `claim` → `new_lease_epoch =
  old + 1`, `new_owner_token = mint(address:subagent-id:session-uuid:lease_epoch)` (the composite
  self-fencing format, DAEMON.md §8). Append `lease_recovered`. **(Blocking dependency on ① — see the
  re-adopt-edge open seam, §12.)** ①'s `claim` is currently hardwired to `transition(expected_state=
  planned, …)` (DAEMON.md §6.1) and the §3.3 legality table has **no** `running → claimed` or
  `dead → claimed` edge — but an adopt targets a node that is `running` (live actor) or `dead` (orphan),
  never `planned`. As written the executor would abort the adopt-claim on its `expected_state`
  precondition. ② does **not** silently assume this type-checks; it is owed from the DAEMON author.
- **On RESPAWN (§3.4 step 8 / §5.2 / §7):** the **resume chokepoint** (DAEMON.md §6.4) re-adopts the
  address through `claim` (bump epoch, re-mint token), assembles a delta brief, boots via the spawn
  path. **Resume = spawn-variant; ② does NOT build a separate resume path** (DAEMON.md §6.4). Append
  `ownership_replaced`.
- **Gate firewall on respawn:** because respawn routes through the chokepoint, the §9 firewall
  applies — a respawn across a crossed gate is a **fresh** spawn (delta brief), never a `--resume`.

**Stale-return handling is ALREADY ①'s — ② does not re-implement it.** A returning old actor's
lower-epoch token **aborts** the mutation; the executor records `stale_return_ignored` +
`terminal_signal = FENCED` (DAEMON.md §8). ② **reads** `FENCED` to classify "de-authorized" apart
from "completed" / "died-infra" / "died-methodology" — the old actor is **de-authorized, not
auto-killed** (`watchdog-design-01.md` L70). The composite token format and the 3-precondition CAS
are **fixed in ①** (DAEMON.md §4.2/§8); ② only **calls** the commands that rotate them.

> **The fencing CAS is also the double-kill / prod-race interlock** (§5.4 FORK Option A): every reap
> and every prod-with-owner-token routes through the same CAS, so a stale killer/prodder aborts.

---

## 11. What ② Provides to ③ / ④

### 11.1 To cluster ③ (transports — the prod/wake wire + human channels)

② specifies **what a prod/nudge must do and its preconditions**; ③ builds the wire. The contract ③
must satisfy:

- **The prod preconditions (§4.3):** (1) **prompt-string gate** — only deliver a prod when the pane
  shows the idle input prompt (so it can't land mid-tool-call); (2) **owner-token fencing** — the
  prod carries the `owner_token` ② observed; a respawned seat's stale token makes the prod a no-op
  (§5.4 FORK A); (3) **no blind trust** — ② confirms a prod "worked" only by observing a **new JSONL
  turn** (`send-keys` has no ack).
- **The wake (best-effort):** a bus nudge that triggers an **immediate sweep** of a node (instead of
  waiting for the timer). **The durable fact is never on the wire** — the sign-off lives in
  `<node>/.signal.json` → the journal (DAEMON.md §3.5); a dropped nudge only delays journaling, never
  loses it (§4.1). ③'s wire is an **optimization**, not a correctness dependency.
- **The events ③ surfaces:** the watchdog-imposed `FAILED` (§4.4) and the recovery/escalation events
  (`stale_suspect_opened`, `recovery_probe_started`, `ownership_replaced`, `coordinator_died`,
  `died_*`) are journaled by the executor; ③ may carry best-effort notifications of them and route
  the `ESCALATED` answer-round-trip (which rides `terminal_signal = ESCALATED` + `terminal_note`,
  DAEMON.md §9). **Human-kill** routes through the executor's stamping path (never raw tmux) — ③'s
  channel, ②'s reap policy still applies (leaves only; L1 force-reap is the human override).

### 11.2 To cluster ④ (scale-as-resource)

② provides **nothing new** to ④ — admission control wedges at ①'s **claim-slot pre-step** (DAEMON.md
§6.1/§9), between claim-accepted and actor-open, without re-opening the CAS. ②'s respawn path (§10)
goes through the same chokepoint, so ④'s ceilings/backoff gate ②'s respawns automatically. ② does
**not** design admission, 429-backoff, per-runtime ceilings, or the resource envelope (out of scope,
§1.3).

---

## 12. Open Seams (recorded, not resolved here)

- **`semantic_event_at` / semantic-trace renewal** (§2.3 FORK): null in v1; whether the JSONL-growth
  floor counts as the semantic-trace signal or semantic renewal is deferred behind the interface.
- **`failed_confirmed` expression** (§3.1 FORK): recommended as `condition = terminal` + `died_*`
  `terminal_signal` (needs DAEMON author confirmation that `terminal` is the agreed terminal-lease
  `condition` value — no enum extension).
- **`stale_check_count` carried field** (§3.5): the consecutive-stale-poll counter the recovered impl
  carries (`watchdog.py` L132/L206–207) and the grace gate keys off, distinct from `recovery_attempts`
  (recovery-cycle budget). DAEMON.md §3.2 carries `recovery_attempts` + `stale_grace_checks` but not
  this per-poll counter — a **schema addition requested of the DAEMON author** (one line, parallel to
  `gate_crossed_at`). Do not overload `recovery_attempts`.
- **`recovery_attempt_ceiling`** (§3.5): the per-node bound on step-8 respawns (set at spawn like W,
  §8); KNOWN-OPEN default. Without it, step 8's RESPAWN-or-ESCALATE has no stated respawn bound — the
  loop hazard the counter-split closes.
- **`gate_crossed_at` exact field name** (§9 FORK): recommended `gate_crossed_at` (ISO-UTC) — a
  schema addition this doc requests of the DAEMON author (with `stale_check_count`, above).
- **W / W2 numeric values** (§8): KNOWN-OPEN; settled empirically in commissioning. The only numeric
  defaults inheritable from the recovered impl are `poll_interval_s = 60` and `stale_grace_checks =
  2` — neither a window value.
- **Wedge `pane_pid` CPU promotion** (§6 — DECIDED, no longer a fork): `pane_pid` CPU is a v1
  requirement scoped to the wedge path only (§2.3 signal 3); the general working/idle floor stays
  two-signal. CPU-flat is the load-bearing distinguisher (hung syscall vs spiking model turn); mtime
  is confirming-not-required. Wedge-kill is leaf-only and escalate-not-kill until W2 is commissioned
  (§6/§8).
- **Codex pane-warmth** (§2.4, §8): ASSUMED-not-verified; a named commissioning gate — first-run
  measurement owed, or promote the Codex session-log probe to v1.
- **Re-adopt edge owed from ① (blocking dependency, §10).** ADOPT/RESUME re-adopt an **existing**
  address (`running` live actor or `dead` orphan), but ①'s `claim` is `transition(expected_state=
  planned, …)` (DAEMON.md §6.1) and the §3.3 legality table has no `running → claimed` / `dead →
  claimed` edge. DAEMON.md §6.4 step 1 carries the **same** latent gap ("re-adopt the address through
  `claim`"). ① must admit either a `claim` variant whose `expected_state ∈ {running, dead, blocked}`
  or a dedicated re-adopt edge in the §3.3 table; the `planned → claimed` claim cannot express
  re-adoption of a live/dead address. Owed from the DAEMON author — ② does not assert it type-checks.
- **`resurrected` vs `recovered` audit transition** (OBSERVABILITY.md §23 lists `collapsed` /
  `resurrected`): ②'s adopt/respawn-from-ledger should emit a transition the audit log can name —
  reconcile with §23's vocabulary (recommend reusing `resurrected` for a ledger-recovery of an
  orphaned coordinator) or extend it explicitly. Recorded, not resolved.

---

*Cluster-② spec. Sits on `design/DAEMON.md` (cluster ①). Promotes
`research/orchestration-frame/phase-2-runs/research/watchdog-design-01.md` to canon.*
*Created: 2026-06-05.*
