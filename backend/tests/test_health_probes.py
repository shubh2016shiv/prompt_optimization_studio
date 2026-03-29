import httpx
import pytest

from app.config import get_settings
from app.services import health_checks


class _FakeResponse:
    def __init__(self, status_code: int):
        self.status_code = status_code


class _FakeClient:
    def __init__(self, response_status: int = 200, raise_error: bool = False, timeout=None):
        self.response_status = response_status
        self.raise_error = raise_error
        self.timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, *args, **kwargs):
        if self.raise_error:
            raise httpx.ConnectError("failed")
        return _FakeResponse(self.response_status)


@pytest.mark.asyncio
async def test_openai_probe_not_configured(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = await health_checks._probe_openai(settings=get_settings())
    assert result["status"] == "not_configured"


@pytest.mark.asyncio
async def test_google_probe_not_configured(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    result = await health_checks._probe_google_embeddings(settings=get_settings())
    assert result["status"] == "not_configured"


@pytest.mark.asyncio
async def test_health_probe_success(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(health_checks.httpx, "AsyncClient", lambda timeout: _FakeClient(response_status=200, timeout=timeout))

    result = await health_checks._probe_openai(settings=get_settings())
    assert result["status"] == "ok"
    assert "latency_ms" in result


@pytest.mark.asyncio
async def test_health_probe_failure(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "g-test")
    monkeypatch.setattr(health_checks.httpx, "AsyncClient", lambda timeout: _FakeClient(raise_error=True, timeout=timeout))

    result = await health_checks._probe_google_embeddings(settings=get_settings())
    assert result["status"] == "down"
    assert "error" in result
