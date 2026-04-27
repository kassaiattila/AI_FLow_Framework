"""Integration test — Alembic 049 ``rag_collections.customer`` drop.

@test_registry
suite: integration-alembic
component: alembic.versions.049_rag_collections_drop_customer
covers: [alembic/versions/049_rag_collections_drop_customer.py]
phase: v1.7.0
priority: high
requires_services: [postgres]
tags: [integration, alembic, migration, rag_collections, sprint_w, sw_3, postgres]

Real Docker PostgreSQL (port 5433) — SOHA NE mock (CLAUDE.md rule).

Validates Sprint W / SW-3 (SS-FU-1 / SS-FU-5):
* After ``upgrade 049``, the ``customer`` column on ``rag_collections`` is
  gone and the ``idx_rag_collections_customer`` index has been dropped.
* Downgrade 049→048 restores the column as nullable text + recreates the
  index. Existing rows have ``customer = NULL`` (lossy downgrade per the
  SS-FU-5 authorization).
* Re-upgrade after downgrade is clean.

NOTE (feedback_asyncpg_pool_event_loop.md): SYNC test — alembic.command.*
spin their own asyncio.run() loop via alembic/env.py.
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


async def _column_exists(table: str, column: str) -> bool:
    conn = await _connect()
    try:
        row = await conn.fetchrow(
            """
            SELECT 1 FROM information_schema.columns
            WHERE table_name = $1 AND column_name = $2
            """,
            table,
            column,
        )
        return row is not None
    finally:
        await conn.close()


async def _index_exists(name: str) -> bool:
    conn = await _connect()
    try:
        row = await conn.fetchrow("SELECT 1 FROM pg_indexes WHERE indexname = $1", name)
        return row is not None
    finally:
        await conn.close()


def test_049_drops_customer_column_and_index() -> None:
    cfg = _alembic_cfg()
    starting = asyncio.run(_current_revision())
    try:
        # Sprint X SX-3 — head moved past 049 (now 050+). Downgrade to 048
        # baseline first so the upgrade-to-049 below isn't a no-op when the
        # DB is already past 049.
        command.downgrade(cfg, "048")
        command.upgrade(cfg, "049")
        assert asyncio.run(_current_revision()) == "049"
        assert not asyncio.run(_column_exists("rag_collections", "customer"))
        assert not asyncio.run(_index_exists("idx_rag_collections_customer"))

        command.downgrade(cfg, "048")
        assert asyncio.run(_current_revision()) == "048"
        assert asyncio.run(_column_exists("rag_collections", "customer"))
        assert asyncio.run(_index_exists("idx_rag_collections_customer"))

        command.upgrade(cfg, "049")
        assert asyncio.run(_current_revision()) == "049"
        assert not asyncio.run(_column_exists("rag_collections", "customer"))
    finally:
        if starting and starting != asyncio.run(_current_revision()):
            try:
                command.upgrade(cfg, starting)
            except Exception:
                pass
