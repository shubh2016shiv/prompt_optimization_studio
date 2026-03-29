import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.responses import (
    OptimizationAnalysis,
    OptimizationResponse,
    PromptVariant,
    VariantTCRTEScores,
)


class DummyStrategy:
    async def generate_variants(self, request, core_k=2, few_shot_examples=None, auto_reason=None):
        return OptimizationResponse(
            analysis=OptimizationAnalysis(
                detected_issues=[],
                model_notes="",
                framework_applied=request.framework,
                coverage_delta="",
                auto_selected_framework=None,
                auto_reason=auto_reason,
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
        "gap_data": {"overall_score": 80, "complexity": "standard"},
        "answers": {},
        "api_key": "dummy",
        "quality_gate_mode": "off",
    }


def test_optimize_sets_few_shot_source_not_applicable(client, monkeypatch):
    from app.api.routes import optimization as opt_route

    monkeypatch.setattr(opt_route.OptimizerFactory, "get_optimizer", lambda _f: DummyStrategy())
    response = client.post("/api/optimize", json=_base_payload("kernel"))
    assert response.status_code == 200
    assert response.json()["analysis"]["few_shot_source"] == "not_applicable"


def test_optimize_sets_few_shot_source_knn(client, monkeypatch):
    from app.api.routes import optimization as opt_route

    async def fake_count(*args, **kwargs):
        return 2

    async def fake_retrieve(*args, **kwargs):
        return [{"input": "a", "output": "b"}]

    monkeypatch.setattr(opt_route.OptimizerFactory, "get_optimizer", lambda _f: DummyStrategy())
    monkeypatch.setattr(opt_route, "count_reasoning_hops", fake_count)
    monkeypatch.setattr(opt_route, "retrieve_k_nearest", fake_retrieve)
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    app.state.few_shot_corpus = [{"id": "x"}]

    response = client.post("/api/optimize", json=_base_payload("cot_ensemble"))
    assert response.status_code == 200
    assert response.json()["analysis"]["few_shot_source"] == "knn"


def test_optimize_sets_few_shot_source_synthetic_on_retrieval_failure(client, monkeypatch):
    from app.api.routes import optimization as opt_route

    async def fake_count(*args, **kwargs):
        return 2

    async def fail_retrieve(*args, **kwargs):
        raise RuntimeError("knn unavailable")

    monkeypatch.setattr(opt_route.OptimizerFactory, "get_optimizer", lambda _f: DummyStrategy())
    monkeypatch.setattr(opt_route, "count_reasoning_hops", fake_count)
    monkeypatch.setattr(opt_route, "retrieve_k_nearest", fail_retrieve)
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    app.state.few_shot_corpus = [{"id": "x"}]

    response = client.post("/api/optimize", json=_base_payload("cot_ensemble"))
    assert response.status_code == 200
    assert response.json()["analysis"]["few_shot_source"] == "synthetic"
