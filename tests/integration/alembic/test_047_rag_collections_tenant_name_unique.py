"""Integration test — Alembic 047 ``rag_collections (tenant_id, name)`` unique.

@test_registry
suite: integration-alembic
component: alembic.versions.047_rag_collections_tenant_name_unique
covers: [alembic/versions/047_rag_collections_tenant_name_unique.py]
phase: v1.5.2
priority: high
requires_services: [postgres]
tags: [integration, alembic, migration, rag_collections, sprint_s, s145, postgres]

Real Docker PostgreSQL (port 5433) — SOHA NE mock (CLAUDE.md rule).

Validates Sprint S / S145 SS-FU-4:
* After ``upgrade 047``, ``rag_collections_name_key`` (UNIQUE name) is
  gone and ``uq_rag_collections_tenant_name`` (UNIQUE tenant_id, name)
  is in place. Two tenants may now share a collection name; uniqueness
  within a tenant is preserved.
* Downgrade 047→046 reverses the swap: name-only unique restored,
  composite unique gone.
* Re-upgrade after downgrade is clean.

NOTE (feedback_asyncpg_pool_event_loop.md): SYNC test — alembic.command.*
spin their own asyncio.run() loop via alembic/env.py.

Sprint X SX-2 repair note:
* Sprint W SW-3 (Alembic 049) dropped the ``customer`` column from
  ``rag_collections``. The test originally hard-coded
  ``command.upgrade(cfg, "047")`` as the first step, which is a no-op
  when starting from head=049 (alembic upgrade is forward-only). It also
  inserted with ``customer`` in the column list — the column is gone at
  head and exists only when the migration has been rolled back to
  ≤ 048. The test now uses :func:`_move_to` to downgrade from any post-047
  head to revision 047 and back, and the insert helper omits the dropped
  ``customer`` column (relying on the column's nullability at revisions
  ≤ 048 — see ``alembic/versions/049_rag_collections_drop_customer.py``).
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

_OLD_NAME_UNIQUE = "rag_collections_name_key"
_NEW_TENANT_NAME_UNIQUE = "uq_rag_collections_tenant_name"

_TEST_NAMES = ("s145-alembic-shared", "s145-alembic-unique-a", "s145-alembic-unique-b")


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


async def _constraint_exists(name: str) -> bool:
    conn = await _connect()
    try:
        row = await conn.fetchrow(
            """
            SELECT 1 FROM pg_constraint con
            JOIN pg_class rel ON rel.oid = con.conrelid
            WHERE rel.relname = 'rag_collections' AND con.conname = $1
            """,
            name,
        )
        return row is not None
    finally:
        await conn.close()


async def _cleanup_test_rows() -> None:
    conn = await _connect()
    try:
        await conn.execute(
            "DELETE FROM rag_collections WHERE name = ANY($1::text[])",
            list(_TEST_NAMES),
        )
    finally:
        await conn.close()


async def _insert(tenant: str, name: str) -> None:
    """Insert a row that works at any revision in [046, 048].

    The ``customer`` column was dropped in 049 (SW-3); 046–048 leave it
    nullable, so omitting it is forward-compatible across the test's
    downgrade window.
    """
    conn = await _connect()
    try:
        await conn.execute(
            """
            INSERT INTO rag_collections (id, name, skill_name, tenant_id)
            VALUES (gen_random_uuid(), $1, 'rag_engine', $2)
            """,
            name,
            tenant,
        )
    finally:
        await conn.close()


def _move_to(cfg: Config, target: str) -> None:
    """Move the alembic state to ``target``, picking the right direction.

    Required because ``command.upgrade`` is forward-only — calling
    ``upgrade(cfg, "047")`` from head=049 is a silent no-op. With
    Sprint W's 048+049 migrations the test must be able to walk
    backwards from head to 047 to inspect the constraint state.
    """
    current = asyncio.run(_current_revision())
    if current == target:
        return
    # Compare zero-padded revision IDs: alembic IDs are 3-digit.
    if current is None or current < target:
        command.upgrade(cfg, target)
    else:
        command.downgrade(cfg, target)


def test_047_upgrade_swaps_constraints_and_downgrade_roundtrip() -> None:
    cfg = _alembic_cfg()
    starting = asyncio.run(_current_revision())
    try:
        _move_to(cfg, "047")
        assert asyncio.run(_current_revision()) == "047"
        assert not asyncio.run(_constraint_exists(_OLD_NAME_UNIQUE))
        assert asyncio.run(_constraint_exists(_NEW_TENANT_NAME_UNIQUE))

        command.downgrade(cfg, "046")
        assert asyncio.run(_current_revision()) == "046"
        assert asyncio.run(_constraint_exists(_OLD_NAME_UNIQUE))
        assert not asyncio.run(_constraint_exists(_NEW_TENANT_NAME_UNIQUE))

        command.upgrade(cfg, "047")
        assert asyncio.run(_current_revision()) == "047"
        assert not asyncio.run(_constraint_exists(_OLD_NAME_UNIQUE))
        assert asyncio.run(_constraint_exists(_NEW_TENANT_NAME_UNIQUE))
    finally:
        if starting and starting != asyncio.run(_current_revision()):
            try:
                _move_to(cfg, starting)
            except Exception:
                pass


def test_047_cross_tenant_name_collision_allowed_after_upgrade() -> None:
    cfg = _alembic_cfg()
    starting = asyncio.run(_current_revision())
    try:
        _move_to(cfg, "047")
        asyncio.run(_cleanup_test_rows())

        asyncio.run(_insert("tenant-a", "s145-alembic-shared"))
        asyncio.run(_insert("tenant-b", "s145-alembic-shared"))

        with pytest.raises(asyncpg.UniqueViolationError):
            asyncio.run(_insert("tenant-a", "s145-alembic-shared"))

        asyncio.run(_cleanup_test_rows())

        command.downgrade(cfg, "046")
        asyncio.run(_insert("tenant-a", "s145-alembic-shared"))
        with pytest.raises(asyncpg.UniqueViolationError):
            asyncio.run(_insert("tenant-b", "s145-alembic-shared"))
    finally:
        try:
            asyncio.run(_cleanup_test_rows())
        except Exception:
            pass
        if starting and starting != asyncio.run(_current_revision()):
            try:
                _move_to(cfg, starting)
            except Exception:
                pass
