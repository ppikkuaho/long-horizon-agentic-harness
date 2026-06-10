"""harnessctl — the OPERATOR CLI. A CLIENT, NEVER a writer.

Authoritative sources:
  - IMPLEMENTATION-PLAN §3 module table (harnessctl.py row, L65): "CLI client — NOT a writer. Sends
    requests to the resident daemon over a local socket/FIFO; the daemon performs the mutation inside
    the one lock. Read-only commands (show/next/validate/reconcile-inspect) may take the shared lock
    directly." GENERALIZE: the recovered ``build_parser`` L1613-1696 subcommand structure -> node-addressed.
  - IMPLEMENTATION-PLAN §2.x / Increment-13 Done-test (L800-803): node-addressed subcommands
    (spawn/transition/show/reconcile-inspect/kill) over a local socket/FIFO to the daemon; a mutation
    via harnessctl is performed BY THE DAEMON inside the one lock (not by the CLI process); a read
    command returns ledger state.
  - DAEMON §4.3: "CLIs are clients, not writers. A harnessctl command sends a request to the resident
    daemon (over a local socket/fifo), and the daemon performs the mutation inside the one lock." §4.5:
    read-only (shared lock) = show / next / validate / reconcile-inspect; mutating (exclusive lock) =
    transition / claim / collapse-kill.

THE CARDINAL RULE (§4.3): this module is a CLIENT. It does arg parsing + socket I/O ONLY. It NEVER
imports or calls the single-writer primitives (the ledger's whole-map writer, the executor's
state-changer, the spawn-chokepoint mutators). Every mutation is serialized into a request dict and
shipped over the local unix socket to the resident daemon, which performs it inside the one EX lock.
The client prints the JSON response to stdout and returns an exit code (0 on ``ok``, nonzero otherwise).

BUILDER DECISIONS (stated in the build report):

  * THE SOCKET PATH (FORK-SOCKET-PATH). The daemon's IPC socket lives at
    ``<RUNTIME_ROOT>/.harnessd/harnessd.sock`` by default (alongside the §2.3 runtime.json / status.json
    under ``.harnessd/``). The client resolves the path in precedence order: an explicit
    ``main(argv, socket_path=...)`` kwarg, then a ``--socket <path>`` flag, then the ``HARNESSD_SOCKET``
    env var, then the RUNTIME_ROOT default. This keeps the wiring detail un-over-constrained (the §2.x
    plan names "a local socket/FIFO", not an exact path).

  * THE PRINT-JSON / EXIT-CODE CONVENTION. The client prints the daemon's response dict as one JSON line
    to stdout and returns ``0`` when ``response["ok"]`` is truthy, else ``2`` (a command-level abort —
    a daemon-reported abort OR a client-side input error such as an unreadable ``--brief``/``--file``
    input file, where the daemon is never contacted). A transport failure (no daemon reachable, or a
    garbled non-JSON response — the daemon did not speak the protocol) returns ``3`` after printing a
    JSON error line — the client cannot perform the mutation itself, so a failed transport is a hard
    failure, never a silent local write and NEVER a traceback.

  * NODE-ADDRESSED SUBCOMMANDS. Every command carries the node address as a positional ``addr`` (the
    GENERALIZE of the recovered ``build_parser`` subcommand structure). The read surface (show / next /
    validate / reconcile-inspect) and the mutation surface (spawn / transition / kill) share the
    node-addressed shape; the request dict is built from the parsed namespace and shipped as-is.
"""

from __future__ import annotations

import argparse
import json
import os
import socket as socket_mod
import sys
from pathlib import Path
from typing import Optional

from . import ledger


# The IPC socket lives under the runtime's ``.harnessd/`` dir (alongside runtime.json / status.json).
SOCKET_FILENAME: str = "harnessd.sock"
SOCKET_ENV_VAR: str = "HARNESSD_SOCKET"


# ---------------------------------------------------------------------------
# build_parser — the node-addressed argparse CLI (GENERALIZE of the recovered build_parser L1613-1696).
# ---------------------------------------------------------------------------


def render_tree(nodes: dict) -> str:
    """Render the binding map as an indented supervision TREE (the operator fleet view, COMP-4).

    Each line: ``<indent><address>  [<level>] <state>/<liveness>``. Children are indented under their
    ``parent_address``; roots (parentless) are the top level. An ORPHAN (parent not in the map) is shown
    at the top level with a marker — never silently dropped (a missing node would hide a real gap). Sorted
    by address for stable output.
    """
    if not nodes:
        return "(no nodes)"
    children: dict = {}
    roots = []
    for addr, b in nodes.items():
        parent = (b or {}).get("parent_address")
        if parent and parent in nodes:
            children.setdefault(parent, []).append(addr)
        else:
            roots.append(addr)  # a true root (parent None) OR an orphan (parent absent from the map)

    lines: list[str] = []

    def _emit(addr: str, depth: int) -> None:
        b = nodes.get(addr) or {}
        level = b.get("level", "?")
        state = b.get("state", "?")
        liveness = b.get("liveness_state", "?")
        parent = b.get("parent_address")
        orphan = bool(parent) and parent not in nodes
        marker = "  ⚠orphan(parent missing)" if orphan else ""
        lines.append(f"{'  ' * depth}{addr}  [{level}] {state}/{liveness}{marker}")
        for child in sorted(children.get(addr, [])):
            _emit(child, depth + 1)

    for root in sorted(roots):
        _emit(root, 0)
    return "\n".join(lines)


def _add_addr(subparser) -> None:
    """Attach the node-address positional shared by every node-addressed subcommand (parse+route)."""
    subparser.add_argument(
        "addr",
        help="the node address (e.g. 'proj/widget#exec') this command targets",
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the node-addressed CLI parser (§3 GENERALIZE of build_parser L1613-1696 -> node-addressed).

    Subcommands (Increment-13 Done-test L800-803 + §4.5 read-only surface):
      reads  (§4.5):  show / next-seq / validate / reconcile-inspect — return ledger state.
      writes (§4.3):  spawn / transition / kill — serialized into a request, performed by the daemon.

    The parser sets ``args.command`` to the subcommand name (the route) and carries the node ``addr``
    positional on every node-addressed command. A ``--socket`` flag overrides the daemon socket path.
    """
    parser = argparse.ArgumentParser(
        prog="harnessctl",
        description=(
            "harnessctl — the operator CLI. A CLIENT, not a writer: mutations are sent to the resident "
            "daemon over a local socket and performed inside the one lock (DAEMON §4.3)."
        ),
    )
    parser.add_argument(
        "--socket",
        dest="socket_path",
        default=None,
        help="path to the daemon IPC socket (default: <RUNTIME_ROOT>/.harnessd/harnessd.sock or $HARNESSD_SOCKET)",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="<command>")
    subparsers.required = True

    # --- Read-only surface (§4.5) ---------------------------------------------------------------
    show = subparsers.add_parser("show", help="print the ledger state for a node (read-only)")
    _add_addr(show)

    subparsers.add_parser(
        "tree", help="print the whole supervision tree (address / level / state / liveness; read-only)"
    )

    next_seq = subparsers.add_parser(
        "next-seq", help="print the next monotonic WAL seq (read-only)"
    )

    validate = subparsers.add_parser(
        "validate", help="run the whole-ledger admission scan (read-only)"
    )

    inspect = subparsers.add_parser(
        "reconcile-inspect", help="dry-inspect what a reconcile would do (read-only)"
    )

    # --- Mutating surface (§4.3 — performed BY THE DAEMON, never the CLI) -----------------------
    spawn = subparsers.add_parser("spawn", help="claim-before-spawn a node (mutation -> daemon)")
    _add_addr(spawn)
    spawn.add_argument("--level", default=None, help="the level config (L1..L5) for the spawn seat")
    spawn.add_argument("--expected-state", dest="expected_state", default=None)
    spawn.add_argument("--expected-generation", dest="expected_generation", type=int, default=None)
    spawn.add_argument("--expected-owner-token", dest="expected_owner_token", default=None)
    # The PARENT-SPAWNS-CHILD route (the supervision-tree spawn). When --parent is given the daemon
    # registers the child under the parent + briefs it + spawns it; without it the daemon falls to the
    # EXISTING claim-only spawn of an already-planned node. The CLI only serializes the parent address.
    spawn.add_argument(
        "--parent", dest="parent", default=None,
        help="the parent node address — routes a parent-spawns-child (register+brief+spawn) via the daemon",
    )
    spawn.add_argument(
        "--brief", dest="brief", default=None,
        help="path to a file whose contents are the child's brief (the child's actual task)",
    )

    transition = subparsers.add_parser(
        "transition", help="transition a node to a target state (mutation -> daemon)"
    )
    _add_addr(transition)
    transition.add_argument("--expected-state", dest="expected_state", default=None)
    transition.add_argument("--expected-generation", dest="expected_generation", type=int, default=None)
    transition.add_argument("--expected-owner-token", dest="expected_owner_token", default=None)
    transition.add_argument("--target-state", dest="target_state", required=True)
    transition.add_argument("--event", dest="event", default="transition")

    kill = subparsers.add_parser(
        "kill", help="collapse a node to a terminal state (mutation -> daemon)"
    )
    _add_addr(kill)
    kill.add_argument("--expected-owner-token", dest="expected_owner_token", default=None)
    kill.add_argument(
        "--terminal-signal", dest="terminal_signal", default="FAILED",
        help="the terminal signal (DONE / FAILED / DIED / DEAD); default FAILED",
    )

    # service-outbox: drain a node's spawn-request OUTBOX (FORK-SPAWN-CHANNEL). The daemon adjudicates
    # each request (compose child address from the parent's address + spawn under the parent's token).
    # With --node -> one node's outbox; without -> EVERY live non-leaf node (the operator/loop sweep).
    svc = subparsers.add_parser(
        "service-outbox", help="drain spawn-request outboxes -> register+brief+spawn children (-> daemon)"
    )
    svc.add_argument(
        "--node", dest="addr", default=None,
        help="service ONLY this node's outbox; omit to service every live non-leaf node",
    )

    # The F16 human-control verbs (TRANSPORTS §5.3) — pure arg-parsing here; the DAEMON performs
    # every mutation through the single-writer executor.
    pause = subparsers.add_parser(
        "pause",
        help=(
            "pause a subtree: set paused_at — a FLAG spawner+watchdog respect, NOT a kill; "
            "the in-flight agent keeps running (mutation -> daemon)"
        ),
    )
    _add_addr(pause)

    resume = subparsers.add_parser(
        "resume",
        help="clear paused_at — re-admit children + recovery (mutation -> daemon)",
    )
    _add_addr(resume)

    answer = subparsers.add_parser(
        "answer",
        help=(
            "post a human answer into an ESCALATED node's terminal_note + wake its parent "
            "(mutation -> daemon)"
        ),
    )
    _add_addr(answer)
    answer_src = answer.add_mutually_exclusive_group(required=True)
    answer_src.add_argument("--text", dest="answer_text", help="the answer text itself")
    answer_src.add_argument(
        "--file", dest="answer_file",
        help="path to a file whose contents are the answer",
    )

    # The F8 delivery-terminus caller (INTAKE-TO-DELIVERY Stage 5→6): L1's final-accept made
    # concrete. Pure serialization here — the DAEMON performs the cross-jail copy/push and the
    # executor.deliver stamp (promotion stays a harnessd action; the CLI stays a client).
    # --decision is REQUIRED so a fat-fingered bare `promote <addr>` cannot speculatively deliver.
    promote_p = subparsers.add_parser(
        "promote",
        help=(
            "L1 final-accept -> control-plane delivery of a project node out of /runtime/ "
            "(mutation -> daemon)"
        ),
    )
    _add_addr(promote_p)
    promote_p.add_argument(
        "--decision", dest="decision", required=True, choices=["accept", "reject"],
        help=(
            "the Stage-5 decision; only 'accept' opens the gate — a reject round-trips as a "
            "recorded no-op (exit 2)"
        ),
    )
    promote_p.add_argument(
        "--acceptance-ref", dest="acceptance_ref", default=None,
        help="the frozen intent-spec the accept was judged against",
    )
    promote_p.add_argument("--note", dest="note", default=None)

    return parser


# ---------------------------------------------------------------------------
# Request assembly — build the daemon request dict from the parsed namespace. NO mutation here: this is
# pure serialization (the daemon performs the mutation). Only the relevant fields per command are sent.
# ---------------------------------------------------------------------------


# Per-command request fields (besides ``command`` + ``addr``) the client serializes and ships.
_REQUEST_FIELDS = {
    "show": (),
    "next-seq": (),
    "validate": (),
    "reconcile-inspect": (),
    "spawn": ("level", "expected_state", "expected_generation", "expected_owner_token", "parent"),
    "transition": (
        "expected_state",
        "expected_generation",
        "expected_owner_token",
        "target_state",
        "event",
    ),
    "kill": ("expected_owner_token", "terminal_signal"),
    "pause": (),
    "resume": (),
    "answer": (),
    "promote": ("decision", "acceptance_ref", "note"),
}


def _build_request(args: argparse.Namespace) -> dict:
    """Serialize the parsed namespace into the daemon request dict (pure — no ledger mutation).

    The ONLY non-trivial step is the spawn ``--brief`` flag: the CLIENT reads the brief FILE
    (client-side file I/O, NOT a ledger write — the brief is the child's task text the daemon writes
    into the child node) and ships its CONTENTS as ``brief_content``. The daemon, not the CLI, writes
    the brief into the child node (the cardinal rule: the CLI is a client, never a writer).
    """
    request: dict = {"command": args.command}
    if hasattr(args, "addr"):
        request["addr"] = args.addr
    for field in _REQUEST_FIELDS.get(args.command, ()):  # only the fields this command carries
        if hasattr(args, field):
            request[field] = getattr(args, field)
    # spawn --brief <file>: read the file CONTENTS (client-side file read) and ship as brief_content.
    brief_path = getattr(args, "brief", None)
    if args.command == "spawn" and brief_path:
        request["brief_content"] = Path(brief_path).read_text(encoding="utf-8")
    # answer --text/--file: ship the answer CONTENTS as answer_content (the --file read mirrors the
    # spawn --brief precedent — client-side file I/O is not ledger I/O; the DAEMON stamps the note).
    if args.command == "answer":
        if getattr(args, "answer_file", None):
            request["answer_content"] = Path(args.answer_file).read_text(encoding="utf-8")
        else:
            request["answer_content"] = args.answer_text
    return request


# ---------------------------------------------------------------------------
# The socket round-trip — the CLIENT's ONLY I/O. Connect, send the framed request, read the response to
# EOF, return the parsed JSON. This is socket I/O, NOT ledger I/O: the client never writes the ledger.
# ---------------------------------------------------------------------------


def _resolve_socket_path(explicit: Optional[str], parsed: Optional[str]) -> Optional[str]:
    """Resolve the daemon socket path: explicit kwarg > --socket flag > env var > RUNTIME_ROOT default."""
    if explicit is not None:
        return explicit
    if parsed is not None:
        return parsed
    env_value = os.environ.get(SOCKET_ENV_VAR)
    if env_value:
        return env_value
    if ledger.RUNTIME_ROOT is not None:
        return str(Path(ledger.RUNTIME_ROOT) / ".harnessd" / SOCKET_FILENAME)
    return None


def _round_trip(socket_path: str, request: dict) -> dict:
    """Send ``request`` to the daemon at ``socket_path``, return the parsed JSON response.

    Connects to the AF_UNIX socket, writes the whole request, shuts down the write half (so the daemon's
    EOF-framed read terminates), reads the response to EOF, and parses it. A missing socket / refused
    connection raises (FileNotFoundError / ConnectionError / OSError) — the client is NOT a writer, so
    an unreachable daemon is a hard failure the caller surfaces as a nonzero exit (never a local write).
    """
    payload = json.dumps(request).encode("utf-8")
    with socket_mod.socket(socket_mod.AF_UNIX, socket_mod.SOCK_STREAM) as client:
        client.connect(str(socket_path))
        client.sendall(payload)
        client.shutdown(socket_mod.SHUT_WR)  # signal EOF so the daemon's read-to-EOF completes
        chunks: list[bytes] = []
        while True:
            data = client.recv(65536)
            if not data:
                break
            chunks.append(data)
    raw = b"".join(chunks)
    if not raw.strip():
        return {"ok": False, "errors": ["empty response from daemon"]}
    return json.loads(raw.decode("utf-8"))


# ---------------------------------------------------------------------------
# main — parse argv, build the request, ship it over the socket, print the JSON response + return an
# exit code. The ONLY entrypoint. A CLIENT: arg parsing + socket I/O, never a ledger write.
# ---------------------------------------------------------------------------


def main(argv: Optional[list] = None, *, socket_path: Optional[str] = None) -> int:
    """Parse ``argv``, ship the request to the daemon, print the JSON response, return an exit code.

    Exit codes (the print-JSON / exit-code convention):
      0 — the daemon reported ``ok`` (a committed mutation or a successful read);
      2 — a command-level abort: the daemon reported ``ok`` false (a CAS miss / illegal edge /
          fencing rejection) OR a client-side input error (an unreadable ``--brief``/``--file``
          input file — the daemon was never contacted, the ledger untouched);
      3 — a transport failure (no daemon reachable, or a garbled non-JSON response) — the client
          cannot perform the mutation itself. Every failure is a printed JSON error line + a nonzero
          exit, never a traceback.

    The mutation path is SOCKET I/O, not ledger I/O: ``main`` builds a request dict and ships it; the
    DAEMON performs the mutation inside the one lock. ``main`` never writes the ledger.
    """
    if argv is None:
        argv = sys.argv[1:]

    parser = build_parser()
    args = parser.parse_args(argv)

    resolved_socket = _resolve_socket_path(socket_path, getattr(args, "socket_path", None))
    if resolved_socket is None:
        print(json.dumps({"ok": False, "errors": ["no daemon socket configured (--socket / $HARNESSD_SOCKET / RUNTIME_ROOT)"]}))
        return 3

    # The client-side input-file reads (spawn --brief / answer --file) get their OWN guard, scoped to
    # the _build_request call only — NOT folded into the transport except below (that would mislabel a
    # missing input file as "daemon unreachable"). The daemon was never contacted -> exit 2 (a
    # command-level abort), the ledger untouched (DAEMON §4.3). OSError covers FileNotFoundError /
    # PermissionError / IsADirectoryError; UnicodeDecodeError covers a binary input file.
    try:
        request = _build_request(args)
    except (OSError, UnicodeDecodeError) as exc:
        # Name the ACTUAL input file: spawn carries --brief, answer carries --file (F16) — report
        # whichever this command shipped, never hard-coding the message to one flag.
        brief_path = getattr(args, "brief", None)
        answer_path = getattr(args, "answer_file", None)
        flag, input_path = ("--brief", brief_path) if brief_path else ("--file", answer_path)
        print(json.dumps({
            "ok": False,
            "command": args.command,
            "errors": [f"cannot read {flag} input file {input_path!r}: {exc}"],
        }))
        return 2

    try:
        response = _round_trip(resolved_socket, request)
    except (ConnectionError, FileNotFoundError, OSError) as exc:
        # The daemon is unreachable. The CLIENT cannot perform the mutation itself (DAEMON §4.3) — print
        # the error as JSON and fail with a nonzero exit. The ledger is NOT touched.
        print(json.dumps({"ok": False, "command": args.command, "errors": [f"daemon unreachable: {exc}"]}))
        return 3
    except json.JSONDecodeError as exc:
        # The daemon answered with bytes the client cannot parse (json.JSONDecodeError is a ValueError,
        # NOT caught by the OSError-family arm above). The daemon did not speak the protocol — a
        # transport-class failure (exit 3), structured, never a traceback.
        print(json.dumps({
            "ok": False,
            "command": args.command,
            "errors": [f"garbled response from daemon (not JSON): {exc}"],
        }))
        return 3

    # The `tree` read is rendered as a human-readable supervision tree (the operator fleet view, COMP-4);
    # every other command prints the raw JSON response (the machine surface).
    if args.command == "tree" and response.get("ok"):
        print(render_tree(response.get("nodes") or {}))
        return 0
    print(json.dumps(response))
    return 0 if response.get("ok", False) else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
