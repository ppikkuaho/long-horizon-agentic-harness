"""detector_signals — the RAW signal readers the liveness verdict fuses (Increment 6).

Authoritative sources:
  - IMPLEMENTATION-PLAN §2.8 (the FROZEN detector_signals.py interface — exact
    signatures below): jsonl_progress / pane_alive / pane_pid_cpu / read_terminal_signal.
  - IMPLEMENTATION-PLAN §4.1 "terminal-signal reader (the PRODUCER for INCLUDE-item #3,
    fully mockable)" (L564-571) — the stale-owner_token fence is the load-bearing case.
  - Runtime tree layout (§3 tree, L454-471): nodes/<collapsed-address>/.signal.json carries
    {signal: DONE|FAILED|ESCALATED, ts, owner_token, evidence}, agent-written atomic tmp+rename.

THE TMUX SEAM (§2.11, frozen Increment 0; concrete tmux.py lands Increment 9):
    pane_alive() reaches tmux ONLY through the module-level `_tmux` reference (the §2.11
    `display-message '#{pane_dead} #{pane_pid}'` interface). In Increment 6 there is no
    concrete tmux.py, so `_tmux` is None and pane_alive's tmux branch is unreachable under
    the test harness — tests MONKEYPATCH `pane_alive` (and the detector's reference to it)
    directly, per the frozen test's `_patch_signals_everywhere`. The seam is a module-level
    name so Increment 9 can bind `_tmux = harnessd.spawn.tmux` (or the detector can inject a
    fake) WITHOUT editing this module's verdict-feeding readers. See escalations/notes in the
    Increment-6 builder report for how this was wired.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# The TMUX seam (§2.11). MOCKABLE module-level reference. None until Increment 9
# binds the concrete `harnessd/spawn/tmux.py`. pane_alive() calls through this; a
# test that wants real-tmux behavior monkeypatches pane_alive itself (Inc 6 floor).
# ---------------------------------------------------------------------------

_tmux = None  # Increment 9: `import harnessd.spawn.tmux as _tmux` (the §2.11 interface).


# ---------------------------------------------------------------------------
# Fail-loud sentinel for the spawn<->detector contract violation (no transcript_path).
# A binding with no transcript_path is a contract violation that must surface, NEVER
# be silently swallowed into a benign (False, None) 'flat' the verdict reads as idle/dead.
# ---------------------------------------------------------------------------

class MissingTranscriptPath(ValueError):
    """A node/binding carries no transcript_path — the spawn<->detector contract is broken.

    Raised by jsonl_progress (and surfaced by detector.liveness) so the violation fails LOUD
    at the cheapest place to catch it, rather than collapsing the node to a phantom dead/idle.
    """


# The internal size/mtime cache backing jsonl_progress's grew-vs-flat comparison.
# Keyed by node_address. This is the impl's private business (the frozen contract is the
# SIGNAL the verdict fuses, not this cache); tests pin the signal by monkeypatching the
# reader at the detector's call site, so this cache is exercised only by the signal-layer
# tests that drive a real file.
_size_cache: dict[str, int] = {}


def _node_address(node) -> str:
    """The node's stable address (the cache key). Accepts a binding/node-shaped dict."""
    return node["node_address"]


def _transcript_path(node):
    """Resolve the node's transcript_path; a missing/None value is a contract violation.

    Both an explicit ``transcript_path: None`` and an entirely MISSING key are the same
    spawn<->detector violation, so both raise MissingTranscriptPath (fail-loud), never a
    silent benign return.
    """
    path = node.get("transcript_path")
    if not path:
        raise MissingTranscriptPath(
            f"node {node.get('node_address')!r} has no transcript_path — the spawn<->detector "
            "contract requires one; refusing to silently read as flat/dead/idle"
        )
    return path


def _iso_from_mtime(st_mtime: float) -> str:
    """Render a stat st_mtime (epoch seconds) as a tz-aware UTC ISO-8601 string."""
    return datetime.fromtimestamp(st_mtime, tz=timezone.utc).isoformat()


def jsonl_progress(node) -> tuple[bool, str | None]:
    """(grew, mtime_iso) from os.stat(transcript) st_size/st_mtime vs a cached prior (§2.8).

    grew is True iff the transcript's byte size is STRICTLY GREATER than the size cached from
    the prior read for this node — the forward-progress signal the verdict fuses. The first
    read establishes the baseline (grew=False, no prior to grow past); subsequent reads compare
    against the last observed size. mtime_iso is the file's st_mtime rendered as a tz-aware UTC
    ISO-8601 string (the detector compares it via the canonical clock).

    FAIL-LOUD: no transcript_path -> raises MissingTranscriptPath (NEVER a silent (False, None)
    that the verdict would read as a benign flat). An absent FILE (path set but not yet created)
    is a transient pre-write condition, not a contract violation: it reads (False, None).
    """
    address = _node_address(node)
    path = _transcript_path(node)  # raises MissingTranscriptPath on the contract violation

    try:
        st = os.stat(path)
    except FileNotFoundError:
        # The path is contracted but the file is not on disk yet (a just-spawned actor that
        # has not written its first transcript line). This is transient, NOT the contract
        # violation — read as flat with no mtime, do not poison the cache.
        return False, None

    prior = _size_cache.get(address)
    _size_cache[address] = st.st_size
    grew = prior is not None and st.st_size > prior
    return grew, _iso_from_mtime(st.st_mtime)


def pane_alive(node) -> tuple[bool, int | None]:
    """(alive, pane_pid) via the tmux display-message '#{pane_dead} #{pane_pid}' interface (§2.8/§2.11).

    Reaches tmux ONLY through the module-level `_tmux` seam (frozen §2.11 interface; concrete
    tmux.py lands Increment 9). alive is True iff the pane exists and is not pane_dead. In
    Increment 6 `_tmux` is None (no concrete adapter), so this raises if called un-mocked —
    the floor's tests MONKEYPATCH this reader (the boundary the detector calls), per
    §4 subscription-safety (ZERO model usage, tmux mocked).
    """
    if _tmux is None:
        raise RuntimeError(
            "pane_alive: the tmux seam is not bound (Increment 9 binds harnessd.spawn.tmux). "
            "Increment 6 mocks this reader directly — see detector_signals._tmux."
        )
    target = node["tmux_target"]
    # §2.11 interface: list_targets() -> {tmux_target: {pane_pid, pane_dead, window_activity}}.
    targets = _tmux.list_targets()
    info = targets.get(target)
    if info is None:
        return False, None  # pane gone entirely -> not alive
    pane_dead = bool(info.get("pane_dead"))
    pane_pid = info.get("pane_pid")
    return (not pane_dead), (None if pane_dead else pane_pid)


def pane_pid_cpu(node, pane_pid) -> float | None:
    """ps -o %cpu= for the pane pid — WEDGE-PATH ONLY; STUB-return None in v1 (§2.8).

    The CPU heuristic is the wedge-detection path (a pane that is warm but burning no CPU);
    it is DEFERRED. v1 fuses ONLY jsonl_progress + pane_alive, so this is a hard stub that
    always returns None — an impl that fuses real CPU into v1 is non-conformant.
    """
    return None


# ---------------------------------------------------------------------------
# read_terminal_signal — the FENCED .signal.json reader (the §4.1 producer for
# INCLUDE-item #3). nodes/<collapsed-address>/.signal.json -> {signal, ts, owner_token, evidence}.
# ---------------------------------------------------------------------------

def _signal_path(node):
    """The per-SEAT sign-off signal: ``<nested-node-dir>/.signal.<seat>.json`` (``addressing.signal_path``).

    NESTED by path + seat-qualified: exec and review share the node dir (two actors, one node) so the
    signal filename carries the seat to keep their sign-offs distinct. Resolved against the ledger's
    injectable RUNTIME_ROOT (the daemon binds it once; tests bind tmp_path) so the agent-writer and the
    detector-reader agree on the same path without a second seat.
    """
    from . import addressing, ledger  # local import: share the ONE injectable RUNTIME_ROOT seat

    root = ledger.RUNTIME_ROOT
    if root is None:
        raise RuntimeError(
            "read_terminal_signal: ledger.RUNTIME_ROOT is not bound — the runtime tree root is "
            "where nodes/<nested-path>/.signal.<seat>.json lives; bind it (daemon startup / tests)."
        )
    return addressing.signal_path(_node_address(node), root)


def read_terminal_signal(node, binding) -> dict | None:
    """Read the FENCED terminal-signal artifact for a node (§2.8 / §4.1).

    Returns {signal, ts, owner_token, evidence} IFF the on-disk .signal.json exists AND its
    owner_token EQUALS the live binding's owner_token (current epoch). Otherwise None:

      * absent .signal.json (or absent node dir)            -> None
      * a STALE owner_token (a prior incarnation's leftover) -> None  (THE LOAD-BEARING FENCE:
        a dead incarnation's leftover signal must NEVER collapse a re-spawned node at the same
        address — the watchdog journals stale_return_ignored and falls through to liveness).

    The reader does NOT decide collapse-vs-noop and does NOT filter by signal kind — an ESCALATED
    signal with a live token is returned unchanged (the verdict needs it as the waiting-reason;
    the watchdog routes ESCALATED to NOOP, DONE/FAILED to collapse).
    """
    path = _signal_path(node)
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None  # no signal artifact present -> no terminal event

    payload = json.loads(text)

    # THE FENCE: only a signal whose owner_token matches the LIVE binding's owner_token is the
    # current incarnation's. A lower/other-epoch token is a stale leftover -> ignore (None).
    if payload.get("owner_token") != binding.get("owner_token"):
        return None

    return payload
