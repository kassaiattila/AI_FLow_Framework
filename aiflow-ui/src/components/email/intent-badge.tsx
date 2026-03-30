"use client";

import { Card, CardContent } from "@/components/ui/card";
import { useI18n } from "@/hooks/use-i18n";
import type { IntentResult } from "@/lib/types";
import { ConfidenceBar, MethodBadge } from "./shared";

interface IntentBadgeDetailProps {
  intent: IntentResult;
}

export function IntentBadgeDetail({ intent }: IntentBadgeDetailProps) {
  const { t } = useI18n();
  return (
    <Card>
      <CardContent className="pt-4 space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium">{intent.intent_display_name}</p>
            {intent.sub_intent && (
              <p className="text-xs text-muted-foreground">{intent.sub_intent}</p>
            )}
          </div>
          <MethodBadge method={intent.method} />
        </div>

        <div className="space-y-2">
          <div>
            <div className="flex items-center justify-between text-xs mb-1">
              <span>{t("email.result")}</span>
              <span className="font-medium">{(intent.confidence * 100).toFixed(1)}%</span>
            </div>
            <ConfidenceBar value={intent.confidence} />
          </div>

          {intent.sklearn_intent && (
            <div>
              <div className="flex items-center justify-between text-xs mb-1">
                <span className="text-purple-700">ML (sklearn)</span>
                <span>{intent.sklearn_intent}</span>
              </div>
              <ConfidenceBar value={intent.sklearn_confidence} />
            </div>
          )}

          {intent.llm_intent && (
            <div>
              <div className="flex items-center justify-between text-xs mb-1">
                <span className="text-blue-700">LLM</span>
                <span>{intent.llm_intent}</span>
              </div>
              <ConfidenceBar value={intent.llm_confidence} />
            </div>
          )}
        </div>

        {intent.reasoning && (
          <p className="text-xs text-muted-foreground border-t pt-2">{intent.reasoning}</p>
        )}
      </CardContent>
    </Card>
  );
}
