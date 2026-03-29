from fastapi.testclient import TestClient

from app.main import app


def test_health_includes_observability_fields():
    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert "knn_corpus_ready" in body
    assert "judge_model" in body
    assert "openai_subtask_model" in body
    assert body["corpus_status"] in {"ready", "unavailable", "not_configured"}
