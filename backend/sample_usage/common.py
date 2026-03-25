"""
Shared helpers for sample_usage scripts.

Loads environment from backend/.env (python-dotenv). Endpoints expect the same
per-request API key pattern as the React UI: the key for the provider you choose.

Environment variables (optional overrides):
  APOST_SAMPLE_BASE_URL   — default http://127.0.0.1:8000
  APOST_TEST_API_KEY      — preferred single key for scripts
  APOST_TEST_PROVIDER     — anthropic | openai | google (default: openai)
  APOST_TEST_MODEL_ID     — model id string for that provider
  APOST_TEST_MODEL_LABEL  — human label for gap-analysis request

If APOST_TEST_API_KEY is unset, falls back to OPENAI_API_KEY, then ANTHROPIC_API_KEY,
then GOOGLE_API_KEY / GEMINI_API_KEY depending on provider.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx

_BACKEND_ROOT = Path(__file__).resolve().parent.parent


def load_backend_env() -> None:
    """Load backend/.env so keys match uvicorn's working directory conventions."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    env_path = _BACKEND_ROOT / ".env"
    if env_path.is_file():
        load_dotenv(env_path)


def base_url() -> str:
    load_backend_env()
    return os.environ.get("APOST_SAMPLE_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


def test_provider() -> str:
    load_backend_env()
    return os.environ.get("APOST_TEST_PROVIDER", "openai").strip().lower()


def test_model_id() -> str:
    load_backend_env()
    defaults = {
        "openai": "gpt-4o",
        "anthropic": "claude-sonnet-4-6",
        "google": "gemini-2.5-flash",
    }
    p = test_provider()
    return os.environ.get("APOST_TEST_MODEL_ID", defaults.get(p, "gpt-4o")).strip()


def test_model_label() -> str:
    load_backend_env()
    return os.environ.get("APOST_TEST_MODEL_LABEL", test_model_id()).strip()


def resolve_api_key() -> str:
    """
    Resolve an API key for the configured test provider.

    Gap analysis (app.services.scoring.tcrte_scorer) uses OpenAI gpt-4.1-nano for
    deterministic TCRTE pre-scoring with the *same* request api_key. If you only
    have an Anthropic key, pre-scoring fails gracefully and the main model scores TCRTE.
    """
    load_backend_env()
    explicit = os.environ.get("APOST_TEST_API_KEY", "").strip()
    if explicit:
        return explicit
    p = test_provider()
    if p == "openai":
        return os.environ.get("OPENAI_API_KEY", "").strip()
    if p == "anthropic":
        return os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if p == "google":
        return (
            os.environ.get("GOOGLE_API_KEY", "").strip()
            or os.environ.get("GEMINI_API_KEY", "").strip()
        )
    return os.environ.get("OPENAI_API_KEY", "").strip()


def require_api_key() -> str:
    key = resolve_api_key()
    if not key:
        print(
            "Missing API key. Set APOST_TEST_API_KEY or the provider-specific env var.",
            file=sys.stderr,
        )
        sys.exit(2)
    return key


def http_json(
    method: str,
    path: str,
    *,
    json_body: dict | None = None,
    timeout: float = 120.0,
) -> tuple[int, dict | list | None, str]:
    """Perform HTTP request; return (status, parsed_json_or_none, raw_text)."""
    url = f"{base_url()}{path}"
    try:
        with httpx.Client(timeout=timeout) as client:
            r = client.request(method, url, json=json_body)
    except httpx.ConnectError as e:
        print(f"Cannot connect to {url}: {e}", file=sys.stderr)
        sys.exit(3)
    text = r.text
    try:
        data = r.json()
    except json.JSONDecodeError:
        data = None
    return r.status_code, data, text


def print_json(title: str, obj: object) -> None:
    print(f"\n--- {title} ---")
    print(json.dumps(obj, indent=2, ensure_ascii=False)[:8000])
    if isinstance(obj, str) and len(obj) > 8000:
        print("... [truncated]")
