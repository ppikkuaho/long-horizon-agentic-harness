"""Repo-root conftest.

Ensures the flat repo-root `harnessd/` package (IMPLEMENTATION-PLAN §3 module table)
is importable when the suite runs from the repo root without requiring an editable
install. The package layout is flat at the repo root, NOT a src/ layout.
"""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
