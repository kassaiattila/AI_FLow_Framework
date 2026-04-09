"""
@test_registry:
    suite: service-unit
    component: services.rate_limiter
    covers: [src/aiflow/services/rate_limiter/service.py]
    phase: B2.1
    priority: critical
    estimated_duration_ms: 400
    requires_services: []
    tags: [service, rate-limiter, redis, sliding-window]
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from aiflow.services.rate_limiter.service import (
    RateLimiterConfig,
    RateLimiterService,
    RateLimitRule,
)
from tests.unit.services.conftest import AsyncPipelineMock


@pytest.fixture()
def svc(mock_redis) -> RateLimiterService:
    """RateLimiterService with mock Redis and a tight rule."""
    config = RateLimiterConfig(
        default_max_requests=5,
        default_window_seconds=60,
        rules=[RateLimitRule(key="api", max_requests=3, window_seconds=10)],
    )
    service = RateLimiterService(config=config)
    service._redis = mock_redis
    return service


class TestRateLimiterService:
    @pytest.mark.asyncio
    async def test_allow_under_limit(self, svc: RateLimiterService, mock_redis) -> None:
        """allow() returns True when under rate limit."""
        pipeline = AsyncPipelineMock()
        pipeline._results = [0, 1, True, True]  # zcard=1 (under limit of 3)
        mock_redis.pipeline = MagicMock(return_value=pipeline)

        result = await svc.allow("api")
        assert result is True

    @pytest.mark.asyncio
    async def test_allow_over_limit(self, svc: RateLimiterService, mock_redis) -> None:
        """allow() returns False when at or over rate limit."""
        pipeline = AsyncPipelineMock()
        pipeline._results = [0, 3, True, True]  # zcard=3 (at limit)
        mock_redis.pipeline = MagicMock(return_value=pipeline)
        mock_redis.zrem = AsyncMock(return_value=1)

        result = await svc.allow("api")
        assert result is False

    @pytest.mark.asyncio
    async def test_get_remaining(self, svc: RateLimiterService, mock_redis) -> None:
        """get_remaining() returns correct remaining count."""
        pipeline = AsyncPipelineMock()
        pipeline._results = [0, 1]  # zremrangebyscore=0, zcard=1
        mock_redis.pipeline = MagicMock(return_value=pipeline)

        info = await svc.get_remaining("api")
        assert info["key"] == "api"
        assert info["limit"] == 3
        assert info["remaining"] == 2
        assert info["used"] == 1
        assert info["window_seconds"] == 10

    @pytest.mark.asyncio
    async def test_reset_clears_counter(self, svc: RateLimiterService, mock_redis) -> None:
        """reset() deletes the Redis key for the rate limiter."""
        await svc.reset("api")
        mock_redis.delete.assert_awaited_once()

    def test_add_rule_runtime(self, svc: RateLimiterService) -> None:
        """add_rule() registers a new rule at runtime."""
        new_rule = RateLimitRule(key="uploads", max_requests=10, window_seconds=300)
        svc.add_rule(new_rule)

        assert "uploads" in svc._rules
        assert svc._rules["uploads"].max_requests == 10
