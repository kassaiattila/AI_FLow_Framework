"""Integration test — Alembic 037 CHECK trigger on association_mode.

@test_registry
suite: integration-alembic
component: alembic.versions.037_association_mode_check_constraint
covers: [alembic/versions/037_association_mode_check_constraint.py]
phase: 1c
priority: critical
requires_services: [postgres]
tags: [integration, alembic, migration, association_mode, trigger, postgres]

Exercises the real Docker PostgreSQL (port 5433) — SOHA NE mock (see CLAUDE.md).

Validates architect condition C5 part b:
* INSERT description where parent.association_mode IS NULL   -> REJECTED.
* INSERT description where parent.association_mode IS set    -> ACCEPTED.
* UPDATE description.package_id to a NULL-mode parent        -> REJECTED.
* Zero-description packages with NULL mode remain legal.
* Downgrade removes trigger (INSERT into NULL-mode parent succeeds again).
* Re-upgrade is idempotent.

NOTE (feedback_asyncpg_pool_event_loop.md): SYNC test — command.upgrade/
downgrade run their own asyncio.run() via alembic/env.py; seed + assert
blocks each open a short-lived asyncpg.connect().
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from uuid import UUID, uuid4

import asyncpg
import pytest
from alembic import command
from alembic.config import Config

pytestmark = pytest.mark.integration


_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_ALEMBIC_INI = _PROJECT_ROOT / "alembic.ini"

_DB_URL_ASYNCPG = "postgresql://aiflow:aiflow_dev_password@localhost:5433/aiflow_dev"


def _alembic_cfg() -> Config:
    cfg = Config(str(_ALEMBIC_INI))
    cfg.set_main_option("script_location", str(_PROJECT_ROOT / "alembic"))
    return cfg


async def _connect() -> asyncpg.Connection:
    return await asyncpg.connect(_DB_URL_ASYNCPG)


async def _insert_package(
    conn: asyncpg.Connection,
    tenant_id: str,
    *,
    mode: str | None,
) -> UUID:
    pid = uuid4()
    if mode is None:
        await conn.execute(
            "INSERT INTO intake_packages (package_id, source_type, tenant_id) "
            "VALUES ($1, 'batch_import', $2)",
            pid,
            tenant_id,
        )
    else:
        await conn.execute(
            "INSERT INTO intake_packages (package_id, source_type, tenant_id, association_mode) "
            "VALUES ($1, 'batch_import', $2, $3::association_mode_enum)",
            pid,
            tenant_id,
            mode,
        )
    return pid


async def _insert_description(
    conn: asyncpg.Connection,
    package_id: UUID,
    *,
    text: str = "desc",
) -> UUID:
    did = uuid4()
    await conn.execute(
        "INSERT INTO intake_descriptions (description_id, package_id, text) VALUES ($1, $2, $3)",
        did,
        package_id,
        text,
    )
    return did


async def _cleanup(tenant_id: str) -> None:
    conn = await _connect()
    try:
        rows = await conn.fetch(
            "SELECT package_id FROM intake_packages WHERE tenant_id = $1",
            tenant_id,
        )
        if not rows:
            return
        ids = [r["package_id"] for r in rows]
        async with conn.transaction():
            await conn.execute(
                "DELETE FROM intake_descriptions WHERE package_id = ANY($1::uuid[])",
                ids,
            )
            await conn.execute(
                "DELETE FROM intake_files WHERE package_id = ANY($1::uuid[])",
                ids,
            )
            await conn.execute(
                "DELETE FROM intake_packages WHERE package_id = ANY($1::uuid[])",
                ids,
            )
    finally:
        await conn.close()


async def _current_revision() -> str | None:
    conn = await _connect()
    try:
        row = await conn.fetchrow("SELECT version_num FROM alembic_version")
        return None if row is None else row["version_num"]
    finally:
        await conn.close()


async def _run_trigger_cases(tenant_id: str) -> None:
    """Exercise the trigger behaviour at revision 037."""
    conn = await _connect()
    try:
        # --- (1) NULL-mode parent: description INSERT must fail ---------------
        # ERRCODE 'check_violation' -> asyncpg.exceptions.CheckViolationError.
        null_pkg = await _insert_package(conn, tenant_id, mode=None)
        with pytest.raises(asyncpg.exceptions.CheckViolationError) as exc_info:
            await _insert_description(conn, null_pkg, text="should-fail")
        msg = str(exc_info.value)
        assert "association_mode" in msg, f"expected 'association_mode' in {msg!r}"
        assert str(null_pkg) in msg, f"expected package_id {null_pkg} in {msg!r}"

        # --- (2) mode-set parent: description INSERT succeeds -----------------
        ok_pkg = await _insert_package(conn, tenant_id, mode="single_description")
        ok_desc = await _insert_description(conn, ok_pkg, text="ok")

        # --- (3) re-parent description to NULL-mode parent must fail ---------
        with pytest.raises(asyncpg.exceptions.CheckViolationError) as exc_info:
            await conn.execute(
                "UPDATE intake_descriptions SET package_id = $1 WHERE description_id = $2",
                null_pkg,
                ok_desc,
            )
        assert "association_mode" in str(exc_info.value)

        # --- (4) zero-description NULL-mode packages remain legal -------------
        bare_pkg = await _insert_package(conn, tenant_id, mode=None)
        row = await conn.fetchrow(
            "SELECT association_mode FROM intake_packages WHERE package_id = $1",
            bare_pkg,
        )
        assert row is not None and row["association_mode"] is None
    finally:
        await conn.close()


async def _assert_no_trigger(tenant_id: str) -> None:
    """At revision 036 the trigger is gone — NULL-mode + description must succeed."""
    conn = await _connect()
    try:
        pkg = await _insert_package(conn, tenant_id, mode=None)
        await _insert_description(conn, pkg, text="post-downgrade")
    finally:
        await conn.close()


def test_037_check_trigger_rejects_null_mode_with_descriptions() -> None:
    """Full C5b contract: trigger rejects violators, allows legal rows,
    downgrade removes enforcement, re-upgrade is idempotent."""
    cfg = _alembic_cfg()
    tenant_id = f"tenant-037-{uuid4().hex[:8]}"

    starting_revision = asyncio.run(_current_revision())

    try:
        # --- stage at 037 and exercise the trigger ---------------------------
        command.upgrade(cfg, "037")
        assert asyncio.run(_current_revision()) == "037"
        asyncio.run(_run_trigger_cases(tenant_id))

        # --- downgrade to 036: trigger removed, constraint no longer applies -
        # Clean up any rows from the 037 test first so the downgrade and
        # subsequent post-downgrade insert run on a predictable tenant slice.
        asyncio.run(_cleanup(tenant_id))
        command.downgrade(cfg, "036")
        assert asyncio.run(_current_revision()) == "036"
        asyncio.run(_assert_no_trigger(tenant_id))

        # --- re-upgrade is idempotent ---------------------------------------
        asyncio.run(_cleanup(tenant_id))
        command.upgrade(cfg, "037")
        assert asyncio.run(_current_revision()) == "037"
        asyncio.run(_run_trigger_cases(tenant_id))
    finally:
        asyncio.run(_cleanup(tenant_id))
        if starting_revision and starting_revision != asyncio.run(_current_revision()):
            try:
                command.upgrade(cfg, starting_revision)
            except Exception:
                pass


def test_037_trigger_function_and_object_present() -> None:
    """Smoke-test: the trigger + function actually exist in pg_catalog at 037."""

    async def _probe() -> tuple[bool, bool]:
        conn = await _connect()
        try:
            fn_row = await conn.fetchrow(
                "SELECT 1 FROM pg_proc WHERE proname = $1",
                "intake_require_association_mode",
            )
            tg_row = await conn.fetchrow(
                "SELECT 1 FROM pg_trigger WHERE tgname = $1 AND NOT tgisinternal",
                "intake_descriptions_require_mode",
            )
            return (fn_row is not None, tg_row is not None)
        finally:
            await conn.close()

    cfg = _alembic_cfg()
    starting = asyncio.run(_current_revision())
    try:
        command.upgrade(cfg, "037")
        fn_exists, tg_exists = asyncio.run(_probe())
        assert fn_exists, "function intake_require_association_mode() missing at 037"
        assert tg_exists, "trigger intake_descriptions_require_mode missing at 037"
    finally:
        if starting and starting != asyncio.run(_current_revision()):
            try:
                command.upgrade(cfg, starting)
            except Exception:
                pass
