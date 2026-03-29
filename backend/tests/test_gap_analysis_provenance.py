from fastapi.testclient import TestClient

from app.main import app


class DummyLLMClient:
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


def _payload() -> dict:
    return {
        "raw_prompt": "Summarize this text",
        "provider": "openai",
        "model_id": "gpt-4.1-mini",
        "api_key": "secret-key",
    }


def test_gap_analysis_marks_deterministic_tcrte_source(monkeypatch):
    from app.api.routes import gap_analysis as gap_route

    async def fake_score(*args, **kwargs):
        return {
            "task": {"score": 61, "note": "task"},
            "context": {"score": 62, "note": "context"},
            "role": {"score": 63, "note": "role"},
            "tone": {"score": 64, "note": "tone"},
            "execution": {"score": 65, "note": "execution"},
            "overall_score": 63,
        }

    monkeypatch.setattr(gap_route, "score_tcrte", fake_score)
    monkeypatch.setattr(gap_route, "LLMClient", DummyLLMClient)

    with TestClient(app) as client:
        response = client.post("/api/gap-analysis", json=_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["tcrte_scores_source"] == "openai_deterministic"
    assert body["overall_score"] == 63


def test_gap_analysis_marks_model_estimated_tcrte_source_on_fallback(monkeypatch):
    from app.api.routes import gap_analysis as gap_route

    async def fake_score(*args, **kwargs):
        raise RuntimeError("openai scorer unavailable")

    monkeypatch.setattr(gap_route, "score_tcrte", fake_score)
    monkeypatch.setattr(gap_route, "LLMClient", DummyLLMClient)

    with TestClient(app) as client:
        response = client.post("/api/gap-analysis", json=_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["tcrte_scores_source"] == "model_estimated"
    assert body["overall_score"] == 50
