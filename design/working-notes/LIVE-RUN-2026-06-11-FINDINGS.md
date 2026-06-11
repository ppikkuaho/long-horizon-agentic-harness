# First supervised live run — findings (2026-06-11)

Run: unjailed smoke, md2html intake, full L1→L5 cascade reached. User watching live.
This file records what the run surfaced, separated into (A) fixed during the run and
(B) post-run remediation candidates. Source for (B): direct user observation of the
L1/L2/L4 panes mid-run.

## A. Fixed mid-run (committed)

### LR-1 — transcript_path pointed at a file CC never writes (CRITICAL, fixed: 27cea6f)
The adapter minted a session_uuid it never handed to CC and derived the transcript dir
from the tmux session name; CC files by encoded REALPATH cwd under its OWN uuid.
verify-new-turn statted size-0 forever → the idle ladder failed a healthy, legitimately
waiting L1 root (`watchdog_nonresponse`) after three prods, and the sender-side fence
then (correctly) refused to deliver the human intake to the terminal binding.
Fix: `--session-id <uuid>` pins CC's uuid to ours (pinned 2.1.152 supports it);
`_transcript_path` now encodes the realpath cwd (every char outside [A-Za-z0-9-] → '-').
The old test pin was vacuous (TM-class) — replaced with the exact-file contract.
Verified live: recovery respawned L1 at epoch 4 and the recorded file exists and grows.

## Governing posture decision (user, 2026-06-11, mid-run)

"We've gone a bit overboard on security. It's starting to cause friction in the
sandbox / PoC phase, which is not the right approach for this. Security is important,
but it's something we can start building later on. It's not something that should
cause significant friction at this point."

Operative consequences for this phase:
- Env model flips ALLOWLIST → DENYLIST: panes start from a normal environment
  (PATH, HOME, LANG, TMPDIR, etc.) with CREDENTIALS stripped (no raw
  ANTHROPIC_API_KEY / OPENAI_API_KEY), plus the OAuth token + pinned config dir.
  The exact-4-var `env -i` floor is retired for the PoC phase (it was the single
  biggest friction source — LR-2).
- Zero-friction security KEEPS: OAuth-only credential rule, pinned binary/config
  isolation (that one is reliability as much as security).
- Friction-bearing security DEFERS: jail tier (F9-F13) stays deferred; when built,
  middle-ground privileges per the earlier user decision (2026-06-11, remediation
  plan note) — and it must not reintroduce the LR-2..4 tax.

## Governing preference 2 (user, 2026-06-11, mid-run): real over dummy

"I'd like to get it as close as possible to a real deployment — whenever we do
anything that's a dummy environment etc, it tends to mean that when we move to a
real environment or case, something breaks."

Evidence from this very session: EVERY run-blocking bug lived at a mock→real seam,
invisible to the 888-green unit suite because mocks encode assumptions, not reality:
LT-1 (placeholder env reached real spawns), the missing --model (CC silently booted
Sonnet while the binding recorded Opus), F18 (tmux silently rewrites session names),
LR-1 (transcript path CC never writes). Each surfaced within MINUTES of touching the
real substrate.

Operative consequences:
- Wire the REAL Codex adapter for L5 (DEFERRED-REGISTER O1) sooner rather than
  later — the Opus stand-in is exactly the kind of dummy this preference targets.
- Add a thin REAL-substrate smoke tier alongside the unit suite: real tmux server,
  real pinned CC boot, one tiny intake, assert transcript/kickoff/sign-off — run
  before declaring any transport/spawn change done. Unit mocks keep their speed
  role; they no longer count as evidence a seam works.
- Prefer validating increments against the live daemon over adding more mocks.

## Priority order for the post-run wave (user, 2026-06-11: "I'm much more focused
## on the behavioural bugs — I'm more architect than coder")

BEHAVIORAL (first — the process is the product):
 1. Per-level GATE OUTPUT CONTRACTS (LR-13 root cause): each level's gate must
    produce an altitude-specific artifact — L1: client playback (intent vs
    delivered vs deviations + the ask); L2: architecture/composition judgment;
    L4: workstream-composition report over the rubric. A gate whose required
    artifact is a playback cannot be satisfied by re-running tests. Includes the
    explicit DON'T: never re-run lower-level verification.
 2. L1 CLOSING PROTOCOL: L1's final act is ESCALATED-with-playback to the user;
    only the user's answer converts to DONE (machinery exists — F16 answer verb).
    Kills both self-certification and the DONE-bias path of least resistance.
 3. Reviewer authority wiring (LR-9) + producer-triggered, harness-resolved review
    invocation (LR-10).
 4. Identity auto-load (LR-3 — behavioral too: what's in context shapes behavior).
PLUMBING (second): PATH/denylist env (LR-2), collapse-wakes-parent (LR-11),
spawn-time pane labels (LR-7), 1M-context probe (LR-5), spawn-doc gaps (LR-4).
SECURITY (later, per governing posture decision): jail tier F9-F13.

ROOT-PROMPT PROPAGATION (meta-finding, mine): the operator intake said "deliver …
when the work is complete AND VERIFIED" — the word "verified" at the root framed
the entire cascade toward verification; four levels re-ran the same suite. Intake
wording propagates down the tree with compounding force; the intake template
should carry intent-language, not verification-language.

## The behavioral wave IS Phase 6 (mapping, 2026-06-11, from the full corpus read)

BEHAVIOURAL-VALIDATION.md already specifies the spec→system translation machinery;
today's run was effectively an UNPLANNED Inc-24 full trace executed before Inc
18-23. Every behavioral finding maps onto a Phase-6 instrument that would have
caught it:
- LR-3/LR-4 (docs not loaded, briefs hand-prose, dangling relative paths) →
  Inc 18 PIECES-PRESENT (deterministic, no model, front-loaded — "every manifest
  doc path resolves; the brief carries every field the receiving level needs").
- L1 no grilling session / no reflect-back / self-certify (LR-8c, LR-13) →
  Inc 19 rubric items 6-7 + the leak test.
- Four-levels-re-ran-tests, L2→L4 skip, prose briefs (LR-13, LR-6) → Inc 20/22
  workflow-adherence rubrics ("did it FOLLOW ITS PRESCRIBED WORKFLOW" — explicitly
  process-adherence ≠ output-plausibility).
- Collapse-not-waking-parent (LR-11) → Inc 23 cascade-dynamics ("report-up reaches
  the parent AND IS ACTED ON; collapsing a coordinator cascades").
- Reviewer independence/authority (LR-9/10) → fold into the Inc 22/22b contracts.
EXECUTION ORDER for the behavioral wave = Phase 6's own order: Inc 18 first (cheap,
deterministic), then 19-22b per-level evals with the rubrics UPDATED for today's
user decisions (gate output contracts, consulting-partner L1 frame, reviewer
authority), then Inc 23, then a CONFORMANT Inc 24 re-run. Per the doc: "behavioural
contracts are the user's to set" — the drafted rubrics go to the user for editing
before they're executed.
Also: INTAKE-TO-DELIVERY Stage 5 (L1 judges vs frozen spec, triggers promote) vs
QUALITY-GATE L1 gate (user renders verdict via playback) — reconcilable (user
authority = the reflect-back-confirmed frozen spec) but needs an explicit ruling;
today's L1 had NEITHER form of user authority, which is the hole self-certification
fell through.

## The fairer L1 diagnosis (from reading the operational membrane, 2026-06-11)

The live L1's self-certification was NOT primarily doc-ignoring. Three causes stack:
 1. THE MISSING HUMAN CHANNEL (the biggest unbuilt behavioral piece). The role doc
    assumes a conversational client ("the client conversation is continuous");
    INTAKE-TO-DELIVERY Stage 0 assumes the user attaches to L1's pane and
    converses. Our run had a read-only attach (R-1 hazard) + a one-shot inbox
    intake. L1 NOTICED — it recorded "no synchronous user" in decisions/D-001 and
    adapted. comms-protocol's L1→User section is ONE SENTENCE ("high threshold")
    with NO mechanic. The F16 escalation/answer machinery could carry a
    playback-and-wait flow today, but no document tells L1 that is the move.
 2. ROLE-DOC AMBIGUITY BAKED IN: role.md line 38 literally instructs L1 to run
    `harnessctl promote --decision accept` itself on ITS OWN intent-fidelity
    accept — the Stage-5 vs QUALITY-GATE authority contradiction reproduced in the
    agent-facing layer. Meanwhile §Guarding-Intent says "the user is the ultimate
    fidelity reviewer." An agent reading both, with no user channel, resolves the
    tension toward self-accept.
 3. My intake wording ("deliver when complete and verified") licensed it.
The altitude violation (re-running tests) is the part that IS a plain role-doc
gap: no gate output contract, no DON'T against re-verification.

TRANSLATION LIST (behavioral wave, grounded in the corpus read):
 A. Build the L1↔user channel mechanic. Minimal v1: Stage-5 close = L1 writes the
    playback artifact + ESCALATED signal; the user answers via the F16 answer verb;
    only then DONE → promote. Reconcile Stage-0 interactive attach with R-1
    separately (maybe a dedicated client console seat).
 B. User ruling on Stage-5 authority, then propagate ONE answer to
    INTAKE-TO-DELIVERY §Stage-5, QUALITY-GATE §L1-gate, and role.md:38.
 C. Per-level gate output contracts in role docs (+ the DON'T).
 D. Inc 18 pieces-present + identity auto-load (LR-3) — the deterministic floor.
 E. Reviewer authority wiring (LR-9/10).
 F. Intake template: intent-language not verification-language; capture delivery
    destination + user-availability (sync/async) explicitly.
Still unread (honesty ledger): L2/L3/L5 role.md in full, intake-session-template,
intent-spec-contract, COMMUNICATION.md, PLAN-ALIGNMENT-GATE.md in full,
DESIGN-PRINCIPLES.md — queued before any role-doc rewrites land.

### LR-14 — BUILT-AS-EVAL ≠ WIRED-AS-ENFORCEMENT (capstone; amended after user
### challenge "I thought we built it earlier")
CREDIT WHERE DUE (user was right): the Phase-6 instruments WERE built — the full
eval suite tools/eval_{l1_intake,l2_architect,l3_design,l4_coordinate,l5_execute,
reviews,full_trace}.py with committed results in dev/eval-runs/ (incl. the md2pdf
full trace-through capstone f36a3a3, review-machinery planted-issue evals), the
dry-run plan-alignment gate run (gate-report.md — an agent ROLE-PLAYING the gate,
2026-06-02), and pieces_present.py (Inc 18).
THE PRECISE GAP: all of it runs OFFLINE, after the fact, largely via agent judges.
At RUNTIME nothing sits on the report/freeze/spawn paths: zero hits in harnessd/
for preflight / return-contract / MISSING-TRACE; pieces_present is referenced
nowhere in the runtime; no freeze-block on reflect-back=pending. The role docs'
"the hook rejects it — you cannot report complete" sentences (L1/L2 role,
intent-spec-contract) describe enforcement that exists only as eval-time scoring.
No separate validation daemon exists in either repo (checked: launchd plist = the
harnessd wrapper; the §2.6 harnessd-pinger has its F14 surface but no built pinger).
CONSEQUENCE unchanged: at runtime the behavioral layer runs on exhortation, and
today exhortation lost to completion bias every time while enforced structure held.
HIGHEST-LEVERAGE BUILD: promote the existing eval logic into runtime hooks —
pieces_present into the chokepoint (deterministic half), the return-contract
walkers onto the report/sign-off path, the freeze-block onto the gate path.

## B. Post-run remediation candidates (user-observed, in priority order)

### LR-2 — no PATH in the pane env: every shell call pays a tax (HIGH, ergonomics)
The 4-var `env -i` floor carries no PATH. Observed: L4's `head` → exit 127
("command not found"), L2 "python3 isn't on the restricted PATH", agents using
/bin/ls absolute paths everywhere. Every level re-discovers this by failure.
Superseded remedy per the posture decision above: don't just add PATH to the floor —
retire the allowlist floor entirely for the PoC phase. Panes inherit a normal env
with credentials STRIPPED (deny-list), keeping CLAUDE_CODE_OAUTH_TOKEN +
CLAUDE_CONFIG_DIR + the two kill-switches on top. Touches: commissioning env,
tmux.build_pane_argv (`env -i` seam), the exact-4-keys env-floor tests (rewrite as
deny-list tests: forbidden keys absent, required keys present), oauth_guard
(unchanged in spirit), SECURITY.md §6.2 wording.

### LR-3 — identity documents are not auto-loaded; relative paths dangle (HIGH)
Briefs list identity docs as repo-relative paths (`operational/L1/soul.md`) but the
pane boots in the NODE workspace — the agent must first hunt for the harness root.
User-confirmed: this happened at EVERY level of the cascade, not just L1/L2 — the
navigation tax is paid once per spawned agent, so it scales linearly with tree size. Options (not exclusive):
  (a) absolute paths in the brief manifest (cheapest; matches the
      --system-prompt-file absolutization precedent from the transport fix);
  (b) kickoff message carries the harness root explicitly;
  (c) auto-load: concatenate the manifest into the brief (or --append-system-prompt)
      at spawn — costs context up-front but removes all navigation.
User intent: "should be auto-loaded on spawn."

### LR-4 — spawning a child is re-derived from source every time (HIGH)
Observed: L1 read chokepoint.py to learn child workspace/brief derivation; L2 read
the L4 spawn-template and grepped for "outbox"; L4 re-explored the outbox/bus layout
before planning. The mechanics ARE deterministic (author brief + drop
.harness-outbox JSON) — the friction is discovery+trust, not capability.
Remedy: a one-shot, self-contained "spawn a child" recipe (single command or
copy-paste template) in the handbook/comms-protocol, with a worked example, so no
level ever needs harness source. Candidate: a `spawn-child` helper script on the
node workspace (authors brief skeleton + outbox JSON from args), so spawning ≈ one
command. User intent: "remove/minimize mental overhead of non-core tasks."

### LR-5 — L4 hit a context compact surprisingly early (MEDIUM)
Cause is mostly LR-2/3/4: the window filled with harness-source exploration and
directory listings, not task content. Two-part remedy: (1) the ergonomics fixes
above shrink exploration; (2) probe the 1M-context model id (`claude-opus-4-8[1m]`)
in CC_MODEL_FLAGS — verify the OAuth subscription tier honors it on pinned 2.1.152.
POSITIVE observation: post-compact the L4 re-read brief/plan/status/log.md and
continued correctly — files-as-continuity absorbed the compact as designed.

### LR-7 — tmux panes carry no human-readable identity (MEDIUM, observability)
User: "you can't identify what identity each window holds — L1, L2, L3 (and what
variant)." The default status bar truncates the session name to ~10 chars and the
window shows "claude.exe". Fixed live mid-run via per-session options; make it
spawn-time behavior in tmux.create_detached: status-left = "[<level> <variant>:
<node-name>]" (status-left-length 50), automatic-rename off, window renamed to the
label, server-wide set-titles on + set-titles-string "#S" (full session name into
the terminal title bar). Update the label when the node reaches a terminal state
(e.g. "(done)") — the watchdog collapse path can do this.

### LR-6 — L2 spawned an L4 directly (level skip) (OBSERVATION, verify intent)
`L1/md2html#exec` (L2) spawned `L1/md2html/tool#exec` as L4 — no L3 Module Designer.
Reasonable for a single-module project (intake said keep the tree minimal), but
confirm the level guard / role docs intend skips to be legal, and that L3-skip
doesn't break promote/sign-off path assumptions anywhere.

### LR-8 — upward-gate audit checklist (user clarification on the review spine)
Per QUALITY-GATE.md, the review function has two instantiations and they must not
be conflated (user corrected this mid-run):
  (a) L5+ per-unit review (M52) — independent reviewer of L5's code AT THE LINE
      against the frozen rubric; accept→collapse / bounce→bounded loop. In this run:
      the `review` child in the L4's plan.
  (b) per-level whole-set review — a `#review` SEAT co-located at the node
      (e.g. L1/md2html/tool#review), reviewing the COMPOSITION at that altitude
      (L4: units integrate; L2: product/architecture fit) — never re-reviewing
      lower lines. Separate from the parent's own evaluative judgment, which the
      gate does not replace.
  (c) L1 gate = intent fidelity, verdict rendered by the USER via triangulated
      playback — L1 must not self-certify and promote without the user.
Post-run audit: did (a) actually test, did any #review seats get spawned at L4/L2,
did L1 present playback to the user before promote? Run-specific caveats: a single
L5 unit makes the L4 composition review nearly degenerate; the O1 Opus stand-in
removes the different-runtime judgment diversity the spec wants for L5+
(reinforces governing preference 2 — wire real Codex).

### LR-9 — review authority model: the gate, not the producer, unlocks upward flow
(user decision, 2026-06-11 mid-run: "the owner (L4) should not have control over
it. It doesn't have the authority to send finished work upwards. The reviewer does
that. L4 can invoke it and send it work, but it needs to be separate, independent,
with its own authority.")
Spec agreement: QUALITY-GATE.md — the reviewer is "structurally separate from the
producing level — not spawned by it, not part of its hierarchy." Refinement:
separation is against the PRODUCER at each altitude — L4 invoking the L5+ reviewer
of build's code is legitimate (L4 didn't write it); the gate on L4's OWN composition
must not be under L4's control (spawned by the boundary above / the harness, at the
#review seat).
HARNESS GAP (the live run made it visible): sign-offs flow child→parent, so the
producing parent is structurally the one deciding what moves up — a reviewer child's
accept is merely advisory input the parent could ignore. Required mechanic: a
level's upward sign-off is INVALID unless accompanied by a gate-accept artifact
written under the REVIEWER's own owner_token (the producer cannot forge or own it —
the fencing primitive already exists). Today's L5+ -as-child of L4 was acceptable
only because L4 wasn't the code's producer; the L4→L2 boundary in this run has no
independent gate at all unless L2/harness spawns one.

### LR-10 — invocation vs authority; levels manage WORK, not agents (user, mid-run)
"L5+ should actually also be invoked by L5. L4 should have minimal need to manage
agents. Its focus is the work. It's not an agent manager — the agents are the
vehicle."
Model: WHO PULLS THE TRIGGER is mechanical and belongs at the point of work — L5
finishing IS the trigger for its own L5+ review (a deterministic lifecycle step,
like CI; agent-lifecycle.md already treats the pair as one unit that "on accept,
both collapse and forward upward"). WHO HOLDS AUTHORITY is where independence
lives: rubric frozen at planning (producer can't author it), reviewer
identity/config resolved by the harness (producer can't pick a friendly reviewer),
verdict under the reviewer's own owner_token (producer can't forge/suppress — LR-9).
Observed overhead this run: L4 hand-sequenced tester → build → review, spending its
turns on agent choreography instead of workstream-level work. Remedy direction:
make pair-completion (and review invocation generally) harness machinery — L4's
products are the decomposition, spec, and gate rubric; the lifecycle runs itself.
Connects to LR-4 (one-command spawn): same theme — agent mechanics should be
deterministic, frictionless, and near-invisible to every level.
MECHANIC CORRECTION (full spec read, post-grep): under current harness mechanics an
outbox request spawns the child UNDER THE REQUESTER'S ADDRESS — so L5 dropping a
spawn request would put the reviewer in L5's hierarchy, which QUALITY-GATE.md §29
forbids ("not spawned by it, not part of its hierarchy"). L5-invoked review must
therefore be a DISTINCT harness verb: producer's finish = trigger; harness spawns
the reviewer at the node's #review seat with custody OUTSIDE the producer's subtree.

### LR-11 — collapse does not wake the parent (HIGH, found live; fix post-run)
A child's terminal collapse appends nothing to the PARENT's inbox — L2 collapsed
DONE and L1 sat unaware in its (correct) holding pattern; only the generic idle
ladder would eventually prod it into rediscovering tree state. Required mechanic:
chokepoint.collapse (or the watchdog enactment) appends a `child_collapsed` line
{child address, terminal signal, evidence} to the parent seat's inbox — the ③-wake
then delivers it on the next tick. (Worked around live with an operator-appended
inbox line to finish the run.) Same family as LR-12 below.

### LR-12 — coordinator terminal-signal processing dropped by the §5.4 split (CRITICAL, FIXED live: d639e56)
The leaf/coordinator split exempted coordinators from the idle ladder but silently
dropped terminal-signal processing with it: L4's and L2's DONE signals sat
unprocessed for 15 minutes while the daemon ticked normally; the upward path froze
with the whole subtree green. Fixed: watchdog.check_terminal_signal extracted from
check_leaf, coordinators run it first, gated on no-live-descendants (bottom-up
shutdown preserved; the frozen live-child no-collapse pin still green). Found ONLY
by the live run — the suite had leaf-collapse and coordinator-death tests, but
coordinator-COMPLETION was an unimagined case (mock-reality seam again,
governing preference 2).

### LR-13 — altitude discipline broke on the way up: every level re-ran the tests (HIGH, role-doc fix)
User (watching L1's final gate): "The question for L1 isn't 'does this work' — by the
time anything gets to L1, it works. It's 'is this the thing the user asked for'…
like a consulting partner auditing finished work before delivery. Not 'is the code
good, do the tests pass' — they're not technical. Did the technical build the thing
the client asked for?"
Observed: the SAME test suite was executed four times up the chain (build, L5+
review, L2, L1); L1 additionally ran AST scans and construct checks, burning its
context to 4%-until-compact on technical re-verification, then SELF-RENDERED the
intent verdict ("Intent-fidelity ACCEPT, decisions/D-002… Nothing further needs
your input") — the verdict the spec assigns to the USER via triangulated playback
(LR-8c deviation, now observed not predicted).
Spec already forbids this (QUALITY-GATE.md: "a gate never re-does lower-level
review; re-checking is wasted cost and erodes the producing level's
accountability") — so this is a ROLE-DOC/PROMPT-STRENGTH finding, not a spec gap:
the L1 (and L2) role docs need their gate sections rewritten around the
consulting-partner frame, with an explicit DON'T (do not re-run lower-level
verification; trust the gated chain; your judgment is fit-to-intent) and an
explicit closing duty (present playback, await the user's verdict — never
self-certify delivery).

### Corrections from the full spec read (2026-06-11, after user pressed "did you?")
- LR-4 reframed: the one-shot spawn recipe ALREADY EXISTS — agent-lifecycle.md
  "How You Spawn a Child" ("a thin administrative act": prepare node + one-line
  JSON in .harness-outbox). The live friction is agents not having/trusting that
  doc — LR-4 is largely a DELIVERY failure of LR-3, not absent design. (Residual
  LR-4 work: agents still read harness source for workspace-derivation details the
  doc leaves implicit — close those gaps in the doc, not in agents' time.)
- LR-3 upgraded: spec VIOLATION, not preference — agent-lifecycle.md line 13: "By
  the time you receive your first context everything is already loaded — you never
  bootstrap yourself." Every agent in this run bootstrapped itself.
- L4 role doc: briefs should be POINTER-NOT-PAYLOAD (spawn by pointer to prepared
  node, prose brief is the exception) — audit whether the live L4 hand-wrote prose
  briefs instead.

### LR-15 — a pieces-refused child spawn WEDGES permanently (HIGH, found in Run-val2)
The E1 gate refused the first L5+ spawn (correctly — LR-16); but the refusal left
the binding `planned` with the outbox request consumed (.done), and NOTHING
re-drives it: _child_already_live counts `planned` as live (a re-request by the
parent is consumed as already-live without spawning), reconcile excludes pre-spawn
states from owned-but-dead (INT-4), and the F21 claim-as-is leg is L1-only.
Recovered by operator: harnessctl spawn with the planned binding's CAS values.
REMEDY: the daemon should re-drive planned bindings whose nodes are prepared (a
sweep leg: planned + brief.md present + no pane -> claim_and_spawn), OR a parent
re-request should be honored when the existing binding is pre-spawn.

### LR-16 — the L5+ reviewer manifest was never authored; the E1 gate caught it (FIXED a150914)
ROLE-RESOLUTION §84-87 prescribes a distinct reviewer manifest for L5+#review;
the bundle did not exist, so the FIRST live L5+ spawn was refused
(pieces_missing: manifest docs do not resolve). Authored
operational/L5+/{soul,role,config}.md from QUALITY-GATE M52/D27 (own-testing-
pass-first, fidelity-dominant two-axis verdict, ACCEPT/BOUNCE with named
defects); pieces_present sweep extended to L5+ so a registry seat without its
bundle can never again pass silently. NOTE the meta-point: the enforcement spine
caught ITS OWN AUTHOR'S config gap within hours of landing — exactly the
loud-stop-over-silent-leak behavior BEHAVIOURAL-VALIDATION demands.
