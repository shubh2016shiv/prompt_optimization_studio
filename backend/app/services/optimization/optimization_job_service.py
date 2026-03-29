"""
Durable optimization job orchestration service.

Why this module exists:
  The API layer should orchestrate job lifecycle while persistence and execution
  details remain replaceable. This service coordinates:
    - durable job state in `IJobStore`
    - execution strategy in `OptimizationJobExecutionBackend`
    - in-process async task scheduling for orchestration only

Educational note:
  "Durable" means job metadata survives API restarts because state is written
  to Redis through the store adapter. Background tasks can crash, but status
  remains recoverable and auditable.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

import structlog
from fastapi import HTTPException, Request

from app.models.requests import OptimizationRequest
from app.models.responses import (
    OptimizationJobCreatedResponse,
    OptimizationJobStatusResponse,
    OptimizationResponse,
)
from app.services.optimization.job_execution_backends import (
    OptimizationJobExecutionBackend,
    ProcessPoolOptimizationJobExecutionBackend,
)
from app.services.optimization.optimization_pipeline import (
    OptimizationJobCancelledError,
    OptimizationRequestBudgetError,
    enforce_optimization_request_budget,
)
from app.services.store.base import IJobStore
from app.services.store.models import OptimizationJobPersistedRecord
from app.services.store.redis_store import RedisStoreConnectionError

logger = structlog.get_logger(__name__)

OptimizationJobStatus = Literal["queued", "running", "succeeded", "failed", "cancelled"]


class OptimizationJobService:
    """
    Coordinates asynchronous optimization jobs within the current API process.

    Association:
      Used by the new job-oriented optimize routes. This service owns job
      lifecycle state and delegates actual prompt work to
      `execute_optimization_request`.
    """

    def __init__(
        self,
        *,
        job_store: IJobStore,
        execution_backend: OptimizationJobExecutionBackend | None = None,
        job_ttl_seconds: int = 7 * 24 * 60 * 60,
    ) -> None:
        self._job_store = job_store
        self._execution_backend = execution_backend or ProcessPoolOptimizationJobExecutionBackend()
        self._job_ttl_seconds = job_ttl_seconds
        self._background_tasks_by_job_id: dict[str, asyncio.Task[None]] = {}

    async def create_job(
        self,
        optimization_request: OptimizationRequest,
        http_request: Request,
        request_id: str | None,
        trace_id: str | None,
    ) -> OptimizationJobCreatedResponse:
        """
        Create a job record and schedule background execution.

        Association:
          Called by the job creation route. Returns immediately after the
          background task has been scheduled.
        """
        try:
            enforce_optimization_request_budget(optimization_request, request_id=request_id)
        except OptimizationRequestBudgetError as budget_error:
            raise HTTPException(status_code=422, detail=str(budget_error)) from budget_error

        now_timestamp = self._utc_now_isoformat()
        job_id = str(uuid4())
        persisted_job_record = OptimizationJobPersistedRecord(
            job_id=job_id,
            request_payload=optimization_request.model_dump(mode="python"),
            created_at=now_timestamp,
            updated_at=now_timestamp,
            status="queued",
            request_id=request_id,
            trace_id=trace_id,
            current_phase="queued",
        )
        try:
            await self._job_store.create_job_record(
                job_record=persisted_job_record,
                ttl_seconds=self._job_ttl_seconds,
            )
        except RedisStoreConnectionError as redis_error:
            raise HTTPException(
                status_code=503,
                detail=f"Job persistence unavailable: {redis_error}",
            ) from redis_error

        background_task = asyncio.create_task(
            self._run_job(
                persisted_job_record=persisted_job_record,
                few_shot_corpus_state=getattr(http_request.app.state, "few_shot_corpus", None),
            ),
            name=f"optimization-job-{job_id}",
        )
        self._background_tasks_by_job_id[job_id] = background_task
        logger.info(
            "optimize.job_created",
            job_id=job_id,
            request_id=request_id,
            trace_id=trace_id,
        )
        return OptimizationJobCreatedResponse(
            job_id=persisted_job_record.job_id,
            status=persisted_job_record.status,
            created_at=persisted_job_record.created_at,
            request_id=persisted_job_record.request_id,
            trace_id=persisted_job_record.trace_id,
        )

    async def get_job_status(self, job_id: str) -> OptimizationJobStatusResponse:
        """
        Return the current API status payload for a job.

        Association:
          Called by `/api/optimize/jobs/{job_id}`.
        """
        persisted_job_record = await self._get_job_record_or_raise(job_id)
        return self._build_job_status_response(persisted_job_record)

    async def get_job_result(self, job_id: str) -> OptimizationResponse:
        """
        Return the final optimization result for a completed job.

        Association:
          Called by `/api/optimize/jobs/{job_id}/result`. Raises a 409 error
          until the job has succeeded.
        """
        persisted_job_record = await self._get_job_record_or_raise(job_id)
        if persisted_job_record.status == "failed":
            raise HTTPException(
                status_code=409,
                detail=persisted_job_record.error_message or "Optimization job failed.",
            )
        if persisted_job_record.status == "cancelled":
            raise HTTPException(status_code=409, detail="Optimization job was cancelled by user.")
        if (
            persisted_job_record.status != "succeeded"
            or persisted_job_record.optimization_response_json is None
        ):
            raise HTTPException(status_code=409, detail="Optimization job is not finished yet.")
        return OptimizationResponse.model_validate_json(persisted_job_record.optimization_response_json)

    async def cancel_job(self, job_id: str) -> OptimizationJobStatusResponse:
        """
        Cancel an optimization job cooperatively and durably.

        Association:
          Called by `/api/optimize/jobs/{job_id}/cancel`. This method is
          idempotent and never rewrites terminal non-cancelled states.
        """
        persisted_job_record = await self._get_job_record_or_raise(job_id)
        if persisted_job_record.status in ("succeeded", "failed", "cancelled"):
            return self._build_job_status_response(persisted_job_record)

        try:
            updated_job_record = await self._job_store.update_job_record_atomic(
                job_id=job_id,
                patch_fields={
                    "status": "cancelled",
                    "current_phase": "cancelled",
                    "error_message": "cancelled_by_user",
                    "updated_at": self._utc_now_isoformat(),
                },
                ttl_seconds=self._job_ttl_seconds,
                expected_current_status=persisted_job_record.status,
            )
        except RedisStoreConnectionError as redis_error:
            raise HTTPException(
                status_code=503,
                detail=f"Job store unavailable: {redis_error}",
            ) from redis_error
        if updated_job_record is None:
            # Another worker updated state first; return latest durable truth.
            refreshed_job_record = await self._get_job_record_or_raise(job_id)
            return self._build_job_status_response(refreshed_job_record)

        background_task = self._background_tasks_by_job_id.get(job_id)
        if persisted_job_record.status == "queued" and background_task is not None:
            # Queued jobs can be cancelled immediately by stopping orchestration.
            background_task.cancel()
            self._background_tasks_by_job_id.pop(job_id, None)
        logger.info("optimize.job_cancel_requested", job_id=job_id, previous_status=persisted_job_record.status)
        return self._build_job_status_response(updated_job_record)

    async def _run_job(
        self,
        *,
        persisted_job_record: OptimizationJobPersistedRecord,
        few_shot_corpus_state: object | None,
    ) -> None:
        """
        Execute a job in the background and persist durable state transitions.

        Association:
          This method is the orchestration boundary between job lifecycle
          management and the execution backend.
        """
        await self._update_job_record_resilient(
            job_id=persisted_job_record.job_id,
            status="running",
            current_phase="starting",
            error_message=None,
            expected_current_status="queued",
        )

        async def report_phase(phase_name: str) -> None:
            """Update the record whenever the pipeline advances a phase."""
            await self._update_job_record_resilient(
                job_id=persisted_job_record.job_id,
                status="running",
                current_phase=phase_name,
                expected_current_status="running",
            )

        try:
            optimization_response = await self._execution_backend.execute_job(
                request_payload=OptimizationRequest.model_validate(persisted_job_record.request_payload),
                request_id=persisted_job_record.request_id,
                job_id=persisted_job_record.job_id,
                few_shot_corpus_state=few_shot_corpus_state,
            )
            await report_phase("completed")
            run_id = optimization_response.run_metadata.run_id if optimization_response.run_metadata else None
            await self._update_job_record_resilient(
                job_id=persisted_job_record.job_id,
                status="succeeded",
                current_phase="completed",
                run_id=run_id,
                optimization_response_json=optimization_response.model_dump_json(),
                error_message=None,
                expected_current_status="running",
            )
            logger.info(
                "optimize.job_completed",
                job_id=persisted_job_record.job_id,
                run_id=run_id,
            )
        except OptimizationJobCancelledError:
            await self._update_job_record_resilient(
                job_id=persisted_job_record.job_id,
                status="cancelled",
                current_phase="cancelled",
                error_message="cancelled_by_user",
                expected_current_status="running",
            )
            logger.info("optimize.job_cancelled", job_id=persisted_job_record.job_id)
        except Exception as job_error:
            await self._update_job_record_resilient(
                job_id=persisted_job_record.job_id,
                status="failed",
                current_phase="failed",
                error_message=str(job_error),
                expected_current_status="running",
            )
            logger.exception(
                "optimize.job_failed",
                job_id=persisted_job_record.job_id,
                error=str(job_error),
            )
        finally:
            self._background_tasks_by_job_id.pop(persisted_job_record.job_id, None)

    async def shutdown(self) -> None:
        """
        Release resources owned by the configured execution backend.

        Association:
          Called from FastAPI lifespan shutdown to close process pools cleanly.
        """
        for background_task in self._background_tasks_by_job_id.values():
            background_task.cancel()
        self._background_tasks_by_job_id.clear()
        await self._execution_backend.shutdown()
        await self._job_store.close()

    async def _update_job_record_resilient(
        self,
        *,
        job_id: str,
        status: OptimizationJobStatus | None = None,
        current_phase: str | None = None,
        run_id: str | None = None,
        optimization_response_json: str | None = None,
        error_message: str | None = None,
        expected_current_status: str | None = None,
    ) -> None:
        """
        Update durable job state while tolerating transient Redis blips.

        Educational note on 'Swallowing Connection Errors':
          Imagine an optimization job that just spent 2 minutes and $0.50 generating 
          beautiful prompt variants via the LLM pipeline. Now it simply needs to update 
          the Redis status to 'succeeded'.
          
          If there is a 1-second network blip to Redis right at this moment, 
          raising an uncaught exception would crash the entire background context, 
          destroying the generated prompts and wasting the user's money. 
          By catching RedisStoreConnectionError here, we log the failure but allow 
          the background pipeline execution to safely continue.
        """
        patch_fields: dict[str, object] = {"updated_at": self._utc_now_isoformat()}
        if status is not None:
            patch_fields["status"] = status
        if current_phase is not None:
            patch_fields["current_phase"] = current_phase
        if run_id is not None:
            patch_fields["run_id"] = run_id
        if optimization_response_json is not None:
            patch_fields["optimization_response_json"] = optimization_response_json
        patch_fields["error_message"] = error_message

        try:
            await self._job_store.update_job_record_atomic(
                job_id=job_id,
                patch_fields=patch_fields,
                ttl_seconds=self._job_ttl_seconds,
                expected_current_status=expected_current_status,
            )
        except RedisStoreConnectionError as redis_error:
            # We swallow the error cleanly. We log it loudly so DevOps knows Redis blinked, 
            # but we do NOT raise an exception that would crash the active LLM evaluation job.
            logger.warning(
                "optimize.job_status_update_failed",
                job_id=job_id,
                error=str(redis_error),
            )

    async def _get_job_record_or_raise(self, job_id: str) -> OptimizationJobPersistedRecord:
        """
        Look up a job record or raise a 404 API error.

        Association:
          Shared by status and result endpoints.
        """
        try:
            persisted_job_record = await self._job_store.get_job_record(job_id)
        except RedisStoreConnectionError as redis_error:
            raise HTTPException(
                status_code=503,
                detail=f"Job store unavailable: {redis_error}",
            ) from redis_error
        if persisted_job_record is None:
            raise HTTPException(status_code=404, detail=f"Optimization job '{job_id}' was not found.")
        return persisted_job_record

    def _build_job_status_response(
        self,
        persisted_job_record: OptimizationJobPersistedRecord,
    ) -> OptimizationJobStatusResponse:
        """
        Convert an internal job record into the public status response model.

        Association:
          Keeps API serialization separate from orchestration state storage.
        """
        return OptimizationJobStatusResponse(
            job_id=persisted_job_record.job_id,
            status=persisted_job_record.status,
            created_at=persisted_job_record.created_at,
            updated_at=persisted_job_record.updated_at,
            current_phase=persisted_job_record.current_phase,
            request_id=persisted_job_record.request_id,
            trace_id=persisted_job_record.trace_id,
            run_id=persisted_job_record.run_id,
            error_message=persisted_job_record.error_message,
        )

    def _utc_now_isoformat(self) -> str:
        """
        Return a canonical UTC timestamp string for stored job metadata.

        Association:
          Used for created_at and updated_at fields across all job state changes.
        """
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
