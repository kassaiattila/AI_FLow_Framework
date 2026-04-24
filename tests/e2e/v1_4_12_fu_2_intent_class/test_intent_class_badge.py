"""
@test_registry:
    suite: e2e-uc3
    component: aiflow-admin.email-detail.intent-class-badge + api.v1.emails
    covers:
        - aiflow-admin/src/pages-new/EmailDetail.tsx (IntentClassBadge)
        - src/aiflow/api/v1/emails.py (intent_class field)
        - skills/email_intent_processor/schemas/v1/intents.json
    phase: sprint-o-fu-2
    priority: critical
    estimated_duration_ms: 30000
    requires_services: [postgres, fastapi, vite]
    tags: [e2e, ui, sprint-o, fu-2, intent-class, playwright, live-stack]

Sprint O FU-2 — UI surfaces the abstract intent_class as a colored badge
in the Intent card header. This test runs against the **real live stack**
(no route mock):

1. Seed two ``workflow_runs`` rows directly in Postgres (one
   ``invoice_received`` → EXTRACT, one ``support`` → SUPPORT).
2. Hit the live API to confirm the new ``intent_class`` field is in the
   response payload.
3. Open ``/#/emails/<run-id>`` in Playwright, assert the badge renders
   with the correct text + the page is functional.

Skipped automatically if API or UI is unreachable.
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

# Pin runtime imports against the autoformatter strip.
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
    """pytest-asyncio's main-thread loop blocks asyncio.run; spawn a thread."""
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


def _seed_run(run_id: uuid.UUID, intent_id: str) -> None:
    output_data = {
        "tenant_id": f"fu-2-e2e-{uuid.uuid4().hex[:6]}",
        "email_id": str(run_id),
        "subject": f"FU-2 E2E — {intent_id}",
        "sender": "fu-2@example.com",
        "label": intent_id,
        "method": "keywords",
        "intent": {
            "intent_id": intent_id,
            "intent_display_name": intent_id.replace("_", " ").title(),
            "confidence": 0.81,
            "method": "keywords",
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
                    $2::jsonb, $3::jsonb, NOW(), NOW(), 73
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
            await conn.execute("DELETE FROM step_runs WHERE workflow_run_id = $1", run_id)
            await conn.execute("DELETE FROM workflow_runs WHERE id = $1", run_id)
        finally:
            await conn.close()

    _run_in_thread(_delete)


@pytest.fixture()
def extract_run() -> Generator[uuid.UUID, None, None]:
    run_id = uuid.uuid4()
    _seed_run(run_id, "invoice_received")
    try:
        yield run_id
    finally:
        _delete_run(run_id)


@pytest.fixture()
def support_run() -> Generator[uuid.UUID, None, None]:
    run_id = uuid.uuid4()
    _seed_run(run_id, "support")
    try:
        yield run_id
    finally:
        _delete_run(run_id)


class TestIntentClassBadgeOnLiveStack:
    """FU-2 golden path against the real running services."""

    def test_extract_run_renders_extract_badge(
        self,
        authenticated_page: Page,
        extract_run: uuid.UUID,
    ) -> None:
        page = authenticated_page
        run_id = str(extract_run)

        # 1) Live API surface check — proves uvicorn is on the new code.
        token = page.evaluate("() => localStorage.getItem('aiflow_token')")
        assert token, "UI login did not store aiflow_token"
        api_resp = page.request.get(
            f"{API_BASE_URL}/api/v1/emails/{run_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert api_resp.ok, f"API GET failed: {api_resp.status} {api_resp.text()}"
        api_data = api_resp.json()
        assert api_data.get("intent_class") == "EXTRACT", (
            f"API missing intent_class=EXTRACT for invoice_received run; got {api_data!r}"
        )

        # 2) Visual UI assertion against the real Vite dev server.
        page.goto(f"{BASE_URL}/#/emails/{run_id}")
        page.wait_for_load_state("networkidle")
        badge = page.get_by_test_id("intent-class-badge")
        expect(badge).to_be_visible()
        expect(badge).to_have_text("EXTRACT")

    def test_support_run_renders_support_badge(
        self,
        authenticated_page: Page,
        support_run: uuid.UUID,
    ) -> None:
        page = authenticated_page
        run_id = str(support_run)

        token = page.evaluate("() => localStorage.getItem('aiflow_token')")
        api_resp = page.request.get(
            f"{API_BASE_URL}/api/v1/emails/{run_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert api_resp.ok
        assert api_resp.json().get("intent_class") == "SUPPORT"

        page.goto(f"{BASE_URL}/#/emails/{run_id}")
        page.wait_for_load_state("networkidle")
        badge = page.get_by_test_id("intent-class-badge")
        expect(badge).to_be_visible()
        expect(badge).to_have_text("SUPPORT")
