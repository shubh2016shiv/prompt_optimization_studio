"""
Purpose:
  Execute the core API pipeline smoke tests in one command.

Scope:
  - Runs health, gap analysis, optimize, and chat pipeline scripts sequentially.
  - Fails fast on first regression.

Method:
  - Launch each check as a subprocess from backend cwd.
  - Reuse generated pipeline artifacts between steps.

Artifacts:
  - sample_usage/_last_gap.json
  - sample_usage/_last_optimize.json

Run:
  python sample_usage/run_pipeline_smoke_suite.py
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
    print(f"\n{'=' * 70}\n>>> {label}\n{'=' * 70}", flush=True)
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    result = subprocess.run(
        [sys.executable, str(_DIR / script), *args],
        cwd=str(_BACKEND),
        env=env,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main() -> int:
    _run("smoke_healthcheck.py")
    _run("pipeline_gap_analysis_check.py")
    _run("pipeline_optimize_check.py", str(_DIR / "_last_gap.json"))
    _run("pipeline_chat_refinement_check.py", str(_DIR / "_last_optimize.json"))
    print("\nPipeline smoke suite completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

