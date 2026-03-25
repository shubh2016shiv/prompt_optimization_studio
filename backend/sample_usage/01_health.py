"""
Step 1 — Liveness: GET /api/health

Why this exists:
  FastAPI exposes a cheap endpoint for orchestration (Docker/K8s). It also surfaces
  whether the few-shot corpus embeddings were pre-computed at startup (main.py lifespan
  + knn_retriever.precompute_corpus_embeddings). That flag tells you if cot_ensemble
  can use Gemini kNN or will fall back to LLM-generated examples.

How to run:
  From repo root or backend: ensure uvicorn is running on port 8000, then:
    python sample_usage/01_health.py
"""

from __future__ import annotations

import sys

from common import http_json


def main() -> int:
    # Step 1: Call health — no API key; this only checks the process and app.state.
    status, data, raw = http_json("GET", "/api/health", json_body=None, timeout=10.0)
    if status != 200:
        print(f"Expected 200, got {status}: {raw[:500]}", file=sys.stderr)
        return 1
    if not isinstance(data, dict):
        print("Response is not a JSON object", file=sys.stderr)
        return 1

    # Step 2: Assert contract (matches app.main.health_check return shape).
    assert data.get("status") == "healthy", data
    assert "version" in data, data
    assert "knn_corpus_ready" in data, data
    assert isinstance(data["knn_corpus_ready"], bool), data

    print("OK /api/health:", data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
