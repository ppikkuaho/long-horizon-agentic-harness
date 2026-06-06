"""tmux — the thin REAL tmux control-plane wrapper (IMPLEMENTATION-PLAN §2.11; DAEMON §6.2).

The transport the spawn chokepoint, detector, and reconcile sweep talk through. Unlike
``oauth_guard`` (pure functions) this module shells out to a REAL ``tmux`` binary via
``subprocess`` — it is the boundary between the harness and the OS process tree.

The §2.11 frozen surface:

  * ``create_detached(session_name, argv, env) -> pane_id`` — open a DETACHED session whose
    pane process is the FROM-EMPTY isolator ``env -i <K=V…> <argv…>`` (``build_pane_argv``).
    ``env -i`` clears the inherited environment and re-adds ONLY the explicit vars, so the
    pane inherits NOTHING from the long-lived tmux SERVER env (the load-bearing OAuth-only
    mechanism: a launchd-spawned daemon may have widened the server env with a stray
    ANTHROPIC_API_KEY/OPENAI_API_KEY; a bare ``new-session <cmd>`` would leak it into the pane).
  * ``capture_pane(session_name) -> str`` — ``capture-pane -p`` readback of the pane buffer.
  * ``list_targets() -> {tmux_target: {pane_pid, pane_dead, window_activity}}`` — the live
    control-plane snapshot Increments 6/7 (detector / reconcile) read.
  * ``kill(session_name) -> None`` — tear a session down (the control-plane teardown edge).
  * ``server_env() -> dict`` — ``show-environment -g`` readback: WHAT THE SERVER WOULD LEAK,
    the input ``oauth_guard.assert_pane_env_isolated`` checks before a spawn.

THE SOCKET SEAM (``set_socket`` / module-level ``_SOCKET``):
    Every tmux invocation is prefixed ``tmux -L <socket>`` when a socket is bound. The daemon
    binds ONE dedicated socket for its server; tests bind a unique per-test ``-L`` socket so a
    real-tmux test drives an ISOLATED server (never the user's default) and a kill-server
    teardown guarantees no leak. ``set_socket(None)`` falls back to the default tmux server.

DESIGN DECISIONS for §2.11 details the plan leaves to the builder (stated in the build report):
  * ``build_pane_argv`` is the SINGLE from-empty pane constructor BOTH this wrapper's
    ``create_detached`` and the Claude adapter use, so the guard and the wrapper agree on the
    exact isolator shape (the test pins ``build_pane_argv(...)[: 2] == ["env", "-i"]``).
  * ``list_targets`` keys are ``<session_name>:<window_index>.<pane_index>`` (the tmux target
    triple) — ``window_activity`` is included per the §2.11 shape even though v1's verdict fuses
    only ``pane_pid``/``pane_dead`` (Increment 6).
  * ``new-session`` receives ``argv`` as DISTINCT argv tokens (NOT a re-quoted shell string), so
    the ``env -i <K=V…> <argv…>`` vector is handed to tmux verbatim — no quoting round-trip that
    could re-expand a value.
"""

from __future__ import annotations

import subprocess

# ---------------------------------------------------------------------------
# The socket seam. None -> the user's default tmux server. A bound socket ->
# `tmux -L <socket>` (a DEDICATED server: the daemon's, or a per-test isolated one).
# ---------------------------------------------------------------------------

_SOCKET: str | None = None


def set_socket(socket: str | None) -> None:
    """Bind (or clear) the dedicated ``-L`` socket every tmux invocation targets.

    The daemon binds its one server socket once at boot; tests bind a unique per-test socket
    so they drive an ISOLATED server (and tear it down via kill-server) without ever touching
    the user's default tmux server. ``set_socket(None)`` restores the default-server behavior.
    """
    global _SOCKET
    _SOCKET = socket


def _base_cmd() -> list[str]:
    """The ``tmux [-L <socket>]`` prefix every invocation is built on."""
    cmd = ["tmux"]
    if _SOCKET is not None:
        cmd += ["-L", _SOCKET]
    return cmd


def _run(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess:
    """Run a tmux subcommand on the bound socket, capturing output (text)."""
    return subprocess.run(
        _base_cmd() + args,
        check=check,
        capture_output=True,
        text=True,
    )


# ---------------------------------------------------------------------------
# The from-empty pane isolator — the SINGLE constructor the wrapper AND the adapter share.
# ---------------------------------------------------------------------------

def build_pane_argv(env: dict, argv: list[str]) -> list[str]:
    """Build the from-empty ``env -i <K=V…> <argv…>`` pane command (§2.11, the OAuth-only floor).

    ``env -i`` clears the inherited environment, then re-adds ONLY the explicit ``env`` vars, so
    the pane inherits NOTHING from the tmux SERVER environment. This is the ONE place the
    isolator vector is assembled — the adapter calls this same seam so the guard
    (``oauth_guard.assert_pane_env_isolated``, which requires ``pane_argv[:2] == ["env", "-i"]``)
    and the wrapper agree on the exact pane shape.
    """
    pane = ["env", "-i"]
    for key, value in env.items():
        pane.append(f"{key}={value}")
    pane += list(argv)
    return pane


# ---------------------------------------------------------------------------
# create_detached — open a detached session whose pane is the from-empty isolator.
# ---------------------------------------------------------------------------

def create_detached(session_name: str, argv: list[str], env: dict) -> str:
    """Open a DETACHED tmux session running the from-empty ``env -i`` pane; return the pane id.

    The pane command is ``build_pane_argv(env, argv)`` — ``env -i <K=V…> <argv…>`` — handed to
    ``new-session`` as distinct argv tokens. ``-d`` keeps the session detached (the daemon owns
    it, not an attached terminal). Returns the ``#{pane_id}`` of the created pane (a non-empty
    ``%N`` string) as the spawn handle.

    WRAPPING-IDEMPOTENT: if ``argv`` ALREADY begins with the from-empty isolator (``env -i``) —
    the adapter pre-builds the exact pane vector it gates with ``build_pane_argv`` and passes it
    here — it is used verbatim (NOT re-wrapped). A raw ``argv`` (the direct-call path the
    real-tmux tests use, e.g. ``["sh", "-c", …]``) is wrapped from-empty. Either way the pane is
    a single from-empty ``env -i`` isolator.
    """
    if list(argv[:2]) == ["env", "-i"]:
        pane_argv = list(argv)
    else:
        pane_argv = build_pane_argv(env, argv)
    # `new-session -d -s <session> -P -F '#{pane_id}' <pane_argv...>` opens detached and prints
    # the new pane's id. The pane_argv tokens follow as the command (NOT a re-quoted string).
    args = ["new-session", "-d", "-s", session_name, "-P", "-F", "#{pane_id}"] + pane_argv
    proc = _run(args)
    return proc.stdout.strip()


# ---------------------------------------------------------------------------
# capture_pane — readback of the pane's visible buffer.
# ---------------------------------------------------------------------------

def capture_pane(session_name: str) -> str:
    """Return the pane's captured buffer (``capture-pane -p``) — the pane-readback channel.

    Targets the session by name (``-t``); ``-p`` prints the buffer to stdout. Used to read back
    a fake-CLI pane's output in the real-tmux tests (e.g. the ``printenv`` isolation probe).
    """
    proc = _run(["capture-pane", "-p", "-t", session_name], check=False)
    return proc.stdout


# ---------------------------------------------------------------------------
# list_targets — the live control-plane snapshot (the §2.11 shape Inc 6/7 read).
# ---------------------------------------------------------------------------

def list_targets() -> dict[str, dict]:
    """Return ``{<session>:<window>.<pane> -> {pane_pid, pane_dead, window_activity}}`` (§2.11).

    A ``list-panes -a`` sweep across the WHOLE server, formatted into the exact shape Increment
    6's ``pane_alive`` (``targets[t]["pane_dead"]`` / ``["pane_pid"]``) and Increment 7's
    reconcile sweep read. ``pane_pid`` is a real int; ``pane_dead`` is 0/1. On an empty server
    (no sessions) tmux exits non-zero with "no server running" — that is the empty snapshot, so
    we return ``{}`` rather than raising.
    """
    fmt = "#{session_name}\t#{window_index}\t#{pane_index}\t#{pane_pid}\t#{pane_dead}\t#{window_activity}"
    proc = _run(["list-panes", "-a", "-F", fmt], check=False)
    if proc.returncode != 0:
        # No server / no sessions -> an empty snapshot, not an error.
        return {}
    targets: dict[str, dict] = {}
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 6:
            continue
        session, window, pane, pid, dead, activity = parts[:6]
        target = f"{session}:{window}.{pane}"
        targets[target] = {
            "pane_pid": int(pid) if pid.isdigit() else None,
            "pane_dead": int(dead) if dead.isdigit() else dead,
            "window_activity": int(activity) if activity.lstrip("-").isdigit() else activity,
        }
    return targets


# ---------------------------------------------------------------------------
# kill — control-plane teardown of a session.
# ---------------------------------------------------------------------------

def kill(session_name: str) -> None:
    """Kill a session (``kill-session -t``) — the control-plane teardown edge.

    Best-effort: a session that is already gone is not an error here (idempotent teardown).
    Per §2.11 the chokepoint reaches this ONLY via the executor-stamping path for control
    state; the raw transport is idempotent so reconcile/teardown can call it safely.
    """
    _run(["kill-session", "-t", session_name], check=False)


# ---------------------------------------------------------------------------
# server_env — what the tmux SERVER environment would leak (the guard's input).
# ---------------------------------------------------------------------------

def server_env() -> dict:
    """Return the tmux SERVER global environment (``show-environment -g``) as a dict (§2.11).

    This surfaces WHAT THE SERVER WOULD LEAK into a pane — the input
    ``oauth_guard.assert_pane_env_isolated`` checks to refuse a spawn from a server that already
    carries a stray ANTHROPIC_API_KEY/OPENAI_API_KEY. ``show-environment -g`` prints ``K=V`` per
    line; a ``-K`` line means the var is REMOVED from the server env (we drop those). On a server
    with no sessions yet tmux may report none — an empty dict is the clean snapshot.
    """
    proc = _run(["show-environment", "-g"], check=False)
    if proc.returncode != 0:
        return {}
    env: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        if not line or line.startswith("-"):
            # `-NAME` => the variable is to be UNSET in the pane; not a leakable value.
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key] = value
    return env
