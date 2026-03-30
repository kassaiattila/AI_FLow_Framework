"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useI18n } from "@/hooks/use-i18n";
import type { ReviewOutput } from "@/lib/types";

interface ReviewScoresProps {
  review: ReviewOutput;
}

function ScoreBox({ label, score }: { label: string; score: number }) {
  const color =
    score >= 7
      ? "text-green-700 bg-green-50 border-green-200"
      : score >= 4
        ? "text-yellow-700 bg-yellow-50 border-yellow-200"
        : "text-red-700 bg-red-50 border-red-200";

  return (
    <div className={`border rounded p-3 text-center ${color}`}>
      <p className="text-2xl font-bold">{score}</p>
      <p className="text-xs">{label}</p>
    </div>
  );
}

export function ReviewScores({ review }: ReviewScoresProps) {
  const { t } = useI18n();
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm">{t("processdoc.qualityTitle")}</CardTitle>
          <span
            className={`text-sm font-bold ${review.is_acceptable ? "text-green-600" : "text-red-600"}`}
          >
            {review.is_acceptable ? t("processdoc.acceptable") : t("processdoc.needsWork")}
          </span>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-5 gap-2">
          <ScoreBox label={t("processdoc.scoreOverall")} score={review.score} />
          <ScoreBox label={t("processdoc.scoreCompleteness")} score={review.completeness_score} />
          <ScoreBox label={t("processdoc.scoreLogic")} score={review.logic_score} />
          <ScoreBox label={t("processdoc.scoreActors")} score={review.actors_score} />
          <ScoreBox label={t("processdoc.scoreDecisions")} score={review.decisions_score} />
        </div>

        {review.issues.length > 0 && (
          <div>
            <p className="text-xs font-medium mb-1">{t("processdoc.issues")}:</p>
            <ul className="text-xs text-muted-foreground space-y-1">
              {review.issues.map((issue, i) => (
                <li key={i} className="flex gap-1">
                  <span className="text-red-500">-</span> {issue}
                </li>
              ))}
            </ul>
          </div>
        )}

        {review.suggestions.length > 0 && (
          <div>
            <p className="text-xs font-medium mb-1">{t("processdoc.suggestions")}:</p>
            <ul className="text-xs text-muted-foreground space-y-1">
              {review.suggestions.map((sug, i) => (
                <li key={i} className="flex gap-1">
                  <span className="text-blue-500">+</span> {sug}
                </li>
              ))}
            </ul>
          </div>
        )}

        {review.reasoning && (
          <p className="text-xs text-muted-foreground border-t pt-2">{review.reasoning}</p>
        )}
      </CardContent>
    </Card>
  );
}
