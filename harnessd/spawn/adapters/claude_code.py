"""claude_code — the concrete Claude-Code RuntimeAdapter (IMPLEMENTATION-PLAN §2.11; DAEMON §6.2).

The FROZEN H40 boot recipe (the ONE Claude-Code spawn the whole harness uses):

  argv = [CC, "--system-prompt-file", system_prompt_file]
      where ``system_prompt_file`` is the CONSTANT shared ``operational/shared/system-prompt.md``
      (``config.SYSTEM_PROMPT_FILE``) — the ONE shared minimal prompt, BYTE-IDENTICAL L1–L5. The
      per-seat role is NEVER in argv: it arrives as the brief's load-manifest (role-as-documents),
      which the agent READS in place. argv NEVER carries ``--bare`` (forces API-key auth, breaks
      the OAuth token), ``--append-system-prompt`` (keeps the full base framing), or
      ``--agents``/``--agent`` (does not inject the persona) — the H40 foot-guns.

  env  = exactly the 4 isolation vars {CLAUDE_CONFIG_DIR, CLAUDE_CODE_OAUTH_TOKEN,
         CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC, DISABLE_AUTOUPDATER}. No raw API key.

  session = addressing.session_name_for(address)  ('harness-' + the address with '/', '#',
      ':', '.' all folded to '-' — F18: a name tmux 3.6a will NOT silently rename). The RECORDED
      tmux_target is the canonical '<session>:<window>.<pane>' triple create_detached RETURNS
      (tmux's own post-rename report) so reconcile/pane_alive match tmux<->ledger byte-for-byte.

  The pane handed to ``tmux.create_detached`` is the from-empty isolator ``env -i <K=V…> <argv…>``
  (``tmux.build_pane_argv`` — the SAME seam the wrapper uses), and the OAuth-only gate
  (``oauth_guard.assert_oauth_only(env, argv, pane_argv, tmux.server_env())``) fires BEFORE
  ``create_detached`` so NO actor opens on a forbidden env (E32 ordering). The Claude-specific
  POSITIVE token check (``check_credential_health``) runs in this path (NOT the shared gate).

Recorded facts (config = INTENT, model_used = FACT): model_used = "<model> / <runtime>" DERIVED
from the level_config (LT-8 — never a constant that can contradict the config; the deferred F17
configured-vs-actual fact-checker can only reconcile intent that is real), role_variant,
system_prompt_file (the shared constant) + its content hash, session_uuid, and the derived
transcript_path (a ``<session-uuid>.jsonl`` file the detector stats).

BUILDER DECISIONS for the §2.11 details the plan leaves open (stated in the build report):

  * verify_binary — verifies the pinned VERSION against ``config.PINNED_BINARY_VERSION`` without
    a subprocess (the dry-run forbids any real exec, and ``config.PINNED_BINARY_HASH`` is a v1
    placeholder = None, so a real ``claude --version`` / sha256 probe is the documented seam
    DEFERRED to commissioning — FORK-VERIFY). It is a pure, no-exec confirmation in v1.
  * deterministic first-boot trust — NOT a send-keys race against the trust dialog; it is the
    pre-seeded clean ``CLAUDE_CONFIG_DIR`` (.cc-pinned/config, pre-trusted, non-interactive) the
    env already points at. v1 carries this as a no-op marker (the config dir IS the mechanism).
  * transcript_path derivation — ``<CLAUDE_CONFIG_DIR>/projects/<encoded-cwd>/<uuid>.jsonl``:
    Claude Code files transcripts under ``<config>/projects/<encoded-cwd>/<session-uuid>.jsonl``,
    where <encoded-cwd> is the pane's REALPATH cwd with every non-[A-Za-z0-9-] char folded to '-'.
    The uuid is OURS: argv carries ``--session-id <uuid>`` so CC writes the EXACT file we record
    (first-live-run finding 2026-06-11: a session-NAME-derived segment + an un-pinned uuid pointed
    the detector at a file CC never writes; verify-new-turn read size-0 forever and the idle
    ladder failed a healthy waiting L1 with watchdog_nonresponse).
  * CC binary path — the pinned ``.cc-pinned/node_modules/@anthropic-ai/claude-code/bin/claude.exe``
    resolved relative to HARNESS_ROOT. Never execed in the dry-run (the no_real_exec spy proves it).
"""

from __future__ import annotations

import hashlib
import os
import re
import uuid
from pathlib import Path

from harnessd import addressing, config
from harnessd.spawn import oauth_guard, sandbox, cc_config

from .base import RuntimeAdapter, SpawnResult


# The pinned Claude binary, relative to HARNESS_ROOT (PINNED-CC.md). A path constant, never
# flattened with role text; never execed in the dry-run (mock tmux + the no_real_exec spy).
_PINNED_CC = ".cc-pinned/node_modules/@anthropic-ai/claude-code/bin/claude.exe"

# The exact 4-var isolation set the env MUST equal (DAEMON §6.2). Defined here so a missing/extra
# var fails the assembly loudly rather than silently spawning a widened env.
_ISOLATION_ENV_KEYS = frozenset(
    {
        "CLAUDE_CONFIG_DIR",
        "CLAUDE_CODE_OAUTH_TOKEN",
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC",
        "DISABLE_AUTOUPDATER",
    }
)

# The legacy recorded-intent FALLBACK — used only when a level_config lacks model/runtime seats
# (a sparse test fake). The real record derives from the level_config (LT-8, _model_used below).
_MODEL_USED = "opus-4.8 / claude-code"


def _model_used(level_config) -> str:
    """The recorded INTENT, derived from the CONFIG (LT-8): ``"<model> / <runtime>"``.

    The old constant recorded 'opus-4.8 / claude-code' regardless of level_config — so an L5
    configured gpt-5.5/codex but driven through THIS adapter recorded an intent that contradicted
    its own config (and the actual unflagged-CC default), a three-way divergence the deferred F17
    fact-checker could not even reconstruct. Intent now comes from the config; the
    configured-vs-ACTUAL check remains F17 territory.
    """
    model = getattr(level_config, "model", None)
    runtime = getattr(level_config, "runtime", None)
    if model and runtime:
        return f"{model} / {runtime}"
    return _MODEL_USED


def _harness_root() -> Path:
    """Resolve HARNESS_ROOT — the repo root the relative config/pinned paths join against.

    The daemon is launchd-managed with a CWD that is NOT guaranteed to be the repo root
    (config.py NOTE), so paths are joined against the resolved root, never passed raw to a
    launchd-CWD process. This module lives at ``<root>/harnessd/spawn/adapters/claude_code.py``,
    so the root is three parents up.
    """
    return Path(__file__).resolve().parents[3]


def _system_prompt_hash() -> str:
    """sha256 of the SHARED system-prompt file content (the system_prompt_file_hash fact).

    Reads the constant ``config.SYSTEM_PROMPT_FILE`` under HARNESS_ROOT. If the file is not on
    disk (a CI without the operational tree), fall back to hashing the PATH string so the
    recorded hash is still a non-empty deterministic value (it pins WHICH prompt, and the real
    content hash lands wherever the file is present — never an empty/None hash).
    """
    spf = config.SYSTEM_PROMPT_FILE
    path = _harness_root() / spf
    try:
        data = path.read_bytes()
    except OSError:
        data = spf.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _transcript_path(env: dict, cwd: str | None, session_uuid: str) -> str:
    """Derive ``<CLAUDE_CONFIG_DIR>/projects/<encoded-cwd>/<session_uuid>.jsonl``.

    Claude Code files transcripts by the pane's REALPATH cwd — every char outside [A-Za-z0-9-]
    folded to '-' (probed on pinned 2.1.152: '/', '.', '_' all fold; case preserved; the leading
    '/' yields the leading '-'; macOS /var/... realpaths to /private/var/...). The session_uuid
    must be pinned into CC's argv via ``--session-id`` by the caller — only then is this path the
    file CC actually writes. The detector/watchdog stat this path for verify-new-turn; a wrong
    path here reads size-0 forever and the idle ladder kills healthy agents (2026-06-11 live run).
    A None cwd means the pane inherits the daemon's cwd (no ``-c``), so encode that.
    """
    config_dir = env.get("CLAUDE_CONFIG_DIR", "")
    real = os.path.realpath(cwd) if cwd else os.path.realpath(os.getcwd())
    project_seg = re.sub(r"[^A-Za-z0-9-]", "-", real)
    return str(Path(config_dir) / "projects" / project_seg / f"{session_uuid}.jsonl")


def _brief_get(brief, key, default=None):
    """Read a brief field TOLERANTLY — works for a dict brief AND a NeutralContract dataclass.

    THE BRIEF-SHAPE BUG (JAIL-WIRING): ``brief.assemble_neutral`` returns a ``NeutralContract``
    DATACLASS (no ``.get``), but the production chokepoint hands that dataclass straight to the
    adapter. The old ``(neutral_brief or {}).get(...)`` reads raised ``AttributeError`` on the
    dataclass (the existing adapter tests passed only because they handed a DICT brief). This helper
    does ``dict.get`` for a mapping and ``getattr`` for the dataclass, so BOTH shapes read the same
    fields (``role_variant`` / ``containment_profile``). A None brief yields the default.
    """
    if brief is None:
        return default
    if isinstance(brief, dict):
        return brief.get(key, default)
    return getattr(brief, key, default)


def _resolve_containment(neutral_brief, level_config) -> dict | None:
    """Resolve the §2.5a ``containment_profile`` block, or None for the unjailed (dry-run) path.

    SECURITY.md §7 wires the write-jail at the DAEMON §6.2 pane-launch command. The chokepoint
    resolves the containment block (machine baseline -> per-spawn override -> resolved block,
    §2.5a/§2.5b) and rides it on the brief / level_config. When NO block is present (the pure
    dry-run argv/env assembly that the Increment-9 adapter tests exercise), the pane is the bare
    ``env -i`` isolator — UNJAILED — so the dry-run boundary stays a deterministic, sandbox-free
    assembly. When a block IS present, ``pin_and_open`` renders the §2.3 profile and wraps the
    pane with ``sandbox-exec`` (§7.1).

    The block is read from ``neutral_brief['containment_profile']`` first (the per-spawn override
    the chokepoint flattens onto the brief), then ``level_config.containment_profile``. It must
    already be RESOLVED to the §2.5a shape — WORKROOT/TMPDIR/CONFIG/HOME (+ optional
    READ_DENY_ROOT / extra_read_denies / extra_write_roots). ``sandbox.render_profile`` owns the
    §2.4 realpath-canonicalization; the chokepoint hands it logical paths.
    """
    block = _brief_get(neutral_brief, "containment_profile")
    if block is None:
        block = getattr(level_config, "containment_profile", None)
    if not block:
        return None
    return dict(block)


class ClaudeCodeAdapter(RuntimeAdapter):
    """The concrete Claude-Code adapter (the H40 boot recipe; OAuth-only by construction)."""

    def __init__(self, tmux=None):
        # The tmux transport seam. Production wires ``harnessd.spawn.tmux``; the dry-run wires a
        # mock that records create_detached without a real exec. Attribute-injectable too.
        if tmux is None:
            from harnessd.spawn import tmux as _tmux

            tmux = _tmux
        self.tmux = tmux

    # ---- the §2.11 pieces, each a single seam ----------------------------------------------

    def verify_binary(self, level_config=None) -> None:
        """Confirm the configured model+runtime is pinned BEFORE the child runs (E32).

        Pure, NO-exec in v1: confirms ``config.PINNED_BINARY_VERSION`` is set (the pin is the
        npm version + isolated prefix, PINNED-CC). ``config.PINNED_BINARY_HASH`` is a v1
        placeholder (None) so the sha256 probe is DEFERRED (FORK-VERIFY) — the dry-run forbids a
        real ``claude --version`` exec. Raises if the pinned version seat is missing.
        """
        if not config.PINNED_BINARY_VERSION:
            raise oauth_guard.SpawnFailure(
                "pinned Claude binary version is not configured (config.PINNED_BINARY_VERSION) — "
                "the pinned-binary seat must exist before a spawn (E32)"
            )
        # config.PINNED_BINARY_HASH is None in v1 (gitignored install): the sha256 verification is
        # the documented commissioning seam, not skippable silence — see FORK-VERIFY in the docstring.

    def _deterministic_trust(self, env: dict, containment=None, cwd=None) -> None:
        """Deterministic first-boot trust — pre-seed CLAUDE_CONFIG_DIR so NO startup dialog /
        permission prompt appears, NOT a send-keys race (SECURITY.md §deterministic-trust).

        A real interactive spawn hits BLOCKING dialogs (workspace trust, the bypass-permissions
        warning, per-tool prompts) that would FREEZE an unattended agent. ``cc_config.seed_trust``
        writes the acceptance keys for the agent's WORKSPACE into ``.claude.json``/``settings.json``
        BEFORE launch, so the agent boots straight to working. Verified live: a fresh workspace
        pre-seeded this way shows zero dialogs.

        Seeded for the ACTUAL pane cwd on EVERY spawn (the transport increment) — jailed (the
        WORKROOT) AND unjailed (the node-workspace cwd the pane now boots in, F18 ``-c``): an
        untrusted cwd freezes an UNJAILED agent on the trust dialog exactly the same way.
        ``seed_trust`` itself skips cleanly when CLAUDE_CONFIG_DIR is not a real on-disk dir
        (the dry-run placeholder), so the pure-assembly tests stay side-effect-free.
        """
        config_dir = env.get("CLAUDE_CONFIG_DIR")
        workroot = (containment or {}).get("WORKROOT") or cwd
        if config_dir and workroot:
            cc_config.seed_trust(config_dir, workroot)
        return None

    def _write_profile(self, env, containment, session_name, profile_text) -> str:
        """Write the rendered ``.sb`` to a stable per-session path the seatbelt reads, return it.

        The profile file lives under the jail's writable CONFIG dir (CLAUDE_CONFIG_DIR — a §2.3
        write-allow root, realpath-canonicalized) so sandbox-exec can read it AND the spawning
        daemon may rewrite it on resume/necro (the same jail is re-applied — §7). Falls back to
        the containment CONFIG/TMPDIR when CLAUDE_CONFIG_DIR is not a real on-disk path (e.g. the
        ``$HARNESS/...`` placeholder the dry-run carries). The filename is keyed to the collapsed
        session so concurrent spawns never collide.
        """
        config_dir = env.get("CLAUDE_CONFIG_DIR", "")
        base = config_dir if os.path.isdir(config_dir) else (
            containment.get("CONFIG") or containment.get("TMPDIR") or containment.get("WORKROOT")
        )
        prof_dir = Path(base) / ".sandbox-profiles"
        prof_dir.mkdir(parents=True, exist_ok=True)
        safe = session_name.replace("/", "-").replace(":", "-")
        pf = prof_dir / f"{safe}.sb"
        pf.write_text(profile_text)
        return str(pf)

    def pin_and_open(self, neutral_brief, level_config, tmux_target, env) -> SpawnResult:
        """Pin, OAuth-gate, open the from-empty pane, record the facts (the H40 recipe)."""
        env = dict(env)  # never mutate the caller's dict

        # role_variant rides the brief / level_config (role-as-documents), NEVER the argv. Read the
        # brief field TOLERANTLY (dict brief OR NeutralContract dataclass) — the brief-shape bug fix.
        role_variant = (
            _brief_get(neutral_brief, "role_variant")
            or getattr(level_config, "role_variant", None)
            or getattr(level_config, "level", None)
        )

        # (1) Pin the binary (model+runtime) before anything child-facing runs (E32).
        self.verify_binary(level_config)

        # (1a) Resolve the §2.5a containment block FIRST — it decides both the jail AND the
        #      permission posture: --dangerously-skip-permissions is added ONLY for a jailed spawn
        #      (the safety invariant — auto-approve is safe ONLY because the seatbelt jail is the
        #      structural bound, SECURITY.md constraint 4; an UNJAILED dry-run never auto-approves)
        #      …with ONE explicit exception: the USER-APPROVED supervised-smoke override
        #      (level_config.unjailed_skip_permissions — see the loud branch at (2)).
        containment = _resolve_containment(neutral_brief, level_config)

        # (2) Assemble argv: the SHARED system-prompt, identical L1..L5 — the per-level role is
        #     NEVER in argv. No --bare/--append-system-prompt/--agents/--agent. When jailed, add
        #     --dangerously-skip-permissions so the unattended agent auto-approves its own tool calls
        #     (the jail bounds the blast radius; every permission prompt is superfluous and would only
        #     FREEZE the agent with no human at the pane — SECURITY.md §362).
        #
        #     The --system-prompt-file value is ABSOLUTE (resolved against HARNESS_ROOT — the
        #     config.py NOTE's resolution contract): the pane now boots in the NODE's workspace
        #     (cwd below), so a repo-relative path would dangle. The recorded
        #     SpawnResult.system_prompt_file stays the canonical config CONSTANT (intent).
        #
        #     --model is derived from level_config.model via config.CC_MODEL_FLAGS (probed live:
        #     the pinned CC defaults to Sonnet without it — the recorded "opus-4.8" was a lie).
        #     An unmapped model adds NO flag (explicit mapping, never a guessed id); model_used
        #     below remains the recorded INTENT (the E32 fact-checker is deferred F17 territory).
        cc = str(_harness_root() / _PINNED_CC)
        argv = [cc, "--system-prompt-file", str(_harness_root() / config.SYSTEM_PROMPT_FILE)]
        cc_model = config.CC_MODEL_FLAGS.get(getattr(level_config, "model", None))
        if cc_model:
            argv += ["--model", cc_model]
        # --session-id pins CC's session uuid to OURS, so the recorded transcript_path is the
        # file CC actually writes (verify-new-turn's stat target). Without the pin CC mints its
        # own uuid and the detector watches a file that never exists (2026-06-11 live-run
        # finding: the idle ladder failed a healthy L1 as watchdog_nonresponse). Minted fresh
        # per spawn attempt — never reused across incarnations (CC refuses a duplicate id).
        session_uuid = str(uuid.uuid4())
        argv += ["--session-id", session_uuid]
        if containment is not None:
            argv.append("--dangerously-skip-permissions")
            permission_posture = "jailed-skip-permissions"
        elif getattr(level_config, "unjailed_skip_permissions", False):
            # SUPERVISED-SMOKE OVERRIDE (USER-APPROVED, 2026-06-10) — the LOUD, EXPLICIT
            # decoupling of SECURITY.md constraint 4 ("skip-permissions INSIDE the jail …
            # containment bounds the blast radius"). The user's decision for the first
            # supervised live run: "Unjailed + dangerously skip permissions. It is a small
            # run, the risk of something catastrophic happening is minimal." The knob is
            # NEVER read from the environment here — it rides ONLY level_config (stamped by
            # commissioning.build_runtime / config.get_level_config from the strict
            # HARNESS_UNJAILED_SKIP_PERMISSIONS=1 opt-in) and NEVER the brief (§2.5b: a
            # per-spawn brief may TIGHTEN, never RELAX — an injected brief cannot
            # self-escalate to auto-approve). Journaled below as
            # permission_posture="unjailed-skip-permissions-override" (SECURITY.md §4.3).
            # RETIREMENT: the jail tier (REMEDIATION F9–F13) retires this branch.
            argv.append("--dangerously-skip-permissions")
            permission_posture = "unjailed-skip-permissions-override"
        else:
            permission_posture = "unjailed-prompting"

        # (3) The from-empty pane (the SAME isolator seam the wrapper uses). The adapter builds
        #     the EXACT pane it hands to create_detached so the guard checks the real pane vector;
        #     create_detached is wrapping-idempotent (it will not re-wrap an `env -i`-led argv).
        pane_argv = self.tmux.build_pane_argv(env, argv)

        # (4) OAuth-only gate BEFORE create_detached: the runtime-AGNOSTIC negative invariant +
        #     the pane-env-isolation guard, checking the env the PANE WILL ACTUALLY SEE
        #     (tmux.server_env()). A forbidden env raises ApiKeyForbidden here -> NO actor opens.
        oauth_guard.assert_oauth_only(env, argv, pane_argv, self.tmux.server_env())

        # (5) The CLAUDE-SPECIFIC positive token check (DISTINCT AuthExpired; refresh-the-token,
        #     not a model outage). Lives in this path, NOT the shared gate.
        oauth_guard.check_credential_health(env)

        # (6) The §2.5a containment block was resolved at (1a). When present, the pane is JAILED
        #     (§2.3 profile + sandbox-exec wrap, §7.1) and its env legitimately carries the §2.3
        #     containment vars (CLAUDE_CODE_TMPDIR/HOME + the cache-redirection set) ON TOP of the 4
        #     isolation vars. When absent (the dry-run boundary), the pane is the bare `env -i`
        #     isolator and the env MUST be EXACTLY the 4 isolation vars.

        # (6a) ENFORCE the OAuth-only isolation floor. UNJAILED: the env must be the 4 isolation
        #      vars + (LR-2, user posture decision 2026-06-11: allowlist->denylist for the PoC
        #      phase) the named NON-CREDENTIAL extras below — PATH (agent subshells failed to
        #      find python3/head every turn; zero security value in omitting it) and TERM. Any
        #      OTHER extra still refuses (the credential-leak surface stays closed).
        #      JAILED: the 4 isolation vars are the REQUIRED floor; the extra vars are the named
        #      §2.3 containment set (no raw API key — already rejected by the OAuth gate above).
        #      Runs AFTER the OAuth gate + credential check (so api-key -> ApiKeyForbidden and a
        #      missing token -> AuthExpired keep their SPECIFIC classes) but BEFORE create_detached.
        if containment is None:
            allowed_extras = {"PATH", "TERM"}  # LR-2: non-credential ergonomics, never a secret
            extra = set(env) - _ISOLATION_ENV_KEYS - allowed_extras
            missing = _ISOLATION_ENV_KEYS - set(env)
            if extra or missing:
                raise oauth_guard.SpawnFailure(
                    "pane env must be the 4 isolation vars (+ optionally PATH/TERM — LR-2) "
                    f"(DAEMON §6.2 amended); refusing a widened/incomplete env. "
                    f"extra={sorted(extra)} missing={sorted(missing)}"
                )
        else:
            missing = _ISOLATION_ENV_KEYS - set(env)
            if missing:
                raise oauth_guard.SpawnFailure(
                    "jailed pane env must carry the 4 isolation vars (DAEMON §6.2) as its floor; "
                    f"missing={sorted(missing)}"
                )

        # (6b) Resolve the PANE CWD: the node's workspace (the brief's ``workspace`` pointer — the
        #      nested addressing.node_dir the chokepoint registered). The agent boots WHERE its
        #      brief lands, so the kickoff pointer's relative reads (brief.md, .inbox.<seat>.jsonl)
        #      agree with the pane cwd. Ensured on disk (a `-c` into a missing dir fails the
        #      new-session). Absent workspace (the bare adapter-level dry-run) -> no cwd, the pane
        #      inherits the server default exactly as before.
        cwd = _brief_get(neutral_brief, "workspace")
        if cwd:
            cwd = str(cwd)
            try:
                Path(cwd).mkdir(parents=True, exist_ok=True)
            except OSError:
                pass  # an un-creatable workspace surfaces at create_detached, loudly
            # REALPATH-canonicalize (probed live): CC keys its trust map by the REALPATH the
            # session opens (e.g. macOS /var/... -> /private/var/...). A symlinked cwd seeded
            # under the logical path MISSES the trust lookup and the agent freezes on the
            # trust dialog — so the cwd handed to seed_trust AND to tmux -c is the realpath.
            cwd = os.path.realpath(cwd)

        # (7) Deterministic first-boot trust (pre-seeded config dir; no send-keys race) — KILLS every
        #     startup dialog/permission prompt for the agent's workspace (trust dialog + bypass warning
        #     + per-tool prompts) so an unattended agent boots straight to working, never frozen on a
        #     dialog (SECURITY.md §deterministic-trust; the jail is the bound, prompts are superfluous).
        #     Seeded for the ACTUAL pane cwd on EVERY spawn — unjailed included (the trust dialog
        #     freezes an unjailed agent just the same).
        self._deterministic_trust(env, containment, cwd)

        # (8) Render the §2.3 seatbelt profile and wrap the env-i pane with sandbox-exec (§7.1) when
        #     a containment block is resolved. The wrapped vector — `sandbox-exec -f <profile>.sb
        #     env -i <K=V…> <binary> <flags>` — IS the detached pane's launch command. The §2.4
        #     canonicalization + the cache-redirection env are owned by the sandbox seam. create_-
        #     detached is wrapping-idempotent for the bare-`env -i` head; the sandbox-wrapped vector
        #     (head = sandbox-exec) is passed through verbatim.
        session_name = addressing.session_name_for(tmux_target)
        launch_argv = pane_argv
        if containment is not None:
            profile_text = sandbox.render_profile(containment)
            profile_path = self._write_profile(env, containment, session_name, profile_text)
            launch_argv = sandbox.wrap(pane_argv, profile_path)

        # (9) Open the detached actor with the pane vector (wrapped when jailed, bare env -i when not),
        #     booting in the node workspace when one is contracted (-c cwd). create_detached returns
        #     the CANONICAL live target '<session>:<window>.<pane>' (tmux's own post-rename report,
        #     F18/OSA-01) — THAT is the recorded tmux_target, never the requested name (which tmux
        #     may rewrite) and never a guessed ':0.0' suffix (base-index may differ).
        if cwd:
            canonical_target = self.tmux.create_detached(session_name, launch_argv, env, cwd=cwd)
        else:
            canonical_target = self.tmux.create_detached(session_name, launch_argv, env)

        # (8) Record the facts (config = intent, model_used = fact). session_uuid was minted at
        #     argv assembly (--session-id pins it into CC); the transcript path is the encoded
        #     REALPATH-cwd file CC will write under that uuid.
        transcript_path = _transcript_path(env, cwd, session_uuid)

        return SpawnResult(
            ok=True,
            session_uuid=session_uuid,
            model_used=_model_used(level_config),
            role_variant=role_variant,
            system_prompt_file=config.SYSTEM_PROMPT_FILE,
            system_prompt_file_hash=_system_prompt_hash(),
            tmux_target=canonical_target,
            transcript_path=transcript_path,
            failure_class=None,
            argv=tuple(argv),
            env=dict(env),
            permission_posture=permission_posture,
        )
