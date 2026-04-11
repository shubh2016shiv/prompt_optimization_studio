import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.responses import (
    OptimizationAnalysis,
    OptimizationResponse,
    PromptVariant,
    TaskEvaluationCaseResult,
    TaskEvaluationResult,
    VariantTCRTEScores,
)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _base_payload(framework: str) -> dict:
    return {
        "raw_prompt": "Summarize this text.",
        "task_type": "reasoning",
        "framework": framework,
        "provider": "openai",
        "model_id": "gpt-4.1-mini",
        "model_label": "GPT-4.1 Mini",
        "is_reasoning_model": False,
        "gap_data": {
            "overall_score": 80,
            "complexity": "medium",
            "recommended_techniques": ["CoRe", "RAL-Writer"],
        },
        "answers": {},
        "api_key": "dummy",
        "quality_gate_mode": "off",
    }


def _payload_with_large_evaluation_dataset(framework: str, case_count: int) -> dict:
    payload = _base_payload(framework)
    payload["evaluation_dataset"] = [
        {"input": f"case-{index}", "expected_output": f"expected-{index}"}
        for index in range(case_count)
    ]
    return payload


def _build_pipeline_response(include_task_evaluation: bool) -> OptimizationResponse:
    task_evaluation = None
    if include_task_evaluation:
        task_evaluation = TaskEvaluationResult(
            task_success_score=84,
            pass_rate=1.0,
            total_cases=1,
            passed_cases=1,
            judging_mode="deterministic",
            pairwise_tie_break_applied=False,
            failure_reasons=[],
            case_results=[
                TaskEvaluationCaseResult(
                    case_index=1,
                    score=84,
                    status="pass",
                    scoring_method="deterministic",
                    failure_reason=None,
                )
            ],
        )

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
                task_evaluation=task_evaluation,
                strengths=[],
                best_for="test",
                overshoot_guards=[],
                undershoot_guards=[],
            )
        ],
    )


def test_optimize_route_returns_pipeline_response(client, monkeypatch):
    from app.api.routes import optimization as opt_route

    async def fake_execute(**kwargs):
        return _build_pipeline_response(include_task_evaluation=False)

    monkeypatch.setattr(opt_route, "execute_optimization_request", fake_execute)
    response = client.post("/api/optimize", json=_base_payload("kernel"))
    assert response.status_code == 200
    assert response.json()["analysis"]["few_shot_source"] == "not_applicable"
    assert response.json()["variants"][0]["task_evaluation"] is None


def test_optimize_route_returns_task_evaluation_when_pipeline_supplies_it(client, monkeypatch):
    from app.api.routes import optimization as opt_route

    async def fake_execute(**kwargs):
        return _build_pipeline_response(include_task_evaluation=True)

    monkeypatch.setattr(opt_route, "execute_optimization_request", fake_execute)
    response = client.post("/api/optimize", json=_base_payload("kernel"))
    assert response.status_code == 200
    assert response.json()["variants"][0]["task_evaluation"]["task_success_score"] == 84


def test_optimize_route_rejects_requests_over_evaluation_budget(client):
    response = client.post(
        "/api/optimize",
        json=_payload_with_large_evaluation_dataset("kernel", case_count=101),
    )
    assert response.status_code == 422
    assert "maximum is 100" in response.json()["detail"]


def test_optimize_route_rejects_opro_without_evaluation_dataset(client):
    response = client.post("/api/optimize", json=_base_payload("opro"))

    assert response.status_code == 422
    assert "OPRO requires evaluation_dataset" in response.json()["detail"]


def test_optimize_route_accepts_opro_with_evaluation_dataset(client, monkeypatch):
    from app.api.routes import optimization as opt_route

    async def fake_execute(**kwargs):
        return _build_pipeline_response(include_task_evaluation=False)

    monkeypatch.setattr(opt_route, "execute_optimization_request", fake_execute)

    payload = _base_payload("opro")
    payload["evaluation_dataset"] = [
        {"input": "case-1", "expected_output": "expected-1"}
    ]
    response = client.post("/api/optimize", json=payload)

    assert response.status_code == 200
