# Compute/Time-Bounded Agent Tasks

*Created: 2026-03-23*
*Status: Idea — not yet designed*
*Relates to: ARCHITECTURE.md §4 (Invocation), §5 (Failure and Timeout)*

## The Problem

No universal mechanism for agent task stop conditions. Current failure modes:
- Agent gives up too early on hard problems
- Agent asks "should I keep going?" — interrupts the delegating level
- Agent runs unbounded on impossible problems
- Spawning level can't express "this is worth significant effort" vs "quick attempt"

## Proposed Solution

Two budget dimensions, usable independently or combined:

### 1. Wall-Clock Time Budget

Agent receives a time allocation. As long as time remains, keep trying — different approaches, strategies, pivots. On expiry, wrap up with best result.

### 2. Compute Budget

Agent receives a token/usage allocation (or iteration count). Spend it however is most effective. On exhaustion, stop.

### Combined Mode

"30 minutes OR 50k tokens, whichever comes first." Handles both fast-burning and slow-burning edge cases.

## Why This Matters for the Architecture

### Invocation Integration (§4)

Budget becomes part of the brief structure:

```
1. Identity
2. Bootstrap (soul + loadset)
3. Workspace
4. Brief (the actual task)
5. Reporting
6. Budget ← NEW: time and/or compute allocation
```

The spawning level sets the budget as part of delegation. Budget size is a judgment call that signals priority and expected difficulty.

### Timeout/Failure Design (§5)

Current design: "If a delegated task produces no result within an expected timeframe, the spawning level sends a status inquiry."

Budgets make this more precise. Instead of the parent guessing timeframes and polling, the agent self-manages within its budget. The timeout becomes the budget itself — no dead-man's switch needed for normal operation. Dead-man's switch only needed for agent crashes (no heartbeat), not for long-running tasks.

### Escalation Integration (§2)

Budget extension as a new escalation type:

```
---
type: budget-extension
from: [agent-id]
re: [task]
urgency: needs-attention
---
Budget: 70% consumed
Progress: [summary of what's been achieved]
Remaining work: [what's left]
Request: [additional budget amount and justification]
```

Parent evaluates: is the progress worth more investment? This is a natural resource allocation decision — exactly what the parent level is for.

### Agent Behavior Shift

With a budget, the agent's objective changes from "complete the task" to "use this budget effectively." This is a meaningful cognitive reframe:

- Early in the budget: explore broadly, try the obvious approach
- Mid-budget: evaluate progress, decide whether to refine or pivot
- Late budget: converge on best available result, prepare handoff report
- Budget exhausted: stop, report what was achieved and what remains

The agent can reason about its own resource allocation — a form of meta-cognition that emerges naturally from the budget constraint.

## Design Questions

1. **Budget format**: Minutes? Tokens? Iterations? All three as options?
2. **Default budgets**: Should each level have default budgets, overridable per task?
3. **Budget visibility**: Should the agent see exact remaining budget, or just "low/medium/high"?
4. **Partial completion protocol**: How should an agent report "budget exhausted, task 60% complete"?
5. **Budget inheritance**: If L2 gets a budget, does it subdivide across L3s? Or are budgets set independently per level?
6. **Implementation**: What's the mechanism? Timer process? Token counter in the spawn script? Agent self-monitoring?

## Connection to Existing Ideas

- **Variable depth (§4)**: Budget could inform depth decisions. Small budget → direct L4. Large budget → full L2-L3-L4 stack.
- **Resource awareness (§5)**: Budgets are a more granular version of the "resource awareness" concept already in the architecture.
- **Event-driven reporting (§2)**: Budget milestones (50%, 75%, 90%) could be reportable events.

---

*Also documented in: `dev/ideas/lifeos.md` under `2026-03-23 idea: compute-time-bounded-tasks`*
*Also indexed in: `dev/ideas/INDEX.md`*
