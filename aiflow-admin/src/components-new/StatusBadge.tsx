/**
 * StatusBadge — Live/Demo/Healthy/Degraded badge based on source tag.
 * Shows data provenance on every page (MANDATORY per CLAUDE.md).
 */

import { useTranslate } from "../lib/i18n";

interface StatusBadgeProps {
  source: string;
  size?: "sm" | "md";
}

const BADGE_STYLES: Record<string, string> = {
  backend:
    "bg-green-50 text-green-700 ring-green-600/20 dark:bg-green-900/30 dark:text-green-400",
  live: "bg-green-50 text-green-700 ring-green-600/20 dark:bg-green-900/30 dark:text-green-400",
  demo: "bg-amber-50 text-amber-700 ring-amber-600/20 dark:bg-amber-900/30 dark:text-amber-400",
  healthy:
    "bg-green-50 text-green-700 ring-green-600/20 dark:bg-green-900/30 dark:text-green-400",
  degraded:
    "bg-amber-50 text-amber-700 ring-amber-600/20 dark:bg-amber-900/30 dark:text-amber-400",
  down: "bg-red-50 text-red-700 ring-red-600/20 dark:bg-red-900/30 dark:text-red-400",
};

export function StatusBadge({ source, size = "sm" }: StatusBadgeProps) {
  const translate = useTranslate();

  const label = translate(`aiflow.status.${source}`);
  const style = BADGE_STYLES[source] || BADGE_STYLES.demo;
  const sizeClass =
    size === "sm" ? "px-2 py-0.5 text-xs" : "px-2.5 py-1 text-sm";

  return (
    <span
      className={`inline-flex items-center rounded-full font-medium ring-1 ring-inset ${style} ${sizeClass}`}
    >
      {label}
    </span>
  );
}
