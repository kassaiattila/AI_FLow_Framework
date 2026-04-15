"""E2E test for Alembic 034 — intake_packages.source_type hardening.

@test_registry
suite: phase_1b_e2e
tags: [e2e, phase_1b, alembic, intake, source_adapter]

Exercises the real Docker Postgres (port 5433) — no mocks per CLAUDE.md.

NOTE (feedback_asyncpg_pool_event_loop.md): asyncpg pools are event-loop-bound.
All assertions are merged into one @pytest.mark.asyncio method to share a
single pool across checks without pytest-asyncio recreating the loop.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import asyncpg
import pytest

from aiflow.api.deps import get_pool

REPO_ROOT = Path(__file__).resolve().parents[3]


def _alembic(*args: str) -> subprocess.CompletedProcess[str]:
    """Run alembic CLI against the real dev DB."""
    cmd = [sys.executable, "-m", "alembic", *args]
    return subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT / "src")},
        capture_output=True,
        text=True,
        check=False,
    )


async def _current_revision(conn: asyncpg.Connection) -> str | None:
    row = await conn.fetchrow("SELECT version_num FROM alembic_version")
    return None if row is None else row["version_num"]


@pytest.mark.asyncio
async def test_migration_034_source_type_hardening() -> None:
    """Full contract for Alembic 034: head revision, CHECK, NOT NULL, round-trip."""
    pool = await get_pool()

    async with pool.acquire() as conn:
        # 1. Head revision is 034
        assert await _current_revision(conn) == "034"

        # 2. CHECK constraint exists
        row = await conn.fetchrow(
            """
            SELECT conname
            FROM pg_constraint
            WHERE conrelid = 'intake_packages'::regclass
              AND conname = 'ck_intake_source_type'
            """
        )
        assert row is not None, "ck_intake_source_type constraint missing"

        # 3. source_type is NOT NULL
        row = await conn.fetchrow(
            """
            SELECT is_nullable
            FROM information_schema.columns
            WHERE table_name = 'intake_packages' AND column_name = 'source_type'
            """
        )
        assert row is not None and row["is_nullable"] == "NO"

        # 4. CHECK rejects unknown source_type
        with pytest.raises(asyncpg.exceptions.CheckViolationError):
            async with conn.transaction():
                await conn.execute(
                    """
                    INSERT INTO intake_packages (package_id, source_type, tenant_id)
                    VALUES ($1, 'NOT_A_REAL_TYPE', 'tenant-ck-violation')
                    """,
                    uuid4(),
                )

        # 5. CHECK accepts every whitelisted value (including legacy)
        for value in (
            "email",
            "file_upload",
            "folder_import",
            "batch_import",
            "api_push",
            "legacy",
        ):
            async with conn.transaction():
                pkg_id = uuid4()
                await conn.execute(
                    """
                    INSERT INTO intake_packages (package_id, source_type, tenant_id)
                    VALUES ($1, $2, $3)
                    """,
                    pkg_id,
                    value,
                    f"tenant-ck-accept-{value}",
                )
                await conn.execute("DELETE FROM intake_packages WHERE package_id = $1", pkg_id)

    # 6. Round-trip: downgrade -> upgrade leaves schema at 034 again
    down = _alembic("downgrade", "-1")
    assert down.returncode == 0, f"downgrade failed: {down.stderr}"
    up = _alembic("upgrade", "head")
    assert up.returncode == 0, f"upgrade failed: {up.stderr}"

    async with pool.acquire() as conn:
        assert await _current_revision(conn) == "034"
        row = await conn.fetchrow(
            """
            SELECT conname FROM pg_constraint
            WHERE conrelid = 'intake_packages'::regclass
              AND conname = 'ck_intake_source_type'
            """
        )
        assert row is not None, "CHECK constraint not restored after round-trip"
