/**
 * AIFlow Media — F6.4 upload + STT jobs table.
 */

import { useState, useCallback } from "react";
import { useTranslate } from "../lib/i18n";
import { useApi } from "../lib/hooks";
import { uploadFile } from "../lib/api-client";
import { PageLayout } from "../layout/PageLayout";
import { ErrorState } from "../components-new/ErrorState";
import { DataTable, type Column } from "../components-new/DataTable";

interface MediaJob { id: string; filename: string; status: string; provider: string | null; duration_seconds: number | null; created_at: string; transcript: string | null; }
interface MediaResponse { jobs: MediaJob[]; total: number; source: string; }

export function Media() {
  const translate = useTranslate();
  const { data, loading, error, refetch } = useApi<MediaResponse>("/api/v1/media");
  const [uploading, setUploading] = useState(false);

  const handleUpload = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.length) return;
    setUploading(true);
    try {
      const fd = new FormData();
      Array.from(e.target.files).forEach(f => fd.append("files", f));
      await uploadFile("/api/v1/media/upload", fd);
      refetch();
    } catch { /* */ }
    finally { setUploading(false); }
  }, [refetch]);

  const columns: Column<Record<string, unknown>>[] = [
    { key: "filename", label: translate("aiflow.media.filename"), render: (item) => <span className="font-medium text-gray-900 dark:text-gray-100">{String(item.filename)}</span> },
    { key: "status", label: translate("aiflow.media.status"), render: (item) => {
      const s = String(item.status);
      const color = s === "completed" ? "bg-green-50 text-green-700" : s === "processing" ? "bg-blue-50 text-blue-700" : "bg-gray-100 text-gray-600";
      return <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${color}`}>{s}</span>;
    }},
    { key: "provider", label: translate("aiflow.media.provider"), render: (item) => <span className="text-gray-500">{String(item.provider ?? "—")}</span> },
    { key: "duration_seconds", label: translate("aiflow.media.duration"), getValue: (item) => item.duration_seconds as number ?? 0, render: (item) => { const d = item.duration_seconds as number | null; return <span className="text-gray-500">{d ? `${Math.floor(d/60)}:${String(Math.floor(d%60)).padStart(2,"0")}` : "—"}</span>; }},
    { key: "created_at", label: "Created", render: (item) => <span className="text-xs text-gray-500">{new Date(String(item.created_at)).toLocaleDateString()}</span> },
  ];

  return (
    <PageLayout titleKey="aiflow.media.title" subtitleKey="aiflow.media.subtitle" source={data?.source}>
      <div className="mb-4 flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-gray-300 bg-white p-6 dark:border-gray-600 dark:bg-gray-900">
        <p className="text-sm text-gray-600 dark:text-gray-400">{translate("aiflow.media.dropzone")}</p>
        <label className="mt-2 cursor-pointer rounded-lg bg-brand-500 px-4 py-2 text-sm font-medium text-white hover:bg-brand-600">
          {uploading ? translate("aiflow.common.loading") : "Upload"}
          <input type="file" accept="video/*,audio/*" multiple className="hidden" onChange={handleUpload} />
        </label>
      </div>
      {error ? <ErrorState error={error} onRetry={refetch} /> :
        <DataTable data={(data?.jobs ?? []) as unknown as Record<string, unknown>[]} columns={columns} loading={loading} searchKeys={["filename", "status"]} />
      }
    </PageLayout>
  );
}
