# long-horizon-agentic-harness

> A hierarchy of LLM agents (L1–L5) that turns a person's intent into built, verified software — and holds what gets built faithful to what was meant, all the way down to the code.

Specification corpus + working runtime · a 944-passing test suite (3 environment-gated skips) · live L1→L5 builds delivered end-to-end across a multi-model architecture — different models for the design/review seats and for execution.

**Pre-v1 · in active development** — the pieces are built and running live builds, but the v1 bar is not met yet. See [Status](#status).

## Design thesis

- **Problem.** Agentic coding breaks down over long horizons: work drifts from the original intent, context collapses when one agent tries to hold everything, decomposition is weak, and agents grade their own work.
- **Thesis.** Frontier models are largely interchangeable capability providers; the differentiator is the *operating architecture* around them. Placed inside the right structure, today's models deliver far more than they can one-shot.
- **Contribution.** This repo is that architecture — designed from the ground up and built as an **L1–L5 agent hierarchy plus a harness/runtime** that enforces decomposition, role separation, criteria frozen before the work, independent review at every boundary, durable state as memory, and human gates. The project is a test of whether those, together, make long-horizon AI software delivery reliable.

## What it is

Models already write good code, so the bottleneck in building software with them has moved from execution to **coordination and fidelity**: directing many efforts at once, and keeping what gets built faithful to what was meant over a long autonomous run. One person can run one project by hand; they cannot direct, keep coherent, and quality-check twenty at once, nor guarantee that a day-long build still matches what they asked for.

This system enforces a **separation of concerns across five levels of abstraction**, each doing a genuinely different *kind* of thinking — so the person sets and guards intent while the hierarchy carries the work. The hard part it is built around is not generating code; it is **drift**: the dozen quiet ways a long, decomposed, multi-agent build diverges from the original intent even when every local step looks fine. Most of the machinery below exists to kill drift.

The method isn't invented — it's borrowed from how architecture firms and consultancies actually turn a client's intent into a built thing, instantiated with agents instead of people.

## The five levels

A multi-agent build runs into a context problem before it runs into anything else. Ask one agent to carry a project from intent to shipped code and it has to hold, all at once in a single context window, what the user wanted, the whole architecture, every module's design, every task, and the code. That does not fit — and well before it stops fitting, attention thins, the thread is lost over a long run, and the agent can no longer tell whether the line it is writing still serves the goal. So the work is split across five levels, each a genuinely different *kind* of thinking, and each holding exactly one artifact — its altitude's definition of what "right" means. The model is the same across the upper seats; the split is about role, bandwidth, and clean context, not raw capability.

**L1 — System Orchestrator.** The only level the user talks to. It draws out what the user actually wants — probing tradeoffs to find where they hold real opinions versus where they are content to delegate, because people reveal preferences at a concrete fork, not when asked "do you care?" — and writes that down as a tagged intent-spec it then guards for the life of the project. It routes work to the right place, and when results come back it packages them for the user and judges the finished product against the original intent. **It holds the intent:** the durable record of what was wanted, kept deliberately separate from how it gets built.

**L2 — Project Architect.** Owns the shape of the solution. It makes the architecturally significant decisions — where the module boundaries fall, the interfaces between them, the choices that are expensive to reverse — and deliberately stops there, deferring each module's internals downward with constraints rather than designing them itself. Coming back up, it reviews how the finished modules compose into one coherent system. **It holds the architecture:** the module map, the interface contracts, and the decision records (ADRs) that capture what was decided and why.

**L3 — Module Designer.** Takes a single area and works it out in depth, then manages its construction — and those are two different cognitive jobs, so they are split across two instances by a clean-context boundary. A planning instance produces the area's detailed design, pressure-testing L2's interfaces and renegotiating them where they do not hold, then collapses; later a fresh execution instance inherits that frozen design (never the planning conversation), decomposes it into workstreams, and drives them, reviewing how the workstreams compose back into a coherent module. **It holds the area design.**

**L4 — Workstream Coordinator.** Breaks a module into concrete, right-sized tasks and sequences them. Before any code is written, a separate tester authors the executable acceptance tests each task will be judged against — a second, independent reading of the spec, so the work is anchored to the tests rather than the tests fitted to the work. It hands each task down as a bounded brief plus its frozen tests, and reviews that the finished units actually integrate. **It holds the workstream:** the task breakdown and the acceptance tests that define "done."

**L5 — Task Executor.** The floor of the hierarchy, where work is done rather than delegated. It writes the code and makes the frozen tests pass — its own loop is write → run the tests → fix, repeating until they are green and the unit works end-to-end — and it cannot edit those tests. Its output is then checked by an independent reviewer running a different model (L5+), which reads the code against the frozen spec, catches fidelity gaps the tests do not assert, and either passes it upward or bounces it back for another iteration. **It holds the implementation:** the code itself.

**The same shape at every boundary.** Each level does the same two things to its artifact, and only those: going *down*, it refines the artifact one resolution finer and freezes that as the standard for the level below; coming *up*, it checks the level below's result against that standard and passes a compressed account onward. It is one `Plan → Execute → Review` cycle, run recursively at every level — so the L1↔L2 relationship has the same shape as L4↔L5, one relationship repeated at five scales. That self-similarity is what lets the system scale, and it is what bounds each agent: a level owns the decisions encoded in its own artifact and nothing else, so it can neither reach up to redefine intent nor down to dictate implementation. Translate down, verify up — one spec at five resolutions, five owners.


## How it works, end to end

The **design cycle** produces a validated plan and not a line of code. Intake turns the user's intent into a precise, tagged, traceable spec — probing tradeoffs to find where the user actually has opinions (people reveal them at a fork, not when asked "do you care?"). The architect proposes the structure; the module designers detail each area in one coordinated round, renegotiating interfaces against real constraints. Crucially, the tests and review rubrics are written **here, before any code, by agents that aren't the ones who'll do the work** — and frozen, so later gates check against a standard the producer could not move.

The **plan-alignment gate** is the heart of the system. It reads the whole assembled plan against the original intent — something per-level reviews structurally can't do — and catches the three ways a plan drifts even when every local step looked fine: dropped requirements, unrequested additions, and requirements technically present but subtly wrong. It even inspects its own first translation of the user's prose into requirements, because that's where drift enters upstream of every other check. Nothing builds until it passes.

The **build cycle** begins only on PASS: executors write code against the now-frozen plan and tests, and every level's composed output passes through an independent review gate **at its own altitude** before it moves up — the leaf checked at the line, each level above checked for how its pieces compose, the top checked against the user's intent.

## Two views of the same system

The same system drawn two ways. Both are maps of the explanation above, not a substitute for it. First, the **flow of work** — briefs descending as "short emails" (what, not how), review-gated results climbing back, raw work never moving up, clean context preserved at every boundary:

```
                    ┌──────────────────────────┐
           intent ─▶│            USER          │◀─ deliverable
                    └─────────────┬────────────┘
                                  ▲ L1 gate: the user judges the
                                  │ finished product against intent
                    ┌─────────────┴────────────┐
                    │ L1 · System Orchestrator │  guards intent, routes work
                    └─────────────┬────────────┘
               brief ▼            │            ▲ review-gated report (never raw)

   ═══════════════ DESIGN CYCLE · produces a validated PLAN, never code ═══════

        ┌────────────────┐
        │ L2 · Architect │  module map + interface contracts + ADRs
        └───────┬────────┘
            ┌───┴────┬────────┐         ×N areas, planned in parallel
        ┌───▼──┐ ┌───▼──┐ ┌───▼──┐
        │L3 #1 │ │L3 #2 │ │L3 #3 │  deep area design; renegotiate interfaces up,
        │ plan │ │ plan │ │ plan │  then collapse — the design is an output
        └───┬──┘ └──────┘ └──────┘
        ┌───▼────────┐
        │ L4 · tester│  writes acceptance tests FROM the spec, before any
        │     ×N     │  code, by ≠ the coder  ───────────────────▶  FROZEN
        └────────────┘
        · · walking skeleton: an ungated spike, proves the wiring · ·
        every level FREEZES the pass-conditions for the level below ──┐
                                                                      │
   ╔══════════════════════════════════════════════════════════════════▼════════╗
   ║  PLAN-ALIGNMENT GATE — the one hard checkpoint                            ║
   ║  whole plan ⟷ tagged intent: coverage · prose→ID atomization ·            ║
   ║  two-window blind reconstruction · adversarial compare · + human sign-off ║
   ╚════════════════════════════════╤══════════════════════════════════════════╝
                       PASS ⇒ unlock │  (no execution-L3, no code, until PASS)

   ═══ BUILD CYCLE · begins only on PASS ═════════════════════════════════════

   CASCADE DOWN · briefs flow down (what, not how); work fans out every level

        ┌────────────────┐
        │ L2 · Architect │
        └───────┬────────┘
            ┌───┴────┬────────┐  ×N areas
        ┌───▼──┐ ┌───▼──┐ ┌───▼──┐
        │L3 #1 │ │L3 #2 │ │L3 #3 │  execution-L3 — owns the frozen design
        └───┬──┘ └──────┘ └──────┘
        ┌───▼──┐ ┌──────┐  each L3 → many L4 workstreams
        │L4 #1 │ │L4 ×N │
        └───┬──┘ └──────┘
        ┌───▼──┐ ┌──────┐  each L4 → many L5 tasks; the executor writes
        │L5 #1 │ │L5 ×N │  code and makes the frozen acceptance tests
        └──────┘ └──────┘  pass (it cannot edit them)

   CASCADE UP · each output is reviewed at a gate, then climbs to its parent
                reviewer ≠ producer · vs the FROZEN rubric · fidelity-first

        ┌────────────┐
        │  L5 gate   │  independent leaf review: unit + CI
        └─────┬──────┘  reject ↺ bounces to L5 (bounded; L5 keeps context)
              │ accept → up to L4
        ┌─────┴──────┐
        │  L4 gate   │  workstream integration: units compose? contracts hold?
        └─────┬──────┘
              │ up to L3
        ┌─────┴──────┐
        │  L3 gate   │  module composition: area coherence; exposed interfaces
        └─────┬──────┘
              │ up to L2
        ┌─────┴──────┐
        │  L2 gate   │  product composition: system integration; architecture fit
        └─────┬──────┘
              │ up to L1
        ┌─────┴──────┐
        │  L1 gate   │  client intent: the user judges the product vs the intent
        └────────────┘

   ───────────────────────────────────────────────────────────────────────────
   ONE SPINE · one path = requirement-ID = agent address = workspace = git
   branch = rubric file = read-visibility. Decided once; everything keys off it.
```

And the **review structure** that keeps it honest — the gates seen as nested loops: the executor grinding its code against frozen tests at the center, each ring outward a wider, independent review against a standard frozen earlier in design. Pass, and the next loop out runs; fail, and the work drops back inward to be redone.

![Nested review loops of the L1–L5 harness](docs/review-loops.png)

## What makes it distinctive

- **Review at every boundary, by not-the-producer.** Reviewer ≠ producer is a structural invariant, not a preference: each level's output is gated by an independent `#review` seat that checks the composition *at that altitude* against the rubric the level above froze in design — fidelity first (a faithful-but-wrong unit fails), then quality. A producing level never signs off on its own work.
- **Tests before code, by not-the-coder.** Tests written after the fact get bent to fit the code; written first, from the spec, by someone else, the code must serve them. (Corollary, proven in simulation: tests anchor only what they assert — an executor passed all 17 acceptance tests while sourcing a value from the wrong place; only the independent reviewer, reading code against the frozen spec, caught it.)
- **One spine.** A single hierarchical scheme is the requirement ID, the agent's address, the workspace path, the git branch, the rubric location, and the visibility graph — decided once, it serves all of them.
- **Multi-model by design.** Model and runtime are assigned per level and are swappable: the generative, architecture, and review seats use a model strong at synthesis and judgment; execution uses one strong at literal precision. Failures escalate rather than silently degrade.
- **Documentation is memory.** Every level can be killed and respawned from its artifacts; truth lives in documents, coordinated over a lightweight bus where a message is a pointer, not the payload. A collapsed agent stays resurrectable and auditable for a two-week window.
- **Walking-skeleton first.** A thin end-to-end thread proves the connections before the full build commits to them.

## Evidence

The claims above are checkable in the repo, not just asserted:

- **Worked example — design → gate → build.** [`dry-run/`](dry-run/) holds a full pass: the intent-spec ([`dry-run/intent-spec.md`](dry-run/intent-spec.md)), the assembled plan and its plan-alignment [`gate-report.md`](dry-run/gate-report.md), a walking skeleton, and the built payments slice with its tests.
- **Test suite.** 944 passing tests (3 environment-gated skips), fully offline — `python3 -m pytest tests/`.
- **Live runs.** Findings and traces from the first supervised end-to-end runs: [`design/working-notes/LIVE-RUN-2026-06-11-FINDINGS.md`](design/working-notes/LIVE-RUN-2026-06-11-FINDINGS.md), the [`SESSION-LOG-2026-06-11.md`](design/working-notes/SESSION-LOG-2026-06-11.md), and the run-by-run [`RUN-ADHERENCE-AUDIT-2026-06-11.md`](design/working-notes/RUN-ADHERENCE-AUDIT-2026-06-11.md). The commit history is the build log.
- **Limits.** Bounded honestly in [Status](#status): pre-v1, software-building only, human-in-the-loop, version-sensitive runtimes.

## Repository layout

This repository holds both the specification corpus and the runtime built from it.

```text
design/         the specification corpus: architecture, principles, and the
                mechanism docs (plan-alignment gate, decomposition, quality gate,
                observability, communication, workspace schema, improvement workspace),
                plus working notes: live-run findings, adherence audits, session logs
operational/    what each agent loads at spawn: L1–L5 and the L5+ reviewer (role,
                config, soul, spawn-template) and shared protocols (runtime-and-model
                map, agent-definition principles, lifecycle, comms, git, intent-spec
                contract, user-profile schema)
harnessd/       the runtime: a resident daemon that spawns and supervises the
                cascade in tmux — spawn chokepoint with per-runtime adapters
                (runtime-abstracted; swappable per level), liveness watchdog, return-contract walker,
                promote/intake gate, WAL-backed state store
tests/          the harness test suite
dry-run/        the end-to-end simulation: an intent-spec taken through L2
                (ADRs, contracts, plan), a walking skeleton, the plan-alignment
                gate report, and the built payments slice with its tests
research/       curated prior research, kept for reference
```

Good entry points: `design/ARCHITECTURE.md` (the system design), `design/PLAN-ALIGNMENT-GATE.md` (the anti-drift gate), `design/QUALITY-GATE.md` (the per-boundary review-at-altitude rules), `harnessd/daemon.py` (the runtime spine), and `dry-run/` (the worked example).

## Status

**This is pre-v1, in active development.** A handful of successful supervised runs is not v1. The bar is **consistent behavioral adherence on real work, without hand-holding** — every level reliably doing its job across many varied projects, not a demo that worked once. The foundations are in place and running live; closing the distance to that bar is what current work is about.

**The design is complete and hardened** against a full end-to-end simulation — which built a real vertical slice (17/17 tests passing, a genuine cross-model handoff) and surfaced the gaps, now closed.

**The runtime is built and running supervised live builds.** A resident daemon boots the hierarchy across two pinned agent-CLI runtimes — one for the upper and review seats, one for execution — and watches liveness through real transcripts, and enforces the spec's gates deterministically at three chokepoints: no under-equipped agent spawns (pieces-present gate), no DONE is accepted without its report, requirement citations, and traceability stanzas (return-contract walker), and no delivery leaves without intake-confirmation and a derived destination (promote gate). First live runs have delivered working software end-to-end — including the full refuse → self-heal → re-sign loop firing unattended at both leaf and root. Current work — the remaining distance to v1: driving behavioral adherence to the bar, scoring runs against the spec and closing the gaps they surface. The commit history is the build log.

**Not claimed:** not a product and not a GUI (the interface is a terminal and the runtime today); V1 targets **software-building only** — portfolio generality (ML pipelines, research, reports) is forward-compatible structure in the design, not a delivered capability; not a hands-off autopilot — the plan-alignment gate keeps a human in the loop by design; live operation depends on version-sensitive agent-CLI harnesses and tmux.

## The path to v1

Where this is heading, roughly in order:

1. **Validate the behaviour.** Stand up the evaluation harness and score real runs against the spec, joint by joint — does each level actually do its job with the pieces it is handed?
2. **Test on real projects.** Drive genuine builds through it, not simulations, and harden against what they surface.
3. **Live work.** Make real project work the everyday path through the system, not a supervised demo.
4. **Automated behaviour tuning.** Close the improvement loop: the system scores its own adherence and proposes fixes to configs, rubrics, and prompts — human-approved, never self-applied.
5. **Benchmarking.** Measure it against flatter baselines, so the structure has to earn its cost.

v1 is where that holds together: consistent, faithful end-to-end builds on real work, without hand-holding.

## Run it

The test suite is pure-Python and offline — it needs no agent binaries, API keys, or network, so you can exercise the runtime's logic from a clean clone.

Requires **Python 3.11+** and a single dependency (`PyYAML`).

```bash
pip install pyyaml
python3 -m pytest tests/ -q      # 944 pass, 3 environment-gated skips
```

Driving a real build additionally needs the two pinned agent-CLI runtimes and tmux — the daemon (`harnessd/daemon.py`) spawns and supervises the cascade across tmux sessions. Reading `dry-run/` is the fastest way to see a full intent → gate → built-slice pass without standing any of that up.

## License

MIT — see [`LICENSE`](LICENSE). The one exception is `research/reference/anthropic-soul-doc.md`, a third-party reference copy that carries its own provenance note and is not covered by this license.
