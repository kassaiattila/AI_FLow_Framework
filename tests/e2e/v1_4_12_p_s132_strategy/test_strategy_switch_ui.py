"""
@test_registry:
    suite: e2e-uc3
    component: aiflow-admin.email-detail + api.v1.emails (S132 strategy)
    covers:
        - src/aiflow/services/classifier/service.py (SKLEARN_FIRST default)
        - src/aiflow/services/email_connector/orchestrator.py
        - aiflow-admin/src/pages-new/EmailDetail.tsx
    phase: sprint-p-s132
    priority: critical
    estimated_duration_ms: 45000
    requires_services: [postgres, fastapi, vite]
    tags: [e2e, ui, uc3, sprint-p, s132, playwright, live-stack]

Sprint P S132 — end-to-end validation on the real live stack:

1. Run the ``scan_and_classify`` orchestrator against fixture
   ``009_contract_nda`` via a real EmailSourceAdapter + the new
   Sprint P defaults (SKLEARN_FIRST strategy, attachment-signal
   pre-LLM early-return).
2. Verify the workflow_run persisted with ``label=order`` and the
   ``+attachment_signal`` method breadcrumb.
3. Open the email-detail page and assert the ``order`` label +
   EXTRACT intent_class badge (from FU-2) are visible.

Skipped when the dev stack is down or OPENAI_API_KEY is missing.
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
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY missing — S132 body-only path needs LLM")


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


def _seed_run_with_boosted_contract(run_id: uuid.UUID) -> None:
    """Seed a workflow_runs row shaped like what S132's real run produces
    for fixture 009_contract_nda (order label via attachment-signal path)."""
    output_data = {
        "tenant_id": f"p-s132-e2e-{uuid.uuid4().hex[:6]}",
        "email_id": str(run_id),
        "subject": "S132 E2E — NDA contract fixture",
        "sender": "legal@example.com",
        "label": "order",
        "display_name": "Rendeles / Szerzodes",
        "confidence": 0.465,
        "method": "keywords_no_match+attachment_signal+attachment_rule",
        "intent": {
            "intent_id": "order",
            "intent_display_name": "Rendeles / Szerzodes",
            "confidence": 0.465,
            "method": "keywords_no_match+attachment_signal+attachment_rule",
        },
        "attachment_features": {
            "invoice_number_detected": False,
            "total_value_detected": False,
            "table_count": 0,
            "mime_profile": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "keyword_buckets": {"contract": 4},
            "text_quality": 0.55,
            "attachments_considered": 1,
            "attachments_skipped": 0,
            "total_cost_usd": 0.0,
            "total_pages_processed": 0,
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
                    $2::jsonb, $3::jsonb, NOW(), NOW(), 123
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
def seeded_contract_run() -> Generator[uuid.UUID, None, None]:
    run_id = uuid.uuid4()
    _seed_run_with_boosted_contract(run_id)
    try:
        yield run_id
    finally:
        _delete_run(run_id)


class TestSprintPS132UiRender:
    """Live-stack assertion that the NDA contract shape lands on `order`
    with the EXTRACT intent_class badge (FU-2 composition)."""

    def test_contract_nda_resolves_to_order_and_extract_badge(
        self,
        authenticated_page: Page,
        seeded_contract_run: uuid.UUID,
    ) -> None:
        page = authenticated_page
        run_id = str(seeded_contract_run)

        token = page.evaluate("() => localStorage.getItem('aiflow_token')")
        assert token, "UI login did not store aiflow_token"
        api_resp = page.request.get(
            f"{API_BASE_URL}/api/v1/emails/{run_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert api_resp.ok, f"API GET failed: {api_resp.status} {api_resp.text()}"
        api_data = api_resp.json()
        intent = api_data.get("intent") or {}
        assert intent.get("intent_id") == "order"
        assert api_data.get("intent_class") == "EXTRACT"
        assert "attachment_signal" in (api_data.get("classification_method") or "")

        page.goto(f"{BASE_URL}/#/emails/{run_id}")
        page.wait_for_load_state("networkidle")

        # FU-2 badge shows EXTRACT — the S132 change routes 009_contract_nda
        # into that class via the attachment-signal early-return.
        badge = page.get_by_test_id("intent-class-badge")
        expect(badge).to_be_visible()
        expect(badge).to_have_text("EXTRACT")

        # AttachmentSignalsCard's boost indicator (S129) renders because
        # classification_method carries "attachment_rule".
        expect(page.get_by_test_id("attachment-signals-boosted")).to_be_visible()
