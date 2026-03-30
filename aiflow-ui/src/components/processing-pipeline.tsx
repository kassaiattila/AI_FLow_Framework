"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { WorkflowTimeline } from "@/components/workflow/workflow-timeline";
import { useI18n } from "@/hooks/use-i18n";
import type { StepExecution } from "@/lib/types";

type Source = "backend" | "subprocess" | "demo" | "filesystem" | null;

interface ProcessingPipelineProps {
  /** Step definitions for this skill */
  steps: StepExecution[];
  /** Data source: backend, subprocess, demo, or unknown (null) */
  source: Source;
  /** True while the skill is actively processing */
  isProcessing?: boolean;
  /** Optional title override (defaults to "Pipeline") */
  title?: string;
}

const SOURCE_STYLES: Record<string, { bg: string; label: string }> = {
  backend:    { bg: "bg-green-100 text-green-800", label: "backend.live" },
  subprocess: { bg: "bg-blue-100 text-blue-800",  label: "backend.subprocess" },
  filesystem: { bg: "bg-green-100 text-green-800", label: "backend.live" },
  demo:       { bg: "bg-yellow-100 text-yellow-800", label: "backend.demo" },
};

/**
 * Unified processing pipeline viewer.
 *
 * Shows skill execution steps with honest status:
 * - During processing: first incomplete step is "running", rest "pending"
 * - After processing: real statuses from skill output
 * - Source badge always visible so user knows if data is real or demo
 */
export function ProcessingPipeline({
  steps,
  source,
  isProcessing = false,
  title,
}: ProcessingPipelineProps) {
  const { t } = useI18n();

  // During processing: override statuses to show honest "running" state
  const displaySteps: StepExecution[] = isProcessing
    ? steps.map((s, i) => ({
        ...s,
        status: i === 0 ? "running" as const : "pending" as const,
        output_preview: i === 0 ? t("pipeline.running") : "",
        duration_ms: 0,
      }))
    : steps;

  const sourceStyle = source ? SOURCE_STYLES[source] : null;

  // Summary stats (only when not processing)
  const completedSteps = isProcessing ? 0 : steps.filter((s) => s.status === "completed").length;
  const totalDuration = isProcessing ? 0 : steps.reduce((sum, s) => sum + s.duration_ms, 0);
  const totalCost = isProcessing ? 0 : steps.reduce((sum, s) => sum + s.cost_usd, 0);
  const totalTokens = isProcessing ? 0 : steps.reduce((sum, s) => sum + s.tokens_used, 0);

  return (
    <Card>
      <CardContent className="pt-4 space-y-3">
        {/* Header: title + source badge + stats */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold">
              {title || t("pipeline.title")}
            </h3>
            {sourceStyle && (
              <Badge className={`text-[10px] px-1.5 py-0 ${sourceStyle.bg}`}>
                {t(sourceStyle.label)}
              </Badge>
            )}
            {isProcessing && (
              <span className="text-xs text-blue-600 animate-pulse font-medium">
                {t("pipeline.running")}
              </span>
            )}
          </div>

          {!isProcessing && completedSteps > 0 && (
            <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
              <span>{completedSteps}/{steps.length} {t("pipeline.stepsCompleted")}</span>
              {totalDuration > 0 && (
                <span>{totalDuration < 1000 ? `${totalDuration}ms` : `${(totalDuration / 1000).toFixed(1)}s`}</span>
              )}
              {totalTokens > 0 && <span>{totalTokens} tok</span>}
              {totalCost > 0 && <span>${totalCost.toFixed(4)}</span>}
            </div>
          )}
        </div>

        {/* Source explanation for demo */}
        {source === "demo" && !isProcessing && (
          <p className="text-[10px] text-muted-foreground italic">
            {t("pipeline.demoHint")}
          </p>
        )}

        {/* Timeline */}
        <WorkflowTimeline steps={displaySteps} />
      </CardContent>
    </Card>
  );
}
