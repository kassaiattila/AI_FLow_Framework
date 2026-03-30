"use client";

import { useEffect, useState, useCallback } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PipelineProgress, FileDetail } from "@/components/cubix/pipeline-progress";
import { CourseStructureView } from "@/components/cubix/course-structure";
import { LessonResults } from "@/components/cubix/lesson-results";
import { SkillViewerLayout, KpiCard } from "@/components/skill-viewer";
import { useI18n } from "@/hooks/use-i18n";
import type { CubixCourseResult } from "@/lib/types";

export default function CubixCourseCapturePage() {
  const { t } = useI18n();
  const [courses, setCourses] = useState<CubixCourseResult[]>([]);
  const [selected, setSelected] = useState<CubixCourseResult | null>(null);
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [source, setSource] = useState<"filesystem" | "demo" | null>(null);

  const loadData = useCallback(() => {
    setLoading(true);
    setError(null);
    fetch("/api/cubix")
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data: { courses: CubixCourseResult[]; source?: string }) => {
        setCourses(data.courses);
        if (data.source) setSource(data.source as "filesystem" | "demo");
        if (data.courses.length > 0 && !selected) {
          setSelected(data.courses[0]);
        }
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const ps = selected?.pipeline_state;
  const completedPct = ps ? Math.round((ps.completed_files / ps.total_files) * 100) : 0;
  const selectedFile = ps && selectedSlug ? ps.files[selectedSlug] : null;

  return (
    <SkillViewerLayout
      skillName="cubix"
      source={source}
      loading={loading}
      error={error}
      onRetry={loadData}
      badgeFallbackKey="cubix.resultsViewer"
      badgeExtra={source === "demo" ? t("cubix.resultsViewer") : undefined}
      headerNote={source === "demo" ? t("cubix.resultsViewerHint") : undefined}
    >
      {selected && <>
        {/* Course selector */}
        {courses.length > 1 && (
          <div className="flex gap-2 overflow-x-auto pb-1">
            {courses.map((c) => (
              <button
                key={c.course_id}
                onClick={() => { setSelected(c); setSelectedSlug(null); }}
                className={`px-3 py-1 rounded-full text-xs whitespace-nowrap border transition-colors ${
                  selected.course_id === c.course_id
                    ? "bg-primary text-primary-foreground"
                    : "hover:bg-muted"
                }`}
              >
                {c.course_title}
              </button>
            ))}
          </div>
        )}

        {/* KPIs */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <KpiCard title={t("cubix.course")} value={selected.course_title} sub={selected.course_name} />
          <KpiCard title={t("cubix.progress")} value={`${completedPct}%`} sub={`${ps?.completed_files || 0} / ${ps?.total_files || 0} ${t("common.file")}`} />
          <KpiCard title={t("cubix.failedFiles")} value={String(ps?.failed_files || 0)} sub={t("common.file")} />
          <KpiCard title={t("cubix.cost")} value={`$${selected.total_cost_usd.toFixed(4)}`} sub={t("common.total")} />
          <KpiCard title={t("cubix.videoLessons")} value={String(selected.structure.total_video_lessons)} sub={`/ ${selected.structure.total_lessons} ${t("cubix.lesson")}`} />
        </div>

        {/* Main content */}
        <Tabs defaultValue="pipeline">
          <TabsList>
            <TabsTrigger value="pipeline">{t("cubix.pipeline")}</TabsTrigger>
            <TabsTrigger value="structure">{t("cubix.structure")}</TabsTrigger>
            <TabsTrigger value="results">{t("cubix.results")}</TabsTrigger>
          </TabsList>

          <TabsContent value="pipeline" className="mt-4">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <PipelineProgress files={ps?.files || {}} selectedSlug={selectedSlug} onSelect={setSelectedSlug} />
              {selectedFile ? (
                <FileDetail file={selectedFile} />
              ) : (
                <Card>
                  <CardContent className="py-12 text-center text-muted-foreground text-sm">
                    {t("cubix.selectFile")}
                  </CardContent>
                </Card>
              )}
            </div>
          </TabsContent>

          <TabsContent value="structure" className="mt-4">
            <CourseStructureView structure={selected.structure} results={selected.results} />
          </TabsContent>

          <TabsContent value="results" className="mt-4">
            <LessonResults results={selected.results} />
          </TabsContent>
        </Tabs>
      </>}
    </SkillViewerLayout>
  );
}
