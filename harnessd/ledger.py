"""Binding-ledger + run-ledger (WAL) I/O — the durable state layer of the harness.

Authoritative sources:
  - IMPLEMENTATION-PLAN §2.4 (frozen ledger.py interface) + §3 module table (ledger.py row)
    + §3.4 (binding record / WAL record schema) + §4.4 (intent-first ordering + torn-tail).
  - DAEMON §3.2, §3.4, §3.5, §4.3 (binding atomic-replace + single-writer rule), §4.4
    (intent-first crash-atomicity + framed-append torn-tail tolerance).
  - REWRITE of the recovered control_plane.py ``load_ledger`` L209-225 — the ANTI-pattern:
    it RAISES ``ValueError`` on ANY ``json.JSONDecodeError`` (L220), so a single torn final
    line (the ordinary crash-mid-append artifact) bricked the entire boot-recovery path.
    This module CORRECTS that: truncate-and-continue on a torn FINAL line, FAIL CLOSED only
    on a torn NON-FINAL line (mid-file corruption is not a crash artifact).

RESOLVED FORKS this module implements (user-delegated 2026-06-05):
  * FORK-CRC: ``build_wal_record`` always emits ``crc32(payload)``; ``load_wal`` treats
    ``crc32(content) != record['crc32']`` as a torn signal ALONGSIDE the length-prefix
    mismatch. This catches a silently-SPLIT record whose declared byte-len prefix STILL
    equals the surviving byte count (the case the length-prefix alone misses). The crc32 is
    computed over the json CONTENT of the record's NON-crc32 fields (deterministic key
    order) — never over a length, never over itself (not circular). NO ``len`` field inside
    the json: the framed ``<byte-len>`` PREFIX (owned by ``store.append_framed``) is the
    sole length authority.
  * FORK-SEQ: ``next_seq()`` = last WAL ``seq`` + 1, computed on load from the WAL itself.
    No persisted counter to desync; 1-based on an empty/absent WAL.

BINDING-LEDGER SERIALIZATION (fork settled, reported to the orchestrator): §2.4 names the
file ``binding-ledger.yaml`` and DAEMON §3.4 shows a YAML example, but the design treats the
file as DAEMON-WRITTEN ONLY (§4.3: "CLIs are clients, never writers"; "No external process
ever read-modify-replaces binding-ledger.yaml directly"). The serialization FORMAT is nowhere
pinned as load-bearing — the ``.yaml`` naming is the recovered ``manifest.yaml`` carried
forward, not a content requirement. This module serializes the binding ledger as **JSON**:
stdlib (no new dep beyond what's already vendored), round-trips cleanly through
``store.normalize_scalars``, and is consistent with the WAL's json framing. The file name is
taken from the injected ``binding_path`` (tests use ``binding-ledger.json``); under
``RUNTIME_ROOT`` the default name is ``binding-ledger.json``.

PATH INJECTION (§2.4 "make the WAL + binding paths injectable"): both the WAL and binding
paths are injectable. Each public function accepts a per-call keyword (``wal_path=`` /
``binding_path=``) that overrides the module-level ``RUNTIME_ROOT`` default. The daemon binds
``RUNTIME_ROOT`` once at startup to ``/runtime/<build-id>/``; tests target ``tmp_path``.
"""

from __future__ import annotations

import json
import zlib
from pathlib import Path

from . import clock, store

# ---------------------------------------------------------------------------
# Injectable runtime root + the canonical on-disk file names (§3 tree).
#
# RUNTIME_ROOT is the daemon-bound default; a per-call wal_path=/binding_path=
# keyword overrides it (the test adapter and the daemon both drive it this way).
# ---------------------------------------------------------------------------

RUNTIME_ROOT: Path | None = None

WAL_FILENAME: str = "run-ledger.jsonl"
BINDING_FILENAME: str = "binding-ledger.json"


def _resolve_wal_path(wal_path: Path | None) -> Path:
    """Resolve the WAL path: the explicit per-call path wins, else RUNTIME_ROOT/<wal name>."""
    if wal_path is not None:
        return Path(wal_path)
    if RUNTIME_ROOT is not None:
        return Path(RUNTIME_ROOT) / WAL_FILENAME
    raise RuntimeError(
        "ledger WAL path is not configured: pass wal_path= or bind ledger.RUNTIME_ROOT"
    )


def _resolve_binding_path(binding_path: Path | None) -> Path:
    """Resolve the binding path: explicit per-call path wins, else RUNTIME_ROOT/<binding name>."""
    if binding_path is not None:
        return Path(binding_path)
    if RUNTIME_ROOT is not None:
        return Path(RUNTIME_ROOT) / BINDING_FILENAME
    raise RuntimeError(
        "ledger binding path is not configured: pass binding_path= or bind ledger.RUNTIME_ROOT"
    )


# ---------------------------------------------------------------------------
# crc32 over record CONTENT (FORK-CRC). Measures the json content of the
# record's NON-crc32 fields in deterministic key order — never the length, never
# itself, so it is not circular.
# ---------------------------------------------------------------------------

def _crc32_of_content(record: dict) -> int:
    """crc32 of the json content of ``record`` excluding its own ``crc32`` field.

    Deterministic key order (``sort_keys=True``) and ``ensure_ascii=True`` so the digest is
    byte-stable across processes and matches the loader's recompute exactly.
    """
    body = {key: value for key, value in record.items() if key != "crc32"}
    content = json.dumps(body, sort_keys=True, ensure_ascii=True)
    return zlib.crc32(content.encode("utf-8")) & 0xFFFFFFFF


# ---------------------------------------------------------------------------
# WAL record construction (§2.4 frozen field set).
# ---------------------------------------------------------------------------

def build_wal_record(
    *,
    node_address,
    event,
    from_state,
    to_state,
    expected_generation,
    generation,
    lease_epoch,
    owner_token,
    binding_delta,
    summary,
    artifacts,
    seq,
) -> dict:
    """Build one frozen-shape WAL record (§2.4).

    Fields: ``{ts, seq, node_address, event, actor:'harnessd', crc32, from_state, to_state,
    expected_generation, generation (=expected+1), lease_epoch, owner_token, binding_delta,
    summary, artifacts}``. ``actor`` is fixed to ``'harnessd'`` — the single writer. There is
    NO ``len`` field: the framed ``<byte-len>`` prefix is the sole length authority. ``crc32``
    is computed over the json CONTENT of all other fields (FORK-CRC) for content integrity /
    split-record detection — never over a length, never over itself.

    Scalars are normalized (``store.normalize_scalars``) so a datetime/date in ``binding_delta``
    or elsewhere serializes deterministically; this keeps the producer crc32 and the loader's
    recompute byte-identical (both see the same json content).
    """
    record = {
        "ts": clock.now_utc(),
        "seq": seq,
        "node_address": node_address,
        "event": event,
        "actor": "harnessd",  # the single writer (DAEMON §4.3)
        "from_state": from_state,
        "to_state": to_state,
        "expected_generation": expected_generation,
        "generation": generation,
        "lease_epoch": lease_epoch,
        "owner_token": owner_token,
        "binding_delta": binding_delta,
        "summary": summary,
        "artifacts": artifacts,
    }
    record = store.normalize_scalars(record)
    # crc32 LAST, over the normalized content of the other fields (not over itself).
    record["crc32"] = _crc32_of_content(record)
    return record


# ---------------------------------------------------------------------------
# WAL append (hands RAW json to store.append_framed — NEVER pre-frames; §2.4).
# ---------------------------------------------------------------------------

def append_wal(record: dict, *, wal_path: Path | None = None) -> None:
    """Append ``record`` to the WAL as one durable framed line.

    Hands the RAW ``json.dumps(record)`` string to ``store.append_framed`` (the sole owner of
    framing), which writes ``<byte-len>\\t<payload>\\n`` in EXACTLY ONE ``write()`` + fsync.
    ``append_wal`` never pre-frames and never computes a length itself — the ``<byte-len>``
    prefix is store's job and is the sole length authority (no in-payload ``len``).

    ``ensure_ascii=True`` (json.dumps default) guarantees no raw newline in the payload, which
    is store.append_framed's precondition (one record == one physical line).
    """
    path = _resolve_wal_path(wal_path)
    payload = json.dumps(record)
    store.append_framed(path, payload)


# ---------------------------------------------------------------------------
# WAL load — the headline torn-tail-tolerant REWRITE (§2.4 / §4.4).
# ---------------------------------------------------------------------------

class WALCorruptionError(ValueError):
    """A NON-final WAL line is corrupt (mid-file) — fail closed, not a crash-tail artifact."""


def _line_is_torn(line: str) -> tuple[bool, dict | None]:
    """Classify one physical WAL line (no trailing newline).

    Returns ``(torn, record)``. A line is TORN iff any of:
      * it has no TAB separator (incomplete frame), OR
      * the declared ``<byte-len>`` prefix is not an int, OR
      * the prefix != the UTF-8 byte length of the payload (length-frame mismatch), OR
      * ``json.loads(payload)`` fails (truncated/broken json), OR
      * ``crc32(content) != record['crc32']`` (FORK-CRC split-record backstop — catches a
        record whose byte length still matches but whose content was silently corrupted).
    When NOT torn, ``record`` is the parsed dict; when torn it is ``None``.
    """
    if "\t" not in line:
        return True, None
    prefix, payload = line.split("\t", 1)
    try:
        declared_len = int(prefix)
    except ValueError:
        return True, None
    if declared_len != len(payload.encode("utf-8")):
        return True, None  # length-frame mismatch — primary torn signal
    try:
        record = json.loads(payload)
    except json.JSONDecodeError:
        return True, None
    if not isinstance(record, dict):
        return True, None
    # FORK-CRC backstop: only meaningful when the record carries a crc32 (all records built by
    # build_wal_record do). A crc disagreement is a torn signal even when the length matched.
    expected_crc = record.get("crc32")
    if expected_crc is not None and _crc32_of_content(record) != expected_crc:
        return True, None
    return False, record


def load_wal(*, wal_path: Path | None = None) -> list[dict]:
    """Load the WAL, tolerant of a torn FINAL line, fail-closed on a torn NON-final line.

    REWRITE of the recovered ``load_ledger`` L209-225, which RAISED ``ValueError`` on ANY
    json decode error (L220) and so bricked boot recovery on the ordinary crash-mid-append
    artifact. The corrected rule (§4.4):

      * torn on the LAST physical line  -> TRUNCATE-and-continue (a crash mid-append whose
        binding atomic-replace never landed; the clean prefix is the recovered state).
      * torn on ANY non-final line      -> FAIL CLOSED (raise ``WALCorruptionError``): a
        mid-file corruption is NOT a crash-tail artifact and proves the single-write contract
        was violated, so halting is correct.

    An absent WAL loads as ``[]`` (never raises). The on-disk text is split on ``\\n``; a
    trailing newline yields a final empty segment that is ignored (the file ended cleanly).
    """
    path = _resolve_wal_path(wal_path)
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return []

    if text == "":
        return []

    # Split into physical lines. A clean file ends in "\n" -> trailing "" segment we drop.
    # A torn final append (no trailing "\n") leaves its partial bytes as the last segment.
    segments = text.split("\n")
    if segments and segments[-1] == "":
        segments.pop()  # the file ended on a newline; no dangling partial tail

    records: list[dict] = []
    last_index = len(segments) - 1
    for index, line in enumerate(segments):
        torn, record = _line_is_torn(line)
        if torn:
            if index == last_index:
                # The final line is torn: a crash mid-append. Truncate it and return the
                # clean prefix — DO NOT raise (the L220 brick is exactly this case).
                break
            # A non-final line is torn: mid-file corruption -> fail closed, deliberately.
            raise WALCorruptionError(
                f"corrupt non-final WAL line at index {index} in {path} "
                "(mid-file corruption is not a crash-tail artifact — failing closed; "
                "the single-write contract guarantees only the FINAL line can be torn)"
            )
        records.append(record)
    return records


# ---------------------------------------------------------------------------
# next_seq — FORK-SEQ: last WAL seq + 1, derived from the WAL on load.
# ---------------------------------------------------------------------------

def next_seq(*, wal_path: Path | None = None) -> int:
    """Return the next monotonic ``seq`` to allocate: last WAL ``seq`` + 1 (FORK-SEQ).

    Derived from the WAL itself on load (no persisted counter to desync). An empty/absent
    WAL yields the base ``1`` (the first record is ``seq == 1``). A torn tail does NOT poison
    the allocation: ``load_wal`` has already truncated it, so the max here is the last GOOD
    seq. The ``seq`` is the global monotonic ordering AND the per-node replay watermark, so a
    crash-safe allocation is load-bearing.
    """
    wal = load_wal(wal_path=wal_path)
    if not wal:
        return 1
    return max(record["seq"] for record in wal) + 1


# ---------------------------------------------------------------------------
# Binding ledger I/O — whole-map atomic-replace (Option A), JSON on disk.
# ---------------------------------------------------------------------------

def _load_binding_map(binding_path: Path | None) -> dict:
    """Load the whole binding-ledger keyed map (Option A). Absent file -> empty map."""
    path = _resolve_binding_path(binding_path)
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    if text.strip() == "":
        return {}
    loaded = json.loads(text)
    if not isinstance(loaded, dict):
        # The binding ledger is a single keyed map (Option A). A non-object top level means a
        # corrupt or externally-tampered file — fail with a clear error, not a downstream
        # AttributeError on .get(). (It is daemon-written via atomic_replace, so this is a
        # never-should-happen guard, surfaced loudly rather than silently mis-handled.)
        raise ValueError(
            f"binding ledger at {path} is not a JSON object (got {type(loaded).__name__}) "
            "— corrupt or externally tampered"
        )
    return loaded


def read_binding(node_address: str, *, binding_path: Path | None = None) -> dict | None:
    """Return the one binding record for ``node_address`` (Option A keyed map), or None.

    None when the node is absent from the map OR the binding file does not exist — the daemon
    treats both as "no such binding yet". CLIs read through the daemon; this is the read side.
    """
    return _load_binding_map(binding_path).get(node_address)


def all_nodes(*, binding_path: Path | None = None) -> dict[str, dict]:
    """Return the whole binding-ledger keyed map (address#seat -> binding). Absent -> ``{}``."""
    return _load_binding_map(binding_path)


def write_binding(candidate_map: dict, *, _lock_held: bool, binding_path: Path | None = None) -> None:
    """Whole-map atomic-replace of the binding ledger (Option A) — PRIVATE, lock-guarded.

    With a single keyed file, a whole-map replace by anyone but the serialized daemon writer
    silently CLOBBERS a concurrent write to a DIFFERENT node — per-node generation CAS cannot
    catch a cross-node overwrite (DAEMON §4.3). So this is a STRUCTURAL single-writer guard,
    not a convention: ``_lock_held`` MUST be True (the caller holds the one EX serialization
    lock). It is keyword-only (§2.4 signature ``write_binding(candidate_map, *, _lock_held)``)
    so a positional spelling cannot smuggle past the guard, and it has NO default so a bare
    call raises ``TypeError`` (a missing-guard call is non-conformant, not silently allowed).

    The guard fires BEFORE any disk write, so a guard violation leaves the prior map intact.
    The map is persisted via ``store.atomic_replace`` (tmp + fsync + os.replace), so a concurrent
    reader never sees a torn binding ledger and a render failure leaves the original untouched.
    """
    if not _lock_held:
        raise PermissionError(
            "write_binding called without the held EX lock (_lock_held=False): a whole-map "
            "replace by a non-serialized writer silently clobbers a concurrent cross-node "
            "write that per-node CAS cannot catch (DAEMON §4.3). This is a structural "
            "single-writer guard — route the mutation through the daemon."
        )
    path = _resolve_binding_path(binding_path)
    serializable = store.normalize_scalars(candidate_map)

    def render(handle):
        json.dump(serializable, handle, ensure_ascii=True, sort_keys=True, indent=2)
        handle.write("\n")

    store.atomic_replace(path, render)
