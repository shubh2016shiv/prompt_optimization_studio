import pytest

from app.models.requests import OptimizationRequest
from app.models.responses import OptimizationAnalysis, OptimizationResponse, PromptVariant, VariantTCRTEScores
from app.services.analysis.auto_selection_normalizer import normalize_gap_data_for_auto_selection
from app.services.optimization.optimization_pipeline import execute_optimization_request


def _build_response(framework: str, auto_reason: str | None) -> OptimizationResponse:
    return OptimizationResponse(
        analysis=OptimizationAnalysis(
            detected_issues=[],
            model_notes="",
            framework_applied=framework,
            coverage_delta="",
            auto_selected_framework=framework if auto_reason else None,
            auto_reason=auto_reason,
            few_shot_source="not_applicable",
        ),
        techniques_applied=[],
        variants=[
            PromptVariant(
                id=1,
                name="V1",
                strategy="test",
                system_prompt="system",
                user_prompt="user",
                token_estimate=1,
                tcrte_scores=VariantTCRTEScores(task=10, context=10, role=10, tone=10, execution=10),
                strengths=[],
                best_for="test",
                overshoot_guards=[],
                undershoot_guards=[],
            )
        ],
    )


def test_normalize_gap_data_handles_malformed_mapping():
    normalized = normalize_gap_data_for_auto_selection("not-a-dict")

    assert normalized.malformed_gap_data is True
    assert normalized.tcrte_overall_score == 0
    assert normalized.complexity == "standard"
    assert normalized.recommended_techniques == []
    assert "overall_score" in normalized.defaults_applied
    assert "complexity" in normalized.defaults_applied
    assert "recommended_techniques" in normalized.defaults_applied


def test_normalize_gap_data_handles_invalid_score_and_non_list_techniques():
    normalized = normalize_gap_data_for_auto_selection(
        {
            "overall_score": "not-a-number",
            "complexity": "medium",
            "recommended_techniques": "CoRe",
        }
    )

    assert normalized.tcrte_overall_score == 0
    assert normalized.complexity == "standard"
    assert normalized.recommended_techniques == []
    assert "overall_score" in normalized.defaults_applied
    assert "recommended_techniques" in normalized.defaults_applied


def test_normalize_gap_data_tracks_known_and_unknown_techniques():
    normalized = normalize_gap_data_for_auto_selection(
        {
            "overall_score": "62",
            "complexity": "medium",
            "recommended_techniques": ["CoRe", "Prefill", "mystery-technique", "RAL-Writer"],
        }
    )

    assert normalized.tcrte_overall_score == 62
    assert normalized.complexity == "standard"
    assert normalized.recommended_techniques == ["context_repetition", "constraint_restatement"]
    assert normalized.ignored_techniques == ["Prefill"]
    assert normalized.unknown_techniques == ["mystery-technique"]


@pytest.mark.asyncio
async def test_pipeline_passes_normalized_auto_selection_inputs_to_selector(monkeypatch):
    request = OptimizationRequest(
        raw_prompt="Summarize records.",
        task_type="analysis",
        framework="auto",
        provider="openai",
        model_id="gpt-4.1-mini",
        model_label="GPT-4.1 Mini",
        is_reasoning_model=False,
        gap_data={
            "overall_score": "62.0",
            "complexity": "medium",
            "recommended_techniques": ["CoRe", "Prefill", "mystery-technique"],
        },
        api_key="test-api-key",
        quality_gate_mode="off",
    )

    captured_selector_args: dict[str, object] = {}

    async def _unused_generate_variants(**kwargs):
        return _build_response(framework="reasoning_aware", auto_reason=kwargs.get("auto_reason"))

    class FakeOptimizer:
        async def generate_variants(self, **kwargs):
            return await _unused_generate_variants(**kwargs)

    def fake_select_framework(**kwargs):
        captured_selector_args.update(kwargs)
        return "reasoning_aware", "normalized for test"

    from app.services.optimization import optimization_pipeline

    monkeypatch.setattr(optimization_pipeline, "select_framework", fake_select_framework)
    monkeypatch.setattr(
        optimization_pipeline.OptimizerFactory,
        "get_optimizer",
        staticmethod(lambda framework_id: FakeOptimizer()),
    )

    response = await execute_optimization_request(request=request, request_id="request-1")

    assert captured_selector_args["complexity"] == "standard"
    assert captured_selector_args["tcrte_overall_score"] == 62
    assert captured_selector_args["recommended_techniques"] == ["context_repetition"]
    assert response.analysis.auto_selected_framework == "reasoning_aware"
    assert response.analysis.auto_reason == "normalized for test"
