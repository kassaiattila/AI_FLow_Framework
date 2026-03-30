"use client";

import { useI18n } from "@/hooks/use-i18n";
import { SidebarUser } from "@/components/sidebar-user";
import { BackendDot } from "@/components/connection-status";
import { SKILLS, type SkillStatus } from "@/lib/types";

const STATUS_DOT: Record<SkillStatus, string> = {
  production:       "bg-green-500",
  "in-development": "bg-blue-500",
  "results-viewer": "bg-gray-400",
  stub:             "bg-gray-300",
};

const SKILL_ICONS: Record<string, string> = {
  invoice_processor: "\uD83D\uDCC4",
  email_intent_processor: "\uD83D\uDCE7",
  aszf_rag_chat: "\uD83D\uDCAC",
  process_documentation: "\uD83D\uDCCA",
  cubix_course_capture: "\uD83C\uDF93",
  qbpp_test_automation: "\uD83E\uDDEA",
};

const SKILL_TKEY: Record<string, string> = {
  invoice_processor: "skill.invoice",
  email_intent_processor: "skill.email",
  aszf_rag_chat: "skill.rag",
  process_documentation: "skill.diagram",
  cubix_course_capture: "skill.cubix",
  qbpp_test_automation: "skill.qbpp",
};

export function Sidebar() {
  const { t } = useI18n();

  return (
    <aside className="w-56 border-r bg-background flex flex-col h-screen sticky top-0">
      <div className="p-4 border-b">
        <div className="flex items-center justify-between">
          <h1 className="text-lg font-bold">AIFlow</h1>
          <BackendDot />
        </div>
        <p className="text-xs text-muted-foreground">Workflow Dashboard</p>
      </div>
      <nav className="flex-1 p-2 space-y-1">
        <a href="/" className="flex items-center gap-2 px-3 py-2 rounded-md hover:bg-muted text-sm font-medium">
          {t("sidebar.dashboard")}
        </a>
        <div className="pt-3 pb-1 px-3 text-xs font-semibold text-muted-foreground uppercase">
          {t("sidebar.skills")}
        </div>
        {SKILLS.filter((s) => s.status !== "stub").map((skill) => (
          <a key={skill.name} href={`/skills/${skill.name}`} className="flex items-center gap-2 px-3 py-2 rounded-md hover:bg-muted text-sm">
            <span>{SKILL_ICONS[skill.name] || "\u2699"}</span>
            <span className="flex-1">{t(SKILL_TKEY[skill.name] || skill.name)}</span>
            <span className={`w-2 h-2 rounded-full ${STATUS_DOT[skill.status]}`} title={t(`common.${skill.status === "in-development" ? "inDevelopment" : skill.status === "results-viewer" ? "resultsViewer" : skill.status}`)} />
          </a>
        ))}
        <div className="pt-3 pb-1 px-3 text-xs font-semibold text-muted-foreground uppercase">
          {t("sidebar.monitoring")}
        </div>
        <a href="/costs" className="flex items-center gap-2 px-3 py-2 rounded-md hover:bg-muted text-sm">
          {t("sidebar.costs")}
        </a>
        <a href="/runs" className="flex items-center gap-2 px-3 py-2 rounded-md hover:bg-muted text-sm">
          {t("sidebar.runs")}
        </a>
      </nav>
      <SidebarUser />
    </aside>
  );
}
