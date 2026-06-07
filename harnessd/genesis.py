"""genesis — the first-boot sequence that establishes the L1 root custody (IMPLEMENTATION-PLAN §2.12).

THE single load-bearing property: ``run_genesis`` drives the DAEMON §7 LOCKED genesis sequence in
order — (1) acquire the EX serialization lock; (2) write runtime.json; (3) the PRECONDITION CHECK
(OAuth credential health + pinned-binary, FAIL-LOUD, do NOT spawn on a bad precondition); (4)
reconcile-on-restart (replay the WAL, classify every binding against live tmux, necro the
owned-but-dead — liveness reconstructed from the LEDGER, not memory); (5) if no live, non-terminal L1
binding exists -> SPAWN the L1 root in-role through the ONE spawn chokepoint (role_variant='L1',
parent_address=null, the shared --system-prompt-file + the L1 load-manifest in the brief), ELSE RESUME
(do NOT double-spawn — the F35 stable-address resume-not-double-spawn rule).

genesis is NOT a writer and NOT a spawn path of its own: every binding mutation routes through the
REAL executor (the single writer), the spawn rides the REAL chokepoint.claim_and_spawn (the ONE
spawn path, F-024 claim-before-spawn), and the reconcile rides the REAL reconcile_on_restart. The
ONLY thing genesis owns is the SEQUENCE (lock -> runtime.json -> precondition -> reconcile ->
spawn-or-resume) and the L1-root REGISTRATION (the parentless root planned slot the chokepoint claims).

Authoritative sources:
  - IMPLEMENTATION-PLAN §2.12 (``run_genesis(executor, tmux, config) -> None``), §3 module table
    (genesis.py row, L63): "acquire .harnessd.lock -> write runtime.json -> preconditions() (OAuth
    health + pinned-binary hash, fail-loud) -> reconcile_on_restart -> if no live non-terminal L1
    binding: spawn.claim_and_spawn(L1-root, role_variant='L1', parent=null) ... else RESUME (no
    double-spawn, F35)".
  - DAEMON §7 (the LOCKED genesis sequence, L1058-1087), §5.1 (reconcile-on-restart), §6.1
    (claim-before-spawn), §6.3 (the auth_expired precondition class).

BUILDER DECISIONS (the §2.12 details the frozen tests leave open — stated in the build report):

  * THE GENESIS ``config`` SHAPE — §2.12 names only ``config``; the test threads a permissive
    SimpleNamespace carrying ``env`` (the OAuth env for the credential precondition), ``l1_address``
    (the L1 root address — the test owns the identity, genesis owns the sequence), ``l1_level`` /
    ``level_config`` (the L1 LevelConfig), ``runtime_root``, ``build_id``, and ``pinned_binary``.
    genesis reads these defensively (``getattr`` with sane fallbacks) so a sparse config still drives
    a well-formed boot. FORK-GENESIS-CONFIG: the precise carrier is the caller's; the load-bearing
    inputs (env for the precondition, the L1 address + level) are pinned by the tests.

  * runtime.json SHAPE — the §2.3 daemon runtime descriptor: ``{build_id, started_at, pid}`` (+
    ``runtime_root`` for legibility). Written via the durable ``store.atomic_replace`` (tmp + fsync +
    os.replace) so a concurrent reader never sees a torn descriptor. It is written INSIDE the held EX
    lock (§7 step 3 orders it after the lock), but it is a daemon-runtime descriptor, NOT control
    state, so it does NOT route through the executor / append a WAL row. Path: ``<runtime_root>/
    runtime.json`` (the §3 on-disk tree).

  * THE L1-ROOT REGISTRATION — the chokepoint claims an EXISTING planned slot (executor.claim reads
    the live binding). On first boot there is no L1 binding, so genesis REGISTERS the parentless root
    planned slot first (state='planned', generation=0, lease_epoch=1, parent_address=null,
    level/role_variant=L1, a minted owner_token), then hands it to claim_and_spawn. The registration
    is the ONE direct ``ledger.write_binding(_lock_held=True)`` genesis does (it runs inside the held
    EX lock, the §2.10-sanctioned lock-held seeding path the suite uses) — the chokepoint then drives
    planned->claimed->spawning->running through the REAL executor. FORK-L1-REGISTER: an alternative is
    a dedicated executor.register primitive; v1 reuses the lock-held write_binding seed the suite
    already validates, keeping the registration a single faithful write.

  * THE LIVE-L1 CHECK (§7 step 6 spawn-vs-resume) — "no live, non-terminal L1 binding" means: the L1
    binding is absent, OR it is terminal (done/failed/dead). reconcile_on_restart has already
    classified it (adopt a live pane, necro a dead one) BEFORE this check, so genesis reads the
    POST-reconcile binding: a non-terminal L1 binding after reconcile is a live/resumable root ->
    RESUME (no double-spawn); an absent or terminal one -> SPAWN. By reading the post-reconcile ledger
    (not memory) the no-double-spawn invariant holds against the durable truth.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from harnessd import addressing
from harnessd import config as _config_mod
from harnessd import fencing, ledger, states, store
from harnessd import reconcile as _reconcile_mod
from harnessd.spawn import chokepoint
from harnessd.spawn import oauth_guard


# ---------------------------------------------------------------------------
# Step 1 — the EX serialization lock (the single serialization domain, §4.3 / §7 step 3).
# The lock file co-locates with the WAL/binding under RUNTIME_ROOT (executor.LOCK_FILENAME).
# ---------------------------------------------------------------------------

_LOCK_FILENAME = ".harnessd.lock"


def _lock_path(runtime_root: Path) -> Path:
    """The EX serialization-domain lock path (``<runtime_root>/.harnessd.lock``, §4.3)."""
    return Path(runtime_root) / _LOCK_FILENAME


def _runtime_root(cfg) -> Path:
    """Resolve the runtime root from the config, falling back to the bound ledger.RUNTIME_ROOT."""
    root = getattr(cfg, "runtime_root", None)
    if root is not None:
        return Path(root)
    if ledger.RUNTIME_ROOT is not None:
        return Path(ledger.RUNTIME_ROOT)
    raise RuntimeError(
        "genesis runtime_root is not configured: pass config.runtime_root or bind ledger.RUNTIME_ROOT"
    )


# ---------------------------------------------------------------------------
# Step 2 — runtime.json (the §2.3 daemon runtime descriptor: build-id / started_at / pid).
# ---------------------------------------------------------------------------

def write_runtime_json(runtime_root: Path, *, build_id: Optional[str], pid: Optional[int] = None) -> Path:
    """Write the §2.3 daemon runtime descriptor (``runtime.json``) durably (tmp + fsync + replace).

    Carries ``build_id`` / ``started_at`` (the single canonical UTC clock, §4.6) / ``pid`` / the
    ``runtime_root`` for legibility. A daemon-runtime descriptor, NOT control state — it does NOT
    route through the executor and appends no WAL row (only durable bindings + the WAL are control
    truth). Returns the written path.
    """
    import os

    from harnessd import clock

    runtime_root = Path(runtime_root)
    path = runtime_root / "runtime.json"
    descriptor = {
        "build_id": build_id,
        "started_at": clock.now_utc(),
        "pid": pid if pid is not None else os.getpid(),
        "runtime_root": str(runtime_root),
    }

    import json

    def render(handle):
        json.dump(descriptor, handle, ensure_ascii=True, sort_keys=True, indent=2)
        handle.write("\n")

    store.atomic_replace(path, render)
    return path


# ---------------------------------------------------------------------------
# Step 4 — preconditions (FAIL-LOUD, do NOT spawn on a bad precondition; DAEMON §7 step 4).
# ---------------------------------------------------------------------------

def preconditions(cfg) -> None:
    """The §7 step-4 precondition gate (FAIL-LOUD — raises BEFORE any spawn on a bad precondition).

    (1) OAuth credential health via the REAL ``oauth_guard.check_credential_health`` — an absent /
        expired ``CLAUDE_CODE_OAUTH_TOKEN`` raises the DISTINCT ``AuthExpired`` (a SpawnFailure, NOT
        an ApiKeyForbidden), so a token lapse reads as "refresh the token", not a model outage
        (DAEMON §6.3). genesis does NOT home-grow a string check — it routes through the positive
        oauth_guard check, the single credential authority.
    (2) Pinned-binary present + version (§6.2). The pinned hash is a v1 placeholder (config.PINNED_
        BINARY_HASH is None until commissioning captures it), so the hash check is a no-op when the
        hash is unset; the VERSION seat must be present (a missing version is a misconfiguration).

    Raises (AuthExpired / a precondition error) BEFORE returning — the caller (run_genesis) never
    reaches the spawn on a raised precondition, so no L1 actor opens on a bad precondition.
    """
    env = getattr(cfg, "env", None) or {}
    # (1) Credential health — the REAL positive check (raises AuthExpired on an absent token).
    oauth_guard.check_credential_health(env)

    # (2) Pinned-binary present + version verified (§6.2). The hash is verified only when captured.
    pinned = getattr(cfg, "pinned_binary", None) or _config_mod.PINNED_BINARY
    version = getattr(pinned, "version", None)
    if not version:
        raise RuntimeError(
            "pinned-binary precondition failed: no pinned version configured (§6.2) — "
            "do not spawn on a bad precondition (DAEMON §7 step 4)"
        )
    return None


# ---------------------------------------------------------------------------
# Step 6 — the L1-root registration (the parentless planned slot the chokepoint claims).
# ---------------------------------------------------------------------------

def _register_l1_root(l1_address: str, level: str, role_variant: str, runtime_root: Path) -> dict:
    """Register the parentless L1 root in the binding ledger as a fresh ``planned`` slot.

    The chokepoint claims an EXISTING planned slot (executor.claim CAS-reads the live binding); on
    first boot there is no L1 binding, so genesis seeds the parentless root here first. parent_address
    is null (the L1 root is the ONLY node with no parent — DAEMON §7), generation=0 / lease_epoch=1 /
    a minted owner_token (the same fresh-planned shape the chokepoint tests seed).

    The whole-map write takes the EX serialization lock HERE (a brief, self-contained acquire) so
    ``_lock_held=True`` is TRUE-by-fact, not just by flag — the genesis single-instance lock was
    released before STEP 5, so this seeding write must re-acquire it. The lock is released when this
    function returns, BEFORE ``chokepoint.claim_and_spawn`` runs (which re-takes it per-mutation via
    ``executor.claim``) — so there is no re-entrant fcntl deadlock. Returns the registered binding
    (its owner_token is the claim's CAS precondition).
    """
    subagent_id = "subagent-l1-root"
    session_uuid = "genesis-l1-root"
    lease_epoch = 1
    generation = 0
    owner_token = fencing.mint_owner_token(l1_address, subagent_id, session_uuid, lease_epoch)
    binding = {
        "node_address": l1_address,
        "parent_address": None,  # the L1 root is the ONLY parentless node (DAEMON §7)
        "level": level,
        "subagent_id": subagent_id,
        "session_uuid": session_uuid,
        "tmux_target": "harness:" + l1_address,
        "state": "planned",
        "generation": generation,
        "lease_epoch": lease_epoch,
        "owner_token": owner_token,
        "last_applied_seq": 0,
        "liveness_state": "claimed",
        "terminal_signal": None,
        "terminal_signal_at": None,
        "gate_crossed_at": None,
        "paused_at": None,
        # The L1 root's workspace = its canonical nested node dir (mirror _register_child). Without it
        # service_outbox short-circuits to [] and L1 can never spawn L2 — the cascade dies at edge 1
        # (REMEDIATION F7 / review CFW-01).
        "workspace": str(addressing.node_dir(l1_address, runtime_root)),
    }
    # Merge into the live map (preserve any pre-existing siblings) and write under a BRIEFLY-held EX
    # lock — released on exit, before claim_and_spawn re-takes it per-mutation (no re-entrant deadlock).
    with store.file_lock(_lock_path(runtime_root), shared=False):
        live_map = dict(ledger.all_nodes())
        live_map[l1_address] = binding
        ledger.write_binding(live_map, _lock_held=True)
    return binding


def _l1_binding_resumable(l1_address: str) -> bool:
    """True iff an L1 binding exists and is NON-TERMINAL (a live-or-resumable root; §7 step 6).

    Read AFTER reconcile_on_restart, so this reads the POST-reconcile durable ledger — not in-memory
    daemon state. An absent or terminal (done/failed/dead) binding means SPAWN; a non-terminal one is
    a live-or-resumable root (the caller further distinguishes ALREADY-LIVE-adopted vs needs-RESUME
    using the reconcile report).
    """
    binding = ledger.read_binding(l1_address)
    if binding is None:
        return False
    return not states.is_terminal(binding.get("state"))


# ---------------------------------------------------------------------------
# run_genesis — the §2.12 frozen entry. The DAEMON §7 LOCKED sequence, in order.
# ---------------------------------------------------------------------------

def run_genesis(executor, tmux, config) -> None:
    """The first-boot sequence (§2.12 / DAEMON §7 LOCKED) — establishes the L1 root custody.

    Sequence (in order, under the held EX lock):
      1. acquire ``.harnessd.lock`` (the single serialization domain, §4.3);
      2. write ``runtime.json`` (the §2.3 daemon runtime descriptor);
      3. PRECONDITIONS — OAuth credential health + pinned-binary (FAIL-LOUD; do NOT spawn on a bad
         precondition — an absent token raises AuthExpired BEFORE any spawn, §7 step 4);
      4. ``reconcile_on_restart`` — replay the WAL + classify every binding against live tmux (necro
         the owned-but-dead, adopt the live; liveness reconstructed from the LEDGER, §5.1);
      5. spawn-or-resume L1: if NO live non-terminal L1 binding -> register the parentless root +
         ``chokepoint.claim_and_spawn`` it in-role (role_variant='L1', the shared --system-prompt-file
         + the L1 load-manifest in the brief); ELSE ``necro.resume_brief`` (RESUME, no double-spawn,
         F35).

    Returns None. Raises a precondition failure (AuthExpired / a pinned-binary error) BEFORE the
    spawn — no L1 actor opens on a bad precondition.
    """
    runtime_root = _runtime_root(config)
    l1_address = getattr(config, "l1_address", "L1#exec")
    l1_level = getattr(config, "l1_level", "L1")
    level_config = getattr(config, "level_config", None) or _config_mod.LevelConfig.for_level(l1_level)
    role_variant = getattr(level_config, "role_variant", l1_level)
    build_id = getattr(config, "build_id", None)

    # STEP 1+2 — the single-instance guard + the runtime descriptor write, under a BRIEFLY-held EX
    # lock. The lock here is the §7-step-3 SINGLE-INSTANCE guard (two daemons cannot both write
    # runtime.json / claim the root); it is acquired and RELEASED before the executor-backed work
    # below. It must NOT wrap STEP 4/5: the frozen single-writer executor (and reconcile through it)
    # take this SAME .harnessd.lock per mutation, so holding it across them would re-enter fcntl
    # LOCK_EX on the same path and DEADLOCK. The executor's own per-mutation EX lock is the
    # serialization domain for the control-plane writes (§4.3); genesis serializes only the
    # non-executor single-instance + descriptor step here.
    with store.file_lock(_lock_path(runtime_root), shared=False):
        # STEP 2 — write the daemon runtime descriptor (§2.3). Not control state; no WAL row.
        write_runtime_json(runtime_root, build_id=build_id)

        # STEP 3 — PRECONDITION CHECK (FAIL-LOUD). Raises BEFORE any spawn on a bad precondition
        # (an absent OAuth token -> AuthExpired) — the fail-loud gate is ahead of the spawn (§7 step 4).
        # Run inside the single-instance lock (no executor call) so a bad precondition fails before
        # any other instance could race the root claim.
        preconditions(config)

    # STEP 4 — reconcile-on-restart: replay the WAL, classify every binding against live tmux, necro
    # the owned-but-dead, adopt the live. Liveness is reconstructed from the LEDGER (+ tmux), not from
    # memory (§5.1). Routes through the REAL executor, which takes the .harnessd.lock per mutation —
    # so it runs OUTSIDE the single-instance lock above (no re-entrant fcntl deadlock). NEVER spawns
    # here — the spawn-or-resume decision is STEP 5. The report's ``adopted`` list tells genesis
    # whether the L1 pane was found ALIVE (adopted) — the no-double-spawn discriminator below.
    report = _reconcile_mod.reconcile_on_restart(executor, tmux)

    # STEP 5 — spawn-or-resume L1 (§7 step 6), reading the POST-reconcile durable ledger.
    if _l1_binding_resumable(l1_address):
        # A non-terminal L1 binding survived reconcile -> do NOT double-spawn (F35). Two sub-cases:
        if l1_address in (report.adopted or []):
            # ALREADY LIVE: reconcile ADOPTED the live L1 pane (pane alive + uuid-matched). The actor
            # is already running and its custody is re-established — there is NOTHING to (re)open. A
            # fresh --resume here would open a SECOND L1 actor (F35 violation). Adopt-and-done.
            return None
        # Non-terminal but NOT adopted (its pane was not found live, yet it was not necro'd — a
        # resumable root): RESUME via necro.resume_brief -> the SINGLE gate-firewall point
        # (chokepoint.resume), which re-adopts the address and continues it (never a second fresh root).
        from harnessd import necro

        necro.resume_brief(l1_address, level_config=level_config)
        return None

    # No live/resumable L1 -> first boot (or a necro'd prior root): register the parentless root
    # planned slot, then SPAWN it in-role through the ONE spawn chokepoint (claim-before-spawn, F-024).
    registered = _register_l1_root(l1_address, l1_level, role_variant, runtime_root)
    chokepoint.claim_and_spawn(
        l1_address,
        expected_state="planned",
        expected_generation=registered["generation"],
        expected_owner_token=registered["owner_token"],
        level_config=level_config,
    )
    return None
