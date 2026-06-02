# AI Architecture — Project Guide

Orientation document. Read this first to understand the project's structure, where things live, and where new work goes.

---

## 1. Document Hierarchy

The project follows a five-level abstraction stack. Each level constrains the levels below it. Changes propagate downward from the highest affected level.

| Level | Document(s) | Purpose | Constrained by | Constrains |
|-------|-------------|---------|----------------|------------|
| 1. Vision | `VISION.md` | Why this exists. The problem (leadership scaling), the desired end state (owner not operator). | — | Everything below |
| 2. Principles | `DESIGN-PRINCIPLES.md` | Philosophical constraints governing all decisions. 18 numbered principles. Generative — specific designs should be derivable from these. | Vision | Architecture, Process, Implementation |
| 3. Architecture | `ARCHITECTURE.md` | Structural design — the four levels (L1-L4), their boundaries, relationships, information flows, concurrency, lifecycle, failure recovery. | Vision, Principles | Process, Implementation |
| 4. Process Design | `QUALITY-GATE.md`, `WORKSPACE-SCHEMA.md`, `COMMUNICATION.md`, `GIT-INTEGRATION.md`, `GUI-DESIGN.md` | Protocols, schemas, contracts, workflows. The "how does each part actually work" layer. | Vision, Principles, Architecture | Implementation |
| 5. Implementation | *(not yet built)* | Actual code, configs, prompts, infrastructure. | Everything above | — |

**Soul documents** (`L1-SOUL.md` through `L4-SOUL.md`) are a parallel artifact type, not a level. They define the fundamental identity and natural orientation of each level. They feed into levels 3-5 but do not sit within the hierarchy — they are seeds from which each level's behavior grows.

### Feedback Loop

When implementation reveals a gap, trace it to the right level before fixing:

1. Process doesn't work → fix the process design (Level 4)
2. Process can't be fixed within the architecture → revise the architecture (Level 3)
3. Architecture change contradicts a principle → re-examine the principle against the vision (Level 2)
4. Principle no longer serves the vision → the vision may have shifted (Level 1)

Do not patch implementation when the problem is architectural. Do not patch architecture when the problem is a missing principle.

---

## 2. File Inventory

### Level 1 — Vision

| File | Purpose |
|------|---------|
| `VISION.md` | The problem being solved (leadership scaling bottleneck), the desired end state (user as owner, not operator), and what this project is not. |

### Level 2 — Principles

| File | Purpose |
|------|---------|
| `DESIGN-PRINCIPLES.md` | 18 numbered philosophical constraints. Every structural decision should be traceable to these. Living document. |

### Level 3 — Architecture

| File | Purpose |
|------|---------|
| `ARCHITECTURE.md` | Structural design: the four cognitive levels (L1-L4), delegation, reporting, escalation, artifact model, invocation, concurrency, lifecycle, failure recovery. First-pass skeleton with PLACEHOLDERs. |

### Soul Documents (parallel artifact type)

| File | Purpose |
|------|---------|
| `L1-SOUL.md` | Soul of the System Orchestrator — natural orientation toward the user's success, holding the portfolio, protecting attention. |
| `L2-SOUL.md` | Soul of the Project Architect — natural orientation toward mastering a single project, making it visible and charting the path to completion. |
| `L3-SOUL.md` | Soul of the Project Manager — natural orientation toward flawless execution of well-given orders, operational rigor. |
| `L4-SOUL.md` | Soul of the Task Executor — natural orientation toward making the thing itself beautifully, craft autonomy within boundaries. |

### Level 4 — Process Design

| File | Purpose |
|------|---------|
| `QUALITY-GATE.md` | Review department system at each level boundary. Independent evaluation, citation ledger, pre-submission checklists, Toyota-inspired quality-at-source design. |
| `WORKSPACE-SCHEMA.md` | Workspace directory structure, document types, edit policies, naming conventions, living-doc navigation, shutdown handoff protocol. |
| `COMMUNICATION.md` | Inter-level communication: inbox (email metaphor), direct messages (Teams metaphor), pings, escalation dynamics, reporting protocol. |
| `GIT-INTEGRATION.md` | Branch strategy (task → workstream → main), PR as review mechanism, merge flow, conflict resolution protocol. |
| `GUI-DESIGN.md` | User-facing spatial interface: a domain-navigation ring (belonging to a separate personal-assistant system) and L1-L4 focus+periphery rooms (agent execution). Early design. |

### Project Management

| File | Purpose |
|------|---------|
| `ROADMAP.md` | Horizon-organized map of all outstanding work (V1, Post-V1, Exploration). One-liners with pointers to detail locations. Navigation, not backlog. |
| `NOTES.md` | Running scratchpad: design notes, research directions, TODOs, candidate principles. Things that are not yet mature enough for their own document. |
| `DOCUMENT-HIERARCHY.md` | Lightweight reference for the 5-level hierarchy and feedback loop. Superseded by this guide (see Section 6). |
| `PROJECT-GUIDE.md` | This file. Orientation and conventions. |

### `sources/` — Raw Source Material

| File | Purpose |
|------|---------|
| `SESSION-2026-03-10.md` | Raw conversation history from the founding architecture session. Voice note transcriptions + design discussion that produced DESIGN-PRINCIPLES.md. |
| `notes-scan-2026-03-16.md` | 14 relevant ideas extracted from personal idea notes (2026-03-02 to 2026-03-16). Escalation patterns, audit traces, research pointers, tooling ideas. |
| `code-review-dimensions-research.md` | Research on code review dimensions (17 identified, 9 independent, 4-tier preset structure). Feeds into QUALITY-GATE.md. |
| `cognitive-config-ideas.md` | Meta-configuration dimensions: effort/depth toggle, audience/register, confidence threshold, scope/horizon. Early-stage exploration. |
| `PROPOSAL-deferred-ideas-consolidation.md` | Consolidated inventory of all deferred/future/post-V1 ideas across the project. Research and collation — preceded ROADMAP.md. |

### `reference/` — External Reference Material

| File | Purpose |
|------|---------|
| `anthropic-soul-doc.md` | Full text of Anthropic's Claude 4.5 Opus internal alignment document (~70K chars). Reference material for soul document design. |
| `anthropic-soul-doc-summary.md` | Structural analysis of the Anthropic soul document: section-by-section breakdown, abstraction levels, design patterns identified. |

### `steering-preferences/` — User Behavioral Preference Extraction

This directory contains the output of a systematic preference extraction pipeline that processed a full conversation archive from a separate personal-assistant system (138 conversations, ~65M tokens, ~829 subagent runs). The goal: extract user behavioral preferences to inform level configurations.

| File/Dir | Purpose |
|----------|---------|
| `STRATEGY.md` | Pipeline architecture: 4-phase extraction design, scale metrics, chunk handling strategy. |
| `METHODOLOGY.md` | Post-hoc methodology documentation and learnings (H1-H5) from running the pipeline. |
| `extraction-manifest.md` | Per-chunk tracking manifest for Phase 1 extraction runs. |
| `aggregated/` | ~140 per-chunk extraction outputs (Phase 1 raw results). Timestamped files. |
| `thematic/` | 11 thematic cluster analyses (Phase 3): agent-autonomy, code-development, communication-style, decision-planning, values-philosophy, etc. Plus `CLUSTERS.md` index. |
| `synthesis/` | Final synthesis outputs (Phase 4): `full-preference-spec.md` (comprehensive spec), `preference-spec.md` (concise spec), `behavioral-profile.md` (personality dimensions), `preference-gap.md` (gap analysis vs current system behavior). |

---

## 3. Where New Content Goes

### Decision Tree

**New principle or philosophical constraint:**
→ Add to `DESIGN-PRINCIPLES.md` with the next sequential number.

**New architectural decision (structural, affects components/boundaries/relationships):**
→ Add to `ARCHITECTURE.md` in the relevant section.

**Mature process or protocol design (has been through multiple design rounds, has clear structure):**
→ Create a new Level 4 document at the project root. Name it descriptively in CAPS: `{TOPIC}.md`. Add a header noting it is a Level 4 process design document and what constrains it.

**Idea, research direction, candidate principle, TODO, or design note:**
→ Add to `NOTES.md` under a descriptive heading. Use the existing format: `## Design Note:`, `## TODO:`, `## Research Direction:`, `## Principle Candidate:`, or `## Future Exploration:`.

**Raw source material (session transcripts, note scans, research output):**
→ Place in `sources/`. Descriptive filename. Date-prefixed if chronological.

**External reference material (papers, third-party docs, analysis of external systems):**
→ Place in `reference/`.

**User preference/behavioral data:**
→ Place in `steering-preferences/` (or appropriate subdirectory).

**Outstanding work items:**
→ Add to `ROADMAP.md` under the appropriate horizon (V1, Post-V1, Exploration) with a one-liner and pointer to where the detail lives.

### When Does a Note Graduate to a Level 4 Document?

A design note in `NOTES.md` is ready to become a standalone process design document when:

1. It has been through multiple design rounds (not just a first-pass idea)
2. It has clear internal structure (sections, not just paragraphs)
3. It is too mature and too large to remain buried in a scratchpad
4. It defines a protocol, schema, contract, or workflow that other documents need to reference

**Graduation process:** Extract the content from `NOTES.md`, create a standalone `{TOPIC}.md` at the project root, and replace the original note with a one-line pointer: "Promoted to standalone design document. See `{TOPIC}.md`." (Several notes have already graduated this way — see COMMUNICATION.md, WORKSPACE-SCHEMA.md, GUI-DESIGN.md, QUALITY-GATE.md, GIT-INTEGRATION.md.)

---

## 4. Folder Structure

```
ai-architecture/
│
├── VISION.md                  # Level 1 — why this exists
├── DESIGN-PRINCIPLES.md       # Level 2 — philosophical constraints (18 principles)
├── ARCHITECTURE.md            # Level 3 — structural design (four cognitive levels)
│
├── L1-SOUL.md                 # Soul: System Orchestrator identity
├── L2-SOUL.md                 # Soul: Project Architect identity
├── L3-SOUL.md                 # Soul: Project Manager identity
├── L4-SOUL.md                 # Soul: Associate identity
│
├── QUALITY-GATE.md            # Level 4 — review department process design
├── WORKSPACE-SCHEMA.md        # Level 4 — workspace structure and document schema
├── COMMUNICATION.md           # Level 4 — inter-level communication system
├── GIT-INTEGRATION.md         # Level 4 — git/branch/PR integration
├── GUI-DESIGN.md              # Level 4 — user-facing spatial interface
│
├── NOTES.md                   # Scratchpad: design notes, TODOs, research directions
├── ROADMAP.md                 # Outstanding work organized by horizon
├── DOCUMENT-HIERARCHY.md      # Lightweight hierarchy reference (see Section 6)
├── PROJECT-GUIDE.md           # This file — orientation and conventions
│
├── sources/                   # Raw source material
│   ├── SESSION-2026-03-10.md          # Founding architecture session transcript
│   ├── notes-scan-2026-03-16.md       # Ideas from personal idea notes
│   ├── code-review-dimensions-research.md  # Review dimension research
│   ├── cognitive-config-ideas.md      # Meta-configuration exploration
│   └── PROPOSAL-deferred-ideas-consolidation.md  # Deferred ideas inventory
│
├── reference/                 # External reference material
│   ├── anthropic-soul-doc.md          # Anthropic's Claude alignment document
│   └── anthropic-soul-doc-summary.md  # Structural analysis of the above
│
└── steering-preferences/      # User behavioral preference extraction
    ├── STRATEGY.md                    # Pipeline architecture
    ├── METHODOLOGY.md                 # Process documentation and learnings
    ├── extraction-manifest.md         # Per-chunk tracking
    ├── aggregated/                    # ~140 Phase 1 per-chunk extractions
    ├── thematic/                      # 11 Phase 3 thematic cluster analyses
    └── synthesis/                     # Phase 4 final outputs (preference specs, profiles)
```

**Root-level files** are the design documents — organized by hierarchy level, plus project management files and soul documents.

**`sources/`** holds anything that fed into the design: session transcripts, note scans, research. Raw material, not design output. Things here are referenced by design documents but are not themselves part of the design.

**`reference/`** holds external material consulted during design. Not project-authored.

**`steering-preferences/`** holds the output of a large-scale preference extraction pipeline. Its purpose is to inform future level configurations with empirically derived user behavioral preferences. Self-contained with its own strategy, methodology, and phased output structure.

---

## 5. Conventions

### File Naming

- **Design documents** (Levels 1-4): `UPPERCASE-HYPHENATED.md` at the project root. Examples: `ARCHITECTURE.md`, `QUALITY-GATE.md`, `GUI-DESIGN.md`.
- **Soul documents**: `L{N}-SOUL.md` where N is the level number (1-4).
- **Sources**: Descriptive, lowercase-hyphenated. Date-prefixed if chronological: `SESSION-2026-03-10.md`, `notes-scan-2026-03-16.md`.
- **Steering-preferences outputs**: Follow the pipeline's own conventions (timestamp-prefixed chunks in `aggregated/`, descriptive names in `thematic/` and `synthesis/`).

### Promoting Notes to Design Documents

1. Extract the mature content from `NOTES.md`
2. Create a standalone file at the project root following the naming convention
3. Add a header identifying it as a Level 4 process design document and stating what constrains it
4. Replace the original note in `NOTES.md` with a pointer: "Promoted to standalone design document. See `{FILE}.md`."
5. Add the new document to `ROADMAP.md` if it has outstanding work items

### Document Formatting

- **Design documents** open with a title (`# AI Architecture — {Topic}`) and a one-line description of their place in the hierarchy
- **Status footers**: Documents end with creation date and status note in italics. Example: `*Created: 2026-03-12* / *Status: First-pass skeleton.*`
- **Governing documents**: Level 4 documents note their constraining documents in the header. Example: "Constrained by: `ARCHITECTURE.md`, `DESIGN-PRINCIPLES.md`."
- **Section references**: Use `§` for section references within ARCHITECTURE.md (e.g., "ARCHITECTURE.md §4")
- **Principle references**: Reference by number (e.g., "principle 6", "P4 and P17")
- **ROADMAP pointers**: Each roadmap item includes a "Detail location" column pointing to the file and section where the full thinking lives

### Cross-Referencing

- Documents reference each other by filename: `ARCHITECTURE.md`, `DESIGN-PRINCIPLES.md`
- Backtick formatting for file references within prose: "See `QUALITY-GATE.md`"
- ARCHITECTURE.md's "Open Design Work" section tracks outstanding architectural items with pointers to where detail lives (NOTES.md TODOs, other documents)
- ROADMAP.md centralizes all outstanding work with pointers — it is navigation, not the detail itself
- The detail always lives in place (in the relevant design document or in NOTES.md), never duplicated into the roadmap

---

## 6. Relationship to DOCUMENT-HIERARCHY.md

`DOCUMENT-HIERARCHY.md` contains the same hierarchy table and feedback loop described in Section 1 of this guide, but in a more compact form. This guide (`PROJECT-GUIDE.md`) is the authoritative and more complete source — it covers hierarchy, file inventory, placement conventions, folder structure, and formatting conventions.

`DOCUMENT-HIERARCHY.md` is retained as a lightweight standalone reference. If the two ever conflict, this guide governs.

---

*Created: 2026-03-17*
*Status: Living document. Authoritative project orientation guide.*
