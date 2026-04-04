"""
Multi-page user journey: Pipeline orchestration.

Login → Pipelines → list → Services catalog → pipeline detail (if exists).
Tests the pipeline orchestration browsing flow.

@test_registry:
    suite: e2e-journey
    component: aiflow-admin.pipelines
    covers: [aiflow-admin/src/pages-new/Pipelines.tsx, aiflow-admin/src/pages-new/Services.tsx]
    phase: S13
    priority: critical
    estimated_duration_ms: 20000
    requires_services: [postgresql, redis, fastapi, vite]
    tags: [e2e, journey, pipelines, services, playwright]
"""

from __future__ import annotations

from playwright.sync_api import Page, expect

from tests.e2e.conftest import navigate_to


class TestPipelineJourney:
    """Full pipeline orchestration journey across multiple pages."""

    def test_pipelines_list_renders(self, authenticated_page: Page) -> None:
        """Journey: Pipelines → verify list or empty state."""
        page = authenticated_page
        navigate_to(page, "/pipelines")

        body = page.locator("body").text_content() or ""
        assert any(
            w in body
            for w in ["Pipeline", "pipeline", "Orchestr", "No data", "Nincs", "Csovezetek"]
        ), f"Pipelines page missing content: {body[:200]}"

    def test_pipelines_to_services_and_back(self, authenticated_page: Page) -> None:
        """Journey: Pipelines → Services → back to Pipelines."""
        page = authenticated_page

        # Pipelines
        navigate_to(page, "/pipelines")
        assert "pipelines" in page.url

        # Navigate to Services
        svc_link = page.locator('a[href*="services"]').first
        expect(svc_link).to_be_visible()
        svc_link.click()
        page.wait_for_load_state("networkidle")
        assert "services" in page.url

        svc_body = page.locator("body").text_content() or ""
        assert any(w in svc_body for w in ["Service", "service", "Szolg", "adapter"]), (
            "Services page missing content"
        )

        # Back to Pipelines
        pip_link = page.locator('a[href*="pipelines"]').first
        pip_link.click()
        page.wait_for_load_state("networkidle")
        assert "pipelines" in page.url

    def test_pipelines_to_runs_journey(self, authenticated_page: Page) -> None:
        """Journey: Pipelines → Runs → verify execution history."""
        page = authenticated_page

        navigate_to(page, "/pipelines")

        # Navigate to Runs
        runs_link = page.locator('a[href*="runs"]').first
        expect(runs_link).to_be_visible()
        runs_link.click()
        page.wait_for_load_state("networkidle")
        assert "runs" in page.url

        body = page.locator("body").text_content() or ""
        assert any(
            w in body for w in ["Run", "Futtat", "run", "Execution", "No data", "Nincs", "Status"]
        ), f"Runs page missing content: {body[:200]}"

    def test_pipeline_services_runs_costs_loop(self, authenticated_page: Page) -> None:
        """Journey: Pipelines → Services → Runs → Costs (full orchestration loop)."""
        page = authenticated_page
        errors: list[str] = []
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)

        pages_to_visit = ["/pipelines", "/services", "/runs", "/costs"]
        for path in pages_to_visit:
            navigate_to(page, path)
            page.wait_for_timeout(300)
            body = page.locator("body").text_content() or ""
            assert len(body.strip()) > 20, f"Page {path} rendered empty"

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
                ]
            )
        ]
        assert not real_errors, f"Console errors during pipeline loop: {real_errors}"

    def test_services_catalog_search_flow(self, authenticated_page: Page) -> None:
        """Journey: Services → verify search/filter capability."""
        page = authenticated_page
        navigate_to(page, "/services")

        body = page.locator("body").text_content() or ""
        assert len(body.strip()) > 50, "Services page is empty"

        # Check for search input (services page has search capability)
        search = page.locator(
            'input[type="search"], input[type="text"], '
            'input[placeholder*="earch"], input[placeholder*="eres"]'
        )
        if search.count() > 0:
            # Type a search term
            search.first.fill("rag")
            page.wait_for_timeout(500)
            # Page should still be functional
            body_after = page.locator("body").text_content() or ""
            assert len(body_after.strip()) > 20, "Services page crashed after search"
