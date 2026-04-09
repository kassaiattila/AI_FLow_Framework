"""
E2E tests for B8 journey-based navigation.

Sidebar 6 groups, breadcrumb, dashboard journey cards, Journey 1+2 flows.

@test_registry:
    suite: e2e-journey
    component: aiflow-admin.navigation
    covers:
      - aiflow-admin/src/layout/Sidebar.tsx
      - aiflow-admin/src/components-new/Breadcrumb.tsx
      - aiflow-admin/src/pages-new/Dashboard.tsx
    phase: S33
    priority: critical
    estimated_duration_ms: 30000
    requires_services: [postgresql, redis, fastapi, vite]
    tags: [e2e, journey, navigation, playwright]
"""

from __future__ import annotations

from playwright.sync_api import Page, expect

from tests.e2e.conftest import navigate_to


class TestJourneyNavigation:
    """B8 journey-based navigation tests."""

    def test_sidebar_has_6_groups(self, authenticated_page: Page) -> None:
        """Sidebar renders 6 journey-based groups + bottom section."""
        page = authenticated_page
        navigate_to(page, "/")

        sidebar = page.locator("aside")
        expect(sidebar).to_be_visible()

        # 5 main groups + "More" bottom label = 6 group labels
        group_headers = sidebar.locator("button")
        # At least 5 collapsible group buttons (main groups)
        assert group_headers.count() >= 5, (
            f"Expected at least 5 sidebar group buttons, got {group_headers.count()}"
        )

        # Check key menu items exist
        sidebar_text = sidebar.text_content() or ""
        # Verify journey group names (Hungarian or English)
        assert any(w in sidebar_text for w in ["Dokumentum", "Document Processing"]), (
            "Document Processing group missing"
        )
        assert any(w in sidebar_text for w in ["Monitoring", "monitoring"]), (
            "Monitoring group missing"
        )
        assert any(w in sidebar_text for w in ["Beallitasok", "Settings"]), "Settings group missing"

        # Spec Writer should now be in the menu (was missing before B8)
        spec_link = sidebar.locator('a[href*="spec-writer"]')
        assert spec_link.count() > 0, "Spec Writer not found in sidebar"

        # Cubix should be in bottom menu
        cubix_link = sidebar.locator('a[href*="cubix"]')
        assert cubix_link.count() > 0, "Cubix not found in sidebar bottom menu"

    def test_breadcrumb_shows_hierarchy(self, authenticated_page: Page) -> None:
        """Navigate to documents → breadcrumb shows Dashboard > group."""
        page = authenticated_page
        navigate_to(page, "/documents")

        # Breadcrumb nav should be visible
        breadcrumb = page.locator('nav[aria-label="Breadcrumb"]')
        expect(breadcrumb).to_be_visible()

        crumb_text = breadcrumb.text_content() or ""
        assert "Dashboard" in crumb_text, f"Breadcrumb missing Dashboard: {crumb_text}"
        assert any(w in crumb_text for w in ["Dokumentum", "Document"]), (
            f"Breadcrumb missing group name: {crumb_text}"
        )

        # Dashboard link should be clickable
        dashboard_link = breadcrumb.locator('a[href*="/"]').first
        expect(dashboard_link).to_be_visible()

    def test_dashboard_journey_cards(self, authenticated_page: Page) -> None:
        """Dashboard shows 4 clickable journey cards."""
        page = authenticated_page
        navigate_to(page, "/")

        # Wait for dashboard to load
        page.wait_for_timeout(1000)

        body_text = page.locator("main").text_content() or ""

        # Journey card indicators (check for "Open" or "Megnyitas" link text)
        assert (
            body_text.count("→") >= 4
            or body_text.count("Megnyitas") >= 4
            or body_text.count("Open viewer") >= 4
        ), "Expected 4 journey cards with navigation arrows"

        # Click first journey card (Document Processing) → should navigate to /documents
        journey_cards = page.locator("main >> div.cursor-pointer.rounded-xl")
        if journey_cards.count() >= 1:
            journey_cards.first.click()
            page.wait_for_load_state("networkidle")
            assert "documents" in page.url, (
                f"Journey card click didn't navigate to documents: {page.url}"
            )

    def test_journey1_invoice_flow(self, authenticated_page: Page) -> None:
        """Journey 1: Documents → detail → verify page reachable."""
        page = authenticated_page
        navigate_to(page, "/documents")

        # Documents page should load
        body = page.locator("body").text_content() or ""
        assert any(w in body for w in ["Document", "Dokumentum", "No data", "Nincs"]), (
            "Documents page missing expected content"
        )

        # Check if there are documents to click on
        table_rows = page.locator("table tbody tr")
        if table_rows.count() > 0:
            # Click first row → should navigate to detail
            table_rows.first.click()
            page.wait_for_load_state("networkidle")
            assert "documents" in page.url, "Not on document detail page"

        # Navigate to reviews/verification page
        navigate_to(page, "/reviews")
        body = page.locator("body").text_content() or ""
        assert any(
            w in body
            for w in ["Review", "Verifikacio", "review", "verifikacio", "No data", "Nincs"]
        ), "Reviews/Verification page missing expected content"

    def test_journey2_monitoring_flow(self, authenticated_page: Page) -> None:
        """Journey 2: Dashboard → drill-down runs → costs → back."""
        page = authenticated_page

        # Start at runs
        navigate_to(page, "/runs")
        body = page.locator("body").text_content() or ""
        assert any(w in body for w in ["Run", "Workflow", "Pipeline", "No data", "Nincs"]), (
            "Runs page missing expected content"
        )

        # Breadcrumb should show monitoring hierarchy
        breadcrumb = page.locator('nav[aria-label="Breadcrumb"]')
        if breadcrumb.count() > 0:
            crumb_text = breadcrumb.text_content() or ""
            assert "Monitoring" in crumb_text or "monitoring" in crumb_text.lower(), (
                f"Runs breadcrumb missing Monitoring: {crumb_text}"
            )

        # Navigate to costs
        navigate_to(page, "/costs")
        body = page.locator("body").text_content() or ""
        assert any(w in body for w in ["Cost", "Koltseg", "cost", "koltseg", "No data", "Nincs"]), (
            "Costs page missing expected content"
        )

        # Navigate back to dashboard
        navigate_to(page, "/")
        body = page.locator("body").text_content() or ""
        assert any(w in body for w in ["Dashboard", "Skills", "Active"]), (
            "Dashboard missing expected content after navigation"
        )
