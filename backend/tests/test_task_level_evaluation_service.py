"""Unit tests for task-level empirical evaluation service."""

import pytest

from app.models.requests import EvaluationDatasetCase, OptimizationRequest
from app.models.responses import (
    OptimizationAnalysis,
    OptimizationResponse,
    PromptVariant,
    VariantTCRTEScores,
)
from app.services.evaluation.task_level_evaluation import (
    DeterministicCaseScore,
    RubricCaseScore,
    TaskLevelEvaluationService,
)


def _build_request_with_dataset() -> OptimizationRequest:
    """Create an OptimizationRequest fixture with evaluation dataset enabled."""
    return OptimizationRequest(
        raw_prompt="Extract structured fields from messages.",
        task_type="extraction",
        framework="kernel",
        provider="openai",
        model_id="gpt-4.1-mini",
        model_label="GPT-4.1 Mini",
        is_reasoning_model=False,
        api_key="test-api-key",
        quality_gate_mode="off",
        evaluation_dataset=[
            EvaluationDatasetCase(
                input="Invoice INV-2044 amount 1842.50 due 2026-04-15",
                expected_output={"invoice_number": "INV-2044", "amount": 1842.50},
            ),
            EvaluationDatasetCase(
                input="Invoice INV-9001 amount 99.00 due 2026-05-01",
                expected_output={"invoice_number": "INV-9001", "amount": 99.0},
            ),
        ],
    )


def _build_response_with_variants() -> OptimizationResponse:
    """Create a 3-variant response shell used by evaluator tests."""
    variants = []
    for variant_index in range(1, 4):
        variants.append(
            PromptVariant(
                id=variant_index,
                name=f"Variant {variant_index}",
                strategy="test",
                system_prompt=f"System prompt {variant_index}",
                user_prompt="user",
                token_estimate=10,
                tcrte_scores=VariantTCRTEScores(
                    task=60,
                    context=60,
                    role=60,
                    tone=60,
                    execution=60,
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
async def test_task_evaluation_attaches_deterministic_scores(monkeypatch):
    """Deterministic matches should produce task_evaluation without rubric mode."""
    service = TaskLevelEvaluationService()
    request = _build_request_with_dataset()
    response = _build_response_with_variants()

    async def fake_generate_output(*, prompt_variant, **kwargs):
        if prompt_variant.id == 1:
            return '{"invoice_number":"INV-2044","amount":1842.5}'
        if prompt_variant.id == 2:
            return '{"invoice_number":"INV-2044","amount":1500.0}'
        return "nonsense output"

    monkeypatch.setattr(
        service,
        "_generate_variant_output_for_case",
        fake_generate_output,
    )

    await service.evaluate_response_variants(
        optimization_request=request,
        optimization_response=response,
    )

    assert response.variants[0].task_evaluation is not None
    assert response.variants[0].task_evaluation.judging_mode == "deterministic"
    assert response.variants[0].task_evaluation.total_cases == 2
    assert response.variants[0].task_evaluation.task_success_score >= 50
    assert response.variants[2].task_evaluation is not None
    assert response.variants[2].task_evaluation.task_success_score == 0


@pytest.mark.asyncio
async def test_task_evaluation_uses_rubric_when_deterministic_is_uncertain(monkeypatch):
    """Uncertain deterministic scores should escalate to rubric judging."""
    service = TaskLevelEvaluationService()
    request = _build_request_with_dataset()
    response = _build_response_with_variants()

    async def fake_generate_output(*, prompt_variant, **kwargs):
        return f"Potentially correct output for variant {prompt_variant.id}"

    async def fake_rubric_score(*args, **kwargs):
        return RubricCaseScore(score=88, failure_reason=None)

    monkeypatch.setattr(
        service,
        "_generate_variant_output_for_case",
        fake_generate_output,
    )
    monkeypatch.setattr(
        service._deterministic_task_scorer,
        "score_generated_output",
        lambda **kwargs: DeterministicCaseScore(
            score=60,
            should_use_rubric=True,
            failure_reason=None,
        ),
    )
    monkeypatch.setattr(
        service._rubric_task_judge,
        "score_case_with_rubric",
        fake_rubric_score,
    )

    await service.evaluate_response_variants(
        optimization_request=request,
        optimization_response=response,
    )

    first_variant_task_evaluation = response.variants[0].task_evaluation
    assert first_variant_task_evaluation is not None
    assert first_variant_task_evaluation.judging_mode == "rubric"
    assert all(
        case_result.scoring_method == "rubric"
        for case_result in first_variant_task_evaluation.case_results
    )


@pytest.mark.asyncio
async def test_pairwise_tie_break_applies_small_adjustment(monkeypatch):
    """Close top scores should receive small pairwise tie-break adjustment."""
    service = TaskLevelEvaluationService()
    request = _build_request_with_dataset()
    response = _build_response_with_variants()

    async def fake_generate_output(*, prompt_variant, **kwargs):
        return f"output from variant {prompt_variant.id}"

    async def fake_rubric_score(*args, generated_output_text, **kwargs):
        if "variant 1" in generated_output_text:
            return RubricCaseScore(score=80, failure_reason=None)
        if "variant 2" in generated_output_text:
            return RubricCaseScore(score=80, failure_reason=None)
        return RubricCaseScore(score=20, failure_reason="wrong_answer")

    async def fake_pairwise_compare(*args, **kwargs):
        return "B"

    monkeypatch.setattr(
        service,
        "_generate_variant_output_for_case",
        fake_generate_output,
    )
    monkeypatch.setattr(
        service._deterministic_task_scorer,
        "score_generated_output",
        lambda **kwargs: DeterministicCaseScore(
            score=60,
            should_use_rubric=True,
            failure_reason=None,
        ),
    )
    monkeypatch.setattr(
        service._rubric_task_judge,
        "score_case_with_rubric",
        fake_rubric_score,
    )
    monkeypatch.setattr(
        service._pairwise_tie_breaker_judge,
        "compare_outputs_for_case",
        fake_pairwise_compare,
    )

    await service.evaluate_response_variants(
        optimization_request=request,
        optimization_response=response,
    )

    first_variant_evaluation = response.variants[0].task_evaluation
    second_variant_evaluation = response.variants[1].task_evaluation
    assert first_variant_evaluation is not None
    assert second_variant_evaluation is not None
    assert first_variant_evaluation.pairwise_tie_break_applied is True
    assert second_variant_evaluation.pairwise_tie_break_applied is True
    assert second_variant_evaluation.task_success_score > first_variant_evaluation.task_success_score
    assert any(
        case_result.scoring_method == "pairwise"
        for case_result in second_variant_evaluation.case_results
    )
