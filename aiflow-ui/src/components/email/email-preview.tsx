"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { EmailProcessingResult, Entity } from "@/lib/types";
import { formatDate } from "./shared";

interface EmailPreviewProps {
  email: EmailProcessingResult;
  highlightedEntity: string | null;
  onEntityClick?: (entityType: string) => void;
}

function highlightEntities(
  text: string,
  entities: Entity[],
  highlightedEntity: string | null
): React.ReactNode[] {
  if (!entities.length) return [text];

  // Sort entities by start_offset, filter out those without offsets
  const sorted = entities
    .filter((e) => e.start_offset != null && e.end_offset != null)
    .sort((a, b) => a.start_offset! - b.start_offset!);

  if (!sorted.length) return [text];

  const parts: React.ReactNode[] = [];
  let lastEnd = 0;

  for (const entity of sorted) {
    const start = entity.start_offset!;
    const end = entity.end_offset!;
    if (start < lastEnd || start >= text.length) continue;

    if (start > lastEnd) {
      parts.push(text.slice(lastEnd, start));
    }

    const isActive = highlightedEntity === entity.entity_type;
    parts.push(
      <mark
        key={`${entity.entity_type}-${start}`}
        className={`rounded px-0.5 ${isActive ? "bg-yellow-300 ring-2 ring-yellow-500" : "bg-yellow-100"}`}
        title={`${entity.entity_type}: ${entity.value}`}
      >
        {text.slice(start, Math.min(end, text.length))}
      </mark>
    );
    lastEnd = Math.min(end, text.length);
  }

  if (lastEnd < text.length) {
    parts.push(text.slice(lastEnd));
  }

  return parts;
}

export function EmailPreview({ email, highlightedEntity, onEntityClick }: EmailPreviewProps) {
  const entities = email.entities?.entities || [];
  const bodyParts = highlightEntities(email.body || "", entities, highlightedEntity);

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm">Email</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid grid-cols-[80px_1fr] gap-y-1 text-sm">
          <span className="text-muted-foreground">Feladó:</span>
          <span className="font-medium">{email.sender}</span>
          <span className="text-muted-foreground">Tárgy:</span>
          <span className="font-medium">{email.subject}</span>
          <span className="text-muted-foreground">Dátum:</span>
          <span>{formatDate(email.received_date)}</span>
          {email.has_attachments && (
            <>
              <span className="text-muted-foreground">Csatolm.:</span>
              <span>{email.attachment_count} fájl</span>
            </>
          )}
        </div>

        <div className="border-t pt-3">
          <pre className="whitespace-pre-wrap text-sm font-sans leading-relaxed">{bodyParts}</pre>
        </div>

        {email.attachment_summaries.length > 0 && (
          <div className="border-t pt-3 space-y-2">
            <p className="text-xs font-medium text-muted-foreground">Csatolmányok</p>
            {email.attachment_summaries.map((att) => (
              <div
                key={att.filename}
                className="flex items-center gap-2 text-xs p-2 bg-muted/50 rounded"
              >
                <span className="font-medium">{att.filename}</span>
                <span className="text-muted-foreground">
                  ({(att.size_bytes / 1024).toFixed(0)} KB)
                </span>
                {att.document_type && (
                  <Badge className="bg-gray-100 text-gray-700 text-[9px]">
                    {att.document_type}
                  </Badge>
                )}
                {att.processor_used && (
                  <Badge className="bg-blue-50 text-blue-700 text-[9px]">
                    {att.processor_used}
                  </Badge>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
