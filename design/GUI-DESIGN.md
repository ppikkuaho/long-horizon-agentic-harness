# AI Architecture — GUI Design (Process Design)

Level 4 process design document. Defines the user-facing visual interface over the agent infrastructure. Constrained by: `ARCHITECTURE.md` (Section 6: User Interface).

---

## Motivation

The terminal (Claude Code) is great for input but awful for state representation. It shows you exactly what you ask for — nothing more. That works for L4-style heads-down dev work, but for a user managing a portfolio of projects and agents, you need spatial awareness: what's active, what's waiting, what's blocked, how things relate — all at a glance.

**Core insight:** The GUI is for the **user**, not for the agents. Claude Code remains the backbone (agent spawning, file management, tool use, conversation). The GUI is a lens over the same filesystem and agent infrastructure — the workspace schema (project folders, status board, inbox, living docs) is already the data layer.

**Design philosophy:** Design for the end state, build iteratively. Not aiming for quick wins or stopgaps — every piece of work should serve as a sensible foundation for the final product.

**Future exploration:** Could the GUI also improve agent orientation? L1/L2 agents face similar state-representation challenges when managing portfolios/projects. Not the primary use case, but worth considering whether the same visual layer could serve agents too.

---

## Two GUI Paradigms

The design establishes two fundamentally different visual interfaces solving different problems.

### 1. Life-OS Ring/Donut — Domain Navigation (Being/Knowing)

A sunburst or radial navigation for the domain-oriented knowledge landscape. The ~17 Life-OS domains are arranged as segments of a ring, with values/core at the center. Hover or click a domain segment to expand into sub-layers — hot/warm/cold tiers, individual entries, connections. This serves orientation and navigation: where does information live, what domains exist, how does knowledge relate across the system. It's about *being* — understanding the shape of your knowledge and life.

### 2. L1-L5 Spatial Interface — Agent Execution (Doing/Executing)

The isometric rooms / focus+periphery design described below. This serves the agent execution system: what's running, what's blocked, what work is in flight. It's about *doing* — managing a portfolio of projects and agents.

### Integration (Open Question)

How these two paradigms relate is explicitly unresolved. They could be separate tabs or modes within one app, entirely separate applications, or nested (the ring as a top-level navigation layer that can drill into the spatial execution view for a given domain's active projects). The right answer likely depends on usage patterns that don't exist yet. Both paradigms share the same underlying data layer (filesystem, memory entries, agent infrastructure), so the integration is a UI question, not a data question.

---

## Rejected Alternatives

Several spatial models were explored for the L1-L5 execution interface before settling on focus+periphery:

- **Buildings model:** Each project as a building, floors for L3 areas, offices for L4/L5 workstreams and tasks. Rejected — too much physical-world simulation. The metaphor breaks at edge cases (what's the lobby? what are stairs?), and the skeuomorphism adds cognitive overhead without earning it.
- **Neighborhoods model:** Project clusters on a pannable 2D canvas. Interesting — spatial clustering has real value — but needs strong visual anchors to avoid disorientation, and loses the "everything at a glance" property when the portfolio grows.
- **Focus + periphery chosen:** Gives both overview and drill-down in one continuous scene. Maintains vertical grouping (L2-L3-L4-L5 within a project). Clean transitions via zoom rather than navigation. The periphery solves the "where am I" problem that neighborhoods struggle with.

---

## Spatial Design (Focus + Periphery, Continuous Scene)

One continuous scene, three zoom levels, no scene changes or cuts — only camera movement.

### Zoom Levels

1. **Zoomed out** — all project verticals visible, low-res, labeled. You see the shape of your portfolio. Pick a vertical.
2. **Vertical pulled forward** — smooth zoom. That project's L2-L3-L4-L5 rooms become full-size. Others recede but stay visible in periphery. Each room shows its agent's assignment and level tag. You see the structure of work in this project.
3. **Agent engaged** — smooth zoom into one room. Conversation history streams in (autonomous work log). Input field appears. You're in the session — same as a Claude Code terminal, just rendered in the GUI.

### Rooms

Rooms are the core visual unit. Each level's head agent is at the top of its room. Lateral spawns (post-V1) fill the room — room population visually encodes cognitive depth.

The **review department** is a parallel room next to each level — work flows from the producing room through the review room before going up. Visually obvious gatekeeping function. (See `QUALITY-GATE.md` for the full review department process design.)

### Positional Consistency

Projects and their rooms always occupy the same spatial position across all zoom levels. When you zoom in on a project, everything else shifts to the periphery but nothing relocates. When you zoom back out, everything returns to its known position. This is a distinct constraint beyond "no cuts" — the user builds spatial memory of where things live, and that memory must map reliably regardless of zoom level or navigation path. If a project is top-right at the portfolio view, its rooms are top-right when zoomed in, and it returns to top-right when you zoom out. Spatial consistency is what makes the continuous scene actually useful rather than just visually smooth.

The no-cuts principle means spatial memory is never broken. You always know where you are relative to everything else. Chat is built into the GUI, superseding terminal for conversation mode.

### L1 Dashboard

A dashboard layer at the portfolio altitude — shows high-level overview, active agents, citation ledgers, quality gate status. Not a separate view, just information rendered at the zoomed-out level.

#### Dashboard Distribution (L1 vs L2)

Both L1 and L2 have dashboards, but at different granularity — same concept, different altitude.

- **L2's desk (project level):** Individual project agents and their states, code visualizer for its codebase, workstream-level detail, gate activity for its project. L2 sees the trees.
- **L1's desk (portfolio level):** Portfolio totals, aggregate quality metrics across projects, cross-project status comparison, resource allocation overview, code visualizer (aggregate/multi-project view). L1 sees the forest.

This mirrors the zoom levels in the spatial design — L1's dashboard *is* what you see at the zoomed-out altitude, L2's dashboard is what populates when a vertical is pulled forward. The data is the same; the aggregation level changes with altitude.

---

## Dual Rendering Principle

The same underlying data — agent states, quality metrics, codebase structure, gate activity — gets rendered differently depending on who's consuming it.

- **Visual/spatial rendering (for humans):** The GUI, diagrams, code visualizer. Optimized for spatial awareness, pattern recognition, and at-a-glance orientation. Humans absorb structure faster from layout than from text.
- **Structured text rendering (for agents):** Summaries injected into agent context at boot or per-turn. Agents don't see pixels — they need compact, information-dense text that fits within context budgets.

**Example:** The code visualizer shows the human a spatial map of the codebase — modules as nodes, dependencies as edges, change hotspots glowing. The same underlying data feeds L2's context as structured text: "Module X: 1200 lines, 8 dependencies, high change rate this week. Module Y: stable, no recent changes." Same data, different rendering surface.

This is a design constraint, not just an observation: when building any new data view (quality dashboards, gate status, agent workload), design both rendering paths from the start. The data model and the visual model are separate layers — the visual model is one consumer, agent context injection is another.

---

*Status: Early design.*
*Created: 2026-03-17*
