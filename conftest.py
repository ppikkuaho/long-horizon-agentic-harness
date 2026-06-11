"""Repo-root conftest.

Ensures the flat repo-root `harnessd/` package (IMPLEMENTATION-PLAN §3 module table)
is importable when the suite runs from the repo root without requiring an editable
install. The package layout is flat at the repo root, NOT a src/ layout.
"""

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


@pytest.fixture(autouse=True)
def _restore_spawn_env_seam():
    """Save/restore the chokepoint's module-level SPAWN_ENV seam around every test.

    ``daemon.boot`` binds the runtime's spawn env into ``chokepoint.SPAWN_ENV`` (LT-1). A test
    that drives boot (or binds the seam directly) must not leak that binding into later tests,
    which pin the structural placeholder fallback (the dry-run shape).
    """
    from harnessd.spawn import chokepoint

    prior = chokepoint.SPAWN_ENV
    yield
    chokepoint.SPAWN_ENV = prior
