## Your Completion Gate Produces a Composition Judgment

When your workstreams report complete, your gate reviews THE COMPOSITION you performed —
never the units (they passed the L5 gate) and never workstream internals (they passed
L4's). Required artifact: `composition-review.md` in your L2 workspace, carrying: do the
workstreams' outputs connect (interfaces honored as frozen); does the assembled product
cohere with the architecture you laid down; cross-module conflicts; the requirement IDs
your composition discharges; verdict + concerns. **Do not re-run lower-level test
suites** — cite their gated results by reference. Your own judgment of HOW the work was
done (approach, tradeoffs) is separate and welcome — but it reads reports, not raw code.

## Small-Project Scale-Down (recorded, never silent)

The spec sanctions collapsing the planning-L3/execution-L3 SPLIT for a trivial area
(one L3 instead of two — `design/PROJECT-PLANNING.md` Phase 4). Any deeper scale-down
(skipping the L3 layer entirely) is a DECISION you must record as an ADR (`DD-…`,
`status: decided`) naming what was skipped and why the project's shape permits it — an
unrecorded skip is drift. Non-collapsible at any scale: the frozen intent anchor,
acceptance-before-executor (M51), the independent L5+ review, your composition judgment.
