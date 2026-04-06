"""
APOST FastAPI Application Entry Point.

Configures the FastAPI application with CORS, routes, and static file serving.
Also manages application lifecycle with durable Redis-backed orchestration.
"""

import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import chat, gap_analysis, optimization, optimization_jobs
from app.config import get_settings
from app.observability.logging_setup import setup_logging
from app.observability.request_context import attach_request_context_middleware
from app.services.health_checks import run_health_probes
from app.services.optimization.optimization_job_service import OptimizationJobService
from app.services.store.redis_store import RedisStore

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage startup/shutdown dependencies for the API process.

    Startup:
      - initialize Redis adapter and verify connectivity
      - initialize durable OptimizationJobService that depends on Redis
      - keep few-shot corpus lazy (computed on-demand and cache-backed)

    Shutdown:
      - gracefully stop background worker backend
      - close Redis resources to avoid socket leaks
    """
    settings = get_settings()
    logger.info(
        "app.starting",
        app_name=settings.app_name,
        app_version=settings.app_version,
    )

    # Build Redis adapter first. Job creation should not proceed unless durable
    # persistence is at least initialized.
    redis_store = RedisStore()
    try:
        await redis_store.ping()
        logger.info("redis.startup_ping_succeeded")
    except Exception as redis_error:
        logger.critical("redis.startup_ping_failed", error=str(redis_error))
        if settings.redis_fail_fast:
            # Fail fast in strict production mode where durable job storage is required.
            raise SystemExit(1)

    app.state.redis_store = redis_store
    app.state.optimization_job_service = OptimizationJobService(job_store=redis_store)
    app.state.started_at_utc = datetime.now(timezone.utc)

    # Corpus is now lazy and cache-backed, so no expensive warm-up at startup.
    app.state.few_shot_corpus = None

    yield

    optimization_job_service = getattr(app.state, "optimization_job_service", None)
    if optimization_job_service is not None:
        await optimization_job_service.shutdown()

    # Defensive fallback: if service was not initialized, still close Redis.
    redis_store_instance = getattr(app.state, "redis_store", None)
    if redis_store_instance is not None and optimization_job_service is None:
        await redis_store_instance.close()

    logger.info("app.stopping", app_name=settings.app_name)


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    setup_logging(settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Automated Prompt Optimisation & Structuring Tool API",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    attach_request_context_middleware(app)

    # Register API routes
    app.include_router(gap_analysis.router, prefix="/api", tags=["Gap Analysis"])
    app.include_router(optimization.router, prefix="/api", tags=["Optimization"])
    app.include_router(optimization_jobs.router, prefix="/api", tags=["Optimization Jobs"])
    app.include_router(chat.router, prefix="/api", tags=["Chat"])

    # Health check endpoint
    @app.get("/api/health/live", tags=["Health"])
    async def liveness_check():
        """Lightweight process-level liveness endpoint for frontend heartbeat polling."""
        started_at = getattr(app.state, "started_at_utc", None)
        uptime_seconds = None
        if started_at is not None:
            uptime_seconds = round(
                max(0.0, (datetime.now(timezone.utc) - started_at).total_seconds()),
                3,
            )

        return {
            "status": "ok",
            "service": settings.app_name,
            "version": settings.app_version,
            "uptime_seconds": uptime_seconds,
        }

    @app.get("/api/health", tags=["Health"])
    async def health_check():
        """Health check endpoint with active dependency probes."""
        from app.services.evaluation.evaluation_rubric import LLM_JUDGE_MODEL

        corpus_ready = getattr(app.state, "few_shot_corpus", None) is not None
        google_key_present = bool(os.getenv("GOOGLE_API_KEY"))
        if not google_key_present:
            corpus_status = "not_configured"
        elif corpus_ready:
            corpus_status = "ready"
        else:
            corpus_status = "unavailable"

        probe_results = await run_health_probes(settings=settings, corpus_ready=corpus_ready)

        redis_store = getattr(app.state, "redis_store", None)
        redis_status = {"status": "not_configured"}
        if redis_store is not None:
            try:
                await redis_store.ping()
                redis_status = {"status": "ok"}
            except Exception as redis_error:
                redis_status = {"status": "down", "error": str(redis_error)}
                if probe_results["status"] == "healthy":
                    probe_results["status"] = "degraded"

        probe_results["dependencies"]["redis"] = redis_status

        return {
            "status": probe_results["status"],
            "version": settings.app_version,
            "knn_corpus_ready": corpus_ready,
            "judge_model": LLM_JUDGE_MODEL,
            "openai_subtask_model": settings.openai_subtask_model,
            "corpus_status": corpus_status,
            "dependencies": probe_results["dependencies"],
        }

    # Serve static files (React build) in production
    static_path = Path(__file__).parent.parent / "static"
    if static_path.exists():
        app.mount("/assets", StaticFiles(directory=static_path / "assets"), name="assets")

        @app.get("/")
        async def serve_root():
            """Serve React SPA root path."""
            index_path = static_path / "index.html"
            if index_path.exists():
                return FileResponse(index_path)
            return {"error": "Frontend not built"}

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            """Serve the React SPA for all non-API routes."""
            index_path = static_path / "index.html"
            if index_path.exists():
                return FileResponse(index_path)
            return {"error": "Frontend not built"}

    return app


app = create_application()
