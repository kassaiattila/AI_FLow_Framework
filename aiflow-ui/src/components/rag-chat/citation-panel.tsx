"use client";

import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useI18n } from "@/hooks/use-i18n";
import type { Citation } from "@/lib/types";

interface CitationPanelProps {
  citations: Citation[];
  activeCitation: number | null;
}

export function CitationPanel({ citations, activeCitation }: CitationPanelProps) {
  const { t } = useI18n();
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);

  if (citations.length === 0) {
    return (
      <div className="text-sm text-muted-foreground text-center py-8">
        {t("rag.noCitations")}
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {citations.map((cit, idx) => {
        const citNum = idx + 1;
        const isActive = activeCitation === citNum;
        const isExpanded = expandedIdx === idx;
        const pct = Math.round(cit.relevance_score * 100);
        const barColor =
          pct >= 90 ? "bg-green-500" : pct >= 70 ? "bg-yellow-500" : "bg-red-500";

        return (
          <Card
            key={idx}
            className={`cursor-pointer transition-colors ${
              isActive ? "ring-2 ring-blue-500" : ""
            }`}
            onClick={() => setExpandedIdx(isExpanded ? null : idx)}
          >
            <CardContent className="p-3 space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Badge className="bg-blue-100 text-blue-800 text-[10px]">[{citNum}]</Badge>
                  <span className="text-xs font-medium truncate max-w-[200px]">
                    {cit.document_name}
                  </span>
                </div>
                <span className="text-xs text-muted-foreground">{pct}%</span>
              </div>

              <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                <div className={`h-full rounded-full ${barColor}`} style={{ width: `${pct}%` }} />
              </div>

              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                {cit.section && <span>{cit.section}</span>}
                {cit.page && <span>p. {cit.page}</span>}
              </div>

              {isExpanded && cit.excerpt && (
                <div className="border-t pt-2 mt-2">
                  <p className="text-xs leading-relaxed text-muted-foreground whitespace-pre-wrap">
                    {cit.excerpt}
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
