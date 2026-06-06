"""cc_config — deterministic first-boot trust / kill-all-prompts (SECURITY.md §deterministic-trust).

A spawned interactive Claude Code session hits BLOCKING startup dialogs that, with no human at the
pane, would FREEZE the agent forever:
  1. the workspace TRUST dialog ("Is this a project you trust?")        — per-folder
  2. the BYPASS-PERMISSIONS warning (from --dangerously-skip-permissions) — once-accepted
  3. per-tool permission prompts                                          — covered by skip-permissions

These are ALL superfluous for the harness: the seatbelt JAIL is the structural blast-radius bound
(SECURITY.md constraint 4), NOT the agent's tool-by-tool approval. So the harness ELIMINATES every
prompt deterministically — pre-seeding the config so no dialog appears — rather than racing send-keys
against a dialog (the Inc-9 ``_deterministic_trust`` no-op becomes this real mechanism). Verified live:
a fresh workspace with these keys pre-seeded boots STRAIGHT to the agent prompt, zero dialogs.

The config keys (from the pinned CC v2.1.152, confirmed by accepting the dialogs + reading the persisted
``.claude.json`` / ``settings.json``):
  * ``.claude.json`` ``projects[<workspace>].hasTrustDialogAccepted = true``     — the trust dialog
  *                  ``projects[<workspace>].hasCompletedProjectOnboarding = true`` — project onboarding
  * ``.claude.json`` ``bypassPermissionsModeAccepted = true``                    — the bypass warning
  * ``settings.json`` ``skipDangerousModePermissionPrompt = true``               — the bypass prompt floor
  * ``.claude.json`` ``hasCompletedOnboarding = true``                           — first-run onboarding
"""

from __future__ import annotations

import json
from pathlib import Path


def seed_trust(config_dir: str, workspace_path: str) -> None:
    """Pre-seed the pinned CLAUDE_CONFIG_DIR so NO startup dialog / permission prompt appears for
    ``workspace_path`` (the agent's node workspace = its cwd). Idempotent; the daemon calls this at
    the spawn chokepoint BEFORE launch (outside the jail), so the agent boots straight to working.

    Writes/merges:
      - ``.claude.json``: ``projects[<workspace>]`` trust+onboarding flags, top-level
        ``bypassPermissionsModeAccepted`` + ``hasCompletedOnboarding``.
      - ``settings.json``: ``skipDangerousModePermissionPrompt`` (the bypass-prompt floor).
    The workspace path is stored as its absolute string (CC keys ``projects`` by the realpath the
    session opens; the caller passes the same path the agent ``cd``s into).
    """
    cfg_dir = Path(config_dir)
    # The pinned CLAUDE_CONFIG_DIR ALWAYS pre-exists in production (it IS the pinned install). If it is
    # absent, this is a placeholder/dry-run path (no real agent boots), so there is nothing to pre-trust
    # — skip cleanly. We do NOT mkdir a fake config tree (that would mask a real misconfiguration and
    # crash on a placeholder). In production the real dir is present, so the seed always runs.
    if not cfg_dir.is_dir():
        return

    ws = str(workspace_path)

    # --- .claude.json: per-folder trust + onboarding + the bypass acceptance ---
    claude_json = cfg_dir / ".claude.json"
    data = _load_json(claude_json, default={})
    projects = data.setdefault("projects", {})
    proj = projects.setdefault(ws, {})
    proj["hasTrustDialogAccepted"] = True
    proj["hasCompletedProjectOnboarding"] = True
    proj.setdefault("projectOnboardingSeenCount", 1)
    proj.setdefault("allowedTools", [])
    data["bypassPermissionsModeAccepted"] = True
    data["hasCompletedOnboarding"] = True
    _dump_json(claude_json, data)

    # --- settings.json: the bypass-prompt floor (already on in the pinned install; ensure it) ---
    settings_json = cfg_dir / "settings.json"
    settings = _load_json(settings_json, default={})
    settings["skipDangerousModePermissionPrompt"] = True
    _dump_json(settings_json, settings)


def _load_json(path: Path, *, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return dict(default)


def _dump_json(path: Path, data) -> None:
    # Write the whole map back (CC reads it fresh each boot); 0600 — it holds session/onboarding state.
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass
