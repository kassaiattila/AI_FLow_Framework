/**
 * AIFlow Costs — F6.5 cost analytics with KPIs + DataTable.
 */
import { useTranslate } from "../lib/i18n";
import { useApi } from "../lib/hooks";
import { PageLayout } from "../layout/PageLayout";
import { ErrorState } from "../components-new/ErrorState";
import { DataTable, type Column } from "../components-new/DataTable";

interface SkillCost { skill_name: string; run_count: number; total_cost_usd: number; avg_cost_usd: number; }
interface CostsSummary { total_cost_usd: number; total_runs: number; per_skill: SkillCost[]; daily: unknown[]; source?: string; }

export function Costs() {
  const translate = useTranslate();
  const { data, loading, error, refetch } = useApi<CostsSummary>("/api/v1/costs/summary");

  const columns: Column<Record<string, unknown>>[] = [
    { key: "skill_name", label: "Skill", render: (item) => <span className="font-medium text-gray-900 dark:text-gray-100">{String(item.skill_name)}</span> },
    { key: "run_count", label: translate("aiflow.costs.runs"), getValue: (item) => item.run_count as number },
    { key: "total_cost_usd", label: translate("aiflow.costs.totalCostCol"), getValue: (item) => item.total_cost_usd as number, render: (item) => <span className="text-gray-600 dark:text-gray-400">${((item.total_cost_usd as number) ?? 0).toFixed(3)}</span> },
    { key: "avg_cost_usd", label: translate("aiflow.costs.avgCost"), getValue: (item) => item.avg_cost_usd as number, render: (item) => <span className="text-gray-500 dark:text-gray-400">${((item.avg_cost_usd as number) ?? 0).toFixed(4)}</span> },
  ];

  return (
    <PageLayout titleKey="aiflow.costs.title" source={data?.source}>
      {/* KPIs */}
      <div className="mb-4 grid grid-cols-1 gap-4 md:grid-cols-3">
        <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
          <p className="text-xs font-medium text-gray-500">{translate("aiflow.costs.totalCost")}</p>
          <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-gray-100">${(data?.total_cost_usd ?? 0).toFixed(2)}</p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
          <p className="text-xs font-medium text-gray-500">{translate("aiflow.costs.totalRuns")}</p>
          <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-gray-100">{data?.total_runs ?? 0}</p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
          <p className="text-xs font-medium text-gray-500">{translate("aiflow.costs.avgCost")}</p>
          <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-gray-100">${data && data.total_runs > 0 ? (data.total_cost_usd / data.total_runs).toFixed(4) : "0.00"}</p>
        </div>
      </div>

      <h3 className="mb-2 text-base font-semibold text-gray-900 dark:text-gray-100">{translate("aiflow.costs.bySkill")}</h3>
      {error ? <ErrorState error={error} onRetry={refetch} /> :
        <DataTable data={(data?.per_skill ?? []) as unknown as Record<string, unknown>[]} columns={columns} loading={loading} searchKeys={["skill"]} />
      }
    </PageLayout>
  );
}
