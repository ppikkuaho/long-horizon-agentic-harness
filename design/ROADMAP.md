# AI Architecture — Roadmap

Horizon-organized map of all outstanding design work. This is navigation, not a backlog — each item is a one-liner with a pointer to where the full thinking lives. Detail stays in place.

*Last triaged: 2026-03-26*

---

## V1 — Required for the system to work

> Key decisions 2026-03-25/26: this harness and a separate personal-assistant system are separate systems. Review Department is a full parallel function. Cognitive config not loaded for agents (drift risk). Conversational mode = terminal switching. Acceptance tests written by L3, not L4. Review Department must interact with running products. Every post-V1 feature earns its place through observed need. 5-level hierarchy (L3 Program Manager added between L2 and old L3). Old L3 → L4, old L4 → L5.

| # | Item | Detail location |
|---|------|-----------------|
| 1 | ~~L1 portfolio documentation schema~~ | WORKSPACE-SCHEMA.md (L1 Portfolio Workspace section) |
| 2 | ~~L1-L4 role docs~~ (operational configs still TODO) | operational/L1/role.md through operational/L4/role.md, ARCHITECTURE.md §1 |
| 4 | User profile document | NOTES.md (TODO: User Profile Document) |
| 6 | ~~Connect generative skeleton to architecture — L2's planning approach~~ *(resolved/evolved)* | Evolved from generative skeleton to professional services planning process. See PROJECT-PLANNING.md. |
| 7 | Benchmarking — how to measure if the system works better than flat dispatch | ARCHITECTURE.md §Open Design Work (#18) |
| 19 | Review Department — full parallel organizational function design *(deferred to post-V1)* | Conceptual brief exists (QUALITY-GATE.md); full design pass needed: agent identity, role, operational config, interfaces, lifecycle, coordinator + reviewer agent types. See NOTES.md. Still important, but not vital to starting work on the system — some things will be spotted faster once the system is running. |
| 25 | Review Department interacts with running products | Browser automation / Playwright MCP required for Review Department. Evaluates by using, not just reading code. Without this, review is theater. See NOTES.md (Anthropic harness design insights). |
| 26 | L5 enforcement stack | Four layers: SWE handbook (spawn) → enriched briefs from L4 (acceptance tests + structural guidance) → automated tools mandatory (linter/formatter/type checker) → Review Department (downstream). See NOTES.md. |
| 27 | Tool manifest per task type | For L5 (was L4). All code: file editing, terminal, git, LSP, test runner, linter, formatter, type checker. Frontend adds: browser, dev server. Backend adds: curl, database CLI. Provided at spawn. See operational/L5/config.md. |
| 28 | Internal Affairs — development home base | IMPROVEMENT-WORKSPACE.md created 2026-03-25. May extend for V1. |
| 29 | 5-level architecture restructuring — redesign ARCHITECTURE.md, all soul/role/config docs, COMMUNICATION.md, WORKSPACE-SCHEMA.md, QUALITY-GATE.md, OBSERVABILITY.md, GUI-DESIGN.md, DESIGN-PRINCIPLES.md for 5 levels | See NOTES.md (5-Level Architecture Redesign). |
| 30 | ~~L3 Module Designer — soul, role, config for new level~~ | Created. See operational/L3/. |
| 31 | Planning/execution phase split — planning L3 templates, plan file format, Phase A/B process | See NOTES.md. |

---

## Deferred (V1.1+)

| # | Item | Detail location |
|---|------|-----------------|
| 5 | Time awareness — can L2 schedule and pace work across days? | ARCHITECTURE.md §Open Design Work (#13), DESIGN-PRINCIPLES.md |
| 12 | Multi-account subscription orchestration | personal idea notes (item #4) |
| 14 | L1 pre-work research team | personal idea notes (item #2) |
| 15 | Discussive L1 branch — branching discussion pattern | personal idea notes (item #3) |
| 16 | Seeds not instructions — formalize as design principle | NOTES.md (Design Note: Seeds, Not Instructions) |
| 17 | Design principles as loadable skill — navigator pattern with detail files | NOTES.md (Design Note: Dynamic Cognitive Configuration, design principles section) |
| 18 | CULTURE.md — organizational environment/values document | NOTES.md (Idea: CULTURE.md) |

---

## Post-V1 — Designed or partially designed, extends V1

### Existing design work

| # | Item | Detail location |
|---|------|-----------------|
| 1 | Multiple L1 design — personal/life L1, Internal Affairs L1 | ARCHITECTURE.md §6 |
| 2 | Sibling communication — lateral agent communication across projects | NOTES.md (Future Exploration: Sibling Communication) |
| 3 | Lateral depth / within-level decomposition — cognitive director pattern | NOTES.md (Design Note: Lateral Depth) |
| 4 | LLM self-managed context — active context window management | NOTES.md (Research Direction: LLM Self-Managed Context) |
| 5 | Separate verifier agent pattern | personal idea notes (item #9) |
| 6 | Cognitive config meta-dimensions (iterative portion) | a design-principles reference (not published) |
| 7 | L2 decomposition depth placement — where the guideline lives | NOTES.md (Design Note: L2 Decomposition Depth) |
| 8 | Proof-of-access compliance gates for alignment/review enforcement | NOTES.md (Future Exploration: Proof-of-Access Gates as Compliance Enforcement for L1-L5) |

### New from 2026-03-26 design session — shapes for future releases

| # | Item | Shape | Detail location |
|---|------|-------|-----------------|
| 9 | Structural scaffolding — encoding handbook principles as shapes L5 fills in | L4 lateral agent creates per-task scaffolds: function signatures, comment placeholders at decision points, error handling patterns, interface definitions. LLMs fill shapes faithfully; blank pages produce mediocre structure. Handbook principles become structural containers, not advice to remember. | NOTES.md (Upstream Mitigation Strategy) |
| 10 | Execute-review pairs at L5 level | One L5 executes, separate L5 reviews against handbook/acceptance criteria. Same pattern as S+ rubric loop from agentic design skill building. Catches what self-verification misses. Add when observation shows self-verification quality is insufficient. | NOTES.md (Testing Architecture) |
| 11 | Review intensity scaling | Parent levels set review depth. L1 proposes baseline with user (with override option). L1 defines for L2, L2 for L3, etc. Scales with task complexity and risk. Not every L5 output needs the same review depth. | NOTES.md (Anthropic harness design insights) |
| 12 | L4 lateral: dedicated acceptance test writer | Moves acceptance test writing from L4 directly to a lateral team member. Keeps L4's context clean for coordination. Same structural principle: writer and tester are separate. | NOTES.md (Testing Architecture, Integration Engineer) |
| 13 | L3/L4 lateral: conventions and interface contracts | L2 spawns lateral to produce granular conventions.md. L4 spawns lateral to define interface contracts between tasks. Offloads analytical work from their context windows. | NOTES.md (Upstream Mitigation Strategy) |
| 14 | Metacognition schemas per level — mental models, skills, rubrics | Moved from V1. Current configs have self-monitoring baked in. Explore whether formal schemas add value beyond what the configs already provide. | ARCHITECTURE.md §Open Design Work (#12) |
| 15 | Dynamic cognitive configuration for agents | Moved from V1. Cognitive config causes drift in long sessions. Explore selective use for specific task types where benefit outweighs drift risk. | NOTES.md (Design Note: Dynamic Cognitive Configuration, Design Note: Cognitive Config Not Loaded for L1-L5) |
| 16 | Plan → Execute → Review operating cycle | Fundamental redesign of the system's orchestration model. Every non-trivial unit of work: planned separately, executed separately, reviewed separately. Affects all levels — skeleton resolution, task decomposition, brief writing, execution. Different kinds of thinking (P3) collapsed into one pass degrades all three. | NOTES.md (Plan → Execute → Review — System Operating Cycle Redesign) |
| 17 | Dual L2s for complex projects | Two L2 peers with different expertise co-producing concept design. Product/design L2 + technical architecture L2. Peers, not lead + subordinate. L1 mediates divergence. | NOTES.md |

---

## Completed

| Item | Detail location |
|------|-----------------|
| L4-CONFIG.md — operational config for L4 | Was L4 (now L5). Config needs renumbering. Second draft 2026-03-26. Thin config (stance + self-monitoring), practices in SWE handbook. |
| SWE practices handbook / skill catalogue for L5 compiled | operational/L5/swe-handbook.md. Compiled from Beck, Clean Code, Ousterhout, Google. |
| Alignment checkpoints — built into L1, L2, L3, L4 configs | Pre-execution sign-off at L2-L3 boundary. Periodic alignment checks at phase boundaries, child-initiated on schedule, parent evaluates against spec. Checkpoints placed during planning while understanding is freshest. |
| Testing architecture — acceptance tests at L4, unit tests at L5 | L4 writes acceptance tests (delivered with brief). L5 makes them pass + writes unit tests. Writer and tester structurally separate. |
| Conversational mode open questions — mechanics for user bypass | Resolved 2026-03-25. Each agent is a terminal session. User lists instances via status board, opens the terminal. No special protocol needed. |
| User intentionality assumption — operational config | Resolved 2026-03-25. Soul documents plant this seed sufficiently. No additional config needed. |
| Steering preferences integration — behavioral specs into level configs | Resolved 2026-03-25. Preferences extracted in a separate personal-assistant system's context. Not applicable to L1-L5. Reference material only. |
| Escalation/leadership skills for agent managers | Resolved 2026-03-25. Workspace write + inbox message + config guidance. Not a separate skill. |
| Internal Affairs — development home base | IMPROVEMENT-WORKSPACE.md created 2026-03-25. |
| L3-CONFIG.md — operational config for L3 | First draft created 2026-03-25. |
| Invocation protocol + spawn mechanism | ARCHITECTURE.md §4 |
| Concurrency mechanics — instance caps, tracking, throttling | ARCHITECTURE.md §5 |
| Agent lifecycle — persistence, message routing, context management | ARCHITECTURE.md §5 |
| Timeout and failure design — values, cascading prevention, circuit breakers | ARCHITECTURE.md §5 |
| Agent state transitions — Active/Parked/Waiting | ARCHITECTURE.md §5, NOTES.md (Agent Awareness) |
| Git integration — branch strategy, PR-as-review, merge conflict protocol | GIT-INTEGRATION.md |
| GUI — user-facing spatial interface over agent infrastructure | GUI-DESIGN.md |
| Audit trace / observability — narrative timeline, traceability chain, visualization | OBSERVABILITY.md |
| Quality gate system — review departments at each level boundary | QUALITY-GATE.md |
| Citation ledger + incident log — persistent quality tracking | QUALITY-GATE.md |
| Pre-submission checklist — quality at the source for each level | QUALITY-GATE.md |
| Communication protocol — inbox, DM, reporting, escalation | COMMUNICATION.md |
| Workspace schema — folder structure, document types, edit policies | WORKSPACE-SCHEMA.md |
| Design principles P4, P17, P18, P19 | DESIGN-PRINCIPLES.md |
| 5-Level architecture design — all 10 design notes recorded 2026-03-26 | See NOTES.md (5-Level Architecture Redesign). |
| Workflow diagram — sequence-style swimlane, end-to-end process flow | Working reference diagram (not published). 27 steps across 6 lanes (User, L1-L5, Review). Monochrome, cross-lane arrows, 3 gates, alignment checkpoints. |
| Cognitive config injection fix — restored depth demand, forward-looking module eval | Per-turn cognitive-config injection. 4-step per-turn procedure. All S on 8-criterion rubric. |
| Planning process / generative skeleton — Evolved from decision-point mapping methodology to professional services planning process. Derived from architecture, consulting, and SWE parallels. | PROJECT-PLANNING.md |

---

## Exploration — Research, evaluate, maybe use

### Research directions

| # | Item | Detail location |
|---|------|-----------------|
| 1 | Org design literature survey | NOTES.md (Research Direction: Organizational Design Literature) |
| 2 | ReAct vs Plan-and-Execute architecture patterns | personal idea notes (item #11) |
| 3 | Treat AI context like Unix files (paper) | personal idea notes (item #8) |

### Infrastructure and tooling ideas

| # | Item | Detail location |
|---|------|-----------------|
| 4 | Manus CLI pattern — single tool vs function calling | personal idea notes (item #5) |
| 5 | Backend primitives for Claude Code agents (6 primitives) | personal idea notes (item #14) |
| 6 | Long-running agent harness patterns (Anthropic engineering) | personal idea notes (item #6) |
| 7 | GDP agentic research loops | personal idea notes (item #7) |

### Agent skill ideas

| # | Item | Detail location |
|---|------|-----------------|
| 8 | Answer quality evaluation system | personal idea notes (item #3) |
| 9 | Atomic skills + skill/prompt builder | personal idea notes (item #10) |
| 10 | Small specialized models for atomic tasks | personal idea notes (item #12) |

### Methodology learnings (reusable)

| # | Item | Detail location |
|---|------|-----------------|
| 11 | Pipeline learnings (H1-H5) — pre-filtering, signal density, confidence fields | preference-extraction methodology notes (not published) |

### Unread external references

| # | Item | Detail location |
|---|------|-----------------|
| 12 | Anthropic Claude Certified Architect study guide | personal idea notes (item #15) |
| 13 | Claude Code best practices (15K stars thread) | personal idea notes (item #16) |
| 14 | Karpathy Auto-ML research repo | personal idea notes (item #18) |
| 15 | ARC-AGI solve harness + iterative self-improvement | personal idea notes (item #19) |
| 16 | B2B SaaS growth playbooks as Claude skill | personal idea notes (item #20) |

---

*Governing documents: VISION.md, DESIGN-PRINCIPLES.md, ARCHITECTURE.md*
