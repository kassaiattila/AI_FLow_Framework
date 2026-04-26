/**
 * Document Recognizer — admin UI for the generic doc-type registry.
 * Sprint V SV-4.
 *
 * Consumes:
 *   GET    /api/v1/document-recognizer/doctypes
 *   GET    /api/v1/document-recognizer/doctypes/{name}
 *   PUT    /api/v1/document-recognizer/doctypes/{name}
 *   DELETE /api/v1/document-recognizer/doctypes/{name}
 *   POST   /api/v1/document-recognizer/recognize
 *
 * Browse view: doc-type list table + Recognize tab + DocTypeEditor side drawer.
 */

import { useCallback, useEffect, useState } from "react";
import { PageLayout } from "../../layout/PageLayout";
import { ErrorState } from "../../components-new/ErrorState";
import { LoadingState } from "../../components-new/LoadingState";
import { fetchApi } from "../../lib/api-client";
import { PiiBadge } from "./PiiBadge";
import { DocTypeDetailDrawer } from "./DocTypeDetailDrawer";
import { RecognizePanel } from "./RecognizePanel";
import type {
  DoctypeDetailResponse,
  DoctypeListItem,
  DoctypeListResponse,
} from "./types";

type Tab = "browse" | "recognize";

export function DocumentRecognizer() {
  const [tab, setTab] = useState<Tab>("browse");
  const [items, setItems] = useState<DoctypeListItem[]>([]);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<DoctypeListItem | null>(null);
  const [drawerData, setDrawerData] = useState<DoctypeDetailResponse | null>(null);

  const refetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchApi<DoctypeListResponse>(
        "GET",
        "/api/v1/document-recognizer/doctypes",
      );
      setItems(data.items);
      setCount(data.count);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Fetch failed");
      setItems([]);
      setCount(0);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (tab === "browse") void refetch();
  }, [tab, refetch]);

  const handleSelectDoctype = async (item: DoctypeListItem) => {
    setSelected(item);
    try {
      const detail = await fetchApi<DoctypeDetailResponse>(
        "GET",
        `/api/v1/document-recognizer/doctypes/${encodeURIComponent(item.name)}`,
      );
      setDrawerData(detail);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Detail fetch failed");
      setDrawerData(null);
    }
  };

  const handleDrawerClose = () => {
    setSelected(null);
    setDrawerData(null);
  };

  const handleDrawerSaved = async () => {
    await refetch();
    handleDrawerClose();
  };

  return (
    <PageLayout
      title="Document Recognizer"
      description="Pluggable doc-type registry — invoice / ID card / contract / passport / address card."
    >
      <div className="mb-4 flex gap-2 border-b border-gray-200 dark:border-gray-700">
        <button
          type="button"
          className={`px-4 py-2 text-sm font-medium ${
            tab === "browse"
              ? "border-b-2 border-blue-600 text-blue-600 dark:text-blue-400"
              : "text-gray-600 hover:text-gray-900 dark:text-gray-400"
          }`}
          onClick={() => setTab("browse")}
          data-testid="tab-browse"
        >
          Browse
        </button>
        <button
          type="button"
          className={`px-4 py-2 text-sm font-medium ${
            tab === "recognize"
              ? "border-b-2 border-blue-600 text-blue-600 dark:text-blue-400"
              : "text-gray-600 hover:text-gray-900 dark:text-gray-400"
          }`}
          onClick={() => setTab("recognize")}
          data-testid="tab-recognize"
        >
          Recognize
        </button>
      </div>

      {tab === "browse" && (
        <>
          {loading && <LoadingState message="Loading doc-types…" />}
          {error && <ErrorState title="Failed to load" message={error} />}
          {!loading && !error && (
            <div className="overflow-hidden rounded-lg border border-gray-200 dark:border-gray-700">
              <div className="border-b border-gray-200 bg-gray-50 px-4 py-2 text-xs text-gray-600 dark:border-gray-700 dark:bg-gray-800/50 dark:text-gray-400">
                {count} doc-type{count === 1 ? "" : "s"} registered
              </div>
              <table className="w-full" data-testid="doctype-list">
                <thead className="bg-gray-50 text-left text-xs uppercase text-gray-500 dark:bg-gray-800/50 dark:text-gray-400">
                  <tr>
                    <th className="px-4 py-2">Name</th>
                    <th className="px-4 py-2">Display</th>
                    <th className="px-4 py-2">Lang</th>
                    <th className="px-4 py-2">Category</th>
                    <th className="px-4 py-2">PII</th>
                    <th className="px-4 py-2">Fields</th>
                    <th className="px-4 py-2">Source</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 text-sm dark:divide-gray-700">
                  {items.map((item) => (
                    <tr
                      key={item.name}
                      className="cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/30"
                      onClick={() => handleSelectDoctype(item)}
                      data-testid={`doctype-row-${item.name}`}
                    >
                      <td className="px-4 py-3 font-mono text-xs">{item.name}</td>
                      <td className="px-4 py-3">{item.display_name}</td>
                      <td className="px-4 py-3 text-xs uppercase text-gray-500">
                        {item.language}
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-500">{item.category}</td>
                      <td className="px-4 py-3">
                        <PiiBadge level={item.pii_level} />
                      </td>
                      <td className="px-4 py-3 text-right">{item.field_count}</td>
                      <td className="px-4 py-3 text-xs">
                        {item.has_tenant_override ? (
                          <span
                            className="rounded bg-purple-100 px-2 py-0.5 text-purple-800 dark:bg-purple-900 dark:text-purple-200"
                            data-testid={`override-badge-${item.name}`}
                          >
                            Tenant override
                          </span>
                        ) : (
                          <span className="text-gray-400">Bootstrap</span>
                        )}
                      </td>
                    </tr>
                  ))}
                  {items.length === 0 && (
                    <tr>
                      <td
                        colSpan={7}
                        className="px-4 py-8 text-center text-sm text-gray-500"
                      >
                        No doc-types registered. Operators can add YAML
                        descriptors at <code>data/doctypes/</code>.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {tab === "recognize" && <RecognizePanel doctypes={items} />}

      {selected && drawerData && (
        <DocTypeDetailDrawer
          item={selected}
          detail={drawerData}
          onClose={handleDrawerClose}
          onSaved={handleDrawerSaved}
        />
      )}
    </PageLayout>
  );
}
