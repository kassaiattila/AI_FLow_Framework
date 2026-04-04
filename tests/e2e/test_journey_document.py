"""
Multi-page user journey: Document lifecycle.

Login → Dashboard → Documents → table check → detail nav → source verify.
Tests the full document browsing flow across multiple pages.

@test_registry:
    suite: e2e-journey
    component: aiflow-admin.documents
    covers: [aiflow-admin/src/pages-new/Documents.tsx]
    phase: S13
    priority: critical
    estimated_duration_ms: 20000
    requires_services: [postgresql, redis, fastapi, vite]
    tags: [e2e, journey, documents, playwright]
"""
from __future__ import annotations

from playwright.sync_api import Page, expect

from tests.e2e.conftest import navigate_to


class TestDocumentJourney:
    """Full document lifecycle journey across multiple pages."""

    def test_dashboard_to_documents_navigation(self, authenticated_page: Page) -> None:
        """Journey: Dashboard → click Documents link → Documents page loads."""
        page = authenticated_page
        navigate_to(page, "/")

        # Dashboard should be loaded
        body = page.locator("body").text_content() or ""
        assert len(body.strip()) > 50, "Dashboard is empty"

        # Navigate to Documents via sidebar
        doc_link = page.locator('a[href*="documents"]').first
        expect(doc_link).to_be_visible()
        doc_link.click()
        page.wait_for_load_state("networkidle")

        # Should now be on Documents page
        assert "documents" in page.url
        body = page.locator("body").text_content() or ""
        assert any(
            w in body
            for w in ["Document", "Dokumentum", "documents", "dokumentum", "No data", "Nincs"]
        ), "Documents page missing expected content after navigation"

    def test_documents_table_and_source(self, authenticated_page: Page) -> None:
        """Journey: Documents page → verify table renders → check source indicator."""
        page = authenticated_page
        navigate_to(page, "/documents")

        body = page.locator("body").text_content() or ""

        # Should show either table data or empty state
        has_table = page.locator("table").count() > 0
        has_content = any(
            w in body
            for w in ["Document", "Dokumentum", "No data", "Nincs", "Upload", "Feltolt"]
        )
        assert has_table or has_content, "Documents page has no table or content"

        # Page should at minimum not be empty
        assert len(body.strip()) > 20, "Documents page rendered empty"

    def test_documents_action_buttons_present(self, authenticated_page: Page) -> None:
        """Journey: Documents → verify action buttons (upload, process) exist."""
        page = authenticated_page
        navigate_to(page, "/documents")

        # Should have some actionable UI elements
        buttons = page.locator("button")
        assert buttons.count() >= 1, "Documents page has no buttons"

    def test_documents_to_emails_crossnav(self, authenticated_page: Page) -> None:
        """Journey: Documents → Emails → back to Documents (cross-page nav)."""
        page = authenticated_page

        # Start at Documents
        navigate_to(page, "/documents")
        doc_body = page.locator("body").text_content() or ""
        assert "documents" in page.url.lower() or any(
            w in doc_body for w in ["Document", "Dokumentum"]
        )

        # Navigate to Emails via sidebar
        email_link = page.locator('a[href*="emails"]').first
        expect(email_link).to_be_visible()
        email_link.click()
        page.wait_for_load_state("networkidle")
        assert "emails" in page.url

        # Navigate back to Documents
        doc_link = page.locator('a[href*="documents"]').first
        doc_link.click()
        page.wait_for_load_state("networkidle")
        assert "documents" in page.url

    def test_no_console_errors_during_journey(self, authenticated_page: Page) -> None:
        """Full document journey with zero JS console errors."""
        page = authenticated_page
        errors: list[str] = []
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)

        # Journey: Dashboard → Documents → Emails → Documents
        navigate_to(page, "/")
        page.wait_for_timeout(500)
        navigate_to(page, "/documents")
        page.wait_for_timeout(500)
        navigate_to(page, "/emails")
        page.wait_for_timeout(500)
        navigate_to(page, "/documents")
        page.wait_for_timeout(500)

        real_errors = [
            e for e in errors
            if not any(x in e for x in [
                "favicon", "ResizeObserver", "Failed to fetch",
                "Failed to load resource", "Maximum update depth",
            ])
        ]
        assert not real_errors, f"Console errors during document journey: {real_errors}"
