/**
 * ChunkViewer — paginated RAG chunk browser with detail modal.
 *
 * S102 surfaces the S101 `embedding_dim` column plus `chunk_index` and the
 * token_count metadata derived from the chunker.
 */

import { useEffect, useMemo, useState } from "react";
import { useTranslate } from "../../lib/i18n";
import { useApi } from "../../lib/hooks";
import { DataTable, type Column } from "../../components-new/DataTable";
import { ErrorState } from "../../components-new/ErrorState";

export interface ChunkItem {
  chunk_id: string;
  content: string;
  document_name: string | null;
  created_at: string | null;
  chunk_index: number;
  token_count: number | null;
  embedding_dim: number | null;
  metadata: Record<string, unknown>;
}

interface ChunksResponse {
  chunks: ChunkItem[];
  total: number;
  source: string;
}

interface ChunkViewerProps {
  collectionId: string;
  pageSize?: number;
}

export function ChunkViewer({ collectionId, pageSize = 25 }: ChunkViewerProps) {
  const translate = useTranslate();
  const [searchQuery, setSearchQuery] = useState("");
  const [filterDoc, setFilterDoc] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [selected, setSelected] = useState<ChunkItem | null>(null);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQuery(searchQuery), 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  const chunksUrl = useMemo(() => {
    const p = new URLSearchParams();
    p.set("limit", "200");
    if (debouncedQuery) p.set("q", debouncedQuery);
    if (filterDoc) p.set("document_name", filterDoc);
    return `/api/v1/rag/collections/${collectionId}/chunks?${p.toString()}`;
  }, [collectionId, debouncedQuery, filterDoc]);

  const { data, loading, error, refetch } = useApi<ChunksResponse>(chunksUrl);

  const columns: Column<Record<string, unknown>>[] = [
    {
      key: "chunk_index",
      label: translate("aiflow.rag.chunkIndex"),
      width: "60",
      getValue: (item) => (item as unknown as ChunkItem).chunk_index,
      render: (item) => (
        <span className="inline-flex min-w-[28px] justify-center rounded-md bg-gray-100 px-1.5 py-0.5 font-mono text-xs text-gray-700 dark:bg-gray-800 dark:text-gray-300">
          {(item as unknown as ChunkItem).chunk_index}
        </span>
      ),
    },
    {
      key: "content",
      label: translate("aiflow.rag.chunkContent"),
      render: (item) => {
        const c = item as unknown as ChunkItem;
        const text = c.content ?? "";
        return (
          <span
            className="line-clamp-3 text-sm text-gray-700 dark:text-gray-300"
            title={text}
          >
            {text}
          </span>
        );
      },
    },
    {
      key: "document_name",
      label: translate("aiflow.rag.chunkSource"),
      render: (item) => (
        <span
          className="block max-w-[200px] truncate text-xs font-medium text-gray-600 dark:text-gray-400"
          title={(item as unknown as ChunkItem).document_name ?? ""}
        >
          {(item as unknown as ChunkItem).document_name || "—"}
        </span>
      ),
    },
    {
      key: "token_count",
      label: translate("aiflow.rag.chunkTokens"),
      width: "80",
      getValue: (item) => (item as unknown as ChunkItem).token_count ?? 0,
      render: (item) => {
        const tc = (item as unknown as ChunkItem).token_count;
        return (
          <span className="whitespace-nowrap text-xs text-gray-500 dark:text-gray-400">
            {tc ?? "—"}
          </span>
        );
      },
    },
    {
      key: "embedding_dim",
      label: translate("aiflow.rag.chunkEmbeddingDim"),
      width: "80",
      getValue: (item) => (item as unknown as ChunkItem).embedding_dim ?? 0,
      render: (item) => {
        const d = (item as unknown as ChunkItem).embedding_dim;
        return d ? (
          <span
            data-testid="chunk-embedding-dim"
            className="inline-flex whitespace-nowrap rounded-full bg-brand-50 px-2 py-0.5 font-mono text-[11px] font-semibold text-brand-700 dark:bg-brand-900/30 dark:text-brand-300"
          >
            {d}
          </span>
        ) : (
          <span className="text-xs text-gray-400">—</span>
        );
      },
    },
    {
      key: "created_at",
      label: translate("aiflow.rag.chunkCreated"),
      width: "110",
      render: (item) => {
        const c = item as unknown as ChunkItem;
        return (
          <span className="whitespace-nowrap text-xs text-gray-500 dark:text-gray-400">
            {c.created_at ? new Date(c.created_at).toLocaleDateString() : "—"}
          </span>
        );
      },
    },
  ];

  if (error) {
    return <ErrorState error={error} onRetry={refetch} />;
  }

  const docOptions = [
    ...new Set(
      (data?.chunks ?? []).map((c) => c.document_name).filter(Boolean),
    ),
  ] as string[];

  return (
    <div data-testid="chunk-viewer">
      <div className="mb-4 flex items-center gap-3">
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder={translate("aiflow.rag.chunkSearch")}
          data-testid="chunk-search"
          className="flex-1 rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-900 placeholder-gray-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 dark:placeholder-gray-500"
        />
        <select
          value={filterDoc}
          onChange={(e) => setFilterDoc(e.target.value)}
          className="rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300"
        >
          <option value="">— {translate("aiflow.rag.chunkSource")} —</option>
          {docOptions.map((d) => (
            <option key={d} value={d}>
              {d}
            </option>
          ))}
        </select>
        {(debouncedQuery || filterDoc) && (
          <button
            onClick={() => {
              setSearchQuery("");
              setFilterDoc("");
            }}
            className="text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          >
            {translate("common.action.clear_input_value")}
          </button>
        )}
      </div>
      {data && (
        <p className="mb-2 text-xs text-gray-500 dark:text-gray-400">
          {data.total} chunk(s) · source: {data.source}
        </p>
      )}
      <DataTable
        data={(data?.chunks ?? []) as unknown as Record<string, unknown>[]}
        columns={columns}
        loading={loading}
        searchKeys={["content", "document_name"]}
        pageSize={pageSize}
        emptyMessageKey="aiflow.rag.noChunks"
        onRowClick={(row) => setSelected(row as unknown as ChunkItem)}
      />

      {selected && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
          onClick={() => setSelected(null)}
          data-testid="chunk-detail-modal"
        >
          <div
            className="max-h-[85vh] w-full max-w-3xl overflow-hidden rounded-xl border border-gray-200 bg-white shadow-2xl dark:border-gray-700 dark:bg-gray-900"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b border-gray-200 px-5 py-3 dark:border-gray-700">
              <div className="min-w-0">
                <h3 className="truncate text-sm font-semibold text-gray-900 dark:text-gray-100">
                  {translate("aiflow.rag.chunkDetailTitle")}
                  {" — #"}
                  {selected.chunk_index}
                </h3>
                <p className="mt-0.5 truncate text-xs text-gray-500 dark:text-gray-400">
                  {selected.document_name || "—"}
                </p>
              </div>
              <button
                onClick={() => setSelected(null)}
                className="rounded-md p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-800"
                aria-label="Close"
              >
                <svg
                  className="h-5 w-5"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>
            <div className="max-h-[70vh] overflow-y-auto p-5">
              <div className="mb-3 flex flex-wrap gap-2">
                {selected.embedding_dim != null && (
                  <span className="inline-flex rounded-full bg-brand-50 px-2 py-0.5 font-mono text-[11px] font-semibold text-brand-700 dark:bg-brand-900/30 dark:text-brand-300">
                    dim {selected.embedding_dim}
                  </span>
                )}
                {selected.token_count != null && (
                  <span className="inline-flex rounded-full bg-gray-100 px-2 py-0.5 font-mono text-[11px] text-gray-700 dark:bg-gray-800 dark:text-gray-300">
                    {selected.token_count}{" "}
                    {translate("aiflow.rag.chunkTokens").toLowerCase()}
                  </span>
                )}
                {selected.created_at && (
                  <span className="inline-flex rounded-full bg-gray-100 px-2 py-0.5 text-[11px] text-gray-600 dark:bg-gray-800 dark:text-gray-400">
                    {new Date(selected.created_at).toLocaleString()}
                  </span>
                )}
              </div>
              <pre className="mb-4 max-h-72 overflow-auto whitespace-pre-wrap rounded-lg bg-gray-50 p-3 text-xs text-gray-800 dark:bg-gray-800 dark:text-gray-200">
                {selected.content}
              </pre>
              <div>
                <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
                  {translate("aiflow.rag.chunkMetadata")}
                </p>
                <pre className="max-h-56 overflow-auto rounded-lg bg-gray-900 p-3 text-[11px] leading-relaxed text-gray-100">
                  {JSON.stringify(selected.metadata ?? {}, null, 2)}
                </pre>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
