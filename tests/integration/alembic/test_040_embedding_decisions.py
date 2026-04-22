"""Integration test — Alembic 040 embedding_decisions table + index.

@test_registry
suite: integration-alembic
component: alembic.versions.040_embedding_decisions
covers: [alembic/versions/040_embedding_decisions.py]
phase: v1.4.6
priority: high
requires_services: [postgres]
tags: [integration, alembic, migration, embedding_decisions, postgres]

Exercises the real Docker PostgreSQL (port 5433) — SOHA NE mock (see CLAUDE.md).

Validates Sprint J (v1.4.6 / S100):
* After upgrade head, the `embedding_decisions` table + tenant index + CHECK
  constraint on profile exist in the live catalog.
* Downgrade 040→039 removes the table cleanly.
* Re-upgrade is idempotent.

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
    """Honor AIFLOW_DATABASE__URL (CI) and fall back to the Docker dev default."""
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


async def _table_exists(name: str) -> bool:
    conn = await _connect()
    try:
        row = await conn.fetchrow(
            "SELECT 1 FROM information_schema.tables WHERE table_name = $1",
            name,
        )
        return row is not None
    finally:
        await conn.close()


async def _index_exists(name: str) -> bool:
    conn = await _connect()
    try:
        row = await conn.fetchrow(
            "SELECT 1 FROM pg_indexes WHERE indexname = $1",
            name,
        )
        return row is not None
    finally:
        await conn.close()


async def _check_constraint_exists(name: str) -> bool:
    conn = await _connect()
    try:
        row = await conn.fetchrow(
            "SELECT 1 FROM pg_constraint WHERE conname = $1",
            name,
        )
        return row is not None
    finally:
        await conn.close()


def test_040_upgrade_creates_table_index_and_constraint() -> None:
    cfg = _alembic_cfg()
    starting = asyncio.run(_current_revision())
    try:
        command.upgrade(cfg, "040")
        assert asyncio.run(_current_revision()) == "040"
        assert asyncio.run(_table_exists("embedding_decisions"))
        assert asyncio.run(_index_exists("ix_embedding_decisions_tenant"))
        assert asyncio.run(_check_constraint_exists("ck_embedding_decisions_profile"))
    finally:
        if starting and starting != asyncio.run(_current_revision()):
            try:
                command.upgrade(cfg, starting)
            except Exception:
                pass


def test_040_downgrade_then_upgrade_is_clean() -> None:
    cfg = _alembic_cfg()
    starting = asyncio.run(_current_revision())
    try:
        command.upgrade(cfg, "040")
        assert asyncio.run(_table_exists("embedding_decisions"))

        command.downgrade(cfg, "039")
        assert asyncio.run(_current_revision()) == "039"
        assert not asyncio.run(_table_exists("embedding_decisions"))
        assert not asyncio.run(_index_exists("ix_embedding_decisions_tenant"))

        command.upgrade(cfg, "040")
        assert asyncio.run(_current_revision()) == "040"
        assert asyncio.run(_table_exists("embedding_decisions"))
        assert asyncio.run(_index_exists("ix_embedding_decisions_tenant"))
    finally:
        if starting and starting != asyncio.run(_current_revision()):
            try:
                command.upgrade(cfg, starting)
            except Exception:
                pass
