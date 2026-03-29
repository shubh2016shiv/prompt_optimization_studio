"""
Redis-backed store adapter implementing job persistence and caching contracts.

Educational note:
  Redis stores bytes, not Python objects. This adapter always serializes and
  validates with Pydantic JSON boundaries so schema contracts remain explicit
  and safe across process boundaries.
"""

from __future__ import annotations

import json
from typing import Any

import redis.asyncio as redis
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import WatchError

from app.config import get_settings
from app.services.store.base import ICacheStore, IJobStore
from app.services.store.models import OptimizationJobPersistedRecord


class RedisStore(IJobStore, ICacheStore):
    """
    Redis adapter for durable job storage and shared caching.

    Association:
      Wired by application startup and injected into job orchestration and
      optimization caching components.
    """

    def __init__(
        self,
        *,
        redis_url: str | None = None,
        max_connections: int | None = None,
        socket_timeout_seconds: float | None = None,
        key_prefix: str | None = None,
    ) -> None:
        settings = get_settings()
        self._key_prefix = key_prefix or settings.redis_key_prefix
        self._pool = redis.ConnectionPool.from_url(
            redis_url or settings.redis_url,
            max_connections=max_connections or settings.redis_max_connections,
            socket_timeout=socket_timeout_seconds or settings.redis_socket_timeout_seconds,
            decode_responses=True,
        )
        self._client = redis.Redis(connection_pool=self._pool)

    async def ping(self) -> None:
        """Validate Redis connectivity."""
        await self._client.ping()

    async def close(self) -> None:
        """Close Redis client resources cleanly."""
        await self._client.aclose()
        await self._pool.aclose()

    async def create_job_record(
        self,
        job_record: OptimizationJobPersistedRecord,
        ttl_seconds: int,
    ) -> None:
        """Persist a new job record with TTL."""
        key = self._job_key(job_record.job_id)
        await self._client.set(name=key, value=job_record.model_dump_json(), ex=ttl_seconds)

    async def get_job_record(self, job_id: str) -> OptimizationJobPersistedRecord | None:
        """Load and validate one job record from Redis."""
        key = self._job_key(job_id)
        payload = await self._client.get(key)
        if payload is None:
            return None
        return OptimizationJobPersistedRecord.model_validate_json(payload)

    async def update_job_record_atomic(
        self,
        job_id: str,
        *,
        patch_fields: dict[str, Any],
        ttl_seconds: int,
        expected_current_status: str | None = None,
    ) -> OptimizationJobPersistedRecord | None:
        """
        Atomically patch one job record with optimistic locking.

        Educational note:
          `WATCH + MULTI/EXEC` ensures two workers do not silently overwrite
          each other. If status transitions race, one update is retried.
        """
        key = self._job_key(job_id)
        for _ in range(5):
            async with self._client.pipeline(transaction=True) as transaction:
                try:
                    await transaction.watch(key)
                    # Read through the watched pipeline so optimistic locking
                    # observes concurrent writes to this key correctly.
                    raw_payload = await transaction.get(key)
                    if raw_payload is None:
                        await transaction.reset()
                        return None
                    record = OptimizationJobPersistedRecord.model_validate_json(raw_payload)
                    if (
                        expected_current_status is not None
                        and record.status != expected_current_status
                    ):
                        await transaction.reset()
                        return None

                    updated_record = record.model_copy(update=patch_fields)
                    transaction.multi()
                    transaction.set(key, updated_record.model_dump_json(), ex=ttl_seconds)
                    await transaction.execute()
                    return updated_record
                except WatchError:
                    continue
                finally:
                    await transaction.reset()
        raise RuntimeError(f"Unable to atomically update job '{job_id}' after retries.")

    async def get_json(self, cache_key: str) -> Any | None:
        """Load JSON cache value when present."""
        raw_value = await self._client.get(self._cache_key(cache_key))
        if raw_value is None:
            return None
        return json.loads(raw_value)

    async def set_json(self, cache_key: str, value: Any, ttl_seconds: int) -> None:
        """Store JSON cache value with TTL."""
        await self._client.set(
            name=self._cache_key(cache_key),
            value=json.dumps(value),
            ex=ttl_seconds,
        )

    async def acquire_lock(self, lock_key: str, lock_token: str, ttl_seconds: int) -> bool:
        """Acquire distributed lock via Redis `SET NX EX`."""
        result = await self._client.set(
            name=self._lock_key(lock_key),
            value=lock_token,
            ex=ttl_seconds,
            nx=True,
        )
        return bool(result)

    async def release_lock(self, lock_key: str, lock_token: str) -> None:
        """
        Release distributed lock only when lock token matches.

        Educational note:
          Token checks prevent one request from accidentally deleting another
          request's active lock.
        """
        redis_lock_key = self._lock_key(lock_key)
        current_token = await self._client.get(redis_lock_key)
        if current_token == lock_token:
            await self._client.delete(redis_lock_key)

    def _job_key(self, job_id: str) -> str:
        return f"{self._key_prefix}job:{job_id}"

    def _cache_key(self, cache_key: str) -> str:
        return f"{self._key_prefix}cache:{cache_key}"

    def _lock_key(self, lock_key: str) -> str:
        return f"{self._key_prefix}lock:{lock_key}"


RedisStoreConnectionError = RedisConnectionError
