"""
Async LLM client for Anthropic API calls.

Provides a clean interface for making LLM requests with proper error handling.
"""

from typing import Optional

import httpx

from app.config import get_settings


class LLMClientError(Exception):
    """Raised when an LLM API call fails."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class LLMClient:
    """Async client for LLM API calls."""

    def __init__(self, api_key: str, timeout: float = 60.0):
        """
        Initialize the LLM client.

        Args:
            api_key: The API key for authentication.
            timeout: Request timeout in seconds.
        """
        self.api_key = api_key
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Context manager entry."""
        self._client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def call_anthropic(
        self,
        prompt: str,
        max_tokens: int = 2048,
        system: Optional[str] = None,
        model: Optional[str] = None,
    ) -> str:
        """
        Call the Anthropic Messages API.

        Args:
            prompt: The user message content.
            max_tokens: Maximum tokens to generate.
            system: Optional system prompt.
            model: Model ID (defaults to optimizer model from settings).

        Returns:
            The assistant's response text.

        Raises:
            LLMClientError: If the API call fails.
        """
        settings = get_settings()
        model = model or settings.optimizer_model

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }

        messages = [{"role": "user", "content": prompt}]

        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages,
        }

        if system:
            payload["system"] = system

        if not self._client:
            raise LLMClientError("Client not initialized. Use 'async with' context manager.")

        try:
            response = await self._client.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
            )

            if response.status_code != 200:
                error_body = response.json() if response.content else {}
                error_message = error_body.get("error", {}).get("message", response.text)
                raise LLMClientError(
                    f"Anthropic API error: {error_message}",
                    status_code=response.status_code,
                )

            data = response.json()
            content_blocks = data.get("content", [])

            # Extract text from content blocks
            text_parts = []
            for block in content_blocks:
                if block.get("type") == "text":
                    text_parts.append(block.get("text", ""))

            return "".join(text_parts)

        except httpx.TimeoutException:
            raise LLMClientError("Request timed out")
        except httpx.RequestError as e:
            raise LLMClientError(f"Request failed: {str(e)}")

    async def call_anthropic_chat(
        self,
        messages: list[dict],
        system: str,
        max_tokens: int = 2048,
        model: Optional[str] = None,
    ) -> str:
        """
        Call the Anthropic Messages API with a conversation history.

        Args:
            messages: List of message dicts [{role: str, content: str}].
            system: System prompt.
            max_tokens: Maximum tokens to generate.
            model: Model ID (defaults to optimizer model from settings).

        Returns:
            The assistant's response text.

        Raises:
            LLMClientError: If the API call fails.
        """
        settings = get_settings()
        model = model or settings.optimizer_model

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }

        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": messages,
        }

        if not self._client:
            raise LLMClientError("Client not initialized. Use 'async with' context manager.")

        try:
            response = await self._client.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
            )

            if response.status_code != 200:
                error_body = response.json() if response.content else {}
                error_message = error_body.get("error", {}).get("message", response.text)
                raise LLMClientError(
                    f"Anthropic API error: {error_message}",
                    status_code=response.status_code,
                )

            data = response.json()
            content_blocks = data.get("content", [])

            text_parts = []
            for block in content_blocks:
                if block.get("type") == "text":
                    text_parts.append(block.get("text", ""))

            return "".join(text_parts)

        except httpx.TimeoutException:
            raise LLMClientError("Request timed out")
        except httpx.RequestError as e:
            raise LLMClientError(f"Request failed: {str(e)}")
