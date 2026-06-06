"""oauth_guard — the OAuth-only enforcer (IMPLEMENTATION-PLAN §2.11, §7; DAEMON §7, §6.3).

THE HARD INVARIANT: no part of the system may ever use a raw API key; all model
usage rides the OAuth subscription token. This module is the chokepoint that
makes that invariant structurally enforceable, BEFORE any pane is spawned.

Three layers (§2.11):

  1. ``assert_no_api_key(env, argv)`` — the RUNTIME-AGNOSTIC negative invariant.
     Always on, Claude AND Codex. Raises ``ApiKeyForbidden`` if a raw
     ``ANTHROPIC_API_KEY`` / ``OPENAI_API_KEY`` sits in ``env`` or ``--bare``
     (the H40 foot-gun that forces API-key auth) is in ``argv``. There is NO
     runtime parameter by design: a future Codex adapter fill cannot satisfy the
     gate by deleting a Claude-only check.

  2. ``assert_pane_env_isolated(pane_argv, server_env)`` — closes the tmux-server
     env-leak hole. A tmux pane otherwise inherits the long-lived tmux SERVER
     environment, which a launchd-spawned daemon may have widened with a stray
     key. Raises ``ApiKeyForbidden`` unless the pane is launched from-empty
     (``env -i …``) AND the SERVER env carries no raw key the pane could inherit.

  3. ``assert_oauth_only(env, argv, pane_argv, server_env)`` — the composed call
     the adapter makes before ``create_detached``: ``assert_no_api_key`` +
     ``assert_pane_env_isolated``.

Plus the CLAUDE-SPECIFIC positive check:

  * ``check_credential_health(env)`` — raises ``AuthExpired`` when the OAuth token
    is absent/expired. This is the POSITIVE half (token present) and lives in the
    Claude adapter's path, NOT the shared negative gate. ``AuthExpired`` is a
    DISTINCT spawn-failure class (subclasses ``SpawnFailure``, never
    ``ApiKeyForbidden``) so a token lapse reads as "refresh the token", NOT a
    fleet-wide model-outage storm (DAEMON §6.3).

These are PURE functions over real env dicts + argv lists. No I/O, no spawn.
"""

from __future__ import annotations

# The raw API-key names that are forbidden EVERYWHERE (env or tmux server env),
# runtime-agnostic. Adding a runtime's key here keeps the gate shared, not gated.
_FORBIDDEN_API_KEYS = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY")

# The CLI flag that forces ANTHROPIC_API_KEY auth and breaks the OAuth token (H40).
_BARE_FLAG = "--bare"

# The OAuth subscription token the Claude positive check requires (DAEMON §7).
_OAUTH_TOKEN_VAR = "CLAUDE_CODE_OAUTH_TOKEN"


# --------------------------------------------------------------------------------------------------
# Exception taxonomy (§2.13). ApiKeyForbidden (the negative-gate class) and AuthExpired (the
# positive-credential class) are DISTINCT and neither subclasses the other — that distinction is
# load-bearing: it lets the escalation say "refresh the token" instead of "model is down".
# --------------------------------------------------------------------------------------------------

class SpawnFailure(Exception):
    """A spawn was refused for a classifiable reason (§2.13).

    The ``class`` is one of {auth_expired, model_unavailable, override_rejected,
    runtime_down}. Subclasses carry the specific semantics; the generic class is
    here so an auth lapse can be classified SEPARATELY from a model outage
    (DAEMON §6.3 — a token lapse is not a fleet-wide outage storm).
    """


class ApiKeyForbidden(Exception):
    """A raw API key (or the --bare flag, or a non-isolated/leaky pane) was found
    where only the OAuth subscription token is allowed (§2.11, the HARD INVARIANT).

    Deliberately a direct ``Exception`` subclass — NOT a ``SpawnFailure`` and NOT
    related to ``AuthExpired`` — so the forbidden-api-key path and the
    credential-lapse path are independently catchable.
    """


class AuthExpired(SpawnFailure):
    """The OAuth subscription token is absent or expired (DAEMON §7, §6.3).

    A DISTINCT spawn-failure class: subclasses ``SpawnFailure`` (so it is
    classified as a spawn failure, separate from ``model_unavailable``) but is
    NOT an ``ApiKeyForbidden`` — a token lapse must read as "refresh the token",
    not "a raw API key leaked" and not "the model is down".
    """


# --------------------------------------------------------------------------------------------------
# Layer 1 — the runtime-agnostic negative invariant.
# --------------------------------------------------------------------------------------------------

def assert_no_api_key(env: dict, argv: list[str]) -> None:
    """RUNTIME-AGNOSTIC negative invariant (ALWAYS enforced, Claude AND Codex).

    Raises ``ApiKeyForbidden`` if a raw ``ANTHROPIC_API_KEY`` OR ``OPENAI_API_KEY``
    is present in ``env``, or if ``--bare`` appears ANYWHERE in ``argv`` (the H40
    foot-gun that forces API-key auth). Returns ``None`` on a clean spawn.

    No runtime/adapter parameter by design (§7): this is the SHARED, immovable
    gate a future Codex adapter fill cannot satisfy by deleting a check.
    """
    for key in _FORBIDDEN_API_KEYS:
        if key in env:
            raise ApiKeyForbidden(
                f"raw API key {key!r} is forbidden — all model usage must ride the "
                "OAuth subscription token (the HARD INVARIANT, §2.11)"
            )
    if _BARE_FLAG in argv:
        raise ApiKeyForbidden(
            f"{_BARE_FLAG!r} in argv is forbidden — it forces ANTHROPIC_API_KEY auth "
            "and breaks the OAuth token (H40)"
        )
    return None


# --------------------------------------------------------------------------------------------------
# Layer 2 — the pane-env isolation guard (closes the tmux-server env-leak hole).
# --------------------------------------------------------------------------------------------------

def _is_env_i_isolated(pane_argv: list[str]) -> bool:
    """True iff ``pane_argv`` begins with the from-empty isolator ``env -i …``.

    ``env -i`` clears the inherited environment and re-adds only the explicit
    vars; it is the load-bearing mechanism that prevents the pane from inheriting
    the tmux SERVER environment (§7, §2.11). The bare ``env <K=V> cmd`` form
    (without ``-i``) AUGMENTS rather than clears, so it is NOT isolation —
    hence we require BOTH the ``env`` token AND the ``-i`` flag immediately after.
    """
    return (
        len(pane_argv) >= 2
        and pane_argv[0] == "env"
        and pane_argv[1] == "-i"
    )


def assert_pane_env_isolated(pane_argv: list[str], server_env: dict) -> None:
    """The pane-layer guard that closes the tmux-server-leak hole.

    Raises ``ApiKeyForbidden`` unless BOTH hold:
      * ``pane_argv`` begins with the from-empty isolator (``env -i …``) — the
        pane environment is built from-empty, NOT inherited from the tmux server.
      * neither ``ANTHROPIC_API_KEY`` nor ``OPENAI_API_KEY`` is present in the tmux
        SERVER environment (``server_env``) — i.e. no key the pane could inherit
        FROM, checking the env the PANE WILL ACTUALLY SEE, not just the prefix.

    Returns ``None`` when the pane is isolated and the server env is clean.
    """
    if not _is_env_i_isolated(pane_argv):
        raise ApiKeyForbidden(
            "pane not from-empty (`env -i …`): it would inherit the tmux SERVER "
            "environment, which may carry a stray API key (§7)"
        )
    for key in _FORBIDDEN_API_KEYS:
        if key in server_env:
            raise ApiKeyForbidden(
                f"raw API key {key!r} is present in the tmux SERVER environment — even "
                "an env-i isolated pane must not be launched from a leaky server (§2.11)"
            )
    return None


# --------------------------------------------------------------------------------------------------
# Layer 3 — the composed adapter call.
# --------------------------------------------------------------------------------------------------

def assert_oauth_only(
    env: dict, argv: list[str], pane_argv: list[str], server_env: dict
) -> None:
    """The single composed gate the adapter calls before ``create_detached``.

    Composes the runtime-agnostic negative invariant (``assert_no_api_key``) with
    the pane-isolation guard (``assert_pane_env_isolated``). Raises
    ``ApiKeyForbidden`` if EITHER half trips; returns ``None`` when fully clean.

    The Claude-specific POSITIVE token check (``check_credential_health``) is NOT
    composed here — it lives in the Claude adapter's path, not the shared gate.
    """
    assert_no_api_key(env, argv)
    assert_pane_env_isolated(pane_argv, server_env)
    return None


# --------------------------------------------------------------------------------------------------
# The Claude-specific POSITIVE credential check.
# --------------------------------------------------------------------------------------------------

def _expired(env: dict) -> bool:
    """Whether the OAuth token in ``env`` is detectably expired.

    v1 FORK: the harness carries the OAuth token as an opaque string with NO
    embedded expiry metadata, so token EXPIRY is not detectable from the env
    alone in v1 — only ABSENCE is. We therefore return ``False`` here (presence
    is treated as healthy). When a token-expiry channel exists (e.g. a sidecar
    expiry timestamp or a refresh-probe), this is the single seam to wire it in;
    the absent-token precondition (DAEMON §7) is already enforced by the caller.
    """
    return False


def check_credential_health(env: dict) -> None:
    """CLAUDE-SPECIFIC positive check — the OAuth token is present (and unexpired).

    Raises ``AuthExpired`` (the DISTINCT spawn-failure class) when
    ``CLAUDE_CODE_OAUTH_TOKEN`` is absent or detectably expired (DAEMON §7, §6.3).
    This is the POSITIVE half ONLY: it must NOT raise merely because the env has
    no api key — that negative concern belongs to ``assert_no_api_key``. Returns
    ``None`` when the token is present.
    """
    if _OAUTH_TOKEN_VAR not in env or _expired(env):
        raise AuthExpired(
            f"{_OAUTH_TOKEN_VAR} absent or expired — refresh the OAuth subscription "
            "token (genesis credential precondition, DAEMON §7). This is a credential "
            "lapse, NOT a fleet-wide model outage (DAEMON §6.3)."
        )
    return None
