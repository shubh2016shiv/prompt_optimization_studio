"""Route-scoped usage accounting helpers."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Iterator


@dataclass
class UsageSnapshot:
    """Aggregated LLM usage for a logical request/session."""

    llm_call_count: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def record(
        self,
        *,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        call_count: int = 1,
    ) -> None:
        self.llm_call_count += max(0, int(call_count))
        self.prompt_tokens += max(0, int(prompt_tokens))
        self.completion_tokens += max(0, int(completion_tokens))

    def to_dict(self) -> dict[str, int]:
        return {
            "llm_call_count": self.llm_call_count,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


_current_usage_snapshot: ContextVar[UsageSnapshot | None] = ContextVar(
    "current_usage_snapshot",
    default=None,
)


@contextmanager
def bind_usage_snapshot(snapshot: UsageSnapshot) -> Iterator[UsageSnapshot]:
    """Bind a usage snapshot to the current async context."""
    token: Token[UsageSnapshot | None] = _current_usage_snapshot.set(snapshot)
    try:
        yield snapshot
    finally:
        _current_usage_snapshot.reset(token)


def get_current_usage_snapshot() -> UsageSnapshot | None:
    """Return the current route-scoped usage snapshot, if bound."""
    return _current_usage_snapshot.get()


def record_usage(
    *,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    call_count: int = 1,
) -> None:
    """Record usage into the current route-scoped snapshot if one exists."""
    snapshot = get_current_usage_snapshot()
    if snapshot is None:
        return
    snapshot.record(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        call_count=call_count,
    )
