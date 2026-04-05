/**
 * AIFlow Media — F6.4 upload + STT jobs table.
 * Per-file upload with FileProgressRow (consistent with Documents/RAG/ProcessDocs).
 */

import { useState, useCallback } from "react";
import { useTranslate } from "../lib/i18n";
import { useApi } from "../lib/hooks";
import { uploadFile, fetchApi } from "../lib/api-client";
import { PageLayout } from "../layout/PageLayout";
import { ErrorState } from "../components-new/ErrorState";
import { DataTable, type Column } from "../components-new/DataTable";
import { FileProgressRow, FileProgressBar, type FileProgress } from "../components-new/FileProgress";

interface TranscriptSection { title: string; summary: string; content: string; start_time: number; end_time: number; }
interface TranscriptStructured { title: string; summary: string; sections?: TranscriptSection[]; key_topics?: string[]; vocabulary?: string[]; }
interface MediaJob { id: string; filename: string; status: string; provider: string | null; duration_seconds: number | null; created_at: string; transcript_raw: string | null; transcript_structured: TranscriptStructured | null; error: string | null; processing_time_ms: number | null; }
interface MediaResponse { jobs: MediaJob[]; total: number; source: string; }

function TranscriptSections({ sections }: { sections: TranscriptSection[] }) {
  const [openIdx, setOpenIdx] = useState<number | null>(null);
  return (
    <div className="space-y-1">
      {sections.map((s, i) => (
        <div key={i} className="rounded-lg border border-gray-100 dark:border-gray-700">
          <button
            onClick={() => setOpenIdx(openIdx === i ? null : i)}
            className="flex w-full items-center justify-between rounded-lg px-3 py-2 text-left hover:bg-gray-50 dark:hover:bg-gray-800/50"
          >
            <div className="flex items-center gap-2">
              <svg className={`h-3 w-3 shrink-0 text-gray-400 transition-transform ${openIdx === i ? "rotate-90" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
              </svg>
              <span className="text-sm font-medium text-gray-900 dark:text-gray-100">{s.title}</span>
            </div>
            <span className="text-xs text-gray-400">
              {Math.floor(s.start_time / 60)}:{String(Math.floor(s.start_time % 60)).padStart(2, "0")} — {Math.floor(s.end_time / 60)}:{String(Math.floor(s.end_time % 60)).padStart(2, "0")}
            </span>
          </button>
          {openIdx === i && (
            <div className="border-t border-gray-100 px-3 pb-3 pt-2 dark:border-gray-700">
              {s.summary && <p className="mb-2 text-xs font-medium text-brand-600 dark:text-brand-400">{s.summary}</p>}
              <p className="text-xs leading-relaxed text-gray-700 dark:text-gray-300">{s.content}</p>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

export function Media() {
  const translate = useTranslate();
  const { data, loading, error, refetch } = useApi<MediaResponse>("/api/v1/media");
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [fileProgress, setFileProgress] = useState<FileProgress[]>([]);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [selectedJob, setSelectedJob] = useState<MediaJob | null>(null);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const dropped = Array.from(e.dataTransfer.files).filter(
      f => f.type.startsWith("video/") || f.type.startsWith("audio/"),
    );
    setFiles(prev => [...prev, ...dropped]);
  }, []);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) setFiles(prev => [...prev, ...Array.from(e.target.files!)]);
  }, []);

  const handleUpload = async () => {
    if (files.length === 0) return;
    setUploading(true);
    setUploadError(null);

    // Each file is uploaded separately (backend expects singular "file")
    const steps = ["upload", "process"];
    setFileProgress(files.map(f => ({
      name: f.name,
      status: "pending" as const,
      steps: steps.map(s => ({ name: s, status: "pending" as const })),
    })));

    for (let i = 0; i < files.length; i++) {
      const f = files[i];
      setFileProgress(prev => prev.map((fp, idx) =>
        idx === i ? { ...fp, status: "processing", steps: fp.steps.map((s, si) => si === 0 ? { ...s, status: "running" as const } : s) } : fp
      ));

      try {
        const fd = new FormData();
        fd.append("file", f);

        // Upload step done
        setFileProgress(prev => prev.map((fp, idx) =>
          idx === i ? { ...fp, steps: fp.steps.map((s, si) => si === 0 ? { ...s, status: "done" as const } : si === 1 ? { ...s, status: "running" as const } : s) } : fp
        ));

        await uploadFile("/api/v1/media/upload", fd);

        // Process step done
        setFileProgress(prev => prev.map((fp, idx) =>
          idx === i ? { ...fp, status: "done", steps: fp.steps.map(s => ({ ...s, status: "done" as const })) } : fp
        ));
      } catch (err) {
        const errMsg = err instanceof Error ? err.message : "Upload failed";
        setFileProgress(prev => prev.map((fp, idx) =>
          idx === i ? { ...fp, status: "error", error: errMsg, steps: fp.steps.map(s => s.status === "running" ? { ...s, status: "error" as const } : s) } : fp
        ));
        setUploadError(errMsg);
      }
    }

    setUploading(false);
    setFiles([]);
    refetch();
  };

  const handleReset = () => {
    setFiles([]);
    setFileProgress([]);
    setUploadError(null);
  };

  const doneCount = fileProgress.filter(fp => fp.status === "done").length;

  const columns: Column<Record<string, unknown>>[] = [
    { key: "filename", label: translate("aiflow.media.filename"), render: (item) => <span className="font-medium text-gray-900 dark:text-gray-100">{String(item.filename)}</span> },
    { key: "status", label: translate("aiflow.media.status"), render: (item) => {
      const s = String(item.status);
      const color = s === "completed" ? "bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-400" : s === "running" ? "bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400" : s === "failed" ? "bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-400" : "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400";
      return <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${color}`}>{s}</span>;
    }},
    { key: "provider", label: translate("aiflow.media.provider"), render: (item) => <span className="text-gray-500 dark:text-gray-400">{String(item.provider ?? "—")}</span> },
    { key: "duration_seconds", label: translate("aiflow.media.duration"), getValue: (item) => item.duration_seconds as number ?? 0, render: (item) => { const d = item.duration_seconds as number | null; return <span className="text-gray-500 dark:text-gray-400">{d ? `${Math.floor(d/60)}:${String(Math.floor(d%60)).padStart(2,"0")}` : "—"}</span>; }},
    { key: "created_at", label: "Created", render: (item) => <span className="text-xs text-gray-500 dark:text-gray-400">{new Date(String(item.created_at)).toLocaleDateString()}</span> },
  ];

  return (
    <PageLayout titleKey="aiflow.media.title" subtitleKey="aiflow.media.subtitle" source={data?.source}>
      {/* Dropzone */}
      <div
        onDragOver={e => e.preventDefault()}
        onDrop={handleDrop}
        className="mb-4 flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-gray-300 bg-white p-8 text-center transition-colors hover:border-brand-400 dark:border-gray-600 dark:bg-gray-900 dark:hover:border-brand-500"
      >
        <svg className="mb-3 h-10 w-10 text-gray-300 dark:text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 10.5l4.72-4.72a.75.75 0 011.28.53v11.38a.75.75 0 01-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 002.25-2.25v-9a2.25 2.25 0 00-2.25-2.25h-9A2.25 2.25 0 002.25 7.5v9a2.25 2.25 0 002.25 2.25z" />
        </svg>
        <p className="text-sm font-medium text-gray-700 dark:text-gray-300">{translate("aiflow.media.dropzone")}</p>
        <p className="mt-1 text-xs text-gray-400">MP4, MKV, MP3, WAV, WebM</p>
        <label className="mt-3 cursor-pointer rounded-lg bg-brand-500 px-4 py-2 text-sm font-medium text-white hover:bg-brand-600">
          {translate("aiflow.media.selectFiles")}
          <input type="file" accept="video/*,audio/*" multiple className="hidden" onChange={handleFileSelect} />
        </label>
      </div>

      {/* Selected files (before upload) */}
      {files.length > 0 && fileProgress.length === 0 && (
        <div className="mb-4 rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              {files.length} file(s)
            </span>
            <div className="flex gap-2">
              <button onClick={handleReset} className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-400">
                {translate("aiflow.common.cancel")}
              </button>
              <button onClick={handleUpload} disabled={uploading} className="rounded-lg bg-brand-500 px-4 py-1.5 text-xs font-semibold text-white hover:bg-brand-600 disabled:opacity-50">
                {uploading ? translate("aiflow.common.loading") : translate("aiflow.media.process")}
              </button>
            </div>
          </div>
          {files.map((f, i) => (
            <div key={i} className="flex items-center gap-2 border-t border-gray-100 py-2 text-sm dark:border-gray-800">
              <span className="text-gray-600 dark:text-gray-400">{f.name}</span>
              <span className="text-xs text-gray-400">{(f.size / 1024 / 1024).toFixed(1)} MB</span>
            </div>
          ))}
        </div>
      )}

      {/* Per-file progress */}
      {fileProgress.length > 0 && (
        <div className="mb-4 rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
          <div className="mb-2 flex items-center justify-between">
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
              {translate("aiflow.pipeline.title")}
            </p>
            {uploading && (
              <span className="text-xs text-brand-600 dark:text-brand-400">
                {doneCount}/{fileProgress.length}
              </span>
            )}
          </div>
          <FileProgressBar done={doneCount} total={fileProgress.length} />
          {fileProgress.map((fp, i) => (
            <FileProgressRow key={i} fp={fp} />
          ))}
          {!uploading && (
            <button onClick={handleReset} className="mt-3 rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-400">
              {translate("aiflow.documentUpload.newBatch")}
            </button>
          )}
        </div>
      )}

      {uploadError && <ErrorState error={uploadError} onRetry={handleUpload} />}

      {/* Transcript viewer */}
      {selectedJob && (
        <div className="mb-4 rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
          <div className="mb-3 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">{selectedJob.filename}</h3>
              <div className="mt-1 flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
                {selectedJob.duration_seconds && <span>{Math.floor(selectedJob.duration_seconds / 60)}:{String(Math.floor(selectedJob.duration_seconds % 60)).padStart(2, "0")}</span>}
                {selectedJob.processing_time_ms && <span>{(selectedJob.processing_time_ms / 1000).toFixed(1)}s processing</span>}
                {selectedJob.status === "failed" && selectedJob.error && <span className="text-red-500">{selectedJob.error.substring(0, 100)}</span>}
              </div>
            </div>
            <button onClick={() => setSelectedJob(null)} className="rounded-md p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-800">
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
          </div>

          {selectedJob.transcript_structured ? (
            <div className="space-y-3">
              {/* Title + Summary */}
              <div>
                <h4 className="text-base font-semibold text-gray-900 dark:text-gray-100">{selectedJob.transcript_structured.title}</h4>
                {selectedJob.transcript_structured.summary && (
                  <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">{selectedJob.transcript_structured.summary}</p>
                )}
              </div>

              {/* Key topics */}
              {selectedJob.transcript_structured.key_topics && selectedJob.transcript_structured.key_topics.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {selectedJob.transcript_structured.key_topics.map((t, i) => (
                    <span key={i} className="rounded-full bg-brand-50 px-2 py-0.5 text-xs font-medium text-brand-700 dark:bg-brand-900/30 dark:text-brand-400">{t}</span>
                  ))}
                </div>
              )}

              {/* Sections (collapsible) */}
              {selectedJob.transcript_structured.sections && selectedJob.transcript_structured.sections.length > 0 && (
                <TranscriptSections sections={selectedJob.transcript_structured.sections} />
              )}
            </div>
          ) : selectedJob.transcript_raw ? (
            <pre className="max-h-64 overflow-auto whitespace-pre-wrap rounded-lg bg-gray-50 p-3 text-xs text-gray-700 dark:bg-gray-800 dark:text-gray-300">
              {selectedJob.transcript_raw}
            </pre>
          ) : (
            <p className="text-sm text-gray-400">{translate("aiflow.media.noTranscript")}</p>
          )}
        </div>
      )}

      {/* Jobs table */}
      {error ? <ErrorState error={error} onRetry={refetch} /> :
        <DataTable
          data={(data?.jobs ?? []) as unknown as Record<string, unknown>[]}
          columns={columns}
          loading={loading}
          searchKeys={["filename", "status"]}
          onRowClick={(item) => setSelectedJob(item as unknown as MediaJob)}
        />
      }
    </PageLayout>
  );
}
