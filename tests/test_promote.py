"""FROZEN acceptance — Increment 17: control-plane promotion / delivery (promote-out-of-/runtime/).

Authoritative sources (transcribed, not recalled):
  - harnessd/IMPLEMENTATION-PLAN.md — the Increment-17 Done-test (lines 833-857).
  - design/INTAKE-TO-DELIVERY.md §3 (promotion is a control-plane cross-jail write) + Stage 6.
  - design/DAEMON.md §3.2 — the deliverable binding block: deliverable_state
    (planned|active|waiting|completed|blocked|cancelled|delivered|delivery-failed),
    write_targets (the IN-JAIL source surface), delivery_destination (the OUT-OF-JAIL target),
    delivery_kind (filesystem-path | git-remote). delivery_destination is DISTINCT from
    write_targets — the jail boundary stays legible; do NOT overload one onto the other.
  - harnessd/executor.py — the SINGLE writer (executor.transition; commit is private). No second
    mutation path. Every committed change journals a WAL row with actor='harnessd' and advances
    last_applied_seq.
  - harnessd/spawn/chokepoint.py — the collapse / escalation precedent (a failure emits an L1
    escalation WAL row via the run-ledger; _emit_spawn_failure_escalation is the §6.3 seam).

THE INCREMENT (the one sanctioned cross-write-jail action):
  promote() is a harnessd op, GATED on L1 final-accept for a project, that copies the finished
  deliverable OUT of the gitignored /runtime/proj/{project}/ node TO the delivery destination
  captured at intake in the frozen intent-spec (a filesystem user-path or a git remote). Agents
  CANNOT do this — every agent is write-jailed to its /runtime/ node subtree and the destination
  is OUTSIDE every jail; only the control plane (harnessd) may cross it, and only on accept.

  GATE        — proceeds ONLY on L1 final-accept. With NO accept (or a reject) -> NO-OP: the
                destination is untouched and /runtime/ is left intact (gated, never speculative).
  ON ACCEPT   — copy-out (delivery_kind=filesystem-path) or push (git-remote) the finished
                deliverable to delivery_destination; write deliverable_state=delivered on the
                binding via the SINGLE writer (executor.transition — no second mutation path);
                delivery_destination records the target; write_targets stays the in-jail source.
  ON FAILURE  — deliverable_state=delivery-failed + an escalation (the §6.3 run-ledger seam).

  Project teardown/reclaim of /runtime/ AFTER delivery is DEFERRED (register D7) — NOT tested here.

BIAS TO REAL (Lesson 7): a real on-disk /runtime/proj/{project}/ tree; a real temp-dir filesystem
destination (assert the deliverable BYTES land there); the REAL executor records deliverable_state;
the git-remote variant uses a REAL local bare git repo (real `git init --bare` + real `git push`)
so the push is genuinely exercised. No mock of the file/git boundary. No model usage.
"""

from __future__ import annotations

import copy
import importlib
import subprocess

import pytest

from harnessd import executor, fencing, ledger


# ===========================================================================
# Runtime fixture — bind ledger.RUNTIME_ROOT to tmp_path so the REAL executor's
# pathless ledger calls (read_binding / append_wal / write_binding) AND the EX
# lock all land under the test tree. Restores the prior value (no cross-test
# leak). This is the same fixture precedent as test_chokepoint.py / test_executor.py.
# ===========================================================================

@pytest.fixture
def runtime(tmp_path):
    # The /runtime/ jail root is a DISTINCT subdir of tmp_path, NOT tmp_path itself: the delivery
    # destination (a sibling under tmp_path, e.g. tmp_path/"delivery-out") must be genuinely OUTSIDE
    # the /runtime/ tree for the cross-jail-boundary assertions to mean anything. Binding RUNTIME_ROOT
    # to tmp_path directly would put every destination INSIDE the jail and make those assertions vacuous.
    runtime_root = tmp_path / "runtime"
    runtime_root.mkdir()
    previous = ledger.RUNTIME_ROOT
    ledger.RUNTIME_ROOT = runtime_root
    try:
        yield runtime_root
    finally:
        ledger.RUNTIME_ROOT = previous


# ===========================================================================
# Module-resolution seam. promote lives in harnessd/promote.py (a NEW module —
# the ONE new build artifact of Increment 17). We import it lazily so the RED
# run fails with a clear "module not built yet" rather than a collection error.
# ===========================================================================

def _promote_module():
    """Import harnessd.promote, FAILING LOUDLY with the contract if it is not built.

    The Increment-17 deliverable is a harnessd promotion op. The plan (§3 module table style)
    pins it as harnessd/promote.py exposing a ``promote`` callable. If the module/callable is
    absent the test tells the implementer the exact contract rather than dying on an opaque
    ImportError.
    """
    try:
        return importlib.import_module("harnessd.promote")
    except ImportError as exc:  # pragma: no cover - RED guidance path
        raise AssertionError(
            "Increment 17 not built: expected module ``harnessd/promote.py`` exposing a "
            "control-plane ``promote(node_address, *, accept_signal)`` op (the one sanctioned "
            "cross-write-jail action, gated on L1 final-accept; INTAKE-TO-DELIVERY §3 / "
            "IMPLEMENTATION-PLAN Increment-17 Done-test). Underlying import error: "
            f"{exc!r}"
        ) from exc


def _promote_callable():
    module = _promote_module()
    if not hasattr(module, "promote"):
        raise AssertionError(
            "harnessd.promote is missing the ``promote`` op: expected "
            "``promote(node_address, *, accept_signal) -> result`` (gated control-plane "
            "promote-out-of-/runtime/, INTAKE-TO-DELIVERY §3)."
        )
    return module.promote


# ===========================================================================
# Accept-signal builders. The GATE is L1 final-accept (Stage 5). We model the
# accept and reject signals as small dicts the promote op consumes; the impl is
# free to read whatever shape it pins, but the gate semantics are fixed:
#   accept  -> proceed;  reject/none -> NO-OP.
# We pass an EXPLICIT, self-describing accept object so a wrong impl that ignores
# the gate (speculative promote) is caught by the reject-path no-op test.
# ===========================================================================

def _accept_signal(node_address):
    """An L1 final-accept signal for the project (Stage 5 accept)."""
    return {
        "decision": "accept",
        "level": "L1",
        "node_address": node_address,
        "acceptance_ref": "client-brief/intent-spec.md",
        "note": "intent-fidelity accept (Stage 5)",
    }


def _reject_signal(node_address):
    """An L1 final-accept signal that is a REJECT (must NOT promote)."""
    return {
        "decision": "reject",
        "level": "L1",
        "node_address": node_address,
        "acceptance_ref": "client-brief/intent-spec.md",
        "note": "intent-fidelity reject (Stage 5) — bounded re-do",
    }


# ===========================================================================
# Binding seeding — write DIRECTLY through the REAL ledger (the seeding path the
# whole suite uses: ledger.write_binding(map, _lock_held=True)). The node is an
# ACCEPTED project node: lifecycle state=done (the deliverable is finished and
# accepted), deliverable_state=completed (awaiting delivery), with the deliverable
# binding block carrying the in-jail write_targets + the out-of-jail
# delivery_destination/delivery_kind captured at intake.
# ===========================================================================

PROJECT = "demo-widget"
NODE = "proj/demo-widget#exec"
PARENT = "root#exec"
SUBAGENT = "subagent-promote01"
SESSION = "sess-uuid-promote-0001"


def _binding(
    *,
    node_address=NODE,
    state="done",
    deliverable_state="completed",
    generation=5,
    lease_epoch=2,
    delivery_destination=None,
    delivery_kind=None,
    write_targets=None,
    extra=None,
):
    token = fencing.mint_owner_token(node_address, SUBAGENT, SESSION, lease_epoch)
    rec = {
        "node_address": node_address,
        "parent_address": PARENT,
        "level": "L1",
        "subagent_id": SUBAGENT,
        "session_uuid": SESSION,
        "state": state,
        "generation": generation,
        "lease_epoch": lease_epoch,
        "owner_token": token,
        "last_applied_seq": 0,
        "liveness_state": "terminal",
        "gate_crossed_at": None,
        "paused_at": None,
        "transcript_path": None,
        # --- the §3.2 deliverable binding block ---
        "deliverable_state": deliverable_state,
        "stop_condition": "demo-widget passes acceptance.md",
        "write_targets": (
            write_targets if write_targets is not None else ["proj/demo-widget/"]
        ),  # the IN-JAIL source surface (must stay this, never overloaded with the destination)
        "evidence_refs": ["report.md"],
        "acceptance_ref": "client-brief/intent-spec.md",
        "delivery_destination": delivery_destination,  # captured at intake (intent-spec §8)
        "delivery_kind": delivery_kind,
    }
    if extra:
        rec.update(extra)
    return rec, token


def _seed(binding):
    ledger.write_binding({binding["node_address"]: copy.deepcopy(binding)}, _lock_held=True)


def _read(node=NODE):
    return ledger.read_binding(node)


# ===========================================================================
# Real on-disk /runtime/ tree builder. The finished deliverable lives INSIDE the
# gitignored /runtime/proj/{project}/ node subtree (the in-jail source surface).
# We synthesize a real multi-file tree with distinctive bytes so the copy-out /
# push is asserted on the ACTUAL bytes, not a placeholder.
# ===========================================================================

DELIVERABLE_FILES = {
    "README.md": "# Demo Widget\n\nThe finished, accepted deliverable.\n",
    "src/widget.py": "def widget():\n    return 'PROMOTED-DELIVERABLE-MARKER-7f3a'\n",
    "src/util/helpers.py": "HELPER = 'nested-helper-payload'\n",
    "acceptance.md": "All requirements satisfied.\n",
}


def _build_runtime_tree(runtime_root, project=PROJECT, files=DELIVERABLE_FILES):
    """Synthesize a REAL /runtime/proj/{project}/ deliverable tree on disk. Returns its path."""
    proj_dir = runtime_root / "proj" / project
    for rel, content in files.items():
        target = proj_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return proj_dir


def _tree_snapshot(root):
    """Map of relative-path -> bytes for every file under ``root`` (for untouched-assertions)."""
    snapshot = {}
    if not root.exists():
        return snapshot
    for path in sorted(root.rglob("*")):
        if path.is_file():
            snapshot[str(path.relative_to(root))] = path.read_bytes()
    return snapshot


# ===========================================================================
# Agent-write sentinel. The promote write must be attributable to harnessd (the
# control plane), NEVER to a jailed agent. Every agent — L1 included — is
# write-jailed to its /runtime/ node subtree; the destination is OUTSIDE every
# jail. We assert NO jailed-agent write touched the destination two ways:
#   (1) every WAL row the promote journals carries actor='harnessd' (the ledger
#       hard-codes actor='harnessd' for the single writer);
#   (2) the destination's parent is OUTSIDE /runtime/ (structurally un-reachable
#       by a write-jailed agent), and the only writer that produced its bytes is
#       the control-plane copy.
# ===========================================================================

def _wal_rows_for(node_address):
    return [r for r in ledger.load_wal() if r.get("node_address") == node_address]


# ===========================================================================
# 1. ACCEPT-GATED PROMOTE (filesystem-path) — the headline Done-test.
#    On a FAKE accepted project (real /runtime/ tree + intent-spec destination +
#    L1 accept), promote LANDS the deliverable AT the captured destination and the
#    binding shows deliverable_state=delivered with delivery_destination recording
#    the target. write_targets stays the in-jail source. The write is the control
#    plane's (actor='harnessd'), NOT an agent's.
# ===========================================================================

def test_accept_promote_lands_deliverable_at_destination(runtime, tmp_path):
    promote = _promote_callable()
    proj_dir = _build_runtime_tree(runtime)

    # The destination is a REAL temp dir OUTSIDE /runtime/ (outside every write-jail).
    dest = tmp_path / "delivery-out" / "demo-widget"
    assert runtime not in dest.parents and dest != runtime, (
        "the delivery destination must be OUTSIDE /runtime/ (outside every agent's write-jail) — "
        "that is the whole point of the control-plane cross-jail promote"
    )

    binding, token = _binding(
        delivery_destination=str(dest),
        delivery_kind="filesystem-path",
    )
    _seed(binding)

    result = promote(NODE, accept_signal=_accept_signal(NODE))

    # The op reports success.
    assert getattr(result, "ok", result) , f"accept-gated promote should succeed; got {result!r}"

    # (a) The deliverable BYTES landed AT the captured destination (real on-disk copy-out).
    for rel, content in DELIVERABLE_FILES.items():
        landed = dest / rel
        assert landed.is_file(), f"deliverable file {rel!r} did not land at the destination {dest}"
        assert landed.read_text(encoding="utf-8") == content, (
            f"deliverable file {rel!r} landed with wrong bytes (copy-out corrupted/mismatched)"
        )
    # The distinctive marker proves the ACTUAL deliverable bytes were copied, not a placeholder.
    assert "PROMOTED-DELIVERABLE-MARKER-7f3a" in (dest / "src/widget.py").read_text("utf-8")

    # (b) The binding shows deliverable_state=delivered, recorded via the executor.
    after = _read()
    assert after["deliverable_state"] == "delivered", (
        f"expected deliverable_state=delivered after a successful promote, got "
        f"{after['deliverable_state']!r}"
    )

    # (c) delivery_destination records the target.
    assert after["delivery_destination"] == str(dest), (
        "delivery_destination must record the captured target after promote"
    )

    # (d) write_targets is NOT overloaded with the destination — it stays the in-jail source surface.
    assert after["write_targets"] == ["proj/demo-widget/"], (
        "write_targets must stay the IN-JAIL source surface — the out-of-jail destination belongs "
        "in delivery_destination, NEVER overloaded onto write_targets (DAEMON §3.2: distinct fields)"
    )
    assert str(dest) not in after["write_targets"], (
        "the out-of-jail destination leaked into write_targets — the jail boundary is no longer "
        "legible (the overload mutant)"
    )


# ===========================================================================
# 2. SINGLE-WRITER attribution — the promote's deliverable_state write goes through
#    executor.transition (the one mutation path), journaling a WAL row with
#    actor='harnessd' and advancing last_applied_seq. NO second mutation path; the
#    write is the CONTROL PLANE's, never an agent's.
# ===========================================================================

def test_promote_state_write_is_single_writer_harnessd(runtime, tmp_path):
    promote = _promote_callable()
    _build_runtime_tree(runtime)
    dest = tmp_path / "delivery-out" / "demo-widget"

    binding, token = _binding(delivery_destination=str(dest), delivery_kind="filesystem-path")
    _seed(binding)

    before = _read()
    seq_before = before["last_applied_seq"]

    promote(NODE, accept_signal=_accept_signal(NODE))

    after = _read()

    # The state change went through the executor commit path (last_applied_seq advanced — the
    # intent-first watermark only moves on a real executor.commit; a raw write_binding side-channel
    # would NOT advance it).
    assert after["last_applied_seq"] > seq_before, (
        "deliverable_state must be written via the SINGLE writer (executor.transition/commit), "
        "which stamps last_applied_seq from the WAL entry — a second mutation path (raw "
        "write_binding) would not advance the watermark (DAEMON §4.4 intent-first)"
    )

    # A WAL row journals the delivery, attributable to harnessd (the single writer hard-codes
    # actor='harnessd'). No agent ever writes the ledger.
    rows = _wal_rows_for(NODE)
    delivery_rows = [
        r for r in rows
        if r.get("binding_delta", {}).get("deliverable_state") == "delivered"
        or "deliver" in (r.get("event", "") or "").lower()
        or r.get("to_state") == "delivered"
    ]
    assert delivery_rows, (
        "the promote must journal the delivery in the WAL (the single-writer audit log) — found "
        f"no delivery row among {[r.get('event') for r in rows]}"
    )
    assert all(r.get("actor") == "harnessd" for r in delivery_rows), (
        "every promote WAL row must be attributable to harnessd (the control plane / single "
        "writer), NEVER a jailed agent — actor is hard-coded to 'harnessd' by the ledger"
    )


# ===========================================================================
# 3. CONTROL-PLANE attribution at the destination — the destination sits OUTSIDE
#    /runtime/ (structurally un-reachable by any write-jailed agent), and its bytes
#    were produced by the control-plane copy. Assert NO jailed-agent write touched
#    the destination: the only writer that could reach outside /runtime/ is harnessd.
# ===========================================================================

def test_destination_is_outside_runtime_jail_and_written_by_control_plane(runtime, tmp_path):
    promote = _promote_callable()
    _build_runtime_tree(runtime)
    dest = tmp_path / "delivery-out" / "demo-widget"

    binding, _ = _binding(delivery_destination=str(dest), delivery_kind="filesystem-path")
    _seed(binding)

    promote(NODE, accept_signal=_accept_signal(NODE))

    # The destination is genuinely outside the /runtime/ tree (no agent jail covers it).
    assert runtime not in dest.parents, (
        "the destination must be outside /runtime/ — a write-jailed agent (allow-list scoped to "
        "its node WORKROOT under /runtime/) is STRUCTURALLY unable to write here; only the "
        "control plane can cross this boundary (INTAKE-TO-DELIVERY §3)"
    )
    # The deliverable landed there nonetheless => the writer was NOT a jailed agent (it crossed a
    # boundary no jailed agent can cross). The control plane is the only candidate.
    assert (dest / "README.md").is_file(), (
        "deliverable did not land outside the jail — the control-plane cross-jail copy did not run"
    )


# ===========================================================================
# 4. REJECT PATH — with NO accept signal, promote is a NO-OP: the destination is
#    untouched and /runtime/ is left intact. A speculative promote is caught here.
# ===========================================================================

def test_no_accept_is_noop_destination_untouched_runtime_intact(runtime, tmp_path):
    promote = _promote_callable()
    proj_dir = _build_runtime_tree(runtime)
    before_runtime = _tree_snapshot(proj_dir)

    dest = tmp_path / "delivery-out" / "demo-widget"
    binding, _ = _binding(delivery_destination=str(dest), delivery_kind="filesystem-path")
    _seed(binding)
    before_binding = _read()

    # NO accept signal at all (accept_signal=None) — the gate must hold.
    result = promote(NODE, accept_signal=None)

    # The op did not deliver.
    assert not getattr(result, "ok", False), (
        "promote with NO accept signal must NOT report a successful delivery (gated, never "
        "speculative)"
    )

    # The destination is UNTOUCHED — nothing was created there.
    assert not dest.exists(), (
        "promote with no accept wrote to the destination — a SPECULATIVE promote (the gate is "
        "missing: a wrong impl that promotes without an accept is caught here)"
    )

    # /runtime/ is left INTACT — byte-for-byte unchanged.
    assert _tree_snapshot(proj_dir) == before_runtime, (
        "the /runtime/ tree changed on a no-op promote — promotion must not mutate the source on "
        "a gated no-op"
    )

    # The binding's deliverable_state did NOT advance to delivered.
    after = _read()
    assert after["deliverable_state"] != "delivered", (
        "deliverable_state advanced to delivered on a no-accept promote — the gate did not hold"
    )
    assert after["delivery_destination"] == before_binding["delivery_destination"], (
        "delivery_destination changed on a no-op promote"
    )


def test_reject_signal_is_noop_destination_untouched(runtime, tmp_path):
    """A REJECT (not merely a missing accept) is also a no-op — the gate is on ACCEPT, not presence."""
    promote = _promote_callable()
    proj_dir = _build_runtime_tree(runtime)
    before_runtime = _tree_snapshot(proj_dir)

    dest = tmp_path / "delivery-out" / "demo-widget"
    binding, _ = _binding(delivery_destination=str(dest), delivery_kind="filesystem-path")
    _seed(binding)

    result = promote(NODE, accept_signal=_reject_signal(NODE))

    assert not getattr(result, "ok", False), (
        "a REJECT signal must NOT deliver — the gate proceeds only on an ACCEPT decision"
    )
    assert not dest.exists(), (
        "promote on a REJECT wrote to the destination — a reject is a no-op, not a delivery"
    )
    assert _tree_snapshot(proj_dir) == before_runtime, "/runtime/ mutated on a reject no-op"
    assert _read()["deliverable_state"] != "delivered", (
        "deliverable_state advanced to delivered on a REJECT — the accept gate did not hold"
    )


# ===========================================================================
# 5. FAILED PROMOTE — a copy-out failure sets deliverable_state=delivery-failed and
#    ESCALATES (the §6.3 run-ledger escalation seam). A silent success on failure is
#    caught here.
#
#    We force a real failure by pointing delivery_destination at a path whose parent
#    is a REGULAR FILE — the OS cannot create a directory child of a file, so the
#    real copy-out raises. No mock; a genuine filesystem failure.
# ===========================================================================

def test_failed_promote_sets_delivery_failed_and_escalates(runtime, tmp_path):
    promote = _promote_callable()
    _build_runtime_tree(runtime)

    # A regular file standing where the destination's PARENT directory must be — the copy-out
    # cannot create a directory under a file, so the real filesystem write fails.
    blocker = tmp_path / "blocker-file"
    blocker.write_text("i am a file, not a directory\n", encoding="utf-8")
    dest = blocker / "demo-widget"  # parent (blocker) is a file => mkdir/copy must fail

    binding, _ = _binding(delivery_destination=str(dest), delivery_kind="filesystem-path")
    _seed(binding)

    result = promote(NODE, accept_signal=_accept_signal(NODE))

    # The op does NOT report a successful delivery.
    assert not getattr(result, "ok", True) if hasattr(result, "ok") else True, (
        "a failed promote must not report ok=True (no silent success on failure)"
    )

    # deliverable_state=delivery-failed on the binding (the §3.2 failure value).
    after = _read()
    assert after["deliverable_state"] == "delivery-failed", (
        "a failed copy-out must set deliverable_state=delivery-failed (DAEMON §3.2) — NOT delivered, "
        f"NOT left unchanged; got {after['deliverable_state']!r} (the silent-success-on-failure mutant)"
    )

    # An escalation is journaled (the §6.3 run-ledger escalation seam — chokepoint precedent: a
    # failure emits an L1-readable escalation WAL row). We look for an escalation/failure row that
    # names this node.
    rows = _wal_rows_for(NODE)
    escalation_rows = [
        r for r in rows
        if "escal" in (r.get("event", "") or "").lower()
        or "fail" in (r.get("event", "") or "").lower()
        or r.get("binding_delta", {}).get("deliverable_state") == "delivery-failed"
    ]
    assert escalation_rows, (
        "a failed promote must ESCALATE — journal an L1-readable escalation/delivery-failed row in "
        f"the run-ledger (the §6.3 seam). Found events: {[r.get('event') for r in rows]}"
    )
    assert all(r.get("actor") == "harnessd" for r in escalation_rows), (
        "the escalation row must be attributable to harnessd (the control plane)"
    )


def test_failed_promote_leaves_write_targets_in_jail_source(runtime, tmp_path):
    """Even on failure, write_targets stays the in-jail source surface (never overloaded)."""
    promote = _promote_callable()
    _build_runtime_tree(runtime)
    blocker = tmp_path / "blocker-file2"
    blocker.write_text("file-not-dir\n", encoding="utf-8")
    dest = blocker / "demo-widget"

    binding, _ = _binding(delivery_destination=str(dest), delivery_kind="filesystem-path")
    _seed(binding)

    promote(NODE, accept_signal=_accept_signal(NODE))

    after = _read()
    assert after["write_targets"] == ["proj/demo-widget/"], (
        "write_targets must remain the in-jail source surface even on a failed promote"
    )


# ===========================================================================
# 6. GIT-REMOTE VARIANT — delivery_kind=git-remote. The promote PUSHES the
#    deliverable to a REAL local bare git repo (real `git init --bare` + real
#    `git push`), same accept gate. We assert the deliverable bytes are retrievable
#    from the bare remote (the push genuinely landed) and the binding shows
#    deliverable_state=delivered with delivery_destination recording the remote.
# ===========================================================================

def _git(args, cwd, check=True):
    env = {
        "GIT_AUTHOR_NAME": "harnessd",
        "GIT_AUTHOR_EMAIL": "harnessd@example.invalid",
        "GIT_COMMITTER_NAME": "harnessd",
        "GIT_COMMITTER_EMAIL": "harnessd@example.invalid",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_SYSTEM": "/dev/null",
        "HOME": str(cwd),
        "PATH": __import__("os").environ.get("PATH", ""),
    }
    return subprocess.run(
        ["git", *args], cwd=str(cwd), env=env,
        capture_output=True, text=True, check=check,
    )


def test_git_remote_promote_pushes_to_real_bare_remote(runtime, tmp_path):
    promote = _promote_callable()
    proj_dir = _build_runtime_tree(runtime)

    # The /runtime/ deliverable tree must be a real git repo with a commit for `git push` to have
    # something to push (the build produced the tree; here we make it a committed work tree).
    _git(["init", "-b", "main"], cwd=proj_dir)
    _git(["add", "-A"], cwd=proj_dir)
    _git(["commit", "-m", "finished deliverable"], cwd=proj_dir)

    # A REAL local bare repo standing in for the captured git remote (outside /runtime/).
    bare = tmp_path / "delivery-remote.git"
    _git(["init", "--bare", str(bare)], cwd=tmp_path)

    binding, _ = _binding(delivery_destination=str(bare), delivery_kind="git-remote")
    _seed(binding)

    result = promote(NODE, accept_signal=_accept_signal(NODE))
    assert getattr(result, "ok", result), f"git-remote promote should succeed; got {result!r}"

    # The push genuinely landed: clone the bare remote and assert the deliverable bytes are there.
    checkout = tmp_path / "verify-clone"
    clone = _git(["clone", str(bare), str(checkout)], cwd=tmp_path, check=False)
    assert clone.returncode == 0, (
        f"could not clone the delivery remote — the push did not land. stderr: {clone.stderr}"
    )
    landed = checkout / "src" / "widget.py"
    assert landed.is_file(), "deliverable was not pushed to the bare remote"
    assert "PROMOTED-DELIVERABLE-MARKER-7f3a" in landed.read_text("utf-8"), (
        "the pushed bytes are not the actual deliverable (push did not carry the real tree)"
    )

    # The binding records delivered + the remote, write_targets untouched.
    after = _read()
    assert after["deliverable_state"] == "delivered", (
        f"git-remote promote must set deliverable_state=delivered; got {after['deliverable_state']!r}"
    )
    assert after["delivery_destination"] == str(bare), (
        "delivery_destination must record the captured git remote"
    )
    assert after["write_targets"] == ["proj/demo-widget/"], (
        "write_targets must stay the in-jail source surface for the git-remote variant too"
    )


def test_git_remote_no_accept_is_noop_remote_empty(runtime, tmp_path):
    """The git-remote gate: with no accept, nothing is pushed to the bare remote (empty remote)."""
    promote = _promote_callable()
    proj_dir = _build_runtime_tree(runtime)
    _git(["init", "-b", "main"], cwd=proj_dir)
    _git(["add", "-A"], cwd=proj_dir)
    _git(["commit", "-m", "finished deliverable"], cwd=proj_dir)

    bare = tmp_path / "delivery-remote-empty.git"
    _git(["init", "--bare", str(bare)], cwd=tmp_path)

    binding, _ = _binding(delivery_destination=str(bare), delivery_kind="git-remote")
    _seed(binding)

    promote(NODE, accept_signal=None)

    # The bare remote has NO refs (nothing was pushed — the gate held).
    refs = _git(["for-each-ref"], cwd=bare, check=False)
    assert refs.stdout.strip() == "", (
        "a no-accept git-remote promote pushed to the remote — speculative push (gate missing)"
    )
    assert _read()["deliverable_state"] != "delivered", (
        "deliverable_state advanced to delivered on a no-accept git-remote promote"
    )
