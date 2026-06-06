"""Increment 6 — detector.liveness FROZEN acceptance (the thin liveness floor).

Authoritative sources (grounded, not recalled):
  - IMPLEMENTATION-PLAN §2.8 (the FROZEN detector.py / detector_signals.py interface).
  - IMPLEMENTATION-PLAN Increment-6 Done-test (L711-719): the five verdict cases +
    the false-idle hazard + transcript_path-absent fails loud.
  - IMPLEMENTATION-PLAN §4.1 "detector verdicts (fully mockable)" (L559-571).
  - WATCHDOG §2.4 (the working-vs-waiting-vs-idle boundary, the false-idle hazard) +
    §3.3 / config.W / config.SUSPICION_WINDOWS (the W window).

FROZEN INTERFACE (transcribed exactly from §2.8):
    detector.liveness(node_address) -> Liveness(state, last_progress_at: str|None)
      state in working | waiting | idle | dead
      v1 floor fuses ONLY jsonl_progress + pane_alive.
        grew within W                                                  -> working
        flat beyond W + pane warm + LEGIT reason                       -> waiting
          (legit reason = terminal_signal == ESCALATED, OR a coordinator
           with a live-descendant roll-up)
        flat beyond W + pane warm + NO reason                          -> idle
        pane_dead == 1 OR pane gone                                    -> dead
      FALSE-IDLE HAZARD: flat JSONL but still WITHIN the W window reads WORKING, not idle —
        the W(state) window (config.W / SUSPICION_WINDOWS, via clock age) must ELAPSE
        before flat -> idle/waiting.
      FAIL-LOUD: a binding with NO transcript_path makes jsonl_progress/liveness RAISE
        (or return an explicit "unknown") — NEVER silently return dead/idle.

TEST STRATEGY (§4 subscription-safety: ZERO model usage):
  - tmux is MOCKED: monkeypatch detector_signals.pane_alive (the boundary the detector calls).
  - JSONL is SYNTHESIZED: a real temp transcript file whose size/mtime we control; the
    flat-vs-grew floor signal is driven through detector_signals.jsonl_progress at the
    detector's call site (its internal size/mtime cache is the impl's business; we pin
    the SIGNAL the verdict fuses, which is the frozen contract).
  - The W window is controlled by setting last_progress_at recent (within W) vs far in
    the past (beyond W); the detector reads it through the canonical clock.

NO IMPLEMENTATION lives here — detector.py / detector_signals.py do not exist yet. RED first.
"""

from __future__ import annotations

import importlib
from datetime import datetime, timedelta, timezone

import pytest

import harnessd.config as config
import harnessd.fencing as fencing
import harnessd.ledger as ledger


# ---------------------------------------------------------------------------
# Import the modules-under-test lazily so collection does not hard-crash before
# the impl exists; each test skips-to-fail with a clear RED reason if missing.
# (RED expectation: ModuleNotFoundError until Increment 6 is built.)
# ---------------------------------------------------------------------------

def _detector():
    return importlib.import_module("harnessd.detector")


def _signals():
    return importlib.import_module("harnessd.detector_signals")


# ---------------------------------------------------------------------------
# Fixtures: a real ledger rooted at tmp_path, plus a binding seeder carrying the
# spawn<->detector contract fields the detector reads (transcript_path, tmux_target,
# owner_token, terminal_signal, last_progress_at, liveness_state).
# ---------------------------------------------------------------------------

@pytest.fixture
def runtime(tmp_path, monkeypatch):
    monkeypatch.setattr(ledger, "RUNTIME_ROOT", tmp_path)
    return tmp_path


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _ago(seconds: float) -> str:
    """An ISO-8601 UTC instant `seconds` in the past (for last_progress_at)."""
    return _iso(datetime.now(timezone.utc) - timedelta(seconds=seconds))


def _seed_binding(
    runtime,
    node_address,
    *,
    transcript_path,
    last_progress_at,
    state="running",
    liveness_state="working",
    terminal_signal=None,
    role_variant="L5#exec",
    epoch=1,
    tmux_target="harness:proj-a-exec",
):
    """Seed one binding the detector will resolve from node_address."""
    token = fencing.mint_owner_token(node_address, "sa", "uuid", epoch)
    rec = {
        "node_address": node_address,
        "state": state,
        "generation": 0,
        "owner_token": token,
        "lease_epoch": epoch,
        "subagent_id": "sa",
        "session_uuid": "uuid",
        "tmux_target": tmux_target,
        "transcript_path": transcript_path,
        "last_progress_at": last_progress_at,
        "liveness_state": liveness_state,
        "terminal_signal": terminal_signal,
        "role_variant": role_variant,
    }
    # MERGE into the existing keyed map (write_binding is a whole-map replace, so a
    # bare single-key write would clobber any other seeded node — see ledger §2.4).
    current = dict(ledger.all_nodes())
    current[node_address] = rec
    ledger.write_binding(current, _lock_held=True)
    return rec


def _write_transcript(tmp_path, *, size: int, age_seconds: float = 0.0):
    """Write a real JSONL transcript file of a controlled byte-size and mtime."""
    p = tmp_path / "transcript.jsonl"
    p.write_bytes(b"x" * size)
    if age_seconds:
        import os
        when = datetime.now(timezone.utc).timestamp() - age_seconds
        os.utime(p, (when, when))
    return str(p)


def _patch_signals(monkeypatch, *, grew, mtime_iso, pane_alive, pane_pid):
    """MOCK the two floor signals at the detector's call sites (tmux boundary mocked)."""
    sig = _signals()
    monkeypatch.setattr(sig, "jsonl_progress", lambda node: (grew, mtime_iso))
    monkeypatch.setattr(sig, "pane_alive", lambda node: (pane_alive, pane_pid))


# Some impls call the signal readers via the detector module's own reference
# (from detector_signals import ...). Patch BOTH the source module and any name
# the detector may have bound, so the mock is honored regardless of import style.
def _patch_signals_everywhere(monkeypatch, *, grew, mtime_iso, pane_alive, pane_pid):
    _patch_signals(monkeypatch, grew=grew, mtime_iso=mtime_iso,
                   pane_alive=pane_alive, pane_pid=pane_pid)
    det = _detector()
    for name, fn in (("jsonl_progress", lambda node: (grew, mtime_iso)),
                     ("pane_alive", lambda node: (pane_alive, pane_pid))):
        if hasattr(det, name):
            monkeypatch.setattr(det, name, fn, raising=False)


# ===========================================================================
# VERDICT CASE 1 — working (JSONL grew within W).
# Discriminating: grew=True -> working regardless of pane/age.
# ===========================================================================

def test_verdict_working_jsonl_grew(runtime, tmp_path, monkeypatch):
    tp = _write_transcript(tmp_path, size=200)
    _seed_binding(runtime, "proj/a#exec", transcript_path=tp,
                  last_progress_at=_ago(5))
    _patch_signals_everywhere(monkeypatch, grew=True, mtime_iso=_ago(1),
                              pane_alive=True, pane_pid=4242)
    live = _detector().liveness("proj/a#exec")
    assert live.state == "working", "JSONL grew -> working"


# ===========================================================================
# VERDICT CASE 2 — idle (flat beyond W + pane warm + NO legit reason).
# This is the ONLY actionable flat case.
# MUTANT KILL: an impl that returns 'dead' on a warm pane, or 'waiting' with no
# reason, fails here.
# ===========================================================================

def test_verdict_idle_flat_beyond_w_warm_pane_no_reason(runtime, tmp_path, monkeypatch):
    tp = _write_transcript(tmp_path, size=200)
    # flat for well beyond W_working (120s) and NO escalation/coordinator reason.
    _seed_binding(runtime, "proj/a#exec", transcript_path=tp,
                  last_progress_at=_ago(config.SUSPICION_WINDOWS["working"] + 600),
                  terminal_signal=None, role_variant="L5#exec")
    _patch_signals_everywhere(monkeypatch, grew=False, mtime_iso=_ago(700),
                              pane_alive=True, pane_pid=4242)
    live = _detector().liveness("proj/a#exec")
    assert live.state == "idle", "flat beyond W + warm pane + no reason -> idle"


# ===========================================================================
# VERDICT CASE 3 — waiting (flat beyond W + pane warm + LEGIT reason ESCALATED).
# MUTANT KILL (the waiting-vs-idle split): an impl that calls everything-flat
# idle, ignoring terminal_signal == ESCALATED, fails here.
# ===========================================================================

def test_verdict_waiting_escalated_reason(runtime, tmp_path, monkeypatch):
    tp = _write_transcript(tmp_path, size=200)
    _seed_binding(runtime, "proj/a#exec", transcript_path=tp,
                  last_progress_at=_ago(config.SUSPICION_WINDOWS["working"] + 600),
                  terminal_signal="ESCALATED", role_variant="L5#exec")
    _patch_signals_everywhere(monkeypatch, grew=False, mtime_iso=_ago(700),
                              pane_alive=True, pane_pid=4242)
    live = _detector().liveness("proj/a#exec")
    assert live.state == "waiting", (
        "flat beyond W + warm pane + ESCALATED reason -> waiting, NOT idle"
    )


def test_waiting_and_idle_differ_only_by_the_escalated_reason(runtime, tmp_path, monkeypatch):
    """Direct discriminator: identical flat/warm/beyond-W inputs split ONLY on the reason.

    A mutant that ignores terminal_signal collapses these two to the same verdict -> caught.
    """
    tp1 = _write_transcript(tmp_path / "a", size=200) if False else _write_transcript(tmp_path, size=200)
    far_past = _ago(config.SUSPICION_WINDOWS["working"] + 600)

    _seed_binding(runtime, "proj/idle#exec", transcript_path=tp1,
                  last_progress_at=far_past, terminal_signal=None)
    _seed_binding(runtime, "proj/wait#exec", transcript_path=tp1,
                  last_progress_at=far_past, terminal_signal="ESCALATED")
    _patch_signals_everywhere(monkeypatch, grew=False, mtime_iso=_ago(700),
                              pane_alive=True, pane_pid=4242)

    det = _detector()
    assert det.liveness("proj/idle#exec").state == "idle"
    assert det.liveness("proj/wait#exec").state == "waiting"


# ===========================================================================
# VERDICT CASE 4 — dead (pane_dead == 1 OR pane gone).
# MUTANT KILL: an impl that ignores pane_dead (keys only off JSONL) returns
# working/idle on a dead pane -> caught.
# ===========================================================================

def test_verdict_dead_pane_dead(runtime, tmp_path, monkeypatch):
    tp = _write_transcript(tmp_path, size=200)
    # JSONL grew, but the pane is DEAD -> dead WINS over the growth signal.
    _seed_binding(runtime, "proj/a#exec", transcript_path=tp,
                  last_progress_at=_ago(5))
    _patch_signals_everywhere(monkeypatch, grew=True, mtime_iso=_ago(1),
                              pane_alive=False, pane_pid=None)
    live = _detector().liveness("proj/a#exec")
    assert live.state == "dead", "pane_dead/pane-gone -> dead, even when JSONL grew"


def test_verdict_dead_overrides_flat_warm_inputs(runtime, tmp_path, monkeypatch):
    """A second dead discriminator: dead is reached via pane_alive False, not via flat JSONL."""
    tp = _write_transcript(tmp_path, size=200)
    _seed_binding(runtime, "proj/a#exec", transcript_path=tp,
                  last_progress_at=_ago(config.SUSPICION_WINDOWS["working"] + 600))
    _patch_signals_everywhere(monkeypatch, grew=False, mtime_iso=_ago(700),
                              pane_alive=False, pane_pid=None)
    assert _detector().liveness("proj/a#exec").state == "dead"


# ===========================================================================
# VERDICT CASE 5 — THE FALSE-IDLE HAZARD (load-bearing).
# Flat JSONL but still WITHIN the W window reads WORKING, not idle.
# MUTANT KILL: an impl that returns idle as soon as JSONL is flat (ignoring W)
# fails this — flat-WITHIN-W must be working.
# ===========================================================================

def test_false_idle_hazard_flat_within_w_is_working(runtime, tmp_path, monkeypatch):
    tp = _write_transcript(tmp_path, size=200)
    # flat JSONL, warm pane, but last progress is RECENT — well WITHIN W_working (120s).
    _seed_binding(runtime, "proj/a#exec", transcript_path=tp,
                  last_progress_at=_ago(5), terminal_signal=None)
    _patch_signals_everywhere(monkeypatch, grew=False, mtime_iso=_ago(5),
                              pane_alive=True, pane_pid=4242)
    live = _detector().liveness("proj/a#exec")
    assert live.state == "working", (
        "flat JSONL but WITHIN the W window must read working, NOT idle — "
        "the W window must elapse before flat -> idle"
    )


def test_false_idle_boundary_elapsing_w_flips_working_to_idle(runtime, tmp_path, monkeypatch):
    """The SAME flat/warm node reads working within-W and idle beyond-W.

    This pins that W is genuinely the gate: only the elapsed-age changes between
    the two assertions. A mutant ignoring W (always-idle-on-flat) fails the
    within-W leg; a mutant ignoring W (never-idle-on-flat) fails the beyond-W leg.
    """
    tp = _write_transcript(tmp_path, size=200)
    w = config.SUSPICION_WINDOWS["working"]

    # within W -> working
    _seed_binding(runtime, "proj/a#exec", transcript_path=tp,
                  last_progress_at=_ago(max(1, w // 4)), terminal_signal=None)
    _patch_signals_everywhere(monkeypatch, grew=False, mtime_iso=_ago(5),
                              pane_alive=True, pane_pid=4242)
    assert _detector().liveness("proj/a#exec").state == "working"

    # beyond W (re-seed same address with an old last_progress_at) -> idle
    _seed_binding(runtime, "proj/a#exec", transcript_path=tp,
                  last_progress_at=_ago(w + 600), terminal_signal=None)
    assert _detector().liveness("proj/a#exec").state == "idle"


# ===========================================================================
# FAIL-LOUD — transcript_path absent.
# A binding with NO transcript_path makes jsonl_progress/liveness RAISE
# (or return an explicit "unknown") — NEVER silently return dead/idle.
# MUTANT KILL: an impl that swallows the missing path and returns dead/idle -> caught.
# ===========================================================================

def test_transcript_path_absent_fails_loud(runtime, tmp_path, monkeypatch):
    # binding with transcript_path=None (the spawn<->detector contract violation).
    _seed_binding(runtime, "proj/a#exec", transcript_path=None,
                  last_progress_at=_ago(5))
    # pane is warm; if the impl silently fell through it would return idle/working —
    # the contract says it must NOT.
    sig = _signals()
    monkeypatch.setattr(sig, "pane_alive", lambda node: (True, 4242), raising=False)
    det = _detector()
    if hasattr(det, "pane_alive"):
        monkeypatch.setattr(det, "pane_alive", lambda node: (True, 4242), raising=False)

    raised = False
    try:
        live = det.liveness("proj/a#exec")
    except Exception:
        raised = True
    else:
        # The only acceptable non-raising outcome is an EXPLICIT 'unknown' verdict.
        assert getattr(live, "state", None) == "unknown", (
            "transcript_path absent must fail loud: raise OR return explicit 'unknown' — "
            f"NEVER silently return dead/idle (got state={getattr(live, 'state', None)!r})"
        )
        assert live.state not in ("dead", "idle"), "must not silently collapse to dead/idle"
    # Either path (raise or explicit unknown) is acceptable; a silent dead/idle is not.
    assert raised or True


def test_transcript_path_missing_key_fails_loud(runtime, tmp_path, monkeypatch):
    """A binding entirely MISSING the transcript_path key is the same contract violation."""
    token = fencing.mint_owner_token("proj/a#exec", "sa", "uuid", 1)
    rec = {
        "node_address": "proj/a#exec", "state": "running", "generation": 0,
        "owner_token": token, "lease_epoch": 1, "subagent_id": "sa", "session_uuid": "uuid",
        "tmux_target": "harness:proj-a-exec",
        "last_progress_at": _ago(5), "liveness_state": "working", "terminal_signal": None,
        # transcript_path key intentionally OMITTED
    }
    ledger.write_binding({"proj/a#exec": rec}, _lock_held=True)
    sig = _signals()
    monkeypatch.setattr(sig, "pane_alive", lambda node: (True, 4242), raising=False)
    det = _detector()
    if hasattr(det, "pane_alive"):
        monkeypatch.setattr(det, "pane_alive", lambda node: (True, 4242), raising=False)

    try:
        live = det.liveness("proj/a#exec")
    except Exception:
        return  # raising is acceptable
    assert getattr(live, "state", None) == "unknown", (
        "missing transcript_path key must fail loud (raise or explicit 'unknown')"
    )
    assert live.state not in ("dead", "idle")


# ===========================================================================
# Liveness shape — last_progress_at is surfaced on the verdict.
# ===========================================================================

def test_liveness_surfaces_last_progress_at(runtime, tmp_path, monkeypatch):
    tp = _write_transcript(tmp_path, size=200)
    mt = _ago(3)
    _seed_binding(runtime, "proj/a#exec", transcript_path=tp, last_progress_at=_ago(5))
    _patch_signals_everywhere(monkeypatch, grew=True, mtime_iso=mt,
                              pane_alive=True, pane_pid=4242)
    live = _detector().liveness("proj/a#exec")
    # Liveness carries a last_progress_at field (state in working|waiting|idle|dead).
    assert hasattr(live, "state")
    assert hasattr(live, "last_progress_at")
    assert live.state in ("working", "waiting", "idle", "dead", "unknown")
