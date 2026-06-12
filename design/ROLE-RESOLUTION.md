# Role Resolution — How a Role Is Resolved at Boot

The canonical spec for **how a spawned agent becomes who it is** at boot. It reconciles the H40
boot model (resolved 2026-06-05) with the write-jail (SECURITY §1.4) and the spawn chokepoint
(DAEMON §6): the system prompt is one shared minimal constant; the **role arrives as documents the
agent reads in place** under the read-allow graph. No per-level system prompt, no inline-flatten.

Authoritative sources, do not contradict: `operational/shared/agent-definition-principles.md` §4
(the reframe), `operational/shared/system-prompt.md` (the promoted shared prompt),
`working-notes/DEFERRED-REGISTER.md` Decision A (write-jail) + Decision B (this reframe),
`DAEMON.md` §6 (spawn chokepoint) + §3.2 (binding schema), `SECURITY.md` §1.4 (the read graph).

> **Supersedes** the old "`--system-prompt-file` = per-level `role.md`" model wherever it still
> appears (DAEMON §6.2 line 930, §3.2 `role_file`, SECURITY §1.4 / §356 / §504, IMPLEMENTATION-PLAN
> adapter + tests). Those bake `role.md` into the prompt; this doc is what they reconcile *to*.
> Reconcile, don't redesign — no new mechanism is introduced beyond what §4 + Decision B fixed.

---

## 1. The split — shared minimal prompt (constant) vs role-as-delivered-documents

H40 asked: the Claude Code base prompt frames the model as a deferential *coding assistant*, which
fights every non-coding seat (L1 Orchestrator, L2 Architect, a reviewer). **Resolved: don't fight
the base framing — replace it, and deliver the role separately.** Two distinct pieces, never folded
into one:

- **THE SYSTEM PROMPT (constant, shared).** `--system-prompt-file` is **always**
  `operational/shared/system-prompt.md` — the ONE shared minimal prompt, byte-identical for L1–L5.
  It exists now (promoted 2026-06-05). It is **not** a per-level file and **not** `role.md`. It
  *replaces* Claude Code's base coding-assistant block (base block 2), keeps the 57-char identity
  line and the default 24-tool set, and stays OAuth/interactive-safe. Its opening line points the
  agent at its own node: *"your role, scope, and current task are delivered as documents in your
  workspace — read those first."* The SWE-craft framing is gone at the source, so role docs no
  longer have to *compensate* for an assistant default fighting them.
- **THE ROLE (delivered as documents the agent READS at boot).** Who the agent is and what it is
  doing are **files it reads in place** — never strings baked into the prompt, never flattened into
  a bundle. Two regions:
  - **Node-local:** the instantiated spawn brief (the filled `spawn-template`, written into the
    node) carries identity (address, level, role-variant) **and** its load-manifest (the
    "Identity — Load These Documents" list), plus the frozen read-only `acceptance.md`. The brief is
    the per-spawn delivery vehicle; it lives in the node.
  - **Read-allowed harness docs:** the per-level `operational/L{n}/{soul,role,config}.md` and the
    always-loaded `operational/shared/*` contract docs, read **in place at their harness-root
    paths** — not copied, not inlined.

**Why the split (three reasons, all load-bearing):**

1. **Token-saving + no-out-of-role-pull** — the shared prompt is deliberately bare so it carries no
   SWE/coding-assistant framing to pull a non-coding seat out of role, and the same file serves
   every level (no reason to fork it).
2. **Write-jail, not read-jail, makes refs resolve without flatten** — Decision A confines *writes*
   to the node but leaves *reads* open across the read-allow graph (§3). So a role doc's references
   to `design/…` and sibling `operational/…` files resolve **read-only against the harness docs in
   place**. There is no need to inline-flatten the bundle into the prompt — the precise reason the
   audit's "compose all role docs into one `--system-prompt-file`" framing was superseded
   (Decision B). H40 also confirmed role-content *outside* the system prompt bites hard.

This applies to **Claude (Opus) seats**, which have a base prompt to replace. **GPT-5.5 seats** run
under Codex with no Claude base prompt; their literalness concern is handled in the brief
(`runtime-and-model-map.md`). The role-as-documents half applies to **both** — a Codex L5 also reads
its role + brief from its node.

---

## 2. The per-seat LOAD-MANIFEST

What each seat reads at boot. The manifest lives in the brief's "Identity — Load These Documents"
list; the chokepoint assembles it from the binding's `role_variant` (§4). Three tiers:

| Tier | Documents | Loaded |
|---|---|---|
| **Shared — always** | `operational/shared/system-prompt.md` *(this is the **prompt**, not a read-doc)* | every level, as `--system-prompt-file` |
| | `operational/shared/comms-protocol.md`, `agent-lifecycle.md`, `runtime-and-model-map.md` | every level — each header says "loaded at boot for all levels" |
| | `operational/shared/agent-definition-principles.md` | definition-authoring levels (L1–L4) — its header scopes itself; **L5 omits it** |
| | `operational/shared/git-protocol.md` | levels that produce code (L4, L5, sometimes L3) — its header scopes itself |
| **Per-level** | `operational/L{n}/soul.md` (one-line pointer), `role.md` (boundaries/outputs), `config.md` (self-monitoring) | the agent's own level |
| | **L1 extras:** `handbook.md`, `intake-session-template.md` | L1 |
| | **L3 extra:** `planning-template.md` | L3 (planning seat) |
| | **L5 extra:** `swe-handbook.md` | L5 |
| **Node-local** | the filled spawn brief (identity + this manifest + resolved decisions) | per-spawn, written into the node |
| | frozen read-only `acceptance.md` (the rubric, authored before the work) | per-spawn, at the node |
| | per-project `conventions.md` / `README.md` / append-only `log.md` (read-only reference) | per-project, per F34 read scope |

**Seat-variants select different manifests.** The `role_variant` field (`#exec`, `#review`,
`#test`, e.g. `L5#exec` vs `L5+#review`) selects **which** per-level docs + bundle the chokepoint
assembles into the brief. An `L5#exec` reads the L5 executor bundle; an `L5+#review` reviewer (a
separate Opus seat) reads the reviewer manifest against the *same* frozen `acceptance.md`. Same
shared prompt for all of them; different read-set.

The manifest is **authored** in each level's `spawn-template.md` "Identity — Load These Documents" /
"Read before anything else" sections — those lists ARE the per-seat manifest (e.g. L5's lists
`soul/role/config/swe-handbook` + brief + frozen `acceptance.md`). This doc is the canonical index;
the templates are the per-seat instances.

---

## 3. Reference resolution — read-in-place against the harness root

> **AMENDED 2026-06-12 (user ruling, LR-4 cure — identity auto-load):** the per-level IDENTITY
> TRIO (`soul.md`/`role.md`/`config.md`, `brief.identity_docs`) no longer rides on agent
> diligence. The Claude-Code adapter FLATTENS it (shared prompt first, provenance headers per
> doc) into a per-spawn composed system prompt (`<workspace>/.identity-prompt.md`) that argv
> points at; the Codex adapter lists the trio as explicit first-reads in its boot prompt (its
> native system message stays — user decision). Evidence: run-1's L1 booted without its
> identity (LR-4); doc-presence alone proved insufficient against completion bias in run-2.
> Everything below — the manifest, read-in-place, no-flatten — REMAINS TRUE for the shared
> protocol docs and all cross-refs: they are a reference library the agent reads and re-reads
> in place; only the identity trio is delivered in-context at boot.

Every manifest doc and every cross-ref inside it (`design/…`, `operational/…`) is a path **relative
to the harness root**, which the node reads in place. The mechanics:

- **Read-allow, write-jail.** The node can **READ** the harness root (role docs, shared contract
  docs, referenced `design/*.md`) but cannot **WRITE** outside its own subtree. This is exactly the
  read-allow graph SECURITY §1.4 enumerates: own subtree + same-level siblings' published surface +
  parent + the role/shared/design docs + the shared system prompt. Reads resolve; writes are jailed.
- **No flatten.** Because reads stay open, a role doc that references `WORKSPACE-SCHEMA.md` or an ADR
  pulls it on demand from its harness-root path. Nothing is inlined into the prompt or copied into
  the node. (This is the write-jail-not-read-jail payoff from Decision A/B — refs resolve without
  flattening.)
- **The chokepoint makes the root resolvable.** The spawn chokepoint (DAEMON §6) launches the actor
  with the harness root reachable from the node's working directory, so the relative paths in the
  manifest and its cross-refs land on real files under the read-allow graph.
- **The shared prompt path is itself read-allowed.** `operational/shared/system-prompt.md` must be
  readable at boot — the Claude Code process reads it to honor `--system-prompt-file`. SECURITY §1.4
  lists "the shared system prompt" in the read-allow set for this reason.

See `SECURITY.md` §1.4 for the authoritative read-allow / write-deny enumeration and §2.3 for the
seatbelt profile that enforces it. This doc does not duplicate the profile; it specifies what the
profile must leave readable for role resolution to work.

---

## 4. Wiring — how this rides the spawn chokepoint

This resolution rides the single spawn chokepoint; it does not add a code path. At spawn (DAEMON
§6.1 **STEP 2**) the adapter reads the level config and **assembles the runtime-neutral brief +
load-manifest** from the binding's `role_variant`. The Claude-Code adapter (§6.2) then passes
`--system-prompt-file` = the shared prompt — **not** the per-level role doc — and boots the pinned
binary with the isolation env. The role docs named in the manifest are read in place by the agent
(§3). The binding (DAEMON §3.2) splits the old single field accordingly:

- `role_file: "L5/role.md"` (the old "`--system-prompt-file` passed at spawn") is **SPLIT** into:
  - **`system_prompt_file: "operational/shared/system-prompt.md"`** — constant; what the chokepoint
    passes as `--system-prompt-file`. Identical for every binding (may be a runtime-global rather
    than a per-row field, but at minimum it is **no longer the per-level role path**).
  - **`role_variant: "L5#exec"`** (or `"L4"`, `"L5+#review"`, `"L3#plan"`, …) — per-binding; selects
    **which** load-manifest + per-level role docs the chokepoint assembles into the brief. This is
    the field that varies by seat.

Genesis (§7) boots L1 the same way; resume (§6.4) re-assembles the manifest into a delta brief. See
DAEMON for the chokepoint mechanics — this doc points at it, it is not duplicated here.

---

## 5. Invariants preserved (do not weaken)

This reframe changes *what* `--system-prompt-file` points at and splits one binding field. It changes
**nothing** below; all of these remain true after it:

- **OAuth-only.** Never `--bare` (reads auth strictly from `ANTHROPIC_API_KEY`, breaks an OAuth
  subscription token), never `ANTHROPIC_API_KEY` / `OPENAI_API_KEY`. `--bare` stays forbidden.
- **Never `--append-system-prompt`** (keeps the SWE block) / **never `--agents`** (does not inject
  persona). The shared prompt *replaces* base block 2 via `--system-prompt-file`; nothing is appended.
- **Write-jail.** Writes confined to the node subtree + the per-session `CLAUDE_CODE_TMPDIR`,
  redirected tool-caches, and `CLAUDE_CONFIG_DIR`. Harness code, the ledger, secrets, and `~` are
  unreachable-for-write (SECURITY §1.3 / §2.3, Decision A).
- **Read-allow graph (F34).** Own subtree + siblings' published surface + parent + the
  role/shared/design docs + the shared system prompt. The role docs are now **READ-documents** read
  in place — not "the `--system-prompt-file` role doc." This is what makes refs resolve without
  flatten (§3).
- **Gate firewall on resume.** Never `--resume` a session across a quality-gate boundary
  (DAEMON §6.4, LOCKED) — unaffected by this reframe; left intact.

---

*Created: 2026-06-05. Sources: agent-definition-principles §4 (H40 resolved); DEFERRED-REGISTER Decisions A + B; DAEMON §6 + §3.2; SECURITY §1.4; system-prompt.md (promoted 2026-06-05).*
