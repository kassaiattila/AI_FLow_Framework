/**
 * AIFlow RunDetail — C2.2 step-level run detail with retry + export.
 */
import { Fragment, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useTranslate } from "../lib/i18n";
import { useApi } from "../lib/hooks";
import { fetchApi } from "../lib/api-client";
import { PageLayout } from "../layout/PageLayout";
import { LoadingState } from "../components-new/LoadingState";
import { ErrorState } from "../components-new/ErrorState";
import { ConfirmDialog } from "../components-new/ConfirmDialog";

interface StepRunItem {
  step_name: string;
  status: string;
  duration_ms: number | null;
  cost_usd: number | null;
  model_used: string | null;
  input_tokens: number | null;
  output_tokens: number | null;
  error: string | null;
}

interface RunItem {
  run_id: string;
  workflow_name: string;
  skill_name: string | null;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  total_duration_ms: number | null;
  total_cost_usd: number;
  pipeline_id?: string;
  steps: StepRunItem[];
}

export function RunDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const translate = useTranslate();
  const { data, loading, error, refetch } = useApi<RunItem>(`/api/v1/runs/${id}`);
  const [retryOpen, setRetryOpen] = useState(false);
  const [retrying, setRetrying] = useState(false);

  async function handleRetry() {
    if (!data?.pipeline_id) return;
    setRetrying(true);
    try {
      await fetchApi<unknown>("POST", `/api/v1/pipelines/${data.pipeline_id}/execute`);
      setRetryOpen(false);
      refetch();
    } catch {
      /* ErrorState will handle */
    } finally {
      setRetrying(false);
    }
  }

  function handleExport() {
    if (!data) return;
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `run-${id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  if (loading) return <PageLayout titleKey="aiflow.runDetail.title"><LoadingState /></PageLayout>;
  if (error || !data) return <PageLayout titleKey="aiflow.runDetail.title"><ErrorState error={error ?? "Run not found"} onRetry={refetch} /></PageLayout>;

  const statusColor = data.status === "completed" ? "bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-400"
    : data.status === "running" ? "bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
    : data.status === "failed" ? "bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-400"
    : "bg-gray-100 text-gray-600";

  return (
    <PageLayout titleKey="aiflow.runDetail.title">
      {/* Header */}
      <div className="mb-4 flex items-center gap-3">
        <button onClick={() => navigate("/runs")} className="text-xs text-gray-500 hover:text-brand-600">
          {translate("aiflow.runDetail.backToRuns")} /
        </button>
        <span className="font-mono text-lg font-bold text-gray-900 dark:text-white">
          {data.run_id.substring(0, 8)}
        </span>
        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${statusColor}`}>
          {data.status}
        </span>
      </div>

      {/* KPI cards */}
      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard label={translate("aiflow.runDetail.pipeline")} value={data.skill_name ?? data.workflow_name} />
        <KpiCard label={translate("aiflow.runs.duration")} value={data.total_duration_ms ? `${(data.total_duration_ms / 1000).toFixed(1)}s` : "\u2014"} />
        <KpiCard label={translate("aiflow.runs.cost")} value={data.total_cost_usd > 0 ? `$${data.total_cost_usd.toFixed(3)}` : "\u2014"} />
        <KpiCard label={translate("aiflow.runs.started")} value={data.started_at ? new Date(data.started_at).toLocaleString() : "\u2014"} />
      </div>

      {/* Step log */}
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100">
          {translate("aiflow.runDetail.stepLog")}
        </h3>
        <div className="flex gap-2">
          <button
            onClick={() => setRetryOpen(true)}
            disabled={!data.pipeline_id}
            className="rounded-lg border border-brand-300 px-3 py-1.5 text-sm font-medium text-brand-600 hover:bg-brand-50 disabled:cursor-not-allowed disabled:opacity-40 dark:border-brand-700 dark:text-brand-400 dark:hover:bg-brand-900/20"
          >
            {translate("aiflow.runDetail.retryPipeline")}
          </button>
          <button
            onClick={handleExport}
            className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-400 dark:hover:bg-gray-800"
          >
            {translate("aiflow.runDetail.exportJson")}
          </button>
        </div>
      </div>

      <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-900">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 text-left dark:border-gray-800">
              <th className="px-4 py-3 text-xs font-medium uppercase tracking-wider text-gray-500">#</th>
              <th className="px-4 py-3 text-xs font-medium uppercase tracking-wider text-gray-500">{translate("aiflow.runDetail.stepName")}</th>
              <th className="px-4 py-3 text-xs font-medium uppercase tracking-wider text-gray-500">{translate("aiflow.runs.status")}</th>
              <th className="px-4 py-3 text-xs font-medium uppercase tracking-wider text-gray-500">{translate("aiflow.runs.duration")}</th>
              <th className="px-4 py-3 text-xs font-medium uppercase tracking-wider text-gray-500">{translate("aiflow.runDetail.model")}</th>
              <th className="px-4 py-3 text-xs font-medium uppercase tracking-wider text-gray-500">{translate("aiflow.runDetail.tokens")}</th>
              <th className="px-4 py-3 text-xs font-medium uppercase tracking-wider text-gray-500">{translate("aiflow.runs.cost")}</th>
            </tr>
          </thead>
          <tbody>
            {(data.steps ?? []).map((step, i) => {
              const sc = step.status === "completed" ? "bg-green-50 text-green-700" : step.status === "running" ? "bg-blue-50 text-blue-700" : step.status === "failed" ? "bg-red-50 text-red-700" : "bg-gray-100 text-gray-600";
              return (
                <Fragment key={step.step_name}>
                  <tr className="border-b border-gray-50 dark:border-gray-800">
                    <td className="px-4 py-3 text-gray-500">{i + 1}</td>
                    <td className="px-4 py-3 font-medium text-gray-900 dark:text-gray-100">{step.step_name}</td>
                    <td className="px-4 py-3"><span className={`rounded-full px-2 py-0.5 text-xs font-medium ${sc}`}>{step.status}</span></td>
                    <td className="px-4 py-3 text-gray-500">{step.duration_ms != null ? `${(step.duration_ms / 1000).toFixed(1)}s` : "\u2014"}</td>
                    <td className="px-4 py-3 text-xs text-gray-500">{step.model_used ?? "\u2014"}</td>
                    <td className="px-4 py-3 text-xs text-gray-500">
                      {step.input_tokens != null || step.output_tokens != null
                        ? `${step.input_tokens ?? 0} / ${step.output_tokens ?? 0}`
                        : "\u2014"}
                    </td>
                    <td className="px-4 py-3 text-gray-500">{step.cost_usd != null && step.cost_usd > 0 ? `$${step.cost_usd.toFixed(3)}` : "\u2014"}</td>
                  </tr>
                  {step.error && (
                    <tr className="border-b border-gray-50 dark:border-gray-800">
                      <td />
                      <td colSpan={6} className="px-4 py-2">
                        <div className="rounded-lg bg-red-50 px-3 py-2 text-xs text-red-700 dark:bg-red-900/20 dark:text-red-400">
                          {translate("aiflow.runDetail.error")}: {step.error}
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Retry confirm dialog */}
      <ConfirmDialog
        open={retryOpen}
        title={translate("aiflow.runDetail.retryPipeline")}
        message={translate("aiflow.runDetail.retryConfirm")}
        variant="danger"
        loading={retrying}
        confirmLabel={translate("aiflow.runDetail.retryPipeline")}
        onConfirm={handleRetry}
        onCancel={() => setRetryOpen(false)}
      />
    </PageLayout>
  );
}

function KpiCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
      <p className="text-xs font-medium text-gray-500">{label}</p>
      <p className="mt-1 text-lg font-bold text-gray-900 dark:text-gray-100">{value}</p>
    </div>
  );
}
