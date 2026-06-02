# Run Observation File Template

*Copy into an instance as `run-NN.md` or `round-N-observation.md` and keep it live during execution. This template is task-independent.*

Use this file as the human-readable companion to the live observation-window surface: it should reflect the same active window of evidence that `probe-active` refreshes in the manifest.

This file exists for three distinct output shapes:

1. **Observation** — raw findings and methodology signal
2. **Overview** — short exec summary for orientation
3. **Narrative** — chronological story for detailed understanding

Do not collapse them into one format. The artifact is the status surface for long runs.

## Section 0 — Overview

*Target: 300-500 words. Update at least once while the run is live, then finalize at run end.*

- What the run is
- How it is being approached
- Current or final status
- The 2-3 most important things to know beyond the main story

Use tight paragraphs, not a blow-by-blow. The overview should be readable in under a minute.

## Section 0.5 — Detailed Narrative

*Target: 1000-2500 words when the run is substantial.*

Tell the chronological story:

- setup and task framing
- decomposition choice
- important incidents
- recovery or branch changes
- result

Use this section only when the run is large enough that a reader would still have important "why/how" questions after the overview.

## Section 1 — Pre-Run Intent

Write before or near spawn time.

- what you expect to happen
- what would surprise you
- what signals would count as success or failure
- what specific methodology questions this run is supposed to answer

This section exists so later surprises are visible instead of being rewritten as if they were expected.

## Section 2 — Live Observations

Update incrementally while the run is in flight. Treat this as a live dashboard for the observation window, not a post-hoc summary.

For each entry:

- timestamp
- what actually happened
- what evidence you used
- what you know vs what you infer
- any candidate methodology finding

If the run is long, do not wait until the end. The artifact is the status path.

## Section 3 — Reviewer Commentary

Capture reviewer verdicts after they return.

- what the reviewer judged
- what they praised
- what they criticized
- what changes they imply for the next round

Keep reviewer evidence separate from your own live observations.

## Section 4 — Gap Delta

What gap changed because of this run?

- what gap closed
- what gap remained open
- what new gap appeared
- whether the gap is task-specific or cross-task

Convert cross-task gaps into:

- `research/methodology-log.md` narrative lessons
- `research/ARCHITECTURE-FINDINGS.md` structured findings

## Section 5 — Next-Run Change Candidates

List only real candidates for the next round or next task:

- what would change
- why
- what evidence from this run justifies it
- whether it belongs in harness, research docs, or the next delegation packet

Do not silently absorb failures into "we learned a lot." Name the actual change candidate or explicitly say why no general change is justified.
