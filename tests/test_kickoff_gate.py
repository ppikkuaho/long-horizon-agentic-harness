"""LT-6 / LT-9 — the kickoff nudge is prompt-GATED and a delivered kickoff is ACKED.

  * LT-6 — STEP6's send-keys fired milliseconds after create_detached into a mid-boot pane with
    NO prompt gate — the one keystroke delivery in the system typed blind. If any boot dialog is
    up (unseeded trust, a new prompt type), the kickoff text scrambles the dialog and its Enter
    CONFIRMS the highlighted option (TRANSPORTS §3.3: send-keys into a modal answers the modal).
    Now: a bounded capture_pane poll (the same measured CC marker strings the watchdog's prod
    gate uses) must show the idle prompt — and no working/dialog marker — before the nudge; a
    gate that never opens SKIPS the immediate nudge (journaled kickoff_gate_timeout) and the
    durable inbox line + ③-wake heal it once the gate opens.

  * LT-9 — a successfully delivered kickoff was never acked, so EVERY spawn owed one guaranteed
    spurious ③-wake re-nudge of the already-actioned kickoff line (the standing fuel for LT-3's
    post-collapse nudge). Now a kickoff whose send reported delivery acks the watermark to the
    kickoff line's own end-offset; a failed/skipped send leaves it unmoved (the wake delivers).
"""

from __future__ import annotations

import copy
import json

import pytest

import harnessd.addressing as addressing
import harnessd.config as config
import harnessd.executor as executor  # noqa: F401 — the REAL single writer
import harnessd.fencing as fencing
import harnessd.ledger as ledger
import harnessd.watchdog as watchdog
from harnessd.spawn import chokepoint
from harnessd.spawn.adapters.base import SpawnResult

LEAF = "proj/widget/task#exec"


@pytest.fixture
def runtime(tmp_path):
    previous = ledger.RUNTIME_ROOT
    ledger.RUNTIME_ROOT = tmp_path
    try:
        yield tmp_path
    finally:
        ledger.RUNTIME_ROOT = previous


@pytest.fixture(autouse=True)
def _reset_chokepoint_adapter():
    previous = chokepoint.ADAPTER
    try:
        yield
    finally:
        chokepoint.ADAPTER = previous


@pytest.fixture(autouse=True)
def _fast_gate(monkeypatch):
    """Keep the bounded gate poll instant in tests (the bound is a module seat)."""
    monkeypatch.setattr(chokepoint, "KICKOFF_GATE_DEADLINE_S", 0.05)
    monkeypatch.setattr(chokepoint, "KICKOFF_GATE_POLL_S", 0.0)


IDLE_PANE = f"{watchdog.FORK_PROMPT} \n? for shortcuts"
DIALOG_PANE = (
    f"Do you trust the files in this folder?\n{watchdog.FORK_PROMPT} 1. Yes, I trust this folder\n"
    "Enter to confirm · Esc to cancel"
)


class _GateTmux:
    """Controllable kickoff transport: scripted capture frames + a scripted send result."""

    def __init__(self, panes=None, send_result=True, has_capture=True):
        self.sent = []
        self.captures = 0
        self._panes = list(panes) if panes is not None else [IDLE_PANE]
        self._send_result = send_result
        if not has_capture:
            self.capture_pane = None  # getattr(..., 'capture_pane') -> None: the legacy mock shape

    def capture_pane(self, target):
        self.captures += 1
        if self.captures <= len(self._panes):
            return self._panes[self.captures - 1]
        return self._panes[-1] if self._panes else ""

    def send_keys(self, target, text):
        self.sent.append((target, text))
        return self._send_result

    def kill(self, target):
        pass


class FakeAdapter:
    def __init__(self, tmux):
        self.tmux = tmux

    def pin_and_open(self, neutral_brief, level_config, tmux_target, env):
        return SpawnResult(
            ok=True,
            session_uuid="sess-kick-0001",
            model_used="opus-4.8 / claude-code",
            role_variant=getattr(level_config, "role_variant", "L5"),
            system_prompt_file=config.SYSTEM_PROMPT_FILE,
            system_prompt_file_hash="deadbeef",
            tmux_target=addressing.session_name_for(tmux_target) + ":0.0",
            transcript_path="/runtime/transcripts/sess-kick-0001.jsonl",
            failure_class=None,
        )


def _seed_planned(runtime):
    token = fencing.mint_owner_token(LEAF, "sa", "uuid", 1)
    ws = addressing.node_dir(LEAF, runtime)
    ws.mkdir(parents=True, exist_ok=True)
    rec = {
        "node_address": LEAF, "parent_address": "proj/widget#exec", "level": "L5",
        "subagent_id": "sa", "session_uuid": "uuid", "state": "planned", "generation": 0,
        "lease_epoch": 1, "owner_token": token, "last_applied_seq": 0,
        "liveness_state": "claimed", "terminal_signal": None, "gate_crossed_at": None,
        "paused_at": None, "transcript_path": None,
        "tmux_target": addressing.session_name_for(LEAF), "workspace": str(ws),
    }
    ledger.write_binding({LEAF: copy.deepcopy(rec)}, _lock_held=True)
    return token


def _spawn(runtime, tmux):
    token = _seed_planned(runtime)
    chokepoint.set_adapter(FakeAdapter(tmux))
    return chokepoint.claim_and_spawn(
        LEAF, expected_state="planned", expected_generation=0,
        expected_owner_token=token, level_config=config.LevelConfig.for_level("L5"),
    )


def _wal_events():
    return [r.get("event") for r in ledger.load_wal() if r.get("node_address") == LEAF]


# ---------------------------------------------------------------------------------------
# (1) LT-9 — a DELIVERED kickoff acks its own line: no spurious wake owed.
# ---------------------------------------------------------------------------------------

def test_delivered_kickoff_acks_the_kickoff_line(runtime):
    tmux = _GateTmux(panes=[IDLE_PANE])
    result = _spawn(runtime, tmux)
    assert result.ok and tmux.sent, "the gated kickoff must deliver on an idle-prompt pane"

    inbox = addressing.inbox_path(LEAF, runtime)
    size = inbox.stat().st_size
    live = ledger.read_binding(LEAF)
    assert live.get("last_inbox_acked_offset") == size, (
        "a DELIVERED kickoff must ack the watermark to its own line's end-offset (LT-9) — "
        "else every spawn owes one guaranteed spurious ③-wake re-nudge"
    )
    assert watchdog.inbox_has_unacked({"node_address": LEAF}, live) is False, (
        "nothing unacked remains: the heal loop is terminated for the delivered kickoff"
    )


def test_failed_kickoff_send_leaves_the_watermark_unmoved(runtime):
    tmux = _GateTmux(panes=[IDLE_PANE], send_result=False)
    result = _spawn(runtime, tmux)
    assert result.ok and tmux.sent, "the send was attempted (and reported failure)"

    live = ledger.read_binding(LEAF)
    assert live.get("last_inbox_acked_offset", 0) == 0, (
        "a send that REPORTED failure must NOT ack — the ③-wake delivers from the durable line"
    )
    assert watchdog.inbox_has_unacked({"node_address": LEAF}, live) is True
    assert "kickoff_send_failed" in _wal_events(), "the lost nudge is journaled, never silent"


# ---------------------------------------------------------------------------------------
# (2) LT-6 — the prompt gate: no blind keystroke into a mid-boot/dialog pane.
# ---------------------------------------------------------------------------------------

def test_kickoff_skips_the_nudge_when_a_dialog_is_up(runtime):
    tmux = _GateTmux(panes=[DIALOG_PANE])
    result = _spawn(runtime, tmux)
    assert result.ok, "the spawn itself succeeds — the kickoff nudge is best-effort"

    assert tmux.sent == [], (
        "NO keystroke may be typed while a blocking dialog renders — the kickoff's Enter would "
        "CONFIRM the highlighted option (TRANSPORTS §3.3)"
    )
    # The durable line is the heal: present, unacked, so the ③-wake delivers once the gate opens.
    inbox = addressing.inbox_path(LEAF, runtime)
    lines = [json.loads(l) for l in inbox.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert any(l.get("type") == "kickoff" for l in lines), "the durable kickoff line still lands"
    live = ledger.read_binding(LEAF)
    assert live.get("last_inbox_acked_offset", 0) == 0, "a skipped nudge never acks"
    assert "kickoff_gate_timeout" in _wal_events(), "the skipped nudge is journaled (visible)"


def test_kickoff_skips_on_a_blank_mid_boot_pane(runtime):
    tmux = _GateTmux(panes=[""])
    result = _spawn(runtime, tmux)
    assert result.ok
    assert tmux.sent == [], "a pane that never reaches the idle prompt within the bound gets no nudge"
    assert "kickoff_gate_timeout" in _wal_events()


def test_kickoff_waits_for_the_prompt_then_sends(runtime):
    """The bounded poll: a working pane that reaches the idle prompt within the bound IS nudged."""
    working = f"{watchdog.FORK_PROMPT} \nesc to interrupt"
    tmux = _GateTmux(panes=[working, working, IDLE_PANE])
    result = _spawn(runtime, tmux)
    assert result.ok
    assert tmux.sent, "the nudge fires once the gate opens (within the bound)"
    assert tmux.captures >= 3, "the gate POLLED (bounded retries), not a single blind capture"


def test_kickoff_without_capture_keeps_the_legacy_ungated_send(runtime):
    """A transport that cannot capture (the older dry-run mocks) keeps the pre-gate behavior:
    best-effort send + the LT-9 ack."""
    tmux = _GateTmux(has_capture=False)
    result = _spawn(runtime, tmux)
    assert result.ok
    assert tmux.sent, "no capture seam -> the legacy ungated best-effort send still fires"
    live = ledger.read_binding(LEAF)
    assert live.get("last_inbox_acked_offset", 0) > 0, "the delivered kickoff still acks (LT-9)"
