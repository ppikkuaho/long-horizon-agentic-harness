"""codex — the Codex RuntimeAdapter PORT, UNDERSPECIFIED/owed (IMPLEMENTATION-PLAN §2.11; DAEMON §6.3).

The Codex runtime (L5, GPT-5.5 per runtime-and-model-map E32) is the spec-anchored execution
seat — but its adapter port is OWED, pending the Codex audit. v1 ships a STUB, not a silent
fallback: ``pin_and_open`` raises a deterministic ``NotImplementedError("adapter port to be
supplied")`` so a missing Codex fill fails LOUD (no substitute model, no best-effort, no
API-key fallback).

THE SHARED NEGATIVE INVARIANT survives the stub: BEFORE raising the not-implemented error, the
stub asserts the OAuth-only invariant — no raw ``OPENAI_API_KEY`` (the Codex twin of
ANTHROPIC_API_KEY). This is the runtime-AGNOSTIC gate the future Codex fill CANNOT delete to make
itself pass: an OPENAI key in env trips the gate here, today, even though the rest of the port is
unbuilt. So "no raw API key, ever" is true by construction for Codex from this increment on.
"""

from __future__ import annotations

from harnessd.spawn import oauth_guard

from .base import RuntimeAdapter


class CodexAdapter(RuntimeAdapter):
    """The owed Codex port — a fail-loud stub that still enforces the OAuth-only negative gate."""

    def pin_and_open(self, neutral_brief, level_config, tmux_target, env) -> "object":
        """Assert no raw OPENAI key, then raise the deterministic "adapter port to be supplied".

        The negative invariant fires FIRST (an OPENAI_API_KEY in env raises ApiKeyForbidden — the
        shared gate the unbuilt fill cannot delete). With a clean env the stub raises
        ``NotImplementedError`` so the owed port surfaces as an explicit gap, never a silent
        fallback to an API key or a substitute model (DAEMON §6.3).
        """
        # The runtime-AGNOSTIC negative invariant (no raw API key) — enforced even by the stub.
        oauth_guard.assert_no_api_key(env or {}, [])
        raise NotImplementedError(
            "Codex adapter port to be supplied — the L5 Codex runtime adapter is owed pending the "
            "Codex audit (DAEMON §6.3). v1 refuses to spawn rather than silently fall back to a "
            "raw API key or a substitute model (no-silent-fallback + OAuth-only by construction)."
        )
