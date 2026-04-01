"""Redis sliding window rate limiter service.

Uses Redis sorted sets for precise sliding window counting.
Each service/endpoint gets an independent rate limit configuration.
"""
from __future__ import annotations

import time
import uuid
from typing import Any

import redis.asyncio as aioredis
import structlog
from pydantic import Field

from aiflow.services.base import BaseService, ServiceConfig

__all__ = ["RateLimiterConfig", "RateLimitRule", "RateLimiterService"]

logger = structlog.get_logger(__name__)


class RateLimitRule(ServiceConfig):
    """Rate limit rule for a specific key/service."""

    key: str = "default"
    max_requests: int = 100
    window_seconds: int = 60


class RateLimiterConfig(ServiceConfig):
    """Rate limiter service configuration."""

    redis_url: str = "redis://localhost:6379/0"
    key_prefix: str = "aiflow:ratelimit:"
    default_max_requests: int = 100
    default_window_seconds: int = 60
    rules: list[RateLimitRule] = Field(default_factory=list)


class RateLimiterService(BaseService):
    """Redis sliding window rate limiter.

    Uses sorted sets to track request timestamps within a sliding window.
    Each key (service name, endpoint, user) gets its own counter.
    """

    def __init__(self, config: RateLimiterConfig | None = None) -> None:
        self._rl_config = config or RateLimiterConfig()
        super().__init__(self._rl_config)
        self._redis: aioredis.Redis | None = None
        self._rules: dict[str, RateLimitRule] = {
            r.key: r for r in self._rl_config.rules
        }

    @property
    def service_name(self) -> str:
        return "rate_limiter"

    @property
    def service_description(self) -> str:
        return "Redis sliding window rate limiter"

    async def _start(self) -> None:
        self._redis = aioredis.from_url(
            self._rl_config.redis_url,
            decode_responses=False,
            socket_connect_timeout=5,
        )
        await self._redis.ping()

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

    def _get_rule(self, key: str) -> RateLimitRule:
        """Get rate limit rule for key, or default."""
        if key in self._rules:
            return self._rules[key]
        return RateLimitRule(
            key=key,
            max_requests=self._rl_config.default_max_requests,
            window_seconds=self._rl_config.default_window_seconds,
        )

    def _redis_key(self, key: str) -> str:
        return f"{self._rl_config.key_prefix}{key}"

    async def allow(self, key: str = "default") -> bool:
        """Check if request is allowed. Returns True if under limit.

        Uses Redis sorted set with timestamps as scores.
        Sliding window: remove entries older than window, count remaining.
        """
        assert self._redis is not None
        rule = self._get_rule(key)
        redis_key = self._redis_key(key)
        now = time.time()
        window_start = now - rule.window_seconds

        pipe = self._redis.pipeline()
        # Remove expired entries
        pipe.zremrangebyscore(redis_key, 0, window_start)
        # Count current entries
        pipe.zcard(redis_key)
        # Add current request (optimistic)
        member = f"{now}:{uuid.uuid4().hex[:8]}"
        pipe.zadd(redis_key, {member: now})
        # Set TTL on the key
        pipe.expire(redis_key, rule.window_seconds + 1)

        results = await pipe.execute()
        current_count = results[1]  # zcard result

        if current_count >= rule.max_requests:
            # Over limit — remove the entry we just added
            await self._redis.zrem(redis_key, member)
            self._logger.debug(
                "rate_limited",
                key=key,
                count=current_count,
                limit=rule.max_requests,
                window=rule.window_seconds,
            )
            return False

        self._logger.debug(
            "rate_allowed",
            key=key,
            count=current_count + 1,
            limit=rule.max_requests,
        )
        return True

    async def get_remaining(self, key: str = "default") -> dict[str, Any]:
        """Get remaining requests info for a key."""
        assert self._redis is not None
        rule = self._get_rule(key)
        redis_key = self._redis_key(key)
        now = time.time()
        window_start = now - rule.window_seconds

        pipe = self._redis.pipeline()
        pipe.zremrangebyscore(redis_key, 0, window_start)
        pipe.zcard(redis_key)
        results = await pipe.execute()
        current = results[1]

        return {
            "key": key,
            "limit": rule.max_requests,
            "remaining": max(0, rule.max_requests - current),
            "used": current,
            "window_seconds": rule.window_seconds,
        }

    async def reset(self, key: str = "default") -> None:
        """Reset rate limit counter for a key."""
        assert self._redis is not None
        await self._redis.delete(self._redis_key(key))
        self._logger.info("rate_limit_reset", key=key)

    def add_rule(self, rule: RateLimitRule) -> None:
        """Add or update a rate limit rule at runtime."""
        self._rules[rule.key] = rule
        self._logger.info(
            "rate_limit_rule_added",
            key=rule.key,
            max_requests=rule.max_requests,
            window_seconds=rule.window_seconds,
        )
