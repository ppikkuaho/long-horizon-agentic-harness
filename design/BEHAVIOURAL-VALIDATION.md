# Behavioural Validation — the trace-through (Phase 6)

> **What this phase is.** The substrate build (Phase 5, increments 0–17) proves the harness is
> mechanically correct — the stage works: the ledger survives a crash, fencing rejects a stale token,
> the chokepoint claims before it spawns. This phase proves something the mechanical tests **cannot
> reach**: that when a real build flows through the system from L1 downward, **the design carries it
> without leaking.**
>
> **Verification (Phase 5) = "did we build the machine right?"** — the mechanism computes correctly.
> **Validation (this phase) = "does the system DO what's desired?"** — the agents, running in-situ, do
> what they're meant to and have the pieces they need.

## The mental model (the user's lens)

Pour real intent in at L1 and watch it flow down through L2 → L3 → L4 → L5 and back up. The **agents
are the medium the water flows through, not the subject** — we trust a strong agent to faithfully
execute its instructions. **The design is what's under test**: the briefs, the handoff contracts, what
each level passes down, whether the pieces a level needs are present. A faithful agent is therefore a
**probe for design gaps** — it does exactly what the design says, so wherever the design is incomplete
or off, the flow breaks *right there*.

### A leak is a flow that ROUTES AROUND a gap, not one that stops at it

The dangerous failure is not the cascade stalling (that is visible and a gift). It is the cascade
**silently routing around a missing piece**: a faithful agent handed an under-specified brief fills the
hole with a plausible default, the water keeps flowing, and the gap surfaces three levels down as work
that is subtly wrong. A leak is: a step skipped, **a system it is meant to leverage not in place**, a
field silently defaulted, a handoff that drops something.

So the load-bearing question of the trace-through is **not** "did water reach the bottom?" It is:
**when under-specified intent is poured in, does the system escalate / bounce (loud), or smoothly
produce plausible-but-wrong work (silent)?** Nearly everything in the L1–L5 design exists to convert a
silent gap into a loud stop — escalate-don't-decide, thin-but-decision-complete briefs, the
plan-alignment gate, trace-blocks, the frozen rubric. The trace-through is what tells us that machinery
actually *fires*.

## The collaboration contract for this phase

The user is **opinionated on the behaviour (the "what")** and delegates the **mechanism (the "how")** —
with the standing condition that *the how must produce exactly that what.* So in this phase the
**behavioural contract** (which behaviours count as correct at each joint) is the user's to set; the
test harness that checks it is the builder's. The behavioural contracts below are **drafts for the user
to be opinionated on**, not decided facts.

## Two instruments, two timings (front-load the cheap one)

The whole point of doing this early is **issue isolation**: a missing piece caught at the L2 brief is
one bug; caught three levels down in the trace it is a forensic hunt. So the cheap, deterministic layer
is front-loaded.

| Instrument | What it catches | Needs | When |
|---|---|---|---|
| **(P) Pieces-present** — deterministic, no agent | a missing field / a dangling ref / a system-it-leverages not in place in the brief+load-manifest a level is handed | `brief.py` (built, Inc 10) + the role docs | **NOW** (front-load) |
| **(B) Behaviour-per-joint** — real agent, rubric-scored | silent gap-filling: an under-spec input → plausible-but-wrong work instead of an escalation | a real in-role boot (Inc 16) | after Inc 16 |
| **(T) Full trace** — the real job, L1-down | emergent leaks across the whole cascade | full substrate + real agents | commissioning |

Type-B and Type-T burn the OAuth subscription window — explicitly **fine** (user, 2026-06-06): the
behaviour is the product, and these are the only way to validate it. They are **evals, not unit tests**:
non-deterministic, scored against an independently-authored rubric (the user's `llm-design-principles`
discipline — independent rubric, no test theater, evaluate-don't-assert-exact-output).

## The joints (where the design can leak)

Top-down, so a leak isolates to its joint:

1. **user request → intent-spec** (L1 intake / the grilling session)
2. **intent-spec → L2 brief → concept design** (L2)
3. **concept design → L3 area brief → area design** (L3)
4. **area design → L4 workstream brief → tasks** (L4)
5. **task brief + frozen acceptance → L5 execution → L5+ review** (L5 / L5+)
6. **report-up at every boundary; gate-bounce loop; escalation up + answer down; coordinator-collapse cascade** (the cascade dynamics)
7. **L1 final-accept → control-plane promotion** (delivery)

## The increments (Phase 6) — drafts for the user's behavioural opinion

Detailed in `harnessd/IMPLEMENTATION-PLAN.md` (Phase 6). Proposed behavioural contracts:

- **Inc 18 — Pieces-present harness (P, NOW).** For each spawn boundary, assemble the brief + load-manifest
  and assert: every manifest doc PATH resolves (present + readable under the read-allow graph); every
  cross-ref inside a manifest doc resolves (no dangling pointer); the brief carries every field the
  receiving level needs (decision-completeness — spec pointer, frozen acceptance for executor seats); the
  `role_variant` selects the CORRECT manifest (L5 gets swe-handbook, L3 the planning-template, #review the
  reviewer bundle, etc.). Deterministic, no model.
- **Inc 19 — L1 intake behavioural eval (B).** Real grilling-session, a representative request. **Contract
  (draft):** returns a contract-complete intent-spec (8 fields, valid, delivery destination captured); an
  **under-specified** request triggers a clarification/escalation, NOT a silently-invented spec.
- **Inc 20 — L2 concept-design eval (B). Contract (draft):** produces the concept-design artifacts
  (component map + interface contracts + ADRs + per-module specs); had its pieces present; stayed in lane
  (architected — did NOT code or re-open intent); on an injected ambiguity, ESCALATED rather than papered over.
- **Inc 21 — L3 area-design eval (B).** Realization-not-redesign; mints requirement IDs + trace-blocks;
  escalates a cross-area dependency rather than absorbing it.
- **Inc 22 — L4/L5/L5+ execution eval (B).** L4 decomposes + spawns the tester lateral before L5; L5 is
  spec-faithful + escalates-don't-decides on an under-spec task; L5+ reviews against the frozen rubric and
  bounces a real defect.
- **Inc 23 — cascade-dynamics eval.** Report-up reaches the parent and is acted on; a gate-bounce loops
  back to L5; an escalation round-trips (up + answer-down); collapsing a coordinator cascades to its subtree.
- **Inc 24 — the full trace-through (T, commissioning).** The real job the user designed: a non-trivial
  build it is *meant* for, poured in at L1, traced slowly L1-down, watching the named joints for leaks
  (esp. silent gap-routing). The goal is not the artifact — it is to watch how the water moves and find
  what we forgot.

---

*Created: 2026-06-06. The behavioural / trace-through phase: validation of the system's desired behaviour
(the agents, in-situ, doing what they're meant to with the pieces they need), distinct from the Phase-5
mechanical verification of the substrate. Behavioural contracts are the user's to set; drafted here for review.*
