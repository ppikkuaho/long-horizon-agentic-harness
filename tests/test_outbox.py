"""The spawn-request OUTBOX — the agent-facing half of the live cascade (FORK-SPAWN-CHANNEL).

A jailed agent cannot reach the daemon control socket (that would hand it kill/transition/reconcile on
ANY node — a privilege-escalation hole + a single-writer violation). Instead it DROPS a spawn-REQUEST
into its OWN workroot (a write the jail already allows). The privileged daemon reads the request,
composes the child address FROM THE PARENT'S address (the agent never names a child outside its subtree),
and calls the REAL register_and_spawn_child with the parent's live owner_token (the parent-fence proves
provenance). The agent never touches the ledger or the control plane.

These tests pin REAL conditions: the REAL ledger, the REAL chokepoint.register_and_spawn_child, real
files on disk. Only the actor-open adapter is faked (no tmux/model in a unit test). The properties:
  - namespace confinement: a request can ONLY create a child UNDER the requesting node's address;
    a child_name carrying '/', '..', '#', or whitespace is REJECTED (can't escape the subtree).
  - provenance: the daemon services a node's outbox under THAT node's owner_token (the parent-fence),
    so a request in node X's outbox spawns ONLY under X.
  - reject-with-reason, never silent-drop: a malformed/invalid request is renamed .rejected with a
    reason the agent can read in its own workroot (a leak would be the flow silently skipping it).
  - idempotency: a serviced request is marked .done and is NOT re-spawned on the next sweep.
  - leaf rule: an L5 (executor leaf) outbox is not serviced (L5 has no children).
"""

import copy
import json

import pytest

import harnessd.config as config
import harnessd.fencing as fencing
import harnessd.ledger as ledger
import harnessd.spawn.chokepoint as chokepoint
import harnessd.spawn.outbox as outbox


@pytest.fixture
def runtime(tmp_path):
    prev = ledger.RUNTIME_ROOT
    ledger.RUNTIME_ROOT = tmp_path
    try:
        yield tmp_path
    finally:
        ledger.RUNTIME_ROOT = prev


class _FakeAdapter:
    """Records every actor-open so a test can assert spawn happened (or did NOT)."""

    def __init__(self):
        self.calls = []

    def pin_and_open(self, neutral_brief, level_config, tmux_target, env):
        self.calls.append(tmux_target)
        from harnessd.spawn.adapters.base import SpawnResult
        return SpawnResult(ok=True, session_uuid="s", model_used="m", role_variant="L3",
                           system_prompt_file="operational/shared/system-prompt.md",
                           system_prompt_file_hash="h", tmux_target=tmux_target,
                           transcript_path="/tmp/s.jsonl", failure_class=None)


def _install(fake):
    if hasattr(chokepoint, "set_adapter"):
        chokepoint.set_adapter(fake)
    else:
        chokepoint.ADAPTER = fake


import harnessd.addressing as _addressing


def _seed_live_node(runtime, address, level="L2"):
    """Seed a LIVE parent node with a real (NESTED) workspace dir on disk (where its outbox lives)."""
    token = fencing.mint_owner_token(address, "sa", "uuid", 2)
    workspace = _addressing.node_dir(address, runtime)
    workspace.mkdir(parents=True, exist_ok=True)
    rec = {"node_address": address, "parent_address": "root#exec", "level": level, "subagent_id": "sa",
           "session_uuid": "uuid", "state": "running", "generation": 5, "lease_epoch": 2,
           "owner_token": token, "last_applied_seq": 0, "liveness_state": "working",
           "tmux_target": "harness:" + address, "workspace": str(workspace)}
    ledger.write_binding({address: copy.deepcopy(rec)}, _lock_held=True)
    return token, workspace


PARENT = "proj/widget#exec"


# --------------------------------------------------------------------------- #
# child-address composition (namespace confinement is enforced HERE)
# --------------------------------------------------------------------------- #

def test_child_address_composes_under_the_parent():
    """The child address is the parent's path + the child leaf-name + the parent's role suffix —
    so a child ALWAYS lands inside the parent's subtree (the agent supplies only a leaf-name)."""
    assert outbox.compose_child_address("proj/widget#exec", "parser") == "proj/widget/parser#exec"
    assert outbox.compose_child_address("proj/widget/mod#exec", "lexer") == "proj/widget/mod/lexer#exec"


@pytest.mark.parametrize("evil", ["../escape", "a/b", "side#exec", "with space", "", ".", "..", "/abs",
                                  "parser\n", "trailing ", "lead\ttab", "new\nline\nmid"])
def test_unsafe_child_names_are_rejected(evil):
    """A child_name carrying a path separator, '..', a '#'-role, ANY whitespace (incl. a TRAILING
    newline — the ``$``-vs-``\\Z`` regex hole), or empty is INVALID — it must not be able to name a
    node outside the parent's namespace or embed a newline in the composed address."""
    ok, _reason = outbox.validate_request({"child_name": evil, "child_level": "L3", "brief": "x"})
    assert not ok, f"unsafe child_name {evil!r} must be rejected"


def test_unknown_level_is_rejected():
    ok, _ = outbox.validate_request({"child_name": "parser", "child_level": "L9", "brief": "x"})
    assert not ok


def test_l1_is_not_a_spawnable_child_level():
    """A child is NEVER an L1 root (L1 is genesis-only / parentless) — even though L1 is a valid level
    config, it is not a spawnable CHILD level (a privilege/role-escalation guard)."""
    ok, reason = outbox.validate_request({"child_name": "elevated", "child_level": "L1", "brief": "x"})
    assert not ok and "L1" in reason


def test_empty_brief_is_rejected_when_provided():
    """A brief that is PRESENT but blank is invalid (omit it to derive; don't send an empty one)."""
    ok, _ = outbox.validate_request({"child_name": "parser", "child_level": "L3", "brief": "  "})
    assert not ok


def test_a_well_formed_request_validates():
    ok, reason = outbox.validate_request({"child_name": "parser", "child_level": "L3",
                                          "brief": "design the markdown parser"})
    assert ok, reason


def test_request_without_a_brief_is_valid_the_derivation_default():
    """The DEFAULT: no brief in the request — the spawn derives spec_pointer/frozen_acceptance_ref from
    the pre-authored node files. A bare {child_name, child_level} is a complete, valid request."""
    ok, reason = outbox.validate_request({"child_name": "parser", "child_level": "L3"})
    assert ok, reason


# --------------------------------------------------------------------------- #
# request_child_spawn — the agent-side writer (lands in the node's own workroot)
# --------------------------------------------------------------------------- #

def test_request_child_spawn_writes_into_the_workroot_outbox(runtime, tmp_path):
    work = tmp_path / "work"; work.mkdir()
    path = outbox.request_child_spawn(work, child_name="parser", child_level="L3", brief="do it")
    assert path.exists() and path.parent.name == outbox.OUTBOX_DIRNAME
    obj = json.loads(path.read_text())
    assert obj["child_name"] == "parser" and obj["child_level"] == "L3" and obj["brief"] == "do it"


def test_request_child_spawn_refuses_to_write_an_unsafe_name(runtime, tmp_path):
    work = tmp_path / "work"; work.mkdir()
    with pytest.raises(Exception):
        outbox.request_child_spawn(work, child_name="../escape", child_level="L3", brief="x")


# --------------------------------------------------------------------------- #
# service_outbox — the daemon-side intake (the REAL spawn, faked adapter only)
# --------------------------------------------------------------------------- #

def test_a_valid_request_spawns_the_child_under_the_parent(runtime):
    token, workspace = _seed_live_node(runtime, PARENT)
    fake = _FakeAdapter(); _install(fake)
    outbox.request_child_spawn(workspace, child_name="parser", child_level="L3", brief="design parser")

    outcomes = outbox.service_outbox(PARENT)

    assert len(outcomes) == 1 and outcomes[0].status == "spawned"
    child = ledger.read_binding("proj/widget/parser#exec")
    assert child is not None, "the child must be registered under the parent's namespace"
    assert child["parent_address"] == PARENT, "the supervision-tree edge points at the requesting node"
    assert len(fake.calls) == 1, "exactly one actor opened"


def test_request_is_marked_done_and_not_respawned(runtime):
    _seed_live_node(runtime, PARENT)
    fake = _FakeAdapter(); _install(fake)
    workspace = ledger.read_binding(PARENT)["workspace"]
    outbox.request_child_spawn(workspace, child_name="parser", child_level="L3", brief="x")

    first = outbox.service_outbox(PARENT)
    second = outbox.service_outbox(PARENT)  # a second sweep must NOT spawn again

    assert len(first) == 1 and first[0].status == "spawned"
    assert second == [], "a serviced (.done) request is not re-processed"
    assert len(fake.calls) == 1, "the child is spawned exactly once across two sweeps (idempotent)"


def test_malformed_request_is_rejected_with_a_reason_not_silently_dropped(runtime):
    _seed_live_node(runtime, PARENT)
    fake = _FakeAdapter(); _install(fake)
    outbox_dir = ledger.read_binding(PARENT)["workspace"]
    od = __import__("pathlib").Path(outbox_dir) / outbox.OUTBOX_DIRNAME
    od.mkdir(parents=True, exist_ok=True)
    bad = od / "0001-broken.json"
    bad.write_text("{ this is not valid json", encoding="utf-8")

    outcomes = outbox.service_outbox(PARENT)

    assert len(outcomes) == 1 and outcomes[0].status == "rejected"
    assert outcomes[0].reason, "a rejection must carry a reason (surfaced, not silent)"
    assert not bad.exists(), "the request file is consumed (renamed), not left pending"
    rejected = list(od.glob("*.rejected"))
    assert rejected, "the rejected request is renamed .rejected so the agent can see it in its workroot"
    assert len(fake.calls) == 0, "a malformed request opens NO actor"


def test_unsafe_name_in_a_dropped_file_is_rejected_daemon_side(runtime):
    """Defence-in-depth: even if a request file is hand-written (bypassing request_child_spawn's
    client-side check) with an escaping name, the DAEMON re-validates and refuses it."""
    _seed_live_node(runtime, PARENT)
    fake = _FakeAdapter(); _install(fake)
    od = __import__("pathlib").Path(ledger.read_binding(PARENT)["workspace"]) / outbox.OUTBOX_DIRNAME
    od.mkdir(parents=True, exist_ok=True)
    (od / "0001-evil.json").write_text(
        json.dumps({"child_name": "../../root", "child_level": "L3", "brief": "escape"}), encoding="utf-8")

    outcomes = outbox.service_outbox(PARENT)

    assert len(outcomes) == 1 and outcomes[0].status == "rejected"
    assert ledger.read_binding("root#exec") is None or "root" not in str(ledger.all_nodes().keys()).replace(PARENT, "")
    assert len(fake.calls) == 0, "no actor opened for an escaping name"


def test_dead_parent_outbox_spawns_nothing(runtime):
    """If the requesting node is gone/terminal, its outbox services nothing (register refuses a dead
    parent — no orphan child)."""
    token, workspace = _seed_live_node(runtime, PARENT)
    # mark the parent terminal (a real terminal state: done | failed | dead)
    b = ledger.read_binding(PARENT); b["state"] = "dead"
    ledger.write_binding({PARENT: b}, _lock_held=True)
    fake = _FakeAdapter(); _install(fake)
    outbox.request_child_spawn(workspace, child_name="parser", child_level="L3", brief="x")

    outcomes = outbox.service_outbox(PARENT)

    # The authoritative guarantee: NO child spawned for a dead parent (register's _parent_is_live
    # precondition enforces this even if the service-level short-circuit is removed).
    assert all(o.status != "spawned" for o in outcomes), "a dead parent spawns no child"
    assert ledger.read_binding("proj/widget/parser#exec") is None
    assert len(fake.calls) == 0
    # The service-level short-circuit: a terminal node's outbox is not even read (cheap, and it keeps
    # an abandoned node from churning register-refusals nobody will read). Pin it so the guard is
    # load-bearing, not redundant dead code.
    assert outcomes == [], "a terminal parent's outbox short-circuits (not even read)"


def test_service_all_skips_leaf_l5(runtime):
    """An L5 executor is a LEAF — its outbox is not serviced (L5 spawns no children)."""
    _seed_live_node(runtime, "proj/widget/mod/task#exec", level="L5")
    fake = _FakeAdapter(); _install(fake)
    workspace = ledger.read_binding("proj/widget/mod/task#exec")["workspace"]
    outbox.request_child_spawn(workspace, child_name="sneaky", child_level="L5", brief="x")

    outcomes = outbox.service_all_outboxes()

    assert all(o.status != "spawned" for o in outcomes), "an L5 leaf must not spawn children"
    assert len(fake.calls) == 0


def test_service_all_services_a_live_l2(runtime):
    """service_all_outboxes services a live non-leaf node's pending request (the daemon-loop entry)."""
    _seed_live_node(runtime, PARENT, level="L2")
    fake = _FakeAdapter(); _install(fake)
    workspace = ledger.read_binding(PARENT)["workspace"]
    outbox.request_child_spawn(workspace, child_name="parser", child_level="L3", brief="x")

    outcomes = outbox.service_all_outboxes()

    spawned = [o for o in outcomes if o.status == "spawned"]
    assert len(spawned) == 1 and spawned[0].child_address == "proj/widget/parser#exec"
    assert len(fake.calls) == 1


# --------------------------------------------------------------------------- #
# DERIVATION default — a no-brief request spawns from the pre-authored node files
# --------------------------------------------------------------------------- #

def test_no_brief_request_derives_from_preauthored_node(runtime):
    """The canonical flow: the parent (in its nested subtree-jail) pre-authors the child's brief.md +
    acceptance.md, then drops a NO-BRIEF request; the spawn brings the prepared node online, the binding
    carries the derived pointers, and the pre-authored brief.md is left intact."""
    _seed_live_node(runtime, PARENT)
    fake = _FakeAdapter(); _install(fake)
    workspace = ledger.read_binding(PARENT)["workspace"]
    # parent pre-authors the child node (a subdir of its own workspace — writable under the nested jail)
    child_node = _addressing.node_dir("proj/widget/parser#exec", runtime)
    child_node.mkdir(parents=True, exist_ok=True)
    (child_node / "brief.md").write_text("# pointer-not-payload\nserves: R-002.1.a\n", encoding="utf-8")
    (child_node / "acceptance.md").write_text("frozen tests", encoding="utf-8")
    outbox.request_child_spawn(workspace, child_name="parser", child_level="L3")  # NO brief

    outcomes = outbox.service_outbox(PARENT)

    assert len(outcomes) == 1 and outcomes[0].status == "spawned"
    child = ledger.read_binding("proj/widget/parser#exec")
    assert child["spec_pointer"] == str(child_node / "brief.md")
    assert child["frozen_acceptance_ref"] == str(child_node / "acceptance.md")
    assert (child_node / "brief.md").read_text("utf-8").startswith("# pointer-not-payload"), \
        "the pre-authored brief.md must survive the no-brief spawn"


# --------------------------------------------------------------------------- #
# DESCENT — a child must be strictly deeper than its parent (no same/up-level spawn)
# --------------------------------------------------------------------------- #

def test_same_level_child_is_rejected_by_descent(runtime):
    """An L3 parent cannot spawn another L3 (a sibling-level spawn) — that's the parent's parent's job."""
    token, workspace = _seed_live_node(runtime, "proj/widget/mod#exec", level="L3")
    fake = _FakeAdapter(); _install(fake)
    outbox.request_child_spawn(workspace, child_name="twin", child_level="L3", brief="x")

    outcomes = outbox.service_outbox("proj/widget/mod#exec")

    assert len(outcomes) == 1 and outcomes[0].status == "rejected" and "deeper" in outcomes[0].reason
    assert len(fake.calls) == 0


def test_up_level_child_is_rejected_by_descent(runtime):
    """An L4 parent cannot spawn an L3 (a shallower / up-level child) — an escalation guard."""
    token, workspace = _seed_live_node(runtime, "proj/widget/mod/ws#exec", level="L4")
    fake = _FakeAdapter(); _install(fake)
    outbox.request_child_spawn(workspace, child_name="up", child_level="L3", brief="x")

    outcomes = outbox.service_outbox("proj/widget/mod/ws#exec")

    assert len(outcomes) == 1 and outcomes[0].status == "rejected" and "deeper" in outcomes[0].reason
    assert len(fake.calls) == 0


# --------------------------------------------------------------------------- #
# LEAK — an UNEXPECTED spawn error must be a VISIBLE rejection, never a silent stall
# --------------------------------------------------------------------------- #

def test_unexpected_spawn_error_is_a_visible_rejection_not_a_silent_stall(runtime, monkeypatch):
    """The load-bearing guarantee: if register_and_spawn_child raises an UNEXPECTED error, the request
    is renamed .rejected with a reason (visible to the agent) — it does NOT stay a pending .json that
    the daemon's best-effort sweep swallows forever (the silent-drop LEAK the review found)."""
    _seed_live_node(runtime, PARENT)
    fake = _FakeAdapter(); _install(fake)
    workspace = ledger.read_binding(PARENT)["workspace"]
    req = outbox.request_child_spawn(workspace, child_name="parser", child_level="L3", brief="x")

    def _boom(*a, **k):
        raise OSError("disk gone")
    monkeypatch.setattr(chokepoint, "register_and_spawn_child", _boom)

    outcomes = outbox.service_outbox(PARENT)

    assert len(outcomes) == 1 and outcomes[0].status == "rejected"
    assert "spawn error" in outcomes[0].reason
    assert not req.exists(), "the request must be consumed (renamed), not left pending after an error"
    od = req.parent
    assert list(od.glob("*.rejected")), "a visible .rejected is produced on an unexpected error"


def test_one_raising_node_does_not_starve_later_nodes(runtime, monkeypatch):
    """service_all_outboxes isolates each node: a node whose service raises must not abort the sweep or
    starve nodes iterated after it."""
    # Seed BOTH nodes into the ledger. NB: _seed_live_node REPLACES the whole binding map, so capture
    # node A's binding before seeding Z, then write both together — else only the last-seeded survives
    # and node A is never iterated (the test would pass trivially without exercising the isolation).
    _seed_live_node(runtime, "proj/aaa#exec", level="L2")
    a_binding = ledger.read_binding("proj/aaa#exec")
    _, zws = _seed_live_node(runtime, "proj/zzz#exec", level="L2")
    z_binding = ledger.read_binding("proj/zzz#exec")
    ledger.write_binding({"proj/aaa#exec": a_binding, "proj/zzz#exec": z_binding}, _lock_held=True)
    assert ledger.read_binding("proj/aaa#exec") is not None, "both nodes must be present (sanity)"
    fake = _FakeAdapter(); _install(fake)
    outbox.request_child_spawn(zws, child_name="parser", child_level="L3", brief="x")

    real_service = outbox.service_outbox
    def _maybe_raise(addr):
        if addr == "proj/aaa#exec":
            raise RuntimeError("node A blew up")
        return real_service(addr)
    monkeypatch.setattr(outbox, "service_outbox", _maybe_raise)

    outcomes = outbox.service_all_outboxes()

    assert any(o.status == "spawned" and o.child_address == "proj/zzz/parser#exec" for o in outcomes), \
        "node Z must still be serviced even though node A raised"
    assert len(fake.calls) == 1


# --------------------------------------------------------------------------- #
# IDEMPOTENT RE-SERVICE + per-tick cap
# --------------------------------------------------------------------------- #

def test_idempotent_reservice_marks_done_when_child_already_live(runtime):
    """A pending request whose child is ALREADY live (a crash before the prior .done rename) is a
    SUCCESS (.done), not a misleading .rejected — the register lost its claim because the child exists."""
    token, workspace = _seed_live_node(runtime, PARENT)
    fake = _FakeAdapter(); _install(fake)
    # seed the child as already running (the prior spawn succeeded; only the .done rename was lost)
    child_addr = "proj/widget/parser#exec"
    child_tok = fencing.mint_owner_token(child_addr, "csa", "cuuid", 1)
    ledger.write_binding({**ledger.all_nodes(),
                          child_addr: {"node_address": child_addr, "parent_address": PARENT, "level": "L3",
                                       "state": "running", "generation": 1, "lease_epoch": 1,
                                       "owner_token": child_tok, "last_applied_seq": 0,
                                       "session_uuid": "cuuid", "subagent_id": "csa",
                                       "tmux_target": "harness:" + child_addr}}, _lock_held=True)
    outbox.request_child_spawn(workspace, child_name="parser", child_level="L3", brief="x")

    outcomes = outbox.service_outbox(PARENT)

    assert len(outcomes) == 1 and outcomes[0].status == "spawned", \
        "an already-live child is an idempotent success, not a rejection"
    assert len(fake.calls) == 0, "no SECOND actor opened for the already-live child"


def test_per_tick_cap_limits_requests_serviced(runtime):
    """A flood of requests is rate-limited per tick (MAX_REQUESTS_PER_SWEEP); the remainder stay pending
    and drain on later ticks — bounded work per tick, never a silent drop."""
    _seed_live_node(runtime, PARENT)
    fake = _FakeAdapter(); _install(fake)
    workspace = ledger.read_binding(PARENT)["workspace"]
    n = outbox.MAX_REQUESTS_PER_SWEEP + 5
    for i in range(n):
        outbox.request_child_spawn(workspace, child_name=f"child{i:03d}", child_level="L3", brief="x")

    outcomes = outbox.service_outbox(PARENT)

    assert len(outcomes) == outbox.MAX_REQUESTS_PER_SWEEP, "at most one sweep's worth serviced per tick"
    od = __import__("pathlib").Path(workspace) / outbox.OUTBOX_DIRNAME
    assert len(list(od.glob("*.json"))) == 5, "the remainder stay pending (visible) for the next tick"


# --------------------------------------------------------------------------- #
# FAN-OUT ORDERING — already-live resolves ABOVE the cap (outbox-1), only a
# genuinely-NEW spawn counts in-sweep (outbox-2), and an unknown parent level
# refuses descent fail-LOUD, not fail-open (outbox-3)
# --------------------------------------------------------------------------- #

def _seed_live_children(parent_address, names, level="L3"):
    """Seed live child bindings under the parent in ONE whole-map write.

    NB: ledger.write_binding REPLACES the whole binding map (the footgun documented at the
    starvation-isolation test above) — merge with all_nodes() and write ONCE, never one-by-one.
    """
    nodes = ledger.all_nodes()
    for name in names:
        addr = outbox.compose_child_address(parent_address, name)
        tok = fencing.mint_owner_token(addr, "csa", "cuuid", 1)
        nodes[addr] = {"node_address": addr, "parent_address": parent_address, "level": level,
                       "state": "running", "generation": 1, "lease_epoch": 1,
                       "owner_token": tok, "last_applied_seq": 0,
                       "session_uuid": "cuuid", "subagent_id": "csa",
                       "tmux_target": "harness:" + addr}
    ledger.write_binding(nodes, _lock_held=True)


def test_already_live_child_at_cap_is_done_not_rejected(runtime):
    """outbox-1: at the fan-out cap, a request whose child ALREADY spawned (a crash before the prior
    .done rename) must resolve .done — NOT a misleading cap-.rejected for a child that actually
    exists. The already-live check must sit ABOVE the cap, exactly where it is hardest to debug."""
    _, workspace = _seed_live_node(runtime, PARENT)
    fake = _FakeAdapter(); _install(fake)
    names = [f"c{i:03d}" for i in range(outbox.MAX_CHILDREN_PER_PARENT - 1)] + ["parser"]
    _seed_live_children(PARENT, names)  # parent sits exactly AT the cap, "parser" among the live
    outbox.request_child_spawn(workspace, child_name="parser", child_level="L3", brief="x")

    outcomes = outbox.service_outbox(PARENT)

    assert len(outcomes) == 1 and outcomes[0].status == "spawned", \
        "the crash-recovery replay of an already-live child is a SUCCESS even at the cap"
    assert outcomes[0].already_live is True
    od = __import__("pathlib").Path(workspace) / outbox.OUTBOX_DIRNAME
    assert list(od.glob("*.done")), "the replayed request is consumed .done"
    assert not list(od.glob("*.rejected")) and not list(od.glob("*.reason")), \
        "no misleading cap-rejection for a child that actually exists"
    assert len(fake.calls) == 0, "no SECOND actor opened"


def test_already_live_reservice_does_not_double_count_against_the_cap(runtime):
    """outbox-2: an idempotent .done is ALREADY in the _live_child_count base — counting it AGAIN
    against the in-sweep counter would prematurely trip the cap for a fresh request this sweep."""
    _, workspace = _seed_live_node(runtime, PARENT)
    fake = _FakeAdapter(); _install(fake)
    names = [f"c{i:03d}" for i in range(outbox.MAX_CHILDREN_PER_PARENT - 2)] + ["parser"]
    _seed_live_children(PARENT, names)  # cap - 1 live children, one of them "parser"
    outbox.request_child_spawn(workspace, child_name="parser", child_level="L3", brief="x")  # already live
    outbox.request_child_spawn(workspace, child_name="fresh", child_level="L3", brief="x")   # genuinely new

    outcomes = outbox.service_outbox(PARENT)

    assert [o.status for o in outcomes] == ["spawned", "spawned"], \
        "the idempotent .done must not eat the last cap slot the fresh request needs"
    assert outcomes[0].already_live is True and outcomes[1].already_live is False
    assert len(fake.calls) == 1, "only the fresh child opened an actor"
    assert ledger.read_binding("proj/widget/fresh#exec") is not None


def test_fresh_spawns_still_count_against_the_in_sweep_cap(runtime):
    """Mutation guard for the surviving half of the counter: a genuinely-NEW spawn still admits
    against the running in-sweep count, so the next fresh request in the same sweep hits the cap."""
    _, workspace = _seed_live_node(runtime, PARENT)
    fake = _FakeAdapter(); _install(fake)
    _seed_live_children(PARENT, [f"c{i:03d}" for i in range(outbox.MAX_CHILDREN_PER_PARENT - 1)])
    outbox.request_child_spawn(workspace, child_name="first", child_level="L3", brief="x")
    outbox.request_child_spawn(workspace, child_name="second", child_level="L3", brief="x")

    outcomes = outbox.service_outbox(PARENT)

    assert [o.status for o in outcomes] == ["spawned", "rejected"]
    assert "cap" in outcomes[1].reason
    assert len(fake.calls) == 1, "exactly one actor opened (the second request was refused at cap)"
    od = __import__("pathlib").Path(workspace) / outbox.OUTBOX_DIRNAME
    assert list(od.glob("*-second*.rejected")) and list(od.glob("*-second*.reason")), \
        "the at-cap refusal is a visible reject-with-reason, never a silent drop"


_DELETED = object()  # sentinel: remove the parent binding's level key entirely


@pytest.mark.parametrize("corrupt_level", [None, "L9", _DELETED], ids=["none", "unknown", "missing"])
def test_unknown_parent_level_refuses_descent_fail_loud_not_fail_open(runtime, corrupt_level):
    """outbox-3: a None/unknown parent level must REFUSE descent visibly (reject-with-reason), not
    map to rank 0 and wave ANY child level through the system's ONLY descent gate (the chokepoint
    has no descent gate of its own — fail-open here is fail-open everywhere)."""
    _, workspace = _seed_live_node(runtime, PARENT)
    fake = _FakeAdapter(); _install(fake)
    b = ledger.read_binding(PARENT)
    if corrupt_level is _DELETED:
        del b["level"]
    else:
        b["level"] = corrupt_level
    ledger.write_binding({**ledger.all_nodes(), PARENT: b}, _lock_held=True)
    outbox.request_child_spawn(workspace, child_name="parser", child_level="L3", brief="x")

    outcomes = outbox.service_outbox(PARENT)

    assert len(outcomes) == 1 and outcomes[0].status == "rejected"
    expected = None if corrupt_level is _DELETED else corrupt_level
    assert repr(expected) in outcomes[0].reason and "descent" in outcomes[0].reason, \
        "the reason names the unverifiable parent level and the descent guarantee"
    assert ledger.read_binding("proj/widget/parser#exec") is None, \
        "an unverifiable descent must NOT register the child (fail-loud, not fail-open)"
    assert len(fake.calls) == 0
    od = __import__("pathlib").Path(workspace) / outbox.OUTBOX_DIRNAME
    assert list(od.glob("*.rejected")) and list(od.glob("*.reason")), "never a silent drop"


def test_concurrent_register_loss_still_marks_done_with_already_live_flag(runtime, monkeypatch):
    """Pins the post-spawn backstop as LOAD-BEARING (not dead code): a child registered BETWEEN the
    pre-check and register (an interleaved IPC service-outbox or sweep) makes register lose its
    claim — still a success (.done, already_live), never a misleading reject through the race window."""
    _, workspace = _seed_live_node(runtime, PARENT)
    fake = _FakeAdapter(); _install(fake)
    outbox.request_child_spawn(workspace, child_name="parser", child_level="L3", brief="x")

    def _concurrent_winner(parent, child, **kwargs):
        # the interleaved actor registers the child live; OUR register loses its single-owner claim
        _seed_live_children(PARENT, ["parser"])
        from harnessd.spawn.adapters.base import SpawnResult
        return SpawnResult(ok=False, session_uuid=None, model_used="", role_variant="",
                           system_prompt_file="", system_prompt_file_hash="", tmux_target="",
                           transcript_path=None, failure_class="claim_lost")
    monkeypatch.setattr(chokepoint, "register_and_spawn_child", _concurrent_winner)

    outcomes = outbox.service_outbox(PARENT)

    assert len(outcomes) == 1 and outcomes[0].status == "spawned", \
        "losing the claim BECAUSE the child already exists is a success, not a rejection"
    assert outcomes[0].already_live is True, "the backstop must flag already_live for the cap accounting"
    od = __import__("pathlib").Path(workspace) / outbox.OUTBOX_DIRNAME
    assert list(od.glob("*.done")) and not list(od.glob("*.rejected"))
    assert len(fake.calls) == 0
