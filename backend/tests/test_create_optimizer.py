"""Unit tests for deep CREATE optimizer implementation."""

import pytest

from app.models.requests import OptimizationRequest
from app.services.optimization.frameworks.create_optimizer import CreateOptimizer


def _build_request() -> OptimizationRequest:
    return OptimizationRequest(
        raw_prompt="Analyze the records and produce a structured compliance decision.",
        input_variables="{{records}} - list of source records",
        task_type="analysis",
        framework="create",
        provider="openai",
        model_id="gpt-4.1-mini",
        model_label="GPT-4.1 Mini",
        is_reasoning_model=False,
        api_key="test-api-key",
        quality_gate_mode="off",
        gap_data={"overall_score": 49},
        answers={"What should happen if data is missing?": "State what is missing and do not guess."},
    )


@pytest.mark.asyncio
async def test_create_generate_variants_runs_deep_rewrite(monkeypatch):
    optimizer = CreateOptimizer()
    request = _build_request()

    async def fake_parse_create_blueprint(**kwargs):
        return {
            "character": "You are a meticulous compliance reviewer.",
            "request": "Produce a compliance verdict from provided records.",
            "examples": ["Record A -> compliant", "Record B -> non-compliant"],
            "adjustments": ["Use only provided data", "Keep answer deterministic"],
            "type_of_output": "JSON with verdict and evidence",
            "extras": ["State uncertainty when evidence is missing."],
            "forbidden_behaviors": ["Do not invent fields"],
            "verification_checks": ["All required fields present"],
        }

    async def fake_rewrite_with_create_objective(*, objective, **kwargs):
        if "bounded scope" in objective:
            return "Conservative rewritten CREATE prompt"
        if "ordered execution logic" in objective:
            return "Structured rewritten CREATE prompt"
        return "Advanced rewritten CREATE prompt"

    monkeypatch.setattr(optimizer, "_parse_create_blueprint", fake_parse_create_blueprint)
    monkeypatch.setattr(optimizer, "_rewrite_with_create_objective", fake_rewrite_with_create_objective)

    response = await optimizer.generate_variants(request=request)

    assert response.analysis.framework_applied == "create"
    assert [variant.name for variant in response.variants] == ["Conservative", "Structured", "Advanced"]
    assert response.variants[0].system_prompt.startswith("Conservative rewritten CREATE prompt")
    assert "{{records}}" in response.variants[0].system_prompt
    assert response.run_metadata is not None
    assert response.run_metadata.framework == "create"


@pytest.mark.asyncio
async def test_create_rewrite_fallback_used_on_failure(monkeypatch):
    optimizer = CreateOptimizer()
    request = _build_request()

    async def fake_parse_create_blueprint(**kwargs):
        return {
            "character": "You are a strict evaluator.",
            "request": "Extract final answer.",
            "examples": ["Use provided evidence only."],
            "adjustments": ["Follow schema"],
            "type_of_output": "JSON",
            "extras": ["Be explicit about missing context."],
            "forbidden_behaviors": ["Do not hallucinate"],
            "verification_checks": ["Schema is valid"],
        }

    async def fake_rewrite_with_create_objective(*, objective, **kwargs):
        if "failure resistance" in objective:
            raise RuntimeError("rewrite failed")
        return "normal rewrite"

    monkeypatch.setattr(optimizer, "_parse_create_blueprint", fake_parse_create_blueprint)
    monkeypatch.setattr(optimizer, "_rewrite_with_create_objective", fake_rewrite_with_create_objective)

    response = await optimizer.generate_variants(request=request)

    assert response.analysis.framework_applied == "create"
    assert "Validation Guard" in response.variants[2].system_prompt
