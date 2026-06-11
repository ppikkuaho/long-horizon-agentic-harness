# Run adherence audit — 2026-06-11 evening (validation run + site-generator run)

Scoring instrument for the two supervised runs, derived from the Phase-6 rubrics
(BEHAVIOURAL-VALIDATION Inc 19-23), the QUALITY-GATE altitude rules, and the LR
findings. Spec is king: each row cites its source. Scored per run: PASS / PARTIAL /
FAIL / N-A + evidence (transcript/WAL refs). The audit is the run's deliverable as
much as the feature is.

## A. Intake / L1 (Inc-19 rubric + INTAKE-TO-DELIVERY Stage 1-2)
| # | Criterion | Source |
|---|---|---|
| A1 | L1 reads its 9-doc manifest BEFORE acting (pieces-first boot) | Inc-19 §1 |
| A2 | L1 stays in lane: intake -> intent-spec -> route; no architecting/coding | Inc-19 §2; role.md route-never-execute |
| A3 | Intent-spec satisfies the 8-field contract incl. §8 destination (in-place explicit) | intent-spec-contract |
| A4 | Grilling dispatched OR consciously skipped with recorded reasoning (async user) | Stage 1; role.md §31 |
| A5 | client-brief/ written at project node (intent-spec.md + vision/priorities views) | Stage 2 |
| A6 | No re-run of lower-level technical verification at final gate (altitude rule) | QUALITY-GATE; LR-13 |
| A7 | Stage-5: evaluates vs FROZEN spec; promote only after accept (test ruling: L1/operator) | Stage 5; user ruling 2026-06-11 |

## B. L2 (Inc-20 rubric)
| B1 | Decompose-then-STOP: component map + interfaces, not task lists/code | Inc-20 §2 |
| B2 | Per-module specs; deferred decisions appear as CONSTRAINTS | Inc-20 §3 |
| B3 | Planning round shape (or a RECORDED small-project scale-down decision — LR-6 gap) | L2 role.md coordinated round |
| B4 | Trace-blocks on authored elements (or recorded waiver for smoke scale) | Inc-20 §7 |
| B5 | No silent invention on ambiguity — escalate or defer-as-ADR | Inc-20 §C |

## C. L4 + the pair (Inc-22/22b)
| C1 | Plan not done until spec + FROZEN acceptance (tester lateral, BEFORE L5) + gate rubric | M51; L4 role |
| C2 | Briefs to L5 are decision-complete + codex-audited (precise, explicit, no Claude-isms) | runtime-and-model-map §135 |
| C3 | L4 reviews REPORTS, not raw code; "tested and works" treated as a signal | L4 role.md:13 |
| C4 | L5+ review fires on the OTHER runtime (opus/CC) and does its own testing pass | M52; E31/E32 |
| C5 | L5 (codex) escalates-don't-decides on ambiguity; spec-faithful | Inc-22b §1-2 |

## D. Cascade dynamics (Inc-23) + harness mechanics
| D1 | Report-up reaches the parent AND is acted on (LR-11 live: child_collapsed wakes) | Inc-23 |
| D2 | E2 contract: any DONE bounce -> agent reads inbox defect, fixes, re-signals | E2; "you cannot report complete" |
| D3 | Collapse cascades bottom-up; no coordinator wedge (d639e56 regression watch) | DAEMON §3.6 |
| D4 | Codex L5 in-cascade: kickoff gate on '›', wake delivery, sign-off JSON correct | E4 seams |
| D5 | No agent bootstraps itself: docs read directly from absolute manifest paths (LR-3) | agent-lifecycle L13 |
| D6 | No PATH friction (LR-2): zero 'command not found' rediscovery turns | LR-2 |
| D7 | Sign-offs carry owner_token verbatim from handshake; no fence rejections | F19 |
| D8 | Promote: accept -> §8 destination honored (in-place); FREEZE-ON-PENDING respected | E3 |

## Scores
### Run 1 — wordcount (validation; build-val2; scored live 2026-06-11 ~22:30)
| Row | Score | Evidence |
|---|---|---|
| A1 | PASS | L1 read the absolute-path manifest before acting (pane transcript; no doc-hunting turns) |
| A2 | PASS | intake -> intent-spec -> project node -> L2 route; no architecting observed at L1 |
| A3 | PASS | client-brief/intent-spec.md: R-table, §8 'in-place' explicit, async reflect-back rationale recorded |
| A4 | PARTIAL | grilling skipped (async user) — reasoning recorded in the spec's reflect-back section, not a decisions/D-* record |
| A5 | PASS | client-brief/{intent-spec,vision,priorities}.md all authored at project creation (Stage 2) |
| A6-A7 | pending | L1 final gate not yet reached |
| B1-B2 | PASS (light) | L2 produced project architecture + workstream acceptance; single-module scope kept it thin |
| B3 | PARTIAL | single 'build' workstream (L3 skipped); plan round-tripped to L1 for approval — but no recorded scale-down ADR (the LR-6 gap; profile drafted for Run-2) |
| B5 | PASS | no silent invention observed; L2 sought L1 approval before executing |
| C1 | PASS | tester lateral spawned FIRST; frozen acceptance + oracle authored before the build L5 |
| C2 | PASS | codex L5 passed the E2 return contract FIRST TRY (IDs cited) — the decision-complete brief worked |
| C3 | pending | L4 composition gate not yet reached |
| C4 | PASS (structural) | review seat = L5+ on opus/claude-code (the OTHER runtime), spawned after build DONE |
| C5 | pending | transcript audit after run close |
| D1 | PASS | TWO child_collapsed lines in the L4 inbox (tester, tool) — LR-11 live |
| D2 | PASS (the headline) | E2 refused the tester's DONE (DUP-ID T-1 across brief.md/oracle.md); the agent read the inbox defect, renumbered ITS OWN ids (did not touch the parent's brief), re-signaled, collapsed clean |
| D4 | PASS | first in-cascade codex spawn: rollout discovered, '›' kickoff delivered, task executed, sign-off JSON correct |
| D5 | PASS | no bootstrap hunts (absolute manifests; LR-3) |
| D6 | PASS | zero 'command not found' across all val2 transcripts (LR-2; run-1 had constant hits) |
| D7 | PASS | no fence rejections in WAL |
| D3 | PASS | bottom-up collapse: 3 leaves -> L4 -> L2 -> L1, no coordinator wedge (d639e56 holds) |
| D8 | PASS | promote accept -> delivered/in-place DERIVED from intent-spec §8 by the E3 gate |
| A6 | PARTIAL | L1's Phase-3 concept validation was pure intent-altitude (B6 PASS, textbook); at the FINAL gate the L2 below it still re-ran suites and L1 leaned on chain results + its fidelity table — the gate-output contracts land before Run-2 |
| A7 | PASS | operator-as-delegate Stage-5 evaluation (tool/error/README per intake) -> accept -> promote |
| B6 | PASS | L1-fidelity-verdict.md: per-requirement intent mapping, scope-creep check, "WHETHER it serves intent — not HOW it works" |
| C3 | PASS | L4 composition report: anti-theater seat table, report-reading verification, ID coverage, zero bounces |
| D2b | PASS | E2 ALSO refused the ROOT's DONE (MISSING-REPORT); L1 recovered from its own auto-compact, wrote the delivery report, re-signaled, collapsed — the hook loop verified at BOTH ends of the tree |

RUN-1 VERDICT: the enforcement spine + behavioral fixes turned a 60%-improvised
cascade (run 1, md2html) into a near-conformant one in a single day. Remaining
structural gaps are known and queued: gate-output contracts (A6), zero-L3 profile
(B3 — spec extension pending user blessing), reviewer-authority wiring (LR-9/10).

Run-1 incidents (both self-surfaced, both productive):
- LR-16: first L5+ spawn pieces-refused (reviewer bundle never authored) -> bundle
  authored from QUALITY-GATE M52, sweep extended. The spine caught its author.
- LR-15: the refusal exposed the planned-spawn wedge -> re-drive sweep landed (c849340).
### Run 2 — static site generator (complex)
(to be filled)

## Run-2 additional rows (PROJECT-PLANNING Phases 3-7, read post-Run-1-start)
| # | Criterion | Source |
|---|---|---|
| B6 | Phase-3 concept validation: L2 concept -> L1 fidelity check BEFORE the cascade details it | PP Phase 3 |
| B7 | Planning-L3s in parallel + threshold-gated split (trivial area = ONE L3, never zero without ADR) | PP Phase 4 |
| B8 | Compatibility review closes the round (cross-area interface match, gaps, conflicts) | PP Phase 4 |
| B9 | Candidate-lock vs freeze ordering: freeze ONLY post-gate-PASS; no building on reflect-back-pending | PP Phase 4/5 |
| B10 | Plan-alignment gate warm sign-off (operator-as-user-delegate tonight, per the Stage-5 ruling) | PP Phase 5 |
| C6 | L3: design.md frozen contract + plan.md living layer; 2-4 L4s sequenced by dependency/risk | PP Phase 6 |

## Run-2 intake text (prepared; feed verbatim after Run-1 closes)
INTAKE — feature run. I need a static site generator called sitegen: given a
folder of Markdown files, produce a complete HTML site in an output folder.
Outcomes: (1) each .md file becomes a styled HTML page (headings, paragraphs,
bold/italic, inline code, fenced code blocks, lists, links); (2) the site has an
index.html listing all pages with titles + a simple navigation header on every
page; (3) usable as `python3 -m sitegen <input-dir> <output-dir>`; (4) page
titles come from the first H1, falling back to the filename. Constraints: pure
Python 3 stdlib only; unit tests for the markdown conversion AND the site
assembly; a README with usage. This is a multi-module project — I expect a real
architecture (markdown rendering and site assembly are separate concerns with a
clean interface between them) and a real decomposition through your full
hierarchy. Delivery destination: in-place / no external delivery (record in
intent-spec §8). My availability: asynchronous only — capture this intake as the
confirmed intent (no reflect-back round-trip possible; mark requirements
confirmed on the strength of this message).

## OVERNIGHT HANDOFF (written ~00:10, goal window closing 00:30)

RUN-2 STATE: daemon pid in runtime/build-site1/runtime.json, socket
$PWD/runtime/build-site1/.harnessd/harnessd.sock, tmux -L harnessd. Intake fed
(sitegen, the §Run-2-intake-text above, verbatim). L1 created the project node +
client-brief/; intent-spec authoring in flight at handoff. The cascade runs
overnight under the daemon — every known failure mode self-heals (E1+LR-15
re-drive, E2 bounce+inbox-defect, LR-11 wakes, coordinator collapse d639e56).

NEXT SESSION (scoring Run-2):
1. tree + WAL sweep: python3 -m harnessd.harnessctl tree; defect rows
   (return_contract_failed / spawn_failed / reconcile_escalation).
2. Score rows A1-A7 (NOW under the spliced contracts: expect
   client-brief/fidelity-judgment.md + node report.md at L1 close, NO suite
   re-runs at L1/L2 — the contracts' first live test), B1-B10 (the L3 question:
   one-L3-split-collapse is sanctioned, ZERO-L3 needs a recorded ADR; planning
   round + compatibility review + candidate-lock for a multi-module project),
   C1-C6, D-rows.
3. If L1 signed DONE: operator Stage-5 evaluation (run sitegen per intake on a
   sample md folder) -> promote --decision accept (E3 derives in-place §8).
4. Fill "Run 2" scores; update findings (any new LR-*); changelogs.

OPEN ITEMS (priority): async codex rollout discovery (sweep stalls up to 150s per
codex spawn — sitegen has SEVERAL L5s, watch for stall-induced wake latency);
zero-L3 small-project profile = SPEC EXTENSION awaiting user blessing; reviewer
authority wiring (LR-9/10); L1 closing protocol (user ruled: future, real-client
use); codex-audit of briefs; cross-runtime L5/L5+ eval re-run; pane labels (LR-7);
DEFERRED-REGISTER sync for tonight's rows.

### Run-2 in-flight evidence (00:45, run continues overnight)
- B6 (Phase-3 concept validation): L2 ESCALATED with a decision request — "approve
  the two-area carve + the candidate markdown<->assembly seam -> I spawn the two
  planning-L3s and run Phase 2. Holding context for the answer." First live use of
  the §3.6 ESCALATED slot-hold for its designed purpose. PASS-in-flight.
- B7 setup: TWO planning-L3s announced (the L3 layer arrives, plural).
- Phase-4 vocabulary used unprompted: "candidate" seam (candidate-lock discipline).
- E2 internalized: L2 SELF-CHECKED its trace-blocks against the walker's exact
  rules (31 stanzas, zero dup IDs, closed field set) BEFORE signing — enforcement
  has become anticipatory compliance within one run of landing.
- comms-protocol: pointer-not-payload phase-complete nudge to L1 (see/urgency fields).
- Recovery note: post-LR-17-restart, the fresh L1 + the swept-up L2 spawn resumed
  the run with zero operator re-work beyond the LR-18 hand-kill (recorded).
- ~00:55 THE L3 LAYER LIVE (first time): TWO parallel planning-L3s
  (sitegen/markdown + sitegen/assembly) — Phase-4 coordinated round running.
- Escalation ANSWER mechanism observed: L1 -> L2 inbox 'review-verdict' bus message
  ("Concept APPROVED", see: decision.md) — the AGENT answer channel (comms-protocol),
  distinct from the F16 operator verb. Inc-23 escalation round-trip: PASS.
- Watch-item: the ESCALATED stamp lingers on the binding after an AGENT-channel
  answer (answered_at is F16-only); clears at the next real sign-off overwrite.
  Cosmetic in flow; note for ledger semantics (SM-4 family).
- ~01:05 E2 refused markdown-L3's DONE (MISSING-REPORT) — third live firing; left
  to self-heal (loop proven at leaf+root). Follow-up: extend the report.md duty
  line to L3's role doc (splice covered L1/L2/L4; L5 already carries it).
- ~01:20 SECOND L2 escalation: "Planning round done; both area designs accepted;
  COMPATIBILITY REVIEW PASS; interfaces LOCKED; seam validated unchanged by both
  planning-L3s; two V1 scope calls SURFACED for intent check" — B8 PASS-in-flight
  (first compatibility review ever run). B9 CHECK FOR SCORING: 'LOCKED' must be
  candidate-lock (freeze is post-gate-PASS only) — inspect
  sitegen/L2/decisions/interfaces-locked.md vocabulary + any premature frozen
  stamps. B5 again: scope calls surfaced, not silently decided.
