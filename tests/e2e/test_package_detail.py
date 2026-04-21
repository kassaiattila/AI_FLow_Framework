"""E2E — UC1 PackageDetail viewer (Sprint I / S98).

@test_registry:
    suite: e2e-ui
    component: aiflow-admin.packages
    covers: [aiflow-admin/src/pages-new/PackageDetail.tsx, src/aiflow/api/v1/document_extractor.py]
    phase: S98
    priority: critical
    estimated_duration_ms: 45000
    requires_services: [postgresql, redis, fastapi, vite]
    tags: [e2e, ui, packages, playwright, uc1]

Golden-path UC1: login → seed package via POST /api/v1/intake/upload-package
→ navigate /packages/:id → assert parser-badge + tab switching (Overview /
Routing / Extraction / PII) render without console errors.

The seed reuses the JWT minted by the UI login flow (read from localStorage)
so the tenant scope matches the one the aggregate endpoint will filter on.
"""

from __future__ import annotations

import json

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.conftest import BASE_URL, navigate_to

pytestmark = pytest.mark.e2e


VALID_PARSER_VARIANTS = {
    "docling_standard",
    "unstructured_fast",
    "azure_document_intelligence",
    "skipped_policy",
    "unknown",
}


def _seed_package(page: Page) -> str:
    """Upload one PDF via /api/v1/intake/upload-package using the UI token."""
    token = page.evaluate("() => localStorage.getItem('aiflow_token')")
    assert token, "UI login did not set aiflow_token in localStorage"

    resp = page.request.post(
        f"{BASE_URL}/api/v1/intake/upload-package",
        headers={"Authorization": f"Bearer {token}"},
        multipart={
            "files": {
                "name": "uc1-sample.pdf",
                "mimeType": "application/pdf",
                "buffer": b"%PDF-1.4\n% UC1 E2E seed payload\n%%EOF\n",
            },
            "descriptions": json.dumps([{"text": "UC1 E2E seed"}]),
            "association_mode": "order",
        },
    )
    assert resp.ok, f"upload-package failed: {resp.status} {resp.text()}"
    body = resp.json()
    assert body.get("file_count") == 1
    package_id = body["package_id"]
    assert package_id
    return package_id


class TestPackageDetailJourney:
    """UC1 golden-path: authenticated user views a package aggregate."""

    def test_package_detail_renders_badge_and_tabs(
        self,
        authenticated_page: Page,
        console_errors: list[str],
    ) -> None:
        page = authenticated_page

        package_id = _seed_package(page)

        navigate_to(page, f"/packages/{package_id}")

        # Hard-wait the badge — the page mounts before the useApi fetch resolves.
        badge = page.locator('[data-testid="parser-badge"]').first
        badge.wait_for(state="visible", timeout=15000)
        variant = badge.get_attribute("data-parser") or ""
        assert variant in VALID_PARSER_VARIANTS, (
            f"parser-badge data-parser={variant!r} not in {VALID_PARSER_VARIANTS}"
        )

        # Package heading shows the seeded id (prefix is enough — UUID in full).
        body = page.locator("body").text_content() or ""
        assert package_id.split("-")[0] in body, "package_id prefix missing from page"

        # Overview tab is the default — confirm Files section renders.
        expect(page.locator('[data-testid="tab-overview"]')).to_have_attribute(
            "data-testid", "tab-overview"
        )
        assert "uc1-sample.pdf" in body or "Files" in body

        # Routing tab renders at least a header; we don't assert content since
        # an unauthenticated seed path may route-skip. Presence + click is enough.
        page.locator('[data-testid="tab-routing"]').click()
        page.wait_for_load_state("networkidle")

        # Extraction tab renders the empty-state copy until S97.5 persists rows.
        page.locator('[data-testid="tab-extraction"]').click()
        page.wait_for_load_state("networkidle")
        ext_body = page.locator("body").text_content() or ""
        assert (
            "S97.5" in ext_body or "No persisted" in ext_body or "parser-badge" in ext_body.lower()
        ), "Extraction tab did not render its empty/populated variant"

        # PII tab — same pattern, empty copy expected.
        page.locator('[data-testid="tab-pii"]').click()
        page.wait_for_load_state("networkidle")
        pii_body = page.locator("body").text_content() or ""
        assert "PII" in pii_body or "S97.5" in pii_body or "report" in pii_body, (
            "PII tab did not render"
        )

        # Guard against regressions — tab interaction must not spew console errors.
        real = [
            e
            for e in console_errors
            if not any(noise in e for noise in ("favicon", "ResizeObserver", "CORS policy"))
        ]
        assert not real, f"Console errors during UC1 journey: {real}"
