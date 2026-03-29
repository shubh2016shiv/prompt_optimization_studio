"""Small Langfuse compatibility layer for tracing and generation telemetry."""

from __future__ import annotations

from contextlib import contextmanager, nullcontext
from typing import Any, Callable, Iterator

from dotenv import load_dotenv

load_dotenv()

try:
    import langfuse
except ImportError:  # pragma: no cover - exercised when dependency is unavailable
    langfuse = None


def observe(*args, **kwargs):
    """Return Langfuse's decorator when available, otherwise a no-op decorator."""
    if langfuse is None:
        def noop_decorator(func: Callable):
            return func
        if args and callable(args[0]) and len(args) == 1 and not kwargs:
            return args[0]
        return noop_decorator
    return langfuse.observe(*args, **kwargs)


def get_langfuse_client():
    """Return the configured Langfuse client when available."""
    if langfuse is None:
        return None
    try:
        return langfuse.get_client()
    except Exception:
        return None


def create_trace_id(seed: str) -> str | None:
    """Create a deterministic trace id from a request id."""
    client = get_langfuse_client()
    if client is None:
        return None
    try:
        return client.create_trace_id(seed=seed)
    except Exception:
        return None


@contextmanager
def start_trace(name: str, trace_id: str | None, metadata: dict[str, Any] | None = None) -> Iterator[None]:
    """Start a current span bound to a deterministic trace id when possible."""
    client = get_langfuse_client()
    if client is None or trace_id is None or not hasattr(client, "start_as_current_span"):
        with nullcontext():
            yield
        return

    with client.start_as_current_span(
        name=name,
        trace_context={"trace_id": trace_id},
        metadata=metadata,
    ):
        yield


def update_current_trace(**kwargs: Any) -> None:
    """Safely update the current Langfuse trace."""
    client = get_langfuse_client()
    if client is None:
        return
    try:
        client.update_current_trace(**kwargs)
    except Exception:
        return


def update_current_generation(**kwargs: Any) -> None:
    """Safely update the current Langfuse generation observation."""
    client = get_langfuse_client()
    if client is None:
        return
    try:
        client.update_current_generation(**kwargs)
    except Exception:
        return


def get_current_trace_id() -> str | None:
    """Return the active Langfuse trace id when one exists."""
    client = get_langfuse_client()
    if client is None:
        return None
    try:
        return client.get_current_trace_id()
    except Exception:
        return None
