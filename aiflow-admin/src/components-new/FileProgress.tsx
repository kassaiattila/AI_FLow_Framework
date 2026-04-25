/**
 * FileProgress — shared per-file pipeline progress display.
 * Used by Documents upload and RAG ingest tabs.
 */

export interface FileStepState {
  name: string;
  status: "pending" | "running" | "done" | "error";
  elapsed_ms?: number;
}

export interface FileProgress {
  name: string;
  status: "pending" | "processing" | "done" | "error";
  steps: FileStepState[];
  error?: string;
}

const STEP_LABELS: Record<string, string> = {
  parse: "Parse",
  classify: "Classify",
  extract: "Extract",
  validate: "Validate",
  store: "Store",
  upload: "Upload",
  chunk: "Chunk",
  embed: "Embed",
};

export function FileProgressRow({ fp }: { fp: FileProgress }) {
  const icon =
    fp.status === "done"
      ? "✓"
      : fp.status === "error"
        ? "✗"
        : fp.status === "processing"
          ? "▶"
          : "…";
  const iconColor =
    fp.status === "done"
      ? "text-green-600 dark:text-green-400"
      : fp.status === "error"
        ? "text-red-500"
        : fp.status === "processing"
          ? "text-brand-500"
          : "text-gray-400";

  return (
    <div className="flex items-center gap-3 border-t border-gray-100 py-2.5 first:border-t-0 dark:border-gray-800">
      <span className={`w-5 text-center text-sm font-bold ${iconColor}`}>
        {icon}
      </span>
      <span
        className="min-w-0 flex-1 truncate text-sm font-medium text-gray-700 dark:text-gray-300"
        title={fp.name}
      >
        {fp.name}
      </span>
      <div className="flex gap-1">
        {fp.steps.map((s, i) => (
          <div
            key={i}
            className="flex flex-col items-center gap-0.5"
            title={`${STEP_LABELS[s.name] ?? s.name}${s.elapsed_ms ? ` (${(s.elapsed_ms / 1000).toFixed(1)}s)` : ""}`}
          >
            <div
              className={`h-1.5 w-8 rounded-full ${
                s.status === "done"
                  ? "bg-green-500"
                  : s.status === "running"
                    ? "bg-brand-500 animate-pulse"
                    : s.status === "error"
                      ? "bg-red-500"
                      : "bg-gray-200 dark:bg-gray-700"
              }`}
            />
            <span className="text-[9px] text-gray-400">
              {STEP_LABELS[s.name] ?? s.name}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

/** Overall progress bar (only shown for multi-file batches) */
export function FileProgressBar({
  done,
  total,
}: {
  done: number;
  total: number;
}) {
  if (total <= 1) return null;
  return (
    <div className="mb-3 h-1.5 w-full overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
      <div
        className="h-full rounded-full bg-brand-500 transition-all duration-300"
        style={{ width: `${total > 0 ? (done / total) * 100 : 0}%` }}
      />
    </div>
  );
}
