# Report — `<node-address>#<seat>` → `<parent-address>`

**From:** `<node-address>#<seat>` (<level> <role>) · **To:** `<parent-address>`
**Type:** <task-complete | workstream-complete | area-complete | project-complete | review-verdict | escalation>
**Status:** <DONE | FAILED | ESCALATED> — <one line: the state of the work as the parent will experience it>

> One page. Pointer-not-payload (`operational/shared/comms-protocol.md`): the detail lives in the
> artifacts this report points at — never pasted in. Delete this line and every <angle-bracket>
> prompt when filling.

## Outcome
<One short paragraph: what exists now, where it is, what verdict/state it carries.>

## What was done
<Compressed narrative at your altitude — what, not how. Point at the artifacts that hold the
detail (`plan.md`, child reports, design docs, code paths).>

## Requirement IDs discharged
<BARE references only (`R-003.2.1`) — never re-declared trace stanzas. Every ID given in your
brief.md/acceptance.md accounted for: discharged / deferred (reason) / escalated.>

## Verification evidence
<Pointers, not payload: which suite/check ran, where its output lives, which reviewer verdict
covers it. Cite gated results by reference — do not re-run lower-level verification.>

## Deviations & concerns
<Every divergence from the brief, tagged material/cosmetic, with its requirement ID. Zero concerns
means you either didn't look or didn't think — there are always edges where judgment was required.>

## Sign-off checklist
- [ ] Every `plan.md` task checked, or explicitly deferred with reason
- [ ] Anything done beyond the brief is listed above
- [ ] Requirement IDs cited as bare references (no re-declared stanzas)
- [ ] Project log appended

*Template: `operational/shared/templates/report-template.md` (doc-system; see `design/DOC-SYSTEM.md`).*
