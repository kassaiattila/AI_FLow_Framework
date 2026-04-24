"""
@test_registry:
    suite: integration-api
    component: api.v1.emails (FU-2 intent_class surface)
    covers:
        - src/aiflow/api/v1/emails.py
    phase: sprint-o-fu-2
    priority: critical
    estimated_duration_ms: 4000
    requires_services: [postgres]
    tags: [integration, api, emails, intent_class, sprint-o, fu-2]

Sprint O FU-2 — GET /api/v1/emails/{id} carries the abstract
``intent_class`` derived from the v1 intent schema. Seeds two
``workflow_runs`` rows (invoice → EXTRACT, support → SUPPORT), hits
the FastAPI app in-process via httpx.AsyncClient, asserts the field
is populated correctly.
"""

from __future__ import annotations

import json
import os
import uuid
from collections.abc import AsyncGenerator

import asyncpg
import httpx
import pytest
from httpx import ASGITransport

from aiflow.api.app import create_app
from aiflow.api.v1 import emails as emails_module
from aiflow.security.auth import AuthProvider

pytestmark = pytest.mark.asyncio

DATABASE_URL = os.getenv(
    "AIFLOW_DATABASE__URL",
    "postgresql://aiflow:aiflow_dev_password@localhost:5433/aiflow_dev",
)
# asyncpg speaks the libpq URL without the +asyncpg suffix.
PG_DSN = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")


def _auth_headers() -> dict[str, str]:
    """Mint a signed admin token for the in-process FastAPI app."""
    auth = AuthProvider.from_env()
    token = auth.create_token(user_id="fu-2-test", role="admin", team_id="default")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
async def seeded_runs() -> AsyncGenerator[dict[str, uuid.UUID], None]:
    """Insert two workflow_runs rows covering two intent_classes."""
    invoice_id = uuid.uuid4()
    support_id = uuid.uuid4()

    async def _seed(run_id: uuid.UUID, intent_id: str) -> None:
        output_data = {
            "tenant_id": f"fu-2-{uuid.uuid4().hex[:8]}",
            "email_id": str(run_id),
            "subject": f"FU-2 fixture — {intent_id}",
            "sender": "test@example.com",
            "label": intent_id,
            "method": "keywords",
            "intent": {
                "intent_id": intent_id,
                "intent_display_name": intent_id.title(),
                "confidence": 0.75,
                "method": "keywords",
            },
        }
        conn = await asyncpg.connect(PG_DSN)
        try:
            await conn.execute(
                """
                INSERT INTO workflow_runs (
                    id, workflow_name, workflow_version, skill_name, status,
                    input_data, output_data, started_at, completed_at,
                    total_duration_ms
                )
                VALUES (
                    $1, 'email_connector_scan_classify', '1.0',
                    'email_intent_processor', 'completed',
                    $2::jsonb, $3::jsonb, NOW(), NOW(), 42
                )
                """,
                run_id,
                json.dumps({}),
                json.dumps(output_data),
            )
        finally:
            await conn.close()

    await _seed(invoice_id, "invoice_received")
    await _seed(support_id, "support")

    # Reset the resolver cache in case a previous test mutated it.
    emails_module._INTENT_CLASS_MAP = None

    try:
        yield {"invoice": invoice_id, "support": support_id}
    finally:
        conn = await asyncpg.connect(PG_DSN)
        try:
            await conn.execute(
                "DELETE FROM step_runs WHERE workflow_run_id = ANY($1::uuid[])",
                [invoice_id, support_id],
            )
            await conn.execute(
                "DELETE FROM workflow_runs WHERE id = ANY($1::uuid[])",
                [invoice_id, support_id],
            )
        finally:
            await conn.close()


async def test_email_detail_carries_intent_class(
    seeded_runs: dict[str, uuid.UUID],
) -> None:
    app = create_app()
    transport = ASGITransport(app=app)
    headers = _auth_headers()
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        inv_resp = await client.get(f"/api/v1/emails/{seeded_runs['invoice']}", headers=headers)
        sup_resp = await client.get(f"/api/v1/emails/{seeded_runs['support']}", headers=headers)

    assert inv_resp.status_code == 200, inv_resp.text
    assert sup_resp.status_code == 200, sup_resp.text

    inv_data = inv_resp.json()
    sup_data = sup_resp.json()

    assert inv_data["intent_class"] == "EXTRACT"
    assert sup_data["intent_class"] == "SUPPORT"

    # Openapi-surface check: field is present even when unset (None), not stripped.
    assert "intent_class" in inv_data
    assert "intent_class" in sup_data
