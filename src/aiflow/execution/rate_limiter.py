"""Token bucket rate limiter for API and workflow throttling."""
from __future__ import annotations

import time

import structlog
from pydantic import BaseModel

__all__ = ["RateLimitConfig", "RateLimiter", "InMemoryRateLimiter"]

logger = structlog.get_logger(__name__)


class RateLimitConfig(BaseModel):
    """Rate limit configuration."""

    requests_per_second: float = 10.0
    burst_size: int = 20
    key: str = "default"


class RateLimiter:
    """Abstract rate limiter interface."""

    async def allow(self, key: str = "default") -> bool:
        """Check if a request is allowed. Returns True if allowed."""
        raise NotImplementedError

    async def reset(self, key: str = "default") -> None:
        """Reset the rate limiter for a key."""
        raise NotImplementedError


class InMemoryRateLimiter(RateLimiter):
    """Token bucket rate limiter (in-memory)."""

    def __init__(self, config: RateLimitConfig | None = None) -> None:
        self._config = config or RateLimitConfig()
        self._buckets: dict[str, dict] = {}

    def _get_bucket(self, key: str) -> dict:
        """Get or create a token bucket for the given key."""
        if key not in self._buckets:
            self._buckets[key] = {
                "tokens": float(self._config.burst_size),
                "last_refill": time.monotonic(),
            }
        return self._buckets[key]

    def _refill(self, bucket: dict) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - bucket["last_refill"]
        bucket["tokens"] = min(
            self._config.burst_size,
            bucket["tokens"] + elapsed * self._config.requests_per_second,
        )
        bucket["last_refill"] = now

    async def allow(self, key: str = "default") -> bool:
        """Check if request is allowed under rate limit."""
        bucket = self._get_bucket(key)
        self._refill(bucket)

        if bucket["tokens"] >= 1.0:
            bucket["tokens"] -= 1.0
            return True

        logger.debug("rate_limited", key=key, tokens=bucket["tokens"])
        return False

    async def reset(self, key: str = "default") -> None:
        """Reset rate limiter for a key."""
        if key in self._buckets:
            del self._buckets[key]

    @property
    def config(self) -> RateLimitConfig:
        """Return the rate limit configuration."""
        return self._config
