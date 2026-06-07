# Implementation-vs-Spec Review — 2026-06-07

**Method.** Two multi-phase adversarial workflows over the whole build, then orchestrator ground-truth
re-verification of every CRITICAL/HIGH (the workflow output is *input to judgment, not the verdict*).

- **W1 — per-module conformance** (27 modules): one reviewer per module reading it line-by-line vs its
  governing spec, then **3 independent adversarial verifiers per finding** (spec-accuracy / code-accuracy /
  intentionality-vs-fork-registers). Survives only at ≥2/3. → 96 raised, **62 confirmed**.
- **W2 — cross-cutting invariants + completeness** (10 invariants traced across modules + 4 completeness
  critics): same 3-way verification. → 62 raised, **41 confirmed**.
- **Merged: 103 confirmed** (5 CRITICAL, 25 HIGH, 37 MEDIUM, 36 LOW). Both workflows independently
  returned **BLOCK**.

**Orchestrator-verified false positive (dropped):** `sandbox-1` (W1 HIGH) claimed a jailed agent cannot
traverse into its own nested WORKROAT — refuted by a real sandbox-exec test (read rc=0). A reminder that
the verifiers can share a misread; every actioned finding is re-checked against ground truth.

---

## THE HEADLINE — the daemon is built but not ASSEMBLED (both workflows converge here)

Every substrate piece exists and is unit-tested, but the top-level resident-daemon assembly that wires
them together in production is missing. Three converging confirmations:

- **No process entrypoint** (W1 daemon-4): the launchd plist execs `python3 -m harnessd.daemon`, but
  `daemon.py` has no `if __name__ == "__main__"` / no `harnessd/__main__.py` → the process defines
  functions and exits. `boot()`/`poll_loop()` are never called. *(orchestrator-verified)*
- **IPC listener never served** (W1 ipc-1): `serve_forever`/`serve_one` have no production caller;
  `boot`/`poll_loop` never bind the `.harnessd/harnessd.sock`. The entire CLI→daemon path is dead.
  *(orchestrator-verified: no `AF_UNIX`/`serve_*` in daemon.py)*
- **Watchdog never ticked** (W2 NSL-01 / CRIT-1 / URP-01 / URP-02, all 3/3): `poll_once` calls
  `reconcile_tick` + outbox drain only. It never calls the watchdog — so **no node ever auto-collapses on
  sign-off, no idle leaf ever fails-loud, no coordinator-death probe, no ③-wake nudge.** The autonomous
  spine does not run. *(orchestrator-verified: no watchdog/read_terminal_signal call in daemon.py or
  reconcile.py)*

A green 578→647-test suite hides all of it because every collapse/sign-off/wake/promote test drives the
unit functions directly and **bypasses `poll_once`** (W2 LOW-6). This is Lesson 9 (test-masking) at the
system level.

---

## CRITICAL (5) — all orchestrator-verified

| id | finding | verified |
|---|---|---|
| W2 NSL-01 / CRIT-1 / URP-01 / URP-02 | watchdog orphaned from the daemon loop (see headline) | ✅ grep: no caller |
| W2 CFW-01 | **L1 root binding has no `workspace` field** → its outbox is never serviced → L1 can never spawn L2; the cascade is dead at edge 1. `_register_child` sets workspace (added in the nesting fix) but `_register_l1_root` (genesis.py:192-209) was never updated. Masked by CFW-03 (tests hand-seed workspace). | ✅ genesis.py vs outbox.py:219 |
| W2 JSF-01 | cross-project read-deny covers only `/runtime/`; with `(allow default)`, a jailed agent can READ the user's OTHER projects/files on disk (outside /runtime/ + the named secret-denies). **Needs a SECURITY.md scope check** — may be an intended v1 write-jail-not-read-jail limitation, or a real exfil hole. | ⏳ spec-scope check owed |

(W2 listed CRIT-1/URP-01/NSL-01 as separate CRITICALs; they are the same root — counted once in the fix plan.)

---

## HIGH (25) — CRITICAL/HIGH all orchestrator-verified; grouped by cluster

### Cluster ① — result-swallowing (systemic; one root fix)
A caller discards the executor/spawn `Result` and reports success on a *failed* CAS/fenced/illegal
transition. Root: `chokepoint.collapse()` calls `executor.transition(...)` then `return None`
unconditionally (chokepoint.py). Members:
- W1 genesis-1 (3/3): first-boot L1 spawn failure swallowed — `claim_and_spawn` returns `ok=False`
  (doesn't raise); `run_genesis` discards it → clean "success" with no actor, no escalation. ✅
- W1 chokepoint-2 (root): collapse drops the TransitionResult. ✅
- W1 watchdog-2: COLLAPSE/FAILED actions trust collapse → a fenced/illegal terminal transition "succeeds". ✅
- W1 ipc-2 (milder than stated): `_handle_kill` *does* catch failure via a post-read, but reports a
  generic message and loses the specific abort reason (CAS vs fencing vs illegal-edge). ✅ downgraded
- W1 harnessctl-1/-2: CLI crashes on a missing --brief file / garbled daemon response (uncaught).

### Cluster ② — exception taxonomy (systemic; one root fix)
`SpawnFailure`/`AuthExpired`/`ApiKeyForbidden` never set a `failure_class` attribute (oauth_guard.py:209),
so the chokepoint's `getattr(exc,'failure_class',None) or 'model_unavailable'` mis-routes:
- W1 oauth_guard-1 / claude_code-2 (3/3): an auth-token lapse is escalated as `model_unavailable` — the
  exact masquerade DAEMON §6.3 forbids. ✅ (latent until containment/real-spawn live)
- W1 claude_code-3 / oauth_guard-2: `ApiKeyForbidden` is uncatchable by the chokepoint catch; the `class`
  discriminator the docstrings promise is never set.

### Cluster ③ — durability / replay
- W1 executor-1 / W2 WAL-01 (3/3, same family): **WAL replay applies `binding_delta`, not the record's
  authoritative `to_state`.** A committed transition whose caller delta omits `state` (state is set
  authoritatively in `transition`, not via the delta) replays to the *un-advanced* state after a
  §4.4-window crash. The most serious durability finding. ✅
- W1 reconcile-2 / W2 SWCAS-01 (same): `reconcile.replay_wal` checkpoint writes with `_lock_held=True`
  while genesis has *released* the lock before `reconcile_on_restart` → the flag is false-by-fact (the
  guard is flag-only, not a real lock check). Latent (single-writer topology), but the documented
  invariant is literally broken on the recovery write path. ✅
- W2 SWCAS-02 (3/3): the §2.3 single-instance lock is dropped after genesis STEP1+2 (same file is the
  per-mutation EX lock; holding both deadlocks) → no lifetime single-instance guard. Design conflict
  between §2.3 (long-held) and §4.3 (per-mutation) sharing one lock file.

### Cluster ④ — terminal-vocab / state-machine
- W1 reconcile-1 (3/3): leaf-necro stamps `(terminal_signal=DIED_INFRA, state=dead)` but the §3.6 vocab
  maps `DIED_INFRA → state failed`. `_terminal_necro` hardcodes `"dead"` for both leaf + coordinator. ✅
- W2 SML-01 (3/3): the §3.6 normative run-ledger event names aren't emitted as specified.
- W2 SML-02 (3/3): `signal_ESCALATED` is never journaled; the ESCALATED running→running slot-hold isn't
  exercised through the loop.

### Cluster ⑤ — jail / security (all LATENT: no production caller requests containment yet)
- W1 chokepoint-1 (3/3): the resume/necro path never re-applies the write-jail (containment produced only
  in `claim_and_spawn` STEP2a) → a contained node re-opens UNJAILED on every recovery (SECURITY §8.1
  requires "same jail re-applied on resume/necro"). ✅
- W1 tmux-1 (3/3): `create_detached`'s `argv[:2]==["env","-i"]` idempotency guard misses a jailed vector
  (`["sandbox-exec",...]`) → re-wraps, putting `env -i` OUTSIDE `sandbox-exec` (wrong §7.1 launch form). ✅
- W1 claude_code-1 (3/3): the jailed pane env never sets `CLAUDE_CODE_TMPDIR`/`HOME` (docstring claims it
  does; SECURITY §2.3 needs TMPDIR→WORKROOT so CC scratch stays in-jail). ✅
- W2 JSF-02 (3/3): an empty/malformed containment WORKROOT silently degrades the jail to the daemon CWD
  while still skip-perms — a fail-open. ✅
- W2 JSF-03 (3/3): **`promote()` sources `/runtime/proj/{project}/` but agents write `/runtime/nodes/<path>/`**
  → the delivery terminus reads a path no agent writes to (a layout mismatch promote never reconciled with
  the node layout). ✅

### Cluster ⑥ — orphaned terminus / cascade edges
- W2 CRIT-3 (2/3): `promote()` (Inc 17, the delivery terminus) has no caller — no IPC handler, no L1
  final-accept path invokes it. ✅
- W2 CFW-02 (3/3): genesis RESUME branch dead-ends the cascade root if post-reconcile L1 state isn't
  running/dead (routes into an illegal-transition claim).
- W2 CRIT-2 (3/3): the ③-wake nudge has no daemon caller (folds into the headline watchdog-wiring fix).

### Cluster ⑦ — signal schema / observability / addressing
- W1 detector_signals-1 (3/3): the `.signal` artifact is written/fenced as `{signal,ts,owner_token,evidence}`
  but DAEMON §3.5 specifies `{tag,at,notes,session_uuid}` fenced on `session_uuid`. Stricter, but the
  agent-writer and daemon-reader must agree on the schema. ✅
- W2 OSA-01 (3/3): `binding.tmux_target` (raw `harness:<address>`) disagrees with the live tmux session
  key (collapsed) → reconcile's `targets.get(tmux_target)` lookup can never match. ✅ (needs check vs how
  tmux sessions are actually keyed)
- W2 OBS-1 (3/3): the E32 `model_used == configured` trace-checker is unbuilt — a silent model-fallback
  could reach a node with no escalation in the trace.
- W1 daemon-1 / W2 COMP-5 (same): `runtime.json.last_tick_at` is never stamped per tick → the §2.6
  hang-detection surface (a wedged-but-alive daemon) doesn't exist.

---

## MEDIUM (37) / LOW (36)
Workflow-confirmed (≥2/3), not all individually orchestrator-re-verified. Notable:
- **MEDIUMs in code authored this session (orchestrator-verified):** outbox-1 (fan-out cap runs before
  the idempotent-re-service check → an already-live child gets a misleading `.rejected` at cap) + outbox-2
  (already-live child double-counted against the in-sweep cap). Fix: move the already-live check above the
  cap. Also outbox-3 (a None parent level lets any child level through — superseded by the descent gate but
  the guard order is loose).
- **Completeness (W2 critics):** COMP-3 (human-control WRITE verbs pause/resume/answer absent — only the
  read-side `paused_at` exists), COMP-4 (no fleet/tree TEXT VIEW in harnessctl — the sole operator
  situational-awareness surface), MED-5 (the L1→grilling-session intake dispatch has no harness owner).
- **LOWs:** mostly docstring/comment drift (≈15 of 36) — low-risk; a documentation sweep, not behavior.

---

## DEDUP NOTES
Same-root pairs counted once in the fix plan: {daemon-4 + ipc-1 + NSL-01/CRIT-1/URP-01/URP-02} =
daemon-assembly; {executor-1 + WAL-01}; {reconcile-2 + SWCAS-01}; {daemon-1 + COMP-5};
{CRIT-2 + watchdog-wiring}.
