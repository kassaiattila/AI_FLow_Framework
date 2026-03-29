import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { SimStatus } from "@/hooks/use-workflow-simulation";
import type { ProcessedInvoice } from "@/lib/types";

// --- Document processing status ---

export type DocStatus = "new" | "processing" | "completed" | "failed" | "verified";

export function getDocStatus(inv: ProcessedInvoice): DocStatus {
  // Derive status from data — in real app this would be a backend field
  if (!inv.validation) return "new";
  if (inv.parser_used === "pending") return "new";
  const conf = inv.extraction_confidence || inv.validation.confidence_score;
  if (conf === 0 && inv.line_items.length === 0) return "new";
  if (!inv.validation.is_valid && inv.validation.errors.length > 0) return "failed";
  if (conf >= 0.9 && inv.validation.is_valid) return "completed";
  if (conf > 0) return "completed";
  return "new";
}

export const DOC_STATUS_CONFIG: Record<DocStatus, { icon: string; color: string; label: string }> = {
  new:        { icon: "\u25CB", color: "text-gray-400", label: "Uj" },
  processing: { icon: "\u25CF", color: "text-blue-500 animate-pulse", label: "Feldolgozas" },
  completed:  { icon: "\u2713", color: "text-green-600", label: "Kesz" },
  failed:     { icon: "!", color: "text-red-600", label: "Hiba" },
  verified:   { icon: "\u2713\u2713", color: "text-green-700", label: "Verifikalt" },
};

// --- Compact amount formatting ---

export function formatCompactAmount(inv: ProcessedInvoice): string {
  const g = inv.totals.gross_total;
  const c = inv.header.currency;
  if (c === "HUF") return g >= 1000 ? `${Math.round(g / 1000)}k Ft` : `${g} Ft`;
  if (c === "EUR") return `\u20AC${g}`;
  if (c === "USD") return `$${g}`;
  return `${g} ${c}`;
}

// --- Shared badge components ---

export function ConfidenceBadge({ value }: { value: number }) {
  if (!value || value === 0) return <Badge className="bg-gray-100 text-gray-500 text-xs">—</Badge>;
  const pct = Math.round(value * 100);
  const color =
    pct >= 90 ? "bg-green-100 text-green-800" : pct >= 70 ? "bg-yellow-100 text-yellow-800" : "bg-red-100 text-red-800";
  return <Badge className={`${color} text-xs`}>{pct}%</Badge>;
}

export function RunStatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    completed: "bg-green-100 text-green-700",
    running: "bg-blue-100 text-blue-700",
    failed: "bg-red-100 text-red-700",
    pending: "bg-gray-100 text-gray-500",
  };
  return <Badge className={`text-xs ${styles[status] || styles.pending}`}>{status}</Badge>;
}

export function SimStatusBadge({ status }: { status: SimStatus }) {
  if (status === "running") return <Badge className="bg-blue-100 text-blue-700 text-xs">Fut...</Badge>;
  if (status === "completed") return <Badge className="bg-green-100 text-green-700 text-xs">Kesz</Badge>;
  if (status === "failed") return <Badge className="bg-red-100 text-red-700 text-xs">Hiba</Badge>;
  return null;
}

export function KpiCard({ title, value, sub }: { title: string; value: string; sub: string }) {
  return (
    <Card>
      <CardContent className="pt-4 pb-3 px-4">
        <p className="text-xs text-muted-foreground">{title}</p>
        <p className="text-2xl font-bold">{value}</p>
        <p className="text-[10px] text-muted-foreground">{sub}</p>
      </CardContent>
    </Card>
  );
}

export function DocStatusIcon({ status }: { status: DocStatus }) {
  const cfg = DOC_STATUS_CONFIG[status];
  return <span className={`text-sm font-bold ${cfg.color}`} title={cfg.label}>{cfg.icon}</span>;
}
