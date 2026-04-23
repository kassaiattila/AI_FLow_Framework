/**
 * AIFlow Emails — F6.3 tabbed page (Inbox + Upload + Connectors).
 * Replaces old MUI EmailList + EmailUpload + EmailConnectors.
 */

import { useState, useCallback, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslate } from "../lib/i18n";
import { useApi } from "../lib/hooks";
import { fetchApi } from "../lib/api-client";
import { PageLayout } from "../layout/PageLayout";
import { ErrorState } from "../components-new/ErrorState";
import { DataTable, type Column } from "../components-new/DataTable";
import { FileProgressRow, FileProgressBar, type FileProgress } from "../components-new/FileProgress";

// Observed averages from hybrid_llm runs (gpt-4o-mini, ~3700 input tokens).
// Used for cost/ETA preview only — actual numbers vary per email length.
const BATCH_CAP = 25;
const AVG_COST_PER_EMAIL_USD = 0.0008;
const AVG_TIME_PER_EMAIL_SEC = 60;

function formatDuration(totalSec: number): string {
  if (!Number.isFinite(totalSec) || totalSec <= 0) return "—";
  const h = Math.floor(totalSec / 3600);
  const m = Math.floor((totalSec % 3600) / 60);
  const s = Math.floor(totalSec % 60);
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

function formatCost(usd: number): string {
  if (usd < 0.01) return `<$0.01`;
  if (usd < 1) return `$${usd.toFixed(2)}`;
  return `$${usd.toFixed(2)}`;
}

// --- Types ---

interface EmailItem {
  email_id: string;
  sender: string;
  subject: string;
  received_date: string | null;
  intent_id: string | null;
  intent_display_name: string | null;
  intent_confidence: number;
  intent_method: string | null;
  priority_level: number | null;
  department_name: string | null;
  queue_name: string | null;
  entity_count: number;
  attachment_count: number;
  processing_time_ms: number;
  status: string;
}

interface EmailsResponse {
  emails: EmailItem[];
  total: number;
  source: string;
}

interface ConnectorItem {
  id: string;
  name: string;
  provider: string;
  host: string;
  port: number;
  use_ssl: boolean;
  mailbox: string;
  polling_interval_minutes: number;
  max_emails_per_fetch: number;
  is_active: boolean;
  last_fetched_at: string | null;
  created_at: string;
  source: string;
}

// --- Inbox Tab ---

function InboxTab({ refreshKey }: { refreshKey: number }) {
  const translate = useTranslate();
  const navigate = useNavigate();
  const { data, loading, error, refetch } = useApi<EmailsResponse>("/api/v1/emails");

  // Re-fetch when other tabs trigger a refresh
  useEffect(() => { if (refreshKey > 0) refetch(); }, [refreshKey, refetch]);
  const emails = data?.emails ?? [];
  const [processing, setProcessing] = useState<string | null>(null);
  const [processProgress, setProcessProgress] = useState<FileProgress[]>([]);
  const [selectedEmails, setSelectedEmails] = useState<Record<string, unknown>[]>([]);
  const [clearSel, setClearSel] = useState(0);
  const [confirmBatch, setConfirmBatch] = useState<{ ids: string[]; label: string } | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const [processStartTs, setProcessStartTs] = useState<number | null>(null);
  const [doneCount, setDoneCount] = useState(0);

  const priorityColor: Record<string, string> = {
    critical: "bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-400",
    high: "bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
    normal: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400",
    low: "bg-gray-50 text-gray-500 dark:bg-gray-800 dark:text-gray-400",
  };

  const isUnprocessed = (item: Record<string, unknown>) => !item.intent_display_name || item.intent_display_name === "Not processed";

  // Process unprocessed emails via SSE (per-email pipeline).
  // Splits into BATCH_CAP-sized chunks; AbortController stops mid-stream.
  const handleProcessEmails = async (emailIds: string[]) => {
    if (emailIds.length === 0) return;
    setProcessing("bulk");
    setProcessStartTs(Date.now());
    setDoneCount(0);
    const defaultSteps = ["parse", "classify", "extract", "priority", "route"];
    setProcessProgress(emailIds.map((id) => ({
      name: id.substring(0, 50),
      status: "pending" as const,
      steps: defaultSteps.map(s => ({ name: s, status: "pending" as const })),
    })));

    const ac = new AbortController();
    abortRef.current = ac;
    let globalOffset = 0;

    const runOneBatch = async (batchIds: string[], offset: number): Promise<boolean> => {
      if (ac.signal.aborted) return false;
      const token = localStorage.getItem("aiflow_token");
      const resp = await fetch("/api/v1/emails/process-batch-stream", {
        method: "POST",
        headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: JSON.stringify({ email_ids: batchIds }),
        signal: ac.signal,
      });

      if (!resp.ok || !resp.body) return true;

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      try {
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
              const globalIdx = msg.file_index !== undefined ? offset + msg.file_index : undefined;

              if (msg.event === "file_start" && globalIdx !== undefined) {
                setProcessProgress(prev => prev.map((fp, i) =>
                  i === globalIdx ? { ...fp, name: msg.file || fp.name, status: "processing" } : fp
                ));
              }
              if (msg.event === "file_step" && globalIdx !== undefined && msg.step_index !== undefined) {
                setProcessProgress(prev => prev.map((fp, i) => {
                  if (i !== globalIdx) return fp;
                  return { ...fp, steps: fp.steps.map((s, si) => si !== msg.step_index ? s : { ...s, status: msg.status === "done" ? "done" as const : "running" as const, elapsed_ms: msg.elapsed_ms ?? s.elapsed_ms }) };
                }));
              }
              if (msg.event === "file_error" && globalIdx !== undefined) {
                setProcessProgress(prev => prev.map((fp, i) =>
                  i === globalIdx ? { ...fp, status: "error", error: msg.error } : fp
                ));
              }
              if (msg.event === "file_done" && globalIdx !== undefined) {
                setProcessProgress(prev => prev.map((fp, i) =>
                  i === globalIdx ? { ...fp, status: msg.ok ? "done" as const : "error" as const } : fp
                ));
                setDoneCount(c => c + 1);
                if (msg.ok) refetch();
              }
            } catch { /* skip */ }
          }
        }
      } catch (e) {
        if ((e as { name?: string })?.name === "AbortError") return false;
        throw e;
      }
      return true;
    };

    try {
      while (globalOffset < emailIds.length) {
        if (ac.signal.aborted) break;
        const batch = emailIds.slice(globalOffset, globalOffset + BATCH_CAP);
        const ok = await runOneBatch(batch, globalOffset);
        if (!ok) break;
        globalOffset += batch.length;
      }

      // Mark any still-pending rows as canceled when user aborted mid-flight.
      if (ac.signal.aborted) {
        setProcessProgress(prev => prev.map(fp =>
          fp.status === "pending" || fp.status === "processing"
            ? { ...fp, status: "error" as const, error: "Megszakitva" }
            : fp,
        ));
      }

      refetch();
      setClearSel(c => c + 1);
    } finally {
      setProcessing(null);
      abortRef.current = null;
    }
  };

  const handleCancelProcessing = () => {
    abortRef.current?.abort();
  };

  const handleExportCsv = async () => {
    try {
      const res = await fetchApi<Response>("GET", "/api/v1/emails/export/csv", undefined, { rawResponse: true });
      const blob = await (res as unknown as Response).blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = "aiflow_emails.csv"; a.click();
      URL.revokeObjectURL(url);
    } catch { /* ignore */ }
  };

  const unprocessedCount = emails.filter(e => !e.intent_display_name || e.intent_display_name === "Not processed").length;
  const processedCount = emails.filter(e => e.intent_display_name && e.intent_display_name !== "Not processed").length;

  return (
    <>
      {/* KPIs */}
      <div className="mb-4 grid grid-cols-1 gap-4 md:grid-cols-4">
        <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
          <p className="text-xs font-medium text-gray-500">{translate("aiflow.emails.title")}</p>
          <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-gray-100">{data?.total ?? 0}</p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
          <p className="text-xs font-medium text-gray-500">{translate("aiflow.emails.intentSection")}</p>
          <p className="mt-1 text-2xl font-bold text-green-600">{processedCount}</p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
          <p className="text-xs font-medium text-gray-500">Unprocessed</p>
          <p className="mt-1 text-2xl font-bold text-amber-600">{unprocessedCount}</p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
          <p className="text-xs font-medium text-gray-500">{translate("aiflow.emails.attachments")}</p>
          <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-gray-100">
            {emails.reduce((s, e) => s + (e.attachment_count || 0), 0)}
          </p>
        </div>
      </div>

      {/* Action bar */}
      <div className="mb-3 flex items-center gap-2">
        {unprocessedCount > 0 && (
          <button
            onClick={() => {
              const ids = emails.filter(isUnprocessed).map(e => e.email_id);
              setConfirmBatch({ ids, label: `osszes feldolgozatlan (${ids.length})` });
            }}
            disabled={!!processing}
            className="rounded-lg bg-brand-500 px-3 py-1.5 text-xs font-semibold text-white hover:bg-brand-600 disabled:opacity-50"
          >
            {processing ? translate("aiflow.common.loading") : `Process All (${unprocessedCount})`}
          </button>
        )}
        {selectedEmails.length > 0 && selectedEmails.some(isUnprocessed) && (
          <button
            onClick={() => {
              const ids = selectedEmails.filter(isUnprocessed).map(e => String((e as unknown as EmailItem).email_id));
              setConfirmBatch({ ids, label: `kivalasztott (${ids.length})` });
            }}
            disabled={!!processing}
            className="rounded-lg bg-brand-500 px-3 py-1.5 text-xs font-semibold text-white hover:bg-brand-600 disabled:opacity-50"
          >
            Process Selected ({selectedEmails.filter(isUnprocessed).length})
          </button>
        )}
        <div className="flex-1" />
        <button onClick={handleExportCsv} className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-400">
          CSV Export
        </button>
      </div>

      {/* Confirm batch modal */}
      {confirmBatch && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" role="dialog" aria-modal="true">
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-2xl dark:bg-gray-900">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              {confirmBatch.ids.length} email feldolgozasa
            </h3>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
              Batch: {confirmBatch.label}
            </p>
            <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
              <div className="rounded-lg bg-gray-50 p-3 dark:bg-gray-800">
                <dt className="text-xs font-medium text-gray-500">Becsult koltseg</dt>
                <dd className="mt-1 font-mono text-base font-semibold text-gray-900 dark:text-gray-100">
                  ~{formatCost(confirmBatch.ids.length * AVG_COST_PER_EMAIL_USD)}
                </dd>
              </div>
              <div className="rounded-lg bg-gray-50 p-3 dark:bg-gray-800">
                <dt className="text-xs font-medium text-gray-500">Becsult ido</dt>
                <dd className="mt-1 font-mono text-base font-semibold text-gray-900 dark:text-gray-100">
                  ~{formatDuration(confirmBatch.ids.length * AVG_TIME_PER_EMAIL_SEC)}
                </dd>
              </div>
            </dl>
            <p className="mt-3 text-xs text-gray-500 dark:text-gray-400">
              OpenAI gpt-4o-mini ~$0.0008/email, ~60s latency alapjan.
              {confirmBatch.ids.length > BATCH_CAP && (
                <> {BATCH_CAP}-esevel kuldve; kozben megszakithato.</>
              )}
            </p>
            <div className="mt-5 flex justify-end gap-2">
              <button
                onClick={() => setConfirmBatch(null)}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800"
              >
                Megse
              </button>
              <button
                onClick={() => {
                  const ids = confirmBatch.ids;
                  setConfirmBatch(null);
                  void handleProcessEmails(ids);
                }}
                className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-600"
              >
                Inditas
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Process progress */}
      {processProgress.length > 0 && (() => {
        const done = processProgress.filter(fp => fp.status === "done").length;
        const errorCount = processProgress.filter(fp => fp.status === "error").length;
        const remaining = processProgress.length - done - errorCount;
        let etaText = "";
        if (processing && processStartTs && doneCount > 0 && remaining > 0) {
          const elapsedSec = (Date.now() - processStartTs) / 1000;
          const avgSec = elapsedSec / doneCount;
          etaText = ` · ETA ~${formatDuration(remaining * avgSec)}`;
        } else if (processing && remaining > 0) {
          etaText = ` · ETA ~${formatDuration(remaining * AVG_TIME_PER_EMAIL_SEC)}`;
        }
        return (
          <div className="mb-3 rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
            <div className="mb-2 flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-700 dark:text-gray-300">{translate("aiflow.pipeline.title")}</p>
                <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-400">
                  {done}/{processProgress.length} kesz
                  {errorCount > 0 && <span className="text-red-500"> · {errorCount} hiba</span>}
                  {etaText}
                </p>
              </div>
              {processing && (
                <button
                  onClick={handleCancelProcessing}
                  className="rounded-lg border border-red-300 px-3 py-1 text-xs font-semibold text-red-600 hover:bg-red-50 dark:border-red-700 dark:text-red-400 dark:hover:bg-red-900/20"
                >
                  Megszakitas
                </button>
              )}
            </div>
            <FileProgressBar done={done} total={processProgress.length} />
            <div className="max-h-48 overflow-y-auto">
              {processProgress.map((fp, i) => <FileProgressRow key={i} fp={fp} />)}
            </div>
          </div>
        );
      })()}

      {/* Table */}
      {error ? (
        <ErrorState error={error} onRetry={refetch} />
      ) : (
        <DataTable
          data={emails as unknown as Record<string, unknown>[]}
          loading={loading}
          searchKeys={["sender", "subject", "intent"]}
          pageSize={15}
          selectable
          onSelectionChange={setSelectedEmails}
          clearSelection={clearSel}
          onRowClick={(item) => {
            // Unprocessed rows have no workflow_run yet (email_id = .eml file
            // stem); /emails/{id} backend looks in DB and returns 404. Drill
            // down only for processed rows where the route has real data.
            if (isUnprocessed(item)) return;
            const id = String((item as unknown as EmailItem).email_id);
            if (id) navigate(`/emails/${encodeURIComponent(id)}`);
          }}
          columns={[
            { key: "sender", label: translate("aiflow.emails.sender"), render: (item) => <span className="block max-w-[180px] truncate font-medium text-gray-900 dark:text-gray-100" title={String(item.sender ?? "")}>{String(item.sender ?? "")}</span> },
            { key: "subject", label: translate("aiflow.emails.subject"), render: (item) => <span className="block max-w-[250px] truncate text-gray-600 dark:text-gray-400" title={String(item.subject ?? "")}>{String(item.subject ?? "")}</span> },
            { key: "intent_display_name", label: translate("aiflow.emails.intent"), render: (item) => {
              const intent = String(item.intent_display_name ?? "");
              if (!intent || intent === "Not processed") return <span className="rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-600 dark:bg-amber-900/30 dark:text-amber-400">Not processed</span>;
              return <span className="rounded-full bg-brand-50 px-2 py-0.5 text-xs font-medium text-brand-700 dark:bg-brand-900/30 dark:text-brand-400">{intent}</span>;
            }},
            { key: "priority_level", label: translate("aiflow.emails.priority"), render: (item) => {
              const p = item.priority_level as number | null;
              if (!p) return <span className="text-gray-400">—</span>;
              const pName = p <= 2 ? "critical" : p === 3 ? "high" : p === 4 ? "normal" : "low";
              return <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${priorityColor[pName] ?? priorityColor.normal}`}>P{p}</span>;
            }},
            { key: "intent_confidence", label: "%", getValue: (item) => (item.intent_confidence as number) ?? 0, render: (item) => {
              const c = item.intent_confidence as number;
              return <span className="text-xs text-gray-600 dark:text-gray-400">{c ? `${Math.round(c * 100)}%` : "—"}</span>;
            }},
            { key: "received_date", label: translate("aiflow.emails.received"), render: (item) => <span className="whitespace-nowrap text-xs text-gray-500">{item.received_date ? new Date(String(item.received_date)).toLocaleDateString() : "—"}</span> },
            { key: "actions", label: "", sortable: false, render: (item) => {
              if (!isUnprocessed(item)) return null;
              return (
                <button
                  onClick={(e) => { e.stopPropagation(); void handleProcessEmails([String((item as unknown as EmailItem).email_id)]); }}
                  disabled={!!processing}
                  className="rounded-md bg-brand-50 px-2 py-1 text-xs font-medium text-brand-600 hover:bg-brand-100 disabled:opacity-50 dark:bg-brand-900/30 dark:text-brand-400"
                >
                  Process
                </button>
              );
            }},
          ]}
        />
      )}
    </>
  );
}

// --- Upload Tab ---

function UploadTab({ onProcessed }: { onProcessed?: () => void }) {
  const translate = useTranslate();
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [fileProgress, setFileProgress] = useState<FileProgress[]>([]);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const dropped = Array.from(e.dataTransfer.files).filter(
      f => /\.(eml|msg|txt)$/i.test(f.name),
    );
    setFiles(prev => [...prev, ...dropped]);
  }, []);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) setFiles(prev => [...prev, ...Array.from(e.target.files!)]);
  }, []);

  const handleUpload = async () => {
    if (files.length === 0) return;
    setUploading(true);
    setError(null);
    setResult(null);

    const defaultSteps = ["upload", "parse", "classify", "extract", "priority", "route"];
    setFileProgress(files.map(f => ({
      name: f.name,
      status: "pending" as const,
      steps: defaultSteps.map(s => ({ name: s, status: "pending" as const })),
    })));

    try {
      const token = localStorage.getItem("aiflow_token");
      const formData = new FormData();
      files.forEach(f => formData.append("files", f));

      const resp = await fetch("/api/v1/emails/upload-and-process-stream", {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      });

      if (!resp.ok || !resp.body) {
        setError(`Upload failed: ${resp.status}`);
        setUploading(false);
        return;
      }

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
                return { ...fp, steps: fp.steps.map((s, si) => si !== msg.step_index ? s : { ...s, status: msg.status === "done" ? "done" as const : "running" as const, elapsed_ms: msg.elapsed_ms ?? s.elapsed_ms }) };
              }));
            }
            if (msg.event === "file_error" && msg.file_index !== undefined) {
              setFileProgress(prev => prev.map((fp, i) =>
                i === msg.file_index ? { ...fp, status: "error", error: msg.error } : fp
              ));
            }
            if (msg.event === "file_done" && msg.file_index !== undefined) {
              setFileProgress(prev => prev.map((fp, i) =>
                i === msg.file_index ? { ...fp, status: msg.ok ? "done" as const : "error" as const } : fp
              ));
            }
            if (msg.event === "complete") {
              const total = msg.total_processed ?? 0;
              setResult(`${total}/${files.length} email(s) processed`);
              setFileProgress(prev => prev.map(fp => fp.status === "pending" || fp.status === "processing"
                ? { ...fp, status: "done" as const, steps: fp.steps.map(s => ({ ...s, status: "done" as const })) } : fp));
              onProcessed?.();
            }
            if (msg.event === "error") {
              setError(msg.error ?? "Processing failed");
            }
          } catch { /* skip non-json */ }
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const handleReset = () => { setFiles([]); setFileProgress([]); setResult(null); setError(null); };
  const doneCount = fileProgress.filter(fp => fp.status === "done").length;

  return (
    <div className="space-y-4">
      {/* Dropzone */}
      <div
        onDragOver={e => e.preventDefault()}
        onDrop={handleDrop}
        className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-gray-300 bg-white p-8 text-center transition-colors hover:border-brand-400 dark:border-gray-600 dark:bg-gray-900 dark:hover:border-brand-500"
      >
        <svg className="mb-3 h-10 w-10 text-gray-300 dark:text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75" />
        </svg>
        <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
          {translate("aiflow.emailUpload.dropzone")}
        </p>
        <p className="mt-1 text-xs text-gray-400">.eml, .msg, .txt</p>
        <label className="mt-3 cursor-pointer rounded-lg bg-brand-500 px-4 py-2 text-sm font-medium text-white hover:bg-brand-600">
          {translate("aiflow.emailUpload.uploaded")}
          <input type="file" accept=".eml,.msg,.txt" multiple className="hidden" onChange={handleFileSelect} />
        </label>
      </div>

      {/* File list (before upload) */}
      {files.length > 0 && fileProgress.length === 0 && (
        <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{files.length} file(s)</span>
            <div className="flex gap-2">
              <button onClick={handleReset} className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-400">
                {translate("aiflow.common.cancel")}
              </button>
              <button onClick={handleUpload} disabled={uploading} className="rounded-lg bg-brand-500 px-4 py-1.5 text-xs font-semibold text-white hover:bg-brand-600 disabled:opacity-50">
                {uploading ? translate("aiflow.common.loading") : translate("aiflow.emailUpload.process")}
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

      {/* Per-file progress */}
      {fileProgress.length > 0 && (
        <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
          <div className="mb-2 flex items-center justify-between">
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300">{translate("aiflow.pipeline.title")}</p>
            {uploading && <span className="text-xs text-brand-600 dark:text-brand-400">{doneCount}/{fileProgress.length}</span>}
          </div>
          <FileProgressBar done={doneCount} total={fileProgress.length} />
          {fileProgress.map((fp, i) => <FileProgressRow key={i} fp={fp} />)}
          {!uploading && (
            <button onClick={handleReset} className="mt-3 rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-400">
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
            <button onClick={handleReset} className="rounded-lg border border-green-300 px-3 py-1.5 text-xs font-medium text-green-700 hover:bg-green-100 dark:border-green-700 dark:text-green-400">
              {translate("aiflow.documentUpload.newBatch")}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// --- Connectors Tab ---

const PROVIDERS = [
  { value: "outlook_com", label: "Outlook (local)" },
  { value: "imap", label: "IMAP" },
  { value: "o365_graph", label: "Office 365 Graph" },
  { value: "gmail", label: "Gmail" },
];

const EMPTY_FORM = { name: "", provider: "outlook_com", host: "", port: 993, use_ssl: true, mailbox: "", credentials_encrypted: "", polling_interval_minutes: 15, max_emails_per_fetch: 50, is_active: true };

function ConnectorFormDialog({ initial, onSave, onClose, translate }: {
  initial: typeof EMPTY_FORM & { id?: string };
  onSave: () => void;
  onClose: () => void;
  translate: (k: string) => string;
}) {
  const [form, setForm] = useState(initial);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const isEdit = !!initial.id;

  const handleSubmit = async () => {
    setSaving(true);
    setErr(null);
    try {
      if (isEdit) {
        await fetchApi("PUT", `/api/v1/emails/connectors/${initial.id}`, form);
      } else {
        await fetchApi("POST", "/api/v1/emails/connectors", form);
      }
      onSave();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!isEdit || !window.confirm(translate("aiflow.connectors.confirmDelete"))) return;
    try {
      await fetchApi("DELETE", `/api/v1/emails/connectors/${initial.id}`);
      onSave();
    } catch { /* ignore */ }
  };

  const set = (k: string, v: string | number | boolean) => setForm(f => ({ ...f, [k]: v }));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-lg rounded-xl border border-gray-200 bg-white p-6 shadow-xl dark:border-gray-700 dark:bg-gray-900">
        <h3 className="mb-4 text-lg font-semibold text-gray-900 dark:text-gray-100">
          {isEdit ? translate("aiflow.connectors.edit") : translate("aiflow.connectors.create")}
        </h3>

        <div className="space-y-3">
          {/* Name + Provider */}
          <div className="grid grid-cols-2 gap-3">
            <label className="block">
              <span className="text-xs font-medium text-gray-600 dark:text-gray-400">{translate("aiflow.connectors.name")}</span>
              <input value={form.name} onChange={e => set("name", e.target.value)} className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100" />
            </label>
            <label className="block">
              <span className="text-xs font-medium text-gray-600 dark:text-gray-400">{translate("aiflow.connectors.provider")}</span>
              <select value={form.provider} onChange={e => set("provider", e.target.value)} className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100">
                {PROVIDERS.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
              </select>
            </label>
          </div>

          {/* Host + Port (hidden for outlook_com) */}
          {form.provider !== "outlook_com" && (
            <div className="grid grid-cols-3 gap-3">
              <label className="col-span-2 block">
                <span className="text-xs font-medium text-gray-600 dark:text-gray-400">{translate("aiflow.connectors.host")}</span>
                <input value={form.host} onChange={e => set("host", e.target.value)} placeholder="mail.example.com" className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100" />
              </label>
              <label className="block">
                <span className="text-xs font-medium text-gray-600 dark:text-gray-400">Port</span>
                <input type="number" value={form.port} onChange={e => set("port", Number(e.target.value))} className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100" />
              </label>
            </div>
          )}

          {/* Mailbox / Account filter */}
          <label className="block">
            <span className="text-xs font-medium text-gray-600 dark:text-gray-400">
              {form.provider === "outlook_com" ? "Account filter (e.g. bestix, aam, field)" : translate("aiflow.connectors.mailbox")}
            </span>
            <input value={form.mailbox} onChange={e => set("mailbox", e.target.value)} placeholder={form.provider === "outlook_com" ? "bestix" : "INBOX"} className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100" />
          </label>

          {/* Credentials (hidden for outlook_com) */}
          {form.provider !== "outlook_com" && (
            <label className="block">
              <span className="text-xs font-medium text-gray-600 dark:text-gray-400">{translate("aiflow.connectors.credentials")}</span>
              <input value={form.credentials_encrypted} onChange={e => set("credentials_encrypted", e.target.value)}
                placeholder={form.provider === "o365_graph" ? "tenant_id:client_id:client_secret:user@email" : "user:password"}
                className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-mono dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100" />
            </label>
          )}

          {/* Polling + Max + SSL + Active */}
          <div className="grid grid-cols-2 gap-3">
            <label className="block">
              <span className="text-xs font-medium text-gray-600 dark:text-gray-400">{translate("aiflow.connectors.pollingInterval")}</span>
              <input type="number" value={form.polling_interval_minutes} onChange={e => set("polling_interval_minutes", Number(e.target.value))} className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100" />
            </label>
            <label className="block">
              <span className="text-xs font-medium text-gray-600 dark:text-gray-400">{translate("aiflow.connectors.maxEmails")}</span>
              <input type="number" value={form.max_emails_per_fetch} onChange={e => set("max_emails_per_fetch", Number(e.target.value))} className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100" />
            </label>
          </div>

          <div className="flex items-center gap-4">
            {form.provider !== "outlook_com" && (
              <label className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                <input type="checkbox" checked={form.use_ssl} onChange={e => set("use_ssl", e.target.checked)} className="rounded border-gray-300 text-brand-600" />
                {translate("aiflow.connectors.ssl")}
              </label>
            )}
            <label className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
              <input type="checkbox" checked={form.is_active} onChange={e => set("is_active", e.target.checked)} className="rounded border-gray-300 text-brand-600" />
              {translate("aiflow.connectors.active")}
            </label>
          </div>
        </div>

        {err && <p className="mt-2 text-sm text-red-600">{err}</p>}

        <div className="mt-5 flex items-center justify-between">
          <div>
            {isEdit && (
              <button onClick={handleDelete} className="rounded-lg border border-red-200 px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-50 dark:border-red-800 dark:text-red-400">
                {translate("aiflow.connectors.delete")}
              </button>
            )}
          </div>
          <div className="flex gap-2">
            <button onClick={onClose} className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300">
              {translate("common.action.cancel")}
            </button>
            <button onClick={handleSubmit} disabled={saving || !form.name.trim()} className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-600 disabled:opacity-50">
              {saving ? translate("aiflow.common.loading") : isEdit ? translate("common.action.save") : translate("aiflow.connectors.create")}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function ConnectorsTab({ onProcessed }: { onProcessed?: () => void }) {
  const translate = useTranslate();
  const { data, loading, error, refetch } = useApi<ConnectorItem[]>("/api/v1/emails/connectors");
  const connectors = Array.isArray(data) ? data : [];
  const [testing, setTesting] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<{ id: string; ok: boolean; msg: string } | null>(null);
  const [fetching, setFetching] = useState<string | null>(null);
  const [fetchDays, setFetchDays] = useState(7);
  const [fetchResult, setFetchResult] = useState<{ id: string; count: number; processed: number } | null>(null);
  const [fetchProgress, setFetchProgress] = useState<FileProgress[]>([]);
  const [autoProcess, setAutoProcess] = useState(true);
  const [editConnector, setEditConnector] = useState<(typeof EMPTY_FORM & { id?: string }) | null>(null);

  const handleTest = async (id: string) => {
    setTesting(id);
    setTestResult(null);
    try {
      const res = await fetchApi<{ success: boolean; message: string }>("POST", `/api/v1/emails/connectors/${id}/test`);
      setTestResult({ id, ok: res.success, msg: res.success ? translate("aiflow.connectors.testSuccess") : res.message });
    } catch {
      setTestResult({ id, ok: false, msg: translate("aiflow.connectors.testFailed") });
    } finally {
      setTesting(null);
    }
  };

  const handleFetch = async (id: string) => {
    setFetching(id);
    setFetchResult(null);
    setFetchProgress([]);

    try {
      // No auto-process: simple fetch only
      if (!autoProcess) {
        const res = await fetchApi<{ total_count: number; new_count: number }>("POST", "/api/v1/emails/fetch", { config_id: id, since_days: fetchDays, limit: 100 });
        setFetchResult({ id, count: res.new_count ?? res.total_count, processed: 0 });
        refetch();
        setFetching(null);
        return;
      }

      // Auto-process: SSE stream
      const token = localStorage.getItem("aiflow_token");
      const resp = await fetch("/api/v1/emails/fetch-and-process-stream", {
        method: "POST",
        headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: JSON.stringify({ config_id: id, since_days: fetchDays, limit: 100 }),
      });

      if (!resp.ok || !resp.body) {
        const res = await fetchApi<{ total_count: number; new_count: number }>("POST", "/api/v1/emails/fetch", { config_id: id, since_days: fetchDays, limit: 100 });
        setFetchResult({ id, count: res.new_count ?? res.total_count, processed: 0 });
        refetch();
        return;
      }

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      const defaultSteps = ["fetch", "parse", "classify", "extract", "priority", "route"];

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

            if (msg.event === "init") {
              const steps: string[] = msg.steps ?? defaultSteps;
              const items: FileProgress[] = Array.from({ length: msg.total_files }, (_, i) => ({
                name: `Email ${i + 1}`,
                status: "pending" as const,
                steps: steps.map(s => ({ name: s, status: "pending" as const })),
              }));
              setFetchProgress(items);
            }
            if (msg.event === "file_start" && msg.file_index !== undefined) {
              setFetchProgress(prev => prev.map((fp, i) =>
                i === msg.file_index ? { ...fp, name: msg.file || fp.name, status: "processing" } : fp
              ));
            }
            if (msg.event === "file_step" && msg.file_index !== undefined && msg.step_index !== undefined) {
              setFetchProgress(prev => prev.map((fp, i) => {
                if (i !== msg.file_index) return fp;
                return { ...fp, steps: fp.steps.map((s, si) => si !== msg.step_index ? s : { ...s, status: msg.status === "done" ? "done" as const : "running" as const, elapsed_ms: msg.elapsed_ms ?? s.elapsed_ms }) };
              }));
            }
            if (msg.event === "file_error" && msg.file_index !== undefined) {
              setFetchProgress(prev => prev.map((fp, i) =>
                i === msg.file_index ? { ...fp, status: "error", error: msg.error } : fp
              ));
            }
            if (msg.event === "file_done" && msg.file_index !== undefined) {
              setFetchProgress(prev => prev.map((fp, i) =>
                i === msg.file_index ? { ...fp, status: msg.ok ? "done" as const : "error" as const } : fp
              ));
            }
            if (msg.event === "complete") {
              setFetchResult({ id, count: msg.total_fetched ?? 0, processed: msg.total_processed ?? 0 });
              setFetchProgress(prev => prev.map(fp => fp.status === "pending" || fp.status === "processing"
                ? { ...fp, status: "done" as const, steps: fp.steps.map(s => ({ ...s, status: "done" as const })) } : fp));
              refetch();
              onProcessed?.();
            }
            if (msg.event === "error") {
              setTestResult({ id, ok: false, msg: msg.error ?? "Fetch failed" });
            }
          } catch { /* skip */ }
        }
      }
    } catch { /* ignore */ }
    finally { setFetching(null); }
  };

  const openCreate = () => setEditConnector({ ...EMPTY_FORM });
  const openEdit = (item: Record<string, unknown>) => {
    const c = item as unknown as ConnectorItem;
    setEditConnector({
      id: c.id, name: c.name, provider: c.provider, host: c.host ?? "", port: c.port ?? 993,
      use_ssl: c.use_ssl ?? true, mailbox: c.mailbox ?? "", credentials_encrypted: "",
      polling_interval_minutes: c.polling_interval_minutes ?? 15,
      max_emails_per_fetch: c.max_emails_per_fetch ?? 50, is_active: c.is_active ?? true,
    });
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-500">{connectors.length} connector(s)</span>
        <button onClick={openCreate} className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-600">
          + {translate("aiflow.connectors.create")}
        </button>
      </div>

      {/* Date range + auto-process toggle */}
      <div className="flex items-center gap-3 rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-900">
        <span className="text-xs font-medium text-gray-500 dark:text-gray-400">{translate("aiflow.connectors.fetchPeriod")}</span>
        {[1, 3, 7, 14, 30, 90].map(d => (
          <button
            key={d}
            onClick={() => setFetchDays(d)}
            className={`rounded-md px-2 py-1 text-xs font-medium transition-colors ${
              fetchDays === d
                ? "bg-brand-500 text-white"
                : "text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
            }`}
          >
            {d}d
          </button>
        ))}
        <div className="mx-2 h-4 w-px bg-gray-300 dark:bg-gray-600" />
        <label className="flex cursor-pointer items-center gap-2 text-xs font-medium text-gray-600 dark:text-gray-400">
          <div className="relative">
            <input type="checkbox" checked={autoProcess} onChange={e => setAutoProcess(e.target.checked)} className="peer sr-only" />
            <div className="h-5 w-9 rounded-full bg-gray-300 transition-colors peer-checked:bg-brand-500 dark:bg-gray-600 dark:peer-checked:bg-brand-600" />
            <div className="absolute left-0.5 top-0.5 h-4 w-4 rounded-full bg-white shadow transition-transform peer-checked:translate-x-4" />
          </div>
          Auto-process intents
        </label>
      </div>

      {testResult && (
        <div className={`rounded-xl p-3 text-sm ${testResult.ok ? "bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400" : "bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400"}`}>
          {testResult.msg}
        </div>
      )}

      {fetchResult && (
        <div className="rounded-xl border border-green-200 bg-green-50 p-3 text-sm text-green-700 dark:border-green-800 dark:bg-green-900/20 dark:text-green-400">
          {fetchResult.count} email(s) fetched, {fetchResult.processed} processed
        </div>
      )}

      {/* Fetch + Process progress */}
      {fetchProgress.length > 0 && (
        <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
          <div className="mb-2 flex items-center justify-between">
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300">{translate("aiflow.pipeline.title")}</p>
            {fetching && (
              <span className="text-xs text-brand-600 dark:text-brand-400">
                {fetchProgress.filter(fp => fp.status === "done").length}/{fetchProgress.length}
              </span>
            )}
          </div>
          <FileProgressBar done={fetchProgress.filter(fp => fp.status === "done").length} total={fetchProgress.length} />
          <div className="max-h-64 overflow-y-auto">
            {fetchProgress.map((fp, i) => <FileProgressRow key={i} fp={fp} />)}
          </div>
        </div>
      )}

      {/* Connectors Table */}
      {error ? (
        <ErrorState error={error} onRetry={refetch} />
      ) : (
        <DataTable
          data={connectors as unknown as Record<string, unknown>[]}
          loading={loading}
          searchKeys={["name", "host", "provider"]}
          emptyMessageKey="aiflow.connectors.noConnectors"
          onRowClick={openEdit}
          columns={[
            { key: "name", label: translate("aiflow.connectors.name"), render: (item) => <span className="font-medium text-gray-900 dark:text-gray-100">{String(item.name)}</span> },
            { key: "provider", label: translate("aiflow.connectors.provider"), render: (item) => <span className="rounded-full bg-brand-50 px-2 py-0.5 text-xs font-medium text-brand-700 dark:bg-brand-900/30 dark:text-brand-400">{String(item.provider).toUpperCase()}</span> },
            { key: "host", label: translate("aiflow.connectors.host"), render: (item) => {
              const p = String(item.provider);
              if (p === "outlook_com") return <span className="text-gray-500 dark:text-gray-400 italic">local</span>;
              return <span className="text-gray-600 dark:text-gray-400">{String(item.host)}:{String(item.port)}</span>;
            }},
            { key: "mailbox", label: translate("aiflow.connectors.mailbox"), render: (item) => <span className="text-gray-600 dark:text-gray-400">{String(item.mailbox)}</span> },
            { key: "polling_interval_minutes", label: translate("aiflow.connectors.pollingInterval"), render: (item) => <span className="text-gray-600 dark:text-gray-400">{String(item.polling_interval_minutes)} min</span> },
            { key: "is_active", label: translate("aiflow.connectors.status"), render: (item) => {
              const active = item.is_active as boolean;
              return <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${active ? "bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-400" : "bg-gray-100 text-gray-500"}`}>
                <span className={`h-1.5 w-1.5 rounded-full ${active ? "bg-green-500" : "bg-gray-400"}`} />{active ? translate("aiflow.connectors.active") : "Paused"}
              </span>;
            }},
            { key: "actions", label: "Actions", sortable: false, render: (item) => (
              <div className="flex gap-1">
                <button onClick={(e) => { e.stopPropagation(); handleTest(String(item.id)); }} disabled={testing === String(item.id)} className="rounded-md bg-gray-100 px-2 py-1 text-xs font-medium text-gray-600 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-400">{testing === String(item.id) ? "..." : translate("aiflow.connectors.testConnection")}</button>
                <button onClick={(e) => { e.stopPropagation(); handleFetch(String(item.id)); }} disabled={fetching === String(item.id)} className="rounded-md bg-brand-50 px-2 py-1 text-xs font-medium text-brand-600 hover:bg-brand-100 disabled:opacity-50 dark:bg-brand-900/30 dark:text-brand-400">{fetching === String(item.id) ? `${fetchDays}d...` : `${translate("aiflow.connectors.fetchNow")} (${fetchDays}d)`}</button>
              </div>
            )},
          ]}
        />
      )}

      {/* Connector form dialog */}
      {editConnector && (
        <ConnectorFormDialog
          initial={editConnector}
          onSave={() => { setEditConnector(null); refetch(); }}
          onClose={() => setEditConnector(null)}
          translate={translate}
        />
      )}
    </div>
  );
}

// --- Main ---

// --- Pipeline Types ---

interface PipelineListItem {
  id: string;
  name: string;
  enabled: boolean;
}

interface ScanResponseItem {
  package_id: string;
  label: string;
  display_name: string;
  confidence: number;
  method: string;
}

interface ScanResponse {
  config_id: string;
  processed: number;
  items: ScanResponseItem[];
  error: string | null;
  source: string;
}

export function Emails() {
  const translate = useTranslate();
  const navigate = useNavigate();
  const [tab, setTab] = useState<"inbox" | "upload" | "connectors">("inbox");
  const [refreshKey, setRefreshKey] = useState(0);
  const triggerRefresh = useCallback(() => setRefreshKey(k => k + 1), []);

  // Scan Mailbox state
  const [scanning, setScanning] = useState(false);
  const [scanResult, setScanResult] = useState<{ status: string; runId: string } | null>(null);
  const [scanError, setScanError] = useState<string | null>(null);

  const handleScanMailbox = async () => {
    setScanning(true);
    setScanResult(null);
    setScanError(null);
    try {
      // S106/S107 scan_and_classify endpoint: fetch new emails from the
      // configured IMAP inbox, classify intent with the sklearn+LLM hybrid,
      // optionally route via IntentRoutingPolicy (server-side config).
      const connectors = await fetchApi<ConnectorItem[]>("GET", "/api/v1/emails/connectors");
      const active = connectors.filter(c => c.is_active);
      if (active.length === 0) {
        setScanError(translate("aiflow.emails.noActiveConnector"));
        return;
      }
      // Pick the first active connector — a picker UI is the next iteration
      // when there is more than one active. For now the most-recently-created
      // active connector wins (API returns ORDER BY created_at DESC).
      const connector = active[0];
      const result = await fetchApi<ScanResponse>(
        "POST",
        `/api/v1/emails/scan/${connector.id}`,
        { tenant_id: "default", max_items: 50 },
      );
      const msg = translate("aiflow.emails.scanSuccessful")
        .replace("{count}", String(result.processed))
        .replace("{connector}", connector.name);
      setScanResult({ status: msg, runId: connector.id });
      triggerRefresh();
    } catch (e) {
      setScanError(e instanceof Error ? e.message : "Scan failed");
    } finally {
      setScanning(false);
    }
  };

  const tabs = [
    { key: "inbox" as const, label: "Inbox" },
    { key: "upload" as const, label: "Upload" },
    { key: "connectors" as const, label: translate("aiflow.connectors.menuLabel") },
  ];

  return (
    <PageLayout titleKey="aiflow.emails.title" subtitleKey="aiflow.emails.detail">
      {/* Scan Mailbox action bar */}
      <div className="mb-4 flex items-center gap-3">
        <button
          onClick={() => void handleScanMailbox()}
          disabled={scanning}
          className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-brand-600 disabled:opacity-50"
        >
          {scanning ? translate("aiflow.emails.scanning") : translate("aiflow.emails.scanMailbox")}
        </button>
        {scanResult && (
          <div className="rounded-lg border border-green-200 bg-green-50 px-3 py-1.5 text-sm text-green-700 dark:border-green-800 dark:bg-green-900/20 dark:text-green-400">
            Pipeline elindult — <button onClick={() => navigate("/documents")} className="font-semibold underline">
              {translate("aiflow.emails.scanComplete")} →
            </button>
          </div>
        )}
        {scanError && (
          <span className="rounded-lg border border-red-200 bg-red-50 px-3 py-1.5 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400">
            {scanError}
          </span>
        )}
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

      {tab === "inbox" && <InboxTab refreshKey={refreshKey} />}
      {tab === "upload" && <UploadTab onProcessed={triggerRefresh} />}
      {tab === "connectors" && <ConnectorsTab onProcessed={triggerRefresh} />}
    </PageLayout>
  );
}
