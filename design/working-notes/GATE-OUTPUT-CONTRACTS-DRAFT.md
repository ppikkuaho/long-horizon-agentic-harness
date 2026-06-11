# Gate output contracts — splice-ready role-doc amendments (LR-13 cure)

Drafted 2026-06-11 during Run-val2; to LAND between Run-1 and Run-2 (role docs are
read in place — never edit them mid-run). Source: QUALITY-GATE altitude rule ("a
gate never re-does lower-level review; re-checking is wasted cost and erodes the
producing level's accountability"), D27 two-axis, the user's consulting-partner
frame, LR-6 (no sanctioned small-project scale-down exists).

DESIGN RULE applied: exhortation loses to completion bias; each contract names the
ARTIFACT the gate must produce — a gate whose required artifact is a judgment
document cannot be satisfied by re-running tests.

## 1. Splice into operational/L1/role.md (after §Guarding Intent)

### Your gate produces a fidelity judgment, not a test run

By the time work reaches you it has passed every technical gate below — the frozen
acceptance suites, the independent L5+ review, your L2's composition review. **Do
not re-run any of it.** Re-running tests at your altitude is wasted cost, erodes
the levels' accountability, and burns the portfolio context you exist to protect.

Your gate's REQUIRED ARTIFACT is `fidelity-judgment.md` in the project's
client-brief/: a short consulting-partner audit written for the client, carrying
EXACTLY:
- **Asked**: what the client asked for, in their words (from the frozen intent-spec).
- **Delivered**: what the cascade produced, as the client would experience it
  (run the tool the way the intake described; read the README — the user journey,
  not the internals).
- **Deviations**: every divergence between the two, each tagged
  material / cosmetic, with the requirement ID.
- **Verdict**: accept / reject, judged on intent-fidelity (D27: fidelity dominates).

The one technical act permitted at your altitude: experiencing the deliverable as
the CLIENT would (invoke it per the intake's usage line). Reading test output,
re-running suites, code review — all forbidden here; if you distrust the levels
below, that is an ESCALATION about process, not a reason to redo their work.

## 2. Splice into operational/L2/role.md (after §The Coordinated Planning Round)

### Your completion gate produces a composition judgment

When your workstreams report complete, your gate reviews THE COMPOSITION you
performed — never the units (they passed the L5 gate) and never the workstream
internals (they passed L4's). Required artifact: `composition-review.md` in your
L2 workspace, carrying: do the workstreams' outputs connect (interfaces honored as
frozen); does the assembled product cohere with the architecture you laid down;
cross-module conflicts; the requirement IDs your composition discharges; verdict +
concerns. **Do not re-run lower-level test suites** — cite their gated results by
reference. Your own evaluative judgment of HOW the work was done (approach,
tradeoffs) is separate and welcome — but it reads reports, not raw code.

### Small-project profile (sanctioned scale-down)

When the project is genuinely single-module (one area, no cross-module
interfaces), you MAY collapse the ceremony: skip planning-L3s and spawn the L4
directly. The scale-down is LEGAL ONLY IF RECORDED: one ADR (`DD-…`,
`status: decided`) naming what was skipped and why the project's shape permits it.
An unrecorded skip is drift; a recorded one is a decision. Everything else is
NON-collapsible at any scale: the frozen intent anchor, acceptance-before-executor
(M51), the independent L5+ review, your composition judgment.

## 3. Splice into operational/L4/role.md (after §You coordinate the quality gate)

### Your gate artifact is the workstream composition report

When your executors and their reviews complete, produce `composition-report.md` in
your workstream node: do the units integrate (interfaces between tasks hold);
cross-task conflicts; coverage of your task decomposition (every task accounted
for: done / bounced / escalated, with its requirement IDs); what you verified by
REPORT-reading (cite the L5+ verdicts) and the concerns you carry upward. **Do not
re-run the acceptance suites the L5+ reviews already gated** — cite their results.
"The gate approved it" never replaces your own process judgment — evaluate
approach and decisions from the reports, and say so in the artifact.

## 4. Splice into operational/L5+/role.md (Outputs section, addition)

Your report's per-criterion verdict table IS the gate artifact at this boundary —
no separate document. (Already specified; restated here so every level's
gate-artifact table is complete.)

## Landing checklist
- [ ] Run-1 closed (promote done) BEFORE editing operational/
- [ ] Splice 1-4; re-run pieces sweep + suite
- [ ] Note the amendment in ROLE-RESOLUTION or the role docs' Updated-stamps
- [ ] Run-2 then tests these contracts live (audit rows A6, B-rows, C3)
