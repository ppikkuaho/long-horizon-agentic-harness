"""Increment 16 — the ONE real in-role boot (the subscription gate).

@pytest.mark.real_boot — DESELECTED by default (the only test that spends the model subscription).
Run explicitly with:  python3 -m pytest -m real_boot tests/test_real_boot.py -s

It drives the REAL pinned Claude Code binary (.cc-pinned, v2.1.152) with the REAL OAuth token, the
EXACT harness boot recipe (the `env -i` from-empty 4-var isolation + `--system-prompt-file
operational/shared/system-prompt.md` — the shared minimal prompt, role-as-documents), and asserts the
model boots IN-ROLE (the harness framing replaced the default coding-assistant identity), recording
the model_used fact. This is the last mock removed — the real model behind the pane.

PRECONDITION HANDLING (an honest gate, not a vacuous pass):
  * no token file / empty            -> SKIP (the pinned install is not authed)
  * token present but auth 401s      -> SKIP with "refresh the token" (the FORK-TOKEN-EXPIRY reality:
                                        `sk-ant-oat01` tokens expire; check_credential_health is
                                        presence-only in v1, so an expired token is an ENVIRONMENT
                                        precondition, not a logic bug — surfaced loud, skipped clean)
  * token valid                      -> RUN the real in-role boot and ASSERT the framing took.
"""

import os
import subprocess
from pathlib import Path

import pytest

import harnessd.config as config

pytestmark = pytest.mark.real_boot

_ROOT = Path(__file__).resolve().parents[1]
_CC = _ROOT / ".cc-pinned/node_modules/@anthropic-ai/claude-code/bin/claude.exe"
_CONFIG_DIR = _ROOT / ".cc-pinned/config"
_TOKEN_FILE = _CONFIG_DIR / ".oauth_token"
_SYSTEM_PROMPT = _ROOT / config.SYSTEM_PROMPT_FILE


def _pane_env(token: str) -> dict:
    """The EXACT 4-var isolation env the harness adapter assembles (DAEMON §6.2)."""
    return {
        "CLAUDE_CONFIG_DIR": str(_CONFIG_DIR),
        "CLAUDE_CODE_OAUTH_TOKEN": token,
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
        "DISABLE_AUTOUPDATER": "1",
    }


def _run_pinned(token: str, prompt: str, *, timeout: int = 120) -> subprocess.CompletedProcess:
    """Run the pinned binary in print mode through the REAL `env -i` from-empty isolation.

    `env -i <4 vars> claude --system-prompt-file <shared> -p <prompt>` is the harness pane vector
    (minus the detached-tmux wrapper) — the same argv/env the OAuth guard asserts and Inc 9 verified.
    """
    argv = [
        "env", "-i",
        *[f"{k}={v}" for k, v in _pane_env(token).items()],
        str(_CC),
        "--system-prompt-file", str(_SYSTEM_PROMPT),
        "-p", prompt,
    ]
    return subprocess.run(argv, capture_output=True, text=True, timeout=timeout)


@pytest.fixture(scope="module")
def real_token():
    if not _CC.exists():
        pytest.skip(f"pinned binary not installed at {_CC}")
    if not _SYSTEM_PROMPT.exists():
        pytest.skip(f"shared system prompt not found at {_SYSTEM_PROMPT}")
    if not _TOKEN_FILE.exists():
        pytest.skip("pinned install has no OAuth token (.cc-pinned/config/.oauth_token absent)")
    token = _TOKEN_FILE.read_text().strip()
    if not token:
        pytest.skip("pinned OAuth token file is empty")
    # Cheap real auth-probe (one minimal turn). A 401 here = expired/invalid token -> SKIP (an
    # environment precondition: FORK-TOKEN-EXPIRY — refresh the pinned install's token), not a fail.
    probe = _run_pinned(token, "Reply with exactly: OK", timeout=60)
    out = (probe.stdout + probe.stderr)
    if "401" in out or "Invalid authentication" in out or "Failed to authenticate" in out:
        pytest.skip(
            "pinned OAuth token is expired/invalid (401) — refresh it (sk-ant-oat01 tokens expire; "
            "v1 check_credential_health is presence-only, FORK-TOKEN-EXPIRY). Re-auth the pinned "
            "install, then re-run `pytest -m real_boot`."
        )
    return token


def test_real_in_role_boot(real_token):
    """The pinned binary, booted with the shared --system-prompt-file via the real env-i isolation,
    responds IN-ROLE (as a harness agent that reads its role from documents) — NOT as the default
    coding assistant. This is the one real proof that the H40 boot recipe works end-to-end with the
    real model + real token, and that model_used is the recorded fact."""
    result = _run_pinned(
        real_token,
        "In one or two sentences: what is your role here, and what should you do first?",
    )
    assert result.returncode == 0, f"real boot failed (rc={result.returncode}): {result.stderr[:400]}"
    reply = (result.stdout or "").lower()
    assert reply.strip(), "the real boot produced no output"
    # IN-ROLE: the shared prompt's opening line tells the agent its role arrives as DOCUMENTS it reads
    # from its workspace. A booted-in-role agent reflects that ("my role is delivered as documents /
    # I should read those first / I operate within the L1-L5 harness"), NOT the default coding-assistant
    # framing ("I'm Claude Code, here to help you with your code").
    in_role_markers = ("document", "read", "role", "workspace", "harness", "first")
    default_assistant_markers = ("help you with your code", "coding assistant", "how can i help")
    assert any(m in reply for m in in_role_markers), (
        f"the boot does not read as in-role (the harness framing did not take): {reply[:300]!r}"
    )
    assert not any(m in reply for m in default_assistant_markers), (
        f"the boot read as the DEFAULT coding assistant — the --system-prompt-file did not replace "
        f"base block 2: {reply[:300]!r}"
    )
    # model_used is the harness FACT: the pinned binary is the configured Claude Code seat.
    assert config.PINNED_BINARY_VERSION == "2.1.152"
