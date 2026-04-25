/**
 * BudgetCard — one per-period tenant budget editor.
 * Sprint N / S123.
 *
 * Renders the live projection (used / limit / remaining / thresholds) from
 * ``TenantBudgetGetResponse`` and lets the operator PUT
 * ``/api/v1/tenants/{tenant_id}/budget/{period}``.
 */

import { useEffect, useMemo, useState } from "react";
import { ApiClientError, fetchApi } from "../../lib/api-client";
import { ThresholdEditor } from "./ThresholdEditor";
import type {
  BudgetPeriod,
  TenantBudgetGetResponse,
  TenantBudgetUpsertRequest,
} from "./types";

interface BudgetCardProps {
  tenantId: string;
  period: BudgetPeriod;
  initial: TenantBudgetGetResponse | null;
  onSaved: (next: TenantBudgetGetResponse) => void;
}

function alertClass(usagePct: number, overThresholds: number[]): string {
  const maxOver = overThresholds.length > 0 ? Math.max(...overThresholds) : 0;
  if (usagePct >= 100 || maxOver >= 100) return "bg-red-500";
  if (usagePct >= 80 || maxOver >= 80) return "bg-orange-500";
  if (usagePct >= 50 || maxOver >= 50) return "bg-yellow-500";
  return "bg-brand-500";
}

function thresholdsEqual(a: number[], b: number[]): boolean {
  if (a.length !== b.length) return false;
  return a.every((value, index) => value === b[index]);
}

function defaultPayload(): TenantBudgetUpsertRequest {
  return {
    limit_usd: 0,
    alert_threshold_pct: [50, 80, 95],
    enabled: true,
  };
}

function fromServer(entry: TenantBudgetGetResponse): TenantBudgetUpsertRequest {
  return {
    limit_usd: entry.budget.limit_usd,
    alert_threshold_pct: [...entry.budget.alert_threshold_pct],
    enabled: entry.budget.enabled,
  };
}

function formatUsd(value: number): string {
  return `$${value.toFixed(4)}`;
}

function formatDate(iso?: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export function BudgetCard({
  tenantId,
  period,
  initial,
  onSaved,
}: BudgetCardProps) {
  const [form, setForm] = useState<TenantBudgetUpsertRequest>(() =>
    initial ? fromServer(initial) : defaultPayload(),
  );
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveOk, setSaveOk] = useState(false);

  useEffect(() => {
    setForm(initial ? fromServer(initial) : defaultPayload());
    setSaveError(null);
    setSaveOk(false);
  }, [initial, tenantId, period]);

  const baselinePayload = useMemo<TenantBudgetUpsertRequest>(
    () => (initial ? fromServer(initial) : defaultPayload()),
    [initial],
  );

  const dirty =
    form.limit_usd !== baselinePayload.limit_usd ||
    form.enabled !== baselinePayload.enabled ||
    !thresholdsEqual(
      form.alert_threshold_pct,
      baselinePayload.alert_threshold_pct,
    );

  const view = initial?.view;
  const usagePct = view?.usage_pct ?? 0;
  const over = view?.over_thresholds ?? [];
  const progressWidth = Math.min(100, Math.max(0, usagePct));

  const handleSave = async () => {
    if (!dirty || saving) return;
    if (!Number.isFinite(form.limit_usd) || form.limit_usd < 0) {
      setSaveError("limit_usd must be >= 0");
      return;
    }
    setSaving(true);
    setSaveError(null);
    setSaveOk(false);
    try {
      const result = await fetchApi<TenantBudgetGetResponse>(
        "PUT",
        `/api/v1/tenants/${encodeURIComponent(tenantId)}/budget/${period}`,
        {
          limit_usd: form.limit_usd,
          alert_threshold_pct: form.alert_threshold_pct,
          enabled: form.enabled,
        },
      );
      onSaved(result);
      setSaveOk(true);
      setTimeout(() => setSaveOk(false), 2000);
    } catch (e) {
      if (e instanceof ApiClientError) {
        const detail =
          typeof e.detail === "string" ? e.detail : JSON.stringify(e.detail);
        setSaveError(`${e.status}: ${detail}`);
      } else {
        setSaveError(e instanceof Error ? e.message : "Save failed");
      }
    } finally {
      setSaving(false);
    }
  };

  const periodLabel = period === "daily" ? "Daily" : "Monthly";

  return (
    <div
      data-testid={`budget-card-${period}`}
      data-period={period}
      data-tenant={tenantId}
      className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900"
    >
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-900 dark:text-gray-100">
            {periodLabel}
          </h3>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Frissitve: {formatDate(initial?.budget.updated_at ?? null)}
          </p>
        </div>
        <label className="flex cursor-pointer items-center gap-2 text-xs text-gray-600 dark:text-gray-400">
          <input
            type="checkbox"
            checked={form.enabled}
            onChange={(event) =>
              setForm({ ...form, enabled: event.target.checked })
            }
            data-testid={`budget-enabled-${period}`}
            className="h-4 w-4 accent-brand-500"
          />
          <span>Aktiv</span>
        </label>
      </div>

      {view ? (
        <div className="mb-3 space-y-2">
          <div className="flex items-baseline justify-between gap-2 text-xs text-gray-600 dark:text-gray-400">
            <span>
              Felhasznalt:{" "}
              <span
                data-testid={`budget-used-${period}`}
                className="font-mono font-semibold text-gray-900 dark:text-gray-100"
              >
                {formatUsd(view.used_usd)}
              </span>{" "}
              / {formatUsd(view.limit_usd)}
            </span>
            <span>
              Hatralevo:{" "}
              <span
                data-testid={`budget-remaining-${period}`}
                className="font-mono font-semibold text-gray-900 dark:text-gray-100"
              >
                {formatUsd(view.remaining_usd)}
              </span>
            </span>
            <span
              data-testid={`budget-usage-pct-${period}`}
              className="font-mono font-semibold text-gray-900 dark:text-gray-100"
            >
              {view.usage_pct.toFixed(1)}%
            </span>
          </div>
          <div
            className="h-2 overflow-hidden rounded-full bg-gray-100 dark:bg-gray-800"
            role="progressbar"
            aria-valuenow={view.usage_pct}
            aria-valuemin={0}
            aria-valuemax={100}
          >
            <div
              data-testid={`budget-progress-${period}`}
              className={`h-full ${alertClass(usagePct, over)} transition-all`}
              style={{ width: `${progressWidth}%` }}
            />
          </div>
          {view.alert_threshold_pct.length > 0 && (
            <div
              data-testid={`budget-over-${period}`}
              className="flex flex-wrap items-center gap-1.5 text-xs"
            >
              <span className="text-gray-500 dark:text-gray-400">
                Kuszobok:
              </span>
              {view.alert_threshold_pct.map((pct) => {
                const isOver = over.includes(pct);
                return (
                  <span
                    key={pct}
                    data-threshold={pct}
                    data-over={isOver ? "1" : "0"}
                    className={`rounded-full px-2 py-0.5 font-mono ${
                      isOver
                        ? "bg-red-50 text-red-700 ring-1 ring-red-200 dark:bg-red-900/30 dark:text-red-300 dark:ring-red-800"
                        : "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400"
                    }`}
                  >
                    {pct}%
                  </span>
                );
              })}
            </div>
          )}
        </div>
      ) : (
        <div
          data-testid={`budget-empty-${period}`}
          className="mb-3 rounded-lg border border-dashed border-gray-300 bg-gray-50 p-3 text-xs text-gray-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-400"
        >
          Meg nincs {periodLabel.toLowerCase()} kuszob ennek a tenant-nek.
          Allitsd be a limitet es mentsd.
        </div>
      )}

      <div className="space-y-3">
        <label className="block">
          <span className="mb-1 block text-xs font-medium text-gray-600 dark:text-gray-400">
            Limit (USD)
          </span>
          <input
            type="number"
            step="0.01"
            min="0"
            value={Number.isFinite(form.limit_usd) ? form.limit_usd : 0}
            onChange={(event) =>
              setForm({ ...form, limit_usd: Number(event.target.value) })
            }
            data-testid={`budget-limit-${period}`}
            className="w-full rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-900 focus:border-brand-500 focus:outline-none dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100"
          />
        </label>

        <div>
          <span className="mb-1 block text-xs font-medium text-gray-600 dark:text-gray-400">
            Alert kuszobok (%)
          </span>
          <ThresholdEditor
            value={form.alert_threshold_pct}
            onChange={(next) => setForm({ ...form, alert_threshold_pct: next })}
            testid={`budget-thresholds-${period}`}
          />
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleSave}
            disabled={!dirty || saving}
            data-testid={`budget-save-${period}`}
            className="rounded-lg bg-brand-500 px-4 py-1.5 text-sm font-semibold text-white hover:bg-brand-600 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {saving ? "Mentes..." : "Mentes"}
          </button>
          {saveOk && (
            <span
              data-testid={`budget-save-ok-${period}`}
              className="text-xs text-green-600 dark:text-green-400"
            >
              Elmentve.
            </span>
          )}
          {saveError && (
            <span
              role="alert"
              data-testid={`budget-save-error-${period}`}
              className="text-xs text-red-600 dark:text-red-400"
            >
              {saveError}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
