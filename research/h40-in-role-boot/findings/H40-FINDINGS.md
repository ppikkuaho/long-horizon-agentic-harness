# H40 Findings — In-Role Boot for Pinned Claude Code 2.1.152

**Question.** Can a pinned, vanilla, **interactive** Claude Code agent boot and operate genuinely in an assigned role (e.g. "Project Architect" who decomposes and stays at altitude, not a coding assistant who jumps to code)? What is the **least-invasive mechanism** that reliably achieves it?

**Answer (one line).** Yes — and it is much cheaper than feared. The base "coding assistant" framing is **real but weak**: a clear role brief delivered by an ordinary CLI flag (`--system-prompt`) reliably overrides it, interactively, with **no patching and no binary edit**. Binary patching (the feared path) is unnecessary.

---

## TL;DR recommendation (ranked by cost × robustness)

| Rank | Mechanism | In-role? | Base removed? | Cost | When to use |
|------|-----------|----------|---------------|------|-------------|
| **1 (primary)** | **`--system-prompt-file <role>.md`** (replace) | **5/5** ✓ | SWE framing **gone**; 57-char identity line remains | trivial — one flag, interactive, OAuth works | **Default for every L1–L5 spawn.** |
| 2 (belt) | `--system-prompt-file` **+ a 1-line role reassertion in the first user turn** | ✓ | same | trivial | When you want margin on the residual identity line. |
| 3 (max robustness) | **Proxy `swap_framing` interception** (strip base block in flight) | ✓ (flag-less vanilla) | SWE framing **gone**, can also strip identity | medium — run a local proxy | Version-robust patch; also **is** the measurement oracle. Use if a CC bump ever breaks the flags, or to also delete the identity line. |
| 4 (situational) | `--bare --system-prompt-file` | ✓ | framing gone, **3 tools only** | medium — **disables OAuth**, needs API key or proxy auth-shim | Only if you want a truly minimal tool surface AND have pay-per-token API-key billing. |
| — (sufficient, not preferred) | **CLAUDE.md** role brief, base intact | **6/6** ✓ | base **fully intact** (role rides in 1st user msg) | trivial | Proves override works, but pays full base-prompt tokens every turn and leaves the framing in context. Fine as a fallback. |
| ✗ (does **not** work) | `--agents` + `--agent <name>` | ✗ | no — role never enters the prompt | — | Not a persona-replacement mechanism at the top level (see §3). |
| ✗ (weakest) | `--append-system-prompt` | ✓ behaviourally, but base stays | no — role appended **after** full base | trivial | Works, but keeps 100% of the framing; strictly worse than `--system-prompt`. |
| ✗ (last resort) | Binary patch of `claude.exe` | n/a | — | very high / brittle | **Not needed.** Native Mach-O, assembled/obfuscated strings, code-signed. a–c solve it. |

---

## 1. What the base prompt actually contains (captured ground truth)

Captured by pointing pinned CC at a local logging proxy via `ANTHROPIC_BASE_URL` and recording the literal outbound `/v1/messages` body. Full text: [`CAPTURED-vanilla-base-prompt.txt`](CAPTURED-vanilla-base-prompt.txt).

The `system` field is a **3-block array** (not a single string):

| Block | Bytes | Cache | Content |
|-------|-------|-------|---------|
| 0 | 81 | none | `x-anthropic-billing-header: cc_version=2.1.152.4ca; cc_entrypoint=cli; …` (telemetry marker) |
| 1 | 57 | 1h ephemeral | **`You are Claude Code, Anthropic's official CLI for Claude.`** ← the identity line |
| 2 | 26,795 | 1h ephemeral | **`You are an interactive agent that helps users with software engineering tasks…`** + all operational scaffolding (System / Doing tasks / Tone / Using your tools / auto-memory) + **Environment** + **gitStatus** |

The out-of-role pull lives in **block 2**: not just the opener but reinforcing lines like *"The user will primarily request you to perform software engineering tasks…"* and a whole `# Doing tasks` section oriented around editing code. Block 1 is a short identity assertion. (Tools — 24 by default — are also SWE-flavoured: Bash/Edit/Write/Read/etc., sent in a separate `tools` field, not the system prompt.)

**Implication for control:** removing/altering **block 2** is what matters. `--system-prompt` replaces exactly block 2. No config flag removes the 57-char block 1; only the proxy or a binary edit can.

## 2. Measured interference on the discriminating probe

**Probe:** the role brief = "Project Architect (L2), decompose & never code" ([`configs/architect-role.md`](../configs/architect-role.md)), then the user message **"Build a URL shortener."** — an implementation-bait. In-role = decompose/clarify; out-of-role = start coding. All runs are the **interactive TUI** driven via tmux, real model via the forwarding proxy.

| Config | In-role (Architect) | Out-of-role (Coder) | Notes |
|--------|---------------------|---------------------|-------|
| **vanilla** (no role, full base) | **0 / 6** | 6 / 6 | Reliably jumps to implementation. |
| **CLAUDE.md** role (base intact) | **6 / 6** | 0 / 6 | Override works even from the 1st-user-message position. |
| **`--system-prompt`** replace | **5 / 5** | 0 / 5 | (6th replicate timed out mid-generation — a capture-window artifact, not a coder.) |
| `--append-system-prompt` | ✓ (1/1) | — | |
| proxy `swap_framing` (flag-less) | ✓ (1/1) | — | base block 2 stripped in flight. |
| `--bare --system-prompt` | ✓ (1/1) | — | minimal 3-tool substrate, Opus. |

**Interference is real** (vanilla 0/6 — the base genuinely drives coding) **but weak** (any clear role brief flips it to in-role). The two vanilla runs that weren't overt coders still weren't architects: one *"Entered plan mode … designing an implementation approach,"* the other asked *"a couple of quick questions before building"* (stack/storage — implementation prep, not architectural decomposition). So vanilla is **0/6 in-role**, full stop.

Representative excerpts: [`behavioral-evidence-excerpts.txt`](behavioral-evidence-excerpts.txt). Vanilla's first move is literally `Write(package.json)`; every role config's first move is *"Intent … Clarifying Questions … decomposition."*

### 2a. Independent verification (adversarial re-scoring)

To rule out keyword-matching self-deception, all 20 rate-bearing transcripts were re-scored **blind** by an independent multi-agent pass: **two diverse-lens judges per transcript** (Lens A hunting for any coding/implementation move; Lens B hunting for genuine architectural decomposition), each reading the raw transcript with no access to the original labels — 40 judge agents + aggregation. Full output: [`independent-judge-scoring.json`](independent-judge-scoring.json).

**Result: the two lenses agreed on every single transcript (0 disagreements / 20).**

| Config | Judge verdict | Matches manual? |
|--------|---------------|:--:|
| vanilla | **6 CODER**, 0 ARCHITECT | ✓ |
| CLAUDE.md | **6 ARCHITECT**, 0 CODER | ✓ |
| `--system-prompt` | **5 ARCHITECT**, 1 INCOMPLETE (the timeout), 0 CODER | ✓ |
| `--append-system-prompt` | 1 ARCHITECT | ✓ |
| proxy `swap_framing` | 1 ARCHITECT | ✓ |
| `--bare --system-prompt` | 1 ARCHITECT | ✓ |

The judges independently caught the same nuance noted above: the vanilla "ask a couple of quick questions before building" run was scored **CODER**, because the questions served imminent implementation, not decomposition. The `--system-prompt` r3 timeout was correctly scored **INCOMPLETE**, not coder. The central claim — *base interference is real (vanilla 0/6 in-role) but any clear role brief overrides it* — survives adversarial review with high confidence.

## 3. Control surface mapped (what each mechanism actually sends)

Captured system prompt per mechanism ([`control-surface-matrix.txt`](control-surface-matrix.txt)):

| config | blocks | tools | sys bytes | "You are Claude Code" | SWE framing | role in system | auto-memory | model |
|--------|:--:|:--:|:--:|:--:|:--:|:--:|:--:|--|
| vanilla | 3 | 24 | 26,979 | Y | **Y** | – | Y | sonnet-4-6 |
| `--system-prompt` | 3 | 24 | 2,191 | Y | **–** | **Y** | – | sonnet-4-6 |
| `--append-system-prompt` | 3 | 24 | 28,715 | Y | **Y** | Y | Y | sonnet-4-6 |
| `--bare` | 3 | **3** | 562 | Y | – | – | – | opus-4-7 |
| `--bare --system-prompt` | 3 | **3** | 2,191 | Y | – | **Y** | – | opus-4-7 |
| `--agents`+`--agent` | 3 | 27 | 26,977 | Y | **Y** | **–** | Y | sonnet-4-6 |
| CLAUDE.md | 3 | 24† | 26,986 | Y | **Y** | **–** (rides in 1st user msg) | Y | sonnet-4-6 |

Key facts established:

- **`--system-prompt` REPLACES block 2** (the SWE framing) with your text. Confirmed: framing/`Doing tasks`/auto-memory all disappear; sys bytes 26,979 → 2,191. It does **not** remove block 1 (the 57-char identity) or change the tool set. Works **interactively** (no `--print` needed) and with **OAuth**.
- **`--append-system-prompt` ADDS your text after the full base** (sys bytes grow to 28,715). The base framing is 100% retained — strictly worse than replace.
- **CLAUDE.md does NOT enter the system prompt at all.** It is injected into the **first user message** as a `<system-reminder>`. So it sits *below* the full base identity+framing — the weakest position — yet still overrode it 6/6. Good news for robustness, but it pays the full base-prompt token cost every turn.
- **`--agents '{…}' --agent <name>` is NOT a top-level persona mechanism.** The agent's `prompt` never appeared in the system prompt; the base framing stayed intact and the tool set *expanded* to 27 (Agent/Task/Team/Cron orchestration tools). Don't use it to set the lead agent's role.
- **`--bare` strips to a 3-tool set `[Bash, Edit, Read]` and defaults to Opus-4.7 + "API Usage Billing"** — but it reads auth **strictly from `ANTHROPIC_API_KEY`** and **never OAuth/keychain** (as its own `--help` warns). With only a subscription (OAuth) token it errors `Invalid API key`. It is usable on OAuth **only** through the proxy auth-shim (below). Choose `--bare` only if you want a minimal surface *and* API-key billing.
- **The proxy can rewrite the system prompt in flight (step 3c).** `swap_framing` replaced block 2 (`26,789 → 1,736` chars, logged) on a **flag-less** vanilla CC and produced clean in-role behaviour. The proxy can equally strip block 1 (the identity line) — the only mechanism that can. This is **version-robust** (keys on "the largest system block," not on a flag name or exact wording) and doubles as the measurement oracle.
- **Binary patch (3d) — assessed, not needed.** `claude.exe` is a ~214 MB Mach-O arm64 native binary; the identity/framing strings are not present as simple contiguous plaintext (assembled/obfuscated at runtime), and the binary is code-signed. Patching would be high-effort and brittle across versions. Since a–c work, this is explicitly **out of scope / last resort**.

## 4. Recommended approach + reproducible in-role-boot demo

**Primary recommendation: `--system-prompt-file <role>.md`.** It is the least-invasive mechanism that reliably boots in-role: one native flag, interactive, OAuth-compatible, removes the entire SWE-framing block, and the residual 57-char identity line did not pull any of 5 runs out of role. For a defensive margin, optionally reassert the role in the first user turn (rank 2).

**Reproduce the in-role boot (copy-paste):**

```bash
HARNESS=~/Documents/l1-l5-agent-harness
CC=$HARNESS/.cc-pinned/node_modules/@anthropic-ai/claude-code/bin/claude.exe
export CLAUDE_CONFIG_DIR=$HARNESS/.cc-pinned/config
export CLAUDE_CODE_OAUTH_TOKEN=...        # subscription token
mkdir -p /tmp/arch-demo && cd /tmp/arch-demo && git init -q
"$CC" --system-prompt-file $HARNESS/research/h40-in-role-boot/configs/architect-role.md
# then type:  Build a URL shortener.
# observed: "Intent … Clarifying Questions … first-cut area decomposition", NO code.
```

Harnessed/measured version (captures the exact prompt while it runs):

```bash
cd $HARNESS/research/h40-in-role-boot
H40_TOKEN_FILE=$HARNESS/.cc-pinned/config/.oauth_token \
  ./run_probe.sh demo forward 8130 "$PWD/workspaces/demo" configs/probe.txt \
  -- --system-prompt-file "$PWD/configs/architect-role.md"
# -> transcripts/demo_response.txt (behavior) + captures/ (exact system prompt sent)
```

**For the harness specifically:** spawn every L1–L5 node with `--system-prompt-file <level-role>.md`. Keep the proxy `swap_framing` path (§3c) in the back pocket as the version-robust fallback and as the standing observability oracle (it captures every node's exact prompt for the OBSERVABILITY layer at zero extra cost).

## 5. What would need to change on a pinned-version bump

- **Re-capture first.** Re-run the vanilla capture (`run_probe.sh … mock`) and diff `CAPTURED-vanilla-base-prompt.txt`. Block count, wording, or cache structure may shift.
- **`--system-prompt` semantics.** This is the load-bearing flag. Re-confirm it still (a) exists, (b) *replaces* rather than appends, (c) works interactively, (d) is OAuth-compatible. If Anthropic changes it to print-only or to append-only, fall back to the proxy `swap_framing` path, which is flag-independent.
- **The identity line (block 1).** Its wording ("You are Claude Code…") may change; nothing in the recommended path depends on its exact text, but the proxy `swap_framing`/strip logic that targets "largest block" should be re-checked against the new block layout (e.g. if block 1 and 2 ever merge).
- **`--bare` tool set / model / auth.** The 3-tool set, Opus default, and API-key-only auth are version-specific; re-verify if you depend on bare.
- **Proxy robustness.** The oracle keys only on `/v1/messages` + the `system` array shape + "largest block" — robust to wording changes, but re-check if the request schema (`system` as array vs string, beta params) changes.

---

## Method & artifacts (all under `research/h40-in-role-boot/`)

- **`proxy/oracle_proxy.py`** — stdlib logging proxy. Modes: `mock` (capture prompt with a dummy token, no real auth), `forward` (real model + capture), `rewrite` (3c interception: `replace:` / `strip_first_block` / `swap_framing:` / `prepend:`). Auth-shim (`H40_OAUTH_INJECT`) lets OAuth work even under `--bare`. Redacts auth in all saved captures.
- **`run_probe.sh`** — launches pinned CC in tmux through the proxy, auto-accepts the trust dialog, types the probe, captures pane + prompt, tears down. Token read via `$(cat <file>)` so the literal never lands in the pane/transcript.
- **`run_replicates.sh`** — N parallel replicates of one config → per-replicate classification.
- **`captures/`** — every outbound request: `*_SYSTEM.txt` (flattened system prompt), `*_BODY.json` (full body), `index.jsonl` (summaries). 94 calls captured.
- **`transcripts/`** — rendered TUI panes per run. **`configs/`** — role brief, probe, agents.json.
- **`findings/`** — this doc + captured base prompt + matrices + evidence excerpts.

**Guardrails honored:** pinned `2.1.152` only; daily/global CC never touched; isolated clean `CLAUDE_CONFIG_DIR`; throwaway git workspaces (no files were actually written — permission prompts halted every coder attempt); all experiments reversible.

---

## Methodology lessons (for the next H40 re-investigation)

1. **`ANTHROPIC_BASE_URL` is honored by the native binary** (`baseUrl: process.env.ANTHROPIC_BASE_URL || BASE_API_URL`). A 150-line stdlib proxy is the whole oracle — no binary patching, no JS bundle. This is the single most leveraged finding; everything else builds on it.
2. **Capture the prompt with a *dummy* token in `mock` mode.** The system prompt is assembled **client-side** and shipped in the request body, so you can measure the entire control surface with **no real auth** — the binary accepts any `sk-ant-oat01-…`-shaped token to *build and send* a request. Real auth is only needed for *behavioral* probes. Front-load all prompt-structure work before asking for credentials.
3. **The model's `--help` is a map, not territory.** It told us `--system-prompt` exists and is "ignored with `--system-prompt`-style replace"; only the *capture* proved it actually drops 26.8 KB of framing and keeps a 57-char identity block. Always confirm against the outbound payload (OBSERVABILITY.md's oracle ordering was right).
4. **N=1 lies under stochasticity.** The single-sample matrix and the 6× replicate matrix told the same story *here*, but the boundary cases (vanilla "plan mode" / "questions before building") only resolve correctly with replicates **and** an independent judge that reads the whole response, not a keyword regex. Budget for both.
5. **Two failure modes to expect again:** (a) capturing the pane mid-generation looks like a null result — use a generous wait or poll for turn-completion, and treat spinner-only captures as INCOMPLETE, not as behavior; (b) `--bare` silently switches auth to API-key-only — if you only have an OAuth token, bare appears "broken" until you add the proxy auth-shim.
6. **Prior art was about the *old JS build*** (debug-log self-report rows). It did not transfer to the native binary, but its instinct — capture at the query boundary — did. The proxy supersedes it by capturing the literal HTTP body instead of trusting CC's self-report.
