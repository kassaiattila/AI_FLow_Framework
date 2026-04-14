/**
 * AIFlow Runs — F6.5 workflow run list with DataTable.
 */
import { useNavigate } from "react-router-dom";
import { useTranslate } from "../lib/i18n";
import { useApi } from "../lib/hooks";
import { fetchApi } from "../lib/api-client";
import { PageLayout } from "../layout/PageLayout";
import { ErrorState } from "../components-new/ErrorState";
import { DataTable, type Column } from "../components-new/DataTable";

interface RunItem { run_id: string; workflow_name: string; skill_name: string | null; status: string; started_at: string | null; total_duration_ms: number | null; total_cost_usd: number; pipeline_id?: string; }
interface RunsResponse { runs: RunItem[]; total: number; }

export function Runs() {
  const navigate = useNavigate();
  const translate = useTranslate();
  const { data, loading, error, refetch } = useApi<RunsResponse>("/api/v1/runs");

  const handleRestart = async (pipelineId: string) => {
    try {
      await fetchApi<unknown>("POST", `/api/v1/pipelines/${pipelineId}/execute`);
      refetch();
    } catch { /* ignore — ErrorState will handle */ }
  };

  const columns: Column<Record<string, unknown>>[] = [
    { key: "run_id", label: "Run ID", render: (item) => <span className="font-mono text-xs text-gray-600 dark:text-gray-400">{String(item.run_id).substring(0, 8)}...</span> },
    { key: "skill_name", label: translate("aiflow.runs.skill"), render: (item) => <span className="font-medium text-gray-900 dark:text-gray-100">{String(item.skill_name ?? item.workflow_name)}</span> },
    { key: "status", label: translate("aiflow.runs.status"), render: (item) => {
      const s = String(item.status);
      const c = s === "completed" ? "bg-green-50 text-green-700" : s === "running" ? "bg-blue-50 text-blue-700" : s === "failed" ? "bg-red-50 text-red-700" : "bg-gray-100 text-gray-600";
      return <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${c}`}>{s}</span>;
    }},
    { key: "total_duration_ms", label: translate("aiflow.runs.duration"), getValue: (item) => item.total_duration_ms as number ?? 0, render: (item) => <span className="text-gray-500">{item.total_duration_ms ? `${((item.total_duration_ms as number)/1000).toFixed(1)}s` : "—"}</span> },
    { key: "total_cost_usd", label: translate("aiflow.runs.cost"), getValue: (item) => item.total_cost_usd as number ?? 0, render: (item) => <span className="text-gray-500">{(item.total_cost_usd as number) > 0 ? `$${(item.total_cost_usd as number).toFixed(3)}` : "—"}</span> },
    { key: "started_at", label: translate("aiflow.runs.started"), render: (item) => <span className="text-xs text-gray-500">{item.started_at ? new Date(String(item.started_at)).toLocaleString() : "—"}</span> },
    { key: "actions", label: "", sortable: false, render: (item) => {
      const pipeId = item.pipeline_id as string | undefined;
      const status = String(item.status);
      if (!pipeId || status === "running") return null;
      return (
        <button
          onClick={(e) => { e.stopPropagation(); void handleRestart(pipeId); }}
          className="rounded-md border border-brand-300 px-2 py-1 text-xs font-medium text-brand-600 hover:bg-brand-50 dark:border-brand-700 dark:text-brand-400 dark:hover:bg-brand-900/20"
          title="Restart"
        >
          ↻
        </button>
      );
    }},
  ];

  return (
    <PageLayout titleKey="aiflow.runs.title">
      {error ? <ErrorState error={error} onRetry={refetch} /> :
        <DataTable data={(data?.runs ?? []) as unknown as Record<string, unknown>[]} columns={columns} loading={loading} searchKeys={["skill_name", "workflow_name", "status"]} onRowClick={(item) => navigate(`/runs/${item.run_id as string}`)} />
      }
    </PageLayout>
  );
}
