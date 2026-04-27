"""
@test_registry:
    suite: integration-services
    component: services.routing_runs.repository
    covers:
        - src/aiflow/services/routing_runs/repository.py
        - alembic/versions/050_routing_runs.py
    phase: v1.8.0
    priority: high
    estimated_duration_ms: 5000
    requires_services: [postgres]
    tags: [integration, routing_runs, sprint_x, sx_3]

Sprint X / SX-3 — round-trip repository tests against real PostgreSQL
(Docker 5433). Skips cleanly when the DB is unavailable so the unit
suite still runs in environments without Docker.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta

import asyncpg
import pytest

from aiflow.api import deps
from aiflow.api.deps import get_pool
from aiflow.services.routing_runs.repository import RoutingRunRepository
from aiflow.services.routing_runs.schemas import (
    RoutingRunCreate,
    RoutingRunFilters,
)

pytestmark = pytest.mark.asyncio

DATABASE_URL = os.getenv(
    "AIFLOW_DATABASE__URL",
    "postgresql+asyncpg://aiflow:aiflow_dev_password@localhost:5433/aiflow_dev",
)


@pytest.fixture(autouse=True)
async def _reset_deps_pool():
    """Reset cached pool after each test (asyncpg + event-loop trap)."""
    yield
    await deps.close_all()


async def _ensure_pg_available() -> bool:
    """Ping PG; return False (skip) when unreachable so CI without
    Docker keeps the unit suite green."""
    raw = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    try:
        conn = await asyncpg.connect(raw, timeout=2)
        await conn.execute(
            """
            SELECT 1 FROM information_schema.tables
            WHERE table_name = 'routing_runs'
            """
        )
        await conn.close()
    except Exception:
        return False
    return True


@pytest.fixture
async def repo() -> RoutingRunRepository:
    if not await _ensure_pg_available():
        pytest.skip("PostgreSQL with routing_runs table unavailable (run Alembic 050).")
    pool = await get_pool()
    return RoutingRunRepository(pool)


# ---------------------------------------------------------------------------
# 1. test_insert_then_list_real_pg
# ---------------------------------------------------------------------------


async def test_insert_then_list_real_pg(repo: RoutingRunRepository):
    tenant = f"sx3-real-{uuid.uuid4()}"
    row = RoutingRunCreate(
        tenant_id=tenant,
        email_id=uuid.uuid4(),
        intent_class="EXTRACT",
        doctype_detected="hu_invoice",
        doctype_confidence=0.93,
        extraction_path="invoice_processor",
        extraction_outcome="success",
        cost_usd=0.0042,
        latency_ms=235,
        metadata={"attachments": [{"filename": "a.pdf", "extraction_outcome": "succeeded"}]},
    )
    inserted_id = await repo.insert(row)
    assert isinstance(inserted_id, uuid.UUID)

    # List via tenant filter — exactly one row, our row.
    listed = await repo.list(
        filters=RoutingRunFilters(tenant_id=tenant),
        limit=10,
        offset=0,
    )
    assert len(listed) == 1
    assert listed[0].id == inserted_id
    assert listed[0].doctype_detected == "hu_invoice"
    assert listed[0].extraction_outcome == "success"

    # Detail fetch round-trip.
    detail = await repo.get(inserted_id, tenant_id=tenant)
    assert detail is not None
    assert detail.metadata is not None
    assert detail.metadata["attachments"][0]["filename"] == "a.pdf"

    # Cross-tenant isolation: detail returns None for a different tenant.
    other = await repo.get(inserted_id, tenant_id=f"{tenant}-other")
    assert other is None


# ---------------------------------------------------------------------------
# 2. test_aggregate_stats_real_pg
# ---------------------------------------------------------------------------


async def test_aggregate_stats_real_pg(repo: RoutingRunRepository):
    tenant = f"sx3-stats-{uuid.uuid4()}"
    base_row = dict(
        tenant_id=tenant,
        email_id=uuid.uuid4(),
        intent_class="EXTRACT",
        doctype_confidence=0.9,
        latency_ms=200,
    )
    # Three runs: 2 hu_invoice / success, 1 hu_id_card / failed.
    await repo.insert(
        RoutingRunCreate(
            **base_row,
            doctype_detected="hu_invoice",
            extraction_path="invoice_processor",
            extraction_outcome="success",
            cost_usd=0.001,
        )
    )
    await repo.insert(
        RoutingRunCreate(
            **base_row,
            doctype_detected="hu_invoice",
            extraction_path="invoice_processor",
            extraction_outcome="success",
            cost_usd=0.003,
        )
    )
    await repo.insert(
        RoutingRunCreate(
            **base_row,
            doctype_detected="hu_id_card",
            extraction_path="doc_recognizer_workflow",
            extraction_outcome="failed",
            cost_usd=0.005,
        )
    )

    until = datetime.now(UTC) + timedelta(minutes=1)
    since = until - timedelta(hours=1)
    stats = await repo.aggregate_stats(tenant_id=tenant, since=since, until=until)

    assert stats.total_runs == 3
    doctype_map = {b.key: b.count for b in stats.by_doctype}
    assert doctype_map["hu_invoice"] == 2
    assert doctype_map["hu_id_card"] == 1
    outcome_map = {b.key: b.count for b in stats.by_outcome}
    assert outcome_map["success"] == 2
    assert outcome_map["failed"] == 1
    path_map = {b.key: b.count for b in stats.by_extraction_path}
    assert path_map["invoice_processor"] == 2
    assert path_map["doc_recognizer_workflow"] == 1
    assert stats.mean_cost_usd == pytest.approx(0.003, rel=0.05)
    assert stats.p50_latency_ms == pytest.approx(200.0, abs=0.001)
