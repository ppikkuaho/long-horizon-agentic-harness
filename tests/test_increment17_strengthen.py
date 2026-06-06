"""Increment 17 — load-bearing STRENGTHENING (verification-gate fixes).

The Inc-17 review + my gate found defects the frozen tests didn't cover. After fixing the impl, pin the
new load-bearing properties so a regression is caught:
  1. GATE node-binding — the accept must be FOR THIS node; an accept for a DIFFERENT project must NOT
     promote this one (was: gated on decision=='accept' alone — an accept for A could promote B).
  2. NONE-destination precondition — the gate passed but intake captured no delivery_destination ->
     delivery-failed + escalate, NOT an uncaught crash / a None-destination copy.
  3. RESOLUTION fault is JOURNALED, not raised — a project-resolution failure (no write_targets, no
     proj/<name> in the address) routes to delivery-failed, never an uncaught ValueError out of promote.
  4. The §6.3 escalation row is INDEPENDENTLY assertable (a DISTINCT event from the state-stamp).
"""

from __future__ import annotations

import copy

import pytest

from harnessd import fencing, ledger
import harnessd.promote as promote_mod


PROJECT = "demo-widget"
NODE = "proj/demo-widget#exec"
OTHER_NODE = "proj/other-project#exec"


@pytest.fixture
def runtime(tmp_path):
    runtime_root = tmp_path / "runtime"
    runtime_root.mkdir()
    prev = ledger.RUNTIME_ROOT
    ledger.RUNTIME_ROOT = runtime_root
    try:
        yield runtime_root
    finally:
        ledger.RUNTIME_ROOT = prev


def _seed(*, node_address=NODE, delivery_destination=None, delivery_kind="filesystem-path",
          write_targets=None, deliverable_state="completed"):
    token = fencing.mint_owner_token(node_address, "sa", "uuid", 2)
    rec = {
        "node_address": node_address, "parent_address": "root#exec", "level": "L1",
        "subagent_id": "sa", "session_uuid": "uuid", "state": "done", "generation": 5,
        "lease_epoch": 2, "owner_token": token, "last_applied_seq": 0, "liveness_state": "terminal",
        "gate_crossed_at": None, "paused_at": None, "transcript_path": None,
        "deliverable_state": deliverable_state,
        "write_targets": write_targets if write_targets is not None else ["proj/demo-widget/"],
        "delivery_destination": delivery_destination, "delivery_kind": delivery_kind,
    }
    ledger.write_binding({node_address: copy.deepcopy(rec)}, _lock_held=True)
    return rec


def _build_tree(runtime_root, project=PROJECT):
    d = runtime_root / "proj" / project
    (d / "src").mkdir(parents=True, exist_ok=True)
    (d / "README.md").write_text("deliverable\n", encoding="utf-8")
    (d / "src" / "widget.py").write_text("X = 'MARKER-17s'\n", encoding="utf-8")
    return d


def _accept(node_address):
    return {"decision": "accept", "level": "L1", "node_address": node_address}


def _wal_rows(node_address):
    return [r for r in ledger.load_wal() if r.get("node_address") == node_address]


# --- 1. GATE node-binding: an accept for a DIFFERENT node must NOT promote this one ---------------

def test_accept_for_a_different_node_does_not_promote_this_one(runtime, tmp_path):
    """An L1 accept bound to OTHER_NODE must NOT promote NODE (the gate is per-project; an accept for
    project A must not deliver project B). Was a hole: the gate checked decision only."""
    _build_tree(runtime)
    dest = tmp_path / "delivery-out" / "demo-widget"
    _seed(delivery_destination=str(dest))

    # The accept is for a DIFFERENT node.
    result = promote_mod.promote(NODE, accept_signal=_accept(OTHER_NODE))

    assert not getattr(result, "ok", False), "an accept for a different node must NOT promote this node"
    assert not dest.exists(), "a cross-node accept wrote to the destination — the node-binding gate failed"
    assert ledger.read_binding(NODE)["deliverable_state"] != "delivered", \
        "deliverable_state advanced on a cross-node accept — the gate is not node-bound"


def test_accept_missing_node_address_holds_the_gate(runtime, tmp_path):
    """An accept with NO node_address can't be verified as for-this-project -> gate held (secure default)."""
    _build_tree(runtime)
    dest = tmp_path / "delivery-out" / "demo-widget"
    _seed(delivery_destination=str(dest))
    result = promote_mod.promote(NODE, accept_signal={"decision": "accept", "level": "L1"})  # no node_address
    assert not getattr(result, "ok", False) and not dest.exists(), \
        "an accept with no node binding promoted — a node-unbound accept must hold the gate"


# --- 2. NONE-destination precondition: gate passed, no destination -> delivery-failed (not a crash) ---

def test_accept_with_no_destination_is_delivery_failed_not_crash(runtime):
    """The gate passes but intake captured NO delivery_destination -> delivery-failed + escalate,
    NOT an uncaught crash and NOT a None-destination copy attempt."""
    _build_tree(runtime)
    _seed(delivery_destination=None)  # intake never captured a destination

    result = promote_mod.promote(NODE, accept_signal=_accept(NODE))  # must not raise

    assert not getattr(result, "ok", True), "a missing destination must not report a successful delivery"
    assert ledger.read_binding(NODE)["deliverable_state"] == "delivery-failed", \
        "a missing delivery_destination must set delivery-failed (a real precondition fault), not crash"


# --- 3. RESOLUTION fault is JOURNALED, not raised (the HIGH: uncaught ValueError) -----------------

def test_unresolvable_project_is_delivery_failed_not_uncaught(runtime, tmp_path):
    """A binding with NO usable write_targets AND a node_address with no proj/<name> segment makes
    project-resolution fail. It must route to delivery-failed (journaled), NOT raise an uncaught
    ValueError out of promote (the HIGH the gate found)."""
    weird_node = "rootless#exec"  # no 'proj/<name>' segment
    _seed(node_address=weird_node, delivery_destination=str(tmp_path / "out"), write_targets=[])

    # Must NOT raise — a resolution fault is a journaled delivery-failed, not a crash.
    result = promote_mod.promote(weird_node, accept_signal=_accept(weird_node))

    assert not getattr(result, "ok", True), "an unresolvable project must not report success"
    assert ledger.read_binding(weird_node)["deliverable_state"] == "delivery-failed", \
        "an unresolvable project must be journaled delivery-failed, not crash uncaught"


# --- 4. The §6.3 escalation row is INDEPENDENTLY assertable (distinct event from the state-stamp) ---

def test_failed_promote_emits_a_distinct_escalation_row(runtime, tmp_path):
    """On a failed promote there are TWO distinguishable rows: the deliverable_state stamp
    (event='delivery_failed') AND a SEPARATE §6.3 escalation (event='delivery_failed_escalation').
    The escalation must be independently assertable, not collapsed into the state-stamp."""
    _build_tree(runtime)
    blocker = tmp_path / "blocker"
    blocker.write_text("file-not-dir\n", encoding="utf-8")
    _seed(delivery_destination=str(blocker / "demo-widget"))  # parent is a file -> copy fails

    promote_mod.promote(NODE, accept_signal=_accept(NODE))

    events = [r.get("event") for r in _wal_rows(NODE)]
    assert "delivery_failed" in events, "the deliverable_state stamp row (event='delivery_failed') is missing"
    assert "delivery_failed_escalation" in events, (
        "the §6.3 escalation must be a DISTINCT row (event='delivery_failed_escalation'), independently "
        f"assertable from the state-stamp — found events: {events}"
    )
    # Both attributable to harnessd (the single writer / control plane).
    esc = [r for r in _wal_rows(NODE) if r.get("event") == "delivery_failed_escalation"]
    assert esc and all(r.get("actor") == "harnessd" for r in esc), \
        "the escalation row must be attributable to harnessd"
