# L1–L5 Agent Harness

A hierarchy of LLM agents that turns a user's intent into built, verified software — and keeps what gets built faithful to what was meant, all the way down to the code.

Models already write good code, so the bottleneck in building software with them has shifted from execution to coordination and fidelity: directing many efforts in parallel, and keeping what gets built faithful to what was meant. One person can run one project by hand; they cannot direct, keep coherent, and quality-check twenty at once, nor guarantee that a long autonomous build still matches what they asked for. This system enforces a separation of concerns across five levels of abstraction, each doing a genuinely different kind of thinking, so the person sets and guards intent while the hierarchy carries the work. Three things come out of that:

**1 — Higher-quality architecture and code.** It architects the way a senior architect actually does, not ad-hoc. There's a real method underneath: carve a system by where its connections are thin — where change is naturally isolated — not by drawing arbitrary boxes; keep complexity hidden behind narrow, stable interfaces; point dependencies toward the stable core. "Deep modules" is used as a quality rubric that pressure-tests a design, never as the carving rule itself. The result is codebases with clean seams that stay coherent as they grow.

**2 — Long-horizon, high-difficulty autonomous execution.** Large autonomous builds usually degrade because error compounds over a long horizon with nothing to catch it. Here, nothing runs without a validated plan; work is decomposed until each unit is small and independently verifiable; every level reviews composition and fidelity at its own altitude; and tests are frozen before code, so the work is anchored to them rather than the reverse. A genuinely hard task can run end-to-end with accuracy held up by structure instead of hope.

**3 — Alignment and fidelity.** The first priority is that the thing built is the thing meant — and stays that way from intent to shipped code. Intent is captured precisely: the intake probes tradeoffs to find where the user actually has opinions (people reveal them at a fork, not when asked "do you care?"), and records how technically fluent they are per area, so the system knows what to decide for them and what to bring back. Every requirement then carries a stable ID that threads through the whole system — design element, test, branch, and review all trace to it. The gate, the per-level independent reviews, and that traceability spine exist for one purpose: to kill drift.

## The five levels

A separation by the kind of thinking each does, not a rank ladder:

- **L1 — System Orchestrator** — captures the user's intent, guards it for the life of the project, routes work, and is the only level the user talks to.
- **L2 — Project Architect** — designs the shape of the solution: where the module boundaries fall, the interfaces between them, the decisions that are expensive to reverse.
- **L3 — Module Designer** — takes one module and designs it in depth, then manages its construction.
- **L4 — Workstream Coordinator** — breaks a module into concrete tasks and authors the acceptance tests they'll be judged against.
- **L5 — Task Executor** — writes the actual code against frozen tests, paired with an independent reviewer (L5+) that checks it.

Direction flows down as minimal "short-email" briefs (what, not how); results flow up as compressed reports. Raw work never moves up, and clean context is preserved at every boundary.

## How it works, end to end

Work runs as two cycles joined by a single hard gate — design, then build — never one big waterfall.

The **design cycle** produces a validated plan and not a line of code. Intake turns the user's intent into a precise, tagged, traceable spec. The architect proposes the structure. The module designers detail each area in a single coordinated round, renegotiating interfaces against real constraints. And — critically — the tests and review rubrics are written here, before any code, by agents that aren't the ones who'll do the work.

The **plan-alignment gate** is the heart of the system, at the seam between designing and building. It reads the whole assembled plan against the original intent — something per-level reviews structurally can't do — and catches the three ways a plan drifts even when every local step looked fine: dropped requirements, unrequested additions, and requirements technically present but subtly wrong. It even inspects its own first translation (turning the user's prose into requirements), because that's where drift enters upstream of every other check. A human gives a warm sign-off on a triangulated view; nothing builds until it passes.

The **build cycle** begins only on PASS: executors write code against the now-frozen plan, every level's output checked by independent review before it moves up.

## What makes it distinctive

- **Tests before code, by not-the-coder.** Tests written after the fact get bent to fit the code; written first, from the spec, by someone else, the code must serve them. (Corollary, proven in simulation: tests anchor only what they assert — so an independent reviewer is load-bearing, catching the fidelity gaps tests miss.)
- **One spine.** A single hierarchical scheme is the requirement ID, the agent's address, the workspace path, the git branch, the rubric location, and the visibility graph — decided once, it serves all of them.
- **Cross-model by design.** Opus 4.8 for the generative/architecture levels; GPT-5.5 (via Codex) for execution, where literal precision is the strength. Failures escalate rather than silently degrade.
- **Documentation is memory.** Every level can be killed and respawned from its artifacts; truth lives in documents, coordinated over a lightweight bus. The system also keeps a workspace to observe itself and propose its own improvements.
- **Walking-skeleton first.** A thin end-to-end thread proves the connections before the full build commits to them.

The methodology isn't invented — it's borrowed from how architecture firms and consultancies actually turn a client's intent into a built thing, instantiated with agents instead of people.

## Repository layout

This repository is the design and specification layer — the documents the runtime would be built from.

```text
design/         the specification corpus: architecture, principles, and the
                mechanism docs (plan-alignment gate, decomposition, quality gate,
                observability, communication, workspace schema, improvement workspace),
                plus parked navigation docs and a consolidation/decision log
operational/    what each agent loads at spawn: L1–L5 (role, config, soul,
                spawn-template) and shared protocols (runtime-and-model map,
                agent-definition principles, lifecycle, comms, git, intent-spec
                contract, user-profile schema)
dry-run/        the end-to-end simulation: an intent-spec taken through L2
                (ADRs, contracts, plan), a walking skeleton, the plan-alignment
                gate report, and the built payments slice with its tests
```

Good entry points: `design/working-notes/consolidation-plan-2026-06-02.md` (the decision log), `design/ARCHITECTURE.md` (the system design), and `dry-run/` (the worked example).

## Status

The design is complete and hardened against a full end-to-end simulation — which built a real vertical slice (17/17 tests passing, a genuine cross-model handoff) and surfaced the gaps, now closed. The runtime harness, on a pinned Claude Code, is now in progress.
