"""ipc — the daemon-side IPC request handler: the ONLY writer path for a CLI-originated mutation.

Authoritative sources:
  - IMPLEMENTATION-PLAN §3 module table (harnessctl.py row, L65): "CLI client — NOT a writer. Sends
    requests to the resident daemon over a local socket/FIFO; the daemon performs the mutation inside
    the one lock. Read-only commands (show/next/validate/reconcile-inspect) may take the shared lock
    directly."
  - IMPLEMENTATION-PLAN §2.x / Increment-13 Done-test (L800-803): node-addressed subcommands
    (spawn/transition/show/reconcile-inspect/kill) over a local socket/FIFO to the daemon; a mutation
    via harnessctl is performed BY THE DAEMON inside the one lock (not by the CLI process); a read
    command returns ledger state.
  - DAEMON §4.3 (Lock discipline — one serialization domain): "CLIs are clients, not writers." The
    daemon performs the mutation inside the one EX lock. §4.5: read-only (shared lock) =
    show/next/validate/reconcile-inspect; mutating (exclusive lock) = transition / claim / collapse-kill.

THE WRITER SIDE. harnessctl (the CLIENT) NEVER mutates: it serializes a request and ships it over the
local socket. This module is the daemon-resident handler that RECEIVES that request and performs the
mutation THROUGH THE EXECUTOR inside ``store.file_lock(EX)`` (the single writer). Every mutation funnels
through ``harnessd.executor`` / ``harnessd.spawn.chokepoint`` — this module never read-modify-replaces
the binding ledger directly. Reads return ledger state (``ledger.read_binding`` / ``ledger.all_nodes`` /
``ledger.next_seq`` / ``reconcile`` for inspect).

BUILDER DECISIONS (the §2.x details the frozen tests leave open — stated in the build report):

  * REQUEST / RESPONSE SCHEMA (FORK-IPC-SCHEMA). A request is a JSON object:
    ``{"command": <name>, "addr": <node-address>, ...command-specific fields}``. A response is a JSON
    object ``{"ok": <bool>, "command": <name>, ...}`` carrying, per command:
      - transition/kill: ``ok``, ``errors`` (the executor's SPECIFIC abort reason — a CAS miss /
        fencing rejection / illegal edge / no-such-node; empty on success), ``warnings``, ``binding``
        (post-state). ``kill`` additionally echoes ``terminal_signal``.
      - promote:         ``ok``, ``addr``, ``delivered``, ``deliverable_state``,
        ``delivery_destination``, ``errors`` — EVERY PromoteResult field routed into the response
        (no result-swallowing). The gate opens ONLY on an explicit ``decision == 'accept'`` field.
      - show:            ``ok``, ``addr``, ``binding`` (the node's ledger slice, or ``null`` if absent).
      - next/next-seq:   ``ok``, ``next_seq``.
      - validate:        ``ok``, ``errors``, ``warnings`` (the whole-ledger admission scan).
      - reconcile-inspect: ``ok``, ``adopted``/``necroed``/``escalations`` (a DRY read-only sweep).
    ``ok`` is ``False`` on any abort (a CAS miss, an illegal edge, a fencing rejection, an unknown
    command); the client prints the response + sets a nonzero exit code on ``ok is False``.

  * THE BOUNDED SINGLE-ACCEPT PRIMITIVE (``serve_one``). ``serve_one(listener)`` accepts EXACTLY ONE
    connection, reads the framed request, runs ``handle_request`` (the lock-held mutator/reader), writes
    the JSON response back, and returns. It is the §2.12 ``poll_once`` analogue for the IPC loop: a
    single drivable accept/handle so a test (and the production serve loop) drive it one step at a time.
    There is NO unbounded serve-forever loop in this module's test path — ``serve_forever`` exists for
    production but is NEVER exercised by a test (it simply loops ``serve_one``).

  * RECONCILE-INSPECT IS READ-ONLY (FORK-INSPECT-DRY). The §4.5 ``reconcile-inspect`` read returns the
    divergence verdict WITHOUT mutating: it replays the WAL into an in-memory map and classifies it,
    but does NOT persist or drive the executor. It reports what a reconcile WOULD do (a dry inspect),
    consistent with "read-only commands may take the shared lock directly" (a real reconcile_tick is the
    daemon's poll loop, not a CLI-triggered write).
"""

from __future__ import annotations

import json
import socket
from typing import Optional

from . import addressing, clock, config, detector_signals, ledger, store, validate
from . import executor as _executor
from . import promote as _promote
from . import reconcile as _reconcile
from .spawn import chokepoint
from .spawn import outbox as _outbox


# ---------------------------------------------------------------------------
# The framed request/response transport (mirrors the WAL's <len>\t framing spirit, but the IPC
# transport is a single connection: we read to EOF, write the whole response, and the peer reads to
# EOF). The test harness sends the request then shuts down its write half; the bounded server reads to
# EOF, handles, and writes the response back on the same connection.
# ---------------------------------------------------------------------------


def _recv_all(conn: socket.socket) -> bytes:
    """Read a whole request from ``conn`` until the peer closes its write half (EOF-framed)."""
    chunks: list[bytes] = []
    while True:
        data = conn.recv(65536)
        if not data:
            break
        chunks.append(data)
    return b"".join(chunks)


# ---------------------------------------------------------------------------
# handle_request — the request->response dispatcher. The ONLY writer path for a CLI-originated
# mutation: every mutating command routes through the executor / chokepoint (the single writer) inside
# the one EX lock; every read returns ledger state.
# ---------------------------------------------------------------------------


def handle_request(request: dict) -> dict:
    """Dispatch one CLI request to its handler and return a JSON-serializable response dict.

    Mutations (transition / kill / spawn) route THROUGH THE EXECUTOR / CHOKEPOINT (the single writer)
    inside ``store.file_lock(EX)``; this handler never read-modify-replaces the binding ledger itself.
    Reads (show / next / validate / reconcile-inspect) return ledger state.

    A request is ``{"command": <name>, "addr": <addr>, ...}``. An unknown / missing command is a
    structured abort (``ok=False``) — never a silent no-op (the client surfaces it as a nonzero exit).
    """
    if not isinstance(request, dict):
        return {"ok": False, "errors": ["malformed request: expected a JSON object"]}

    command = request.get("command")
    handler = _DISPATCH.get(command)
    if handler is None:
        return {
            "ok": False,
            "command": command,
            "errors": [
                f"unknown command {command!r}: the daemon IPC routes "
                f"{sorted(_DISPATCH)} (Increment-13 node-addressed surface)"
            ],
        }
    return handler(request)


# ---------------------------------------------------------------------------
# Mutating handlers — every one routes through the executor / chokepoint (the single writer).
# ---------------------------------------------------------------------------


def _handle_transition(request: dict) -> dict:
    """A lifecycle transition — routed THROUGH THE EXECUTOR (the single writer) inside the EX lock.

    Carries the CAS preconditions (expected_state / expected_generation / expected_owner_token) the
    client serialized. The executor checks them all BEFORE any write (§4.2) and commits intent-first.
    """
    addr = request.get("addr")
    result = _executor.transition(
        addr,
        expected_state=request.get("expected_state"),
        expected_generation=request.get("expected_generation"),
        expected_owner_token=request.get("expected_owner_token"),
        target_state=request.get("target_state"),
        binding_delta=request.get("binding_delta") or {},
        event=request.get("event", "transition"),
        summary=request.get("summary", "harnessctl transition"),
    )
    return _transition_response("transition", addr, result)


def _handle_kill(request: dict) -> dict:
    """A terminal collapse (kill <addr>) — routed THROUGH chokepoint.collapse -> the REAL executor.

    ``kill`` collapses the node to a terminal state (DONE->done, FAILED/DIED*->failed, DEAD->dead).
    chokepoint.collapse is NOT a writer itself: it routes through ``executor.transition`` (the single
    writer) inside the one EX lock. The default signal is FAILED (an operator kill is a failure-class
    teardown, not a clean DONE).

    The TransitionResult is ROUTED into the response (F2r ipc-2, mirroring watchdog.check_leaf's F2b
    routing): an abort surfaces the executor's SPECIFIC structured reason (a CAS miss / fencing
    rejection / illegal edge) in ``errors``, and collapse-returns-None (no binding for the address)
    is an explicit "no such node" abort. The old post-read heuristic (state in the terminal set ->
    ok) phantom-reported success when killing an ALREADY-terminal node even though the transition
    aborted on the illegal edge — no result-swallowing.
    """
    addr = request.get("addr")
    terminal_signal = request.get("terminal_signal", "FAILED")
    expected_owner_token = request.get("expected_owner_token")
    try:
        result = chokepoint.collapse(
            addr,
            terminal_signal,
            expected_owner_token=expected_owner_token,
        )
    except ValueError as exc:
        # collapse REFUSES an asymmetric/unknown signal (e.g. ESCALATED) — surface it, do not crash.
        return {"ok": False, "command": "kill", "addr": addr, "errors": [str(exc)], "binding": None}
    if result is None:
        # collapse found NO binding for the address (nothing to collapse) — name the absence.
        return {
            "ok": False,
            "command": "kill",
            "addr": addr,
            "terminal_signal": terminal_signal,
            "binding": None,
            "errors": [f"kill: no such node {addr!r} — nothing to collapse"],
        }
    response = _transition_response("kill", addr, result)
    response["terminal_signal"] = terminal_signal
    return response


def _handle_spawn(request: dict) -> dict:
    """A spawn (spawn <addr>) — routed THROUGH the chokepoint (the single writer), inside the one lock.

    TWO routes (the ``parent`` field is the discriminator):
      * --parent given -> the PARENT-SPAWNS-CHILD route: ``chokepoint.register_and_spawn_child``
        registers the child UNDER the parent (parent_address SET), writes the brief into the child
        node, then claim-before-spawns it (F-024). The CLI is NOT a writer — the DAEMON performs the
        whole register+brief+spawn here inside the one lock.
      * no --parent -> the EXISTING claim-only spawn of an already-planned node
        (``chokepoint.claim_and_spawn``): STEP1 CAS-claim, STEP3 actor open via the installed adapter.

    The chokepoint's claim is a REAL ``executor.claim`` transition under the one EX lock (the single
    writer); the actor opens through the installed adapter (a dry-run FakeAdapter in tests, the real
    RuntimeAdapter in production). The level config is resolved from the request's ``level`` (defaulting
    to the node's recorded level, else L3).
    """
    addr = request.get("addr")
    live = ledger.read_binding(addr)
    level = request.get("level") or (live.get("level") if live else None) or "L3"
    level_config = config.get_level_config(level)

    parent = request.get("parent") or request.get("parent_address")
    if parent:
        # PARENT-SPAWNS-CHILD: the daemon registers the child under the parent + briefs it + spawns it,
        # all inside the one lock (the CLI shipped only the parent address + the brief_content text).
        result = chokepoint.register_and_spawn_child(
            parent,
            addr,
            child_level_config=level_config,
            brief_content=request.get("brief_content"),
            expected_parent_owner_token=request.get("expected_owner_token"),
        )
    else:
        expected_state = request.get("expected_state")
        expected_generation = request.get("expected_generation")
        if expected_state is None and live is not None:
            expected_state = live.get("state")
        if expected_generation is None and live is not None:
            expected_generation = live.get("generation")
        result = chokepoint.claim_and_spawn(
            addr,
            expected_state=expected_state,
            expected_generation=expected_generation,
            expected_owner_token=request.get("expected_owner_token"),
            level_config=level_config,
        )
    binding = ledger.read_binding(addr)
    ok = bool(getattr(result, "ok", False))
    return {
        "ok": ok,
        "command": "spawn",
        "addr": addr,
        "parent": parent,
        "session_uuid": getattr(result, "session_uuid", None),
        "model_used": getattr(result, "model_used", None),
        "failure_class": getattr(result, "failure_class", None),
        "binding": binding,
        "errors": [] if ok else [f"spawn failed for {addr!r}: {getattr(result, 'failure_class', None)}"],
    }


def _handle_service_outbox(request: dict) -> dict:
    """Service a node's spawn-request OUTBOX (FORK-SPAWN-CHANNEL) — routed through the chokepoint.

    The agent dropped spawn-requests into its own jail-writable workroot; this drains them. The daemon
    (NOT the agent) composes each child address from the parent's own address and spawns under the
    parent's live owner_token (the parent-fence). With ``addr`` -> service that one node's outbox; with
    no ``addr`` -> service EVERY live non-leaf node (the daemon-loop sweep). Each spawn is a REAL
    register_and_spawn_child through the single writer.
    """
    addr = request.get("addr")
    outcomes = _outbox.service_outbox(addr) if addr else _outbox.service_all_outboxes()
    serviced = [
        {"request": o.request_path, "status": o.status,
         "child_address": o.child_address, "reason": o.reason}
        for o in outcomes
    ]
    spawned = [o for o in serviced if o["status"] == "spawned"]
    return {
        "ok": True,
        "command": "service-outbox",
        "addr": addr,
        "serviced": serviced,
        "spawned_count": len(spawned),
        "rejected_count": len(serviced) - len(spawned),
    }


def _handle_promote(request: dict) -> dict:
    """The F8 delivery-terminus caller (CRIT-3) — routed THROUGH promote() -> executor.deliver.

    L1's Stage-5 final-accept (INTAKE-TO-DELIVERY Stage 5→6) arrives as a FLAT explicit
    ``decision`` request field (the ipc style — the _handle_transition precedent); the handler
    synthesizes the node-bound accept signal ITSELF, binding ``node_address=addr`` by
    construction, so a synthesized signal cannot cross-promote another node. An OMITTED decision
    ships ``accept_signal=None`` so promote's gate HOLDS — never default-accept (a bare request
    must never speculatively cross the jail boundary). promote() performs the cross-jail
    copy/push and stamps the binding via ``executor.deliver`` (the single writer, locks
    internally — the _handle_transition pattern, no extra lock wrapper here). EVERY PromoteResult
    field is routed into the response — the no-result-swallowing rule.
    """
    addr = request.get("addr")
    decision = request.get("decision")
    accept_signal = None if decision is None else {
        "decision": decision,
        "level": "L1",
        "node_address": addr,
        "acceptance_ref": request.get("acceptance_ref"),
        "note": request.get("note"),
    }
    result = _promote.promote(addr, accept_signal=accept_signal)
    return {
        "ok": bool(result.ok),
        "command": "promote",
        "addr": addr,
        "delivered": result.delivered,
        "deliverable_state": result.deliverable_state,
        "delivery_destination": result.delivery_destination,
        "errors": list(result.errors),
    }


def _handle_pause(request: dict) -> dict:
    """The F16 pause WRITE verb — routed THROUGH executor.pause (the single writer).

    Sets ``paused_at`` on the addressed node, flagging the whole SUBTREE (node-or-ancestor walk)
    for the two enforcing read-points: chokepoint STEP0 (no new children) and the watchdog's
    §3.4 STEP 0 gate (no recovery actions). NOT a kill — the in-flight agent keeps running. The
    TransitionResult is ROUTED into the response (no result-swallowing).
    """
    addr = request.get("addr")
    result = _executor.pause(addr, expected_owner_token=request.get("expected_owner_token"))
    return _transition_response("pause", addr, result)


def _handle_resume(request: dict) -> dict:
    """The F16 resume WRITE verb — clear ``paused_at`` through executor.resume (the single writer)."""
    addr = request.get("addr")
    result = _executor.resume(addr, expected_owner_token=request.get("expected_owner_token"))
    return _transition_response("resume", addr, result)


def _handle_answer(request: dict) -> dict:
    """The F16 answer-injection verb (TRANSPORTS §5.3 primitive 3) — stamp, then wake the parent.

    (1) Fail-loud guards: content required; the node must exist; the node must actually be
        ESCALATED — read the binding stamp first, falling back to the durable fenced .signal
        artifact (the same fenced reader the watchdog uses) for the agent-signed-but-not-yet-
        journaled tick gap. Mirrors the _handle_kill fail-loud precedent.
    (2) Stamp ``terminal_note`` through executor.post_answer (the single writer). The ESCALATED
        stamp stays IN PLACE — the answer RIDES terminal_signal=ESCALATED + terminal_note.
    (3) The human->parent wake hop: append ONE pointer line to the PARENT's .inbox.<seat>.jsonl
        (the §3 multi-writer append log harnessd TAILS — not the single-writer ledger), which the
        existing ``inbox_has_unacked`` edge-trigger reads. The human sits ABOVE the parent, so a
        parentless L1 is woken ITSELF (the human IS L1's parent). An append failure is surfaced
        (the stamp is already durable) — never swallowed.
    """
    addr = request.get("addr")
    content = request.get("answer_content")
    if not content:
        return {
            "ok": False,
            "command": "answer",
            "addr": addr,
            "errors": ["answer requires answer_content (--text/--file)"],
            "binding": None,
        }

    binding = ledger.read_binding(addr)
    if binding is None:
        return {
            "ok": False,
            "command": "answer",
            "addr": addr,
            "errors": [f"no binding for node {addr!r}: nothing to answer"],
            "binding": None,
        }

    # The ESCALATED guard (fail-loud): the binding stamp (chokepoint.escalate's journal), else
    # the durable fenced .signal artifact (covers the agent-signed / watchdog-not-yet-ticked gap).
    escalated = binding.get("terminal_signal") == "ESCALATED"
    if not escalated:
        sig = detector_signals.read_terminal_signal(binding, binding)
        escalated = sig is not None and sig.get("signal") == "ESCALATED"
    if not escalated:
        return {
            "ok": False,
            "command": "answer",
            "addr": addr,
            "errors": [f"node {addr!r} is not ESCALATED — nothing to answer"],
            "binding": binding,
        }

    result = _executor.post_answer(addr, answer=content)
    if not result.ok:
        return _transition_response("answer", addr, result)

    # The human->parent wake hop (stamp-then-wake, TRANSPORTS §5.3): the next-up node, or the
    # node ITSELF for a parentless L1 root.
    wake_target = binding.get("parent_address") or addr
    inbox = addressing.inbox_path(wake_target, ledger.RUNTIME_ROOT)
    line = {
        "from": "human",
        "type": "answer_posted",
        "child": addr,
        "message": f"human answer posted for {addr}, execute the decision-down",
        "ts": clock.now_utc(),
    }
    try:
        inbox.parent.mkdir(parents=True, exist_ok=True)
        with inbox.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(line) + "\n")
    except OSError as exc:
        return {
            "ok": False,
            "command": "answer",
            "addr": addr,
            "errors": [f"answer stamped (durable) but the parent wake append failed: {exc}"],
            "warnings": [],
            "binding": result.binding,
            "wake_target": wake_target,
        }

    response = _transition_response("answer", addr, result)
    response["wake_target"] = wake_target
    return response


def _transition_response(command: str, addr, result) -> dict:
    """Shape a TransitionResult into the JSON response (ok / errors / warnings / binding)."""
    return {
        "ok": bool(result.ok),
        "command": command,
        "addr": addr,
        "errors": list(result.errors),
        "warnings": list(result.warnings),
        "binding": result.binding,
    }


# ---------------------------------------------------------------------------
# Read handlers — return ledger state (§4.5 read-only surface). These read through the ledger's keyed
# map; they take the shared lock implicitly via the read path (no whole-map replace).
# ---------------------------------------------------------------------------


def _handle_show(request: dict) -> dict:
    """Return the REAL ledger state for the addressed node (or ``null`` if absent) — a §4.5 read."""
    addr = request.get("addr")
    binding = ledger.read_binding(addr)
    return {"ok": True, "command": "show", "addr": addr, "binding": binding}


def _handle_tree(request: dict) -> dict:
    """Return the WHOLE binding map — the operator fleet/tree read (§4.5 read-only; review COMP-4). The
    CLI renders it as an indented supervision tree for situational awareness during a run."""
    return {"ok": True, "command": "tree", "nodes": ledger.all_nodes()}


def _handle_next_seq(request: dict) -> dict:
    """Return the next monotonic WAL ``seq`` (read-only — derived from the WAL on load, §4.5)."""
    return {"ok": True, "command": "next-seq", "next_seq": ledger.next_seq()}


def _handle_validate(request: dict) -> dict:
    """A whole-ledger admission scan (read-only): validate every live binding against the WAL tail.

    PURE: ``validate.validate`` writes nothing (§4.2). We scan each node's current binding against the
    committed WAL (no about-to-commit entry to append for a steady read, so we pass the node's own last
    WAL row as the tail anchor when present). Reports aggregate errors/warnings.
    """
    wal = ledger.load_wal()
    nodes = ledger.all_nodes()
    errors: list[str] = []
    warnings: list[str] = []
    for addr, binding in nodes.items():
        tail = [record for record in wal if record.get("node_address") == addr]
        node_errors, node_warnings = validate.validate(binding, tail or wal)
        errors.extend(f"{addr}: {message}" for message in node_errors)
        warnings.extend(f"{addr}: {message}" for message in node_warnings)
    return {"ok": not errors, "command": "validate", "errors": errors, "warnings": warnings}


def _handle_reconcile_inspect(request: dict) -> dict:
    """A DRY reconcile inspect (read-only, FORK-INSPECT-DRY): what a reconcile WOULD do, no write.

    Replays the WAL into an in-memory map and classifies divergence WITHOUT persisting or driving the
    executor — a read-only divergence verdict (§4.5: read-only commands may take the shared lock
    directly). The real reconcile sweep is the daemon's poll loop, not a CLI-triggered mutation.
    """
    bindings = ledger.all_nodes()
    wal = ledger.load_wal()
    replayed = _reconcile.replay_wal(bindings, wal)
    diverged = [
        addr
        for addr, replayed_binding in replayed.items()
        if bindings.get(addr) != replayed_binding
    ]
    return {
        "ok": True,
        "command": "reconcile-inspect",
        "nodes": sorted(replayed),
        "would_replay": sorted(diverged),
    }


_DISPATCH = {
    # Mutating (exclusive lock, routed through the single writer — §4.5).
    "transition": _handle_transition,
    "kill": _handle_kill,
    "spawn": _handle_spawn,
    "service-outbox": _handle_service_outbox,
    "promote": _handle_promote,
    "pause": _handle_pause,
    "resume": _handle_resume,
    "answer": _handle_answer,
    # Read-only (shared lock — §4.5).
    "show": _handle_show,
    "tree": _handle_tree,
    "next": _handle_next_seq,
    "next-seq": _handle_next_seq,
    "validate": _handle_validate,
    "reconcile-inspect": _handle_reconcile_inspect,
}


# ---------------------------------------------------------------------------
# serve_one — the BOUNDED single-accept primitive (the §2.12 poll_once analogue for IPC). A test drives
# exactly ONE accept/handle; production loops it in serve_forever. NEVER an unbounded loop in a test path.
# ---------------------------------------------------------------------------


def serve_one(listener: socket.socket, *, handler=handle_request) -> Optional[dict]:
    """Accept EXACTLY ONE connection on ``listener``, handle the framed request, write the response.

    The single drivable IPC step (mirrors ``daemon.poll_once``): accept one connection, read the
    request to EOF, run ``handler`` (the lock-held mutator/reader through the executor), write the JSON
    response back, close the connection, and RETURN the request handled (or None on a clean
    accept-then-EOF with no payload). There is NO loop here — this is the bounded unit the unbounded
    ``serve_forever`` composes, and the unit a test drives one step at a time.

    Takes the ``listener`` it accepts on as an explicit argument (no implicit global serve-forever): the
    caller owns the socket's lifecycle (bind / listen / close).
    """
    conn, _addr = listener.accept()
    with conn:
        raw = _recv_all(conn)
        request = json.loads(raw.decode("utf-8")) if raw.strip() else {}
        response = handler(request)
        conn.sendall(json.dumps(response).encode("utf-8"))
    return request


def serve_forever(listener: socket.socket, *, handler=handle_request) -> None:  # pragma: no cover
    """The production resident IPC loop — loops ``serve_one`` forever. NEVER driven in a test path.

    The daemon assembles + binds the listener at boot and runs this in its serve thread. It is the
    unbounded composition of the BOUNDED ``serve_one`` (the single drivable step the tests exercise);
    the unbounded loop itself is never entered by a test (mirrors ``daemon.poll_loop`` vs ``poll_once``).
    """
    while True:
        try:
            serve_one(listener, handler=handler)
        except OSError:
            # The listener was closed (shutdown) — exit the resident loop cleanly.
            return
