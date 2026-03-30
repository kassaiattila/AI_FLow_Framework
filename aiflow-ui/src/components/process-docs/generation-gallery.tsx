"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { ProcessDocResult } from "@/lib/types";

interface GenerationGalleryProps {
  documents: ProcessDocResult[];
  selectedId: string | null;
  onSelect: (doc: ProcessDocResult) => void;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("hu-HU", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function GenerationGallery({ documents, selectedId, onSelect }: GenerationGalleryProps) {
  if (documents.length === 0) {
    return (
      <div className="text-center text-muted-foreground py-12 text-sm">
        Nincs korabbi generalas
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
      {documents.map((doc) => {
        const scoreColor =
          doc.review.score >= 7
            ? "bg-green-100 text-green-800"
            : doc.review.score >= 4
              ? "bg-yellow-100 text-yellow-800"
              : "bg-red-100 text-red-800";

        return (
          <Card
            key={doc.doc_id}
            className={`cursor-pointer transition-colors ${
              selectedId === doc.doc_id ? "ring-2 ring-primary" : "hover:bg-muted/50"
            }`}
            onClick={() => onSelect(doc)}
          >
            <CardContent className="p-4 space-y-2">
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium truncate">{doc.extraction.title}</p>
                <Badge className={`${scoreColor} text-[10px]`}>{doc.review.score}/10</Badge>
              </div>

              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <span>{doc.extraction.actors.length} szereplo</span>
                <span>{doc.extraction.steps.length} lepes</span>
              </div>

              <pre className="text-[10px] text-muted-foreground bg-muted rounded p-2 max-h-[60px] overflow-hidden font-mono">
                {doc.mermaid_code.slice(0, 150)}...
              </pre>

              <p className="text-xs text-muted-foreground">{formatDate(doc.created_at)}</p>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
