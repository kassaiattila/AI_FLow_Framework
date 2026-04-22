"""Integration test — Alembic 041 rag_chunks.embedding_dim column.

@test_registry
suite: integration-alembic
component: alembic.versions.041_rag_chunks_embedding_dim
covers: [alembic/versions/041_rag_chunks_embedding_dim.py]
phase: v1.4.6
priority: high
requires_services: [postgres]
tags: [integration, alembic, migration, rag_chunks, postgres]

Exercises the real Docker PostgreSQL (port 5433) — SOHA NE mock (see CLAUDE.md).

Validates Sprint J (v1.4.6 / S101):
* After upgrade to 041, ``rag_chunks.embedding_dim`` column exists as
  nullable ``integer`` on the live table.
* Downgrade 041→040 drops the column cleanly.
* Re-upgrade is idempotent (column re-added with same type + nullability).

NOTE (feedback_asyncpg_pool_event_loop.md): SYNC test — command.upgrade/
downgrade run their own asyncio.run() via alembic/env.py.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import asyncpg
import pytest
from alembic import command
from alembic.config import Config

pytestmark = pytest.mark.integration


_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_ALEMBIC_INI = _PROJECT_ROOT / "alembic.ini"


def _resolve_db_url() -> str:
    raw = os.getenv(
        "AIFLOW_DATABASE__URL",
        "postgresql+asyncpg://aiflow:aiflow_dev_password@localhost:5433/aiflow_dev",
    )
    return raw.replace("postgresql+asyncpg://", "postgresql://")


_DB_URL_ASYNCPG = _resolve_db_url()


def _alembic_cfg() -> Config:
    cfg = Config(str(_ALEMBIC_INI))
    cfg.set_main_option("script_location", str(_PROJECT_ROOT / "alembic"))
    cfg.set_main_option(
        "sqlalchemy.url",
        _DB_URL_ASYNCPG.replace("postgresql://", "postgresql+asyncpg://"),
    )
    return cfg


async def _connect() -> asyncpg.Connection:
    return await asyncpg.connect(_DB_URL_ASYNCPG)


async def _current_revision() -> str | None:
    conn = await _connect()
    try:
        row = await conn.fetchrow("SELECT version_num FROM alembic_version")
        return None if row is None else row["version_num"]
    finally:
        await conn.close()


async def _column_info(table: str, column: str) -> tuple[str, str] | None:
    conn = await _connect()
    try:
        row = await conn.fetchrow(
            """
            SELECT data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = $1 AND column_name = $2
            """,
            table,
            column,
        )
        if row is None:
            return None
        return row["data_type"], row["is_nullable"]
    finally:
        await conn.close()


def test_041_upgrade_adds_embedding_dim_column() -> None:
    cfg = _alembic_cfg()
    starting = asyncio.run(_current_revision())
    try:
        command.downgrade(cfg, "040")
        command.upgrade(cfg, "041")
        assert asyncio.run(_current_revision()) == "041"
        info = asyncio.run(_column_info("rag_chunks", "embedding_dim"))
        assert info is not None, "embedding_dim column missing after upgrade 041"
        data_type, is_nullable = info
        assert data_type == "integer"
        assert is_nullable == "YES"
    finally:
        if starting and starting != asyncio.run(_current_revision()):
            try:
                command.upgrade(cfg, starting)
            except Exception:
                pass


def test_041_downgrade_then_upgrade_is_clean() -> None:
    cfg = _alembic_cfg()
    starting = asyncio.run(_current_revision())
    try:
        command.upgrade(cfg, "041")
        assert asyncio.run(_column_info("rag_chunks", "embedding_dim")) is not None

        command.downgrade(cfg, "040")
        assert asyncio.run(_current_revision()) == "040"
        assert asyncio.run(_column_info("rag_chunks", "embedding_dim")) is None

        command.upgrade(cfg, "041")
        info = asyncio.run(_column_info("rag_chunks", "embedding_dim"))
        assert info is not None
        assert info[0] == "integer"
        assert info[1] == "YES"
    finally:
        if starting and starting != asyncio.run(_current_revision()):
            try:
                command.upgrade(cfg, starting)
            except Exception:
                pass
