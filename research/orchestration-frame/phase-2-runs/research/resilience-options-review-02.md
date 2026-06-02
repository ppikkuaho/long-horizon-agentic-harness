# Resilience Options Review 02

Current baseline after the latest live hardening: the mousepad loop now has a persisted manifest + ledger, transition validation, compare-and-set transition guards, a watchdog evidence block, a supervisor-driven `probe-active` command that checkpoints the active runtime observation window into durable state, and a spawn-slot claim pattern before actor creation.

The question here is what stronger structural options are worth considering next if the goal is robustness and resilience, not just one successful live run.

## Comparison

| Option | Resilience strengths | Main weakness | Cost | Recommendation |
| --- | --- | --- | --- | --- |
| 1. Supervisor-driven probe checkpoints | Durable observation, resumable evidence, low conceptual churn, works with the existing manifest/ledger model. | Still depends on something choosing to run the probe. Semantic visibility is only as good as the underlying observe surface. | Low | Keep. This is the correct immediate layer and is now live. |
| 2. External poller / lightweight control-loop runner | Removes dependence on a foreground operator for observation cadence and straightforward auto-advance cases. Natural place to run `probe-active`, validate, and call `transition`. | Introduces another runtime process to supervise and debug. If the state model is weak, the poller just automates weak decisions faster. | Medium | Best next structural upgrade once the transition predicates are trusted. |
| 3. Backend semantic tap | Pulls richer semantic evidence from Claude/Codex traces than heartbeat/progress alone, reducing false "healthy but opaque" runs. | Backend-specific, more brittle than generic observe, and may vary with transcript format changes. | Medium | Prototype next for high-value loops where semantic opacity is the limiting factor. |
| 4. Durable parent-child mailbox | Gives long-running parents and children a real bidirectional coordination surface with generation guards, resumable requests, and repair-friendly state. Much stronger than implicit notifications. | Requires protocol design and ownership rules; more moving parts than the current one-shot reviewer chain. | Medium to high | High-value if retained-mode coordinators or nested work-scoped coordination become common. |
| 5. Step journal / action receipts | Best path to measuring actual learning density and decomposition rigor. Makes it easier to distinguish busy work from meaningful advancement. | Requires child-runtime integration or disciplined emitted checkpoints. Easy to overbuild too early. | High | Defer until the control-loop surface and mailbox semantics are clearer. |
| 6. Timeout-first enforcement | Simple to explain and easy to implement. | Too rigid, prone to false kills, and mismatched to the actual failure modes seen so far. | Low | Do not lead with this. Use suspicion and evidence, not timer-triggered termination. |

## Decision

Adopted now:

- keep the probe-checkpoint model as the baseline observability layer

Strongest next options:

- add an external poller that runs probe/validate/transition on a safe cadence
- prototype a backend semantic tap for richer observation windows
- design a durable mailbox before expanding retained-mode or nested-agent coordination further

## Why this is the right order

The live problem is still not "we have no state." It is "we do not yet have enough structural control over observation, recovery, and coordination." The probe fixes the most immediate gap with minimal churn. A poller then removes operator dependence. Semantic taps and mailboxes are the next meaningful upgrades because they attack the two remaining blind spots directly:

- semantic opacity
- cross-turn / cross-agent coordination durability

Timeouts alone do neither.
