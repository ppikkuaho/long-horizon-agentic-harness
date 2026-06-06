"""chokepoint — THE ONE spawn path (claim-before-spawn + rollback + the gate firewall).

Authoritative sources:
  - IMPLEMENTATION-PLAN §2.11 (the FROZEN chokepoint interface — exact signatures below):
        claim_and_spawn(node_address, *, expected_state, expected_generation,
                        expected_owner_token, level_config) -> SpawnResult
        resume(node_address, *, expected_state, expected_generation,
               expected_owner_token, delta_inputs, level_config) -> SpawnResult
        release_claim(node_address, *, expected_owner_token) -> None
        collapse(node_address, terminal_signal, *, expected_owner_token, ...) -> None
  - IMPLEMENTATION-PLAN §3 module table (chokepoint.py row): "NOT a writer — calls
    executor.transition() for every state change. On any post-claim failure, CAS-releases the claim
    (claimed->planned, bump epoch)."
  - DAEMON §6.1 (claim-before-spawn STEP0-5, the F-024 fix), §6.3 (the E32 spawn-failure contract),
    §6.4 (the gate firewall — LOCKED, correctness-not-optimization).
  - design/ROLE-RESOLUTION.md (the load-manifest assembled into the brief at STEP2).

THE F-024 STRUCTURAL FIX: the control-plane slot is CLAIMED (a REAL CAS transition into ``claimed``
via ``executor.claim`` under the REAL EX lock) STRICTLY BEFORE the actor opens. A lost claim means
``adapter.pin_and_open`` was NEVER reached — no double-spawn is possible. The chokepoint is NOT a
writer: every state change funnels through the single-writer executor.

THE GATE FIREWALL (LOCKED §6.4): ``resume`` refuses ``--resume`` across a crossed quality gate.
The firewall is the SINGLE enforcement point (necro.resume_brief delegates here, never re-raises).
The ``--resume`` argv is CONSTRUCTED ONLY on the gate-NOT-crossed else-branch — there is structurally
no code path that builds a ``--resume`` under ``gate_crossed_at != null``.

BUILDER DECISIONS (the §2.11 details the frozen tests leave open — stated in the build report):

  * ADAPTER INJECTION SEAM — the §2.11 signature carries NO adapter param, so the adapter is a
    module-level injectable (``set_adapter`` / ``ADAPTER``), exactly the ``ledger.RUNTIME_ROOT``
    precedent. The chokepoint orchestrates the adapter PORT; the concrete Claude/Codex fill is wired
    by the daemon (production) or the test (mock). No real adapter is constructed here.

  * ClaimLost RESULT — a lost CAS-claim returns a ``SpawnResult(ok=False, failure_class="claim_lost",
    …)`` — a NON-null ``failure_class`` distinguishes it from a real spawn AND it reads as a
    ClaimLost-flavored outcome (the repr carries "claim"/"lost"). No actor opened. FORK-CLAIMLOST:
    a distinct ``ClaimLost`` type would also satisfy §2.11; the SpawnResult-with-failure_class shape
    reuses the ONE result dataclass (base.SpawnResult) the adapter already returns.

  * THE ESCALATION RECORD (§6.3) — on a post-claim adapter SpawnFailure the chokepoint (1) RELEASES
    the claim (claimed->planned, bump epoch) and (2) emits an L1 escalation. The escalation surface is
    BOTH spec-faithful halves: the returned SpawnResult carries the ``failure_class`` (configured-vs-
    actual classification) AND a ``spawn_failed`` / escalation WAL row naming the child-address +
    which class fired is appended to the run-ledger (so an L1 reader sees it). FORK-ESCALATION: the
    precise downstream transport (an inbox row, a parent-notify) is a later cluster's fork; v1 surfaces
    it on the result + the WAL, the two channels the tests + an L1 reconcile reader can both observe.

  * ancestors_inclusive — STEP0's pause-subtree read-point walks THIS node + its ancestors via the
    binding's ``parent_address`` chain (DAEMON §3.2): start at ``node_address``, follow
    ``parent_address`` upward, collecting every binding, stopping at a null/empty parent or a missing
    binding (a missing ancestor is not paused — it cannot admit/deny). If ANY collected binding has
    ``paused_at != null`` the spawn ABORTS BEFORE the claim. FORK-ANCESTORS: the address-prefix walk
    (DAEMON §6.1 "address-prefix check over the node + its ancestors") and the parent_address-chain
    walk agree on a well-formed tree; the chain walk is authoritative because parent_address is the
    binding's own recorded edge (an address-string prefix can be spoofed by a sibling naming).
"""

from __future__ import annotations

from typing import Optional

from harnessd import config, executor, fencing, ledger
from harnessd.spawn import brief
from harnessd.spawn.adapters.base import SpawnResult
from harnessd.spawn.oauth_guard import SpawnFailure

# ---------------------------------------------------------------------------
# The adapter injection seam (§2.11 carries no adapter param — see module docstring).
# The daemon wires the concrete Claude/Codex fill; tests inject a mock recorder.
# ---------------------------------------------------------------------------

ADAPTER = None


def set_adapter(adapter) -> None:
    """Inject the RuntimeAdapter the chokepoint opens actors through (module-level seam)."""
    global ADAPTER
    ADAPTER = adapter


def _require_adapter():
    """Return the injected adapter, or fail loud (the chokepoint cannot spawn without a port)."""
    if ADAPTER is None:
        raise RuntimeError(
            "no RuntimeAdapter injected into the chokepoint: wire one via set_adapter(adapter) "
            "(the §2.11 signature carries no adapter param — the adapter is injected like "
            "ledger.RUNTIME_ROOT)"
        )
    return ADAPTER


# ---------------------------------------------------------------------------
# ClaimLost / failure result helpers — a lost claim or an aborted spawn is a
# NON-null-failure_class SpawnResult, distinguishable from a real spawn.
# ---------------------------------------------------------------------------

def _result_failed(failure_class: str, *, tmux_target: str = "", model_used: str = "") -> SpawnResult:
    """Build a not-ok SpawnResult carrying a ``failure_class`` (ClaimLost / SpawnFailure outcome).

    No actor opened (or the actor failed and was rolled back). ``failure_class`` names the outcome
    so the caller can distinguish a lost claim / a spawn failure from a successful spawn.
    """
    return SpawnResult(
        ok=False,
        session_uuid=None,
        model_used=model_used,
        role_variant="",
        system_prompt_file=config.SYSTEM_PROMPT_FILE,
        system_prompt_file_hash="",
        tmux_target=tmux_target,
        transcript_path=None,
        failure_class=failure_class,
    )


# ---------------------------------------------------------------------------
# STEP0 — the pause-subtree read-point (ancestors_inclusive).
# ---------------------------------------------------------------------------

def ancestors_inclusive(node_address: str) -> list[dict]:
    """Return THIS node's binding + every ancestor binding, walking ``parent_address`` upward.

    Starts at ``node_address`` and follows the binding's recorded ``parent_address`` edge (DAEMON
    §3.2) to the root, collecting each binding. Stops at a null/empty parent, a missing binding, or
    a cycle (defensive — a self/loop parent terminates the walk). A missing binding contributes
    nothing (it cannot pause a subtree). The returned list is the node + ancestors, inclusive.
    """
    collected: list[dict] = []
    seen: set[str] = set()
    addr: Optional[str] = node_address
    while addr and addr not in seen:
        seen.add(addr)
        binding = ledger.read_binding(addr)
        if binding is None:
            break
        collected.append(binding)
        parent = binding.get("parent_address")
        addr = parent or None
    return collected


def _subtree_paused(node_address: str) -> bool:
    """True iff THIS node or any ancestor has ``paused_at`` set (STEP0 admits no child if so)."""
    return any(b.get("paused_at") is not None for b in ancestors_inclusive(node_address))


# ---------------------------------------------------------------------------
# The escalation seam (§6.3) — emit an L1 spawn-failure escalation WAL row.
# ---------------------------------------------------------------------------

def _emit_spawn_failure_escalation(node_address: str, failure_class: str, model_used: str) -> None:
    """Append a spawn-failure escalation row to the run-ledger naming the child + which class fired.

    §6.3: on a refused spawn, RELEASE the claim and emit a spawn-failure escalation to L1
    (child-address + configured vs actual + which class fired). This is a DIRECT WAL append (not a
    lifecycle transition — the lifecycle rollback is the separate release_claim): an L1 reconcile
    reader sees the ``spawn_failed`` event naming the node + the class. Best-effort journaling — a
    journaling hiccup must not mask the underlying spawn failure, which is also carried on the result.
    """
    try:
        record = ledger.build_wal_record(
            node_address=node_address,
            event="spawn_failed",
            from_state="claimed",
            to_state="planned",
            expected_generation=None,
            generation=None,
            lease_epoch=None,
            owner_token=None,
            binding_delta={"failure_class": failure_class, "model_used": model_used},
            summary=(
                f"spawn-failure escalation -> L1: node {node_address} failed to spawn "
                f"(class={failure_class}, model_used={model_used}); claim released (§6.3)"
            ),
            artifacts=[],
            seq=ledger.next_seq(),
        )
        ledger.append_wal(record)
    except Exception:
        # The result already carries failure_class; a WAL hiccup must not swallow the spawn failure.
        return None


# ---------------------------------------------------------------------------
# release_claim — the standalone rollback edge (CAS claimed -> planned, bump epoch).
# ---------------------------------------------------------------------------

def release_claim(node_address: str, *, expected_owner_token: Optional[str]) -> None:
    """Release a claim: CAS ``claimed`` -> ``planned``, BUMP the epoch (§6.1 rollback edge).

    The first-class rollback edge. The release is itself a CAS-guarded transition (replayable via the
    WAL), so a failed claim is reclaimable: the slot returns to ``planned`` and the epoch advances
    AGAIN (claim 1->2, release 2->3) so the rolled-back slot fences the failed incarnation. NOT a
    writer itself — routes through ``executor.transition`` (the single writer). Re-mints the
    owner_token at the bumped epoch in the SAME candidate (F-012, no split window).
    """
    live = ledger.read_binding(node_address)
    if live is None:
        return None

    new_lease_epoch = fencing.advance_epoch(live)
    new_owner_token = fencing.mint_owner_token(
        node_address,
        live.get("subagent_id"),
        live.get("session_uuid"),
        new_lease_epoch,
    )
    executor.transition(
        node_address,
        expected_state="claimed",
        expected_generation=live["generation"],
        expected_owner_token=expected_owner_token,
        target_state="planned",
        binding_delta={
            "state": "planned",
            "lease_epoch": new_lease_epoch,
            "owner_token": new_owner_token,
        },
        new_lease_epoch=new_lease_epoch,
        new_owner_token=new_owner_token,
        event="release_claim",
        summary="claim released: CAS claimed->planned, bump epoch (rollback edge, §6.1)",
    )
    return None


# ---------------------------------------------------------------------------
# The shared post-claim spawn body (STEP2-5) — used by claim_and_spawn and resume's branches.
# ---------------------------------------------------------------------------

def _spawn_after_claim(
    node_address: str,
    claimed_binding: dict,
    level_config,
    spawn_brief: dict,
) -> SpawnResult:
    """STEP2-5 after a committed claim: assemble brief, open the actor, record facts, reach running.

    The claim is ALREADY committed (``claimed_binding`` is the post-claim binding: state='claimed',
    bumped epoch, re-minted owner_token). On ANY failure STEP2-5 the claim is RELEASED
    (claimed->planned, bump epoch) and a spawn-failure escalation is emitted (§6.3). On success the
    node ends in ``running`` with the actual session_uuid / transcript_path / model_used recorded.
    """
    adapter = _require_adapter()
    post_claim_token = claimed_binding["owner_token"]
    post_claim_generation = claimed_binding["generation"]

    # STEP3 — pin + open the actor. The claim is STRICTLY before this (the F-024 ordering).
    try:
        spawn_result = adapter.pin_and_open(spawn_brief, level_config, node_address, _spawn_env())
    except SpawnFailure as exc:
        # POST-claim failure (§6.3): release the claim and escalate to L1 with the class that fired.
        failure_class = getattr(exc, "failure_class", None) or "model_unavailable"
        model_used = getattr(exc, "model_used", "")
        release_claim(node_address, expected_owner_token=post_claim_token)
        _emit_spawn_failure_escalation(node_address, failure_class, model_used)
        return _result_failed(failure_class, tmux_target=node_address, model_used=model_used)

    if not getattr(spawn_result, "ok", False):
        # The adapter reported a non-ok spawn without raising — treat as a post-claim failure too.
        failure_class = getattr(spawn_result, "failure_class", None) or "runtime_down"
        release_claim(node_address, expected_owner_token=post_claim_token)
        _emit_spawn_failure_escalation(node_address, failure_class, getattr(spawn_result, "model_used", ""))
        return _result_failed(failure_class, tmux_target=node_address)

    # STEP4 — record the actor's products (session_uuid + the NON-NULL transcript_path + the ACTUAL
    # model_used) via the single writer. claimed -> spawning. config = intent; model_used = fact.
    step4 = executor.transition(
        node_address,
        expected_state="claimed",
        expected_generation=post_claim_generation,
        expected_owner_token=post_claim_token,
        target_state="spawning",
        binding_delta={
            "session_uuid": spawn_result.session_uuid,
            "transcript_path": spawn_result.transcript_path,
            "model_used": spawn_result.model_used,
            "role_variant": spawn_result.role_variant,
            "system_prompt_file": spawn_result.system_prompt_file,
        },
        event="spawn_open",
        summary="STEP4: actor opened; record session_uuid + transcript_path + model_used (claimed->spawning)",
    )
    if not step4.ok:
        release_claim(node_address, expected_owner_token=post_claim_token)
        _emit_spawn_failure_escalation(node_address, "runtime_down", spawn_result.model_used)
        return _result_failed("runtime_down", tmux_target=node_address)

    # STEP5 — confirm boot: spawning -> running. The owner_token/epoch are unchanged across STEP4/5
    # (the claim minted them); the generation advanced by STEP4.
    step5 = executor.transition(
        node_address,
        expected_state="spawning",
        expected_generation=step4.binding["generation"],
        expected_owner_token=post_claim_token,
        target_state="running",
        binding_delta={},
        event="spawn_running",
        summary="STEP5: actor confirmed boot (spawning->running)",
    )
    if not step5.ok:
        # The actor opened but the running transition failed: still a post-claim failure -> rollback.
        # (release_claim CAS targets 'claimed'; the node is now 'spawning', so route the rollback
        # spawning->planned through the executor directly with the live token.)
        _rollback_spawning(node_address, post_claim_token)
        _emit_spawn_failure_escalation(node_address, "runtime_down", spawn_result.model_used)
        return _result_failed("runtime_down", tmux_target=node_address)

    return spawn_result


def _rollback_spawning(node_address: str, expected_owner_token: str) -> None:
    """Roll a ``spawning`` node back to ``planned`` (the §6.1 spawning->planned rollback edge)."""
    live = ledger.read_binding(node_address)
    if live is None or live.get("state") != "spawning":
        return None
    new_lease_epoch = fencing.advance_epoch(live)
    new_owner_token = fencing.mint_owner_token(
        node_address,
        live.get("subagent_id"),
        live.get("session_uuid"),
        new_lease_epoch,
    )
    executor.transition(
        node_address,
        expected_state="spawning",
        expected_generation=live["generation"],
        expected_owner_token=expected_owner_token,
        target_state="planned",
        binding_delta={
            "state": "planned",
            "lease_epoch": new_lease_epoch,
            "owner_token": new_owner_token,
        },
        new_lease_epoch=new_lease_epoch,
        new_owner_token=new_owner_token,
        event="release_claim",
        summary="actor-open-confirm failed: spawning->planned rollback, bump epoch (§6.1)",
    )
    return None


def _spawn_env() -> dict:
    """The 4-var isolation env the adapter opens the pane with (DAEMON §6.2).

    The chokepoint orchestrates; the env is the OAuth-only isolation set the adapter expects. The
    concrete credential values are resolved by the daemon at boot; v1 carries the structural 4-var
    shape (no raw API key, never a --resume token) so the gate firewall's no-resume scan is clean.
    """
    return {
        "CLAUDE_CONFIG_DIR": "$HARNESS/.cc-pinned/config",
        "CLAUDE_CODE_OAUTH_TOKEN": "<oauth-token-file>",
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
        "DISABLE_AUTOUPDATER": "1",
    }


# ---------------------------------------------------------------------------
# claim_and_spawn — STEP0-5 (the F-024 claim-before-spawn path).
# ---------------------------------------------------------------------------

def claim_and_spawn(
    node_address: str,
    *,
    expected_state: str,
    expected_generation: int,
    expected_owner_token: Optional[str],
    level_config,
) -> SpawnResult:
    """THE spawn path (§6.1 STEP0-5). Claim STRICTLY before the actor (F-024).

    STEP0 pause-subtree read-point (abort BEFORE claiming if the subtree is paused);
    STEP1 CAS-claim into ``claimed`` (a lost claim -> ClaimLost, NO actor opened);
    STEP2 assemble the runtime-neutral brief + load-manifest;
    STEP3 adapter.pin_and_open (the actor opens — STRICTLY after the committed claim);
    STEP4 record session_uuid + NON-NULL transcript_path + actual model_used (claimed->spawning);
    STEP5 spawning->running.
    On ANY post-claim failure STEP2-5: release_claim (claimed->planned, bump epoch) + L1 escalation.
    """
    # STEP0 — a paused subtree admits no child: ABORT BEFORE claiming (no claim, no actor).
    if _subtree_paused(node_address):
        return _result_failed("paused_subtree", tmux_target=node_address)

    # STEP1 — the CAS-claim (a REAL transition into ``claimed`` under the REAL EX lock). A lost claim
    # (wrong CAS precondition) returns ClaimLost with the binding UNCHANGED and NO actor opened.
    claim_result = executor.claim(
        node_address,
        expected_state=expected_state,
        expected_generation=expected_generation,
        expected_owner_token=expected_owner_token,
        level_config=level_config,
    )
    if not claim_result.ok:
        # F-024: the slot was claimed by someone else (or the CAS precondition missed) -> NO actor
        # opened (we have not reached the adapter), the binding is unchanged. ClaimLost.
        return _result_failed("claim_lost", tmux_target=node_address)

    # STEP2 — assemble the runtime-neutral brief + the role_variant-selected load-manifest.
    work_node = _work_node_for(node_address, claim_result.binding)
    neutral = brief.assemble_neutral(node_address, level_config, work_node)
    spawn_brief = _brief_payload(neutral)

    # STEP3-5 — open the actor, record facts, reach running (rollback on any failure).
    return _spawn_after_claim(node_address, claim_result.binding, level_config, spawn_brief)


def _work_node_for(node_address: str, binding: dict) -> dict:
    """Assemble the durable work-node pointer the brief is built against (read off the binding).

    v1 derives the pointers from the binding's recorded fields where present; absent fields are left
    None (the brief tolerates a sparse work node). The durable work-node authoring is a node-local
    artifact (status/log/report live under the node's workspace) — the chokepoint points at it.
    """
    binding = binding or {}
    return {
        "node_address": node_address,
        "workspace": binding.get("workspace"),
        "spec_pointer": binding.get("spec_pointer"),
        "frozen_acceptance_ref": binding.get("frozen_acceptance_ref"),
        "status_md": binding.get("status_md"),
        "log_md": binding.get("log_md"),
        "report_md": binding.get("report_md"),
    }


def _brief_payload(neutral) -> dict:
    """Flatten the NeutralContract into the dict the adapter's pin_and_open consumes.

    Carries the load-manifest (role-as-documents) + identity/acceptance/spec — and CRUCIALLY no
    ``--resume`` / session-continuation token (the gate-firewall scan asserts no fresh spawn ever
    carries one). role_variant rides the brief so the adapter selects the right manifest.
    """
    return {
        "node_address": neutral.node_address,
        "role_variant": neutral.role_variant,
        "level": neutral.level,
        "system_prompt_file": neutral.system_prompt_file,
        "load_manifest": list(neutral.load_manifest),
        "spec_pointer": neutral.spec_pointer,
        "frozen_acceptance_ref": neutral.frozen_acceptance_ref,
        "workspace": neutral.workspace,
        "reporting": neutral.reporting,
    }


# ---------------------------------------------------------------------------
# resume — the spawn variant with the GATE FIREWALL (the SINGLE enforcement point, LOCKED §6.4).
# ---------------------------------------------------------------------------

def resume(
    node_address: str,
    *,
    expected_state: str,
    expected_generation: int,
    expected_owner_token: Optional[str],
    delta_inputs: dict,
    level_config,
) -> SpawnResult:
    """Resume a live/dead address through the chokepoint, WITH the gate firewall (§6.4 — LOCKED).

    THE FIREWALL (the single, authoritative never-resume-across-the-gate point):

      * gate_crossed_at != null  -> REFUSE ``--resume``. Fall back to a FRESH spawn with a DELTA
        brief: re-adopt the live address via ``executor.claim`` (expected_state in {running, dead}),
        then open a FRESH actor recording a NEW session_uuid. The ``--resume`` argv is NEVER built on
        this branch — a crossed gate re-spawns clean, carrying NO pre-gate session context.

      * gate_crossed_at == null  -> the ELSE-branch: re-adopt the live address AND build the
        ``--resume`` continuation (the ONLY place a ``--resume`` argv is ever constructed). Bumps the
        epoch + re-mints the owner_token (fences the prior incarnation) and records a NEW session_uuid.

    STRUCTURAL guarantee: because the ``--resume`` argv is constructed ONLY on the else-branch, there
    is no code path that builds a ``--resume`` under ``gate_crossed_at != null`` — the firewall cannot
    be bypassed (necro.resume_brief delegates here; it owns no second copy of the check).
    """
    live = ledger.read_binding(node_address)
    if live is None:
        return _result_failed("absent_node", tmux_target=node_address)

    gate_crossed = live.get("gate_crossed_at") is not None

    # Re-adopt the live address through the claim (the §6.4 re-adopt variant). expected_state is the
    # caller's {running, dead}; the claim bumps the epoch + re-mints the owner_token (fences the prior
    # incarnation). This is claim-before-spawn for resume too — it never double-spawns a live address.
    claim_result = executor.claim(
        node_address,
        expected_state=expected_state,
        expected_generation=expected_generation,
        expected_owner_token=expected_owner_token,
        level_config=level_config,
    )
    if not claim_result.ok:
        return _result_failed("claim_lost", tmux_target=node_address)

    # STEP2 — assemble the DELTA brief (what changed since the prior incarnation, pointing at the
    # durable work node). The prior incarnation is the pre-claim live binding.
    work_node = _work_node_for(node_address, claim_result.binding)
    prior_incarnation = {
        "session_uuid": live.get("session_uuid"),
        "lease_epoch": live.get("lease_epoch"),
        "generation": live.get("generation"),
    }
    delta = brief.delta_brief(node_address, prior_incarnation, work_node, delta_inputs or {})
    spawn_brief = _delta_brief_payload(delta)

    if gate_crossed:
        # ---- GATE CROSSED: REFUSE --resume. Fall back to a FRESH spawn (no --resume argv built). ----
        # spawn_brief carries NO resume continuation; the pre-gate session is NOT threaded anywhere.
        # The actor opens FRESH, recording a NEW session_uuid (the firewall's whole purpose).
        return _spawn_after_claim(node_address, claim_result.binding, level_config, spawn_brief)

    # ---- ELSE (clean gate): re-adopt + build the --resume continuation (the ONLY place it is built). ----
    spawn_brief = _attach_resume_continuation(spawn_brief, live.get("session_uuid"))
    return _spawn_after_claim(node_address, claim_result.binding, level_config, spawn_brief)


def _delta_brief_payload(delta) -> dict:
    """Flatten the DeltaBrief into the dict the adapter consumes (no --resume token here).

    The base delta payload carries NO session-continuation marker — the ``--resume`` is attached ONLY
    on resume's clean-gate else-branch (``_attach_resume_continuation``), never here, so a crossed-gate
    fallback that uses this payload directly is structurally resume-free.
    """
    return {
        "node_address": delta.node_address,
        "changes": dict(delta.changes),
        "delta": delta.delta,
        "workspace": delta.workspace,
        "frozen_acceptance_ref": delta.frozen_acceptance_ref,
        "prior_lease_epoch": delta.prior_incarnation.get("lease_epoch"),
    }


def _attach_resume_continuation(spawn_brief: dict, prior_session_uuid) -> dict:
    """Attach the ``--resume`` session-continuation to the brief — the ONLY place this is built.

    Called ONLY on resume's clean-gate else-branch (gate_crossed_at == null). Adds the resume argv
    marker + the prior session as the continuation target. Because this is the SINGLE construction
    site and it is unreachable under a crossed gate, the firewall is structural, not merely guarded.
    """
    enriched = dict(spawn_brief)
    enriched["resume_session"] = prior_session_uuid
    enriched["resume_argv"] = ["--resume", str(prior_session_uuid)]
    return enriched


# ---------------------------------------------------------------------------
# collapse — the terminal write carrying the in_flight RELEASE-DECREMENT (§3.6 / §6.1).
# done/failed/dead collapse; ESCALATED is NOT a collapse (asymmetric — state stays running).
# ---------------------------------------------------------------------------

# The terminal signals that DO collapse a node (symmetric to STEP1's claim-increment). ESCALATED is
# DELIBERATELY absent: it is asymmetric (§3.6) — the terminal_signal is set but the state stays running.
_COLLAPSE_TARGETS: dict[str, str] = {
    "DONE": "done",
    "FAILED": "failed",
    "DIED": "failed",
    "DIED_INFRA": "failed",
    "DIED_METHODOLOGY": "failed",
    "DEAD": "dead",
}


def collapse(
    node_address: str,
    terminal_signal: str,
    *,
    expected_owner_token: Optional[str],
    **_unused,
) -> None:
    """The terminal collapse (§6.1 / §3.6): route the terminal transition + carry the release-decrement.

    ``DONE`` -> done, ``FAILED``/``DIED*`` -> failed, ``DEAD`` -> dead. The terminal transaction
    carries cluster ④'s in_flight RELEASE-DECREMENT (symmetric to STEP1's claim-increment). NOT a
    writer itself — routes through ``executor.transition`` (the single writer), crash-safe via
    last_applied_seq.

    ESCALATED is NOT a collapse (§3.6, ASYMMETRIC): the terminal_signal is set but the lifecycle state
    STAYS ``running`` and the node is NOT torn down. ``collapse`` REFUSES the ESCALATED signal (raises)
    so a caller cannot collapse a node that is merely waiting for the answer round-trip.
    """
    if terminal_signal == "ESCALATED":
        raise ValueError(
            "ESCALATED is NOT a collapse (§3.6 ASYMMETRIC): the terminal_signal is set but the "
            "lifecycle state STAYS running — collapsing on ESCALATED would tear the node off its "
            "slot while it waits for the answer round-trip. Refusing."
        )

    target_state = _COLLAPSE_TARGETS.get(terminal_signal)
    if target_state is None:
        raise ValueError(
            f"unknown terminal_signal {terminal_signal!r}: collapse routes only the terminal "
            f"vocabulary {sorted(_COLLAPSE_TARGETS)} (ESCALATED is asymmetric, not a collapse)"
        )

    live = ledger.read_binding(node_address)
    if live is None:
        return None

    # The terminal transition carries the in_flight RELEASE-DECREMENT (the slot the §6.1 claim
    # reserved is released here). We record the terminal_signal into the binding alongside the
    # lifecycle collapse, symmetric to STEP1's claim-increment seat.
    executor.transition(
        node_address,
        expected_state=live["state"],
        expected_generation=live["generation"],
        expected_owner_token=expected_owner_token,
        target_state=target_state,
        binding_delta={
            "terminal_signal": terminal_signal,
            "in_flight_release": True,
        },
        event=f"collapse_{target_state}",
        summary=(
            f"terminal collapse: {terminal_signal} -> {target_state} "
            "(carries ④ in_flight RELEASE-DECREMENT, symmetric to STEP1 claim-increment; §6.1/§3.6)"
        ),
    )
    return None
