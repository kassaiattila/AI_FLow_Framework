/**
 * Pipelines — v1.2.0 Pipeline list page with DataTable + Templates tab.
 * GATE 5: Figma frame 11693:283232
 */
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslate } from "../lib/i18n";
import { useApi } from "../lib/hooks";
import { fetchApi } from "../lib/api-client";
import { PageLayout } from "../layout/PageLayout";
import { ErrorState } from "../components-new/ErrorState";
import { EmptyState } from "../components-new/EmptyState";
import { LoadingState } from "../components-new/LoadingState";
import { DataTable, type Column } from "../components-new/DataTable";

interface PipelineItem {
  id: string;
  name: string;
  version: string;
  description: string;
  enabled: boolean;
  step_count: number;
  trigger_type: string;
  created_at: string | null;
}

interface PipelineListResponse {
  pipelines: PipelineItem[];
  total: number;
  source: string;
}

interface TemplateItem {
  name: string;
  version: string;
  description: string;
  step_count: number;
  category: string;
  tags: string[];
}

interface TemplateListResponse {
  templates: TemplateItem[];
  total: number;
  source: string;
}

type Tab = "pipelines" | "templates";

export function Pipelines() {
  const translate = useTranslate();
  const navigate = useNavigate();
  const [tab, setTab] = useState<Tab>("pipelines");
  const { data, loading, error, refetch } =
    useApi<PipelineListResponse>("/api/v1/pipelines");
  const {
    data: templatesData,
    loading: templatesLoading,
    error: templatesError,
    refetch: templatesRefetch,
  } = useApi<TemplateListResponse>("/api/v1/pipelines/templates/list");
  const [showCreate, setShowCreate] = useState(false);
  const [yaml, setYaml] = useState("");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState("");

  const columns: Column<Record<string, unknown>>[] = [
    {
      key: "name",
      label: translate("pipelines.name"),
      render: (item) => (
        <button
          className="font-medium text-brand-600 hover:text-brand-700 dark:text-brand-400 text-left"
          onClick={() => navigate(`/pipelines/${item.id}`)}
        >
          {String(item.name)}
        </button>
      ),
    },
    {
      key: "version",
      label: translate("pipelines.version"),
      render: (item) => (
        <span className="text-gray-500">{String(item.version)}</span>
      ),
    },
    {
      key: "step_count",
      label: translate("pipelines.steps"),
      getValue: (item) => item.step_count as number,
      render: (item) => (
        <span className="text-gray-500">{String(item.step_count)}</span>
      ),
    },
    {
      key: "trigger_type",
      label: translate("pipelines.trigger"),
      render: (item) => (
        <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs dark:bg-gray-700 dark:text-gray-300">
          {String(item.trigger_type)}
        </span>
      ),
    },
    {
      key: "enabled",
      label: translate("pipelines.status"),
      render: (item) => {
        const enabled = item.enabled as boolean;
        const cls = enabled
          ? "bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-400"
          : "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400";
        return (
          <span
            className={`rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}
          >
            {enabled
              ? translate("pipelines.enabled")
              : translate("pipelines.disabled")}
          </span>
        );
      },
    },
    {
      key: "created_at",
      label: translate("pipelines.created"),
      render: (item) => (
        <span className="text-xs text-gray-500">
          {item.created_at
            ? new Date(String(item.created_at)).toLocaleDateString()
            : "—"}
        </span>
      ),
    },
  ];

  const templateColumns: Column<Record<string, unknown>>[] = [
    {
      key: "name",
      label: translate("pipelines.templateName"),
      render: (item) => (
        <span className="font-medium text-gray-900 dark:text-white">
          {String(item.name)}
        </span>
      ),
    },
    {
      key: "version",
      label: translate("pipelines.templateVersion"),
      render: (item) => (
        <span className="text-gray-500">{String(item.version)}</span>
      ),
    },
    {
      key: "category",
      label: translate("pipelines.templateCategory"),
      render: (item) => (
        <span className="rounded-full bg-blue-50 px-2 py-0.5 text-xs text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
          {String(item.category || "—")}
        </span>
      ),
    },
    {
      key: "step_count",
      label: translate("pipelines.templateSteps"),
      getValue: (item) => item.step_count as number,
      render: (item) => (
        <span className="text-gray-500">{String(item.step_count)}</span>
      ),
    },
    {
      key: "description",
      label: translate("pipelines.templateDescription"),
      render: (item) => (
        <span className="text-sm text-gray-500 truncate max-w-xs block">
          {String(item.description || "—")}
        </span>
      ),
    },
    {
      key: "_deploy",
      label: "",
      render: (item) => (
        <button
          className="rounded-lg border border-brand-500 px-3 py-1 text-xs font-medium text-brand-600 hover:bg-brand-50 dark:text-brand-400 dark:hover:bg-brand-900/20 transition-colors"
          onClick={async (e) => {
            e.stopPropagation();
            try {
              await fetchApi(
                "POST",
                `/api/v1/pipelines/templates/${item.name}/deploy`,
              );
              setTab("pipelines");
              refetch();
            } catch (err) {
              // error handled by fetchApi interceptor
            }
          }}
        >
          {translate("pipelines.deploy")}
        </button>
      ),
    },
  ];

  async function handleCreate() {
    setCreating(true);
    setCreateError("");
    try {
      await fetchApi("POST", "/api/v1/pipelines", { yaml_source: yaml });
      setShowCreate(false);
      setYaml("");
      refetch();
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : String(err));
    } finally {
      setCreating(false);
    }
  }

  const tabCls = (t: Tab) =>
    `px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
      tab === t
        ? "border-brand-500 text-brand-600 dark:text-brand-400"
        : "border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
    }`;

  return (
    <PageLayout
      titleKey="pipelines.title"
      subtitleKey="pipelines.subtitle"
      actions={
        tab === "pipelines" ? (
          <button
            className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-600 transition-colors"
            onClick={() => setShowCreate(true)}
          >
            + {translate("pipelines.new")}
          </button>
        ) : undefined
      }
    >
      {/* Tab bar */}
      <div className="mb-4 flex border-b border-gray-200 dark:border-gray-700">
        <button
          className={tabCls("pipelines")}
          onClick={() => setTab("pipelines")}
        >
          {translate("pipelines.tabPipelines")}
        </button>
        <button
          className={tabCls("templates")}
          onClick={() => setTab("templates")}
        >
          {translate("pipelines.tabTemplates")}
        </button>
      </div>

      {/* Pipelines tab */}
      {tab === "pipelines" && (
        <>
          {error ? (
            <ErrorState error={error} onRetry={refetch} />
          ) : loading ? (
            <LoadingState />
          ) : !data?.pipelines?.length ? (
            <EmptyState messageKey="pipelines.empty" />
          ) : (
            <DataTable
              data={data.pipelines as unknown as Record<string, unknown>[]}
              columns={columns}
              searchKeys={["name", "trigger_type"]}
            />
          )}
        </>
      )}

      {/* Templates tab */}
      {tab === "templates" && (
        <>
          {templatesError ? (
            <ErrorState error={templatesError} onRetry={templatesRefetch} />
          ) : templatesLoading ? (
            <LoadingState />
          ) : !templatesData?.templates?.length ? (
            <EmptyState messageKey="pipelines.templatesEmpty" />
          ) : (
            <DataTable
              data={
                templatesData.templates as unknown as Record<string, unknown>[]
              }
              columns={templateColumns}
              searchKeys={["name", "category", "description"]}
            />
          )}
        </>
      )}

      {/* Create modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-2xl rounded-xl bg-white p-6 shadow-xl dark:bg-gray-800">
            <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">
              {translate("pipelines.new")}
            </h2>
            <textarea
              className="w-full h-64 rounded-lg border border-gray-300 bg-gray-50 p-3 font-mono text-sm dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100"
              placeholder="name: my_pipeline&#10;steps:&#10;  - name: step1&#10;    service: email_connector&#10;    method: fetch_emails"
              value={yaml}
              onChange={(e) => setYaml(e.target.value)}
            />
            {createError && (
              <p className="mt-2 text-sm text-red-600">{createError}</p>
            )}
            <div className="mt-4 flex justify-end gap-3">
              <button
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm dark:border-gray-600 dark:text-gray-300"
                onClick={() => {
                  setShowCreate(false);
                  setCreateError("");
                }}
              >
                {translate("pipelines.cancel")}
              </button>
              <button
                className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-600 disabled:opacity-50"
                onClick={handleCreate}
                disabled={creating || !yaml.trim()}
              >
                {creating ? "..." : translate("pipelines.create")}
              </button>
            </div>
          </div>
        </div>
      )}
    </PageLayout>
  );
}
