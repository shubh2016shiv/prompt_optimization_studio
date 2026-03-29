import json

import pytest

from app.models.requests import OptimizationRequest
from app.services.optimization.frameworks.reasoning_aware_optimizer import (
    ReasoningAwareOptimizer,
)
from app.services.optimization.frameworks.tcrte_coverage_optimizer import (
    TcrteCoverageOptimizer,
)


def _build_request(*, framework: str) -> OptimizationRequest:
    return OptimizationRequest(
        raw_prompt="Analyze the input and produce structured output.",
        task_type="analysis",
        framework=framework,
        provider="openai",
        model_id="gpt-4.1-nano",
        model_label="GPT-4.1 Nano",
        is_reasoning_model=False,
        api_key="test-key",
        quality_gate_mode="off",
    )


@pytest.mark.asyncio
async def test_reasoning_aware_repairs_malformed_json_and_normalizes_fields(monkeypatch):
    malformed_response = """{
  "absolute_task": "Identify trends",
  "hard_constraints": ["Return valid JSON"],
  "output_format": "{
    \\"concerning_trends\\": []
  }"
}"""
    repaired_response = json.dumps(
        {
            "absolute_task": "Identify trends",
            "hard_constraints": "- Return valid JSON\n- No diagnosis",
            "output_format": {"concerning_trends": []},
        }
    )
    call_payloads: list[dict] = []

    async def fake_call(self, **kwargs):
        call_payloads.append(kwargs)
        if len(call_payloads) == 1:
            return malformed_response
        return repaired_response

    monkeypatch.setattr("app.services.llm_client.LLMClient.call", fake_call)

    optimizer = ReasoningAwareOptimizer()
    response = await optimizer.generate_variants(request=_build_request(framework="reasoning_aware"))

    assert len(call_payloads) == 2
    assert call_payloads[0]["response_format"]["type"] == "json_schema"
    assert response.analysis.framework_applied == "reasoning_aware"
    assert response.variants[0].system_prompt.count("- Return valid JSON") == 1
    assert '"concerning_trends": []' in response.variants[0].system_prompt


@pytest.mark.asyncio
async def test_tcrte_handles_top_level_array_payload_without_crashing(monkeypatch):
    array_payload = json.dumps(
        [
            {
                "task_section": "Task content",
                "context_section": "Context content",
                "role_section": "Role content",
                "tone_section": "Tone content",
                "execution_section": "Execution content",
                "constraints": ["Constraint A", "Constraint B"],
                "critical_context_for_core": "Critical context",
            }
        ]
    )
    call_payloads: list[dict] = []

    async def fake_call(self, **kwargs):
        call_payloads.append(kwargs)
        return array_payload

    monkeypatch.setattr("app.services.llm_client.LLMClient.call", fake_call)

    optimizer = TcrteCoverageOptimizer()
    request = _build_request(framework="tcrte")
    request.gap_data = {"overall_score": 30}
    response = await optimizer.generate_variants(request=request)

    assert len(call_payloads) == 1
    assert call_payloads[0]["response_format"]["type"] == "json_schema"
    assert response.analysis.framework_applied == "tcrte"
    assert "Constraint A" in response.variants[1].system_prompt
