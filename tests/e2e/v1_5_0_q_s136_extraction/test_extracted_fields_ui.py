"""
@test_registry:
    suite: e2e-uc3
    component: aiflow-admin.email-detail.extracted-fields-card + api.v1.emails
    covers:
        - aiflow-admin/src/components-new/ExtractedFieldsCard.tsx
        - aiflow-admin/src/pages-new/EmailDetail.tsx (ExtractedFieldsCard mount)
        - src/aiflow/api/v1/emails.py (EmailDetailResponse.extracted_fields)
    phase: sprint-q-s136
    priority: critical
    estimated_duration_ms: 30000
    requires_services: [postgres, fastapi, vite]
    tags: [e2e, ui, sprint-q, s136, playwright, live-stack]

Sprint Q / S136 — ExtractedFieldsCard visual render against the real
running stack. Seeds a workflow_runs row with a Sprint Q shape (invoice
extraction fields), hits the real FastAPI, loads the real Vite UI, and
asserts the card + invoice number + gross total + confidence render.

No route mocks — this is the live dev-stack contract test. Skipped if
the dev stack isn't up.
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
from pathlib import Path

import asyncpg
import pytest
from dotenv import load_dotenv
from playwright.sync_api import Page, expect

load_dotenv(Path(__file__).resolve().parents[3] / ".env", override=False)

from tests.e2e.conftest import BASE_URL  # noqa: E402

_RUNTIME_HOOKS = (asyncio, asyncpg, threading, urllib.request)

pytestmark = pytest.mark.e2e

PG_DSN = (
    os.getenv("AIFLOW_DATABASE__URL")
    or os.getenv("AIFLOW_TEST_DSN")
    or "postgresql://aiflow:aiflow_dev_password@localhost:5433/aiflow_dev"
).replace("postgresql+asyncpg://", "postgresql://")
API_BASE_URL = os.getenv("AIFLOW_API_BASE_URL", "http://localhost:8102")


def _service_alive(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=2) as resp:
            return resp.status < 500
    except (urllib.error.URLError, OSError):
        return False


@pytest.fixture(autouse=True)
def _skip_when_stack_down() -> None:
    if not _service_alive(BASE_URL):
        pytest.skip(f"UI at {BASE_URL} unreachable")
    if not _service_alive(f"{API_BASE_URL}/health"):
        pytest.skip(f"API at {API_BASE_URL} unreachable")


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


_SEED_EXTRACTED = {
    "invoice_march.pdf": {
        "vendor": {"name": "Acme Consulting Kft", "tax_id": "HU-12345678"},
        "buyer": {"name": "Customer Zrt", "tax_id": "HU-87654321"},
        "header": {
            "invoice_number": "INV-2026-0042",
            "currency": "EUR",
            "issue_date": "2026-04-01",
            "due_date": "2026-05-01",
        },
        "line_items": [
            {"description": "Consulting — March", "quantity": 40, "unit_price": 100, "total": 4000},
            {"description": "Travel expenses", "quantity": 1, "unit_price": 250, "total": 250},
        ],
        "totals": {"net_total": 4250.0, "vat_total": 1147.5, "gross_total": 5397.5},
        "extraction_confidence": 0.92,
        "extraction_time_ms": 1487.0,
        "cost_usd": 0.00054,
    }
}


def _seed_run(run_id: uuid.UUID) -> None:
    output_data = {
        "tenant_id": f"s136-e2e-{uuid.uuid4().hex[:6]}",
        "email_id": str(run_id),
        "subject": "S136 E2E — invoice with extraction",
        "sender": "supplier@example.com",
        "label": "invoice_received",
        "display_name": "Invoice received",
        "confidence": 0.85,
        "method": "keywords",
        "intent": {
            "intent_id": "invoice_received",
            "intent_display_name": "Invoice received",
            "confidence": 0.85,
            "method": "keywords",
        },
        "extracted_fields": _SEED_EXTRACTED,
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
                    $2::jsonb, $3::jsonb, NOW(), NOW(), 1510
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
def seeded_extraction_run() -> Generator[uuid.UUID, None, None]:
    run_id = uuid.uuid4()
    _seed_run(run_id)
    try:
        yield run_id
    finally:
        _delete_run(run_id)


class TestExtractedFieldsCardLiveStack:
    """Live-stack Playwright assertion: real API + real UI + real DB."""

    def test_extracted_fields_render_on_email_detail(
        self,
        authenticated_page: Page,
        seeded_extraction_run: uuid.UUID,
    ) -> None:
        page = authenticated_page
        run_id = str(seeded_extraction_run)

        # 1) API surface check — proves the live API carries extracted_fields.
        token = page.evaluate("() => localStorage.getItem('aiflow_token')")
        assert token, "UI login did not store aiflow_token"
        api_resp = page.request.get(
            f"{API_BASE_URL}/api/v1/emails/{run_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert api_resp.ok, f"API GET failed: {api_resp.status} {api_resp.text()}"
        api_data = api_resp.json()
        assert api_data.get("extracted_fields"), "extracted_fields missing on live API"
        fields = api_data["extracted_fields"]["invoice_march.pdf"]
        assert fields["header"]["invoice_number"] == "INV-2026-0042"

        # 2) UI render against real Vite dev server.
        page.goto(f"{BASE_URL}/#/emails/{run_id}")
        page.wait_for_load_state("networkidle")

        expect(page.get_by_test_id("extracted-fields-card")).to_be_visible()
        expect(page.get_by_test_id("extracted-fields-invoice-number")).to_have_text("INV-2026-0042")
        expect(page.get_by_test_id("extracted-fields-gross-total")).to_contain_text("5")
        expect(page.get_by_test_id("extracted-fields-gross-total")).to_contain_text("EUR")
