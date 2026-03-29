"""
Purpose:
  Execute all framework transparency suites over centralized healthcare scenarios.

Scope:
  - Iterates through every framework in VALID_FRAMEWORKS.
  - Aggregates per-framework pass/fail exit behavior.

Method:
  - Invoke run_framework_transparency_harness for each framework id.
  - Continue through all frameworks; return non-zero if any suite fails.

Artifacts:
  - sample_usage/prompt_output/<framework>/<timestamp>/...

Run:
  python sample_usage/run_all_framework_suites.py
"""

from __future__ import annotations

from framework_transparency_harness import VALID_FRAMEWORKS, run_framework_transparency_harness


def main() -> int:
    exit_code = 0
    for framework in VALID_FRAMEWORKS:
        print("\n" + "=" * 100)
        print(f"FRAMEWORK RUN START: {framework}")
        print("=" * 100)
        rc = run_framework_transparency_harness(framework)
        if rc != 0:
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())

