"""
@test_registry:
    suite: e2e-uc3
    component: aiflow-admin.email-detail.attachment-cost + api.v1.emails
    covers:
        - aiflow-admin/src/components-new/AttachmentSignalsCard.tsx (cost row)
        - src/aiflow/services/email_connector/orchestrator.py (cost emission)
        - src/aiflow/tools/attachment_cost.py
    phase: sprint-o-fu-7
    priority: critical
    estimated_duration_ms: 30000
    requires_services: [postgres, fastapi, vite]
    tags: [e2e, ui, sprint-o, fu-7, attachment-cost, playwright, live-stack]

Sprint O FU-7 — AttachmentSignalsCard surfaces the per-run aggregate cost
+ pages processed when > 0. Runs against the real live stack (no route
mock): seeds a workflow_run with a Sprint O-shaped output_data carrying
``attachment_features.total_cost_usd = 0.03``, loads the real UI, asserts
the cost row renders with the expected text.

Skipped automatically when API or UI is unreachable.
"""

from __future__ import annotations

import asyncio
import json
import os
import threading
import urllib.error
import urllib.request
import uuid
from collections.abc import Generator

import asyncpg
import pytest
from playwright.sync_api import Page, expect

from tests.e2e.conftest import BASE_URL

_RUNTIME_HOOKS = (asyncio, asyncpg, threading, urllib.request)

pytestmark = pytest.mark.e2e

PG_DSN = os.getenv(
    "AIFLOW_TEST_DSN",
    "postgresql://aiflow:aiflow_dev_password@localhost:5433/aiflow_dev",
)
API_BASE_URL = os.getenv("AIFLOW_API_BASE_URL", "http://localhost:8102")


def _service_alive(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=2) as resp:
            return resp.status < 500
    except (urllib.error.URLError, OSError):
        return False


@pytest.fixture(autouse=True)
def _skip_when_dev_stack_down() -> None:
    if not _service_alive(BASE_URL):
        pytest.skip(f"UI dev server at {BASE_URL} unreachable.")
    if not _service_alive(f"{API_BASE_URL}/health"):
        pytest.skip(f"API at {API_BASE_URL} unreachable.")


def _run_in_thread(make_coro):
    box: dict[str, object] = {}

    def _runner() -> None:
        loop = asyncio.new_event_loop()
        try:
            box["result"] = loop.run_until_complete(make_coro())
        except BaseException as exc:  # pragma: no cover
            box["error"] = exc
        finally:
            loop.close()

    t = threading.Thread(target=_runner)
    t.start()
    t.join()
    if "error" in box:
        raise box["error"]  # type: ignore[misc]
    return box.get("result")


def _seed_run(run_id: uuid.UUID) -> None:
    output_data = {
        "tenant_id": f"fu-7-e2e-{uuid.uuid4().hex[:6]}",
        "email_id": str(run_id),
        "subject": "FU-7 E2E — invoice with cost",
        "sender": "supplier@example.com",
        "label": "invoice_received",
        "method": "keywords+attachment_rule",
        "intent": {
            "intent_id": "invoice_received",
            "intent_display_name": "Invoice received",
            "confidence": 0.81,
            "method": "keywords+attachment_rule",
        },
        "attachment_features": {
            "invoice_number_detected": True,
            "total_value_detected": True,
            "table_count": 1,
            "mime_profile": "application/pdf",
            "keyword_buckets": {"invoice": 2},
            "text_quality": 0.82,
            "attachments_considered": 1,
            "attachments_skipped": 0,
            # FU-7 additive fields: Azure DI 3 pages × $0.01 = $0.03.
            "total_cost_usd": 0.03,
            "total_pages_processed": 3,
        },
    }

    async def _seed():
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
                    $2::jsonb, $3::jsonb, NOW(), NOW(), 97
                )
                """,
                run_id,
                json.dumps({"subject": output_data["subject"]}),
                json.dumps(output_data),
            )
        finally:
            await conn.close()

    _run_in_thread(_seed)


def _delete_run(run_id: uuid.UUID) -> None:
    async def _delete():
        conn = await asyncpg.connect(PG_DSN)
        try:
            await conn.execute("DELETE FROM cost_records WHERE workflow_run_id = $1", run_id)
            await conn.execute("DELETE FROM step_runs WHERE workflow_run_id = $1", run_id)
            await conn.execute("DELETE FROM workflow_runs WHERE id = $1", run_id)
        finally:
            await conn.close()

    _run_in_thread(_delete)


@pytest.fixture()
def seeded_cost_run() -> Generator[uuid.UUID, None, None]:
    run_id = uuid.uuid4()
    _seed_run(run_id)
    try:
        yield run_id
    finally:
        _delete_run(run_id)


class TestAttachmentCostBadge:
    """FU-7 golden path against the real running services."""

    def test_cost_row_visible_when_non_zero(
        self,
        authenticated_page: Page,
        seeded_cost_run: uuid.UUID,
    ) -> None:
        page = authenticated_page
        run_id = str(seeded_cost_run)

        # Live API smoke — asserts backend passthrough.
        token = page.evaluate("() => localStorage.getItem('aiflow_token')")
        assert token, "UI login did not store aiflow_token"
        api_resp = page.request.get(
            f"{API_BASE_URL}/api/v1/emails/{run_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert api_resp.ok, f"API GET failed: {api_resp.status} {api_resp.text()}"
        api_data = api_resp.json()
        feats = api_data.get("attachment_features") or {}
        assert feats.get("total_cost_usd") == 0.03
        assert feats.get("total_pages_processed") == 3

        # Visual UI assertion on live Vite dev server.
        page.goto(f"{BASE_URL}/#/emails/{run_id}")
        page.wait_for_load_state("networkidle")

        cost_row = page.get_by_test_id("attachment-signals-cost")
        expect(cost_row).to_be_visible()
        expect(cost_row).to_contain_text("$0.0300")
        expect(cost_row).to_contain_text("3")  # pages count
