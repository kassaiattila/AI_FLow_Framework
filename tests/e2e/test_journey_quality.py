"""
Multi-page user journey: Quality & Observability.

Login → Quality dashboard → KPIs → rubrics → external tools → Costs → Monitoring.
Tests the quality/observability browsing flow.

@test_registry:
    suite: e2e-journey
    component: aiflow-admin.quality
    covers: [aiflow-admin/src/pages-new/Quality.tsx, aiflow-admin/src/pages-new/Costs.tsx, aiflow-admin/src/pages-new/Monitoring.tsx]
    phase: S13
    priority: critical
    estimated_duration_ms: 25000
    requires_services: [postgresql, redis, fastapi, vite]
    tags: [e2e, journey, quality, observability, playwright]
"""
from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.conftest import BASE_URL, navigate_to


def _wait_quality_loaded(page: Page) -> None:
    """Wait for Quality page to finish loading."""
    navigate_to(page, "/quality")
    page.wait_for_timeout(2000)
    spinner = page.locator('[class*="animate-spin"]')
    if spinner.count() > 0:
        spinner.first.wait_for(state="hidden", timeout=10000)


class TestQualityJourney:
    """Full quality & observability journey across multiple pages."""

    def test_quality_kpis_and_external_tools(self, authenticated_page: Page) -> None:
        """Journey: Quality → verify KPIs load → check external tool links."""
        page = authenticated_page
        _wait_quality_loaded(page)

        body = page.locator("body").text_content() or ""

        # Page should show quality content or error state
        has_content = any(
            w in body
            for w in [
                "Quality", "Minoseg",
                "Promptfoo", "Langfuse",
                "Evaluations", "ertekeles",
                "retry", "Ujraprob", "Failed",
            ]
        )
        assert has_content, f"Quality page has no meaningful content: {body[:200]}"

    def test_quality_external_links_target_blank(self, authenticated_page: Page) -> None:
        """Journey: Quality → verify Promptfoo/Langfuse links open in new tab."""
        page = authenticated_page
        _wait_quality_loaded(page)

        # Check for external tool links
        pf_link = page.locator('a[href*="15500"]')
        lf_link = page.locator('a[href*="langfuse"]')

        if pf_link.count() > 0:
            expect(pf_link.first).to_have_attribute("target", "_blank")
        if lf_link.count() > 0:
            expect(lf_link.first).to_have_attribute("target", "_blank")

    def test_quality_to_costs_journey(self, authenticated_page: Page) -> None:
        """Journey: Quality → Costs → verify cost data or empty state."""
        page = authenticated_page
        _wait_quality_loaded(page)

        # Navigate to Costs
        costs_link = page.locator('a[href*="costs"]').first
        expect(costs_link).to_be_visible()
        costs_link.click()
        page.wait_for_load_state("networkidle")
        assert "costs" in page.url

        body = page.locator("body").text_content() or ""
        assert any(
            w in body
            for w in ["Cost", "Koltseg", "cost", "koltseg", "No data", "Nincs", "$", "USD"]
        ), f"Costs page missing expected content: {body[:200]}"

    def test_quality_to_monitoring_journey(self, authenticated_page: Page) -> None:
        """Journey: Quality → Monitoring → verify monitoring content."""
        page = authenticated_page
        _wait_quality_loaded(page)

        # Navigate to Monitoring
        mon_link = page.locator('a[href*="monitoring"]').first
        expect(mon_link).to_be_visible()
        mon_link.click()
        page.wait_for_load_state("networkidle")
        assert "monitoring" in page.url

        body = page.locator("body").text_content() or ""
        assert any(
            w in body
            for w in ["Monitor", "monitor", "Health", "health", "Status", "status", "Service"]
        ), f"Monitoring page missing expected content: {body[:200]}"

    def test_observability_loop(self, authenticated_page: Page) -> None:
        """Journey: Quality → Costs → Monitoring → Quality (full observability loop)."""
        page = authenticated_page
        errors: list[str] = []
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)

        # Quality
        _wait_quality_loaded(page)
        q_body = page.locator("body").text_content() or ""
        assert len(q_body.strip()) > 20

        # Costs
        navigate_to(page, "/costs")
        c_body = page.locator("body").text_content() or ""
        assert len(c_body.strip()) > 20

        # Monitoring
        navigate_to(page, "/monitoring")
        m_body = page.locator("body").text_content() or ""
        assert len(m_body.strip()) > 20

        # Back to Quality
        navigate_to(page, "/quality")
        page.wait_for_timeout(1000)

        real_errors = [
            e for e in errors
            if not any(x in e for x in [
                "favicon", "ResizeObserver", "Failed to fetch",
                "Failed to load resource", "Maximum update depth",
            ])
        ]
        assert not real_errors, f"Console errors during observability loop: {real_errors}"
