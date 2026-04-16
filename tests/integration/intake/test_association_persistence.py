"""Integration tests — association_mode round-trip via PostgreSQL.

@test_registry
suite: integration-intake
component: intake.associator, state.repositories.intake
covers: [src/aiflow/intake/package.py, src/aiflow/state/repositories/intake.py,
         src/aiflow/sources/batch_adapter.py, alembic/versions/035_association_mode.py]
phase: 1b
priority: critical
requires_services: [postgres]
tags: [integration, intake, association_mode, batch_adapter, postgres]

Exercises the real Docker PostgreSQL (port 5433) — no mocks per CLAUDE.md.

Validates:
* ``association_mode`` column round-trips for ORDER / FILENAME_MATCH / NULL via
  ``IntakeRepository.insert_package`` + ``get_package``.
* ``IntakeDescription.associated_file_ids`` survives the DB round-trip when
  the associator was run inside ``BatchSourceAdapter``.
* ``intake_packages.association_mode`` is the real PostgreSQL ENUM column
  (values rejected outside the whitelist by the DB, not by Python).

NOTE (feedback_asyncpg_pool_event_loop.md): asyncpg pools are event-loop-bound.
All assertions share a single ``get_pool()`` across one ``@pytest.mark.asyncio``
test method to avoid recreating the pool on each pytest-asyncio loop.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path
from uuid import uuid4

import asyncpg
import pytest

from aiflow.api.deps import get_pool
from aiflow.intake.package import AssociationMode, IntakeDescription
from aiflow.sources.batch_adapter import BatchSourceAdapter
from aiflow.state.repositories.intake import IntakeRepository

pytestmark = pytest.mark.integration


def _make_zip(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_STORED) as zf:
        for name, data in files.items():
            zf.writestr(name, data)
    return buf.getvalue()


async def _cleanup_tenant(pool: asyncpg.Pool, tenant_id: str) -> None:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT package_id FROM intake_packages WHERE tenant_id = $1",
            tenant_id,
        )
        if not rows:
            return
        ids = [r["package_id"] for r in rows]
        async with conn.transaction():
            await conn.execute(
                """
                DELETE FROM package_associations
                WHERE file_id IN (
                    SELECT file_id FROM intake_files WHERE package_id = ANY($1::uuid[])
                )
                """,
                ids,
            )
            await conn.execute(
                "DELETE FROM intake_descriptions WHERE package_id = ANY($1::uuid[])", ids
            )
            await conn.execute("DELETE FROM intake_files WHERE package_id = ANY($1::uuid[])", ids)
            await conn.execute(
                "DELETE FROM intake_packages WHERE package_id = ANY($1::uuid[])", ids
            )


@pytest.mark.asyncio
async def test_association_mode_round_trip(tmp_path: Path) -> None:
    """Full contract for E3.1-B: association_mode persisted + hydrated across 3 modes."""
    pool = await get_pool()
    repo = IntakeRepository(pool)

    tenant_order = f"tenant-assoc-order-{uuid4().hex[:8]}"
    tenant_filename = f"tenant-assoc-filename-{uuid4().hex[:8]}"
    tenant_none = f"tenant-assoc-none-{uuid4().hex[:8]}"

    try:
        # --- 1. ORDER mode ---------------------------------------------------
        order_adapter = BatchSourceAdapter(storage_root=tmp_path / "order", tenant_id=tenant_order)
        order_zip = _make_zip({"a.pdf": b"A", "b.pdf": b"B"})
        d1 = IntakeDescription(text="first")
        d2 = IntakeDescription(text="second")
        order_pkgs = order_adapter.enqueue(
            raw_bytes=order_zip,
            filename="order.zip",
            descriptions=[d1, d2],
            association_mode=AssociationMode.ORDER,
        )
        assert len(order_pkgs) == 1
        order_pkg = order_pkgs[0]
        await repo.insert_package(order_pkg)

        async with pool.acquire() as conn:
            raw_mode = await conn.fetchval(
                "SELECT association_mode FROM intake_packages WHERE package_id = $1",
                order_pkg.package_id,
            )
        assert raw_mode == "order"

        hydrated = await repo.get_package(order_pkg.package_id)
        assert hydrated is not None
        assert hydrated.association_mode == AssociationMode.ORDER
        assert len(hydrated.files) == 2
        assert len(hydrated.descriptions) == 2
        hydrated_by_id = {d.description_id: d for d in hydrated.descriptions}
        first_file_id = order_pkg.files[0].file_id
        second_file_id = order_pkg.files[1].file_id
        assert hydrated_by_id[d1.description_id].associated_file_ids == [first_file_id]
        assert hydrated_by_id[d2.description_id].associated_file_ids == [second_file_id]

        # --- 2. FILENAME_MATCH mode -----------------------------------------
        filename_adapter = BatchSourceAdapter(
            storage_root=tmp_path / "filename", tenant_id=tenant_filename
        )
        filename_zip = _make_zip({"invoice-x.pdf": b"X", "receipt-y.pdf": b"Y"})
        inv = IntakeDescription(text="invoice batch")
        rec = IntakeDescription(text="receipt batch")
        filename_pkgs = filename_adapter.enqueue(
            raw_bytes=filename_zip,
            filename="mixed.zip",
            descriptions=[inv, rec],
            association_mode=AssociationMode.FILENAME_MATCH,
            filename_rules=[
                (r"^invoice-", inv.description_id),
                (r"^receipt-", rec.description_id),
            ],
        )
        filename_pkg = filename_pkgs[0]
        await repo.insert_package(filename_pkg)

        async with pool.acquire() as conn:
            raw_mode = await conn.fetchval(
                "SELECT association_mode FROM intake_packages WHERE package_id = $1",
                filename_pkg.package_id,
            )
        assert raw_mode == "filename_match"

        hydrated = await repo.get_package(filename_pkg.package_id)
        assert hydrated is not None
        assert hydrated.association_mode == AssociationMode.FILENAME_MATCH

        # --- 3. No descriptions → association_mode stays NULL ---------------
        none_adapter = BatchSourceAdapter(storage_root=tmp_path / "none", tenant_id=tenant_none)
        none_pkgs = none_adapter.enqueue(
            raw_bytes=_make_zip({"only.pdf": b"only"}),
            filename="plain.zip",
        )
        assert len(none_pkgs) == 1
        assert none_pkgs[0].association_mode is None
        await repo.insert_package(none_pkgs[0])

        async with pool.acquire() as conn:
            raw_mode = await conn.fetchval(
                "SELECT association_mode FROM intake_packages WHERE package_id = $1",
                none_pkgs[0].package_id,
            )
        assert raw_mode is None

        hydrated = await repo.get_package(none_pkgs[0].package_id)
        assert hydrated is not None
        assert hydrated.association_mode is None

        # --- 4. PostgreSQL ENUM rejects unknown mode ------------------------
        async with pool.acquire() as conn:
            with pytest.raises(asyncpg.exceptions.InvalidTextRepresentationError):
                async with conn.transaction():
                    await conn.execute(
                        """
                        INSERT INTO intake_packages (package_id, source_type, tenant_id, association_mode)
                        VALUES ($1, 'batch_import', $2, 'NOT_A_REAL_MODE')
                        """,
                        uuid4(),
                        f"tenant-assoc-reject-{uuid4().hex[:6]}",
                    )
    finally:
        await _cleanup_tenant(pool, tenant_order)
        await _cleanup_tenant(pool, tenant_filename)
        await _cleanup_tenant(pool, tenant_none)
