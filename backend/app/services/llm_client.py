"""
Async LLM client supporting Anthropic, OpenAI, and Google providers.

Routes every call to the provider the user selected in the UI,
using only the API key they entered — no server-side keys needed.
"""

from typing import Optional

import httpx


class LLMClientError(Exception):
    """Raised when an LLM API call fails."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class LLMClient:
    """
    Async HTTP client for Anthropic, OpenAI, and Google LLM APIs.

    Use as an async context manager so the underlying httpx session
    is opened and closed cleanly:

        async with LLMClient(api_key=key) as client:
            text = await client.call(provider="openai", ...)
    """

    def __init__(self, api_key: str, timeout: float = 120.0):
        self.api_key = api_key
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()
            self._client = None

    # ------------------------------------------------------------------
    # Public dispatchers — used by all three route handlers
    # ------------------------------------------------------------------

    async def call(
        self,
        provider: str,
        prompt: str,
        max_tokens: int,
        model: str,
        system: Optional[str] = None,
    ) -> str:
        """
        Dispatch a single-turn call to the correct provider.

        Args:
            provider: 'anthropic' | 'openai' | 'google'
            prompt:   The user message.
            max_tokens: Maximum tokens to generate.
            model:    Provider-specific model ID.
            system:   Optional system prompt.

        Returns:
            The model's response text.
        """
        if provider == "openai":
            return await self._call_openai(prompt, max_tokens, model, system)
        elif provider == "google":
            return await self._call_google(prompt, max_tokens, model, system)
        else:
            return await self._call_anthropic(prompt, max_tokens, model, system)

    async def call_chat(
        self,
        provider: str,
        messages: list[dict],
        system: str,
        max_tokens: int,
        model: str,
    ) -> str:
        """
        Dispatch a multi-turn chat call to the correct provider.

        Args:
            provider: 'anthropic' | 'openai' | 'google'
            messages: Conversation history [{role, content}, ...].
            system:   System prompt.
            max_tokens: Maximum tokens to generate.
            model:    Provider-specific model ID.

        Returns:
            The model's response text.
        """
        if provider == "openai":
            return await self._call_openai_chat(messages, system, max_tokens, model)
        elif provider == "google":
            return await self._call_google_chat(messages, system, max_tokens, model)
        else:
            return await self._call_anthropic_chat(messages, system, max_tokens, model)

    # ------------------------------------------------------------------
    # Anthropic
    # ------------------------------------------------------------------

    async def _call_anthropic(
        self,
        prompt: str,
        max_tokens: int,
        model: str,
        system: Optional[str] = None,
    ) -> str:
        payload: dict = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            payload["system"] = system

        return await self._post_anthropic(payload)

    async def _call_anthropic_chat(
        self,
        messages: list[dict],
        system: str,
        max_tokens: int,
        model: str,
    ) -> str:
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": messages,
        }
        return await self._post_anthropic(payload)

    async def _post_anthropic(self, payload: dict) -> str:
        self._require_client()
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }
        try:
            response = await self._client.post(  # type: ignore[union-attr]
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
            )
        except httpx.TimeoutException:
            raise LLMClientError("Request timed out")
        except httpx.RequestError as exc:
            raise LLMClientError(f"Request failed: {exc}")

        if response.status_code != 200:
            error_body = response.json() if response.content else {}
            msg = error_body.get("error", {}).get("message", response.text)
            raise LLMClientError(f"Anthropic API error: {msg}", status_code=response.status_code)

        data = response.json()
        return "".join(
            block.get("text", "")
            for block in data.get("content", [])
            if block.get("type") == "text"
        )

    # ------------------------------------------------------------------
    # OpenAI
    # ------------------------------------------------------------------

    async def _call_openai(
        self,
        prompt: str,
        max_tokens: int,
        model: str,
        system: Optional[str] = None,
    ) -> str:
        messages: list[dict] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return await self._call_openai_chat(messages, system="", max_tokens=max_tokens, model=model, _messages_prebuilt=messages)

    async def _call_openai_chat(
        self,
        messages: list[dict],
        system: str,
        max_tokens: int,
        model: str,
        _messages_prebuilt: Optional[list[dict]] = None,
    ) -> str:
        """
        Call the OpenAI Chat Completions API.

        If _messages_prebuilt is provided (from _call_openai), use it directly
        to avoid prepending the system prompt twice.
        """
        self._require_client()

        if _messages_prebuilt is not None:
            full_messages = _messages_prebuilt
        else:
            full_messages = []
            if system:
                full_messages.append({"role": "system", "content": system})
            full_messages.extend(messages)

        payload = {
            "model": model,
            "messages": full_messages,
        }
        
        # Reasoning models (o1, o3, o4 series) use max_completion_tokens instead of max_tokens
        if model.startswith("o1") or model.startswith("o3") or model.startswith("o4"):
            payload["max_completion_tokens"] = max_tokens
        else:
            payload["max_tokens"] = max_tokens

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        try:
            response = await self._client.post(  # type: ignore[union-attr]
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
            )
        except httpx.TimeoutException:
            raise LLMClientError("Request timed out")
        except httpx.RequestError as exc:
            raise LLMClientError(f"Request failed: {exc}")

        if response.status_code != 200:
            error_body = response.json() if response.content else {}
            msg = error_body.get("error", {}).get("message", response.text)
            raise LLMClientError(f"OpenAI API error: {msg}", status_code=response.status_code)

        data = response.json()
        return data["choices"][0]["message"]["content"]

    # ------------------------------------------------------------------
    # Google (Gemini)
    # ------------------------------------------------------------------

    async def _call_google(
        self,
        prompt: str,
        max_tokens: int,
        model: str,
        system: Optional[str] = None,
    ) -> str:
        messages = [{"role": "user", "parts": [{"text": prompt}]}]
        return await self._post_google(messages, system, max_tokens, model)

    async def _call_google_chat(
        self,
        messages: list[dict],
        system: str,
        max_tokens: int,
        model: str,
    ) -> str:
        """
        Convert the standard {role, content} history to Google's {role, parts} format.
        """
        google_messages = [
            {"role": msg["role"], "parts": [{"text": msg["content"]}]}
            for msg in messages
        ]
        return await self._post_google(google_messages, system, max_tokens, model)

    async def _post_google(
        self,
        google_messages: list[dict],
        system: Optional[str],
        max_tokens: int,
        model: str,
    ) -> str:
        self._require_client()

        payload: dict = {
            "contents": google_messages,
            "generationConfig": {"maxOutputTokens": max_tokens},
        }
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models"
            f"/{model}:generateContent?key={self.api_key}"
        )

        try:
            response = await self._client.post(  # type: ignore[union-attr]
                url,
                headers={"Content-Type": "application/json"},
                json=payload,
            )
        except httpx.TimeoutException:
            raise LLMClientError("Request timed out")
        except httpx.RequestError as exc:
            raise LLMClientError(f"Request failed: {exc}")

        if response.status_code != 200:
            error_body = response.json() if response.content else {}
            msg = (
                error_body.get("error", {}).get("message", response.text)
            )
            raise LLMClientError(f"Google API error: {msg}", status_code=response.status_code)

        data = response.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as exc:
            raise LLMClientError(f"Unexpected Google API response format: {exc}")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _require_client(self) -> None:
        if self._client is None:
            raise LLMClientError(
                "Client not initialised. Use 'async with LLMClient(...) as client:'"
            )
