import { Badge } from "@/components/ui/badge";

interface HallucinationIndicatorProps {
  score: number;
}

export function HallucinationIndicator({ score }: HallucinationIndicatorProps) {
  const pct = Math.round(score * 100);

  let color: string;
  let label: string;

  if (score >= 0.85) {
    color = "bg-green-100 text-green-800";
    label = "Megalapozott";
  } else if (score >= 0.7) {
    color = "bg-yellow-100 text-yellow-800";
    label = "Reszben megalapozott";
  } else {
    color = "bg-red-100 text-red-800";
    label = "Lehetseges hallucin.";
  }

  return (
    <Badge className={`${color} text-[10px]`}>
      {label} ({pct}%)
    </Badge>
  );
}
