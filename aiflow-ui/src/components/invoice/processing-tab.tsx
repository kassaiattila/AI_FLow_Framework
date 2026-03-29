"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { WorkflowTimeline } from "@/components/workflow/workflow-timeline";
import { StepDetailPanel } from "@/components/workflow/step-detail-panel";
import { CostBreakdown } from "@/components/workflow/cost-breakdown";
import { useWorkflowSimulation } from "@/hooks/use-workflow-simulation";
import { RunStatusBadge, SimStatusBadge } from "./shared";
import type { ProcessedInvoice, WorkflowRun } from "@/lib/types";

interface ProcessingTabProps {
  invoice: ProcessedInvoice;
  runs: WorkflowRun[];
}

export function ProcessingTab({ invoice, runs }: ProcessingTabProps) {
  const sim = useWorkflowSimulation(invoice.source_file);
  const [simSelectedStep, setSimSelectedStep] = useState<string | null>(null);
  const [selectedRun, setSelectedRun] = useState<WorkflowRun | null>(null);
  const [runSelectedStep, setRunSelectedStep] = useState<string | null>(null);

  // Auto-select running step in simulation
  useEffect(() => {
    if (sim.simStatus === "running") {
      const running = sim.steps.find((s) => s.status === "running");
      if (running) setSimSelectedStep(running.step_name);
    }
  }, [sim.steps, sim.simStatus]);

  // Reset sim when document changes
  useEffect(() => {
    sim.reset();
    setSelectedRun(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [invoice.source_file]);

  const simActiveStep = sim.steps.find((s) => s.step_name === simSelectedStep);
  const runActiveStep = selectedRun?.steps.find((s) => s.step_name === runSelectedStep);

  return (
    <div className="space-y-4">
      {/* Live simulation */}
      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm">Elo feldolgozas</CardTitle>
            <div className="flex items-center gap-2">
              {sim.simStatus !== "idle" && (
                <span className="text-xs font-mono text-muted-foreground">{(sim.elapsedMs / 1000).toFixed(1)}s</span>
              )}
              {sim.simStatus !== "idle" && <SimStatusBadge status={sim.simStatus} />}
              {sim.simStatus === "idle" || sim.simStatus === "completed" ? (
                <button onClick={sim.start} className="px-3 py-1 rounded-md bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90">
                  {sim.simStatus === "completed" ? "Ujra" : `Feldolgozas: ${invoice.vendor.name.slice(0, 20)}`}
                </button>
              ) : (
                <button onClick={sim.reset} className="px-3 py-1 rounded-md bg-muted text-muted-foreground text-xs hover:bg-muted/80">
                  Leallitas
                </button>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {sim.steps.length === 0 ? (
            <p className="py-6 text-center text-xs text-muted-foreground">
              Kattints a &quot;Feldolgozas&quot; gombra a szimulaciohoz
            </p>
          ) : (
            <div className="grid lg:grid-cols-2 gap-4">
              <WorkflowTimeline steps={sim.steps} selectedStep={simSelectedStep || undefined} onStepClick={setSimSelectedStep} />
              <div className="space-y-3">
                {simActiveStep ? <StepDetailPanel step={simActiveStep} /> : <p className="text-xs text-muted-foreground">Kattints egy step-re</p>}
                {sim.simStatus === "completed" && <CostBreakdown steps={sim.steps} totalCost={sim.steps.reduce((s, st) => s + st.cost_usd, 0)} />}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Past runs */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Korabbi futasok ({runs.length})</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-40">Run ID</TableHead>
                <TableHead className="w-24">Status</TableHead>
                <TableHead className="min-w-[150px]">Input</TableHead>
                <TableHead className="w-16 text-right">Ido</TableHead>
                <TableHead className="w-20 text-right">Koltseg</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {runs.map((run) => (
                <TableRow
                  key={run.run_id}
                  className={`cursor-pointer hover:bg-muted/50 ${selectedRun?.run_id === run.run_id ? "bg-primary/5" : ""}`}
                  onClick={() => {
                    setSelectedRun(run);
                    const failed = run.steps.find((s) => s.status === "failed");
                    const first = run.steps.find((s) => s.status !== "pending");
                    setRunSelectedStep((failed || first)?.step_name || null);
                  }}
                >
                  <TableCell className="font-mono text-xs">{run.run_id}</TableCell>
                  <TableCell><RunStatusBadge status={run.status} /></TableCell>
                  <TableCell className="text-xs text-muted-foreground truncate max-w-[200px]">{run.input_summary}</TableCell>
                  <TableCell className="text-right font-mono text-xs">{(run.total_duration_ms / 1000).toFixed(1)}s</TableCell>
                  <TableCell className="text-right font-mono text-xs">${run.total_cost_usd.toFixed(4)}</TableCell>
                </TableRow>
              ))}
              {runs.length === 0 && (
                <TableRow>
                  <TableCell colSpan={5} className="text-center py-4 text-xs text-muted-foreground">Nincs korabbi futas</TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Selected run detail */}
      {selectedRun && (
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-mono">{selectedRun.run_id}</CardTitle>
              <RunStatusBadge status={selectedRun.status} />
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <CostBreakdown steps={selectedRun.steps} totalCost={selectedRun.total_cost_usd} />
            <div className="grid lg:grid-cols-2 gap-4 pt-2">
              <WorkflowTimeline steps={selectedRun.steps} selectedStep={runSelectedStep || undefined} onStepClick={setRunSelectedStep} />
              <div>{runActiveStep ? <StepDetailPanel step={runActiveStep} /> : <p className="text-xs text-muted-foreground">Kattints egy step-re</p>}</div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
