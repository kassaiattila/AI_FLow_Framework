"""Centralized database dependencies — shared connection pool and engine.

All API endpoints should use these instead of creating their own connections.
"""
from __future__ import annotations

import os

import asyncpg
import structlog
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

__all__ = ["get_pool", "get_engine", "close_all"]

logger = structlog.get_logger(__name__)

_pool: asyncpg.Pool | None = None
_engine: AsyncEngine | None = None


def _get_db_url_raw() -> str:
    """Get raw asyncpg connection URL (no SQLAlchemy prefix)."""
    url = os.environ.get(
        "AIFLOW_DATABASE__URL",
        "postgresql+asyncpg://aiflow:aiflow_dev_password@localhost:5433/aiflow_dev",
    )
    return url.replace("postgresql+asyncpg://", "postgresql://")


def _get_db_url_sa() -> str:
    """Get SQLAlchemy async connection URL."""
    url = os.environ.get(
        "AIFLOW_DATABASE__URL",
        "postgresql+asyncpg://aiflow:aiflow_dev_password@localhost:5433/aiflow_dev",
    )
    if not url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://")
    return url


async def get_pool() -> asyncpg.Pool:
    """Get the shared asyncpg connection pool (created on first call)."""
    global _pool
    if _pool is None:
        db_url = _get_db_url_raw()
        _pool = await asyncpg.create_pool(db_url, min_size=2, max_size=20)
        logger.info("db_pool_created", min_size=2, max_size=20)
    return _pool


async def get_engine() -> AsyncEngine:
    """Get the shared SQLAlchemy async engine (created on first call)."""
    global _engine
    if _engine is None:
        db_url = _get_db_url_sa()
        _engine = create_async_engine(db_url, pool_size=10, max_overflow=20)
        logger.info("db_engine_created", pool_size=10)
    return _engine


async def close_all() -> None:
    """Close pool and engine — call on app shutdown."""
    global _pool, _engine
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("db_pool_closed")
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        logger.info("db_engine_closed")
