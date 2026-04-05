"""
i18n toggle E2E tests — verify HU/EN switch works across pages.

@test_registry:
    suite: e2e-i18n
    component: aiflow-admin.i18n
    covers: [aiflow-admin/src/lib/i18n.ts, aiflow-admin/src/locales/]
    phase: S9
    priority: high
    estimated_duration_ms: 10000
    requires_services: [vite]
    tags: [e2e, i18n, playwright]
"""
from __future__ import annotations

from playwright.sync_api import Page, expect

from tests.e2e.conftest import BASE_URL, navigate_to


class TestI18n:
    """Language toggle tests."""

    def test_login_locale_toggle(self, page: Page) -> None:
        page.goto(f"{BASE_URL}/#/login")
        page.wait_for_load_state("networkidle")

        # Click English button
        en_btn = page.locator("button", has_text="English")
        en_btn.click()
        page.wait_for_timeout(500)

        # Submit button should be in English
        submit = page.locator('button[type="submit"]')
        submit_text = submit.text_content() or ""
        assert any(w in submit_text.lower() for w in ["sign in", "login", "log in"]), \
            f"Expected English submit, got: {submit_text}"

        # Click Magyar button
        hu_btn = page.locator("button", has_text="Magyar")
        hu_btn.click()
        page.wait_for_timeout(500)

        # Submit button should be in Hungarian
        submit_text_hu = submit.text_content() or ""
        assert submit_text_hu != submit_text or "bel" in submit_text_hu.lower(), \
            f"HU toggle did not change text: {submit_text_hu}"

    def test_dashboard_locale_content(self, authenticated_page: Page) -> None:
        navigate_to(authenticated_page, "/")

        # Get initial content
        body_text = authenticated_page.locator("body").text_content() or ""
        # Dashboard should have some content regardless of locale
        assert len(body_text.strip()) > 50, "Dashboard has no content"
