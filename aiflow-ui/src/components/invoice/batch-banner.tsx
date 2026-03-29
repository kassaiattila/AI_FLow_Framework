"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";

export type DocBatchStatus = "pending" | "processing" | "completed" | "failed";

export interface BatchItem {
  file: string;
  displayName: string;
  status: DocBatchStatus;
  step?: string; // current step name during processing
  confidence?: number;
}

export type BatchState =
  | { status: "idle" }
  | { status: "running"; total: number; current: number; currentFile: string; startedAt: number; items: BatchItem[] }
  | { status: "completed"; total: number; succeeded: number; failed: number; durationMs: number; items: BatchItem[] };

// SessionStorage persistence
const BATCH_KEY = "aiflow_batch_state";

export function saveBatchToSession(state: BatchState) {
  try { sessionStorage.setItem(BATCH_KEY, JSON.stringify(state)); } catch { /* ok */ }
}

export function loadBatchFromSession(): BatchState | null {
  try {
    const raw = sessionStorage.getItem(BATCH_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch { return null; }
}

export function clearBatchSession() {
  try { sessionStorage.removeItem(BATCH_KEY); } catch { /* ok */ }
}

// --- Component ---

interface BatchBannerProps {
  state: BatchState;
  onStop: () => void;
  onDismiss: () => void;
}

const STEP_LABELS: Record<string, string> = {
  parse_pdf: "PDF",
  extract_fields: "Kinyeres",
  validate_output: "Validalas",
  export_csv: "Export",
};

export function BatchBanner({ state, onStop, onDismiss }: BatchBannerProps) {
  if (state.status === "idle") return null;

  const isRunning = state.status === "running";
  const isDone = state.status === "completed";
  const items = state.items || [];

  const total = state.total;
  // Count actual progress from items (more accurate than position counter)
  const doneCount = items.filter((i) => i.status === "completed" || i.status === "failed").length;
  const processingCount = items.filter((i) => i.status === "processing").length;
  const current = isRunning ? doneCount + processingCount : doneCount;
  const progress = total > 0 ? Math.round((doneCount / total) * 100) : 0;

  // ETA
  let eta = "";
  if (isRunning && state.current > 0) {
    const elapsed = Date.now() - state.startedAt;
    const remaining = ((state.total - state.current) * elapsed) / state.current;
    eta = remaining > 60000 ? `~${Math.ceil(remaining / 60000)} perc` : `~${Math.ceil(remaining / 1000)}s`;
  }

  return (
    <Card>
      <CardContent className="py-3 px-4 space-y-2">
        {/* Header row */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-sm font-medium">
              {isRunning
                ? `Feldolgozas: ${doneCount + 1}/${total}`
                : `Batch kesz: ${doneCount}/${total}`}
            </span>
            {isRunning && <span className="text-xs text-muted-foreground font-mono truncate max-w-[200px]">{state.currentFile}</span>}
            {isDone && (
              <div className="flex gap-2">
                {state.succeeded > 0 && <Badge className="bg-green-100 text-green-700 text-xs">{state.succeeded} sikeres</Badge>}
                {state.failed > 0 && <Badge className="bg-red-100 text-red-700 text-xs">{state.failed} hiba</Badge>}
                {items.filter((i) => i.status === "pending").length > 0 && (
                  <Badge className="bg-gray-100 text-gray-600 text-xs">{items.filter((i) => i.status === "pending").length} kihagyva</Badge>
                )}
                {state.durationMs > 0 && <span className="text-xs text-muted-foreground">{(state.durationMs / 1000).toFixed(1)}s</span>}
              </div>
            )}
            {eta && <span className="text-[10px] text-muted-foreground">{eta}</span>}
          </div>
          <div className="flex gap-1.5">
            {isRunning && <button onClick={onStop} className="px-2 py-1 rounded text-xs border border-red-200 text-red-600 hover:bg-red-50">Leall</button>}
            {isDone && <button onClick={onDismiss} className="px-2 py-1 rounded text-xs border border-border text-muted-foreground hover:bg-muted">Bezar</button>}
          </div>
        </div>

        {/* Main progress bar */}
        <Progress value={progress} className="h-1.5" />

        {/* Per-document step grid */}
        {items.length > 0 && items.length <= 30 && (
          <div className="flex flex-wrap gap-1 pt-1">
            {items.map((item) => (
              <DocMiniCard key={item.file} item={item} />
            ))}
          </div>
        )}

        {/* Compact summary for large batches */}
        {items.length > 30 && (
          <div className="flex gap-3 text-[10px] text-muted-foreground pt-1">
            <span className="text-green-600">{items.filter((i) => i.status === "completed").length} kesz</span>
            <span className="text-blue-600">{items.filter((i) => i.status === "processing").length} folyamatban</span>
            <span className="text-red-600">{items.filter((i) => i.status === "failed").length} hiba</span>
            <span>{items.filter((i) => i.status === "pending").length} varakozik</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/** Mini card for each document in the batch */
function DocMiniCard({ item }: { item: BatchItem }) {
  const bgColor =
    item.status === "completed" ? "bg-green-50 border-green-200" :
    item.status === "processing" ? "bg-blue-50 border-blue-200" :
    item.status === "failed" ? "bg-red-50 border-red-200" :
    "bg-gray-50 border-gray-200";

  const icon =
    item.status === "completed" ? "\u2713" :
    item.status === "processing" ? "\u25B6" :
    item.status === "failed" ? "!" :
    "\u25CB";

  const iconColor =
    item.status === "completed" ? "text-green-600" :
    item.status === "processing" ? "text-blue-600 animate-pulse" :
    item.status === "failed" ? "text-red-600" :
    "text-gray-400";

  return (
    <div className={`flex items-center gap-1 px-1.5 py-0.5 rounded border text-[9px] ${bgColor} min-w-0`}>
      <span className={`font-bold ${iconColor}`}>{icon}</span>
      <span className="truncate max-w-[80px]" title={item.file}>
        {item.displayName}
      </span>
      {item.status === "processing" && item.step && (
        <span className="text-blue-500 font-medium shrink-0">
          {STEP_LABELS[item.step] || item.step}
        </span>
      )}
      {item.status === "completed" && item.confidence !== undefined && item.confidence > 0 && (
        <span className={`font-mono shrink-0 ${item.confidence >= 0.9 ? "text-green-700" : item.confidence >= 0.7 ? "text-yellow-700" : "text-red-700"}`}>
          {Math.round(item.confidence * 100)}%
        </span>
      )}
    </div>
  );
}
