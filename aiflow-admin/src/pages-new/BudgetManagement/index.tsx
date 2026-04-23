/**
 * BudgetManagement — per-tenant LLM cost budget admin dashboard.
 * Sprint N / S123. Consumes the S121 endpoints
 * ``GET/PUT /api/v1/tenants/{tenant_id}/budget[/{period}]``.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { PageLayout } from "../../layout/PageLayout";
import { ErrorState } from "../../components-new/ErrorState";
import { LoadingState } from "../../components-new/LoadingState";
import { ApiClientError, fetchApi } from "../../lib/api-client";
import { BudgetCard } from "./BudgetCard";
import { BUDGET_PERIODS, type BudgetPeriod, type TenantBudgetGetResponse } from "./types";

const TENANT_RE = /^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}$/;

type BudgetsByPeriod = Record<BudgetPeriod, TenantBudgetGetResponse | null>;

function emptyBudgets(): BudgetsByPeriod {
  return { daily: null, monthly: null };
}

function mergeBudgets(list: TenantBudgetGetResponse[]): BudgetsByPeriod {
  const next = emptyBudgets();
  for (const entry of list) {
    next[entry.budget.period] = entry;
  }
  return next;
}

export function BudgetManagement() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const tenantParam = searchParams.get("tenant") ?? "";
  const [tenantDraft, setTenantDraft] = useState(tenantParam);
  const [activeTenant, setActiveTenant] = useState(tenantParam);
  const [budgets, setBudgets] = useState<BudgetsByPeriod>(emptyBudgets());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setActiveTenant(tenantParam);
    setTenantDraft(tenantParam);
  }, [tenantParam]);

  const draftValid = useMemo(() => TENANT_RE.test(tenantDraft), [tenantDraft]);

  const refetch = useCallback(async () => {
    if (!activeTenant) {
      setBudgets(emptyBudgets());
      setError(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const list = await fetchApi<TenantBudgetGetResponse[]>(
        "GET",
        `/api/v1/tenants/${encodeURIComponent(activeTenant)}/budget`,
      );
      setBudgets(mergeBudgets(Array.isArray(list) ? list : []));
    } catch (e) {
      if (e instanceof ApiClientError) {
        setError(`${e.status}: ${typeof e.detail === "string" ? e.detail : JSON.stringify(e.detail)}`);
      } else {
        setError(e instanceof Error ? e.message : "Fetch failed");
      }
      setBudgets(emptyBudgets());
    } finally {
      setLoading(false);
    }
  }, [activeTenant]);

  useEffect(() => {
    void refetch();
  }, [refetch]);

  const handleLoad = () => {
    if (!draftValid) return;
    setSearchParams({ tenant: tenantDraft }, { replace: false });
    navigate(`/budget-management?tenant=${encodeURIComponent(tenantDraft)}`);
  };

  const handleSaved = (entry: TenantBudgetGetResponse) => {
    setBudgets((prev) => ({ ...prev, [entry.budget.period]: entry }));
  };

  return (
    <PageLayout
      titleKey="aiflow.budgets.title"
      subtitleKey="aiflow.budgets.subtitle"
      source="live"
    >
      <div
        data-testid="budget-tenant-selector"
        className="mb-4 rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900"
      >
        <label className="block text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
          Tenant
        </label>
        <div className="mt-2 flex items-center gap-2">
          <input
            type="text"
            value={tenantDraft}
            onChange={(event) => setTenantDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") handleLoad();
            }}
            placeholder="tenant_id (pl: default, acme, partner1)"
            data-testid="budget-tenant-input"
            className="flex-1 rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-900 focus:border-brand-500 focus:outline-none dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100"
          />
          <button
            type="button"
            onClick={handleLoad}
            disabled={!draftValid}
            data-testid="budget-tenant-load"
            className="rounded-lg bg-brand-500 px-4 py-1.5 text-sm font-semibold text-white hover:bg-brand-600 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Betoltes
          </button>
        </div>
        {tenantDraft && !draftValid && (
          <p className="mt-2 text-xs text-red-600 dark:text-red-400">
            Ervenytelen tenant_id: csak a-z A-Z 0-9 _ . - karaktereket tartalmazhat.
          </p>
        )}
      </div>

      {!activeTenant && (
        <div
          data-testid="budget-hint"
          className="rounded-xl border border-dashed border-gray-300 bg-gray-50 p-6 text-center text-sm text-gray-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-400"
        >
          Valassz tenant-et a felul talalhato mezoben a koltsegvetes kezelesehez.
        </div>
      )}

      {activeTenant && loading && <LoadingState />}
      {activeTenant && error && <ErrorState error={error} onRetry={() => void refetch()} />}

      {activeTenant && !loading && !error && (
        <div
          data-testid="budget-cards"
          data-tenant={activeTenant}
          className="grid grid-cols-1 gap-4 md:grid-cols-2"
        >
          {BUDGET_PERIODS.map((period) => (
            <BudgetCard
              key={period}
              tenantId={activeTenant}
              period={period}
              initial={budgets[period]}
              onSaved={handleSaved}
            />
          ))}
        </div>
      )}
    </PageLayout>
  );
}
