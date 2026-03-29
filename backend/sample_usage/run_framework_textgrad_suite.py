"""
Purpose:
  Execute the isolated transparency suite for the 'textgrad' framework.

Scope:
  - Runs the framework against all centralized healthcare scenarios.
  - Captures per-scenario success/failure and evaluation summaries.

Method:
  - Delegates execution to run_framework_transparency_harness('textgrad').

Artifacts:
  - sample_usage/prompt_output/textgrad/<timestamp>/<case_id>.md
  - sample_usage/prompt_output/textgrad/<timestamp>/_summary.md

Run:
  python sample_usage/run_framework_textgrad_suite.py
"""

from framework_transparency_harness import run_framework_transparency_harness


if __name__ == "__main__":
    raise SystemExit(run_framework_transparency_harness("textgrad"))

