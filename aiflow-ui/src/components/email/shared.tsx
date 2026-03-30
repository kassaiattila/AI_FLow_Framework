"use client";

import { Badge } from "@/components/ui/badge";
import { useI18n } from "@/hooks/use-i18n";

const priorityColors: Record<number, string> = {
  1: "bg-red-100 text-red-800",
  2: "bg-orange-100 text-orange-800",
  3: "bg-yellow-100 text-yellow-800",
  4: "bg-blue-100 text-blue-800",
  5: "bg-gray-100 text-gray-800",
};

const priorityKeys: Record<number, string> = {
  1: "email.p1", 2: "email.p2", 3: "email.p3", 4: "email.p4", 5: "email.p5",
};

export function PriorityBadge({ level }: { level: number }) {
  const { t } = useI18n();
  return (
    <Badge className={`${priorityColors[level] || priorityColors[3]} text-[10px]`}>
      P{level} {t(priorityKeys[level] || "email.p3")}
    </Badge>
  );
}

export function IntentBadge({ intent, confidence }: { intent: string; confidence: number }) {
  const color =
    confidence >= 0.9
      ? "bg-green-100 text-green-800"
      : confidence >= 0.7
        ? "bg-yellow-100 text-yellow-800"
        : "bg-red-100 text-red-800";
  return (
    <Badge className={`${color} text-[10px]`}>
      {intent} ({(confidence * 100).toFixed(0)}%)
    </Badge>
  );
}

export function MethodBadge({ method }: { method: string }) {
  const color =
    method === "sklearn"
      ? "bg-purple-100 text-purple-800"
      : method === "llm"
        ? "bg-blue-100 text-blue-800"
        : "bg-indigo-100 text-indigo-800";
  return <Badge className={`${color} text-[10px]`}>{method.toUpperCase()}</Badge>;
}

export function ConfidenceBar({ value, className }: { value: number; className?: string }) {
  const pct = Math.round(value * 100);
  const color = pct >= 90 ? "bg-green-500" : pct >= 70 ? "bg-yellow-500" : "bg-red-500";
  return (
    <div className={`flex items-center gap-2 ${className || ""}`}>
      <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-muted-foreground w-10 text-right">{pct}%</span>
    </div>
  );
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("hu-HU", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}
