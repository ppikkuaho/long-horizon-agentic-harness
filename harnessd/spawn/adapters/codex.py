"""codex — the REAL Codex-runtime adapter (E4 / DEFERRED-REGISTER O1, retires the fail-loud
stub): GPT-5.5 on the Codex harness at L5, per runtime-and-model-map E32.

Probed LIVE against codex-cli 0.128.0 + the ChatGPT account (2026-06-11, preference 2 — real
over dummy; every mechanism below is a probe result, not an assumption):

  * CODEX_HOME redirects ~/.codex fully; a copied auth.json authenticates. The pinned home is
    ``.codex-pinned/config`` (auth.json + minimal config.toml; NO global AGENTS.md, no user
    hooks/MCP — the .cc-pinned isolation precedent).
  * NO SYSTEM-PROMPT INJECTION (user decision 2026-06-11): "it's sufficient to not change the
    existing system message that it uses — it basically just needs precise technical
    instructions… what it's not told to do, it probably doesn't do." Codex's native base
    instructions stay; ALL harness instruction rides the brief + kickoff (maximally explicit,
    decision-complete — the codex-audit discipline, runtime-and-model-map §135). The recorded
    ``system_prompt_file`` is the explicit sentinel below, never the CC shared prompt.
  * ``-m gpt-5.5`` is accepted AND the rollout header records ``"model":"gpt-5.5"`` as FACT —
    the silent-fallback divergence runtime-and-model-map warns about is detectable downstream.
  * TRANSCRIPT surface: ``<CODEX_HOME>/sessions/YYYY/MM/DD/rollout-<ts>-<uuid>.jsonl``; the
    header line carries the session ``id`` + the pane ``cwd``; the file GROWS per turn (the
    detector's verify-new-turn stat works unchanged). There is NO session-id flag, so the
    adapter DISCOVERS the rollout post-boot: a bounded poll for a rollout whose header cwd ==
    the node workspace realpath, created at/after boot. Undiscoverable in the deadline =
    SpawnFailure('transcript_undiscovered') — fail-loud, never a blind binding (the 2026-06-11
    CC watchdog-blindness lesson, applied here from day one).
  * First-boot TRUST dialog persists as ``[projects."<REALPATH>"] trust_level = "trusted"`` in
    CODEX_HOME/config.toml — seeded deterministically pre-spawn (the CC realpath precedent).
  * The TUI idle marker is '›' (CC's '❯') — surfaced as PROMPT_MARKER for the per-runtime
    marker map (kickoff gate / prod_precondition / wake delivery).
  * Posture: unjailed_skip_permissions -> ``--dangerously-bypass-approvals-and-sandbox``
    ("YOLO mode" in the TUI banner). Containment (the CC seatbelt jail) is NOT supported on
    this runtime in v1 — a containment-requesting spawn refuses loudly, never silently unjailed.

OAuth-only: the shared negative gate (oauth_guard.assert_oauth_only) runs unchanged — no
ANTHROPIC_API_KEY / OPENAI_API_KEY ever rides the pane; Codex auth is the auth.json file
inside the pinned CODEX_HOME (file-based, never an env credential).
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Optional

from harnessd import addressing, config
from harnessd.spawn import oauth_guard

from .base import RuntimeAdapter, SpawnResult
from harnessd.spawn.oauth_guard import SpawnFailure  # the shared typed spawn-refusal (E32)

# The recorded system_prompt_file sentinel: Codex runs its NATIVE base instructions (user
# decision) — this string documents that fact on the binding instead of pretending a file.
CODEX_NATIVE_INSTRUCTIONS = "(codex-native-base-instructions)"

# The TUI idle-input marker (probed 0.128.0) — the per-runtime prompt-marker map reads this.
PROMPT_MARKER: str = "›"

# The BOOT PROMPT — the optional [PROMPT] argv the codex TUI accepts. Two jobs: (1) the TUI
# creates its rollout LAZILY on the FIRST TURN (probed: boot 20:01, rollout appeared at the
# 20:04 first message), so starting a turn at boot is what makes the rollout discoverable
# within the spawn path's deadline; (2) it is the codex-idiomatic first instruction (user
# decision: precise technical instructions; the brief carries everything else).
BOOT_PROMPT: str = (
    "Read the file brief.md in your current working directory and follow its instructions "
    "exactly. Further messages arrive as appended lines in the .inbox.*.jsonl file in this "
    "directory; when a message tells you to check it, read any lines you have not yet read."
)

# Rollout discovery bounds. MEASURED (smoke, 0.128.0): the TUI opens its rollout when the
# boot-prompt turn actually starts streaming — ~100s after create_detached on a cold boot
# (NOT the few seconds `codex exec` takes). The deadline covers that with margin; the cost is
# a blocking wait on the spawn path per codex actor (FOLLOW-UP: async discovery via a later
# sweep so one slow codex boot does not stall the daemon's whole tick).
DISCOVERY_DEADLINE_S: float = 150.0
DISCOVERY_POLL_S: float = 1.0


def _harness_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _pinned_codex() -> Path:
    return _harness_root() / config.PINNED_CODEX_BINARY


def _pinned_home() -> Path:
    return _harness_root() / config.PINNED_CODEX_HOME


class CodexAdapter(RuntimeAdapter):
    """RuntimeAdapter for the Codex harness (GPT-5.5 at L5)."""

    def __init__(self, tmux=None):
        if tmux is None:
            from harnessd.spawn import tmux as tmux_mod
            tmux = tmux_mod
        self.tmux = tmux

    # ------------------------------------------------------------------ #
    # E32 step 1 — pin the binary (pure, no-exec confirmation in v1).
    # ------------------------------------------------------------------ #
    def verify_binary(self, level_config) -> None:
        binary = _pinned_codex()
        if not binary.is_file():
            raise SpawnFailure(
                f"pinned codex binary missing at {binary} (npm @openai/codex@"
                f"{config.PINNED_CODEX_VERSION} into .codex-pinned/)",
                failure_class="runtime_down",
            )

    # ------------------------------------------------------------------ #
    # Trust seeding — deterministic, pre-spawn, realpath-keyed (probe result).
    # ------------------------------------------------------------------ #
    def _seed_trust(self, cwd: Optional[str]) -> None:
        if not cwd:
            return
        real = os.path.realpath(cwd)
        cfg = _pinned_home() / "config.toml"
        try:
            text = cfg.read_text(encoding="utf-8") if cfg.is_file() else ""
        except OSError:
            text = ""
        section = f'[projects."{real}"]'
        if section in text:
            return  # already trusted — idempotent
        try:
            cfg.parent.mkdir(parents=True, exist_ok=True)
            with cfg.open("a", encoding="utf-8") as f:
                f.write(f'\n{section}\ntrust_level = "trusted"\n')
        except OSError as exc:
            raise SpawnFailure(
                f"could not seed codex trust for {real}: {exc}",
                failure_class="runtime_down",
            ) from exc

    # ------------------------------------------------------------------ #
    # Rollout discovery — the transcript surface (probe result; injectable for tests).
    # ------------------------------------------------------------------ #
    @staticmethod
    def discover_rollout(
        sessions_root: Path,
        cwd_realpath: str,
        since_epoch: float,
        *,
        deadline_s: float = DISCOVERY_DEADLINE_S,
        poll_s: float = DISCOVERY_POLL_S,
    ) -> tuple:
        """Find the rollout the freshly-booted pane is writing: the newest ``rollout-*.jsonl``
        under ``sessions_root`` whose mtime >= since_epoch AND whose header line records
        ``cwd == cwd_realpath``. Returns (session_uuid, transcript_path); raises
        SpawnFailure('transcript_undiscovered') past the deadline — fail-loud, a binding with a
        blind transcript path is exactly the 2026-06-11 watchdog-blindness bug class."""
        deadline = time.monotonic() + deadline_s
        while True:
            candidates = []
            if sessions_root.is_dir():
                for p in sessions_root.rglob("rollout-*.jsonl"):
                    try:
                        if p.stat().st_mtime + 1.0 >= since_epoch:
                            candidates.append(p)
                    except OSError:
                        continue
            for p in sorted(candidates, key=lambda q: q.stat().st_mtime, reverse=True):
                try:
                    header = json.loads(p.read_text(encoding="utf-8").splitlines()[0])
                except (OSError, ValueError, IndexError):
                    continue
                # The header line nests the session meta under "payload" (the TUI rollout shape:
                # {"timestamp":…, "type":"session_meta", "payload": {"id":…, "cwd":…}}); tolerate
                # the flat shape too (the exec probe's unwrapped reading).
                meta = header.get("payload") if isinstance(header.get("payload"), dict) else header
                if meta.get("cwd") == cwd_realpath and meta.get("id"):
                    return str(meta["id"]), str(p)
            if time.monotonic() >= deadline:
                raise SpawnFailure(
                    f"no codex rollout discovered under {sessions_root} for cwd "
                    f"{cwd_realpath!r} within {deadline_s}s — refusing a blind binding",
                    failure_class="transcript_undiscovered",
                )
            time.sleep(poll_s)

    # ------------------------------------------------------------------ #
    # The spawn (mirrors the CC adapter's pin -> gate -> open -> record recipe).
    # ------------------------------------------------------------------ #
    def pin_and_open(self, neutral_brief, level_config, tmux_target, env) -> SpawnResult:
        env = dict(env)

        def _brief_get(key, default=None):
            if neutral_brief is None:
                return default
            if isinstance(neutral_brief, dict):
                return neutral_brief.get(key, default)
            return getattr(neutral_brief, key, default)

        role_variant = (
            _brief_get("role_variant")
            or getattr(level_config, "role_variant", None)
            or getattr(level_config, "level", None)
        )

        # (1) Pin the binary before anything child-facing runs (E32).
        self.verify_binary(level_config)

        # (1a) Containment is NOT supported on the Codex runtime in v1: the seatbelt profile is
        # CC-shaped (sandbox-exec around the CC binary). Refuse loudly — never silently unjailed.
        if _brief_get("containment_profile") is not None:
            raise SpawnFailure(
                "containment requested on the codex runtime — the v1 jail is CC-only; refusing "
                "rather than silently spawning unjailed",
                failure_class="containment_unsupported",
            )

        # (2) argv: the pinned codex + the EXPLICIT model flag (never a guessed id) + posture.
        codex = str(_pinned_codex())
        argv = [codex]
        model_flag = config.CODEX_MODEL_FLAGS.get(getattr(level_config, "model", None))
        if model_flag:
            argv += ["-m", model_flag]
        if getattr(level_config, "unjailed_skip_permissions", False):
            # The user-approved PoC posture rendered in codex terms (probed: "YOLO mode").
            argv.append("--dangerously-bypass-approvals-and-sandbox")
            permission_posture = "unjailed-skip-permissions-override"
        else:
            permission_posture = "unjailed-prompting"
        # The boot prompt is the LAST argv element (the TUI's optional [PROMPT]) — it starts the
        # first turn at boot, which is what creates the rollout the discovery below finds.
        argv.append(BOOT_PROMPT)

        # (3) The pane env floor — CODEX-OWN, never CC's. The chokepoint hands every adapter the
        # commissioned CC env (CLAUDE_CODE_OAUTH_TOKEN + config dir + kill-switches): STRIP all
        # CLAUDE_* vars (a CC OAuth token must never ride a codex pane — cross-runtime credential
        # hygiene; also drops the dry-run placeholder sentinels the transport rightly refuses)
        # and build the probed floor: PATH (codex's npm shim needs node; shells it spawns need
        # standard bins + homebrew), HOME, TERM, the pinned CODEX_HOME. Auth is auth.json inside
        # the pinned home — never an env credential (the negative gate below still enforces).
        env = {k: v for k, v in env.items() if not k.startswith("CLAUDE_") and k != "DISABLE_AUTOUPDATER"}
        env.setdefault("PATH", "/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:/opt/homebrew/bin")
        env.setdefault("HOME", os.path.expanduser("~"))
        env.setdefault("CODEX_HOME", str(_pinned_home()))
        env.setdefault("TERM", "xterm-256color")

        cwd = _brief_get("workspace")
        if cwd:
            cwd = str(cwd)
            try:
                Path(cwd).mkdir(parents=True, exist_ok=True)
            except OSError:
                pass
            cwd = os.path.realpath(cwd)

        # (4) Deterministic first-boot trust for the pane cwd (probe: realpath-keyed TOML).
        self._seed_trust(cwd)

        # (5) The from-empty pane + the shared OAuth-only negative gate BEFORE the actor opens.
        pane_argv = self.tmux.build_pane_argv(env, argv)
        oauth_guard.assert_oauth_only(env, argv, pane_argv, self.tmux.server_env())

        # (6) Open the detached actor (the F18 canonical-target contract).
        session_name = addressing.session_name_for(tmux_target)
        boot_epoch = time.time()
        if cwd:
            canonical_target = self.tmux.create_detached(session_name, pane_argv, env, cwd=cwd)
        else:
            canonical_target = self.tmux.create_detached(session_name, pane_argv, env)

        # (7) Discover the rollout (session uuid + transcript path) — the REAL files codex
        # writes, never an invented uuid.
        sessions_root = _pinned_home() / "sessions"
        session_uuid, transcript_path = self.discover_rollout(
            sessions_root, cwd or os.path.realpath(os.getcwd()), boot_epoch
        )

        return SpawnResult(
            ok=True,
            session_uuid=session_uuid,
            model_used=f"{getattr(level_config, 'model', '?')} / codex",
            role_variant=role_variant,
            system_prompt_file=CODEX_NATIVE_INSTRUCTIONS,
            system_prompt_file_hash=hashlib.sha256(
                CODEX_NATIVE_INSTRUCTIONS.encode("utf-8")
            ).hexdigest(),
            tmux_target=canonical_target,
            transcript_path=transcript_path,
            failure_class=None,
            argv=tuple(argv),
            env=dict(env),
            permission_posture=permission_posture,
        )
