"""addressing — the ONE canonical address→workspace mapping (the one-spine, NESTED).

An address is ``<path>#<seat>`` (e.g. ``proj/payments/gateway/stripe-client#exec``). The node WORKSPACE
is the PATH, nested on disk: ``<RUNTIME_ROOT>/nodes/proj/payments/gateway/stripe-client/``. Nesting is
load-bearing: a child's dir sits UNDER its parent's, so the write-jail's existing "write your WORKROOT
subtree" rule gives a coordinator write access to its children's nodes — which is exactly the canonical
write model:

  * ARCHITECTURE.md:122 — "Write access follows the NESTED tree — each level writes within its own
    workspace and CREATES CHILD WORKSPACES WITHIN IT."
  * IMPLEMENTATION-PLAN — "every agent is write-jailed to its /runtime/ node SUBTREE."
  * WORKSPACE-SCHEMA — the visibility graph: own subtree + same-level siblings + parent.

The earlier flat ``a/b#seat -> a-b-seat`` collapse (a misread of the plan-diagram word "collapsed-
address" as flatten-slashes, when the spec means collapse-the-#seat-but-keep-the-path) put every node
in its OWN flat dir, so a coordinator's WORKROOT did NOT contain its children — which is why the build
fell back to passing the brief as spawn payload. This module is the fix: ONE nested derivation, used by
the chokepoint (node/brief landing), the sandbox (jail WORKROOT), the detector (sign-off signal), and
the watchdog (wake inbox), so they cannot drift.

THE SEAT is NOT a path segment. ``#exec`` and ``#review`` are two ACTORS on ONE node (the reviewer reads
the executor's work in place), so they share the node WORKSPACE. Making the seat a trailing path segment
would break child-nesting (a child of ``parser#exec`` would not sit under ``parser/exec/``). Only the
PER-ACTOR metadata files — the sign-off ``.signal`` and the wake ``.inbox`` — are seat-qualified, so the
L5/L5+ pair sharing a node dir don't clobber each other's sign-off.
"""

from pathlib import Path

# The default seat when an address carries no ``#`` (the working incarnation).
DEFAULT_SEAT: str = "exec"

# The runtime subdir that holds all node workspaces (``<RUNTIME_ROOT>/nodes/<nested-path>/``).
NODES_DIRNAME: str = "nodes"


def split_address(address: str) -> tuple[str, str]:
    """``a/b#seat`` -> ``("a/b", "seat")``. No ``#`` -> the default ``exec`` seat.

    The PATH is what nests on disk; the SEAT distinguishes two actors on the same node.
    """
    path, sep, seat = address.partition("#")
    return path, (seat if (sep and seat) else DEFAULT_SEAT)


def node_path(address: str) -> str:
    """The nested on-disk relpath for a node — the PATH part only (the ``#seat`` is NOT a segment)."""
    return split_address(address)[0]


def node_dir(address: str, runtime_root) -> Path:
    """``<runtime_root>/nodes/<nested-path>/`` — a child's dir nests UNDER its parent's (subtree).

    This is BOTH the agent's workspace and the jail WORKROOT, so ``(allow file-write* (subpath
    WORKROOT))`` on a coordinator's node dir covers all of its descendants' dirs.
    """
    return Path(runtime_root) / NODES_DIRNAME / node_path(address)


def signal_path(address: str, runtime_root) -> Path:
    """The per-SEAT sign-off signal file: ``<node-dir>/.signal.<seat>.json``.

    Seat-qualified so the L5 (exec) and L5+ (review) sharing one node dir don't clobber each other's
    terminal signal (each actor signs off independently).
    """
    _, seat = split_address(address)
    return node_dir(address, runtime_root) / f".signal.{seat}.json"


def inbox_path(address: str, runtime_root) -> Path:
    """The per-SEAT wake inbox: ``<node-dir>/.inbox.<seat>.jsonl`` (③-wake surface, multi-writer)."""
    _, seat = split_address(address)
    return node_dir(address, runtime_root) / f".inbox.{seat}.jsonl"
