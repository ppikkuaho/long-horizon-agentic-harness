"""Commissioning entry — assemble the runtime descriptor + bind the global seams so daemon.run boots.

The review found daemon.run / boot read ledger.RUNTIME_ROOT + the tmux dedicated-server socket but never
SET them, and the launchd-named entry had no descriptor assembler. This is the commissioning gate to a
live run: build_runtime() wires the REAL ClaudeCodeAdapter + the 4-var OAuth env (read from the pinned
install) + the L1 root config; daemon._apply_global_seams binds ledger.RUNTIME_ROOT + the dedicated tmux
socket so the substrate (genesis/executor/tmux) is correctly anchored before boot.

These tests pin the descriptor SHAPE + the seam-binding (no real boot — the live run is the real oracle).
"""

import os

import pytest

import harnessd.commissioning as commissioning
import harnessd.config as config
import harnessd.daemon as daemon
import harnessd.ledger as ledger
import harnessd.spawn.tmux as tmux
from harnessd.spawn.adapters.claude_code import ClaudeCodeAdapter


def test_build_runtime_assembles_the_oauth_env_and_l1_config(tmp_path):
    """The descriptor carries the genesis config: the 4-var OAuth-only env (token + config dir + the two
    isolation flags), the L1 root address/level, and a real ClaudeCodeAdapter."""
    rt = commissioning.build_runtime(
        runtime_root=tmp_path / "runtime", build_id="build-test",
        oauth_token="sk-ant-oat01-TESTTOKEN")
    cfg = rt.config
    assert cfg.env["CLAUDE_CODE_OAUTH_TOKEN"] == "sk-ant-oat01-TESTTOKEN"
    assert cfg.env.get("CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC") == "1"
    assert cfg.env.get("DISABLE_AUTOUPDATER") == "1"
    assert "CLAUDE_CONFIG_DIR" in cfg.env
    assert cfg.l1_address and cfg.l1_level == "L1"
    # E4: production ships adapter=None — the chokepoint resolves adapters from the
    # per-runtime REGISTRY (daemon._apply_global_seams); injecting a single adapter here
    # would override the registry and recreate the LT-8/O1 silent divergence.
    assert rt.adapter is None
    # the genesis collaborators are present
    assert rt.executor is not None and rt.tmux is not None


def test_build_runtime_reads_the_pinned_token_when_not_supplied(tmp_path, monkeypatch):
    """When no token is passed, build_runtime reads it from the pinned install's .oauth_token (the real
    source). We point the token-file resolution at a temp file to avoid depending on the live token."""
    tokfile = tmp_path / ".oauth_token"
    tokfile.write_text("sk-ant-oat01-FROMFILE", encoding="utf-8")
    monkeypatch.setattr(commissioning, "_pinned_token_file", lambda: tokfile)
    rt = commissioning.build_runtime(runtime_root=tmp_path / "runtime", build_id="b")
    assert rt.config.env["CLAUDE_CODE_OAUTH_TOKEN"] == "sk-ant-oat01-FROMFILE"


def test_build_runtime_oauth_only_no_raw_api_key(tmp_path):
    """The HARD invariant: the assembled env carries the OAuth token and NO raw API key."""
    rt = commissioning.build_runtime(runtime_root=tmp_path / "runtime", build_id="b",
                                     oauth_token="sk-ant-oat01-X")
    assert "ANTHROPIC_API_KEY" not in rt.config.env and "OPENAI_API_KEY" not in rt.config.env


def test_apply_global_seams_binds_runtime_root_and_tmux_socket(tmp_path):
    """daemon._apply_global_seams must bind ledger.RUNTIME_ROOT (the substrate's anchor) + the dedicated
    tmux server socket (so harness panes land on the daemon's own tmux server, not the user's), BEFORE
    boot. Without this, genesis/executor raise 'runtime_root not configured' and panes pollute the
    default tmux server."""
    prev_root = ledger.RUNTIME_ROOT
    prev_sock = tmux._SOCKET
    try:
        rt = commissioning.build_runtime(runtime_root=tmp_path / "runtime", build_id="b",
                                         oauth_token="sk-ant-oat01-X")
        daemon._apply_global_seams(rt)
        assert str(ledger.RUNTIME_ROOT) == str(tmp_path / "runtime"), "RUNTIME_ROOT must be bound"
        assert tmux._SOCKET is not None, "the dedicated tmux server socket must be bound (visible-mode attach)"
    finally:
        ledger.RUNTIME_ROOT = prev_root
        tmux.set_socket(prev_sock)


def test_runtime_exposes_the_tmux_socket_name_for_observability(tmp_path):
    """The descriptor surfaces the tmux socket NAME so the operator can attach:
    `tmux -L <socket> attach -t harness:<addr>` (the visible-mode watch path, task #11)."""
    rt = commissioning.build_runtime(runtime_root=tmp_path / "runtime", build_id="b",
                                     oauth_token="sk-ant-oat01-X")
    assert getattr(rt, "tmux_socket", None), "the runtime must name its tmux socket for attach"


def test_default_runtime_root_lands_in_the_external_workspaces_root(monkeypatch, tmp_path):
    """Workspaces live OUTSIDE the repo (user ruling 2026-06-12): with no explicit root and no
    per-run env override, the default lands under DEFAULT_WORKSPACES_ROOT/<build-id> — never
    inside the repo. $HARNESS_WORKSPACES_ROOT relocates the family. (Mutant: repo-nested
    default restored -> caught.)"""
    monkeypatch.delenv("HARNESS_RUNTIME_ROOT", raising=False)
    monkeypatch.delenv("HARNESS_WORKSPACES_ROOT", raising=False)
    rt = commissioning.build_runtime(build_id="b-default", oauth_token="sk-ant-oat01-X")
    assert rt.runtime_root == commissioning.DEFAULT_WORKSPACES_ROOT / "b-default"
    assert "l1-l5-agent-harness" not in str(rt.runtime_root), (
        "the default workspace tree must not nest inside the repo"
    )

    monkeypatch.setenv("HARNESS_WORKSPACES_ROOT", str(tmp_path / "ws"))
    rt2 = commissioning.build_runtime(build_id="b-relocated", oauth_token="sk-ant-oat01-X")
    assert rt2.runtime_root == tmp_path / "ws" / "b-relocated"
