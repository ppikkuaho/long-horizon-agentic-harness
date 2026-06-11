#!/usr/bin/env python3
"""Land the gate output contracts (GATE-OUTPUT-CONTRACTS-DRAFT.md) into the role docs.

Run ONLY between runs (role docs are read in place by live agents). Inserts each
contract block immediately BEFORE the '## Visibility Scope (F34)' heading of the
three role docs, and appends the gate-artifact note to L5+'s Outputs. Idempotent:
skips a doc that already carries its block marker.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
ANCHOR = "## Visibility Scope (F34)"
MARK = "<!-- gate-output-contract (LR-13) -->"

L1_BLOCK = MARK + """
## Your Gate Produces a Fidelity Judgment, Not a Test Run

By the time work reaches you it has passed every technical gate below — the frozen
acceptance suites, the independent L5+ review, your L2's composition review. **Do not
re-run any of it.** Re-running tests at your altitude is wasted cost, erodes the levels'
accountability, and burns the portfolio context you exist to protect (the altitude rule,
`design/QUALITY-GATE.md`: "a gate never re-does lower-level review").

Your gate's REQUIRED ARTIFACT is `fidelity-judgment.md` in the project's `client-brief/`:
a short consulting-partner audit written for the client, carrying exactly —

- **Asked**: what the client asked for, in their words (from the frozen intent-spec).
- **Delivered**: what the cascade produced, as the client would experience it — invoke the
  tool the way the intake described, read the README; the user journey, not the internals.
- **Deviations**: every divergence between the two, tagged material/cosmetic, with the
  requirement ID.
- **Verdict**: accept / reject, judged on intent-fidelity (D27: fidelity dominates).

The ONE technical act permitted at your altitude is experiencing the deliverable as the
client would. Reading test output, re-running suites, code review — all belong to the
levels below; if you distrust their gates, that is an ESCALATION about process, never a
reason to redo their work.

"""

L2_BLOCK = MARK + """
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

"""

L4_BLOCK = MARK + """
## Your Gate Artifact Is the Workstream Composition Report

When your executors and their reviews complete, produce `composition-report.md` in your
workstream node: do the units integrate (interfaces between tasks hold); cross-task
conflicts; coverage of your decomposition (every task accounted for — done / bounced /
escalated, with its requirement IDs); what you verified by REPORT-reading (cite the L5+
verdicts); the concerns you carry upward. **Do not re-run the acceptance suites the L5+
reviews already gated** — cite their results. "The gate approved it" never replaces your
own process judgment — evaluate approach and decisions from the reports, and say so in
the artifact.

"""


def splice(rel, block):
    p = ROOT / rel
    src = p.read_text(encoding="utf-8")
    if MARK in src:
        print(f"{rel}: already spliced — skipped")
        return
    if ANCHOR not in src:
        sys.exit(f"{rel}: anchor missing — aborting (no partial landing)")
    p.write_text(src.replace(ANCHOR, block + ANCHOR, 1), encoding="utf-8")
    print(f"{rel}: spliced")


def main():
    splice("operational/L1/role.md", L1_BLOCK)
    splice("operational/L2/role.md", L2_BLOCK)
    splice("operational/L4/role.md", L4_BLOCK)
    print("done — run the pieces sweep + suite, then stamp the Updated lines")


if __name__ == "__main__":
    main()
