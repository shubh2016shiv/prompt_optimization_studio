"""Tests for the OPRO trajectory optimizer integration."""

import pytest

from app.models.requests import EvaluationDatasetCase, OptimizationRequest
from app.models.responses import (
    OptimizationAnalysis,
    OptimizationResponse,
    PromptVariant,
    TaskEvaluationCaseResult,
    TaskEvaluationResult,
    VariantTCRTEScores,
)
from app.services.optimization.base import OptimizerFactory
from app.services.optimization.frameworks.opro_trajectory_optimizer import (
    OproCandidate,
    OproTrajectoryOptimizer,
)
from app.services.optimization.optimization_pipeline import execute_optimization_request


def _build_opro_request() -> OptimizationRequest:
    return OptimizationRequest(
        raw_prompt="Seed prompt",
        task_type="extraction",
        framework="opro",
        provider="openai",
        model_id="gpt-4.1-mini",
        model_label="GPT-4.1 Mini",
        is_reasoning_model=False,
        api_key="test-api-key",
        quality_gate_mode="off",
        evaluation_dataset=[
            EvaluationDatasetCase(input=f"input-{index}", expected_output=f"output-{index}")
            for index in range(1, 5)
        ],
    )


def _build_response(framework: str = "opro") -> OptimizationResponse:
    return OptimizationResponse(
        analysis=OptimizationAnalysis(
            detected_issues=[],
            model_notes="",
            framework_applied=framework,
            coverage_delta="",
            auto_selected_framework=None,
            auto_reason=None,
            few_shot_source="not_applicable",
        ),
        techniques_applied=[],
        variants=[
            PromptVariant(
                id=index,
                name=f"V{index}",
                strategy="test",
                system_prompt=f"system-{index}",
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
            for index in range(1, 4)
        ],
    )


def test_optimizer_factory_registers_opro():
    optimizer = OptimizerFactory.get_optimizer("opro")

    assert isinstance(optimizer, OproTrajectoryOptimizer)
    assert "opro" in OptimizerFactory.list_available_framework_ids()


def test_select_training_cases_uses_evenly_spaced_subset():
    optimizer = OproTrajectoryOptimizer()
    cases = [
        EvaluationDatasetCase(input=f"input-{index}", expected_output=f"output-{index}")
        for index in range(25)
    ]

    selected_cases = optimizer._select_training_cases(cases, max_cases=5)

    assert len(selected_cases) == 5
    assert selected_cases[0].input == "input-0"
    assert selected_cases[-1].input == "input-24"
    assert [case.input for case in selected_cases] == [
        "input-0",
        "input-6",
        "input-12",
        "input-18",
        "input-24",
    ]


@pytest.mark.asyncio
async def test_opro_generate_variants_deduplicates_and_maps_trajectory(monkeypatch):
    optimizer = OproTrajectoryOptimizer()
    request = _build_opro_request()
    proposal_batches = [
        [
            OproCandidate(system_prompt="System alpha", rationale="early alpha"),
            OproCandidate(system_prompt="System beta", rationale="early beta"),
        ],
        [
            OproCandidate(system_prompt="System gamma", rationale="best gamma"),
            OproCandidate(system_prompt="System alpha", rationale="duplicate alpha"),
        ],
        [
            OproCandidate(system_prompt="System delta", rationale="later delta"),
            OproCandidate(system_prompt="System epsilon", rationale="later epsilon"),
        ],
    ]
    score_by_prompt = {
        "Seed prompt": 50,
        "System alpha": 70,
        "System beta": 65,
        "System gamma": 95,
        "System delta": 80,
        "System epsilon": 75,
    }

    async def fake_propose_candidate_prompts(**kwargs):
        return proposal_batches.pop(0)

    async def fake_score_candidate_prompt(*, candidate_prompt, **kwargs):
        return score_by_prompt[candidate_prompt]

    monkeypatch.setattr(optimizer, "_propose_candidate_prompts", fake_propose_candidate_prompts)
    monkeypatch.setattr(optimizer, "_score_candidate_prompt", fake_score_candidate_prompt)

    response = await optimizer.generate_variants(request=request)

    assert response.analysis.framework_applied == "opro"
    assert [variant.name for variant in response.variants] == ["Conservative", "Structured", "Advanced"]
    assert response.variants[0].system_prompt.startswith("System alpha")
    assert response.variants[1].system_prompt.startswith("System delta")
    assert response.variants[2].system_prompt.startswith("System gamma")
    assert response.run_metadata is not None
    assert response.run_metadata.framework == "opro"
    assert response.run_metadata.opro_iterations_run == 3
    assert response.run_metadata.opro_candidates_evaluated == 6
    assert response.run_metadata.opro_training_cases_used == 4
    assert response.run_metadata.opro_best_score == 95


@pytest.mark.asyncio
async def test_pipeline_evaluates_final_opro_variants(monkeypatch):
    request = _build_opro_request()

    class FakeOproOptimizer:
        async def generate_variants(self, **kwargs):
            return _build_response(framework="opro")

    async def fake_evaluate_response_variants(self, optimization_request, optimization_response, **kwargs):
        for variant in optimization_response.variants:
            variant.task_evaluation = TaskEvaluationResult(
                task_success_score=88,
                pass_rate=1.0,
                total_cases=1,
                passed_cases=1,
                judging_mode="deterministic",
                pairwise_tie_break_applied=False,
                failure_reasons=[],
                case_results=[
                    TaskEvaluationCaseResult(
                        case_index=1,
                        score=88,
                        status="pass",
                        scoring_method="deterministic",
                        failure_reason=None,
                    )
                ],
            )

    from app.services.optimization import optimization_pipeline

    monkeypatch.setattr(
        optimization_pipeline.OptimizerFactory,
        "get_optimizer",
        staticmethod(lambda framework_id: FakeOproOptimizer()),
    )
    monkeypatch.setattr(
        optimization_pipeline.TaskLevelEvaluationService,
        "evaluate_response_variants",
        fake_evaluate_response_variants,
    )

    response = await execute_optimization_request(request=request, request_id="request-1")

    assert response.analysis.framework_applied == "opro"
    assert all(variant.task_evaluation is not None for variant in response.variants)
    assert response.variants[0].task_evaluation.task_success_score == 88