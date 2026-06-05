# DAEMON — The Harness-as-a-Process (Cluster ① spec)

Status: design, v1 cut. This is the **substrate** spec — clusters ②/③/④ sit on it.

This document specifies the always-on harness daemon: the process that maintains the
**accountability invariant** across the L1–L5 agent tree. It is the cluster-① deliverable
named in `working-notes/runtime-decisions-and-commissioning-2026-06-04.md` §6 and closes
gap-review blocking **#1** (daemon SPOF / genesis), the cluster-① half of blocking **#2**
(per-node process-liveness/death signal + durable coordinator-completion artifact), and the
**lost `state-ledger-races` lens** (ledger atomicity/locking/write-races,
`arch-gap-review-2026-06-04.md` line 105).

It **adapts** the recovered self-improvement-harness control plane
(`research/orchestration-frame/self-improvement-harness/control_plane.py`, 1706 lines, +
`CONTROL-PLANE.md`, `manifest.yaml`, `workboard.py`, `watchdog.py`). The recovered model is **one
loop / one manifest**; cluster ① generalizes it to a **tree of per-node bindings**.

Two sources sit in **different streams**, and the doc keeps them distinct (the provenance honesty
matters for trusting the reuse claims):

- the **recovered control plane** (`self-improvement-harness/`) — the CAS/transition/atomicity
  skeleton this doc generalizes. It has **no** `lease_epoch`/`owner_token`/CAS-on-spawn (verified:
  those strings appear nowhere in its `control_plane.py`, `manifest.yaml`, or `watchdog.py`).
- the **phase-2 lease design** (`research/orchestration-frame/phase-2-runs/research/watchdog-design-01.md`)
  — a **proposed-but-never-coded** lease design that originates the `lease_epoch` + composite
  `owner_token` format (L17, L23–24, L65); it was *partially* wired into
  `phase-2-runs/harness/loop_supervisor.py`'s `--expected-owner-token` plumbing (L176–178) but never
  into a CAS-guarded spawn. v1 **promotes this proven-on-paper design into code for the first time.**

Do **NOT** import the older superseded **`phase-2-runs/harness/loop_supervisor.py`** (the prior
live proving-ground supervisor that carries the older `owner_token` wiring). Per `CONTROL-PLANE.md`'s
precedence rule, `phase-2-runs` is a proving ground — designs promote only through a canonical round,
which is exactly why its `loop_supervisor.py` is **not** the adaptation base (the
`self-improvement-harness` control plane is). *(Note: there is no `control_plane.py` under
`phase-2-runs/`; `loop_supervisor.py` is the file the "do-not-import" guard actually names.)*

---

## 1. Charter & Scope

### 1.1 The accountability invariant (LOCKED, quoted verbatim from runtime-decisions §1)

> The daemon maintains the **accountability invariant** — single-owner-always, continuous
> reconciliation, fenced ownership transfer.

with the precise guarantee:

> **every session owned, reconciled within bounded time, stale actions fenced**

(a brief reconciliation lag is expected; *fencing makes the lag safe*.)

The invariant decomposes into two orthogonal layers (runtime-decisions §1 line 16):

- **Accounting = single owner always.** Supervision tree (one parent-owner per node) +
  the binding ledger as the authoritative registry + a continuous reconciliation loop that
  keeps *actual* (tmux) == *recorded* (ledger). Solves the **orphan** problem (including the
  dead-coordinator-with-live-children case).
- **Fencing = a stale owner's action fails.** `lease_epoch` + `owner_token` + compare-and-set,
  enforced at the instant the actor acts. Solves the **stale-authority / split-brain** problem
  (incident F-024) that accounting alone cannot.

They compose: accounting guarantees *someone* owns every node; fencing guarantees only the
*current* owner can change it.

### 1.2 What the daemon HOSTS

- the single-writer **control-plane executor** (the only state-changing code path),
- the **binding ledger** (per-node current state) + the append-only **run-ledger** (history),
- the single **spawn chokepoint** (claim-before-spawn),
- the **reconcile loop** (on-restart + continuous),
- the **watchdog loop** (it runs *inside* this process; the **loop body / detector / recovery
  state-machine are cluster ②** — the daemon owns the loop scheduling and the ledger fields the
  loop reads/writes through the executor),
- **genesis / first-boot**.

### 1.3 Cluster ① owns (and ONLY these — sufficiency-cut INCLUDE set)

Per the sufficiency-cut test (runtime-decisions §2: *retrofitting it later means re-plumbing
every call site → now; attaches at one known site later → defer; single-writer is the keystone
that makes deferral safe*), v1 includes:

1. the **daemon process** itself (service-manager-hosted, PID/lock, behavior when it dies),
2. the **per-node binding-ledger schema** (incl. `lease_epoch`/`owner_token`/liveness/deliverable/terminal-signal),
3. the **append-only run-ledger** event format,
4. the **single-writer executor** (CAS-guarded transition chokepoint, lock-serialized, atomic,
   validate-before-commit) + the **ledger write-race/atomicity model**,
5. **reconcile-on-restart + continuous reconciliation**,
6. the **single spawn chokepoint** (boot via `--system-prompt-file operational/shared/system-prompt.md`
   — the ONE shared minimal prompt; the role is delivered as documents the agent reads — claim-before-spawn
   / F-024 fix, thin per-runtime adapter),
7. **genesis / first-boot**,
8. **fencing** (`lease_epoch` + `owner_token` + CAS on transition **and** spawn).

### 1.4 Explicitly DEFERRED (named here, owned elsewhere — NOT designed in this doc)

| Deferred item | Owner | Cluster ① provides the SEAT |
|---|---|---|
| Evidence-lease recovery state-machine (`stale_suspect → recovery_in_progress → failed_confirmed → adopt`) | ② | the binding fields the machine reads/writes: `condition`, `suspect_since`, `recovery_attempts`, `last_evidence` |
| Detector internals (multi-signal fusion: window_activity + CPU + JSONL-growth) | ② | the `liveness-state` field + `last-progress` field the detector writes through the executor |
| Leaf-reap vs coordinator-recover policy; auto-resume *execution* logic | ② | `auto_resume_command` + `allow_recovery` plumbing (carried, not fired) |
| Bus transport + wake contract + escalation-answer-down + human channels | ③ | terminal-signal events are journaled by the executor; the bus carries best-effort nudges |
| Admission control / 429-backoff / per-runtime ceilings / resource envelope | ④ | the spawn chokepoint's claim-slot pre-step (admission wedges *between* claim-accepted and actor-open) |
| Full desired-vs-actual reconciliation **controller** | ② (later) | the v1 continuous reconcile loop (boundary drawn in §5) |
| 2-week resurrection GC reaper | infra (separate) | distinct from the daemon's liveness reap (see §5.4) |

The cluster-① rule: **provide the seats, not the internals.** Every deferred policy attaches to a
ledger field or the spawn-chokepoint claim-slot that this doc defines now.

---

## 2. The Daemon Process

### 2.1 What it is

A single **resident, always-on, service-manager-hosted** process — the `harnessd` executor +
watchdog scheduler + reconcile loop in one address space. It is the only writer of durable
control-plane state. It is **infrastructure, not an agent**: it never reasons, never calls a
model; it executes deterministic transitions, sweeps tmux, and fires the watchdog tick.

Distinct from the recovered control plane, which was a **per-CLI-invocation** process that took
an advisory lock and exited (`CONTROL-PLANE.md` L119–124: *"The current goal is not full
daemonization."*). v1 makes it **resident** so that (a) restart = recovery has a defined owner,
(b) the watchdog loop has a host that survives a child's death, and (c) all bindings sit under
**one serialization domain** (closing the two-lock gap, §4.4).

> **Adapted from control_plane.py: reused / changed.**
> *Reused:* the read→validate→commit-inside-the-lock mutation skeleton; atomic-replace + append-fsync
> primitives; validate-before-commit. *Changed:* per-CLI-process → resident single-writer; one
> manifest → tree of bindings; two locks (`.control-plane.lock` + `.workboard.lock`) → one
> serialization domain.

### 2.2 Service-manager-hosted (genesis charter)

The daemon runs under a **launchd user agent** (`Restart=always` / `KeepAlive=true` — this is the
**watchdog-of-the-watchdog**: if `harnessd` itself dies, launchd relaunches it, and relaunch =
recovery). The launchd plist:

- `KeepAlive = true` (relaunch on any exit, including OOM/crash),
- `RunAtLoad = true` (start at login → survives machine reboot, the gap-review #1 SPOF),
- `ThrottleInterval ≥ 10` (relaunch backoff floor — no crash-loop / kill-rewedge storm, §2.6),
- `StandardOut/ErrorPath` → daemon log,
- working directory = the harness root (the workspace tree root that holds the ledgers).

A **second**, tiny launchd job (`harnessd-pinger`, `StartInterval ~60s`) is installed alongside it
to catch the **hang** case launchd's exit-only `KeepAlive` misses (§2.6).

`Restart=always` is the spelling for a systemd user unit if Linux parity is later needed; the v1
target is macOS launchd (matches the H40 pinned-CC + tmux environment).

### 2.3 PID / lock — single-instance guard

On boot the daemon acquires an **exclusive `fcntl.flock` on `.harnessd.lock`** and writes a
`runtime.json` self-report `{pid, started_at, lock_path, last_tick_at, last_reconcile_at,
incarnation}`. If the lock is already held, the new instance exits (*"another harnessd instance
already holds the lock"*) — launchd will not spawn two, but a manual launch must not race the
service-managed one.

> **Naming guard (one-spine discipline).** `incarnation` here is the **daemon-restart counter**
> (how many times launchd has relaunched `harnessd`) — it is a NEW field of the daemon's
> `runtime.json` self-report and is **deliberately distinct** from the per-node binding
> `generation` (the per-node CAS counter, §3.2/§4.2). Same-name collision avoided on purpose: one
> word, one meaning. `last_tick_at` is **read** by the external watchdog-pinger (§2.6), not merely
> written.

> **Adapted from watchdog.py: reused / changed.** *Reused:* the `fcntl.flock LOCK_EX`
> single-instance guard (watchdog.py L74–81) and the `runtime.json` self-report surface, whose
> **reused** fields are `{pid, started_at, last_checked_at, last_condition}` (verified against
> watchdog.py L370–440 — it carries no CAS/generation field). *Changed / NEW:* `last_tick_at`,
> `last_reconcile_at`, `incarnation`, and `lock_path` are NEW fields on the daemon's self-report
> (not part of the reused watchdog.py set); the lock guards the *whole resident daemon* (not just a
> watchdog loop); the surface is launchd-hosted rather than a bare pid-file (gap-review note:
> existing service status *"only detects pid-file daemons"*).

### 2.4 FORK — single-central daemon vs one-daemon-per-node

> **FORK — for user review.** The charter and gap-review both flag this as undecided
> (blocking #1: *"one-central vs one-per-node"*).
>
> - **Option A — single-central daemon (RECOMMENDED).** One `harnessd` holds all per-node
>   bindings, sweeps the whole tree each reconcile tick, and serializes every mutation behind one
>   lock. **Pro:** one serialization domain ⇒ a node's control + deliverable update is one atomic
>   transaction (closes the two-lock gap directly); one CAS authority; one reconcile sweep; matches
>   the single-writer keystone. **Con:** it is itself a SPOF — but that is exactly what launchd
>   `KeepAlive` + lease-state-in-the-ledger + relaunch=recovery is designed to neutralize (its
>   death is recoverable, not catastrophic, because all state is durable and fenced). Scaling
>   ceiling: one process sweeping N tmux panes per tick — fine for an L1–L5 tree (tens of nodes),
>   and the sweep is I/O-cheap (tmux list + mtime stat).
> - **Option B — one daemon per node.** Each node has its own supervisor process. **Pro:** no
>   central SPOF; natural process-tree parenting. **Con:** N lock domains ⇒ no atomic cross-node
>   commit; reconcile across the tree must read N processes' state; fencing needs a distributed
>   CAS authority; far more moving parts for a tens-of-nodes tree. Re-introduces the very
>   two-lock atomicity gap §4.4 closes.
>
> **Recommendation: Option A.** The single-writer keystone (runtime-decisions §2) is the whole
> reason deferral is safe; splitting the writer per-node forfeits it. The SPOF objection is
> answered structurally by §2.5 (relaunch = recovery), not by sharding the writer.

### 2.5 Behavior when the daemon dies (the SPOF answer)

This is the core of gap-review blocking #1 (*"Machine reboot/OOM kills the tmux server + every
session + the watchdog together, with no surviving actor to recover"*). Two death modes:

1. **Daemon dies, tmux survives** (OOM-kill of `harnessd` only, or a daemon crash). launchd
   relaunches → the daemon runs **reconcile-on-restart** (§5.1): read bindings → check each
   recorded session-uuid against live tmux → resume ownership, necro the dead, escalate the
   unowned. No double-spawn (resume-not-double-spawn, §7). The surviving agents kept working
   while unsupervised; reconciliation re-establishes accountability within bounded time (the
   "brief reconciliation lag" the guarantee explicitly tolerates — fencing makes it safe).
2. **Machine reboot / tmux server dies too** (everything gone). launchd `RunAtLoad` restarts the
   daemon at login → it reads the ledger, finds **no** live tmux sessions, marks every
   non-terminal node `dead`, and runs **genesis-recovery**: resume L1 from its binding (§7),
   which then re-decomposes/re-spawns its subtree from the durable work-node artifacts (G38
   stateless-respawn backstop). Lease-state-in-the-ledger ⇒ relaunch = recovery.

The invariant that makes both safe: **lease-state lives in the ledger, not in the daemon's RAM.**
The daemon is reconstructible from the ledger on every boot. This is the recovered research's
proven rule (`watchdog-design-01.md`: *"The lease belongs to the work unit, not to the watchdog
process. A restarted watchdog can resume from manifest state."*).

### 2.6 Behavior when the daemon HANGS (the third death mode)

launchd `KeepAlive` restarts only on **exit** — it does nothing for a **wedged-but-alive**
`harnessd` (a deadlock, an infinite loop, a stuck syscall) that still holds `.harnessd.lock` and
the serialization domain. A hang freezes the whole tree just as hard as a crash, but invisibly. Two
defences, both required:

- **An external liveness pinger reads `last_tick_at`.** The daemon stamps `runtime.json.last_tick_at`
  on every reconcile tick (§2.3). A tiny separate launchd job (`harnessd-pinger`, `StartInterval`
  ~60s, no shared lock) reads `last_tick_at`; if it is older than a staleness bound (e.g. 3 missed
  ticks), the pinger **kills the wedged `harnessd` by PID** (turning a silent hang into an exit so
  launchd `KeepAlive` relaunches it → relaunch = recovery). This is the "watchdog-of-the-watchdog"
  for the hang case, parallel to launchd's for the crash case. *(macOS launchd has no built-in
  `WatchdogTimeout`; the external pinger is the portable equivalent.)*
- **A `ThrottleInterval` backoff floor.** The plist sets `ThrottleInterval` (≥10s) so a
  crash-on-boot or kill-relaunch-rewedge cycle cannot become a relaunch **storm** that pins the CPU
  and starves the tree. Bounded relaunch, not busy-relaunch.

This closes the gap that `last_tick_at` was *written but never read* and that there was no storm
floor — making blocking #1 cover daemon **hang**, not just daemon **death**.

---

## 3. The Ledgers

Two durable surfaces, mirroring the recovered `manifest.yaml` (current state) + `run-ledger.jsonl`
(history) split, **generalized to a tree**:

- the **binding ledger** — per-node *current* state, one record per node-address. Atomic-replace.
- the **run-ledger** — append-only event journal, global ordering, one line per event. Append+fsync.

### 3.1 The ledger key — the one-spine semantic address

The binding-ledger key is the **collapsed semantic address** (`WORKSPACE-SCHEMA.md` §"One
Hierarchical-Path Spine"): node-path + `#role-variant` suffix — e.g.
`payments/gateway/stripe-client#exec`. NOT the physical `L{n}/`-laden workspace path. The address
is **stable across respawn/collapse/resurrection** (F35) because it is a property of the *position
in the tree*, not of any ephemeral instance. This is the one-spine identity reused as ledger key:

> node-address = requirement-ID = filesystem path = git branch = agent-address = **ledger key**.

Topology is derivable from the key by **prefix arithmetic** (parent = truncate last segment;
children/siblings = prefix match) — no separate parent-pointer field is *required* for
correctness, though a denormalized `parent` field MAY be stored to speed reconcile sweeps.

**Seats co-locate on a node.** A node hosts more than one seat (`#exec`, `#review`, `#test`). Each
seat is its own ledger key (`...gateway#exec`, `...gateway#review`) with its own session-uuid /
owner / lease. "Single-owner-always" is **per seat**, not per node — two live sessions legitimately
occupy one node via different suffixes. (FORK note below.)

> **FORK — for user review.** Per-seat ledger row vs one node row with per-seat sub-fields.
> **Recommendation: per-seat row (one binding per `address#suffix`).** It keeps "single-owner" a
> flat per-key property, lets `#exec` and `#review` carry independent lease_epoch/owner_token, and
> keeps reconcile a flat sweep. Alternative (one row, nested seats) couples two leases' atomicity
> and complicates CAS. Cost of the recommendation: a node's "is anything alive here" query becomes
> a prefix scan over suffixes — cheap.

### 3.2 Binding-ledger record schema (per node-address#seat)

> **Adapted:** the field set generalizes the recovered `manifest.yaml`'s `activity_lease` +
> `watchdog` + `observation_window` blocks (which existed **once**, for one loop) into **one record
> per node-address**, and **adds** the fencing tokens and the process-liveness/death fields the
> recovered model lacked.

```yaml
# binding-ledger.yaml  (or per-node files — see FORK §3.4); keyed by address
"payments/gateway/stripe-client#exec":

  # --- identity / topology ---
  node_address: payments/gateway/stripe-client#exec   # the one-spine key (== this map key)
  parent_address: payments/gateway#exec               # denormalized; derivable by truncation
  level: L5                                            # L1..L5 / L5+ (#review)
  session_uuid: 9bca3f79-6517-4991-b041-37607fbc0da4   # the CC/Codex session id (per incarnation)
  tmux_target: harness:payments/gateway/stripe-client#exec  # tmux session/pane name (§6.2)

  # --- ownership / fencing (NEW vs recovered) ---
  owner: payments/gateway#exec        # the parent-owner address (supervision tree)
  lease_epoch: 3                      # monotonic int; bumped on every claim/adopt/respawn
  owner_token: "payments/gateway/stripe-client#exec:subagent-656084b1:9bca3f79:3"
                                      # composite: address:subagent-id:session-uuid:lease_epoch
  generation: 7                       # per-node CAS counter (NOT global ledger length — see §4.2)
  last_applied_seq: 412               # run-ledger seq of the last WAL event committed to THIS node
                                      #   (the replay watermark — written in the same atomic-replace; §4.4)
  paused_at: null                     # ISO-UTC timestamp; null = not paused (TRANSPORTS §5.3). A subtree
                                      #   is paused if THIS node OR any ancestor (address-prefix) has it set.
                                      #   Set/cleared ONLY by the human control surface (③), routed through
                                      #   the single-writer executor — never raw. Two enforcing read-points:
                                      #   ①'s §6.1 claim-slot pre-step (refuse to launch a child under a
                                      #   paused subtree) and ②'s recovery loop (skip prod/respawn for a
                                      #   paused subtree). Carried here; honored at those read-points.

  # --- lifecycle state (GENERIC per-node, NOT the reviewer-loop vocabulary) ---
  state: running                      # planned|claimed|spawning|running|blocked|done|failed|dead
  state_entered_at: '2026-06-05T10:00:00+03:00'
  last_binding_update_at: '2026-06-05T10:14:00+03:00'   # last-touch, separate from entry-time

  # --- liveness-state (written by the reconcile loop from ACTUAL tmux; NEW) ---
  liveness_state: working             # working|waiting|idle|dead  (CANONICAL — agent-lifecycle.md owns
                                      #   this enum; the ② detector writes it). Optional bookkeeping
                                      #   values: 'claimed' (pre-spawn, no actor yet), 'terminal'
                                      #   (post terminal-signal). working/waiting are NOT folded — the
                                      #   waiting-vs-idle split is load-bearing for the §5.4 coordinator roll-up.
  last_progress_at: '2026-06-05T10:13:30+03:00'         # forward-progress (artifact/JSONL growth)
  last_heartbeat_at: '2026-06-05T10:14:00+03:00'        # liveness ping (separate from progress)

  # --- detector/lease fields READ BY cluster ② (carried, not interpreted here) ---
  condition: healthy                  # never_checked|healthy|inactive|stale_suspect
                                      #   |recovery_required|recovery_in_progress|terminal|invalid
                                      #   (terminal = the confirmed-failed lease value, WATCHDOG §3.1 —
                                      #    no separate failed_confirmed enum; condition IS the surface)
  suspect_since: null
  stale_check_count: 0                # consecutive-stale-poll GRACE counter (name matches recovered
                                      #   watchdog.py); reset on ANY renewal. ② keys the grace gate off it.
  stale_grace_checks: 2               # the grace THRESHOLD (config, default 2): ② escalates to recovery
                                      #   when stale_check_count >= stale_grace_checks (WATCHDOG §3.5; watchdog.py L211).
  recovery_attempts: 0                # recovery-CYCLE counter; reset ONLY on confirmed-healthy-after-recovery.
                                      #   DISTINCT from stale_check_count — never overload one onto the other (WATCHDOG §3.5).
  recovery_attempt_ceiling: 3         # respawn bound for recovery_attempts (per-node config, set at spawn
                                      #   like W); recovery ESCALATES past it instead of looping (WATCHDOG §3.4 step 8).
  gate_crossed_at: null               # resume-firewall flag (§6.4): set when this node crosses a quality-gate
                                      #   boundary. ② maintains it; ① reads it to REFUSE --resume (fail-closed).
  auto_resume_command: null           # cluster-② SEAT; carried, fired only with --run-recovery
  last_evidence: { source: reconcile_sweep, heartbeat_at: ..., progress_at: ...,
                   semantic_event_at: null }   # semantic_event_at: ② writes (semantic detector); null in v1

  # --- deliverable-state (the workboard-stream half, merged onto the node; §3.3) ---
  deliverable_state: active           # planned|active|waiting|completed|blocked|cancelled|delivered|delivery-failed
  stop_condition: "stripe-client passes acceptance.md"
  write_targets: [ "src/payments/gateway/stripe-client/" ]   # IN-JAIL relative write surface inside the node
  evidence_refs: [ "report.md" ]                              # completion artifacts
  acceptance_ref: "acceptance.md"     # frozen rubric at the node (read-only)
  delivery_destination: null          # OUT-OF-JAIL promotion TARGET — user-path or git-remote (from intent-spec §8); set at intake, consumed by promote-out (INTAKE-TO-DELIVERY §3). Distinct from write_targets (the in-jail source).
  delivery_kind: null                 # filesystem-path | git-remote — drives copy-out vs push at promotion

  # --- terminal-signal (the durable completion/death fact the parent's kill keys off; NEW) ---
  terminal_signal: null               # DONE|FAILED|ESCALATED|DIED_INFRA|DIED_METHODOLOGY|FENCED (§3.6 table)
  terminal_signal_at: null
  terminal_note: null                 # free text (e.g. ESCALATED question, FAILED reason)
  signal_artifact_seen_at: null       # last <node>/.signal.json the sweep journaled (journal-once guard; §3.5)

  # --- verifiable spawn fact (H40 / runtime-and-model-map) ---
  model_used: "opus-4.8 / claude-code"  # ACTUAL model+runtime that ran (config=intent, this=fact)
  system_prompt_file: "operational/shared/system-prompt.md"  # CONSTANT — the ONE shared minimal prompt
                                        #   passed as --system-prompt-file at EVERY spawn, identical L1–L5
                                        #   (H40, agent-definition-principles §4). May be a runtime-global
                                        #   rather than per-row; at minimum it is NO LONGER a per-level path.
  role_variant: "L5#exec"               # PER-binding — selects WHICH load-manifest/bundle + per-level role
                                        #   docs the chokepoint assembles into the brief (e.g. "L4",
                                        #   "L5+#review"). This is the field that varies by seat.
  role_bundle_hash: "sha256:…"          # detect role-bundle drift (fencing surface, open Q)
```

**Two-surface split (kept from the recovered model).** `liveness_state` + `condition` (lease/health)
is one surface; `deliverable_state` + `terminal_signal` (semantic/work) is the other. They are
*distinct* (F-003/F-033): a session can be `alive` but its deliverable `blocked`. The reconcile
loop writes the liveness surface from tmux; the executor writes the deliverable surface from
terminal signals and transitions.

> **Provenance — reused / promoted / NEW (split honestly across the two streams).**
> *Reused from the recovered `manifest.yaml` (self-improvement-harness):* `activity_lease`
> `{last_heartbeat_at, last_progress_at, status}` → `last_heartbeat_at`/`last_progress_at`/
> `liveness_state`; the `watchdog` block `{condition, suspect_since, recovery_attempts,
> stale_grace_checks, auto_resume_command, last_evidence}` → carried per node (this block has **no**
> `lease_epoch` — verified); the workboard stream `{stream_id, status, owner, stop_condition,
> write_targets, evidence_refs}` → the deliverable fields.
> *Promoted from phase-2 `watchdog-design-01.md` (proposed-but-never-coded; see header):*
> `lease_epoch` + the composite `owner_token` format (`address:subagent-id:session-uuid:lease_epoch`,
> = the design's `role:…` with `role` → the one-spine `address`). These are **NOT** "reused from the
> recovered manifest" — they were **absent** from the recovered control plane's code AND manifest,
> and present only as an uncoded phase-2 design (partially wired in `loop_supervisor.py`'s
> `--expected-owner-token` plumbing). v1 codes them into CAS for the first time (F-012/F-024 fix).
> *Genuinely NEW here:* `session_uuid` + `tmux_target` + `liveness_state` (no process-liveness field
> existed in either stream); `terminal_signal` + `signal_artifact_seen_at` (no per-node died/done
> signal existed — terminality was only a global `status: stopped`); `last_applied_seq` (the WAL
> replay watermark, §4.4); generic lifecycle `state` vocab replacing the reviewer-loop
> `builder/reviewer_1/reviewer_2` states; per-node `generation` replacing global `len(ledger)`.

### 3.3 Generic per-node lifecycle state machine

The recovered `KNOWN_STATES`/`ALLOWED_TRANSITIONS` encode reviewer-loop semantics
(`builder`/`reviewer_1_pending`/…). v1 keeps the **mechanism** (a static legality table +
the CAS legality gate, `cmd_transition` L1526) but replaces the **contents** with a generic
node lifecycle:

```
planned ──claim──▶ claimed ──spawn-ok──▶ spawning ──actor-open──▶ running
claimed ──release (admission-deny / E32-pin-fail)──▶ planned     (ROLLBACK; §6.1)
spawning ──actor-open-fails──▶ planned                           (ROLLBACK after claim→spawning; §6.1)
spawning ──unrecoverable-spawn-error──▶ failed                   (give up the slot, not retry)
running ──block──▶ blocked ──unblock──▶ running
running ──DONE──▶ done
running ──FAILED/DIED──▶ failed
{any non-terminal} ──reconcile-finds-dead──▶ dead     (reconcile-driven, not actor-driven)
running ──re-adopt(claim, expected_state=running)──▶ claimed   (RESUME a live address; §6.4 — fences the prior incarnation via lease_epoch bump)
dead    ──re-adopt(claim, expected_state=dead)──▶ claimed       (RESUME/necro a dead address; §6.4 / §5)
done | failed | dead = terminal
```

`ALLOWED_TRANSITIONS` is the static table; an illegal target is rejected before any write (the
recovered legality gate, reused verbatim in mechanism). **The rollback edges (`claimed → planned`,
`spawning → planned`, `spawning → failed`) are first-class members of the table** — without them
the §4.2 legality gate would reject the very claim-release the spawn chokepoint (§6.1) depends on,
leaking an un-reclaimable `claimed` slot (a worse F-024 than the duplicate it prevents). Every edge
the spawn chokepoint can traverse on failure is enumerated here so the gate permits it. **The re-adopt
edges (`running → claimed`, `dead → claimed`) are likewise first-class:** RESUME/necro (§6.4; WATCHDOG
ADOPT) is a `claim` variant whose CAS precondition is `expected_state ∈ {running, dead}` — NOT the
fresh-claim's `expected_state=planned`. The `claim` primitive therefore takes an `expected_state`
parameter (`planned` fresh | `running` resume-live | `dead` necro), CAS-guarded against whichever it is
given. Without these edges the legality gate would abort every adopt/resume on its precondition —
un-buildable as WATCHDOG §3/§5 require.

### 3.4 Merge of binding + deliverable (closes the two-registry split)

The recovered model kept **two** registries (`manifest` control-state + `WORKBOARD.yaml` stream
deliverables) reconciled by the validator across **two locks** — so no atomic two-file commit
existed. v1 **merges them into one per-node record keyed on the one-spine address.** The
workboard's free-form `stream_id` (`WS-001`) becomes the node-address (per one-spine). Control-state
and deliverable-state update in **one atomic transaction** (§4.4), not two locks reconciled later.

> **FORK — for user review.** Binding-ledger physical storage: **one keyed file vs one file per
> node-address.**
> - **Option A — single keyed file** (`binding-ledger.yaml`, the whole map): one atomic-replace
>   target ⇒ one write-lock ⇒ simplest CAS and simplest cross-node atomic commit. Con: every
>   mutation rewrites the whole map (fine at tens of nodes; the recovered model already rewrote the
>   whole manifest each commit).
> - **Option B — one file per node-address** (`<path>/.binding.yaml`): aligns the ledger key with
>   the one-spine filesystem path (node-address *is* a path); finer locks. Con: N lock domains
>   unless the resident daemon serializes them all (which Option A in §2.4 does anyway), and
>   cross-node reconcile reads N files.
> - **Recommendation: Option A** (single keyed file) for v1. With the single-central daemon
>   (§2.4-A) there is one writer anyway, so the single-file model gives atomic whole-tree commits
>   for free and the simplest crash-atomicity story. Revisit if the tree grows past hundreds of
>   nodes.

### 3.5 Run-ledger event format (append-only journal)

`run-ledger.jsonl` — one JSON object per line, **global ordering**, append+fsync. This is the
**harness-level lifecycle/terminal-signal journal** written by the single-writer executor.
Distinct from per-project `log.md` (agent-written `STARTED/SUBMITTED/APPROVED/SENT-BACK`,
append-queue, `WORKSPACE-SCHEMA.md` §log.md) — they are **siblings, not the same file**: `log.md`
is project-domain history written by agents; the run-ledger is process-lifecycle history written
only by `harnessd`. (Whether terminal-signal entries are *also* mirrored into `log.md` is an open
seam — see §10.)

Every state-changing entry is the **WAL record for exactly one transition** and carries enough to
replay that transition deterministically (§4.4):

```json
{ "ts": "2026-06-05T10:14:00+03:00",
  "seq": 412,                       // monotonic global sequence (= the ordering AND the per-node watermark)
  "node_address": "payments/gateway/stripe-client#exec",
  "event": "spawned",
  "actor": "harnessd",              // executor is the only writer of this journal
  "crc32": "a1b2c3d4",              // content checksum (FORK-CRC); NO in-payload "len" — the byte length is the append_framed <byte-len> PREFIX (§4.4), not a field inside the json (self-referential len is circular)

  // --- the transition this WAL row commits (drives deterministic replay) ---
  "from_state": "spawning",         // pre-image state the CAS expected
  "to_state": "running",            // post-commit state
  "expected_generation": 6,         // pre-image generation the CAS checked against
  "generation": 7,                  // POST-commit generation (= expected_generation + 1)
  "lease_epoch": 3,
  "owner_token": "payments/gateway/stripe-client#exec:subagent-656084b1:9bca3f79:3",  // post-commit token

  // --- the mutation payload (the fields this transition set on the binding) ---
  "binding_delta": { "session_uuid": "9bca3f79-…", "model_used": "opus-4.8 / claude-code",
                     "liveness_state": "working", "state_entered_at": "2026-06-05T10:14:00+03:00" },

  "summary": "claimed slot + opened tmux actor on opus-4.8/claude-code",
  "artifacts": ["report.md"] }
```

**Replay is a deterministic re-apply, not a guess.** Recovery (§4.4 / §5.1) replays *only* events
whose `seq > binding.last_applied_seq` for that node. For each, it verifies the binding's current
`generation == expected_generation` (the pre-image the CAS checked); if so it applies `binding_delta`,
sets `generation` and `owner_token` to the post-commit values, and stamps `last_applied_seq = seq`
— all in the **same atomic-replace**. If the binding's generation already equals the event's
post-commit `generation` (the event already landed before the crash), the event is a no-op skip.
This makes "reflected in the binding ledger" a **checkable predicate** (`seq ≤ last_applied_seq`),
not prose. Non-state-changing rows (heartbeats, edge-triggered condition notes) omit the
transition/`binding_delta` block and are never replayed.

**Event vocabulary** (closed set the run-ledger accepts), composed from the recovered ledger's
event taxonomy + the comms-protocol terminal signals + the F-017/stale-return classes:

- **lifecycle:** `node_planned`, `slot_claimed`, `spawned`, `state_transition`, `collapsed`,
  `necroed`, `resumed`.
- **lease / ownership:** `lease_renewed`, `ownership_replaced`, `stale_suspect_opened`,
  `recovery_probe_started`, `lease_recovered`, **`stale_return_ignored`** (a fenced actor returned
  after respawn — non-destructive de-authorization, F-012/F-024).
- **terminal-signal (first-class):** `signal_DONE`, `signal_FAILED`, `signal_ESCALATED`
  (the comms-protocol §terminal-signal contract — the executor journals the *fact-of-being-sent*;
  the watchdog's sign-off check reads **this journal**, not the transient bus nudge — see the
  durable write-path below), plus daemon-stamped death classes `coordinator_died`,
  `died_infrastructure`, `died_methodology` (F-017: infra-vs-methodology are *distinct* terminal
  classes; recovery branches on them).
- **completion:** `coordinator_completed` (the durable harness-stamped row the parent's kill keys
  off — gap-review #2 cluster-① half).

**Terminal-signal write-path — durable artifact, not a fragile in-process call (closes the
gap-review #2 transport gap).** The signing agent runs in a tmux pane; it **cannot** call the
in-process executor, and routing its terminal signal *only* over the best-effort bus would mean a
**dropped nudge loses the durable row entirely** — the exact failure the design distrusts. So the
signal is durable-by-write, journaled-by-sweep:

1. **Agent writes the signal to a durable per-node artifact** — `<node>/.signal.json`
   `{tag: DONE|FAILED|ESCALATED, at, notes, session_uuid}` (an atomic tmp+rename the agent does as
   its last act, alongside `report.md`). This is the durable fact; the bus nudge is only an
   *optional fast-path wake*.
2. **The reconcile sweep detects the artifact and the executor journals from the durable read** —
   each tick, reconcile checks for a `.signal.json` newer than the node's `terminal_signal_at`; on
   finding one it stamps `terminal_signal` + appends the `signal_*` run-ledger row (validating
   `session_uuid` against the live binding to fence a stale-actor signal). A dropped bus nudge
   therefore only **delays journaling to the next sweep**, never loses it. The bus nudge, if it
   arrives, just triggers an *immediate* sweep of that node instead of waiting for the timer.

The binding carries `signal_artifact_seen_at` so the sweep journals each artifact **exactly once**
(idempotent; matches "terminal states reconcile exactly once").

**Edge-triggered append (anti-spam, reused verbatim).** Steady-state healthy reconcile sweeps do
**not** append; the run-ledger appends only on a **condition/state change** or a forced
`--record-stable`. The per-poll status is written to a sidecar (`runtime.json` /
`.harnessd/status.json`), not the durable journal. Terminal states reconcile **exactly once**.
Invalid candidate checkpoints **fail closed** (validate-before-commit).

> **Adapted from run-ledger.jsonl + watchdog.py: reused / changed.** *Reused:* append-only
> JSONL one-object-per-line + append+fsync; per-entry `{ts, event, actor, state, summary,
> artifacts?}`; the edge-triggered "append only on condition change, sidecar every poll, terminal
> reconciled once, invalid fails closed" idempotency rule (WATCHDOG.md L120–128); the
> ownership-lifecycle event names from `watchdog-design-01.md`. *Changed / NEW:* every entry is
> keyed by `node_address`; a global `seq` is added (the recovered ledger had no explicit global
> sequence — it relied on file order, which v1 keeps but names); explicit terminal-signal events
> (`signal_DONE/FAILED/ESCALATED`) and death-class events (`coordinator_died`, `died_*`) become
> first-class (the recovered model encoded terminality only as `state: stopped`); `iteration` is
> dropped (reviewer-loop-specific).

### 3.6 Terminal vocabulary — the one normative mapping table

Three layers each have their own word for "ended," and a builder must be able to translate among
them to write the sign-off check. This table is **normative**; the layers are deliberately distinct
(different granularity), and this is the only place the translation is defined.

| Agent-emitted tag (comms-protocol, strict 3-set) | `terminal_signal` (binding) | run-ledger `event` | lifecycle `state` | Node collapsed? |
|---|---|---|---|---|
| `DONE` | `DONE` | `signal_DONE` | `done` | yes (parent reads `report.md`) |
| `FAILED` | `FAILED` | `signal_FAILED` | `failed` | yes (parent respawns/escalates) |
| `ESCALATED` | `ESCALATED` | `signal_ESCALATED` | **stays `running`** (non-terminal) | **NO — keeps context, waits** |
| *(none — daemon-stamped)* | `DIED_INFRA` | `died_infrastructure` | `failed` | per ② recovery policy |
| *(none — daemon-stamped)* | `DIED_METHODOLOGY` | `died_methodology` | `failed` | per ② recovery policy |
| *(none — daemon-stamped)* | `FENCED` | `stale_return_ignored` | *(unchanged — stale actor only)* | no (live owner unaffected) |
| *(none — daemon-stamped, coordinator)* | *(none)* | `coordinator_died` | `dead` | recovered-as-orphan, not collapsed (§5.4) |
| *(none — daemon-stamped, coordinator)* | `DONE` | `coordinator_completed` | `done` | yes |

Two rules a builder must encode:

- **ESCALATED is the asymmetric case:** `terminal_signal` is **set** but `state` stays
  **`running`** and the node is **not collapsed** — the agent keeps context and waits for the
  answer-round-trip (comms-protocol). The sign-off check ("is there a terminal-signal event for
  this node?") is satisfied, yet the node is *not* terminal. Any code that assumes
  `terminal_signal != null ⇒ collapse` is wrong; gate collapse on `state ∈ {done, failed, dead}`.
- **The spelling split is deliberate, not an accident:** the binding field uses SCREAMING
  `DIED_INFRA` (a value); the run-ledger uses snake `died_infrastructure` (an event name); the
  lifecycle uses lowercase `dead`/`failed` (a state). They are three layers, and this table is the
  exact translation — do not "unify" them by renaming; translate through here.

> **in_flight release-DECREMENT rides the terminal transaction (④'s count, ①'s hook).** The
> single-writer terminal write — the executor write that stamps `terminal_signal` on a
> `done`/`failed`/`dead` collapse, AND the §5.4 necro / §5.1 reconcile-finds-dead path — carries
> cluster ④'s symmetric in_flight **release-decrement**. It rides the **existing** single-writer
> terminal write (no new writer, no second mutator): same atomic-replace, crash-safe via
> `last_applied_seq`, exactly symmetric to the §6.1 claim-INCREMENT seat. ④ owns the slot COUNT; ①
> only acknowledges and provides this reserved decrement hook so ④'s admission gate is a balanced
> counter, not an increment-only ratchet. (The `ESCALATED` row is **not** a release — it stays
> `running`, holds its slot, and waits for the answer round-trip.)

---

## 4. The Single-Writer Executor + Atomicity Model

This section closes the **lost `state-ledger-races` lens** explicitly: *who may write, the
ordering, and crash-atomicity* (gap-review line 105: *"multiple events stamping the same ledger;
one-writer discipline"*).

### 4.1 Who may write — exactly one writer

**Only `harnessd` mutates durable control-plane state.** All mutation flows through one funnel
(the descendant of `commit_mutation`, L1264). Even the **watchdog and the detector write through
the executor** — they never edit the binding ledger directly; they call the executor's
checkpoint/transition primitive, which mutates only their slice and appends one run-ledger row
(the recovered "observer writes through the executor" pattern — `watchdog.py` shells
`control_plane.py watchdog-checkpoint`, never touches the manifest). In the resident model these
are in-process calls into the single executor, not subprocess shell-outs, but the discipline is
identical: **one writer, no second mutator.**

> **Adapted: reused.** The "observer writes through the executor" rule from `watchdog.py` /
> `watchdog-design-01.md` (three-writer discipline: manifest = truth, ledger = history, transition
> = only state-changer). Reused as-is; collapsed from cross-process shell-out to in-process call.

### 4.2 The transition primitive — CAS-guarded, lock-serialized, validate-before-commit

The single state-changing primitive, lifted from `cmd_transition` (L1505–1610) and generalized
per-node:

```
transition(node_address, expected_state, expected_generation, expected_owner_token, target_state, …):
    with EXCLUSIVE serialization-domain lock:          # §4.3
        binding  = read_binding(node_address)
        # --- CAS preconditions (ALL checked before ANY mutation) ---
        if binding.state      != expected_state:        abort  # recovered L1511
        if binding.generation != expected_generation:   abort  # per-node generation, NOT len(ledger)
        if binding.owner_token != expected_owner_token:  abort  # FENCING (new) — reject stale owner
        if target_state not in ALLOWED_TRANSITIONS[binding.state]: abort   # legality gate (recovered L1526)
        # --- build candidate, validate, commit ---
        candidate = deepcopy(binding); mutate(candidate); candidate.generation += 1
        entry = build_run_ledger_entry(...)
        errors, warnings = validate(candidate, ledger + [entry])      # recovered validate() L618
        if errors: abort   # validate-before-commit: NOTHING written
        commit(candidate, entry)                                       # §4.4 ordering
```

**Three CAS preconditions** (the F-024 fix is here):

1. `expected_state` — the recovered expected-state guard (L1511).
2. `expected_generation` — the recovered ledger-generation guard (L1516), **but per-node**. The
   recovered guard used **global** `len(ledger)`; in a tree with one shared append-only ledger,
   length is a global counter any node's append bumps, so it cannot fence a single node. v1 uses
   a **per-node `generation` field** bumped on every commit to that node. (open Q resolved: the
   shared run-ledger stays single-file for global ordering; per-node CAS uses per-node generation.)
3. `expected_owner_token` — **NEW fencing precondition.** A stale actor presents its old token;
   the live binding holds the new token (higher `lease_epoch`); mismatch ⇒ abort. This is what
   makes a stale owner's action *fail*, not merely get reconciled later. Because `owner_token`
   embeds `lease_epoch` (`address:subagent-id:session-uuid:lease_epoch`), comparing tokens
   compares epochs — the token is **self-fencing**.

> **Adapted from cmd_transition: reused / changed.** *Reused:* the read→check-preconditions→
> deepcopy→mutate→validate→commit-inside-the-exclusive-lock skeleton (L1505–1610); the
> precondition-accumulate-then-abort-before-write pattern; the static `ALLOWED_TRANSITIONS`
> legality gate; the pure `validate()` returning `(errors, warnings)` with errors-block/
> warnings-allow. *Changed:* added the third CAS precondition (`expected_owner_token`); per-node
> `generation` replaces global `len(ledger)`; per-node binding replaces the single manifest;
> `lease_epoch`/`owner_token` rotate **in the same transaction** as actor-changing transitions
> (F-012 fix — no window where state advanced but ownership didn't).

### 4.3 Lock discipline — one serialization domain

The recovered model had **two** advisory `fcntl.flock` domains (`.control-plane.lock` +
`.workboard.lock`) — control-state and deliverable-state could not be committed atomically
together. v1 has **one** exclusive serialization domain owned by the resident daemon. Because there
is one writer (the daemon) and one lock, every mutation is a read→validate→commit fully inside the
lock. Reads (show/next/reconcile-inspect) take a shared lock.

**No CLI read-modify-replace of the shared map — all mutation routes through the daemon.** With the
single-keyed binding file (§3.4-A), a cooperating CLI that atomic-replaced the *whole map* to change
one node would silently clobber a concurrent daemon write to a *different* node — and per-node
`generation` CAS does **not** guard that cross-node clobber (it guards the node the CLI changed, not
the bystander it overwrote). So the rule is: **CLIs are clients, not writers.** A `harnessctl`
command sends a request to the resident daemon (over a local socket / fifo / the same executor
entrypoint), and the daemon performs the mutation inside the one lock. No external process ever
read-modify-replaces `binding-ledger.yaml` directly. (Option 3.4-B per-node files would also remove
the cross-node clobber, by giving each node its own replace target — noted in the §3.4 fork.)

**Caveat (honest):** the lock is still *advisory and process-local* to `harnessd` — it fences the
daemon's own concurrent operations, **not** a rogue process that ignores both the lock and the
route-through-daemon rule. The real protection against a rogue/stale *actor* is **fencing** (§8),
not the lock; the lock serializes the *daemon's* writes.

### 4.4 Crash-atomicity ordering — intent-first

The recovered `commit_mutation` (L1264) did `save_manifest` → `append_ledger` → `save_continuation`
as three separate fsync'd ops; a crash mid-funnel leaves the manifest **ahead of** the ledger
(manifest replaced, ledger not yet appended), forcing recovery to tolerate manifest-newer-than-ledger.
v1 fixes the ordering to make the **append-only run-ledger the single source of truth**:

```
commit(candidate_binding, entry):
    # entry carries: seq, from/to_state, expected_generation, post-commit generation+owner_token, binding_delta (§3.5)
    candidate_binding.last_applied_seq = entry.seq         # stamp the watermark IN the checkpoint
    1. append_ledger(entry)                  # append+fsync the INTENT/EVENT FIRST (framed line, §4.4 box)
    2. atomic_replace(binding_ledger, candidate_binding)   # tmp + fsync + os.replace (incl. last_applied_seq)
    3. regenerate derived handoff (continuation/next-action packet)   # derived, never hand-edited
```

**Why intent-first.** Step 1 is append-only, and a crash can only ever corrupt the **final** line
(the one being appended). If the daemon crashes between step 1 and step 2, recovery sees a
run-ledger event with **no corresponding binding update** and **re-applies it deterministically**
(see the replay watermark + pre-image rule below). If it crashes before step 1, nothing happened —
the actor's CAS will simply be retried. This makes reconcile-on-restart's job: *replay any
run-ledger event whose `seq` is greater than the binding's `last_applied_seq` for that node.* The
run-ledger is the WAL; the binding ledger is the checkpoint.

> **CORRECTION to the recovered code — torn-tail tolerance is NOT inherited, it is ADDED in v1.**
> The recovered `load_ledger` (control_plane.py L209–225) skips only **empty** lines (L216–217);
> on **any** `json.JSONDecodeError` it **raises** `ValueError` (L220–221) and on a non-dict it
> raises (L222–223) — so a torn final WAL line makes the *entire* run-ledger un-loadable, which
> would brick the very boot-recovery path that replays it (§5.1 step 1). v1 **changes** load so a
> crash mid-append survives:
>
> 1. **Frame every record.** Each WAL line is written as `<len>\t<json>\n` where `<len>` is the
>    byte length of the JSON payload (a self-describing length frame; a CRC32 checksum field MAY be
>    added inside the JSON for defence-in-depth). Write-path: format the full line, `write()`,
>    `os.fsync()` — never a partial flush.
> 2. **Recover by truncating only a torn FINAL line.** On load, parse line by line. A length/JSON
>    mismatch or `JSONDecodeError` on the **last** line ⇒ treat it as a torn append: **truncate it
>    and continue** (the binding atomic-replace for that event never landed, so its effect was never
>    committed — dropping the torn intent is correct). A decode/frame error on **any non-final
>    line** ⇒ **fail closed** (corruption-halt: a non-tail corruption is not a crash artifact and
>    must not be silently swallowed).
> 3. **Anchor recovery on the binding atomic-replace, treat the ledger tail as advisory.** The
>    binding ledger (atomic `os.replace`) is the authoritative checkpoint; the WAL tail is replayed
>    only to roll *forward* any committed-intent-not-yet-checkpointed event. A dropped torn tail
>    therefore loses at most the one uncommitted intent, never committed state.

> **Adapted from commit_mutation: reused / changed.** *Reused:* atomic-replace
> (tmp+fsync+os.replace, `save_manifest` L191–197) for the binding ledger; append+fsync JSONL
> (`append_ledger` L241–245) for the run-ledger; the single commit funnel as the one auditable
> write path; derived-handoff-regenerated-on-every-commit (`render_continuation`, never
> hand-edited — F-035). *Changed:* **reversed the ordering** — ledger-append FIRST (intent/WAL),
> then binding atomic-replace, so a crash yields ledger-ahead-of-binding (replayable) instead of
> binding-ahead-of-ledger (ambiguous). Atomic-replace now covers the binding ledger and the
> run-ledger goes through the same funnel — closing the recovered model's "watchdog wrote
> status.json with plain write_text, only control_plane did atomic-replace" gap: **no plain
> `write_text` for any control-plane state that recovery reads — every such write goes through the
> executor's atomic path.**

> **The status sidecar is the ONE deliberate carve-out (not durable control state).**
> `runtime.json` / `.harnessd/status.json` (§2.3 — `{pid, started_at, last_tick_at,
> last_reconcile_at, incarnation, …}`) is a **best-effort, lock-free liveness surface** for an
> external pinger and `service status` reads. It is written **every poll**, so it CANNOT take the
> exclusive serialization lock (that would serialize a non-event against real mutations every tick)
> and is NOT part of the durable journal (edge-triggered append, §3.5). The two claims reconcile by
> scope: the sidecar (a) uses its **own** atomic tmp+rename (so a crash never leaves it torn) but
> (b) takes **no** serialization lock, and (c) **recovery NEVER trusts it for control state** — all
> control state is reconstructed from the binding ledger + WAL. It is a status mirror, not a source
> of truth.

### 4.5 Executor command surface (per-node generalization of the recovered six commands)

Read-only (shared lock): `show <node>`, `next <node>`, `validate`, `reconcile-inspect`.
Mutating (exclusive lock): `transition`, `heartbeat`, `release-lease`, `watchdog-checkpoint`,
and the **NEW** `claim` (the spawn-chokepoint slot-claim, §6) and `reconcile-apply` (§5).
`heartbeat`/`release-lease`/`watchdog-checkpoint` still blind-overwrite their own slice under the
lock **but now also present `owner_token`** so a stale owner cannot heartbeat over a live one — the
recovered model let `cmd_heartbeat` (L1440) blindly set `owner` with no epoch check; v1 requires
the token on every mutator, not just `transition`.

### 4.6 Single canonical clock (F-019)

All lease-freshness math (`now − last_heartbeat_at`, `now − last_progress_at`) uses **one canonical
clock: UTC**, and **all timestamps are stored timezone-aware ISO-8601**. The recovered incident
F-019 manufactured a false 3-hour-stale diagnosis by comparing UTC trace timestamps against
local-wall-clock supervision. The reconcile loop and every binding timestamp use UTC; rendering to
local time is a display concern only.

---

## 5. Reconciliation (on-restart + continuous)

Reconciliation keeps **actual (tmux) == recorded (binding ledger).** It is the *accounting* layer.
The recovery **policy** (what to do with a stale_suspect) is cluster ②; v1 reconcile does the
**mechanical** part: detect divergence, apply the unambiguous resolutions, escalate the rest.

### 5.1 Reconcile-on-restart (genesis-recovery, runs once per boot)

```
on daemon boot, after acquiring .harnessd.lock:
  1. load run-ledger with torn-tail tolerance (§4.4 box); replay WAL: for each event with
       seq > binding.last_applied_seq[node], deterministically re-apply it (verify pre-image
       generation, apply binding_delta, stamp last_applied_seq — §3.5/§4.4)
  2. list live tmux targets (tmux list-sessions/panes → set of live tmux_targets + pane_pids)
  3. for each binding:
       recorded-alive & tmux-present & session-uuid matches  → ADOPT (resume ownership, renew lease)
       recorded-alive & tmux-absent (or pane_dead), LEAF     → owned-but-dead → necro: mark dead,
                                                                stamp died_* terminal_signal, bump
                                                                lease_epoch, append run-ledger event
       recorded-alive & tmux-absent (or pane_dead), COORD    → owned-but-dead → mark dead, stamp
                                                                coordinator_died, bump lease_epoch,
                                                                append event, and ESCALATE (recover-
                                                                vs-reap is ②, §5.4 — NOT decided here)
       recorded-terminal                                     → leave (reconcile-once; no action)
  4. tmux-present & NO binding (alive-but-unowned)            → ESCALATE (orphan; record, hand to
                                                                cluster-② policy / L1)
  5. resume-not-double-spawn L1 (§7): if L1's binding is non-terminal and its tmux is gone,
     resume L1 from its binding; if its tmux is alive, ADOPT — never spawn a second L1.
```

### 5.2 Continuous reconciliation (the v1 loop)

The same sweep on a timer (the watchdog tick — one loop, one sweep, matches single-central §2.4-A).
Each tick: re-derive `liveness_state` per node from floor signals — *examples the cluster-② detector
MAY fuse, not the v1 floor*: transcript-JSONL growth, tmux `window_activity`/`pane_dead`, node-file
mtimes, `pane_pid` CPU. The detector sits behind the stable
`liveness(node) → {working|waiting|idle|dead, last_progress}` interface (the canonical enum, §3.2),
written through the executor; **which signals it fuses and how is cluster-② internals (§1.4)** —
cluster ① owns only the interface and the field. Apply the same divergence resolutions as §5.1.
**Owned-but-dead → reaped/necro'd (leaf) or escalated (coordinator, §5.4); alive-but-unowned →
escalated.** Edge-triggered: only state/condition *changes* append to the run-ledger.

### 5.3 The v1 boundary vs the deferred reconciliation controller

> **FORK — for user review (boundary, not a true fork; recommendation stated).** runtime-decisions
> §3 defers the *full desired-vs-actual reconciliation controller* (trigger: *"orphan/ghost cases
> the watchdog process-check misses"*). The v1 line:
> - **v1 IN:** the per-node read-tmux-vs-ledger divergence detection + the two unambiguous
>   resolutions (owned-but-dead → necro; recorded-terminal → leave) + **escalate** everything
>   ambiguous (alive-but-unowned orphan, dead-pid-but-live-children).
> - **DEFERRED to ②:** *automatically reconciling* the ambiguous cases (adopting an orphan into a
>   new owner, GC'ing ghost subtrees, the full controller). v1 **escalates** these rather than
>   auto-resolving them — which is the correct conservative posture for the commissioning phase
>   (*"don't auto-recover past a break — freeze and examine"*, runtime-decisions §5).
> - **Recommendation:** ship the detect+escalate loop in v1; let cluster ② add auto-resolution
>   behind the same escalation seat. This is a one-site add later (the escalation handler), which
>   is exactly why deferring it is safe under the sufficiency-cut test.

### 5.4 Two reapers — keep them distinct

- **Liveness reap (daemon-hosted, v1) — the v1 mechanical action is detect + escalate, not
  auto-recover.** The reconcile loop necros an owned-but-dead session (evidence-based: tmux gone /
  `pane_dead`), stamps a `died_*` terminal signal, never blind-kills. Coordinator vs leaf
  asymmetry, drawn at the **mechanism** level cluster ① owns:
    - a dead **leaf** (L5/L5+) is reaped → `FAILED` (the unambiguous resolution);
    - a dead **coordinator** is marked **owned-but-dead**, the daemon stamps `coordinator_died`
      (which fires on `pane_pid` death *regardless of subtree activity* — the cheap orphan-killer
      the subtree-gating misses, gap-review #2), and the daemon **ESCALATES** it. The
      **recover-vs-reap CHOICE** (adopt the orphan from the ledger vs give it up) is the cluster-②
      recovery *policy* reading the `coordinator_died` signal — **NOT** decided here (it is a §1.4
      DEFER). Cluster ① detects + escalates; ② chooses. This keeps §5.4 consistent with the §5.3
      detect-and-escalate boundary and avoids pre-committing the recovery policy.
  A coordinator is idle-actionable **only when its whole subtree is also quiet** (per-node
  live-descendant roll-up — visibility the daemon computes by prefix scan; this roll-up is why
  `liveness_state` must keep `waiting` distinct from `idle`, §3.2).
  **in_flight release-DECREMENT seat (④).** Every necro/collapse here is a single-writer terminal
  write (stamps `died_*`/`FAILED` + appends the run-ledger row), so it is also the point that carries
  cluster ④'s in_flight **release-decrement** — symmetric to the §6.1 claim-increment, riding the
  existing terminal write (no new writer; crash-safe via `last_applied_seq`; §3.6). The leaf-reap and
  the coordinator-died necro both release the slot the §6.1 claim reserved.
- **2-week resurrection GC (separate infra, NOT the daemon).** Collapse-on-finish (G37) holds a
  node's state resurrectable for 2 weeks keyed by its stable address; a separate lifecycle reaper
  GCs it after the window. **The daemon does not host this.** Do not conflate the evidence-based
  liveness reap with the time-based 2w garbage-collector.

> **Adapted: reused / changed.** *Reused:* the recovered/lifecycle model of evidence-based reap
> (never blind-kill), the coordinator-vs-leaf **asymmetry** (here drawn at the mechanism level:
> leaf-reap vs coordinator-detect-and-escalate; the recover-vs-reap policy is ②'s), live-descendant
> roll-up.
> *Changed / NEW:* there was **no** tmux↔ledger reconcile loop in the recovered code at all
> (liveness was inferred only from heartbeat-age, nothing checked actual tmux) — the entire
> reconcile sweep, the orphan escalation, and the `coordinator_died` process-death event are new
> in cluster ①.

---

## 6. The Single Spawn Chokepoint

One spawn path. It boots a pinned Claude Code (or Codex) actor in a detached tmux session, in role,
and — critically — **claims the slot in control-plane state BEFORE opening the actor** (the F-024
structural fix).

### 6.1 Claim-before-spawn (the F-024 fix, headline)

F-024: the recovered CAS guarded `transition` but `work_scoped_agent.py spawn` bypassed
control-plane state entirely, so a stale session double-spawned a duplicate actor. *"Spawning is
side-effecting and cannot be undone by a rejected transition. If the spawn happens before the
transition, the guard fires too late."* The fix makes spawn a **CAS-guarded transition into a
claimed state that must succeed before the actor opens:**

```
spawn(node_address, expected_state, expected_generation, expected_owner_token, level_config):
    # STEP 0 — PAUSE-SUBTREE READ-POINT (③'s human-control primitive; ① seats the enforcement here).
    #   Refuse to launch a child under a paused subtree: address-prefix check — if THIS node OR any
    #   ancestor binding has paused_at != null, ABORT before claiming. A paused subtree admits no new
    #   children. (Set/cleared only by the human control surface via the single writer — §3.2 / ③ §5.3.)
    if any(b.paused_at is not None for b in ancestors_inclusive(node_address)):  return  # paused — no spawn

    # STEP 1 — CLAIM (CAS-guarded transition, §4.2). Atomic. Fails if a concurrent/stale claim won.
    #   This claim seat also reserves the in_flight CLAIM-INCREMENT for cluster ④ (④ owns the slot
    #   COUNT; ① provides the seat — no new writer). Symmetric to the terminal release-DECREMENT
    #   (§3.6 / §5.4) so ④'s admission gate can't be an increment-only ratchet.
    claim = transition(node_address, expected_state=planned, target_state=claimed,
                       expected_generation, expected_owner_token,
                       new_lease_epoch = old+1, new_owner_token = mint(...))   # §8
    if claim aborted:  return  # someone else already claimed this slot — NO actor opened. F-024 closed.

    # --- ADMISSION SEAT (cluster ④ wedges here, between claim-accepted and actor-open) ---

    # STEP 2 — ADAPTER: read level config, assemble the runtime-NEUTRAL brief INCLUDING its
    #   load-manifest ("Identity — Load These Documents": the per-level role docs + always-loaded
    #   shared contract docs + referenced design docs the child READS at boot, per role_variant),
    #   pick runtime adapter; the boot call passes --system-prompt-file system_prompt_file (the
    #   CONSTANT shared minimal prompt — §6.2). The role rides the brief/manifest, NOT this flag.
    # STEP 3 — confirm model+runtime pinned (E32) BEFORE the child runs; on failure → escalate, RELEASE claim
    # STEP 4 — open the tmux actor (§6.2); record session_uuid + model_used into the binding (one writer)
    # STEP 5 — transition claimed → spawning → running as the actor confirms boot
```

The claim is a **distinct pre-step** so admission control (cluster ④) can wedge between
claim-accepted and actor-open **without re-opening the CAS**. If admission denies, or the adapter
cannot pin the configured model/runtime (E32), or the actor fails to open, the chokepoint
**releases the claim** (transition `claimed → planned`, bump epoch) — a FAILED claim is rolled back
atomically so the slot is reclaimable. (open Q resolved: crash-atomicity of a failed claim = the
release is itself a CAS-guarded transition, replayable via the WAL.)

**Two seats this pre-step provides.** (1) **Pause-subtree (③):** STEP 0 is the enforcing read-point
for the human-control pause primitive (③ §5.3) — the chokepoint **refuses** to launch a child under a
paused subtree (address-prefix check over the node + its ancestors). ① only seats the read-point; ③'s
human control surface sets/clears `paused_at` through the single writer (§3.2). (2) **in_flight
CLAIM-increment (④):** STEP 1's accepted claim is the seat where cluster ④'s in_flight slot count is
**incremented**. ④ owns the COUNT; ① provides the seat (no new writer). This increment is symmetric to
the **release-DECREMENT** carried on the terminal transaction (§3.6 / §5.4) — the two seats are a
matched pair so ④'s gate is a balanced counter, not an increment-only ratchet that leaks slots.

> **Adapted: NEW (the headline fix).** The recovered code had **no spawn command at all** and only
> `transition` was CAS-guarded. Claim-before-spawn is net-new: it extends the *same* CAS
> precondition pattern (§4.2) to the spawn path, which F-024 left open. F-024 was OPEN in the prior
> art (documented as discipline, never code-fixed); this makes it **structural**.

### 6.2 In-role boot — the H40 recipe (Claude-Code adapter)

The Claude-Code adapter boots the **pinned** binary with
`--system-prompt-file operational/shared/system-prompt.md` (H40 rank-1, 5/5 in-role, survived a
40-agent blind re-score). The flag delivers the **ONE shared minimal prompt — identical for L1–L5**,
NOT a per-level file and NOT `role.md` (H40 resolved, agent-definition-principles §4). **The role is
NOT in the prompt:** it is delivered as **documents the agent reads at boot** — the node's spawn brief
+ its load-manifest ("Identity — Load These Documents") plus the read-allowed harness docs (the
per-level `operational/L{n}/{soul,role,config}.md`, the always-loaded shared contract docs, and
referenced `design/*.md`), which the agent reads IN PLACE at their harness-root paths (no
inline-flatten). The role-bundle delivery is specified in `design/ROLE-RESOLUTION.md`. Concrete
invocation:

- **Binary:** `.cc-pinned/node_modules/@anthropic-ai/claude-code/bin/claude.exe`, version pinned
  `2.1.152`. The chokepoint **verifies the binary version/hash at spawn** (do not trust
  `DISABLE_AUTOUPDATER` alone — PINNED-CC.md notes it was not found in the binary strings; the real
  pin is the npm version + isolated prefix).
- **Flag:** `--system-prompt-file operational/shared/system-prompt.md` (REPLACES base block 2, keeps
  the identity line, keeps the 24-tool set, works interactively, OAuth-compatible). The file is the
  shared minimal prompt, the same for every level; the per-seat differentiation rides the brief +
  load-manifest, not this flag (selected by the binding's `role_variant`, §3.2). The file itself must
  be **read-allowed** to the CC process so it can be read at boot. **Do NOT** use
  `--append-system-prompt` (keeps full framing), `--agents`/`--agent` (does not inject persona),
  or `--bare` (reads auth strictly from `ANTHROPIC_API_KEY`, errors `Invalid API key` on an OAuth
  subscription token — a latent foot-gun guarded below).
- **Isolation env (exact set):** `CLAUDE_CONFIG_DIR=$HARNESS/.cc-pinned/config` (clean config — no
  inherited hooks/MCP/injections), `CLAUDE_CODE_OAUTH_TOKEN` (read via token-file `$(cat …)` /
  `_FILE_DESCRIPTOR` so the literal credential never lands in the pane or transcript),
  `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1`, `DISABLE_AUTOUPDATER=1`.
- **tmux:** create a **detached** session whose name is **derived from the one-spine address**
  (`harness:<collapsed-address>`), so the reconcile loop can match tmux↔ledger across respawn.
  First-boot trust/permission acceptance must be **deterministic for an unattended session**
  (pre-seed trust state in `CLAUDE_CONFIG_DIR` or use a non-interactive permission mode) — **not** a
  send-keys race against the trust dialog (the H40 experiment auto-accepted interactively; the
  production chokepoint must not). Pane capture is the readback channel for the reconcile/observe
  loop.
- **`--bare` guardrail:** if any level config selects a minimal tool surface, the chokepoint MUST
  NOT use `--bare` with an OAuth token; route tool-trimming through an OAuth-compatible mechanism.

> **Adapted from H40 / run_probe.sh: reused / changed.** *Reused:* the exact flag, env-var
> isolation set, token-never-in-pane discipline, detached-tmux + pane-capture pattern.
> *Changed:* generalized the one-off interactive experiment (`run_probe.sh`: auto-accept trust +
> type a probe + tear down) into a **daemon-owned, claim-before-spawn, per-node** path; tmux session
> names bound to the one-spine address (the experiment used ad-hoc names); first-boot trust made
> deterministic instead of a send-keys race; binary version verified at spawn.

### 6.3 Per-runtime adapter (hexagonal: neutral core + thin port)

The parent emits a **runtime-neutral task contract** (identity/address, spec, frozen acceptance
artifact, interface contracts, constraints, workspace location, reporting expectations —
**identical across runtimes**). The adapter injects **only three** runtime-specific things:
(1) tool manifest, (2) harness invocation, (3) output format. Swapping a level's runtime = swapping
its adapter. Model+runtime is **config-time, not run-time** (E31): the chokepoint reads the level
config; no agent picks its own or its child's model. Assignment: L1–L4 = Opus 4.8 / Claude Code;
L5 = GPT-5.5 / Codex; L5+ (#review) = Opus 4.8 / Claude Code (judgment diversity).

**Spawn-failure contract (E32, no silent fallback).** The adapter MUST confirm it pinned the
configured model+runtime **before** the child runs. On any of {**auth-expired**, model-unavailable,
override-rejected, runtime-down}: do **not** spawn on a substitute, do **not** best-effort —
**release the claim** and emit a spawn-failure escalation to L1 (child-address + configured vs actual
model/runtime + **which class fired**); L1 alerts the user. The chokepoint always writes the
**actual** `model_used` into the binding via the single-writer path (config = intent; recorded
`model_used` = fact; a checker asserts every spawned child has a `model_used` == configured, or a
corresponding escalation exists).

**Auth-expiry is a DISTINCT failure class, not a model-unavailable.** An expired/lapsed OAuth token
makes *every* spawn hit the E32 "cannot pin the model" path at once — so without a distinct class it
masquerades as a **fleet-wide model-outage storm**, and (worse) a post-expiry reboot cannot respawn
even L1. The chokepoint classifies an auth failure as **`auth_expired`** (separate from
`model_unavailable`) so the escalation says "refresh the token," not "the model is down," and so a
storm of identical `auth_expired` escalations is recognizable as one credential problem. Token health
is also a **named genesis precondition** (§7): genesis verifies the credential before spawning L1, so
the very first spawn fails *loudly on the credential* rather than as a mystery model-pin failure.

> **Codex adapter — UNDERSPECIFIED (flagged).** The Claude-Code half is fully measured (H40). The
> **Codex** invocation (how the Codex harness is spawned/driven, its tool manifest, its output
> format) is NOT yet specified in the source material; the L4+L5 Codex audit is explicitly **owed**
> (runtime-and-model-map.md). v1 marks the Codex runtime as an **adapter port to be supplied** —
> the seat (the three adapter slots + the neutral contract + claim-before-spawn) is defined; the
> Codex-specific fill is owed. Result-flow needs no runtime-specific return channel (F33): both
> runtimes write durable truth into the work node + post a best-effort bus pointer; the parent
> re-reads the node.

### 6.4 Resume / necro — a spawn variant through the same chokepoint (with the gate firewall)

"Resume" appears throughout reconcile-on-restart (§5) and genesis (§7); this is its contract. It is
**not** a separate code path — it is a **variant of the spawn chokepoint** that re-adopts an
existing address instead of claiming a fresh one. Sufficiency-cut item #8 ("basic necro —
`--resume` + delta brief — WITH the gate-firewall carve-out") makes the carve-out a v1 INCLUDE, and
it lives in the chokepoint cluster ① owns.

The resume path:

1. **Re-adopt the address** through `claim` (§6.1) — the **re-adopt variant**: a CAS-guarded claim
   with `expected_state ∈ {running, dead}` (the §3.3 re-adopt edges), NOT the fresh-claim's
   `expected_state=planned`, on the **existing** node-address, **bumping `lease_epoch` and re-minting
   `owner_token`** (the prior incarnation, if it returns, is now fenced — §8). Resume is therefore
   claim-before-spawn too; it never double-spawns a live address (the §5.1 ADOPT-vs-resume split
   decides which).
2. **Assemble a delta brief** — not the full original brief: what changed since the prior
   incarnation (new messages, parent answers to an `ESCALATED`, reconcile findings), pointing at the
   durable work node the fresh instance re-reads (`status.md`, `log.md`, `report.md`, frozen
   acceptance — `agent-lifecycle.md`'s stateless-respawn recovery).
3. **Boot via §6.2** with the shared minimal prompt + the (delta) brief and its load-manifest,
   recording the **new** `session_uuid` into the binding via the single writer.

**The gate firewall (LOCKED correctness invariant, runtime-decisions §2.8): NEVER `--resume` a
session across a quality-gate boundary.** A session that has crossed a gate (e.g. an L5 whose work
went to `#review`, or any node whose plan was approved at a `PLAN-ALIGNMENT-GATE`) must be **re-spawned
fresh**, never resumed — carrying the pre-gate session's conversational context past the gate
re-introduces the exact contamination the gate exists to stop. This is **correctness, not
optimization**: the chokepoint **refuses** a `--resume` when the node's gate-crossing flag is set,
and falls back to a fresh spawn with a delta brief. The chokepoint enforces the refusal in cluster
①; the **gate-crossed signal itself** is a binding field cluster ② maintains
(`gate_crossed_at` / equivalent) — cluster ① reads it and enforces the firewall, ② decides when it
flips.

> **Adapted: NEW (mechanism) + LOCKED (firewall).** The recovered code had `--resume`-style
> continuation but no gate concept (single reviewer loop, no plan-alignment gate). The resume-as-
> spawn-variant routing and the never-resume-across-the-gate firewall are net-new here, promoted
> from runtime-decisions §2.8.

---

## 7. Genesis / First-Boot

LOCKED sequence (runtime-decisions §4 + gap-review #1 resolution):

```
1. USER launches the harness APP.
2. The app installs/loads the launchd user agent + the harnessd-pinger job (§2.6), and starts
   harnessd (KeepAlive=true, RunAtLoad=true, ThrottleInterval≥10).
3. harnessd acquires .harnessd.lock, writes runtime.json.
4. PRECONDITION CHECK (fail loud, do not spawn on a bad precondition):
     - credential health: the OAuth token / CLAUDE_CODE_OAUTH_TOKEN is present and unexpired
       (refresh if a refresh path exists; else escalate `auth_expired` to the user — §6.3). This is
       a NAMED genesis precondition precisely because a lapsed token makes the FIRST L1 spawn fail
       as a mystery model-pin error otherwise.
     - pinned-binary present + version/hash verified (§6.2).
5. harnessd runs reconcile-on-restart (§5.1):
     - first boot ever: binding ledger empty → nothing to reconcile.
     - relaunch: read ledger → replay WAL (torn-tail-tolerant, §4.4) → reconcile tmux → necro the
       dead → resume L1.
6. If no live, non-terminal L1 binding exists:
     - SPAWN L1 as root via the single spawn chokepoint (§6), in role
       (--system-prompt-file operational/shared/system-prompt.md — the shared minimal prompt — with
       L1's load-manifest in the brief; role_variant = L1), claim-before-spawn at address (the L1
       root address).
     - REGISTER L1 as the root node in the binding ledger (parent_address = null; it is the only
       node with no parent — every other node has a declared parent by the supervision-tree
       invariant).
   Else (a live or resumable L1 binding exists):
     - RESUME, do NOT double-spawn (the F35 stable-address resume-not-double-spawn rule).
```

L1 has no parent agent — **the daemon is what starts L1** (closing the gap-review genesis hole:
*"every bootstrap is child-spawned-by-parent; L1 has no parent and nothing starts it"*). The daemon
is the root of the supervision tree's *custody* chain even though it is not an agent.

> **FORK — for user review (minor).** Ordering of the daemon's process-level resume of L1 vs L1's
> own doc-level boot-reconciliation (L1 reads README → portfolio → threads → comms). These are two
> different reconciliations firing at L1 boot. **Recommendation:** the daemon resumes/spawns the L1
> *actor* first (process-level), then L1 performs its own doc-reconcile *inside* its session
> (agent-level) — the daemon establishes custody, then the agent orients. They are layered, not
> competing.

The harness **app** is plausibly also the human control-surface (runtime-decisions §4: *"dents the
human-channel gap"*). v1 treats that as a **side-benefit, not a committed cluster-① deliverable** —
the human control surface (pause-subtree flag, human-kill routed through the harness path that
stamps ledgers, answer-escalation slot) is **cluster ③**. Cluster ① ships only the app→daemon→L1
genesis path.

---

## 8. Fencing

**Why in v1 (defend against "defer it"):** fencing's failure mode (split-brain, incident F-024) is
**silent**, so its trigger is a **design event** (enabling concurrent-spawn or live-necro), not a
failure event — you cannot wait for it to "bite" in a run, because it fails *quietly*. And it is
**cheap once single-writer exists** (it is three extra fields + one extra CAS precondition).
(runtime-decisions §2 item 11 + §3 special-status note.)

**Mechanism:**

- **`lease_epoch`** — a monotonic int per node, **bumped on every claim / adopt / respawn /
  ownership-transfer**, rotated **in the same atomic transaction** as the actor-changing transition
  (F-012 fix: no window where state advanced but ownership didn't).
- **`owner_token`** — a composite identity minted at claim/adopt time:
  `address:subagent-id:session-uuid:lease_epoch` (the recovered
  `role:subagent-id:session-uuid:lease_epoch` format with `role` → the one-spine `address`). Because
  it embeds the epoch, **the token is self-fencing** — comparing tokens compares epochs.
- **CAS on transition AND spawn** — every mutator (transition, heartbeat, release-lease,
  watchdog-checkpoint, **claim/spawn**) presents `expected_owner_token`; a mismatch aborts the
  mutation. This is what extends the recovered `transition`-only guard to **every** write path,
  including the spawn path F-024 left unguarded.

**Stale-return fencing (non-destructive).** If an old actor returns after a respawn and tries to
act, its token's epoch is lower than the live binding's; the mutation aborts and the executor
records **`stale_return_ignored`** in the run-ledger. *The old actor is de-authorized, not
auto-killed* (`watchdog-design-01.md`). Its eventual terminal signal, if any, is journaled with
`terminal_signal = FENCED` so cluster ②'s policy can tell "fenced/de-authorized" apart from
"completed" / "died-infra" / "died-methodology."

> **Provenance — promoted from phase-2 design / NEW in code.** *Promoted from
> `phase-2-runs/research/watchdog-design-01.md` (proposed-but-never-coded):* the composite
> `owner_token` format, the "lease belongs to the work unit, restart resumes from ledger state"
> principle, and the `stale_return_ignored` non-destructive de-authorization event. *NEW in code
> here:* `lease_epoch`/`owner_token` were **entirely absent from the recovered control plane**
> (`self-improvement-harness/` — its manifest carried only a name-string `owner` with no epoch, and
> its `control_plane.py` `cmd_transition` checked only `expected_state` + `len(ledger)`, no
> `--expected-owner-token`; F-012/F-024); the CAS-on-every-mutator and CAS-on-spawn are new (the
> phase-2 plumbing exposed `--expected-owner-token` on a supervisor but never gated a CAS spawn);
> epoch rotation made transactional with the actor-changing transition is new. This is **promoting a
> proven-on-paper lease into code for the first time**, not inventing it against a clean baseline.

---

## 9. The Seats Provided to Clusters ②/③/④

Cluster ① provides **seats, not internals.** Each deferred policy attaches to a field or a
chokepoint defined above — so adding it later is a one-site change, not a re-plumb.

**To cluster ② (Liveness & lifecycle):**
- the binding fields the evidence-lease state-machine reads/writes: `condition`, `suspect_since`,
  `recovery_attempts`, `stale_grace_checks`, `last_evidence`, `liveness_state`, `last_progress_at`,
  `last_heartbeat_at`.
- the **terminal-signal field + the closed event set** (`signal_DONE/FAILED/ESCALATED`,
  `coordinator_died`, `died_infrastructure`, `died_methodology`, `coordinator_completed`,
  `stale_return_ignored`) — recovery branches on the terminal class (F-017).
- `auto_resume_command` + the `--run-recovery` `allow_recovery` plumbing (the two-keyed interlock):
  carried by cluster ①, **fired** by cluster ② (the daemon never auto-resumes without both the
  field and the flag).
- the reconcile **hooks**: the per-node read-tmux-vs-ledger pass (where ② plugs the multi-signal
  detector behind the stable `liveness(node)` interface), the escalation seat for ambiguous cases
  (where ② plugs auto-resolution), and the **coordinator-died ESCALATE seat** (§5.4 — ② reads
  `coordinator_died` and chooses recover-vs-reap; ① only detects + escalates).
- the **gate-crossed signal** the resume firewall reads (§6.4): cluster ① *enforces* "never resume
  across the gate" by reading a binding field (`gate_crossed_at` / equivalent); **② maintains when
  that field flips** (it owns gate detection). The enforcement is ①'s; the signal is ②'s.
- the watchdog **loop scheduling** (the daemon runs the tick; ② supplies the loop body / probe /
  state-machine, written through the executor — never a second writer).

**To cluster ③ (Transports):**
- the **terminal-signal journaling** contract: the agent writes a durable `<node>/.signal.json` as
  its last act; the reconcile sweep detects it and the executor journals from the durable read
  (§3.5) — so the sign-off check reads the **journal**, and a dropped live bus nudge can at worst
  **delay** journaling to the next sweep, **never** lose the durable row or cause a false sign-off
  failure. The bus carries a best-effort *wake* (triggering an immediate sweep); the durable fact
  lives in `.signal.json` → the ledger + the work-node `report.md`.
- the human control surface attaches to the harness app (genesis path) and routes human-kill
  **through the executor's stamping path** (never raw tmux), and the answer-escalation slot rides
  the `terminal_signal = ESCALATED` + `terminal_note` carried in the binding.
- the **pause-subtree read-point**: ③'s human control surface sets/clears the `paused_at` binding
  field (§3.2) — set/cleared **only** through the single-writer executor, never raw — and ① **seats
  the enforcement** at the §6.1 claim-slot pre-step (STEP 0), which refuses to launch a child under a
  paused subtree (the node OR any ancestor by address-prefix). The companion read-point in ②'s
  recovery loop (skip prod/respawn for a paused subtree) is the other half; both are required or
  `paused_at` is a flag no one honors.

**To cluster ④ (Scale-as-resource):**
- the **claim-slot pre-step** in the spawn chokepoint (§6.1): admission control wedges between
  claim-accepted and actor-open **without re-opening the CAS**. Per-runtime ceilings / 429-backoff /
  resource envelope all gate that same single spawn path. The claim-then-admit-then-open ordering is
  defined now precisely so ④ has a clean insertion point.
- the **in_flight increment/decrement seat pair** for ④'s slot count (④ owns the COUNT; ① provides
  the SEATS, no new writer). The §6.1 accepted-claim is the **claim-INCREMENT** seat; the
  single-writer **terminal transaction** (the §3.6 `done`/`failed`/`dead` collapse write, AND the
  §5.4 necro / §5.1 reconcile-finds-dead path) carries the symmetric **release-DECREMENT** — it rides
  the existing terminal write, crash-safe via `last_applied_seq`. The pair is matched on purpose so
  ④'s admission gate is a balanced counter, not an increment-only ratchet that leaks slots.

---

## 10. Open Seams (recorded, not resolved here)

- **run-ledger vs project `log.md`:** are terminal-signal entries mirrored into `log.md`, or kept
  strictly in the daemon run-ledger? Recommendation leans "strictly in the run-ledger; `log.md`
  stays agent-written project history" — but the mirror decision is left open.
- **`role_bundle_hash` as a fencing surface:** whether a role-bundle change mid-flight should be
  detectable/fence-triggering is recorded as a binding field (`role_bundle_hash`) but the policy is
  open.
- **launchd token lifecycle:** token *health* is now a named genesis precondition and `auth_expired`
  is a distinct spawn-failure class (§6.3/§7). What remains open is the **refresh mechanism** for a
  long-lived always-on daemon (token-file vs `_FILE_DESCRIPTOR`, whether an unattended automatic
  refresh path exists or expiry must always escalate to the user) — unaddressed in the source
  material, flagged for the credential design.
- **`--system-prompt-file` re-verification on version bump:** H40 lists the re-checks for the shared
  `operational/shared/system-prompt.md` boot (flag exists, still REPLACES base block 2, still
  interactive, still OAuth). Whether genesis runs this as a self-check is unresolved.
- **Codex adapter fill** (§6.3) — owed.

---

## Adaptation summary (control_plane.py → DAEMON.md)

Sourcing note: `control_plane.py`/`manifest.yaml`/`watchdog.py` are the **recovered**
self-improvement-harness; rows marked *(phase-2)* are promoted from
`phase-2-runs/research/watchdog-design-01.md` (proposed-but-never-coded), NOT from the recovered code.

| Component | Reused from the recovered control plane | Changed / NEW for the tree |
|---|---|---|
| Mutation skeleton | read→validate→commit-inside-lock (cmd_transition) | per-node binding; resident not per-CLI |
| CAS | expected-state + expected-ledger-entries (L1511/L1516) | + `expected_owner_token` *(phase-2 token, first time in CAS)*; per-node `generation` not global `len(ledger)` |
| Lock | `fcntl.flock` SH/EX contextmanager (L248) | one serialization domain (was two: control-plane + workboard); CLIs route through daemon, no external read-modify-replace |
| Atomicity | tmp+fsync+os.replace; append+fsync JSONL (L191/L241) | ordering reversed: ledger-append FIRST (WAL); covers binding ledger; **torn-tail tolerance ADDED** (recovered `load_ledger` RAISES on a torn line — §4.4); WAL record carries `binding_delta`+pre/post `generation`+`last_applied_seq` watermark; no plain write_text for recovery-read state (status sidecar is the lock-free carve-out) |
| Validate | pure `validate()` errors-block/warnings-allow (L618) | per-node admission check |
| Manifest | `activity_lease`+`watchdog`+`observation_window` blocks | one block → map keyed by node-address; + `lease_epoch`/`owner_token` *(phase-2)* / `session_uuid`/`liveness_state` (canonical working\|waiting\|idle\|dead) / `terminal_signal` / `last_applied_seq` |
| Workboard stream | `{stream_id,status,owner,stop_condition,write_targets,evidence_refs}` | merged onto the node record, keyed on one-spine address (was separate file/lock) |
| Run-ledger | append-only JSONL event journal; edge-triggered; reconcile-once | keyed by node-address; + global seq (= replay watermark); + record framing (len/crc); + first-class terminal/death events; + §3.6 terminal mapping table |
| Resume / necro | `--resume`-style continuation (no gate concept) | NEW: resume = spawn-variant through the chokepoint (re-adopt + bump epoch + delta brief); LOCKED gate firewall (never resume across the gate) |
| Spawn | (none — no spawn command existed) | NEW single chokepoint; claim-before-spawn (F-024 fix); H40 in-role boot; per-runtime adapter |
| Reconcile | (none — only heartbeat-age inference) | NEW tmux↔ledger sweep; on-restart + continuous; orphan escalation; `coordinator_died` |
| Daemon | (none — explicitly deferred) | NEW resident launchd-hosted process; PID/lock; relaunch=recovery; genesis |
| Watchdog ownership | observer-writes-through-executor | loop hosted in the resident daemon; in-process not shell-out |
