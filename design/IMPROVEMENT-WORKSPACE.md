# Internal Affairs — System Improvement Workspace

A workspace where system observations land, patterns get logged, and improvement proposals get drafted. The place to bring recurring failures, friction signals, and ideas for making the system better. Not an agent — a shared accumulation layer that any session can write to and any future improvement capability can read from.

---

## Purpose

The system generates experience but has no native place to accumulate it. Individual sessions end, context compacts, and observations disappear. Internal Affairs is the answer to that problem: a persistent workspace that captures what the system is learning about itself.

Four things happen here:

1. **Observations get logged** — what's working, what keeps breaking, patterns noticed across sessions
2. **Proposals get drafted** — structured cases for changes to prompts, process, or architecture
3. **Outcomes get tracked** — what was tried, what changed, what the result was
4. **Patterns get surfaced** — recurring signals that individually look like noise but collectively point at something real

This workspace is an input to system evolution, not a decision-maker. Decisions happen through the normal design process (ROADMAP.md, design sessions, explicit changes to soul/role/config docs). Internal Affairs feeds that process with grounded evidence.

---

## Workspace Structure

```
design/internal-affairs/
  observations/          # Raw session observations — friction, failures, surprises
  proposals/             # Structured improvement proposals (see schema below)
  outcomes/              # Outcome records for proposals that were acted on
  patterns/              # Synthesized pattern notes — clusters across observations
```

### Observation Log Format

Each observation is a lightweight entry:

```
Date: YYYY-MM-DD
Source: [level, domain, or session context]
Signal: [what happened — concrete, one paragraph]
Category: [failure | friction | surprise | working-well]
Linked proposal: [proposal ID if one was drafted, else "none"]
```

Observations do not need to be complete analyses. Raw signal is valuable. Patterns emerge from accumulation, not from individual entries being polished.

### Proposal Format

Proposals are structured cases for a specific change:

```
ID: IA-YYYY-NNN
Date: YYYY-MM-DD
Status: draft | under-review | accepted | rejected | deferred
Target: [what would change — specific doc, prompt, process, or config]
Trigger: [observation IDs or pattern notes that motivated this]
Proposal: [what change to make, stated precisely]
Expected effect: [what should improve and how you'd know]
Risk: [what could break or regress]
Decision: [leave blank until acted on]
Outcome: [leave blank until outcome is known]
```

### Outcome Records

When a proposal is accepted and implemented, an outcome record closes the loop:

```
Proposal: IA-YYYY-NNN
Implemented: YYYY-MM-DD
Change made: [link or description of what actually changed]
Observed result: [what happened — match against expected effect]
Residual: [what's still unresolved, if anything]
```

---

## Inputs to This Workspace

**Session observations** — any session at any level can write an observation entry. The bar is low: if something struck you as broken, surprising, or notably good, log it.

**Audit trail and resurrection windows** — the 2-week resurrection window gives a defined period during which a paused or stalled workspace can be audited before being closed. Patterns that emerge during resurrection audits (what was the last state, what broke continuity, what caused the stall) are high-value inputs here.

**Post-mortem signals** — when a level fails to complete work, escalates unexpectedly, or produces output that required significant correction, that's an observation worth logging regardless of whether a proposal follows immediately.

**Design session conclusions** — when a design session resolves a previously open question (see V1 Open Items below), the key decision and its rationale belong here as an observation-class entry so future sessions can understand why the system is the way it is.

---

## What the System IS

Architecture, identity, and design — all in this project folder.

| Document | Purpose |
|----------|---------|
| `VISION.md` | Why this exists |
| `DESIGN-PRINCIPLES.md` | 19 philosophical constraints |
| `ARCHITECTURE.md` | Structural design — 5 levels, boundaries, lifecycle |
| `operational/L1/soul.md` — `operational/L5/soul.md` | Fundamental identity per level |
| `operational/L1/role.md` — `operational/L5/role.md` | Responsibilities, boundaries, interfaces |
| `operational/L1/config.md` — `operational/L5/config.md` | Operational configs per level |
| `QUALITY-GATE.md` | Independent review function — conceptual brief (full design needed) |
| `COMMUNICATION.md` | Inter-level communication protocol |
| `WORKSPACE-SCHEMA.md` | Folder structure, document types, edit policies |
| `GIT-INTEGRATION.md` | Branch strategy, PR-as-review |
| `OBSERVABILITY.md` | Narrative timeline, traceability |
| `GUI-DESIGN.md` | Spatial interface design |
| `NOTES.md` | Running design notes, ideas, research directions |
| `ROADMAP.md` | V1 items, post-V1, exploration |
| `PROJECT-GUIDE.md` | How to navigate this project |

## How the System THINKS

Thinking frameworks and cognitive tools.

| What |
|------|
| Thinking-frameworks research and reference |
| Cognitive config system — 72 spectrums, 14 families, deep manual, operations, test harness |
| Parent cognitive-space model framework |
| Cognitive config skill (entry point for activation) |
| An empathy-frame skill for agent interface design (P20) |

## How the System RUNS

Injection, delivery, and runtime infrastructure.

| What |
|------|
| Per-turn injection mechanism — delivers context to active sessions |
| Grounding injection — route decisions, evidence gates |
| Cognitive config per-turn injection |
| Cognitive config script — posture, tools, state persistence |
| Auto-boot after context compact |
| Hook configuration — what runs on SessionStart, Stop, PreToolUse, etc. |
| Status bar — visible system state |
| Transcript-backed Claude session control plane for LLM use — spawn/resume by session id, payload-backed turns |

## What the System USES

Development tools and external integrations.

| What |
|------|
| Claude Code wrapper patches plus prompt-assembly observability tooling — injection delivery, ephemerality, truncation fixes, smoke harness, final request payload capture |
| Patch registry entry point |
| Pre/post-update process |
| MCP server infrastructure (relevant servers TBD) |
| Template for delegating work to subagents |
| Evidence standards for subagent returns |
| Evidence collection and verification pipeline |
| Spawn-time gate for subagent compliance |

**Important observability pattern:** when debugging what Claude Code actually gives the model, the cleanest client-side oracle is the final outbound request payload captured at the last query boundary. UI rendering, hidden-context viewers, and model self-report are secondary surfaces; the payload file is the direct evidence of what the client sent.

**Important control-plane pattern:** keep two Claude control planes instead of forcing one transport to do both jobs.

- Human-facing control: a PTY/session wrapper
- LLM-facing control: transcript-backed noninteractive spawn/resume

That split is cleaner because the LLM path wants determinism, explicit session ids, resumability, and payload capture, while the human path wants a stable interactive terminal.

## How the System was DESIGNED

Methodology, research, preferences, and patterns.

| What |
|------|
| Process guide for constructing agent skills |
| Spec for instructions agents actually follow |
| Rubric for evaluating steering effectiveness |
| Extracted lessons from prior skill work |
| Design ideas for cognitive config |
| Reference exemplar skill examples |
| Behavioral specs extracted from 138 sessions |
| Preference spec, behavioral profile, gap analysis |
| A reference soul document (reference material) |
| Session notes, config design notes, research |
| Preference extraction pipeline (methodology + results) |

---

## Future: Improvement Agent Capability

An automated improvement capability — an optimizer that runs analyses against this workspace, surfaces proposal candidates, and validates outcome patterns — is a plausible future direction. If built, it would operate out of this workspace: reading observations, drafting proposals, and writing outcome records using the same formats.

That capability is not V1 scope. It is also not the same thing as this workspace. Internal Affairs exists and is useful as a passive accumulation layer regardless of whether an optimizer ever runs on top of it.

---

## V1 Open Items

**Major architectural change: 5-level hierarchy. Old L3 → L4, old L4 → L5. New L3 (Module Designer) added. All documentation needs restructuring.**

Current development priorities (triaged 2026-03-24):

| # | Item | Status |
|---|------|--------|
| 3/9 | Metacognition schemas + cognitive config per level | Design needed |
| 4 | User profile document | Needs creation |
| 6 | Generative skeleton → architecture (L2 planning) | Design needed |
| 7 | Benchmarking | Metrics framework needed |
| ~~8~~ | ~~Conversational mode~~ | **Resolved.** Each agent is a terminal session. User lists instances via status board, opens the terminal they want. No special conversational mode protocol needed — the interaction surface is the terminal itself. |
| 10 | User intentionality assumption | Operational config |
| 11 | Steering preferences integration | Integration needed |
| ~~13~~ | ~~Escalation/leadership skills~~ | **Resolved.** Subordinate writes block description to workspace → sends high-urgency inbox message to parent → goes idle. Parent behavior (interrogate process, parallel approaches, different tools, correct course, escalate further) documented in operational configs as typical responses. Not a separate skill. Iterate from experience. |
| RV | Independent review function — full design per level | Conceptual brief exists; full design needed |
| IA | Internal Affairs — system improvement workspace | This document |

**Deferred:** Time awareness (#5), L1 pre-work research team (#14), discussive L1 branch (#15), seeds-not-instructions formalization (#16), design principles skill (#17), CULTURE.md (#18), multi-account orchestration (#12).

**Key decisions this session:**
- A separate personal-assistant system and L1-L5 are separate systems — not integrating
- Independent review function is baked into each level's process, not a parallel organizational entity
- Internal Affairs is a system improvement workspace — observations, proposals, outcomes
- Conversational mode is just terminal switching — no special protocol needed
- Escalation is workspace write + inbox message + config guidance — no separate skill needed
- 5-level hierarchy confirmed — L3 Module Designer added between L2 and old L3 (2026-03-26)

---

*Created: 2026-03-24 | Revised: 2026-06-02*
