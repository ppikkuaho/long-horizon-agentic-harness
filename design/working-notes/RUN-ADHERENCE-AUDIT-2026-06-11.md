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
| D3, D8 | pending | upward collapse + promote not yet reached |

Run-1 incidents (both self-surfaced, both productive):
- LR-16: first L5+ spawn pieces-refused (reviewer bundle never authored) -> bundle
  authored from QUALITY-GATE M52, sweep extended. The spine caught its author.
- LR-15: the refusal exposed the planned-spawn wedge -> re-drive sweep landed (c849340).
### Run 2 — static site generator (complex)
(to be filled)

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
