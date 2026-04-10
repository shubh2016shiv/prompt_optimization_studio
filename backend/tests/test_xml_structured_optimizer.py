"""Unit tests for deep XML Structured optimizer implementation."""

import pytest

from app.models.requests import OptimizationRequest
from app.services.optimization.frameworks.xml_structured_optimizer import XmlStructuredOptimizer


def _build_request() -> OptimizationRequest:
    return OptimizationRequest(
        raw_prompt="Review documents and return a structured compliance summary.",
        input_variables="{{documents}} - list of source documents",
        task_type="analysis",
        framework="xml_structured",
        provider="openai",
        model_id="gpt-4.1-mini",
        model_label="GPT-4.1 Mini",
        is_reasoning_model=False,
        api_key="test-api-key",
        quality_gate_mode="off",
        gap_data={"overall_score": 47},
        answers={"What should be excluded?": "Exclude unsupported claims."},
    )


@pytest.mark.asyncio
async def test_xml_generate_variants_runs_deep_rewrite(monkeypatch):
    optimizer = XmlStructuredOptimizer()
    request = _build_request()

    async def fake_parse_xml_blueprint(**kwargs):
        return {
            "objective": "Return compliant summary from provided documents.",
            "instruction_hierarchy": [
                {
                    "node": "task_objective",
                    "purpose": "Define objective",
                    "depends_on": [],
                    "priority": "critical",
                }
            ],
            "hard_constraints": ["Use provided documents only"],
            "soft_preferences": ["Prefer concise phrasing"],
            "required_outputs": {
                "format": "JSON",
                "schema_notes": "fields: verdict, evidence, confidence",
            },
            "safety_bounds": ["State uncertainty when evidence is missing."],
        }

    async def fake_rewrite_with_xml_objective(*, objective, **kwargs):
        if "one bounded objective" in objective:
            return "<system_directives>conservative rewritten xml</system_directives>"
        if "dependency mapping" in objective:
            return "<system_directives>structured rewritten xml</system_directives>"
        return "<system_directives>advanced rewritten xml</system_directives>"

    monkeypatch.setattr(optimizer, "_parse_xml_blueprint", fake_parse_xml_blueprint)
    monkeypatch.setattr(optimizer, "_rewrite_with_xml_objective", fake_rewrite_with_xml_objective)

    response = await optimizer.generate_variants(request=request)

    assert response.analysis.framework_applied == "xml_structured"
    assert [variant.name for variant in response.variants] == ["Conservative", "Structured", "Advanced"]
    assert response.variants[0].system_prompt.startswith("<system_directives>conservative")
    assert "{{documents}}" in response.variants[0].system_prompt
    assert response.run_metadata is not None
    assert response.run_metadata.framework == "xml_structured"


@pytest.mark.asyncio
async def test_xml_rewrite_fallback_used_on_failure(monkeypatch):
    optimizer = XmlStructuredOptimizer()
    request = _build_request()

    async def fake_parse_xml_blueprint(**kwargs):
        return {
            "objective": "Extract only requested facts.",
            "instruction_hierarchy": [
                {
                    "node": "constraint_graph",
                    "purpose": "boundaries",
                    "depends_on": ["task_objective"],
                    "priority": "high",
                }
            ],
            "hard_constraints": ["Do not invent facts"],
            "soft_preferences": [],
            "required_outputs": {"format": "JSON", "schema_notes": "field: answer"},
            "safety_bounds": ["Say unknown for missing data."],
        }

    async def fake_rewrite_with_xml_objective(*, objective, **kwargs):
        if "anti-injection" in objective:
            raise RuntimeError("rewrite failed")
        return "<system_directives>normal rewrite</system_directives>"

    monkeypatch.setattr(optimizer, "_parse_xml_blueprint", fake_parse_xml_blueprint)
    monkeypatch.setattr(optimizer, "_rewrite_with_xml_objective", fake_rewrite_with_xml_objective)

    response = await optimizer.generate_variants(request=request)

    assert response.analysis.framework_applied == "xml_structured"
    assert "<anti_injection_protocol>" in response.variants[2].system_prompt
