"""Per-tenant budget service — Sprint N / S121.

Persists spending limits in ``tenant_budgets`` (Alembic 045) and exposes a
read-side helper that subtracts the tenant's running cost (as computed by
``CostAttributionRepository.aggregate_running_cost``) from the configured
limit. Pre-flight guardrail enforcement lands in S122 and consumes the
:class:`BudgetView` payload produced here.
"""

from __future__ import annotations

from aiflow.services.tenant_budgets.contracts import (
    BUDGET_PERIOD_DAILY,
    BUDGET_PERIOD_MONTHLY,
    BudgetPeriod,
    BudgetView,
    TenantBudget,
)
from aiflow.services.tenant_budgets.service import TenantBudgetService

__all__ = [
    "BUDGET_PERIOD_DAILY",
    "BUDGET_PERIOD_MONTHLY",
    "BudgetPeriod",
    "BudgetView",
    "TenantBudget",
    "TenantBudgetService",
]
