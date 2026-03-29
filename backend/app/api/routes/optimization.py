"""
Optimization API Route.

POST /api/optimize - Generate optimized prompt variants synchronously.
"""

import structlog
from fastapi import APIRouter, HTTPException, Request

from app.models.requests import OptimizationRequest
from app.models.responses import OptimizationResponse
from app.observability.redaction import redact_sensitive_data
from app.observability.request_context import get_request_id
from app.services.json_extractor import JSONExtractionError
from app.services.llm_client import LLMClientError
from app.services.optimization.optimization_pipeline import (
    OptimizationRequestBudgetError,
    execute_optimization_request,
)
from app.services.store.redis_store import RedisStoreConnectionError

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

    try:
        return await execute_optimization_request(
            request=request,
            request_id=request_id,
            few_shot_corpus_state=getattr(http_request.app.state, "few_shot_corpus", None),
            cache_store=getattr(http_request.app.state, "redis_store", None),
        )
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
    except RedisStoreConnectionError as redis_error:
        logger.warning(
            "optimize.redis_unavailable",
            request_id=request_id,
            error=str(redis_error),
        )
        raise HTTPException(
            status_code=503,
            detail=f"Optimization cache/storage unavailable: {str(redis_error)}",
        )
    except OptimizationRequestBudgetError as budget_error:
        logger.warning(
            "optimize.budget_rejected",
            request_id=request_id,
            error=str(budget_error),
        )
        raise HTTPException(status_code=422, detail=str(budget_error))
    except Exception as unexpected_error:
        logger.exception(
            "optimize.unexpected_error",
            request_id=request_id,
            error=str(unexpected_error),
        )
        raise HTTPException(status_code=500, detail=f"Internal error: {str(unexpected_error)}")
