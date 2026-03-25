"""
Step 4 — Refinement (doc §7.6–7.7): POST /api/chat

Pipeline stitch:
  - build_chat_system_prompt (chat_system_builder.py) serializes session context:
    raw prompt, framework, task_type, gap_data, optimization variants, answers.
  - chat route trims history to the last 28 messages (same as doc / frontend).
  - LLMClient.call_chat sends provider-specific chat completions.

This script sends a context object shaped like the frontend ChatContext (see
frontend/src/types/chat.types.ts): the assistant can reference gap scores and
variant bodies when answering.

Run:
  python sample_usage/04_chat.py [path/to/optimize_response.json]

Without a file, uses inline minimal context so the chat still runs; with a file,
passes real variants from a prior optimize call.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from common import http_json, require_api_key, test_model_id, test_provider
from fixtures_healthcare import INPUT_VARIABLES, RAW_PROMPT, SAMPLE_GAP_ANSWERS, TASK_TYPE


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

    result: dict
    if len(sys.argv) > 1:
        result = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    else:
        result = _minimal_result()

    gap_data = _minimal_gap()

    # Step 1: Context seeding — mirrors UI passing full session into /api/chat.
    context = {
        "raw_prompt": RAW_PROMPT,
        "variables": INPUT_VARIABLES,
        "framework": "kernel",
        "task_type": TASK_TYPE,
        "provider": test_provider(),
        "model": {"id": test_model_id(), "label": test_model_id(), "reasoning": False},
        "is_reasoning": False,
        "gap_data": gap_data,
        "answers": SAMPLE_GAP_ANSWERS,
        "result": result,
    }

    # Step 2: User message asks for a concrete refinement tied to LOINC / Variant 2.
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
