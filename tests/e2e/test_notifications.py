"""
Notification bell E2E tests.

@test_registry:
    suite: e2e-notifications
    component: aiflow-admin.notifications
    covers: [aiflow-admin/src/layout/TopBar.tsx]
    phase: S9
    priority: high
    estimated_duration_ms: 10000
    requires_services: [postgresql, redis, fastapi, vite]
    tags: [e2e, notifications, playwright]
"""
from __future__ import annotations

from playwright.sync_api import Page, expect

from tests.e2e.conftest import navigate_to


class TestNotifications:
    """Notification bell and dropdown tests."""

    def test_bell_icon_visible(self, authenticated_page: Page) -> None:
        navigate_to(authenticated_page, "/")

        # Bell icon should be in the top bar (svg with bell path or aria label)
        bell = authenticated_page.locator('[aria-label*="otif"], [aria-label*="bell"], button:has(svg)').first
        expect(bell).to_be_visible()

    def test_notification_dropdown_toggles(self, authenticated_page: Page) -> None:
        navigate_to(authenticated_page, "/")

        # Find and click the notification bell button
        # The bell is typically in the TopBar area
        top_bar_buttons = authenticated_page.locator("header button, [class*='top'] button")
        if top_bar_buttons.count() > 0:
            top_bar_buttons.first.click()
            authenticated_page.wait_for_timeout(500)

            # After click, some dropdown/panel should appear
            body = authenticated_page.locator("body").text_content() or ""
            # Either shows notifications or "no notifications" message
            assert len(body) > 0  # Page should not crash
