## Trace Discipline — Declare Once, Cite Bare

Trace stanzas (`<!-- trace: {id, serves, kind, level, node} -->`) are DECLARED exactly once, in the
artifact that owns the element they tag — `acceptance.md` (per test/rubric line), design docs (per
design element), code adjacent to the implementation. Everything downstream — `report.md`,
reviews, plans, status — REFERENCES the bare ID (`R-003.2.1`) and never re-declares the stanza:
the E2 walker treats a re-declaration in your node as a duplicate declaration and rejects it
(DUP-ID — Run-2: a builder re-declared 10 acceptance IDs in its report and was bounced at
sign-off). IDs are minted only by the level that owns the decomposition that creates them; an ID
you were GIVEN is cited, never re-minted, never renumbered. The canonical stanza syntax, the
dotted-child minting rule, and the per-level emission obligations live in
`design/PLAN-ALIGNMENT-GATE.md` (Requirements Traceability) — this block fixes only the
declare-once / cite-bare split.
