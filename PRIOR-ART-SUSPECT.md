# Prior Art — Mine for Lessons, NOT for Reuse (SUSPECT)

Per the 2026-06-02 decision: the harness is built **clean**. The existing Life-OS implementation work is **subpar for this purpose** — do not import it as code. But some of it encodes hard-won *lessons* worth not re-discovering. Mine those; treat everything below as **suspect**.

All paths are in `~/Documents/Life-os/`.

| Prior art | Why it's worth a look | Verdict |
|-----------|-----------------------|---------|
| `dev/patches/claude-code/` (`claude_session_manager.py`, `recursive_subagent_runtime.py`, `prompt_assembly_*.py`, `rule_origin_report.py`) | The **base-prompt interference (H40)** investigation — how Claude Code's injected system prompt behaves and where it fights a role identity. This is the build's highest-risk unknown; the *findings* here may save a rediscovery. | **SUSPECT — study findings only, don't reuse code.** |
| `core/system/scripts/agent-activate.py`, `work_scoped_agent.py` | Spawn / session-activation prior art (the pattern the old design referenced). | **SUSPECT — reference for shape, build fresh.** |
| The Life-OS **bus** (`/message` system + related) | Inter-session messaging. The harness needs its **own** bus; study this for ideas only. | **SUSPECT — study, do NOT reuse as-is.** |
| `core/system/scripts/subagent-preflight.py` | A working example of a return-contract preflight **hook** — the pattern the trace-block enforcement hook will follow. | **SUSPECT — pattern reference.** |

**Rule:** anything pulled from here is rewritten clean and re-validated. Nothing above is trusted by default.
