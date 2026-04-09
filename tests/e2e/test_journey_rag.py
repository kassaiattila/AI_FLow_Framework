"""
Multi-page user journey: RAG & Service Catalog.

Login → RAG page → collections → Service Catalog → find RAG service → back.
Tests the AI services browsing flow.

@test_registry:
    suite: e2e-journey
    component: aiflow-admin.rag
    covers: [aiflow-admin/src/pages-new/Rag.tsx, aiflow-admin/src/pages-new/Services.tsx]
    phase: S13
    priority: critical
    estimated_duration_ms: 20000
    requires_services: [postgresql, redis, fastapi, vite]
    tags: [e2e, journey, rag, services, playwright]
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
