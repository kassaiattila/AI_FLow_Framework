"""
@test_registry:
    suite: execution-unit
    component: execution.rate_limiter
    covers: [src/aiflow/execution/rate_limiter.py]
    phase: 5
    priority: high
    estimated_duration_ms: 150
    requires_services: []
    tags: [execution, rate-limiter, token-bucket]
"""
import pytest

from aiflow.execution.rate_limiter import InMemoryRateLimiter, RateLimitConfig


class TestRateLimitConfig:
    def test_default_config(self):
        config = RateLimitConfig()
        assert config.requests_per_second == 10.0
        assert config.burst_size == 20
        assert config.key == "default"

    def test_custom_config(self):
        config = RateLimitConfig(requests_per_second=5.0, burst_size=10, key="api")
        assert config.requests_per_second == 5.0
        assert config.burst_size == 10


class TestInMemoryRateLimiter:
    @pytest.fixture
    def limiter(self):
        config = RateLimitConfig(requests_per_second=10.0, burst_size=5)
        return InMemoryRateLimiter(config=config)

    @pytest.mark.asyncio
    async def test_allow_within_limit(self, limiter):
        allowed = await limiter.allow("test")
        assert allowed is True

    @pytest.mark.asyncio
    async def test_deny_when_exhausted(self, limiter):
        # Exhaust burst tokens
        for _ in range(5):
            await limiter.allow("test")
        # Next request should be denied (no time for refill)
        denied = await limiter.allow("test")
        assert denied is False

    @pytest.mark.asyncio
    async def test_burst_allows_multiple(self, limiter):
        results = []
        for _ in range(5):
            results.append(await limiter.allow("test"))
        assert all(results)

    @pytest.mark.asyncio
    async def test_reset_restores_tokens(self, limiter):
        # Exhaust tokens
        for _ in range(5):
            await limiter.allow("test")
        assert await limiter.allow("test") is False
        # Reset
        await limiter.reset("test")
        assert await limiter.allow("test") is True

    def test_config_property(self, limiter):
        assert limiter.config.burst_size == 5
        assert limiter.config.requests_per_second == 10.0
