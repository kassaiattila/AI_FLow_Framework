"""E2E test for Alembic 034 — intake_packages.source_type hardening.

@test_registry
suite: phase_1b_e2e
tags: [e2e, phase_1b, alembic, intake, source_adapter]

Exercises the real Docker Postgres (port 5433) — no mocks per CLAUDE.md.

NOTE (feedback_asyncpg_pool_event_loop.md): asyncpg pools are event-loop-bound.
All assertions are merged into one @pytest.mark.asyncio method to share a
single pool across checks without pytest-asyncio recreating the loop.

Resync note (S88 / v1.4.4.1, 2026-04-25): Alembic head advanced past 035 in
Phase 1c (036 association_backfill, 037 check_constraints). The test was
previously pinned to ``head == "035"`` with a ``downgrade -1`` round-trip,
which broke once head moved to 037 (downgrade -1 now lands on 036, not 034).

Rewritten to be **head-relative**: the test no longer hard-codes any migration
identifier. It records the current head, downgrades directly to 034, verifies
034's CHECK/NOT NULL/whitelist contract holds in isolation, then upgrades
back to the recorded head and re-verifies. The actual test subject is the
034 contract, not the specific head revision.
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


async def _assert_034_invariants(conn: asyncpg.Connection) -> None:
    """034's source_type hardening must hold at every revision from 034 onward."""
    # CHECK constraint exists
    row = await conn.fetchrow(
        """
        SELECT conname
        FROM pg_constraint
        WHERE conrelid = 'intake_packages'::regclass
          AND conname = 'ck_intake_source_type'
        """
    )
    assert row is not None, "ck_intake_source_type constraint missing"

    # source_type is NOT NULL
    row = await conn.fetchrow(
        """
        SELECT is_nullable
        FROM information_schema.columns
        WHERE table_name = 'intake_packages' AND column_name = 'source_type'
        """
    )
    assert row is not None and row["is_nullable"] == "NO"

    # CHECK rejects unknown source_type
    with pytest.raises(asyncpg.exceptions.CheckViolationError):
        async with conn.transaction():
            await conn.execute(
                """
                INSERT INTO intake_packages (package_id, source_type, tenant_id)
                VALUES ($1, 'NOT_A_REAL_TYPE', 'tenant-ck-violation')
                """,
                uuid4(),
            )

    # CHECK accepts every whitelisted value (including legacy)
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


@pytest.mark.asyncio
async def test_migration_034_source_type_hardening() -> None:
    """034 contract (CHECK, NOT NULL, whitelist) holds at head and survives a round-trip to 034 and back."""
    pool = await get_pool()

    # 1. Record current head (whatever it is — must be >= 034 for this test to be meaningful).
    async with pool.acquire() as conn:
        head_before = await _current_revision(conn)
        assert head_before is not None, "alembic_version empty — run `alembic upgrade head` first"

        # 2-5. 034 invariants hold at current head
        await _assert_034_invariants(conn)

    # 6. Downgrade directly to 034 and verify invariants still hold in isolation.
    down = _alembic("downgrade", "034")
    assert down.returncode == 0, f"downgrade to 034 failed: {down.stderr}"

    async with pool.acquire() as conn:
        assert await _current_revision(conn) == "034"
        await _assert_034_invariants(conn)

    # 7. Upgrade back to the original head and re-verify.
    up = _alembic("upgrade", "head")
    assert up.returncode == 0, f"upgrade head failed: {up.stderr}"

    async with pool.acquire() as conn:
        assert await _current_revision(conn) == head_before
        await _assert_034_invariants(conn)
