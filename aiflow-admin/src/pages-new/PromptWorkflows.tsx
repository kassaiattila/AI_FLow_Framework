/**
 * AIFlow Prompt Workflows — list + detail + dry-run for the new
 * `PromptWorkflow` foundation (Sprint R / S140).
 *
 * Route: /prompts/workflows
 * Source: src/aiflow/api/v1/prompt_workflows.py
 *
 * Read-only surface — no execution, no mutation. The "Test run" button
 * hits `/dry-run` which returns the resolved descriptor + nested
 * PromptDefinitions without any LLM call.
 */

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { PageLayout } from "../layout/PageLayout";
import { LoadingState } from "../components-new/LoadingState";
import { ErrorState } from "../components-new/ErrorState";
import { EmptyState } from "../components-new/EmptyState";
import { useApi } from "../lib/hooks";
import { fetchApi, ApiClientError } from "../lib/api-client";
import type {
  PromptWorkflow,
  PromptWorkflowDryRunResponse,
  PromptWorkflowListResponse,
} from "../types/promptWorkflow";

const LIST_PATH = "/api/v1/prompts/workflows";

export function PromptWorkflows() {
  const { t } = useTranslation();
  const { data, loading, error, refetch } = useApi<PromptWorkflowListResponse>(
    LIST_PATH,
  );
  const [selected, setSelected] = useState<string | null>(null);

  if (loading) {
    return (
      <PageLayout titleKey="aiflow.prompts.workflows.title">
        <LoadingState fullPage />
      </PageLayout>
    );
  }

  if (error) {
    const isFlagDisabled = error.startsWith("503");
    return (
      <PageLayout titleKey="aiflow.prompts.workflows.title">
        <ErrorState
          error={
            isFlagDisabled
              ? t("aiflow.prompts.workflows.flagDisabled")
              : error
          }
          onRetry={refetch}
        />
      </PageLayout>
    );
  }

  if (!data || data.workflows.length === 0) {
    return (
      <PageLayout titleKey="aiflow.prompts.workflows.title">
        <EmptyState messageKey="aiflow.prompts.workflows.noWorkflows" />
      </PageLayout>
    );
  }

  return (
    <PageLayout titleKey="aiflow.prompts.workflows.title" source={data.source}>
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        <div className="lg:col-span-2">
          <div
            className="rounded-xl border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-900"
            data-testid="prompt-workflows-table"
          >
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 text-left dark:border-gray-800">
                  <th className="px-4 py-2 text-xs font-medium uppercase text-gray-500">
                    {t("aiflow.prompts.workflows.columnName")}
                  </th>
                  <th className="px-4 py-2 text-xs font-medium uppercase text-gray-500">
                    {t("aiflow.prompts.workflows.columnVersion")}
                  </th>
                  <th className="px-4 py-2 text-xs font-medium uppercase text-gray-500">
                    {t("aiflow.prompts.workflows.columnSteps")}
                  </th>
                </tr>
              </thead>
              <tbody>
                {data.workflows.map((wf) => {
                  const isSelected = wf.name === selected;
                  return (
                    <tr
                      key={wf.name}
                      className={`cursor-pointer border-b border-gray-50 hover:bg-gray-50 dark:border-gray-800 dark:hover:bg-gray-800 ${
                        isSelected
                          ? "bg-blue-50 dark:bg-blue-900/20"
                          : ""
                      }`}
                      onClick={() => setSelected(wf.name)}
                      data-testid={`prompt-workflow-row-${wf.name}`}
                    >
                      <td className="px-4 py-2 font-medium text-gray-900 dark:text-gray-100">
                        {wf.name}
                      </td>
                      <td className="px-4 py-2 text-gray-600 dark:text-gray-400">
                        {wf.version}
                      </td>
                      <td className="px-4 py-2 text-gray-600 dark:text-gray-400">
                        {wf.step_count}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        <div className="lg:col-span-3">
          {selected ? (
            <WorkflowDetailPanel name={selected} />
          ) : (
            <div className="rounded-xl border border-dashed border-gray-300 p-8 text-center text-sm text-gray-500 dark:border-gray-700">
              {t("aiflow.prompts.workflows.detailTitle")}
            </div>
          )}
        </div>
      </div>
    </PageLayout>
  );
}

interface WorkflowDetailPanelProps {
  name: string;
}

function WorkflowDetailPanel({ name }: WorkflowDetailPanelProps) {
  const { t } = useTranslation();
  const { data, loading, error } = useApi<PromptWorkflow>(
    `/api/v1/prompts/workflows/${encodeURIComponent(name)}`,
  );
  const [dryRun, setDryRun] = useState<PromptWorkflowDryRunResponse | null>(
    null,
  );
  const [dryRunLoading, setDryRunLoading] = useState(false);
  const [dryRunError, setDryRunError] = useState<string | null>(null);

  async function handleDryRun() {
    setDryRunLoading(true);
    setDryRunError(null);
    try {
      const resp = await fetchApi<PromptWorkflowDryRunResponse>(
        "GET",
        `/api/v1/prompts/workflows/${encodeURIComponent(name)}/dry-run`,
      );
      setDryRun(resp);
    } catch (e) {
      const msg =
        e instanceof ApiClientError
          ? `${e.status}: ${e.message}`
          : e instanceof Error
            ? e.message
            : t("aiflow.prompts.workflows.loadFailed");
      setDryRunError(msg);
    } finally {
      setDryRunLoading(false);
    }
  }

  if (loading) return <LoadingState />;
  if (error || !data) {
    return (
      <ErrorState
        error={error ?? t("aiflow.prompts.workflows.loadFailed")}
        onRetry={() => undefined}
      />
    );
  }

  return (
    <div
      className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900"
      data-testid="prompt-workflow-detail"
    >
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            {data.name}{" "}
            <span className="text-sm font-normal text-gray-500">
              v{data.version}
            </span>
          </h3>
          {data.description && (
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
              {data.description}
            </p>
          )}
        </div>
        <button
          type="button"
          onClick={handleDryRun}
          disabled={dryRunLoading}
          data-testid="prompt-workflow-dry-run-button"
          className="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {dryRunLoading
            ? t("aiflow.prompts.workflows.dryRunRunning")
            : t("aiflow.prompts.workflows.dryRunButton")}
        </button>
      </div>

      <div className="mb-4">
        <h4 className="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">
          {t("aiflow.prompts.workflows.stepsHeading")}
        </h4>
        <ol className="space-y-2">
          {data.steps.map((step, idx) => (
            <li
              key={step.id}
              className="rounded border border-gray-100 bg-gray-50 px-3 py-2 text-sm dark:border-gray-800 dark:bg-gray-800"
              style={{ marginLeft: `${step.depends_on.length * 12}px` }}
            >
              <div className="flex items-baseline justify-between gap-2">
                <span className="font-mono text-xs text-gray-500">
                  #{idx + 1}
                </span>
                <span className="font-semibold text-gray-900 dark:text-gray-100">
                  {step.id}
                </span>
                <span className="text-xs text-gray-500">→ {step.prompt_name}</span>
              </div>
              {step.depends_on.length > 0 && (
                <div className="mt-1 text-xs text-gray-500">
                  {t("aiflow.prompts.workflows.dependsOn")}: {step.depends_on.join(", ")}
                </div>
              )}
              {Object.keys(step.metadata).length > 0 && (
                <div className="mt-1 flex flex-wrap gap-1">
                  {Object.entries(step.metadata).map(([k, v]) => (
                    <span
                      key={k}
                      className="rounded bg-blue-100 px-1.5 py-0.5 text-xs text-blue-800 dark:bg-blue-900 dark:text-blue-200"
                    >
                      {k}: {String(v)}
                    </span>
                  ))}
                </div>
              )}
            </li>
          ))}
        </ol>
      </div>

      {dryRunError && (
        <div className="mb-3 rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-300">
          {dryRunError}
        </div>
      )}

      {dryRun && (
        <div data-testid="prompt-workflow-dry-run-output">
          <h4 className="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">
            {t("aiflow.prompts.workflows.dryRunOutput")}
          </h4>
          <pre className="overflow-x-auto rounded bg-gray-900 p-3 text-xs text-green-300 dark:bg-black">
            {JSON.stringify(dryRun, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
