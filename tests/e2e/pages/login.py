"""Login Page Object for AIFlow admin."""
from __future__ import annotations

from tests.e2e.pages.base import BasePage


class LoginPage(BasePage):
    path = "/login"

    def login(self, email: str = "admin@bestix.hu", password: str = "admin") -> None:
        self.navigate()
        self.page.fill("input#email", email)
        self.page.fill("input#password", password)
        self.page.click('button[type="submit"]')
        self.page.locator("nav").wait_for(state="visible", timeout=15000)
        self.page.wait_for_load_state("networkidle")

    def get_error_message(self) -> str | None:
        error = self.page.locator(".bg-red-50, .bg-red-900\\/20")
        if error.count() > 0:
            return error.first.text_content()
        return None

    def has_locale_toggle(self) -> bool:
        return self.page.locator("button:has-text('HU'), button:has-text('EN')").count() >= 2
