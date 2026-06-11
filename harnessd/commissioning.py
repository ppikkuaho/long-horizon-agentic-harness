"""commissioning — assemble the runtime descriptor that ``daemon.run`` boots (the live-run gate).

The substrate is built + unit-tested; ``daemon.run``/``boot`` READ ``ledger.RUNTIME_ROOT``, the dedicated
tmux-server socket, and the spawn adapter — but nothing ASSEMBLED them for a real launch. This module is
that assembler: it wires the REAL ``ClaudeCodeAdapter`` + the 4-var OAuth-only env (read from the pinned
install) + the L1 root config into the ``runtime`` descriptor ``boot``/``run_genesis`` consume.

OAUTH-ONLY (HARD invariant): the env carries ``CLAUDE_CODE_OAUTH_TOKEN`` and NEVER a raw
``ANTHROPIC_API_KEY``/``OPENAI_API_KEY`` (the pane's ``env -i`` + oauth_guard enforce it at spawn; this
assembler simply never puts a raw key in).

This module is intentionally separate from ``config`` (config is import-cycle-free; constructing the
adapter here would cycle config<->adapter). It is imported only by the daemon's ``__main__`` launch path.
"""

from __future__ import annotations

import dataclasses
import os
from pathlib import Path
from types import SimpleNamespace

from harnessd import config, ledger
from harnessd import executor as _executor
from harnessd.spawn import tmux as _tmux

# The pinned, isolated Claude Code install (v2.1.152) + its clean CLAUDE_CONFIG_DIR (no inherited hooks/
# MCP/patches) — the OAuth-only credential lives at <config>/.oauth_token (DAEMON §7; CLAUDE.md).
_REPO_ROOT = Path(__file__).resolve().parents[1]
_PINNED_CONFIG_DIR = _REPO_ROOT / ".cc-pinned" / "config"

# The L1 root address/level (the parentless System Orchestrator — genesis registers it parentless, §7).
L1_ADDRESS = "L1#exec"
L1_LEVEL = "L1"


def _pinned_token_file() -> Path:
    """The pinned install's OAuth token file (a test seam patches this to avoid the live token)."""
    return _PINNED_CONFIG_DIR / ".oauth_token"


def _read_oauth_token() -> str:
    """Read the OAuth subscription token: $CLAUDE_CODE_OAUTH_TOKEN, else the pinned .oauth_token file.

    Raises a clear commissioning error if absent (genesis would otherwise fail the credential
    precondition — a token lapse now reads as 'refresh the token', F3/FORK-TOKEN-EXPIRY)."""
    env_tok = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")
    if env_tok:
        return env_tok
    tok_file = _pinned_token_file()
    if tok_file.is_file():
        tok = tok_file.read_text(encoding="utf-8").strip()
        if tok:
            return tok
    raise RuntimeError(
        "no OAuth token: set $CLAUDE_CODE_OAUTH_TOKEN or write the pinned install's token to "
        f"{_pinned_token_file()} (refresh it via the pinned-install login). The harness is OAuth-only — "
        "a raw API key is forbidden."
    )


def _tmux_socket_name(build_id: str) -> str:
    """The dedicated tmux SERVER socket name (``tmux -L <name>``) for this daemon — isolated from the
    user's default tmux server. A short, memorable name so the operator can attach to watch the panes:
    ``tmux -L <name> attach -t harness:<addr>`` (visible-mode, task #11)."""
    return "harnessd"


def build_runtime(*, runtime_root=None, build_id: str = None, oauth_token: str = None) -> SimpleNamespace:
    """Assemble the ``runtime`` descriptor ``daemon.run``/``boot`` consume.

    runtime_root: where the per-build tree lives (``/runtime/<build-id>/`` style); resolved from the arg,
    else $HARNESS_RUNTIME_ROOT, else ``<repo>/runtime/<build-id>``. build_id: the arg, else
    $HARNESS_BUILD_ID, else ``build-local``. oauth_token: the arg, else read from the pinned install.

    Returns a descriptor carrying: ``runtime_root``, ``build_id``, ``config`` (the genesis cfg: env +
    l1_address/level + runtime_root + build_id + pinned_binary + level_config), ``adapter`` (the REAL
    ClaudeCodeAdapter), ``executor`` + ``tmux`` (the genesis collaborators), and ``tmux_socket`` (the
    dedicated server name for attach). The global seams (ledger.RUNTIME_ROOT + tmux socket) are bound by
    ``daemon._apply_global_seams`` at run() time, NOT here (this is pure construction).
    """
    build_id = build_id or os.environ.get("HARNESS_BUILD_ID") or "build-local"
    if runtime_root is None:
        env_root = os.environ.get("HARNESS_RUNTIME_ROOT")
        runtime_root = Path(env_root) if env_root else (_REPO_ROOT / "runtime" / build_id)
    runtime_root = Path(runtime_root)

    token = oauth_token or _read_oauth_token()

    # The 4-var OAuth-only isolation env (DAEMON §6.2) — exactly what the pinned launcher exports.
    env = {
        "CLAUDE_CODE_OAUTH_TOKEN": token,
        "CLAUDE_CONFIG_DIR": str(_PINNED_CONFIG_DIR),
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
        "DISABLE_AUTOUPDATER": "1",
    }

    # SUPERVISED-SMOKE OVERRIDE (user-approved 2026-06-10): when the operator launched this
    # daemon with HARNESS_UNJAILED_SKIP_PERMISSIONS=1 (strictly "1" — config owns the read seam),
    # the genesis L1 LevelConfig carries unjailed_skip_permissions=True, and the adapter adds
    # --dangerously-skip-permissions to the UNJAILED argv. This EXPLICITLY decouples SECURITY.md
    # constraint 4's skip-perms<->jail coupling for the small supervised smoke run — the user's
    # call: "Unjailed + dangerously skip permissions. It is a small run, the risk of something
    # catastrophic happening is minimal." Default OFF = byte-identical behavior. The jail tier
    # (REMEDIATION F9–F13) RETIRES this knob. Child spawns resolve the same posture via
    # config.get_level_config (the ipc/outbox resolver). The posture is journaled per spawn
    # (SpawnResult.permission_posture + the STEP4 binding stamp).
    level_config = config.LevelConfig.for_level(L1_LEVEL)
    if config.unjailed_skip_permissions_requested():
        level_config = dataclasses.replace(level_config, unjailed_skip_permissions=True)

    cfg = SimpleNamespace(
        env=env,
        l1_address=L1_ADDRESS,
        l1_level=L1_LEVEL,
        runtime_root=runtime_root,
        build_id=build_id,
        pinned_binary=config.PINNED_BINARY,
        level_config=level_config,
    )

    # E4: production ships adapter=None — the chokepoint resolves adapters from the PER-RUNTIME
    # REGISTRY (daemon._apply_global_seams registers claude-code + codex), so a codex-configured
    # L5 gets the CodexAdapter. Injecting a single adapter here would WIN over the registry (the
    # injected seam is the explicit test override) and recreate the LT-8/O1 silent divergence.
    return SimpleNamespace(
        runtime_root=runtime_root,
        build_id=build_id,
        config=cfg,
        adapter=None,
        executor=_executor,
        tmux=_tmux,
        tmux_socket=_tmux_socket_name(build_id),
    )
