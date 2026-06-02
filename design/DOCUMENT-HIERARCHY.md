# AI Architecture — Document Hierarchy

The design documents follow a top-down abstraction stack. Each level constrains the ones below it. Changes flow downward — if the vision shifts, principles may need updating, which may cascade to architecture, and so on.

| Level | Document | Purpose | Constrains |
|-------|----------|---------|------------|
| 1. Vision | `VISION.md` | Why this exists. The problem being solved, the desired end state. | Everything below |
| 2. Principles | `DESIGN-PRINCIPLES.md` | The philosophical constraints governing all decisions. Generative — specific designs should be derivable from these. | Architecture, Process, Implementation |
| 3. Architecture | `ARCHITECTURE.md` (planned) | Structural design. Components, boundaries, relationships, information flows. The "what are the parts and how do they connect." | Process, Implementation |
| 4. Process Design | `QUALITY-GATE.md`, `WORKSPACE-SCHEMA.md`, `COMMUNICATION.md`, `GIT-INTEGRATION.md`, `GUI-DESIGN.md` | Protocols, schemas, contracts, workflows. The "how does each part actually work." Documentation templates, reporting formats, invocation protocols. | Implementation |
| 5. Implementation | (code, configs, prompts) | The built thing. Actual infrastructure, agent configs, scripts, prompts. | — |

## Feedback loop

When implementation reveals a gap, the first question is: which level is the gap at?

- If a process doesn't work → fix the process design
- If the process can't be fixed within the architecture → the architecture needs revision
- If the architecture change contradicts a principle → the principle needs re-examination against the vision
- If the principle no longer serves the vision → the vision may have shifted

Changes propagate downward from the highest affected level. Don't patch implementation when the problem is architectural. Don't patch architecture when the problem is a missing principle.

---

*Created: 2026-03-12*
