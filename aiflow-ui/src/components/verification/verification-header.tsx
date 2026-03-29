"use client";

import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import type { DocumentMeta } from "@/lib/verification-types";
import { getConfidenceColor, CONFIDENCE_STYLES } from "@/lib/verification-types";

const DOC_TYPE_LABELS: Record<string, string> = {
  invoice: "Szamla",
  receipt: "Nyugta",
  contract: "Szerzodes",
  credit_note: "Jovairas",
  proforma: "Proforma",
  unknown: "Ismeretlen",
};

const DIRECTION_LABELS: Record<string, string> = {
  incoming: "Bejovo",
  outgoing: "Kimeno",
  unknown: "?",
};

interface VerificationHeaderProps {
  meta: DocumentMeta | null;
  sourceFile: string;
  stats: {
    total: number;
    auto: number;
    corrected: number;
    confirmed: number;
  };
}

export function VerificationHeader({
  meta,
  sourceFile,
  stats,
}: VerificationHeaderProps) {
  if (!meta) return null;

  const progress =
    stats.total > 0
      ? Math.round(((stats.confirmed + stats.corrected) / stats.total) * 100)
      : 0;

  return (
    <div className="flex items-center gap-4 flex-wrap">
      {/* Document type */}
      <MetaBadge
        label="Tipus"
        value={DOC_TYPE_LABELS[meta.document_type] || meta.document_type}
        confidence={meta.document_type_confidence}
      />

      {/* Direction */}
      <MetaBadge
        label="Irany"
        value={DIRECTION_LABELS[meta.direction] || meta.direction}
        confidence={meta.direction_confidence}
      />

      {/* Language */}
      <MetaBadge
        label="Nyelv"
        value={meta.language.toUpperCase()}
        confidence={meta.language_confidence}
      />

      {/* File name */}
      <span className="text-xs text-muted-foreground font-mono truncate max-w-[200px]">
        {sourceFile}
      </span>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Progress */}
      <div className="flex items-center gap-2 shrink-0">
        <span className="text-xs text-muted-foreground">
          {stats.confirmed + stats.corrected}/{stats.total}
        </span>
        <div className="w-24">
          <Progress value={progress} className="h-2" />
        </div>
        <span className="text-xs font-medium">{progress}%</span>
      </div>
    </div>
  );
}

function MetaBadge({
  label,
  value,
  confidence,
}: {
  label: string;
  value: string;
  confidence: number;
}) {
  const color = getConfidenceColor(confidence);
  return (
    <div className="flex items-center gap-1.5">
      <span className="text-[10px] text-muted-foreground">{label}:</span>
      <Badge className={`${CONFIDENCE_STYLES[color].badge} text-xs px-1.5 py-0`}>
        {value}
      </Badge>
      <span className="text-[10px] text-muted-foreground">
        {(confidence * 100).toFixed(0)}%
      </span>
    </div>
  );
}
