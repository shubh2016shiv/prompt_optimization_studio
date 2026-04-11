"""
Task-level empirical evaluation service for optimization variants.

Why this module exists:
  The quality gate in prompt_quality_critic.py measures structural prompt quality.
  This module measures empirical task success by executing each generated variant
  against user-provided `evaluation_dataset` cases.

How this module fits with the rest of the backend:
  - Request model source:
      app.models.requests.OptimizationRequest.evaluation_dataset
  - Response model target:
      app.models.responses.PromptVariant.task_evaluation
  - Runtime caller:
      app.services.optimization.optimization_pipeline.execute_optimization_request

Evaluation strategy:
  1. Deterministic checks first (exact / normalized / structured similarity).
  2. Rubric-based LLM judging for ambiguous cases (with transient retry).
  3. Pairwise tie-break only when top variants are very close.

Concurrency model:
  - Variants are evaluated sequentially to keep total provider pressure bounded.
  - Cases inside one variant are evaluated concurrently with a semaphore limit
    from centralized settings (`task_evaluation_max_concurrency`).
"""

from __future__ import annotations

import asyncio
from statistics import mean
from typing import Literal

import structlog

from app.config import get_settings
from app.models.requests import EvaluationDatasetCase, OptimizationRequest
from app.models.responses import (
    OptimizationResponse,
    PromptVariant,
    TaskEvaluationCaseResult,
    TaskEvaluationResult,
)
from app.services.evaluation.task_level import (
    CancellationCheck,
    DeterministicCaseScore,
    DeterministicTaskScorer,
    PairwiseTieBreakerJudge,
    RubricCaseScore,
    RubricTaskJudge,
    TaskEvaluationRetryPolicy,
)
from app.services.llm_client import LLMClient

logger = structlog.get_logger(__name__)


class TaskLevelEvaluationService:
    """
    Orchestrates per-variant empirical evaluation over `evaluation_dataset`.

    Association:
      Called by the optimization pipeline after variant generation and quality
      gate completion. Mutates each PromptVariant by attaching `task_evaluation`.
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._retry_policy = TaskEvaluationRetryPolicy(self._settings)
        self._deterministic_task_scorer = DeterministicTaskScorer(self._settings)
        self._rubric_task_judge = RubricTaskJudge(
            settings=self._settings,
            retry_policy=self._retry_policy,
        )
        self._pairwise_tie_breaker_judge = PairwiseTieBreakerJudge(settings=self._settings)

    async def evaluate_response_variants(
        self,
        optimization_request: OptimizationRequest,
        optimization_response: OptimizationResponse,
        cancellation_check: CancellationCheck | None = None,
    ) -> None:
        """
        Evaluate all generated variants over the request `evaluation_dataset`.

        Association:
          This is the primary API called by optimization_pipeline.
          It adds task-level evidence without changing quality-gate data.
        """
        evaluation_dataset_cases = optimization_request.evaluation_dataset
        if not evaluation_dataset_cases:
            return

        logger.info(
            "optimize.task_evaluation.started",
            dataset_cases=len(evaluation_dataset_cases),
            variants=len(optimization_response.variants),
            per_variant_max_concurrency=self._settings.task_evaluation_max_concurrency,
        )

        case_outputs_by_variant_id: dict[int, list[str]] = {}
        async with LLMClient(api_key=optimization_request.api_key) as llm_client:
            for prompt_variant in optimization_response.variants:
                if cancellation_check is not None:
                    await cancellation_check()

                variant_case_results, generated_case_outputs = await self._evaluate_single_variant(
                    llm_client=llm_client,
                    optimization_request=optimization_request,
                    prompt_variant=prompt_variant,
                    evaluation_dataset_cases=evaluation_dataset_cases,
                    cancellation_check=cancellation_check,
                )
                case_outputs_by_variant_id[prompt_variant.id] = generated_case_outputs
                prompt_variant.task_evaluation = self._build_variant_task_evaluation_result(
                    variant_case_results=variant_case_results,
                )

            await self._apply_pairwise_tie_break_if_needed(
                llm_client=llm_client,
                optimization_request=optimization_request,
                optimization_response=optimization_response,
                evaluation_dataset_cases=evaluation_dataset_cases,
                case_outputs_by_variant_id=case_outputs_by_variant_id,
                cancellation_check=cancellation_check,
            )

        logger.info("optimize.task_evaluation.completed")

    async def _evaluate_single_variant(
        self,
        *,
        llm_client: LLMClient,
        optimization_request: OptimizationRequest,
        prompt_variant: PromptVariant,
        evaluation_dataset_cases: list[EvaluationDatasetCase],
        cancellation_check: CancellationCheck | None = None,
    ) -> tuple[list[TaskEvaluationCaseResult], list[str]]:
        """
        Evaluate one variant across all dataset cases with bounded concurrency.

        Educational note:
          We use a semaphore to avoid unbounded parallel calls. This speeds up
          evaluation materially while still protecting provider limits.
        """
        max_concurrency = max(1, self._settings.task_evaluation_max_concurrency)
        case_evaluation_semaphore = asyncio.Semaphore(max_concurrency)

        case_tasks = [
            asyncio.create_task(
                self._evaluate_single_case_for_variant(
                    llm_client=llm_client,
                    optimization_request=optimization_request,
                    prompt_variant=prompt_variant,
                    evaluation_case=evaluation_case,
                    case_index=case_index,
                    case_evaluation_semaphore=case_evaluation_semaphore,
                    cancellation_check=cancellation_check,
                )
            )
            for case_index, evaluation_case in enumerate(evaluation_dataset_cases, start=1)
        ]

        try:
            indexed_case_results = await asyncio.gather(*case_tasks)
        except Exception:
            await self._cancel_pending_tasks(case_tasks)
            raise

        # Gather may return cases in completion order; sort for stable output.
        sorted_case_results = sorted(indexed_case_results, key=lambda item: item[0])
        case_results = [result for _, result, _ in sorted_case_results]
        generated_output_texts = [generated_output for _, _, generated_output in sorted_case_results]
        return case_results, generated_output_texts

    async def _evaluate_single_case_for_variant(
        self,
        *,
        llm_client: LLMClient,
        optimization_request: OptimizationRequest,
        prompt_variant: PromptVariant,
        evaluation_case: EvaluationDatasetCase,
        case_index: int,
        case_evaluation_semaphore: asyncio.Semaphore,
        cancellation_check: CancellationCheck | None,
    ) -> tuple[int, TaskEvaluationCaseResult, str]:
        """
        Evaluate exactly one (variant, case) pair.

        Association:
          This unit is intentionally tiny and isolated so concurrency behavior,
          cancellation checkpoints, and case-level failures are easy to debug.
        """
        if cancellation_check is not None:
            await cancellation_check()

        async with case_evaluation_semaphore:
            try:
                if cancellation_check is not None:
                    await cancellation_check()

                generated_output_text = await self._generate_variant_output_for_case(
                    llm_client=llm_client,
                    optimization_request=optimization_request,
                    prompt_variant=prompt_variant,
                    case_input_text=evaluation_case.input,
                )

                if cancellation_check is not None:
                    await cancellation_check()

                deterministic_case_score = self._deterministic_task_scorer.score_generated_output(
                    generated_output_text=generated_output_text,
                    expected_output_reference=evaluation_case.expected_output,
                    expected_output_json_schema=evaluation_case.expected_output_json_schema,
                )
                case_score_value = deterministic_case_score.score
                scoring_method: Literal["deterministic", "rubric", "pairwise"] = "deterministic"
                failure_reason = deterministic_case_score.failure_reason

                if deterministic_case_score.should_use_rubric:
                    rubric_case_score = await self._rubric_task_judge.score_case_with_rubric(
                        llm_client=llm_client,
                        provider=optimization_request.provider,
                        model_id=optimization_request.model_id,
                        case_input_text=evaluation_case.input,
                        expected_output_reference=evaluation_case.expected_output,
                        generated_output_text=generated_output_text,
                    )
                    case_score_value = rubric_case_score.score
                    scoring_method = "rubric"
                    failure_reason = rubric_case_score.failure_reason

            except asyncio.CancelledError:
                raise
            except Exception as evaluation_error:
                logger.warning(
                    "optimize.task_evaluation.case_failed",
                    case_index=case_index,
                    error=str(evaluation_error),
                )
                generated_output_text = ""
                case_score_value = 0
                scoring_method = "deterministic"
                failure_reason = f"Evaluation failed: {evaluation_error}"

            status_value = self._classify_case_status(case_score_value)
            case_result = TaskEvaluationCaseResult(
                case_index=case_index,
                score=case_score_value,
                status=status_value,
                scoring_method=scoring_method,
                failure_reason=failure_reason if status_value != "pass" else None,
            )
            return case_index, case_result, generated_output_text

    async def _generate_variant_output_for_case(
        self,
        *,
        llm_client: LLMClient,
        optimization_request: OptimizationRequest,
        prompt_variant: PromptVariant,
        case_input_text: str,
    ) -> str:
        """
        Execute one variant prompt against one dataset input case.

        Association:
          This method is the runtime bridge between generated prompt variants
          and empirical case-level evaluation.
        """
        return await llm_client.call(
            provider=optimization_request.provider,
            prompt=case_input_text,
            max_tokens=self._settings.max_tokens_task_evaluation_generation,
            model=optimization_request.model_id,
            system=prompt_variant.system_prompt,
            temperature=0.0,
        )

    def _build_variant_task_evaluation_result(
        self,
        *,
        variant_case_results: list[TaskEvaluationCaseResult],
    ) -> TaskEvaluationResult:
        """
        Aggregate case-level scores into one variant-level task evaluation block.

        Association:
          Maps internal case results into app.models.responses.TaskEvaluationResult.
        """
        case_scores = [result.score for result in variant_case_results]
        aggregate_score = int(round(mean(case_scores))) if case_scores else 0
        passed_case_count = sum(1 for result in variant_case_results if result.status == "pass")
        case_count = len(variant_case_results)
        pass_rate = (passed_case_count / case_count) if case_count else 0.0
        scoring_methods = {result.scoring_method for result in variant_case_results}

        if scoring_methods == {"deterministic"}:
            judging_mode: Literal["deterministic", "rubric", "pairwise", "mixed"] = "deterministic"
        elif scoring_methods == {"rubric"}:
            judging_mode = "rubric"
        elif scoring_methods == {"pairwise"}:
            judging_mode = "pairwise"
        else:
            judging_mode = "mixed"

        unique_failure_reasons = sorted(
            {
                result.failure_reason
                for result in variant_case_results
                if result.failure_reason and result.status != "pass"
            }
        )

        return TaskEvaluationResult(
            task_success_score=aggregate_score,
            pass_rate=round(pass_rate, 4),
            total_cases=case_count,
            passed_cases=passed_case_count,
            judging_mode=judging_mode,
            pairwise_tie_break_applied=False,
            failure_reasons=unique_failure_reasons,
            case_results=variant_case_results,
        )

    async def _apply_pairwise_tie_break_if_needed(
        self,
        *,
        llm_client: LLMClient,
        optimization_request: OptimizationRequest,
        optimization_response: OptimizationResponse,
        evaluation_dataset_cases: list[EvaluationDatasetCase],
        case_outputs_by_variant_id: dict[int, list[str]],
        cancellation_check: CancellationCheck | None = None,
    ) -> None:
        """
        Apply pairwise tie-break when top variant scores are within margin.

        Association:
          Called once after all variants have initial task scores.
        """
        evaluated_variants = [
            variant for variant in optimization_response.variants if variant.task_evaluation is not None
        ]
        if len(evaluated_variants) < 2:
            return

        sorted_variants = sorted(
            evaluated_variants,
            key=lambda variant: variant.task_evaluation.task_success_score,  # type: ignore[union-attr]
            reverse=True,
        )
        leading_variant = sorted_variants[0]
        trailing_variant = sorted_variants[1]
        leading_score = leading_variant.task_evaluation.task_success_score  # type: ignore[union-attr]
        trailing_score = trailing_variant.task_evaluation.task_success_score  # type: ignore[union-attr]
        score_gap = abs(leading_score - trailing_score)
        if score_gap > self._settings.task_evaluation_pairwise_margin:
            return

        leading_outputs = case_outputs_by_variant_id.get(leading_variant.id, [])
        trailing_outputs = case_outputs_by_variant_id.get(trailing_variant.id, [])
        if not leading_outputs or not trailing_outputs:
            return

        leading_wins = 0
        trailing_wins = 0
        compared_case_indexes: list[int] = []

        for case_offset, evaluation_case in enumerate(evaluation_dataset_cases):
            if cancellation_check is not None:
                await cancellation_check()
            if case_offset >= len(leading_outputs) or case_offset >= len(trailing_outputs):
                continue

            pairwise_winner = await self._pairwise_tie_breaker_judge.compare_outputs_for_case(
                llm_client=llm_client,
                provider=optimization_request.provider,
                model_id=optimization_request.model_id,
                case_input_text=evaluation_case.input,
                expected_output_reference=evaluation_case.expected_output,
                candidate_a_output_text=leading_outputs[case_offset],
                candidate_b_output_text=trailing_outputs[case_offset],
            )
            if pairwise_winner is None:
                continue
            if pairwise_winner == "A":
                leading_wins += 1
                compared_case_indexes.append(case_offset + 1)
            elif pairwise_winner == "B":
                trailing_wins += 1
                compared_case_indexes.append(case_offset + 1)
            

        if leading_wins == trailing_wins:
            return

        winner_variant = leading_variant if leading_wins > trailing_wins else trailing_variant
        loser_variant = trailing_variant if winner_variant.id == leading_variant.id else leading_variant
        self._apply_pairwise_adjustment(winner_variant=winner_variant, loser_variant=loser_variant)
        self._mark_pairwise_case_methods(
            leading_variant=leading_variant,
            trailing_variant=trailing_variant,
            compared_case_indexes=compared_case_indexes,
        )
        logger.info(
            "optimize.task_evaluation.pairwise_tie_break_applied",
            winner_variant_id=winner_variant.id,
            loser_variant_id=loser_variant.id,
            leading_wins=leading_wins,
            trailing_wins=trailing_wins,
        )

    def _apply_pairwise_adjustment(self, *, winner_variant: PromptVariant, loser_variant: PromptVariant) -> None:
        """
        Adjust close scores after a pairwise decision.

        Association:
          Keeps tie-break impact intentionally small to avoid overriding strong
          deterministic evidence.
        """
        score_adjustment = self._settings.task_evaluation_pairwise_adjustment
        winner_evaluation = winner_variant.task_evaluation
        loser_evaluation = loser_variant.task_evaluation
        if winner_evaluation is None or loser_evaluation is None:
            return

        winner_evaluation.task_success_score = min(100, winner_evaluation.task_success_score + score_adjustment)
        loser_evaluation.task_success_score = max(0, loser_evaluation.task_success_score - score_adjustment)
        winner_evaluation.pairwise_tie_break_applied = True
        loser_evaluation.pairwise_tie_break_applied = True
        winner_evaluation.judging_mode = self._merge_judging_mode(winner_evaluation.judging_mode, "pairwise")
        loser_evaluation.judging_mode = self._merge_judging_mode(loser_evaluation.judging_mode, "pairwise")

    def _mark_pairwise_case_methods(
        self,
        *,
        leading_variant: PromptVariant,
        trailing_variant: PromptVariant,
        compared_case_indexes: list[int],
    ) -> None:
        """
        Mark case results as pairwise-touched for transparent provenance.

        Association:
          Updates tied variants so per-case metadata reflects tie-break usage.
        """
        if not compared_case_indexes:
            return

        leading_evaluation = leading_variant.task_evaluation
        trailing_evaluation = trailing_variant.task_evaluation
        if leading_evaluation is None or trailing_evaluation is None:
            return

        compared_case_index_set = set(compared_case_indexes)
        for case_result in leading_evaluation.case_results:
            if case_result.case_index in compared_case_index_set:
                case_result.scoring_method = "pairwise"
        for case_result in trailing_evaluation.case_results:
            if case_result.case_index in compared_case_index_set:
                case_result.scoring_method = "pairwise"

    def _merge_judging_mode(
        self,
        current_judging_mode: Literal["deterministic", "rubric", "pairwise", "mixed"],
        new_mode: Literal["deterministic", "rubric", "pairwise", "mixed"],
    ) -> Literal["deterministic", "rubric", "pairwise", "mixed"]:
        """Merge two judging mode labels into a single stable mode value."""
        if current_judging_mode == new_mode:
            return current_judging_mode
        if current_judging_mode == "mixed" or new_mode == "mixed":
            return "mixed"
        return "mixed"

    def _classify_case_status(self, case_score: int) -> Literal["pass", "partial", "fail"]:
        """Map numeric score to pass/partial/fail status."""
        pass_threshold = self._settings.task_evaluation_case_pass_threshold
        if case_score >= pass_threshold:
            return "pass"
        if case_score >= max(0, pass_threshold - 20):
            return "partial"
        return "fail"

    async def _cancel_pending_tasks(self, case_tasks: list[asyncio.Task[object]]) -> None:
        """
        Cancel still-running case tasks after a gather failure.

        Association:
          Prevents task leaks and noisy "Task exception was never retrieved"
          warnings when one case raises while others are still pending.
        """
        for case_task in case_tasks:
            if not case_task.done():
                case_task.cancel()
        await asyncio.gather(*case_tasks, return_exceptions=True)


__all__ = [
    "DeterministicCaseScore",
    "RubricCaseScore",
    "TaskLevelEvaluationService",
]
