# Runtime Model — Decisions, Sufficiency Cut & Commissioning Plan — 2026-06-04

Companion to `arch-gap-review-2026-06-04.md` (the adversarial gap review that triggered these). Captures the runtime-model decisions from the 2026-06-04 design session, the build cut (include-now vs defer), and the bring-up/commissioning method. These are decisions, not yet propagated into the canonical design docs.

---

## 1. Liveness / ownership synthesis (LOCKED)

Four composed layers, each taken from its best source — they are orthogonal, not competing:

- **Detector (ours).** Multi-signal, *observed-not-self-reported*: Claude transcript-JSONL growth + tmux `window_activity`/`pane_dead` + node mtime + `pane_pid` CPU. Matches the recovered research's rule "never infer progress from heartbeat alone." Day-one impl is **thin** (JSONL-growth + pane-alive) behind a stable `liveness(node) → {alive, working|idle, last_progress}` interface; multi-signal fusion is deferred behind that interface.
- **Control layer (recovered research — `watchdog-design-01.md`).** Evidence-**lease** state machine `healthy → stale_suspect → recovery_in_progress → failed_confirmed`; *"move to failed only on explicit evidence, not elapsed time."* FULL machine for **persistent coordinators**; **light sign-off-or-fail** for **ephemeral leaves** (L5/L5+).
- **Accounting (supervision tree + reconciliation).** Every node has exactly one parent-owner (supervision tree); the binding ledger is the authoritative registry; a **continuous reconciliation loop** keeps actual (tmux) == recorded (ledger) — owned-but-dead reaped/necro'd, alive-but-unowned escalated. Solves the **orphan** problem (incl. dead-coordinator-with-live-children).
- **Fencing (recovered research — `lease_epoch` + `owner_token` + compare-and-set).** Rejects a *stale-but-accounted-for* actor's action at the instant it acts. Solves the **stale-authority** problem (split-brain, incident F-024) that accounting alone cannot. **INCLUDED in v1** (silent-failure class; cheap once single-writer exists).

Compose orthogonally: **accounting** = single owner always; **fencing** = stale owner's action fails.

**Daemon charter (one line):** the daemon maintains the **accountability invariant** — single-owner-always, continuous reconciliation, fenced ownership transfer. Watchdog, spawn, ledgers all hang off that. Precise guarantee: *"every session owned, reconciled within bounded time, stale actions fenced"* (a brief reconciliation lag is expected; fencing makes the lag safe).

Concepts (for future readers): supervision tree (Erlang/OTP), reconciliation loop / owner-references + orphan-GC (Kubernetes), fencing token (Kleppmann). The intuition: chain-of-custody — every agent always has a known handler.

---

## 2. Sufficiency cut — INCLUDE in v1 (11)

The test for "now": *retrofitting it later means re-plumbing every call site* (structural) → now; *attaches at one known site later* → defer. **Single-writer is the keystone** — it's what makes most elaborate machinery a one-site add later, so it's what makes deferral safe.

1. **Single-writer executor** — one code path mutates state (the keystone; cheaper *and* makes deferral safe).
2. **Binding ledger** — node → uuid + state + owner + `lease_epoch`/`owner_token` fields.
3. **Terminal-signal artifacts** — L5 `DONE/FAILED/ESCALATED` file + durable coordinator-completion row.
4. **Thin detector behind a stable interface** — JSONL-growth + pane-alive day-one.
5. **Simple watchdog loop** — idle → prod → mark-failed → respawn; **+ coordinator process-death detection** (cheap orphan-killer the subtree-gating misses).
6. **Supervision-tree invariant** — one parent-owner per node (≈ free, it's the hierarchy).
7. **Reconcile-on-restart** — daemon boot reads ledger, checks tmux, marks-dead/necros.
8. **Basic necro** — `--resume` + delta brief — **with the gate-firewall carve-out kept in: never resume across the gate** (correctness, not optimization).
9. **Single spawn chokepoint** — one spawn path (where admission control later attaches).
10. **Harness-app + daemon** — genesis + the host for 1–9.
11. **Fencing** — `lease_epoch` + CAS on transition/spawn (moved in from defer; silent-failure class).

---

## 3. DEFER — recorded with trigger + where the design lives

| Deferred | Pull in when… | Design already exists? |
|---|---|---|
| Full lease recovery state-machine (stale_suspect → recover → adopt) | false-idle kills destroy real work, or multi-claimant ambiguity | **Yes — `watchdog-design-01.md`** |
| Multi-signal detector fusion (window_activity + CPU) | thin detector's false-read rate bites in a run | partial |
| State-sensitive suspicion windows (per-state W) | a single conservative W proves too coarse | `watchdog-design-01.md` (mentioned) |
| Continuous reconciliation *controller* (full desired-vs-actual) | orphan/ghost cases the watchdog process-check misses | no |
| Corrupt-jsonl → cold-respawn fallback | first observed `--resume` failure (loud, one-line add) | no |
| Cost-keyed resume-vs-fresh policy | replay token cost becomes material | no |
| Admission control + 429/backoff + per-runtime ceilings + resource envelope | run wide enough to hit a rate/resource limit | partial (spawn chokepoint exists) |
| Coordinator context-recycle policy | a long-lived coordinator's quality visibly drifts | no |
| Elaborate human control surface / sophisticated bus / downward-escalation-to-collapsed-child | cluster ③ work or a real need surfaces | no |

**Note on fencing's special status:** its failure (split-brain) is *silent*, so its trigger is a **design event** (enabling concurrent-spawn or live-necro), not a failure event — which is why it was pulled into INCLUDE rather than deferred.

---

## 4. Genesis (LOCKED)

User launches a harness **app**; the app boots the always-on daemon and spawns L1 as root. Lease-state-in-the-ledger ⇒ relaunch = recovery (daemon reads ledger, reconciles tmux). Remaining design = daemon/app internals + reconcile routine (cluster ①). The app is plausibly also the human control-surface (dents the human-channel gap).

---

## 5. Commissioning / bring-up method (LOCKED)

**Run a real, non-trivial job — one the system is designed for — slowly, traced, expecting breakage.** The goal is NOT the output; it's to observe behavior and find what breaks early.

- **Failure-finding stance.** Assume everything is probably broken; a clean run is *suspicious* (job too easy, or we didn't look hard enough). **Choose the job to maximize stress on the scary joints:** decomposition (L2/L3 carving), concurrency (→ fencing), review (L5/L5+), genuine ambiguity (→ escalation), length (→ coordinator persistence/context). Job choice *is* test design.
- **Run slow + heavily traced.** Low concurrency, watch each step. The run is the first real exercise of the observability layer ("watching the water move" = reading the ledger/trace). Don't auto-recover past a break — freeze and examine.
- **Connectivity smoke first.** A ~5-min trivial-signal check that the pipes are physically wired (one spawn, one sign-off, one collapse) *before* pouring the real job in — so when the real job misbehaves we debug *agent behavior*, not a broken spawn.
- **Two pressures, two passes.** Slow single flow finds **joint** leaks (detection, wake, sign-off, reconciliation, escalation); then **pressure-up** (concurrency, wide tree) finds **load** leaks (fencing races, admission/rate-limits, resource ceilings) — where most DEFERRED items surface.
- **This is how deferred triggers get pulled:** controlled provocation, not waiting for prod.

Named lineage: tracer bullet (Pragmatic Programmer), walking skeleton (Cockburn), commissioning / leak-and-pressure testing (plant/plumbing). The build's walking-skeleton order exists *so that* there are pipes to run water through.

---

## 6. Build clusters + order

1. **① Harness-as-a-process** — daemon, single-writer executor (adapt the recovered control-plane), ledgers + lease fields, reconcile (on-restart + continuous), genesis. *Substrate; everything sits on it.*
2. **② Liveness & lifecycle** — lease state-machine + detector + leaf/coordinator split + terminal-signal artifacts.
3. **③ Transports** — bus wire (+ reconcile ARCHITECTURE.md:156), wake contract, escalation-answer-down, human channels (via the app).
4. **④ Scale-as-resource** — admission gate (= lease's claim-before-spawn), per-runtime ceilings, 429/backoff, resource envelope.

Then: build skeleton → connectivity smoke → real-job commissioning (slow, traced) → pressure-up → pull deferred items as their joints leak.

---

## 7. Phase-1 (Cluster ① / `design/DAEMON.md`) decisions + carried assumptions (2026-06-05)

`DAEMON.md` authored + adversarially reviewed (workflow). All four design forks **CONFIRMED as recommended**:
- **Daemon shape:** single-central `harnessd` — one writer / one serialization domain, preserving the single-writer keystone. SPOF answered by relaunch=recovery (lease-state in the ledger, not RAM) + the §2.6 external-pinger hang defence, **not** by sharding. Per-node rejected (forfeits the keystone; N lock domains; no atomic cross-node commit; messier).
- **Ledger storage:** single keyed `binding-ledger.yaml` — atomic whole-tree commits; cross-process clobber closed by routing all mutation through the daemon. File-per-node is the "revisit past hundreds of nodes" escape.
- **Write-race model:** intent-first WAL (append framed run-ledger record → atomic-replace binding; torn-tail-tolerant load; `last_applied_seq` watermark). Closes the lost state-ledger-races lens.
- **Seat layout:** per-seat row (one binding per `address#seat`; independent leases; flat reconcile sweep).

**Carried assumption — hold consciously, do NOT auto-defer: L5 is a deliberately-minimal, mechanistic code-writer.** Its task is bounded — make the frozen acceptance tests pass; escalate ambiguity, don't decide (no real judgment/multi-step autonomy). This is *why* the **Codex-adapter fill** (the cross-runtime spawn half — owed; the parked "L5 Codex audit") is low-risk to defer: even worst-case the L5 task is mechanistically simple, little can go wrong, and the role is **reducible further** if something doesn't work. We carry this explicitly: if it ever stops holding (L5 needing genuine judgment), the Codex-adapter risk re-opens and must be addressed before a real Codex spawn.
