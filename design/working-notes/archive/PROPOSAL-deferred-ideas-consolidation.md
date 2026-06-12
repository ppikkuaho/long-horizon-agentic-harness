# Proposal: Deferred Ideas Consolidation

*Consolidated inventory of all deferred, future, post-V1, and unactioned ideas across the AI architecture project. Research and collation only -- no changes proposed to existing files.*

*Generated: 2026-03-16*

---

## Table of Contents

1. [Consolidated Ideas by Category](#1-consolidated-ideas-by-category)
2. [Recommendations: Where This List Should Live](#2-recommendations-where-this-list-should-live)
3. [Project Folder Organization Assessment](#3-project-folder-organization-assessment)
4. [Proposed Changes Summary](#4-proposed-changes-summary)

---

## 1. Consolidated Ideas by Category

### A. Architecture -- Open Design Work (Structural Decisions)

These are the items from the ARCHITECTURE.md "Open Design Work" section and NOTES.md TODOs that represent unresolved structural decisions needed before or during V1 implementation.

#### A1. Invocation Protocol + Spawn Mechanism
- **Source:** ARCHITECTURE.md, line 327; NOTES.md, lines 367-375
- **Description:** How levels spawn the level below. Includes exact mechanism for spawning (subagent, background process, etc.), how the brief is structured, how bootstrapping works at each level boundary, documentation scaffolding at spawn time, how templates are populated, how spawn hooks into status board updates, how the brief is delivered.
- **Status:** PLACEHOLDER in architecture doc. TODO in NOTES.md.
- **Related:** L2 Multi-L3 Management (A3), Execution Strategy (NOTES.md lines 58-71)

#### A2. Concurrency Mechanics
- **Source:** ARCHITECTURE.md, lines 226-228, 327 (item 6)
- **Description:** Exact instance cap, how active instance count is tracked and queried, whether Claude Code has subscription-level throttling to account for, how L1 uses capacity data in routing decisions. Primary resource constraint is number of parallel instances (likely 20-64, to be determined empirically).
- **Status:** PLACEHOLDER in architecture doc.
- **Related:** Multi-Account Orchestration (E2), Resource Awareness section

#### A3. Agent Lifecycle Mechanics
- **Source:** ARCHITECTURE.md, lines 229-243, 329 (item 7)
- **Description:** How persistence is implemented (background sessions? parked processes?), how message routing works to persistent agents, how context windows are managed for long-lived agents, maximum lifetime before forced refresh.
- **Status:** PLACEHOLDER in architecture doc.
- **Related:** Agent Awareness / State Tracking (A5)

#### A4. Timeout and Failure Design
- **Source:** ARCHITECTURE.md, lines 258-261, 330 (item 8)
- **Description:** Specific timeout values per level, how to prevent cascading failures (one stuck instance triggering a chain of timeout escalations), circuit-breaker patterns if needed.
- **Status:** PLACEHOLDER in architecture doc.

#### A5. Agent Awareness -- State Transition Design
- **Source:** NOTES.md, lines 119-154
- **Description:** Define the exact conditions/triggers for each state transition (Active, Parked, Waiting) and the infrastructure hooks that detect them. Collapsed sessions are not a tracked state — they're simply removed from the status board. Promoted to V1 because the inbox/communication system requires it. Infrastructure-tracked, not self-reported.
- **Status:** TODO in NOTES.md (line 153). Partially designed (state definitions exist, transition triggers do not).
- **Related:** Agent Lifecycle (A3), Communication System

#### A6. Git Integration Design
- **Source:** NOTES.md, lines 390-404; ARCHITECTURE.md, line 331 (item 9)
- **Description:** Branch strategy (L4 task branches, L3 workstream branches, main as truth), PR-as-review mechanism, merge conflict protocol, what stays outside git (status board, inbox), agent git instructions (branch naming, commit format, when to push), file locking replaced by git merge, immutability enforcement via history, append-only verification.
- **Status:** TODO in NOTES.md. Listed as open design work in ARCHITECTURE.md.

#### A7. L1 Portfolio Documentation Schema
- **Source:** NOTES.md, lines 379-387; ARCHITECTURE.md, line 332 (item 10)
- **Description:** L1's workspace is portfolio-level, not project-scoped. Needs: project registry, cross-project status view, resource allocation / capacity tracking, user communication artifacts, how L1's workspace relates to per-project workspaces.
- **Status:** TODO in NOTES.md. Listed as open design work in ARCHITECTURE.md.

---

### B. Architecture -- Level Configurations (Per-Level Design)

These items fill in once the architecture skeleton is set. Highly iterative.

#### B1. L1-L4 Level Operational Configurations
- **Source:** ARCHITECTURE.md, lines 31, 37-38, 43, 49, 338 (item 11)
- **Description:** Personality, behavioral design, tooling, metacognition schema per level. Soul documents (first drafts) are complete. Operational configs need the architecture slots to exist first. L1 is the most critical -- its core competency is communication, and communication design is the primary design surface.
- **Status:** PLACEHOLDERs in ARCHITECTURE.md for each level. Soul docs exist as first drafts.
- **Related:** Metacognition Schemas (B2), Soul Documents (L1-L4)

#### B2. Metacognition Schemas Per Level
- **Source:** ARCHITECTURE.md, line 339 (item 12); DESIGN-PRINCIPLES.md, line 209; SESSION-2026-03-10.md (voice notes)
- **Description:** Each level needs its own mental models, skillsets, rubrics, and behavior design -- what "good judgment" looks like at that level. Upper levels need strategy/organization/communication skills. Lower levels need concrete LLM skills and verification loops. Designed to be highly iterative. Infrastructure must make reconfiguration easy (principle 16).
- **Status:** Listed as open design work, separate workstream. Voice notes explicitly call this out as a key design area.

#### B3. Time Awareness
- **Source:** ARCHITECTURE.md, line 341 (item 13); DESIGN-PRINCIPLES.md, line 207
- **Description:** Can L2 schedule and pace work across days? Stretch tasks to fit timeframes, divide compute between sessions? This would enable L2 to manage project timelines, not just task decomposition.
- **Status:** Open question in both documents.

#### B4. User Profile Document
- **Source:** NOTES.md, lines 32-35; ARCHITECTURE.md, line 341 (item 14)
- **Description:** A profile of the user referenced by soul documents and level configurations. L1 especially needs to know who it's working with. Not a personality spec -- whatever context the levels need to orient around the user effectively.
- **Status:** TODO in NOTES.md. Note: the preference-extraction work (full-preference-spec.md) largely covers this territory but was produced independently and hasn't been formally integrated.
- **Related:** Preference Extraction synthesis (full-preference-spec.md)

#### B5. Connect Generative Skeleton to Architecture
- **Source:** ARCHITECTURE.md, line 342 (item 15)
- **Description:** The decomposition method from cognitive-space-framework.md is relevant to L2's planning approach. Connect that methodology to L2's operational configuration.
- **Status:** Deferred.

---

### C. Architecture -- Product / UX

#### C1. User Interface / Navigation / GUI
- **Source:** ARCHITECTURE.md, line 346 (item 16), line 288; NOTES.md, lines 407-418; SESSION-2026-03-10.md (voice notes: "Visual front-end needed"); ideas-inbox item #13
- **Description:** The terminal is great for input but poor for state representation. The GUI is for the user, not for the agents. Claude Code remains the backbone. The GUI is a lens over the same filesystem and agent infrastructure. Design for the end state, build iteratively. The workspace schema (project folders, status board, inbox, living docs) is already the data layer.
- **Open question (NOTES.md line 415):** Could the GUI also improve agent orientation? L1/L2 face similar state-representation challenges.
- **Related resources:** ideas-inbox item #13 ("Chat Box is a Terrible Interface for AI Agents" -- workspace/dashboard over chat)
- **Status:** Early design. Multiple sources confirm this as a future workstream.

#### C2. Multiple L1 Design
- **Source:** ARCHITECTURE.md, lines 280-287, 347 (item 17); DESIGN-PRINCIPLES.md, line 208
- **Description:** Separate L1s anticipated for: personal/life domains (health, life admin -- different function, different structure), Internal Affairs (system observation, process improvement, meta-analysis -- its "projects" are the system itself). These may not need the same L1-L4 structure.
- **Status:** Listed as separate design tasks. Not started.

#### C3. Benchmarking
- **Source:** ARCHITECTURE.md, line 348 (item 18); DESIGN-PRINCIPLES.md, line 210; SESSION-2026-03-10.md (voice note: "we can't really know what works without a benchmark system")
- **Description:** How to measure whether the system works better than flat dispatch. Without measurement, improvements are guesswork. Voice notes emphasize this as a hard problem.
- **Status:** Listed as open design work. No design started.

---

### D. Architecture -- Research Directions and Future Exploration

#### D1. Organizational Design Literature Survey
- **Source:** NOTES.md, lines 7-20
- **Description:** Selectively survey org design literature for patterns that port well to this architecture. Areas identified: risk/verification frameworks, information compression between management layers, delegation failure modes, span of control research, decision rights frameworks (RACI adapted for LLMs), organizational learning / knowledge management, process improvement methodologies (lean, six sigma -- what ports vs. what's human-artifact).
- **Status:** Listed as "Future work." Not started.
- **Related:** Principle 10 (Organizational Theory as Research Corpus)

#### D2. LLM Self-Managed Context
- **Source:** NOTES.md, lines 24-28
- **Description:** Prior work on letting LLMs manage their own context windows -- deciding what to keep, compress, discard. Directly relevant to drift/context-loss problem. If levels can actively manage what stays in context rather than relying on blind compacts, drift from context loss becomes less likely. Find the prior art. Evaluate whether the pattern ports -- could each level manage its own context as part of normal operation?
- **Status:** Listed as "Future work." Not started.
- **Related:** Drift Detection (ARCHITECTURE.md section 7), Agent Lifecycle (A3)

#### D3. Sibling Communication (Lateral Agent Communication)
- **Source:** NOTES.md, lines 38-43
- **Description:** Could agents at the same level communicate directly? E.g., two L3s under different L2s sharing information about overlapping concerns, or two L4s coordinating on interdependent tasks. Would require real-time visibility into what agents are active across projects. Interesting possibilities but adds significant complexity.
- **Status:** Explicitly deferred to post-V1. Design from real needs -- start by observing where sibling communication would have been useful in practice.

#### D4. User-Initiated Conversational Mode -- Open Questions
- **Source:** NOTES.md, lines 93-116
- **Description:** The user bypassing levels to work directly with a specific level. Several open questions remain:
  - How does the user signal conversational mode vs. normal delegation? Explicit or inferred?
  - What happens to in-flight work when the user hijacks a level mid-execution?
  - Does the conversational session's content feed back into process artifacts, or is it a sidebar?
  - What does "L1 stays aware" look like mechanically? Notification? Shared log?
  - What does backfill look like? Structured handoff document? Summary injected into parent's context?
- **Status:** Partially resolved (L1 stays aware, bypassed levels get backfilled). Open questions remain on mechanics.

#### D5. ReAct vs. Plan-and-Execute Architecture Patterns
- **Source:** ideas-inbox item #11
- **Description:** Two key agent architecture patterns (ReAct for uncertain tasks, Plan-and-Execute for predictable workflows). Advanced systems combine both. Key insight: choosing the right level of structure for the uncertainty level. Could inform how L2/L3 choose execution strategies.
- **Status:** Reference material captured. Not integrated into architecture.

#### D6. Treat All AI Context Like a Unix File
- **Source:** ideas-inbox item #8
- **Description:** Paper proposing Unix file abstractions for managing AI agent context. Could inform the workspace/filesystem design.
- **Status:** Reference link captured. Paper not yet read or evaluated.

---

### E. Architecture -- Infrastructure and Tooling Ideas

#### E1. Single CLI Tool vs. Function Calling (Manus Pattern)
- **Source:** ideas-inbox item #5
- **Description:** Former Manus backend lead argues that a single `run(command="...")` tool with Unix-style commands outperforms a catalog of typed function calls. Key insights: Unix text streams and LLM tokens share the same interface model; CLI is densest tool-use pattern in training data; pipe composition replaces multiple tool calls; progressive `--help` discovery beats stuffing docs into system prompts; two-layer architecture separating Unix execution from LLM presentation.
- **Status:** Reference material captured. Could inform L3/L4 tool interface design.
- **Links:** https://www.reddit.com/r/LocalLLaMA/comments/1rrisqn/, https://github.com/epiral/pinix

#### E2. Multi-Account Subscription Orchestration
- **Source:** ideas-inbox item #4
- **Description:** Managing multiple Claude subscriptions: balance usage limits and auto-switch between subscriptions (LLM-driven and deterministic), handle MCP login/integrations and Chrome extension tied to logged-in account.
- **Status:** Noted. Infrastructure problem for scaling the system.

#### E3. Backend Layer for Claude Code Agents (6 Primitives)
- **Source:** ideas-inbox item #14
- **Description:** Someone built a backend layer providing 6 primitives for Claude Code agents to manage backend operations end-to-end.
- **Status:** Reference link captured. Not evaluated.
- **Links:** https://www.reddit.com/r/ClaudeAI/comments/1rtddzb/

#### E4. Long-Running Agent Harness Patterns (Anthropic Engineering)
- **Source:** ideas-inbox item #6
- **Description:** Anthropic's engineering blog on harnesses for agents across multiple context windows. Patterns: initializer agent + coding agent, feature list in JSON with status tracking, git commits + progress files for session recovery, startup protocol (check working dir, read progress, select next task), browser automation for end-to-end testing.
- **Status:** Reference link captured. Directly relevant to agent lifecycle / session recovery design.
- **Links:** https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents

#### E5. Get Physics Done (GDP) -- Agentic Research Loops
- **Source:** ideas-inbox item #7
- **Description:** Open-source MCP-based agentic research system with phased execution (formulation, planning, execution, verification), task dependency management, wave-based parallelization, research memory, artifact generation, rigorous validation.
- **Status:** Reference material. Exemplar of domain-specific agentic system with phased workflows. Could inform L2/L3 execution strategy design.
- **Links:** https://github.com/psi-oss/get-physics-done

---

### F. Architecture -- Agent Skills and Capabilities

#### F1. Escalation, Leadership, and Problem-Solving Skills for Agent Managers
- **Source:** ideas-inbox item #1
- **Description:** When a lower-level agent hits a block, the manager should not just say "try harder" but: (a) interrogate the associate's process, (b) consider parallel approaches, (c) consult lateral experts (Codex, Gemini), (d) offer different tools, (e) correct the associate's approach. Each level needs leadership skills, prompt writing/design skills, knowledge of typical AI failure modes, and structured problem-solving methodologies packaged as validated skills.
- **Status:** Noted in gmail self-notes. Directly relevant to B1 (level configurations) and B2 (metacognition schemas).

#### F2. L1 Pre-Work Research Team
- **Source:** ideas-inbox item #2
- **Description:** L1 needs its own pre-work/pre-spec research team that operates before engagement. Research phase before delegation.
- **Status:** Noted. Connects to L1's design as the managing partner.

#### F3. Discussive L1 Branch (Branching Discussion Pattern)
- **Source:** ideas-inbox item #3
- **Description:** A separate L1 branch that is discussive (for problem work), using a branching discussion with an L1 copy subagent. Keeps main context window clean and avoids earlier context influencing later questions.
- **Status:** Noted. Relates to User-Initiated Conversational Mode (D4) and context management.

#### F4. "What Does a Good Answer Look Like" System
- **Source:** ideas-inbox item #3
- **Description:** A separate system that evaluates answer quality -- given a question, what areas/topics does a good answer need to cover conceptually? Quality evaluation of outputs against a pre-defined coverage model.
- **Status:** Noted. Could inform L2/L3 verification and quality gating.

#### F5. Separate Verifier Agent Pattern
- **Source:** ideas-inbox item #9
- **Description:** Formal verification agent/bot: use a separate verifier (not the executor) that compares ground truth with output, describes differences, and may not even pass judgment -- just reports differences. For visual/uneven tasks, use multiple verification passes.
- **Status:** Noted. Directly relevant to L3's verification role and L4's self-verification.
- **Related:** Trust by Default, Verify by Exception (Principle 4)

#### F6. Atomic Skills + Skill/Prompt Builder
- **Source:** ideas-inbox item #10
- **Description:** Codify specific atomic functions (verification, etc.) as skills. Have workflows invoke individual skills. Build a skill/prompt builder and explain the thinking to Claude. Composable skill architecture for agents.
- **Status:** Noted. Connects to loadset design in the Invocation protocol (A1) and principle 16 (Designed for Evolution).

#### F7. Small Specialized Models for Atomic Tasks
- **Source:** ideas-inbox item #12
- **Description:** Capability density compressing fast (36-parameter transformer with 99%+ accuracy on 10-digit addition). Small specialized models could handle atomic agent tasks extremely efficiently. Not everything needs a frontier model.
- **Status:** Reference observation. Longer-term research direction.

#### F8. User-Level Audit Process / Behavioral Trace
- **Source:** ideas-inbox item #2
- **Description:** A readable trace showing "L1 kicks off to L2, L2 breaks the problem, delegates to L3s, L3s delegate to L4s, L4s get stuck, ask L3..." Essentially a behavioral trace of the multi-agent system for early system runs.
- **Status:** Noted. Relates to Observability (Principle 11) and GUI (C1).

---

### G. Cognitive Configuration and Process Improvements

#### G1. Cognitive Configuration Meta-Dimensions
- **Source:** cognitive-config-ideas.md (entire file)
- **Description:** Meta-configurations for how agents engage, not what they think about. Four dimensions explored:
  1. **Effort/Depth Toggle** -- self-declared thinking effort level with structural behaviors (not just "try harder"). Levels: minimal to ultrathink. Challenge: defining concrete behaviors per level.
  2. **Audience/Register** -- who you're writing for changes what counts as adequate.
  3. **Confidence Threshold** -- how sure you need to be before stating something (exploratory, operational, rigorous).
  4. **Scope/Horizon** -- how far out to think (tactical, strategic, civilizational).
- **Status:** Ideas to explore. Common design challenge noted: each dimension must be defined in concrete structural behaviors, not adjectives.
- **Related:** B2 (Metacognition Schemas), full-preference-spec.md mode switching

#### G2. Seeds, Not Instructions (Natural Alignment)
- **Source:** NOTES.md, lines 74-88
- **Description:** The soul documents are seeds, not instruction sets. Each defines a fundamental being whose natural desires are what the architecture needs. Close to principle-ready. May need to mature before formalizing as a design principle.
- **Status:** "Close to principle-ready. May need to mature before formalizing."

#### G3. Assumption of User Intentionality
- **Source:** NOTES.md, lines 241-257
- **Description:** Default to high intentionality -- "The user said X. X means X." When the spec is sparse, ask rather than imagine. Connects to L2 and L3 souls. Evaluate after testing whether agents extrapolate beyond user intent; add explicit operational config only if needed.
- **Status:** "Potential direction. Soul documents already plant the seed -- may be sufficient. Evaluate after testing."

#### G4. L2 Decomposition Depth Placement
- **Source:** NOTES.md, lines 46-55
- **Description:** L2's decomposition depth guideline ("decompose until strategic decisions are resolved, stop before tactical ones") needs explicit placement. Likely belongs in L2's operational configuration or the architecture doc's invocation section, not in the soul document.
- **Status:** Design note. Placement decision pending.

#### G5. Preference Extraction Integration
- **Source:** preference-extraction/synthesis/full-preference-spec.md, behavioral-profile.md, preference-gap.md, preference-spec.md
- **Description:** The comprehensive preference extraction (138 conversations, 732 chunks) produced detailed behavioral specifications, a cognitive disposition profile, and a preference gap analysis. These have not been formally integrated into the architecture design. They would inform: L1's communication design, all levels' behavioral defaults, the user profile document (B4), and cognitive configuration (G1).
- **Status:** Completed as standalone deliverables. Integration into architecture design not yet done.

---

### H. Documentation and Process Ideas from Preference Extraction Pipeline

#### H1. Pre-Filter Consolidation Pipeline Noise
- **Source:** preference-extraction/METHODOLOGY.md, lines 200-203
- **Description:** Future extraction runs should pre-filter automated consolidation processing (distinctive signature: system-level language, no user turns, repetitive reformatting). Would eliminate ~40% of chunks and ~130 wasted subagent runs.
- **Status:** Learning documented for future reuse.

#### H2. Signal Density Score Per Chunk
- **Source:** preference-extraction/METHODOLOGY.md, lines 205-207
- **Description:** Include a "signal density" field in extraction prompts to enable downstream weighting of high-density chunks.
- **Status:** Learning documented for future reuse.

#### H3. Confidence Field Per Observation
- **Source:** preference-extraction/METHODOLOGY.md, lines 209-211
- **Description:** Each extracted observation carries strong/moderate/weak confidence indicator for downstream weighting.
- **Status:** Learning documented for future reuse.

#### H4. Cross-Cutting Dimension in Thematic Clustering
- **Source:** preference-extraction/METHODOLOGY.md, lines 213-215
- **Description:** Separate "cross-cutting preferences" (apply everywhere) from "domain-specific preferences" (apply within one context) to reduce overlap in thematic documents.
- **Status:** Learning documented for future reuse.

#### H5. Conversation-Level Pre-Screening
- **Source:** preference-extraction/METHODOLOGY.md, lines 217-219
- **Description:** Lightweight pre-screening pass to classify conversations as high/medium/low expected signal density before running full extraction.
- **Status:** Learning documented for future reuse.

---

### I. External Research and Reference Material (Not Yet Evaluated)

These are links and references captured in the gmail scan that haven't been read, evaluated, or integrated but are marked as relevant.

#### I1. Anthropic Claude Certified Architect Study Guide
- **Source:** ideas-inbox item #15
- **Description:** PDF of Claude Certified Architect Foundations exam guide. May inform agent design patterns.

#### I2. Claude Code Best Practices (15K stars)
- **Source:** ideas-inbox item #16
- **Links:** https://www.reddit.com/r/ClaudeAI/comments/1rsyfdz/

#### I3. Karpathy Auto-ML Research Repo
- **Source:** ideas-inbox item #18
- **Description:** Automated ML research. Could inform autonomous research agent design.
- **Links:** https://www.reddit.com/r/AgentsOfAI/comments/1ro490o/

#### I4. ARC-AGI Solve Harness + Iterative Self-Improvement
- **Source:** ideas-inbox item #19
- **Description:** Iterative self-improvement patterns for AI agents.
- **Links:** https://x.com/noemon_ai/status/2029970173248049243

#### I5. B2B SaaS Growth Playbooks as Claude Skill
- **Source:** ideas-inbox item #20
- **Description:** Demonstrates skill packaging pattern for domain expertise.
- **Links:** https://www.reddit.com/r/ClaudeAI/comments/1rsgn90/

---

## 2. Recommendations: Where This List Should Live

### Current state

Deferred ideas are currently scattered across:
- NOTES.md (TODOs, Future work, Future exploration sections)
- ARCHITECTURE.md (Open Design Work section, PLACEHOLDERs inline)
- DESIGN-PRINCIPLES.md (Open Questions section)
- cognitive-config-ideas.md (standalone file)
- ideas-inbox-2026-03.md (raw scan output)
- SESSION-2026-03-10.md (implicit ideas in conversation)

This fragmentation means there is no single view of "what remains to be done" and no way to prioritize across categories.

### Recommendation

**Create a permanent `BACKLOG.md` at the project root.** This file should contain:

1. **Active design work** -- items that need to be resolved for V1 (categories A and B above). These are blocking or near-blocking.
2. **Post-V1 explorations** -- items explicitly deferred to after V1 (categories C, D).
3. **Research queue** -- external references and papers to evaluate (categories E, I).
4. **Methodology learnings** -- reusable patterns for future pipeline runs (category H).

The existing ARCHITECTURE.md "Open Design Work" section should be kept as a high-level summary with pointers to BACKLOG.md for details. PLACEHOLDERs in ARCHITECTURE.md should remain as inline markers showing where design work is needed.

NOTES.md should continue as a running design notes document (ideas, explorations, design rationale) but individual TODOs should be migrated to BACKLOG.md so there is one canonical place to check for outstanding work.

**Rationale:** A single backlog file prevents items from being forgotten across documents. The project is at a stage where active design work, deferred exploration, and reference material all need to be visible in one place to enable prioritization. The alternative -- leaving items scattered -- works fine when the project is small and you re-read everything each session, but this project has already grown beyond that point (14 files, 200K+ characters of content).

---

## 3. Project Folder Organization Assessment

### Current structure

```
ai-architecture/
  ARCHITECTURE.md              # Core architecture document
  DESIGN-PRINCIPLES.md         # Governing principles
  DOCUMENT-HIERARCHY.md        # Meta: how documents relate
  VISION.md                    # Why this exists
  L1-SOUL.md                   # Soul documents (4 files)
  L2-SOUL.md
  L3-SOUL.md
  L4-SOUL.md
  NOTES.md                     # Running design notes
  SESSION-2026-03-10.md        # Raw session transcript
  cognitive-config-ideas.md    # Standalone ideas file
  ideas-inbox-2026-03.md  # Gmail scan output
  reference/                   # External reference material
    anthropic-soul-doc.md
    anthropic-soul-doc-summary.md
  preference-extraction/        # Preference extraction project
    METHODOLOGY.md
    STRATEGY.md
    extraction-manifest.md
    aggregated/                # 138 conversation-level files + stage1/
    synthesis/                 # Final outputs (4 files)
    thematic/                  # 11 cluster files + CLUSTERS.md
```

### Assessment

**What works well:**
- The document hierarchy (Vision > Principles > Architecture) is clear and well-established
- Soul documents are appropriately at the root level (parallel to architecture, not subordinate)
- The `reference/` directory cleanly separates external material
- The `preference-extraction/` subtree is well-organized internally

**What could be improved:**

1. **Session transcripts and raw scans at root level.** `SESSION-2026-03-10.md` and `ideas-inbox-2026-03.md` are source material, not design documents. They add noise to the root directory alongside the core design docs. They would be better in a `sessions/` or `source/` directory.

2. **`cognitive-config-ideas.md` is an orphan.** It's a standalone ideas file with no clear relationship to the document hierarchy. Its content (meta-cognitive configuration dimensions) is part of the design work (B2, G1) and should either be absorbed into NOTES.md or moved to a dedicated `ideas/` or `explorations/` directory.

3. **No clear home for the backlog.** As argued in section 2, outstanding work items are scattered. A `BACKLOG.md` at root would solve this.

4. **`DOCUMENT-HIERARCHY.md` is redundant.** The same information appears in ARCHITECTURE.md (lines 3-20). The standalone file adds a maintenance burden with no clear benefit. The architecture doc's version is more authoritative.

5. **`preference-extraction/` is large and self-contained.** The 130+ aggregated files and 10+ stage1 files are intermediate pipeline data. The synthesis outputs (4 files) are the deliverables. The pipeline data could be archived or moved to `dev/preference-extraction/` (which is where the METHODOLOGY.md says the raw data lives anyway). The `preference-extraction/` directory in the project folder should contain only the deliverables and methodology.

### Suggested directory structure

```
ai-architecture/
  # Core design documents (the document hierarchy)
  VISION.md
  DESIGN-PRINCIPLES.md
  ARCHITECTURE.md
  BACKLOG.md                   # NEW: consolidated outstanding work
  NOTES.md                     # Running design notes (TODOs migrated to BACKLOG.md)

  # Soul documents (parallel artifact type)
  L1-SOUL.md
  L2-SOUL.md
  L3-SOUL.md
  L4-SOUL.md

  # Source material (moved from root)
  sources/
    SESSION-2026-03-10.md
    ideas-inbox-2026-03.md
    cognitive-config-ideas.md

  # External reference material (unchanged)
  reference/
    anthropic-soul-doc.md
    anthropic-soul-doc-summary.md

  # Preference extraction (trimmed to deliverables)
  preference-extraction/
    METHODOLOGY.md
    STRATEGY.md
    synthesis/
      full-preference-spec.md
      behavioral-profile.md
      preference-gap.md
      preference-spec.md
    thematic/                  # Keep: these are synthesis outputs
      CLUSTERS.md
      [11 cluster files]
    # aggregated/ and extraction-manifest.md -> stay in dev/preference-extraction/
```

---

## 4. Proposed Changes Summary

**This is a proposal. No changes should be made without explicit approval.**

### New files to create
| File | Purpose |
|------|---------|
| `BACKLOG.md` | Consolidated list of all outstanding design work, deferred ideas, and research queue. Single source of truth for "what remains." |

### Files to move
| From | To | Reason |
|------|-----|--------|
| `SESSION-2026-03-10.md` | `sources/SESSION-2026-03-10.md` | Source material, not design doc |
| `ideas-inbox-2026-03.md` | `sources/ideas-inbox-2026-03.md` | Source material, not design doc |
| `cognitive-config-ideas.md` | `sources/cognitive-config-ideas.md` | Exploratory ideas, not design doc |
| `preference-extraction/aggregated/` | Remove from project dir (lives in `dev/preference-extraction/`) | Intermediate pipeline data, not deliverables |
| `preference-extraction/extraction-manifest.md` | Remove from project dir | Intermediate pipeline data |

### Files to update (content changes)
| File | Change |
|------|--------|
| `NOTES.md` | Migrate individual TODOs to BACKLOG.md. Keep design notes, rationale, and explorations. Add cross-reference to BACKLOG.md at top. |
| `ARCHITECTURE.md` | Add cross-reference to BACKLOG.md in the "Open Design Work" section. Keep PLACEHOLDERs inline. Keep struck-through completed items. |

### Files to potentially remove
| File | Reason |
|------|--------|
| `DOCUMENT-HIERARCHY.md` | Content is duplicated in ARCHITECTURE.md lines 3-20. The architecture doc version is more complete and authoritative. |

### Count summary
| Action | Count |
|--------|-------|
| Unique deferred/future ideas identified | 47 |
| Categories | 9 (A through I) |
| Blocking for V1 | ~12 (categories A, B) |
| Post-V1 / research | ~20 (categories C, D, E, I) |
| Agent skills/capabilities | 8 (category F) |
| Process/methodology | 5 (category H) |
| Cognitive config / alignment | 5 (category G) |

---

*This proposal is research and collation only. No existing files have been modified.*
