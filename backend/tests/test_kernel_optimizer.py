"""Unit tests for deep KERNEL optimizer implementation."""

import pytest

from app.models.requests import OptimizationRequest
from app.services.optimization.frameworks.kernel_optimizer import KernelOptimizer


def _build_request() -> OptimizationRequest:
    return OptimizationRequest(
        raw_prompt="Analyze the input and produce structured output.",
        input_variables="{{records}} - array of records",
        task_type="analysis",
        framework="kernel",
        provider="openai",
        model_id="gpt-4.1-mini",
        model_label="GPT-4.1 Mini",
        is_reasoning_model=False,
        api_key="test-api-key",
        quality_gate_mode="off",
        gap_data={"overall_score": 52},
        answers={"What is the scope?": "Only evaluate the provided records."},
    )


@pytest.mark.asyncio
async def test_kernel_generate_variants_runs_deep_rewrite(monkeypatch):
    optimizer = KernelOptimizer()
    request = _build_request()

    async def fake_parse_kernel_components(**kwargs):
        return {
            "task": "Evaluate records and return risk summary.",
            "context": "Only use provided records.",
            "positive_constraints": ["Return deterministic output"],
            "negative_constraints": ["Do not hallucinate fields"],
            "success_criteria": ["All records are covered"],
            "output_format": "JSON with summary and findings",
        }

    async def fake_rewrite_with_kernel_objective(*, objective, **kwargs):
        if "simple" in objective:
            return "Conservative rewritten prompt"
        if "MUST/MUST NOT" in objective:
            return "Structured rewritten prompt"
        return "Advanced rewritten prompt"

    monkeypatch.setattr(optimizer, "_parse_kernel_components", fake_parse_kernel_components)
    monkeypatch.setattr(optimizer, "_rewrite_with_kernel_objective", fake_rewrite_with_kernel_objective)

    response = await optimizer.generate_variants(request=request)

    assert response.analysis.framework_applied == "kernel"
    assert [variant.name for variant in response.variants] == ["Conservative", "Structured", "Advanced"]
    assert response.variants[0].system_prompt.startswith("Conservative rewritten prompt")
    assert "{{records}}" in response.variants[0].system_prompt
    assert response.run_metadata is not None
    assert response.run_metadata.framework == "kernel"


@pytest.mark.asyncio
async def test_kernel_rewrite_fallback_used_on_failure(monkeypatch):
    optimizer = KernelOptimizer()
    request = _build_request()

    async def fake_parse_kernel_components(**kwargs):
        return {
            "task": "Extract final answer.",
            "context": "Only data in prompt.",
            "positive_constraints": ["Follow schema"],
            "negative_constraints": ["No unsupported claims"],
            "success_criteria": ["Valid schema"],
            "output_format": "JSON",
        }

    async def fake_rewrite_with_kernel_objective(*, objective, **kwargs):
        if "validation" in objective:
            raise RuntimeError("rewrite failed")
        return "normal rewrite"

    monkeypatch.setattr(optimizer, "_parse_kernel_components", fake_parse_kernel_components)
    monkeypatch.setattr(optimizer, "_rewrite_with_kernel_objective", fake_rewrite_with_kernel_objective)

    response = await optimizer.generate_variants(request=request)

    assert response.analysis.framework_applied == "kernel"
    assert "Validation Guard" in response.variants[2].system_prompt