"""
Store abstraction contracts for durable orchestration and caching.

Why this module exists:
  APOST business logic should not depend directly on Redis SDK details.
  These interfaces define stable contracts that job orchestration and caching
  can target, while concrete adapters (Redis now, others later) implement them.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.services.store.models import OptimizationJobPersistedRecord


class IJobStore(ABC):
    """
    Durable store contract for optimization job records.

    Association:
      Used by `OptimizationJobService` to persist and retrieve job state.
      Implemented by `RedisStore` in this repository snapshot.
    """

    @abstractmethod
    async def ping(self) -> None:
        """Verify the backing store is reachable."""

    @abstractmethod
    async def close(self) -> None:
        """Release backing store resources gracefully."""

    @abstractmethod
    async def create_job_record(
        self,
        job_record: OptimizationJobPersistedRecord,
        ttl_seconds: int,
    ) -> None:
        """Persist a new job record with TTL protection."""

    @abstractmethod
    async def get_job_record(self, job_id: str) -> OptimizationJobPersistedRecord | None:
        """Load one persisted job record by id."""

    @abstractmethod
    async def update_job_record_atomic(
        self,
        job_id: str,
        *,
        patch_fields: dict[str, Any],
        ttl_seconds: int,
        expected_current_status: str | None = None,
    ) -> OptimizationJobPersistedRecord | None:
        """
        Atomically patch a job record, optionally guarded by current status.

        Returns:
          Updated record when successful, or None when optimistic status check
          fails.
        """


class ICacheStore(ABC):
    """
    Durable cache contract for reusable optimization artifacts.

    Association:
      Used by `CachedOptimizationOperations` to cache expensive repeated work
      such as corpus embeddings and per-prompt derived computations.
    """

    @abstractmethod
    async def get_json(self, cache_key: str) -> Any | None:
        """Load JSON payload by cache key."""

    @abstractmethod
    async def set_json(self, cache_key: str, value: Any, ttl_seconds: int) -> None:
        """Store JSON payload by cache key with TTL."""

    @abstractmethod
    async def acquire_lock(self, lock_key: str, lock_token: str, ttl_seconds: int) -> bool:
        """Attempt to acquire a distributed lock."""

    @abstractmethod
    async def release_lock(self, lock_key: str, lock_token: str) -> None:
        """Release a distributed lock when the token matches."""
