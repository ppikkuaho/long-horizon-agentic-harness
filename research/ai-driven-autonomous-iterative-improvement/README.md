# AI-Driven Autonomous Iterative Improvement

Investigation into how multiple LLMs can be orchestrated to autonomously develop, test, evaluate, and improve methodologies and artifacts through structured iteration cycles.

## Origin

Emerged from the InternalAI 2.0 mental model methodology development (2026-04-08). A 7-phase multi-model cycle (propose → test → evaluate → synthesize → test → identify issues → fix) produced a validated methodology from zero in one session. The process used Claude, Codex, and Gemini in parallel at key phases, with each model contributing independent proposals, independent test results, and unique innovations that survived into the final synthesis.

Observations that motivated this investigation:
- 3 models independently finding the same data patterns is the strongest available validation signal
- Each model consistently contributes innovations the others don't
- The cost of parallel execution is ~1.2-1.3x over single-model (Codex and Gemini draw from separate, non-rolling budgets — unused capacity is lost)
- The synthesized result was consistently richer than any single model's proposal
- The process is reusable across different design problems (tested on: universal domain frameworks, digital twin section lists, mental model extraction methodology)

## Current Evidence

### The multi-model parallel development cycle

Documented in `projects/internal-ai-2.0/design/tool-design-learnings.md` (section: "Multi-model parallel methodology development — the shape"). Contains: the 10-step process, cost structure, what each phase produces, 3 project applications with convergence/divergence data, and observed patterns.

### Key observed properties

- **Convergence = robustness signal.** When N models independently arrive at the same architecture or the same findings from the same data, the result is not dependent on any single model's biases. This is the strongest validation available without human expert review.
- **Divergence = design choice map.** Where models disagree, the disagreement maps the space of reasonable design choices. This is useful input for practitioner decision-making.
- **Per-model innovation.** Each model brings ideas from different training data and analytical tendencies. The synthesis draws from all N, producing results richer than any individual.
- **Convergence strength correlates with domain establishment.** Well-established domains (corporate profiling) produce near-unanimous convergence. Less-established domains (civil society profiling, novel methodology design) produce more divergence.

## Future Exploration Directions

### 1. Mutation prompting / genetic approach

Instead of asking each model to propose a solution from scratch, start from a base solution and ask each model to MUTATE it — introduce specific variations. This parallels genetic algorithms:
- **Base solution** = the current best methodology
- **Mutations** = each model proposes N variations (change one step, restructure one section, add one dimension, remove one constraint)
- **Testing** = each mutation is tested on real data
- **Selection** = compare mutation results against the base; keep improvements, discard regressions
- **Recombination** = combine successful mutations from different models into the next generation

This could be more efficient than the current approach (which asks each model to design from scratch) because mutations are smaller, more testable, and the improvement signal is clearer (delta from base, not absolute quality).

### 2. Independent parallel solo development vs council approach

Compare different orchestration configurations systematically:

**Configuration A: Single model, solo development.**
One model does the full cycle: propose → test → evaluate → fix → iterate. N iterations, single perspective.

**Configuration B: LLM council, parallel proposals.**
N models each propose independently. Synthesis + test. Current approach.

**Configuration C: Independent parallel solo development.**
Each of N models runs its OWN full development cycle independently (propose → test → fix → iterate, multiple rounds). At the end, compare the N independently-developed final products. Each model has had multiple iterations to refine its own approach. This tests whether iterative self-improvement within one model produces better results than one-shot proposals compared across models.

**Configuration D: Hybrid — solo development + cross-pollination.**
Each model develops independently for K rounds, then results are shared across models. Each model continues developing but now aware of what the others produced. Tests whether cross-pollination mid-cycle improves the final results.

### 3. Systematic mapping

Run multiple configurations (10+ tests per configuration) across different design problems to map:
- Which configuration produces the best results for which type of problem?
- Where does multi-model add value vs where is single-model sufficient?
- What is the optimal number of models? (Is 3 better than 2? Is 4 better than 3?)
- What is the optimal number of iterations per model before synthesis?
- Does mutation prompting outperform from-scratch proposals?
- Does the advantage of multi-model scale with problem complexity?
- How does convergence/divergence change across problem types?

The goal: a validated map of which orchestration approach to use for which type of design problem, with empirical evidence rather than intuition.

### 4. Shared-workspace research team pattern

Instead of isolated parallel work with synthesis at the end, agents share a workspace with specific access rules:
- **Read:** all agents can read all files in the shared workspace (including files created by other agents)
- **Write:** agents can CREATE new files but NOT edit existing ones
- **Accumulation:** each agent adds its findings, and subsequent agents build on what's already there

This creates a dynamic more like a research team: Agent A writes initial findings. Agent B reads A's findings, does its own work, writes a file that extends or challenges A's conclusions. Agent C reads both A and B, synthesizes or explores a gap neither covered. The shared workspace accumulates collective knowledge without any single agent being able to overwrite or corrupt another's work.

Potential applications:
- **Golden set development:** Each agent explores a different angle of a domain, reads what others found, fills gaps others missed
- **Change factor identification:** Multiple agents scan the same domain from different perspectives, building on each other's coverage
- **Literature review:** Each agent researches different sources, reads others' summaries, produces a cumulative synthesis

The append-only constraint is key: it prevents agents from collapsing toward consensus by editing each other's work. Disagreement is preserved. The synthesis happens from reading the full accumulated workspace, not from convergent editing.

This pattern differs from the parallel-then-synthesize approach (where agents work in isolation and a parent merges results). The research team pattern has agents building ON each other's work incrementally. The tradeoff: richer cross-pollination but potential anchoring (later agents may anchor to earlier agents' framings).

Shape is preliminary — needs prototyping to understand the dynamics. The access control mechanism (read all, append only) may need to be enforced at the filesystem or agent-delegation level.

### 5. Evaluation methodology for comparing configurations

To compare configurations rigorously, we need:
- A set of standardized design problems (diverse enough to reveal configuration-dependent strengths)
- A consistent evaluation rubric (applied by an independent evaluator, not by the models that produced the solutions)
- Multiple runs per configuration (to measure variance, not just single-run quality)
- Controlled variables (same prompt, same data, same evaluation — only the orchestration differs)

This itself is a methodology design problem that could be bootstrapped using the multi-model approach.

## Relationship to Other Work

- **InternalAI 2.0 tool design learnings** — `projects/internal-ai-2.0/design/tool-design-learnings.md` contains the empirical evidence from 3 applications of the multi-model pattern
- **Agentic design patterns** — `projects/ai-architecture/design/agentic-design/` contains related work on multi-agent skill building
- **Multi-model evaluation via MCP** — `projects/internal-ai-2.0/design/tool-design-learnings.md` Part 5 documents the operational pattern for running Claude + Codex + Gemini in parallel via MCP

## Status

Investigation file opened 2026-04-08. Current evidence is from 3 InternalAI applications. Future exploration directions documented but not yet tested. The systematic mapping (direction #3) is the highest-value next step — it would move from anecdotal evidence ("it worked well 3 times") to systematic understanding ("here's when it works, here's when it doesn't, here's why").

---

*Created: 2026-04-08*
