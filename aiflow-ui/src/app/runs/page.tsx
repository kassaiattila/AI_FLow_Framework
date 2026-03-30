"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ExportButton } from "@/components/export-button";
import { PrintButton } from "@/components/print-button";
import { useI18n } from "@/hooks/use-i18n";
import type { WorkflowRun } from "@/lib/types";

const STATUS_BADGE: Record<string, string> = {
  completed: "bg-green-100 text-green-700 hover:bg-green-100",
  running: "bg-blue-100 text-blue-700 hover:bg-blue-100",
  failed: "bg-red-100 text-red-700 hover:bg-red-100",
  pending: "bg-gray-100 text-gray-500 hover:bg-gray-100",
};

const SKILL_LABELS: Record<string, string> = {
  invoice_processor: "Invoice Processor",
  email_intent_processor: "Email Intent",
  aszf_rag_chat: "RAG Chat",
  process_documentation: "Process Docs",
  cubix_course_capture: "Course Capture",
};

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString("hu-HU", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
}

export default function RunsPage() {
  const { t } = useI18n();
  const [runs, setRuns] = useState<WorkflowRun[]>([]);
  const [filter, setFilter] = useState<string>("all");
  const [live, setLive] = useState(false);
  const eventSourceRef = useRef<AbortController | null>(null);

  const loadRuns = useCallback(() => {
    fetch("/api/runs")
      .then((r) => r.json())
      .then((data: { runs: WorkflowRun[] }) => setRuns(data.runs))
      .catch(() => {});
  }, []);

  useEffect(() => {
    loadRuns();
  }, [loadRuns]);

  // SSE live updates when toggled on
  useEffect(() => {
    if (!live) return;
    const ctrl = new AbortController();
    eventSourceRef.current = ctrl;

    (async () => {
      try {
        const res = await fetch("/api/runs/stream", { signal: ctrl.signal });
        if (!res.body) return;
        const reader = res.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value, { stream: true });
          for (const line of chunk.split("\n")) {
            if (!line.startsWith("data: ") || line.includes("[DONE]")) continue;
            try {
              const data = JSON.parse(line.slice(6));
              if (data.runs) setRuns(data.runs);
            } catch { /* skip */ }
          }
        }
      } catch { /* aborted or error */ }
      setLive(false);
    })();

    return () => ctrl.abort();
  }, [live]);

  const skills = ["all", ...new Set(runs.map((r) => r.skill_name))];
  const filtered = filter === "all" ? runs : runs.filter((r) => r.skill_name === filter);

  const stats = {
    total: runs.length,
    completed: runs.filter((r) => r.status === "completed").length,
    failed: runs.filter((r) => r.status === "failed").length,
    running: runs.filter((r) => r.status === "running").length,
    totalCost: runs.reduce((sum, r) => sum + r.total_cost_usd, 0),
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">{t("runs.title")}</h2>
          <p className="text-muted-foreground">{t("runs.subtitle")}</p>
        </div>
        <ExportButton
          filename={`runs_${new Date().toISOString().slice(0, 10)}.csv`}
          headers={["Run ID", "Skill", "Status", "Duration (ms)", "Cost ($)", "Started"]}
          rows={filtered.map((r) => [
            r.run_id,
            r.skill_name,
            r.status,
            String(r.total_duration_ms),
            String(r.total_cost_usd),
            r.started_at,
          ])}
        />
        <PrintButton />
        <button
          onClick={() => setLive(!live)}
          className={`px-3 py-1.5 rounded-md text-xs font-medium border transition-colors ${
            live ? "bg-green-600 text-white border-green-600" : "border-border text-muted-foreground hover:bg-muted"
          }`}
        >
          {live ? t("runs.liveOn") : t("runs.liveOff")}
        </button>
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <MiniKpi label={t("common.total")} value={stats.total} />
        <MiniKpi label={t("common.completed")} value={stats.completed} color="text-green-600" />
        <MiniKpi label={t("common.failed")} value={stats.failed} color="text-red-600" />
        <MiniKpi label={t("common.running")} value={stats.running} color="text-blue-600" />
        <MiniKpi label={t("runs.totalCost")} value={`$${stats.totalCost.toFixed(4)}`} />
      </div>

      {/* Skill filter */}
      <div className="flex gap-2 flex-wrap">
        {skills.map((s) => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
              filter === s
                ? "bg-primary text-primary-foreground"
                : "bg-muted text-muted-foreground hover:bg-muted/80"
            }`}
          >
            {s === "all" ? t("runs.allSkills") : SKILL_LABELS[s] || s}
          </button>
        ))}
      </div>

      {/* Runs Table */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[160px]">{t("table.runId")}</TableHead>
                <TableHead>{t("table.skill")}</TableHead>
                <TableHead>{t("common.status")}</TableHead>
                <TableHead>Input</TableHead>
                <TableHead className="text-right">{t("table.duration")}</TableHead>
                <TableHead className="text-right">{t("common.cost")}</TableHead>
                <TableHead className="text-right">{t("table.started")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((run) => (
                <TableRow key={run.run_id} className="cursor-pointer hover:bg-muted/50">
                  <TableCell>
                    <a href={`/runs/${run.run_id}`} className="font-mono text-xs text-primary hover:underline">
                      {run.run_id}
                    </a>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" className="text-xs">
                      {SKILL_LABELS[run.skill_name] || run.skill_name}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge className={`text-xs ${STATUS_BADGE[run.status]}`}>{run.status}</Badge>
                  </TableCell>
                  <TableCell className="max-w-[250px] truncate text-xs text-muted-foreground">
                    {run.input_summary}
                  </TableCell>
                  <TableCell className="text-right font-mono text-xs">
                    {formatDuration(run.total_duration_ms)}
                  </TableCell>
                  <TableCell className="text-right font-mono text-xs">${run.total_cost_usd.toFixed(4)}</TableCell>
                  <TableCell className="text-right text-xs text-muted-foreground">
                    {formatTime(run.started_at)}
                  </TableCell>
                </TableRow>
              ))}
              {filtered.length === 0 && (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                    {t("runs.noRuns")}
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}

function MiniKpi({ label, value, color }: { label: string; value: string | number; color?: string }) {
  return (
    <Card>
      <CardContent className="pt-4 pb-3 px-4">
        <p className="text-[11px] text-muted-foreground uppercase">{label}</p>
        <p className={`text-xl font-bold ${color || ""}`}>{value}</p>
      </CardContent>
    </Card>
  );
}
