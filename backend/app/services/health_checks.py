"""Active health probes for external dependencies."""

from __future__ import annotations

import os
from time import perf_counter
from typing import Any

import httpx
import structlog

from app.config import Settings

logger = structlog.get_logger(__name__)
_GOOGLE_EMBED_URL = (
    "https://generativelanguage.googleapis.com/v1beta/"
    "models/gemini-embedding-001:embedContent"
)


async def run_health_probes(
    *,
    settings: Settings,
    corpus_ready: bool,
) -> dict[str, Any]:
    """Run active dependency probes and return a machine-readable status block."""
    openai_result = await _probe_openai(settings=settings)
    google_result = await _probe_google_embeddings(settings=settings)

    # Overall health should reflect hard failures of core request-serving
    # dependencies. Transient or optional probe degradation should not cause
    # flaky "unhealthy" signals.
    overall_status = "healthy"
    if openai_result["status"] == "down":
        overall_status = "degraded"

    dependency_status = {
        "openai_chat": openai_result,
        "google_embeddings": google_result,
        "corpus": {
            "status": "ok" if corpus_ready else "degraded",
            "ready": corpus_ready,
        },
    }
    logger.info(
        "health.probes_completed",
        status=overall_status,
        dependencies=dependency_status,
    )
    return {
        "status": overall_status,
        "dependencies": dependency_status,
    }


async def _probe_openai(*, settings: Settings) -> dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {"status": "not_configured"}

    payload = {
        "model": settings.openai_subtask_model,
        "messages": [{"role": "user", "content": "healthcheck"}],
        "max_tokens": 1,
        "temperature": 0,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    started = perf_counter()
    try:
        async with httpx.AsyncClient(timeout=settings.health_probe_timeout_seconds) as client:
            response = await client.post(
                settings.openai_chat_completions_url,
                headers=headers,
                json=payload,
            )
        latency_ms = round((perf_counter() - started) * 1000, 2)
        if response.status_code == 200:
            return {"status": "ok", "latency_ms": latency_ms}
        return {
            "status": "down",
            "latency_ms": latency_ms,
            "status_code": response.status_code,
            "error": "non_200_response",
        }
    except Exception as exc:
        latency_ms = round((perf_counter() - started) * 1000, 2)
        return {"status": "down", "latency_ms": latency_ms, "error": str(exc)}


async def _probe_google_embeddings(*, settings: Settings) -> dict[str, Any]:
    google_key = os.getenv("GOOGLE_API_KEY")
    if not google_key:
        return {"status": "not_configured"}

    payload = {
        "model": "models/gemini-embedding-001",
        "content": {"parts": [{"text": "healthcheck"}]},
        "output_dimensionality": 8,
    }
    url = f"{_GOOGLE_EMBED_URL}?key={google_key}"

    started = perf_counter()
    try:
        async with httpx.AsyncClient(timeout=settings.health_probe_timeout_seconds) as client:
            response = await client.post(url, json=payload)
        latency_ms = round((perf_counter() - started) * 1000, 2)
        if response.status_code == 200:
            return {"status": "ok", "latency_ms": latency_ms}
        if response.status_code == 429:
            # Quota/rate-limit responses are often transient. Report as degraded
            # so operators see pressure without flapping global health status.
            return {
                "status": "degraded",
                "latency_ms": latency_ms,
                "status_code": response.status_code,
                "error": "rate_limited",
                "transient": True,
            }
        return {
            "status": "down",
            "latency_ms": latency_ms,
            "status_code": response.status_code,
            "error": "non_200_response",
        }
    except Exception as exc:
        latency_ms = round((perf_counter() - started) * 1000, 2)
        return {"status": "down", "latency_ms": latency_ms, "error": str(exc)}
