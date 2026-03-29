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
      app.api.routes.optimization.optimize_prompt
  - Shared LLM transport:
      app.services.llm_client.LLMClient

Evaluation strategy:
  1. Deterministic checks first (exact / normalized / structured similarity).
  2. Rubric-based LLM judging for ambiguous cases.
  3. Pairwise tie-break only when top variants are very close.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
from statistics import mean
from typing import Any, Literal

import structlog

from app.config import get_settings
from app.models.requests import EvaluationDatasetCase, OptimizationRequest
from app.models.responses import (
    OptimizationResponse,
    PromptVariant,
    TaskEvaluationCaseResult,
    TaskEvaluationResult,
)
from app.services.json_extractor import JSONExtractionError, extract_json_from_llm_response
from app.services.llm_client import LLMClient

logger = structlog.get_logger(__name__)


@dataclass
class DeterministicCaseScore:
    """
    Internal representation of a deterministic case scoring result.

    Association:
      Produced by DeterministicTaskScorer and consumed by
      TaskLevelEvaluationService when deciding whether rubric judging is needed.
    """

    score: int
    should_use_rubric: bool
    failure_reason: str | None


@dataclass
class RubricCaseScore:
    """
    Internal representation of a rubric-judge case score.

    Association:
      Produced by RubricTaskJudge and transformed into TaskEvaluationCaseResult.
    """

    score: int
    failure_reason: str | None


class DeterministicTaskScorer:
    """
    Fast deterministic evaluator for objective task checks.

    Association:
      Called by TaskLevelEvaluationService before any rubric judging.
      If deterministic evidence is strong, this scorer avoids extra judge calls.
    """

    def score_generated_output(
        self,
        generated_output_text: str,
        expected_output_reference: Any,
    ) -> DeterministicCaseScore:
        """
        Score one model output against an expected reference deterministically.

        Rules:
          - Structured expected outputs (dict/list) use structural similarity.
          - Textual expected outputs use exact/normalized/token-overlap checks.
          - Ambiguous textual matches request rubric judging.
        """
        if isinstance(expected_output_reference, (dict, list)):
            return self._score_structured_output(
                generated_output_text=generated_output_text,
                expected_output_reference=expected_output_reference,
            )

        expected_text = str(expected_output_reference).strip()
        actual_text = generated_output_text.strip()
        if actual_text == expected_text:
            return DeterministicCaseScore(
                score=100,
                should_use_rubric=False,
                failure_reason=None,
            )

        normalized_expected_text = self._normalize_text(expected_text)
        normalized_actual_text = self._normalize_text(actual_text)
        if normalized_actual_text == normalized_expected_text:
            return DeterministicCaseScore(
                score=95,
                should_use_rubric=False,
                failure_reason=None,
            )

        token_overlap_ratio = self._calculate_token_overlap_ratio(
            normalized_expected_text=normalized_expected_text,
            normalized_actual_text=normalized_actual_text,
        )
        deterministic_score = int(round(token_overlap_ratio * 100))
        if token_overlap_ratio >= 0.9:
            return DeterministicCaseScore(
                score=max(85, deterministic_score),
                should_use_rubric=False,
                failure_reason=None,
            )

        if token_overlap_ratio >= 0.45:
            return DeterministicCaseScore(
                score=max(40, deterministic_score),
                should_use_rubric=True,
                failure_reason=None,
            )

        return DeterministicCaseScore(
            score=max(5, deterministic_score),
            should_use_rubric=False,
            failure_reason="semantic_mismatch",
        )

    def _score_structured_output(
        self,
        generated_output_text: str,
        expected_output_reference: dict[str, Any] | list[Any],
    ) -> DeterministicCaseScore:
        """
        Score structured outputs with recursive structural similarity.

        Association:
          Used for extraction/classification/format-constrained tasks where
          deterministic checks are the most trustworthy evaluator.
        """
        parsed_output_value = self._extract_structured_value(generated_output_text)
        if parsed_output_value is None:
            return DeterministicCaseScore(
                score=0,
                should_use_rubric=False,
                failure_reason="invalid_structured_output",
            )

        structural_similarity = self._calculate_structural_similarity(
            expected_value=expected_output_reference,
            actual_value=parsed_output_value,
        )
        structured_score = int(round(structural_similarity * 100))
        if structural_similarity >= 0.99:
            return DeterministicCaseScore(
                score=100,
                should_use_rubric=False,
                failure_reason=None,
            )

        failure_reason = None
        if structured_score < get_settings().task_evaluation_case_pass_threshold:
            failure_reason = "structured_value_mismatch"

        return DeterministicCaseScore(
            score=structured_score,
            should_use_rubric=False,
            failure_reason=failure_reason,
        )

    def _extract_structured_value(self, generated_output_text: str) -> Any | None:
        """
        Parse JSON-like content from model output.

        Association:
          Keeps deterministic scoring robust when model output is wrapped in
          markdown code-fences or contains extra leading text.
        """
        trimmed_output = generated_output_text.strip()
        try:
            return json.loads(trimmed_output)
        except json.JSONDecodeError:
            pass

        try:
            extracted_json_dictionary = extract_json_from_llm_response(trimmed_output)
            return extracted_json_dictionary
        except JSONExtractionError:
            pass

        json_array_match = re.search(r"\[[\s\S]*\]", trimmed_output)
        if json_array_match:
            try:
                return json.loads(json_array_match.group())
            except json.JSONDecodeError:
                return None
        return None

    def _calculate_structural_similarity(self, expected_value: Any, actual_value: Any) -> float:
        """
        Recursively compute structural similarity in range [0.0, 1.0].

        Association:
          Shared by structured deterministic checks to produce transparent,
          explainable partial-credit scores.
        """
        if isinstance(expected_value, dict):
            if not isinstance(actual_value, dict):
                return 0.0
            expected_keys = list(expected_value.keys())
            if not expected_keys:
                return 1.0
            per_key_scores = [
                self._calculate_structural_similarity(
                    expected_value=expected_value[key],
                    actual_value=actual_value.get(key),
                )
                if key in actual_value
                else 0.0
                for key in expected_keys
            ]
            return float(mean(per_key_scores))

        if isinstance(expected_value, list):
            if not isinstance(actual_value, list):
                return 0.0
            if not expected_value:
                return 1.0
            compared_items_count = min(len(expected_value), len(actual_value))
            if compared_items_count == 0:
                return 0.0
            paired_scores = [
                self._calculate_structural_similarity(
                    expected_value=expected_value[index],
                    actual_value=actual_value[index],
                )
                for index in range(compared_items_count)
            ]
            # Penalize missing expected items.
            coverage_penalty = compared_items_count / len(expected_value)
            return float(mean(paired_scores) * coverage_penalty)

        if expected_value is None and actual_value is None:
            return 1.0
        return 1.0 if str(expected_value).strip() == str(actual_value).strip() else 0.0

    def _normalize_text(self, text_value: str) -> str:
        """
        Normalize text for deterministic comparisons.

        Association:
          Used by exact/near-exact text checks before escalating to rubric judge.
        """
        lowercase_text = text_value.lower()
        collapsed_whitespace_text = re.sub(r"\s+", " ", lowercase_text).strip()
        return re.sub(r"[^\w\s]", "", collapsed_whitespace_text)

    def _calculate_token_overlap_ratio(
        self,
        normalized_expected_text: str,
        normalized_actual_text: str,
    ) -> float:
        """
        Compute token-overlap ratio between expected and actual normalized text.

        Association:
          Provides a deterministic approximation for fuzzy text similarity when
          exact matching is too strict.
        """
        expected_tokens = set(normalized_expected_text.split())
        actual_tokens = set(normalized_actual_text.split())
        if not expected_tokens:
            return 0.0
        matched_tokens = expected_tokens.intersection(actual_tokens)
        return len(matched_tokens) / len(expected_tokens)


class RubricTaskJudge:
    """
    LLM-powered rubric judge for ambiguous or semantic task cases.

    Association:
      Invoked by TaskLevelEvaluationService only when deterministic scoring
      marks a case as uncertain (`should_use_rubric=True`).
    """

    async def score_case_with_rubric(
        self,
        llm_client: LLMClient,
        provider: str,
        model_id: str,
        case_input_text: str,
        expected_output_reference: Any,
        generated_output_text: str,
    ) -> RubricCaseScore:
        """
        Ask the LLM to judge one case with a strict JSON rubric response.

        Association:
          Uses app.services.llm_client.LLMClient so route-level usage counters
          and tracing remain centralized and consistent.
        """
        settings = get_settings()
        rubric_prompt = (
            "Evaluate the model output against the expected output for the task input.\n"
            "Score from 0 to 100.\n"
            "Return ONLY valid JSON with keys: score, failure_reason.\n\n"
            f"<task_input>\n{case_input_text}\n</task_input>\n\n"
            f"<expected_output>\n{json.dumps(expected_output_reference, ensure_ascii=True)}\n</expected_output>\n\n"
            f"<generated_output>\n{generated_output_text}\n</generated_output>\n"
        )
        rubric_system_prompt = (
            "You are a strict task evaluator. "
            "Do not reward style when correctness is weak. "
            "Use score 70+ only when the task is materially satisfied."
        )
        try:
            rubric_response_text = await llm_client.call(
                provider=provider,
                prompt=rubric_prompt,
                max_tokens=settings.max_tokens_task_evaluation_judging,
                model=model_id,
                system=rubric_system_prompt,
                temperature=0.0,
            )
            rubric_payload = extract_json_from_llm_response(rubric_response_text)
            raw_score_value = rubric_payload.get("score", 0)
            normalized_score = int(max(0, min(100, int(raw_score_value))))
            failure_reason = rubric_payload.get("failure_reason")
            if isinstance(failure_reason, str) and failure_reason.strip():
                normalized_failure_reason = failure_reason.strip()
            else:
                normalized_failure_reason = None
            return RubricCaseScore(
                score=normalized_score,
                failure_reason=normalized_failure_reason,
            )
        except Exception as rubric_error:
            logger.warning(
                "optimize.task_evaluation.rubric_judge_failed",
                error=str(rubric_error),
            )
            return RubricCaseScore(
                score=0,
                failure_reason="rubric_judge_unavailable",
            )


class PairwiseTieBreakerJudge:
    """
    Pairwise tie-break judge used only for close top-variant scores.

    Association:
      Called by TaskLevelEvaluationService after per-variant aggregate scores
      are computed. This avoids pairwise cost for clearly-separated variants.
    """

    async def compare_outputs_for_case(
        self,
        llm_client: LLMClient,
        provider: str,
        model_id: str,
        case_input_text: str,
        expected_output_reference: Any,
        candidate_a_output_text: str,
        candidate_b_output_text: str,
    ) -> Literal["A", "B", "TIE"]:
        """
        Determine which candidate output better satisfies one evaluation case.

        Association:
          Used strictly for tie-breaking and never as the default scorer.
        """
        settings = get_settings()
        pairwise_prompt = (
            "Compare candidate A and candidate B against the expected output.\n"
            "Return ONLY valid JSON: {\"winner\": \"A|B|TIE\"}.\n\n"
            f"<task_input>\n{case_input_text}\n</task_input>\n\n"
            f"<expected_output>\n{json.dumps(expected_output_reference, ensure_ascii=True)}\n</expected_output>\n\n"
            f"<candidate_a>\n{candidate_a_output_text}\n</candidate_a>\n\n"
            f"<candidate_b>\n{candidate_b_output_text}\n</candidate_b>\n"
        )
        pairwise_system_prompt = (
            "You are a strict evaluator. "
            "Prefer factual correctness and constraint adherence over writing style."
        )
        try:
            pairwise_response_text = await llm_client.call(
                provider=provider,
                prompt=pairwise_prompt,
                max_tokens=settings.max_tokens_task_evaluation_judging,
                model=model_id,
                system=pairwise_system_prompt,
                temperature=0.0,
            )
            pairwise_payload = extract_json_from_llm_response(pairwise_response_text)
            winner_value = str(pairwise_payload.get("winner", "TIE")).upper()
            if winner_value in ("A", "B"):
                return winner_value
        except Exception as pairwise_error:
            logger.warning(
                "optimize.task_evaluation.pairwise_judge_failed",
                error=str(pairwise_error),
            )
        return "TIE"


class TaskLevelEvaluationService:
    """
    Orchestrates per-variant empirical evaluation over `evaluation_dataset`.

    Association:
      Called by optimize route after variant generation and quality gate.
      Mutates each PromptVariant by attaching `task_evaluation`.
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._deterministic_task_scorer = DeterministicTaskScorer()
        self._rubric_task_judge = RubricTaskJudge()
        self._pairwise_tie_breaker_judge = PairwiseTieBreakerJudge()

    async def evaluate_response_variants(
        self,
        optimization_request: OptimizationRequest,
        optimization_response: OptimizationResponse,
    ) -> None:
        """
        Evaluate all generated variants over the request `evaluation_dataset`.

        Association:
          This is the primary API called by app.api.routes.optimization.
          It adds task-level evidence without changing existing quality gate data.
        """
        evaluation_dataset_cases = optimization_request.evaluation_dataset
        if not evaluation_dataset_cases:
            return

        logger.info(
            "optimize.task_evaluation.started",
            dataset_cases=len(evaluation_dataset_cases),
            variants=len(optimization_response.variants),
        )

        case_outputs_by_variant_id: dict[int, list[str]] = {}
        async with LLMClient(api_key=optimization_request.api_key) as llm_client:
            for prompt_variant in optimization_response.variants:
                variant_case_results, generated_case_outputs = await self._evaluate_single_variant(
                    llm_client=llm_client,
                    optimization_request=optimization_request,
                    prompt_variant=prompt_variant,
                    evaluation_dataset_cases=evaluation_dataset_cases,
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
            )

        logger.info("optimize.task_evaluation.completed")

    async def _evaluate_single_variant(
        self,
        llm_client: LLMClient,
        optimization_request: OptimizationRequest,
        prompt_variant: PromptVariant,
        evaluation_dataset_cases: list[EvaluationDatasetCase],
    ) -> tuple[list[TaskEvaluationCaseResult], list[str]]:
        """
        Evaluate one prompt variant across all dataset cases.

        Association:
          Called by evaluate_response_variants for each of the 3 output variants.
          Returns both case scores and raw generated outputs for optional tie-break.
        """
        case_results: list[TaskEvaluationCaseResult] = []
        generated_output_texts: list[str] = []
        for case_index, evaluation_case in enumerate(evaluation_dataset_cases, start=1):
            generated_output_text = await self._generate_variant_output_for_case(
                llm_client=llm_client,
                optimization_request=optimization_request,
                prompt_variant=prompt_variant,
                case_input_text=evaluation_case.input,
            )
            generated_output_texts.append(generated_output_text)

            deterministic_case_score = self._deterministic_task_scorer.score_generated_output(
                generated_output_text=generated_output_text,
                expected_output_reference=evaluation_case.expected_output,
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

            status_value = self._classify_case_status(case_score_value)
            case_results.append(
                TaskEvaluationCaseResult(
                    case_index=case_index,
                    score=case_score_value,
                    status=status_value,
                    scoring_method=scoring_method,
                    failure_reason=failure_reason if status_value != "pass" else None,
                )
            )
        return case_results, generated_output_texts

    async def _generate_variant_output_for_case(
        self,
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
        llm_client: LLMClient,
        optimization_request: OptimizationRequest,
        optimization_response: OptimizationResponse,
        evaluation_dataset_cases: list[EvaluationDatasetCase],
        case_outputs_by_variant_id: dict[int, list[str]],
    ) -> None:
        """
        Apply pairwise tie-break when top variant scores are within margin.

        Association:
          Called once after all variants have initial task scores.
          Keeps pairwise logic isolated from baseline deterministic/rubric scoring.
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
        self._apply_pairwise_adjustment(winner_variant, loser_variant)
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

    def _apply_pairwise_adjustment(self, winner_variant: PromptVariant, loser_variant: PromptVariant) -> None:
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
        leading_variant: PromptVariant,
        trailing_variant: PromptVariant,
        compared_case_indexes: list[int],
    ) -> None:
        """
        Mark case results as pairwise-touched for transparent provenance.

        Association:
          Updates both tied variants so per-case metadata reflects the tie-break.
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
        """
        Merge two judging mode labels into a single stable value.

        Association:
          Used when pairwise tie-break augments an existing deterministic/rubric
          evaluation mode.
        """
        if current_judging_mode == new_mode:
            return current_judging_mode
        if current_judging_mode == "mixed" or new_mode == "mixed":
            return "mixed"
        return "mixed"

    def _classify_case_status(self, case_score: int) -> Literal["pass", "partial", "fail"]:
        """
        Map numeric score to pass/partial/fail status.

        Association:
          Shared by deterministic and rubric flows so status semantics are
          consistent across all case results.
        """
        pass_threshold = self._settings.task_evaluation_case_pass_threshold
        if case_score >= pass_threshold:
            return "pass"
        if case_score >= max(0, pass_threshold - 20):
            return "partial"
        return "fail"
