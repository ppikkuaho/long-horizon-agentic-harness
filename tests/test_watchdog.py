"""Increment 11 — watchdog.* FROZEN acceptance (the liveness lifecycle).

Cluster ② — terminal-signal collapse + the leaf idle->prod->FAILED ladder + the
③-wake trigger + the coordinator-death probe.

Authoritative sources (grounded, not recalled):
  - IMPLEMENTATION-PLAN §2.9 (the FROZEN watchdog.py interface — transcribed below).
  - IMPLEMENTATION-PLAN Increment-11 Done-test (L779-788) + §4.1 test battery (L564-587).
  - design/WATCHDOG.md §3.5 (the two-counter discipline + stale-grace), §4 (the
    sign-off-or-fail path / prod gate / FAILED-via-executor + actor='harnessd'),
    §5.1 (the coordinator process-death probe; dead-pid + live-children = recoverable
    orphan -> ESCALATE).
  - design/DAEMON.md §3.6 (the TERMINAL_VOCAB mapping) — states.TERMINAL_VOCAB.

FROZEN INTERFACE (§2.9 — transcribed exactly):
    check_leaf(node, binding, *, now) -> WatchdogAction
        # STEP A (TERMINAL-SIGNAL FIRST): sig = detector_signals.read_terminal_signal(node, binding).
        #   sig present & fenced: DONE/FAILED -> COLLAPSE (via chokepoint.collapse / the executor);
        #   ESCALATED -> NOOP (holds its slot, NEVER collapses).
        #   sig present but STALE owner_token -> ignore (journal stale_return_ignored), fall through to liveness.
        # STEP B (no actionable signal): liveness(node); idle + age>W -> PROD (gated by prod_precondition)
        #   up to stale_grace_checks, else FAILED.
        # CLOSING ACTION on FAILED (v1 floor): mark running->failed via the executor (actor='harnessd',
        #   reason='watchdog_nonresponse') AND ESCALATE TO THE PARENT. v1 does NOT auto-respawn from harnessd.
    prod_precondition(node) -> bool       # capture-pane shows an idle input prompt (FORK-PROMPT)
    confirm_prod_worked(node, jsonl_size_before) -> bool  # re-read JSONL; True iff a new turn appeared
    inbox_has_unacked(node, binding) -> bool  # tail <node>/.inbox.jsonl; True iff a line was appended
                                              #   AFTER binding.last_inbox_acked_offset (edge-triggered)
    wake_keystroke(node) -> str           # the ③-wake send-keys POINTER ("...re-read <node>/.inbox.jsonl...")
    check_coordinator_death(node, binding, ledger) -> WatchdogAction
        # dead-pid + LIVE children -> ESCALATE (recoverable orphan); quiet pane-alive + live children -> waiting.

BIAS TO REAL (Lesson 7): the executor + on-disk ledger are REAL; the .signal.json and .inbox.jsonl are
REAL files read by the REAL detector_signals.read_terminal_signal / inbox tail; a COLLAPSE/FAILED routes
through the REAL executor (asserted via the REAL ledger). The ONLY injected mock is detector.liveness
(the verdict) — justified: the within-W TIMING was validated for real in Inc 6 + the Inc 9 tmux contract,
so the watchdog LADDER is tested deterministically by driving the verdict (working/idle/...).

NO IMPLEMENTATION here — harnessd/watchdog.py does not exist yet. RED first.
"""

from __future__ import annotations

import copy
import importlib
import json
from datetime import datetime, timedelta, timezone

import pytest

import harnessd.config as config
import harnessd.detector as detector
import harnessd.detector_signals as detector_signals
import harnessd.fencing as fencing
import harnessd.ledger as ledger
from harnessd.detector import Liveness


# ===========================================================================
# Module-under-test loader (the module does not exist yet -> RED on import).
# ===========================================================================

def _wd():
    return importlib.import_module("harnessd.watchdog")


# ===========================================================================
# Runtime fixture — bind ledger.RUNTIME_ROOT to tmp_path so the REAL executor's
# pathless ledger calls (read_binding/append_wal/write_binding), the EX lock, AND
# detector_signals' .signal.json / .inbox.jsonl resolution all land under tmp_path.
# ===========================================================================

@pytest.fixture
def runtime(tmp_path, monkeypatch):
    monkeypatch.setattr(ledger, "RUNTIME_ROOT", tmp_path)
    # Clear detector_signals' private size cache so a fresh tmp transcript reads a clean baseline.
    monkeypatch.setattr(detector_signals, "_size_cache", {}, raising=False)
    return tmp_path


# ===========================================================================
# The ONE justified mock: inject the liveness verdict deterministically.
#
# The §2.9 contract has check_leaf read liveness(node) in STEP B. The frozen
# interface does not fix HOW the watchdog reaches it; the established precedent in
# this codebase is a module-level injectable (ledger.RUNTIME_ROOT,
# chokepoint.set_adapter). We bind the verdict through whichever seam the impl
# exposes and ALSO patch detector.liveness as the belt-and-suspenders default, so a
# correct impl that calls detector.liveness directly is honored too.
# ===========================================================================

def _inject_liveness(monkeypatch, wd, verdict_fn):
    """Drive the watchdog's liveness verdict deterministically (the one justified mock).

    verdict_fn(node_address) -> Liveness. Bound through every plausible seam the frozen
    interface permits, so a conformant impl (whatever its injection style) is driven:
      * a watchdog module-level set_liveness(fn) / LIVENESS attribute, if present;
      * detector.liveness itself (the live module attribute the detector calls through).
    """
    if hasattr(wd, "set_liveness"):
        wd.set_liveness(verdict_fn)
    elif hasattr(wd, "LIVENESS"):
        monkeypatch.setattr(wd, "LIVENESS", verdict_fn, raising=False)
    # Belt-and-suspenders: patch the live detector.liveness attribute (the seam the
    # detector module itself exposes). check_leaf receives a single-arg node_address-or-node;
    # accept either shape.
    def _by_address(node_or_address):
        addr = node_or_address if isinstance(node_or_address, str) else node_or_address["node_address"]
        return verdict_fn(addr)

    monkeypatch.setattr(detector, "liveness", _by_address, raising=True)


def _const_liveness(state, last_progress_at):
    def _fn(_node_address):
        return Liveness(state=state, last_progress_at=last_progress_at)
    return _fn


# ===========================================================================
# Seeding helpers — write REAL bindings through the REAL ledger; write REAL
# .signal.json / .inbox.jsonl files under the REAL runtime tree.
# ===========================================================================

LEAF = "proj/widget#exec"
PARENT = "proj#exec"
COORD = "proj#exec"
SUBAGENT = "subagent-aaaa1111"
SESSION = "sess-uuid-seed-0001"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ago_iso(seconds: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(seconds=seconds)).isoformat()


def _binding(
    *,
    node_address=LEAF,
    parent_address=PARENT,
    state="running",
    generation=0,
    lease_epoch=1,
    subagent_id=SUBAGENT,
    session_uuid=SESSION,
    transcript_path=None,
    last_progress_at=None,
    last_inbox_acked_offset=0,
    stale_check_count=0,
    stale_grace_checks=2,
    level="L5",
    extra=None,
):
    token = fencing.mint_owner_token(node_address, subagent_id, session_uuid, lease_epoch)
    rec = {
        "node_address": node_address,
        "parent_address": parent_address,
        "level": level,
        "subagent_id": subagent_id,
        "session_uuid": session_uuid,
        "state": state,
        "generation": generation,
        "lease_epoch": lease_epoch,
        "owner_token": token,
        "last_applied_seq": 0,
        "liveness_state": "idle",
        "last_progress_at": last_progress_at,
        "last_inbox_acked_offset": last_inbox_acked_offset,
        "stale_check_count": stale_check_count,
        "stale_grace_checks": stale_grace_checks,
        "recovery_attempts": 0,
        "gate_crossed_at": None,
        "paused_at": None,
        "transcript_path": transcript_path,
        "terminal_signal": None,
    }
    if extra:
        rec.update(extra)
    return rec, token


def _seed(bindings):
    ledger.write_binding({b["node_address"]: copy.deepcopy(b) for b in bindings}, _lock_held=True)


def _read(node=LEAF):
    return ledger.read_binding(node)


import harnessd.addressing as _addressing


def _node_dir(runtime, node_address):
    d = _addressing.node_dir(node_address, runtime)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _write_signal(runtime, node_address, *, signal, owner_token, evidence=None):
    # Same canonical derivation the reader uses (nested dir + per-seat .signal.<seat>.json).
    p = _addressing.signal_path(node_address, runtime)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "signal": signal,
        "ts": _now_iso(),
        "owner_token": owner_token,
        "evidence": evidence or {},
    }
    p.write_text(json.dumps(payload))
    return payload


def _append_inbox(runtime, node_address, line: dict) -> int:
    """Append one JSONL line to the per-seat wake inbox (addressing.inbox_path). Return new size."""
    p = _addressing.inbox_path(node_address, runtime)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(line) + "\n")
    return p.stat().st_size


def _node_from(binding):
    return {
        "node_address": binding["node_address"],
        "transcript_path": binding.get("transcript_path"),
        "tmux_target": binding.get("tmux_target", "harness:t"),
    }


def _write_wal_record(*, node_address, event, from_state="running", to_state="running"):
    """Append one REAL framed WAL row directly (used to seed a coordinator_died EVENT)."""
    rec = ledger.build_wal_record(
        node_address=node_address,
        event=event,
        from_state=from_state,
        to_state=to_state,
        expected_generation=None,
        generation=None,
        lease_epoch=None,
        owner_token=None,
        binding_delta={},
        summary=f"seeded {event} event",
        artifacts=[],
        seq=ledger.next_seq(),
    )
    ledger.append_wal(rec)
    return rec


# ===========================================================================
# WatchdogAction tag normalization — the result type is a TAGGED action
# (COLLAPSE / NOOP / PROD / FAILED / ESCALATE / WAKE / ...). We do NOT over-fix its
# concrete shape; we read a tag robustly so the tests bind to the BEHAVIOR (which
# action fired), not an incidental field name.
# ===========================================================================

def _tag(action) -> str:
    """Best-effort uppercase tag for a WatchdogAction (kind/tag/action attr, an enum .name, or repr)."""
    for attr in ("kind", "tag", "action", "name", "type", "verb"):
        val = getattr(action, attr, None)
        if isinstance(val, str) and val:
            return val.upper()
        # an Enum-valued attr
        inner = getattr(val, "name", None)
        if isinstance(inner, str) and inner:
            return inner.upper()
    # an Enum action itself
    inner = getattr(action, "name", None)
    if isinstance(inner, str) and inner:
        return inner.upper()
    return repr(action).upper()


def _is(action, *expected_tags) -> bool:
    t = _tag(action)
    return any(e.upper() in t for e in expected_tags)


# ===========================================================================
# BATTERY 1 — the §4.1 terminal-signal-reader battery (TERMINAL-SIGNAL FIRST).
# DONE+live-token -> COLLAPSE; DONE+stale-token -> ignored (binding UNCHANGED,
# journal stale_return_ignored); ESCALATED -> NOOP; absent -> fall through.
# ===========================================================================

def test_done_signal_live_token_collapses(runtime):
    """A fenced DONE .signal.json -> COLLAPSE, routed through the REAL executor/ledger.

    LOAD-BEARING (terminal-signal FIRST): the node's liveness verdict is driven to `idle`
    — a mutant that read liveness FIRST would FAILED an idle node instead of COLLAPSE on
    the DONE signal. Asserting COLLAPSE (and the REAL terminal collapse on disk) kills it.
    """
    wd = _wd()
    binding, token = _binding(state="running", generation=4, lease_epoch=2)
    _seed([binding])
    _write_signal(runtime, LEAF, signal="DONE", owner_token=token, evidence={"report": "report.md"})

    # liveness would say idle (so a liveness-first impl would mis-FAIL) — but terminal-signal wins.
    import harnessd.watchdog as _mod
    monkeypatch_holder = pytest.MonkeyPatch()
    try:
        _inject_liveness(monkeypatch_holder, _mod, _const_liveness("idle", _ago_iso(9999)))
        action = wd.check_leaf(_node_from(binding), _read(), now=_now_iso())
    finally:
        monkeypatch_holder.undo()

    assert _is(action, "COLLAPSE"), f"a fenced DONE signal must COLLAPSE (got tag {_tag(action)!r})"
    # The REAL executor routed the terminal collapse: the live binding is now `done` (not failed).
    after = _read()
    assert after["state"] == "done", (
        "a DONE collapse routes running->done through the REAL executor (terminal-signal FIRST: "
        "an idle liveness verdict must NOT FAIL the node)"
    )
    assert after["terminal_signal"] == "DONE"


def test_failed_signal_live_token_collapses(runtime):
    """A fenced FAILED .signal.json -> COLLAPSE (running->failed via the REAL executor)."""
    wd = _wd()
    binding, token = _binding(state="running", generation=1, lease_epoch=1)
    _seed([binding])
    _write_signal(runtime, LEAF, signal="FAILED", owner_token=token)

    import harnessd.watchdog as _mod
    mp = pytest.MonkeyPatch()
    try:
        _inject_liveness(mp, _mod, _const_liveness("working", _now_iso()))
        action = wd.check_leaf(_node_from(binding), _read(), now=_now_iso())
    finally:
        mp.undo()

    assert _is(action, "COLLAPSE"), f"a fenced FAILED signal must COLLAPSE (got {_tag(action)!r})"
    assert _read()["state"] == "failed"


def test_stale_token_signal_ignored_binding_unchanged(runtime):
    """A DONE signal with a STALE owner_token is IGNORED — binding byte-for-byte UNCHANGED.

    LOAD-BEARING (the fence): a dead incarnation's leftover DONE (epoch 1) must NEVER
    collapse a re-spawned node (epoch 3). A mutant that honors a stale signal collapses the
    live node -> caught by the unchanged-binding assertion (state stays running, no collapse).
    The watchdog journals stale_return_ignored (or simply falls through to liveness); either
    way the LIVE binding is unchanged and is NOT collapsed.
    """
    wd = _wd()
    binding, live_token = _binding(state="running", generation=5, lease_epoch=3)
    _seed([binding])
    before = copy.deepcopy(_read())
    # leftover from a PRIOR incarnation (epoch 1), a DIFFERENT token than the live one.
    stale_token = fencing.mint_owner_token(LEAF, "sa-old", "uuid-old", 1)
    assert stale_token != live_token
    _write_signal(runtime, LEAF, signal="DONE", owner_token=stale_token)

    import harnessd.watchdog as _mod
    mp = pytest.MonkeyPatch()
    try:
        # Drive liveness to `working` so STEP B (fall-through) is a NOOP — isolating the fence.
        _inject_liveness(mp, _mod, _const_liveness("working", _now_iso()))
        action = wd.check_leaf(_node_from(binding), _read(), now=_now_iso())
    finally:
        mp.undo()

    after = _read()
    assert after["state"] == "running", "a stale-token signal must NOT collapse the live re-spawned node"
    assert after == before, (
        "a STALE-token terminal signal is IGNORED: the live binding must be byte-for-byte UNCHANGED "
        "(no collapse, no state/epoch mutation)"
    )
    assert not _is(action, "COLLAPSE"), "a stale-token signal must never produce a COLLAPSE action"


def test_escalated_signal_is_noop_never_collapses(runtime):
    """A fenced ESCALATED signal -> NOOP. ESCALATED HOLDS ITS SLOT — never collapses — AND the
    slot-hold is JOURNALED (SML-02): the binding carries terminal_signal=ESCALATED and the WAL
    gains the §3.6 signal_ESCALATED running->running row (exactly once across ticks).

    LOAD-BEARING: a mutant that routes ESCALATED to collapse tears a waiting node off its slot
    while it waits for the answer round-trip; a bare-NOOP mutant (no journal) leaves the durable
    ledger blind to the escalation. Both are killed here.
    """
    wd = _wd()
    binding, token = _binding(state="running", generation=2, lease_epoch=1)
    _seed([binding])
    _write_signal(runtime, LEAF, signal="ESCALATED", owner_token=token)
    wal_before = len(ledger.load_wal())

    import harnessd.watchdog as _mod
    mp = pytest.MonkeyPatch()
    try:
        _inject_liveness(mp, _mod, _const_liveness("waiting", _now_iso()))
        action = wd.check_leaf(_node_from(binding), _read(), now=_now_iso())
    finally:
        mp.undo()

    assert _is(action, "NOOP", "NONE", "WAIT"), (
        f"ESCALATED must be NOOP (holds its slot), never a collapse — got {_tag(action)!r}"
    )
    assert not _is(action, "COLLAPSE", "FAILED"), "ESCALATED must NEVER collapse or fail the node"
    after = _read()
    assert after["state"] == "running", "an ESCALATED node stays running (asymmetric §3.6)"
    # SML-02: the slot-hold is DURABLE — terminal_signal stamped + signal_ESCALATED journaled.
    assert after.get("terminal_signal") == "ESCALATED", (
        "check_leaf must stamp terminal_signal=ESCALATED on the binding (the §3.6 slot-hold fact)"
    )
    escalated_rows = [
        r for r in ledger.load_wal()[wal_before:]
        if r.get("node_address") == LEAF and r.get("event") == "signal_ESCALATED"
    ]
    assert len(escalated_rows) == 1, (
        f"the ESCALATED slot-hold must journal exactly ONE signal_ESCALATED WAL row; got {len(escalated_rows)}"
    )

    # A SECOND tick re-reads the same artifact: still NOOP, NO second journal row (exactly-once).
    mp2 = pytest.MonkeyPatch()
    try:
        _inject_liveness(mp2, _mod, _const_liveness("waiting", _now_iso()))
        action2 = wd.check_leaf(_node_from(binding), _read(), now=_now_iso())
    finally:
        mp2.undo()
    assert _is(action2, "NOOP", "NONE", "WAIT"), "the second tick holds the slot too"
    escalated_rows_2 = [
        r for r in ledger.load_wal()[wal_before:]
        if r.get("node_address") == LEAF and r.get("event") == "signal_ESCALATED"
    ]
    assert len(escalated_rows_2) == 1, (
        "exactly-once: a second tick over the SAME ESCALATED artifact must NOT journal a second row"
    )


def test_escalated_signal_journal_failure_is_routed_not_reported_clean(runtime):
    """A FENCED/CAS abort on the ESCALATED journal write must be ROUTED (NOOP with
    reason=escalate_journal_failed + the errors), never read as a clean slot-hold.

    Setup: the binding handed to check_leaf is a STALE incarnation (old epoch/token) whose
    matching .signal.json passes the READER's fence, but the LIVE ledger binding has rotated
    (re-claimed at a higher epoch) — so the escalate write aborts on the executor's fencing
    precondition. Mutant killed: treat any escalate outcome as a clean 'escalated_holds_slot'
    (the result-swallowing branch).
    """
    wd = _wd()
    # The STALE incarnation (epoch 1) — the .signal.json carries ITS token, so the reader admits it.
    stale_binding, stale_token = _binding(state="running", generation=2, lease_epoch=1)
    # The LIVE binding: same address re-claimed at a HIGHER epoch (token rotated).
    live_binding, live_token = _binding(state="running", generation=5, lease_epoch=3,
                                        session_uuid="sess-uuid-live-0002")
    _seed([live_binding])
    _write_signal(runtime, LEAF, signal="ESCALATED", owner_token=stale_token)
    before = copy.deepcopy(_read())
    wal_before = len(ledger.load_wal())

    import harnessd.watchdog as _mod
    mp = pytest.MonkeyPatch()
    try:
        _inject_liveness(mp, _mod, _const_liveness("waiting", _now_iso()))
        action = wd.check_leaf(_node_from(stale_binding), stale_binding, now=_now_iso())
    finally:
        mp.undo()

    assert _is(action, "NOOP", "NONE", "WAIT"), "the aborted journal write still NOOPs (next tick retries)"
    detail = getattr(action, "detail", {}) or {}
    assert detail.get("reason") == "escalate_journal_failed", (
        f"a fenced/CAS-aborted escalate must be routed as escalate_journal_failed, got {detail!r}"
    )
    assert detail.get("errors"), "the routed abort must carry the executor's errors"
    after = _read()
    assert after["state"] == "running" and after.get("terminal_signal") != "ESCALATED", (
        "the LIVE binding must be untouched by the stale incarnation's escalate (non-destructive fence)"
    )
    assert after == before, "the live binding is byte-for-byte unchanged (the §3.6 FENCED de-auth)"
    new_events = [r.get("event") for r in ledger.load_wal()[wal_before:]]
    assert "signal_ESCALATED" not in new_events, (
        "a fenced escalate must NOT land a signal_ESCALATED row for the stale incarnation"
    )


def test_absent_signal_falls_through_to_liveness(runtime):
    """No .signal.json -> STEP A yields nothing -> fall through to the STEP B liveness ladder.

    With liveness driven to `working`, the fall-through is a NOOP (the node is fine). This pins
    that an absent signal is NOT itself a terminal event (read_terminal_signal returns None).
    """
    wd = _wd()
    binding, _token = _binding(state="running", generation=0, lease_epoch=1)
    _seed([binding])
    _node_dir(runtime, LEAF)  # dir exists, NO .signal.json

    import harnessd.watchdog as _mod
    mp = pytest.MonkeyPatch()
    try:
        _inject_liveness(mp, _mod, _const_liveness("working", _now_iso()))
        action = wd.check_leaf(_node_from(binding), _read(), now=_now_iso())
    finally:
        mp.undo()

    assert not _is(action, "COLLAPSE"), "an absent signal is not a terminal event -> no collapse"
    assert _read()["state"] == "running"


# ===========================================================================
# BATTERY 2 — the watchdog-leaf battery (idle->prod->FAILED ladder, two-counter).
# idle+age>W -> PROD (gated); repeated idle past grace -> FAILED; FAILED -> marks
# failed via the executor (actor='harnessd') AND ESCALATES TO PARENT, NOT respawn.
# ===========================================================================

def _patch_prod_gate(mp, wd, allow: bool):
    """Force prod_precondition (the prompt-string/capture-pane gate) to a deterministic value.

    The gate reads a real captured pane in production; here it is the second-most natural seam to
    drive (alongside the liveness verdict). We patch the module attribute the impl exposes.
    """
    if hasattr(wd, "prod_precondition"):
        mp.setattr(wd, "prod_precondition", lambda _node: allow, raising=True)


def test_idle_beyond_w_prods_when_gated_open(runtime):
    """idle + age>W + prod gate OPEN + within grace -> PROD (a nudge, NOT a collapse/fail).

    LOAD-BEARING (the ladder respects grace before FAILED): with stale_check_count below
    stale_grace_checks, the first idle poll PRODS — it does NOT FAIL. A mutant that fails on
    first idle is caught (this asserts PROD, and the node stays running).
    """
    wd = _wd()
    binding, _token = _binding(
        state="running", generation=0, lease_epoch=1,
        last_progress_at=_ago_iso(9999), stale_check_count=0, stale_grace_checks=2,
    )
    _seed([binding])

    import harnessd.watchdog as _mod
    mp = pytest.MonkeyPatch()
    try:
        _inject_liveness(mp, _mod, _const_liveness("idle", _ago_iso(9999)))
        _patch_prod_gate(mp, _mod, allow=True)
        action = wd.check_leaf(_node_from(binding), _read(), now=_now_iso())
    finally:
        mp.undo()

    assert _is(action, "PROD"), f"idle within grace + gate open must PROD (got {_tag(action)!r})"
    assert not _is(action, "FAILED", "COLLAPSE"), "a first idle poll within grace must NOT fail the node"
    assert _read()["state"] == "running", "a prodded node is still running (not yet failed)"


def test_prod_gate_blocks_mid_tool_call(runtime):
    """prod_precondition False (pane NOT at the idle prompt) -> NO prod fired.

    LOAD-BEARING: a send-keys nudge that lands mid-tool-call corrupts the input line. The gate is
    what prevents it. A mutant that prods regardless of the gate -> caught (assert NOT a PROD).
    """
    wd = _wd()
    binding, _token = _binding(
        state="running", generation=0, lease_epoch=1,
        last_progress_at=_ago_iso(9999), stale_check_count=0, stale_grace_checks=2,
    )
    _seed([binding])

    import harnessd.watchdog as _mod
    mp = pytest.MonkeyPatch()
    try:
        _inject_liveness(mp, _mod, _const_liveness("idle", _ago_iso(9999)))
        _patch_prod_gate(mp, _mod, allow=False)
        action = wd.check_leaf(_node_from(binding), _read(), now=_now_iso())
    finally:
        mp.undo()

    assert not _is(action, "PROD"), (
        f"the prod gate (prod_precondition False) must SUPPRESS the prod — got {_tag(action)!r}"
    )


def test_repeated_idle_past_grace_marks_failed_via_executor(runtime):
    """idle past stale_grace_checks -> FAILED, marked through the REAL executor.

    LOAD-BEARING (bounded prods THEN failed): only once stale_check_count has reached the grace
    threshold does the ladder mark FAILED. The FAILED is written through the REAL executor — the
    live binding on disk goes running->failed. A mutant that fails on first idle is killed by the
    grace-respecting PROD test above; this one proves the terminal rung is reached AT grace.
    """
    wd = _wd()
    binding, _token = _binding(
        state="running", generation=0, lease_epoch=1,
        last_progress_at=_ago_iso(9999),
        stale_check_count=2, stale_grace_checks=2,   # already AT grace -> this poll fails
    )
    _seed([binding])

    import harnessd.watchdog as _mod
    mp = pytest.MonkeyPatch()
    try:
        _inject_liveness(mp, _mod, _const_liveness("idle", _ago_iso(9999)))
        _patch_prod_gate(mp, _mod, allow=True)
        action = wd.check_leaf(_node_from(binding), _read(), now=_now_iso())
    finally:
        mp.undo()

    assert _is(action, "FAILED", "ESCALATE"), (
        f"idle AT/over grace must mark FAILED (got {_tag(action)!r})"
    )
    after = _read()
    assert after["state"] == "failed", (
        "the watchdog marks running->failed through the REAL executor once the prod ladder exhausts"
    )


def test_watchdog_failed_row_marked_harnessd_nonresponse(runtime):
    """The watchdog-imposed FAILED row carries actor='harnessd' + reason watchdog_nonresponse.

    Distinguishes a watchdog-declared FAILED (no .signal.json) from an agent-self-emitted FAILED.
    Asserted against the REAL run-ledger (load_wal).
    """
    wd = _wd()
    binding, _token = _binding(
        state="running", generation=0, lease_epoch=1,
        last_progress_at=_ago_iso(9999),
        stale_check_count=2, stale_grace_checks=2,
    )
    _seed([binding])

    import harnessd.watchdog as _mod
    mp = pytest.MonkeyPatch()
    try:
        _inject_liveness(mp, _mod, _const_liveness("idle", _ago_iso(9999)))
        _patch_prod_gate(mp, _mod, allow=True)
        wd.check_leaf(_node_from(binding), _read(), now=_now_iso())
    finally:
        mp.undo()

    wal = ledger.load_wal()
    # The failing row: state landed in failed, written by the single writer (actor harnessd).
    fail_rows = [r for r in wal if r.get("to_state") == "failed" and r.get("node_address") == LEAF]
    assert fail_rows, "a watchdog FAILED must append a run-ledger row landing in `failed`"
    row = fail_rows[-1]
    assert row.get("actor") == "harnessd", "the watchdog FAILED row is written by actor='harnessd'"
    blob = json.dumps(row).lower()
    assert "watchdog_nonresponse" in blob or "watchdog" in blob, (
        "the watchdog-imposed FAILED must carry a watchdog_nonresponse reason (distinct from an "
        "agent-self-emitted FAILED)"
    )


def test_watchdog_failed_escalates_to_parent_not_respawn(runtime):
    """A FAILED leaf ESCALATES TO THE PARENT and does NOT auto-respawn from harnessd.

    LOAD-BEARING (the v1 closing action): the watchdog marks FAILED + escalates to the parent
    (who re-claims at the stable address); harnessd does NOT itself spawn/resume the leaf. A
    mutant that auto-respawns from harnessd is caught by:
      (1) the returned action escalates to the parent (carries the parent address), AND
      (2) NO fresh spawn/claim/resume WAL row appears for the leaf (no slot_claimed/spawn_open/
          spawn_running/release_claim after the FAILED).
    """
    wd = _wd()
    binding, _token = _binding(
        state="running", generation=0, lease_epoch=1, parent_address=PARENT,
        last_progress_at=_ago_iso(9999),
        stale_check_count=2, stale_grace_checks=2,
    )
    # Seed the parent too so the escalation has a real parent address to target.
    parent, _pt = _binding(node_address=PARENT, parent_address="", state="running", generation=3, lease_epoch=2)
    _seed([binding, parent])

    import harnessd.watchdog as _mod
    mp = pytest.MonkeyPatch()
    try:
        _inject_liveness(mp, _mod, _const_liveness("idle", _ago_iso(9999)))
        _patch_prod_gate(mp, _mod, allow=True)
        action = wd.check_leaf(_node_from(binding), _read(), now=_now_iso())
    finally:
        mp.undo()

    # (1) The action escalates to the PARENT (the parent re-claims at the stable address).
    assert _is(action, "ESCALATE", "FAILED"), f"a FAILED leaf must escalate to the parent (got {_tag(action)!r})"
    blob = (repr(action) + json.dumps(getattr(action, "__dict__", {}), default=str)).lower()
    assert PARENT.lower() in blob or "parent" in blob, (
        "the FAILED closing action must be parent-directed (the parent re-claims at the stable address)"
    )

    # (2) harnessd does NOT auto-respawn: no fresh spawn/claim/resume row for the leaf.
    wal = ledger.load_wal()
    respawn_events = {"slot_claimed", "claim", "spawn_open", "spawn_running", "release_claim", "resume"}
    leaf_respawn_rows = [
        r for r in wal
        if r.get("node_address") == LEAF and r.get("event") in respawn_events
    ]
    assert not leaf_respawn_rows, (
        "v1 does NOT auto-respawn from harnessd: a watchdog FAILED must NOT emit a fresh "
        f"spawn/claim/resume for the leaf (found {[r.get('event') for r in leaf_respawn_rows]})"
    )
    # The leaf is left `failed` (the parent acts next), never re-driven back to claimed/running here.
    assert _read()["state"] == "failed"


def test_escalated_leaf_is_never_prodded(runtime):
    """An ESCALATED leaf reads `waiting` and is NEVER prodded (it holds its slot, §2.4/§4.1).

    A fenced ESCALATED signal routes to NOOP at STEP A — the prod ladder is never entered, so no
    PROD/FAILED/COLLAPSE fires even though it is flat-beyond-W.
    """
    wd = _wd()
    binding, token = _binding(state="running", generation=0, lease_epoch=1, last_progress_at=_ago_iso(9999))
    _seed([binding])
    _write_signal(runtime, LEAF, signal="ESCALATED", owner_token=token)

    import harnessd.watchdog as _mod
    mp = pytest.MonkeyPatch()
    try:
        _inject_liveness(mp, _mod, _const_liveness("waiting", _ago_iso(9999)))
        _patch_prod_gate(mp, _mod, allow=True)
        action = wd.check_leaf(_node_from(binding), _read(), now=_now_iso())
    finally:
        mp.undo()

    assert not _is(action, "PROD", "FAILED", "COLLAPSE"), (
        f"an ESCALATED (waiting) leaf must never be prodded or failed — got {_tag(action)!r}"
    )
    assert _read()["state"] == "running"


# ===========================================================================
# BATTERY 2b — prod helpers: prod_precondition / confirm_prod_worked (verify-new-turn).
# ===========================================================================

def test_confirm_prod_worked_true_only_on_new_turn(runtime, tmp_path):
    """confirm_prod_worked re-reads the JSONL: True iff a NEW turn appeared since the prod.

    send-keys is fire-and-forget (no ack); the watchdog confirms a prod 'worked' ONLY by observing
    forward progress (a grown transcript), never by assuming the keystroke landed.
    """
    wd = _wd()
    p = tmp_path / "transcript.jsonl"
    p.write_bytes(b"turn-1\n")
    size_before = p.stat().st_size
    binding, _t = _binding(state="running", transcript_path=str(p))
    node = _node_from(binding)

    # No new turn yet -> not confirmed.
    assert wd.confirm_prod_worked(node, size_before) is False, (
        "no new JSONL turn since the prod -> confirm_prod_worked False (no blind trust of send-keys)"
    )

    # A new turn appended -> confirmed.
    p.write_bytes(b"turn-1\nturn-2\n")
    assert wd.confirm_prod_worked(node, size_before) is True, (
        "a new JSONL turn after the prod -> confirm_prod_worked True (forward progress observed)"
    )


# ===========================================================================
# BATTERY 3 — the ③-wake battery (EDGE-TRIGGERED: one nudge per NEW inbox line).
# inbox_has_unacked True iff a line was appended AFTER last_inbox_acked_offset;
# wake_keystroke is a POINTER, never a payload.
# ===========================================================================

def test_inbox_unacked_true_for_line_past_watermark(runtime):
    """A line appended PAST last_inbox_acked_offset -> inbox_has_unacked True (the wake TRIGGER)."""
    wd = _wd()
    binding, _t = _binding(state="running", last_inbox_acked_offset=0)
    _seed([binding])
    _append_inbox(runtime, LEAF, {"from": "parent", "msg": "new message"})

    assert wd.inbox_has_unacked(_node_from(binding), _read()) is True, (
        "a line appended past last_inbox_acked_offset is UNACKED -> the wake trigger fires"
    )


def test_inbox_no_new_line_no_nudge(runtime):
    """No append past the watermark -> inbox_has_unacked False (EDGE-TRIGGERED, no storm).

    LOAD-BEARING (edge-triggered): with the watermark already at end-of-file (everything acked),
    a re-poll with NOTHING new returns False. A mutant that nudges every poll (or with nothing new)
    is caught here.
    """
    wd = _wd()
    # Seed one line, then set the acked watermark to the current end-of-file (all caught up).
    size = _append_inbox(runtime, LEAF, {"from": "parent", "msg": "already read"})
    binding, _t = _binding(state="running", last_inbox_acked_offset=size)
    _seed([binding])

    assert wd.inbox_has_unacked(_node_from(binding), _read()) is False, (
        "no line appended past the acked offset -> NO unacked -> NO nudge (edge-triggered, not per-poll)"
    )


def test_inbox_one_nudge_per_new_line_edge_triggered(runtime):
    """Exactly ONE nudge per NEW line: after acking, a re-poll with nothing new yields no further nudge.

    LOAD-BEARING (one per new line): append a line -> unacked True (one nudge owed). Advance the
    acked watermark to end-of-file (the nudge consumed it) -> a re-poll yields False (no second
    nudge for the same line). A mutant that re-nudges an already-acked line is caught.
    """
    wd = _wd()
    binding0, _t = _binding(state="running", last_inbox_acked_offset=0)
    _seed([binding0])
    size_after_line = _append_inbox(runtime, LEAF, {"from": "parent", "msg": "wake up"})

    # First poll: a new line is unacked -> the trigger fires (one nudge owed).
    assert wd.inbox_has_unacked(_node_from(binding0), _read()) is True

    # The nudge consumed the line: advance the watermark to end-of-file (the ack).
    acked, _t2 = _binding(state="running", last_inbox_acked_offset=size_after_line)
    _seed([acked])

    # Second poll, NOTHING new appended: no further nudge (edge-triggered, one per new line).
    assert wd.inbox_has_unacked(_node_from(acked), _read()) is False, (
        "after acking the line, a re-poll with nothing new must NOT fire a second nudge (one per new line)"
    )


def test_wake_keystroke_is_a_pointer_not_a_payload(runtime):
    """wake_keystroke returns a POINTER ('re-read your inbox / resume'), NEVER a fact/payload.

    The agent's prompt loop does the actual per-turn re-read; the keystroke is only a pointer to
    the inbox file. A mutant that stuffs the message content into the keystroke is caught: the
    pointer must name the inbox re-read, not carry the message body.
    """
    wd = _wd()
    binding, _t = _binding(state="running")
    payload = wd.wake_keystroke(_node_from(binding))
    assert isinstance(payload, str) and payload.strip(), "wake_keystroke is a non-empty send-keys string"
    low = payload.lower()
    assert "inbox" in low and ("re-read" in low or "reread" in low or "read" in low), (
        "the wake keystroke must POINT at the inbox re-read (a pointer), never carry a payload/fact"
    )


# ===========================================================================
# BATTERY 4 — the coordinator-death battery.
# dead-pid + live children -> ESCALATE (recoverable orphan, recover-vs-reap deferred);
# quiet pane-alive + live children -> waiting (not dead).
# ===========================================================================

def test_coordinator_dead_pid_live_children_escalates(runtime):
    """A dead-pid coordinator WITH live children -> ESCALATE (recoverable orphan, NOT reap).

    LOAD-BEARING (recover-vs-reap deferred): a coordinator whose process died but whose children
    are still alive is a recoverable orphan — v1 ESCALATES (the choice is deferred, §5.2/§5.5). A
    mutant that REAPS it (collapses to failed/dead unilaterally) is caught: the action must be
    ESCALATE, never a collapse/reap.
    """
    wd = _wd()
    coord, _ct = _binding(node_address=COORD, parent_address="", state="dead", level="L3", generation=2, lease_epoch=2)
    # A LIVE child below (running) — the disambiguator that makes the dead coordinator an orphan.
    child, _cht = _binding(node_address="proj/child#exec", parent_address=COORD, state="running", generation=0, lease_epoch=1)
    _seed([coord, child])
    # A coordinator_died EVENT in the run-ledger (the watchdog keys off the EVENT, not a phantom field).
    _write_wal_record(node_address=COORD, event="coordinator_died", from_state="running", to_state="dead")

    action = wd.check_coordinator_death(_node_from(coord), _read(COORD), ledger)

    assert _is(action, "ESCALATE"), (
        f"a dead-pid coordinator with live children is a recoverable ORPHAN -> ESCALATE (got {_tag(action)!r})"
    )
    assert not _is(action, "COLLAPSE", "FAILED", "REAP", "KILL"), (
        "a live coordinator with live children must NEVER be reaped (recover-vs-reap is deferred)"
    )
    # The coordinator and its live child are left intact (escalate, never reap).
    assert _read("proj/child#exec")["state"] == "running", "the live child must not be reaped"


def test_coordinator_quiet_alive_with_children_is_waiting(runtime):
    """A QUIET but pane-ALIVE coordinator with live children -> waiting (not dead, not actionable).

    LOAD-BEARING (the pane_pid probe disambiguates quiet-vs-dead): a coordinator that merely went
    quiet with live descendants is `waiting`, NOT an orphan. No coordinator_died event, state is
    not dead -> the probe returns waiting. A mutant that treats quiet-with-children as dead (and
    escalates/reaps) is caught: the action must be a benign waiting, never an escalate/reap.
    """
    wd = _wd()
    coord, _ct = _binding(node_address=COORD, parent_address="", state="running", level="L3", generation=2, lease_epoch=2)
    child, _cht = _binding(node_address="proj/child#exec", parent_address=COORD, state="running", generation=0, lease_epoch=1)
    _seed([coord, child])
    # NO coordinator_died event; the coordinator's state is running (not dead).

    action = wd.check_coordinator_death(_node_from(coord), _read(COORD), ledger)

    assert _is(action, "WAIT", "NOOP", "WAITING", "NONE"), (
        f"a quiet-but-alive coordinator with live children is WAITING, not dead -> got {_tag(action)!r}"
    )
    assert not _is(action, "ESCALATE", "COLLAPSE", "FAILED", "REAP"), (
        "a merely-quiet coordinator with live children must not be escalated or reaped (it is waiting)"
    )
