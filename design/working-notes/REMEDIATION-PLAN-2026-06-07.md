# Remediation Plan — 2026-06-07

Inventory + impact + prioritization for the 103 confirmed findings in `SPEC-REVIEW-2026-06-07.md`.
The 103 findings dedup to **27 distinct fixes** (same-root findings counted once). Each carries: the
impact (what breaks if unfixed / what fixing enables), the fix shape, dependencies, and a NOW/LATER call.

**Tiering principle.** NOW = required for *the first supervised end-to-end live run* (the v1 walking
skeleton actually pouring a real feature through L1→L5 and delivering). LATER = real, but safe to defer
behind a stated trigger without blocking that first run. Everything important gets fixed; this is
sequencing, not dropping.

**Keystone ordering.** F1 (daemon assembly) is first and non-negotiable: until the daemon runs+serves+
ticks, *no other fix can be observed or exercised live*, and the loop-test that guards every later fix
can't exist. After F1, the order is correctness-foundations → cascade edges → delivery → hardening.

---

## TIER 0 — KEYSTONE (nothing runs without it)

### F1 — Assemble the resident daemon (process + IPC + watchdog tick + loop-test) — ✅ DONE 2026-06-07
> **Status: COMPLETE** (FORK-DAEMON-ASSEMBLY). `daemon.run` + `__main__` + `make_ipc_listener` + the
> `_watchdog_tick` in `poll_once` (leaf/coordinator split) + the loop-level test. 655 green;
> 4 wirings mutation-verified. Honest v1 limitations recorded in the fork: coordinator
> collapse-on-quiescence + prod/send-keys delivery + coordinator-death ESCALATE routing remain deferred.
- **Findings:** daemon-4, ipc-1, NSL-01, CRIT-1, URP-01, URP-02, CRIT-2, LOW-6 (8 findings, 4 CRITICAL).
- **Impact if unfixed:** the daemon does not run at all (`python3 -m harnessd.daemon` executes nothing),
  the CLI→daemon socket is dead, and the autonomous spine never ticks — no node auto-collapses on
  sign-off, no idle leaf fails-loud, no coordinator-death recovery, no wake nudge. The entire system is
  inert in production. **This is the whole ballgame.**
- **Impact of fixing:** the system becomes a live, self-supervising process; every other fix becomes
  observable and testable; DONE_WHEN clause 3 (spawned→detected→signed-off→collapsed) becomes reachable.
- **Fix shape:** (a) `harnessd/__main__.py` (or `daemon.py` `__main__`) → `boot(runtime)` then
  `poll_loop(interval)`; (b) bind the AF_UNIX listener at `<RUNTIME_ROOT>/.harnessd/harnessd.sock` and
  serve it (a thread alongside poll_loop, or a select-loop inside it) with exception-safe `serve_one`;
  (c) `poll_once` calls the watchdog per live non-terminal node: terminal-signal-FIRST collapse
  (`read_terminal_signal` → `chokepoint.collapse`), the idle→prod→FAILED leaf ladder with parent
  escalation, the coordinator-death branch, the ③-wake nudge — exactly the verdict+policy WATCHDOG.md
  L214 / IMPL-PLAN §3 specify; (d) a **loop-level test** that drives `poll_once` against a node carrying
  a fresh `.signal.json` and asserts autonomous collapse (this closes the system-level test-masking).
- **Depends on:** nothing. **Blocks:** everything.
- **Effort:** large (the keystone increment). **Call: NOW.**

---

## TIER 1 — CORRECTNESS FOUNDATIONS (silent corruption once live; fix before a real run)

### F2 — Route every executor/spawn Result (result-swallowing, cluster ①)
- **Findings:** chokepoint-2 (root), watchdog-2, genesis-1, ipc-2 (downgraded), harnessctl-1/-2.
- **Impact if unfixed:** a *failed* CAS/fenced/illegal transition is reported as success. `collapse()`
  returns None regardless; the watchdog trusts it; first-boot L1 spawn failure is swallowed (clean boot,
  no actor, no escalation). This is a direct *no-silent-leak* violation — the system believes work
  happened that didn't. Corrupts recovery + escalation invisibly.
- **Impact of fixing:** every mutation's real outcome propagates; a fenced/failed transition surfaces as
  an escalation or a visible error, never a phantom success.
- **Fix shape:** `collapse()` inspects the `TransitionResult` and propagates failure; `run_genesis`
  checks `claim_and_spawn`'s `ok`/`failure_class` and escalates a failed L1 boot; watchdog actions route
  the outcome; `_handle_kill` reports the specific abort reason; CLI guards the file/JSON.
- **Depends on:** F1 (to observe). **Effort:** medium. **Call: NOW.**

### F3 — Exception taxonomy: set + route `failure_class` (cluster ②)
- **Findings:** oauth_guard-1, oauth_guard-2, claude_code-2, claude_code-3.
- **Impact if unfixed:** `SpawnFailure`/`AuthExpired`/`ApiKeyForbidden` carry no `failure_class`, so the
  chokepoint's `getattr(exc,'failure_class',None) or 'model_unavailable'` escalates an **auth-token lapse
  as a model outage** (the exact storm DAEMON §6.3 forbids — the user gets "model down, wait" when the
  real action is "refresh your token"), and `ApiKeyForbidden` leaks uncaught. Latent until a real spawn
  hits an expired token — which, given the stale-token situation, is *imminent* on the first real run.
- **Impact of fixing:** an auth lapse reads as "refresh the token" and terminates at L1→user; a leaked
  API key reads as the hard-invariant breach it is; a model outage stays a model outage.
- **Fix shape:** give each exception class a `failure_class` attr (`auth_expired`/`model_unavailable`/
  `override_rejected`/`runtime_down`/`api_key_forbidden`); the chokepoint catch routes by it + catches
  `ApiKeyForbidden`.
- **Depends on:** F1. **Effort:** small. **Call: NOW.**

### F4 — WAL replay applies `to_state`, not `binding_delta` (durability)
- **Findings:** executor-1, WAL-01 (same family).
- **Impact if unfixed:** a committed transition whose caller delta omits `state` (state is set
  authoritatively in `transition`, not via the delta) **replays to the un-advanced state after a crash**
  — recovery silently rolls a node backward. The single most serious durability defect; the kind of
  recovery-corruption Lesson 8 is about.
- **Impact of fixing:** crash recovery reconstructs the exact committed state; exactly-once holds.
- **Fix shape:** `_apply_one` (reconcile) applies the record's authoritative `to_state` (and identity
  fields) over the delta — mirror `executor.transition`'s authoritative-state rule on the replay side.
  Add a real kill-9 recovery test for a state-advancing transition with an empty-state delta.
- **Depends on:** F1 (for the full recovery test). **Effort:** medium. **Call: NOW.**

### F5 — Leaf-necro → state `failed` per §3.6 vocab (state-machine correctness)
- **Findings:** reconcile-1, SML-01, SML-02.
- **Impact if unfixed:** leaf-necro stamps `(DIED_INFRA, state=dead)` but §3.6 maps `DIED_INFRA→failed`;
  a vocab-illegal binding pair → recovery policy (② recover-vs-reap) reads the wrong class → wrong
  recovery decision. Plus `signal_ESCALATED` is never journaled and the §3.6 event names drift.
- **Impact of fixing:** the terminal vocabulary is internally consistent; recovery classifies deaths
  correctly; the audit trail uses the normative event names.
- **Fix shape:** `_terminal_necro` maps DIED_INFRA→failed (leaf) while coordinator_died keeps its rule;
  journal `signal_ESCALATED`; align event names to §3.6.
- **Depends on:** F1. **Effort:** small-medium. **Call: NOW.**

### F6 — reconcile replay lock scope + single-instance lock design
- **Findings:** reconcile-2, SWCAS-01, SWCAS-02.
- **Impact if unfixed:** `reconcile.replay_wal` writes the ledger with `_lock_held=True` while genesis has
  *released* the lock → the guard is false-by-fact (it's flag-only). And the §2.3 single-instance lock is
  dropped after genesis (same file as the per-mutation EX lock; holding both deadlocks). Latent under the
  single-central-daemon topology + launchd KeepAlive, but the documented single-writer invariant is
  literally broken on the recovery write path, and a manually-launched second daemon could race.
- **Impact of fixing:** the single-writer invariant holds by-fact, not by-flag; a second daemon can't
  race the recovery write.
- **Fix shape:** either (a) reconcile takes the EX lock itself for its checkpoint write (and genesis
  doesn't hold it across the call — needs a reentrancy-safe scheme), or (b) a SEPARATE persistent
  single-instance lock file distinct from the per-mutation EX lock (resolves the §2.3-vs-§4.3 conflict).
  This is a small DESIGN decision (a fork) before the code.
- **Depends on:** F1. **Effort:** medium (carries a design fork). **Call: NOW** (decide the fork first).

---

## TIER 2 — CASCADE EDGES + DELIVERY (needed for an actual end-to-end run)

### F7 — L1 root gets a `workspace` field (cascade edge 1)
- **Findings:** CFW-01 (CRITICAL), CFW-03 (test-mask).
- **Impact if unfixed:** the L1 root's outbox is never serviced → **L1 can never spawn L2** → the cascade
  is dead at its first edge. The whole point of the system (a build flowing L1→L5) cannot start.
- **Impact of fixing:** L1 can spawn L2; the cascade can begin.
- **Fix shape:** `_register_l1_root` sets `workspace = addressing.node_dir(l1_address, runtime_root)`
  (mirror `_register_child`); de-mask the outbox tests (stop hand-seeding workspace; let genesis set it).
- **Depends on:** F1. **Effort:** tiny (one line + test fix). **Call: NOW.**

### F8 — promote() path + caller (delivery terminus)
- **Findings:** JSF-03, CRIT-3.
- **Impact if unfixed:** `promote()` sources `/runtime/proj/{project}/` but agents write
  `/runtime/nodes/<path>/` → it reads a path no agent writes to; AND it has no caller (no L1
  final-accept / IPC path invokes it). The finished product never leaves `/runtime/` — the delivery
  terminus is unreachable.
- **Impact of fixing:** L1's final-accept promotes the product out to its destination — the run actually
  delivers.
- **Fix shape:** reconcile promote's source path with `addressing.node_dir` (the project root under
  `nodes/`); add the caller (an IPC `promote`/`accept` verb invoked on L1 final-accept).
- **Depends on:** F1, F7 (a cascade must run before there's anything to deliver). **Effort:** medium.
  **Call: NOW** (last in the NOW sequence — it's the run's final step).

---

## TIER 3 — JAIL HARDENING (all LATENT today; NOW *iff* the first run is jailed)

> **DECISION REQUIRED:** these are all latent because no production caller requests containment yet
> (containment-request wiring is itself a deferred D-row). If the first live run turns the jail ON (the
> SECURITY.md v1 floor), F9–F13 become NOW. If the first run is an unjailed smoke-test, they're LATER
> behind the "enable containment" trigger.

### F9 — resume/necro re-applies the write-jail
- **Finding:** chokepoint-1. **Impact:** a contained node re-opens UNJAILED on every recovery (the
  recovery-weakens-security hazard); SECURITY §8.1 requires the same jail on resume/necro. **Fix:** route
  resume/necro through STEP2a containment production. **Effort:** medium.

### F10 — tmux idempotency guard handles the sandbox-exec vector
- **Finding:** tmux-1. **Impact:** a jailed pane vector (`["sandbox-exec",...]`) is re-wrapped, putting
  `env -i` outside `sandbox-exec` → wrong §7.1 launch form, clobbered cache-env. **Fix:** the guard
  detects the sandbox-exec head too. **Effort:** small.

### F11 — jailed env sets `CLAUDE_CODE_TMPDIR` / `HOME`
- **Finding:** claude_code-1. **Impact:** CC scratch writes land outside the seatbelt write-allow (jail
  breaks CC, or CC writes escape intent). **Fix:** `_produce_containment` sets TMPDIR→WORKROOT + HOME.
  **Effort:** small.

### F12 — fail-closed on empty/malformed WORKROOT
- **Finding:** JSF-02. **Impact:** a bad WORKROOT silently degrades the jail to the daemon CWD while
  still skip-perms — a fail-OPEN. **Fix:** refuse to spawn jailed if WORKROOT doesn't resolve under the
  runtime root. **Effort:** small.

### F13 — cross-project read-jail scope (NEEDS ADJUDICATION)
- **Finding:** JSF-01 (CRITICAL, but scope-dependent). **Impact:** read-deny covers only `/runtime/`;
  with `(allow default)` a jailed agent can read the user's OTHER files on disk. **OPEN QUESTION:** is
  this an intended v1 "write-jail + secret-read-deny, not a full read-jail" limitation (then LATER, a
  documented scope), or a real exfil hole (then NOW)? **Action:** read SECURITY.md to settle the intended
  v1 read-confinement scope BEFORE deciding. **Effort:** small fix; adjudication first.

---

## TIER 4 — OPERABILITY + OBSERVABILITY (needed for a SUPERVISED run)

### F14 — `runtime.json.last_tick_at` per tick
- **Findings:** daemon-1, COMP-5. **Impact:** the §2.6 hang-detector (a wedged-but-alive daemon holding
  the lock) has no surface to key on — a deadlocked daemon is undetectable. **Fix:** stamp last_tick_at
  every poll_once. **Effort:** tiny. **Call: NOW** (cheap, real safety surface; rides F1).

### F15 — harnessctl fleet/tree TEXT VIEW
- **Finding:** COMP-4. **Impact:** the operator's ONLY situational-awareness surface — without it you
  can't see the live tree during a run (only single-node machine reads). **Fix:** a `tree`/`status`
  subcommand rendering the binding map. **Effort:** medium. **Call: NOW** (you need it to watch the run).

### F16 — human-control WRITE verbs (pause / resume / answer)
- **Finding:** COMP-3. **Impact:** only the read-side `paused_at` exists; you cannot actually pause,
  resume, or answer an escalation from the CLI — no human-in-the-loop control during a run. **Fix:** IPC
  + harnessctl verbs routing through the executor. **Effort:** medium. **Call: NOW** (you wanted real
  HITL control; without it a live run is unsteerable).

### F17 — E32 `model_used == configured` trace-checker
- **Finding:** OBS-1. **Impact:** a silent model-fallback could reach a node with no escalation in the
  trace (a build runs on the wrong model unnoticed). **Fix:** a checker over the ledger/WAL. **Effort:**
  small. **Call: LATER** (matters once multi-runtime/Codex is live — pairs with the Codex adapter, O1).

### F18 — tmux_target vs live session-key consistency
- **Finding:** OSA-01. **Impact:** `binding.tmux_target` (raw) may never match the live tmux session key
  (collapsed) → reconcile's pane lookup fails → a live node looks dead. **NEEDS A CHECK** of how tmux
  sessions are actually keyed (this may be partly addressed by the addressing work). **Effort:** small;
  verify first. **Call: NOW** (it would break liveness detection on the first real run).

### F19 — signal artifact schema agreement
- **Finding:** detector_signals-1. **Impact:** the agent-writer (role docs) and daemon-reader must agree
  on `.signal` schema; currently code uses `{signal,ts,owner_token}` vs spec `{tag,at,session_uuid}`.
  Stricter, not broken, but a drift that bites when the real agent writes the file. **Fix:** align the
  code schema to the spec (or update the spec + the agent role-doc instruction to match the code).
  **Effort:** small. **Call: NOW** (the real agent must write what the daemon reads).

---

## TIER 5 — COMPLETENESS + MY-RECENT-CODE (deferrable or quick)

### F20 — outbox fan-out / idempotent ordering (my recent code)
- **Findings:** outbox-1, outbox-2, outbox-3. **Impact:** an already-live child gets a misleading
  `.rejected` at cap + is double-counted against the in-sweep cap; a None parent level loosens the
  descent guard. Minor. **Fix:** move the already-live check above the fan-out cap; tighten the level
  guard. **Effort:** small. **Call: NOW** (cheap, it's code I just wrote, rides the F-series).

### F21 — genesis RESUME branch dead-end guard
- **Finding:** CFW-02. **Impact:** if post-reconcile L1 state isn't running/dead, resume routes into an
  illegal-transition claim → the cascade root dead-ends. **Fix:** handle the intermediate-state case.
  **Effort:** small. **Call: NOW** (it's on the boot path).

### F22 — L1→grilling-session intake dispatch owner
- **Finding:** MED-5. **Impact:** the intake (user→intent-spec) has no harness owner — no spawn path for
  the grilling session. **NOTE:** L1 is the most human-tuned layer and intake may run as an L1-driven
  conversation (role-doc owned) rather than harness-spawned. **Call: LATER** (clarify intake ownership;
  the first run can use a synthetic intent-spec, as the evals did).

### F23 — replay reconstruction / own-slice WAL row shape
- **Findings:** WAL-02, executor-2, reconcile-5. **Impact:** own-slice rows don't omit the
  transition/binding_delta block as §3.5 specs; minor replay-shape drift. **Call: LATER** (correctness
  is preserved by the generation-CAS; a cleanliness fix).

### F24 — reconcile uuid-mismatch handling + MC-1 test-realness
- **Findings:** reconcile-4, MC-1. **Impact:** a uuid-mismatch present pane is silently no-op'd (not
  escalated); the uuid guard is inert against real tmux (tests inject a field real tmux omits). **Fix:**
  escalate the mismatch; add a real-tmux contract test for the uuid field. **Call: LATER** (pairs with
  the real-tmux contract-test debt, Lesson 6).

### F25 — pieces_present cross-ref / seat-boundary coverage
- **Findings:** pieces-present-1, pieces-present-3, brief-1/-2. **Impact:** the completeness checker
  doesn't resolve dangling pointers or exercise #review/#test seat boundaries; the seat-variant doesn't
  select the manifest. **Call: LATER** (the gate's own completeness; not on the first-run critical path).

### F26 — fencing/necro edge cases
- **Findings:** detector_signals-2 (None==None fence no-op), FOT-1 (terminal re-register resets epoch),
  necro-1/-2 (resume_brief contract). **Impact:** edge-case fencing correctness. **Call: LATER**
  (latent; tighten alongside F6's lock work).

### F27 — docstring / comment drift sweep
- **Findings:** ~15 LOWs (addressing-3, states-1/-2, daemon-3, fencing-1, claude_code-7, etc.). **Impact:**
  comments/docstrings describe superseded behavior (the flat collapse, wrong § citations, scrambled step
  numbers) — misleads the next reader, no runtime effect. **Call: LATER** (one documentation pass).

---

## SUMMARY — the NOW set vs LATER

**NOW (first supervised end-to-end live run):**
F1 (daemon assembly) · F2 (result-routing) · F3 (exception taxonomy) · F4 (WAL replay) · F5 (terminal
vocab) · F6 (lock scope — decide the fork) · F7 (L1 workspace) · F8 (promote path+caller) · F14
(last_tick_at) · F15 (fleet view) · F16 (pause/resume/answer) · F18 (tmux_target — verify) · F19 (signal
schema) · F20 (outbox ordering) · F21 (genesis resume).
Plus **F9–F13 (jail) IF the first run is jailed** — pending the jail-on decision + F13 adjudication.

**LATER (deferred behind a trigger):**
F17 (model-used checker → with Codex/O1) · F22 (intake owner → clarify; synthetic spec for now) · F23
(WAL-row shape) · F24 (uuid + real-tmux contract test) · F25 (pieces_present coverage) · F26 (fencing
edges) · F27 (docstring sweep).

**Recommended build order:** F1 → F7 → {F2, F3, F4, F5} → F6 → {F18, F19, F20, F21} → {F14, F15, F16} →
[jail decision → F9–F13] → F8 → first live run → LATER tier.

**Key decisions owed from the user:**
1. **Jail-on for the first run?** (gates whether F9–F13 are NOW or LATER)
2. **F6 lock fork:** reconcile-takes-its-own-lock vs separate single-instance lock file?
3. **F13 read-jail scope:** confirm intended v1 read-confinement (I'll read SECURITY.md and recommend).
4. **Confirm the NOW set** or move items between NOW/LATER.
