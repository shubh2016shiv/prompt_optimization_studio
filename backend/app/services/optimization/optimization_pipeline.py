"""
Reusable optimization pipeline shared by synchronous and job-based APIs.

This module exists to keep the core optimize execution logic in one place.
The synchronous `/api/optimize` route and the asynchronous job runner both
delegate to this service so behavior, logging, and metadata remain aligned.
"""

from __future__ import annotations

import os
from collections.abc import Awaitable, Callable

import structlog

from app.config import get_settings
from app.models.requests import OptimizationRequest
from app.models.responses import OptimizationResponse
from app.observability.langfuse_support import create_trace_id, start_trace, update_current_trace
from app.observability.usage_tracking import UsageSnapshot, bind_usage_snapshot
from app.services.analysis import (
    count_reasoning_hops,
    normalize_gap_data_for_auto_selection,
    select_framework,
)
from app.services.evaluation.task_level_evaluation import TaskLevelEvaluationService
from app.services.optimization.cached_operations import CachedOptimizationOperations
from app.services.optimization import retrieve_k_nearest
from app.services.optimization.base import OptimizerFactory, _sync_run_usage_metadata
from app.services.store.base import ICacheStore

logger = structlog.get_logger(__name__)


PhaseProgressReporter = Callable[[str], Awaitable[None]]
CancellationCheck = Callable[[], Awaitable[None]]


class OptimizationRequestBudgetError(Exception):
    """
    Raised when an optimization request exceeds a configured hard budget cap.

    Association:
      Used by both synchronous and job APIs so cost guardrails behave
      consistently across entrypoints.
    """


class OptimizationJobCancelledError(RuntimeError):
    """
    Raised when cooperative cancellation is detected during pipeline execution.

    Association:
      Worker backends and evaluation loops raise this to stop work safely
      without mislabeling cancellation as a normal failure.
    """


def enforce_optimization_request_budget(
    optimization_request: OptimizationRequest,
    *,
    request_id: str | None,
) -> None:
    """
    Enforce hard request-level budgets before expensive optimization work starts.

    Association:
      This is the single source of truth for evaluation dataset size limits and
      is reused by both `/api/optimize` and `/api/optimize/jobs`.
    """
    settings = get_settings()
    evaluation_cases = optimization_request.evaluation_dataset or []
    total_case_count = len(evaluation_cases)
    max_allowed_cases = settings.max_task_evaluation_cases_per_request

    if total_case_count > max_allowed_cases:
        logger.warning(
            "optimize.budget_check_rejected",
            request_id=request_id,
            evaluation_case_count=total_case_count,
            max_allowed_cases=max_allowed_cases,
        )
        raise OptimizationRequestBudgetError(
            "evaluation_dataset exceeds the allowed limit: "
            f"{total_case_count} provided, maximum is {max_allowed_cases}."
        )

    if optimization_request.framework == "opro" and not evaluation_cases:
        logger.warning(
            "optimize.budget_check_rejected",
            request_id=request_id,
            framework=optimization_request.framework,
            reason="opro_requires_evaluation_dataset",
        )
        raise OptimizationRequestBudgetError(
            "OPRO requires evaluation_dataset because it optimizes from empirical "
            "prompt-score trajectories. Provide at least one evaluation case or "
            "choose a non-OPRO framework."
        )

    logger.info(
        "optimize.budget_check_passed",
        request_id=request_id,
        evaluation_case_count=total_case_count,
        max_allowed_cases=max_allowed_cases,
    )


async def _run_cancellation_checkpoint(
    *,
    cancellation_check: CancellationCheck | None,
    checkpoint_name: str,
) -> None:
    """
    Run a cooperative cancellation checkpoint if a checker callback is provided.

    Association:
      Called at safe boundaries throughout optimization execution.
    """
    if cancellation_check is None:
        return
    await cancellation_check()
    logger.debug("optimize.cancellation_checkpoint_passed", checkpoint=checkpoint_name)


async def execute_optimization_request(
    request: OptimizationRequest,
    request_id: str | None,
    *,
    few_shot_corpus_state: object | None = None,
    cache_store: ICacheStore | None = None,
    progress_reporter: PhaseProgressReporter | None = None,
    cancellation_check: CancellationCheck | None = None,
) -> OptimizationResponse:
    """
    Execute the full optimization pipeline and return the assembled response.

    Association:
      Called by `app.api.routes.optimization.optimize_prompt` for synchronous
      execution and by the optimization job runner for background execution.
    """
    task_level_evaluation_service = TaskLevelEvaluationService()
    cached_operations = CachedOptimizationOperations(cache_store) if cache_store is not None else None
    langfuse_trace_id = create_trace_id(request_id or "optimize-request")
    usage_snapshot = UsageSnapshot()
    enforce_optimization_request_budget(request, request_id=request_id)

    async def report_phase(phase_name: str) -> None:
        """Forward progress updates when the caller provided a reporter."""
        if progress_reporter is not None:
            await progress_reporter(phase_name)

    with bind_usage_snapshot(usage_snapshot), start_trace(
        name="optimize.request",
        trace_id=langfuse_trace_id,
        metadata={
            "request_id": request_id,
            "provider": request.provider,
            "model_id": request.model_id,
        },
    ):
        update_current_trace(
            session_id=request_id,
            metadata={
                "request_id": request_id,
                "provider": request.provider,
                "model_id": request.model_id,
            },
            tags=["optimize", request.provider],
        )
        await _run_cancellation_checkpoint(
            cancellation_check=cancellation_check,
            checkpoint_name="before_framework_resolution",
        )

        await report_phase("resolving_framework")
        effective_framework = request.framework
        auto_reason: str | None = None

        if request.framework == "auto":
            normalized_auto_selection = normalize_gap_data_for_auto_selection(request.gap_data)

            effective_framework, auto_reason = select_framework(
                is_reasoning_model=request.is_reasoning_model,
                task_type=request.task_type,
                complexity=normalized_auto_selection.complexity,
                tcrte_overall_score=normalized_auto_selection.tcrte_overall_score,
                provider=request.provider,
                recommended_techniques=normalized_auto_selection.recommended_techniques,
                has_evaluation_dataset=bool(request.evaluation_dataset),
            )
            logger.info(
                "optimize.framework_selected",
                request_id=request_id,
                framework=effective_framework,
                auto_reason=auto_reason,
                normalized_complexity=normalized_auto_selection.complexity,
                normalized_score=normalized_auto_selection.tcrte_overall_score,
                normalized_techniques=normalized_auto_selection.recommended_techniques,
                defaults_applied=normalized_auto_selection.defaults_applied,
                malformed_gap_data=normalized_auto_selection.malformed_gap_data,
                ignored_unknown_techniques=normalized_auto_selection.unknown_techniques,
                ignored_non_routing_techniques=normalized_auto_selection.ignored_techniques,
            )
        await _run_cancellation_checkpoint(
            cancellation_check=cancellation_check,
            checkpoint_name="after_framework_resolution",
        )

        await report_phase("preparing_cross_cutting_inputs")
        core_k = 2
        if effective_framework in ("kernel", "xml_structured", "cot_ensemble"):
            if cached_operations is not None:
                core_k = await cached_operations.get_or_compute_reasoning_hops(
                    raw_prompt=request.raw_prompt,
                    compute_function=lambda: count_reasoning_hops(
                        raw_prompt=request.raw_prompt,
                        api_key=request.api_key,
                    ),
                )
            else:
                core_k = await count_reasoning_hops(
                    raw_prompt=request.raw_prompt,
                    api_key=request.api_key,
                )
            logger.info(
                "optimize.core_hops_computed",
                request_id=request_id,
                framework=effective_framework,
                core_k=core_k,
            )

        few_shot_examples = None
        few_shot_source = "not_applicable"
        if effective_framework == "cot_ensemble":
            few_shot_source = "synthetic"
            try:
                google_key = os.getenv("GOOGLE_API_KEY")
                if google_key:
                    resolved_corpus_state = few_shot_corpus_state
                    if cached_operations is not None:
                        resolved_corpus_state = await cached_operations.get_or_compute_few_shot_corpus(
                            google_api_key=google_key,
                            compute_function=retrieve_precomputed_corpus,
                        )
                    if resolved_corpus_state:
                        few_shot_examples = await retrieve_k_nearest(
                            query=request.raw_prompt,
                            task_type=request.task_type,
                            google_api_key=google_key,
                            precomputed_corpus=resolved_corpus_state,
                            k=3,
                        )
                        logger.info(
                            "optimize.knn_retrieved",
                            request_id=request_id,
                            k=len(few_shot_examples),
                        )
                        if few_shot_examples:
                            few_shot_source = "knn"
            except Exception as knn_retrieval_error:
                logger.warning(
                    "optimize.knn_retrieval_failed",
                    request_id=request_id,
                    error=str(knn_retrieval_error),
                )
        await _run_cancellation_checkpoint(
            cancellation_check=cancellation_check,
            checkpoint_name="after_cross_cutting_inputs",
        )

        await report_phase("generating_variants")
        strategy = OptimizerFactory.get_optimizer(effective_framework)
        response = await strategy.generate_variants(
            request=request,
            core_k=core_k,
            few_shot_examples=few_shot_examples,
            auto_reason=auto_reason,
        )
        response.analysis.few_shot_source = few_shot_source
        await _run_cancellation_checkpoint(
            cancellation_check=cancellation_check,
            checkpoint_name="after_variant_generation",
        )

        if request.evaluation_dataset:
            await report_phase("evaluating_dataset")
            logger.info(
                "optimize.task_evaluation_requested",
                request_id=request_id,
                run_id=(response.run_metadata.run_id if response.run_metadata else None),
                dataset_cases=len(request.evaluation_dataset),
            )
            try:
                await task_level_evaluation_service.evaluate_response_variants(
                    optimization_request=request,
                    optimization_response=response,
                    cancellation_check=cancellation_check,
                )
            except OptimizationJobCancelledError:
                raise
            except Exception as task_evaluation_error:
                logger.warning(
                    "optimize.task_evaluation_failed",
                    request_id=request_id,
                    run_id=(response.run_metadata.run_id if response.run_metadata else None),
                    error=str(task_evaluation_error),
                )
        else:
            logger.info(
                "optimize.task_evaluation_skipped",
                request_id=request_id,
                reason="no_evaluation_dataset",
            )
        await _run_cancellation_checkpoint(
            cancellation_check=cancellation_check,
            checkpoint_name="before_response_finalization",
        )

        await report_phase("finalizing_response")
        _sync_run_usage_metadata(response)

        run_id = response.run_metadata.run_id if response.run_metadata else None
        update_current_trace(
            metadata={
                "request_id": request_id,
                "run_id": run_id,
                "framework": effective_framework,
                "usage": usage_snapshot.to_dict(),
            },
            tags=["optimize", request.provider, effective_framework],
        )
        logger.info(
            "optimize.request_completed",
            request_id=request_id,
            run_id=run_id,
            framework=effective_framework,
            few_shot_source=few_shot_source,
            llm_call_count=usage_snapshot.llm_call_count,
            prompt_tokens=usage_snapshot.prompt_tokens,
        )
        return response


async def retrieve_precomputed_corpus(google_api_key: str) -> dict[str, object]:
    """
    Build full few-shot corpus embeddings for cache warm-up.

    Association:
      Used as a callback by CachedOptimizationOperations when corpus cache is
      cold and needs a single authoritative build.
    """
    from app.services.optimization.knn_retriever import precompute_corpus_embeddings

    return await precompute_corpus_embeddings(google_api_key)
