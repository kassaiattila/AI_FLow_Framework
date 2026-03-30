"use client";

import { useI18n } from "@/hooks/use-i18n";
import { SourceBadge } from "./source-badge";

type Source = "backend" | "subprocess" | "demo" | "filesystem" | null;
type StepStatus = "completed" | "running" | "pending" | "failed";

interface PipelineStep {
  name: string;
  status: StepStatus;
}

interface PipelineBarProps {
  steps: PipelineStep[];
  source: Source;
  isProcessing?: boolean;
}

const STATUS_ICON: Record<StepStatus, { icon: string; color: string }> = {
  completed: { icon: "\u2713", color: "text-green-600" },
  running:   { icon: "\u25B6", color: "text-blue-600 animate-pulse" },
  pending:   { icon: "\u25CB", color: "text-gray-400" },
  failed:    { icon: "\u2717", color: "text-red-600" },
};

export function PipelineBar({ steps, source, isProcessing = false }: PipelineBarProps) {
  const { t } = useI18n();

  const displaySteps = isProcessing
    ? steps.map((s, i) => ({ ...s, status: (i === 0 ? "running" : "pending") as StepStatus }))
    : steps;

  return (
    <div className="flex items-center gap-1 px-3 py-2 rounded-lg border bg-muted/30 overflow-x-auto">
      {displaySteps.map((step, i) => {
        const { icon, color } = STATUS_ICON[step.status];
        return (
          <span key={step.name} className="flex items-center gap-1 shrink-0">
            {i > 0 && <span className="text-muted-foreground/40 text-xs mx-0.5">{"\u2192"}</span>}
            <span className={`text-[10px] font-bold ${color}`}>{icon}</span>
            <span className={`text-[10px] ${step.status === "pending" ? "text-muted-foreground/50" : "text-muted-foreground"}`}>
              {step.name}
            </span>
          </span>
        );
      })}

      <span className="ml-auto shrink-0">
        <SourceBadge source={source} />
      </span>
    </div>
  );
}
