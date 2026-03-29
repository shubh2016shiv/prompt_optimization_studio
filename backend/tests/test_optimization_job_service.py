import asyncio
import contextlib

import pytest
from fastapi import HTTPException

from app.models.requests import OptimizationRequest
from app.models.responses import (
    OptimizationAnalysis,
    OptimizationResponse,
    PromptVariant,
    VariantTCRTEScores,
)
from app.services.optimization.optimization_job_service import OptimizationJobService
from app.services.store.models import OptimizationJobPersistedRecord
from app.services.store.redis_store import RedisStoreConnectionError


class _DummyApp:
    state = type("State", (), {"few_shot_corpus": None})()


class _DummyRequest:
    app = _DummyApp()


class _FakeExecutionBackend:
    def __init__(self, response_delay_seconds: float = 0.0):
        self.response_delay_seconds = response_delay_seconds

    async def execute_job(self, request_payload, request_id, job_id, few_shot_corpus_state):
        if self.response_delay_seconds > 0:
            await asyncio.sleep(self.response_delay_seconds)
        return _build_response()

    async def shutdown(self) -> None:
        return None


class _FakeJobStore:
    def __init__(self):
        self.records: dict[str, OptimizationJobPersistedRecord] = {}

    async def ping(self) -> None:
        return None

    async def close(self) -> None:
        return None

    async def create_job_record(self, job_record: OptimizationJobPersistedRecord, ttl_seconds: int) -> None:
        self.records[job_record.job_id] = job_record

    async def get_job_record(self, job_id: str) -> OptimizationJobPersistedRecord | None:
        return self.records.get(job_id)

    async def update_job_record_atomic(
        self,
        job_id: str,
        *,
        patch_fields: dict,
        ttl_seconds: int,
        expected_current_status: str | None = None,
    ) -> OptimizationJobPersistedRecord | None:
        existing_record = self.records.get(job_id)
        if existing_record is None:
            return None
        if expected_current_status is not None and existing_record.status != expected_current_status:
            return None
        updated_record = existing_record.model_copy(update=patch_fields)
        self.records[job_id] = updated_record
        return updated_record


class _FailingJobStore(_FakeJobStore):
    async def create_job_record(self, job_record: OptimizationJobPersistedRecord, ttl_seconds: int) -> None:
        raise RedisStoreConnectionError("redis unavailable")

    async def get_job_record(self, job_id: str) -> OptimizationJobPersistedRecord | None:
        raise RedisStoreConnectionError("redis unavailable")


def _build_request(evaluation_case_count: int = 0) -> OptimizationRequest:
    evaluation_dataset = None
    if evaluation_case_count > 0:
        evaluation_dataset = [
            {"input": f"input-{index}", "expected_output": f"expected-{index}"}
            for index in range(evaluation_case_count)
        ]
    return OptimizationRequest(
        raw_prompt="Summarize this text.",
        task_type="reasoning",
        framework="kernel",
        provider="openai",
        model_id="gpt-4.1-mini",
        model_label="GPT-4.1 Mini",
        is_reasoning_model=False,
        api_key="dummy",
        quality_gate_mode="off",
        evaluation_dataset=evaluation_dataset,
    )


def _build_response() -> OptimizationResponse:
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
        variants=[
            PromptVariant(
                id=1,
                name="Variant 1",
                strategy="test",
                system_prompt="system",
                user_prompt="user",
                token_estimate=1,
                tcrte_scores=VariantTCRTEScores(task=10, context=10, role=10, tone=10, execution=10),
                strengths=[],
                best_for="test",
                overshoot_guards=[],
                undershoot_guards=[],
            )
        ],
    )


@pytest.mark.asyncio
async def test_job_service_runs_background_job_to_completion():
    service = OptimizationJobService(
        execution_backend=_FakeExecutionBackend(),
        job_store=_FakeJobStore(),
    )

    created_job = await service.create_job(
        optimization_request=_build_request(),
        http_request=_DummyRequest(),
        request_id="request-123",
        trace_id="trace-123",
    )

    await asyncio.wait_for(service._background_tasks_by_job_id[created_job.job_id], timeout=1.0)

    status_response = await service.get_job_status(created_job.job_id)
    result_response = await service.get_job_result(created_job.job_id)

    assert status_response.status == "succeeded"
    assert status_response.current_phase == "completed"
    assert result_response.analysis.framework_applied == "kernel"


@pytest.mark.asyncio
async def test_job_service_result_raises_until_job_finishes():
    service = OptimizationJobService(
        execution_backend=_FakeExecutionBackend(response_delay_seconds=0.2),
        job_store=_FakeJobStore(),
    )

    created_job = await service.create_job(
        optimization_request=_build_request(),
        http_request=_DummyRequest(),
        request_id="request-123",
        trace_id="trace-123",
    )

    try:
        with pytest.raises(HTTPException) as error_info:
            await service.get_job_result(created_job.job_id)
        assert error_info.value.status_code == 409
    finally:
        service._background_tasks_by_job_id[created_job.job_id].cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await service._background_tasks_by_job_id[created_job.job_id]


@pytest.mark.asyncio
async def test_job_service_returns_503_when_store_unavailable():
    service = OptimizationJobService(
        execution_backend=_FakeExecutionBackend(),
        job_store=_FailingJobStore(),
    )

    with pytest.raises(HTTPException) as creation_error:
        await service.create_job(
            optimization_request=_build_request(),
            http_request=_DummyRequest(),
            request_id="request-123",
            trace_id="trace-123",
        )
    assert creation_error.value.status_code == 503

    with pytest.raises(HTTPException) as status_error:
        await service.get_job_status("job-123")
    assert status_error.value.status_code == 503


@pytest.mark.asyncio
async def test_job_service_rejects_request_over_budget_without_starting_worker():
    service = OptimizationJobService(
        execution_backend=_FakeExecutionBackend(),
        job_store=_FakeJobStore(),
    )

    with pytest.raises(HTTPException) as budget_error:
        await service.create_job(
            optimization_request=_build_request(evaluation_case_count=101),
            http_request=_DummyRequest(),
            request_id="request-123",
            trace_id="trace-123",
        )
    assert budget_error.value.status_code == 422
    assert len(service._background_tasks_by_job_id) == 0
    assert len(service._job_store.records) == 0


@pytest.mark.asyncio
async def test_cancel_queued_job_marks_cancelled_and_clears_background_task():
    fake_job_store = _FakeJobStore()
    service = OptimizationJobService(
        execution_backend=_FakeExecutionBackend(),
        job_store=fake_job_store,
    )
    queued_record = OptimizationJobPersistedRecord(
        job_id="job-queued",
        request_payload=_build_request().model_dump(mode="python"),
        status="queued",
        created_at="2026-03-30T00:00:00Z",
        updated_at="2026-03-30T00:00:00Z",
        current_phase="queued",
    )
    await fake_job_store.create_job_record(queued_record, ttl_seconds=60)
    dummy_task = asyncio.create_task(asyncio.sleep(5))
    service._background_tasks_by_job_id[queued_record.job_id] = dummy_task

    try:
        cancelled_status = await service.cancel_job(queued_record.job_id)
        assert cancelled_status.status == "cancelled"
        assert cancelled_status.current_phase == "cancelled"
        assert queued_record.job_id not in service._background_tasks_by_job_id
    finally:
        dummy_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await dummy_task


@pytest.mark.asyncio
async def test_cancel_running_job_prevents_final_success_overwrite():
    service = OptimizationJobService(
        execution_backend=_FakeExecutionBackend(response_delay_seconds=0.2),
        job_store=_FakeJobStore(),
    )
    created_job = await service.create_job(
        optimization_request=_build_request(),
        http_request=_DummyRequest(),
        request_id="request-123",
        trace_id="trace-123",
    )

    await asyncio.sleep(0.05)
    cancel_response = await service.cancel_job(created_job.job_id)
    assert cancel_response.status == "cancelled"

    background_task = service._background_tasks_by_job_id.get(created_job.job_id)
    if background_task is not None:
        await asyncio.wait_for(background_task, timeout=1.0)

    final_status = await service.get_job_status(created_job.job_id)
    assert final_status.status == "cancelled"

    with pytest.raises(HTTPException) as result_error:
        await service.get_job_result(created_job.job_id)
    assert result_error.value.status_code == 409
    assert "cancelled" in str(result_error.value.detail)
