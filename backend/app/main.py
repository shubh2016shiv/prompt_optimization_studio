"""
APOST FastAPI Application Entry Point.

Configures the FastAPI application with CORS, routes, and static file serving.
Also manages application lifecycle: pre-computing the few-shot corpus embeddings
at startup so they are ready for kNN retrieval without cold-start latency.
"""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import get_settings
from app.api.routes import gap_analysis, optimization, chat

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.

    Startup: pre-computes Gemini embeddings for the entire few-shot corpus so that
    kNN retrieval during cot_ensemble optimization requires only one live embedding
    call (for the query) rather than re-embedding the corpus on every request.

    The computation uses GOOGLE_API_KEY from the environment. If the key is absent,
    the corpus is set to None and the kNN path falls back gracefully to LLM-generated
    examples — no error is raised.
    """
    settings = get_settings()
    logger.info("Starting %s v%s", settings.app_name, settings.app_version)

    # Pre-compute corpus embeddings (non-blocking: failure does not crash startup)
    google_key = os.getenv("GOOGLE_API_KEY")
    if google_key:
        try:
            from app.services.optimization.knn_retriever import precompute_corpus_embeddings
            logger.info("Pre-computing few-shot corpus embeddings via Gemini API...")
            app.state.few_shot_corpus = await precompute_corpus_embeddings(google_key)
            logger.info("Corpus embeddings ready.")
        except Exception as exc:
            logger.warning(
                "Failed to pre-compute corpus embeddings (%s). "
                "cot_ensemble will use LLM-generated examples as fallback.", exc
            )
            app.state.few_shot_corpus = None
    else:
        logger.info(
            "GOOGLE_API_KEY not set — skipping corpus pre-computation. "
            "cot_ensemble kNN retrieval will be unavailable."
        )
        app.state.few_shot_corpus = None

    yield

    logger.info("Shutting down %s", settings.app_name)


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

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

    # Register API routes
    app.include_router(gap_analysis.router, prefix="/api", tags=["Gap Analysis"])
    app.include_router(optimization.router, prefix="/api", tags=["Optimization"])
    app.include_router(chat.router, prefix="/api", tags=["Chat"])

    # Health check endpoint
    @app.get("/api/health", tags=["Health"])
    async def health_check():
        """Health check endpoint for container orchestration."""
        corpus_ready = getattr(app.state, "few_shot_corpus", None) is not None
        return {
            "status": "healthy",
            "version": settings.app_version,
            "knn_corpus_ready": corpus_ready,
        }

    # Serve static files (React build) in production
    static_path = Path(__file__).parent.parent.parent / "static"
    if static_path.exists():
        app.mount("/assets", StaticFiles(directory=static_path / "assets"), name="assets")

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            """Serve the React SPA for all non-API routes."""
            index_path = static_path / "index.html"
            if index_path.exists():
                return FileResponse(index_path)
            return {"error": "Frontend not built"}

    return app


app = create_application()
