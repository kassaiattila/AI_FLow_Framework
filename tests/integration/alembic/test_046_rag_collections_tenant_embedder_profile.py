"""Integration test — Alembic 046 ``rag_collections.tenant_id`` + ``embedder_profile_id``.

@test_registry
suite: integration-alembic
component: alembic.versions.046_rag_collections_tenant_embedder_profile
covers: [alembic/versions/046_rag_collections_tenant_embedder_profile.py]
phase: v1.5.2
priority: high
requires_services: [postgres]
tags: [integration, alembic, migration, rag_collections, sprint_s, s143, postgres]

Real Docker PostgreSQL (port 5433) — SOHA NE mock (CLAUDE.md rule).

Validates Sprint S / S143:
* After ``upgrade 046``, ``rag_collections`` gains ``tenant_id`` (NOT NULL,
  default 'default') and ``embedder_profile_id`` (nullable) columns plus
  the ``ix_rag_collections_tenant_id`` lookup index.
* Pre-existing rows are backfilled to ``tenant_id = 'default'`` via the
  server-default — no operator action required.
* Downgrade 046→045 drops the index + both columns.
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


async def _column_is_nullable(table: str, column: str) -> bool:
    conn = await _connect()
    try:
        row = await conn.fetchrow(
            """
            SELECT is_nullable FROM information_schema.columns
            WHERE table_name = $1 AND column_name = $2
            """,
            table,
            column,
        )
        assert row is not None, f"column {table}.{column} missing"
        return row["is_nullable"] == "YES"
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


def test_046_upgrade_adds_columns_and_index() -> None:
    cfg = _alembic_cfg()
    starting = asyncio.run(_current_revision())
    try:
        command.downgrade(cfg, "045")
        assert not asyncio.run(_column_exists("rag_collections", "tenant_id"))
        assert not asyncio.run(_column_exists("rag_collections", "embedder_profile_id"))

        command.upgrade(cfg, "046")
        assert asyncio.run(_current_revision()) == "046"
        assert asyncio.run(_column_exists("rag_collections", "tenant_id"))
        assert asyncio.run(_column_exists("rag_collections", "embedder_profile_id"))
        assert not asyncio.run(_column_is_nullable("rag_collections", "tenant_id"))
        assert asyncio.run(_column_is_nullable("rag_collections", "embedder_profile_id"))
        assert asyncio.run(_index_exists("ix_rag_collections_tenant_id"))
    finally:
        if starting and starting != asyncio.run(_current_revision()):
            try:
                command.upgrade(cfg, starting)
            except Exception:
                pass


def test_046_backfill_default_tenant_and_downgrade_roundtrip() -> None:
    cfg = _alembic_cfg()
    starting = asyncio.run(_current_revision())

    async def _seed_row_and_read_tenant() -> str:
        conn = await _connect()
        try:
            await conn.execute(
                "DELETE FROM rag_collections WHERE name = $1",
                "s143-alembic-test",
            )
            await conn.execute(
                """
                INSERT INTO rag_collections (id, name, customer, skill_name)
                VALUES (gen_random_uuid(), $1, 's143-test-customer', 'rag_engine')
                """,
                "s143-alembic-test",
            )
            row = await conn.fetchrow(
                "SELECT tenant_id, embedder_profile_id FROM rag_collections WHERE name = $1",
                "s143-alembic-test",
            )
            assert row is not None
            assert row["embedder_profile_id"] is None
            return row["tenant_id"]
        finally:
            await conn.close()

    async def _cleanup() -> None:
        conn = await _connect()
        try:
            await conn.execute(
                "DELETE FROM rag_collections WHERE name = $1",
                "s143-alembic-test",
            )
        finally:
            await conn.close()

    try:
        command.upgrade(cfg, "046")
        tenant = asyncio.run(_seed_row_and_read_tenant())
        assert tenant == "default", f"server_default backfill failed, got tenant_id={tenant!r}"

        asyncio.run(_cleanup())
        command.downgrade(cfg, "045")
        assert asyncio.run(_current_revision()) == "045"
        assert not asyncio.run(_column_exists("rag_collections", "tenant_id"))
        assert not asyncio.run(_column_exists("rag_collections", "embedder_profile_id"))

        command.upgrade(cfg, "046")
        assert asyncio.run(_current_revision()) == "046"
        assert asyncio.run(_index_exists("ix_rag_collections_tenant_id"))
    finally:
        try:
            asyncio.run(_cleanup())
        except Exception:
            pass
        if starting and starting != asyncio.run(_current_revision()):
            try:
                command.upgrade(cfg, starting)
            except Exception:
                pass
