"use client";

import { useState } from "react";
import type { StepExecution } from "@/lib/types";
import { Badge } from "@/components/ui/badge";

const STATUS_STYLES: Record<string, { bg: string; ring: string; icon: string }> = {
  completed: { bg: "bg-green-500", ring: "ring-green-200", icon: "\u2713" },
  running:   { bg: "bg-blue-500 animate-pulse", ring: "ring-blue-200", icon: "\u25B6" },
  failed:    { bg: "bg-red-500", ring: "ring-red-200", icon: "\u2717" },
  pending:   { bg: "bg-gray-300", ring: "ring-gray-100", icon: "\u2022" },
};

function formatDuration(ms: number): string {
  if (ms === 0) return "\u2014";
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function formatCost(usd: number): string {
  if (usd === 0) return "\u2014";
  if (usd < 0.001) return `$${usd.toFixed(4)}`;
  return `$${usd.toFixed(4)}`;
}

interface WorkflowTimelineProps {
  steps: StepExecution[];
  selectedStep?: string;
  onStepClick?: (stepName: string) => void;
}

export function WorkflowTimeline({ steps, selectedStep, onStepClick }: WorkflowTimelineProps) {
  return (
    <div className="relative">
      {steps.map((step, i) => {
        const style = STATUS_STYLES[step.status] || STATUS_STYLES.pending;
        const isSelected = selectedStep === step.step_name;
        const isLast = i === steps.length - 1;

        return (
          <div
            key={step.step_name}
            className={`relative flex gap-4 pb-6 cursor-pointer group ${isLast ? "pb-0" : ""}`}
            onClick={() => onStepClick?.(step.step_name)}
          >
            {/* Vertical line */}
            {!isLast && (
              <div className="absolute left-[15px] top-[32px] w-0.5 h-[calc(100%-24px)] bg-border" />
            )}

            {/* Circle */}
            <div
              className={`relative z-10 flex items-center justify-center w-8 h-8 rounded-full text-white text-xs font-bold ring-4 shrink-0 ${style.bg} ${style.ring} ${
                isSelected ? "ring-primary/30 scale-110" : ""
              } transition-transform`}
            >
              {style.icon}
            </div>

            {/* Content */}
            <div
              className={`flex-1 rounded-lg border p-3 transition-colors ${
                isSelected
                  ? "border-primary bg-primary/5"
                  : "border-border hover:border-muted-foreground/30 hover:bg-muted/50"
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-sm font-semibold">{step.step_name}</span>
                  <StatusBadge status={step.status} />
                </div>
                <div className="flex items-center gap-3 text-xs text-muted-foreground">
                  <span>{formatDuration(step.duration_ms)}</span>
                  {step.tokens_used > 0 && <span>{step.tokens_used} tok</span>}
                  <span className="font-mono">{formatCost(step.cost_usd)}</span>
                </div>
              </div>

              {step.status !== "pending" && (
                <div className="text-xs text-muted-foreground mt-1">
                  {step.error ? (
                    <span className="text-red-600">{step.error}</span>
                  ) : (
                    <span className="line-clamp-1">{step.output_preview}</span>
                  )}
                </div>
              )}

              {step.confidence > 0 && step.confidence < 1 && (
                <div className="mt-2 flex items-center gap-2">
                  <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${
                        step.confidence >= 0.9
                          ? "bg-green-500"
                          : step.confidence >= 0.7
                          ? "bg-yellow-500"
                          : "bg-red-500"
                      }`}
                      style={{ width: `${step.confidence * 100}%` }}
                    />
                  </div>
                  <span className="text-xs text-muted-foreground">{(step.confidence * 100).toFixed(0)}%</span>
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const variants: Record<string, string> = {
    completed: "bg-green-100 text-green-700",
    running: "bg-blue-100 text-blue-700",
    failed: "bg-red-100 text-red-700",
    pending: "bg-gray-100 text-gray-500",
  };
  return (
    <Badge className={`text-[10px] px-1.5 py-0 ${variants[status] || variants.pending}`}>
      {status}
    </Badge>
  );
}
