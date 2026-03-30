"use client";

import { useEffect, useState, useCallback } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PipelineProgress, FileDetail } from "@/components/cubix/pipeline-progress";
import { CourseStructureView } from "@/components/cubix/course-structure";
import { LessonResults } from "@/components/cubix/lesson-results";
import { useI18n } from "@/hooks/use-i18n";
import type { CubixCourseResult } from "@/lib/types";

function KpiCard({ title, value, sub }: { title: string; value: string; sub: string }) {
  return (
    <Card>
      <CardContent className="pt-4">
        <p className="text-xs text-muted-foreground">{title}</p>
        <p className="text-2xl font-bold">{value}</p>
        <p className="text-xs text-muted-foreground">{sub}</p>
      </CardContent>
    </Card>
  );
}

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
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">{t("cubix.title")}</h2>
          <p className="text-muted-foreground">
            {t("cubix.desc")}
          </p>
        </div>
        {source === "filesystem" ? (
          <Badge className="bg-green-100 text-green-800 text-sm px-3 py-1">{t("backend.live")}</Badge>
        ) : source === "demo" ? (
          <Badge className="bg-yellow-100 text-yellow-800 text-sm px-3 py-1">{t("backend.demo")} — {t("cubix.resultsViewer")}</Badge>
        ) : (
          <Badge className="bg-gray-100 text-gray-600 text-sm px-3 py-1">{t("cubix.resultsViewer")}</Badge>
        )}
      </div>

      {source === "demo" && (
        <p className="text-xs text-muted-foreground italic">{t("cubix.resultsViewerHint")}</p>
      )}

      {loading && (
        <Card><CardContent className="py-12 text-center text-muted-foreground">{t("common.loading")}</CardContent></Card>
      )}

      {error && (
        <Card><CardContent className="py-8 text-center">
          <p className="text-red-600 text-sm mb-2">{t("common.errorPrefix")}{error}</p>
          <button onClick={loadData} className="text-sm text-blue-600 underline">{t("common.retry")}</button>
        </CardContent></Card>
      )}

      {!loading && !error && selected && <>
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
        <KpiCard
          title={t("cubix.progress")}
          value={`${completedPct}%`}
          sub={`${ps?.completed_files || 0} / ${ps?.total_files || 0} ${t("common.file")}`}
        />
        <KpiCard
          title={t("cubix.failedFiles")}
          value={String(ps?.failed_files || 0)}
          sub={t("common.file")}
        />
        <KpiCard
          title={t("cubix.cost")}
          value={`$${selected.total_cost_usd.toFixed(4)}`}
          sub={t("common.total")}
        />
        <KpiCard
          title={t("cubix.videoLessons")}
          value={String(selected.structure.total_video_lessons)}
          sub={`/ ${selected.structure.total_lessons} ${t("cubix.lesson")}`}
        />
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
            <PipelineProgress
              files={ps?.files || {}}
              selectedSlug={selectedSlug}
              onSelect={setSelectedSlug}
            />
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
          <CourseStructureView
            structure={selected.structure}
            results={selected.results}
          />
        </TabsContent>

        <TabsContent value="results" className="mt-4">
          <LessonResults results={selected.results} />
        </TabsContent>
      </Tabs>
      </>}
    </div>
  );
}
