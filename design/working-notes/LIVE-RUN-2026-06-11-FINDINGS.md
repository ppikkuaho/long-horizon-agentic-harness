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
