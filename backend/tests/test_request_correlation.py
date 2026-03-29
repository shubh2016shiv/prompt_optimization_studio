import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.responses import (
    OptimizationAnalysis,
    OptimizationJobCreatedResponse,
    OptimizationResponse,
    PromptVariant,
    VariantTCRTEScores,
)


class _DummyLLMClient:
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def call(self, **kwargs):
        return (
            '{"tcrte":{"task":{"score":50,"status":"weak","note":"n"},'
            '"context":{"score":50,"status":"weak","note":"n"},'
            '"role":{"score":50,"status":"weak","note":"n"},'
            '"tone":{"score":50,"status":"weak","note":"n"},'
            '"execution":{"score":50,"status":"weak","note":"n"}},'
            '"overall_score":50,"complexity":"medium","complexity_reason":"r",'
            '"recommended_techniques":["CoRe"],"questions":[],"auto_enrichments":[]}'
        )

    async def call_chat(self, **kwargs):
        return "ok"


class _DummyJobService:
    async def create_job(self, optimization_request, http_request, request_id, trace_id):
        return OptimizationJobCreatedResponse(
            job_id="job-123",
            status="queued",
            created_at="2026-03-29T00:00:00Z",
            request_id=request_id,
            trace_id=trace_id,
        )


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_request_id_generated_when_missing(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID")


def test_request_id_preserved_when_provided(client):
    response = client.get("/api/health", headers={"X-Request-ID": "req-123"})
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == "req-123"


def test_request_id_header_present_across_routes(client, monkeypatch):
    from app.api.routes import gap_analysis as gap_route
    from app.api.routes import chat as chat_route
    from app.api.routes import optimization as opt_route

    async def fake_score(*args, **kwargs):
        return None

    async def fake_execute_optimization_request(**kwargs):
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

    monkeypatch.setattr(gap_route, "score_tcrte", fake_score)
    monkeypatch.setattr(gap_route, "LLMClient", _DummyLLMClient)
    monkeypatch.setattr(chat_route, "LLMClient", _DummyLLMClient)
    monkeypatch.setattr(opt_route, "execute_optimization_request", fake_execute_optimization_request)
    monkeypatch.setattr(app.state, "optimization_job_service", _DummyJobService())

    header = {"X-Request-ID": "shared-request-id"}

    gap_response = client.post(
        "/api/gap-analysis",
        headers=header,
        json={
            "raw_prompt": "Summarize this text",
            "provider": "openai",
            "model_id": "gpt-4.1-mini",
            "api_key": "secret-key",
        },
    )
    assert gap_response.status_code == 200
    assert gap_response.headers.get("X-Request-ID") == "shared-request-id"

    optimize_response = client.post(
        "/api/optimize",
        headers=header,
        json={
            "raw_prompt": "Summarize this text",
            "framework": "kernel",
            "provider": "openai",
            "model_id": "gpt-4.1-mini",
            "api_key": "secret-key",
            "quality_gate_mode": "off",
        },
    )
    assert optimize_response.status_code == 200
    assert optimize_response.headers.get("X-Request-ID") == "shared-request-id"

    optimize_job_response = client.post(
        "/api/optimize/jobs",
        headers=header,
        json={
            "raw_prompt": "Summarize this text",
            "framework": "kernel",
            "provider": "openai",
            "model_id": "gpt-4.1-mini",
            "api_key": "secret-key",
            "quality_gate_mode": "off",
        },
    )
    assert optimize_job_response.status_code == 200
    assert optimize_job_response.headers.get("X-Request-ID") == "shared-request-id"

    chat_response = client.post(
        "/api/chat",
        headers=header,
        json={
            "message": "hello",
            "provider": "openai",
            "model_id": "gpt-4.1-mini",
            "api_key": "secret-key",
        },
    )
    assert chat_response.status_code == 200
    assert chat_response.headers.get("X-Request-ID") == "shared-request-id"

    health_response = client.get("/api/health", headers=header)
    assert health_response.status_code == 200
    assert health_response.headers.get("X-Request-ID") == "shared-request-id"
