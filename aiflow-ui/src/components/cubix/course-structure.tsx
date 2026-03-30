import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { CourseStructure as CourseStructureType, LessonResult } from "@/lib/types";

interface CourseStructureProps {
  structure: CourseStructureType;
  results: LessonResult[];
}

function statusBadge(status: string) {
  const colors: Record<string, string> = {
    completed: "bg-green-100 text-green-800",
    failed: "bg-red-100 text-red-800",
    pending: "bg-gray-100 text-gray-600",
    skipped: "bg-yellow-100 text-yellow-800",
  };
  return <Badge className={`${colors[status] || colors.pending} text-[9px]`}>{status}</Badge>;
}

export function CourseStructureView({ structure, results }: CourseStructureProps) {
  const resultMap = new Map(results.map((r) => [`${r.week_index}-${r.lesson_index}`, r]));

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm">{structure.title}</CardTitle>
          <span className="text-xs text-muted-foreground">
            {structure.total_video_lessons} video / {structure.total_lessons} lecke
          </span>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {structure.weeks.map((week) => (
          <div key={week.index}>
            <p className="text-xs font-semibold text-muted-foreground mb-2">{week.title}</p>
            <div className="space-y-1">
              {week.lessons.map((lesson) => {
                const result = resultMap.get(`${week.index}-${lesson.index}`);
                return (
                  <div
                    key={`${week.index}-${lesson.index}`}
                    className="flex items-center justify-between text-xs p-1.5 rounded hover:bg-muted/50"
                  >
                    <div className="flex items-center gap-2">
                      <span>{lesson.has_video ? "\uD83C\uDFA5" : "\uD83D\uDCC4"}</span>
                      <span className="truncate max-w-[250px]">{lesson.title}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      {lesson.duration && (
                        <span className="text-muted-foreground">{lesson.duration}</span>
                      )}
                      {result && statusBadge(result.status)}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
