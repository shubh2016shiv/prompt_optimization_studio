"""
Cache-backed optimization helper operations.

This module centralizes expensive derived computations and wraps them with
deterministic cache keys, TTL policy, and stampede protection.
"""

from __future__ import annotations

import asyncio
import hashlib
import uuid
from typing import Any, Awaitable, Callable

import structlog

from app.config import get_settings
from app.services.store.base import ICacheStore

logger = structlog.get_logger(__name__)


AsyncComputation = Callable[[], Awaitable[Any]]


class CachedOptimizationOperations:
    """
    High-level cache operations used by the optimization pipeline.

    Association:
      Called by `optimization_pipeline.execute_optimization_request` for
      few-shot corpus, core hops, and other prompt-derived values.
    """

    def __init__(self, cache_store: ICacheStore) -> None:
        self._cache_store = cache_store
        self._settings = get_settings()

    async def get_or_compute_reasoning_hops(
        self,
        *,
        raw_prompt: str,
        compute_function: AsyncComputation,
        ttl_seconds: int = 24 * 60 * 60,
    ) -> int:
        """
        Cache CoRe hop computations by raw prompt hash.

        Educational note:
          CoRe hop counting is an LLM call. Hash-keying by raw prompt avoids
          paying for repeated identical prompts.
        """
        cache_key = self._build_prompt_hash_cache_key(scope="core_hops", raw_prompt=raw_prompt)
        cached_value = await self._cache_store.get_json(cache_key)
        if cached_value is not None:
            logger.info("optimize.cache_hit", cache_key=cache_key, operation="core_hops")
            return int(cached_value)

        logger.info("optimize.cache_miss", cache_key=cache_key, operation="core_hops")
        computed_value = await compute_function()
        await self._cache_store.set_json(cache_key, int(computed_value), ttl_seconds=ttl_seconds)
        return int(computed_value)

    async def get_or_compute_few_shot_corpus(
        self,
        *,
        google_api_key: str,
        compute_function: Callable[[str], Awaitable[dict[str, Any]]],
        ttl_seconds: int = 24 * 60 * 60,
    ) -> dict[str, Any]:
        """
        Lazily build and cache corpus embeddings with lock-based stampede control.

        Educational note on 'Cache Stampede Protection':
          A 'Cache Stampede' happens when an expensive cached item expires (or hasn't been built yet), 
          and under high traffic, hundreds of requests hit the system at the exact same millisecond. 
          Without a lock, all 100 requests would notice the cache is empty, and all 100 would 
          simultaneously make a 10-second API call to Gemini, burning tokens and hitting rate limits.

          By using a distributed lock (acquire_lock), only the *first* request wins the lock and 
          does the hard work. The other 99 requests fall into a waiting loop, periodically checking 
          the cache until the first worker finishes.
        """
        cache_key = "few_shot_corpus"
        cached_value = await self._cache_store.get_json(cache_key)
        if cached_value is not None:
            logger.info("optimize.cache_hit", cache_key=cache_key, operation="few_shot_corpus")
            return cached_value

        logger.info("optimize.cache_miss", cache_key=cache_key, operation="few_shot_corpus")
        lock_key = f"{cache_key}:build"
        lock_token = str(uuid.uuid4())
        lock_acquired = await self._cache_store.acquire_lock(lock_key, lock_token, ttl_seconds=90)
        if lock_acquired:
            try:
                # Double-check cache after acquiring lock in case another process
                # completed the write while this process was waiting for lock.
                cached_after_lock = await self._cache_store.get_json(cache_key)
                if cached_after_lock is not None:
                    logger.info("optimize.cache_hit", cache_key=cache_key, operation="few_shot_corpus")
                    return cached_after_lock

                computed_corpus = await compute_function(google_api_key)
                serializable_corpus = self._serialize_embedded_corpus(computed_corpus)
                await self._cache_store.set_json(cache_key, serializable_corpus, ttl_seconds=ttl_seconds)
                return serializable_corpus
            finally:
                await self._cache_store.release_lock(lock_key, lock_token)

        # Cache Stampede Protection: Another process owns the lock and is doing the expensive work.
        # Instead of failing or making redundant Gemini LLM hits, we safely wait (poll).
        for _ in range(20):
            await asyncio.sleep(0.25)
            polled_value = await self._cache_store.get_json(cache_key)
            if polled_value is not None:
                # The lock-owner finished! We get to use the result without paying the latency/compute cost.
                logger.info("optimize.cache_hit", cache_key=cache_key, operation="few_shot_corpus")
                return polled_value

        raise RuntimeError("Timed out waiting for cached few-shot corpus to be materialized.")

    def _build_prompt_hash_cache_key(self, *, scope: str, raw_prompt: str) -> str:
        """
        Build stable deterministic cache key using SHA-256 over raw prompt.

        Association:
          Implements the naming policy described in the enterprise Redis plan.
        """
        prompt_hash = hashlib.sha256(raw_prompt.encode("utf-8")).hexdigest()
        return f"{scope}:sha256_{prompt_hash}"

    def _serialize_embedded_corpus(self, corpus: dict[str, Any]) -> dict[str, Any]:
        """
        Convert numpy/dataclass corpus objects into JSON-safe structures.

        Association:
          Redis cache values must be JSON serializable.
        """
        serialized: dict[str, Any] = {}
        for task_type, entries in corpus.items():
            serialized_entries = []
            for entry in entries:
                serialized_entries.append(
                    {
                        "entry": entry.entry,
                        "embedding": entry.embedding.tolist(),
                    }
                )
            serialized[task_type] = serialized_entries
        return serialized
