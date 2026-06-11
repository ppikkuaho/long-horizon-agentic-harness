"""return_contract — E2: the deterministic return-contract walker on the sign-off path.

The 2026-06-11 live run + corpus read (LR-14) found the role docs' load-bearing enforcement —
"the return-contract hook walks your artifact and REJECTS it: you cannot report complete"
(operational/L1/role.md, operational/L2/role.md, operational/shared/intent-spec-contract.md) —
existed only as OFFLINE eval scoring (tools/eval_*.py). This module is the runtime half: invoked
by ``watchdog.check_terminal_signal`` on a fenced DONE signal, BEFORE ``chokepoint.collapse``.
A node whose return artifacts fail the deterministic floor is NOT collapsed: the signal stays on
disk, ONE edge-triggered typed-defect row lands in the run-ledger, and ONE defect line lands in
the node's inbox (the ③-wake delivers the nudge) so the agent fixes and re-signals.

THE v1 FLOOR (deterministic only — judgment stays eval-side, per the user-ratified split):
  1. MISSING-REPORT      — ``report.md`` must exist (non-empty) in the node dir at DONE. Every
                           level's role doc names the report as the parent-facing deliverable.
  2. MISSING-REQUIREMENT-CITATION — (L5-class seats only, and ONLY when the node was GIVEN minted
                           IDs): the report must cite >=1 of the requirement IDs present in the
                           node's brief.md/acceptance.md ("you do not mint IDs — they are given to
                           you in the brief; you cite them", operational/L5/role.md §Outputs). A
                           node given NO IDs (a smoke project with no minted spine) owes none.
  3. MALFORMED-TRACE / DUP-ID / TRACE-CONTRADICTION — every ``<!-- trace: {...} -->`` stanza in
                           the node's own top-level *.md files must parse with EXACTLY the closed
                           field set {id, serves, kind, level, node} (PLAN-ALIGNMENT-GATE
                           §Requirements-Traceability), ids unique within the node, and a
                           ``kind: requirement`` dotted id must truncate INTO one of its declared
                           ``serves`` ids. Stanzas are validated WHERE PRESENT — their existence
                           is the gate/eval layer's question, not this floor's.

NEVER TRAP: FAILED and ESCALATED signals are exempt — an agent can always fail/escalate loud
without contract checks (a failing agent must never be wedged into its own refusal loop).

Edge-triggered: the defect row + inbox line land ONCE per (node, signal ts); a re-poll of the
same still-failing artifact journals nothing (the watchdog_checkpoint dedup pattern).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from harnessd import addressing, clock, executor, ledger

# The closed trace-block field set (PLAN-ALIGNMENT-GATE §Requirements-Traceability).
_TRACE_FIELDS = {"id", "serves", "kind", "level", "node"}
_TRACE_STANZA = re.compile(r"<!--\s*trace:\s*\{(.*?)\}\s*-->", re.DOTALL)
_SERVES_LIST = re.compile(r"serves:\s*\[([^\]]*)\]")
_ID_TOKEN = re.compile(r"\b(?:R-\d+(?:\.\d+)*|DR-\d+\w*)\b")

EVENT = "return_contract_failed"


@dataclass
class ContractVerdict:
    ok: bool
    defects: list = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.ok


def _node_dir(node_address: str) -> Optional[Path]:
    if ledger.RUNTIME_ROOT is None:
        return None
    try:
        return addressing.node_dir(node_address, ledger.RUNTIME_ROOT)
    except (OSError, ValueError):
        return None


def check_done_contract(node_address: str, binding: dict) -> ContractVerdict:
    """The deterministic DONE-contract floor. Returns ok=True when every check passes (or when no
    runtime root is bound — nothing to walk; the substrate tests drive collapse without a tree)."""
    node_dir = _node_dir(node_address)
    if node_dir is None or not node_dir.is_dir():
        # No workspace on disk to walk — nothing checkable (e.g. substrate-only test paths).
        return ContractVerdict(ok=True)

    defects: list = []

    # --- 1. MISSING-REPORT: report.md present + non-empty -----------------------------------
    report = node_dir / "report.md"
    report_text = ""
    if not report.is_file() or not (report_text := report.read_text(encoding="utf-8", errors="replace")).strip():
        defects.append(
            f"MISSING-REPORT: {node_address} signed DONE without a non-empty report.md — the "
            f"parent-facing deliverable every role doc requires (you cannot report complete)"
        )

    # --- 2. MISSING-REQUIREMENT-CITATION (L5-class, only when IDs were GIVEN) ----------------
    level = (binding.get("level") or "").strip()
    if level == "L5" and report_text:
        given: set = set()
        for name in ("brief.md", "acceptance.md"):
            f = node_dir / name
            if f.is_file():
                given.update(_ID_TOKEN.findall(f.read_text(encoding="utf-8", errors="replace")))
        if given and not (given & set(_ID_TOKEN.findall(report_text))):
            defects.append(
                f"MISSING-REQUIREMENT-CITATION: {node_address} report.md cites NONE of the "
                f"requirement IDs given in its brief/acceptance ({sorted(given)[:8]}) — the L5+ "
                f"reviewer cannot confirm spec-fidelity against an unstated target (L5 role §Outputs)"
            )

    # --- 3. Trace-block stanzas parse where present ------------------------------------------
    defects.extend(_check_trace_stanzas(node_address, node_dir))

    return ContractVerdict(ok=not defects, defects=defects)


def _parse_stanza(raw: str) -> tuple[Optional[dict], Optional[str]]:
    """Parse one relaxed trace stanza body ('id: R-1.2, serves: [R-1], kind: requirement, …').
    Returns (fields, error)."""
    body = raw.strip()
    serves: list = []
    m = _SERVES_LIST.search(body)
    if m:
        serves = [tok.strip() for tok in m.group(1).split(",") if tok.strip()]
        body = body[: m.start()] + "serves: __SERVES__" + body[m.end():]
    fields: dict = {}
    for pair in body.split(","):
        pair = pair.strip()
        if not pair:
            continue
        if ":" not in pair:
            return None, f"unparseable field {pair!r}"
        key, value = pair.split(":", 1)
        fields[key.strip()] = value.strip()
    if "serves" in fields:
        fields["serves"] = serves
    extra = set(fields) - _TRACE_FIELDS
    if extra:
        return None, f"non-canonical field(s) {sorted(extra)} (closed set is {sorted(_TRACE_FIELDS)})"
    if not fields.get("id"):
        return None, "missing required field 'id'"
    if not fields.get("kind"):
        return None, "missing required field 'kind'"
    return fields, None


def _check_trace_stanzas(node_address: str, node_dir: Path) -> list:
    defects: list = []
    seen_ids: dict = {}
    try:
        md_files = sorted(p for p in node_dir.iterdir() if p.suffix == ".md" and p.is_file())
    except OSError:
        return defects
    for md in md_files:
        try:
            text = md.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for match in _TRACE_STANZA.finditer(text):
            fields, error = _parse_stanza(match.group(1))
            if error:
                defects.append(f"MALFORMED-TRACE: {md.name} in {node_address}: {error}")
                continue
            tid = fields["id"]
            if tid in seen_ids:
                defects.append(
                    f"DUP-ID: {tid} appears in both {seen_ids[tid]} and {md.name} ({node_address})"
                )
            seen_ids[tid] = md.name
            serves = fields.get("serves") or []
            if fields.get("kind") == "requirement" and "." in tid and serves:
                if not any(tid == s or tid.startswith(s + ".") for s in serves):
                    defects.append(
                        f"TRACE-CONTRADICTION: {tid} ({md.name}, {node_address}) does not truncate "
                        f"into any declared serves id {serves} — the dotted prefix IS the upward "
                        f"trace link (PLAN-ALIGNMENT-GATE)"
                    )
    return defects


# ---------------------------------------------------------------------------
# Edge-triggered defect journaling + the inbox nudge line.
# ---------------------------------------------------------------------------

def _already_journaled(node_address: str, sig_ts: str) -> bool:
    try:
        for row in ledger.load_wal():
            if (
                row.get("event") == EVENT
                and row.get("node_address") == node_address
                and sig_ts
                and sig_ts in (row.get("summary") or "")
            ):
                return True
    except Exception:  # noqa: BLE001 — an unreadable WAL must not block the refusal itself
        return True  # be conservative: do not spam if we cannot prove novelty
    return False


def journal_defects_once(node_address: str, binding: dict, sig_ts: Optional[str], defects: list) -> bool:
    """Land the typed-defect row + the inbox defect line ONCE per (node, signal ts).

    Returns True when this call journaled (first detection), False on the steady-state re-poll.
    Both writes are best-effort: a journaling hiccup never converts a refusal into a collapse.
    """
    sig_ts = sig_ts or ""
    if _already_journaled(node_address, sig_ts):
        return False
    try:
        executor.journal(
            node_address,
            event=EVENT,
            from_state=binding.get("state"),
            to_state=binding.get("state"),
            lease_epoch=binding.get("lease_epoch"),
            binding_delta={"defects": list(defects)[:10]},
            summary=(
                f"return contract REFUSED collapse for {node_address} (signal ts {sig_ts}): "
                + "; ".join(str(d)[:160] for d in list(defects)[:5])
            ),
        )
    except Exception:  # noqa: BLE001
        pass
    try:
        if ledger.RUNTIME_ROOT is not None:
            inbox = addressing.inbox_path(node_address, ledger.RUNTIME_ROOT)
            inbox.parent.mkdir(parents=True, exist_ok=True)
            line = json.dumps({
                "from": "harnessd",
                "type": "return_contract_defect",
                "message": (
                    "Your DONE sign-off was REFUSED by the return contract. Defects: "
                    + " | ".join(str(d) for d in list(defects)[:5])
                    + " — fix the named artifact(s), then re-write your .signal file (same "
                    "owner_token, fresh ts)."
                ),
                "ts": clock.now_utc(),
            })
            with inbox.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
    except Exception:  # noqa: BLE001
        pass
    return True
