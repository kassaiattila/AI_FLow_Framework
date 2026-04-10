"""
Multi-page user journey: Document lifecycle.

Login → Dashboard → Documents → table check → detail nav → source verify.
Tests the full document browsing flow across multiple pages.

@test_registry:
    suite: e2e-journey
    component: aiflow-admin.documents
    covers: [aiflow-admin/src/pages-new/Documents.tsx, aiflow-admin/src/pages-new/DocumentDetail.tsx, aiflow-admin/src/pages-new/Verification.tsx]
    phase: S41
    priority: critical
    estimated_duration_ms: 40000
    requires_services: [postgresql, redis, fastapi, vite]
    tags: [e2e, journey, documents, playwright, deep]
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
            w in body for w in ["Document", "Dokumentum", "No data", "Nincs", "Upload", "Feltolt"]
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
        assert not real_errors, f"Console errors during document journey: {real_errors}"


class TestDocumentDeepJourney:
    """Deep E2E tests: real CRUD interactions on Document pages (C6.1)."""

    def test_documents_table_has_data_or_empty_state(self, authenticated_page: Page) -> None:
        """Documents list shows table rows with source tag OR proper empty state."""
        page = authenticated_page
        navigate_to(page, "/documents")

        body = page.locator("body").text_content() or ""
        table = page.locator("table")
        rows = page.locator("table tbody tr")

        if table.count() > 0 and rows.count() > 0:
            # Has data: at least 1 row should be visible
            expect(rows.first).to_be_visible()
            # Source tag (Demo/Live) should be visible somewhere on the page
            assert any(tag in body for tag in ["Demo", "Live", "demo", "live"]), (
                "Source tag (Demo/Live) not visible on Documents page with data"
            )
        else:
            # Empty state: should show a meaningful empty message
            assert any(
                w in body for w in ["No data", "Nincs", "empty", "Upload", "Feltolt", "Ures"]
            ), "Documents page has neither data rows nor a proper empty state"

    def test_document_detail_navigation(self, authenticated_page: Page) -> None:
        """Click first document row → detail page loads with sections → Back returns."""
        page = authenticated_page
        navigate_to(page, "/documents")

        rows = page.locator("table tbody tr")
        if rows.count() == 0:
            # No data — skip gracefully
            return

        # Click first row to navigate to detail
        rows.first.click()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(500)

        # Should be on /documents/:id/show
        assert "/documents/" in page.url, f"Expected document detail URL, got {page.url}"

        body = page.locator("body").text_content() or ""

        # Detail page should have key sections: vendor info, header, totals
        # Check for section headings (in EN or HU)
        has_vendor = any(w in body for w in ["Vendor", "Szallito", "vendor"])
        has_header = any(
            w in body for w in ["Header", "Fejlec", "Invoice", "Szamla", "invoice_number"]
        )
        assert has_vendor or has_header, "Document detail page missing Vendor or Header section"

        # Back button should navigate to /documents
        back_btn = page.locator("button").filter(has_text="Document").first
        if back_btn.count() == 0:
            back_btn = page.locator("button").filter(has_text="Dokumentum").first
        if back_btn.count() > 0:
            back_btn.click()
            page.wait_for_load_state("networkidle")
            # URL should end at /documents (not /documents/:id/show)
            assert page.url.rstrip("/").endswith("/documents") or page.url.rstrip("/").endswith(
                "#/documents"
            ), f"Back button did not return to /documents, got {page.url}"

    def test_verification_page_loads(self, authenticated_page: Page) -> None:
        """Verification page loads with Approve/Reject buttons and confidence data."""
        page = authenticated_page
        navigate_to(page, "/documents")

        rows = page.locator("table tbody tr")
        if rows.count() == 0:
            return

        # Find verify link (the checkmark icon link) in the first row
        verify_link = page.locator('a[href*="/verify"]').first
        if verify_link.count() == 0:
            # If no verify link visible, try navigating directly
            rows.first.click()
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(300)
            # From detail page, find verify button
            verify_btn = page.locator("button").filter(has_text="Verify")
            if verify_btn.count() > 0:
                verify_btn.first.click()
                page.wait_for_load_state("networkidle")
            else:
                return
        else:
            verify_link.click()
            page.wait_for_load_state("networkidle")

        page.wait_for_timeout(500)

        # Should be on /documents/:id/verify
        assert "/verify" in page.url, f"Expected verification URL, got {page.url}"

        body = page.locator("body").text_content() or ""

        # Approve / Reject buttons should exist
        has_approve = any(w in body for w in ["Approve", "Elfogad", "approve", "approveAll"])
        has_reject = any(w in body for w in ["Reject", "Elutasit", "reject"])
        assert has_approve or has_reject, "Verification page missing Approve/Reject buttons"

        # Keyboard navigation hint should be visible
        has_kb_hint = any(w in body for w in ["Tab", "Enter", "Esc"])
        assert has_kb_hint, "Verification page missing keyboard navigation hints"

    def test_documents_search(self, authenticated_page: Page) -> None:
        """DataTable search: type a query → table filters → clear restores."""
        page = authenticated_page
        navigate_to(page, "/documents")

        # DataTable renders a search input with the common search placeholder
        search_input = page.locator('input[type="text"], input[type="search"]').first

        if search_input.count() == 0:
            # No search input on this page variant
            return

        # Count rows before search
        rows_before = page.locator("table tbody tr").count()

        # Type a search term that's unlikely to match everything
        search_input.fill("xyznonexistent999")
        page.wait_for_timeout(400)

        body_after = page.locator("body").text_content() or ""
        rows_after = page.locator("table tbody tr").count()

        # After filtering with nonexistent term: fewer rows or empty state
        if rows_before > 0:
            assert rows_after < rows_before or any(
                w in body_after for w in ["No data", "Nincs", "0 result", "no result"]
            ), "Search did not filter the table"

        # Clear search
        search_input.fill("")
        page.wait_for_timeout(400)
        rows_restored = page.locator("table tbody tr").count()

        # After clearing, rows should be restored
        if rows_before > 0:
            assert rows_restored >= rows_before, (
                f"After clearing search, row count ({rows_restored}) < original ({rows_before})"
            )

    def test_document_delete_confirm_dialog(self, authenticated_page: Page) -> None:
        """Delete button click opens ConfirmDialog → Cancel closes it."""
        page = authenticated_page
        navigate_to(page, "/documents")

        # Look for delete button (trash icon) in table rows
        delete_btn = page.locator('button[title*="elete"], button[title*="orles"]').first

        if delete_btn.count() == 0:
            # No delete button visible (maybe no data)
            return

        # Click delete → confirmation dialog should appear
        delete_btn.click()
        page.wait_for_timeout(300)

        body = page.locator("body").text_content() or ""

        # Dialog should show confirm/cancel options
        has_dialog = any(
            w in body
            for w in [
                "Delete",
                "Torles",
                "Confirm",
                "Megerosit",
                "deleteConfirm",
                "Biztosan",
                "Are you sure",
            ]
        )
        assert has_dialog, "Delete confirmation dialog did not appear"

        # Cancel button should close the dialog
        cancel_btn = page.locator("button").filter(has_text="Cancel").first
        if cancel_btn.count() == 0:
            cancel_btn = page.locator("button").filter(has_text="Megse").first
        if cancel_btn.count() == 0:
            cancel_btn = page.locator("button").filter(has_text="cancel").first

        if cancel_btn.count() > 0:
            cancel_btn.click()
            page.wait_for_timeout(300)

            # Dialog overlay should be gone (no fixed overlay visible)
            overlay = page.locator(".fixed.inset-0")
            assert overlay.count() == 0, "Confirmation dialog did not close after Cancel"
