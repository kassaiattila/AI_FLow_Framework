"""Shared fixtures for service unit tests.

Provides mock pool, connection, and Redis client fixtures
for services that depend on PostgreSQL or Redis.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture()
def mock_pool():
    """Mock asyncpg connection pool with acquire() context manager.

    asyncpg's ``pool.acquire()`` is a synchronous call that returns
    an async context manager (PoolAcquireContext).  The mock must
    therefore use a *regular* MagicMock for pool so that ``acquire()``
    is not wrapped in a coroutine, while the context manager itself
    has async ``__aenter__``/``__aexit__``.
    """
    pool = MagicMock()
    conn = AsyncMock()

    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=conn)
    ctx.__aexit__ = AsyncMock(return_value=False)
    pool.acquire.return_value = ctx

    return pool, conn


@pytest.fixture()
def mock_redis():
    """Mock Redis async client with common commands."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    redis.ping = AsyncMock(return_value=True)
    redis.info = AsyncMock(return_value={"used_memory": 1024})
    redis.scan_iter = MagicMock(return_value=AsyncIterMock([]))
    redis.pipeline = MagicMock(return_value=AsyncPipelineMock())
    redis.aclose = AsyncMock()
    return redis


class AsyncIterMock:
    """Async iterator mock for redis.scan_iter()."""

    def __init__(self, items: list):
        self._items = items
        self._index = 0

    def __aiter__(self):
        self._index = 0
        return self

    async def __anext__(self):
        if self._index >= len(self._items):
            raise StopAsyncIteration
        item = self._items[self._index]
        self._index += 1
        return item


class AsyncPipelineMock:
    """Mock Redis pipeline with chainable commands."""

    def __init__(self):
        self._results: list = [0, 0, True, True]

    def zremrangebyscore(self, *args, **kwargs):
        return self

    def zcard(self, *args, **kwargs):
        return self

    def zadd(self, *args, **kwargs):
        return self

    def expire(self, *args, **kwargs):
        return self

    async def execute(self):
        return self._results
