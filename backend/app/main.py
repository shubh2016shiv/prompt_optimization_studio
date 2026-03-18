"""
APOST FastAPI Application Entry Point.

Configures the FastAPI application with CORS, routes, and static file serving.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import get_settings
from app.api.routes import gap_analysis, optimization, chat


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown events."""
    # Startup
    settings = get_settings()
    print(f"Starting {settings.app_name} v{settings.app_version}")
    yield
    # Shutdown
    print("Shutting down APOST API")


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
        return {
            "status": "healthy",
            "version": settings.app_version,
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
