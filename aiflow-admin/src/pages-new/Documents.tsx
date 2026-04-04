/**
 * AIFlow Documents — F6.2 tabbed page (List + Upload).
 * Replaces old DocumentList + DocumentUpload + DocumentShow.
 */

import { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslate } from "../lib/i18n";
import { useApi } from "../lib/hooks";
import { fetchApi, uploadFile, streamApi } from "../lib/api-client";
import { PageLayout } from "../layout/PageLayout";
import { LoadingState } from "../components-new/LoadingState";
import { ErrorState } from "../components-new/ErrorState";
import { EmptyState } from "../components-new/EmptyState";
import { DataTable, type Column } from "../components-new/DataTable";
import { FileProgressRow, FileProgressBar, type FileProgress } from "../components-new/FileProgress";

// --- Types ---

interface DocVendor {
  name: string | null;
  address: string | null;
  tax_number: string | null;
}

interface DocHeader {
  invoice_number: string | null;
  invoice_date: string | null;
  currency: string | null;
}

interface DocTotals {
  gross_total: number | null;
}

interface DocValidation {
  is_valid: boolean | null;
}

interface DocItem {
  id: string;
  source_file: string;
  direction: string;
  vendor: DocVendor | null;
  header: DocHeader | null;
  totals: DocTotals | null;
  validation: DocValidation | null;
  extraction_confidence: number | null;
  created_at: string | null;
}

interface DocsResponse {
  documents: DocItem[];
  total: number;
  source: string;
}

// --- Helpers ---

function fileName(path: string): string {
  return path.split(/[/\\]/).pop() ?? path;
}

function confidenceColor(conf: number | null): string {
  if (!conf) return "text-gray-400";
  const pct = conf <= 1 ? conf * 100 : conf; // handle 0-1 or 0-100 scale
  if (pct >= 90) return "text-green-600 dark:text-green-400";
  if (pct >= 70) return "text-amber-600 dark:text-amber-400";
  return "text-red-600 dark:text-red-400";
}

function statusBadge(doc: DocItem): { label: string; color: string } {
  if (doc.validation?.is_valid === true) {
    return { label: "Verified", color: "bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-400" };
  }
  if (doc.extraction_confidence && doc.extraction_confidence > 0) {
    return { label: "Processed", color: "bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400" };
  }
  return { label: "Pending", color: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400" };
}

// --- Upload Tab ---

function UploadTab({ onUploadComplete }: { onUploadComplete?: () => void }) {
  const translate = useTranslate();
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [fileProgress, setFileProgress] = useState<FileProgress[]>([]);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const dropped = Array.from(e.dataTransfer.files).filter(f => f.type === "application/pdf");
    setFiles(prev => [...prev, ...dropped]);
  }, []);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFiles(prev => [...prev, ...Array.from(e.target.files!)]);
    }
  }, []);

  const handleUpload = async () => {
    if (files.length === 0) return;
    setUploading(true);
    setError(null);
    setResult(null);
    setFileProgress([]);
    try {
      const formData = new FormData();
      files.forEach(f => formData.append("files", f));
      await uploadFile("/api/v1/documents/upload", formData);
      setUploading(false);
      setProcessing(true);

      // Initialize per-file progress immediately so the UI shows the grid
      const defaultSteps = ["parse", "classify", "extract", "validate", "store"];
      setFileProgress(files.map(f => ({
        name: f.name,
        status: "pending" as const,
        steps: defaultSteps.map(s => ({ name: s, status: "pending" as const })),
      })));

      streamApi(
        `/api/v1/documents/process-stream`,
        (data) => {
          try {
            const msg = JSON.parse(data);

            // New per-file events (v1.1.4+)
            if (msg.event === "init") {
              const stepNames: string[] = msg.steps ?? defaultSteps;
              setFileProgress(files.map(f => ({
                name: f.name,
                status: "pending" as const,
                steps: stepNames.map(s => ({ name: s, status: "pending" as const })),
              })));
            }

            if (msg.event === "file_start" && msg.file_index !== undefined) {
              setFileProgress(prev => prev.map((fp, i) =>
                i === msg.file_index ? { ...fp, status: "processing" } : fp
              ));
            }

            if (msg.event === "file_step" && msg.file_index !== undefined && msg.step_index !== undefined) {
              setFileProgress(prev => prev.map((fp, i) => {
                if (i !== msg.file_index) return fp;
                return {
                  ...fp,
                  steps: fp.steps.map((s, si) => {
                    if (si !== msg.step_index) return s;
                    return {
                      ...s,
                      status: msg.status === "done" ? "done" : msg.status === "running" ? "running" : s.status,
                      elapsed_ms: msg.elapsed_ms ?? s.elapsed_ms,
                    };
                  }),
                };
              }));
            }

            if (msg.event === "file_error" && msg.file_index !== undefined) {
              setFileProgress(prev => prev.map((fp, i) =>
                i === msg.file_index ? { ...fp, status: "error", error: msg.error } : fp
              ));
            }

            if (msg.event === "file_done" && msg.file_index !== undefined) {
              setFileProgress(prev => prev.map((fp, i) =>
                i === msg.file_index
                  ? { ...fp, status: msg.ok ? "done" : "error" }
                  : fp
              ));
            }

            // Legacy batch events (backward compat with old backend)
            if (msg.event === "step_start" && msg.step !== undefined) {
              setFileProgress(prev => {
                // In batch mode, show all files as processing on the current step
                return prev.map(fp => ({
                  ...fp,
                  status: "processing" as const,
                  steps: fp.steps.map((s, si) => ({
                    ...s,
                    status: si < msg.step ? "done" as const : si === msg.step ? "running" as const : s.status,
                  })),
                }));
              });
            }
            if (msg.event === "step_done" && msg.step !== undefined) {
              setFileProgress(prev => prev.map(fp => ({
                ...fp,
                steps: fp.steps.map((s, si) => ({
                  ...s,
                  status: si <= msg.step ? "done" as const : s.status,
                  elapsed_ms: si === msg.step ? msg.elapsed_ms : s.elapsed_ms,
                })),
              })));
            }
            if (msg.event === "error" && msg.name) {
              setError(`Step ${msg.name} failed: ${msg.error}`);
              setProcessing(false);
            }

            if (msg.event === "complete") {
              const results = msg.results ?? [];
              const ok = results.filter((r: Record<string, unknown>) => !r.error).length;
              setResult(`${ok}/${files.length} ${translate("aiflow.documentUpload.files")} processed`);
              setProcessing(false);
              setFileProgress(prev => prev.map(fp => ({ ...fp, status: "done" as const, steps: fp.steps.map(s => ({ ...s, status: "done" as const })) })));
              onUploadComplete?.();
            }
          } catch { /* ignore non-json */ }
        },
        () => { setProcessing(false); },
        () => { setProcessing(false); },
        { method: "POST", body: { files: files.map(f => f.name) } },
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
      setUploading(false);
      setProcessing(false);
    }
  };

  const handleReset = () => {
    setFiles([]);
    setFileProgress([]);
    setResult(null);
    setError(null);
  };

  const doneCount = fileProgress.filter(fp => fp.status === "done").length;
  const totalCount = fileProgress.length;

  return (
    <div className="space-y-4">
      {/* Dropzone */}
      <div
        onDragOver={e => e.preventDefault()}
        onDrop={handleDrop}
        className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-gray-300 bg-white p-8 text-center transition-colors hover:border-brand-400 dark:border-gray-600 dark:bg-gray-900 dark:hover:border-brand-500"
      >
        <svg className="mb-3 h-10 w-10 text-gray-300 dark:text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
        </svg>
        <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
          {translate("aiflow.documentUpload.dropzone")}
        </p>
        <p className="mt-1 text-xs text-gray-400">PDF (max 20MB)</p>
        <label className="mt-3 cursor-pointer rounded-lg bg-brand-500 px-4 py-2 text-sm font-medium text-white hover:bg-brand-600">
          {translate("aiflow.documentUpload.uploaded")}
          <input type="file" accept=".pdf" multiple className="hidden" onChange={handleFileSelect} />
        </label>
      </div>

      {/* File list (before processing) */}
      {files.length > 0 && fileProgress.length === 0 && (
        <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              {files.length} {translate("aiflow.documentUpload.files")}
            </span>
            <div className="flex gap-2">
              <button
                onClick={handleReset}
                className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-400"
              >
                {translate("aiflow.documentUpload.newBatch")}
              </button>
              <button
                onClick={handleUpload}
                disabled={uploading || processing}
                className="rounded-lg bg-brand-500 px-4 py-1.5 text-xs font-semibold text-white hover:bg-brand-600 disabled:opacity-50"
              >
                {uploading ? translate("aiflow.common.loading") : translate("aiflow.documentUpload.process")}
              </button>
            </div>
          </div>
          {files.map((f, i) => (
            <div key={i} className="flex items-center gap-2 border-t border-gray-100 py-2 text-sm dark:border-gray-800">
              <span className="text-gray-600 dark:text-gray-400">{f.name}</span>
              <span className="text-xs text-gray-400">{(f.size / 1024).toFixed(0)} KB</span>
            </div>
          ))}
        </div>
      )}

      {/* Per-file pipeline progress */}
      {fileProgress.length > 0 && (
        <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
          <div className="mb-2 flex items-center justify-between">
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
              {translate("aiflow.pipeline.title")}
            </p>
            {processing && (
              <span className="text-xs text-brand-600 dark:text-brand-400">
                {doneCount}/{totalCount}
              </span>
            )}
          </div>
          <FileProgressBar done={doneCount} total={totalCount} />
          <div>
            {fileProgress.map((fp, i) => (
              <FileProgressRow key={i} fp={fp} />
            ))}
          </div>
          {!processing && !result && (
            <button
              onClick={handleReset}
              className="mt-3 rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-400"
            >
              {translate("aiflow.documentUpload.newBatch")}
            </button>
          )}
        </div>
      )}

      {error && <ErrorState error={error} onRetry={handleUpload} />}
      {result && (
        <div className="rounded-xl border border-green-200 bg-green-50 p-4 dark:border-green-800 dark:bg-green-900/20">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-green-700 dark:text-green-400">{result}</span>
            <button
              onClick={handleReset}
              className="rounded-lg border border-green-300 px-3 py-1.5 text-xs font-medium text-green-700 hover:bg-green-100 dark:border-green-700 dark:text-green-400 dark:hover:bg-green-900/40"
            >
              {translate("aiflow.documentUpload.newBatch")}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// --- Document Table Columns (factory — needs translate) ---

function makeDocColumns(translate: (key: string) => string, onDelete?: (id: string) => void): Column<Record<string, unknown>>[] { return [
  {
    key: "source_file",
    label: translate("aiflow.documents.file"),
    getValue: (item) => fileName(String(item.source_file ?? "")),
    render: (item) => (
      <span className="block max-w-[200px] truncate font-medium text-gray-900 dark:text-gray-100" title={fileName(String(item.source_file ?? ""))}>
        {fileName(String(item.source_file ?? ""))}
      </span>
    ),
  },
  {
    key: "status",
    label: translate("aiflow.runs.status"),
    sortable: false,
    render: (item) => {
      const badge = statusBadge(item as unknown as DocItem);
      return (
        <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${badge.color}`}>
          {badge.label}
        </span>
      );
    },
  },
  {
    key: "vendor.name",
    label: translate("aiflow.documents.vendor"),
    getValue: (item) => (item.vendor as DocVendor | null)?.name ?? "",
    render: (item) => (
      <span className="block max-w-[160px] truncate text-gray-600 dark:text-gray-400" title={(item.vendor as DocVendor | null)?.name ?? ""}>
        {(item.vendor as DocVendor | null)?.name ?? "—"}
      </span>
    ),
  },
  {
    key: "header.invoice_number",
    label: translate("aiflow.documents.invoiceNumber"),
    getValue: (item) => (item.header as DocHeader | null)?.invoice_number ?? "",
    render: (item) => (
      <span className="text-xs text-gray-600 dark:text-gray-400">
        {(item.header as DocHeader | null)?.invoice_number ?? "—"}
      </span>
    ),
  },
  {
    key: "totals.gross_total",
    label: translate("aiflow.documents.grossTotal"),
    getValue: (item) => (item.totals as DocTotals | null)?.gross_total ?? 0,
    render: (item) => {
      const total = (item.totals as DocTotals | null)?.gross_total;
      const currency = (item.header as DocHeader | null)?.currency ?? "HUF";
      return (
        <span className="whitespace-nowrap text-xs text-gray-600 dark:text-gray-400">
          {total ? `${total.toLocaleString()} ${currency}` : "—"}
        </span>
      );
    },
  },
  {
    key: "extraction_confidence",
    label: "%",
    getValue: (item) => (item.extraction_confidence as number | null) ?? 0,
    render: (item) => {
      const conf = item.extraction_confidence as number | null;
      return (
        <span className={`text-xs font-medium ${confidenceColor(conf)}`}>
          {conf ? `${Math.round(conf * 100)}%` : "—"}
        </span>
      );
    },
  },
  {
    key: "actions",
    label: "",
    sortable: false,
    render: (item) => {
      const docId = (item as unknown as DocItem).id;
      if (!docId) return null;
      return (
        <div className="flex shrink-0 items-center gap-2">
          <a
            href={`#/documents/${encodeURIComponent(docId)}/verify`}
            onClick={(e) => e.stopPropagation()}
            className="inline-flex items-center rounded-md border border-brand-300 px-1.5 py-1 text-brand-600 hover:bg-brand-50 dark:border-brand-700 dark:text-brand-400 dark:hover:bg-brand-900/20"
            title="Verify"
          >
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </a>
          {onDelete && (
            <button
              onClick={(e) => { e.stopPropagation(); onDelete(docId); }}
              className="inline-flex items-center rounded-md border border-red-200 px-1.5 py-1 text-red-500 hover:bg-red-50 dark:border-red-800 dark:text-red-400 dark:hover:bg-red-900/20"
              title={translate("aiflow.documents.deleteTitle")}
            >
              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          )}
        </div>
      );
    },
  },
]; }

// --- Main Component ---

interface ExtractorConfig { name: string; display_name: string; document_type: string; field_count: number; enabled: boolean; }
interface ConfigsResponse { configs: ExtractorConfig[]; total: number; source: string; }

export function Documents() {
  const translate = useTranslate();
  const navigate = useNavigate();
  const [tab, setTab] = useState<"list" | "upload">("list");
  const [selectedConfig, setSelectedConfig] = useState<string>("all");
  const { data, loading, error, refetch } = useApi<DocsResponse>("/api/v1/documents");
  const { data: configsData } = useApi<ConfigsResponse>("/api/v1/documents/extractor/configs");
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [selectedDocs, setSelectedDocs] = useState<Record<string, unknown>[]>([]);
  const [bulkDeleting, setBulkDeleting] = useState(false);
  const [showBulkDelete, setShowBulkDelete] = useState(false);
  const [clearSel, setClearSel] = useState(0);

  const docs = data?.documents ?? [];
  const total = data?.total ?? 0;
  const processed = docs.filter(d => d.extraction_confidence && d.extraction_confidence > 0).length;
  const pending = docs.filter(d => !d.extraction_confidence || d.extraction_confidence === 0).length;

  const handleDelete = async () => {
    if (!deleteId || deleting) return;
    setDeleting(true);
    try {
      await fetchApi<void>("DELETE", `/api/v1/documents/delete/${deleteId}`);
      setDeleteId(null);
      refetch();
    } catch {
      // keep dialog open on error
    } finally {
      setDeleting(false);
    }
  };

  const handleBulkDelete = async () => {
    if (selectedDocs.length === 0 || bulkDeleting) return;
    setBulkDeleting(true);
    try {
      const ids = selectedDocs.map(d => (d as unknown as DocItem).id).filter(Boolean);
      await fetchApi<{ deleted: number }>("POST", "/api/v1/documents/delete-bulk", { ids });
      setShowBulkDelete(false);
      setClearSel(c => c + 1);
      refetch();
    } catch {
      // keep dialog open
    } finally {
      setBulkDeleting(false);
    }
  };

  return (
    <PageLayout
      titleKey="aiflow.documents.title"
      subtitleKey="aiflow.documents.detail"
      source={data?.source}
      actions={
        <div className="flex items-center gap-2">
          {configsData && configsData.configs.length > 0 && (
            <select
              value={selectedConfig}
              onChange={(e) => setSelectedConfig(e.target.value)}
              className="rounded-lg border border-gray-300 bg-white px-2 py-2 text-xs text-gray-600 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-400"
            >
              <option value="all">{translate("aiflow.documents.filterAll")}</option>
              {configsData.configs.map(c => (
                <option key={c.name} value={c.name}>{c.display_name}</option>
              ))}
            </select>
          )}
          <button
            onClick={async () => {
              try {
                const res = await fetchApi<Response>("GET", "/api/v1/documents/export/csv", undefined, { rawResponse: true });
                const blob = await (res as unknown as Response).blob();
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = "aiflow_documents.csv";
                a.click();
                URL.revokeObjectURL(url);
              } catch { /* ignore */ }
            }}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm font-medium text-gray-600 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-400 dark:hover:bg-gray-800"
          >
            CSV Export
          </button>
          <button
            onClick={() => setTab("upload")}
            className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-600"
          >
            + Upload
          </button>
        </div>
      }
    >
      {/* Tabs */}
      <div className="mb-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex gap-6">
          <button
            onClick={() => setTab("list")}
            className={`border-b-2 pb-2 text-sm font-medium transition-colors ${
              tab === "list"
                ? "border-brand-500 text-brand-600 dark:text-brand-400"
                : "border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400"
            }`}
          >
            List
          </button>
          <button
            onClick={() => setTab("upload")}
            className={`border-b-2 pb-2 text-sm font-medium transition-colors ${
              tab === "upload"
                ? "border-brand-500 text-brand-600 dark:text-brand-400"
                : "border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400"
            }`}
          >
            Upload
          </button>
        </div>
      </div>

      {tab === "upload" ? (
        <UploadTab onUploadComplete={refetch} />
      ) : (
        <>
          {/* KPI Cards */}
          <div className="mb-4 grid grid-cols-1 gap-4 md:grid-cols-3">
            <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
              <p className="text-xs font-medium text-gray-500">{translate("aiflow.documents.title")}</p>
              <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-gray-100">{total}</p>
            </div>
            <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
              <p className="text-xs font-medium text-gray-500">{translate("aiflow.documents.filterProcessed")}</p>
              <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-gray-100">{processed}</p>
            </div>
            <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
              <p className="text-xs font-medium text-gray-500">{translate("aiflow.documents.unprocessed")}</p>
              <p className="mt-1 text-2xl font-bold text-amber-600">{pending}</p>
            </div>
          </div>

          {/* Bulk action bar */}
          {selectedDocs.length > 0 && (
            <div className="mb-3 flex items-center gap-3 rounded-lg border border-brand-200 bg-brand-50 p-3 dark:border-brand-800 dark:bg-brand-900/20">
              <span className="text-sm font-medium text-brand-700 dark:text-brand-300">
                {selectedDocs.length} {translate("aiflow.common.selected")}
              </span>
              <button
                onClick={() => setShowBulkDelete(true)}
                className="rounded-lg bg-red-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-red-700"
              >
                {translate("aiflow.common.bulkDelete")}
              </button>
              <button
                onClick={() => setClearSel(c => c + 1)}
                className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-400"
              >
                {translate("aiflow.common.cancel")}
              </button>
            </div>
          )}

          {/* Documents Table — sortable, searchable, paginated, selectable */}
          {error ? (
            <ErrorState error={error} onRetry={refetch} />
          ) : (
            <DataTable
              data={docs as unknown as Record<string, unknown>[]}
              loading={loading}
              searchKeys={["source_file", "vendor.name", "header.invoice_number"]}
              pageSize={10}
              columns={makeDocColumns(translate, setDeleteId)}
              selectable
              onSelectionChange={setSelectedDocs}
              clearSelection={clearSel}
              onRowClick={(item) => {
                const docId = (item as unknown as DocItem).id;
                if (docId) navigate(`/documents/${encodeURIComponent(docId)}/show`);
              }}
            />
          )}
        </>
      )}
      {/* Delete confirmation dialog */}
      {deleteId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-sm rounded-xl border border-gray-200 bg-white p-6 shadow-xl dark:border-gray-700 dark:bg-gray-900">
            <h3 className="mb-2 text-lg font-semibold text-gray-900 dark:text-gray-100">
              {translate("aiflow.documents.deleteTitle")}
            </h3>
            <p className="mb-4 text-sm text-gray-600 dark:text-gray-400">
              {translate("aiflow.documents.deleteConfirm")}
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setDeleteId(null)}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800"
              >
                {translate("common.action.cancel")}
              </button>
              <button
                onClick={() => void handleDelete()}
                disabled={deleting}
                className="rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700 disabled:opacity-50"
              >
                {deleting ? translate("aiflow.common.loading") : translate("aiflow.documents.deleteTitle")}
              </button>
            </div>
          </div>
        </div>
      )}
      {/* Bulk delete confirmation dialog */}
      {showBulkDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-sm rounded-xl border border-gray-200 bg-white p-6 shadow-xl dark:border-gray-700 dark:bg-gray-900">
            <h3 className="mb-2 text-lg font-semibold text-gray-900 dark:text-gray-100">
              {translate("aiflow.common.bulkDelete")}
            </h3>
            <p className="mb-4 text-sm text-gray-600 dark:text-gray-400">
              {translate("aiflow.common.bulkDeleteConfirm")} ({selectedDocs.length})
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setShowBulkDelete(false)}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800"
              >
                {translate("common.action.cancel")}
              </button>
              <button
                onClick={() => void handleBulkDelete()}
                disabled={bulkDeleting}
                className="rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700 disabled:opacity-50"
              >
                {bulkDeleting ? translate("aiflow.common.loading") : translate("aiflow.common.bulkDelete")}
              </button>
            </div>
          </div>
        </div>
      )}
    </PageLayout>
  );
}
