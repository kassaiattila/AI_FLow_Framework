"use client";

import type { StepExecution } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface StepDetailPanelProps {
  step: StepExecution;
}

function formatDuration(ms: number): string {
  if (ms === 0) return "\u2014";
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export function StepDetailPanel({ step }: StepDetailPanelProps) {
  const statusColor: Record<string, string> = {
    completed: "bg-green-100 text-green-700",
    running: "bg-blue-100 text-blue-700",
    failed: "bg-red-100 text-red-700",
    pending: "bg-gray-100 text-gray-500",
  };

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base font-mono">{step.step_name}</CardTitle>
          <Badge className={statusColor[step.status] || statusColor.pending}>{step.status}</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Metrics row */}
        <div className="grid grid-cols-4 gap-3">
          <MetricBox label="Duration" value={formatDuration(step.duration_ms)} />
          <MetricBox label="Cost" value={step.cost_usd > 0 ? `$${step.cost_usd.toFixed(4)}` : "\u2014"} />
          <MetricBox label="Tokens" value={step.tokens_used > 0 ? step.tokens_used.toLocaleString() : "\u2014"} />
          <MetricBox
            label="Confidence"
            value={step.confidence > 0 ? `${(step.confidence * 100).toFixed(0)}%` : "\u2014"}
          />
        </div>

        {/* Input */}
        {step.input_preview && (
          <div>
            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Input</label>
            <div className="mt-1 rounded-md bg-muted p-3 font-mono text-xs leading-relaxed whitespace-pre-wrap break-all">
              {step.input_preview}
            </div>
          </div>
        )}

        {/* Output */}
        {step.output_preview && (
          <div>
            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Output</label>
            <div className="mt-1 rounded-md bg-muted p-3 font-mono text-xs leading-relaxed whitespace-pre-wrap break-all">
              {step.output_preview}
            </div>
          </div>
        )}

        {/* Error */}
        {step.error && (
          <div>
            <label className="text-xs font-semibold text-red-600 uppercase tracking-wide">Error</label>
            <div className="mt-1 rounded-md bg-red-50 border border-red-200 p-3 font-mono text-xs text-red-700 leading-relaxed whitespace-pre-wrap">
              {step.error}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function MetricBox({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border p-2 text-center">
      <p className="text-[10px] text-muted-foreground uppercase">{label}</p>
      <p className="text-sm font-semibold mt-0.5">{value}</p>
    </div>
  );
}
