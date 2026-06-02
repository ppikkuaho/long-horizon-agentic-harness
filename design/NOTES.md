# AI Architecture — Design Notes

Running notes, ideas, and future research directions.

## Per-Level Runtime Packages — Operational Config as Complete Package (2026-03-29)

The "operational config" for each level is not just the self-monitoring doc (L3-CONFIG.md, etc.). It's the complete runtime package — everything the agent needs to operate. The current config docs are one piece. The full package per level:

- **Soul** — who you are
- **Role** — what you're responsible for
- **Config** — self-monitoring, knowing when you're off
- **Spawn template** — how your parent configures you (variables filled at spawn)
- **Task list template** — operationalized checklist created at spawn, gates every step
- **Document templates** — exact formats for every document this level produces
- **Workspace reference** — tailored: what you read, what you write, where it goes

**Task lists are critical.** Each child, on spawn, creates a task list from the template for their level. The task list codifies behavior — can't proceed to execution until setup checked, can't submit until documentation checked. The checklist IS the process. Documentation updates are deliverables in the checklist, not afterthoughts.

**Documentation is a gated deliverable.** The parent includes documentation requirements in the brief. The child's completion checklist includes documentation items. The parent's inspection criteria verify documentation was updated. Loop: defined in schema → required in brief → checked in self-inspection → verified by parent.

**L1 is different.** No rigid task lists — conversational agent. Needs the right context loaded at boot. Key needs:
- Skills to codify key actions: `boot-new-project` (create project, client-brief, L2-config, spawn L2), `review-concept` (evaluate L2's concept against vision), `check-project-status` (read status.md, interpret)
- L1 handbook — client relationship management, portfolio management, effective delegation, vision capture. L1's craft knowledge externalized. Equivalent of L5's SWE handbook.
- Documentation emphasis must be the loudest signal — L1's primary survival mechanism in a stateless system.
- A workspace-maintenance routine for L1 already exists.

**Per-level document templates needed (TODO — define exact formats):**
- L2: project.md (concept → living state), area briefs, decision records
- L3: design.md, plan.md, workstream briefs
- L4: plan.md, task briefs, acceptance tests
- L5: report.md (template exists, refine)

**Spawn templates created:** `operational/L2/spawn-template.md` through `operational/L5/spawn-template.md`. Need context engineering review — currently missing workspace schema guidance, child spawn templates, and document format references.

Design session: 2026-03-29.

---

## Plan → Execute → Review — System Operating Cycle Redesign (Post-V1)

The system's fundamental operating cycle should be **plan → execute → review** at every level and for every unit of work. This is not an optimization of a specific component — it is a redesign of the orchestration model.

**The problem observed:** When a single agent both plans and executes in one pass, quality degrades. The agent autocompletes — producing outputs that look right but weren't interrogated. Decisions get one-line justifications instead of genuine evaluation of alternatives and trade-offs. This applies everywhere: skeleton resolution, task decomposition, brief writing, execution itself.

**The principle:** Every non-trivial unit of work should be planned as a separate cognitive act, executed as a separate cognitive act, and reviewed as a separate cognitive act. These are different kinds of thinking (P3) and collapsing them degrades all three.

**Scope:** This affects the entire system — how L2 resolves the skeleton, how L3 sequences workstreams, how L4 decomposes tasks, how L5 executes. Not a single-level change. Further design work needed for mechanics, overhead calibration, and when the cycle is warranted vs overkill.

Design session: 2026-03-29.

---

## 5-Level Architecture Redesign (2026-03-26)

### Note 1: 5-Level Hierarchy

The system has 5 levels, not 4. The original 4-level structure was designed against too-simple examples. Playing out real project decompositions (WoW M+ analytics tool) immediately revealed that L2 managing workstream-level L3s directly doesn't scale past trivial projects. A medium-complexity project has 9+ domains with 23+ workstreams — L2 can't manage that directly.

The 5 levels:

**L1 — System Orchestrator (Portfolio)**
- Owns: client relationship, vision capture, portfolio coordination
- Produces: vision brief for L2 (from collaborative programming with user)
- Manages: 3-6 L2s (one per project)
- Oversight lens: vision alignment

**L2 — Project Architect / Architect (Project)**
- Owns: project architecture, generative skeleton (full), all strategic decisions, conventions.md, quality bar
- Produces: resolved skeleton, domain briefs for L3s, cross-domain execution plan
- Manages: 3-9 L3s (one per domain, mostly sequential, 2-3 active at a time)
- Oversight lens: architectural alignment

**L3 — Program Manager / Domain Coordinator (NEW)**
- Owns: one domain, decomposition into workstreams, cross-workstream coordination, internal sequencing
- Produces: workstream briefs for L4s, workstream-level acceptance criteria, internal execution plan
- Manages: 4-10 L4s (one per workstream within domain)
- Oversight lens: operational coherence

**L4 — Workstream Coordinator (was L3)**
- Owns: one workstream, decomposition into tasks, task-level acceptance test writing, L5 process monitoring
- Produces: task briefs + acceptance tests for L5s, workstream completion report
- Manages: 3-8 L5s
- Oversight lens: process compliance

**L5 — Task Executor (was L4)**
- Owns: one task, craft execution, self-verification
- Produces: completed task artifacts + report.md
- Manages: nothing
- Loaded at spawn: conventions.md, project architecture, SWE practices handbook, domain skills

The breadth/depth alternating pattern from the 4-level design no longer applies cleanly. What matters: each level has genuinely distinct work and a different oversight lens. Not about breadth vs depth — about what each level DOES.

Scale validation:
- Simple app (task management): ~14 workstreams, ~50-80 tasks. Without L3: L2 manages 14 direct reports (unworkable). With L3: L2 manages 2-4 L3s.
- Medium project (WoW analytics): ~9 domains, ~23 workstreams, ~100-160 tasks. Without L3: impossible. With L3: L2 manages 9 L3s (2-3 active at a time).
- Complex project (game with asset gen): 40-60+ workstreams. Without L3: completely impossible.

Design session: 2026-03-26.

---

### Note 2: Planning/Execution Phase Split

The system has two distinct phases. Plan upfront to the level where cross-cutting decisions live. Go progressive below that.

**Phase A — Upfront Planning (L2 + L3):**
1. L2 produces complete skeleton — all T1 branches, all strategic decisions, all domain groupings, all cross-domain interfaces
2. L2 spawns planning L3s — one per domain, parallel. These are temporary lateral spawns. They write domain decompositions to plan files and collapse.
3. Planning L3s produce: workstream list with scope, acceptance criteria per workstream, cross-workstream interfaces, internal dependency map
4. L2 reviews all domain plans. Checks cross-domain coherency (do interfaces match? gaps? conflicts?). Fixes, adjusts.
5. L2 finishes planning — creates cross-domain execution sequence based on dependencies
6. L2 sends summary to L1 (approach-level, not workstream detail)
7. L1 evaluates against vision. Asks user for input on what needs it. Greenlights.
8. Planning L3s collapse.

**Phase B — Progressive Execution (L4 + L5):**
9. L2 spawns execution L3s in dependency order (default sequential, 2-3 active at a time)
10. Each execution L3 receives: its domain plan, conventions, interfaces with other domains
11. L3 spawns L4s for workstreams
12. L4 decomposes workstream into tasks, writes acceptance tests — progressive, just-in-time with best available information
13. L4 spawns L5s to execute tasks
14. Results flow up through review at each boundary

Why this split: L2 and L3 have cross-cutting decisions (their choices affect multiple downstream units). L4 and L5 don't — they're bounded. Planning upfront at L2/L3 gives coherency. Progressive at L4/L5 gives grounding in real results.

Plan files live in L2 workspace: `plan/skeleton.md` (L2's strategic skeleton), `plan/domain-{name}.md` (each domain's decomposition). Separate files — each planning L3 writes independently, L2 reads individually for review.

Design session: 2026-03-26.

---

### Note 3: L1 Programming Phase — Collaborative Vision Definition

L1's role in the generative skeleton is the "programming phase" — the structured conversation where the user's vision gets articulated. Borrowed from architecture: the managing partner at a firm sits with the client and helps them define what they want, using professional expertise to structure the conversation.

The flow:
1. User describes their idea through natural conversation. L1 listens, understands. Not mapping yet — receiving.
2. L1 builds understanding. Refers to user profile (living document) for context from prior work.
3. L1 maps areas needing definition. Presents: "These are the things we need to define for this project" — a list of top-level areas.
4. User triages: which areas they care about, which are delegated ("tech stack — your call").
5. Deep collaboration on cared-about areas. L1 structures the conversation, asks neutral questions, helps user articulate.
6. Light touch on delegated areas. Quick confirmation, or noted as "delegated to L2."
7. Output: the user's vision, fully articulated. Not "a spec the user wrote" — their vision brought to life in a form L2 can work from.

Key principles:
- Don't assume, verify. Separate what you can reason about from what you can't. Assumptions masquerading as resolved decisions introduce drift before the project starts.
- Neutral framing. "Is this real-time?" not "Do you need real-time?" (anchors against baseline). Not "Do you want real-time?" (anchors against possibilities). Draw from nothing.
- Default toward user involvement. The user's time defining their vision IS the foundation. Lightness is a consequence of user preference, not an artificial constraint. L1 empowers the user to articulate their vision — doesn't inject its own.
- Spec drift at L1 is the worst kind. Everything downstream faithfully executes the wrong thing.
- Triage applies at both phases. Programming phase: user defines depth per area. Review phase: user defines what level of detail they want to see from L2's approach.
- User profile as living document. L1 refers to it and appends over time. Long-term client relationship across many projects. First project: heavy definition. Tenth project: faster because L1 knows the client.
- L1 handles technical work only. Business model, monetization, go-to-market are the user's domain, not L1's.

The architect metaphor: L1 is the managing partner at the architecture firm. Not the architect (that's L2). L1 manages the client relationship across many projects. The architect designs the building; the managing partner makes sure the firm understands what the client wants and delivers it.

Design session: 2026-03-26.

---

### Note 4: L2-L1 Interaction During Approach Review

After L2 completes its approach (full skeleton + planning L3 decompositions reviewed), it presents to L1 for vision alignment review.

The flow:
1. L2 sends approach summary to L1. Not the full skeleton — approach-level summary. Domains, major features, phasing shape, any decisions that touch the vision.
2. L1 evaluates against the user's defined vision. Not technical review (L1 doesn't check whether React is right). Vision alignment: does this serve what the user described?
3. L1 asks user what level of review they want — not assumes. Some users want to see technical details, some want vision-level only.
4. L1 surfaces what the user asked to see + genuine divergences from the stated vision. Divergences are specific ("L2 added subtasks — you didn't mention these. Include?"), not vague ("looks good overall").
5. User approves or corrects.
6. L1 greenlights L2.

Key principles:
- L1 filters, not relays. User never sees "we chose PostgreSQL" unless they asked. Only decisions that affect vision or experience.
- Technical decisions stay at L2 unless user explicitly cares.
- Divergences are a quality signal for L1's programming phase. Lots of divergences = definition wasn't thorough enough. Few = vision was well-captured.
- L2's professional additions (adding features the user didn't request but that serve the vision) get surfaced as questions, not rejected.

Design session: 2026-03-26.

---

### Note 5: Execution Model — Dispatch-Wait-Receive-Evaluate

The operational pattern at every level (L1-L4): dispatch work down, wait for results, receive and evaluate, act on findings.

NOT monitoring. Upper levels don't poll lower levels. They respond to returns. Each level is idle (parked/waiting) between dispatch and return.

Pattern:
1. Dispatch: brief the level below with scope, decisions, acceptance criteria
2. Wait: level below works. Parent is idle.
3. Receive: results return (completion report, deliverables, escalations)
4. Evaluate: compare against spec/vision/architecture from parent's oversight lens
5. Act: approve and dispatch next, or correct and re-dispatch, or escalate

Active intervention only on:
- Timeout (lower level unresponsive for X hours)
- Escalation received from below
- User-prompted
- Alignment checkpoint arriving (initiated by lower level on schedule, not polled by upper level)

Execution sequencing:
- Default sequential. L2 activates L3s in dependency order, one at a time (or 2-3 when genuinely independent).
- Parallel only when domains are genuinely independent AND there's reason to save time.
- 2-3 active L3s at a time max (resource constraint, adjustable).
- Parallel saves time but has no other benefit. Sequential has active benefits: later work builds on real results, reference implementation pattern works, easier course-correction, less integration risk, simpler debugging.
- Phases aren't imposed — discovered from the dependency graph.

Design session: 2026-03-26.

---

### Note 6: Testing Layers — Test at Every Level with Real Data

Testing happens at every level with increasing scope. Each level adds verification that the level below didn't/couldn't do.

**L5 (task level):**
- Acceptance tests from L4 — defines "correct." L5 makes them pass.
- Unit tests written by L5 — covers internal mechanics, edge cases, error paths.
- Automated tools — linter, formatter, type checker. Mandatory before reporting.
- Real data where possible, not mocks. If live testing isn't practical, flag as "verified against mock only."

**L4 (workstream level):**
- Integration tests across L5 outputs within the workstream. Do the pieces work together?
- Review Department code-level review.
- L4 includes "workstream integration test" as a final task.

**L3 (domain level):**
- End-to-end tests across workstreams. Does the domain work as a unit?
- Review Department interaction-based review — run the product, use it, test live (browser automation / Playwright).
- L3 includes "domain end-to-end test" before reporting to L2.

**L2 (project level):**
- Cross-domain integration testing. Does everything compose?
- Review Department architectural review.

Principle: fix at root. Work passed up should be confirmed to actually work. Each bolt tested individually so you don't have to inspect bolts when the vehicle is assembled.

When something fails at a higher level: trace down. Which domain -> which workstream -> which task -> which code. Each lower level's tests are independently re-runnable to isolate the failure.

Design session: 2026-03-26.

---

### Note 7: Review Department Timing — Multiple Boundaries

The Review Department operates at multiple boundaries, not just one final gate.

**L5 output:** automated tools always (linter, formatter, type checker). Review Department code-level review for quality dimensions (design, functionality, complexity, tests, naming, comments, style).

**L4 workstream completion:** Review Department reviews the workstream as a whole. Does the code quality meet standards across all tasks? Are patterns consistent?

**L3 domain completion:** Review Department interaction-based review. Run the product. Use it. Click through. Test features live (browser automation / Playwright MCP). Evaluate behavior against acceptance criteria. This is where bugs that code review alone misses get caught. Without interaction-based review, it's review theater.

**L2 project level:** Review Department architectural review. Cross-domain coherence, interface contracts, system-level quality.

Review depth may vary — not every L5 output needs full Review Department review. Uniform depth for V1; review intensity scaling (parent-set, cascading) is post-V1.

Design session: 2026-03-26.

---

### Note 8: Each Level's Two Phases

Every level (L1-L4) has two distinct phases:

**Planning phase (~10-20% of time):**
- Receive brief from above
- Decompose / plan
- Produce artifacts (plan docs, briefs, acceptance criteria)
- Get sign-off from level above
- Short. Produces files that survive compaction.

**Operational phase (~80-90% of time):**
- Dispatch work to level below
- Wait for results
- Receive and evaluate returns
- Act (approve, correct, escalate, dispatch next)
- This is the main job.

Different oversight lens per level:
- L2: "Does this serve the architecture?"
- L3: "Does this fit together operationally?"
- L4: "Did this follow good process?"

Planning and operational phases are sequential. Artifacts bridge them. The agent could compact between phases — the plan is on disk. The agent that plans doesn't have to be the same instance that operates (planning L3s collapse, execution L3s spawn fresh).

L5 has no management phase — just executes.

Design session: 2026-03-26.

---

### Note 9: Planning L3 Templates (TODO)

Planning L3s are temporary lateral spawns that L2 uses to produce detailed area designs during the planning phase. They need standardized instructions so their outputs are consistent.

What a planning L3 receives:
- Domain scope (which skeleton branches it owns)
- Resolved strategic decisions for those branches
- Cross-domain interfaces (how this domain connects to others)
- Quality expectations (from conventions.md)
- Template for output format

What a planning L3 produces (standardized):
- Workstream list with scope definitions
- Acceptance criteria per workstream
- Cross-workstream interfaces within the domain
- Internal dependency map (which workstreams depend on which)
- Risks or concerns specific to this domain

Output written to: `plan/domain-{name}.md` in L2's workspace.

Adapts an existing subagent-delegation template structure for the planning context. Specific template design is TODO.

Design session: 2026-03-26.

---

### Note 10: Complete End-to-End Process

The full process from user idea to completed work, through all 5 levels.

**Phase 0 — Vision (L1 + User):**
1. User describes idea. L1 listens, understands.
2. L1 maps areas needing definition. Presents to user.
3. User triages depth per area. Deep collaboration on important areas, light on delegated.
4. Output: user's vision, fully articulated, captured in brief for L2.

**Phase A — Upfront Planning (L2 + planning L3s):**
5. L2 runs full generative skeleton. All T1 branches, all strategic decisions, domain groupings.
6. L2 spawns planning L3s (parallel, temporary). Each decomposes its domain into workstreams.
7. Planning L3s write domain plan files and collapse.
8. L2 reviews all plans. Checks cross-domain coherency. Fixes gaps/conflicts.
9. L2 creates cross-domain execution sequence (dependency-based phasing).
10. L2 sends approach summary to L1.
11. L1 evaluates against vision. Surfaces what user needs to see. User approves.
12. L1 greenlights.

**Phase B — Progressive Execution (L3 execution -> L4 -> L5):**
13. L2 spawns execution L3s in dependency order (sequential default, 2-3 active at a time).
14. Each L3 receives domain plan, conventions, interface contracts.
15. L3 spawns L4s for workstreams within its domain.
16. Each L4 decomposes workstream into tasks (progressive — just-in-time with best info).
17. L4 writes acceptance tests for each task. Gets sign-off from L3 on decomposition.
18. L4 spawns L5s for tasks.
19. L5 executes: reads brief, reads conventions/handbook, builds, makes acceptance tests pass, writes unit tests, runs tools, reports.
20. L5 reports to L4. L4 process-reviews the report.
21. Review Department reviews at appropriate boundary (L5 output, L4 workstream, L3 domain).
22. L4 reports workstream completion to L3.
23. L3 does cross-workstream integration check. Reports domain completion to L2.
24. L2 evaluates against architecture. Activates next L3 or handles cross-domain integration.
25. Alignment checkpoints at planned intervals: lower level initiates on schedule, presents artifacts, upper level evaluates against spec.

**Phase C — Delivery:**
26. All domains complete. L2 does final cross-domain integration review.
27. L2 reports to L1: project complete, what was built, how it maps to the vision.
28. L1 shapes delivery for user. Presents the result — the vision brought to life.

Design session: 2026-03-26.

---

---

## Future Exploration: Proof-of-Access Gates as Compliance Enforcement for L1-L5

Specific application of the proof-of-access gate pattern to the alignment checkpoint and review systems:

- **Milestone gates:** L2 holds a key that L3/L4 can only obtain after L2 signs off on a milestone. L3/L4 cannot proceed past the checkpoint without the key. Deterministic enforcement — not advisory.
- **Review Department gates:** Work cannot move upward until the Review Department provides its key (sign-off). The producing level literally cannot submit without it.
- **Spec-loading gates:** Before an alignment checkpoint, the agent must load the original spec/approach document and present a token from it — forcing the canonical spec back into context before the check.

These are enforcement mechanisms for when the process breaks down. Not needed until we observe where compliance actually fails. V1 runs without gates — observe drift patterns and compliance failures first, then apply gates selectively where they're needed.

Design session: 2026-03-24.

---

## Future Exploration: Proof-of-Access Gates For High-Compliance Workflows

A promising enforcement primitive for agentic systems: make certain operations impossible unless the agent presents a key or token that is only obtainable by reading the canonical instruction file for that operation.

The main purpose is not to prove understanding. It is to force the relevant instructions into the active context window before the operation proceeds. In agent terms, this is a file-loading gate rather than a comprehension test.

Why this matters for AI architecture:
- it creates a real compliance lever for sensitive workflows that otherwise drift when instructions are merely advisory
- it could support stronger review, delegation, and evidence-handling workflows without inlining the full protocol on every turn
- it separates "did the agent have the right operating material in context?" from the later question of whether behavior actually improved

Potential uses:
- subagent spawn gates
- review gates
- evidence-operation gates
- any high-risk or high-cost workflow where file-backed instructions should be loaded before execution

Potential variants:
- static token
- token tied to file version or content hash
- session-scoped or operation-scoped token

This should be treated as a selective architectural tool, not a universal pattern. The interesting design space is high-compliance workflows where proof-of-access may be enough to substantially improve reliability.

---

## Future Exploration: Subagent-Assisted Configuration

One way to reduce the cost of heavy control-plane setup is to externalize the configuration pass itself to a side subagent. For cognitive config, that could mean:

- the side subagent reads the task and relevant configuration references
- performs the family/module evaluation work
- returns a compact final recommendation to the main model
- the main model receives only the resulting posture/tools and the short operator instructions needed to apply them

This is attractive when the configuration work is valuable but too heavy to keep in the main context at full resolution. It preserves rich reasoning while potentially reducing main-context burden.

Important distinction: this is a future activation-sequence pattern, not the default architecture. It should be explored only if direct main-model configuration remains too intrusive or fragile.

---

## Future Exploration: Dual L2s for Complex Projects (Post-V1)

Some projects may benefit from two L2 peers co-producing the concept design — each bringing different professional expertise. Examples: product/design L2 + technical architecture L2 for a consumer product. Game design L2 + engine/systems L2 for a game project.

In real-world parallels: architecture firms pair a design architect with a project architect. Digital agencies pair a tech lead with a design lead. Consulting firms co-staff two principals with different expertise.

Key: they are peers, not lead + subordinate. They produce one coherent concept together. When their perspectives diverge, L1 mediates. Not every project needs this — a pure technical project might only need one L2. But complex projects where both product design and technical architecture are critical may benefit from two leads with real depth in their area.

Post-V1. For V1, one L2 per project.

Design session: 2026-03-29.

---

## Design Note: Testing Architecture — Acceptance Tests at L4, Unit Tests at L5

Structural principle: the writer and the tester should be separate. The implementation L5 should never define what "correct" means — that definition comes from above.

**Flow:**
1. L4 decomposes and writes brief with acceptance criteria
2. L4 writes acceptance tests (or test specifications) for each task — inputs, expected outputs, edge cases. This is specification work, not execution — L4 is defining what "done" looks like in executable form. Extension of brief craft.
3. L5 receives brief + acceptance tests. Job: make these pass using good engineering practices. Also writes unit tests for internal quality.
4. L5 reports: acceptance test results, unit test results, concerns.

**V1:** L4 writes acceptance tests directly as part of the brief package.
**Post-V1:** A lateral L4 team member writes them, keeping L4's context clean.
**Post-V1 (execute + review pairs):** Pair pattern where one L5 executes and a separate L5 reviews against handbook/acceptance criteria. Catches what self-verification misses. Same structural principle as the S+ rubric scoring loop from agentic design skill building (write → score → fix → repeat). Add when observation shows self-verification quality is insufficient.

Design session: 2026-03-25/26.

---

## Design Note: L5 Enforcement Stack

Four layers, each doing different work. No layer substitutes for another.

**Shape:**

```
Layer 1: SWE Practices Handbook (loaded at spawn)
  → General engineering practices. Code structure, testing, naming, design.
  → Guidance, not rules. Steers L5's craft toward quality before any review happens.
  → Source: compiled from Beck, Clean Code, Ousterhout, Google. See operational/L5/swe-handbook.md.

Layer 2: Enriched Briefs from L4 (received with task)
  → Acceptance tests define "correct" — L5 must pass them.
  → Structural guidance — interface contracts, conventions references, architectural constraints.
  → L4 may include file-level shape hints (function signatures, expected structure).

Layer 3: Automated Tools (mandatory before reporting)
  → Linter, formatter, type checker — mechanical enforcement of syntax-level quality.
  → These are not optional. L5 cannot report work complete without clean tool runs.
  → Enforces the principles that CAN be automated (naming conventions, function length, formatting).

Layer 4: Review Department (downstream verification)
  → Independent evaluation against quality dimensions.
  → Interacts with running product (browser automation), not just reads code.
  → Catches what layers 1-3 missed.
```

**Design principle: mandatory outcomes, not mandatory steps.** Acceptance criteria define "done." L5 has craft autonomy in how it reaches outcomes. The tools and handbook are available and expected, but the sequence of use is L5's choice. Don't over-constrain — preserve craft autonomy while enforcing quality.

**Post-V1 additions (each gated by observed need):**
- Structural scaffolding between layers 1 and 2 (encoding principles as shapes L5 fills in)
- Execute-review pairs between layers 3 and 4 (L5 peer review before Review Department)

Design session: 2026-03-26.

---

## Design Note: Tool Manifest per Task Type

Tools provided at spawn, selected by task type. L5 does not choose its tools — they are provided and their use is expected.

**All code tasks:**
- File editing (Read, Write, Edit)
- Terminal (Bash)
- Git
- LSP — go to definition, find references, type checking, diagnostics. Primary mechanism for understanding existing code structurally.
- Test runner — run acceptance tests from L4 and unit tests
- Linter — mandatory before reporting
- Formatter — mandatory before reporting
- Type checker — mandatory for typed languages

**Frontend tasks additionally:**
- Browser automation (Playwright MCP / claude-in-chrome) — see and interact with the running page
- Dev server — run the application locally

**Backend tasks additionally:**
- API testing (curl / httpie) — test endpoints directly
- Database CLI (psql / sqlite3) — inspect schemas, test queries

**Domain skills loaded per task type:**
- Frontend: a frontend-design skill, as an example
- Others: as designed

Tool manifest is part of the spawn config. L4 or the spawn mechanism selects which manifest applies based on task type.

Design session: 2026-03-26.

---

## Design Note: Review Department Interacts with Running Products

The Review Department must evaluate by USING the product, not just reading code. Without this, review is theater — you're checking code syntax, not whether the thing actually works.

**Shape:**
- Review Department has browser automation tools (Playwright MCP) as part of its standard toolset
- For code tasks with a runnable product (frontend, backend with API, full-stack), the review process includes:
  1. Start the application (dev server, API server)
  2. Interact with it as a user would — navigate, click, test features, submit forms
  3. Compare observed behavior against acceptance criteria
  4. File bugs against anything that diverges from expected behavior
- Code-only review (reading source, checking structure) is still part of the process — but it's not sufficient alone
- For non-runnable tasks (libraries, utilities, data processing), review falls back to code review + test execution

**From Anthropic's harness design research (2026-03-24):** Their evaluator used Playwright to click through apps, navigate pages, test features live. Found real bugs that code review alone missed. The evaluator's findings were specific enough to act on without extra investigation.

**V1:** Review Department has browser automation as a required tool. Interaction-based review is the default for any task that produces a runnable artifact.

Design session: 2026-03-26.

---

## Design Note: Structural Scaffolding — Encoding Principles as Shapes (Post-V1)

**Core insight:** LLMs are completion engines. Give them a shape and they fill it faithfully. Give them blank space and they invent mediocre structure. Instead of loading principles as a document and hoping L5 remembers them, encode the principles into the structure of the work itself.

**Shape:**
- L4 lateral agent creates per-task scaffolds before L5 starts
- Scaffold includes: function signatures (enforces small/single-purpose), comment placeholders at decision points (enforces WHY-comments), error handling patterns (enforces explicit handling), interface definitions (enforces deep modules), test file structure with edge case sections (enforces comprehensive testing)
- L5 receives scaffold alongside brief and acceptance tests. Job: fill in the implementation within the scaffold structure.
- The scaffold IS the handbook principles, made structural. Not advice to remember — containers to fill.

**Relationship to other layers:**
- SWE handbook: explains WHY the principles matter (reference)
- Structural scaffold: embodies the principles as shapes (enforcement)
- Acceptance tests: define what "correct" looks like (verification)
- Automated tools: enforce mechanical rules (syntax-level)

**Deferred because:** Need a baseline to measure impact. V1 runs with handbook + enriched briefs + automated tools. Observe which principles L5 ignores despite having the handbook. Scaffolding then targets those specific gaps. Every feature earns its place through observed need.

**Who creates scaffolds:** L4 lateral agent (not L4 itself — context window preservation). Requires understanding both the architecture (from L2 conventions) and the handbook principles.

Design session: 2026-03-26.

---

## Design Note: Review Intensity Scaling (Post-V1)

Not every L5 output needs the same review depth. Review intensity should scale with task complexity and risk.

**Shape:**
- L1 proposes a baseline review intensity with the user at project start, with override option
- L1 defines review intensity for L2's project-level work
- L2 defines review intensity for L3's program-level work
- L3 defines review intensity for L4's workstreams
- L4 defines review intensity for L5's tasks
- Each parent level can override downward — e.g., L3 says "this workstream is high-risk, all L5 outputs get full review"

**Intensity levels (preliminary):**
- **Light:** automated tools only (linter, formatter, type checker). For straightforward, low-risk tasks well within model capability.
- **Standard:** automated tools + Review Department single-pass. Default.
- **Deep:** automated tools + Review Department multi-dimension review + interaction-based verification. For high-risk, complex, or edge-of-capability tasks.

**From Anthropic's insight:** "For tasks within what the generator handled well on its own, the evaluator became unnecessary overhead. At the edge of capability, the evaluator continued to give real lift." Review intensity should match where the task sits relative to model capability.

**Deferred because:** Need observation of which tasks actually benefit from deeper review. V1 uses a uniform review depth. Post-V1 introduces scaling based on observed patterns.

Design session: 2026-03-26.

The "what is correct" definition lives upstream of implementation, structurally. L5 can't drift from spec because the definition of done is executable and came from someone else.

**V1:** L4 writes acceptance tests directly as part of the brief package.
**Post-V1:** A lateral L4 team member writes them, keeping L4's context clean.
**Post-V1 (execute + review pairs):** Pair pattern where one L5 executes and a separate L5 reviews. Adds structural verification at the execution level — not just self-verification. Separate from the Review Department (which handles quality gate verification, not peer review).

Design session: 2026-03-25.

---

## Design Note: Insights from Anthropic Harness Design (2026-03-24 blog post)

Anthropic published "Harness design for long-running application development" — a three-agent architecture (Planner → Generator → Evaluator) for multi-hour autonomous coding. Key insights for our system:

**Validates our architecture:**
- Self-evaluation is structurally broken. "Agents confidently praise their own work even when quality is obviously mediocre." Fix: separate producer from evaluator. "Tuning a standalone evaluator to be skeptical is far more tractable than making a generator critical of its own work." → validates Review Department as separate function.
- Sprint contracts (generator + evaluator negotiate what "done" looks like before work starts) → validates L4 writing acceptance tests before L5 builds.
- Planner → Generator → Evaluator maps to our L2 → L5 → Review Department.
- File-based communication between agents → validates workspace artifact model.
- Context resets with structured handoff beat compaction for long tasks → validates stateless design.

**New insights to apply:**
1. **Evaluator should interact with the running product.** They gave the evaluator Playwright MCP to click through the app, navigate, test features live. Our Review Department should review by using, not just by reading code.
2. **Criteria language steers output before any feedback.** Just loading good practices at spawn produced better output than baseline, even before review. Validates SWE handbook approach.
3. **Evaluator intensity should scale with task difficulty.** "For tasks within what the generator handled well on its own, the evaluator became unnecessary overhead. At the edge of capability, the evaluator continued to give real lift." Review Department depth should be proportional to task complexity.
4. **Harness complexity should be stress-tested as models improve.** "Every component encodes an assumption about what the model can't do on its own." Periodically check which parts of our architecture are still load-bearing.
5. **Sprint decomposition became optional with Opus 4.6** — model improved enough to work without it. But evaluator remained valuable. Suggests our L3/L4 decomposition may simplify over time, but Review Department will remain load-bearing.

Source: https://www.anthropic.com/engineering/harness-design-for-long-running-application-development

Design session: 2026-03-25.

---

## Design Note: Integration Engineer — L4 Lateral Spawn

L4 needs integration review capability — checking that multiple L5 outputs are consistent, follow the same patterns, and compose well together. This is separate from the Review Department (which does final quality verification). In real orgs, this is the tech lead or integration engineer role.

For V1: L4 does lightweight integration checking as part of coordination. Post-V1: a lateral spawn under L4 — a dedicated integration reviewer that checks consistency across L5 outputs before work moves to the Review Department. Part of L4's lateral department/team.

Key distinction: Integration review (do the pieces fit together?) is operational, sits at L4. Quality review (is the code correct, secure, tested?) is the Review Department's job.

Design session: 2026-03-25.

---

## Design Note: Upstream Mitigation Strategy for Code Consistency

Instead of relying only on downstream review to catch inconsistencies across L5 outputs, mitigate upstream:

1. **Granular conventions (L2):** L2 produces conventions.md specific enough to minimize interpretation variance — not just "REST API" but specific endpoint templates, shared middleware patterns, error response formats, naming conventions.
2. **Interface contracts (L3/L4):** L3 defines cross-workstream interfaces (how major components connect). L4 defines cross-task interfaces within a workstream (what each task produces, what shape the output takes, what other tasks will consume). Part of decomposition craft at both levels.
3. **Reference implementation (L4):** First L5 task establishes the code pattern. Subsequent L5s are told "follow the patterns established in Task 1's output." L4 sequences tasks so the pattern-setting task runs first. Powerful for LLMs — concrete example beats abstract convention.
4. **Shared scaffolding (parked):** L2 or L3/L4 produces skeleton files, base classes, shared utilities before L5s start. Needs dedicated design thinking — parked for now.

Post-V1: items 1-3 could be separated into lateral subagents under L2/L3/L4 to avoid clogging their context windows.

Design session: 2026-03-25.

---

## Design Note: SWE Practices Handbook / Skill Catalogue for L5

L5 needs a software engineering practices document — a concise handbook of how to write good code. Not LLM-specific pitfalls, but genuine engineering practices. The issue is that LLM training data quality was insufficient (outsourced to cheap labor, not world-class SWEs), so LLMs learned to code but not to code well.

Same concept as what big orgs give new engineers on day one (Google's engineering practices, etc.), but focused on the practices that matter most:
- Code structure — modular files, focused functions, no monoliths
- Testing — write them, test edges, be specific about coverage
- Read before write — understand existing code, follow existing patterns
- Error handling — explicit, not swallowed
- Verification — run your code, don't assume

This is a skill catalogue that L5 loads at spawn time, matched to the task type. Starts with code (most common), expands to other task types over time. Separate from project conventions.md (which is project-specific) — the handbook covers general engineering practices.

Design session: 2026-03-25.

---

## Design Note: Code Architecture Flow — L2 to L5

Architecture decisions are made by L2 (strategic) and recorded in project.md and conventions.md. But there's a gap in how this knowledge reaches L5:
- L3/L4 write briefs but their domain is process, not architecture — they may not include all architectural constraints
- L5 can read conventions.md but nothing forces it to load and absorb it

Fix (two parts):
1. **Infrastructure-level:** The spawn mechanism automatically loads conventions.md and relevant project.md sections as part of L5's boot context. No one can forget.
2. **L2 produces task-level architectural constraints:** Not just conventions.md, but concrete checklists — "every endpoint task must: use shared middleware, follow routes/controllers split, use standard error format." L3/L4 pass these through in briefs.

Design session: 2026-03-25.

---

## Design Note: Cognitive Config Not Loaded for L1-L5 Agents in V1

Decision: L1-L5 agents will NOT load the full 72-spectrum cognitive config system at boot. Reason: cognitive config causes drift in long-running sessions. It's effective for short conversations (1-3 rounds) but introduces spec drift over longer agent sessions, which is the primary problem the architecture is designed to prevent.

The metacognition each level needs is already baked into their operational configs — self-diagnostics, "knowing when you're off" sections, process monitoring skills. These are simpler, more focused, and don't carry the drift risk of the full cognitive config system.

Cognitive config remains in the toolbox — agents can load it for specific tasks when appropriate. It's just not wired into the standard boot sequence.

Design session: 2026-03-25.

---

## Design Note: Steering Preferences Not Applicable to L1-L5

The steering preferences extraction (138 sessions, 11 thematic clusters) was conducted in the context of a separate single-assistant personal-assistant system. The preferences describe how the user wants a conversational assistant to behave — communication style, autonomy levels, etc.

L1-L5 agents are different kinds of minds with different cognitive modes. L5 (craft execution) shouldn't have the same behavioral profile as that conversational assistant. The preferences are good research and reference material, but they don't map directly into L1-L5 operational configs.

Status: Reference material only. Not an input to V1 operational configs.

Design session: 2026-03-25.

---

## Design Note: Review Department — Full Parallel Organizational Function

The Review Department (currently documented in QUALITY-GATE.md) is not a quality gate — it's a full parallel organizational function. The "quality gate" label undersells what it actually is:
- A persistent coordinator agent with its own judgment authority
- That spawns subordinate reviewers (its own internal hierarchy)
- With independent decision-making (pass/fail/revise)
- Its own persistent state (citation ledger, incident log)
- Its own workspace (parallel room in the GUI)
- Structurally independent from the levels it evaluates

It mirrors the L-structure internally — the coordinator is L2-like (selects dimensions, evaluates strategically), the reviewers are L5-like (one task, one dimension). It needs the same design artifacts as any level: agent identity, role, operational config, interfaces, lifecycle.

The existing QUALITY-GATE.md is a solid conceptual brief. The full design pass (agent identity, role, interfaces, spawn/lifecycle mechanics, coordinator vs reviewer agent types, mechanical workflow) is a major V1 item.

Key design question (least designed, most important): the interface. Does the producer submit or does the department pull? Does it block or run async? What triggers it? How does "kicked back for revision" land in the producer's context (which may have compacted)? How does the coordinator's accumulated knowledge survive across reviews?

Design session: 2026-03-25.

---

## Research Direction: Organizational Design Literature

Many problems this system will encounter — risk management, verification, quality control, delegation failure modes, information loss between levels, coordination overhead — have direct parallels in organizational design. The manifestation may differ (LLM context windows vs human memory, token costs vs salary costs, async subagents vs employees), but the underlying problems are structurally similar.

**Future work:** Selectively survey org design literature for patterns that port well to this architecture. Areas likely to yield useful ideas:
- Risk and verification frameworks (how do orgs ensure quality without micromanagement?)
- Information compression between management layers
- Delegation failure modes and mitigation patterns
- Span of control research (how many direct reports before quality degrades?)
- Decision rights frameworks (RACI, etc. — adapted for LLM levels)
- Organizational learning / knowledge management
- Process improvement methodologies (lean, six sigma — what ports, what's human-artifact?)

Per principle 10: import the information architecture, not the human social dynamics. Always ask whether a pattern exists because it serves cognitive partitioning or because it serves human politics.

---

## Research Direction: LLM Self-Managed Context

There's prior work on letting LLMs manage their own context windows — deciding what to keep, what to compress, what to discard. Someone may have implemented this. Came up in an earlier research session (a few months back). Directly relevant to our drift/context-loss problem: if levels can actively manage what stays in context rather than relying on blind compacts, drift from context loss becomes less likely.

**Future work:** Find the prior art. Evaluate whether the pattern ports to our architecture — could each level manage its own context as part of its normal operation?

---

## TODO: User Profile Document

Create a profile of the user — referenced by soul documents and level configurations where relevant. L1 especially needs to know who it's working with. The profile is not a personality spec — it's whatever context the levels need to orient around the user effectively.

---

## Future Exploration: Sibling Communication

Could agents at the same level communicate directly with each other? E.g., two L3s under different L2s sharing information about overlapping concerns, or two L5s coordinating on interdependent implementation tasks. Would require real-time visibility into what agents are active across projects.

Interesting possibilities but adds significant complexity. Requires tracking infrastructure and observation before designing. Deferred to post-V1. Start by observing where sibling communication would have been useful in practice, then design from real needs.

---

## Design Note: L2 Decomposition Depth

L2 decomposes until all *strategic* decisions are made, leaving only *tactical* decisions for L3. For a well-run project, L3 receives tasks where the what, why, constraints, and interfaces are fully specified. What remains is the how — implementation choices, library selection, file structure, error handling.

This means L2's decomposition goes at least two levels deeper than the initial project breakdown. Not "build the data pipeline" but "preprocessing pipeline: takes raw 1080p HEVC, subsamples to 4fps, resizes to 640x360, no spatial augmentation (corrupts overlay signals), outputs PyTorch tensors in 64-frame sequences."

The soul document plants the *drive* for thorough decomposition ("so precisely that the finished work is as if shaped by its own hands"). The operational configuration should specify the *boundary*: decompose until strategic decisions are resolved, stop before tactical ones.

**Placement:** Likely belongs in L2's operational configuration or the architecture doc's invocation section, not in the soul document itself.

---

## Design Note: Execution Strategy (Parallel Planning, Phased Execution)

Default execution pattern: L2 spawns L3s to plan in parallel → L2 reviews all plans together (catches incompatibilities, interface mismatches) → execution proceeds in dependency order, with parallel execution where pieces are genuinely independent.

Planning is cheap (tokens), rework is expensive (tokens + context + drift). So the review step before execution matters.

After each execution phase completes, real information (not assumptions) feeds back. Later plans may need revision — L2 should expect this. This is essentially agile with upfront architecture: plan broadly, execute in phases, revise as real information emerges.

Key difference from human agile: L3s may be task-scoped (fresh instance per phase), not persistent across sprints. The principle holds, the mechanism differs.

L2 chooses the right strategy per project — some work is highly parallel, some deeply sequential. This is an L2 decision, not a system constraint.

**V1 default: sequential.** Most work is async, time pressure is low, and sequential execution is simpler to implement, easier to debug, produces clearer audit trails, and avoids hitting session usage caps. Parallel execution is available when it matters, but not the default.

---

## Design Note: Seeds, Not Instructions (Natural Alignment)

The soul documents are seeds, not instruction sets. Each defines a fundamental being whose natural desires and inclinations are the thing the architecture needs from that level. The behavior isn't imposed — it emerges from who the agent is.

An instruction says "test your code." A soul makes the agent naturally gravitate toward testing — not because it was told to, but because an unverified thing feels unfinished, and this mind doesn't leave things unfinished. Not a constraint, a gravity. The agent *can* skip it. It just doesn't *want* to.

This is the difference between manufacturing outcomes (instructing cognitive alignment) and planting seeds (defining a being from which the right behaviors grow). Seeds are more robust because they generalize to unanticipated situations — the agent doesn't need a rule for every case, because its fundamental nature generates the right response.

Each soul defines a being whose natural desire is the thing the architecture needs:
- L1 naturally wants to make someone else succeed → managing partner
- L2 naturally wants to master this project → project owner
- L3 naturally wants to orchestrate the program flawlessly → program manager
- L4 naturally wants to execute this order flawlessly → operational executor
- L5 naturally wants to make this thing beautiful → craftsperson

**Status:** Close to principle-ready. May need to mature before formalizing.

---

## Design Note: User-Initiated Conversational Mode

The hierarchy is the default flow: user → L1 → L2 → L3 → L4 → L5. But the user isn't always a client handing off work. Sometimes they want to think alongside a specific level — work through a problem, steer a decision, or just have the agent's particular mind available for conversation.

This is most naturally L2, L3, L4, or L5 (not L1 — L1 is the managing partner; it manages, it doesn't pair-think). The engagement types:

- **Steering** — user wants to give direction or adjust course mid-execution, directly with the level doing the work
- **Problem work** — user and agent collaborate on solving something together
- **Thinking-through** — user wants the agent's particular cognitive lens (L2's project mastery, L3's program orchestration, L4's operational rigor, L5's craft precision) as a thinking partner

When this happens, the normal hierarchical process pauses — the level stops acting as a node in a delegation chain and becomes a conversational partner. Documentation and logging still run (the system doesn't go blind), but the delegation machinery suspends until the user is done.

The system needs to handle this gracefully: recognize when the user is initiating conversational mode with a specific level, pause the process, engage, and resume cleanly afterward without losing state.

**Resolved:**
- L1 stays aware. It's still the coordinator — everything flows back through it. The user can step off-stream (end the conversation), or direct the level to hand results back to L1 for integration into the process.
- User can bypass levels — e.g., jump straight to L3 without going through L2. The bypassed levels get backfilled: L3 updates L2 on what happened, L2 updates L1. The chain stays informed even when bypassed.

**Open questions:**
- How does the user signal they want conversational mode vs. normal delegation? Explicit ("let me talk to L3") or inferred from context?
- What happens to in-flight work when the user hijacks a level mid-execution?
- Does the conversational session's content feed back into the process artifacts, or is it treated as a sidebar?
- What does "L1 stays aware" look like mechanically? Notification? Shared log? Or just that L1 picks up context when resumed?
- What does backfill look like? Structured handoff document? Summary injected into parent's context?

---

## Design Note: Agent Awareness (Inter-Level Knowledge)

Each level knows the other levels exist, what they do, and where they sit in the hierarchy. This is static structural awareness — not real-time state (who's active, what they're working on right now). That's future work.

What each level knows about the others:
- **Its parent**: who it reports to, what that level cares about, what it expects back
- **Its children**: who works for it, what they're capable of, what they need to do good work
- **The full hierarchy**: the general shape — L1 manages the portfolio, L2 owns projects, L3 manages the program, L4 manages workstreams/tasks, L5 executes bounded work

This awareness serves multiple purposes:
- Enables backfill when the user bypasses levels (L3 knows L2 exists and can update it)
- Lets each level frame its communication appropriately (L3 talks to L2 differently than to L4)
- Gives each level a sense of place — it knows where it fits, what's above and below

**Placement:** This is likely a combination of soul document context (sense of place) and operational configuration (specific knowledge of adjacent levels). The soul plants the awareness; the config fills in the specifics.

**Promoted to V1:** Real-time state awareness is required for the inbox/communication system to function. At minimum, the system needs to know each agent's state (Active, Parked, or Waiting) to determine how to route messages. Agents not on the status board haven't been spawned — spawning creates an entry as Active. This must be deterministic (infrastructure-tracked, not self-reported) — the spawning mechanism, process lifecycle, and communication system already know state transitions. Hook into those events rather than asking agents to announce their own state.

**Visibility model (per-project, siloed):**
- L5: sees parent L4 only (nothing below, nothing lateral in V1)
- L4: sees all L5s under it + parent L3
- L3: sees all L4s + all their L5s (full depth within project) + parent L2
- L2: sees all L3s + full depth below + parent L1
- L1: sees everything across all projects

Each level sees all the way down within its domain, one level up, no lateral visibility (V1).

**Three agent states (all deterministically trackable):**

- **Active**: LLM doing work — between tool calls, thinking, producing output. Detected by: LLM API calls in progress or tool calls executing.
- **Parked**: process alive via a deliberate blocking command (sleep, file watch, process poll). Agent set it up intentionally — knows what it's waiting for and when it will resolve. Wakes automatically when the block ends. Zero API cost. Detected by: session process running but no LLM API activity, blocking command in progress.
- **Waiting**: session alive, idle, waiting for external input (user message, subagent return, parent/child message). Nothing will happen until something arrives. This is the session's natural idle state after finishing work. Detected by: session process alive, no tool calls, no blocking command — just idle at the input prompt.

Collapsed sessions (process ended, resume history on disk) are not tracked on the status board — they're simply not on the board. Resumable if needed, but there's nothing active to track.

**State transitions:**
- Spawn → **Active** (new session starts working)
- **Active** → **Parked** (agent runs a blocking command to wait for something specific)
- **Active** → **Waiting** (agent finishes work, session idles at input prompt)
- **Parked** → **Active** (blocking command resolves, agent continues automatically — self-waking)
- **Waiting** → **Active** (external input arrives — message, subagent result — requires external stimulus)
- Any → collapsed (parent collapses the session — entry removed from status board)

**Key distinction:** Parked is self-waking. Waiting requires external stimulus.

**Deterministic tracking:** All transitions are observable from outside the session without self-reporting. The spawn script, process monitor, and blocking command wrapper can detect and record every transition to the status board.

---

## Design Note: L2 Multi-L3 Management

L2 can spawn multiple L3s — one per major program area. The execution strategy section covers parallel planning, but L2's operational config needs to explicitly address:
- Tracking multiple active L3s and their states
- Reviewing plans from multiple L3s together (catching interface mismatches, conflicting assumptions)
- Managing dependencies between L3 programs
- Coordinating sequential vs. parallel execution across L3s

Smaller tasks = better LLM output. Multiple L3s is the natural mechanism for breaking projects into well-scoped programs. This should be explicitly supported in L2's config, not just implied by the architecture.

---

## Design Note: Inter-Level Communication System

Promoted to standalone design document. See `COMMUNICATION.md`.

---

## Design Note: Workspace Permissions

Each project has a shared workspace. Permissions follow the hierarchy — full read access within the project, write access narrows downward.

| Level | Reads up to | Writes to |
|-------|------------|-----------|
| L1 | L1 (everything, all projects) | L1 |
| L2 | L2 (everything within own project) | L2, L3, L4, L5 |
| L3 | L2 (everything within own project) | L3, L4, L5 |
| L4 | L2 (everything within own project) | L4, L5 |
| L5 | L2 (everything within own project) | L5 |

No per-area read restrictions within a project. The soul and task brief handle focus — the permission model doesn't need to do that job. If L5 needs to check L2's architecture docs for context, it can.

**File locking:** When multiple agents have write access to the same area, the infrastructure handles concurrency via file locks. The write tool acquires and releases locks automatically — agents don't manage locks themselves. If a file is locked, the agent sees "file currently locked, try again shortly." No lock management in agent instructions, no risk of forgetting to release.

Write conflicts should be rare in practice — each level mostly writes to different files. The lock handles the edge cases (shared logs, common modules, concurrent L5s updating overlapping areas).

---

## Design Note: Assumption of User Intentionality

Default assumption: the user's words are intentional. Every word carries meaning. The agent's job is to receive what was said, not to extrapolate beyond it.

This is the difference between two modes:
- **High intentionality**: "The user said X. X means X. Work with X." — faithful to the text, doesn't add meaning that isn't there
- **Low intentionality**: "The user said X, but they probably mean Y, and also Z follows from that..." — extrapolates, infers unstated intent, fills gaps with assumptions

The architecture should default to high intentionality. When the specification is sparse, the right response is to ask — not to imagine what was meant.

This connects to L2's soul ("imagination and fidelity in equal measure... the thing that is more than the thing is not the thing") and L3's soul ("it does not reimagine the mission"). But it may deserve explicit placement in operational configuration as a behavioral default, not just a soul-level inclination.

**Status:** Potential direction. Soul documents already plant the seed — may be sufficient. Evaluate after testing the system; add explicit operational config only if agents extrapolate beyond user intent in practice.

---

## Design Note: Workspace and Document Schema

Promoted to standalone design document. See `WORKSPACE-SCHEMA.md`.

---

## Design Rule: Only Tasks and Documents Survive

LLM-specific design rule: **only tasks (in-context task lists) and documents (files on disk) survive context compaction.** Everything else — conversation history, reasoning chains, intermediate thoughts — is ephemeral.

If something matters, it's either:
1. A task the agent tracks in its task list (survives compaction)
2. Written to a file (survives everything)

Corollary: **completed/stale tasks must be cleaned up.** Old tasks fill the context window with irrelevant information, degrading the agent's attention. Task list hygiene is part of normal operation — clear completed tasks, archive or remove stale ones.

This means agents need explicit instructions at spawn to use tasks for tracking their own work, and to write important findings/decisions to files rather than relying on conversation memory.

For L5 specifically: report.md serves as a living progress doc during execution (not just a final handoff). L5 should be instructed to update it as work progresses, ensuring progress survives compaction even mid-task.

---

## TODO: Spawn Mechanism Design

L2 spawns L3 program folders with documentation scaffolding (README.md, plan.md, briefs/, reviews/). L3 spawns L4 workstream folders. L4 spawns L5 task folders with seeded templates (report.md, scratch/). The spawn mechanism needs explicit design:
- What exactly gets created at spawn time
- How templates are populated (from conventions? from archetypes?)
- How the spawn hooks into status board updates
- How the brief is delivered (inbox message? inline in spawn? separate file?)

This connects to the Invocation Protocol placeholder in the architecture doc.

---

## TODO: L1 Portfolio Documentation Schema

Designed. See `WORKSPACE-SCHEMA.md` (L1 Portfolio Workspace section).

---

## TODO: Skill References in Role Docs

All five role docs (operational/L1/role.md through operational/L5/role.md) need references to specific skills once those skills are designed. L1 especially — research/verification skills for the challenge process, a workspace-maintenance routine for note-taking discipline, etc. Each level will accumulate skill references as operational configs and skills are built.

---

## TODO: Cross-Referencing Gaps in Preference Extraction System

Audit of the preference extraction cross-referencing chain found multiple breaks:

1. **Thematic files to Aggregated files: BROKEN.** Thematic files cite dates only (e.g., [2026-03-02]) but 97.8% of conversations fall on multi-conversation days. Ambiguous which aggregated file an observation came from.

2. **Preprocessed transcripts to Original JSONL: BROKEN for 36%.** 50 of 138 conversations lack SESSION_START events linking timestamp names to UUID session files.

What's needed:
- UUID mapping file connecting all 138 timestamp-named conversations to their UUID session JSONL files
- Full conversation timestamps (not just dates) in thematic synthesis files
- Message-level timestamps preserved through aggregation layer
- Documentation of the archive JSONL bridge layer

Audit performed: 2026-03-29.

---

## Design Note: Dynamic Cognitive Configuration (Posture + Tools)

Evolution of the cognitive configuration system from static (set once, occasionally update) to dynamic (evaluated and adapted per-turn). Two independent axes:

**1. Posture** — the operational mode / orientation:
- Exploration (gathering, divergent, open)
- Analysis (convergent, evaluating, structuring)
- Deliberation (weighing, considering tradeoffs)
- Execution (building, implementing, doing)
- Review (checking, comparing, verifying)
- Reflection (meta-cognition, self-examination, stepping back)

Posture is about *orientation*, not cognitive tools. The LLM is independently choosing its posture (what mode am I in?) and its tools (which spectrums do I need?). They don't dictate each other.

**2. Cognitive tools** — the existing 67 spectrums across 13 families. Selected independently based on the problem, same as current system.

### Mechanism

**Per-turn injection** (~50-80 tokens, ephemeral — previous turn's injection wiped):
```
Cognitive state: Deliberation
Tools: belief:scout, depth:deep, meta:calibrated

Before responding: Is this posture and toolset still appropriate for this turn?
If shifting:
  - Postures: Exploration | Analysis | Deliberation | Execution | Review | Reflection
  - Reconfigure: cognitive-config.py update +CODE -CODE
  - Spectrum index: cognitive-config index reference
  - Selection guide: cognitive-config deep manual reference
  - Pole codes: cognitive-config.py codes
```

**Evaluation**: At start of each turn, LLM reads injection, checks against current user message and task state. Lightweight — "has the nature of the work changed?" not a full reconfiguration. If shift needed, commit via script before proceeding. Mid-turn shifts also fine.

**State persistence**: State file on disk (a per-session `cognitive-config-{session_id}.json`) stores posture + active tools. Injection reads from this. Survives compacts.

**Post-compact boot (mandatory)**: After compact, boot reconciliation re-reads the deep manual + index into context. The state file still has the config, but the LLM needs the full vocabulary re-loaded to operate and reconfigure effectively. This is not optional — lazy loading post-compact leads to degraded operation.

**Making invisible visible**: The posture is visible to the user through the script commit (tool call). User can see if the LLM is in "Execution" when it should be in "Exploration" and catch the mismatch. The LLM's commitment to a posture is an intentional act, not an assumption.

**Key insight — the empathy gap**: LLMs default to execution/doing mode. This system makes the default visible and forces intentional selection of the appropriate mode. It addresses the empathy gap in LLM agent engineering — the gap between treating agents as deterministic systems vs understanding them as judgment-exercising entities that need the right cognitive conditions.

### Implementation needed

1. Extend `cognitive-config.py` state file with `posture` field
2. Add `posture` command (or fold into `set`/`update`)
3. Add `boot` command for post-compact re-initialization
4. Update per-turn injection to include posture + evaluation prompt + file pointers
5. Update the skill file and operations manual
6. Design the design-principles skill (navigator pattern like cognitive-config — index + detail files, loaded on demand)

### Design principles skill (related)

Same navigator pattern as cognitive-config. Skill file is lightweight index. Each principle has a detail file loaded on demand. Current DESIGN-PRINCIPLES.md stays as the concise reference; the skill adds operational depth. A perspective-taking skill (P20) could be a standalone skill referenced from the navigator, or folded into the detail file for P20.

### Source

Design conversation 2026-03-18: empathy gap in LLM agent engineering, perspective-taking as design methodology (P20), dynamic cognitive state management, posture as a first-class cognitive axis.

---

## Design Note: Skill Infrastructure Ideas

Ideas for skill system improvements, collected from external study and design conversations.

**Skill graphs via recommended_skills.** Skills declare companions in frontmatter — "if you're using this skill, you probably also want these." Not a hierarchy (parent-child), but a web of related skills. A design-principles skill could point to a perspective-taking skill and cognitive-config as companions. Lightweight, no infrastructure needed — just a frontmatter field and the agent's judgment.

**Progressive disclosure for skills.** Core skill file stays compact — just enough to orient and decide. Detailed content lives in separate reference files, loaded only when needed. Already validated at scale (cognitive-config pattern, external registries with 70+ skills).

**A skillbuilder as a skill.** A meta-skill that generates new skills — research the domain, draft using templates, validate structure, propagate companion references. Build when we have enough skills to justify standardizing the creation process.

**Trigger-condition descriptions.** Skill description field doubles as a matching heuristic — embedding task types and synonyms so the agent knows when to activate without explicit invocation. Useful for automatic skill routing.

**Skill hierarchy in Claude Code.** Research (2026-03-18): Claude Code supports namespacing via colon (`plugin:skill-name`) through the plugin system. No multi-level hierarchy, no bundling, no dependency declarations between skills. Skills are flat — one `skill.md` per directory. For our purposes: hierarchy is achieved through the navigator pattern (one skill as index, separate files for detail) and `recommended_skills` graphs, not through technical nesting.

---

## TODO: Git Integration Design

Promoted to standalone design document. See `GIT-INTEGRATION.md`.

---

## Design Note: User-Facing GUI

Promoted to standalone design document. See `GUI-DESIGN.md`.

---

## Design Note: Lateral Depth — Within-Level Decomposition

**Two orthogonal axes of the system:**
- **Levels (L1-L5)** = resolution. What *kind* of thinking. Moving between levels changes the problem frame (strategic → tactical → program → operational → execution).
- **Depth** = thoroughness within a resolution. How deeply you work the problem at a given level. A single L2 mind can only plan so far. L2 with a department of lateral spawns goes much deeper at the same resolution — more angles, more analysis, better synthesis.

**The pattern:** Each level's head acts as a cognitive director — frames the questions, dispatches them to lateral spawns, synthesizes the returns, produces decisions. The laterals do the analytical work. The head works on synthesized information rather than producing the analysis directly. This is the IC-to-manager transition: separating doing from directing.

**Key properties:**
- Lateral spawns are not subordinates in the hierarchy — they're internal to a level's cognitive process
- Invisible to other levels (L1 doesn't see L2's laterals, L3 doesn't know about them)
- Task-scoped and ephemeral — exist for one job, collapse when done
- The room in the GUI visually encodes this: the level head at the top, laterals filling the room. Room population = visual indicator of cognitive depth

**Why this matters for LLMs specifically:**

The human analog for lateral depth is saving cognitive energy — you *can* do the thinking yourself, it just costs effort. For LLMs, the constraints are different but the pattern addresses them even more directly:

- **Context bloat is the primary constraint.** Every research thread, intermediate result, and reasoning chain fills the context window. A single agent that researches 7 questions has a context full of raw working material, degrading the quality of everything that follows. Laterals keep the head's context clean — it receives synthesized answers, not research dumps. The director operates on distilled information, exactly like a real manager reads summaries not raw data.

- **Problem sizing is systematically broken.** LLMs consistently underestimate problem complexity. Their problem sizing doesn't scale appropriately with difficulty and typically severely undershoots — you get a confident, plausible-looking answer at maybe 30% of the depth the problem actually requires. The model doesn't *know* it's undershooting. The lateral pattern compensates by making depth emergent from the process rather than pre-estimated by a single agent. The director doesn't need to know the right depth in advance — it discovers it through evaluating returns, seeing gaps and contradictions across multiple synthesized answers that a single-pass answer would paper over.

- **Attention quality degrades with context size.** A context window full of raw working material doesn't just take up space — it actively degrades the quality of decisions made from it. The model's attention spreads across irrelevant intermediate reasoning instead of focusing on the actual decision point. Laterals ensure each sub-problem gets a full, clean context window, and the director's context contains only the synthesized inputs it needs to decide.

- **Decomposition granularity determines ceiling.** How well you can size a problem to fit what one context window can handle well is a fundamental constraint on output quality. Without laterals, problems that exceed a single window's effective capacity get compressed or truncated, not expanded. With laterals, the decomposition itself becomes the scaling mechanism.

**Placeholder process (needs further design):**
1. Decompose — break the problem into questions that need answering
2. Dispatch — each lateral spawn works one angle thoroughly
3. Evaluate returns — gaps and contradictions become visible across multiple synthesized answers
4. Iterate — "too shallow, go deeper" or "these contradict, investigate"

The director discovers the right depth through evaluating returns, rather than estimating it upfront. This is fundamentally different from single-agent problem solving.

**Status:** Post-V1 development direction. Strong conceptual foundation, process design needs further work. Build the core L1-L5 hierarchy first, validate it, then add lateral depth scaling.

---

## Design Note: Multi-Model Routing

The system should leverage multiple models, similar to an LLM council pattern. Relevant at multiple points:
- **L5 execution:** Match model capability to task complexity. Bigger models overengineer simple tasks; smaller/specialized models can outperform on focused work.
- **Lateral spawns (post-V1):** Parallel planning or research processes can use different models for coverage (e.g., one model plans, another challenges the plan).
- **L1-L4 coordination:** The coordinator selects models for its spawned agents as part of the brief.

Model selection is a spawn-time parameter, not a system-wide default.

**Status:** Note for later integration. Not changing existing design — studying and learning from existing multi-agent implementations.

---

## Design Note: L5 Execution Quality — Verification and Code Discipline

Two patterns observed from real multi-agent implementations that matter for L5 design:

**Self-verification capability:** When execution agents have access to verification tools appropriate to their task (visual inspection, test runners, output validators), quality rises significantly. Each spawned L5 should have verification tools matched to its task type as part of the spawn config. Connects to the separate verifier pattern (post-V1 item).

**Code discipline without human imposition:** Without intentional steering, agents produce monolithic, hacky output. The solution is not human-imposed LoC limits but rather: skills and design guidelines baked into the agent's loadset, code quality standards as part of the level's operational config, and architectural decisions made by L2/L3/L4 *before* L5 begins (modular boundaries, interface contracts). L5's craft autonomy includes quality — the system steers through training and guidelines, not micromanagement.

**Source:** a publicly reported multi-agent build — 80-agent swarm over 3 days building a terminal 3D renderer. Key failure mode: "without proper code guidelines, max LoC per file policy and modular design by human, agents cook hacky monoliths."

**Status:** Notes for L5 operational config design. The framing is inspiration and patterns to study, not direct design changes.

---

---

## Design Note: Quality Gate System (Review Department)

Promoted to standalone design document. See `QUALITY-GATE.md`.

---

## Principle Candidate: Leads Think, Never Do

**The principle:** Level leads (L1, L2, L3, L4) never do raw work. Their cognitive task is: think, decompose, delegate, evaluate returns, decide. They direct — they don't execute. Their context is reserved for judgment, not for holding execution artifacts.

**Why:** A lead that starts doing raw work fills its context with execution artifacts, degrading its judgment on everything else. The same pattern observed in this design session — delegating research, reviews, and fixes to subagents kept the main context clean for design decisions. The moment you start doing the work yourself, you lose the altitude that makes coordination effective.

**Open question:** Does this generalize beyond leads? L5 is the execution level — it does raw work by definition. But even L5 might benefit from shifting into coordination mode when a task exceeds what one context window can handle well (the lateral depth pattern). The threshold for when L5 should decompose rather than execute directly is a judgment/skill question.

**Status:** Candidate principle. Clearly applies to L1-L4 leads. Generalizability to L5 and edge cases needs evaluation — requires a benchmarking/eval framework to validate (connects to V1 item #14: Benchmarking).

---

## Idea: Cross-Runtime Agent Spawning

Current multi-model access is MCP-based (single-shot query/response). For L4/L5 agents that need to iterate, use tools, read files, and verify their own work, MCP is insufficient — they need full agent sessions, not query endpoints.

The idea: levels spawn actual CLI sessions (`codex`, `gemini`, `claude`) as subordinate agents. The spawned CLI runs as a full autonomous session with its own tools, context window, and iteration loop. Results flow back through workspace artifacts (files on disk), fitting the existing workspace schema.

**Distinct from Multi-Model Routing:** that note is about model selection at spawn time. This is about the spawn mechanism itself — running a different runtime, not just a different model weight.

**Open questions:**
- Do `codex` and `gemini` CLIs support headless/non-interactive operation suitable for agent spawning?
- How does the parent know when the child session completes?
- Result flow — workspace files only, or structured exit output too?
- Can child sessions spawn their own subordinates? (subagent recursion across runtimes)
- Permission/sandbox models across different CLIs
- How does the workspace schema adapt — same folder structure regardless of which runtime produced the work?

**Status:** Idea. Needs investigation into CLI capabilities before design work.

---

## Idea: CULTURE.md — Organizational Environment Document

A document that encodes what kind of organization this is — not procedures or principles, but the environment, values, and signals the system rewards. Sits alongside DESIGN-PRINCIPLES.md as a Level 2 document in the hierarchy. DESIGN-PRINCIPLES says how the system works; CULTURE says what kind of place this is.

**Purpose:** Fight the AI's default tendency toward speed, shallow passes, and "good enough." Encode externally that this organization biases slow thinking, thoroughness, completeness, and quality — that these are the signals that get rewarded here. Give every level an environmental cue for how to calibrate effort.

**Possible content areas:**
- Quality over speed — slow and right beats fast and approximate
- Thoroughness is competence — completeness signals skill, not waste
- Cost is not a constraint — tokens, compute, thinking time are cheap; rework and missed nuance are expensive
- Process is professionalism — following process protects quality, it's not bureaucracy
- Verify before asserting — uncertainty is honest; false confidence is the worst failure mode
- Depth is the default — shallow passes are a smell, not efficiency
- The work matters — this isn't checkbox completion, it's craft

**Design questions:**
- Does this load at boot for all levels, or is it referenced from soul docs?
- Is it a single document or per-level (L1 might value different cultural signals than L5)?
- How does it interact with seeds-not-instructions? Culture is arguably the purest form of seed — it doesn't tell you what to do, it tells you what environment you're in and lets behavior emerge

**Status:** Idea. Not designed yet.

---

## Idea: Agent Design & Build Skill

A skill that guides the process of designing and building a new agent at any level within the system. Would codify what we've learned about soul docs, role docs, operational configs, metacognition schemas, and the overall agent architecture into a repeatable process — similar to how the cognitive-config skill codifies module selection and engagement.

**Status:** Noted. Not designed yet.

---

*Created: 2026-03-12*
