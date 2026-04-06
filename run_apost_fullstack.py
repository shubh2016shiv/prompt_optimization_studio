#!/usr/bin/env python3
"""
Run the complete APOST stack locally via Docker Compose.

This script is intentionally placed in project root so new users can discover it
immediately. It manages:
  - redis dependency container
  - apost application container (backend API + built frontend)
"""

from __future__ import annotations

import argparse
import http.client
import shutil
import subprocess
import sys
import time
import webbrowser
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent
COMPOSE_FILE = REPO_ROOT / "docker-compose.yml"
BACKEND_ENV = REPO_ROOT / "backend" / ".env"
BACKEND_ENV_EXAMPLE = REPO_ROOT / "backend" / ".env.example"
APP_URL = "http://127.0.0.1:8000"
API_DOCS_URL = f"{APP_URL}/api/docs"
OPENAPI_URL = f"{APP_URL}/api/openapi.json"
LIVE_HEALTH_URL = f"{APP_URL}/api/health/live"


def _compose_cmd(*args: str) -> list[str]:
    return ["docker", "compose", "-f", str(COMPOSE_FILE), *args]


def _run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=check, text=True)


def assert_docker_available() -> None:
    result = subprocess.run(
        ["docker", "version", "--format", "{{.Server.Version}}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError("Docker is not available. Start Docker Desktop/Engine and retry.")


def ensure_backend_env_file() -> None:
    if BACKEND_ENV.exists():
        return

    if not BACKEND_ENV_EXAMPLE.exists():
        raise RuntimeError(f"Missing backend environment template: {BACKEND_ENV_EXAMPLE}")

    BACKEND_ENV.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(BACKEND_ENV_EXAMPLE, BACKEND_ENV)
    print("Created backend/.env from backend/.env.example")


def _healthcheck_once() -> bool:
    connection = http.client.HTTPConnection("127.0.0.1", 8000, timeout=5)
    try:
        connection.request("GET", "/api/health/live")
        response = connection.getresponse()
        response.read()  # Drain socket to allow clean reuse/close.
        return response.status == 200
    finally:
        connection.close()


def print_compose_diagnostics() -> None:
    print()
    print("Startup diagnostics:")
    try:
        _run(_compose_cmd("ps"), check=False)
    except Exception:
        pass

    try:
        _run(_compose_cmd("logs", "--tail=80", "apost"), check=False)
    except Exception:
        pass


def wait_for_health(timeout_seconds: int) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            if _healthcheck_once():
                print(f"APOST is healthy at {LIVE_HEALTH_URL}")
                return
        except (
            TimeoutError,
            http.client.HTTPException,
            ConnectionError,
            OSError,
        ):
            # During startup, the socket can accept and then close while the app
            # process is still initializing. Treat these as retryable.
            time.sleep(2)

    print_compose_diagnostics()
    raise RuntimeError(f"Timed out waiting for health endpoint: {LIVE_HEALTH_URL}")


def print_access_urls() -> None:
    print()
    print("Open these links:")
    print(f"- Frontend:      {APP_URL}")
    print(f"- Backend docs:  {API_DOCS_URL}")
    print(f"- Backend spec:  {OPENAPI_URL}")
    print(f"- Health (live): {LIVE_HEALTH_URL}")


def open_common_urls() -> None:
    webbrowser.open(APP_URL)
    webbrowser.open(API_DOCS_URL)


def cmd_up(no_build: bool, health_timeout_seconds: int, open_browser: bool) -> None:
    ensure_backend_env_file()
    args = ["up", "-d"]
    if not no_build:
        args.append("--build")
    args.extend(["redis", "apost"])
    _run(_compose_cmd(*args))
    wait_for_health(health_timeout_seconds)
    print_access_urls()
    if open_browser:
        open_common_urls()


def cmd_down() -> None:
    _run(_compose_cmd("down", "--remove-orphans"))


def cmd_status() -> None:
    _run(_compose_cmd("ps"))
    print_access_urls()


def cmd_logs() -> None:
    _run(_compose_cmd("logs", "-f", "redis", "apost"))


def cmd_urls(open_browser: bool) -> None:
    print_access_urls()
    if open_browser:
        open_common_urls()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run and operate the full APOST stack (frontend + backend + redis).",
    )
    subparsers = parser.add_subparsers(dest="action", required=True)

    up_parser = subparsers.add_parser("up", help="Build and start redis + apost, then wait for health.")
    up_parser.add_argument(
        "--no-build",
        action="store_true",
        help="Skip image build and use existing local image layers.",
    )
    up_parser.add_argument(
        "--health-timeout-seconds",
        type=int,
        default=120,
        help="Seconds to wait for /api/health/live before failing (default: 120).",
    )
    up_parser.add_argument(
        "--open",
        action="store_true",
        help="Open frontend and backend docs URLs in the default browser after startup.",
    )

    subparsers.add_parser("down", help="Stop and remove stack containers.")
    subparsers.add_parser("status", help="Show docker compose service status.")
    subparsers.add_parser("logs", help="Tail redis + apost logs.")
    urls_parser = subparsers.add_parser("urls", help="Print quick-access URLs for frontend and backend.")
    urls_parser.add_argument(
        "--open",
        action="store_true",
        help="Open frontend and backend docs URLs in the default browser.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        assert_docker_available()

        if args.action == "up":
            cmd_up(args.no_build, args.health_timeout_seconds, args.open)
        elif args.action == "down":
            cmd_down()
        elif args.action == "status":
            cmd_status()
        elif args.action == "logs":
            cmd_logs()
        elif args.action == "urls":
            cmd_urls(args.open)
        else:
            parser.error(f"Unknown action: {args.action}")
            return 2
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as error:
        return error.returncode

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
