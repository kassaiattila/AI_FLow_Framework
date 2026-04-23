"""Integration test — /api/v1/tenants/{id}/budget CRUD round-trip.

@test_registry
suite: integration-api
component: api.v1.tenant_budgets
covers:
    - src/aiflow/api/v1/tenant_budgets.py
    - src/aiflow/services/tenant_budgets/service.py
    - alembic/versions/045_tenant_budgets.py
phase: v1.4.10
priority: critical
requires_services: [postgres]
tags: [integration, api, tenant_budgets, sprint_n, s121, postgres]

Exercises the full PUT → GET → DELETE round-trip against real Docker
PostgreSQL (port 5433) and verifies the live BudgetView surfaces the
``used_usd`` value from a seeded ``cost_records`` row.

NOTE (feedback_asyncpg_pool_event_loop.md): asyncpg pools are event-loop
bound — DB assertions use a fresh connection, never the app's pool.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from datetime import UTC, datetime
from unittest.mock import patch

import asyncpg
import pytest
from fastapi.testclient import TestClient

from aiflow.security.auth import AuthProvider


def _db_url() -> str:
    url = os.environ.get(
        "AIFLOW_DATABASE__URL",
        "postgresql+asyncpg://aiflow:aiflow_dev_password@localhost:5433/aiflow_dev",
    )
    return url.replace("postgresql+asyncpg://", "postgresql://")


_shared_auth = AuthProvider.from_env()

from aiflow.api.app import create_app  # noqa: E402

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module", autouse=True)
def _patch_auth_from_env():
    with patch.object(AuthProvider, "from_env", return_value=_shared_auth):
        yield


@pytest.fixture(scope="module")
def client():
    from aiflow.api import deps as _deps

    _deps._pool = None
    app = create_app()
    with TestClient(app, raise_server_exceptions=False) as c:
        c.get("/health/live")
        yield c
    _deps._pool = None


def _headers() -> dict[str, str]:
    token = _shared_auth.create_token(user_id="test-admin", role="admin", team_id="default")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def tenant_id() -> str:
    return f"s121-api-{uuid.uuid4().hex[:8]}"


async def _seed_cost_record(tenant: str, cost_usd: float) -> None:
    conn = await asyncpg.connect(_db_url())
    try:
        await conn.execute(
            """
            INSERT INTO cost_records
                (id, workflow_run_id, step_name, model, provider,
                 input_tokens, output_tokens, cost_usd, tenant_id, recorded_at)
            VALUES ($1, NULL, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
            uuid.uuid4(),
            "s121-test-step",
            "gpt-4o-mini",
            "openai",
            100,
            50,
            cost_usd,
            tenant,
            datetime.now(UTC),
        )
    finally:
        await conn.close()


async def _cleanup_cost_records(tenant: str) -> None:
    conn = await asyncpg.connect(_db_url())
    try:
        await conn.execute("DELETE FROM cost_records WHERE tenant_id = $1", tenant)
        await conn.execute("DELETE FROM tenant_budgets WHERE tenant_id = $1", tenant)
    finally:
        await conn.close()


def test_tenant_budget_put_get_delete_roundtrip(client: TestClient, tenant_id: str) -> None:
    try:
        # Seed a $7.50 cost_record so the GET surfaces used_usd > 0.
        asyncio.run(_seed_cost_record(tenant_id, 7.5))

        # --- PUT creates the budget row ---
        put = client.put(
            f"/api/v1/tenants/{tenant_id}/budget/daily",
            json={
                "limit_usd": 25.0,
                "alert_threshold_pct": [25, 50, 90],
                "enabled": True,
            },
            headers=_headers(),
        )
        assert put.status_code == 200, put.text
        body = put.json()
        assert body["budget"]["tenant_id"] == tenant_id
        assert body["budget"]["period"] == "daily"
        assert body["budget"]["limit_usd"] == 25.0
        assert body["budget"]["alert_threshold_pct"] == [25, 50, 90]
        assert body["view"]["used_usd"] == pytest.approx(7.5)
        assert body["view"]["remaining_usd"] == pytest.approx(17.5)
        assert body["view"]["usage_pct"] == pytest.approx(30.0)
        assert body["view"]["over_thresholds"] == [25]

        # --- GET single returns the same projection ---
        got = client.get(f"/api/v1/tenants/{tenant_id}/budget/daily", headers=_headers())
        assert got.status_code == 200
        got_body = got.json()
        assert got_body["budget"]["limit_usd"] == 25.0
        assert got_body["view"]["used_usd"] == pytest.approx(7.5)

        # --- GET list contains the row ---
        listed = client.get(f"/api/v1/tenants/{tenant_id}/budget", headers=_headers())
        assert listed.status_code == 200
        listed_body = listed.json()
        assert len(listed_body) == 1
        assert listed_body[0]["budget"]["period"] == "daily"

        # --- PUT again updates in place (upsert) ---
        upd = client.put(
            f"/api/v1/tenants/{tenant_id}/budget/daily",
            json={
                "limit_usd": 50.0,
                "alert_threshold_pct": [90],
                "enabled": False,
            },
            headers=_headers(),
        )
        assert upd.status_code == 200
        upd_body = upd.json()
        assert upd_body["budget"]["limit_usd"] == 50.0
        assert upd_body["budget"]["alert_threshold_pct"] == [90]
        assert upd_body["budget"]["enabled"] is False
        # used_usd unchanged (same cost fixture); usage_pct should drop to 15%.
        assert upd_body["view"]["usage_pct"] == pytest.approx(15.0)
        assert upd_body["view"]["over_thresholds"] == []

        # --- DELETE removes the row ---
        deleted = client.delete(f"/api/v1/tenants/{tenant_id}/budget/daily", headers=_headers())
        assert deleted.status_code == 200
        assert deleted.json() == {"deleted": True}

        # --- GET after DELETE → 404 ---
        missing = client.get(f"/api/v1/tenants/{tenant_id}/budget/daily", headers=_headers())
        assert missing.status_code == 404

        # --- DELETE again → 404 ---
        deleted_again = client.delete(
            f"/api/v1/tenants/{tenant_id}/budget/daily", headers=_headers()
        )
        assert deleted_again.status_code == 404

    finally:
        asyncio.run(_cleanup_cost_records(tenant_id))


def test_tenant_budget_put_rejects_out_of_range_threshold(
    client: TestClient, tenant_id: str
) -> None:
    try:
        r = client.put(
            f"/api/v1/tenants/{tenant_id}/budget/daily",
            json={"limit_usd": 10.0, "alert_threshold_pct": [50, 101]},
            headers=_headers(),
        )
        assert r.status_code == 422
    finally:
        asyncio.run(_cleanup_cost_records(tenant_id))


def test_tenant_budget_put_rejects_bad_period(client: TestClient, tenant_id: str) -> None:
    r = client.put(
        f"/api/v1/tenants/{tenant_id}/budget/weekly",
        json={"limit_usd": 10.0},
        headers=_headers(),
    )
    assert r.status_code == 422
