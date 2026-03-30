"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useI18n } from "@/hooks/use-i18n";
import { SKILLS, type WorkflowRun } from "@/lib/types";

export default function DashboardPage() {
  const { t } = useI18n();
  const [runs, setRuns] = useState<WorkflowRun[]>([]);

  useEffect(() => {
    fetch("/api/runs")
      .then((r) => r.json())
      .then((data: { runs: WorkflowRun[] }) => setRuns(data.runs || []))
      .catch(() => {});
  }, []);

  const today = new Date().toISOString().slice(0, 10);
  const todayRuns = runs.filter((r) => r.started_at?.startsWith(today));
  const todayCost = todayRuns.reduce((s, r) => s + r.total_cost_usd, 0);
  const activeSkills = SKILLS.filter((s) => s.status !== "stub").length;

  return (
    <div className="p-6 space-y-6">
      <div>
        <h2 className="text-2xl font-bold">{t("dashboard.title")}</h2>
        <p className="text-muted-foreground">{t("dashboard.subtitle")}</p>
      </div>

      {/* KPI Cards — real data */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <KpiCard title="Skills" value={String(SKILLS.length)} subtitle={`${activeSkills} ${t("common.active")}, ${SKILLS.length - activeSkills} ${t("common.stub")}`} />
        <KpiCard title={t("dashboard.allRuns")} value={String(runs.length)} subtitle={`${runs.filter((r) => r.status === "completed").length} ${t("common.successful")}`} />
        <KpiCard title={t("dashboard.todayRuns")} value={String(todayRuns.length)} subtitle={today} />
        <KpiCard title={t("dashboard.todayCost")} value={`$${todayCost.toFixed(4)}`} subtitle={t("common.total")} />
      </div>

      {/* Skill Grid */}
      <div>
        <h3 className="text-lg font-semibold mb-3">{t("dashboard.skills")}</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {SKILLS.map((skill) => (
            <a key={skill.name} href={`/skills/${skill.name}`}>
              <Card className="hover:shadow-md transition-shadow cursor-pointer">
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-sm font-medium">{skill.display_name}</CardTitle>
                    <StatusBadge status={skill.status} />
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-xs text-muted-foreground mb-2">{skill.description}</p>
                  <p className="text-xs text-muted-foreground">{skill.test_count} {t("dashboard.tests")}</p>
                </CardContent>
              </Card>
            </a>
          ))}
        </div>
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

function StatusBadge({ status }: { status: string }) {
  if (status === "production") return <Badge className="bg-green-100 text-green-800 hover:bg-green-100">Production</Badge>;
  if (status === "stub") return <Badge variant="outline" className="text-gray-500">Stub</Badge>;
  return <Badge className="bg-blue-100 text-blue-800 hover:bg-blue-100">{status}</Badge>;
}
