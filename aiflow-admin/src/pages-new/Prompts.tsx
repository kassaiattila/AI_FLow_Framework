/**
 * AIFlow Prompts — read-only list of prompt YAML files discovered on disk.
 * Route: /prompts
 * Source: 01_PLAN/110_USE_CASE_FIRST_REPLAN.md §4 Sprint I / UC1 S97.
 *
 * v1 is intentionally view-only (no edit, no pagination — assumes ≤50
 * prompts). Langfuse-aware tooling lives downstream (S98+).
 */

import { useNavigate } from "react-router-dom";
import { PageLayout } from "../layout/PageLayout";
import { LoadingState } from "../components-new/LoadingState";
import { ErrorState } from "../components-new/ErrorState";
import { useApi } from "../lib/hooks";

interface PromptListItem {
  name: string;
  version: string | number | null;
  path: string;
  updated_at: string;
  tags: string[];
}

interface PromptListResponse {
  prompts: PromptListItem[];
  total: number;
  source: string;
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toISOString().slice(0, 16).replace("T", " ");
}

export function Prompts() {
  const navigate = useNavigate();
  const { data, loading, error, refetch } = useApi<PromptListResponse>(
    "/api/v1/prompts/list",
  );

  if (loading) {
    return (
      <PageLayout titleKey="aiflow.prompts.title">
        <LoadingState fullPage />
      </PageLayout>
    );
  }

  if (error || !data) {
    return (
      <PageLayout titleKey="aiflow.prompts.title">
        <ErrorState error={error || "Failed to load"} onRetry={refetch} />
      </PageLayout>
    );
  }

  return (
    <PageLayout titleKey="aiflow.prompts.title" source={data.source}>
      <div className="rounded-xl border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-900">
        <div className="border-b border-gray-100 px-4 py-3 dark:border-gray-800">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
            Prompts ({data.total})
          </h3>
        </div>
        {data.prompts.length === 0 ? (
          <p className="px-4 py-3 text-sm text-gray-500">No prompt YAMLs found.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm" data-testid="prompt-list">
              <thead>
                <tr className="border-b border-gray-100 text-left dark:border-gray-800">
                  <th className="px-4 py-2 text-xs font-medium uppercase text-gray-500">
                    Name
                  </th>
                  <th className="px-4 py-2 text-xs font-medium uppercase text-gray-500">
                    Version
                  </th>
                  <th className="px-4 py-2 text-xs font-medium uppercase text-gray-500">
                    Updated
                  </th>
                  <th className="px-4 py-2 text-xs font-medium uppercase text-gray-500">
                    Tags
                  </th>
                </tr>
              </thead>
              <tbody>
                {data.prompts.map((p) => (
                  <tr
                    key={p.path}
                    onClick={() => navigate(`/prompts/${p.name}`)}
                    className="cursor-pointer border-b border-gray-50 hover:bg-gray-50 dark:border-gray-800 dark:hover:bg-gray-800"
                  >
                    <td
                      className="px-4 py-2 font-medium text-gray-900 dark:text-gray-100"
                      title={p.path}
                    >
                      {p.name}
                    </td>
                    <td className="px-4 py-2 text-gray-600 dark:text-gray-400">
                      {p.version ?? "—"}
                    </td>
                    <td className="px-4 py-2 text-gray-600 dark:text-gray-400">
                      {formatDate(p.updated_at)}
                    </td>
                    <td className="px-4 py-2">
                      <div className="flex flex-wrap gap-1">
                        {p.tags.slice(0, 3).map((t) => (
                          <span
                            key={t}
                            className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-700 dark:bg-gray-800 dark:text-gray-300"
                          >
                            {t}
                          </span>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </PageLayout>
  );
}
