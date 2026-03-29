"""
Asynchronous optimization job API routes.

These endpoints introduce the first job-oriented execution model for APOST.
They reuse the same optimization request contract as `/api/optimize`, but
return a `job_id` immediately so clients can poll for completion later.
"""

import structlog
from fastapi import APIRouter, HTTPException, Request

from app.models.requests import OptimizationRequest
from app.models.responses import (
    OptimizationJobCreatedResponse,
    OptimizationJobStatusResponse,
    OptimizationResponse,
)
from app.observability.langfuse_support import create_trace_id
from app.observability.redaction import redact_sensitive_data
from app.observability.request_context import get_request_id
from app.services.optimization.optimization_job_service import OptimizationJobService

logger = structlog.get_logger(__name__)
router = APIRouter()


def _get_job_service(http_request: Request) -> OptimizationJobService:
    """
    Resolve the optimization job service from app state.

    Educational note:
      This avoids hidden module-level singletons and ensures the route always
      uses the lifecycle-managed service initialized at application startup.
    """
    job_service = getattr(http_request.app.state, "optimization_job_service", None)
    if job_service is None:
        raise HTTPException(status_code=503, detail="Optimization job service is not initialized.")
    return job_service


@router.post("/optimize/jobs", response_model=OptimizationJobCreatedResponse)
async def create_optimization_job(
    request: OptimizationRequest,
    http_request: Request,
) -> OptimizationJobCreatedResponse:
    """
    Create an asynchronous optimization job and return immediately.

    Association:
      The background execution is handled by OptimizationJobService, which
      delegates the actual optimize work to the shared optimization pipeline.
    """
    request_id = get_request_id(http_request)
    trace_id = create_trace_id(request_id or "optimize-job-request")
    logger.info(
        "optimize.job_request_started",
        request_id=request_id,
        provider=request.provider,
        model_id=request.model_id,
        framework=request.framework,
        payload=redact_sensitive_data(request.model_dump()),
    )
    created_job_response = await _get_job_service(http_request).create_job(
        optimization_request=request,
        http_request=http_request,
        request_id=request_id,
        trace_id=trace_id,
    )
    logger.info(
        "optimize.job_request_completed",
        request_id=request_id,
        job_id=created_job_response.job_id,
        status=created_job_response.status,
    )
    return created_job_response


@router.get("/optimize/jobs/{job_id}", response_model=OptimizationJobStatusResponse)
async def get_optimization_job_status(job_id: str, http_request: Request) -> OptimizationJobStatusResponse:
    """
    Return current state for an asynchronous optimization job.

    Association:
      Used by clients to poll progress until they are ready to fetch the final
      optimization result.
    """
    return await _get_job_service(http_request).get_job_status(job_id)


@router.get("/optimize/jobs/{job_id}/result", response_model=OptimizationResponse)
async def get_optimization_job_result(job_id: str, http_request: Request) -> OptimizationResponse:
    """
    Return the completed optimization result for a succeeded job.

    Association:
      This endpoint returns the same OptimizationResponse contract used by the
      synchronous `/api/optimize` route.
    """
    return await _get_job_service(http_request).get_job_result(job_id)
