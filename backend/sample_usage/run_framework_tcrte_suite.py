"""
Purpose:
  Execute the isolated transparency suite for the 'tcrte' framework.

Scope:
  - Runs the framework against all centralized healthcare scenarios.
  - Captures per-scenario success/failure and evaluation summaries.

Method:
  - Delegates execution to run_framework_transparency_harness('tcrte').

Artifacts:
  - sample_usage/prompt_output/tcrte/<timestamp>/<case_id>.md
  - sample_usage/prompt_output/tcrte/<timestamp>/_summary.md

Run:
  python sample_usage/run_framework_tcrte_suite.py
"""

from framework_transparency_harness import run_framework_transparency_harness


if __name__ == "__main__":
    raise SystemExit(run_framework_transparency_harness("tcrte"))

