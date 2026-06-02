# Workflow Diagram: Creation Learnings

What we learned building the L1-L5 workflow diagram (`design/workflow-diagram.html`). Applicable to any complex process visualization.

---

## The Right Diagram Type Matters More Than Execution Quality

Tried three approaches before landing on the right one:

1. **Horizontal swimlane chart** — events connected within lanes. Failed because the story is in the HANDOFFS between levels, not the events within them. Swimlanes naturally emphasize within-lane flow, which is the wrong axis for this system.

2. **Methodology blueprint** — vertical phase containers with sub-steps inside, side panels for context. Closer to what was needed conceptually (phase-organized, readable), but didn't show the cross-level interactions that ARE the workflow. A blueprint shows structure; we needed to show flow.

3. **Sequence-style swimlane** — horizontal lanes for levels, time left-to-right, arrows crossing between lanes to show handoffs. This worked because the arrows ARE the story. You follow them from "Request" to "Deliverable" and see every handoff, gate, and feedback loop. The organizing principle matches the thing being shown: work flowing between levels.

**Takeaway:** Before building, ask: what is the primary thing the viewer needs to see? If it's handoffs → arrows between lanes. If it's phases → containers. If it's hierarchy → tree. The diagram type encodes what matters.

## Aesthetic Direction: Less Is More, Iteratively

Started with saturated level-specific colors (teal, amber, blue, green, rose). Each iteration desaturated further:

- Full saturation → looked childish, colors competed for attention
- Muted earth tones → better but still distracting
- Near-monochrome grayscale → right. The structure carries the information, not the color

**Takeaway:** For working documents, color should differentiate, not decorate. Grayscale with subtle value differences is almost always better than color-coding for process diagrams. Color draws the eye to the wrong thing — you look at WHAT level something is instead of HOW work flows between them.

## Arrowheads: Just Remove Them

SVG arrowhead markers consistently misaligned with node borders across different arrow angles and bezier curves. Adjusting refX/refY, polygon coordinates, and anchor offsets didn't produce reliable alignment.

Solution: remove arrowheads entirely. The connection lines alone are sufficient — the flow direction is obvious from left-to-right positioning and top-to-bottom lane ordering. The diagram became cleaner without them.

**Takeaway:** If a visual element causes consistent rendering issues and the information it carries is already communicated by layout/position, remove it rather than fixing it. Simpler is better for working documents.

## Node Sizing: Square Beats Wide

Default nodes were short/wide rectangles — text got clipped, labels were unreadable. Changing to taller, more square-shaped nodes (115x64px with text wrapping) immediately improved readability.

After changing dimensions, all node positions needed rescaling (1.4x) to prevent overlap — the original positions assumed smaller nodes. This is a cascading change: node dimensions → spacing → total diagram width.

**Takeaway:** Design nodes for the longest label, not the average one. Square nodes with text wrapping are more readable than wide nodes with truncation.

## Chrome DevTools for Visual QA

Used Chrome extension (claude-in-chrome) to screenshot and inspect the diagram during iteration. Required serving via local HTTP server (`python3 -m http.server`) since `file://` URLs don't work through the extension.

**Takeaway:** For visual work, always inspect in the browser. What looks right in code often looks wrong rendered. Screenshot → fix → reload → screenshot is the iteration loop.

## Content Before Style

The first version was visually polished (dark theme, animations, hover effects) but had the wrong diagram type. The final version is visually simple (monochrome, no effects) but has the right structure.

**Takeaway:** Get the structure and content right first. Aesthetic refinement is the last pass, not the first. A beautiful diagram of the wrong thing is worse than an ugly diagram of the right thing.

---

*Created: 2026-03-30*
