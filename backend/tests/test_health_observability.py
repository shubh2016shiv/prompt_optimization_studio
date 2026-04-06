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
    assert "dependencies" in body
    assert "openai_chat" in body["dependencies"]
    assert "google_embeddings" in body["dependencies"]


def test_live_health_endpoint_is_available():
    with TestClient(app) as client:
        response = client.get("/api/health/live")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "service" in body
    assert "version" in body
    assert "uptime_seconds" in body
