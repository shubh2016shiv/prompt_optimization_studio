"""
Purpose:
  Validate the gap-analysis endpoint contract using a realistic healthcare scenario.

Scope:
  - Calls POST /api/gap-analysis.
  - Verifies TCRTE blocks, complexity, and recommendation fields.

Method:
  - Build frontend-like request payload from centralized scenario data.
  - Assert response shape and type constraints.
  - Persist response for downstream pipeline checks.

Artifacts:
  - sample_usage/_last_gap.json

Run:
  python sample_usage/pipeline_gap_analysis_check.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from sample_runtime import http_json, require_api_key, test_model_id, test_model_label, test_provider
from healthcare_prompt_scenarios import PIPELINE_CASE_ID, get_prompt_case


def _assert_gap_payload(data: dict) -> None:
    assert "tcrte" in data, data
    t = data["tcrte"]
    for dim in ("task", "context", "role", "tone", "execution"):
        assert dim in t, (dim, data)
        block = t[dim]
        assert isinstance(block, dict), block
        assert "score" in block and "status" in block and "note" in block, block
    assert isinstance(data.get("overall_score"), int), data
    assert data.get("complexity") in ("simple", "medium", "complex"), data
    assert isinstance(data.get("questions"), list) and len(data["questions"]) >= 1, data
    assert isinstance(data.get("recommended_techniques"), list), data
    assert isinstance(data.get("auto_enrichments"), list), data


def main() -> int:
    api_key = require_api_key()
    case = get_prompt_case(PIPELINE_CASE_ID)

    body = {
        "raw_prompt": case["raw_prompt"],
        "input_variables": case["input_variables"],
        "task_type": case["task_type"],
        "provider": test_provider(),
        "model_id": test_model_id(),
        "model_label": test_model_label(),
        "is_reasoning_model": False,
        "api_key": api_key,
    }

    status, data, raw = http_json("POST", "/api/gap-analysis", json_body=body, timeout=180.0)
    if status != 200:
        print(f"gap-analysis failed {status}: {raw[:2000]}", file=sys.stderr)
        return 1
    if not isinstance(data, dict):
        print(f"Expected JSON object, got: {raw[:500]}", file=sys.stderr)
        return 1

    try:
        _assert_gap_payload(data)
    except AssertionError as e:
        print(f"Schema assertion failed: {e}", file=sys.stderr)
        return 1

    print("OK /api/gap-analysis - top-level keys:", list(data.keys()))

    out = Path(__file__).resolve().parent / "_last_gap.json"
    out.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print("Wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

