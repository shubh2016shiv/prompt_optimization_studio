import pytest

from app.models.responses import (
    OptimizationAnalysis,
    OptimizationResponse,
    PromptVariant,
    VariantTCRTEScores,
)
from app.services.evaluation.critique_result import CritiqueResult, DimensionScores
from app.services.optimization.base import BaseOptimizerStrategy


class DummyStrategy(BaseOptimizerStrategy):
    async def generate_variants(self, request, core_k=2, few_shot_examples=None, auto_reason=None):
        raise NotImplementedError


class FakeLLMClient:
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None


def _build_response() -> OptimizationResponse:
    variants = []
    for idx in range(1, 4):
        variants.append(
            PromptVariant(
                id=idx,
                name=f"Variant {idx}",
                strategy="test",
                system_prompt=f"System prompt {idx}",
                user_prompt=f"User prompt {idx}",
                token_estimate=10,
                tcrte_scores=VariantTCRTEScores(
                    task=50,
                    context=50,
                    role=50,
                    tone=50,
                    execution=50,
                ),
                strengths=[],
                best_for="test",
                overshoot_guards=[],
                undershoot_guards=[],
            )
        )

    return OptimizationResponse(
        analysis=OptimizationAnalysis(
            detected_issues=[],
            model_notes="",
            framework_applied="kernel",
            coverage_delta="",
            auto_selected_framework=None,
            auto_reason=None,
            few_shot_source="not_applicable",
        ),
        techniques_applied=[],
        variants=variants,
    )


@pytest.mark.asyncio
async def test_quality_gate_mode_off_skips_evaluation(monkeypatch):
    strategy = DummyStrategy()
    response = _build_response()

    async def fail_if_called(*args, **kwargs):
        raise AssertionError("Critique should not run when quality_gate_mode='off'")

    monkeypatch.setattr("app.services.llm_client.LLMClient", FakeLLMClient)
    monkeypatch.setattr(
        "app.services.evaluation.prompt_quality_critic.PromptQualityCritic.critique_prompt",
        fail_if_called,
    )

    refined = await strategy._refine_variants_with_quality_critique(
        response=response,
        raw_prompt="raw",
        task_type="reasoning",
        api_key="dummy",
        quality_gate_mode="off",
    )

    for variant in refined.variants:
        assert variant.quality_evaluation is None
        assert variant.quality_scores_source == "not_evaluated"
        assert variant.tcrte_scores_source == "initial_framework_estimate"


@pytest.mark.asyncio
async def test_quality_gate_mode_critique_only_does_not_enhance(monkeypatch):
    strategy = DummyStrategy()
    response = _build_response()

    async def fake_critique(self, system_prompt, raw_prompt, task_type, llm_client):
        return CritiqueResult(
            overall_score=60,
            dimensions=DimensionScores(
                role_clarity=60,
                task_specificity=60,
                constraint_completeness=60,
                output_format=60,
                hallucination_resistance=60,
                edge_case_handling=60,
                improvement_over_raw=60,
            ),
            weaknesses=["missing constraints"],
            enhancement_suggestions=["add constraints"],
            strengths=[],
            reasoning="needs work",
            passed_quality_gate=False,
            was_fallback=False,
        )

    async def fail_if_enhance_called(self, system_prompt, critique, task_type, llm_client):
        raise AssertionError("Enhancement should not run in critique_only mode")

    monkeypatch.setattr("app.services.llm_client.LLMClient", FakeLLMClient)
    monkeypatch.setattr(
        "app.services.evaluation.prompt_quality_critic.PromptQualityCritic.critique_prompt",
        fake_critique,
    )
    monkeypatch.setattr(
        "app.services.evaluation.prompt_quality_critic.PromptQualityCritic.enhance_prompt_from_critique",
        fail_if_enhance_called,
    )

    refined = await strategy._refine_variants_with_quality_critique(
        response=response,
        raw_prompt="raw",
        task_type="reasoning",
        api_key="dummy",
        quality_gate_mode="critique_only",
    )

    for variant in refined.variants:
        assert variant.quality_evaluation is not None
        assert variant.quality_evaluation.was_enhanced is False
        assert variant.quality_scores_source == "prompt_quality_critic"
        assert variant.tcrte_scores_source == "initial_framework_estimate"
        assert variant.tcrte_scores.task == 50
        assert variant.tcrte_scores.execution == 50


@pytest.mark.asyncio
async def test_fallback_propagates_to_variant_metadata(monkeypatch):
    strategy = DummyStrategy()
    response = _build_response()

    async def fallback_critique(self, system_prompt, raw_prompt, task_type, llm_client):
        return CritiqueResult(
            overall_score=0,
            dimensions=DimensionScores(),
            weaknesses=[],
            enhancement_suggestions=[],
            strengths=[],
            reasoning="Critique unavailable: timeout",
            passed_quality_gate=False,
            was_fallback=True,
        )

    monkeypatch.setattr("app.services.llm_client.LLMClient", FakeLLMClient)
    monkeypatch.setattr(
        "app.services.evaluation.prompt_quality_critic.PromptQualityCritic.critique_prompt",
        fallback_critique,
    )

    refined = await strategy._refine_variants_with_quality_critique(
        response=response,
        raw_prompt="raw",
        task_type="reasoning",
        api_key="dummy",
        quality_gate_mode="sample_one_variant",
    )

    first = refined.variants[0]
    second = refined.variants[1]

    assert first.quality_evaluation is not None
    assert first.quality_evaluation.status == "degraded"
    assert first.quality_evaluation.was_fallback is True
    assert first.quality_scores_source == "fallback"
    assert first.tcrte_scores_source == "initial_framework_estimate"

    assert second.quality_evaluation is None
    assert second.quality_scores_source == "not_evaluated"
    assert second.tcrte_scores_source == "initial_framework_estimate"


@pytest.mark.asyncio
async def test_quality_gate_exception_sets_failed_status(monkeypatch):
    strategy = DummyStrategy()
    response = _build_response()

    async def exploding_critique(self, system_prompt, raw_prompt, task_type, llm_client):
        raise RuntimeError("judge unavailable")

    monkeypatch.setattr("app.services.llm_client.LLMClient", FakeLLMClient)
    monkeypatch.setattr(
        "app.services.evaluation.prompt_quality_critic.PromptQualityCritic.critique_prompt",
        exploding_critique,
    )

    refined = await strategy._refine_variants_with_quality_critique(
        response=response,
        raw_prompt="raw",
        task_type="reasoning",
        api_key="dummy",
        quality_gate_mode="sample_one_variant",
        target_model="claude-sonnet-4-6",
    )

    first = refined.variants[0]
    assert first.quality_evaluation is not None
    assert first.quality_evaluation.status == "failed"
    assert first.quality_evaluation.overall_score is None
    assert first.quality_evaluation.was_fallback is True
    assert first.quality_scores_source == "fallback"
    assert refined.run_metadata is not None
    assert refined.run_metadata.framework == "kernel"
    assert refined.run_metadata.target_model == "claude-sonnet-4-6"
    assert len(refined.run_metadata.raw_prompt_hash) == 64
