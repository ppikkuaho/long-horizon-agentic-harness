# long-horizon-agentic-harness

A design and specification for a long-horizon, multi-agent system for building software. Work is organized across a five-level hierarchy (L1–L5), where each level handles a distinct kind of decision and delegates the rest downward.

This repository is the design/specification layer. The runtime — spawn machinery, message bus, visibility graph, the enforcing hooks, and the per-level runtime — is not built yet. These documents are the specification it would be built from. The only worked exercise so far is a tabletop dry-run (`dry-run/`). It is an ongoing project and parts of it are unfinished or in flux.

## Status

- Design/specification stage; no running system.
- `design/ARCHITECTURE.md` notes that only its first section is at build resolution; later sections are coarser and carry open placeholders.
- The five-level model is current. Some navigation documents (`ROADMAP.md`, `PROJECT-GUIDE.md`, `DOCUMENT-HIERARCHY.md`, `GIT-INTEGRATION.md`, `GUI-DESIGN.md`) are parked and still describe an earlier four-level layout; they are kept for reference and have not been brought current.
- Model assignments, concurrency limits, and similar values in the docs are working values expected to change.

## The levels

| Level | Role | Responsibility |
|---|---|---|
| L1 | System Orchestrator | Captures user intent and routes it to a project. |
| L2 | Project Architect | Owns one project; makes the architecturally-significant decisions. |
| L3 | Module Designer | Designs one area, then a fresh instance oversees its build (two clean-context phases). |
| L4 | Workstream Coordinator | Decomposes a workstream into tasks and writes the acceptance tests for the level below. |
| L5 | Task Executor | Writes code as an execute-then-review pair. |

Levels are separated by the kind of thinking they do, not by rank. Autonomy narrows downward: a level may spawn only the levels beneath it, and only within the scope its parent gave it. The five levels are a maximum, not a minimum — a task is routed only through the levels that add a distinct kind of decision.

## How work flows

Two nested Plan → Execute → Review cycles meet at one checkpoint:

- A **design cycle** (intake → architecture → planning) produces a validated plan and no code.
- A **build cycle** (execution → coordination → task execution) produces code against the frozen plan.
- Between them sits the **plan-alignment gate**: it checks the assembled plan against the user's tagged intent before any code is written.

Recurring design choices across the spec:

- Documentation is the primary memory. Each level reads its state from artifacts and writes it back; the system is meant to reconstruct from documents alone if running processes are stopped.
- Acceptance tests and review rubrics are written from the spec, before the work, by an agent that is not the worker.
- One hierarchical path scheme serves at once as requirement IDs, agent addresses, workspace paths, git branches, rubric locations, and the need-to-know visibility graph.
- A message bus carries best-effort nudges and pointers; durable truth lives in the documents in each work node.

## Repository layout

```text
design/                       the specification corpus
  ARCHITECTURE.md             the system design
  VISION.md  PROJECT-PLANNING.md  DESIGN-PRINCIPLES.md     scope, plan, principles
  PLAN-ALIGNMENT-GATE.md  DECOMPOSITION-METHODOLOGY.md     mechanisms
  QUALITY-GATE.md  OBSERVABILITY.md  COMMUNICATION.md
  WORKSPACE-SCHEMA.md  IMPROVEMENT-WORKSPACE.md
  GIT-INTEGRATION.md  GUI-DESIGN.md  ROADMAP.md            parked / older nav docs
  PROJECT-GUIDE.md  DOCUMENT-HIERARCHY.md  NOTES.md
  working-notes/consolidation-plan-2026-06-02.md          decision log / consolidation plan
operational/                  what each agent loads at spawn
  L1/ … L5/                   per level: role, config, soul, spawn-template
                              (L1 also: handbook, intake template, a new-project skill;
                               L3: planning template; L5: swe-handbook)
  shared/                     runtime-and-model-map, agent-definition-principles,
                              agent-lifecycle, comms-protocol, git-protocol,
                              intent-spec-contract, user-profile-schema
dry-run/                      a tabletop simulation
  intent-spec.md              the worked intent
  L2/                         architect output: ADRs, contracts, plan
  skeleton/                   a throwaway walking skeleton
  gate-report.md              the plan-alignment gate run
  build/payments/             a tested payments implementation
```

## Where to start

- `design/working-notes/consolidation-plan-2026-06-02.md` — the decision log; the most direct record of what was decided and why.
- `design/ARCHITECTURE.md` — the system design.
- `dry-run/` — the worked example, including the gate report and the payments build.

## Notes

- This is one part of a larger personal effort and does not depend on or include the rest of it.
- V1 targets building software; broader task types are noted in the docs as possible future direction, not current scope.
- The dry-run is a simulation against a fictional brief: there is no real user, no datastore, and no deployment. Its plan-alignment gate returns a conditional fail, and the payments build is included as a finishing-pass demonstration rather than a clean gated run.
