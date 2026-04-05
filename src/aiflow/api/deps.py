"""Centralized database dependencies — shared connection pool and engine.

All API endpoints should use these instead of creating their own connections.
"""
from __future__ import annotations

import os

import asyncpg
import structlog
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

__all__ = ["get_pool", "get_engine", "get_session_factory", "close_all"]

logger = structlog.get_logger(__name__)

_pool: asyncpg.Pool | None = None
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


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


async def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get the shared SQLAlchemy async session factory (created on first call)."""
    global _session_factory
    if _session_factory is None:
        engine = await get_engine()
        _session_factory = async_sessionmaker(engine, expire_on_commit=False)
        logger.info("db_session_factory_created")
    return _session_factory


async def close_all() -> None:
    """Close pool and engine — call on app shutdown."""
    global _pool, _engine, _session_factory
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("db_pool_closed")
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("db_engine_closed")
