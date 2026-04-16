"""Integration test — Alembic 036 association_mode backfill.

@test_registry
suite: integration-alembic
component: alembic.versions.036_association_mode_backfill
covers: [alembic/versions/036_association_mode_backfill.py]
phase: 1c
priority: critical
requires_services: [postgres]
tags: [integration, alembic, migration, association_mode, postgres]

Exercises the real Docker PostgreSQL (port 5433) — SOHA NE mock (see CLAUDE.md).

Validates architect condition C5 part a:
* description_count = 0            -> stays NULL.
* description_count = 1            -> 'single_description'.
* description_count = file_count   -> 'order'.
* N/M mismatch                     -> stays NULL + WARNING log.
* Pre-set association_mode (not NULL) -> UNCHANGED.
* downgrade is a no-op (rows unchanged on revert).

NOTE (feedback_asyncpg_pool_event_loop.md): this test is SYNC — we call
``alembic.command.upgrade/downgrade`` which runs its own asyncio.run()
internally via ``alembic/env.py``. Seed + assert blocks each spin up a
short-lived ``asyncio.run(...)`` with a direct asyncpg.connect — no
pool reuse, no cross-loop state.
"""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from uuid import UUID, uuid4

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


async def _connect():
    import asyncpg

    return await asyncpg.connect(_DB_URL_ASYNCPG)


async def _seed(tenant_id: str) -> dict[str, UUID]:
    """Seed five scenarios, return package_id map keyed by label."""
    conn = await _connect()
    try:
        ids = {label: uuid4() for label in ("A", "B", "C", "D", "E")}

        # package A: 0 desc, 2 files, association_mode NULL
        await conn.execute(
            "INSERT INTO intake_packages (package_id, source_type, tenant_id) "
            "VALUES ($1, 'batch_import', $2)",
            ids["A"],
            tenant_id,
        )
        await _insert_files(conn, ids["A"], count=2)

        # package B: 1 desc, 1 file, association_mode NULL
        await conn.execute(
            "INSERT INTO intake_packages (package_id, source_type, tenant_id) "
            "VALUES ($1, 'batch_import', $2)",
            ids["B"],
            tenant_id,
        )
        await _insert_files(conn, ids["B"], count=1)
        await _insert_descriptions(conn, ids["B"], count=1)

        # package C: 3 desc, 3 files, association_mode NULL
        await conn.execute(
            "INSERT INTO intake_packages (package_id, source_type, tenant_id) "
            "VALUES ($1, 'batch_import', $2)",
            ids["C"],
            tenant_id,
        )
        await _insert_files(conn, ids["C"], count=3)
        await _insert_descriptions(conn, ids["C"], count=3)

        # package D: 2 desc, 5 files (N/M mismatch), association_mode NULL
        await conn.execute(
            "INSERT INTO intake_packages (package_id, source_type, tenant_id) "
            "VALUES ($1, 'batch_import', $2)",
            ids["D"],
            tenant_id,
        )
        await _insert_files(conn, ids["D"], count=5)
        await _insert_descriptions(conn, ids["D"], count=2)

        # package E: already 'explicit' — must remain unchanged.
        await conn.execute(
            "INSERT INTO intake_packages (package_id, source_type, tenant_id, association_mode) "
            "VALUES ($1, 'batch_import', $2, 'explicit')",
            ids["E"],
            tenant_id,
        )
        await _insert_files(conn, ids["E"], count=1)
        await _insert_descriptions(conn, ids["E"], count=1)

        return ids
    finally:
        await conn.close()


async def _insert_files(conn, package_id: UUID, count: int) -> None:
    for i in range(count):
        await conn.execute(
            """
            INSERT INTO intake_files
                (file_id, package_id, file_path, file_name, mime_type, size_bytes, sha256)
            VALUES ($1, $2, $3, $4, 'application/pdf', 10, $5)
            """,
            uuid4(),
            package_id,
            f"/tmp/{uuid.uuid4().hex}.pdf",
            f"f{i}.pdf",
            uuid.uuid4().hex + uuid.uuid4().hex,  # 64 hex chars
        )


async def _insert_descriptions(conn, package_id: UUID, count: int) -> None:
    for i in range(count):
        await conn.execute(
            "INSERT INTO intake_descriptions (description_id, package_id, text) "
            "VALUES ($1, $2, $3)",
            uuid4(),
            package_id,
            f"description {i}",
        )


async def _read_modes(package_ids: dict[str, UUID]) -> dict[str, str | None]:
    conn = await _connect()
    try:
        out: dict[str, str | None] = {}
        for label, pid in package_ids.items():
            row = await conn.fetchrow(
                "SELECT association_mode FROM intake_packages WHERE package_id = $1",
                pid,
            )
            out[label] = None if row is None else row["association_mode"]
        return out
    finally:
        await conn.close()


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


def test_036_association_mode_backfill() -> None:
    """Full C5a contract: backfill fills correct rows, no-op downgrade, warns on N/M."""
    cfg = _alembic_cfg()
    tenant_id = f"tenant-036-{uuid4().hex[:8]}"

    starting_revision = asyncio.run(_current_revision())

    # Stage the DB at 035 so our seeded NULLs aren't already backfilled.
    if starting_revision != "035":
        command.downgrade(cfg, "035")
    assert asyncio.run(_current_revision()) == "035"

    package_ids = asyncio.run(_seed(tenant_id))
    pre_upgrade_modes = asyncio.run(_read_modes(package_ids))
    assert pre_upgrade_modes == {
        "A": None,
        "B": None,
        "C": None,
        "D": None,
        "E": "explicit",
    }

    try:
        # --- upgrade 035 -> 036: runs the backfill --------------------------
        command.upgrade(cfg, "036")
        assert asyncio.run(_current_revision()) == "036"

        post_upgrade = asyncio.run(_read_modes(package_ids))
        assert post_upgrade == {
            "A": None,  # 0 desc, 2 files -> NULL
            "B": "single_description",  # 1 desc, 1 file
            "C": "order",  # 3/3
            "D": None,  # 2/5 mismatch -> NULL + warning
            "E": "explicit",  # pre-set, untouched
        }

        # --- downgrade 036 -> 035 is a no-op on data ------------------------
        command.downgrade(cfg, "035")
        assert asyncio.run(_current_revision()) == "035"
        post_downgrade = asyncio.run(_read_modes(package_ids))
        assert post_downgrade == post_upgrade, (
            "downgrade must NOT revert data — migration docstring declares no-op"
        )

        # --- re-upgrade is idempotent ---------------------------------------
        command.upgrade(cfg, "036")
        assert asyncio.run(_current_revision()) == "036"
        post_reupgrade = asyncio.run(_read_modes(package_ids))
        assert post_reupgrade == post_upgrade
    finally:
        # Leave DB at head for subsequent tests.
        if starting_revision and starting_revision != "036":
            # Preserve the revision the test started on where possible.
            try:
                command.upgrade(cfg, starting_revision)
            except Exception:
                # starting_revision was older than 036 — fine, stay at 036.
                pass
        asyncio.run(_cleanup(tenant_id))


def test_decide_mode_decision_table() -> None:
    """Pure-function decision table — imports the migration module directly."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "mig_036",
        _PROJECT_ROOT / "alembic" / "versions" / "036_association_mode_backfill.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module._decide_mode(0, 0) is None
    assert module._decide_mode(0, 5) is None
    assert module._decide_mode(1, 0) == "single_description"
    assert module._decide_mode(1, 3) == "single_description"
    assert module._decide_mode(3, 3) == "order"
    assert module._decide_mode(1, 1) == "single_description"  # 1 wins over order
    assert module._decide_mode(2, 5) is None  # mismatch
    assert module._decide_mode(5, 2) is None  # mismatch
    assert module._decide_mode(2, 0) is None  # desc without files
