"""
E2E test fixtures for AIFlow admin dashboard.

@test_registry:
    suite: e2e-ui
    component: aiflow-admin
    covers: [aiflow-admin/src/]
    phase: S9
    priority: critical
    estimated_duration_ms: 60000
    requires_services: [postgresql, redis, fastapi, vite]
    tags: [e2e, playwright, ui]
"""
from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

# AIFlow admin runs on Vite dev server with hash router
BASE_URL = "http://localhost:5174"
LOGIN_URL = f"{BASE_URL}/#/login"
AUTH_EMAIL = "admin@bestix.hu"
AUTH_PASSWORD = "admin"


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict) -> dict:
    """Override default browser context args."""
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 800},
        "ignore_https_errors": True,
    }


@pytest.fixture()
def authenticated_page(page: Page) -> Page:
    """Return a page that is already logged in to AIFlow admin."""
    page.goto(LOGIN_URL)
    page.wait_for_load_state("networkidle")

    # Fill login form
    page.fill('input#email', AUTH_EMAIL)
    page.fill('input#password', AUTH_PASSWORD)
    page.click('button[type="submit"]')

    # Wait for sidebar nav to appear (means login succeeded)
    page.locator("nav").wait_for(state="visible", timeout=15000)
    page.wait_for_load_state("networkidle")

    return page


@pytest.fixture()
def console_errors(page: Page) -> list[str]:
    """Collect JS console errors during test execution."""
    errors: list[str] = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    return errors


def navigate_to(page: Page, path: str) -> None:
    """Navigate to a hash route and wait for load."""
    page.goto(f"{BASE_URL}/#{path}")
    page.wait_for_load_state("networkidle")


def assert_no_console_errors(errors: list[str]) -> None:
    """Assert no JS console errors occurred (ignoring known benign ones)."""
    real_errors = [
        e for e in errors
        if not any(ignore in e for ignore in [
            "favicon.ico",
            "ResizeObserver",
            "Failed to fetch",  # API may not be running
        ])
    ]
    assert not real_errors, f"Console errors: {real_errors}"
