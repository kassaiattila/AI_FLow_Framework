"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useI18n } from "@/hooks/use-i18n";
import { KpiCard } from "@/components/skill-viewer";
import { SKILLS, type SkillStatus, type WorkflowRun } from "@/lib/types";

const STATUS_STYLES: Record<SkillStatus, { bg: string; key: string }> = {
  production:       { bg: "bg-green-100 text-green-800",  key: "common.production" },
  "in-development": { bg: "bg-blue-100 text-blue-800",   key: "common.inDevelopment" },
  "results-viewer": { bg: "bg-gray-100 text-gray-600",   key: "common.resultsViewer" },
  stub:             { bg: "bg-gray-100 text-gray-400",    key: "common.stub" },
};

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
  const productionSkills = SKILLS.filter((s) => s.status === "production").length;

  return (
    <div className="p-6 space-y-6">
      <div>
        <h2 className="text-2xl font-bold">{t("dashboard.title")}</h2>
        <p className="text-muted-foreground">{t("dashboard.subtitle")}</p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <KpiCard title="Skills" value={String(SKILLS.length)} sub={`${productionSkills} production`} />
        <KpiCard title={t("dashboard.allRuns")} value={String(runs.length)} sub={`${runs.filter((r) => r.status === "completed").length} ${t("common.successful")}`} />
        <KpiCard title={t("dashboard.todayRuns")} value={String(todayRuns.length)} sub={today} />
        <KpiCard title={t("dashboard.todayCost")} value={`$${todayCost.toFixed(4)}`} sub={t("common.total")} />
      </div>

      {/* Skill Grid */}
      <div>
        <h3 className="text-lg font-semibold mb-3">{t("dashboard.skills")}</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {SKILLS.map((skill) => {
            const style = STATUS_STYLES[skill.status];
            return (
              <a key={skill.name} href={`/skills/${skill.name}`}>
                <Card className="hover:shadow-md transition-shadow cursor-pointer">
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-sm font-medium">{skill.display_name}</CardTitle>
                      <Badge className={`${style.bg} hover:${style.bg}`}>{t(style.key)}</Badge>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <p className="text-xs text-muted-foreground mb-2">{skill.description}</p>
                    <p className="text-xs text-muted-foreground">{skill.test_count} {t("dashboard.tests")}</p>
                  </CardContent>
                </Card>
              </a>
            );
          })}
        </div>
      </div>
    </div>
  );
}
