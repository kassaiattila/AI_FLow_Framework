"""
Smoke tests — verify every page loads without crash or JS errors.

@test_registry:
    suite: e2e-smoke
    component: aiflow-admin
    covers: [aiflow-admin/src/pages-new/]
    phase: S9
    priority: critical
    estimated_duration_ms: 30000
    requires_services: [postgresql, redis, fastapi, vite]
    tags: [e2e, smoke, playwright]
"""
from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.conftest import BASE_URL, navigate_to

# All authenticated routes to test (hash router paths)
PAGES = [
    ("/", "Dashboard"),
    ("/runs", "Runs"),
    ("/costs", "Costs"),
    ("/monitoring", "Monitoring"),
    ("/quality", "Quality"),
    ("/documents", "Documents"),
    ("/emails", "Emails"),
    ("/rag", "RAG"),
    ("/process-docs", "ProcessDocs"),
    ("/media", "Media"),
    ("/rpa", "RPA"),
    ("/reviews", "Reviews"),
    ("/cubix", "Cubix"),
    ("/services", "Services"),
    ("/pipelines", "Pipelines"),
    ("/audit", "Audit"),
    ("/admin", "Admin"),
]


class TestLogin:
    """Login page tests."""

    def test_login_page_renders(self, page: Page) -> None:
        page.goto(f"{BASE_URL}/#/login")
        page.wait_for_load_state("networkidle")

        # Should show AIFlow branding
        expect(page.locator("h1")).to_contain_text("AI")
        # Should have email and password inputs
        expect(page.locator("input#email")).to_be_visible()
        expect(page.locator("input#password")).to_be_visible()
        # Should have submit button
        expect(page.locator('button[type="submit"]')).to_be_visible()

    def test_login_has_locale_toggle(self, page: Page) -> None:
        page.goto(f"{BASE_URL}/#/login")
        page.wait_for_load_state("networkidle")

        hu = page.locator("button", has_text="Magyar")
        en = page.locator("button", has_text="English")
        expect(hu).to_be_visible()
        expect(en).to_be_visible()

    def test_login_success(self, page: Page) -> None:
        page.goto(f"{BASE_URL}/#/login")
        page.wait_for_load_state("networkidle")

        page.fill("input#email", "admin@bestix.hu")
        page.fill("input#password", "admin")
        page.click('button[type="submit"]')

        # Wait for sidebar nav to appear (means we're past login)
        page.locator("nav").wait_for(state="visible", timeout=15000)
        expect(page.locator("nav")).to_be_visible()

    def test_unauthenticated_redirect(self, page: Page) -> None:
        """Unauthenticated user should be redirected to login."""
        page.goto(f"{BASE_URL}/#/documents")
        page.wait_for_load_state("networkidle")

        # Should end up at login
        assert "/login" in page.url


class TestSmokeAllPages:
    """Smoke test: every page loads, has content, no blank screen."""

    @pytest.mark.parametrize("path,name", PAGES)
    def test_page_loads(self, authenticated_page: Page, path: str, name: str) -> None:
        navigate_to(authenticated_page, path)

        # Page should not be blank
        body = authenticated_page.locator("body").text_content() or ""
        assert len(body.strip()) > 50, f"{name} ({path}) rendered near-empty body"

        # Sidebar should be present (we're in AppShell)
        assert authenticated_page.locator("nav").count() > 0, f"{name} missing sidebar"

    @pytest.mark.parametrize("path,name", PAGES)
    def test_no_js_errors(self, authenticated_page: Page, path: str, name: str) -> None:
        errors: list[str] = []
        authenticated_page.on(
            "console",
            lambda msg: errors.append(msg.text) if msg.type == "error" else None,
        )

        navigate_to(authenticated_page, path)

        # Filter benign errors
        real_errors = [
            e for e in errors
            if not any(x in e for x in ["favicon", "ResizeObserver", "Failed to fetch"])
        ]
        assert not real_errors, f"{name} ({path}) JS errors: {real_errors}"


class TestSidebar:
    """Test sidebar navigation and structure."""

    def test_sidebar_has_menu_groups(self, authenticated_page: Page) -> None:
        navigate_to(authenticated_page, "/")

        nav = authenticated_page.locator("nav")
        expect(nav).to_be_visible()

        # Should have clickable menu items
        links = nav.locator("a")
        assert links.count() >= 10, f"Sidebar has only {links.count()} links, expected 10+"

    def test_sidebar_navigation(self, authenticated_page: Page) -> None:
        navigate_to(authenticated_page, "/")

        # Click Documents link in sidebar
        authenticated_page.locator('a[href*="documents"]').first.click()
        authenticated_page.wait_for_load_state("networkidle")

        assert "documents" in authenticated_page.url
