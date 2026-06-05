# Pinned Claude Code — the harness substrate

The L1-L5 harness runs L1-L4 (and L5+) on a **pinned, vanilla, isolated** Claude Code — separate from any daily/patched CC (which auto-updates and carries Life-OS patches/hooks/injections). The whole point of pinning is a frozen, known surface we can patch (H40) and trust to behave identically across runs.

## What's pinned (2026-06-04)
- **Version:** `2.1.152` — the `stable` dist-tag at pin time. Chosen for a conservative, frozen surface, not newest features. (Daily was `2.1.156`; `latest` was `2.1.162`.)
- **Install (gitignored, reproducible):**
  ```bash
  npm install --prefix .cc-pinned @anthropic-ai/claude-code@2.1.152
  ```
  Native binary: `.cc-pinned/node_modules/@anthropic-ai/claude-code/bin/claude.exe` (Mach-O arm64, ~214 MB).
- **Launch (isolated):** `.cc-pinned/claude-pinned.sh` — sets `CLAUDE_CONFIG_DIR=.cc-pinned/config` (clean config: no inherited hooks/MCP/injections), `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1`, `DISABLE_AUTOUPDATER=1`. Auth via `CLAUDE_CODE_OAUTH_TOKEN` (env, **verified present in the binary**) — not by sharing the patched `~/.claude`.
- **`.cc-pinned/` is gitignored** (node_modules + config); this file is the tracked record + reinstall recipe.

## Open setup items (before first agent boot)
1. **Auth the pinned install** — provide `CLAUDE_CODE_OAUTH_TOKEN` (or the token-file-descriptor) so the clean config runs without inheriting the patched config.
2. **Confirm auto-update is truly off** — `DISABLE_AUTOUPDATER` was not found in the binary's strings; the real pin is the npm version + isolated prefix. Verify the binary never self-replaces.
3. **Vanilla-boot verification = the first H40 test** — launch via the wrapper, confirm it boots with NO Life-OS hooks/injections, then measure whether/how the base "coding assistant" framing can be suppressed so an agent boots in-role.

## Useful env vars discovered in the binary
`CLAUDE_CONFIG_DIR`, `CLAUDE_CODE_OAUTH_TOKEN` (+ `_FILE_DESCRIPTOR`), `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`, `CLAUDE_CODE_SUBAGENT_MODEL`, `CLAUDE_CODE_AUTO_COMPACT_WINDOW`, `CLAUDE_CODE_SESSION_KIND`, `CLAUDE_CODE_ENTRYPOINT`, `CLAUDE_CODE_TMPDIR`, `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB`, `CLAUDE_CODE_REMOTE`.
