# INTAKE → DELIVERY — The End-to-End Arc

The canonical end-to-end path from a user request to a delivered product on the L1–L5 harness. This is the **application arc** that rides the substrate (the 0–16 build queue, `harnessd/IMPLEMENTATION-PLAN.md`); it is **not new substrate**. It connects pieces that already exist — the intake/grilling session, the intent-spec contract, the spawn chokepoint, the deliverable binding block, the write-jail — and names the one genuinely-new mechanism the full arc needs: **control-plane promotion** out of the gitignored `/runtime/` tree.

> **Status:** v1 design. The **full arc including promotion is v1** (user decision, 2026-06-05). Register provenance: closes the V3 register row (`working-notes/DEFERRED-REGISTER.md`) — *"Intake → L2 arc + product delivery / promotion-out-of-/runtime/."* Stages 0–5 ride the existing substrate plus one new intent-spec field (the delivery destination). The new build code is the **promotion increment** (§3), registered as a new IMPL-PLAN increment after the substrate (17+).
>
> **Two user decisions baked in (2026-06-05):** (i) the full arc incl. promotion is v1; (ii) the **delivery destination is captured AT INTAKE** — a user-path (e.g. `~/Projects/foo`) or a git remote — as a field of the intent-spec.

---

## 1. The Six-Stage Arc

Each stage points at the doc that owns it; this section connects them, it does not duplicate them.

### Stage 0 — Kickoff (human → L1)

The user reaches the running, persistent, **genesis-spawned L1** and states a request. L1 is started by the daemon at the L1-root address (`DAEMON.md` §7) and is an interactive Claude Code session with no parent agent. The v1 channel is direct: the user **attaches to L1's tmux pane and converses**. This is not a fork — it is a conversation with the live L1. A `harnessctl message L1` convenience is a later nicety (TRANSPORTS, human-channels, mostly deferred).

### Stage 1 — Intake → intent-spec

L1 does **not** grill inline. It **dispatches a separate "grilling session"** (`operational/L1/intake-session-template.md`) — a throwaway elicitation seat that runs the M50/K45 method and returns **only the finished intent-spec**, keeping L1's portfolio-holding context clean. The session returns the artifact, not its conversation. The returned spec satisfies the 8-field contract (`operational/shared/intent-spec-contract.md`): Outcomes; the hierarchically-IDed requirements table; the per-area opinionated/delegated + technical-fluency map; the must-never-fail decomposition; the ID→intent-span map; a per-requirement trace-block; the reflect-back script + confirmation status; and (**§8, new for this arc**) the **delivery destination** — the user-path or git remote where the finished product is delivered, captured at intake and consumed by promotion (§3). L1 reads the reflect-back script to the user and, on confirmation, **freezes the spec as the signed brief**. L1 **owns and guards** it for the project's life.

### Stage 2 — Project genesis (L1 writes the project node)

On a confirmed intent-spec, L1 **claims and creates the project node** at the logical path `proj/{project}/` (rooted at runtime under `/runtime/`, §4) via the spawn chokepoint, and writes into `client-brief/`: `intent-spec.md` (the canonical frozen brief), plus `vision.md` and `priorities.md` (the L1-authored views, §2). Project nodes are children of the L1-root, so this is an **L1 write within L1's own subtree** — permitted by the write-jail (`SECURITY.md` §1.3). The `client-brief/{vision,priorities}.md` files are written at project creation and are **immutable** (`WORKSPACE-SCHEMA.md` §130–134, §255–256).

### Stage 3 — L1 spawns L2

L1 spawns L2 at the project node through the **single spawn chokepoint** (`DAEMON.md` §6, `role_variant=L2`), with a brief whose load-manifest **points at `client-brief/`** — read in place, **pointer-not-payload**, never copied. L2 reads `client-brief/vision.md` + `priorities.md` (`operational/L2/spawn-template.md`), produces the concept design (component map + interface contracts + ADRs + per-module specs), and drives realization through the coordinated planning round into the L3/L4/L5 cascade (`PROJECT-PLANNING.md`; the cluster specs own the mechanics — referenced here, not duplicated).

### Stage 4 — Execution → complete

The cascade builds the product **inside `/runtime/proj/{project}/`**, every agent write-jailed to its own node subtree (`SECURITY.md` §1.3). Completion flows **up** through the frozen contracts as terminal signals (`DAEMON.md` §3.6); each parent collapses and synthesizes its children's results. L2 runs the final cross-area integration review and **reports project-complete to L1**.

### Stage 5 — Final acceptance (L1)

> **Authority ruling (user, 2026-06-11):** during the test/commissioning phase, Stage-5 acceptance
> does NOT require a user confirmation round-trip — L1 (or the supervising operator) evaluates
> intent-fidelity against the frozen intent-spec and triggers promote. For REAL client use the
> verdict returns to the user via the playback-escalation mechanic (QUALITY-GATE §L1-gate; the
> L1-closing-protocol increment) — that mechanic is registered, not yet built. This note
> reconciles the apparent contradiction between this section and QUALITY-GATE's
> "the user renders the verdict."

L1 judges the assembled result against the **frozen intent-spec** — the anchor it has guarded since Stage 1 (the handbook's Concept Review / Result Shaping posture; `PROJECT-PLANNING.md` Phase 7). This is an **intent-fidelity** judgment, not a re-do of the technical review below. On **accept** → L1 triggers delivery (Stage 6). On **reject** → L1 escalates back down, bounded. The intent-spec is the single thing acceptance is measured against.

### Stage 6 — Promotion / delivery (control plane)

On L1 **final-accept**, the **daemon / control plane promotes the finished product OUT of the gitignored `/runtime/` project node TO the delivery destination captured at intake** (§3). The concrete trigger: L1 runs **`harnessctl promote <project-node-address> --decision accept`** from its own pane (or the operator does); the CLI serializes the request to the resident daemon's IPC `promote` verb, and the **daemon** performs the cross-jail copy/push and stamps the binding via `executor.deliver` — the CLI stays a client, the executor stays the single writer, promotion stays a harnessd action. After delivery, **project teardown / reclaim** of the `/runtime/` tree is a **deferred follow-on** (register D7), not part of v1 promotion.

---

## 2. Connectivity — the frozen intent-spec and its client-brief views

The arc has **one canonical brief and two derived views of it**, all in `client-brief/`:

- `intent-spec.md` — the **canonical frozen brief**. Owner L1; produced by the grilling session; frozen at reflect-back confirmation (`operational/shared/intent-spec-contract.md`). It is the topmost spec on the SDD fidelity spine and the source of every minted requirement ID. **Everything downstream traces to an intent-spec ID or is sanctioned scope.**
- `vision.md` and `priorities.md` — **L1-authored VIEWS of the confirmed intent-spec**, written at project creation, **immutable** (`WORKSPACE-SCHEMA.md` §130–134). `vision.md` renders what is being built / for whom / what success looks like; `priorities.md` renders the opinionated-vs-delegated triage and the priority overrides that flow through the project.

L2 reads `vision.md` + `priorities.md` (`operational/L2/spawn-template.md`) — the **distilled views** — and pulls the canonical `intent-spec.md` on demand (pointer-not-payload). The relationship is strict: the **intent-spec is canonical**; the two views never override it, and after freeze the spec changes only via an explicit intent-revision record. This is the brief side of the arc; promotion (§3) is the delivery side.

---

## 3. Delivery — promotion is a control-plane cross-jail write

**Promotion is performed by `harnessd`, not by any agent, and it is gated on L1's accept signal.**

Why it cannot be a jailed-agent write: every agent — L1 included — is **write-jailed to its own node subtree under `/runtime/`** (`SECURITY.md` §1.3; the seatbelt profile is a global `(deny file-write*)` then an allow-list scoped to the node's `WORKROOT`). The **delivery destination is outside every node's write-jail** — it is a user-path or a git remote, deliberately *not* under any node subtree. So crossing that boundary is **structurally impossible for a jailed agent**; it is a **control-plane operation**, performed by the daemon, which is in the trusted control plane (`SECURITY.md` §1.1) and is not itself write-jailed. This is the **one** sanctioned cross-jail write in the system, and it exists precisely because the write-jail invariant must hold for every agent.

The operation is **gated on L1's final-accept signal** (Stage 5). The deliverable binding block tracks the surface it needs (`DAEMON.md` §3.2 / `IMPLEMENTATION-PLAN.md` §3.4): `deliverable_state` (`planned|active|waiting|completed|blocked|cancelled|delivered|delivery-failed`), `stop_condition`, `write_targets` (the **in-jail source surface**), `evidence_refs`, `acceptance_ref`, and the dedicated **`delivery_destination` + `delivery_kind`** — the out-of-jail promotion target (mirroring intent-spec §8), kept **distinct from `write_targets`** so the jail boundary stays legible. The promote-out sets `deliverable_state=delivered` (or `delivery-failed` on a failed promote, plus the §6.3 escalation row) and writes the target into `delivery_destination`. **The promote op is BUILT** (`harnessd/promote.py`, Increment 17). Its trigger is **`harnessctl promote <project-node-address> --decision accept`** — issued by L1 at Stage-5 final-accept (or by the operator), serialized to the resident daemon's IPC `promote` verb; the **daemon** performs the cross-jail copy/push and stamps the binding via `executor.deliver` (the single writer). The source surface is the node's **`nodes/<path>/` workspace** (`addressing.node_dir` — the one canonical address→workspace mapping every agent writes); §4's `/runtime/proj/{project}/` phrasing refers to the **logical** path, physically rooted at `<RUNTIME_ROOT>/nodes/`. The control-plane dotfiles inside the workspace (`.sign-off.*` / `.signal.*` / `.inbox.*`) are harness machinery and are excluded from the promoted tree.

---

## 4. `/runtime/` vs `proj/` — the logical tree and its throwaway root

The logical `proj/{project}/…` tree (the one-spine workspace paths, `WORKSPACE-SCHEMA.md`) is rooted, **at runtime**, at the **gitignored throwaway `/runtime/`**: per-build project trees live under `/runtime/proj/{project}/` (`WORKSPACE-SCHEMA.md` §138–142; `IMPLEMENTATION-PLAN.md` — code in `harnessd/` is tracked, `/runtime/` is gitignored). Genesis spawns L1 at the L1-root; **projects are nodes below it**, so the project node L1 creates in Stage 2 sits inside L1's own subtree. Everything an agent produces — the whole project node and its deliverable — is written **inside `/runtime/`** and write-jailed there. A finished deliverable **does not stay in `/runtime/`**: promotion (§3) is what moves it out to the captured destination. The teardown/reclaim of the spent `/runtime/` tree afterward is deferred (D7).

---

## 5. Invariants Preserved

- **Write-jail.** Every agent is confined to its own `/runtime/` node subtree. **Promotion is the one control-plane cross-jail write**, gated on L1 accept, performed by `harnessd` — **never an agent write** (`SECURITY.md` §1.3).
- **OAuth-only.** All spawns boot on the OAuth subscription token; no API-key path (`SECURITY.md`, `DAEMON.md` §6).
- **The intent-spec is the frozen anchor.** Frozen at reflect-back confirmation, guarded by L1 for the project's life, and the single thing final-accept (Stage 5) judges against (`operational/shared/intent-spec-contract.md`).
- **Pointer-not-payload.** Every brief points at `client-brief/` (and upstream intent), read in place — never copied (`WORKSPACE-SCHEMA.md`, `operational/L2/spawn-template.md`).

---

*Created: 2026-06-05 — canonical intake→delivery arc spec. Connects the intake/grilling session, the intent-spec contract (+ new delivery-destination field), the spawn chokepoint, the deliverable binding block, and the write-jail; names control-plane promotion as the v1-new mechanism (IMPL-PLAN increment 17+). Closes register V3. Referenced by `WORKSPACE-SCHEMA.md` §138–142.*
