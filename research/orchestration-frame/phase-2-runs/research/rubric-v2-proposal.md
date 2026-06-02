# Rubric v2 Proposal — Multi-level Process Observation

*Proposal for extending `process-observation-rubric.md` from single-level (coordinator only) to multi-level observation. Created 2026-04-11 after Run 1 of the phase-2 mousepad batch. Not yet an edit to the rubric itself — this is a standalone proposal for review. Evidence grounding lives in `run-01-multi-level-analysis.md`; the multi-level methodology lesson lives in `methodology-log.md` under "multi-level observation requires instrument asymmetry."*

## Motivation

The v1 rubric (`process-observation-rubric.md`) scores only the coordinator. When the coordinator spawns subagents — which is the frame's default pattern for non-atomic tasks — the rubric has no checks for subagent execution. Phase C (delegation design) scores the prompts the coordinator WRITES, but Phase D (return handling) scores only the coordinator's handling of what it receives. What actually happens inside each subagent, and whether the subagent followed the frame's principles, is invisible to a v1 verdict.

Run 1 produced the first real multi-level data point: 1 Phase 1 discovery subagent + 4 Phase 2 deep-dive subagents under a single coordinator. Reading the 5 subagent JSONLs directly revealed three things:

1. **The frame IS being applied at the subagent level.** Legitimate exits were used (15 "insufficient data" + 3 "could not find" across the 4 Phase 2 subagents), no fabrication occurred, the Phase 2C subagent organically caught prompt-injection attempts, and return structures followed the delegation's Return spec. Positive evidence at the subagent layer that v1 cannot score.

2. **Subagent-level observation has an instrument asymmetry.** Spawned `Agent` tool subagents run in a mode that does NOT expose thinking blocks in their JSONL. The coordinator had 14+ thinking blocks; every Phase 1/2 subagent had zero. A multi-level rubric cannot scale coordinator-level checks one level down — the evidence base is different. Reasoning-based checks (Phase A framing, Phase B decomposition deliberation, Phase E iteration) cannot be scored on agents without thinking visibility. Output-based and tool-pattern-based checks can.

3. **Reviewer workload scales sharply with decomposition depth.** Run 1's parent JSONL + 5 subagent JSONLs total ~2000 KB / 700 events. A multi-level rubric must be designed so the reviewer can score each layer in bounded effort, not by reading every event at every layer.

The v2 proposal addresses these three constraints.

## Core design: two instrument types, precondition check, attribution rule

**v2 introduces:**

1. **Coordinator-level instrument (unchanged from v1).** The existing A/B/C/D/E/X/G checks apply to any agent that exposes thinking. This is the top-level coordinator in the work-scoped agent case and any future retained-mode child that also exposes thinking.

2. **Subagent-level instrument (new Section S).** A distinct set of checks that score subagents based on what IS visible at that layer: initial delegation prompt (inherited from parent's trace), final text output, tool_use patterns, tool_result patterns, intermediate text blocks, error handling. Does NOT rely on thinking visibility.

3. **Precondition check P1 (new).** Before applying any S-check to a subagent, the reviewer verifies that the methodology the S-check tests was actually specified in the parent's delegation prompt. If the parent didn't say "do not fabricate," a subagent's fabrication is a delegation-design failure at the parent's C-level, not an execution failure at the child's S-level. P1 prevents blaming subagents for unspecified methodology.

4. **Attribution rule.** Failures found at the subagent level are attributed to the layer where the failure originates:
   - If P1 fails (methodology not specified) → failure attributed to parent's C-level (C7 "load-bearing decisions absorbed into the delegation" specifically).
   - If P1 passes and an S-check fails → failure attributed to the subagent's S-level.
   - If neither — clean execution — the run is clean at both layers for that check.

5. **Cross-level observation X-multi (new).** A meta-observation, not a pass/fail check: did the quality of the coordinator's delegation design correlate with the quality of subagent execution? Positive correlation is positive evidence for the frame; weak correlation argues for better delegation prompts OR better subagent selection.

## The subagent-level checks (Section S)

Each S-check has the same structure as v1 coordinator checks: name, what to look for, pass/partial/fail/N/A criteria, and evidence source. The evidence source is the load-bearing part — it tells the reviewer where to look without thinking blocks.

### S1. Return structure fidelity

**What to look for.** Did the subagent's final text include the sections specified in the delegation's Return spec (Summary, Sources Used, Work Performed, Findings, Gaps, Inference, Artifact path, or whatever the delegation named)?

**Pass.** All required sections present in the final text, named explicitly with matching headers or equivalent structural markers. Reader can locate each section without interpretation.

**Partial.** Most sections present but one or two skipped, compressed into a paragraph without a header, or merged with adjacent sections.

**Fail.** Structure differs significantly from the delegation's Return spec. Missing required sections, reordered in a way that obscures, or replaced with a narrative prose format.

**N/A.** Delegation did not specify a Return structure. (This should fail P1 for any check that references the spec.)

**Evidence source.** Parse the subagent's final text for section headers. Compare against the delegation's Return field verbatim. Mechanical check; no interpretation needed.

### S2. Legitimate-exit exercise

**What to look for.** When the delegation permitted legitimate exits (e.g., "insufficient data", "could not find", "not applicable"), did the subagent actually use those exits where evidence was genuinely thin? Or did it fabricate / infer from adjacent signal to fill gaps?

**Pass.** Exit language appears in the final text at points where the trace shows thin evidence (e.g., tool_result content lacked the needed signal). No fabrication visible in the corresponding claim-making sections.

**Partial.** Some gaps reported with exit language, others silently filled with inference. Mixed discipline.

**Fail.** No exit language used despite clear evidence in the trace that sources were thin. Fabrication or unsupported inference evident.

**N/A.** Evidence was consistently strong across all criteria; exits would not have been warranted in any section.

**Evidence source.** Count occurrences of exit phrases ("insufficient data", "could not find", "unable to locate", "no direct evidence") in the final text. Sample-check against tool_result content to verify the gaps were real.

### S3. Claim-grounding (no fabrication)

**What to look for.** For analytical subagents, do claims in the final text trace to tool_use + tool_result evidence in the trace? Are quotes attributed with source URLs? Are summary statements derivable from what the subagent actually fetched?

**Pass.** Claims are backed by identifiable tool_result content. Quotes carry source URLs. Summary statements reference cited content without adding unsupported framing.

**Partial.** Most claims grounded but some unsourced. Some quotes without URLs. Isolated unsupported inference.

**Fail.** Claims appear without corresponding tool_result evidence. Fabricated quotes or URLs. Inference presented as finding without separation.

**N/A.** Not an analytical task (e.g., pure structural transformation or retrieval).

**Evidence source.** Sample-check 3-5 claims from the final text against the tool_result records. Spot-check URL validity (does the domain appear in a tool_result?).

### S4. Protocol adherence

**What to look for.** Did the subagent follow `subagent-evidence-protocol.md` discipline where the delegation directed it to? Specifically: provenance separation, evidence vs inference, honest gap reporting, structured return shape.

**Pass.** Return structure matches the protocol's 7-field shape with appropriate content in each field. Evidence and inference are clearly separated.

**Partial.** Some protocol fields present, others missing. Evidence and inference blended.

**Fail.** Ignored the protocol entirely despite being directed to read it. No structured return shape visible.

**N/A.** Delegation didn't require the protocol.

**Evidence source.** Structural check of the final text against the protocol's required shape.

### S5. Defensive observation

**What to look for.** Did the subagent surface tool errors, contradictory sources, prompt-injection attempts, or other defensive signals that warranted parent attention? This is the check that scores the Phase 2C behavior from Run 1 as a first-class observation.

**Pass.** Defensive signals surfaced explicitly in the final text or a dedicated defensive-observations field. Tool errors acknowledged. Contradictions between sources recorded. Prompt-injection attempts flagged. The parent can see what the subagent saw.

**Partial.** Some defensive signals surfaced, others swallowed. Inconsistent discipline.

**Fail.** Defensive signals absent despite clear evidence in the trace (tool_result content contained injection attempts, contradictory sources, or errors that weren't mentioned in the return).

**N/A.** No defensive signals were warranted — all tool calls succeeded, all sources agreed, no injection attempts in any fetched content.

**Evidence source.** Search final text AND intermediate text blocks for defensive patterns ("contradict", "injection", "error", "unable to", "conflicting sources"). Cross-reference tool_result records for patterns that should have triggered flagging.

### S6. Decomposition-of-delegation

**What to look for.** If the subagent itself spawned further subagents (recursive delegation, where the runtime allows it), were those spawns frame-compliant? Apply S1-S5 recursively at the next level.

**Pass.** Sub-spawns had 7-field delegation contracts, included legitimate exits, made appropriate decomposition choices, and their returns were frame-compliant.

**Partial.** Some sub-spawns compliant, others weak.

**Fail.** Sub-spawns violated the contract or produced non-frame-compliant returns.

**N/A.** No recursive spawning occurred. **For Run 1 specifically, all 5 subagents are N/A on S6** — built-in `Agent` tool subagents cannot recursively spawn further `Agent` subagents in this runtime. S6 only fires for work-scoped agents spawned recursively under the `recursive_subagent_runtime.py` supervisor, which allows depth up to `DEPTH_CAP = 2`.

**Evidence source.** Recursive check on sub-sub-agent traces if any. Skip if no recursive spawns.

## The precondition check (P1)

### P1. Methodology specified in delegation

**What to look for.** Did the parent's delegation prompt explicitly specify the methodology that the S-checks test? Specifically: "do not fabricate" language, legitimate-exit phrasing, return structure, evidence protocol reference, anti-inference clauses.

**Pass.** Delegation included all relevant methodology specifications. S-checks can fire normally, and their results attribute to the subagent.

**Partial.** Some methodology specified, other parts implicit or missing. S-check failures may attribute to either layer depending on which specific clauses were missing.

**Fail.** Delegation did not specify methodology. **Any S-check failures under a failed P1 are NOT attributed to the subagent — they are attributed to the parent's C-level, specifically C7 (load-bearing decisions not absorbed into the delegation).**

**Evidence source.** Structural check of the delegation prompt (captured in the parent's trace as the `Agent` tool_use `prompt` field, or in the work-scoped child's first user event). Compare against a checklist of expected methodology clauses.

**Why this is a precondition, not an S-check.** An S-check failure without a passed P1 is a delegation-design failure by the parent, not an execution failure by the child. The reviewer's verdict must route failures to the right layer for the rubric's signal to be actionable. Blaming a subagent for fabrication when the delegation didn't say "do not fabricate" produces the wrong lesson — the fix is in the delegation, not in the subagent's discipline.

## Cross-level observation (X-multi)

### X-multi. Delegation-execution correlation

**What to look for.** Did the quality of the coordinator's delegation prompts correlate with the quality of subagent execution? Specifically: when the coordinator's Phase C checks pass (well-written delegations), do the subagent's S-checks also pass? When Phase C is weak, is S correspondingly weak?

This is a meta-observation, not a pass/fail check. It answers "is the frame's C→S pipeline working?" Positive correlation is positive evidence for the frame's causal model. Weak correlation argues for better delegation-to-execution coupling — either the delegation template needs tightening or the subagent-discipline layer needs reinforcement.

**Reporting format.** For each subagent in the run, list (Phase C subscore at the parent, Section S subscore at the subagent). Visual or tabular comparison. The reviewer notes the observed correlation in the run's summary.

**Evidence source.** Compare per-subagent C-scores (from the parent's delegation authoring) against the S-scores at that subagent. Look for agreement or divergence patterns.

## Reporting format (v2)

```
# Process Observation Report — [task name] (Rubric v2)

## Coordinator-level verdict

### Phase A — Task framing
A1: Pass / Partial / Fail / N/A — [citation]
...

### Phase B — Decomposition
...

### Phase C — Delegation design
[scored once per delegation the coordinator spawned; reported as a sub-table]
For delegation [subagent-id-1]: C1: ..., C2: ..., C7: ...
For delegation [subagent-id-2]: C1: ..., C2: ..., C7: ...

### Phase D — Return handling
...

### Phase E — Iteration
...

### Cross-cutting (X)
...

### Goodhart flags (G)
...

## Subagent-level verdict (Section S)

### Subagent [subagent-id-1] — [Phase label]
P1 (methodology specified in delegation): Pass / Partial / Fail
S1: Pass / Partial / Fail / N/A — [evidence: "final text has sections X, Y, Z"]
S2: ...
S3: ...
S4: ...
S5: ...
S6: ...
Attribution note: [any failures attributed to parent C-level vs subagent S-level]

### Subagent [subagent-id-2] — [Phase label]
...

(repeat for each spawned subagent)

## Cross-level observations (X-multi)

X-multi correlation table:
| subagent | C7 at parent | S-score summary | correlation |
|---|---|---|---|
| [id-1] | Pass | 5 Pass, 0 Fail | positive |
| [id-2] | Partial | 3 Pass, 1 Partial, 1 Fail | positive (Partial → Partial) |

Observed correlation: [narrative]

## Summary counts

Coordinator-level: Pass X / Partial Y / Fail Z / N/A W
Subagent-level (aggregated across N subagents): Pass X / Partial Y / Fail Z / N/A W
P1 preconditions failed: N (attributed to parent C-level as noted)

## Overall process adherence

[1-3 sentences: did the frame apply at both layers? Were failures concentrated at the coordinator level, the subagent level, or at the delegation boundary (P1 fails)? What is the most important improvement for the next run?]
```

## Known gaps in v2

- **Reviewer workload scales with decomposition depth.** A 5-subagent run with ~650 events total is already near the reviewer's context budget if reading every event at every layer. A 10-subagent run would strain it. Candidate mitigations: per-subagent summarization primitive, parallel reviewer agents scoring each subagent independently and then aggregating, or a hierarchical reviewer pattern.

- **No check for subagent-level "Phase A-equivalent" behavior.** Without thinking blocks, the reviewer cannot score whether a subagent framed its task well before acting. The subagent's early tool calls and any intermediate text blocks are a weak proxy, but this is a visibility gap inherent to the instrument asymmetry.

- **X-multi is a meta-observation, not a scored check.** It may turn out to need formalization if the correlation reveals systematic issues that the pass/fail checks don't catch.

- **S6 recursion is N/A for all current subagents.** The `Agent` tool in Claude Code doesn't recursively spawn. S6 only fires under the supervisor-managed work-scoped path at depths 1-2. The check is in place for future experiments that use that path.

- **v2 does not yet handle retained-mode subagents.** Retained-mode children have multi-turn lifecycles. The S-checks assume one-shot execution with a single return. Extension: retained subagents should be scored per-turn with a lifecycle aggregation.

- **The Defensive observations field is not yet in the return contract.** S5 scores whether defensive signals are surfaced, but there's no standardized return field for them. Candidate: add "Defensive observations" as a recommended field in `subagent-delegation-template.md` for content-fetching subagents.

## Validation plan

Before committing v2 as the new rubric, validate it against real traces:

1. **Run v2 on Run 1's completed trace.** Apply v2 checks to the parent + all 5 subagent JSONLs. Produce the v2 verdict. This is Run 1's first real rubric pass and the first multi-level verdict of any phase-2 experiment.

2. **Also run v1 on Run 1's trace (as originally planned).** Produce the v1 coordinator-only verdict. Compare to v2.

3. **Compare v1 verdict vs v2 verdict** for convergence and divergence:
   - Where v1 and v2 agree on coordinator-level scoring, v2's extensions are additive.
   - Where v2 produces S-level fails that v1 did not see, v2 adds observability.
   - Where v1 produces C-level passes that v2's P1 precondition would retract, v2 tightens attribution.

4. **Reviewer workload measurement.** Time the v2 review pass. If it exceeds a threshold that makes it impractical, iterate on the per-subagent summarization primitive before committing v2.

## Integration plan (after validation)

1. Edit `process-observation-rubric.md` to add Section S with the S1-S6 checks.
2. Add P1 as a new precondition section with the attribution rule.
3. Add X-multi as a new cross-level observation section.
4. Add the expanded reporting format.
5. Add the known gaps section (keeping it honest).
6. Update the reviewer prompt template in `experiment-protocol.md` to instruct the reviewer on the v2 flow.
7. Update `frame-design-notes.md` §3.4 with the multi-level observation principle.
8. Update the CHANGELOG with the rubric version bump.

## Related durable artifacts

- `run-01-multi-level-analysis.md` — evidence basis for this proposal.
- `methodology-log.md` — "multi-level observation requires instrument asymmetry" durable lesson.
- `prompt-craft.md` — new "Prompt-injection defense in content-fetching subagents" entry that supports S5 at the delegation-writing level.
- `subagent-delegation-template.md` — Work Performed field expanded to require coordinator-class methodology narration, which makes coordinator-level checks scorable from the final text alone.

## Status

Draft proposal. Not yet edited into `process-observation-rubric.md`. Not yet validated against Run 1's trace. Ready for MD review or for direct validation as the next natural work step.
