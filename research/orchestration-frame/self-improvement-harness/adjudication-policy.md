# Adjudication Policy

This file tells the orchestrator how to act on verdicts.

## Inputs

Per round, the orchestrator receives:

- `builder-output.md`
- `reviewer-1-verdict.md`
- `reviewer-2-verdict.md` when Reviewer 1 passes

The orchestrator reads the YAML frontmatter first and treats it as authoritative.

## Adjudication rules

### After Reviewer 1

If Reviewer 1 emits `continue`:

- record the verdict
- set manifest state to `reviewer_1_continue`
- open the next round
- carry forward all `required_changes`
- preserve any unresolved regression risks in the next brief

If Reviewer 1 emits `pass`:

- record the verdict
- set manifest state to `reviewer_1_pass`
- send the same artifact set to Reviewer 2

### After Reviewer 2

If Reviewer 2 emits `continue`:

- record the verdict
- set manifest state to `reviewer_2_continue`
- open the next round
- carry forward all `required_changes` and `suggested_changes`
- carry forward the reported highest remaining severity into the next brief

If Reviewer 2 emits `stop`:

- record the verdict
- set manifest state to `stopped`
- close the loop

## Required next-round brief contents

When opening a new round, the orchestrator must restate:

- which reviewer findings are mandatory
- which artifacts are in scope
- what regressions must not recur
- what unresolved issues remain highest severity

## Regression handling

If a reviewer identifies regressions introduced by the builder:

- regressions are treated as mandatory changes for the next round
- if a regression is `critical` or `major`, the next round brief must name it before any new optimization work

## Source-of-truth rule

The authoritative round state is:

1. `manifest.yaml`
2. `run-ledger.jsonl`
3. reviewer verdict files

Narrative files are explanatory, not authoritative.

## Invalid verdict handling

If a verdict file is missing required structured fields:

- the orchestrator does not advance state based on it
- the round stays pending for that reviewer
- the orchestrator requests a corrected verdict from a fresh independent reviewer session if needed
