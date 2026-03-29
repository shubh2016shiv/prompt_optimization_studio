import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.responses import (
    OptimizationAnalysis,
    OptimizationJobCreatedResponse,
    OptimizationJobStatusResponse,
    OptimizationResponse,
    PromptVariant,
    VariantTCRTEScores,
)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _base_payload() -> dict:
    return {
        "raw_prompt": "Summarize this text.",
        "task_type": "reasoning",
        "framework": "kernel",
        "provider": "openai",
        "model_id": "gpt-4.1-mini",
        "model_label": "GPT-4.1 Mini",
        "is_reasoning_model": False,
        "answers": {},
        "api_key": "dummy",
        "quality_gate_mode": "off",
    }


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
                name="V1",
                strategy="test",
                system_prompt="s",
                user_prompt="u",
                token_estimate=1,
                tcrte_scores=VariantTCRTEScores(task=10, context=10, role=10, tone=10, execution=10),
                strengths=[],
                best_for="test",
                overshoot_guards=[],
                undershoot_guards=[],
            )
        ],
    )


def test_create_optimization_job_returns_job_metadata(client, monkeypatch):
    async def fake_create_job(**kwargs):
        return OptimizationJobCreatedResponse(
            job_id="job-123",
            status="queued",
            created_at="2026-03-29T00:00:00Z",
            request_id="request-123",
            trace_id="trace-123",
        )

    monkeypatch.setattr(app.state.optimization_job_service, "create_job", fake_create_job)
    response = client.post("/api/optimize/jobs", json=_base_payload())
    assert response.status_code == 200
    assert response.json()["job_id"] == "job-123"
    assert response.json()["status"] == "queued"


def test_get_optimization_job_status_returns_progress(client, monkeypatch):
    async def fake_get_status(job_id: str):
        return OptimizationJobStatusResponse(
            job_id=job_id,
            status="running",
            created_at="2026-03-29T00:00:00Z",
            updated_at="2026-03-29T00:01:00Z",
            current_phase="generating_variants",
            request_id="request-123",
            trace_id="trace-123",
            run_id=None,
            error_message=None,
        )

    monkeypatch.setattr(app.state.optimization_job_service, "get_job_status", fake_get_status)
    response = client.get("/api/optimize/jobs/job-123")
    assert response.status_code == 200
    assert response.json()["status"] == "running"
    assert response.json()["current_phase"] == "generating_variants"


def test_get_optimization_job_result_returns_optimization_payload(client, monkeypatch):
    async def fake_get_result(job_id: str):
        return _build_response()

    monkeypatch.setattr(app.state.optimization_job_service, "get_job_result", fake_get_result)
    response = client.get("/api/optimize/jobs/job-123/result")
    assert response.status_code == 200
    assert response.json()["analysis"]["framework_applied"] == "kernel"
