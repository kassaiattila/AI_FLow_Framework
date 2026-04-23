"""E2E — Admin UI Budget Management (Sprint N / S123).

@test_registry:
    suite: e2e-ui
    component: aiflow-admin.budget-management + api.v1.tenant_budgets
    covers:
        - aiflow-admin/src/pages-new/BudgetManagement/index.tsx
        - aiflow-admin/src/pages-new/BudgetManagement/BudgetCard.tsx
        - aiflow-admin/src/pages-new/BudgetManagement/ThresholdEditor.tsx
        - src/aiflow/api/v1/tenant_budgets.py
    phase: sprint-n-s123
    priority: critical
    estimated_duration_ms: 40000
    requires_services: [postgresql, redis, fastapi, vite]
    tags: [e2e, ui, budgets, playwright, sprint-n, v1.4.10]

Golden-path for the per-tenant cost-budget dashboard:

1. Seed a budget row via PUT /api/v1/tenants/{id}/budget/{period} using the
   JWT minted by the UI login flow (same pattern as test_package_detail.py).
2. Load /#/budget-management?tenant=<id> and assert the live ``BudgetView``
   (used / limit / remaining / thresholds) renders with real backend numbers.
3. Mutate the daily threshold set + Save and assert the change round-trips
   after a hard reload (regression guard against optimistic-UI-only updates).
"""

from __future__ import annotations

import time

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.conftest import BASE_URL

pytestmark = pytest.mark.e2e


TENANT_ID = f"s123-budget-{int(time.time())}"


def _token(page: Page) -> str:
    value = page.evaluate("() => localStorage.getItem('aiflow_token')")
    assert value, "UI login did not set aiflow_token in localStorage"
    return str(value)


def _seed_budget(
    page: Page,
    tenant_id: str,
    period: str,
    *,
    limit_usd: float,
    alert_threshold_pct: list[int],
    enabled: bool = True,
) -> None:
    token = _token(page)
    resp = page.request.put(
        f"{BASE_URL}/api/v1/tenants/{tenant_id}/budget/{period}",
        headers={"Authorization": f"Bearer {token}"},
        data={
            "limit_usd": limit_usd,
            "alert_threshold_pct": alert_threshold_pct,
            "enabled": enabled,
        },
    )
    assert resp.ok, f"seed PUT failed: {resp.status} {resp.text()}"


def _cleanup_budget(page: Page, tenant_id: str, period: str) -> None:
    token = _token(page)
    page.request.delete(
        f"{BASE_URL}/api/v1/tenants/{tenant_id}/budget/{period}",
        headers={"Authorization": f"Bearer {token}"},
    )


class TestBudgetManagementJourney:
    """S123 golden-path: operator reads and edits a tenant budget."""

    def test_budget_dashboard_renders_live_view(
        self,
        authenticated_page: Page,
        console_errors: list[str],
    ) -> None:
        page = authenticated_page
        tenant_id = f"{TENANT_ID}-render"
        try:
            _seed_budget(
                page,
                tenant_id,
                "daily",
                limit_usd=12.5,
                alert_threshold_pct=[50, 80, 95],
            )

            page.goto(f"{BASE_URL}/#/budget-management?tenant={tenant_id}")
            page.wait_for_load_state("networkidle")

            cards = page.locator('[data-testid="budget-cards"]')
            cards.wait_for(state="visible", timeout=15000)
            assert cards.get_attribute("data-tenant") == tenant_id

            daily = page.locator('[data-testid="budget-card-daily"]')
            expect(daily).to_be_visible()
            expect(daily).to_have_attribute("data-period", "daily")
            expect(daily).to_have_attribute("data-tenant", tenant_id)

            # Live projection surfaces the seeded numbers (used may be $0 in a
            # clean test DB — we assert the limit and the thresholds chips only,
            # which are the signals the UI OWNS rather than an aggregate read).
            limit_input = page.locator('[data-testid="budget-limit-daily"]')
            expect(limit_input).to_have_value("12.5")

            for pct in (50, 80, 95):
                expect(
                    page.locator(f'[data-testid="budget-thresholds-daily-chip-{pct}"]')
                ).to_be_visible()

            # Monthly card renders as empty state (no seed).
            expect(page.locator('[data-testid="budget-empty-monthly"]')).to_be_visible()

            assert console_errors == [], f"Console errors: {console_errors}"
        finally:
            _cleanup_budget(page, tenant_id, "daily")

    def test_edit_thresholds_persists_after_reload(
        self,
        authenticated_page: Page,
        console_errors: list[str],
    ) -> None:
        page = authenticated_page
        tenant_id = f"{TENANT_ID}-edit"
        try:
            _seed_budget(
                page,
                tenant_id,
                "daily",
                limit_usd=7.0,
                alert_threshold_pct=[50, 95],
            )

            page.goto(f"{BASE_URL}/#/budget-management?tenant={tenant_id}")
            page.wait_for_load_state("networkidle")
            page.locator('[data-testid="budget-card-daily"]').wait_for(
                state="visible", timeout=15000
            )

            # Remove 95, add 75 + 80.
            page.locator('[data-testid="budget-thresholds-daily-remove-95"]').click()
            threshold_input = page.locator('[data-testid="budget-thresholds-daily-input"]')
            threshold_input.fill("75")
            threshold_input.press("Enter")
            threshold_input.fill("80")
            threshold_input.press("Enter")

            # Save must become enabled after the diff.
            save = page.locator('[data-testid="budget-save-daily"]')
            expect(save).to_be_enabled()
            save.click()
            # Wait for the PUT round-trip to settle (save button re-disables
            # once the BudgetCard refreshes its baseline from the server).
            expect(save).to_be_disabled(timeout=10000)

            # Hard reload — regression guard: no optimistic-only state.
            page.goto(f"{BASE_URL}/#/budget-management?tenant={tenant_id}")
            page.wait_for_load_state("networkidle")
            page.locator('[data-testid="budget-card-daily"]').wait_for(
                state="visible", timeout=15000
            )

            for pct in (50, 75, 80):
                expect(
                    page.locator(f'[data-testid="budget-thresholds-daily-chip-{pct}"]')
                ).to_be_visible()
            expect(page.locator('[data-testid="budget-thresholds-daily-chip-95"]')).to_have_count(0)

            assert console_errors == [], f"Console errors: {console_errors}"
        finally:
            _cleanup_budget(page, tenant_id, "daily")
