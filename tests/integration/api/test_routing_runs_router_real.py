"""
@test_registry:
    suite: integration-api
    component: api.v1.routing_runs
    covers:
        - src/aiflow/api/v1/routing_runs.py
        - src/aiflow/services/routing_runs/repository.py
        - src/aiflow/services/email_connector/orchestrator.py (write hook)
    phase: v1.8.0
    priority: high
    estimated_duration_ms: 5000
    requires_services: [postgres]
    tags: [integration, api, routing_runs, sprint_x, sx_3]

Sprint X / SX-3 — verifies the orchestrator's audit-write hook persists
to ``routing_runs`` AND the router reads it back. The orchestrator-side
write is invoked directly through ``_write_routing_run_safe`` (the same
helper the orchestrator calls at the SX-2 dispatch boundary) so the
test exercises the end-to-end shape without spinning up the full
EmailSourceAdapter / classifier stack.
"""

from __future__ import annotations

import os
import uuid
from contextlib import contextmanager
from unittest.mock import patch

import asyncpg
import pytest
from fastapi.testclient import TestClient

from aiflow.api import deps
from aiflow.api.deps import get_pool
from aiflow.security.auth import AuthProvider
from aiflow.services.email_connector.orchestrator import _write_routing_run_safe
from aiflow.services.routing_runs.repository import RoutingRunRepository

pytestmark = pytest.mark.asyncio

DATABASE_URL = os.getenv(
    "AIFLOW_DATABASE__URL",
    "postgresql+asyncpg://aiflow:aiflow_dev_password@localhost:5433/aiflow_dev",
)


@pytest.fixture(autouse=True)
async def _reset_deps_pool():
    yield
    await deps.close_all()


async def _pg_ready() -> bool:
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


@contextmanager
def _client_and_headers(tenant_id: str):
    auth = AuthProvider.from_env()
    with patch.object(AuthProvider, "from_env", return_value=auth):
        from aiflow.api.app import create_app

        app = create_app()
        client = TestClient(app, raise_server_exceptions=False)
        client.get("/health/live")
        token = auth.create_token(user_id=tenant_id, role="admin")
        yield client, {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Round-trip: orchestrator hook writes → router GET reads
# ---------------------------------------------------------------------------


async def test_full_round_trip_orchestrator_writes_row_router_reads_it():
    if not await _pg_ready():
        pytest.skip("PostgreSQL with routing_runs table unavailable (run Alembic 050).")

    tenant = f"sx3-rt-{uuid.uuid4()}"
    pool = await get_pool()
    repo = RoutingRunRepository(pool)
    email_id = uuid.uuid4()

    # Drive the orchestrator-side write hook with a flag-on routing_decision
    # payload (mirrors the SX-2 contract shape).
    routing_decision = {
        "attachments": [
            {
                "attachment_id": "1",
                "filename": "a.pdf",
                "doctype_detected": "hu_invoice",
                "doctype_confidence": 0.92,
                "extraction_path": "invoice_processor",
                "extraction_outcome": "succeeded",
                "cost_usd": 0.004,
                "latency_ms": 220.0,
                "error": None,
            }
        ],
        "total_cost_usd": 0.004,
        "total_latency_ms": 220.0,
        "confidence_threshold": 0.6,
        "unknown_doctype_action": "fallback_invoice_processor",
    }
    await _write_routing_run_safe(
        repo,
        tenant_id=tenant,
        email_id=email_id,
        routing_decision=routing_decision,
        flag_off_extracted_fields=None,
        total_cost_usd=0.004,
    )

    # Now hit the router and verify the row is visible.
    with _client_and_headers(tenant) as (client, headers):
        r = client.get(
            f"/api/v1/routing-runs/?tenant_id={tenant}",
            headers=headers,
        )
        assert r.status_code == 200, r.text
        rows = r.json()
        assert len(rows) == 1
        row = rows[0]
        assert row["tenant_id"] == tenant
        assert row["doctype_detected"] == "hu_invoice"
        assert row["extraction_path"] == "invoice_processor"
        assert row["extraction_outcome"] == "success"
        assert row["intent_class"] == "EXTRACT"
        # Detail fetch returns full metadata
        detail = client.get(
            f"/api/v1/routing-runs/{row['id']}?tenant_id={tenant}",
            headers=headers,
        )
        assert detail.status_code == 200, detail.text
        body = detail.json()
        assert body["metadata"]["attachments"][0]["filename"] == "a.pdf"
