import { useI18n } from "@/hooks/use-i18n";
import type { SearchResult } from "@/lib/types";

interface SearchRelevanceProps {
  results: SearchResult[];
}

export function SearchRelevance({ results }: SearchRelevanceProps) {
  const { t } = useI18n();
  if (results.length === 0) {
    return (
      <div className="text-sm text-muted-foreground text-center py-8">
        {t("rag.noSearch")}
      </div>
    );
  }

  const maxScore = Math.max(...results.map((r) => r.similarity_score));

  return (
    <div className="space-y-3">
      <p className="text-xs text-muted-foreground">{results.length} {t("rag.chunks")}</p>
      {results.map((result, idx) => {
        const pct = maxScore > 0 ? (result.similarity_score / maxScore) * 100 : 0;
        const scorePct = Math.round(result.similarity_score * 100);
        const barColor =
          scorePct >= 80 ? "bg-green-500" : scorePct >= 60 ? "bg-yellow-500" : "bg-gray-400";

        return (
          <div key={result.chunk_id || idx} className="space-y-1">
            <div className="flex items-center justify-between text-xs">
              <span className="font-medium truncate max-w-[200px]">{result.document_name}</span>
              <span className="text-muted-foreground">{scorePct}%</span>
            </div>
            <div className="h-2 bg-muted rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full ${barColor} transition-all`}
                style={{ width: `${pct}%` }}
              />
            </div>
            <p className="text-xs text-muted-foreground truncate">{result.content.slice(0, 100)}...</p>
          </div>
        );
      })}
    </div>
  );
}
