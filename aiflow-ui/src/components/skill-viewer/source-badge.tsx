"use client";

import { Badge } from "@/components/ui/badge";
import { useI18n } from "@/hooks/use-i18n";

type Source = "backend" | "subprocess" | "demo" | "filesystem" | null;

const STYLES: Record<string, { bg: string; key: string }> = {
  backend:    { bg: "bg-green-100 text-green-800",  key: "backend.live" },
  subprocess: { bg: "bg-blue-100 text-blue-800",   key: "backend.subprocess" },
  filesystem: { bg: "bg-green-100 text-green-800",  key: "backend.live" },
  demo:       { bg: "bg-yellow-100 text-yellow-800", key: "backend.demo" },
};

interface SourceBadgeProps {
  source: Source;
  extra?: string;
  fallbackKey?: string;
}

export function SourceBadge({ source, extra, fallbackKey }: SourceBadgeProps) {
  const { t } = useI18n();

  if (!source) {
    const label = fallbackKey ? t(fallbackKey) : "";
    return label ? (
      <Badge className="bg-gray-100 text-gray-600 text-sm px-3 py-1">{label}</Badge>
    ) : null;
  }

  const style = STYLES[source] || STYLES.demo;
  const label = t(style.key);

  return (
    <Badge className={`${style.bg} text-sm px-3 py-1`}>
      {extra ? `${label} — ${extra}` : label}
    </Badge>
  );
}
