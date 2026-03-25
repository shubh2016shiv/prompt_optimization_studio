#!/usr/bin/env python3
"""
Start the APOST FastAPI backend (Uvicorn).

Cross-platform: run from the repository root with any Python 3.11+ that has backend
dependencies installed (e.g. after `pip install -e ./backend` or `uv sync` in backend).

  python start_backend.py
  python start_backend.py --reload --port 8000

Environment (optional):
  APOST_UVICORN_HOST   default 127.0.0.1
  APOST_UVICORN_PORT   default 8000
  APOST_UVICORN_RELOAD set to 1/true to enable --reload
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parent


def _backend_dir() -> Path:
    return _repo_root() / "backend"


def _truthy_env(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


def _mask_secret_set(name: str) -> str:
    return "set" if os.environ.get(name, "").strip() else "not set"


def _print_banner(
    *,
    app_name: str,
    app_version: str,
    backend: Path,
    host: str,
    port: int,
    reload: bool,
    cors_preview: str,
    max_tokens: tuple[int, int, int],
) -> None:
    line = "-" * 72
    base = f"http://{host}:{port}"
    print(line)
    print("  APOST Backend Server")
    print(line)
    print(f"  {'Application':<16} {app_name} v{app_version}")
    print(f"  {'ASGI module':<16} app.main:app")
    print(f"  {'Working dir':<16} {backend}")
    print(f"  {'Listen URL':<16} {base}")
    print(f"  {'OpenAPI (Swagger)':<16} {base}/api/docs")
    print(f"  {'ReDoc':<16} {base}/api/redoc")
    print(f"  {'Reload':<16} {'enabled' if reload else 'disabled'}")
    print(f"  {'CORS origins':<16} {cors_preview}")
    print(
        f"  {'Token limits':<16} "
        f"gap={max_tokens[0]}, optimize={max_tokens[1]}, chat={max_tokens[2]}"
    )
    print(f"  {'GOOGLE_API_KEY':<16} {_mask_secret_set('GOOGLE_API_KEY')} (kNN corpus at startup)")
    print(line)
    print("  Logs:")
    print(line)
    sys.stdout.flush()


def main() -> int:
    default_host = os.environ.get("APOST_UVICORN_HOST", "127.0.0.1").strip()
    default_port = int(os.environ.get("APOST_UVICORN_PORT", "8000"))
    default_reload = _truthy_env("APOST_UVICORN_RELOAD")

    parser = argparse.ArgumentParser(
        description="Start the APOST FastAPI backend with Uvicorn.",
    )
    parser.add_argument(
        "--host",
        default=default_host,
        help=f"Bind address (default: {default_host} or APOST_UVICORN_HOST)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=default_port,
        help=f"Port (default: {default_port} or APOST_UVICORN_PORT)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=default_reload,
        help="Enable auto-reload (or set APOST_UVICORN_RELOAD=1)",
    )
    parser.add_argument(
        "--no-reload",
        action="store_true",
        help="Disable reload even if APOST_UVICORN_RELOAD is set",
    )
    args = parser.parse_args()
    reload = args.reload and not args.no_reload

    backend = _backend_dir()
    if not backend.is_dir():
        print(f"Error: backend directory not found: {backend}", file=sys.stderr)
        return 1

    if not (backend / "app" / "main.py").is_file():
        print(f"Error: app.main not found under {backend}", file=sys.stderr)
        return 1

    os.chdir(backend)
    if str(backend) not in sys.path:
        sys.path.insert(0, str(backend))

    try:
        from dotenv import load_dotenv
    except ImportError:
        load_dotenv = None  # type: ignore[assignment,misc]

    env_file = backend / ".env"
    if load_dotenv and env_file.is_file():
        load_dotenv(env_file)

    try:
        from app.config import get_settings
    except ImportError as e:
        print(
            "Error: could not import app.config. Install backend dependencies, e.g.\n"
            "  cd backend && pip install -e .\n"
            f"Detail: {e}",
            file=sys.stderr,
        )
        return 1

    settings = get_settings()
    cors = settings.cors_origins_list
    cors_preview = ", ".join(cors[:4])
    if len(cors) > 4:
        cors_preview += f", ... (+{len(cors) - 4} more)"

    _print_banner(
        app_name=settings.app_name,
        app_version=settings.app_version,
        backend=backend,
        host=args.host,
        port=args.port,
        reload=reload,
        cors_preview=cors_preview or "(none)",
        max_tokens=(
            settings.max_tokens_gap_analysis,
            settings.max_tokens_optimization,
            settings.max_tokens_chat,
        ),
    )

    try:
        import uvicorn
    except ImportError:
        print("Error: uvicorn is not installed.", file=sys.stderr)
        return 1

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=reload,
        factory=False,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
