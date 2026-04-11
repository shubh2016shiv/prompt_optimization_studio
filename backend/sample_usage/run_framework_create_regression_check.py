"""
Purpose:
  Run a focused CREATE regression check against the two healthcare scenarios that
  previously exposed meta-framework leakage and degraded quality scoring.

Scope:
  - Executes POST /api/optimize for hc_05_prior_auth and hc_10_rule_validation.
  - Verifies variants stay task-facing rather than drifting into CREATE-internal
    analysis language such as anchor extraction or blueprint discussion.
  - Flags quality-evaluation fallbacks because they are likely to create UI surprises.

Run:
  python sample_usage/run_framework_create_regression_check.py
"""

from __future__ import annotations

from healthcare_prompt_scenarios import get_prompt_case
from framework_transparency_harness import _post_optimize, _request_body
from sample_runtime import require_api_key


TARGET_CASE_IDS = ("hc_05_prior_auth", "hc_10_rule_validation")
FORBIDDEN_META_PHRASES = (
    "create framework architect",
    "extract stable create anchors",
    "extract create anchors",
    "blueprint",
)


def _variant_contains_meta_leak(variant: dict) -> str | None:
    system_prompt = str(variant.get("system_prompt", ""))
    lowered = system_prompt.lower()
    for phrase in FORBIDDEN_META_PHRASES:
        if phrase in lowered:
            return phrase
    return None


def main() -> int:
    api_key = require_api_key()
    failures: list[str] = []

    for case_id in TARGET_CASE_IDS:
        case = get_prompt_case(case_id)
        status, data, raw = _post_optimize(_request_body(case, "create", api_key), timeout=420.0)
        if status != 200 or not isinstance(data, dict):
            failures.append(f"{case_id}: HTTP {status} {raw[:300]}")
            continue

        variants = data.get("variants", []) if isinstance(data.get("variants"), list) else []
        print(f"{case_id}: received {len(variants)} variants")
        for index, variant in enumerate(variants, start=1):
            meta_phrase = _variant_contains_meta_leak(variant)
            quality_eval = variant.get("quality_evaluation")
            fallback = bool(isinstance(quality_eval, dict) and quality_eval.get("was_fallback"))

            if meta_phrase:
                failures.append(
                    f"{case_id} variant {index}: meta leakage phrase detected -> {meta_phrase!r}"
                )
            if fallback:
                failures.append(f"{case_id} variant {index}: quality evaluation used fallback scoring")

            print(
                f"  variant {index}: "
                f"fallback={fallback} "
                f"meta_leak={meta_phrase or 'none'}"
            )

    if failures:
        print("\nCREATE regression check FAILED:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("\nCREATE regression check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
