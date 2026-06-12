# Session log — 2026-06-11 → early 2026-06-12 (48 commits, 966756b..a274de8)

One session: the first supervised live run, the behavioral-adherence wave it
triggered, the enforcement spine, Codex at L5, and two more live runs. Suite
888 → 910 green. All commits local, no push.

## 1. First supervised live run (md2html, runtime/build-local) — morning/afternoon
- Full L1→L2→L4→L5 cascade completed; working md2html delivered in-place; user
  watched via labeled read-only tmux windows.
- TWO fatal harness bugs found+fixed mid-run:
  - `27cea6f` LR-1: adapter invented a session uuid CC never saw + derived the
    transcript dir from the session name → watchdog blind → idle ladder killed a
    healthy L1. Fix: `--session-id` pins the uuid; encoded-realpath-cwd path.
  - `d639e56` LR-12: the §5.4 leaf/coordinator split dropped terminal-signal
    processing for coordinators → L4/L2 DONEs ignored, upward path frozen. Fix:
    `watchdog.check_terminal_signal` shared, gated on no-live-descendants.
- 14 findings recorded (LIVE-RUN-2026-06-11-FINDINGS.md, LR-1..14) + 2 governing
  user preferences (PoC security = denylist not allowlist; real over dummy) +
  user decisions: reviewer authority (LR-9: gate-accept under the reviewer's own
  token unlocks upward flow), invocation-vs-authority (LR-10), altitude rule
  (LR-13: L1 = consulting-partner intent audit, never test re-runs).
- LR-14 capstone (after the user pressed "did you read it?"): the Phase-6 eval
  suite existed but NOTHING enforced at runtime — built-as-eval ≠ wired-as-
  enforcement. → the enforcement-spine increment.

## 2. The enforcement spine (E1–E3) — afternoon/evening
- `92c172e` **E1 pieces-present gate** at chokepoint STEP2.5: an under-equipped
  actor never opens; spec/acceptance pointers DERIVED from the prepared node
  (brief.md/acceptance.md). ~15 test files' fixtures completed.
- `440d278` **E2 return-contract walker** on the sign-off path: DONE without
  report.md / required ID citations / parseable trace stanzas is REFUSED before
  collapse; one edge-triggered typed-defect WAL row + an inbox defect notice;
  agent fixes and re-signals. FAILED/ESCALATED exempt (never trap).
- `587551b` **E3 promote-edge intake gate**: FREEZE-ON-PENDING blocks accept on
  unconfirmed reflect-back rows; §8 delivery destination derived from the
  intent-spec; explicit `in-place` honored without a cross-jail copy.

## 3. E4 — Codex at L5 (`64a29f6`, O1 retired)
- Live-probed everything first: CODEX_HOME redirect + portable auth.json,
  `-m gpt-5.5` accepted AND recorded as fact in the rollout, rollout =
  sessions/Y/M/D/rollout-<ts>-<uuid>.jsonl (header carries cwd), first-boot
  trust = realpath-keyed config.toml entry, TUI idle marker `›`.
- `.codex-pinned/` (npm @openai/codex@0.128.0 + isolated config home).
- CodexAdapter: NO system-prompt injection (user decision — codex's native
  instructions stay; precision rides the brief/kickoff); BOOT_PROMPT argv starts
  the first turn (the TUI creates its rollout lazily); post-boot rollout
  DISCOVERY (header-payload cwd match) → real uuid + transcript path; codex-own
  env floor (CLAUDE_* stripped — no cross-runtime token leak); containment
  refused loudly (v1 jail is CC-only).
- Chokepoint ADAPTER REGISTRY keyed by level_config.runtime; injected set_adapter
  stays the test override (registry-wins poisoned 83 tests before the precedence
  inversion); commissioning ships adapter=None.
- `L5+` became a first-class LevelConfig (opus/claude-code — judgment diversity);
  outbox accepts L5+; per-runtime prompt markers (`❯`/`›`) at the kickoff gate +
  prod_precondition.
- Real-substrate smoke: a real codex L5 spawned through the real chokepoint read
  its brief and did the work (SMOKE-OK).

## 4. User goal block (~21:00–00:30): behavioral adherence, spec is king
- `1c7a9cd` **LR-11/LR-2/LR-3**: collapse appends `child_collapsed` to the
  parent's inbox; PATH joins the pane env floor (allowlist→denylist posture);
  authored briefs render ABSOLUTE manifest paths.
- `e4cb118` Stage-5 authority ruling recorded at both design sites (user: test
  phase = operator evaluates vs frozen spec; user-verdict mechanic = future) +
  DAEMON §6.2 LR-2 amendment.
- `769fc07` RUN-ADHERENCE-AUDIT-2026-06-11.md — the rubric-derived scoring
  instrument (rows A1–D8, later B6–B10/C6 from the PROJECT-PLANNING read).

## 5. Run-1: wordcount validation (runtime/build-val2) — COMPLETE + PROMOTED
- Stage 1–2 textbook (client-brief trio, §8 in-place, async reflect-back recorded).
- `a150914` **LR-16**: the E1 gate REFUSED the first-ever L5+ spawn — the
  reviewer bundle ROLE-RESOLUTION §84-87 prescribes was never authored. Authored
  operational/L5+/{soul,role,config}.md from QUALITY-GATE M52/D27; pieces sweep
  extended to L5+. The spine caught its own author's gap.
- `c849340` **LR-15**: the refusal exposed the planned-spawn wedge → re-drive
  sweep in poll_once (planned + prepared node + no pane → claim_and_spawn, 60s
  cooldown). (+ a daemon `addressing` import the swallow was hiding.)
- **D2, the headline**: E2 refused the tester's DONE (DUP-ID); the agent read its
  inbox defect, renumbered ITS OWN ids (didn't touch the parent's brief),
  re-signaled, collapsed clean. Later ALSO at the ROOT: E2 refused L1's DONE
  (MISSING-REPORT); L1 recovered from its own auto-compact, wrote the delivery
  report, re-signaled. The hook loop verified at both ends of the tree.
- First in-cascade codex L5: full lifecycle clean, E2 passed first try.
- M52 cross-runtime pair: Codex executor → Opus reviewer → VERDICT ACCEPT.
- Promote: `delivered`/`in-place` DERIVED from intent-spec §8 by the E3 gate.
- Scores in RUN-ADHERENCE-AUDIT (D-rows green; A6 PARTIAL → the contracts).

## 6. Between runs
- `f53366f` **Gate output contracts LANDED** in L1/L2/L4 role docs: required gate
  artifacts (fidelity-judgment.md / composition-review.md / composition-report.md)
  + never-re-run-lower-verification + recorded-scale-down rule + L1's node
  report.md = the delivery report. (Splice script: design/working-notes/
  splice_gate_contracts.py, idempotent.)
- PROJECT-PLANNING Phases 3–7 read: the L3-SPLIT collapse is sanctioned for
  trivial areas; ZERO-L3 is NOT → the small-project profile is a SPEC EXTENSION
  awaiting user blessing.

## 7. Run-2: sitegen complex run (runtime/build-site1) — IN FLIGHT overnight
- Forces the L3 layer + 2 workstreams. Launched on the amended role docs.
- `1c92456` **LR-17**: the ladder killed L1 for DISPATCHING ITS GRILLING SESSION
  (a Task subagent leaves the main transcript flat → false-idle). Fix: verdict
  step 5b — flat-beyond-W + pane showing the mid-turn marker ('esc to
  interrupt', single-sourced as PANE_WORKING_MARKER) → working.
- `a274de8` **LR-18**: collapse never reaps panes → deterministic session names
  collide on respawn (hit twice: failed-L1 vs genesis; collapsed planning-L3 vs
  its execution-L3 respawn — the C21 split). Fix: kill_stale_pane (adapter-
  threaded for the registry) runs on the fresh spawn leg, post-claim.
- Adherence so far: Phase-3 concept validation via a REAL ESCALATED slot-hold
  (first ever), answered on the agent channel (inbox review-verdict — Inc-23
  round-trip PASS); TWO parallel planning-L3s (the layer's first run); both
  E2-bounced on MISSING-REPORT and SELF-HEALED (cycles 4+5); compatibility
  review PASS (first ever), seam validated by both L3s, scope calls SURFACED not
  silently decided; L2 SELF-CHECKED its trace-blocks against the walker's rules
  before signing (anticipatory compliance).
- At log time: markdown execution-L3 `planned`, awaiting the LR-15 re-drive with
  the LR-18 teardown — the two recovery mechanisms' first joint case.

## State at session end
- Suite: **910 passed, 1 skipped**. 48 local commits (this repo) + changelog
  commits in Life-os. Nothing pushed.
- Daemons: build-site1 daemon RUNNING (Run-2 in flight; monitor task armed in
  the old session — re-arm after compact). build-local + build-val2 daemons
  stopped; their trees preserved (audit window).
- Live tmux (socket `harnessd`): Run-2 sessions only.

## Next session (in order)
1. Re-arm a Run-2 monitor; check tree + WAL defect rows; verify the markdown
   execution-L3 respawned via re-drive+teardown.
2. Score Run-2 (audit rows incl. B6–B10/C6; B9: inspect
   sitegen/L2/decisions/interfaces-locked.md for candidate-vs-frozen vocabulary).
3. On L1's close: operator Stage-5 evaluation → promote (E3 derives in-place).
4. Splice the report.md duty into L3's role doc (L5 already has it; L1/L2/L4
   landed); consider the lingering-ESCALATED-stamp cosmetic (SM-4 family).
5. User decisions pending: bless the zero-L3 small-project profile (spec
   extension); the L1 closing protocol (playback-to-user) when real-client use
   approaches.
6. Follow-ups: async codex rollout discovery (sweep stalls ≤150s per codex
   spawn); cross-runtime L5/L5+ eval re-run; codex-audit of briefs; pane labels
   at spawn (LR-7); DEFERRED-REGISTER sync.
