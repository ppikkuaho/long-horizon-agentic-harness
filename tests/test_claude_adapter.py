"""Increment 9 — FROZEN acceptance for the Claude-Code adapter (part (a): DRY-RUN argv/env).

Authoritative sources (grounded, not recalled — Lesson 4):
  * IMPLEMENTATION-PLAN §2.11 — adapters/base.py (`RuntimeAdapter.pin_and_open`) +
    adapters/claude_code.py (the FROZEN boot recipe): argv = [CC, "--system-prompt-file",
    system_prompt_file] where system_prompt_file is the CONSTANT operational/shared/system-prompt.md;
    env = exactly the 4 isolation vars; session name == "harness:"+collapse(address); record
    model_used / role_variant / system_prompt_file / system_prompt_file_hash / transcript_path.
  * IMPLEMENTATION-PLAN §6.2 dry-run done-test (L596-619): mock tmux + mock subprocess, assert NO real
    claude.exe exec; argv identical across role_variants; never --bare/--append-system-prompt/--agents.
  * DAEMON §6.2 (H40 recipe) + §6.3 (E32 spawn-failure contract; always record model_used; Codex =
    "adapter port to be supplied").
  * config.SYSTEM_PROMPT_FILE / PINNED_BINARY_VERSION (the config seats — NOT re-hardcoded).

This is part (a): a PURE-ASSEMBLY dry-run. It mocks the subprocess (justified: it asserts the
assembled argv/env WITHOUT executing — there is nothing real to run in a pure-assembly test, and NO
model may be called). The REAL-tmux tests live in test_tmux.py / test_mock_contract.py.

NO IMPLEMENTATION here — harnessd/spawn/adapters/* do not exist yet (RED first).

Load-bearing properties (each pins a mutant):
  * argv uses the SHARED operational/shared/system-prompt.md, NOT a per-level role path
        (mutant: per-level role.md -> caught).
  * argv is IDENTICAL across role_variants L1..L5 (mutant: vary by level -> caught).
  * argv NEVER carries --bare / --append-system-prompt / --agents / --agent (mutant: any -> caught).
  * env is EXACTLY the 4-var set (mutant: extra/missing var -> caught).
  * session name == "harness:" + collapse(address) (mutant: raw address / wrong prefix -> caught).
  * the role rides the brief/load-manifest, NOT the argv/prompt (mutant: role text in argv -> caught).
  * NO real subprocess exec of claude.exe (mutant: real Popen -> caught by the no-exec spy).
  * model_used is ALWAYS recorded == "opus-4.8 / claude-code" (mutant: drop model_used -> caught).
  * transcript_path is non-null and derived from session_uuid (mutant: null / unrelated -> caught).
  * Codex stub RAISES "adapter port to be supplied" AND asserts OPENAI_API_KEY absent.
"""

from __future__ import annotations

import importlib

import pytest

from harnessd import config
from harnessd.spawn import oauth_guard


def _base():
    return importlib.import_module("harnessd.spawn.adapters.base")


def _claude():
    return importlib.import_module("harnessd.spawn.adapters.claude_code")


def _codex():
    return importlib.import_module("harnessd.spawn.adapters.codex")


# The exact 4-var isolation set (DAEMON §6.2). OAuth token present (positive check passes),
# NO ANTHROPIC_API_KEY / OPENAI_API_KEY (negative invariant passes).
def _iso_env():
    return {
        "CLAUDE_CONFIG_DIR": "/HARNESS/.cc-pinned/config",
        "CLAUDE_CODE_OAUTH_TOKEN": "oauth-token-xyz",
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
        "DISABLE_AUTOUPDATER": "1",
    }


_EXPECTED_ENV_KEYS = frozenset(
    {
        "CLAUDE_CONFIG_DIR",
        "CLAUDE_CODE_OAUTH_TOKEN",
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC",
        "DISABLE_AUTOUPDATER",
    }
)

_FORBIDDEN_FLAGS = ("--bare", "--append-system-prompt", "--agents", "--agent")


@pytest.fixture
def no_real_exec(monkeypatch):
    """Spy that asserts NO real subprocess EXEC happens during a dry-run assembly.

    The adapter's tmux dependency is mocked (see make_adapter); this is a second belt:
    if any code path reaches subprocess.Popen/run/call to actually launch claude.exe,
    fail the test. (Pure-assembly dry-run: there is nothing real to run; NO model burn.)
    """
    import subprocess

    calls = []

    def _boom(*a, **k):  # pragma: no cover - only fires on the mutant
        calls.append((a, k))
        raise AssertionError(
            "a DRY-RUN assembly test must NOT exec a real subprocess (claude.exe) — "
            f"saw subprocess call: args={a!r} kwargs={k!r}"
        )

    monkeypatch.setattr(subprocess, "Popen", _boom)
    monkeypatch.setattr(subprocess, "run", _boom)
    monkeypatch.setattr(subprocess, "call", _boom)
    return calls


class _MockTmux:
    """Mock tmux for the dry-run: records create_detached args, returns a fake pane id,
    NEVER touches a real server (server_env clean). Provides the SAME from-empty
    `build_pane_argv` seam the real wrapper exposes so the adapter assembles the pane the
    same way it would in production — but NO real exec happens (no_real_exec spy proves it)."""

    def __init__(self):
        self.created = []

    def build_pane_argv(self, env, argv):
        pane = ["env", "-i"]
        for k, v in env.items():
            pane.append(f"{k}={v}")
        pane += list(argv)
        return pane

    def create_detached(self, session_name, pane_argv, env):
        self.created.append((session_name, list(pane_argv), dict(env)))
        # Post-F18 contract (mirrors the real wrapper): return the CANONICAL live target
        # '<session>:<window>.<pane>' — what `-P -F` prints and list_targets() keys on.
        return f"{session_name}:0.0"

    def server_env(self):
        return {}  # clean server — no leaked key

    def capture_pane(self, session_name):
        return ""

    def list_targets(self):
        return {}

    def kill(self, session_name):
        pass


def _make_adapter(tmux):
    """Build a ClaudeCodeAdapter wired to the mock tmux (the dry-run boundary)."""
    cc = _claude()
    adapter_cls = getattr(cc, "ClaudeCodeAdapter")
    try:
        return adapter_cls(tmux=tmux)
    except TypeError:
        # tolerate an attribute-injection shape
        a = adapter_cls()
        a.tmux = tmux
        return a


def _level(role_variant="L1"):
    """A LevelConfig with the given role_variant (Claude-Code runtime, Opus 4.8)."""
    return config.LevelConfig(
        level=role_variant,
        model="opus-4.8",
        runtime="claude-code",
        role_variant=role_variant,
        tool_manifest=("read", "write", "edit", "bash", "task"),
    )


def _spawn(adapter, role_variant="L1", address="payments/gateway/stripe#exec", env=None):
    return adapter.pin_and_open(
        neutral_brief={"load_manifest": ["operational/%s/role.md" % role_variant], "role_variant": role_variant},
        level_config=_level(role_variant),
        tmux_target=address,
        env=env if env is not None else _iso_env(),
    )


# ===========================================================================
# Module + interface presence (RED-until-built).
# ===========================================================================

def test_base_exposes_runtime_adapter_port():
    base = _base()
    assert hasattr(base, "RuntimeAdapter")
    from abc import ABC
    assert issubclass(base.RuntimeAdapter, ABC)
    assert hasattr(base.RuntimeAdapter, "pin_and_open")
    # abstract: cannot instantiate directly
    with pytest.raises(TypeError):
        base.RuntimeAdapter()


def test_claude_adapter_is_a_runtime_adapter():
    base = _base()
    cc = _claude()
    assert issubclass(cc.ClaudeCodeAdapter, base.RuntimeAdapter)


# ===========================================================================
# Part (a) — DRY-RUN argv: the SHARED system-prompt, not a per-level role path.
# ===========================================================================

def test_argv_uses_shared_system_prompt_file_flag(no_real_exec):
    """argv == [CC, '--system-prompt-file', <ABSOLUTE shared system-prompt.md>, ...].

    The transport increment made the flag value ABSOLUTE (resolved against HARNESS_ROOT — the
    config.py NOTE's resolution contract): the pane now boots in the NODE's workspace (-c), so a
    repo-relative path would dangle. Still the ONE shared prompt, identical L1..L5.
    """
    import os as _os

    tmux = _MockTmux()
    adapter = _make_adapter(tmux)
    result = _spawn(adapter)

    # the assembled child argv — recorded on the result and/or in the mock tmux pane_argv
    argv = _result_argv(result, tmux)
    assert "--system-prompt-file" in argv, "the boot MUST pass --system-prompt-file (H40 recipe)"
    idx = argv.index("--system-prompt-file")
    spf = argv[idx + 1]
    assert _os.path.isabs(spf), f"--system-prompt-file must be ABSOLUTE (survives any pane cwd); got {spf!r}"
    assert spf.endswith(config.SYSTEM_PROMPT_FILE), (
        "the flag value MUST resolve the CONSTANT shared operational/shared/system-prompt.md, "
        f"not {spf!r} — the per-level role is NEVER in argv (DAEMON §6.2, H40)"
    )


def test_system_prompt_is_not_a_per_level_role_path(no_real_exec):
    """The flag value is the SHARED prompt, NOT a per-level role/soul/config path (the key mutant)."""
    tmux = _MockTmux()
    adapter = _make_adapter(tmux)
    result = _spawn(adapter, role_variant="L3")
    argv = _result_argv(result, tmux)
    spf = argv[argv.index("--system-prompt-file") + 1]
    assert "/L3/" not in spf and "role.md" not in spf and "soul.md" not in spf, (
        "the system-prompt-file must NOT be a per-level role path (e.g. operational/L3/role.md) — "
        f"it is the shared constant; got {spf!r}"
    )
    # ABSOLUTE since the transport increment (the pane boots in the node workspace); still the
    # ONE shared constant path underneath.
    assert spf.endswith("operational/shared/system-prompt.md")


def test_argv_identical_across_role_variants(no_real_exec):
    """argv is byte-identical across L1..L5 — the prompt is runtime-global, role rides the brief."""
    argvs = []
    for rv in ("L1", "L2", "L3", "L4", "L5"):
        tmux = _MockTmux()
        adapter = _make_adapter(tmux)
        result = _spawn(adapter, role_variant=rv)
        argvs.append(tuple(_result_argv(result, tmux)))
    assert len(set(argvs)) == 1, (
        f"argv MUST be identical across role_variants (the shared prompt, not per-level); got {argvs!r}"
    )


def test_argv_never_carries_forbidden_flags(no_real_exec):
    """argv NEVER includes --bare / --append-system-prompt / --agents / --agent (H40 foot-guns)."""
    for rv in ("L1", "L2", "L3", "L4", "L5"):
        tmux = _MockTmux()
        adapter = _make_adapter(tmux)
        result = _spawn(adapter, role_variant=rv)
        argv = _result_argv(result, tmux)
        for flag in _FORBIDDEN_FLAGS:
            assert flag not in argv, (
                f"argv must NEVER carry {flag!r} (DAEMON §6.2: --bare forces API-key auth; "
                f"--append-system-prompt keeps full framing; --agents does not inject persona); got {argv!r}"
            )


def test_role_text_is_not_in_argv(no_real_exec):
    """Role-as-documents: the per-seat role rides the brief/load-manifest, NOT the argv/prompt.

    No argv token may carry role/persona content — only the binary, the flag, and the SHARED path.
    """
    tmux = _MockTmux()
    adapter = _make_adapter(tmux)
    result = _spawn(adapter, role_variant="L2", address="proj/area#plan")
    argv = _result_argv(result, tmux)
    joined = " ".join(argv).lower()
    # the only path allowed is the shared system-prompt; no per-level role doc leaks into argv
    assert "operational/l2/" not in joined and "role.md" not in joined, (
        "the per-level role must arrive via the brief's load-manifest (role-as-documents), "
        f"never flattened into argv; got {argv!r}"
    )


# ===========================================================================
# Part (a) — DRY-RUN env: EXACTLY the 4-var isolation set.
# ===========================================================================

def test_env_is_exactly_the_four_isolation_vars(no_real_exec):
    """The pane env is EXACTLY the 4 isolation vars — no extra, no missing."""
    tmux = _MockTmux()
    adapter = _make_adapter(tmux)
    result = _spawn(adapter)
    env = _result_env(result, tmux)
    assert frozenset(env.keys()) == _EXPECTED_ENV_KEYS, (
        f"env must be EXACTLY the 4-var isolation set {sorted(_EXPECTED_ENV_KEYS)!r}; "
        f"got {sorted(env)!r} (extra or missing var is a mutant)"
    )


def test_env_carries_no_api_key(no_real_exec):
    """The assembled env carries NO raw API key (the negative invariant holds on the real env)."""
    tmux = _MockTmux()
    adapter = _make_adapter(tmux)
    result = _spawn(adapter)
    env = _result_env(result, tmux)
    assert "ANTHROPIC_API_KEY" not in env and "OPENAI_API_KEY" not in env
    # and the guard would accept it
    assert oauth_guard.assert_no_api_key(env, ["claude", "--system-prompt-file", "x"]) is None


def test_pane_argv_is_env_i_isolated(no_real_exec):
    """The pane_argv handed to tmux.create_detached begins with the from-empty `env -i` isolator."""
    tmux = _MockTmux()
    adapter = _make_adapter(tmux)
    _spawn(adapter)
    assert tmux.created, "create_detached must have been called (the dry-run boundary)"
    _session, pane_argv, _env = tmux.created[0]
    assert pane_argv[:2] == ["env", "-i"], (
        f"the pane command MUST be from-empty `env -i <K=V…> <argv…>`; got {pane_argv!r}"
    )
    # and the guard accepts this pane shape
    assert oauth_guard.assert_pane_env_isolated(pane_argv, server_env={}) is None


# ===========================================================================
# Part (a) — session name == addressing.session_name_for(address) (F18/OSA-01).
# The pre-fix 'harness:'+collapse(address) shape was silently RENAMED by tmux
# (':' in a session name -> '_'), so the recorded key never matched the live one.
# ===========================================================================

def test_session_name_is_the_canonical_addressing_derivation(no_real_exec):
    """The tmux session name is addressing.session_name_for(address) — 'harness-' + the address
    with '/', '#', ':', '.' folded to '-' — so tmux never renames it and reconcile can match
    tmux<->ledger (F18; the old 'harness:' prefix was rewritten to 'harness_' by tmux 3.6a)."""
    from harnessd import addressing

    tmux = _MockTmux()
    adapter = _make_adapter(tmux)
    address = "payments/gateway/stripe#exec"
    _spawn(adapter, address=address)
    assert tmux.created, "create_detached must have been called"
    session_name = tmux.created[0][0]
    assert session_name == addressing.session_name_for(address) == "harness-payments-gateway-stripe-exec", (
        f"session name must be addressing.session_name_for(address); got {session_name!r}"
    )


# ===========================================================================
# Part (a) — recorded facts: model_used, system_prompt_file(_hash), transcript_path.
# ===========================================================================

def test_records_model_used_always(no_real_exec):
    """model_used == 'opus-4.8 / claude-code' is ALWAYS recorded (config=intent, model_used=fact)."""
    tmux = _MockTmux()
    adapter = _make_adapter(tmux)
    result = _spawn(adapter)
    assert result.model_used == "opus-4.8 / claude-code", (
        f"the adapter must always record the ACTUAL model_used; got {result.model_used!r}"
    )


def test_records_role_variant_and_system_prompt_file(no_real_exec):
    tmux = _MockTmux()
    adapter = _make_adapter(tmux)
    result = _spawn(adapter, role_variant="L4")
    assert result.role_variant == "L4"
    assert result.system_prompt_file == config.SYSTEM_PROMPT_FILE
    assert isinstance(result.system_prompt_file_hash, str) and result.system_prompt_file_hash


def test_records_transcript_path_derived_from_session_uuid(no_real_exec):
    """transcript_path is non-null and derived from session_uuid (the spawn<->detector producer)."""
    tmux = _MockTmux()
    adapter = _make_adapter(tmux)
    result = _spawn(adapter)
    assert result.session_uuid, "a session_uuid must be recorded"
    assert result.transcript_path, (
        "transcript_path must be non-null (the detector stats it; a null path breaks the contract)"
    )
    assert result.session_uuid in result.transcript_path, (
        f"transcript_path must be DERIVED from session_uuid; uuid {result.session_uuid!r} not in "
        f"path {result.transcript_path!r}"
    )
    assert result.transcript_path.endswith(".jsonl"), "transcript_path is the <session-uuid>.jsonl file"


# ===========================================================================
# Part (a) — the OAuth gate is invoked BEFORE the child runs (E32 ordering).
# ===========================================================================

def test_refuses_when_api_key_present_before_any_create_detached(no_real_exec):
    """An ANTHROPIC_API_KEY in env makes the adapter raise ApiKeyForbidden and open NO actor."""
    tmux = _MockTmux()
    adapter = _make_adapter(tmux)
    leaky = _iso_env()
    leaky["ANTHROPIC_API_KEY"] = "nope"
    with pytest.raises(oauth_guard.ApiKeyForbidden):
        _spawn(adapter, env=leaky)
    assert tmux.created == [], (
        "the OAuth gate must fire BEFORE create_detached — NO tmux actor may open on a forbidden env"
    )


def test_refuses_when_oauth_token_absent(no_real_exec):
    """A missing CLAUDE_CODE_OAUTH_TOKEN raises AuthExpired (the DISTINCT class) and opens NO actor."""
    tmux = _MockTmux()
    adapter = _make_adapter(tmux)
    no_tok = _iso_env()
    del no_tok["CLAUDE_CODE_OAUTH_TOKEN"]
    # absent token: with only 3 vars the env is also incomplete, but the credential check is the
    # load-bearing one — AuthExpired must surface (not ApiKeyForbidden).
    with pytest.raises(oauth_guard.AuthExpired):
        _spawn(adapter, env=no_tok)
    assert tmux.created == [], "no tmux actor may open when the OAuth token is absent (E32)"


def test_no_real_subprocess_exec_during_dry_run(no_real_exec):
    """The whole dry-run assembly executes WITHOUT a real claude.exe subprocess (no model burn)."""
    tmux = _MockTmux()
    adapter = _make_adapter(tmux)
    _spawn(adapter)
    assert no_real_exec == [], "the dry-run must not have invoked any real subprocess"


# ===========================================================================
# Part (a) — the Codex stub RAISES + asserts OPENAI_API_KEY absent.
# ===========================================================================

def test_codex_stub_raises_not_implemented():
    """CodexAdapter.pin_and_open RAISES 'adapter port to be supplied' — never a silent fallback."""
    codex = _codex()
    base = _base()
    assert issubclass(codex.CodexAdapter, base.RuntimeAdapter)
    a = codex.CodexAdapter()
    with pytest.raises(NotImplementedError) as exc:
        a.pin_and_open(
            neutral_brief={},
            level_config=_level("L5#exec"),
            tmux_target="proj/x#exec",
            env={},
        )
    assert "adapter port to be supplied" in str(exc.value).lower()


def test_codex_stub_asserts_no_openai_key():
    """The Codex stub asserts OPENAI_API_KEY is ABSENT — the shared negative invariant the
    unbuilt Codex fill cannot delete."""
    codex = _codex()
    a = codex.CodexAdapter()
    with pytest.raises((AssertionError, oauth_guard.ApiKeyForbidden)):
        a.pin_and_open(
            neutral_brief={},
            level_config=_level("L5#exec"),
            tmux_target="proj/x#exec",
            env={"OPENAI_API_KEY": "sk-nope"},
        )


# ===========================================================================
# Helpers to read the assembled argv/env off the result OR the mock tmux record.
# The frozen contract: the assembled child argv (the part AFTER `env -i <K=V…>`) and the
# 4-var env are observable. We accept either an explicit result.argv/result.env OR the
# pane_argv recorded by the mock tmux (env -i <K=V…> <argv…>), recovering both.
# ===========================================================================

def _recover_from_pane_argv(pane_argv):
    """Split `env -i <K=V…> <argv…>` into (env_dict, child_argv)."""
    assert pane_argv[:2] == ["env", "-i"], (
        f"pane_argv must begin with the from-empty isolator `env -i`; got {pane_argv!r}"
    )
    env = {}
    i = 2
    while i < len(pane_argv) and "=" in pane_argv[i] and not pane_argv[i].startswith("-"):
        k, v = pane_argv[i].split("=", 1)
        env[k] = v
        i += 1
    return env, pane_argv[i:]


def _result_argv(result, tmux):
    argv = getattr(result, "argv", None)
    if argv:
        return list(argv)
    assert tmux.created, "no argv on result and create_detached not called — cannot read child argv"
    _session, pane_argv, _env = tmux.created[0]
    _env_recovered, child_argv = _recover_from_pane_argv(pane_argv)
    return list(child_argv)


def _result_env(result, tmux):
    env = getattr(result, "env", None)
    if env:
        return dict(env)
    assert tmux.created, "no env on result and create_detached not called — cannot read env"
    _session, pane_argv, _passed_env = tmux.created[0]
    if _passed_env:
        return dict(_passed_env)
    env_recovered, _child = _recover_from_pane_argv(pane_argv)
    return env_recovered
