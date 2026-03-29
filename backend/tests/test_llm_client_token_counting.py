import pytest

from app.observability.usage_tracking import UsageSnapshot, bind_usage_snapshot
from app.services.llm_client import LLMClient


class FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code
        self.content = b"ok"
        self.text = "ok"

    def json(self):
        return self._payload


class FakeAsyncClient:
    def __init__(self, responses: list[FakeResponse]):
        self._responses = responses

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def aclose(self):
        return None

    async def post(self, *args, **kwargs):
        return self._responses.pop(0)


@pytest.mark.asyncio
async def test_openai_usage_is_tracked(monkeypatch):
    response = FakeResponse(
        {
            "choices": [{"message": {"content": "hello"}}],
            "usage": {"prompt_tokens": 11, "completion_tokens": 7},
        }
    )

    async with LLMClient(api_key="test-key") as client:
        client._client = FakeAsyncClient([response])
        text = await client.call(
            provider="openai",
            prompt="Say hello",
            max_tokens=10,
            model="gpt-4.1-mini",
        )

    assert text == "hello"
    assert client.get_usage_snapshot() == {
        "llm_call_count": 1,
        "prompt_tokens": 11,
        "completion_tokens": 7,
        "total_tokens": 18,
    }


@pytest.mark.asyncio
async def test_anthropic_usage_contributes_to_route_snapshot():
    response = FakeResponse(
        {
            "content": [{"type": "text", "text": "done"}],
            "usage": {
                "input_tokens": 20,
                "output_tokens": 6,
                "cache_creation_input_tokens": 4,
                "cache_read_input_tokens": 3,
            },
        }
    )
    route_snapshot = UsageSnapshot()

    with bind_usage_snapshot(route_snapshot):
        async with LLMClient(api_key="test-key") as client:
            client._client = FakeAsyncClient([response])
            await client.call(
                provider="anthropic",
                prompt="Test",
                max_tokens=10,
                model="claude-sonnet-4-6",
            )

    assert route_snapshot.llm_call_count == 1
    assert route_snapshot.prompt_tokens == 27
    assert route_snapshot.completion_tokens == 6
