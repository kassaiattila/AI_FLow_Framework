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
  if (conf >= 90) return "text-green-600 dark:text-green-400";
  if (conf >= 70) return "text-amber-600 dark:text-amber-400";
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

interface UploadStep {
  name: string;
  status: "pending" | "running" | "done" | "error";
  elapsed_ms?: number;
}

function UploadTab() {
  const translate = useTranslate();
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [steps, setSteps] = useState<UploadStep[]>([]);
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
    try {
      const formData = new FormData();
      files.forEach(f => formData.append("files", f));
      await uploadFile("/api/v1/documents/upload", formData);
      setUploading(false);
      setProcessing(true);

      // Start SSE processing
      setSteps([
        { name: "PDF Parse", status: "pending" },
        { name: "Classify", status: "pending" },
        { name: "Extract", status: "pending" },
        { name: "Validate", status: "pending" },
        { name: "Store", status: "pending" },
        { name: "Export", status: "pending" },
      ]);

      const source = streamApi(
        `/api/v1/documents/process-stream`,
        (data) => {
          try {
            const msg = JSON.parse(data);
            if (msg.step_index !== undefined) {
              setSteps(prev => prev.map((s, i) => ({
                ...s,
                status: i < msg.step_index ? "done" : i === msg.step_index ? "running" : "pending",
                elapsed_ms: i === msg.step_index ? msg.elapsed_ms : s.elapsed_ms,
              })));
            }
            if (msg.status === "completed") {
              setResult(`${files.length} file(s) processed successfully`);
              setProcessing(false);
              setSteps(prev => prev.map(s => ({ ...s, status: "done" })));
            }
          } catch { /* ignore non-json */ }
        },
        () => { setProcessing(false); },
        () => { setProcessing(false); },
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
      setUploading(false);
      setProcessing(false);
    }
  };

  const handleReset = () => {
    setFiles([]);
    setSteps([]);
    setResult(null);
    setError(null);
  };

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

      {/* File list */}
      {files.length > 0 && (
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

      {/* Pipeline progress */}
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

      {error && <ErrorState error={error} onRetry={handleUpload} />}
      {result && (
        <div className="rounded-xl border border-green-200 bg-green-50 p-4 text-sm text-green-700 dark:border-green-800 dark:bg-green-900/20 dark:text-green-400">
          {result}
        </div>
      )}
    </div>
  );
}

// --- Document Table Columns ---

const docColumns: Column<Record<string, unknown>>[] = [
  {
    key: "source_file",
    label: "File",
    getValue: (item) => fileName(String(item.source_file ?? "")),
    render: (item) => (
      <span className="font-medium text-gray-900 dark:text-gray-100">
        {fileName(String(item.source_file ?? ""))}
      </span>
    ),
  },
  {
    key: "status",
    label: "Status",
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
    label: "Vendor",
    getValue: (item) => (item.vendor as DocVendor | null)?.name ?? "",
    render: (item) => (
      <span className="text-gray-600 dark:text-gray-400">
        {(item.vendor as DocVendor | null)?.name ?? "—"}
      </span>
    ),
  },
  {
    key: "header.invoice_number",
    label: "Invoice #",
    getValue: (item) => (item.header as DocHeader | null)?.invoice_number ?? "",
    render: (item) => (
      <span className="text-gray-600 dark:text-gray-400">
        {(item.header as DocHeader | null)?.invoice_number ?? "—"}
      </span>
    ),
  },
  {
    key: "totals.gross_total",
    label: "Gross Total",
    getValue: (item) => (item.totals as DocTotals | null)?.gross_total ?? 0,
    render: (item) => {
      const total = (item.totals as DocTotals | null)?.gross_total;
      const currency = (item.header as DocHeader | null)?.currency ?? "HUF";
      return (
        <span className="text-gray-600 dark:text-gray-400">
          {total ? `${total.toLocaleString()} ${currency}` : "—"}
        </span>
      );
    },
  },
  {
    key: "extraction_confidence",
    label: "Confidence",
    getValue: (item) => (item.extraction_confidence as number | null) ?? 0,
    render: (item) => {
      const conf = item.extraction_confidence as number | null;
      return (
        <span className={`font-medium ${confidenceColor(conf)}`}>
          {conf ? `${conf}%` : "—"}
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
        <a
          href={`#/documents/${encodeURIComponent(docId)}/verify`}
          onClick={(e) => e.stopPropagation()}
          className="inline-flex items-center gap-1 rounded-lg border border-brand-300 px-2.5 py-1 text-xs font-medium text-brand-600 hover:bg-brand-50 dark:border-brand-700 dark:text-brand-400 dark:hover:bg-brand-900/20"
        >
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Verify
        </a>
      );
    },
  },
];

// --- Main Component ---

export function Documents() {
  const translate = useTranslate();
  const navigate = useNavigate();
  const [tab, setTab] = useState<"list" | "upload">("list");
  const { data, loading, error, refetch } = useApi<DocsResponse>("/api/v1/documents");

  const docs = data?.documents ?? [];
  const total = data?.total ?? 0;
  const processed = docs.filter(d => d.extraction_confidence && d.extraction_confidence > 0).length;
  const pending = docs.filter(d => !d.extraction_confidence || d.extraction_confidence === 0).length;

  return (
    <PageLayout
      titleKey="aiflow.documents.title"
      subtitleKey="aiflow.documents.detail"
      source={data?.source}
      actions={
        <button
          onClick={() => setTab("upload")}
          className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-600"
        >
          + Upload
        </button>
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
        <UploadTab />
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

          {/* Documents Table — sortable, searchable, paginated */}
          {error ? (
            <ErrorState error={error} onRetry={refetch} />
          ) : (
            <DataTable
              data={docs as unknown as Record<string, unknown>[]}
              loading={loading}
              searchKeys={["source_file", "vendor.name", "header.invoice_number"]}
              pageSize={10}
              columns={docColumns}
              onRowClick={(item) => {
                const docId = (item as unknown as DocItem).id;
                if (docId) navigate(`/documents/${encodeURIComponent(docId)}/verify`);
              }}
            />
          )}
        </>
      )}
    </PageLayout>
  );
}
