/**
 * AIFlow Emails — F6.3 tabbed page (Inbox + Upload + Connectors).
 * Replaces old MUI EmailList + EmailUpload + EmailConnectors.
 */

import { useState, useCallback } from "react";
import { useTranslate } from "../lib/i18n";
import { useApi } from "../lib/hooks";
import { fetchApi, uploadFile } from "../lib/api-client";
import { PageLayout } from "../layout/PageLayout";
import { ErrorState } from "../components-new/ErrorState";
import { DataTable, type Column } from "../components-new/DataTable";

// --- Types ---

interface EmailItem {
  id: string;
  sender: string;
  subject: string;
  received_at: string | null;
  intent: string | null;
  confidence: number | null;
  priority: string | null;
  attachments_count: number;
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

function InboxTab() {
  const translate = useTranslate();
  const { data, loading, error, refetch } = useApi<EmailsResponse>("/api/v1/emails");
  const emails = data?.emails ?? [];

  const priorityColor: Record<string, string> = {
    critical: "bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-400",
    high: "bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
    normal: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400",
    low: "bg-gray-50 text-gray-500 dark:bg-gray-800 dark:text-gray-400",
  };

  return (
    <>
      {/* KPIs */}
      <div className="mb-4 grid grid-cols-1 gap-4 md:grid-cols-3">
        <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
          <p className="text-xs font-medium text-gray-500">{translate("aiflow.emails.title")}</p>
          <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-gray-100">{data?.total ?? 0}</p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
          <p className="text-xs font-medium text-gray-500">{translate("aiflow.emails.intentSection")}</p>
          <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-gray-100">
            {emails.filter(e => e.intent).length}
          </p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
          <p className="text-xs font-medium text-gray-500">{translate("aiflow.emails.attachments")}</p>
          <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-gray-100">
            {emails.reduce((s, e) => s + e.attachments_count, 0)}
          </p>
        </div>
      </div>

      {/* Table — sortable, searchable */}
      {error ? (
        <ErrorState error={error} onRetry={refetch} />
      ) : (
        <DataTable
          data={emails as unknown as Record<string, unknown>[]}
          loading={loading}
          searchKeys={["sender", "subject", "intent"]}
          pageSize={10}
          columns={[
            { key: "sender", label: translate("aiflow.emails.sender"), render: (item) => <span className="font-medium text-gray-900 dark:text-gray-100">{String(item.sender ?? "")}</span> },
            { key: "subject", label: translate("aiflow.emails.subject"), render: (item) => <span className="text-gray-600 dark:text-gray-400">{String(item.subject ?? "")}</span> },
            { key: "intent", label: translate("aiflow.emails.intent"), render: (item) => item.intent ? <span className="rounded-full bg-brand-50 px-2 py-0.5 text-xs font-medium text-brand-700 dark:bg-brand-900/30 dark:text-brand-400">{String(item.intent)}</span> : <span>—</span> },
            { key: "priority", label: translate("aiflow.emails.priority"), render: (item) => item.priority ? <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${priorityColor[String(item.priority)] ?? priorityColor.normal}`}>{String(item.priority)}</span> : <span>—</span> },
            { key: "confidence", label: translate("aiflow.emails.confidence"), getValue: (item) => (item.confidence as number) ?? 0, render: (item) => <span className="text-gray-600 dark:text-gray-400">{item.confidence ? `${item.confidence}%` : "—"}</span> },
            { key: "received_at", label: translate("aiflow.emails.received"), render: (item) => <span className="text-xs text-gray-500">{item.received_at ? new Date(String(item.received_at)).toLocaleString() : "—"}</span> },
          ]}
        />
      )}
    </>
  );
}

// --- Upload Tab ---

function UploadTab() {
  const translate = useTranslate();
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) setFiles(Array.from(e.target.files));
  }, []);

  const handleUpload = async () => {
    if (files.length === 0) return;
    setUploading(true);
    setError(null);
    try {
      const formData = new FormData();
      files.forEach(f => formData.append("files", f));
      await uploadFile("/api/v1/emails/upload", formData);
      setResult(`${files.length} email(s) uploaded`);
      setFiles([]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-gray-300 bg-white p-8 text-center dark:border-gray-600 dark:bg-gray-900">
        <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
          {translate("aiflow.emailUpload.dropzone")}
        </p>
        <label className="mt-3 cursor-pointer rounded-lg bg-brand-500 px-4 py-2 text-sm font-medium text-white hover:bg-brand-600">
          {translate("aiflow.emailUpload.uploaded")}
          <input type="file" accept=".eml,.msg" multiple className="hidden" onChange={handleFileSelect} />
        </label>
      </div>
      {files.length > 0 && (
        <div className="flex items-center justify-between rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
          <span className="text-sm text-gray-600 dark:text-gray-400">{files.length} file(s) selected</span>
          <button onClick={handleUpload} disabled={uploading} className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-600 disabled:opacity-50">
            {uploading ? translate("aiflow.common.loading") : translate("aiflow.emailUpload.process")}
          </button>
        </div>
      )}
      {error && <ErrorState error={error} />}
      {result && <div className="rounded-xl border border-green-200 bg-green-50 p-4 text-sm text-green-700 dark:border-green-800 dark:bg-green-900/20 dark:text-green-400">{result}</div>}
    </div>
  );
}

// --- Connectors Tab ---

function ConnectorsTab() {
  const translate = useTranslate();
  const { data, loading, error, refetch } = useApi<ConnectorItem[]>("/api/v1/emails/connectors");
  const connectors = Array.isArray(data) ? data : [];
  const [testing, setTesting] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<{ id: string; ok: boolean; msg: string } | null>(null);

  const handleTest = async (id: string) => {
    setTesting(id);
    setTestResult(null);
    try {
      await fetchApi("POST", `/api/v1/emails/connectors/${id}/test`);
      setTestResult({ id, ok: true, msg: translate("aiflow.connectors.testSuccess") });
    } catch {
      setTestResult({ id, ok: false, msg: translate("aiflow.connectors.testFailed") });
    } finally {
      setTesting(null);
    }
  };

  const handleFetch = async (id: string) => {
    try {
      await fetchApi("POST", "/api/v1/emails/fetch", { config_id: id });
      refetch();
    } catch { /* ignore */ }
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-500">{connectors.length} connector(s)</span>
        <button className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-600">
          + {translate("aiflow.connectors.create")}
        </button>
      </div>

      {testResult && (
        <div className={`rounded-xl p-3 text-sm ${testResult.ok ? "bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400" : "bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400"}`}>
          {testResult.msg}
        </div>
      )}

      {/* Connectors Table — sortable, searchable */}
      {error ? (
        <ErrorState error={error} onRetry={refetch} />
      ) : (
        <DataTable
          data={connectors as unknown as Record<string, unknown>[]}
          loading={loading}
          searchKeys={["name", "host", "provider"]}
          emptyMessageKey="aiflow.connectors.noConnectors"
          columns={[
            { key: "name", label: translate("aiflow.connectors.name"), render: (item) => <span className="font-medium text-gray-900 dark:text-gray-100">{String(item.name)}</span> },
            { key: "provider", label: translate("aiflow.connectors.provider"), render: (item) => <span className="rounded-full bg-brand-50 px-2 py-0.5 text-xs font-medium text-brand-700 dark:bg-brand-900/30 dark:text-brand-400">{String(item.provider).toUpperCase()}</span> },
            { key: "host", label: translate("aiflow.connectors.host"), render: (item) => <span className="text-gray-600 dark:text-gray-400">{String(item.host)}:{String(item.port)}</span> },
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
                <button onClick={() => handleTest(String(item.id))} disabled={testing === String(item.id)} className="rounded-md bg-gray-100 px-2 py-1 text-xs font-medium text-gray-600 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-400">{testing === String(item.id) ? "..." : translate("aiflow.connectors.testConnection")}</button>
                <button onClick={() => handleFetch(String(item.id))} className="rounded-md bg-brand-50 px-2 py-1 text-xs font-medium text-brand-600 hover:bg-brand-100 dark:bg-brand-900/30 dark:text-brand-400">{translate("aiflow.connectors.fetchNow")}</button>
              </div>
            )},
          ]}
        />
      )}
    </div>
  );
}

// --- Main ---

export function Emails() {
  const translate = useTranslate();
  const [tab, setTab] = useState<"inbox" | "upload" | "connectors">("inbox");

  const tabs = [
    { key: "inbox" as const, label: "Inbox" },
    { key: "upload" as const, label: "Upload" },
    { key: "connectors" as const, label: translate("aiflow.connectors.menuLabel") },
  ];

  return (
    <PageLayout titleKey="aiflow.emails.title" subtitleKey="aiflow.emails.detail">
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

      {tab === "inbox" && <InboxTab />}
      {tab === "upload" && <UploadTab />}
      {tab === "connectors" && <ConnectorsTab />}
    </PageLayout>
  );
}
