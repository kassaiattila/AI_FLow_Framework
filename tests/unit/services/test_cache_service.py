"""
@test_registry:
    suite: service-unit
    component: services.cache
    covers: [src/aiflow/services/cache/service.py]
    phase: B2.1
    priority: critical
    estimated_duration_ms: 400
    requires_services: []
    tags: [service, cache, redis, embedding, llm]
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from aiflow.services.cache.service import CacheConfig, CacheService
from tests.unit.services.conftest import AsyncIterMock


@pytest.fixture()
def svc(mock_redis) -> CacheService:
    """CacheService with injected mock Redis."""
    service = CacheService(config=CacheConfig())
    service._redis = mock_redis
    return service


class TestCacheService:
    @pytest.mark.asyncio
    async def test_get_embedding_cache_hit(self, svc: CacheService, mock_redis) -> None:
        """set_embedding + get_embedding returns the stored vector."""
        embedding = [0.1, 0.2, 0.3]
        mock_redis.get = AsyncMock(return_value=json.dumps(embedding).encode())

        result = await svc.get_embedding("hello world")
        assert result == embedding

    @pytest.mark.asyncio
    async def test_get_embedding_cache_miss(self, svc: CacheService, mock_redis) -> None:
        """get_embedding returns None on cache miss."""
        mock_redis.get = AsyncMock(return_value=None)

        result = await svc.get_embedding("unknown text")
        assert result is None

    @pytest.mark.asyncio
    async def test_llm_response_cache(self, svc: CacheService, mock_redis) -> None:
        """set_llm_response + get_llm_response round-trip."""
        response = {"text": "Hello!", "model": "gpt-4o-mini"}
        mock_redis.get = AsyncMock(return_value=json.dumps(response).encode())

        result = await svc.get_llm_response("template", {"key": "val"})
        assert result == response

    @pytest.mark.asyncio
    async def test_invalidate_collection(self, svc: CacheService, mock_redis) -> None:
        """invalidate_collection deletes matching keys and returns count."""
        keys = [b"aiflow:cache:vec:abc", b"aiflow:cache:vec:def"]
        mock_redis.scan_iter = MagicMock(return_value=AsyncIterMock(keys))
        mock_redis.delete = AsyncMock(return_value=2)

        deleted = await svc.invalidate_collection("test_collection")
        assert deleted == 2

    @pytest.mark.asyncio
    async def test_get_stats(self, svc: CacheService, mock_redis) -> None:
        """get_stats returns namespace counts and memory info."""
        mock_redis.scan_iter = MagicMock(return_value=AsyncIterMock([]))
        mock_redis.info = AsyncMock(return_value={"used_memory": 4096})

        stats = await svc.get_stats()
        assert "emb_entries" in stats
        assert "llm_entries" in stats
        assert "vec_entries" in stats
        assert stats["memory_used_bytes"] == 4096
