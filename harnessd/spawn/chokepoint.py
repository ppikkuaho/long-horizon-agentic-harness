"""chokepoint — THE ONE spawn path (claim-before-spawn + rollback + the gate firewall).

Authoritative sources:
  - IMPLEMENTATION-PLAN §2.11 (the FROZEN chokepoint interface — exact signatures below):
        claim_and_spawn(node_address, *, expected_state, expected_generation,
                        expected_owner_token, level_config) -> SpawnResult
        resume(node_address, *, expected_state, expected_generation,
               expected_owner_token, delta_inputs, level_config) -> SpawnResult
        release_claim(node_address, *, expected_owner_token) -> None
        collapse(node_address, terminal_signal, *, expected_owner_token, ...) -> Optional[TransitionResult]
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

import dataclasses
import json
import os
from pathlib import Path
from typing import Optional

from harnessd import addressing, config, executor, fencing, ledger, states, store
from harnessd.spawn import brief, sandbox
from harnessd.spawn.adapters.base import SpawnResult
from harnessd.spawn.oauth_guard import (
    PLACEHOLDER_CONFIG_DIR,
    PLACEHOLDER_OAUTH_TOKEN,
    ApiKeyForbidden,
    SpawnFailure,
)

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
# The spawn-env injection seam (LT-1) — mirrors set_adapter. The daemon binds the REAL
# commissioned 4-var OAuth env at boot (daemon.boot reads runtime.config.env); when nothing is
# bound, _spawn_env() falls back to the STRUCTURAL placeholders (keeps the dry-run tests intact).
# ---------------------------------------------------------------------------

SPAWN_ENV: Optional[dict] = None


def set_spawn_env(env: Optional[dict]) -> None:
    """Bind (or clear) the REAL pane env every structural spawn opens with (module-level seam).

    Production: ``daemon.boot`` binds commissioning's assembled 4-var OAuth-only env
    (``runtime.config.env`` — live token + the pinned CLAUDE_CONFIG_DIR) so the env that passed
    the genesis credential precondition is the SAME env the pane actually boots with (LT-1: the
    placeholder env never reaches a real pane). ``set_spawn_env(None)`` restores the structural
    placeholder fallback (the dry-run shape).
    """
    global SPAWN_ENV
    SPAWN_ENV = dict(env) if env is not None else None


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


def subtree_paused(node_address: str) -> bool:
    """True iff THIS node or any ancestor has ``paused_at`` set — the pause-subtree predicate.

    PUBLIC (F16): both enforcing read-points share this ONE node-or-ancestor walk so the
    prefix semantics cannot drift — the spawn chokepoint's STEP0 (DAEMON §6.1: a paused
    subtree admits no child) AND the watchdog's §3.4 STEP 0 gate (WATCHDOG: a paused subtree
    gets no recovery action).
    """
    return any(b.get("paused_at") is not None for b in ancestors_inclusive(node_address))


_subtree_paused = subtree_paused  # back-compat alias (the pre-F16 private name)


# ---------------------------------------------------------------------------
# Stale-pane teardown (LT-4/INT-1) — the idempotent prior-incarnation kill the
# resume / re-register paths run before reopening a deterministic session name.
# ---------------------------------------------------------------------------

def kill_stale_pane(tmux_target: Optional[str]) -> None:
    """Best-effort, IDEMPOTENT teardown of a PRIOR incarnation's recorded pane (LT-4/INT-1).

    ``addressing.session_name_for`` is deterministic per address, so a respawn at an address whose
    previous incarnation's pane still exists collides in ``create_detached`` ('duplicate session' ->
    SpawnFailure tmux_session_collision). The resume / re-register paths call this with the FENCED
    prior incarnation's recorded ``tmux_target``, strictly AFTER the re-adopting claim committed
    (the epoch bump already fenced the prior incarnation — no live owner holds that pane) and
    strictly BEFORE the fresh ``create_detached``. Routed through the injected adapter's OWN tmux
    seam (a mock without ``kill`` skips — the dry-run tears nothing down); ``tmux.kill`` itself is
    idempotent (a session already gone is not an error), and any teardown hiccup is swallowed —
    the collision SpawnFailure at create_detached remains the loud net.
    """
    if not tmux_target:
        return
    kill = getattr(getattr(ADAPTER, "tmux", None), "kill", None)
    if kill is None:
        return
    try:
        kill(tmux_target)
    except Exception:  # noqa: BLE001 — best-effort teardown; the collision SpawnFailure is the net
        pass


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

def _write_signoff_handshake(node_address: str, owner_token: str) -> None:
    """Seed the per-incarnation sign-off HANDSHAKE into the node dir (F19 — the token delivery).

    ``<node-dir>/.sign-off.<seat>.json`` carries the POST-claim re-minted ``owner_token``, the
    absolute ``.signal.<seat>.json`` path, and the signal schema. Written strictly AFTER the claim
    commits (a lost claim never reaches this — no loser-token handshake can land) and strictly
    BEFORE ``adapter.pin_and_open`` (the agent can read it from its first turn). This is the ONLY
    channel that delivers the fence token to the live agent: the brief payload omits it, brief.md
    may be pre-authored at plan time BEFORE the claim mints the token, and the unjailed pane env is
    contractually EXACTLY the 4 isolation vars (claude_code adapter) — so a node-dir file is the one
    channel that survives all three. The agent copies ``owner_token`` VERBATIM into its
    ``.signal.<seat>.json``; the fenced reader (detector_signals.read_terminal_signal) silently
    ignores any other token.

    Refreshed by THIS same write-point on every re-claim (the §6.4 resume flows through
    ``_spawn_after_claim``), so the file always names the CURRENT incarnation's token. A stale
    leftover (a post-claim spawn failure releases the claim at a bumped epoch) is harmless: the
    fence rejects its token, and the next successful claim overwrites the file BEFORE the new pane
    opens.

    NODE-WORKSPACE SEEDING (like brief.md), NOT a ledger write — the executor stays the single
    ledger writer; no TransitionResult is produced or swallowed here.
    """
    if ledger.RUNTIME_ROOT is None:
        raise RuntimeError(
            "_write_signoff_handshake: ledger.RUNTIME_ROOT is not bound — the handshake lands under "
            "the runtime tree (nodes/<nested-path>/.sign-off.<seat>.json); bind it (daemon startup / "
            "tests). Never a silent skip: an agent without the handshake cannot sign off (its "
            "terminal signal would be fenced as stale)."
        )
    payload = {
        "owner_token": owner_token,
        "signal_path": str(addressing.signal_path(node_address, ledger.RUNTIME_ROOT)),
        "schema": {
            "signal": "DONE|FAILED|ESCALATED",
            "ts": "ISO-8601 UTC",
            "owner_token": "<this token, verbatim>",
            "evidence": "optional dict (e.g. {report: 'report.md', notes: '<failure reason / the ESCALATED question>'})",
        },
    }
    store.atomic_replace(
        addressing.signoff_path(node_address, ledger.RUNTIME_ROOT),
        lambda h: (h.write(json.dumps(payload, indent=2)), h.write("\n")),
    )


def _spawn_after_claim(
    node_address: str,
    claimed_binding: dict,
    level_config,
    spawn_brief,
    spawn_env: Optional[dict] = None,
) -> SpawnResult:
    """STEP2-5 after a committed claim: assemble brief, open the actor, record facts, reach running.

    The claim is ALREADY committed (``claimed_binding`` is the post-claim binding: state='claimed',
    bumped epoch, re-minted owner_token). On ANY failure STEP2-5 the claim is RELEASED
    (claimed->planned, bump epoch) and a spawn-failure escalation is emitted (§6.3). On success the
    node ends in ``running`` with the actual session_uuid / transcript_path / model_used recorded.

    ``spawn_env`` is the pane env handed to the adapter. The JAIL-WIRING path passes the
    cache-redirect-MERGED env (a containment spawn); the structural path passes None, falling back to
    the bare 4-var ``_spawn_env()`` (UNJAILED — exactly the 4 isolation vars, the Increment-14
    integration-B contract).
    """
    adapter = _require_adapter()
    post_claim_token = claimed_binding["owner_token"]
    post_claim_generation = claimed_binding["generation"]
    pane_env = _spawn_env() if spawn_env is None else spawn_env

    # STEP2b — seed the sign-off HANDSHAKE (F19): strictly AFTER the committed claim
    # (post_claim_token IS the re-minted token) and strictly BEFORE the actor opens, so the agent
    # reads its owner_token + signal path in place from its very first turn. A lost claim never
    # reaches here (the F-024 ordering), so a loser token never lands in the node dir.
    _write_signoff_handshake(node_address, post_claim_token)

    # STEP3 — pin + open the actor. The claim is STRICTLY before this (the F-024 ordering).
    try:
        spawn_result = adapter.pin_and_open(spawn_brief, level_config, node_address, pane_env)
    except (SpawnFailure, ApiKeyForbidden) as exc:
        # POST-claim failure (§6.3): release the claim and escalate to L1 with the SPECIFIC class that
        # fired. ApiKeyForbidden is caught here too (it is NOT a SpawnFailure but is a post-claim spawn
        # refusal) — else it leaks UNCAUGHT past the chokepoint, crashing the spawn path AND leaving the
        # claim committed (review claude_code-3). Each exception now carries its own failure_class
        # (auth_expired / api_key_forbidden / …) so an auth lapse no longer masquerades as a model outage.
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
            # F18/OSA-01: the CANONICAL live target ('<session>:<window>.<pane>', tmux's own
            # post-rename report returned by create_detached) overwrites the registration
            # placeholder — pane_alive / the reconcile sweep / send-keys key off THIS value.
            **({"tmux_target": spawn_result.tmux_target} if spawn_result.tmux_target else {}),
            # The journaled permission posture (SECURITY.md §4.3 — auditable like OAuth-only):
            # 'jailed-skip-permissions' | 'unjailed-prompting' |
            # 'unjailed-skip-permissions-override' (the USER-APPROVED supervised-smoke knob).
            # Stamped only when the adapter reports it (a fake/legacy fill omitting the field
            # leaves the binding unchanged).
            **(
                {"permission_posture": spawn_result.permission_posture}
                if getattr(spawn_result, "permission_posture", None)
                else {}
            ),
        },
        event="spawn_open",
        summary="STEP4: actor opened; record session_uuid + transcript_path + model_used + canonical "
                "tmux_target (claimed->spawning)",
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

    # STEP6 — the KICKOFF (the transport increment): deliver the agent's starting instruction.
    # Durable-artifact-FIRST then best-effort nudge (the architecture's own pattern): the kickoff
    # line lands in the node's .inbox.<seat>.jsonl (the multi-writer append log the ③-wake tails),
    # THEN the pointer is typed into the live pane. A lost keystroke is HEALED by the watchdog's
    # ③-wake: the inbox line sits unacked past the watermark, so the next poll re-nudges. Pointer,
    # never payload (the wake_keystroke discipline — the brief content stays in brief.md).
    # Best-effort by construction: a kickoff hiccup never rolls back a successfully RUNNING node.
    _deliver_kickoff(node_address, spawn_result, adapter)

    return spawn_result


def _deliver_kickoff(node_address: str, spawn_result, adapter) -> None:
    """STEP6: append the kickoff pointer to the node's inbox, then best-effort send-keys it.

    (1) DURABLE FIRST — one JSON line in ``addressing.inbox_path`` (the same line discipline the
        F16 answer verb uses: from/type/message/ts). This is the artifact the ③-wake edge-trigger
        reads: as long as it sits past ``last_inbox_acked_offset``, the watchdog keeps re-nudging,
        so the kickoff cannot be lost to a dropped keystroke.
    (2) BEST-EFFORT NUDGE — ``tmux.send_keys(<canonical tmux_target>, pointer)`` through the
        adapter's OWN tmux seam (the same transport that opened the pane; mocks without
        ``send_keys`` simply skip — the dry-run never types). The pointer names WHO the agent is,
        WHERE its brief lands (the workspace it booted in, F18 cwd), and WHICH inbox messages
        arrive in — never the brief/task content itself.
    """
    from harnessd import clock

    if ledger.RUNTIME_ROOT is None:
        return  # no runtime tree (a bare adapter-level dry-run) -> nothing durable to land

    seat = addressing.split_address(node_address)[1]
    node_dir = addressing.node_dir(node_address, ledger.RUNTIME_ROOT)
    inbox = addressing.inbox_path(node_address, ledger.RUNTIME_ROOT)
    pointer = (
        f"You are {node_address}. Read brief.md in your workspace at {node_dir} and begin. "
        f"Messages arrive in .inbox.{seat}.jsonl."
    )

    # (1) the durable kickoff line (multi-writer append log — NOT the single-writer ledger).
    line = {"from": "harnessd", "type": "kickoff", "message": pointer, "ts": clock.now_utc()}
    try:
        inbox.parent.mkdir(parents=True, exist_ok=True)
        with inbox.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(line) + "\n")
    except OSError:
        # Journal best-effort; the spawn itself is already running and must not be rolled back.
        try:
            ledger.append_wal(ledger.build_wal_record(
                node_address=node_address, event="kickoff_append_failed",
                from_state="running", to_state="running", expected_generation=None,
                generation=None, lease_epoch=None, owner_token=None,
                binding_delta={"inbox": str(inbox)},
                summary=f"kickoff inbox append failed for {node_address} (inbox {inbox})",
                artifacts=[], seq=ledger.next_seq(),
            ))
        except Exception:  # noqa: BLE001
            pass
        return  # no durable line -> do not type a nudge the wake could never heal/repeat

    # (2) the best-effort pane nudge. A lost keystroke is healed by the ③-wake on the unacked line.
    send = getattr(getattr(adapter, "tmux", None), "send_keys", None)
    if send is not None and getattr(spawn_result, "tmux_target", None):
        try:
            send(spawn_result.tmux_target, pointer)
        except Exception:  # noqa: BLE001 — fire-and-forget; the unacked inbox line re-nudges
            pass


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

    The chokepoint orchestrates; the env is the OAuth-only isolation set the adapter expects.
    The concrete credential values are resolved by the daemon at boot and BOUND through
    ``set_spawn_env`` (LT-1: ``daemon.boot`` threads ``runtime.config.env`` — commissioning's
    live token + pinned CLAUDE_CONFIG_DIR — into this seam, so every production spawn boots the
    pane with the SAME env that passed the genesis credential precondition). When nothing is
    bound (the dry-run/structural tests), this falls back to the 4-var placeholder shape (no raw
    API key, never a --resume token) so the gate firewall's no-resume scan stays clean — and the
    REAL transport refuses to launch the token sentinel (tmux.create_detached, fail-loud).
    """
    if SPAWN_ENV is not None:
        return dict(SPAWN_ENV)
    return {
        "CLAUDE_CONFIG_DIR": PLACEHOLDER_CONFIG_DIR,
        "CLAUDE_CODE_OAUTH_TOKEN": PLACEHOLDER_OAUTH_TOKEN,
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
        "DISABLE_AUTOUPDATER": "1",
    }


# ---------------------------------------------------------------------------
# JAIL WIRING (§2.3/§2.5a/§7) — the containment-production step the v1 structural
# chokepoint owed. On a spawn that REQUESTS containment (a truthy
# ``level_config.containment`` opt-in, §2.5a "the per-spawn containment_profile is
# set by the parent/L1 at the chokepoint, carried in level_config") AND with
# ``ledger.RUNTIME_ROOT`` bound (needed to compute WORKROOT), the chokepoint
# RESOLVES the §2.5a block, ATTACHES it to the brief (dataclasses.replace onto the
# NeutralContract.containment_profile field), and MERGES the §2.3 cache-redirect env.
# On a spawn that does NOT request containment (the v1 structural chokepoint the
# Increment-14 integration-B + Increment-9 dry-run tests drive) NO containment is
# produced — the pane stays the bare ``env -i`` isolator with EXACTLY the 4 isolation
# vars. Jailing is gated on the EXPLICIT per-spawn REQUEST (NOT RUNTIME_ROOT presence
# alone — the structural integration-B spawn also has RUNTIME_ROOT set).
# ---------------------------------------------------------------------------

def _containment_requested(level_config) -> bool:
    """True iff this spawn carries the §2.5a per-spawn containment_profile REQUEST (opt-in).

    The request is a truthy ``level_config.containment`` flag the parent/L1 sets at the chokepoint
    (§2.5a). Jailing is gated on THIS explicit request — never on RUNTIME_ROOT-presence alone (the v1
    structural integration-B spawn also binds RUNTIME_ROOT yet stays UNJAILED).
    """
    return bool(getattr(level_config, "containment", False))


def _resolve_containment_config_dir() -> str:
    """Resolve the CONFIG dir handed to ``sandbox.resolve_containment`` (CC's own state-write root).

    FORK-CONTAINMENT-CONFIG (spec-faithful, STATED): §2.5c lists CONFIG (CLAUDE_CONFIG_DIR) as a
    write-allow root; the concrete on-disk dir is a deployment value the daemon binds at boot. v1
    reads it from the ``HARNESS_CC_CONFIG_DIR`` env override when present (the seam the production
    daemon/eval-spawn sets), else falls back to ``<RUNTIME_ROOT>/cc-config``. Either lands a REAL
    on-disk writable dir the adapter's ``_write_profile`` can write the rendered ``.sb`` into.
    """
    override = os.environ.get("HARNESS_CC_CONFIG_DIR")
    if override:
        return override
    return os.path.join(str(ledger.RUNTIME_ROOT), "cc-config")


def _produce_containment(node_address: str, level_config, neutral, env: dict):
    """Resolve + attach the §2.5a containment block and merge the §2.3 cache-redirect env.

    Returns ``(neutral, env)`` — the brief with the resolved block attached
    (``dataclasses.replace`` onto ``NeutralContract.containment_profile``) and the env with
    ``sandbox.cache_redirect_env(WORKROOT)`` merged in. Called ONLY when containment is REQUESTED
    and ``ledger.RUNTIME_ROOT`` is bound (the WORKROOT source); otherwise the caller leaves the
    structural brief/env untouched (UNJAILED).

    HOME resolution (FORK-CONTAINMENT-HOME, STATED): §2.5a anchors the secret-deny set on the user
    HOME; v1 lets ``sandbox.resolve_containment`` default HOME to ``os.path.expanduser("~")`` (its
    own documented default — the secret-deny anchor), so the chokepoint passes ``home=None``. A
    per-deployment HOME override is a deferred refinement.
    """
    block = sandbox.resolve_containment(
        node_address,
        runtime_root=ledger.RUNTIME_ROOT,
        config_dir=_resolve_containment_config_dir(),
        home=None,
    )
    neutral = dataclasses.replace(neutral, containment_profile=block)
    merged_env = dict(env)
    merged_env.update(sandbox.cache_redirect_env(block["WORKROOT"]))
    return neutral, merged_env


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
    if subtree_paused(node_address):
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

    # STEP2a — JAIL WIRING (§2.3/§2.5a/§7): on a spawn that REQUESTS containment AND with the runtime
    # root bound, PRODUCE the §2.5a block (resolve_containment), ATTACH it to the brief, and MERGE the
    # §2.3 cache-redirect env. A structural spawn (no request) leaves the brief/env UNJAILED — the
    # pane stays the bare ``env -i`` with exactly the 4 isolation vars (Increment-14 / Increment-9).
    spawn_env: Optional[dict] = None
    if _containment_requested(level_config) and ledger.RUNTIME_ROOT is not None:
        neutral, spawn_env = _produce_containment(node_address, level_config, neutral, _spawn_env())

    spawn_brief = _brief_payload(neutral)

    # STEP3-5 — open the actor, record facts, reach running (rollback on any failure).
    return _spawn_after_claim(
        node_address, claim_result.binding, level_config, spawn_brief, spawn_env
    )


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
        # JAIL WIRING: carry the resolved §2.5a containment block onto the adapter's dict brief so the
        # adapter's tolerant ``_resolve_containment`` jails the pane. None on the structural path.
        "containment_profile": neutral.containment_profile,
    }


# ---------------------------------------------------------------------------
# register_and_spawn_child — THE ONE parent-spawns-child path (the supervision-tree spawn).
#
# A PARENT (e.g. an L2) creates + briefs + spawns its CHILD (e.g. an L3). genesis registers the
# parentless L1 ROOT (_register_l1_root, parent_address=null); this is the GENERAL case the cascade
# below L1 needs: a live parent registers its child with parent_address SET, writes the brief into
# the child node, then hands it to the EXISTING claim_and_spawn (F-024 preserved). STEPS:
#   (1) PRECONDITION — the parent binding exists + is LIVE (non-terminal). Only a live parent spawns;
#       a dead/absent parent is REFUSED BEFORE any child register (no half-registered orphan slot).
#   (2) REGISTER — the child as a fresh planned slot under the parent (mirror _register_l1_root but
#       parent_address SET): generation=0, lease_epoch=1, a minted owner_token, written via the
#       single-writer lock-held ledger path. SAFE if the child already exists (does NOT clobber a
#       live/non-planned child — that lets the claim lose against it, single-owner preserved).
#   (3) BRIEF — DERIVATION by default (FORK-BRIEF-DERIVATION): the child binding carries
#       spec_pointer -> <node>/brief.md and frozen_acceptance_ref -> <node>/acceptance.md, both
#       PRE-AUTHORED by the parent into the child node at plan time (pointer-not-payload,
#       WORKSPACE-SCHEMA:221). A pre-authored brief.md is left intact; a brief_content OVERRIDE writes
#       it (the exception); neither present -> a manifest stub. The load-manifest also rides the
#       neutral contract to the adapter.
#   (4) SPAWN — the EXISTING chokepoint.claim_and_spawn(child, expected_state=planned, …) — the
#       F-024 claim-before-spawn (a lost claim opens NO actor; on a post-claim failure the claim is
#       released exactly as today).
#
# NODE LANDING (FORK-NODE-NESTING, revises FORK-BRIEF-LANDING): the node dir is NESTED by path
#   (``addressing.node_dir`` = ``<RUNTIME_ROOT>/nodes/<address-path>/``, the #seat stripped, the '/'
#   nesting KEPT), so a child's dir sits UNDER its parent's and the parent's WORKROOT-subtree write-jail
#   can seed brief.md/acceptance.md into it (ARCHITECTURE.md:122). The canonical files are lowercase
#   ``brief.md`` + ``acceptance.md``. The earlier flat ``'/'/'#' -> '__'`` collapse broke the nesting.
#
#   * FORK-CHILD-SUBTREE — child_address must be UNDER the parent subtree (the address-prefix edge).
#     v1 checks ``child_address.startswith(parent_address)`` defensively but does NOT hard-refuse a
#     non-prefixed child (the load-bearing supervision edge is parent_address recorded on the child
#     binding, which is set authoritatively from parent_address here regardless of the string shape;
#     an address-prefix can be spoofed by sibling naming — the recorded edge is authoritative, the
#     same reasoning as ancestors_inclusive's FORK-ANCESTORS).
#
#   * FORK-PARENT-TOKEN — ``expected_parent_owner_token`` authorizes spawning a child under a parent.
#     Two gates: (1) the parent's LIVENESS (non-terminal) is always required; (2) the token, WHEN
#     PRESENTED (non-None), is now a HARD fence — a mismatch is REFUSED before any child register
#     (STEP 1a returns ``_result_failed("parent_fence")``), so a caller can only spawn under a parent
#     it owns. A None token is the daemon-internal/genesis-style unfenced path (the EX lock + local IPC
#     are the bound). It is NEVER the child's claim precondition — the child claim uses the CHILD's
#     freshly-minted registered owner_token (the §6.1 claim CAS).
# ---------------------------------------------------------------------------

def _parent_is_live(parent_binding: Optional[dict]) -> bool:
    """True iff the parent binding exists AND is non-terminal (only a LIVE parent spawns a child)."""
    if parent_binding is None:
        return False
    return not states.is_terminal(parent_binding.get("state"))


def _sanitize_address(node_address: str) -> str:
    """Map a node address to a single filesystem-safe node-dir name ('/' and '#' -> '__')."""
    return node_address.replace("/", "__").replace("#", "__")


def _child_node_dir(node_address: str) -> Path:
    """The child node workspace dir — NESTED by path (``addressing.node_dir``), so a child's dir sits
    UNDER its parent's and the parent's WORKROOT-subtree write-jail can seed it (ARCHITECTURE.md:122)."""
    return addressing.node_dir(node_address, ledger.RUNTIME_ROOT)


def _register_child(
    child_address: str,
    parent_address: str,
    child_level_config,
    runtime_root: Path,
) -> Optional[dict]:
    """Register the child as a fresh ``planned`` slot UNDER the parent (mirror _register_l1_root).

    parent_address is SET (the supervision-tree edge — only the L1 root is parentless). generation=0,
    lease_epoch=1, a minted owner_token, written via the single-writer lock-held ledger path under the
    EX lock (the §2.10-sanctioned lock-held seeding the suite uses). SAFE if the child already exists:
    if a NON-planned child binding is already present (e.g. a RUNNING child from a prior spawn) this
    does NOT clobber it — it returns the LIVE binding so the caller's claim (expected_state=planned)
    loses against it (single-owner; no double-register of a live child). A child that is absent (or
    already terminal/planned) is (re-)registered as a fresh planned slot the claim can win.

    Returns the registered (or pre-existing-live) child binding.
    """
    live = ledger.read_binding(child_address)
    # SINGLE-OWNER: do NOT overwrite a live non-planned child (a running/claimed/spawning incarnation).
    # Returning it lets the caller's planned-expected claim lose against it (no double-open, F35/F-024).
    if live is not None and not states.is_terminal(live.get("state")) and live.get("state") != "planned":
        return live
    if live is not None and states.is_terminal(live.get("state")):
        # LT-4/INT-1: a TERMINAL child being re-registered (e.g. a watchdog-FAILED leaf the parent
        # re-spawns) may still hold its WARM pane — no production path killed it at FAILED/collapse.
        # The deterministic session name means the fresh claim_and_spawn below would collide
        # ('duplicate session'); tear the dead incarnation's recorded pane down first (idempotent).
        kill_stale_pane(live.get("tmux_target"))

    level = getattr(child_level_config, "level", None) or "L3"
    role_variant = getattr(child_level_config, "role_variant", None) or level
    subagent_id = "subagent-" + _sanitize_address(child_address)
    session_uuid = "registered-" + _sanitize_address(child_address)
    lease_epoch = 1
    generation = 0
    owner_token = fencing.mint_owner_token(child_address, subagent_id, session_uuid, lease_epoch)
    node_dir = _child_node_dir(child_address)
    binding = {
        "node_address": child_address,
        "parent_address": parent_address,  # the supervision-tree edge — SET (not null), DAEMON §7
        "level": level,
        "subagent_id": subagent_id,
        "session_uuid": session_uuid,
        # The PRE-SPAWN placeholder: the canonical session name (F18 — a name tmux will not
        # rename). STEP4 overwrites it with the full '<session>:<window>.<pane>' triple tmux
        # reports once the pane actually opens.
        "tmux_target": addressing.session_name_for(child_address),
        "state": "planned",
        "generation": generation,
        "lease_epoch": lease_epoch,
        "owner_token": owner_token,
        "last_applied_seq": 0,
        "liveness_state": "claimed",
        "terminal_signal": None,
        "terminal_signal_at": None,
        "gate_crossed_at": None,
        "paused_at": None,
        "workspace": str(node_dir),
        # DERIVATION (FORK-BRIEF-DERIVATION): the brief + frozen acceptance are the node's OWN files,
        # pre-authored by the parent at plan time (pointer-not-payload, WORKSPACE-SCHEMA:221). The spawn
        # derives these pointers from the node — it does not carry the spec/acceptance as payload.
        "spec_pointer": str(node_dir / "brief.md"),
        "frozen_acceptance_ref": str(node_dir / "acceptance.md"),
    }
    # Merge into the live whole map (preserve siblings) and write under a BRIEFLY-held EX lock —
    # released on exit, before claim_and_spawn re-takes it per-mutation (no re-entrant fcntl deadlock).
    # This mirrors genesis._register_l1_root's lock-held seed exactly, with parent_address SET.
    lock_path = Path(runtime_root) / executor.LOCK_FILENAME
    with store.file_lock(lock_path, shared=False):
        live_map = dict(ledger.all_nodes())
        live_map[child_address] = binding
        ledger.write_binding(live_map, _lock_held=True)
    return binding


def _write_child_brief(
    child_address: str,
    child_level_config,
    registered_binding: dict,
    brief_content: Optional[str],
) -> None:
    """Write the child BRIEF.md (the assembled load-manifest + the parent brief_content) into the node.

    The brief lands SOMEWHERE the child reads it in place (DAEMON §6.1 STEP2 + the increment). v1
    assembles the runtime-neutral load-manifest (brief.assemble_neutral — the role-as-documents PATHS
    the child reads) and writes it ALONGSIDE the parent brief_content (the child's actual task) into
    ``<node-dir>/BRIEF.md`` (FORK-BRIEF-LANDING). The brief_content is ALSO recorded onto the child
    binding (a ``brief_content`` field) so the task is recoverable from the binding slice too. A
    skipped brief would leave the child node with no task / no manifest (the mutant the (b) test kills).
    """
    work_node = _work_node_for(child_address, registered_binding)
    neutral = brief.assemble_neutral(child_address, child_level_config, work_node)

    node_dir = _child_node_dir(child_address)
    node_dir.mkdir(parents=True, exist_ok=True)
    brief_path = node_dir / "brief.md"  # canonical lowercase (WORKSPACE-SCHEMA:221)

    manifest_header = [
        f"# brief — {child_address}",
        "",
        f"- node_address: {child_address}",
        f"- parent_address: {registered_binding.get('parent_address')}",
        f"- level: {neutral.level}",
        f"- role_variant: {neutral.role_variant}",
        f"- system_prompt_file: {neutral.system_prompt_file}",
        "",
        "## Identity — Load These Documents (read in place)",
        "",
        *[f"- {path}" for path in neutral.load_manifest],
        "",
        # F19 — the sign-off pointer, visible in the first thing the child reads (belt-and-braces
        # alongside the .sign-off.<seat>.json handshake itself + comms-protocol's Terminal Signal).
        "## Sign-off",
        "",
        f"- handshake (your owner_token + signal path): {addressing.signoff_path(child_address, ledger.RUNTIME_ROOT)}",
        f"- terminal signal artifact: {addressing.signal_path(child_address, ledger.RUNTIME_ROOT)}",
        "- your final act: write the signal file (atomic tmp+rename) with the owner_token copied "
        "verbatim from the sign-off file; a stale/wrong token is silently ignored.",
        "",
    ]

    # THREE cases (FORK-BRIEF-DERIVATION):
    #   (1) OVERRIDE — a brief_content was supplied: write brief.md = manifest + the inlined task (the
    #       exception path, e.g. a throwaway task the parent didn't pre-author a node file for).
    #   (2) PRE-AUTHORED DEFAULT — no override AND brief.md already exists: the parent authored the
    #       pointer-not-payload brief into the node at plan time. Do NOT overwrite it; the spawn only
    #       brings the prepared node online (spec_pointer already points at it).
    #   (3) STUB — no override AND no brief.md: write a manifest-only stub so the node is never empty
    #       (an L4 that forgot to pre-author still gets its load-manifest and can escalate the gap).
    wrote = True
    if brief_content is not None:
        lines = manifest_header + ["## Task", "", brief_content, ""]
        store.atomic_replace(brief_path, lambda h: (h.write("\n".join(lines)), h.write("\n")))
    elif not brief_path.exists():
        lines = manifest_header + ["## Task", "",
                                   "(no brief pre-authored and no override supplied — escalate the gap "
                                   "to your parent rather than guessing the task)", ""]
        store.atomic_replace(brief_path, lambda h: (h.write("\n".join(lines)), h.write("\n")))
    else:
        wrote = False  # pre-authored brief.md left intact — the derivation default

    # Record the deliverable_state=briefed onto the child binding (own-slice write through the single
    # writer; the child is still ``planned`` + unclaimed, so we fence on the registered owner_token).
    # The brief is present by whichever path; the spec_pointer already names brief.md on the binding.
    summary = (f"child brief written into the node ({brief_path})" if wrote
               else f"child brief pre-authored; left intact ({brief_path})")
    executor.deliver(
        child_address,
        deliverable_state="briefed",
        expected_owner_token=registered_binding.get("owner_token"),
        event="brief_written",
        summary=summary,
    )


def register_and_spawn_child(
    parent_address: str,
    child_address: str,
    *,
    child_level_config,
    brief_content: Optional[str] = None,
    expected_parent_owner_token: Optional[str] = None,
) -> SpawnResult:
    """THE parent-spawns-child path: register the child under the parent, brief it, then claim+spawn.

    (1) PRECONDITION — the parent binding exists AND is LIVE (non-terminal). A dead/absent parent is
        REFUSED HERE, BEFORE any child register (no half-registered orphan slot a reconcile sweep
        could adopt). Returns a not-ok SpawnResult; NO child binding, NO actor.
    (2) REGISTER — the child as a fresh planned slot UNDER the parent (parent_address SET; mirror
        genesis._register_l1_root). Safe if the child already exists (does not clobber a live child).
    (3) BRIEF — assemble the load-manifest + write the parent brief_content into the child node.
    (4) SPAWN — the EXISTING chokepoint.claim_and_spawn(child, expected_state=planned, …): the F-024
        claim-before-spawn (a lost claim opens NO actor; a post-claim failure releases the claim).

    The adapter is the module-level injected port (set_adapter / ADAPTER) — register_and_spawn_child
    spawns THROUGH the same real chokepoint, so the child actor open rides the SAME adapter seam.
    """
    runtime_root = ledger.RUNTIME_ROOT
    if runtime_root is None:
        raise RuntimeError(
            "register_and_spawn_child requires ledger.RUNTIME_ROOT bound (the child register + brief "
            "land under the runtime tree; bind it like the executor/ledger path-injection contract)"
        )

    # STEP 1 — PRECONDITION: only a LIVE (existing + non-terminal) parent spawns a child. Decided
    # BEFORE the register so a refused spawn leaves NO half-registered child slot (test (c)/(e)).
    parent_binding = ledger.read_binding(parent_address)
    if not _parent_is_live(parent_binding):
        return _result_failed("dead_parent", tmux_target=child_address)

    # STEP 1a — PARENT FENCE (supervision-tree integrity, FORK-PARENT-TOKEN): when the caller presents
    # an ``expected_parent_owner_token``, it must equal the parent's live owner_token — i.e. the caller
    # must OWN the parent it is spawning under, so an agent can only spawn children under ITS OWN node,
    # not a sibling/cousin subtree. Optional (None) mirrors the deliver()/own-slice pattern: a
    # daemon-internal/genesis-style spawn presents no token (the EX lock + local IPC are the bound). A
    # mismatched token is refused BEFORE the register (no half-registered child).
    if (expected_parent_owner_token is not None
            and parent_binding.get("owner_token") != expected_parent_owner_token):
        return _result_failed("parent_fence", tmux_target=child_address)

    # STEP 2 — REGISTER the child as a fresh planned slot UNDER the parent (parent_address SET). Safe
    # if the child already exists live (returns it so the planned-expected claim below loses — single
    # owner, no double-register of a running child).
    registered = _register_child(child_address, parent_address, child_level_config, runtime_root)
    if registered is None:  # defensive — _register_child always returns a binding
        return _result_failed("register_failed", tmux_target=child_address)

    # STEP 3 — WRITE THE BRIEF (the assembled load-manifest + the parent brief_content) into the child
    # node. Skipped only when the child was NOT freshly registered as planned (an already-live child we
    # did not re-register — the claim below will lose, so there is no fresh brief to write).
    if registered.get("state") == "planned":
        _write_child_brief(child_address, child_level_config, registered, brief_content)

    # STEP 4 — SPAWN via the EXISTING claim-before-spawn (F-024). The child claim's CAS precondition is
    # the CHILD's registered (planned, gen0, minted-token) slot — NOT the parent's token. A lost claim
    # (a racer, or an already-running child this register did not clobber) opens NO actor; a post-claim
    # failure releases the claim, exactly as today.
    fresh = ledger.read_binding(child_address) or registered
    return claim_and_spawn(
        child_address,
        expected_state="planned",
        expected_generation=registered["generation"],
        expected_owner_token=fresh.get("owner_token"),
        level_config=child_level_config,
    )


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
    # STEP 0 (INT-2) — the SAME pause-subtree read-point claim_and_spawn runs: §6.4 resume is
    # "re-adopt the address through claim (§6.1)", a spawn VARIANT, so the §6.1 STEP-0 gate applies
    # here too. Without it a paused node could be re-claimed (epoch bump, token re-mint —
    # invalidating the incarnation the human paused to inspect), re-spawned, and kicked off via the
    # genesis RESUME leg — exactly the 'flag no one honors' failure mode (DAEMON L1225-1230).
    if subtree_paused(node_address):
        return _result_failed("paused_subtree", tmux_target=node_address)

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

    # LT-4/INT-1 — tear down the PRIOR incarnation's still-live pane BEFORE reopening: the genesis
    # RESUME branch's own reachability is a uuid-MISMATCHED leftover pane holding the deterministic
    # session name, which would collide create_detached ('duplicate session'). The claim above has
    # already fenced the prior incarnation (epoch bump), so its recorded target is safe to kill.
    kill_stale_pane(live.get("tmux_target"))

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

# The §3.6 NORMATIVE run-ledger event per terminal signal (SML-01) — sourced from states.TERMINAL_VOCAB
# so the spelling cannot drift (collapse_done/collapse_failed were non-normative names the sign-off
# check cannot key on). Two non-vocab aliases remain: DIED (the ipc kill verb's generic death) maps to
# the died_infrastructure event; DEAD (operator force-kill to `dead`) has NO §3.6 row — it keeps the
# legacy collapse_dead name (open question surfaced to the orchestrator: collapse_dead vs `necroed`).
_COLLAPSE_EVENTS: dict[str, str] = {
    states.TERMINAL_VOCAB["signal_DONE"].terminal_signal: states.TERMINAL_VOCAB["signal_DONE"].event,
    states.TERMINAL_VOCAB["signal_FAILED"].terminal_signal: states.TERMINAL_VOCAB["signal_FAILED"].event,
    states.TERMINAL_VOCAB["died_infrastructure"].terminal_signal: states.TERMINAL_VOCAB["died_infrastructure"].event,
    states.TERMINAL_VOCAB["died_methodology"].terminal_signal: states.TERMINAL_VOCAB["died_methodology"].event,
    "DIED": states.TERMINAL_VOCAB["died_infrastructure"].event,  # alias: generic death -> infra class
    "DEAD": "collapse_dead",  # operator force-kill: no §3.6 row (see comment above)
}


def escalate(node_address: str, *, expected_owner_token: Optional[str]):
    """The §3.6 ESCALATED slot-hold journal (SML-02): stamp ``terminal_signal=ESCALATED`` +
    ``terminal_signal_at`` and journal the ``signal_ESCALATED`` run-ledger row as a FENCED,
    exactly-once, generation-bumping (replayable, §4.4) running→running transition through the
    single-writer executor. The lifecycle state STAYS ``running`` and the slot is HELD — the delta
    deliberately carries NO ``in_flight_release`` (the asymmetric row: the node keeps its context
    and waits for the answer round-trip).

    Returns:
      * ``None``                      — nothing to do: the node is absent, or already stamped
                                        ESCALATED (exactly-once per artifact; a re-poll is a no-op);
      * ``TransitionResult(ok=False)``— a refused/aborted write: a non-running node (the slot-hold
                                        applies only to ``running``, §3.6), a CAS miss, or the
                                        fencing abort (the executor journals ``stale_return_ignored``
                                        and leaves the live binding unchanged);
      * ``TransitionResult(ok=True)`` — the slot-hold committed (the durable journal row landed).

    Callers ROUTE the result (the no-result-swallowing convention): the watchdog reports a failed
    journal write as ``escalate_journal_failed`` and retries next tick (the .signal artifact persists).
    """
    live = ledger.read_binding(node_address)
    if live is None:
        return None
    if live.get("terminal_signal") == "ESCALATED":
        # Already journaled — exactly-once per artifact. The idempotency keys on the binding
        # stamp, and F16's answer verb deliberately does NOT clear it: the answer RIDES
        # terminal_signal=ESCALATED + terminal_note (TRANSPORTS §5.3 — the parent reads both),
        # and clearing the stamp while the .signal artifact persists would let the next watchdog
        # tick re-journal the SAME escalation as a fresh signal_ESCALATED row. Clearing belongs
        # to the round-trip COMPLETION (the parent's decision-down flow), not the answer post.
        return None
    if live.get("state") != "running":
        return executor.TransitionResult(
            ok=False,
            errors=[
                f"ESCALATED slot-hold applies only to a running node (§3.6); "
                f"{node_address!r} is {live.get('state')!r}"
            ],
            warnings=[],
            binding=live,
        )
    from harnessd import clock  # local import, matching reconcile._now's style
    return executor.transition(
        node_address,
        expected_state="running",
        expected_generation=live["generation"],
        expected_owner_token=expected_owner_token,
        target_state="running",  # the §3.6 ASYMMETRIC row: signal set, state UNCHANGED
        binding_delta={
            "terminal_signal": "ESCALATED",
            "terminal_signal_at": clock.now_utc(),
        },
        event=states.TERMINAL_VOCAB["signal_ESCALATED"].event,
        summary=(
            "ESCALATED slot-hold: terminal_signal stamped, state stays running, slot HELD "
            "(no in_flight release; §3.6 asymmetric)"
        ),
    )


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
    #
    # RETURN the TransitionResult (review chokepoint-2): a FAILED terminal transition (a CAS miss /
    # fencing rejection) must NOT be reported as success. Callers (the watchdog, the kill IPC) route the
    # result; a `return None` here silently swallowed a fenced abort and told every caller it collapsed.
    return executor.transition(
        node_address,
        expected_state=live["state"],
        expected_generation=live["generation"],
        expected_owner_token=expected_owner_token,
        target_state=target_state,
        binding_delta={
            "terminal_signal": terminal_signal,
            "in_flight_release": True,
        },
        event=_COLLAPSE_EVENTS[terminal_signal],  # the §3.6 normative event name (SML-01)
        summary=(
            f"terminal collapse: {terminal_signal} -> {target_state} "
            "(carries ④ in_flight RELEASE-DECREMENT, symmetric to STEP1 claim-increment; §6.1/§3.6)"
        ),
    )
