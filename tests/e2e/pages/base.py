"""Base Page Object for AIFlow admin E2E tests."""

from __future__ import annotations

import os

from playwright.sync_api import Page

BASE_URL = os.getenv("AIFLOW_UI_BASE_URL", "http://localhost:5173")


class BasePage:
    """Base class for all page objects. Hash router: /#/path."""

    path: str = "/"

    def __init__(self, page: Page) -> None:
        self.page = page

    @property
    def url(self) -> str:
        return f"{BASE_URL}/#{self.path}"

    def navigate(self) -> None:
        self.page.goto(self.url)
        self.wait_loaded()

    def wait_loaded(self) -> None:
        self.page.wait_for_load_state("networkidle")

    def screenshot(self, name: str) -> bytes:
        return self.page.screenshot(path=f"tests/artifacts/e2e/{name}.png")

    def get_title(self) -> str:
        """Get the page title from the PageLayout h1."""
        h1 = self.page.locator("h1").first
        return h1.text_content() or ""

    def has_sidebar(self) -> bool:
        return self.page.locator("nav").count() > 0

    def get_console_errors(self) -> list[str]:
        errors: list[str] = []
        self.page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        return errors

    def check_no_crash(self) -> None:
        """Verify page did not render a blank screen or crash."""
        body_text = self.page.locator("body").text_content() or ""
        assert len(body_text.strip()) > 0, f"Page {self.path} rendered empty body"
