"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useI18n } from "@/hooks/use-i18n";
import type { EntityResult } from "@/lib/types";
import { ConfidenceBar } from "./shared";

interface EntityListProps {
  entities: EntityResult;
  highlightedEntity: string | null;
  onEntityHover: (entityType: string | null) => void;
}

export function EntityList({ entities, highlightedEntity, onEntityHover }: EntityListProps) {
  const { t } = useI18n();
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm">{t("email.entities")} ({entities.entity_count})</CardTitle>
          <div className="flex gap-1">
            {entities.extraction_methods_used.map((m) => (
              <Badge key={m} className="bg-gray-100 text-gray-600 text-[9px]">
                {m}
              </Badge>
            ))}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {entities.entities.map((entity, idx) => (
            <div
              key={`${entity.entity_type}-${idx}`}
              className={`p-2 rounded border text-sm cursor-pointer transition-colors ${
                highlightedEntity === entity.entity_type
                  ? "border-yellow-400 bg-yellow-50"
                  : "hover:bg-muted/50"
              }`}
              onMouseEnter={() => onEntityHover(entity.entity_type)}
              onMouseLeave={() => onEntityHover(null)}
            >
              <div className="flex items-center justify-between mb-1">
                <Badge className="bg-slate-100 text-slate-700 text-[10px]">
                  {entity.entity_type}
                </Badge>
                <span className="text-xs text-muted-foreground">{entity.extraction_method}</span>
              </div>
              <p className="font-medium text-sm">{entity.value}</p>
              {entity.normalized_value && entity.normalized_value !== entity.value && (
                <p className="text-xs text-muted-foreground">{entity.normalized_value}</p>
              )}
              <ConfidenceBar value={entity.confidence} className="mt-1" />
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
