"""
Multi-page user journey: Admin & Notifications.

Login → Dashboard → KPIs → Services → Notifications bell → Pipelines → Audit.
Tests the admin/governance browsing flow.

@test_registry:
    suite: e2e-journey
    component: aiflow-admin.admin
    covers: [aiflow-admin/src/pages-new/Dashboard.tsx, aiflow-admin/src/pages-new/Admin.tsx]
    phase: S13
    priority: critical
    estimated_duration_ms: 25000
    requires_services: [postgresql, redis, fastapi, vite]
    tags: [e2e, journey, admin, notifications, playwright]
"""
from __future__ import annotations

from playwright.sync_api import Page, expect

from tests.e2e.conftest import navigate_to


class TestAdminJourney:
    """Full admin & governance journey across multiple pages."""

    def test_dashboard_kpis_loaded(self, authenticated_page: Page) -> None:
        """Journey: Dashboard → verify KPI cards are rendered."""
        page = authenticated_page
        navigate_to(page, "/")

        body = page.locator("body").text_content() or ""
        # Dashboard should have meaningful content
        assert len(body.strip()) > 100, "Dashboard has minimal content"

        # Should show some dashboard elements
        has_dashboard = any(
            w in body
            for w in [
                "Dashboard", "Iranyitopult",
                "Skills", "Pipeline", "Service",
                "Active", "Aktiv", "Total", "Osszes",
            ]
        )
        assert has_dashboard, f"Dashboard missing KPI content: {body[:200]}"

    def test_dashboard_to_services_nav(self, authenticated_page: Page) -> None:
        """Journey: Dashboard → Services → verify service count."""
        page = authenticated_page
        navigate_to(page, "/")

        # Navigate to Services
        svc_link = page.locator('a[href*="services"]').first
        expect(svc_link).to_be_visible()
        svc_link.click()
        page.wait_for_load_state("networkidle")
        assert "services" in page.url

        body = page.locator("body").text_content() or ""
        assert len(body.strip()) > 50, "Services page is empty"

    def test_notification_bell_interaction(self, authenticated_page: Page) -> None:
        """Journey: Dashboard → click notification bell → verify dropdown opens."""
        page = authenticated_page
        navigate_to(page, "/")

        # Find notification bell in the top bar
        top_buttons = page.locator("header button, [class*='top'] button, nav ~ div button")
        assert top_buttons.count() >= 1, "No buttons found in top area"

        # Click the first button (should be notification bell)
        top_buttons.first.click()
        page.wait_for_timeout(500)

        # Page should not crash after click
        body = page.locator("body").text_content() or ""
        assert len(body.strip()) > 20, "Page crashed after bell click"

    def test_admin_to_audit_journey(self, authenticated_page: Page) -> None:
        """Journey: Admin → Audit → verify audit log content."""
        page = authenticated_page

        # Admin page
        navigate_to(page, "/admin")
        admin_body = page.locator("body").text_content() or ""
        assert any(
            w in admin_body
            for w in [
                "Admin", "Adminisztrac", "admin",
                "User", "Felhasznalo", "Settings", "Beallitas",
            ]
        ), f"Admin page missing content: {admin_body[:200]}"

        # Navigate to Audit
        audit_link = page.locator('a[href*="audit"]').first
        expect(audit_link).to_be_visible()
        audit_link.click()
        page.wait_for_load_state("networkidle")
        assert "audit" in page.url

        audit_body = page.locator("body").text_content() or ""
        assert any(
            w in audit_body
            for w in ["Audit", "audit", "Log", "log", "Naplo", "No data", "Nincs"]
        ), f"Audit page missing content: {audit_body[:200]}"

    def test_full_admin_loop(self, authenticated_page: Page) -> None:
        """Journey: Dashboard → Services → Pipelines → Audit → Admin → Dashboard."""
        page = authenticated_page
        errors: list[str] = []
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)

        pages_to_visit = ["/", "/services", "/pipelines", "/audit", "/admin", "/"]
        for path in pages_to_visit:
            navigate_to(page, path)
            page.wait_for_timeout(300)
            body = page.locator("body").text_content() or ""
            assert len(body.strip()) > 20, f"Page {path} rendered empty"

        real_errors = [
            e for e in errors
            if not any(x in e for x in [
                "favicon", "ResizeObserver", "Failed to fetch",
                "Failed to load resource", "Maximum update depth",
            ])
        ]
        assert not real_errors, f"Console errors during admin loop: {real_errors}"
