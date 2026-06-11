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

## B. Post-run remediation candidates (user-observed, in priority order)

### LR-2 — no PATH in the pane env: every shell call pays a tax (HIGH, ergonomics)
The 4-var `env -i` floor carries no PATH. Observed: L4's `head` → exit 127
("command not found"), L2 "python3 isn't on the restricted PATH", agents using
/bin/ls absolute paths everywhere. Every level re-discovers this by failure.
The 4-var floor is a CREDENTIAL invariant (OAuth-only) — a sane PATH
(/usr/bin:/bin:/usr/sbin:/sbin + python3's dir, or the user's homebrew prefix)
does not weaken it. Touches: commissioning env, the env-floor exact-4-keys tests,
oauth_guard (no change expected), SECURITY.md §6.2 wording.

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

### LR-6 — L2 spawned an L4 directly (level skip) (OBSERVATION, verify intent)
`L1/md2html#exec` (L2) spawned `L1/md2html/tool#exec` as L4 — no L3 Module Designer.
Reasonable for a single-module project (intake said keep the tree minimal), but
confirm the level guard / role docs intend skips to be legal, and that L3-skip
doesn't break promote/sign-off path assumptions anywhere.
