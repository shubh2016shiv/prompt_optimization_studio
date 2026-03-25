"""
Step 2 — Phase 1 (doc §7.2): POST /api/gap-analysis

Pipeline stitch:
  1) app.api.routes.gap_analysis runs score_tcrte (tcrte_scorer.py) in parallel with
     the first prompt build — deterministic OpenAI nano scores when the key works.
  2) build_gap_analysis_prompt injects those scores as GROUND TRUTH (gap_analysis_builder).
  3) Your chosen provider/model runs the meta-prompt; JSON is parsed via json_extractor.
  4) Pre-computed dimension scores are merged into the "tcrte" object in the route.

Expectations (GapAnalysisResponse in app.models.responses):
  - tcrte.{task,context,role,tone,execution} each have score, status, note
  - overall_score, complexity, questions[], recommended_techniques[], auto_enrichments[]

Run:
  python sample_usage/02_gap_analysis.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from common import http_json, require_api_key, test_model_id, test_model_label, test_provider
from fixtures_healthcare import INPUT_VARIABLES, RAW_PROMPT, TASK_TYPE


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

    # Step 1: Build request mirroring the frontend gap-analysis payload.
    body = {
        "raw_prompt": RAW_PROMPT,
        "input_variables": INPUT_VARIABLES,
        "task_type": TASK_TYPE,
        "provider": test_provider(),
        "model_id": test_model_id(),
        "model_label": test_model_label(),
        "is_reasoning_model": False,
        "api_key": api_key,
    }

    # Step 2: POST — LLM latency can be high on first call.
    status, data, raw = http_json("POST", "/api/gap-analysis", json_body=body, timeout=180.0)
    if status != 200:
        print(f"gap-analysis failed {status}: {raw[:2000]}", file=sys.stderr)
        return 1
    if not isinstance(data, dict):
        print(f"Expected JSON object, got: {raw[:500]}", file=sys.stderr)
        return 1

    # Step 3: Validate shape — if this passes, the backend + response_model align.
    try:
        _assert_gap_payload(data)
    except AssertionError as e:
        print(f"Schema assertion failed: {e}", file=sys.stderr)
        return 1

    print("OK /api/gap-analysis - top-level keys:", list(data.keys()))

    # Artifact for run_all.py / manual re-runs of optimize + chat with the same gap output.
    out = Path(__file__).resolve().parent / "_last_gap.json"
    out.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print("Wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
