"""Request correlation middleware and helpers."""

from __future__ import annotations

from time import perf_counter
from uuid import uuid4

import structlog
from fastapi import FastAPI, Request

REQUEST_ID_HEADER = "X-Request-ID"
logger = structlog.get_logger(__name__)


def attach_request_context_middleware(app: FastAPI) -> None:
    """Attach middleware that binds request-scoped logging context."""

    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid4())
        start = perf_counter()

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            route=request.url.path,
            method=request.method,
        )
        request.state.request_id = request_id

        logger.info("http.request_started")

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((perf_counter() - start) * 1000, 2)
            logger.exception(
                "http.request_failed",
                status_code=500,
                duration_ms=duration_ms,
            )
            structlog.contextvars.clear_contextvars()
            raise

        duration_ms = round((perf_counter() - start) * 1000, 2)
        response.headers[REQUEST_ID_HEADER] = request_id
        logger.info(
            "http.request_completed",
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        structlog.contextvars.clear_contextvars()
        return response


def get_request_id(request: Request) -> str | None:
    """Return the request ID set by middleware."""
    return getattr(request.state, "request_id", None)
