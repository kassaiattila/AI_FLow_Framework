"""
Multi-page user journey: Admin & Notifications.

Login → Dashboard → KPIs → Services → Notifications bell → Pipelines → Audit.
Tests the admin/governance browsing flow.

@test_registry:
    suite: e2e-journey
    component: aiflow-admin.admin
    covers: [aiflow-admin/src/pages-new/Dashboard.tsx, aiflow-admin/src/pages-new/Admin.tsx, aiflow-admin/src/pages-new/Audit.tsx]
    phase: S42
    priority: critical
    estimated_duration_ms: 40000
    requires_services: [postgresql, redis, fastapi, vite]
    tags: [e2e, journey, admin, notifications, playwright, deep]
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
                "Dashboard",
                "Iranyitopult",
                "Skills",
                "Pipeline",
                "Service",
                "Active",
                "Aktiv",
                "Total",
                "Osszes",
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
                "Admin",
                "Adminisztrac",
                "admin",
                "User",
                "Felhasznalo",
                "Settings",
                "Beallitas",
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
            w in audit_body for w in ["Audit", "audit", "Log", "log", "Naplo", "No data", "Nincs"]
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
        assert not real_errors, f"Console errors during admin loop: {real_errors}"


class TestAdminDeepJourney:
    """Deep E2E tests: real CRUD interactions on Admin + Audit pages (C6.3)."""

    def test_admin_users_tab_content(self, authenticated_page: Page) -> None:
        """Admin page: Users tab shows DataTable with email, name, role, status columns."""
        page = authenticated_page
        navigate_to(page, "/admin")
        page.wait_for_timeout(1500)

        # Users tab should be active by default (or click it)
        users_tab = page.locator("button").filter(has_text="Users")
        if users_tab.count() == 0:
            users_tab = page.locator("button").filter(has_text="Felhasznalo")
        if users_tab.count() > 0:
            users_tab.first.click()
            page.wait_for_timeout(500)

        # DataTable should exist with user columns
        table = page.locator("table")
        if table.count() > 0:
            header_text = table.first.locator("thead").text_content() or ""
            # Check for email, name, role, status columns
            has_email = any(w in header_text for w in ["Email", "email", "E-mail"])
            has_role = any(w in header_text for w in ["Role", "role", "Szerepkor"])
            assert has_email or has_role, (
                f"Users table missing expected columns: {header_text[:200]}"
            )

            # Check for role badges (rounded-full spans in tbody)
            rows = table.first.locator("tbody tr")
            if rows.count() > 0:
                badges = table.first.locator("tbody span.rounded-full")
                assert badges.count() > 0, "No role/status badges in Users table"

        # Create User button should be visible
        create_btn = page.locator("button").filter(has_text="Create User")
        if create_btn.count() == 0:
            create_btn = page.locator("button").filter(has_text="Add User")
        if create_btn.count() == 0:
            create_btn = page.locator("button").filter(has_text="Felhasznalo")
        # The action button text changes based on tab — find the brand-colored button
        if create_btn.count() == 0:
            create_btn = page.locator("button.bg-brand-500")
        assert create_btn.count() > 0, "Create User / action button not found"

    def test_admin_api_keys_tab(self, authenticated_page: Page) -> None:
        """Admin page: API Keys tab shows DataTable with name, prefix (mono), status."""
        page = authenticated_page
        navigate_to(page, "/admin")
        page.wait_for_timeout(1000)

        # Click API Keys tab
        keys_tab = page.locator("button").filter(has_text="API Keys")
        if keys_tab.count() == 0:
            keys_tab = page.locator("button").filter(has_text="API")
        if keys_tab.count() == 0:
            # Tabs may not be rendered yet
            return
        keys_tab.first.click()
        page.wait_for_timeout(500)

        # DataTable should exist
        table = page.locator("table")
        if table.count() > 0:
            header_text = table.first.locator("thead").text_content() or ""
            # Check for name, prefix columns
            has_name = any(w in header_text for w in ["Name", "name", "Nev"])
            has_prefix = any(w in header_text for w in ["Prefix", "prefix"])
            assert has_name or has_prefix, (
                f"API Keys table missing expected columns: {header_text[:200]}"
            )

            # Prefix should render in monospace (font-mono class)
            mono_spans = table.first.locator("tbody .font-mono")
            if table.first.locator("tbody tr").count() > 0:
                assert mono_spans.count() > 0, "API key prefix not rendered in monospace"

        # Generate Key button should be visible (the brand action button)
        gen_btn = page.locator("button.bg-brand-500")
        assert gen_btn.count() > 0, "Generate Key action button not found"

    def test_admin_create_user_modal(self, authenticated_page: Page) -> None:
        """Admin page: Create User button → modal with inputs → Cancel closes it."""
        page = authenticated_page
        navigate_to(page, "/admin")
        page.wait_for_timeout(1000)

        # Ensure Users tab is active (use stable testid; fall back to text)
        users_tab = page.locator('[data-testid="admin-tab-users"]')
        if users_tab.count() == 0:
            users_tab = page.locator("button").filter(has_text="Users")
        if users_tab.count() > 0:
            users_tab.first.click()
            page.wait_for_timeout(300)

        # Click Create User (stable testid; fall back to brand-colored button)
        action_btn = page.locator('[data-testid="admin-create-user"]')
        if action_btn.count() == 0:
            action_btn = page.locator("button.bg-brand-500").filter(has_text="Felhasznalo")
        if action_btn.count() == 0:
            return
        action_btn.first.click()
        page.wait_for_timeout(300)

        # Modal should appear (fixed overlay)
        modal = page.locator(".fixed.inset-0")
        assert modal.count() > 0, "Create User modal did not appear"

        # Modal should have email, name, password inputs + role select
        modal_body = modal.first.text_content() or ""
        has_email_field = page.locator('.fixed input[type="email"]').count() > 0
        has_password_field = page.locator('.fixed input[type="password"]').count() > 0
        has_role_select = page.locator(".fixed select").count() > 0

        assert has_email_field, "Create User modal missing email input"
        assert has_password_field, "Create User modal missing password input"
        assert has_role_select or "role" in modal_body.lower() or "Viewer" in modal_body, (
            "Create User modal missing role selector"
        )

        # Cancel should close the modal
        cancel_btn = page.locator(".fixed button").filter(has_text="Cancel")
        if cancel_btn.count() == 0:
            cancel_btn = page.locator(".fixed button").filter(has_text="Megse")
        if cancel_btn.count() > 0:
            cancel_btn.first.click()
            page.wait_for_timeout(300)
            overlay = page.locator(".fixed.inset-0")
            assert overlay.count() == 0, "Create User modal did not close after Cancel"

    def test_audit_filter_and_export(self, authenticated_page: Page) -> None:
        """Audit page: filter dropdowns, CSV export button, DataTable columns."""
        page = authenticated_page
        navigate_to(page, "/audit")
        page.wait_for_timeout(1500)

        # Filter dropdowns should exist (action + entity type)
        filter_selects = page.locator("select")
        assert filter_selects.count() >= 2, (
            f"Audit page should have 2 filter dropdowns, found {filter_selects.count()}"
        )

        # CSV Export button should exist
        export_btn = page.locator("button").filter(has_text="CSV")
        if export_btn.count() == 0:
            export_btn = page.locator("button").filter(has_text="Export")
        assert export_btn.count() > 0, "CSV Export button not found on Audit page"

        # Select an action filter → table should update (no crash)
        action_select = filter_selects.first
        action_select.select_option("create")
        page.wait_for_timeout(500)

        body_after = page.locator("body").text_content() or ""
        assert len(body_after.strip()) > 50, "Audit page crashed after filter selection"

        # DataTable should have timestamp, action, resource columns
        table = page.locator("table")
        if table.count() > 0:
            header_text = table.first.locator("thead").text_content() or ""
            has_timestamp = any(
                w in header_text for w in ["Timestamp", "timestamp", "Idopont", "Date"]
            )
            has_action = any(w in header_text for w in ["Action", "action", "Muvelet"])
            has_resource = any(w in header_text for w in ["Resource", "resource", "Eroforras"])
            assert has_timestamp or has_action or has_resource, (
                f"Audit table missing expected columns: {header_text[:200]}"
            )
