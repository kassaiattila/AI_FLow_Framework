"""
@test_registry:
    suite: integration-api
    component: api.v1.conversations
    covers:
        - src/aiflow/api/v1/conversations.py
        - src/aiflow/services/conversations/repository.py
    phase: v1.8.0
    priority: high
    estimated_duration_ms: 5000
    requires_services: [postgres]
    tags: [integration, api, conversations, sprint_x, sx_4]

Sprint X / SX-4 — full round-trip test against real PostgreSQL through
the FastAPI router. Uses ``httpx.AsyncClient`` + ``ASGITransport`` so the
asyncpg pool stays on a single asyncio event loop (same pattern as
``tests/integration/api/test_routing_runs_router_real.py``).
"""

from __future__ import annotations

import os
import uuid
from unittest.mock import patch

import asyncpg
import httpx
import pytest

from aiflow.api import deps
from aiflow.security.auth import AuthProvider

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
            WHERE table_name = 'aszf_conversations'
            """
        )
        await conn.close()
    except Exception:
        return False
    return True


# ---------------------------------------------------------------------------
# Round-trip: POST create → POST turn → GET detail
# ---------------------------------------------------------------------------


async def test_full_round_trip_create_append_get_real_pg():
    if not await _pg_ready():
        pytest.skip("PostgreSQL with aszf_conversations table unavailable (run Alembic 051).")

    tenant = f"sx4-rt-{uuid.uuid4()}"

    auth = AuthProvider.from_env()
    with patch.object(AuthProvider, "from_env", return_value=auth):
        from aiflow.api.app import create_app

        app = create_app()
        token = auth.create_token(user_id=tenant, role="admin")
        headers = {"Authorization": f"Bearer {token}"}

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            create = await client.post(
                f"/api/v1/conversations/?tenant_id={tenant}",
                headers=headers,
                json={
                    "persona": "expert",
                    "collection_name": "azhu-test",
                    "title": "Panaszkezelési kérdések",
                },
            )
            assert create.status_code == 201, create.text
            conversation_id = create.json()["id"]

            user_turn = await client.post(
                f"/api/v1/conversations/{conversation_id}/turns?tenant_id={tenant}",
                headers=headers,
                json={"role": "user", "content": "Mi a panaszkezelési hatarido?"},
            )
            assert user_turn.status_code == 201, user_turn.text
            assert user_turn.json()["turn_index"] == 0

            assistant_turn = await client.post(
                f"/api/v1/conversations/{conversation_id}/turns?tenant_id={tenant}",
                headers=headers,
                json={
                    "role": "assistant",
                    "content": "A panaszkezelési hatarido 30 nap.",
                    "citations": [
                        {
                            "source_id": "doc-1",
                            "title": "ASZF",
                            "snippet": "A panaszt 30 napon belul...",
                            "score": 0.91,
                        }
                    ],
                    "cost_usd": 0.0042,
                    "latency_ms": 312,
                },
            )
            assert assistant_turn.status_code == 201, assistant_turn.text
            assert assistant_turn.json()["turn_index"] == 1

            # Detail GET — both turns + citations preserved
            detail = await client.get(
                f"/api/v1/conversations/{conversation_id}?tenant_id={tenant}",
                headers=headers,
            )
            assert detail.status_code == 200, detail.text
            payload = detail.json()
            assert payload["title"] == "Panaszkezelési kérdések"
            assert payload["persona"] == "expert"
            assert len(payload["turns"]) == 2
            assert payload["turns"][0]["role"] == "user"
            assert payload["turns"][1]["role"] == "assistant"
            assert payload["turns"][1]["citations"][0]["source_id"] == "doc-1"
            assert payload["turns"][1]["cost_usd"] == 0.0042

            # List — the conversation is visible under its tenant
            listed = await client.get(
                f"/api/v1/conversations/?tenant_id={tenant}",
                headers=headers,
            )
            assert listed.status_code == 200
            ids = [c["id"] for c in listed.json()]
            assert conversation_id in ids

            # Cross-tenant guard: 404 on detail, empty list under another tenant
            other_tenant = f"{tenant}-other"
            cross = await client.get(
                f"/api/v1/conversations/{conversation_id}?tenant_id={other_tenant}",
                headers=headers,
            )
            assert cross.status_code == 404

            cross_list = await client.get(
                f"/api/v1/conversations/?tenant_id={other_tenant}",
                headers=headers,
            )
            assert cross_list.status_code == 200
            assert cross_list.json() == []
