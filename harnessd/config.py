"""Config-time seats the rest of the harness must NOT hardcode.

Authoritative sources:
  - IMPLEMENTATION-PLAN §1 module table (`harnessd/config.py` row): `LevelConfig`
    per level (model / runtime / role_variant / tool_manifest), the CONSTANT
    `system_prompt_file = operational/shared/system-prompt.md`, the per-state
    suspicion windows `W(state)` (placeholder constants in v1, FORK-W), and the
    pinned-binary version/hash.
  - DAEMON §3.2 (the H40 spawn fact): `system_prompt_file` is the ONE shared
    minimal prompt passed as `--system-prompt-file` at EVERY spawn, byte-identical
    L1–L5 (a runtime-global, NOT a per-level role path). `role_variant` is the
    PER-binding selector that varies by seat.
  - operational/shared/runtime-and-model-map.md (E31/E32 assignment table): the
    per-level model + runtime config snapshot.
  - FORK-W (WATCHDOG §8): v1 placeholder windows W_working=120s,
    W_waiting_on_child=600s, W_writing_final=60s.
  - PINNED-CC.md: pinned Claude Code version 2.1.152.

"Commissioning tunes these without a code change" — they are config seats, not
inline constants buried at the spawn site.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, replace

# ---------------------------------------------------------------------------
# CONSTANT shared system prompt (DAEMON §3.2 H40 spawn fact; ROLE-RESOLUTION §1).
#
# The ONE shared minimal `--system-prompt-file`, byte-identical for L1–L5 — a
# runtime-global, NOT a per-level role path. The per-seat selection of role docs
# is carried by `role_variant`, never by this path.
# ---------------------------------------------------------------------------

# NOTE (resolution contract, for Increment 9 / the Claude-Code adapter): this is
# relative-to-HARNESS-ROOT. The daemon is launchd-managed (§2.2) with a CWD that
# is NOT guaranteed to be the repo root, so the adapter MUST join this against the
# resolved HARNESS_ROOT (the same root used for CLAUDE_CONFIG_DIR=$HARNESS/.cc-pinned/config)
# before passing it as `--system-prompt-file`; never pass it raw to a launchd-CWD process.
SYSTEM_PROMPT_FILE: str = "operational/shared/system-prompt.md"


# ---------------------------------------------------------------------------
# Pinned-binary seat (PINNED-CC.md). version is fixed at 2.1.152; the hash is a
# v1 placeholder (the binary is gitignored / not yet captured) but the SEAT must
# exist so the chokepoint's verify_binary(version=..., hash=...) has somewhere to
# read from (IMPLEMENTATION-PLAN §2.11 / §1 config row).
# ---------------------------------------------------------------------------

PINNED_BINARY_VERSION: str = "2.1.152"
# v1 placeholder — the pinned binary hash is not yet captured (the install is
# gitignored, PINNED-CC §"What's pinned"). Commissioning fills this in; the seat
# exists now so nothing downstream hardcodes the pinned hash at the spawn site.
PINNED_BINARY_HASH: str | None = None  # TODO(FORK / commissioning): capture sha256 of the pinned claude binary.


@dataclass(frozen=True)
class PinnedBinary:
    """The pinned-binary descriptor (PINNED-CC). `verify_binary` reads version+hash."""

    version: str = PINNED_BINARY_VERSION
    hash: str | None = PINNED_BINARY_HASH


PINNED_BINARY: PinnedBinary = PinnedBinary()


# ---------------------------------------------------------------------------
# The spec-model -> Claude-Code --model flag mapping (the transport increment).
#
# PROBED LIVE on the pinned CC v2.1.152 (2026-06-10): `--model claude-opus-4-8` boots clean and
# the banner names the model; with NO --model the pinned CC defaults to Sonnet — i.e. without
# this flag every "opus-4.8" LevelConfig silently ran a different model while SpawnResult
# recorded "opus-4.8 / claude-code" as fact. NOTE: CC does NOT validate --model at boot (a
# bogus id banners and only fails on the first API turn), so the mapping is EXPLICIT — an
# unmapped model adds NO flag (never guess an id). model_used remains the recorded INTENT;
# the E32 configured-vs-actual fact-checker is deferred F17 territory.
# ---------------------------------------------------------------------------

CC_MODEL_FLAGS: dict[str, str] = {
    "opus-4.8": "claude-opus-4-8",  # the canonical alias (no date suffix) — probed to boot+banner
}


# ---------------------------------------------------------------------------
# W(state) suspicion-window placeholder constants (FORK-W / WATCHDOG §3.3, §8).
#
# A renewal is overdue when `now - last_progress_at > W(state)`. The numbers are
# KNOWN-OPEN; v1 ships placeholders as config seats (NOT hardcoded inline) so
# commissioning can tune them without a code change.
# ---------------------------------------------------------------------------

# SUSPICION_WINDOWS is the SINGLE SOURCE (state -> seconds). The W_* module
# constants below are DERIVED from it, so a window added/tuned at commissioning is
# a one-line edit here, not two hand-synced places (the key set + a constant).
SUSPICION_WINDOWS: dict[str, int] = {
    "working": 120,           # seconds — actively producing output
    "waiting_on_child": 600,  # seconds — parent parked on a child (tolerates longer)
    "writing_final": 60,      # seconds — wrapping up the final report
}

W_working: int = SUSPICION_WINDOWS["working"]
W_waiting_on_child: int = SUSPICION_WINDOWS["waiting_on_child"]
W_writing_final: int = SUSPICION_WINDOWS["writing_final"]


def W(state: str) -> int:
    """Return the suspicion window (seconds) for a given runtime state.

    Placeholder values per FORK-W; commissioning tunes them. Raises KeyError for
    an unknown state so a typo at a call site fails loud rather than silently
    returning a wrong window.
    """
    return SUSPICION_WINDOWS[state]


# ---------------------------------------------------------------------------
# LevelConfig — the per-level seat carrying the four config-time dimensions the
# spawn machinery reads (model / runtime / role_variant / tool_manifest) plus the
# CONSTANT shared system_prompt_file (carried here for convenience; identical
# across all levels) and a reference to the pinned binary.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LevelConfig:
    """Config-time seat for one level (L1..L5).

    Per runtime-and-model-map E31: model + runtime is a per-level, config-time,
    swappable dimension — an agent never picks its own. `role_variant` is the
    per-seat selector the chokepoint resolves to a role/load-manifest bundle.
    `system_prompt_file` is the runtime-global CONSTANT, identical across levels.
    """

    level: str
    model: str
    runtime: str
    role_variant: str
    tool_manifest: tuple[str, ...]
    # The shared `--system-prompt-file` — CONSTANT, identical across L1..L5.
    system_prompt_file: str = SYSTEM_PROMPT_FILE
    pinned_binary: PinnedBinary = field(default_factory=lambda: PINNED_BINARY)
    # SUPERVISED-SMOKE OVERRIDE (user-approved 2026-06-10; see
    # `unjailed_skip_permissions_requested` below): when True, an UNJAILED spawn adds
    # --dangerously-skip-permissions — explicitly decoupling SECURITY.md constraint 4's
    # skip-perms<->jail coupling for the small supervised smoke run. Default False: absent
    # the explicit opt-in, behavior is byte-identical to before the knob existed. NEVER set
    # in the LEVEL_CONFIGS registry — only the launch-path assemblers
    # (commissioning.build_runtime / get_level_config) stamp it from the env knob.
    unjailed_skip_permissions: bool = False

    @classmethod
    def for_level(cls, level: str) -> "LevelConfig":
        """Resolve the LevelConfig for an L1..L5 token (the factory accessor)."""
        try:
            return LEVEL_CONFIGS[level]
        except KeyError as exc:
            raise KeyError(f"unknown level {level!r}; known levels: {sorted(LEVEL_CONFIGS)}") from exc


# ---------------------------------------------------------------------------
# The per-level registry (runtime-and-model-map E32 assignment table).
#
# L1–L4: Opus 4.8 on the Claude Code runtime (generative / architecture / planning
# seats). L5 per E32 is GPT-5.5 on the Codex runtime (spec-anchored execution) —
# but see the L5 SMOKE STAND-IN note below: until the Codex adapter lands, L5 runs
# opus-4.8/claude-code. The tool_manifest is the only runtime-specific dimension
# (the adapter injects it); v1 carries a coarse placeholder manifest per runtime,
# tuned at commissioning.
# ---------------------------------------------------------------------------

# Coarse v1 placeholder tool surfaces, keyed by runtime. The real per-seat
# manifest is assembled by the chokepoint from the role_variant (ROLE-RESOLUTION
# §4); these are config seats so nothing downstream hardcodes a tool list.
_CLAUDE_CODE_TOOLS: tuple[str, ...] = ("read", "write", "edit", "bash", "task")
_CODEX_TOOLS: tuple[str, ...] = ("read", "write", "edit", "bash")

LEVEL_CONFIGS: dict[str, LevelConfig] = {
    "L1": LevelConfig(
        level="L1",
        model="opus-4.8",
        runtime="claude-code",
        role_variant="L1",
        tool_manifest=_CLAUDE_CODE_TOOLS,
    ),
    "L2": LevelConfig(
        level="L2",
        model="opus-4.8",
        runtime="claude-code",
        role_variant="L2",
        tool_manifest=_CLAUDE_CODE_TOOLS,
    ),
    "L3": LevelConfig(
        level="L3",
        model="opus-4.8",
        runtime="claude-code",
        role_variant="L3",
        tool_manifest=_CLAUDE_CODE_TOOLS,
    ),
    "L4": LevelConfig(
        level="L4",
        model="opus-4.8",
        runtime="claude-code",
        role_variant="L4",
        tool_manifest=_CLAUDE_CODE_TOOLS,
    ),
    # L5 SMOKE STAND-IN (LT-8; DEFERRED-REGISTER O1 — user-approved 2026-06-06 "start on Opus,
    # wire Codex later"): the E32 spec assignment is gpt-5.5/codex, but the Codex adapter (O1)
    # has not landed and the ONE injected adapter is the ClaudeCodeAdapter — a codex-configured
    # L5 driven through it spawned CC with NO --model flag (the pinned CC defaults to Sonnet)
    # while the binding recorded a different intent: a silent three-way divergence
    # (configured vs recorded vs actual). Until O1 lands, L5 runs the pinned opus-4.8/claude-code
    # stand-in so config, record, and actual AGREE for the supervised smoke run.
    # RETIREMENT TRIGGER: the Codex adapter fill (O1) flips this back to gpt-5.5/codex/_CODEX_TOOLS
    # — and re-runs the L5/L5+ cross-runtime judgment-diversity eval (the O1 eval caveat).
    "L5": LevelConfig(
        level="L5",
        model="opus-4.8",
        runtime="claude-code",
        role_variant="L5#exec",
        tool_manifest=_CLAUDE_CODE_TOOLS,
    ),
}


# ---------------------------------------------------------------------------
# SUPERVISED-SMOKE OVERRIDE — the explicit unjailed --dangerously-skip-permissions knob.
#
# SECURITY.md constraint 4 couples skip-permissions to the jail ("skip-permissions INSIDE
# the jail … containment bounds the blast radius"), so the adapter adds
# --dangerously-skip-permissions ONLY when a containment block is resolved. The FIRST
# supervised live run is a small UNJAILED smoke run; the user explicitly decided
# (2026-06-10): "Unjailed + dangerously skip permissions. It is a small run, the risk of
# something catastrophic happening is minimal." This knob is that decision as an explicit,
# loud, opt-in seam — never a silent decoupling:
#
#   * opt-in is STRICTLY HARNESS_UNJAILED_SKIP_PERMISSIONS=1 (no fuzzy truthiness);
#   * the env var is read at the LAUNCH-PATH ASSEMBLERS (commissioning.build_runtime for
#     the genesis L1; get_level_config for the ipc/outbox child-spawn resolution) — NEVER
#     inside the adapter (the adapter reads only the explicit LevelConfig field);
#   * the posture is journaled (SpawnResult.permission_posture +/ the STEP4 binding stamp
#     `permission_posture: unjailed-skip-permissions-override`, SECURITY.md §4.3);
#   * RETIREMENT TRIGGER: the jail tier (REMEDIATION F9–F13) retires this knob — once the
#     first run is jailed, constraint 4's coupled posture is the only one.
# ---------------------------------------------------------------------------

UNJAILED_SKIP_PERMISSIONS_ENV: str = "HARNESS_UNJAILED_SKIP_PERMISSIONS"


def unjailed_skip_permissions_requested(environ=None) -> bool:
    """True iff the operator EXPLICITLY set HARNESS_UNJAILED_SKIP_PERMISSIONS=1 (strictly "1").

    The single read seam for the supervised-smoke override (see the block comment above).
    Called only by the launch-path assemblers; the adapter never calls this.
    """
    env = os.environ if environ is None else environ
    return env.get(UNJAILED_SKIP_PERMISSIONS_ENV) == "1"


def get_level_config(level: str) -> LevelConfig:
    """Module-level accessor: resolve the LevelConfig for an L1..L5 token.

    THIS is the launch-path resolver the daemon's child-spawn paths use (ipc.spawn /
    outbox.service — the L2..L5 children of the L1->L5 smoke run), so it applies the
    SUPERVISED-SMOKE OVERRIDE here, mirroring commissioning.build_runtime for genesis.
    The override lands on a per-call COPY (`dataclasses.replace`) — the shared
    LEVEL_CONFIGS singletons and the pure `LevelConfig.for_level` accessor stay pristine.
    """
    lc = LevelConfig.for_level(level)
    if unjailed_skip_permissions_requested():
        lc = replace(lc, unjailed_skip_permissions=True)
    return lc
