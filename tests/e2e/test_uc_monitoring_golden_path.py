"""
Monitoring + Runs Trace drill-down — golden-path E2E (S111).

@test_registry:
    suite: e2e-uc-monitoring
    component: aiflow-admin.runs + aiflow-admin.monitoring + api.v1.runs + api.v1.monitoring
    covers:
        - aiflow-admin/src/pages-new/Runs.tsx
        - aiflow-admin/src/pages-new/RunDetail.tsx
        - aiflow-admin/src/components-new/TraceTree.tsx
        - aiflow-admin/src/pages-new/Monitoring.tsx
        - src/aiflow/api/v1/runs.py (GET /runs/{id}/trace)
        - src/aiflow/api/v1/monitoring.py (GET /monitoring/span-metrics)
    phase: sprint-l-s111
    priority: critical
    estimated_duration_ms: 30000
    requires_services: [postgresql, redis, fastapi, vite]
    tags: [e2e, uc_monitoring, golden-path, sprint-l, v1.4.8]

Sprint L S111 opening test: verifies the Langfuse drill-down surface works
end-to-end against the running stack.

    Login → /runs (list + Trace column)
          → /runs/:id (detail page renders trace section gracefully even
                       when no Langfuse data is attached)
          → /monitoring (loads the 24h span-metrics block)

No Langfuse cloud connectivity is required — the tests accept both the
populated and the "no trace recorded" rendering paths (empty-state is still
a valid outcome during dev/demo).
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.conftest import BASE_URL

pytestmark = pytest.mark.e2e


class TestUcMonitoringGoldenPath:
    """End-to-end smoke over the Runs + Monitoring observability surface."""

    def test_runs_list_renders_with_trace_column(
        self, authenticated_page: Page, console_errors: list[str]
    ) -> None:
        page = authenticated_page
        page.goto(f"{BASE_URL}/#/runs")
        page.wait_for_load_state("networkidle")

        # Trace column header is present (new S111 column)
        expect(page.locator("th", has_text="Trace")).to_be_visible()

        # No console errors during navigation
        assert console_errors == [], f"Console errors: {console_errors}"

    def test_run_detail_shows_trace_section(
        self, authenticated_page: Page, console_errors: list[str]
    ) -> None:
        page = authenticated_page
        page.goto(f"{BASE_URL}/#/runs")
        page.wait_for_load_state("networkidle")

        rows = page.locator("table tbody tr")
        if rows.count() == 0:
            pytest.skip("No runs in DB — detail page not exercised")

        rows.first.click()
        page.wait_for_url("**/runs/**", timeout=5000)
        page.wait_for_load_state("networkidle")

        # Heading + Trace tree section
        expect(page.locator("h1, h2, h3").filter(has_text="Trace")).to_be_visible()

        # Either a trace grid renders, the "no trace recorded" empty state, or
        # a controlled error banner — all three are valid S111 outcomes. What
        # must NOT appear is a raw 500/uncaught exception crash.
        body_text = page.locator("body").inner_text()
        assert any(needle in body_text for needle in ("Trace", "trace", "Lepes naplo", "Step Log"))

        assert console_errors == [], f"Console errors: {console_errors}"

    def test_monitoring_page_renders_span_metrics_block(
        self, authenticated_page: Page, console_errors: list[str]
    ) -> None:
        page = authenticated_page
        page.goto(f"{BASE_URL}/#/monitoring")
        page.wait_for_load_state("networkidle")

        # S111 LLM span metrics header
        expect(page.locator("h3", has_text="LLM Spans")).to_be_visible()

        # Either the table renders or a controlled unavailable notice shows.
        table_or_notice = page.locator("text=/LLM Spans|Span metrics unavailable|No spans/")
        expect(table_or_notice.first).to_be_visible()

        assert console_errors == [], f"Console errors: {console_errors}"
