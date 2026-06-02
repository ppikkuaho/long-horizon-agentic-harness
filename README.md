# L1–L5 Agent Harness

The standalone home for the **L1–L5 agentic software-building system** — a five-level hierarchy of LLM agents that turns a user's intent into built, verified software.

- **L1 System Orchestrator** → **L2 Project Architect** → **L3 Module Designer** → **L4 Workstream Coordinator** → **L5 Task Executor** (+ L5+ reviewer)

This repo holds two things: the **design corpus** (the hardened spec, copied from Life-OS on 2026-06-02) and — to be built — the **harness** (the runtime that actually spawns and coordinates the agents).

## Status

- ✅ **Design corpus** — consolidated and hardened against a faithful end-to-end simulation (the finishing pass). Copied here non-destructively; see `MOVE-MANIFEST.md` + `manifest.json` for the integrity record.
- ⬜ **Harness runtime** — not yet started. First spike: the Claude Code base-prompt patch + minimal spawn (the one genuinely unproven piece).

## Layout

| Path | What |
|------|------|
| `design/` | The system spec — 17 core docs. Start with `PROJECT-PLANNING.md` (the flow), `PLAN-ALIGNMENT-GATE.md` (the alignment gate), `DECOMPOSITION-METHODOLOGY.md`, `ARCHITECTURE.md`. `working-notes/` holds the consolidation history. |
| `operational/` | The agent definitions — `L1`–`L5` (role/config/spawn-template) + `shared/` (runtime-and-model-map, agent-definition-principles, comms-protocol, git-protocol, agent-lifecycle, intent-spec-contract, user-profile-schema). |
| `reference/` *(dry-run)* | `dry-run/` — the finishing-pass simulation output: a real Payments slice built end-to-end (intent spec, ADRs, area design, frozen acceptance tests, working code, 17/17 passing). A reference exemplar, not part of the spec. |
| `_archive-from-lifeos/` | Parked, **suspect** research copied along from Life-OS (orchestration-frame, preference-extraction, etc.) — unrelated to this system. Prunable; kept only for traceability. |
| `PRIOR-ART-SUSPECT.md` | Life-OS code/infra to mine for *lessons* (not reuse) during the build — marked suspect. |

## Build decisions (settled 2026-06-02)

- **Standalone, clean start.** Build the harness fresh; do not import the Life-OS implementation code (it's subpar for this — see `PRIOR-ART-SUSPECT.md`).
- **Pinned Claude Code version.** The harness runs against a frozen, isolated CC install (separate from any interactive CC, which keeps auto-updating). CC is updated only deliberately, for model needs, with a re-test pass. This stabilizes the hook/prompt surface and makes the base-prompt patch (H40) tractable — patch a known version, not a moving target.
- **Own bus.** The comms layer assumed reusing the Life-OS bus; standalone, the harness owns its bus. The filesystem-truth + best-effort design lets it start dead-simple. (Study the Life-OS bus for ideas; don't reuse as-is.)
- **Runtime artifacts outside git.** The project trees the harness creates when it builds software live in a runtime dir, not committed.
- **L1–L4 on Claude Code (Opus 4.8); L5 on Codex (GPT-5.5).** Cross-runtime handoff proven in the simulation.

*Originals remain in `~/Documents/Life-os/projects/ai-architecture/` (untouched).*
