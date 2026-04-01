"""Redis-backed cache service for embeddings, LLM responses, and vector queries.

Provides three cache namespaces:
- embedding: text_hash -> embedding vector (TTL: 7 days)
- llm: prompt_hash+input_hash -> LLM response (TTL: 24 hours)
- vector_query: query_hash -> top-K search results (TTL: 1 hour)
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

import redis.asyncio as aioredis
import structlog
from pydantic import Field

from aiflow.services.base import BaseService, ServiceConfig

__all__ = ["CacheConfig", "CacheService"]

logger = structlog.get_logger(__name__)


class CacheConfig(ServiceConfig):
    """Cache service configuration."""

    redis_url: str = "redis://localhost:6379/0"
    key_prefix: str = "aiflow:cache:"
    embedding_ttl_seconds: int = 7 * 24 * 3600  # 1 week
    llm_response_ttl_seconds: int = 24 * 3600  # 24 hours
    vector_query_ttl_seconds: int = 3600  # 1 hour
    max_embedding_entries: int = 100_000
    max_value_size_bytes: int = 10 * 1024 * 1024  # 10 MB


class CacheService(BaseService):
    """Redis-backed cache for embeddings, LLM responses, and vector queries."""

    def __init__(self, config: CacheConfig | None = None) -> None:
        self._cache_config = config or CacheConfig()
        super().__init__(self._cache_config)
        self._redis: aioredis.Redis | None = None

    @property
    def service_name(self) -> str:
        return "cache"

    @property
    def service_description(self) -> str:
        return "Redis cache for embeddings, LLM responses, and vector queries"

    async def _start(self) -> None:
        self._redis = aioredis.from_url(
            self._cache_config.redis_url,
            decode_responses=False,
            socket_connect_timeout=5,
        )
        await self._redis.ping()
        self._logger.info("cache_connected", url=self._cache_config.redis_url)

    async def _stop(self) -> None:
        if self._redis:
            await self._redis.aclose()
            self._redis = None

    async def health_check(self) -> bool:
        if not self._redis:
            return False
        try:
            return await self._redis.ping()
        except Exception:
            return False

    # --- Key helpers ---

    def _key(self, namespace: str, hash_val: str) -> str:
        return f"{self._cache_config.key_prefix}{namespace}:{hash_val}"

    @staticmethod
    def _hash_text(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]

    @staticmethod
    def _hash_dict(data: dict[str, Any]) -> str:
        serialized = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:32]

    # --- Embedding cache ---

    async def get_embedding(self, text: str) -> list[float] | None:
        """Get cached embedding for text. Returns None on miss."""
        assert self._redis is not None
        key = self._key("emb", self._hash_text(text))
        data = await self._redis.get(key)
        if data is None:
            self._logger.debug("cache_miss", namespace="embedding", key=key[:50])
            return None
        self._logger.debug("cache_hit", namespace="embedding", key=key[:50])
        return json.loads(data)

    async def set_embedding(self, text: str, embedding: list[float]) -> None:
        """Cache an embedding vector for text."""
        assert self._redis is not None
        key = self._key("emb", self._hash_text(text))
        data = json.dumps(embedding)
        await self._redis.set(
            key, data, ex=self._cache_config.embedding_ttl_seconds
        )

    # --- LLM response cache ---

    async def get_llm_response(
        self,
        prompt_template: str,
        input_data: dict[str, Any],
        model: str = "",
    ) -> dict[str, Any] | None:
        """Get cached LLM response. Returns None on miss."""
        assert self._redis is not None
        hash_input = self._hash_dict(
            {"prompt": prompt_template, "input": input_data, "model": model}
        )
        key = self._key("llm", hash_input)
        data = await self._redis.get(key)
        if data is None:
            self._logger.debug("cache_miss", namespace="llm", key=key[:50])
            return None
        self._logger.debug("cache_hit", namespace="llm", key=key[:50])
        return json.loads(data)

    async def set_llm_response(
        self,
        prompt_template: str,
        input_data: dict[str, Any],
        response: dict[str, Any],
        model: str = "",
    ) -> None:
        """Cache an LLM response."""
        assert self._redis is not None
        hash_input = self._hash_dict(
            {"prompt": prompt_template, "input": input_data, "model": model}
        )
        key = self._key("llm", hash_input)
        data = json.dumps(response, ensure_ascii=False)
        await self._redis.set(
            key, data, ex=self._cache_config.llm_response_ttl_seconds
        )

    # --- Vector query cache ---

    async def get_vector_results(
        self, collection: str, query_text: str, top_k: int = 10
    ) -> list[dict[str, Any]] | None:
        """Get cached vector search results. Returns None on miss."""
        assert self._redis is not None
        hash_input = self._hash_dict(
            {"collection": collection, "query": query_text, "top_k": top_k}
        )
        key = self._key("vec", hash_input)
        data = await self._redis.get(key)
        if data is None:
            self._logger.debug("cache_miss", namespace="vector_query", key=key[:50])
            return None
        self._logger.debug("cache_hit", namespace="vector_query", key=key[:50])
        return json.loads(data)

    async def set_vector_results(
        self,
        collection: str,
        query_text: str,
        results: list[dict[str, Any]],
        top_k: int = 10,
    ) -> None:
        """Cache vector search results."""
        assert self._redis is not None
        hash_input = self._hash_dict(
            {"collection": collection, "query": query_text, "top_k": top_k}
        )
        key = self._key("vec", hash_input)
        data = json.dumps(results, ensure_ascii=False, default=str)
        await self._redis.set(
            key, data, ex=self._cache_config.vector_query_ttl_seconds
        )

    # --- Invalidation ---

    async def invalidate_collection(self, collection: str) -> int:
        """Invalidate all vector query cache entries for a collection.

        Also clears LLM cache entries scoped to this collection.
        Returns number of keys deleted.
        """
        assert self._redis is not None
        count = 0
        pattern = f"{self._cache_config.key_prefix}vec:*"
        async for key in self._redis.scan_iter(match=pattern, count=100):
            count += 1
        # Delete matching keys in bulk
        if count > 0:
            keys = []
            async for key in self._redis.scan_iter(match=pattern, count=100):
                keys.append(key)
            if keys:
                deleted = await self._redis.delete(*keys)
                self._logger.info(
                    "cache_invalidated",
                    collection=collection,
                    deleted=deleted,
                )
                return deleted
        return 0

    async def invalidate_namespace(self, namespace: str) -> int:
        """Clear all entries in a cache namespace (emb, llm, vec)."""
        assert self._redis is not None
        pattern = f"{self._cache_config.key_prefix}{namespace}:*"
        keys = []
        async for key in self._redis.scan_iter(match=pattern, count=100):
            keys.append(key)
        if keys:
            deleted = await self._redis.delete(*keys)
            self._logger.info(
                "namespace_invalidated", namespace=namespace, deleted=deleted
            )
            return deleted
        return 0

    async def get_stats(self) -> dict[str, Any]:
        """Get cache statistics per namespace."""
        assert self._redis is not None
        stats: dict[str, int] = {}
        for ns in ("emb", "llm", "vec"):
            count = 0
            pattern = f"{self._cache_config.key_prefix}{ns}:*"
            async for _ in self._redis.scan_iter(match=pattern, count=100):
                count += 1
            stats[f"{ns}_entries"] = count

        info = await self._redis.info("memory")
        stats["memory_used_bytes"] = info.get("used_memory", 0)
        return stats
