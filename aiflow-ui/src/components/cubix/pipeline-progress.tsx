"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import type { FileProcessingState, StageStatus } from "@/lib/types";

const STAGES = ["probe", "extract", "chunk", "transcribe", "merge", "structure"] as const;

const STAGE_LABELS: Record<string, string> = {
  probe: "Probe",
  extract: "Audio",
  chunk: "Chunk",
  transcribe: "STT",
  merge: "Merge",
  structure: "Struktura",
};

const STATUS_COLORS: Record<StageStatus, string> = {
  completed: "bg-green-500",
  in_progress: "bg-blue-500 animate-pulse",
  failed: "bg-red-500",
  pending: "bg-gray-300",
  skipped: "bg-gray-400",
};

interface PipelineProgressProps {
  files: Record<string, FileProcessingState>;
  selectedSlug: string | null;
  onSelect: (slug: string) => void;
}

export function PipelineProgress({ files, selectedSlug, onSelect }: PipelineProgressProps) {
  const fileList = Object.values(files).sort((a, b) => a.global_index - b.global_index);

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm">Pipeline allapot ({fileList.length} fajl)</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {fileList.map((file) => {
          const completedStages = STAGES.filter((s) => file[s] === "completed").length;
          const pct = Math.round((completedStages / STAGES.length) * 100);
          const hasError = file.last_error !== "";

          return (
            <div
              key={file.slug}
              className={`p-2 rounded border cursor-pointer transition-colors text-sm ${
                selectedSlug === file.slug ? "border-primary bg-muted" : "hover:bg-muted/50"
              }`}
              onClick={() => onSelect(file.slug)}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="font-medium truncate max-w-[200px]">{file.title}</span>
                <div className="flex items-center gap-1">
                  {hasError && <Badge className="bg-red-100 text-red-800 text-[9px]">Hiba</Badge>}
                  <span className="text-xs text-muted-foreground">{pct}%</span>
                </div>
              </div>
              <div className="flex gap-0.5">
                {STAGES.map((stage) => (
                  <div
                    key={stage}
                    className={`h-1.5 flex-1 rounded-full ${STATUS_COLORS[file[stage]]}`}
                    title={`${STAGE_LABELS[stage]}: ${file[stage]}`}
                  />
                ))}
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}

export function FileDetail({ file }: { file: FileProcessingState }) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm">{file.title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid grid-cols-3 gap-2 text-xs">
          <div className="p-2 bg-muted/50 rounded text-center">
            <p className="text-muted-foreground">Idotartam</p>
            <p className="font-bold">{Math.round(file.duration_seconds / 60)} perc</p>
          </div>
          <div className="p-2 bg-muted/50 rounded text-center">
            <p className="text-muted-foreground">Chunk-ok</p>
            <p className="font-bold">{file.chunk_count}</p>
          </div>
          <div className="p-2 bg-muted/50 rounded text-center">
            <p className="text-muted-foreground">Koltseg</p>
            <p className="font-bold">${file.total_cost.toFixed(4)}</p>
          </div>
        </div>

        <div className="space-y-1">
          {STAGES.map((stage) => {
            const status = file[stage];
            const color =
              status === "completed" ? "text-green-600" :
              status === "failed" ? "text-red-600" :
              status === "in_progress" ? "text-blue-600" :
              "text-gray-400";
            const icon =
              status === "completed" ? "\u2713" :
              status === "failed" ? "\u2717" :
              status === "in_progress" ? "\u25B6" : "\u2022";

            return (
              <div key={stage} className="flex items-center justify-between text-xs">
                <span className={color}>{icon} {STAGE_LABELS[stage]}</span>
                <span className="text-muted-foreground">{status}</span>
              </div>
            );
          })}
        </div>

        {file.last_error && (
          <div className="border-t pt-2">
            <p className="text-xs text-red-600">{file.last_error}</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
