/**
 * RagCollections — admin UI for the multi-tenant + multi-profile vector DB
 * model introduced by Sprint S / S143 (Alembic 046). Sprint S / S144.
 *
 * Consumes:
 *   GET   /api/v1/rag-collections?tenant_id=…
 *   GET   /api/v1/rag-collections/{id}
 *   PATCH /api/v1/rag-collections/{id}/embedder-profile
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { PageLayout } from "../../layout/PageLayout";
import { ErrorState } from "../../components-new/ErrorState";
import { LoadingState } from "../../components-new/LoadingState";
import { useTranslate } from "../../lib/i18n";
import { fetchApi } from "../../lib/api-client";
import { EmbedderProfileBadge } from "./EmbedderProfileBadge";
import { RagCollectionDetailDrawer } from "./RagCollectionDetailDrawer";
import type {
  RagCollectionDetail,
  RagCollectionListItem,
  RagCollectionListResponse,
} from "./types";

export function RagCollections() {
  const t = useTranslate();
  const [searchParams, setSearchParams] = useSearchParams();
  const tenantParam = searchParams.get("tenant") ?? "";
  const [tenantDraft, setTenantDraft] = useState(tenantParam);
  const [items, setItems] = useState<RagCollectionListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<RagCollectionListItem | null>(null);

  useEffect(() => {
    setTenantDraft(tenantParam);
  }, [tenantParam]);

  const refetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const qs = tenantParam
        ? `?tenant_id=${encodeURIComponent(tenantParam)}`
        : "";
      const data = await fetchApi<RagCollectionListResponse>(
        "GET",
        `/api/v1/rag-collections${qs}`,
      );
      setItems(data.items);
      setTotal(data.total);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Fetch failed");
      setItems([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [tenantParam]);

  useEffect(() => {
    void refetch();
  }, [refetch]);

  const handleApplyTenant = () => {
    if (tenantDraft) {
      setSearchParams({ tenant: tenantDraft });
    } else {
      setSearchParams({});
    }
  };

  const handleClearTenant = () => {
    setTenantDraft("");
    setSearchParams({});
  };

  const handleDrawerSaved = (updated: RagCollectionDetail) => {
    setItems((prev) =>
      prev.map((row) =>
        row.id === updated.id
          ? {
              ...row,
              embedder_profile_id: updated.embedder_profile_id,
              embedding_dim: updated.embedding_dim,
              updated_at: updated.updated_at,
            }
          : row,
      ),
    );
  };

  const tableHeader = useMemo(
    () => [
      { key: "name", label: t("aiflow.ragCollections.column.name") },
      { key: "tenant", label: t("aiflow.ragCollections.column.tenant") },
      {
        key: "profile",
        label: t("aiflow.ragCollections.column.embedderProfile"),
      },
      { key: "dim", label: t("aiflow.ragCollections.column.embeddingDim") },
      { key: "chunks", label: t("aiflow.ragCollections.column.chunks") },
      { key: "updated", label: t("aiflow.ragCollections.column.updated") },
    ],
    [t],
  );

  return (
    <PageLayout
      titleKey="aiflow.ragCollections.title"
      subtitleKey="aiflow.ragCollections.subtitle"
      source="live"
    >
      <div
        data-testid="rag-collections-filter"
        className="mb-4 flex flex-wrap items-end gap-2 rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-900"
      >
        <div className="flex flex-col">
          <label
            htmlFor="rag-collections-tenant-input"
            className="text-xs font-semibold uppercase tracking-wide text-gray-500"
          >
            {t("aiflow.ragCollections.filter.tenant")}
          </label>
          <input
            id="rag-collections-tenant-input"
            data-testid="rag-collections-tenant-input"
            type="text"
            value={tenantDraft}
            onChange={(e) => setTenantDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleApplyTenant();
            }}
            placeholder="default | bestix | doha"
            className="mt-1 rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100"
          />
        </div>
        <button
          type="button"
          onClick={handleApplyTenant}
          data-testid="rag-collections-tenant-apply"
          className="rounded-lg bg-brand-500 px-3 py-1.5 text-sm font-semibold text-white hover:bg-brand-600"
        >
          {t("aiflow.ragCollections.filter.apply")}
        </button>
        {tenantParam && (
          <button
            type="button"
            onClick={handleClearTenant}
            data-testid="rag-collections-tenant-clear"
            className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-800"
          >
            {t("aiflow.ragCollections.filter.clear")}
          </button>
        )}
        <span
          className="ml-auto text-xs text-gray-500"
          data-testid="rag-collections-total"
        >
          {total} {total === 1 ? "collection" : "collections"}
        </span>
      </div>

      {loading && <LoadingState />}
      {error && <ErrorState error={error} onRetry={() => void refetch()} />}

      {!loading && !error && items.length === 0 && (
        <div
          data-testid="rag-collections-empty"
          className="rounded-xl border border-dashed border-gray-300 bg-gray-50 p-6 text-center text-sm text-gray-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-400"
        >
          {t("aiflow.ragCollections.empty")}
        </div>
      )}

      {!loading && !error && items.length > 0 && (
        <div
          data-testid="rag-collections-table"
          className="overflow-hidden rounded-xl border border-gray-200 dark:border-gray-700"
        >
          <table className="w-full text-left text-sm">
            <thead className="bg-gray-50 dark:bg-gray-800/60">
              <tr>
                {tableHeader.map((h) => (
                  <th
                    key={h.key}
                    scope="col"
                    className="px-3 py-2 text-xs font-semibold uppercase tracking-wide text-gray-600 dark:text-gray-300"
                  >
                    {h.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 bg-white dark:divide-gray-700 dark:bg-gray-900">
              {items.map((row) => (
                <tr
                  key={row.id}
                  data-testid="rag-collections-row"
                  data-collection-id={row.id}
                  data-tenant={row.tenant_id}
                  className="cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/40"
                  onClick={() => setSelected(row)}
                >
                  <td className="px-3 py-2 font-medium text-gray-900 dark:text-gray-100">
                    {row.name}
                  </td>
                  <td className="px-3 py-2 text-gray-700 dark:text-gray-200">
                    {row.tenant_id}
                  </td>
                  <td className="px-3 py-2">
                    <EmbedderProfileBadge profileId={row.embedder_profile_id} />
                  </td>
                  <td className="px-3 py-2 text-gray-700 dark:text-gray-200">
                    {row.embedding_dim}
                  </td>
                  <td className="px-3 py-2 text-gray-700 dark:text-gray-200">
                    {row.chunk_count}
                  </td>
                  <td className="px-3 py-2 text-gray-500 dark:text-gray-400">
                    {row.updated_at?.slice(0, 19).replace("T", " ") ?? "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {selected && (
        <RagCollectionDetailDrawer
          collection={selected}
          onClose={() => setSelected(null)}
          onSaved={handleDrawerSaved}
        />
      )}
    </PageLayout>
  );
}
