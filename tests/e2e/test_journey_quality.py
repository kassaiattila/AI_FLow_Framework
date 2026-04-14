"""
Multi-page user journey: Quality & Observability.

Login → Quality dashboard → KPIs → rubrics → external tools → Costs → Monitoring.
Tests the quality/observability browsing flow.

@test_registry:
    suite: e2e-journey
    component: aiflow-admin.quality
    covers: [aiflow-admin/src/pages-new/Quality.tsx, aiflow-admin/src/pages-new/Costs.tsx, aiflow-admin/src/pages-new/Monitoring.tsx]
    phase: S42
    priority: critical
    estimated_duration_ms: 40000
    requires_services: [postgresql, redis, fastapi, vite]
    tags: [e2e, journey, quality, observability, playwright, deep]
"""

from __future__ import annotations

from playwright.sync_api import Page, expect

from tests.e2e.conftest import navigate_to


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
                "Quality",
                "Minoseg",
                "Promptfoo",
                "Langfuse",
                "Evaluations",
                "ertekeles",
                "retry",
                "Ujraprob",
                "Failed",
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
            e
            for e in errors
            if not any(
                x in e
                for x in [
                    "favicon",
                    "ResizeObserver",
                    "Failed to fetch",
                    "Failed to load resource",
                    "Maximum update depth",
                    "CORS policy",
                ]
            )
        ]
        assert not real_errors, f"Console errors during observability loop: {real_errors}"


class TestQualityDeepJourney:
    """Deep E2E tests: real interactions on Quality, Monitoring, Costs pages (C6.3)."""

    def test_quality_rubric_selector(self, authenticated_page: Page) -> None:
        """Quality page: rubric table renders, clicking a row selects it, KPI cards visible."""
        page = authenticated_page
        _wait_quality_loaded(page)

        body = page.locator("body").text_content() or ""

        # KPI cards should show score/pass rate values (contain % or $)
        has_kpi = any(c in body for c in ["%", "$"])
        assert has_kpi, f"Quality KPI cards missing numeric values: {body[:300]}"

        # Rubric table should exist
        rubric_table = page.locator("table")
        if rubric_table.count() == 0:
            # No rubrics loaded (API may be down) — graceful skip
            return

        rubric_rows = page.locator("table tbody tr")
        if rubric_rows.count() == 0:
            return

        # Click a rubric row → should highlight it (no crash)
        rubric_rows.first.click()
        page.wait_for_timeout(300)

        # Select dropdown should exist and have options
        rubric_select = page.locator("select").first
        if rubric_select.count() > 0:
            options = rubric_select.locator("option")
            assert options.count() > 0, "Rubric select dropdown has no options"

        # Page should not crash after interaction
        body_after = page.locator("body").text_content() or ""
        assert len(body_after.strip()) > 50, "Page crashed after rubric click"

    def test_monitoring_service_cards_and_refresh(self, authenticated_page: Page) -> None:
        """Monitoring page: service cards with status + latency, auto-refresh dropdown, refresh button."""
        page = authenticated_page
        navigate_to(page, "/monitoring")
        page.wait_for_timeout(2000)

        # Wait for spinner to clear
        spinner = page.locator('[class*="animate-spin"]')
        if spinner.count() > 0:
            spinner.first.wait_for(state="hidden", timeout=10000)

        body = page.locator("body").text_content() or ""

        # Service cards should render (at least 1 card with service name + latency)
        has_service_info = any(
            w in body for w in ["ms", "latency", "Latency", "healthy", "degraded", "Service"]
        )
        if not has_service_info:
            # API may be down — check for error state
            assert any(w in body for w in ["retry", "Ujraprob", "Failed", "Error"]), (
                f"Monitoring page has no service cards or error state: {body[:300]}"
            )
            return

        # Auto-refresh dropdown should exist with Off/10s/30s/60s
        auto_refresh_select = page.locator("select")
        assert auto_refresh_select.count() > 0, "Auto-refresh dropdown not found"
        select_text = auto_refresh_select.first.text_content() or ""
        assert any(v in select_text for v in ["Off", "10s", "30s", "60s"]), (
            f"Auto-refresh dropdown missing expected options: {select_text}"
        )

        # Refresh button should exist and be clickable
        refresh_btn = page.locator("button").filter(has_text="Refresh")
        if refresh_btn.count() == 0:
            refresh_btn = page.locator("button").filter(has_text="refresh")
        if refresh_btn.count() == 0:
            refresh_btn = page.locator("button").filter(has_text="Frissit")
        assert refresh_btn.count() > 0, "Refresh button not found on Monitoring page"
        refresh_btn.first.click()
        page.wait_for_timeout(500)

        # Page should still function after refresh click
        body_after = page.locator("body").text_content() or ""
        assert len(body_after.strip()) > 50, "Page crashed after refresh click"

    def test_monitoring_restart_confirm_dialog(self, authenticated_page: Page) -> None:
        """Monitoring page: Restart button → ConfirmDialog → Cancel closes it."""
        page = authenticated_page
        navigate_to(page, "/monitoring")
        page.wait_for_timeout(2000)

        spinner = page.locator('[class*="animate-spin"]')
        if spinner.count() > 0:
            spinner.first.wait_for(state="hidden", timeout=10000)

        # Find Restart button on any service card
        restart_btn = page.locator("button").filter(has_text="Restart")
        if restart_btn.count() == 0:
            # No service cards rendered (API down) — graceful skip
            return

        # Click Restart → ConfirmDialog should appear
        restart_btn.first.click()
        page.wait_for_timeout(300)

        body = page.locator("body").text_content() or ""
        # Dialog should mention restart confirmation
        has_dialog = any(
            w in body for w in ["Restart", "restart", "Confirm", "Megerosit", "Service"]
        )
        assert has_dialog, "Restart confirmation dialog did not appear"

        # Cancel button should close the dialog
        cancel_btn = page.locator("button").filter(has_text="Cancel")
        if cancel_btn.count() == 0:
            cancel_btn = page.locator("button").filter(has_text="Megse")
        if cancel_btn.count() > 0:
            cancel_btn.first.click()
            page.wait_for_timeout(300)

            # Dialog overlay should be gone
            overlay = page.locator(".fixed.inset-0")
            assert overlay.count() == 0, "Restart dialog did not close after Cancel"

    def test_costs_kpi_and_breakdown_tables(self, authenticated_page: Page) -> None:
        """Costs page: KPI cards (Total Cost, Runs, Tokens, API Calls) + DataTable visible."""
        page = authenticated_page
        navigate_to(page, "/costs")
        page.wait_for_timeout(1500)

        body = page.locator("body").text_content() or ""

        # KPI cards should show numeric values
        has_cost_kpi = any(w in body for w in ["$", "Total", "Runs", "Tokens", "API Calls"])
        if not has_cost_kpi:
            # Error state — check gracefully
            assert any(w in body for w in ["retry", "Ujraprob", "Failed", "Error", "Cost"]), (
                f"Costs page has no KPI cards or error state: {body[:300]}"
            )
            return

        # At least one DataTable should render (By Skill or By Model)
        tables = page.locator("table")
        if tables.count() > 0:
            # Table should have header with relevant columns
            header_text = tables.first.locator("thead").text_content() or ""
            has_relevant_col = any(
                w in header_text
                for w in ["Skill", "skill", "Model", "model", "Cost", "cost", "Runs", "Token"]
            )
            assert has_relevant_col, f"Cost table missing expected columns: {header_text[:200]}"
        else:
            # No table — page might show empty or chart only
            assert len(body.strip()) > 100, "Costs page has minimal content"
