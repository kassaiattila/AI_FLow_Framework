/**
 * AIFlow RagDetail — Collection detail page with 3 tabs: Ingest, Chat, Chunks.
 * Accessed via /rag/:id from the Rag collections list.
 */

import { useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useTranslate } from "../lib/i18n";
import { useApi } from "../lib/hooks";
import { uploadFile, fetchApi, streamApi } from "../lib/api-client";
import { PageLayout } from "../layout/PageLayout";
import { LoadingState } from "../components-new/LoadingState";
import { ErrorState } from "../components-new/ErrorState";
import { DataTable, type Column } from "../components-new/DataTable";
import { ChatPanel } from "../components-new/ChatPanel";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface CollectionDetail {
  id: string;
  name: string;
  description: string | null;
  language: string;
  document_count: number;
  chunk_count: number;
  source: string;
}

interface IngestResponse {
  files_processed: number;
  chunks_created: number;
  duration_ms: number;
  errors: string[];
  source: string;
}

interface ChunkItem {
  chunk_id: string;
  content: string;
  document_name: string | null;
  created_at: string | null;
}

interface ChunksResponse {
  chunks: ChunkItem[];
  total: number;
  source: string;
}

/* ------------------------------------------------------------------ */
/*  Ingest Tab                                                         */
/* ------------------------------------------------------------------ */

interface CollectionDocItem {
  document_name: string;
  chunk_count: number;
  first_ingested: string | null;
}

interface CollectionDocsResponse {
  documents: CollectionDocItem[];
  total: number;
  source: string;
}

function IngestTab({ collectionId, onSuccess }: { collectionId: string; onSuccess: () => void }) {
  const translate = useTranslate();
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<IngestResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  interface IngestStep { name: string; status: "pending" | "running" | "done" | "error"; }
  const [steps, setSteps] = useState<IngestStep[]>([]);
  const { data: docsData, refetch: refetchDocs } = useApi<CollectionDocsResponse>(
    `/api/v1/rag/collections/${collectionId}/documents`,
  );
  const [selectedDocNames, setSelectedDocNames] = useState<string[]>([]);
  const [showDocBulkDelete, setShowDocBulkDelete] = useState(false);
  const [docBulkDeleting, setDocBulkDeleting] = useState(false);
  const [clearDocSel, setClearDocSel] = useState(0);

  const handleDocDelete = async (docName: string) => {
    try {
      await fetchApi<void>("DELETE", `/api/v1/rag/collections/${collectionId}/documents/${encodeURIComponent(docName)}`);
      refetchDocs();
      onSuccess();
    } catch { /* ignore */ }
  };

  const handleDocBulkDelete = async () => {
    if (selectedDocNames.length === 0 || docBulkDeleting) return;
    setDocBulkDeleting(true);
    try {
      await fetchApi<{ deleted: number }>("POST", `/api/v1/rag/collections/${collectionId}/documents/delete-bulk`, { document_names: selectedDocNames });
      setShowDocBulkDelete(false);
      setClearDocSel(c => c + 1);
      refetchDocs();
      onSuccess();
    } catch { /* keep dialog */ }
    finally { setDocBulkDeleting(false); }
  };

  const docColumns: Column<Record<string, unknown>>[] = [
    {
      key: "document_name",
      label: translate("aiflow.rag.chunkSource"),
      render: (item) => {
        const name = String((item as unknown as CollectionDocItem).document_name);
        return (
          <span className="block max-w-[300px] truncate text-sm font-medium text-gray-900 dark:text-gray-100" title={name}>
            {name}
          </span>
        );
      },
    },
    {
      key: "chunk_count",
      label: translate("aiflow.rag.statChunks"),
      width: "90",
      getValue: (item) => (item as unknown as CollectionDocItem).chunk_count,
      render: (item) => (
        <span className="whitespace-nowrap rounded-full bg-brand-50 px-2 py-0.5 text-xs font-medium text-brand-600 dark:bg-brand-900/30 dark:text-brand-400">
          {(item as unknown as CollectionDocItem).chunk_count}
        </span>
      ),
    },
    {
      key: "first_ingested",
      label: translate("aiflow.rag.chunkCreated"),
      width: "110",
      render: (item) => {
        const d = (item as unknown as CollectionDocItem).first_ingested;
        return <span className="whitespace-nowrap text-xs text-gray-500">{d ? new Date(d).toLocaleDateString() : "—"}</span>;
      },
    },
    {
      key: "actions",
      label: "",
      sortable: false,
      render: (item) => {
        const name = (item as unknown as CollectionDocItem).document_name;
        return (
          <button
            onClick={(e) => { e.stopPropagation(); void handleDocDelete(name); }}
            className="inline-flex items-center rounded-lg border border-red-200 p-1 text-red-500 hover:bg-red-50 dark:border-red-800 dark:text-red-400 dark:hover:bg-red-900/20"
            title={translate("aiflow.common.delete")}
          >
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        );
      },
    },
  ];

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const accepted = [
      "application/pdf",
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      "text/plain",
      "text/markdown",
    ];
    const dropped = Array.from(e.dataTransfer.files).filter(
      (f) => accepted.includes(f.type) || /\.(pdf|docx|txt|md)$/i.test(f.name),
    );
    setFiles((prev) => [...prev, ...dropped]);
  }, []);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFiles((prev) => [...prev, ...Array.from(e.target.files!)]);
    }
  }, []);

  const removeFile = useCallback((index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const handleIngest = async () => {
    if (files.length === 0) return;
    setUploading(true);
    setError(null);
    setResult(null);
    setSteps([
      { name: "Upload", status: "pending" },
      { name: "Parse", status: "pending" },
      { name: "Chunk", status: "pending" },
      { name: "Embed", status: "pending" },
      { name: "Store", status: "pending" },
    ]);

    try {
      const formData = new FormData();
      files.forEach((f) => formData.append("files", f));

      // Try SSE stream first, fallback to regular upload
      const token = localStorage.getItem("aiflow_token");
      const resp = await fetch(`/api/v1/rag/collections/${collectionId}/ingest-stream`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      });

      if (!resp.ok || !resp.body) {
        // Fallback: regular ingest (no streaming)
        const res = await uploadFile<IngestResponse>(
          `/api/v1/rag/collections/${collectionId}/ingest`,
          formData,
        );
        setResult(res);
        setSteps(s => s.map(st => ({ ...st, status: "done" as const })));
        if (res.errors.length === 0) {
          setFiles([]);
          onSuccess();
          refetchDocs();
        }
        return;
      }

      // SSE stream
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const msg = JSON.parse(line.slice(6));
            if (msg.event === "step_start" && msg.step !== undefined) {
              setSteps(s => s.map((st, i) => ({
                ...st,
                status: i < msg.step ? "done" : i === msg.step ? "running" : st.status,
              })));
            }
            if (msg.event === "step_done" && msg.step !== undefined) {
              setSteps(s => s.map((st, i) => ({
                ...st,
                status: i <= msg.step ? "done" : st.status,
              })));
            }
            if (msg.event === "complete") {
              setResult({
                files_processed: msg.files_processed ?? 0,
                chunks_created: msg.chunks_created ?? 0,
                duration_ms: msg.duration_ms ?? 0,
                errors: msg.errors ?? [],
                source: "backend",
              });
              setSteps(s => s.map(st => ({ ...st, status: "done" as const })));
              setFiles([]);
              onSuccess();
              refetchDocs();
            }
            if (msg.event === "error") {
              setError(msg.error ?? "Ingest failed");
              setSteps(s => s.map(st => st.status === "running" ? { ...st, status: "error" as const } : st));
            }
          } catch { /* skip non-json */ }
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ingest failed");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Dropzone */}
      <div
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
        className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-gray-300 bg-white p-8 text-center transition-colors hover:border-brand-400 dark:border-gray-600 dark:bg-gray-900 dark:hover:border-brand-500"
      >
        <svg
          className="mb-3 h-10 w-10 text-gray-300 dark:text-gray-600"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={1.5}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
          />
        </svg>
        <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
          {translate("aiflow.rag.ingestDropzone")}
        </p>
        <p className="mt-1 text-xs text-gray-400">{translate("aiflow.rag.ingestFormats")}</p>
        <label className="mt-3 cursor-pointer rounded-lg bg-brand-500 px-4 py-2 text-sm font-medium text-white hover:bg-brand-600">
          {translate("aiflow.rag.ingestButton")}
          <input
            type="file"
            accept=".pdf,.docx,.txt,.md"
            multiple
            className="hidden"
            onChange={handleFileSelect}
          />
        </label>
      </div>

      {/* File list */}
      {files.length > 0 && (
        <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              {files.length} file(s)
            </span>
            <button
              onClick={handleIngest}
              disabled={uploading}
              className="rounded-lg bg-brand-500 px-4 py-1.5 text-xs font-semibold text-white hover:bg-brand-600 disabled:opacity-50"
            >
              {uploading
                ? translate("aiflow.common.loading")
                : translate("aiflow.rag.ingestButton")}
            </button>
          </div>
          {files.map((f, i) => (
            <div
              key={i}
              className="flex items-center justify-between border-t border-gray-100 py-2 text-sm dark:border-gray-800"
            >
              <div className="flex items-center gap-2">
                <svg
                  className="h-4 w-4 text-gray-400"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"
                  />
                </svg>
                <span className="text-gray-600 dark:text-gray-400">{f.name}</span>
                <span className="text-xs text-gray-400">
                  {(f.size / 1024).toFixed(0)} KB
                </span>
              </div>
              <button
                onClick={() => removeFile(i)}
                className="text-gray-400 hover:text-red-500"
                aria-label="Remove file"
              >
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Pipeline progress bar */}
      {steps.length > 0 && (
        <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
          <p className="mb-2 text-sm font-medium text-gray-700 dark:text-gray-300">
            {translate("aiflow.pipeline.title")}
          </p>
          <div className="flex gap-2">
            {steps.map((step, i) => (
              <div key={i} className="flex flex-1 flex-col items-center gap-1">
                <div className={`h-2 w-full rounded-full ${
                  step.status === "done" ? "bg-green-500" :
                  step.status === "running" ? "bg-brand-500 animate-pulse" :
                  step.status === "error" ? "bg-red-500" :
                  "bg-gray-200 dark:bg-gray-700"
                }`} />
                <span className="text-[10px] text-gray-500">{step.name}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Error */}
      {error && <ErrorState error={error} onRetry={handleIngest} />}

      {/* Success result */}
      {result && result.errors.length === 0 && (
        <div className="rounded-xl border border-green-200 bg-green-50 p-4 dark:border-green-800 dark:bg-green-900/20">
          <p className="text-sm font-medium text-green-700 dark:text-green-400">
            {result.files_processed} {translate("aiflow.rag.ingestSuccess")} &mdash;{" "}
            {result.chunks_created} {translate("aiflow.rag.chunksCreated")}
          </p>
          {result.duration_ms > 0 && (
            <p className="mt-1 text-xs text-green-600 dark:text-green-500">
              {(result.duration_ms / 1000).toFixed(1)}s
            </p>
          )}
        </div>
      )}

      {/* Partial errors */}
      {result && result.errors.length > 0 && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 dark:border-amber-800 dark:bg-amber-900/20">
          <p className="mb-2 text-sm font-medium text-amber-700 dark:text-amber-400">
            {result.files_processed} {translate("aiflow.rag.ingestSuccess")},{" "}
            {result.errors.length} error(s)
          </p>
          <ul className="space-y-1">
            {result.errors.map((err, i) => (
              <li key={i} className="text-xs text-amber-600 dark:text-amber-400">
                {err}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Ingested documents — DataTable with delete */}
      {docsData && docsData.documents.length > 0 && (
        <div>
          <h3 className="mb-2 text-sm font-semibold text-gray-900 dark:text-gray-100">
            {translate("aiflow.rag.ingestedDocs")} ({docsData.total})
          </h3>
          {selectedDocNames.length > 0 && (
            <div className="mb-2 flex items-center gap-3 rounded-lg border border-brand-200 bg-brand-50 p-2 dark:border-brand-800 dark:bg-brand-900/20">
              <span className="text-sm font-medium text-brand-700 dark:text-brand-300">
                {selectedDocNames.length} {translate("aiflow.common.selected")}
              </span>
              <button onClick={() => setShowDocBulkDelete(true)} className="rounded-lg bg-red-600 px-3 py-1 text-xs font-semibold text-white hover:bg-red-700">
                {translate("aiflow.common.bulkDelete")}
              </button>
              <button onClick={() => setClearDocSel(c => c + 1)} className="rounded-lg border border-gray-300 px-3 py-1 text-xs font-medium text-gray-600 dark:border-gray-600 dark:text-gray-400">
                {translate("aiflow.common.cancel")}
              </button>
            </div>
          )}
          <DataTable
            data={docsData.documents as unknown as Record<string, unknown>[]}
            columns={docColumns}
            selectable
            onSelectionChange={(items) => setSelectedDocNames(items.map(i => String((i as unknown as CollectionDocItem).document_name)))}
            clearSelection={clearDocSel}
            searchKeys={["document_name"]}
            pageSize={10}
          />
        </div>
      )}

      {/* Doc bulk delete dialog */}
      {showDocBulkDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-sm rounded-xl border border-gray-200 bg-white p-6 shadow-xl dark:border-gray-700 dark:bg-gray-900">
            <h3 className="mb-2 text-lg font-semibold text-gray-900 dark:text-gray-100">
              {translate("aiflow.common.bulkDelete")}
            </h3>
            <p className="mb-4 text-sm text-gray-600 dark:text-gray-400">
              {translate("aiflow.common.bulkDeleteConfirm")} ({selectedDocNames.length})
            </p>
            <div className="flex justify-end gap-2">
              <button onClick={() => setShowDocBulkDelete(false)} className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300">
                {translate("common.action.cancel")}
              </button>
              <button onClick={() => void handleDocBulkDelete()} disabled={docBulkDeleting} className="rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700 disabled:opacity-50">
                {docBulkDeleting ? translate("aiflow.common.loading") : translate("aiflow.common.bulkDelete")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Chunks Tab                                                         */
/* ------------------------------------------------------------------ */

function ChunksTab({ collectionId }: { collectionId: string }) {
  const translate = useTranslate();
  const { data, loading, error, refetch } = useApi<ChunksResponse>(
    `/api/v1/rag/collections/${collectionId}/chunks?limit=50`,
  );

  const columns: Column<Record<string, unknown>>[] = [
    {
      key: "content",
      label: translate("aiflow.rag.chunkContent"),
      render: (item) => {
        const c = item as unknown as ChunkItem;
        const text = c.content ?? "";
        return (
          <span className="text-sm text-gray-700 dark:text-gray-300" title={text}>
            {text.length > 200 ? text.substring(0, 200) + "..." : text}
          </span>
        );
      },
    },
    {
      key: "document_name",
      label: translate("aiflow.rag.chunkSource"),
      render: (item) => {
        const c = item as unknown as ChunkItem;
        return (
          <span className="text-xs font-medium text-gray-600 dark:text-gray-400">
            {c.document_name || "---"}
          </span>
        );
      },
    },
    {
      key: "created_at",
      label: translate("aiflow.rag.chunkCreated"),
      render: (item) => {
        const c = item as unknown as ChunkItem;
        return (
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {c.created_at ? new Date(c.created_at).toLocaleDateString() : "---"}
          </span>
        );
      },
    },
  ];

  if (error) {
    return <ErrorState error={error} onRetry={refetch} />;
  }

  return (
    <DataTable
      data={(data?.chunks ?? []) as unknown as Record<string, unknown>[]}
      columns={columns}
      loading={loading}
      searchKeys={["content", "document_name"]}
      pageSize={10}
      emptyMessageKey="aiflow.rag.noChunks"
    />
  );
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                     */
/* ------------------------------------------------------------------ */

export function RagDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const translate = useTranslate();
  const [tab, setTab] = useState<"ingest" | "chat" | "chunks">("ingest");

  const { data: collection, loading, error, refetch } = useApi<CollectionDetail>(
    id ? `/api/v1/rag/collections/${id}` : null,
  );

  interface CollectionStats {
    total_queries: number;
    avg_response_time_ms: number;
    total_cost_usd: number;
    feedback_positive: number;
    feedback_negative: number;
    source: string;
  }
  const { data: stats } = useApi<CollectionStats>(
    id ? `/api/v1/rag/collections/${id}/stats` : null,
  );

  /* Loading state */
  if (loading) {
    return (
      <PageLayout titleKey="aiflow.rag.title">
        <LoadingState fullPage />
      </PageLayout>
    );
  }

  /* Error state */
  if (error) {
    return (
      <PageLayout titleKey="aiflow.rag.title">
        <ErrorState error={error} onRetry={refetch} />
      </PageLayout>
    );
  }

  /* Empty / not found state */
  if (!collection || !id) {
    return (
      <PageLayout titleKey="aiflow.rag.title">
        <ErrorState error="Collection not found" onRetry={() => navigate("/rag")} />
      </PageLayout>
    );
  }

  const tabs = [
    { key: "ingest" as const, label: translate("aiflow.rag.ingestTab") },
    { key: "chat" as const, label: translate("aiflow.rag.chatTab") },
    { key: "chunks" as const, label: translate("aiflow.rag.chunksTab") },
  ];

  return (
    <PageLayout titleKey="aiflow.rag.title" source={collection.source}>
      {/* Back button */}
      <button
        onClick={() => navigate("/rag")}
        className="mb-4 inline-flex items-center gap-1 text-sm font-medium text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
      >
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
        </svg>
        {translate("aiflow.rag.backToCollections")}
      </button>

      {/* Collection header */}
      <div className="mb-4">
        <h2 className="text-lg font-bold text-gray-900 dark:text-gray-100">{collection.name}</h2>
        {collection.description && (
          <p className="mt-0.5 text-sm text-gray-500 dark:text-gray-400">
            {collection.description}
          </p>
        )}
      </div>

      {/* KPI Cards */}
      <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-5">
        <div className="rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-900">
          <p className="text-xs font-medium text-gray-500 dark:text-gray-400">
            {translate("aiflow.rag.statDocs")}
          </p>
          <p className="mt-1 text-xl font-bold text-gray-900 dark:text-gray-100">
            {collection.document_count}
          </p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-900">
          <p className="text-xs font-medium text-gray-500 dark:text-gray-400">
            {translate("aiflow.rag.statChunks")}
          </p>
          <p className="mt-1 text-xl font-bold text-gray-900 dark:text-gray-100">
            {collection.chunk_count}
          </p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-900">
          <p className="text-xs font-medium text-gray-500 dark:text-gray-400">
            {translate("aiflow.rag.statQueries")}
          </p>
          <p className="mt-1 text-xl font-bold text-gray-900 dark:text-gray-100">
            {stats?.total_queries ?? 0}
          </p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-900">
          <p className="text-xs font-medium text-gray-500 dark:text-gray-400">
            {translate("aiflow.rag.statAvgTime")}
          </p>
          <p className="mt-1 text-xl font-bold text-gray-900 dark:text-gray-100">
            {stats?.avg_response_time_ms ? `${(stats.avg_response_time_ms / 1000).toFixed(1)}s` : "—"}
          </p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-900">
          <p className="text-xs font-medium text-gray-500 dark:text-gray-400">
            Feedback
          </p>
          <p className="mt-1 text-xl font-bold text-gray-900 dark:text-gray-100">
            <span className="text-green-600">+{stats?.feedback_positive ?? 0}</span>
            {" / "}
            <span className="text-red-500">-{stats?.feedback_negative ?? 0}</span>
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="mb-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex gap-6">
          {tabs.map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`border-b-2 pb-2 text-sm font-medium transition-colors ${
                tab === t.key
                  ? "border-brand-500 text-brand-600 dark:text-brand-400"
                  : "border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab content */}
      {tab === "ingest" && <IngestTab collectionId={id} onSuccess={refetch} />}

      {tab === "chat" && (
        <ChatPanel
          collections={[{ id: collection.id, name: collection.name }]}
          collectionId={id}
        />
      )}

      {tab === "chunks" && <ChunksTab collectionId={id} />}
    </PageLayout>
  );
}
