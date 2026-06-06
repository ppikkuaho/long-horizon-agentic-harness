"""Security-jail STRENGTHENING (verification-gate fixes).

The jail review found a latent BLOCKER: the trailing `(allow file-read* (subpath WORKROOT))` is
last-match-wins, so if CONFIG sits UNDER WORKROOT it un-denies the `.oauth_token` read-deny -> the
token becomes agent-readable. Fixed by a FINAL last-match re-deny (read AND write) of the token
literal. Pin it with REAL sandbox-exec. Plus pin the new `resolve_containment` production seam.
"""

import os
import shutil
import subprocess
import tempfile

import pytest

import harnessd.spawn.sandbox as sandbox

_HAS_SANDBOX = shutil.which("sandbox-exec") is not None and os.uname().sysname == "Darwin"
pytestmark = pytest.mark.skipif(not _HAS_SANDBOX, reason="needs macOS sandbox-exec")


def _run_in_jail(profile_text, argv):
    with tempfile.NamedTemporaryFile("w", suffix=".sb", delete=False) as f:
        f.write(profile_text)
        prof = f.name
    try:
        return subprocess.run(["/usr/bin/sandbox-exec", "-f", prof, *argv],
                              capture_output=True, text=True)
    finally:
        os.unlink(prof)


def test_token_re_deny_holds_even_when_config_under_workroot():
    """The OAuth token is read-AND-write-denied under the jail EVEN when CONFIG is inside WORKROOT
    (the last-match WORKROOT re-allow would otherwise un-deny it — the latent blocker). REAL sandbox."""
    wr = os.path.realpath(tempfile.mkdtemp(prefix="jail-tokdeny-"))
    try:
        cfg = os.path.join(wr, "config")  # CONFIG UNDER WORKROOT — the hole condition
        os.makedirs(cfg)
        tokpath = os.path.join(cfg, ".oauth_token")
        with open(tokpath, "w") as f:
            f.write("SECRET-TOKEN-LEAK-MARKER")
        profile = sandbox.render_profile(
            {"WORKROOT": wr, "TMPDIR": os.path.join(wr, "tmp"), "CONFIG": cfg, "HOME": os.path.expanduser("~"),
             "READ_DENY_ROOT": ""})
        # READ must be denied (the token marker must NOT leak).
        r = _run_in_jail(profile, ["cat", tokpath])
        assert "SECRET-TOKEN-LEAK-MARKER" not in r.stdout, "the OAuth token LEAKED under the jail (re-deny failed)"
        assert r.returncode != 0, "reading the token under the jail must be DENIED"
        # WRITE must be denied (§3.2 — a writable CONFIG must not let the agent rewrite the token).
        w = _run_in_jail(profile, ["sh", "-c", f"echo X > '{tokpath}'"])
        assert w.returncode != 0, "writing the token under the jail must be DENIED (§3.2)"
        with open(tokpath) as f:
            assert f.read() == "SECRET-TOKEN-LEAK-MARKER", "the token was overwritten under the jail"
    finally:
        shutil.rmtree(wr, ignore_errors=True)


def test_own_env_still_readable_under_workroot():
    """Control: the agent's OWN workspace .env IS readable (the re-deny is scoped to the token, NOT a
    blanket re-deny that would break the agent reading its own secrets)."""
    wr = os.path.realpath(tempfile.mkdtemp(prefix="jail-ownenv-"))
    try:
        envp = os.path.join(wr, ".env")
        with open(envp, "w") as f:
            f.write("OWN_ENV_OK=yes")
        profile = sandbox.render_profile(
            {"WORKROOT": wr, "TMPDIR": os.path.join(wr, "tmp"), "CONFIG": os.path.join(wr, "config"),
             "HOME": os.path.expanduser("~"), "READ_DENY_ROOT": ""})
        r = _run_in_jail(profile, ["cat", envp])
        assert "OWN_ENV_OK=yes" in r.stdout, "the agent must still read its OWN workspace .env (re-deny over-scoped)"
    finally:
        shutil.rmtree(wr, ignore_errors=True)


def test_config_dir_is_readable_even_under_read_deny_root_but_token_still_denied():
    """CC MUST read its CLAUDE_CONFIG_DIR (state/settings). When CONFIG sits UNDER READ_DENY_ROOT (the
    fallback <runtime>/cc-config case), the cross-project read-deny would otherwise deny it -> CC can't
    boot. The CONFIG read re-allow fixes it; the FINAL token re-deny still closes the token. REAL sandbox."""
    rt = os.path.realpath(tempfile.mkdtemp(prefix="jail-cfgread-"))
    try:
        cfg = os.path.join(rt, "cc-config")   # CONFIG under READ_DENY_ROOT (= rt)
        wr = os.path.join(rt, "node")
        os.makedirs(cfg); os.makedirs(wr)
        with open(os.path.join(cfg, "settings.json"), "w") as f:
            f.write("CONFIG-SETTINGS-OK")
        with open(os.path.join(cfg, ".oauth_token"), "w") as f:
            f.write("TOKEN-LEAK-MARKER")
        profile = sandbox.render_profile(
            {"WORKROOT": wr, "TMPDIR": os.path.join(wr, "tmp"), "CONFIG": cfg,
             "HOME": os.path.expanduser("~"), "READ_DENY_ROOT": rt})
        r = _run_in_jail(profile, ["cat", os.path.join(cfg, "settings.json")])
        assert "CONFIG-SETTINGS-OK" in r.stdout, "CC must READ its CLAUDE_CONFIG_DIR even under READ_DENY_ROOT"
        t = _run_in_jail(profile, ["cat", os.path.join(cfg, ".oauth_token")])
        assert "TOKEN-LEAK-MARKER" not in t.stdout and t.returncode != 0, \
            "the token under CONFIG must stay DENIED (final re-deny is last-match-wins)"
    finally:
        shutil.rmtree(rt, ignore_errors=True)


@pytest.mark.skipif(False, reason="pure function")
def test_resolve_containment_produces_the_v1_floor_block():
    """resolve_containment (the production seam): WORKROOT = the node's own subtree under the runtime
    root; READ_DENY_ROOT = the whole runtime root (cross-node read-confidentiality floor)."""
    b = sandbox.resolve_containment("proj/widget#exec", runtime_root="/runtime", config_dir="/cfg", home="/home/u")
    assert b["WORKROOT"] == "/runtime/proj-widget-exec"
    assert b["READ_DENY_ROOT"] == "/runtime"  # deny all other nodes; WORKROOT re-allow re-opens own
    assert b["TMPDIR"] == "/runtime/proj-widget-exec/.tmp"
    assert b["CONFIG"] == "/cfg" and b["HOME"] == "/home/u"
