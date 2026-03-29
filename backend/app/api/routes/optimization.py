"""
Optimization API Route.

POST /api/optimize - Generate optimized prompt variants.
"""

import os

import structlog
from fastapi import APIRouter, HTTPException, Request

from app.models.requests import OptimizationRequest
from app.models.responses import OptimizationResponse
from app.observability.redaction import redact_sensitive_data
from app.observability.request_context import get_request_id
from app.services.analysis import count_reasoning_hops, select_framework
from app.services.json_extractor import JSONExtractionError
from app.services.llm_client import LLMClientError
from app.services.optimization import retrieve_k_nearest
from app.services.optimization.base import OptimizerFactory

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post("/optimize", response_model=OptimizationResponse)
async def optimize_prompt(request: OptimizationRequest, http_request: Request) -> OptimizationResponse:
    """
    Generate three optimized prompt variants (Conservative, Structured, Advanced).

    The route resolves auto-framework selection, computes cross-cutting inputs
    (CoRe hops and optional few-shot examples), and delegates framework logic to
    strategy classes via OptimizerFactory.
    """
    request_id = get_request_id(http_request)
    payload = redact_sensitive_data(request.model_dump())
    logger.info(
        "optimize.request_started",
        request_id=request_id,
        provider=request.provider,
        model_id=request.model_id,
        framework=request.framework,
        payload=payload,
    )

    effective_framework = request.framework
    auto_reason: str | None = None

    if request.framework == "auto":
        tcrte_overall = 0
        if request.gap_data and "overall_score" in request.gap_data:
            tcrte_overall = int(request.gap_data["overall_score"])

        techniques: list[str] = []
        if request.gap_data and "recommended_techniques" in request.gap_data:
            techniques = request.gap_data["recommended_techniques"]

        complexity = "standard"
        if request.gap_data and "complexity" in request.gap_data:
            complexity = request.gap_data["complexity"]

        effective_framework, auto_reason = select_framework(
            is_reasoning_model=request.is_reasoning_model,
            task_type=request.task_type,
            complexity=complexity,
            tcrte_overall_score=tcrte_overall,
            provider=request.provider,
            recommended_techniques=techniques,
        )
        logger.info(
            "optimize.framework_selected",
            request_id=request_id,
            framework=effective_framework,
            auto_reason=auto_reason,
        )

    core_k = 2
    if effective_framework in ("kernel", "xml_structured", "cot_ensemble"):
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
            corpus_state = getattr(http_request.app.state, "few_shot_corpus", None)
            google_key = os.getenv("GOOGLE_API_KEY")
            if corpus_state and google_key:
                few_shot_examples = await retrieve_k_nearest(
                    query=request.raw_prompt,
                    task_type=request.task_type,
                    google_api_key=google_key,
                    precomputed_corpus=corpus_state,
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

    try:
        strategy = OptimizerFactory.get_optimizer(effective_framework)

        response = await strategy.generate_variants(
            request=request,
            core_k=core_k,
            few_shot_examples=few_shot_examples,
            auto_reason=auto_reason,
        )
        response.analysis.few_shot_source = few_shot_source

        run_id = response.run_metadata.run_id if response.run_metadata else None
        logger.info(
            "optimize.request_completed",
            request_id=request_id,
            run_id=run_id,
            framework=effective_framework,
            few_shot_source=few_shot_source,
        )
        return response

    except ValueError as framework_not_found_error:
        logger.warning(
            "optimize.framework_not_found",
            request_id=request_id,
            error=str(framework_not_found_error),
        )
        raise HTTPException(status_code=400, detail=str(framework_not_found_error))
    except LLMClientError as llm_error:
        status_code = llm_error.status_code or 502
        logger.warning(
            "optimize.llm_error",
            request_id=request_id,
            status_code=status_code,
            error=str(llm_error),
        )
        raise HTTPException(status_code=status_code, detail=f"LLM API error: {str(llm_error)}")
    except JSONExtractionError as json_error:
        logger.warning(
            "optimize.json_parse_error",
            request_id=request_id,
            error=str(json_error),
        )
        raise HTTPException(status_code=502, detail=f"Failed to parse LLM response: {str(json_error)}")
    except Exception as unexpected_error:
        logger.exception(
            "optimize.unexpected_error",
            request_id=request_id,
            error=str(unexpected_error),
        )
        raise HTTPException(status_code=500, detail=f"Internal error: {str(unexpected_error)}")
