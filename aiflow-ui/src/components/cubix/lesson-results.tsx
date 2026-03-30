import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { useI18n } from "@/hooks/use-i18n";
import type { LessonResult } from "@/lib/types";

interface LessonResultsProps {
  results: LessonResult[];
}

const STATUS_COLORS: Record<string, string> = {
  completed: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
  pending: "bg-gray-100 text-gray-600",
  skipped: "bg-yellow-100 text-yellow-800",
};

export function LessonResults({ results }: LessonResultsProps) {
  const { t } = useI18n();
  return (
    <div className="border rounded-lg overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-[50px]">{t("table.week")}</TableHead>
            <TableHead>{t("table.lesson")}</TableHead>
            <TableHead className="w-[90px]">{t("common.status")}</TableHead>
            <TableHead className="w-[80px]">{t("common.cost")}</TableHead>
            <TableHead>{t("table.error")}</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {results.map((r) => (
            <TableRow key={`${r.week_index}-${r.lesson_index}`}>
              <TableCell className="text-xs text-muted-foreground">
                W{r.week_index + 1}
              </TableCell>
              <TableCell className="text-sm">{r.title}</TableCell>
              <TableCell>
                <Badge className={`${STATUS_COLORS[r.status] || STATUS_COLORS.pending} text-[10px]`}>
                  {r.status}
                </Badge>
              </TableCell>
              <TableCell className="text-xs">
                {r.cost_usd > 0 ? `$${r.cost_usd.toFixed(4)}` : "-"}
              </TableCell>
              <TableCell className="text-xs text-red-600 truncate max-w-[200px]">
                {r.error || "-"}
              </TableCell>
            </TableRow>
          ))}
          {results.length === 0 && (
            <TableRow>
              <TableCell colSpan={5} className="text-center text-muted-foreground py-8">
                {t("cubix.noResults")}
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  );
}
