"""
Purpose:
  Validate backend liveness and health contract readiness.

Scope:
  - Calls GET /api/health.
  - Verifies required fields including knn_corpus_ready.

Method:
  - Execute health request without API key.
  - Assert response contract and print concise outcome.

Artifacts:
  - Console output only.

Run:
  python sample_usage/smoke_healthcheck.py
"""

from __future__ import annotations

import sys

from sample_runtime import http_json


def main() -> int:
    status, data, raw = http_json("GET", "/api/health", json_body=None, timeout=10.0)
    if status != 200:
        print(f"Expected 200, got {status}: {raw[:500]}", file=sys.stderr)
        return 1
    if not isinstance(data, dict):
        print("Response is not a JSON object", file=sys.stderr)
        return 1

    assert data.get("status") == "healthy", data
    assert "version" in data, data
    assert "knn_corpus_ready" in data, data
    assert isinstance(data["knn_corpus_ready"], bool), data

    print("OK /api/health:", data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

