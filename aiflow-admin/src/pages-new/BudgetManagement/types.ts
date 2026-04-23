/** Mirrors ``aiflow.services.tenant_budgets.contracts`` (Sprint N / S121). */

export type BudgetPeriod = "daily" | "monthly";

export const BUDGET_PERIODS: BudgetPeriod[] = ["daily", "monthly"];

export interface TenantBudgetRow {
  id?: string;
  tenant_id: string;
  period: BudgetPeriod;
  limit_usd: number;
  alert_threshold_pct: number[];
  enabled: boolean;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface TenantBudgetView {
  tenant_id: string;
  period: BudgetPeriod;
  limit_usd: number;
  used_usd: number;
  remaining_usd: number;
  usage_pct: number;
  alert_threshold_pct: number[];
  over_thresholds: number[];
  enabled: boolean;
  as_of: string;
}

export interface TenantBudgetGetResponse {
  budget: TenantBudgetRow;
  view: TenantBudgetView;
}

export interface TenantBudgetUpsertRequest {
  limit_usd: number;
  alert_threshold_pct: number[];
  enabled: boolean;
}
