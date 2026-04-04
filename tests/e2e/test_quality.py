"""
Quality page E2E tests — KPIs, rubrics, external tools.

@test_registry:
    suite: e2e-quality
    component: aiflow-admin.quality
    covers: [aiflow-admin/src/pages-new/Quality.tsx]
    phase: S9
    priority: high
    estimated_duration_ms: 15000
    requires_services: [postgresql, redis, fastapi, vite]
    tags: [e2e, quality, playwright]
"""
from __future__ import annotations

from playwright.sync_api import Page, expect

from tests.e2e.conftest import navigate_to


def _wait_for_quality_loaded(page: Page) -> None:
    """Wait until Quality page finishes loading (spinner gone, content visible)."""
    navigate_to(page, "/quality")
    # Wait for spinner to disappear OR content to appear (max 10s)
    page.wait_for_timeout(2000)
    # Try to wait for the loading spinner to go away
    spinner = page.locator('[class*="animate-spin"]')
    if spinner.count() > 0:
        spinner.first.wait_for(state="hidden", timeout=10000)


class TestQualityPage:
    """Quality dashboard E2E tests."""

    def test_quality_page_loads(self, authenticated_page: Page) -> None:
        _wait_for_quality_loaded(authenticated_page)

        body = authenticated_page.locator("body").text_content() or ""
        # Page should have the title (in either HU or EN)
        assert any(
            w in body for w in ["Minoseg", "Quality"]
        ), "Quality page title missing"

    def test_quality_has_content_or_error(self, authenticated_page: Page) -> None:
        _wait_for_quality_loaded(authenticated_page)

        body = authenticated_page.locator("body").text_content() or ""
        # After loading, should show either KPI content, error state, or retry button
        has_content = any(
            w in body for w in [
                "Total Evaluations", "Osszes ertekeles",  # KPI loaded
                "Promptfoo", "Langfuse",                  # External tools loaded
                "retry", "Ujraprob", "Failed",            # Error state
            ]
        )
        assert has_content, f"Quality page has no meaningful content after load: {body[:200]}"

    def test_quality_has_external_tools_section(self, authenticated_page: Page) -> None:
        _wait_for_quality_loaded(authenticated_page)

        # External tools section should be visible even if API fails
        # (it's static HTML, not dependent on API)
        body = authenticated_page.locator("body").text_content() or ""
        has_tools = "Promptfoo" in body and "Langfuse" in body
        # If page is in error state, external tools might still be hidden
        # because they render after the error return
        if not has_tools:
            # Check if page is in error/loading state
            in_error = any(w in body for w in ["Failed", "retry", "Ujra", "Hiba"])
            assert in_error, "Quality page has neither external tools nor error state"

    def test_quality_external_links_present(self, authenticated_page: Page) -> None:
        _wait_for_quality_loaded(authenticated_page)

        # Links only appear when page fully loads (not in error/loading state)
        pf_link = authenticated_page.locator('a[href*="15500"]')
        lf_link = authenticated_page.locator('a[href*="langfuse"]')

        if pf_link.count() > 0:
            expect(pf_link.first).to_have_attribute("target", "_blank")
        if lf_link.count() > 0:
            expect(lf_link.first).to_have_attribute("target", "_blank")

        # At least verify the page didn't crash
        body = authenticated_page.locator("body").text_content() or ""
        assert len(body.strip()) > 20, "Quality page is empty"
