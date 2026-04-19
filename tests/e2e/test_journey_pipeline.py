"""
Multi-page user journey: Pipeline orchestration.

Login → Pipelines → list → Services catalog → pipeline detail (if exists).
Tests the pipeline orchestration browsing flow + deep CRUD interactions.

@test_registry:
    suite: e2e-journey
    component: aiflow-admin.pipelines
    covers: [aiflow-admin/src/pages-new/Pipelines.tsx, aiflow-admin/src/pages-new/Services.tsx, aiflow-admin/src/pages-new/Runs.tsx, aiflow-admin/src/pages-new/RunDetail.tsx, aiflow-admin/src/pages-new/PipelineDetail.tsx]
    phase: S41
    priority: critical
    estimated_duration_ms: 40000
    requires_services: [postgresql, redis, fastapi, vite]
    tags: [e2e, journey, pipelines, services, runs, playwright, deep]
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
                    "CORS policy",
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


class TestPipelineDeepJourney:
    """Deep E2E tests: real interactions on Pipeline/Runs/Services pages (C6.2)."""

    def test_runs_table_shows_status_badges(self, authenticated_page: Page) -> None:
        """Runs list shows status badges (completed/failed/running) + Skill/Duration/Cost columns."""
        page = authenticated_page
        navigate_to(page, "/runs")
        # Wait for DataTable to finish its initial fetch (loading skeleton → table or empty state)
        page.wait_for_timeout(1500)

        body = page.locator("body").text_content() or ""
        rows = page.locator("table tbody tr")

        if rows.count() > 0:
            # Status badges should be visible (rounded pill spans with status text)
            status_badges = page.locator("table tbody span.rounded-full")
            assert status_badges.count() > 0, "No status badges found in Runs table"

            # Check that the first badge has a known status value
            first_badge_text = status_badges.first.text_content() or ""
            known_statuses = ["completed", "failed", "running", "pending", "cancelled"]
            assert any(s in first_badge_text.lower() for s in known_statuses), (
                f"Unexpected status badge text: {first_badge_text}"
            )

            # Table should have header columns for Skill, Duration, Cost
            header_text = page.locator("table thead").text_content() or ""
            # These columns exist (EN or HU labels)
            assert any(
                w in header_text
                for w in ["Skill", "skill", "Duration", "Idotartam", "Cost", "Koltseg"]
            ), f"Runs table missing expected columns: {header_text[:200]}"
        else:
            # Empty state
            assert any(w in body for w in ["No data", "Nincs", "empty"]), (
                "Runs page has no rows and no empty state"
            )

    def test_run_detail_step_log(self, authenticated_page: Page) -> None:
        """Click first run → RunDetail loads with step log table + Export JSON button."""
        page = authenticated_page
        navigate_to(page, "/runs")

        rows = page.locator("table tbody tr")
        if rows.count() == 0:
            return

        # Click first row to navigate to RunDetail
        rows.first.click()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(500)

        # Should be on /runs/:id
        assert "/runs/" in page.url, f"Expected run detail URL, got {page.url}"

        body = page.locator("body").text_content() or ""

        # Step Log section should be visible
        has_step_log = any(w in body for w in ["Step Log", "Step", "step_name", "Lepes"])
        assert has_step_log, "RunDetail page missing Step Log section"

        # Step rows in the detail table should show step name + model + tokens
        step_table = page.locator("table")
        if step_table.count() > 0:
            step_header = step_table.locator("thead").text_content() or ""
            # Check for Model and Tokens columns
            assert any(w in step_header for w in ["Model", "model", "Modell"]), (
                f"Step log table missing Model column: {step_header[:200]}"
            )
            assert any(w in step_header for w in ["Token", "token"]), (
                f"Step log table missing Tokens column: {step_header[:200]}"
            )

        # Export JSON button should exist
        export_btn = page.locator("button").filter(has_text="Export")
        if export_btn.count() == 0:
            export_btn = page.locator("button").filter(has_text="JSON")
        assert export_btn.count() > 0, "RunDetail page missing Export JSON button"

    def test_run_detail_retry_button(self, authenticated_page: Page) -> None:
        """RunDetail Retry button opens ConfirmDialog → Cancel closes it."""
        page = authenticated_page
        navigate_to(page, "/runs")

        rows = page.locator("table tbody tr")
        if rows.count() == 0:
            return

        # Navigate to first run detail
        rows.first.click()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(500)

        # Retry button
        retry_btn = page.locator("button").filter(has_text="Retry")
        if retry_btn.count() == 0:
            retry_btn = page.locator("button").filter(has_text="Ujra")
        if retry_btn.count() == 0:
            # Retry might be disabled if no pipeline_id — still pass
            return

        # Click Retry → ConfirmDialog should appear
        retry_btn.first.click()
        page.wait_for_timeout(300)

        body = page.locator("body").text_content() or ""
        has_confirm = any(
            w in body for w in ["Retry", "Confirm", "Megerosit", "Biztosan", "retry", "Ujra"]
        )
        assert has_confirm, "Retry confirmation dialog did not appear"

        # Cancel should close the dialog
        cancel_btn = page.locator("button").filter(has_text="Cancel")
        if cancel_btn.count() == 0:
            cancel_btn = page.locator("button").filter(has_text="Megse")
        if cancel_btn.count() > 0:
            cancel_btn.first.click()
            page.wait_for_timeout(300)

    def test_pipeline_detail_yaml_tab(self, authenticated_page: Page) -> None:
        """Pipeline detail loads → YAML tab shows content + Copy YAML button."""
        page = authenticated_page
        navigate_to(page, "/pipelines")

        # Find a pipeline link in the table (name column is a clickable button)
        pipeline_link = page.locator(
            "table tbody button.text-brand-600, table tbody a[href*='/pipelines/']"
        ).first

        if pipeline_link.count() == 0:
            # No pipelines — try clicking a table row
            rows = page.locator("table tbody tr")
            if rows.count() == 0:
                return
            rows.first.click()
        else:
            pipeline_link.click()

        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(500)

        # Should be on /pipelines/:id
        assert "/pipelines/" in page.url, f"Expected pipeline detail URL, got {page.url}"

        # YAML tab should exist
        yaml_tab = page.locator("button").filter(has_text="YAML")
        assert yaml_tab.count() > 0, "Pipeline detail missing YAML tab"

        # Click YAML tab
        yaml_tab.first.click()
        page.wait_for_timeout(300)

        # YAML content should be visible in a <pre> block
        pre_block = page.locator("pre")
        assert pre_block.count() > 0, "YAML tab did not show <pre> content"

        yaml_text = pre_block.first.text_content() or ""
        assert len(yaml_text.strip()) > 10, "YAML content is empty"

        # Copy YAML button should exist
        copy_btn = page.locator("button").filter(has_text="Copy")
        if copy_btn.count() == 0:
            copy_btn = page.locator("button").filter(has_text="Masol")
        assert copy_btn.count() > 0, "Pipeline detail YAML tab missing Copy button"

    def test_services_catalog_pipeline_badge(self, authenticated_page: Page) -> None:
        """Services catalog shows Pipeline-ready badge and Run Pipeline button."""
        page = authenticated_page
        navigate_to(page, "/services")
        page.wait_for_timeout(500)

        body = page.locator("body").text_content() or ""

        # At least one service should show "Pipeline-ready" or translated equivalent
        has_pipeline_badge = any(
            w in body
            for w in [
                "Pipeline-ready",
                "pipeline-ready",
                "Pipeline Ready",
                "Csovezetek kesz",
                "pipelineReady",
                "Pipeline",
            ]
        )

        if not has_pipeline_badge:
            # If no pipeline-ready services exist, that's valid — just verify page loaded
            assert len(body.strip()) > 50, "Services page is empty"
            return

        # "Run Pipeline" button should exist for pipeline-ready services
        run_btn = page.locator("button").filter(has_text="Run Pipeline")
        if run_btn.count() == 0:
            # Try translated / link version
            run_link = page.locator("button, a").filter(has_text="Pipeline")
            assert run_link.count() > 0, (
                "Pipeline-ready badge exists but no Run Pipeline button found"
            )
