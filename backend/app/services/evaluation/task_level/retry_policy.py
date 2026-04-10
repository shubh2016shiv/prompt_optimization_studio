"""
Retry policy for transient task-evaluation judge failures.

Why this module exists:
  Rubric judging depends on external LLM providers that can return temporary
  failures (for example HTTP 429 rate limits). This module encapsulates retry
  policy decisions so the judge implementation stays readable and policy can be
  tuned centrally via app.config.Settings.

Association with other modules:
  - Used by:
      rubric_judge.py
  - Reads config from:
      app.config.Settings
  - Understands provider exceptions from:
      app.services.llm_client.LLMClientError
"""

from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable
from typing import TypeVar

import structlog

from app.config import Settings
from app.services.llm_client import LLMClientError

logger = structlog.get_logger(__name__)
ReturnType = TypeVar("ReturnType")


class TaskEvaluationRetryPolicy:
    """
    Execute async operations with bounded exponential backoff retries.

    This policy retries only transient failures and surfaces permanent errors
    immediately, keeping task-evaluation behavior predictable in production.
    """

    _TRANSIENT_STATUS_CODES = frozenset({408, 409, 425, 429, 500, 502, 503, 504})

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def execute_with_retry(
        self,
        *,
        operation_name: str,
        operation: Callable[[], Awaitable[ReturnType]],
        log_context: dict[str, object] | None = None,
    ) -> ReturnType:
        """
        Run an async operation with retry on transient failures.

        Args:
          operation_name:
            Stable identifier used in logs.
          operation:
            Async callable that executes one attempt.
          log_context:
            Optional structured context merged into retry logs.
        """
        context_fields = dict(log_context or {})
        attempt_limit = max(1, self._settings.task_evaluation_judge_retry_attempts)

        for attempt_number in range(1, attempt_limit + 1):
            try:
                return await operation()
            except Exception as operation_error:
                should_retry = (
                    attempt_number < attempt_limit and self._is_transient_error(operation_error)
                )
                if not should_retry:
                    raise

                delay_seconds = self._compute_backoff_delay_seconds(attempt_number)
                logger.warning(
                    "optimize.task_evaluation.retry_scheduled",
                    operation=operation_name,
                    attempt=attempt_number,
                    next_delay_seconds=delay_seconds,
                    error=str(operation_error),
                    **context_fields,
                )
                await asyncio.sleep(delay_seconds)

        # The loop always returns or raises; this line exists for static typing.
        raise RuntimeError("Retry execution reached an unreachable state.")

    def _is_transient_error(self, operation_error: Exception) -> bool:
        """
        Determine whether an exception is likely to succeed on retry.

        Current policy:
          - LLMClientError with no status code (network/timeout) is transient.
          - LLMClientError with known transient HTTP status code is transient.
          - All other exceptions are treated as non-transient.
        """
        if isinstance(operation_error, LLMClientError):
            if operation_error.status_code is None:
                return True
            return operation_error.status_code in self._TRANSIENT_STATUS_CODES
        return False

    def _compute_backoff_delay_seconds(self, attempt_number: int) -> float:
        """
        Compute capped exponential backoff with positive jitter.

        This avoids synchronized retry spikes when many requests fail together.
        """
        base_delay = max(0.0, self._settings.task_evaluation_judge_retry_base_delay_seconds)
        max_delay = max(0.0, self._settings.task_evaluation_judge_retry_max_delay_seconds)
        jitter = max(0.0, self._settings.task_evaluation_judge_retry_jitter_seconds)

        exponential_delay = base_delay * (2 ** (attempt_number - 1))
        capped_delay = min(max_delay, exponential_delay) if max_delay > 0 else exponential_delay
        return round(capped_delay + random.uniform(0.0, jitter), 4)

