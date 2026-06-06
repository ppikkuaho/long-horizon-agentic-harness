"""sandbox — the SECURITY-JAIL seatbelt write/read jail (design/SECURITY.md §2.3/§2.4/§8.1).

The spawn chokepoint's containment leg. Spawned agents have auto-approved full tools and run
arbitrary code; this seatbelt is the STRUCTURAL blast-radius bound (§1.3), NOT the agent's
judgment. The jail bounds FILESYSTEM WRITES + SECRET READS — not capability (network + tools
stay open, §5).

THREE seams the SECURITY-JAIL increment owns:

  * ``render_profile(containment) -> str`` — render the §2.3 ``.sb`` profile text from a RESOLVED
    ``containment_profile`` block (§2.5a). EVERY path is realpath-canonicalized (§2.4 — the #1
    silent-hole guard: a logical ``/tmp/X`` deny LEAKS while the ``/private/tmp/X`` realpath deny
    BLOCKS, so canonicalize UNCONDITIONALLY). Deny-all-then-allow write jail; keychain mach-deny;
    broad secret read-deny named set + pattern globs; cross-project read-deny; and the LAST-MATCH
    WORKROOT read re-allow (so the agent reads its OWN .env without un-denying siblings').

  * ``wrap(pane_argv, profile_path) -> list[str]`` — build the ``sandbox-exec -f <profile-file>
    <pane…>`` invocation that wraps the env-i pane command (§7.1: the seatbelt prefix is part of
    the detached pane's launch command-line — ``sandbox-exec -f <profile>.sb env -i <…> <binary>``).
    The env-i clean-slate isolator stays the pane head; sandbox-exec wraps the OUTSIDE.

  * ``cache_redirect_env(workroot) -> dict`` — the §2.3 tool-cache redirection env (NPM_CONFIG_CACHE
    etc. pointed INTO WORKROOT) so a real ``npm install`` / ``go mod`` / ``cargo fetch`` writes its
    per-user cache inside the jail instead of hard-failing EPERM on its very first fetch (§1.4).

§2.4 CANONICALIZATION is load-bearing and applied to EVERY templated path here — WORKROOT, TMPDIR,
CONFIG, HOME, every secret-deny path, extra_read_denies, extra_write_roots, READ_DENY_ROOT — via
``os.path.realpath`` before substitution. The traps are ``/tmp`` (-> ``/private/tmp``) and ``/var``
(-> ``/private/var``); the rule is canonicalize unconditionally because a single un-canonicalized
secret path is a silent leak.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

# The real seatbelt binary (root-owned 0755 on macOS 26.4; the substrate Apple's App Sandbox and
# Codex CLI use). Resolved once at import; ``wrap`` prefixes this.
SANDBOX_EXEC = shutil.which("sandbox-exec") or "/usr/bin/sandbox-exec"


def _canon(path: str) -> str:
    """Realpath-canonicalize a single templated path (§2.4 — the #1 silent-hole guard).

    ``/tmp`` -> ``/private/tmp``, ``/var`` -> ``/private/var``. The seatbelt matches the RESOLVED
    REAL path, not the symlink path, so a logical-path rule silently leaks (a deny that never
    fires) or silently over-denies (a write-allow that never matches). Canonicalize UNCONDITIONALLY
    — never trust the caller to have done it (the ``_containment`` test hands LOGICAL paths on
    purpose to prove this seam owns the canonicalization).
    """
    return os.path.realpath(str(path))


# ---------------------------------------------------------------------------
# The §2.3 tool-cache redirection env — per-user caches pointed INTO WORKROOT.
# ---------------------------------------------------------------------------

def cache_redirect_env(workroot: str) -> dict[str, str]:
    """Return the §2.3 tool-cache redirection env (caches pointed INTO WORKROOT).

    Set at the chokepoint BEFORE launch so per-user package caches land INSIDE the jail instead of
    hard-failing EPERM. WITHOUT this a JS/Go/Rust/.NET build hard-fails on its VERY FIRST
    ``npm install`` / ``go mod`` / ``cargo`` fetch (VERIFIED §1.4); pip is the lucky cache-disabled
    exception but is redirected too for parity. The workroot is canonicalized so the env paths
    match the write-allow subpath the profile renders.
    """
    wr = _canon(workroot)
    return {
        "NPM_CONFIG_CACHE": f"{wr}/.cache/npm",
        "PIP_CACHE_DIR": f"{wr}/.cache/pip",
        "GOMODCACHE": f"{wr}/.cache/go",
        "GOCACHE": f"{wr}/.cache/gobuild",
        "CARGO_HOME": f"{wr}/.cargo",
        "YARN_CACHE_FOLDER": f"{wr}/.cache/yarn",
        "NUGET_PACKAGES": f"{wr}/.nuget",
    }


# ---------------------------------------------------------------------------
# resolve_containment — produce the §2.5a containment block from a node's real paths.
# This is the PRODUCTION SEAM the concrete spawn layer calls (the structural v1 chokepoint
# carries placeholder env, so it does not yet call this — see the OWED wiring note in the
# register: the real-boot / Phase-6 eval spawn resolves the real paths + calls this + attaches
# the block to the brief, which makes the adapter jail the pane).
# ---------------------------------------------------------------------------

def _node_workroot(node_address: str, runtime_root: str) -> str:
    """The node's WORKROOT — NESTED by path (``addressing.node_dir``), so a coordinator's WORKROOT is a
    PARENT dir of its children's WORKROOTs and `(allow file-write* (subpath WORKROOT))` covers the whole
    subtree it may seed (ARCHITECTURE.md:122 'creates child workspaces within it'). The `#seat` is not a
    path segment (it would break that nesting); seats share the node workspace."""
    from harnessd import addressing
    return str(addressing.node_dir(node_address, runtime_root))


def resolve_containment(node_address: str, *, runtime_root: str, config_dir: str,
                        home: str | None = None, extra_read_denies=None, extra_write_roots=None) -> dict:
    """Resolve the §2.5a containment block for a node from its REAL paths (the v1 floor).

    WORKROOT = the node's own workspace subtree under the /runtime/ jail root; TMPDIR a per-node
    scratch under it; CONFIG the pinned config dir (CC's own state writes); HOME the user home (the
    secret-deny anchor); READ_DENY_ROOT = the whole /runtime/ root, so EVERY other node's subtree is
    read-denied while the WORKROOT re-allow (render_profile, last-match-wins) re-opens ONLY this
    node's own — the cross-project read-confidentiality floor (WORKSPACE-SCHEMA read graph; sibling
    published-contract + parent-chain reads are a deferred extra_read refinement). All paths are
    realpath-canonicalized by ``render_profile`` (§2.4); logical paths are fine to hand in here.
    """
    workroot = _node_workroot(node_address, str(runtime_root))
    return {
        "WORKROOT": workroot,
        "TMPDIR": os.path.join(workroot, ".tmp"),
        "CONFIG": str(config_dir),
        "HOME": str(home or os.path.expanduser("~")),
        "READ_DENY_ROOT": str(runtime_root),
        "extra_read_denies": list(extra_read_denies or []),
        "extra_write_roots": list(extra_write_roots or []),
    }


# ---------------------------------------------------------------------------
# render_profile — the §2.3 .sb structure, every path realpath-canonicalized (§2.4).
# ---------------------------------------------------------------------------

# The §2.3 home-tree credential-store SUBPATH set (well beyond the old four dirs — the broad set
# the escape-path review found readable). Rendered as `(subpath "<HOME>/<rel>")` denies.
_SECRET_SUBPATH_RELS = (
    ".ssh",                 # NOTE: blocks known_hosts -> SSH-based dep fetch breaks by default (§1.4 / §2.3 option a)
    ".aws",                 # NOTE: blocks ~/.aws/config (non-secret region/profile) too — named limitation (§1.4)
    ".gnupg",
    "Library/Keychains",
    ".config/gh",
    ".config/gcloud",
    ".kube",
    ".docker",
    ".codex",
    ".gemini",
)

# The §2.3 home-tree credential-store LITERAL set (single-file credential stores + histories).
_SECRET_LITERAL_RELS = (
    ".netrc",
    ".npmrc",
    ".pypirc",
    ".git-credentials",
    ".claude.json",
    ".claude/.credentials.json",
    ".zsh_history",
    ".bash_history",
)


def render_profile(containment: dict) -> str:
    """Render the §2.3 seatbelt ``.sb`` profile from a RESOLVED containment block (§2.5a).

    The containment block (§2.5a shape) carries the path-derived roots + resolved knob values:
    ``WORKROOT``, ``TMPDIR``, ``CONFIG``, ``HOME``, ``READ_DENY_ROOT``, ``extra_read_denies``,
    ``extra_write_roots``. EVERY path is realpath-canonicalized (§2.4) before substitution.

    The clause ORDER is load-bearing (seatbelt is last-match-wins; deny-all-then-allow for writes):
      1. ``(version 1)`` + ``(allow default)``     — network + system-lib + /etc reads open (§2.3)
      2. WRITE JAIL: ``(deny file-write*)`` THEN the allow-list (deny-all-then-allow)
      3. KEYCHAIN: ``(deny mach-lookup …)``         — the real keychain control (securityd is mach,
         not file IO; the file-read deny is irrelevant — §2.3 / §3.3)
      4. READ DENY: the broad secret named set (subpaths + literals) + extra_read_denies
      5. READ DENY: cross-project source (READ_DENY_ROOT), if given
      6. READ DENY: secret-pattern globs anywhere (**/.env, credentials/secrets, *.pem)
      7. ``(allow file-read* (subpath WORKROOT))`` — the LAST-MATCH re-allow that un-denies the
         agent's OWN .env/.pem WITHOUT un-denying siblings' (must be the LAST read rule).
    """
    workroot = _canon(containment["WORKROOT"])
    tmpdir = _canon(containment["TMPDIR"])
    config_dir = _canon(containment["CONFIG"])
    home = _canon(containment["HOME"])
    read_deny_root = containment.get("READ_DENY_ROOT") or ""
    extra_read_denies = list(containment.get("extra_read_denies") or [])
    extra_write_roots = list(containment.get("extra_write_roots") or [])

    lines: list[str] = []
    lines.append("(version 1)")
    lines.append("(allow default)                          ; network + system-lib + /etc reads open by default")
    lines.append("")

    # --- WRITE JAIL (verified strong; deny-all-then-allow-list) ---
    lines.append(";; --- WRITE JAIL (verified strong; deny-all-then-allow-list) ---")
    lines.append("(deny file-write*)")
    lines.append("(allow file-write*")
    lines.append(f'  (subpath "{workroot}")                 ; node workspace, realpath-canonicalized')
    lines.append(f'  (subpath "{tmpdir}")                   ; per-session CLAUDE_CODE_TMPDIR')
    lines.append(f'  (subpath "{config_dir}")               ; CLAUDE_CONFIG_DIR — CC lock/state writes')
    lines.append(f'  (subpath "{_canon(os.path.join(home, ".claude"))}")  ; CC session logs/history (§8.1 gate 1)')
    # Additive extra write roots (§2.5a write_roots — additive only), each canonicalized (§2.4).
    for extra in extra_write_roots:
        lines.append(f'  (subpath "{_canon(extra)}")')
    lines.append('  (literal "/dev/null") (literal "/dev/stdout") (literal "/dev/stderr")')
    lines.append('  (regex #"^/dev/tty"))')
    lines.append(";; Dep-cache writes are kept INSIDE WORKROOT by env redirection (cache_redirect_env).")
    lines.append("")

    # --- KEYCHAIN: mach-service deny (the file-read deny does NOT protect it — securityd is mach) ---
    lines.append(";; --- KEYCHAIN: mach-service deny (securityd is a mach service, not file IO) ---")
    lines.append("(deny mach-lookup")
    lines.append('  (global-name "com.apple.SecurityServer")')
    lines.append('  (global-name "com.apple.securityd"))')
    lines.append("")

    # --- READ DENY: secrets (broad named set) ---
    lines.append(";; --- READ DENY: secrets (broad named set — the credential stores the review found readable) ---")
    lines.append("(deny file-read*")
    for rel in _SECRET_SUBPATH_RELS:
        lines.append(f'  (subpath "{home}/{rel}")')
    for rel in _SECRET_LITERAL_RELS:
        lines.append(f'  (literal "{home}/{rel}")')
    # The relocated/denied OAuth token literal (§3 — single-file deny even though config/ is writable).
    lines.append(f'  (literal "{config_dir}/.oauth_token")')
    # <EXTRA_READ_DENIES> — additional secret paths, each realpath-canonicalized (§2.4).
    for deny in extra_read_denies:
        lines.append(f'  (subpath "{_canon(deny)}")')
    lines.append("  )")
    lines.append("")

    # --- READ DENY: cross-project source (the WORKSPACE-SCHEMA read graph for L2–L5) ---
    if read_deny_root:
        lines.append(";; --- READ DENY: cross-project source (cousins / other projects, per address) ---")
        lines.append(f'(deny file-read* (subpath "{_canon(read_deny_root)}"))')
        lines.append("")

    # --- READ DENY: secret-pattern files anywhere (the sibling-.env guarantee, §1.3) ---
    lines.append(";; --- READ DENY: secret-pattern files anywhere (the sibling-.env guarantee, §1.3) ---")
    lines.append("(deny file-read*")
    lines.append(r'  (regex #"/\.env($|\.)")               ; **/.env, **/.env.*')
    lines.append(r'  (regex #"/(credentials|secrets)[^/]*$")')
    lines.append(r'  (regex #"\.pem$"))')
    # ...then re-allow the agent's OWN workspace secret-pattern files (last-match-wins). This MUST be
    # the LAST read rule so it scopes the secret-pattern deny to "outside WORKROOT" WITHOUT
    # un-denying siblings' .env (§2.3).
    lines.append(f'(allow file-read* (subpath "{workroot}"))')
    # CC MUST be able to READ its own CLAUDE_CONFIG_DIR (state/lock/settings). With (allow default) this
    # is already open when CONFIG is OUTSIDE READ_DENY_ROOT (the real harness: .cc-pinned/config). But a
    # CONFIG placed UNDER READ_DENY_ROOT (= the runtime root) would otherwise be read-DENIED by the
    # cross-project deny -> CC fails to boot. Re-allow CONFIG reads here (BEFORE the final token re-deny,
    # so the token under CONFIG stays closed). Defensive — makes CONFIG-anywhere boot correctly.
    lines.append(f'(allow file-read* (subpath "{config_dir}"))')
    lines.append("")

    # --- FINAL: the OAuth token is NEVER agent-readable/writable, even if CONFIG sits under WORKROOT ---
    # The WORKROOT re-allow above is last-match-wins; if CONFIG is inside WORKROOT it would otherwise
    # UN-DENY the token literal (a latent read hole — blocker). Re-deny the token LAST (read AND write,
    # §3.2: a writable CONFIG must not let the agent rewrite the token either) so it is unconditionally
    # closed regardless of CONFIG's position. In the harness CONFIG (.cc-pinned/config) is NOT under a
    # node WORKROOT, so this is defense-in-depth — but it must hold even if that ever changes.
    lines.append(";; --- FINAL: OAuth token never agent-readable/writable (last-match-wins re-deny) ---")
    lines.append(f'(deny file-read* (literal "{config_dir}/.oauth_token"))')
    lines.append(f'(deny file-write* (literal "{config_dir}/.oauth_token"))')
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# wrap — the sandbox-exec invocation that wraps the env-i pane command (§7.1).
# ---------------------------------------------------------------------------

def wrap(pane_argv: list[str], profile_path: str) -> list[str]:
    """Build ``sandbox-exec -f <profile-file> <pane…>`` — the vector the tmux pane actually runs.

    The seatbelt prefix is the OUTSIDE of the detached pane's launch command-line (§7.1):
    ``sandbox-exec -f <profile>.sb env -i <K=V…> <binary> <flags>``. The from-empty ``env -i``
    clean-slate isolator stays the pane HEAD verbatim (sandbox-exec wraps it, does NOT replace it),
    so the Increment-9 OAuth-only isolation invariant still holds inside the jail. The pane vector
    is appended as a CONTIGUOUS, UNCHANGED tail — no re-quote round-trip that could re-expand a
    value (the tmux ``new-session`` argv-token contract).
    """
    return [SANDBOX_EXEC, "-f", str(profile_path), *list(pane_argv)]
