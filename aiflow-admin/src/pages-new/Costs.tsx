/**
 * AIFlow Costs — F6.5 cost analytics with KPIs + DataTable + model breakdown.
 */
import { useTranslate } from "../lib/i18n";
import { useApi } from "../lib/hooks";
import { PageLayout } from "../layout/PageLayout";
import { ErrorState } from "../components-new/ErrorState";
import { DataTable, type Column } from "../components-new/DataTable";

interface SkillCost { skill_name: string; run_count: number; total_cost_usd: number; avg_cost_usd: number; }
interface DailyCost { date: string; total_cost_usd: number; run_count: number; }
interface CostsSummary { total_cost_usd: number; total_runs: number; per_skill: SkillCost[]; daily: DailyCost[]; source?: string; }
interface ModelCostItem { model: string; provider: string; request_count: number; total_input_tokens: number; total_output_tokens: number; total_cost_usd: number; }
interface CostBreakdown { per_model: ModelCostItem[]; total_records: number; total_tokens: number; total_cost_usd: number; source: string; }

function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

export function Costs() {
  const translate = useTranslate();
  const { data, loading, error, refetch } = useApi<CostsSummary>("/api/v1/costs/summary");
  const { data: breakdown } = useApi<CostBreakdown>("/api/v1/costs/breakdown");

  const skillColumns: Column<Record<string, unknown>>[] = [
    { key: "skill_name", label: "Skill", render: (item) => <span className="font-medium text-gray-900 dark:text-gray-100">{String(item.skill_name)}</span> },
    { key: "run_count", label: translate("aiflow.costs.runs"), getValue: (item) => item.run_count as number },
    { key: "total_cost_usd", label: translate("aiflow.costs.totalCostCol"), getValue: (item) => item.total_cost_usd as number, render: (item) => <span className="text-gray-600 dark:text-gray-400">${((item.total_cost_usd as number) ?? 0).toFixed(3)}</span> },
    { key: "avg_cost_usd", label: translate("aiflow.costs.avgCost"), getValue: (item) => item.avg_cost_usd as number, render: (item) => <span className="text-gray-500 dark:text-gray-400">${((item.avg_cost_usd as number) ?? 0).toFixed(4)}</span> },
  ];

  const modelColumns: Column<Record<string, unknown>>[] = [
    { key: "model", label: "Model", render: (item) => <span className="font-medium text-gray-900 dark:text-gray-100">{String(item.model)}</span> },
    { key: "provider", label: "Provider", render: (item) => <span className="text-xs text-gray-500">{String(item.provider)}</span> },
    { key: "request_count", label: "Requests", getValue: (item) => item.request_count as number },
    { key: "total_input_tokens", label: "Input Tokens", getValue: (item) => item.total_input_tokens as number, render: (item) => <span className="text-gray-600 dark:text-gray-400">{formatTokens((item.total_input_tokens as number) ?? 0)}</span> },
    { key: "total_output_tokens", label: "Output Tokens", getValue: (item) => item.total_output_tokens as number, render: (item) => <span className="text-gray-600 dark:text-gray-400">{formatTokens((item.total_output_tokens as number) ?? 0)}</span> },
    { key: "total_cost_usd", label: "Cost", getValue: (item) => item.total_cost_usd as number, render: (item) => <span className="font-medium text-green-600 dark:text-green-400">${((item.total_cost_usd as number) ?? 0).toFixed(4)}</span> },
  ];

  return (
    <PageLayout titleKey="aiflow.costs.title" source={data?.source}>
      {/* KPIs */}
      <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-4">
        <div className="rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-900">
          <p className="text-xs font-medium text-gray-500">{translate("aiflow.costs.totalCost")}</p>
          <p className="mt-1 text-xl font-bold text-gray-900 dark:text-gray-100">${(data?.total_cost_usd ?? 0).toFixed(2)}</p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-900">
          <p className="text-xs font-medium text-gray-500">{translate("aiflow.costs.totalRuns")}</p>
          <p className="mt-1 text-xl font-bold text-gray-900 dark:text-gray-100">{data?.total_runs ?? 0}</p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-900">
          <p className="text-xs font-medium text-gray-500">Total Tokens</p>
          <p className="mt-1 text-xl font-bold text-gray-900 dark:text-gray-100">{formatTokens(breakdown?.total_tokens ?? 0)}</p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-900">
          <p className="text-xs font-medium text-gray-500">API Calls</p>
          <p className="mt-1 text-xl font-bold text-gray-900 dark:text-gray-100">{breakdown?.total_records ?? 0}</p>
        </div>
      </div>

      {/* Daily cost mini-chart (simple bar) */}
      {data && data.daily.length > 0 && (
        <div className="mb-4 rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
          <h3 className="mb-3 text-sm font-semibold text-gray-900 dark:text-gray-100">Daily Cost (last 30 days)</h3>
          <div className="flex items-end gap-1" style={{ height: 80 }}>
            {data.daily.slice(0, 30).reverse().map((d, i) => {
              const maxCost = Math.max(...data.daily.map(x => x.total_cost_usd), 0.001);
              const h = Math.max(4, (d.total_cost_usd / maxCost) * 72);
              return (
                <div key={i} className="flex flex-1 flex-col items-center gap-1" title={`${d.date}: $${d.total_cost_usd.toFixed(4)} (${d.run_count} runs)`}>
                  <div className="w-full rounded-t bg-brand-500" style={{ height: h }} />
                </div>
              );
            })}
          </div>
          <div className="mt-1 flex justify-between text-[10px] text-gray-400">
            <span>{data.daily[data.daily.length - 1]?.date}</span>
            <span>{data.daily[0]?.date}</span>
          </div>
        </div>
      )}

      {/* By Skill */}
      <h3 className="mb-2 text-sm font-semibold text-gray-900 dark:text-gray-100">{translate("aiflow.costs.bySkill")}</h3>
      {error ? <ErrorState error={error} onRetry={refetch} /> :
        <DataTable data={(data?.per_skill ?? []) as unknown as Record<string, unknown>[]} columns={skillColumns} loading={loading} searchKeys={["skill_name"]} />
      }

      {/* By Model (from cost_records) */}
      {breakdown && breakdown.per_model.length > 0 && (
        <div className="mt-4">
          <h3 className="mb-2 text-sm font-semibold text-gray-900 dark:text-gray-100">By Model (Token Breakdown)</h3>
          <DataTable data={breakdown.per_model as unknown as Record<string, unknown>[]} columns={modelColumns} searchKeys={["model", "provider"]} />
        </div>
      )}
    </PageLayout>
  );
}
