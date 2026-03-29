"""
Purpose:
  Validate chat refinement endpoint behavior with context-rich payloads.

Scope:
  - Calls POST /api/chat.
  - Verifies assistant message contract and non-empty response content.

Method:
  - Build frontend-like chat context using scenario + optimize artifacts.
  - Send targeted prompt-refinement instruction.
  - Assert role/content response fields.

Artifacts:
  - Console output only.

Run:
  python sample_usage/pipeline_chat_refinement_check.py
  python sample_usage/pipeline_chat_refinement_check.py path/to/optimize_response.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from sample_runtime import http_json, require_api_key, test_model_id, test_provider
from healthcare_prompt_scenarios import (
    PIPELINE_CASE_ID,
    PIPELINE_SAMPLE_GAP_ANSWERS,
    get_prompt_case,
)


def _minimal_result() -> dict:
    return {
        "analysis": {
            "detected_issues": ["stub"],
            "model_notes": "stub",
            "framework_applied": "kernel",
            "coverage_delta": "stub",
        },
        "techniques_applied": ["KERNEL"],
        "variants": [
            {
                "id": 1,
                "name": "Conservative",
                "strategy": "stub",
                "system_prompt": "stub system",
                "user_prompt": "stub user",
                "token_estimate": 10,
                "tcrte_scores": {"task": 0, "context": 0, "role": 0, "tone": 0, "execution": 0},
                "strengths": [],
                "best_for": "stub",
                "overshoot_guards": [],
                "undershoot_guards": [],
            },
            {
                "id": 2,
                "name": "Structured",
                "strategy": "stub",
                "system_prompt": "stub system 2",
                "user_prompt": "stub user 2",
                "token_estimate": 10,
                "tcrte_scores": {"task": 0, "context": 0, "role": 0, "tone": 0, "execution": 0},
                "strengths": [],
                "best_for": "stub",
                "overshoot_guards": [],
                "undershoot_guards": [],
            },
            {
                "id": 3,
                "name": "Advanced",
                "strategy": "stub",
                "system_prompt": "stub system 3",
                "user_prompt": "stub user 3",
                "token_estimate": 10,
                "tcrte_scores": {"task": 0, "context": 0, "role": 0, "tone": 0, "execution": 0},
                "strengths": [],
                "best_for": "stub",
                "overshoot_guards": [],
                "undershoot_guards": [],
            },
        ],
    }


def _minimal_gap() -> dict:
    return {
        "tcrte": {
            "task": {"score": 50, "status": "weak", "note": "stub"},
            "context": {"score": 50, "status": "weak", "note": "stub"},
            "role": {"score": 50, "status": "weak", "note": "stub"},
            "tone": {"score": 50, "status": "weak", "note": "stub"},
            "execution": {"score": 50, "status": "weak", "note": "stub"},
        },
        "overall_score": 50,
        "complexity": "medium",
        "complexity_reason": "stub",
        "recommended_techniques": [],
        "questions": [],
        "auto_enrichments": [],
    }


def main() -> int:
    api_key = require_api_key()
    case = get_prompt_case(PIPELINE_CASE_ID)

    result: dict
    if len(sys.argv) > 1:
        result = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    else:
        result = _minimal_result()

    gap_data = _minimal_gap()

    context = {
        "raw_prompt": case["raw_prompt"],
        "variables": case["input_variables"],
        "framework": "kernel",
        "task_type": case["task_type"],
        "provider": test_provider(),
        "model": {"id": test_model_id(), "label": test_model_id(), "reasoning": False},
        "is_reasoning": False,
        "gap_data": gap_data,
        "answers": PIPELINE_SAMPLE_GAP_ANSWERS,
        "result": result,
    }

    body = {
        "message": (
            "For Variant 2 (Structured), tighten instructions so every lab row must "
            "echo the exact LOINC code from input, and add one bullet on formulary "
            "tier conflict handling. Keep JSON-only output requirement."
        ),
        "history": [],
        "context": context,
        "provider": test_provider(),
        "model_id": test_model_id(),
        "api_key": api_key,
    }

    status, data, raw = http_json("POST", "/api/chat", json_body=body, timeout=180.0)
    if status != 200:
        print(f"chat failed {status}: {raw[:2000]}", file=sys.stderr)
        return 1
    if not isinstance(data, dict):
        print(f"Expected JSON object: {raw[:800]}", file=sys.stderr)
        return 1

    msg = data.get("message")
    assert isinstance(msg, dict), data
    assert msg.get("role") == "assistant", msg
    content = (msg.get("content") or "").strip()
    assert len(content) > 0, msg

    print("OK /api/chat - assistant reply (preview):", content[:400] + ("..." if len(content) > 400 else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

