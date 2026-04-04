"""Dashboard Page Object for AIFlow admin."""
from __future__ import annotations

from tests.e2e.pages.base import BasePage


class DashboardPage(BasePage):
    path = "/"

    def get_kpi_count(self) -> int:
        """Count the number of KPI cards on the dashboard."""
        return self.page.locator('[class*="rounded-lg"][class*="border"]').count()

    def has_skills_section(self) -> bool:
        body = self.page.locator("body").text_content() or ""
        return any(s in body for s in ["Skills", "Skill", "process_documentation", "aszf_rag_chat"])

    def has_active_pipelines(self) -> bool:
        body = self.page.locator("body").text_content() or ""
        return "Pipeline" in body or "pipeline" in body
