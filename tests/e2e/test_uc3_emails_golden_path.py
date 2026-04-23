"""
UC3 Email Intent — golden-path E2E (S110).

@test_registry:
    suite: e2e-uc3
    component: aiflow-admin.emails + policy.intent_rules + prompts
    covers:
        - aiflow-admin/src/pages-new/Emails.tsx
        - aiflow-admin/src/pages-new/EmailConnectors.tsx
        - aiflow-admin/src/pages-new/EmailDetail.tsx
        - aiflow-admin/src/pages-new/IntentRules.tsx
        - aiflow-admin/src/pages-new/PromptDetail.tsx
    phase: sprint-k-s110
    priority: critical
    estimated_duration_ms: 45000
    requires_services: [postgresql, redis, fastapi, vite]
    tags: [e2e, uc3, golden-path, sprint-k, v1.4.7]

Sprint K closing test: verifies the full UC3 admin surface works end-to-end
against the running stack:

    Login → /emails (Inbox) → /emails/connectors → /emails/intent-rules
      → /prompts → /prompts/:name (editor loads YAML)

No LLM processing triggered — cheap (~15s).
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.conftest import BASE_URL

pytestmark = pytest.mark.e2e


class TestUc3EmailsGoldenPath:
    """End-to-end smoke over the complete UC3 admin surface."""

    def test_inbox_loads_with_kpis_and_action_bar(
        self, authenticated_page: Page, console_errors: list[str]
    ) -> None:
        page = authenticated_page
        page.goto(f"{BASE_URL}/#/emails")
        page.wait_for_load_state("networkidle")

        # Page heading
        expect(page.locator("h1", has_text="Emailek")).to_be_visible()

        # Action bar buttons (S108c/d/b)
        expect(page.get_by_role("button", name="Levelada szkenneles")).to_be_visible()
        expect(page.get_by_role("button", name="Email feltoltes")).to_be_visible()
        expect(page.get_by_role("button", name="Connectorok")).to_be_visible()

        # KPI grid (4 cards)
        expect(page.get_by_text("Emailek").first).to_be_visible()
        expect(page.get_by_text("Szandek felismeres")).to_be_visible()
        expect(page.get_by_text("Unprocessed")).to_be_visible()
        expect(page.get_by_text("Csatolmanyok")).to_be_visible()

        # No console errors during navigation
        assert console_errors == [], f"Console errors: {console_errors}"

    def test_connectors_page_standalone_route(
        self, authenticated_page: Page, console_errors: list[str]
    ) -> None:
        page = authenticated_page
        page.goto(f"{BASE_URL}/#/emails/connectors")
        page.wait_for_load_state("networkidle")

        # Heading + Vissza button (S108b)
        expect(page.locator("h1", has_text="Connectorok")).to_be_visible()
        expect(page.get_by_role("button", name="Vissza")).to_be_visible()
        expect(page.get_by_role("button", name="Uj connector")).to_be_visible()

        assert console_errors == [], f"Console errors: {console_errors}"

    def test_intent_rules_page_list_renders(
        self, authenticated_page: Page, console_errors: list[str]
    ) -> None:
        page = authenticated_page
        page.goto(f"{BASE_URL}/#/emails/intent-rules")
        page.wait_for_load_state("networkidle")

        # Heading (S109a)
        expect(page.locator("h1", has_text="Intent szabalyok")).to_be_visible()
        # New-rule card is always visible, even on empty list
        expect(page.get_by_placeholder("tenant_id", exact=False)).to_be_visible()
        expect(page.get_by_role("button", name="Letrehozas")).to_be_visible()

        assert console_errors == [], f"Console errors: {console_errors}"

    def test_prompts_list_and_drill_down_to_editor(
        self, authenticated_page: Page, console_errors: list[str]
    ) -> None:
        page = authenticated_page
        page.goto(f"{BASE_URL}/#/prompts")
        page.wait_for_load_state("networkidle")

        # List heading + count pill
        heading = page.locator("h3", has_text="Prompts")
        expect(heading).to_be_visible()

        # Table is populated (walks prompts/ + skills/*/prompts/*.yaml)
        rows = page.locator('table[data-testid="prompt-list"] tbody tr')
        expect(rows.first).to_be_visible(timeout=5000)
        row_count = rows.count()
        assert row_count > 0, "No prompt rows rendered"

        # Click first row → navigates to editor (S109b)
        rows.first.click()
        page.wait_for_url("**/prompts/**", timeout=5000)

        # Editor page shows heading + YAML textarea
        expect(page.locator("h1, h2").filter(has_text="Prompt")).to_be_visible()
        expect(page.locator("textarea")).to_be_visible()

        assert console_errors == [], f"Console errors: {console_errors}"
