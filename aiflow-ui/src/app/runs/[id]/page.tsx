"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { WorkflowTimeline } from "@/components/workflow/workflow-timeline";
import { StepDetailPanel } from "@/components/workflow/step-detail-panel";
import { CostBreakdown } from "@/components/workflow/cost-breakdown";
import { useI18n } from "@/hooks/use-i18n";
import type { WorkflowRun } from "@/lib/types";

const STATUS_BADGE: Record<string, string> = {
  completed: "bg-green-100 text-green-700",
  running: "bg-blue-100 text-blue-700",
  failed: "bg-red-100 text-red-700",
  pending: "bg-gray-100 text-gray-500",
};

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString("hu-HU");
}

export default function RunDetailPage() {
  const { t } = useI18n();
  const params = useParams<{ id: string }>();
  const [run, setRun] = useState<WorkflowRun | null>(null);
  const [selectedStep, setSelectedStep] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/runs")
      .then((r) => r.json())
      .then((data: { runs: WorkflowRun[] }) => {
        const found = (data.runs || []).find((r: WorkflowRun) => r.run_id === params.id);
        if (found) {
          setRun(found);
          const failedStep = found.steps.find((s) => s.status === "failed");
          const firstActive = found.steps.find((s) => s.status !== "pending");
          setSelectedStep((failedStep || firstActive)?.step_name || null);
        }
      })
      .catch(() => {});
  }, [params.id]);

  if (!run) {
    return (
      <div className="p-6">
        <p className="text-muted-foreground">{t("common.loading")}</p>
      </div>
    );
  }

  const activeStep = run.steps.find((s) => s.step_name === selectedStep);

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-2xl font-bold font-mono">{run.run_id}</h2>
            <Badge className={STATUS_BADGE[run.status]}>{run.status}</Badge>
          </div>
          <p className="text-muted-foreground mt-1">{run.skill_name}</p>
        </div>
        <a href="/runs" className="text-sm text-muted-foreground hover:text-foreground">
          &larr; {t("runs.allSkills")}
        </a>
      </div>

      {/* Run summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <SummaryCard label="Started" value={formatTime(run.started_at)} />
        <SummaryCard label="Duration" value={formatDuration(run.total_duration_ms)} />
        <SummaryCard label="Steps" value={`${run.steps.length}`} />
        <SummaryCard label="Total Cost" value={`$${run.total_cost_usd.toFixed(4)}`} />
        <SummaryCard label="Tokens" value={run.steps.reduce((s, st) => s + st.tokens_used, 0).toLocaleString()} />
      </div>

      {/* I/O summary */}
      <div className="grid md:grid-cols-2 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Input</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">{run.input_summary}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Output</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">{run.output_summary}</p>
          </CardContent>
        </Card>
      </div>

      {/* Cost breakdown */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Cost Breakdown</CardTitle>
        </CardHeader>
        <CardContent>
          <CostBreakdown steps={run.steps} totalCost={run.total_cost_usd} />
        </CardContent>
      </Card>

      {/* Timeline + Detail */}
      <div className="grid lg:grid-cols-2 gap-6">
        <div>
          <h3 className="text-sm font-semibold mb-3">Step Timeline</h3>
          <WorkflowTimeline
            steps={run.steps}
            selectedStep={selectedStep || undefined}
            onStepClick={setSelectedStep}
          />
        </div>
        <div>
          <h3 className="text-sm font-semibold mb-3">Step Detail</h3>
          {activeStep ? (
            <StepDetailPanel step={activeStep} />
          ) : (
            <p className="text-sm text-muted-foreground">Click a step to see details</p>
          )}
        </div>
      </div>
    </div>
  );
}

function SummaryCard({ label, value }: { label: string; value: string }) {
  return (
    <Card>
      <CardContent className="pt-4 pb-3 px-4">
        <p className="text-[10px] text-muted-foreground uppercase tracking-wide">{label}</p>
        <p className="text-sm font-semibold mt-0.5">{value}</p>
      </CardContent>
    </Card>
  );
}
