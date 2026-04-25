/**
 * PipelineDetail — v1.2.0 Pipeline detail with tabs (Overview / YAML / Runs).
 * GATE 5: Figma frame 11693:283233
 */
import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useTranslate } from "../lib/i18n";
import { useApi } from "../lib/hooks";
import { fetchApi } from "../lib/api-client";
import { PageLayout } from "../layout/PageLayout";
import { ErrorState } from "../components-new/ErrorState";
import { LoadingState } from "../components-new/LoadingState";
import { DataTable, type Column } from "../components-new/DataTable";

interface StepInfo {
  name: string;
  service: string;
  method: string;
}

interface PipelineDetailData {
  id: string;
  name: string;
  version: string;
  description: string;
  enabled: boolean;
  yaml_source: string;
  trigger_config: Record<string, unknown>;
  step_count: number;
  steps: StepInfo[];
  definition: Record<string, unknown>;
  created_at: string | null;
  updated_at: string | null;
  source: string;
}

interface ValidateResult {
  valid: boolean;
  errors: string[];
  adapters_available: Record<string, boolean>;
}

interface RunItem {
  id: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  total_duration_ms: number | null;
  error: string | null;
}

interface RunsResponse {
  runs: RunItem[];
  total: number;
}

type Tab = "overview" | "yaml" | "runs";

export function PipelineDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const translate = useTranslate();
  const { data, loading, error, refetch } = useApi<PipelineDetailData>(
    `/api/v1/pipelines/${id}`,
  );
  const [tab, setTab] = useState<Tab>("overview");
  const [validation, setValidation] = useState<ValidateResult | null>(null);
  const [validating, setValidating] = useState(false);

  async function handleValidate() {
    setValidating(true);
    try {
      const res = await fetchApi<ValidateResult>(
        "POST",
        `/api/v1/pipelines/${id}/validate`,
      );
      setValidation(res);
    } catch {
      setValidation({
        valid: false,
        errors: ["Validation request failed"],
        adapters_available: {},
      });
    } finally {
      setValidating(false);
    }
  }

  async function handleDelete() {
    if (!confirm("Delete this pipeline?")) return;
    await fetchApi("DELETE", `/api/v1/pipelines/${id}`);
    navigate("/pipelines");
  }

  if (loading)
    return (
      <PageLayout titleKey="pipelineDetail.overview">
        <LoadingState />
      </PageLayout>
    );
  if (error || !data)
    return (
      <PageLayout titleKey="pipelineDetail.overview">
        <ErrorState error={error ?? "Pipeline not found"} onRetry={refetch} />
      </PageLayout>
    );

  const tabs: { key: Tab; label: string }[] = [
    { key: "overview", label: translate("pipelineDetail.overview") },
    { key: "yaml", label: translate("pipelineDetail.yaml") },
    { key: "runs", label: translate("pipelineDetail.runs") },
  ];

  const steps =
    ((data.definition as Record<string, unknown>)?.steps as Array<
      Record<string, unknown>
    >) ??
    data.steps ??
    [];

  return (
    <PageLayout
      titleKey="pipelineDetail.overview"
      actions={
        <div className="flex gap-2">
          <button
            className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm font-medium hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
            onClick={handleValidate}
            disabled={validating}
          >
            {validating ? "..." : translate("pipelineDetail.validate")}
          </button>
          <button
            className="rounded-lg border border-red-300 px-3 py-1.5 text-sm font-medium text-red-600 hover:bg-red-50 dark:border-red-700 dark:text-red-400"
            onClick={handleDelete}
          >
            {translate("pipelineDetail.delete")}
          </button>
        </div>
      }
    >
      {/* Header details */}
      <div className="mb-4 flex items-center gap-3">
        <button
          onClick={() => navigate("/pipelines")}
          className="text-xs text-gray-500 hover:text-brand-600"
        >
          {translate("pipelines.title")} /
        </button>
        <span className="text-lg font-bold text-gray-900 dark:text-white">
          {data.name}
        </span>
        <span className="rounded-full bg-brand-50 px-2 py-0.5 text-xs font-medium text-brand-700 dark:bg-brand-900/30 dark:text-brand-300">
          v{data.version}
        </span>
        <span
          className={`rounded-full px-2 py-0.5 text-xs font-medium ${data.enabled ? "bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-400" : "bg-gray-100 text-gray-500"}`}
        >
          {data.enabled
            ? translate("pipelines.enabled")
            : translate("pipelines.disabled")}
        </span>
      </div>

      {/* Validation result */}
      {validation && (
        <div
          className={`mb-4 rounded-lg border p-3 text-sm ${validation.valid ? "border-green-200 bg-green-50 text-green-800 dark:border-green-800 dark:bg-green-900/20 dark:text-green-300" : "border-red-200 bg-red-50 text-red-800 dark:border-red-800 dark:bg-red-900/20 dark:text-red-300"}`}
        >
          {validation.valid
            ? "Pipeline is valid"
            : `Errors: ${validation.errors.join(", ")}`}
          {Object.keys(validation.adapters_available).length > 0 && (
            <div className="mt-1 text-xs">
              {Object.entries(validation.adapters_available).map(([k, v]) => (
                <span
                  key={k}
                  className={`mr-3 ${v ? "text-green-600" : "text-red-600"}`}
                >
                  {v ? "\u2713" : "\u2717"} {k}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tabs */}
      <div className="mb-4 flex gap-1 border-b border-gray-200 dark:border-gray-700">
        {tabs.map((t) => (
          <button
            key={t.key}
            className={`px-4 py-2 text-sm font-medium transition-colors ${tab === t.key ? "border-b-2 border-brand-500 text-brand-600 dark:text-brand-400" : "text-gray-500 hover:text-gray-700 dark:text-gray-400"}`}
            onClick={() => setTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === "overview" && (
        <OverviewTab data={data} steps={steps} translate={translate} />
      )}
      {tab === "yaml" && (
        <YamlTab yaml={data.yaml_source} translate={translate} />
      )}
      {tab === "runs" && <RunsTab pipelineId={data.id} translate={translate} />}
    </PageLayout>
  );
}

function OverviewTab({
  data,
  steps,
  translate,
}: {
  data: PipelineDetailData;
  steps: Array<Record<string, unknown>>;
  translate: (k: string) => string;
}) {
  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      {/* Info card */}
      <div className="rounded-lg border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-800">
        <h3 className="mb-3 text-sm font-semibold text-gray-900 dark:text-white">
          {translate("pipelineDetail.info")}
        </h3>
        <dl className="space-y-2 text-sm">
          {[
            [translate("pipelineDetail.description"), data.description || "—"],
            [
              translate("pipelineDetail.trigger"),
              String(
                (data.trigger_config as Record<string, unknown>)?.type ??
                  "manual",
              ),
            ],
            [translate("pipelineDetail.stepCount"), `${data.step_count} steps`],
            [
              translate("pipelineDetail.createdAt"),
              data.created_at
                ? new Date(data.created_at).toLocaleString()
                : "—",
            ],
            [
              translate("pipelineDetail.updatedAt"),
              data.updated_at
                ? new Date(data.updated_at).toLocaleString()
                : "—",
            ],
          ].map(([label, value]) => (
            <div key={label} className="flex">
              <dt className="w-28 shrink-0 text-gray-500">{label}</dt>
              <dd className="text-gray-900 dark:text-gray-100">{value}</dd>
            </div>
          ))}
        </dl>
      </div>

      {/* Steps card */}
      <div className="rounded-lg border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-800">
        <h3 className="mb-3 text-sm font-semibold text-gray-900 dark:text-white">
          {translate("pipelineDetail.stepsTitle")}
        </h3>
        <ol className="space-y-2">
          {steps.map((step, i) => (
            <li
              key={String(step.name)}
              className="flex items-start gap-3 text-sm"
            >
              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand-50 text-xs font-semibold text-brand-700 dark:bg-brand-900/30 dark:text-brand-300">
                {i + 1}
              </span>
              <div>
                <span className="font-medium text-gray-900 dark:text-white">
                  {String(step.name)}
                </span>
                <span className="ml-2 text-xs text-gray-500">
                  {String(step.service)}.{String(step.method)}
                </span>
                {(step.depends_on as string[] | undefined)?.length ? (
                  <span className="ml-2 text-xs text-gray-400">
                    {"\u2190"} {translate("pipelineDetail.dependsOn")}:{" "}
                    {(step.depends_on as string[]).join(", ")}
                  </span>
                ) : null}
              </div>
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}

function YamlTab({
  yaml,
  translate,
}: {
  yaml: string;
  translate: (k: string) => string;
}) {
  const [copied, setCopied] = useState(false);
  function handleCopy() {
    navigator.clipboard.writeText(yaml);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }
  return (
    <div className="relative">
      <button
        onClick={handleCopy}
        className="absolute right-3 top-3 rounded border border-gray-300 bg-white px-2 py-1 text-xs dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300"
      >
        {copied ? "\u2713" : translate("pipelineDetail.copyYaml")}
      </button>
      <pre className="overflow-auto rounded-lg border border-gray-200 bg-gray-50 p-4 text-sm leading-relaxed text-gray-800 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-200">
        {yaml}
      </pre>
    </div>
  );
}

function RunsTab({
  pipelineId,
  translate,
}: {
  pipelineId: string;
  translate: (k: string) => string;
}) {
  const { data, loading, error, refetch } = useApi<RunsResponse>(
    `/api/v1/pipelines/${pipelineId}/runs`,
  );

  const columns: Column<Record<string, unknown>>[] = [
    {
      key: "id",
      label: "Run ID",
      render: (item) => (
        <span className="font-mono text-xs text-gray-500">
          {String(item.id).substring(0, 8)}...
        </span>
      ),
    },
    {
      key: "status",
      label: translate("pipelines.status"),
      render: (item) => {
        const s = String(item.status);
        const c =
          s === "completed"
            ? "bg-green-50 text-green-700"
            : s === "failed"
              ? "bg-red-50 text-red-700"
              : s === "running"
                ? "bg-blue-50 text-blue-700"
                : "bg-gray-100 text-gray-600";
        return (
          <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${c}`}>
            {s}
          </span>
        );
      },
    },
    {
      key: "total_duration_ms",
      label: translate("pipelineDetail.duration"),
      render: (item) => (
        <span className="text-gray-500">
          {item.total_duration_ms
            ? `${((item.total_duration_ms as number) / 1000).toFixed(1)}s`
            : "—"}
        </span>
      ),
    },
    {
      key: "started_at",
      label: translate("pipelineDetail.createdAt"),
      render: (item) => (
        <span className="text-xs text-gray-500">
          {item.started_at
            ? new Date(String(item.started_at)).toLocaleString()
            : "—"}
        </span>
      ),
    },
    {
      key: "error",
      label: "Error",
      render: (item) => (
        <span className="text-xs text-red-500 truncate max-w-xs">
          {item.error ? String(item.error).substring(0, 60) : ""}
        </span>
      ),
    },
  ];

  if (error) return <ErrorState error={error} onRetry={refetch} />;
  if (loading) return <LoadingState />;
  if (!data?.runs?.length)
    return (
      <p className="py-8 text-center text-sm text-gray-500">
        {translate("pipelineDetail.noRuns")}
      </p>
    );

  return (
    <DataTable
      data={data.runs as unknown as Record<string, unknown>[]}
      columns={columns}
      searchKeys={["status"]}
    />
  );
}
