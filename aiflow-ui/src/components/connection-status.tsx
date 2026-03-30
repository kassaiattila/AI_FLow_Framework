"use client";

import { useBackendStatus } from "@/hooks/use-backend-status";
import { useI18n } from "@/hooks/use-i18n";

/** Small dot indicator for the sidebar header */
export function BackendDot() {
  const { status } = useBackendStatus();
  const { t } = useI18n();

  const color =
    status === "connected" ? "bg-green-500" :
    status === "checking" ? "bg-yellow-500 animate-pulse" :
    "bg-red-400";

  const label =
    status === "connected" ? t("backend.live") :
    status === "checking" ? "..." :
    t("backend.demo");

  return (
    <span
      className="inline-flex items-center gap-1 text-[10px] text-muted-foreground"
      title={status === "connected" ? t("backend.connected") : t("backend.offline")}
    >
      <span className={`w-2 h-2 rounded-full ${color}`} />
      {label}
    </span>
  );
}

/** Banner shown at the top of content area when backend is offline */
export function DemoBanner() {
  const { isDemo, status } = useBackendStatus();
  const { t } = useI18n();

  if (status === "checking" || !isDemo) return null;

  return (
    <div className="bg-amber-50 dark:bg-amber-950/30 border-b border-amber-200 dark:border-amber-800 px-4 py-2 text-center">
      <span className="text-xs text-amber-800 dark:text-amber-300">
        {t("backend.offline")}
      </span>
    </div>
  );
}
