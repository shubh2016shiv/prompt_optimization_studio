"""
Purpose:
  Validate optimization endpoint behavior and response contract.

Scope:
  - Calls POST /api/optimize with kernel (required) and auto (optional).
  - Verifies three-variant output shape and score fields.

Method:
  - Use centralized scenario data and optional prior gap artifact.
  - Assert analysis, techniques, variant prompts, and TCRTE score blocks.
  - Persist optimized output for downstream chat refinement check.

Artifacts:
  - sample_usage/_last_optimize.json

Run:
  python sample_usage/pipeline_optimize_check.py
  python sample_usage/pipeline_optimize_check.py path/to/gap_response.json
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from sample_runtime import http_json, print_json, require_api_key, test_model_id, test_model_label, test_provider
from healthcare_prompt_scenarios import (
    PIPELINE_CASE_ID,
    PIPELINE_SAMPLE_GAP_ANSWERS,
    get_prompt_case,
)


def _minimal_gap_data() -> dict:
    return {
        "tcrte": {
            "task": {"score": 55, "status": "weak", "note": "stub"},
            "context": {"score": 60, "status": "weak", "note": "stub"},
            "role": {"score": 50, "status": "weak", "note": "stub"},
            "tone": {"score": 45, "status": "weak", "note": "stub"},
            "execution": {"score": 70, "status": "good", "note": "stub"},
        },
        "overall_score": 56,
        "complexity": "medium",
        "complexity_reason": "Multiple structured sections and safety rules.",
        "recommended_techniques": ["XML-Bounding", "CoT-Ensemble"],
        "questions": [],
        "auto_enrichments": [],
    }


def _assert_optimize(data: dict) -> None:
    assert "analysis" in data and isinstance(data["analysis"], dict), data
    a = data["analysis"]
    for k in ("detected_issues", "model_notes", "framework_applied", "coverage_delta"):
        assert k in a, a
    assert isinstance(data.get("techniques_applied"), list), data
    variants = data.get("variants")
    assert isinstance(variants, list) and len(variants) == 3, data
    for v in variants:
        assert isinstance(v, dict), v
        assert v.get("name") in ("Conservative", "Structured", "Advanced"), v
        assert "system_prompt" in v and "user_prompt" in v, v
        ts = v.get("tcrte_scores")
        assert isinstance(ts, dict), v
        for dim in ("task", "context", "role", "tone", "execution"):
            assert dim in ts and isinstance(ts[dim], int), ts


def _one_optimize(*, framework: str, gap_data: dict) -> dict:
    api_key = require_api_key()
    case = get_prompt_case(PIPELINE_CASE_ID)
    body = {
        "raw_prompt": case["raw_prompt"],
        "input_variables": case["input_variables"],
        "task_type": case["task_type"],
        "framework": framework,
        "provider": test_provider(),
        "model_id": test_model_id(),
        "model_label": test_model_label(),
        "is_reasoning_model": False,
        "gap_data": gap_data,
        "answers": PIPELINE_SAMPLE_GAP_ANSWERS,
        "api_key": api_key,
    }
    status, data, raw = http_json("POST", "/api/optimize", json_body=body, timeout=300.0)
    if status != 200:
        raise RuntimeError(f"optimize failed {status}: {raw[:2500]}")
    if not isinstance(data, dict):
        raise RuntimeError(f"Expected JSON object: {raw[:800]}")
    return data


def main() -> int:
    gap_data: dict
    if len(sys.argv) > 1:
        p = Path(sys.argv[1])
        gap_data = json.loads(p.read_text(encoding="utf-8"))
    else:
        gap_data = _minimal_gap_data()

    try:
        res_kernel = _one_optimize(framework="kernel", gap_data=gap_data)
        _assert_optimize(res_kernel)
    except (RuntimeError, AssertionError) as e:
        print(f"kernel optimize failed: {e}", file=sys.stderr)
        return 1
    print("OK /api/optimize (framework=kernel) - variants:", [v["name"] for v in res_kernel["variants"]])

    art = Path(__file__).resolve().parent / "_last_optimize.json"
    art.write_text(json.dumps(res_kernel, indent=2), encoding="utf-8")
    print("Wrote", art)

    if os.environ.get("RUN_AUTO", "").strip() in ("1", "true", "yes"):
        try:
            res_auto = _one_optimize(framework="auto", gap_data=gap_data)
            _assert_optimize(res_auto)
            print_json("auto-select analysis", res_auto.get("analysis"))
        except (RuntimeError, AssertionError) as e:
            print(f"auto optimize failed: {e}", file=sys.stderr)
            return 1
        print("OK /api/optimize (framework=auto)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

