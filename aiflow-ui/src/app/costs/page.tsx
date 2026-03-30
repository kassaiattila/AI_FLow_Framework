"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Progress } from "@/components/ui/progress";
import { ExportButton } from "@/components/export-button";
import { PrintButton } from "@/components/print-button";
import { useI18n } from "@/hooks/use-i18n";
import type { WorkflowRun } from "@/lib/types";

const SKILL_LABELS: Record<string, string> = {
  invoice_processor: "Invoice Processor",
  email_intent_processor: "Email Intent",
  aszf_rag_chat: "RAG Chat",
  process_documentation: "Process Docs",
  cubix_course_capture: "Course Capture",
};

interface SkillCostRow {
  skill: string;
  runs: number;
  totalCost: number;
  avgCost: number;
  totalTokens: number;
  avgDuration: number;
}

interface StepCostRow {
  stepName: string;
  occurrences: number;
  totalCost: number;
  totalTokens: number;
}

export default function CostsPage() {
  const { t } = useI18n();
  const [runs, setRuns] = useState<WorkflowRun[]>([]);

  useEffect(() => {
    fetch("/api/runs")
      .then((r) => r.json())
      .then((data: { runs: WorkflowRun[] }) => setRuns(data.runs || []))
      .catch(() => setRuns([]));
  }, []);

  // Aggregate by skill
  const skillMap = new Map<string, SkillCostRow>();
  for (const run of runs) {
    const existing = skillMap.get(run.skill_name) || {
      skill: run.skill_name,
      runs: 0,
      totalCost: 0,
      avgCost: 0,
      totalTokens: 0,
      avgDuration: 0,
    };
    existing.runs += 1;
    existing.totalCost += run.total_cost_usd;
    existing.totalTokens += run.steps.reduce((s, st) => s + st.tokens_used, 0);
    existing.avgDuration += run.total_duration_ms;
    skillMap.set(run.skill_name, existing);
  }
  const skillRows: SkillCostRow[] = [...skillMap.values()].map((r) => ({
    ...r,
    avgCost: r.totalCost / r.runs,
    avgDuration: r.avgDuration / r.runs,
  }));
  skillRows.sort((a, b) => b.totalCost - a.totalCost);

  // Aggregate by step name
  const stepMap = new Map<string, StepCostRow>();
  for (const run of runs) {
    for (const step of run.steps) {
      if (step.cost_usd === 0) continue;
      const existing = stepMap.get(step.step_name) || {
        stepName: step.step_name,
        occurrences: 0,
        totalCost: 0,
        totalTokens: 0,
      };
      existing.occurrences += 1;
      existing.totalCost += step.cost_usd;
      existing.totalTokens += step.tokens_used;
      stepMap.set(step.step_name, existing);
    }
  }
  const stepRows = [...stepMap.values()].sort((a, b) => b.totalCost - a.totalCost);

  // Totals
  const totalCost = runs.reduce((s, r) => s + r.total_cost_usd, 0);
  const totalTokens = runs.reduce(
    (s, r) => s + r.steps.reduce((ss, st) => ss + st.tokens_used, 0),
    0
  );
  const totalRuns = runs.length;
  const avgCostPerRun = totalRuns > 0 ? totalCost / totalRuns : 0;

  // Daily aggregation (group by date)
  const dailyMap = new Map<string, { cost: number; runs: number }>();
  for (const run of runs) {
    const day = run.started_at.slice(0, 10);
    const existing = dailyMap.get(day) || { cost: 0, runs: 0 };
    existing.cost += run.total_cost_usd;
    existing.runs += 1;
    dailyMap.set(day, existing);
  }
  const dailyRows = [...dailyMap.entries()]
    .sort(([a], [b]) => b.localeCompare(a))
    .map(([date, data]) => ({ date, ...data }));

  const maxSkillCost = skillRows.length > 0 ? skillRows[0].totalCost : 1;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">{t("costs.title")}</h2>
          <p className="text-muted-foreground">{t("costs.subtitle")}</p>
        </div>
        <ExportButton
          filename={`costs_${new Date().toISOString().slice(0, 10)}.csv`}
          headers={["Skill", "Runs", "Total Cost ($)", "Avg Cost ($)"]}
          rows={skillRows.map((r) => [
            r.skill,
            String(r.runs),
            r.totalCost.toFixed(4),
            r.avgCost.toFixed(4),
          ])}
        />
        <PrintButton />
      </div>

      {/* Top-level KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KpiCard title={t("costs.totalCost")} value={`$${totalCost.toFixed(4)}`} subtitle={`${totalRuns} runs`} />
        <KpiCard title={t("costs.avgPerRun")} value={`$${avgCostPerRun.toFixed(4)}`} subtitle={t("costs.perRun")} />
        <KpiCard title={t("costs.totalTokens")} value={totalTokens.toLocaleString()} subtitle={t("costs.inputOutput")} />
        <KpiCard
          title={t("costs.today")}
          value={`$${(dailyRows.find((d) => d.date === new Date().toISOString().slice(0, 10))?.cost || 0).toFixed(4)}`}
          subtitle={`${dailyRows.find((d) => d.date === new Date().toISOString().slice(0, 10))?.runs || 0} runs`}
        />
      </div>

      {/* Per-skill breakdown */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">{t("costs.bySkill")}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {skillRows.map((row) => (
              <div key={row.skill} className="space-y-1">
                <div className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{SKILL_LABELS[row.skill] || row.skill}</span>
                    <Badge variant="outline" className="text-[10px]">
                      {row.runs} runs
                    </Badge>
                  </div>
                  <div className="flex items-center gap-4 text-xs text-muted-foreground">
                    <span>{row.totalTokens.toLocaleString()} tok</span>
                    <span className="font-mono font-medium text-foreground">
                      ${row.totalCost.toFixed(4)}
                    </span>
                  </div>
                </div>
                <Progress value={(row.totalCost / maxSkillCost) * 100} className="h-2" />
                <div className="flex justify-between text-[10px] text-muted-foreground">
                  <span>{t("costs.avgCost")}: ${row.avgCost.toFixed(4)} {t("costs.perRun")}</span>
                  <span>{t("costs.avgDuration")}: {(row.avgDuration / 1000).toFixed(1)}s</span>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Per-step breakdown */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t("costs.byStep")}</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t("table.step")}</TableHead>
                  <TableHead className="text-right">{t("table.calls")}</TableHead>
                  <TableHead className="text-right">{t("table.tokens")}</TableHead>
                  <TableHead className="text-right">{t("common.cost")}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {stepRows.map((row) => (
                  <TableRow key={row.stepName}>
                    <TableCell className="font-mono text-xs">{row.stepName}</TableCell>
                    <TableCell className="text-right text-xs">{row.occurrences}</TableCell>
                    <TableCell className="text-right text-xs">{row.totalTokens.toLocaleString()}</TableCell>
                    <TableCell className="text-right font-mono text-xs font-medium">
                      ${row.totalCost.toFixed(4)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        {/* Daily breakdown */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t("costs.daily")}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {dailyRows.map((day) => (
                <div key={day.date} className="flex items-center justify-between">
                  <div>
                    <span className="text-sm font-medium">{day.date}</span>
                    <span className="text-xs text-muted-foreground ml-2">{day.runs} runs</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="w-32">
                      <Progress
                        value={(day.cost / (dailyRows[0]?.cost || 1)) * 100}
                        className="h-2"
                      />
                    </div>
                    <span className="font-mono text-sm font-medium w-16 text-right">
                      ${day.cost.toFixed(4)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function KpiCard({ title, value, subtitle }: { title: string; value: string; subtitle: string }) {
  return (
    <Card>
      <CardContent className="pt-6">
        <p className="text-sm text-muted-foreground">{title}</p>
        <p className="text-3xl font-bold mt-1">{value}</p>
        <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>
      </CardContent>
    </Card>
  );
}
