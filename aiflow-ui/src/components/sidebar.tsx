"use client";

import { useI18n } from "@/hooks/use-i18n";
import { SidebarUser } from "@/components/sidebar-user";

export function Sidebar() {
  const { t } = useI18n();

  const skills = [
    { name: "invoice_processor", icon: "\uD83D\uDCC4", tKey: "skill.invoice" },
    { name: "email_intent_processor", icon: "\uD83D\uDCE7", tKey: "skill.email" },
    { name: "aszf_rag_chat", icon: "\uD83D\uDCAC", tKey: "skill.rag" },
    { name: "process_documentation", icon: "\uD83D\uDCCA", tKey: "skill.diagram" },
    { name: "cubix_course_capture", icon: "\uD83C\uDF93", tKey: "skill.cubix" },
  ];

  return (
    <aside className="w-56 border-r bg-background flex flex-col h-screen sticky top-0">
      <div className="p-4 border-b">
        <h1 className="text-lg font-bold">AIFlow</h1>
        <p className="text-xs text-muted-foreground">Workflow Dashboard</p>
      </div>
      <nav className="flex-1 p-2 space-y-1">
        <a href="/" className="flex items-center gap-2 px-3 py-2 rounded-md hover:bg-muted text-sm font-medium">
          {t("sidebar.dashboard")}
        </a>
        <div className="pt-3 pb-1 px-3 text-xs font-semibold text-muted-foreground uppercase">
          {t("sidebar.skills")}
        </div>
        {skills.map((s) => (
          <a key={s.name} href={`/skills/${s.name}`} className="flex items-center gap-2 px-3 py-2 rounded-md hover:bg-muted text-sm">
            {s.icon} {t(s.tKey)}
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
