"use client";

import { useAuth } from "@/hooks/use-auth";
import { useI18n } from "@/hooks/use-i18n";
import { Badge } from "@/components/ui/badge";
import { ThemeToggle } from "@/components/theme-toggle";

const ROLE_COLORS: Record<string, string> = {
  admin: "bg-red-100 text-red-800",
  operator: "bg-blue-100 text-blue-800",
  viewer: "bg-gray-100 text-gray-700",
};

export function SidebarUser() {
  const { user } = useAuth();
  const { locale, switchLocale, t } = useI18n();

  return (
    <div className="p-3 border-t space-y-2">
      {user && (
        <div className="flex items-center justify-between px-3">
          <span className="text-xs font-medium">{user.user_id}</span>
          <Badge className={`${ROLE_COLORS[user.role] || ROLE_COLORS.viewer} text-[9px]`}>
            {user.role}
          </Badge>
        </div>
      )}
      <div className="flex items-center gap-1 px-3">
        <ThemeToggle />
        <button
          onClick={() => {
            const next = locale === "hu" ? "en" : "hu";
            switchLocale(next);
            window.location.reload();
          }}
          className="px-2 py-1.5 rounded-md hover:bg-muted text-xs font-medium"
          title={locale === "hu" ? "Switch to English" : "Valtson magyarra"}
        >
          {locale === "hu" ? "EN" : "HU"}
        </button>
      </div>
      <a href="/api/auth/logout" className="flex items-center gap-2 px-3 py-1.5 rounded-md hover:bg-muted text-xs">
        {t("sidebar.logout")}
      </a>
      <p className="text-xs text-muted-foreground px-3">v0.1.0 &middot; BestIx Kft.</p>
    </div>
  );
}
