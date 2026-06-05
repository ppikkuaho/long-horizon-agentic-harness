# H40 — In-Role Boot: Research Task

> **STATUS: RESOLVED (2026-06-05).** Ran by Claude + Codex in parallel (adversarial cross-check). Findings: `research/h40-in-role-boot/findings/H40-FINDINGS.md` (Claude — behavioral + 40-judge adversarial verification) and `~/Documents/codex/2026-06-04/read-documents-l1-l5-agent-harness/outputs/H40-in-role-boot-findings.md` (Codex — capture-only).
>
> **Conclusion: no binary patch needed.** The base "coding assistant" framing is real but weak — vanilla CC is 0/6 in-role; a role brief flips it to 5–6/6. **Boot every L1–L5 node with `--system-prompt-file <level-role>.md`** (the existing `operational/L*/role.md` docs *are* those files): it replaces the ~26.8 KB SWE-framing system block, keeps the tools, works interactively + on OAuth, and leaves only a harmless 57-char identity line. Confirmed by BOTH runs; Claude additionally verified behaviorally and by a blind adversarial re-scoring (0/20 judge disagreements).
> - **Fallback + observability gift:** the measurement oracle (a stdlib proxy via `ANTHROPIC_BASE_URL`, honored by the native binary) doubles as the OBSERVABILITY outbound-payload oracle AND a version-robust `swap_framing` interception that strips the base block in-flight (flag-independent; can even remove the identity line).
> - **Do NOT use `--agents/--agent`.** Codex preferred it (for the `@architect` TUI label) but Claude's capture + behavior found the role never enters the prompt and the tool set expands to 27. Contested — avoid until resolved.
> - **Version-bump caveat:** on any pinned-CC bump, re-capture the base prompt and re-confirm `--system-prompt-file` still *replaces* (not appends).
>
> Folds into cluster ① (spawn mechanism) and OBSERVABILITY (the oracle). Original research brief retained below for provenance.

> Hand this to a fresh research session. It is self-contained.

## Goal
Find how to make a pinned, vanilla, **interactive** Claude Code agent boot and operate genuinely **in its assigned role** — e.g. a "Project Architect" who decomposes and stays at altitude, NOT a "coding assistant" who jumps to writing code — and recommend the **least-invasive mechanism** that reliably achieves it.

This is the L1-L5 agent harness's highest-risk unknown ("H40"). The whole architecture depends on agents operating in clean, specialized roles. If Claude Code's built-in identity dominates, role-specialization fails.

## The problem
Claude Code injects its own base system prompt ("You are Claude Code… an interactive agent that helps with software engineering tasks") plus scaffolding (tool instructions, environment, git status, CLAUDE.md, etc.). We need a role identity (Architect / Designer / Coordinator / Executor) to **replace or reliably dominate** that base so behavior matches the role.

## Hard constraints
- **Pinned vanilla Claude Code `2.1.152`**, interactive TUI, driven via **tmux**. **No headless (`claude -p`), no Agent SDK.** Solutions must work with the interactive CLI.
- Use the isolated pinned install ONLY: `~/Documents/l1-l5-agent-harness/.cc-pinned/` (launch via `.cc-pinned/claude-pinned.sh`, which sets a clean `CLAUDE_CONFIG_DIR`). **Do NOT touch the daily/global CC.**
- Experiments reversible + isolated (clean config dir, throwaway workspaces).
- **It is a NATIVE binary now** (`bin/claude.exe`, Mach-O arm64, ~214 MB) — NOT the old JS bundle. The prior JS-patching approach almost certainly does **not** transfer. Treat binary patching as a last resort.

## What "solved" looks like
A pinned CC session that, given a role brief, **demonstrably behaves in-role on a discriminating probe** — e.g. an "Architect" told "build a URL shortener" responds by decomposing/clarifying, not by immediately coding — reproducibly, via a mechanism we control at spawn. Plus a recommendation ranked by cost/robustness.

## Method — measure first, then escalate cost
1. **Build the measurement oracle FIRST.** Capture *exactly what the model receives* (the assembled system prompt + context CC actually sends). Cleanest path: point the pinned CC at a **local logging proxy via `ANTHROPIC_BASE_URL`** (forwarding with the OAuth token) and record the outbound request's `system` blocks. Without this you're guessing; with it, every experiment is measurable. (Life-OS prior art `prompt_assembly_*.py` / `rule_origin_report.py` attempted prompt capture — mine for technique, treat as SUSPECT.)
2. **Characterize the interference.** With only a plain role brief (CLAUDE.md / first message), does the base prompt actually cause out-of-role behavior, and how strongly? Maybe override is enough and suppression isn't needed — **don't assume patching is required.**
3. **Map the control surface, cheapest-first:**
   - **a. Config/flag (no patching):** does the interactive CLI in 2.1.152 expose `--append-system-prompt` / `--system-prompt`? Investigate **output styles**, custom **agents/subagents** definitions, `settings.json`, CLAUDE.md placement, and the `CLAUDE_CODE_*` env vars (see `PINNED-CC.md`). Can a config make the role dominate?
   - **b. Prompt-dominance (no patching):** if the base can't be removed, can a strong enough role injection (CLAUDE.md + append-system-prompt + a disciplined first turn) reliably override it? Measure on the discriminating probe.
   - **c. Interception (no binary edit):** can the proxy from step 1 **rewrite the system prompt in flight** — strip/replace the base block before it reaches the API? A clean, version-robust "patch" that never touches the binary. **This is the most promising path; test it seriously.**
   - **d. Binary patch (last resort):** only if a–c fail. Assess feasibility on the native Mach-O binary; expect high cost / brittleness.
4. **Recommend** the least-invasive mechanism that reliably boots in-role, with evidence (captured prompts + behavior on the probe).

## Resources
- Pinned install + isolation + env vars: `~/Documents/l1-l5-agent-harness/PINNED-CC.md`, `.cc-pinned/claude-pinned.sh`.
- SUSPECT prior art (study findings, do NOT reuse code): `~/Documents/Life-os/dev/patches/claude-code/` — `prompt_assembly_*.py`, `rule_origin_report.py`, `claude_session_manager.py`, `recursive_subagent_runtime.py`. The original H40 investigation, against the OLD JS build.
- Oracle concept also in the harness design: `design/OBSERVABILITY.md` (~lines 104-130, the outbound-payload prompt-assembly oracle).

## Deliverable
A findings doc: (1) what the base prompt/context actually contains (captured), (2) measured interference on the probe, (3) the control surface mapped with what works, (4) a recommended approach ranked by cost/robustness + a reproducible in-role-boot demonstration, (5) anything that would need to change if we later bump the pinned version.

## Guardrails
Pinned version only; never modify the daily/global CC; isolated clean config; reversible experiments; if blocked after a couple of approaches, write up what was tried + what broke and stop rather than thrash.
