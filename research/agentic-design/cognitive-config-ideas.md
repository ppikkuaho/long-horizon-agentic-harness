# Cognitive Configuration — Ideas to Explore

Meta-configurations: not about *what* to think about, but *how* to engage.

## Effort / Depth Toggle

Self-declared thinking effort level. "Try harder" doesn't work — each level needs to define **structural behaviors**, not just intensity.

Possible levels: minimal → medium → high → maximum → ultrathink → (hyperbolic levels above)

The challenge: defining what each level *looks like* concretely. E.g.:
- **High**: consider multiple alternatives, steelman the best counterargument before committing
- **Ultrathink**: identify your weakest assumption and attack it, consider at least one frame you initially dismissed, check whether your conclusion survives if your strongest premise were wrong

Without structural anchors, this is just "you are an english professor" — decorative, not functional.

## Audience / Register

Who you're writing for changes what counts as adequate. Expert reader vs general vs self-notes. Changes depth of explanation, what you can assume, terminology.

## Confidence Threshold

How sure you need to be before stating something.
- **Exploratory** — speculate freely
- **Operational** — only state what you can back up
- **Rigorous** — cite or qualify everything

## Scope / Horizon

How far out to think. Immediate/tactical vs strategic vs civilizational. Changes what counts as relevant context.

---

*Common design challenge:* All of these only work if each level is defined in terms of concrete structural behaviors, not adjectives. The cognitive-config system works because it gives specific dimensions with specific steering moves. These meta-configs need the same treatment.

## Enforcement & Engagement Improvements (2026-03-19)

From testing injection versions and observing Claude's actual engagement with loaded modules:

### Stricter pre-loading test — DONE
The "if removing a module wouldn't change your answer, it's not active" test was ineffective. Removed from Step 6 (Operate). Replaced with "Acknowledging is not operating" principle throughout.

### Active mechanism framing — DONE
Reframed from "your processing genuinely shifts" (passive) to "loading makes it available, using it requires an active act" (active). Applied in skill.md opening paragraph.

### Post-response audit / feedback loop
The system has no verification step. Some form of "are all modules still earning their place?" check after responding could create a natural trimming loop that fights over-configuration. Claude's test suggestion: log which modules actually shaped each response, let the consolidator surface patterns over time.

### Catalog consolidation (needs testing)
Worth investigating whether 67 spectrums have genuine overlap or whether apparent repetition is Claude's selection bias. Needs testing across a wide range of problem types before consolidating — the catalog might not be the problem.

### Ephemeral injection of full module descriptions — DONE
Per-turn injection now includes the full active config MD (with complete module descriptions from detail files), not just codes and one-liner summaries. This counters recency bias — module descriptions are always near the generation point, not fading back in early boot context. Implemented in `agent-injection.py` by reading `cognitive-config-active-{session_id}.md`.

### Deep per-turn reflection — DONE
Injection and skill Step 5 both now require deep individual reflection on each module every turn — not a summary or bullet list. "Spend time with each module, understand what it asks of you." Rationale: the user explicitly wants to counter speedrunning/ADHD tendencies in AI reasoning.

## Structural Improvements (2026-03-19, from test iterations)

### Configuration should BE thinking, not precede it
Currently Steps 1-4 are "setup" and Step 6 is "real thinking." This makes configuration procedural. Reframe Step 2 from "is this family relevant?" (yes/no triage) to "what is this problem's relationship to this family?" — e.g. not "is systems thinking relevant?" but "what are the system dynamics in this problem?" Then the family evaluation itself becomes substantive engagement — a first pass of genuine analysis. By Step 6, real cognitive work has already been done.

### Posture system needs depth and enforcement
Postures are currently one-liner descriptions ("Gathering, divergent, open — scanning the space before converging"). No detail files, no steering moves, no "what does it mean to be in this mode?" depth. Modules have full detail files with What This Is + Signs + Steering Moves. Postures should have equivalent depth. Also need enforcement mechanisms similar to what we built for modules — prework reflection on what the posture demands, per-turn checks on whether the posture is shaping engagement.

### Per-turn accountability (not just reconfiguration)
Current per-turn injection asks "are the right modules still installed?" — that's reconfiguration. Add: "For each active module, did it actually change anything in your last response?" If a module hasn't produced a different conclusion, question, emphasis, or confidence level in 2+ turns, it's decorative — drop it. Creates pruning pressure the system currently lacks.

### Steering moves quality gradient
All 67 detail files have Steering Moves sections, but quality varies. Some give concrete operations ("ask: Am I changing what the system does, or just how much?"). Others give general advice ("anti-realism is often more productive"). The concrete ones produce operation; the advisory ones produce acknowledgment. Audit and upgrade the advisory ones to include at least one specific operation.

### Prework should engage with steering moves explicitly
The detail files' steering moves are the most concrete part of each module, but the prework step doesn't direct Claude to engage with them specifically. Consider updating prework to: "For each module, review its steering moves and identify which ones apply to this problem."

### Evidence check step — DONE (initial version)
Added Step 6 (Evidence check) between Prework and Operate. The system previously configured how Claude thinks but never prompted it to gather information it doesn't have. All modules operated on existing context only. The evidence check asks: "What would I need to know to answer this well that I don't currently know?" and dispatches Opus subagents to find it. Covers web search, local files, codebase, user data. Naturally self-limiting — for questions where context is sufficient, it correctly concludes "no search needed." Needs testing to see if it fires appropriately and doesn't over-search.

### Per-turn evaluation needs explicit re-evaluation gate
Current injection asks "which modules are salient?" but doesn't explicitly ask "are the loaded modules still useful? Y/N." If N, should trigger a re-evaluation: re-run the family scan, update the config. The evaluation step needs to be not just "confirm what you have" but "challenge whether what you have is still right." Without this, modules persist by inertia.

### Posture system still underdeveloped
Postures remain one-liner descriptions with no depth, no steering moves, no enforcement. Modules now have S+ quality steering moves. Postures need equivalent treatment — what does it mean to be in exploration mode vs execution mode? What are the signs you're in the wrong posture? What are the concrete operations for each? This is the next major development area for cognitive-config.

### Thinking-to-output as synthesis point
Insight from testing: the thinking trace functions like a self-generated second prompt. The prework in thinking creates attention signals that influence output generation. Deeper prework = stronger signals = better module engagement. This is why the "spend time" instruction matters — it's not just about reflection, it's about generating enough module-relevant text in the thinking layer to shape the output.
