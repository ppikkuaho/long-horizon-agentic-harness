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
### Run 1 — wordcount (validation)
(to be filled)
### Run 2 — static site generator (complex)
(to be filled)
