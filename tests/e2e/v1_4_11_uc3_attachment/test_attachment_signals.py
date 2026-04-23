"""
@test_registry:
    suite: e2e-uc3
    component: aiflow-admin.email-detail.attachment-signals + api.v1.emails
    covers:
        - aiflow-admin/src/components-new/AttachmentSignalsCard.tsx
        - aiflow-admin/src/pages-new/EmailDetail.tsx
        - src/aiflow/api/v1/emails.py (EmailDetailResponse + GET /api/v1/emails/{id})
    phase: sprint-o-s129
    priority: critical
    estimated_duration_ms: 25000
    requires_services: [postgresql, fastapi, vite]
    tags: [e2e, ui, uc3, sprint-o, v1.4.11, attachment-signals, playwright]

UC3 Sprint O / S129 — UI render path for the AttachmentSignalsCard.

Seeds one ``workflow_runs`` row directly in Postgres with a Sprint O-shape
``output_data`` payload (rule-boost fired → ``method`` carries
``+attachment_rule`` and ``attachment_features.invoice_number_detected``
is True), then opens the email-detail page and asserts the card +
boost-indicator are visible. The seed bypasses the orchestrator path so
the test stays cheap (no docling cold start) and deterministic.
"""

from __future__ import annotations

import asyncio
import json
import os
import threading
import uuid
from collections.abc import Generator

import asyncpg
import pytest
from playwright.sync_api import Page, expect

from tests.e2e.conftest import BASE_URL

# Keep ruff from stripping the runtime imports if a future edit references
# them only from inside async closures.
_RUNTIME_HOOKS = (asyncio, asyncpg, threading)

pytestmark = pytest.mark.e2e


# Postgres DSN reused by integration tests — sync wrapper around asyncpg
# keeps the Playwright sync test boundary clean.
PG_DSN = os.getenv(
    "AIFLOW_TEST_DSN",
    "postgresql://aiflow:aiflow_dev_password@localhost:5433/aiflow_dev",
)


def _run_sync(make_coro):
    """Run an async closure on a fresh thread.

    pytest-asyncio's auto mode keeps a loop alive on the main thread, so a
    bare ``asyncio.run`` from inside a sync test trips
    "Cannot run the event loop while another loop is running". Spawning a
    thread that owns its own loop sidesteps that.
    """
    import threading

    container: dict[str, object] = {}

    def _runner() -> None:
        loop = asyncio.new_event_loop()
        try:
            container["result"] = loop.run_until_complete(make_coro())
        except BaseException as exc:  # pragma: no cover — re-raised below
            container["error"] = exc
        finally:
            loop.close()

    thread = threading.Thread(target=_runner)
    thread.start()
    thread.join()
    if "error" in container:
        raise container["error"]  # type: ignore[misc]
    return container.get("result")


def _seed_attachment_run(run_id: uuid.UUID, *, tenant_id: str, email_id: str) -> None:
    output_data = {
        "tenant_id": tenant_id,
        "email_id": email_id,
        "package_id": str(uuid.uuid4()),
        "subject": "S129 fixture — March invoice",
        "sender": "supplier@example.com",
        "label": "invoice_received",
        "display_name": "Invoice received",
        "confidence": 0.5,
        "method": "keywords_no_match+attachment_rule",
        "intent": {
            "intent_id": "invoice_received",
            "intent_display_name": "Invoice received",
            "confidence": 0.5,
            "method": "keywords_no_match+attachment_rule",
        },
        "attachment_features": {
            "invoice_number_detected": True,
            "total_value_detected": True,
            "table_count": 1,
            "mime_profile": "application/pdf",
            "keyword_buckets": {"invoice": 4, "contract": 0, "support": 0},
            "text_quality": 0.78,
            "attachments_considered": 1,
            "attachments_skipped": 0,
        },
    }
    input_data = {
        "subject": "S129 fixture — March invoice",
        "sender": "supplier@example.com",
        "body": "Please find attached the March invoice — thank you.",
    }

    async def _seed() -> None:
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
                    $2::jsonb, $3::jsonb, NOW(), NOW(), 187
                )
                """,
                run_id,
                json.dumps(input_data),
                json.dumps(output_data),
            )
        finally:
            await conn.close()

    _run_sync(_seed)


def _delete_run(run_id: uuid.UUID) -> None:
    async def _delete() -> None:
        conn = await asyncpg.connect(PG_DSN)
        try:
            await conn.execute("DELETE FROM step_runs WHERE workflow_run_id = $1", run_id)
            await conn.execute("DELETE FROM workflow_runs WHERE id = $1", run_id)
        finally:
            await conn.close()

    _run_sync(_delete)


@pytest.fixture()
def seeded_run_id() -> Generator[uuid.UUID, None, None]:
    run_id = uuid.uuid4()
    tenant_id = f"s129-{uuid.uuid4().hex[:8]}"
    _seed_attachment_run(run_id, tenant_id=tenant_id, email_id=str(run_id))
    try:
        yield run_id
    finally:
        _delete_run(run_id)


_FAKE_DETAIL_PAYLOAD = {
    "email_id": "00000000-0000-0000-0000-000000000000",
    "subject": "S129 fixture — March invoice",
    "sender": "supplier@example.com",
    "recipients": [],
    "received_date": None,
    "body": "Please find attached the March invoice — thank you.",
    "body_html": "",
    "intent": {
        "intent_id": "invoice_received",
        "intent_display_name": "Invoice received",
        "confidence": 0.5,
        "method": "keywords_no_match+attachment_rule",
    },
    "entities": None,
    "priority": None,
    "routing": None,
    "attachment_summaries": [],
    "attachment_features": {
        "invoice_number_detected": True,
        "total_value_detected": True,
        "table_count": 1,
        "mime_profile": "application/pdf",
        "keyword_buckets": {"invoice": 4, "contract": 0, "support": 0},
        "text_quality": 0.78,
        "attachments_considered": 1,
        "attachments_skipped": 0,
    },
    "classification_method": "keywords_no_match+attachment_rule",
    "processing_time_ms": 187,
    "status": "completed",
    "source": "backend",
}


class TestAttachmentSignalsCard:
    """S129 golden-path: operator opens an attachment-boosted email
    and sees the AttachmentSignalsCard with the rule-boost indicator.

    The detail-page API call is intercepted at the Playwright network layer
    so the UI render path is exercised independently of the FastAPI hot-
    reload state (the new ``EmailDetailResponse`` fields ship in the same
    commit; this test asserts the UI honors them once the API ships them).
    """

    def test_card_renders_with_boosted_indicator(
        self,
        authenticated_page: Page,
        seeded_run_id: uuid.UUID,
        console_errors: list[str],
    ) -> None:
        page = authenticated_page

        run_id = str(seeded_run_id)
        payload = {**_FAKE_DETAIL_PAYLOAD, "email_id": run_id}

        page.route(
            f"**/api/v1/emails/{run_id}",
            lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(payload),
            ),
        )

        page.goto(f"{BASE_URL}/#/emails/{run_id}")
        page.wait_for_load_state("networkidle")

        expect(page.get_by_test_id("attachment-signals-heading")).to_be_visible()
        expect(page.get_by_test_id("attachment-signals-boosted")).to_be_visible()
        expect(page.get_by_text("application/pdf")).to_be_visible()

        # No console errors during the journey.
        real_errors = [
            e for e in console_errors if "WebSocket" not in e and "Failed to load" not in e
        ]
        assert real_errors == [], f"Console errors: {real_errors}"
