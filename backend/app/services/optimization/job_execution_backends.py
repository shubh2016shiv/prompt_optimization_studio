"""
Job execution backends for optimization jobs.

Why this module exists:
  APOST's first async job API used `asyncio.create_task` in the same FastAPI
  process. That changes HTTP behavior but does not solve event-loop contention
  under heavy load. This module introduces an execution strategy boundary so
  job orchestration can delegate heavy work to isolated worker processes.

Design:
  - `OptimizationJobExecutionBackend` is the abstraction used by the job service.
  - `ProcessPoolOptimizationJobExecutionBackend` is the default production-style
    implementation for this repository snapshot.
  - Tests can inject a fake backend to keep orchestration tests deterministic.
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ProcessPoolExecutor
from typing import Any, Protocol

import structlog

from app.config import get_settings
from app.models.requests import OptimizationRequest
from app.models.responses import OptimizationResponse
from app.services.optimization.optimization_pipeline import (
    OptimizationJobCancelledError,
    execute_optimization_request,
)
from app.services.store.redis_store import RedisStore

logger = structlog.get_logger(__name__)


class OptimizationJobExecutionBackend(Protocol):
    """
    Contract for executing one optimization job outside orchestration concerns.

    Association:
      `OptimizationJobService` depends on this protocol instead of concrete
      process details (Dependency Inversion Principle).
    """

    async def execute_job(
        self,
        request_payload: OptimizationRequest,
        request_id: str | None,
        job_id: str,
        few_shot_corpus_state: Any | None,
    ) -> OptimizationResponse:
        """Run one job and return the final optimization response."""

    async def shutdown(self) -> None:
        """Release backend resources during application shutdown."""


def _run_optimization_job_in_worker_process(
    request_payload_dict: dict[str, Any],
    request_id: str | None,
    job_id: str,
    few_shot_corpus_state: Any | None,
) -> dict[str, Any]:
    """
    Process entrypoint for running optimization work in a worker process.

    Educational note:
      This function executes in a separate Python process. Heavy JSON handling,
      LLM polling, and quality/evaluation loops happen there, not on FastAPI's
      main event loop. That is the key fix for "monolithic event-loop choking."
    """
    async def _run_pipeline_with_worker_local_store() -> OptimizationResponse:
        """
        Build and close a worker-local Redis adapter for this process execution.

        Educational note:
          Worker processes cannot safely reuse FastAPI's in-process Redis client.
          Each process creates its own adapter and closes it after the job.
        """
        redis_store = RedisStore()

        async def ensure_job_not_cancelled() -> None:
            """
            Read durable job state and raise when the user has cancelled it.

            Educational note:
              This is cooperative cancellation: we let the pipeline stop at safe
              checkpoints instead of killing worker processes abruptly.
            """
            persisted_job_record = await redis_store.get_job_record(job_id)
            if persisted_job_record is not None and persisted_job_record.status == "cancelled":
                raise OptimizationJobCancelledError(f"Optimization job '{job_id}' was cancelled.")

        try:
            return await execute_optimization_request(
                request=OptimizationRequest.model_validate(request_payload_dict),
                request_id=request_id,
                few_shot_corpus_state=few_shot_corpus_state,
                cache_store=redis_store,
                cancellation_check=ensure_job_not_cancelled,
            )
        finally:
            await redis_store.close()

    optimization_response = asyncio.run(_run_pipeline_with_worker_local_store())
    return optimization_response.model_dump(mode="json")


class ProcessPoolOptimizationJobExecutionBackend:
    """
    Execute optimization jobs in a dedicated process pool.

    Educational note:
      The FastAPI event loop only schedules and awaits futures here. The heavy
      work runs in worker processes managed by ProcessPoolExecutor, which keeps
      the web server responsive while jobs are running.
    """

    def __init__(self, worker_processes: int | None = None) -> None:
        settings = get_settings()
        max_workers = worker_processes or settings.optimization_job_worker_processes
        self._process_pool = ProcessPoolExecutor(max_workers=max_workers)

    async def execute_job(
        self,
        request_payload: OptimizationRequest,
        request_id: str | None,
        job_id: str,
        few_shot_corpus_state: Any | None,
    ) -> OptimizationResponse:
        """
        Submit one optimization request to the process pool and await completion.

        Educational note:
          `loop.run_in_executor` bridges async orchestration and synchronous
          process execution cleanly, so we do not block the API event loop.
        """
        event_loop = asyncio.get_running_loop()
        response_payload = await event_loop.run_in_executor(
            self._process_pool,
            _run_optimization_job_in_worker_process,
            request_payload.model_dump(mode="python"),
            request_id,
            job_id,
            few_shot_corpus_state,
        )
        return OptimizationResponse.model_validate(response_payload)

    async def shutdown(self) -> None:
        """
        Gracefully close worker processes on API shutdown.

        Association:
          Called by `OptimizationJobService.shutdown`, which is invoked during
          FastAPI lifespan shutdown.
        """
        self._process_pool.shutdown(wait=False, cancel_futures=True)
        logger.info("optimize.job_workers_shutdown")
