"""
Purpose:
  Run one fixed optimization framework across the centralized healthcare scenario bank
  to produce transparent, comparable artifacts for prompt inspection.

Scope:
  - Executes POST /api/optimize for 10 healthcare scenarios.
  - Captures framework-level and variant-level metadata.
  - Supports all registered framework IDs in VALID_FRAMEWORKS.

Method:
  1. Build frontend-like optimize payload per scenario.
  2. Call backend endpoint with selected framework.
  3. Parse response metrics and fallback indicators.
  4. Emit per-scenario markdown + consolidated summary markdown.

Artifacts:
  - sample_usage/prompt_output/<framework>/<timestamp>/<case_id>.md
  - sample_usage/prompt_output/<framework>/<timestamp>/_summary.md

Run:
  Imported and invoked by:
    run_framework_*_suite.py
    run_all_framework_suites.py
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any

import httpx

from sample_runtime import (
    base_url,
    require_api_key,
    test_model_id,
    test_model_label,
    test_provider,
)
from healthcare_prompt_scenarios import PROMPT_CASES, PromptCase


VALID_FRAMEWORKS = (
    "kernel",
    "xml_structured",
    "create",
    "progressive",
    "reasoning_aware",
    "cot_ensemble",
    "tcrte",
    "textgrad",
)


def _now_timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _quality_gate_mode() -> str:
    return os.environ.get("APOST_QUALITY_GATE_MODE", "full").strip() or "full"


def _is_reasoning_model() -> bool:
    val = os.environ.get("APOST_IS_REASONING_MODEL", "").strip().lower()
    return val in {"1", "true", "yes", "y"}


def _minimal_gap_data(case: PromptCase) -> dict[str, Any]:
    complexity = case["complexity"]
    overall_score = 48 if complexity == "complex" else (62 if complexity == "medium" else 72)
    return {
        "overall_score": overall_score,
        "complexity": complexity,
        "complexity_reason": f"Synthetic sample complexity: {complexity}",
        "recommended_techniques": ["XML-Bounding", "CoT-Ensemble", "Constraint Scaffolding"],
        "questions": [],
        "auto_enrichments": [],
    }


def _request_body(case: PromptCase, framework: str, api_key: str) -> dict[str, Any]:
    return {
        "raw_prompt": case["raw_prompt"],
        "input_variables": case["input_variables"],
        "task_type": case["task_type"],
        "framework": framework,
        "quality_gate_mode": _quality_gate_mode(),
        "provider": test_provider(),
        "model_id": test_model_id(),
        "model_label": test_model_label(),
        "is_reasoning_model": _is_reasoning_model(),
        "gap_data": _minimal_gap_data(case),
        "answers": {
            "audience": "Licensed clinicians and clinical operations stakeholders.",
            "strictness": "Prefer conservative language and explicit uncertainty handling.",
        },
        "api_key": api_key,
    }


def _safe_avg_quality(variants: list[dict[str, Any]]) -> float | None:
    scores: list[int] = []
    for variant in variants:
        qe = variant.get("quality_evaluation")
        if isinstance(qe, dict) and isinstance(qe.get("overall_score"), int):
            scores.append(qe["overall_score"])
    if not scores:
        return None
    return round(mean(scores), 2)


def _post_optimize(body: dict[str, Any], timeout: float = 420.0) -> tuple[int, dict[str, Any] | None, str]:
    url = f"{base_url()}/api/optimize"
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(url, json=body)
    except httpx.RequestError as request_error:
        return 0, None, f"Connection error while calling {url}: {request_error}"

    raw = response.text
    try:
        data = response.json()
    except ValueError:
        data = None

    if isinstance(data, dict):
        return response.status_code, data, raw
    return response.status_code, None, raw


def _write_case_markdown(
    output_dir: Path,
    framework: str,
    case: PromptCase,
    response_data: dict[str, Any] | None,
    error_text: str | None,
) -> None:
    md_path = output_dir / f"{case['id']}.md"
    lines: list[str] = []
    lines.append(f"# {case['title']}")
    lines.append("")
    lines.append(f"- Case ID: `{case['id']}`")
    lines.append(f"- Framework Requested: `{framework}`")
    lines.append(f"- Task Type: `{case['task_type']}`")
    lines.append(f"- Complexity: `{case['complexity']}`")
    lines.append(f"- Quality Gate Mode: `{_quality_gate_mode()}`")
    lines.append(f"- Provider/Model: `{test_provider()}` / `{test_model_id()}`")
    lines.append("")
    lines.append("## Raw Prompt")
    lines.append("")
    lines.append("```text")
    lines.append(case["raw_prompt"])
    lines.append("```")
    lines.append("")
    lines.append("## Input Variables")
    lines.append("")
    lines.append("```text")
    lines.append(case["input_variables"])
    lines.append("```")
    lines.append("")

    if error_text:
        lines.append("## Result")
        lines.append("")
        lines.append("```text")
        lines.append(error_text)
        lines.append("```")
        lines.append("")
        md_path.write_text("\n".join(lines), encoding="utf-8")
        return

    assert response_data is not None
    analysis = response_data.get("analysis", {})
    variants = response_data.get("variants", [])

    lines.append("## Analysis")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(analysis, indent=2, ensure_ascii=False))
    lines.append("```")
    lines.append("")
    lines.append("## Techniques Applied")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(response_data.get("techniques_applied", []), indent=2, ensure_ascii=False))
    lines.append("```")
    lines.append("")

    for idx, variant in enumerate(variants, start=1):
        lines.append(f"## Variant {idx}: {variant.get('name', 'Unknown')}")
        lines.append("")
        lines.append(f"- Strategy: `{variant.get('strategy', '')}`")
        lines.append(f"- Token Estimate: `{variant.get('token_estimate', 'n/a')}`")
        lines.append(f"- TCRTE Score Source: `{variant.get('tcrte_scores_source', 'n/a')}`")
        lines.append(f"- Quality Score Source: `{variant.get('quality_scores_source', 'n/a')}`")
        lines.append("")
        lines.append("### TCRTE Scores")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(variant.get("tcrte_scores", {}), indent=2, ensure_ascii=False))
        lines.append("```")
        lines.append("")

        quality_eval = variant.get("quality_evaluation")
        lines.append("### Quality Evaluation")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(quality_eval, indent=2, ensure_ascii=False))
        lines.append("```")
        lines.append("")

        lines.append("### System Prompt")
        lines.append("")
        lines.append("```text")
        lines.append(variant.get("system_prompt", ""))
        lines.append("```")
        lines.append("")
        lines.append("### User Prompt")
        lines.append("")
        lines.append("```text")
        lines.append(variant.get("user_prompt", ""))
        lines.append("```")
        lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8")


def _write_summary_markdown(
    output_dir: Path,
    framework: str,
    run_timestamp: str,
    rows: list[dict[str, Any]],
) -> None:
    summary_path = output_dir / "_summary.md"
    lines: list[str] = []
    lines.append(f"# Framework Run Summary: `{framework}`")
    lines.append("")
    lines.append(f"- Timestamp: `{run_timestamp}`")
    lines.append(f"- Total Cases: `{len(rows)}`")
    lines.append(f"- Quality Gate Mode: `{_quality_gate_mode()}`")
    lines.append(f"- Provider/Model: `{test_provider()}` / `{test_model_id()}`")
    lines.append("")
    lines.append("| Case ID | Status | Applied Framework | Variants | Avg Quality | Fallback Variants |")
    lines.append("|---|---|---|---:|---:|---:|")
    for row in rows:
        lines.append(
            f"| {row['case_id']} | {row['status']} | {row['applied_framework']} | "
            f"{row['variant_count']} | {row['avg_quality']} | {row['fallback_variants']} |"
        )
    lines.append("")
    summary_path.write_text("\n".join(lines), encoding="utf-8")


def run_framework_transparency_harness(framework: str) -> int:
    if framework not in VALID_FRAMEWORKS:
        print(f"Unsupported framework: {framework}")
        print(f"Valid values: {', '.join(VALID_FRAMEWORKS)}")
        return 2

    api_key = require_api_key()
    run_timestamp = _now_timestamp()
    output_dir = (
        Path(__file__).resolve().parent
        / "prompt_output"
        / framework
        / run_timestamp
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Running framework='{framework}' across {len(PROMPT_CASES)} healthcare prompt cases")
    print(f"Output dir: {output_dir}")
    print(f"quality_gate_mode={_quality_gate_mode()}, provider={test_provider()}, model={test_model_id()}")

    rows: list[dict[str, Any]] = []
    ok_count = 0
    fail_count = 0

    for index, case in enumerate(PROMPT_CASES, start=1):
        body = _request_body(case, framework, api_key)
        status, data, raw = _post_optimize(body, timeout=420.0)

        if status != 200 or not isinstance(data, dict):
            fail_count += 1
            error_text = f"HTTP {status}\n{raw[:8000]}"
            rows.append(
                {
                    "case_id": case["id"],
                    "status": "FAILED",
                    "applied_framework": "n/a",
                    "variant_count": 0,
                    "avg_quality": "n/a",
                    "fallback_variants": 0,
                }
            )
            _write_case_markdown(output_dir, framework, case, None, error_text)
            print(f"[{index:02d}/{len(PROMPT_CASES)}] {case['id']}: FAILED (HTTP {status})")
            continue

        ok_count += 1
        variants = data.get("variants", []) if isinstance(data.get("variants"), list) else []
        analysis = data.get("analysis", {}) if isinstance(data.get("analysis"), dict) else {}
        applied_framework = str(analysis.get("framework_applied", "n/a"))
        avg_quality = _safe_avg_quality(variants)
        fallback_variants = sum(
            1
            for variant in variants
            if isinstance(variant.get("quality_evaluation"), dict)
            and bool(variant["quality_evaluation"].get("was_fallback"))
        )
        avg_quality_text = f"{avg_quality:.2f}" if avg_quality is not None else "n/a"
        rows.append(
            {
                "case_id": case["id"],
                "status": "OK",
                "applied_framework": applied_framework,
                "variant_count": len(variants),
                "avg_quality": avg_quality_text,
                "fallback_variants": fallback_variants,
            }
        )
        _write_case_markdown(output_dir, framework, case, data, None)
        print(
            f"[{index:02d}/{len(PROMPT_CASES)}] {case['id']}: "
            f"OK | applied={applied_framework} | variants={len(variants)} | "
            f"avg_quality={avg_quality_text} | fallback_variants={fallback_variants}"
        )

    _write_summary_markdown(output_dir, framework, run_timestamp, rows)
    print("-" * 100)
    print(
        f"Completed framework='{framework}': "
        f"success={ok_count}, failed={fail_count}, total={len(PROMPT_CASES)}"
    )
    print(f"Full markdown outputs written to: {output_dir}")
    print(f"Run summary markdown: {output_dir / '_summary.md'}")

    return 0 if fail_count == 0 else 1


