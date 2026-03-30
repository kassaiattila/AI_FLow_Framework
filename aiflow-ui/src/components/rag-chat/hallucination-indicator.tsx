import { Badge } from "@/components/ui/badge";
import { useI18n } from "@/hooks/use-i18n";

interface HallucinationIndicatorProps {
  score: number;
}

export function HallucinationIndicator({ score }: HallucinationIndicatorProps) {
  const { t } = useI18n();
  const pct = Math.round(score * 100);

  let color: string;
  let label: string;

  if (score >= 0.85) {
    color = "bg-green-100 text-green-800";
    label = t("rag.grounded");
  } else if (score >= 0.7) {
    color = "bg-yellow-100 text-yellow-800";
    label = t("rag.partiallyGrounded");
  } else {
    color = "bg-red-100 text-red-800";
    label = t("rag.possibleHallucination");
  }

  return (
    <Badge className={`${color} text-[10px]`}>
      {label} ({pct}%)
    </Badge>
  );
}
