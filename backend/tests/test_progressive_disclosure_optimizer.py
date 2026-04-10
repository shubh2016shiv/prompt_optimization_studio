"""Unit tests for deep Progressive Disclosure optimizer implementation."""

import pytest

from app.models.requests import OptimizationRequest
from app.services.optimization.frameworks.progressive_disclosure_optimizer import (
    ProgressiveDisclosureOptimizer,
)


def _build_request() -> OptimizationRequest:
    return OptimizationRequest(
        raw_prompt="Route the request to the right workflow and produce a structured result.",
        input_variables="{{request_payload}} - user task payload",
        task_type="analysis",
        framework="progressive",
        provider="openai",
        model_id="gpt-4.1-mini",
        model_label="GPT-4.1 Mini",
        is_reasoning_model=False,
        api_key="test-api-key",
        quality_gate_mode="off",
        gap_data={"overall_score": 51},
        answers={"How should conflicts be handled?": "Prioritize safety and explicit constraints."},
    )


@pytest.mark.asyncio
async def test_progressive_generate_variants_runs_deep_rewrite(monkeypatch):
    optimizer = ProgressiveDisclosureOptimizer()
    request = _build_request()

    async def fake_parse_progressive_blueprint(**kwargs):
        return {
            "discovery_metadata": ["Capability: classify and route tasks."],
            "activation_rules": [
                {
                    "trigger": "If request asks for analysis",
                    "action": "Use analysis workflow",
                    "priority": "high",
                }
            ],
            "execution_logic": ["Validate input", "Run workflow", "Return result"],
            "output_format": "JSON",
            "safety_bounds": ["Do not invent unsupported facts"],
            "failure_modes": ["Do not skip trigger checks"],
        }

    async def fake_rewrite_with_progressive_objective(*, objective, **kwargs):
        if "separation of discovery" in objective:
            return "Conservative rewritten progressive prompt"
        if "trigger-to-action determinism" in objective:
            return "Structured rewritten progressive prompt"
        return "Advanced rewritten progressive prompt"

    monkeypatch.setattr(optimizer, "_parse_progressive_blueprint", fake_parse_progressive_blueprint)
    monkeypatch.setattr(optimizer, "_rewrite_with_progressive_objective", fake_rewrite_with_progressive_objective)

    response = await optimizer.generate_variants(request=request)

    assert response.analysis.framework_applied == "progressive"
    assert [variant.name for variant in response.variants] == ["Conservative", "Structured", "Advanced"]
    assert response.variants[0].system_prompt.startswith("Conservative rewritten progressive prompt")
    assert "{{request_payload}}" in response.variants[0].system_prompt
    assert response.run_metadata is not None
    assert response.run_metadata.framework == "progressive"


@pytest.mark.asyncio
async def test_progressive_rewrite_fallback_used_on_failure(monkeypatch):
    optimizer = ProgressiveDisclosureOptimizer()
    request = _build_request()

    async def fake_parse_progressive_blueprint(**kwargs):
        return {
            "discovery_metadata": ["Capability discovery"],
            "activation_rules": [
                {
                    "trigger": "If missing data",
                    "action": "Ask for clarification",
                    "priority": "critical",
                }
            ],
            "execution_logic": ["Check inputs", "Execute", "Verify output"],
            "output_format": "JSON",
            "safety_bounds": ["Never hallucinate"],
            "failure_modes": ["Avoid blending activation and execution"],
        }

    async def fake_rewrite_with_progressive_objective(*, objective, **kwargs):
        if "conflict-resolution" in objective:
            raise RuntimeError("rewrite failed")
        return "normal rewrite"

    monkeypatch.setattr(optimizer, "_parse_progressive_blueprint", fake_parse_progressive_blueprint)
    monkeypatch.setattr(optimizer, "_rewrite_with_progressive_objective", fake_rewrite_with_progressive_objective)

    response = await optimizer.generate_variants(request=request)

    assert response.analysis.framework_applied == "progressive"
    assert "ESCALATION GUARD" in response.variants[2].system_prompt
