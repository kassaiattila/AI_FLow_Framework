/**
 * AIFlow RagDetail — Collection detail page with 3 tabs: Ingest, Chat, Chunks.
 * Accessed via /rag/:id from the Rag collections list.
 */

import { useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useTranslate } from "../lib/i18n";
import { useApi } from "../lib/hooks";
import { uploadFile } from "../lib/api-client";
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

function IngestTab({ collectionId, onSuccess }: { collectionId: string; onSuccess: () => void }) {
  const translate = useTranslate();
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<IngestResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

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
    try {
      const formData = new FormData();
      files.forEach((f) => formData.append("files", f));
      const res = await uploadFile<IngestResponse>(
        `/api/v1/rag/collections/${collectionId}/ingest`,
        formData,
      );
      setResult(res);
      if (res.errors.length === 0) {
        setFiles([]);
        onSuccess();
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

      {/* Uploading state */}
      {uploading && (
        <div className="flex items-center gap-3 rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-brand-200 border-t-brand-500" />
          <span className="text-sm text-gray-600 dark:text-gray-400">
            {translate("aiflow.common.loading")}
          </span>
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
      <div className="mb-4 grid grid-cols-1 gap-4 md:grid-cols-2">
        <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
          <p className="text-xs font-medium text-gray-500 dark:text-gray-400">
            {translate("aiflow.rag.statDocs")}
          </p>
          <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-gray-100">
            {collection.document_count}
          </p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
          <p className="text-xs font-medium text-gray-500 dark:text-gray-400">
            {translate("aiflow.rag.statChunks")}
          </p>
          <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-gray-100">
            {collection.chunk_count}
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
