# Stop Policy

The stop condition is reviewer-governed, not builder-governed.

## Severity scale

- `critical`
- `major`
- `medium`
- `small`
- `minor`

The ordering is:

`critical > major > medium > small > minor`

## Reviewer 1 rule

Reviewer 1 may emit:

- `continue`
- `pass`

Reviewer 1 may emit `pass` only if no remaining adherence issue is `critical`, `major`, or `medium`.

Reviewer 1 never stops the loop.

## Reviewer 2 rule

Reviewer 2 may emit:

- `continue`
- `stop`

Reviewer 2 may emit `stop` only if the highest remaining improvement severity is `small` or `minor`.

Equivalently:

- if any `critical`, `major`, or `medium` improvement remains, Reviewer 2 must emit `continue`
- if only `small` or `minor` improvements remain, Reviewer 2 may emit `stop`

## Required Reviewer 2 statement

Reviewer 2 must explicitly state:

- the highest remaining severity
- whether any further improvements still worth doing are `critical`, `major`, `medium`, `small`, or `minor`
- why the loop should continue or stop

## Structured fields

Reviewer verdict files must include YAML frontmatter.

Required fields for Reviewer 1:

- `role: reviewer_1`
- `iteration`
- `verdict`
- `adherence_status`
- `highest_remaining_severity`
- `required_changes`
- `regression_risks`
- `independence_confirmed`

Required fields for Reviewer 2:

- `role: reviewer_2`
- `iteration`
- `verdict`
- `highest_remaining_severity`
- `suggested_changes`
- `independence_confirmed`

## Tie-breaking rule

If reviewer language and structured fields disagree, the structured fields win.

If multiple reviewers disagree, the more severe continuation judgment wins.

## No builder self-stop

The builder may suggest that the work looks strong, but that suggestion has no stopping force.
