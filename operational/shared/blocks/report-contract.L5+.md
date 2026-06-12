## The Report Contract — `report.md` Required at DONE, Every Level

Your `report.md` is the parent-facing deliverable, required at DONE at EVERY level — the root
included. The runtime return-contract gate (E2, `harnessd/return_contract.py`) REFUSES a DONE
sign-off whose node lacks a non-empty `report.md`: the signal stays on disk, a typed defect lands
in your inbox, and you must fix and re-signal. Do not discover this at sign-off — the report is
work, not paperwork; write it before your terminal signal.

- **Follow the L5+ template:** `operational/shared/templates/report-template.L5+.md` — the
  registered reviewer adaptation of the shared report template (typed header, one page,
  pointer-not-payload, `comms-protocol.md`). Your per-criterion verdict table IS the gate
  artifact (M52); the verdict is restated in your terminal signal's `evidence.notes`.
- **Cite the requirement IDs you VERIFIED as BARE references** (`R-003.2.1`) — a reviewer does
  not discharge requirements, it verifies them; the IDs come from the same frozen
  `brief.md`/`acceptance.md` the executor was held to. Never re-declare trace stanzas (see the
  trace-discipline block). The E2 gate enforces the citation mechanically for L5-class seats —
  YOURS INCLUDED: both Run-2 L5+ reviewers tripped this check because no reviewer-facing doc
  carried the duty. A review naming no ID it verified is unverifiable itself.
- **Account for every given criterion:** PASS, or FAIL with the named defect (file, behavior,
  violated requirement ID) — a vague bounce ("needs polish") is worse than no bounce.
