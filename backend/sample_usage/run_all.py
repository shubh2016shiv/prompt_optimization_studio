"""
Orchestrated sample workflow (APOST doc §9.1–9.2 mental model)

Runs, in order:
  01_health.py        — process up + kNN corpus flag (main.py lifespan)
  02_gap_analysis.py  — Phase 1: TCRTE pre-score (tcrte_scorer) + gap JSON; writes _last_gap.json
  03_optimize.py      — Phase 3: optimize with gap_data from _last_gap.json; writes _last_optimize.json
  04_chat.py          — context-seeded chat using _last_optimize.json

Set RUN_AUTO=1 to also run an extra /api/optimize with framework=auto inside 03_optimize.py.

From backend directory (same cwd as uvicorn):
  python sample_usage/run_all.py

Prerequisites:
  uvicorn app.main:app --reload --port 8000
  APOST_TEST_API_KEY or provider key in backend/.env
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_DIR = Path(__file__).resolve().parent
_BACKEND = _DIR.parent


def _run(script: str, *args: str) -> None:
    label = " ".join([script, *args])
    print(f"\n{'=' * 60}\n>>> {label}\n{'=' * 60}", flush=True)
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    r = subprocess.run(
        [sys.executable, str(_DIR / script), *args],
        cwd=str(_BACKEND),
        env=env,
        check=False,
    )
    if r.returncode != 0:
        raise SystemExit(r.returncode)


def main() -> int:
    _run("01_health.py")
    _run("02_gap_analysis.py")
    _run("03_optimize.py", str(_DIR / "_last_gap.json"))
    _run("04_chat.py", str(_DIR / "_last_optimize.json"))
    print("\nAll sample_usage steps completed OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
