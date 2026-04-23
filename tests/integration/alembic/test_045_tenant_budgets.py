"""Integration test — Alembic 045 ``tenant_budgets`` table + unique constraint.

@test_registry
suite: integration-alembic
component: alembic.versions.045_tenant_budgets
covers: [alembic/versions/045_tenant_budgets.py]
phase: v1.4.10
priority: high
requires_services: [postgres]
tags: [integration, alembic, migration, tenant_budgets, sprint_n, s121, postgres]

Real Docker PostgreSQL (port 5433) — SOHA NE mock (CLAUDE.md rule).

Validates Sprint N / S121:
* After ``upgrade 045``, the ``tenant_budgets`` table + unique constraint
  + CHECK on period + lookup index exist.
* Downgrade 045→044 cleanly removes the table.
* Re-upgrade is idempotent and preserves the composite unique key.

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


async def _constraint_exists(name: str) -> bool:
    conn = await _connect()
    try:
        row = await conn.fetchrow(
            "SELECT 1 FROM pg_constraint WHERE conname = $1",
            name,
        )
        return row is not None
    finally:
        await conn.close()


def test_045_upgrade_creates_table_indexes_and_constraints() -> None:
    cfg = _alembic_cfg()
    starting = asyncio.run(_current_revision())
    try:
        command.downgrade(cfg, "044")
        command.upgrade(cfg, "045")
        assert asyncio.run(_current_revision()) == "045"
        assert asyncio.run(_table_exists("tenant_budgets"))
        assert asyncio.run(_index_exists("idx_tenant_budgets_tenant_id"))
        assert asyncio.run(_constraint_exists("uq_tenant_budgets_tenant_period"))
        assert asyncio.run(_constraint_exists("ck_tenant_budgets_period"))
        assert asyncio.run(_constraint_exists("ck_tenant_budgets_limit_nonneg"))
    finally:
        if starting and starting != asyncio.run(_current_revision()):
            try:
                command.upgrade(cfg, starting)
            except Exception:
                pass


def test_045_downgrade_then_upgrade_is_clean_with_data_roundtrip() -> None:
    cfg = _alembic_cfg()
    starting = asyncio.run(_current_revision())

    async def _insert_and_read() -> tuple[float, list[int], bool]:
        conn = await _connect()
        try:
            await conn.execute(
                "DELETE FROM tenant_budgets WHERE tenant_id = $1",
                "s121-alembic-test",
            )
            await conn.execute(
                """
                INSERT INTO tenant_budgets
                    (tenant_id, period, limit_usd, alert_threshold_pct, enabled)
                VALUES ($1, $2, $3, $4::integer[], $5)
                """,
                "s121-alembic-test",
                "daily",
                25.50,
                [60, 90],
                True,
            )
            row = await conn.fetchrow(
                "SELECT limit_usd, alert_threshold_pct, enabled "
                "FROM tenant_budgets WHERE tenant_id = $1 AND period = $2",
                "s121-alembic-test",
                "daily",
            )
            return (
                float(row["limit_usd"]),
                list(row["alert_threshold_pct"]),
                bool(row["enabled"]),
            )
        finally:
            await conn.close()

    async def _cleanup() -> None:
        conn = await _connect()
        try:
            await conn.execute(
                "DELETE FROM tenant_budgets WHERE tenant_id = $1",
                "s121-alembic-test",
            )
        finally:
            await conn.close()

    try:
        command.upgrade(cfg, "045")
        assert asyncio.run(_table_exists("tenant_budgets"))

        limit, thresholds, enabled = asyncio.run(_insert_and_read())
        assert limit == 25.50
        assert thresholds == [60, 90]
        assert enabled is True

        asyncio.run(_cleanup())
        command.downgrade(cfg, "044")
        assert asyncio.run(_current_revision()) == "044"
        assert not asyncio.run(_table_exists("tenant_budgets"))

        command.upgrade(cfg, "045")
        assert asyncio.run(_current_revision()) == "045"
        assert asyncio.run(_table_exists("tenant_budgets"))
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
