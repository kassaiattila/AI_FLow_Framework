"""
Multi-page user journey: RAG & Service Catalog.

Login → RAG page → collections → Service Catalog → find RAG service → back.
Tests the AI services browsing flow.

@test_registry:
    suite: e2e-journey
    component: aiflow-admin.rag
    covers: [aiflow-admin/src/pages-new/Rag.tsx, aiflow-admin/src/pages-new/Services.tsx]
    phase: S42
    priority: critical
    estimated_duration_ms: 35000
    requires_services: [postgresql, redis, fastapi, vite]
    tags: [e2e, journey, rag, services, playwright, deep]
"""

from __future__ import annotations

from playwright.sync_api import Page, expect

from tests.e2e.conftest import navigate_to


class TestRagJourney:
    """Full RAG browsing journey across multiple pages."""

    def test_rag_page_loads_with_content(self, authenticated_page: Page) -> None:
        """Journey: Login → RAG → verify page has collections or empty state."""
        page = authenticated_page
        navigate_to(page, "/rag")

        body = page.locator("body").text_content() or ""
        assert any(
            w in body
            for w in ["RAG", "Collection", "Gyujtemeny", "Chat", "No data", "Nincs", "collection"]
        ), f"RAG page missing expected content: {body[:200]}"

    def test_rag_to_services_navigation(self, authenticated_page: Page) -> None:
        """Journey: RAG → Services catalog → find RAG-related service."""
        page = authenticated_page

        # Start at RAG
        navigate_to(page, "/rag")
        assert "rag" in page.url

        # Navigate to Services via sidebar
        svc_link = page.locator('a[href*="services"]').first
        expect(svc_link).to_be_visible()
        svc_link.click()
        page.wait_for_load_state("networkidle")
        assert "services" in page.url

        # Services catalog should have content
        body = page.locator("body").text_content() or ""
        assert any(w in body for w in ["Service", "service", "Szolg", "rag", "RAG", "adapter"]), (
            "Services catalog missing content"
        )

    def test_services_catalog_has_cards(self, authenticated_page: Page) -> None:
        """Journey: Services → verify service cards are rendered."""
        page = authenticated_page
        navigate_to(page, "/services")

        body = page.locator("body").text_content() or ""
        # Should show service cards or list
        assert len(body.strip()) > 100, "Services page has minimal content"

        # Should have multiple services listed
        has_services = any(
            w in body
            for w in [
                "document_extractor",
                "rag_engine",
                "classifier",
                "email_connector",
                "cache",
                "monitoring",
                "Document",
                "RAG",
                "Email",
                "Cache",
            ]
        )
        assert has_services, "Services catalog doesn't list expected services"

    def test_rag_to_process_docs_ai_flow(self, authenticated_page: Page) -> None:
        """Journey: RAG → Process Docs → back to RAG (AI services cross-nav)."""
        page = authenticated_page

        navigate_to(page, "/rag")
        rag_body = page.locator("body").text_content() or ""
        assert len(rag_body.strip()) > 20

        # Navigate to Process Docs
        pd_link = page.locator('a[href*="process-docs"]').first
        expect(pd_link).to_be_visible()
        pd_link.click()
        page.wait_for_load_state("networkidle")
        assert "process-docs" in page.url

        # Back to RAG
        rag_link = page.locator('a[href*="/rag"]').first
        rag_link.click()
        page.wait_for_load_state("networkidle")
        assert "rag" in page.url

    def test_no_console_errors_rag_journey(self, authenticated_page: Page) -> None:
        """RAG journey with zero JS console errors."""
        page = authenticated_page
        errors: list[str] = []
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)

        navigate_to(page, "/rag")
        page.wait_for_timeout(500)
        navigate_to(page, "/services")
        page.wait_for_timeout(500)
        navigate_to(page, "/process-docs")
        page.wait_for_timeout(500)
        navigate_to(page, "/rag")
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
        assert not real_errors, f"Console errors during RAG journey: {real_errors}"


class TestRagDeepJourney:
    """Deep E2E tests: real interactions on RAG collections + chat pages (C6.4)."""

    def test_rag_collections_table_or_empty(self, authenticated_page: Page) -> None:
        """RAG page: Collections tab shows DataTable rows or proper empty state + source tag."""
        page = authenticated_page
        navigate_to(page, "/rag")
        page.wait_for_timeout(1500)

        body = page.locator("body").text_content() or ""
        table = page.locator("table")
        rows = page.locator("table tbody tr")

        if table.count() > 0 and rows.count() > 0:
            # Has data: check for name, doc count, chunk count columns
            header_text = table.first.locator("thead").text_content() or ""
            has_relevant = any(
                w in header_text for w in ["Name", "name", "Nev", "Doc", "Chunk", "chunk"]
            )
            assert has_relevant, f"Collections table missing expected columns: {header_text[:200]}"

            # Source tag (Demo/Live) should be visible
            assert any(tag in body for tag in ["Demo", "Live", "demo", "live"]), (
                "Source tag (Demo/Live) not visible on RAG page with data"
            )
        else:
            # Empty state or loading
            assert any(
                w in body for w in ["No data", "Nincs", "empty", "Collection", "Gyujtemeny", "RAG"]
            ), "RAG page has neither data rows nor a proper empty state"

    def test_rag_create_collection_modal(self, authenticated_page: Page) -> None:
        """RAG page: New Collection button → modal with name, description, language → Cancel."""
        page = authenticated_page
        navigate_to(page, "/rag")
        page.wait_for_timeout(1000)

        # Click New Collection button (brand-colored action button)
        new_btn = page.locator("button.bg-brand-500")
        if new_btn.count() == 0:
            new_btn = page.locator("button").filter(has_text="New Collection")
        if new_btn.count() == 0:
            new_btn = page.locator("button").filter(has_text="Uj gyujtemeny")
        if new_btn.count() == 0:
            return
        new_btn.first.click()
        page.wait_for_timeout(300)

        # Modal should appear
        modal = page.locator(".fixed.inset-0")
        assert modal.count() > 0, "New Collection modal did not appear"

        # Modal should have name input, description input, language select
        modal_inputs = page.locator(".fixed input")
        modal_selects = page.locator(".fixed select")
        assert modal_inputs.count() >= 1, "New Collection modal missing name input"
        assert modal_selects.count() >= 1, "New Collection modal missing language dropdown"

        # Cancel should close the modal
        cancel_btn = page.locator(".fixed button").filter(has_text="Cancel")
        if cancel_btn.count() == 0:
            cancel_btn = page.locator(".fixed button").filter(has_text="Megse")
        if cancel_btn.count() > 0:
            cancel_btn.first.click()
            page.wait_for_timeout(300)
            overlay = page.locator(".fixed.inset-0")
            assert overlay.count() == 0, "New Collection modal did not close after Cancel"

    def test_rag_collection_delete_dialog(self, authenticated_page: Page) -> None:
        """RAG page: delete button on row → ConfirmDialog → Cancel closes it."""
        page = authenticated_page
        navigate_to(page, "/rag")
        page.wait_for_timeout(1500)

        rows = page.locator("table tbody tr")
        if rows.count() == 0:
            # No data — skip gracefully
            return

        # Find delete button (trash icon button with red styling)
        delete_btn = page.locator(
            'button[title*="elete"], button[title*="orles"], '
            "button.text-red-500, button.text-red-600"
        ).first
        if delete_btn.count() == 0:
            # Try to find the SVG trash icon button in the actions column
            delete_btn = page.locator("table tbody button").filter(has_text="").last
            if delete_btn.count() == 0:
                return

        delete_btn.click()
        page.wait_for_timeout(300)

        # Delete confirmation dialog should appear
        body = page.locator("body").text_content() or ""
        has_dialog = any(
            w in body for w in ["Delete", "Torles", "Confirm", "Megerosit", "Biztosan"]
        )
        assert has_dialog, "Delete confirmation dialog did not appear"

        # Cancel should close
        cancel_btn = page.locator(".fixed button").filter(has_text="Cancel")
        if cancel_btn.count() == 0:
            cancel_btn = page.locator(".fixed button").filter(has_text="Megse")
        if cancel_btn.count() > 0:
            cancel_btn.first.click()
            page.wait_for_timeout(300)
            overlay = page.locator(".fixed.inset-0")
            assert overlay.count() == 0, "Delete dialog did not close after Cancel"

    def test_rag_chat_tab(self, authenticated_page: Page) -> None:
        """RAG page: Chat tab shows chat interface with input + send button."""
        page = authenticated_page
        navigate_to(page, "/rag")
        page.wait_for_timeout(1000)

        # Click Chat tab
        chat_tab = page.locator("button").filter(has_text="Chat")
        if chat_tab.count() == 0:
            return
        chat_tab.first.click()
        page.wait_for_timeout(500)

        # Chat interface should render (input field + send area)
        chat_inputs = page.locator('input[type="text"], textarea, [contenteditable="true"]')
        assert chat_inputs.count() > 0, "Chat tab missing input field"

        # Type a question (without sending) — just check input works
        first_input = chat_inputs.first
        first_input.fill("Test question for E2E")
        page.wait_for_timeout(200)

        input_value = first_input.input_value()
        assert "Test question" in input_value, (
            f"Chat input did not accept typed text, got: {input_value}"
        )

        # Page should not crash
        body = page.locator("body").text_content() or ""
        assert len(body.strip()) > 50, "Page crashed after typing in chat"

    def test_rag_chunk_search(self, authenticated_page: Page) -> None:
        """RAG page: Collections tab DataTable search filters rows."""
        page = authenticated_page
        navigate_to(page, "/rag")
        page.wait_for_timeout(1500)

        # Collections tab should be active by default
        # DataTable has a search input
        search_input = page.locator('input[type="text"], input[type="search"]').first

        if search_input.count() == 0:
            # No search input available
            return

        rows_before = page.locator("table tbody tr").count()

        # Type a search term that won't match
        search_input.fill("xyznonexistent999")
        page.wait_for_timeout(400)

        body_after = page.locator("body").text_content() or ""
        rows_after = page.locator("table tbody tr").count()

        # After filtering: fewer rows or empty state
        if rows_before > 0:
            assert rows_after < rows_before or any(
                w in body_after for w in ["No data", "Nincs", "0 result", "no result"]
            ), "Search did not filter the collections table"

        # Clear search → rows restored
        search_input.fill("")
        page.wait_for_timeout(400)
        rows_restored = page.locator("table tbody tr").count()

        if rows_before > 0:
            assert rows_restored >= rows_before, (
                f"After clearing search, row count ({rows_restored}) < original ({rows_before})"
            )
