"use client";

import { useEffect, useState, useCallback } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PipelineProgress, FileDetail } from "@/components/cubix/pipeline-progress";
import { CourseStructureView } from "@/components/cubix/course-structure";
import { LessonResults } from "@/components/cubix/lesson-results";
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
  const [courses, setCourses] = useState<CubixCourseResult[]>([]);
  const [selected, setSelected] = useState<CubixCourseResult | null>(null);
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(() => {
    setLoading(true);
    setError(null);
    fetch("/api/cubix")
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data: { courses: CubixCourseResult[] }) => {
        setCourses(data.courses);
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
          <h2 className="text-2xl font-bold">Cubix Course Capture</h2>
          <p className="text-muted-foreground">
            Video transcript pipeline (ffmpeg + Whisper STT + LLM strukturalas)
          </p>
        </div>
        <Badge className="bg-green-100 text-green-800 text-sm px-3 py-1">Production</Badge>
      </div>

      {loading && (
        <Card><CardContent className="py-12 text-center text-muted-foreground">Betoltes...</CardContent></Card>
      )}

      {error && (
        <Card><CardContent className="py-8 text-center">
          <p className="text-red-600 text-sm mb-2">Hiba: {error}</p>
          <button onClick={loadData} className="text-sm text-blue-600 underline">Ujraprobalkozas</button>
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
        <KpiCard title="Kurzus" value={selected.course_title} sub={selected.course_name} />
        <KpiCard
          title="Haladás"
          value={`${completedPct}%`}
          sub={`${ps?.completed_files || 0} / ${ps?.total_files || 0} fajl`}
        />
        <KpiCard
          title="Sikertelen"
          value={String(ps?.failed_files || 0)}
          sub="fajl"
        />
        <KpiCard
          title="Koltseg"
          value={`$${selected.total_cost_usd.toFixed(4)}`}
          sub="osszesen"
        />
        <KpiCard
          title="Video lecke"
          value={String(selected.structure.total_video_lessons)}
          sub={`/ ${selected.structure.total_lessons} lecke`}
        />
      </div>

      {/* Main content */}
      <Tabs defaultValue="pipeline">
        <TabsList>
          <TabsTrigger value="pipeline">Pipeline</TabsTrigger>
          <TabsTrigger value="structure">Kurzus</TabsTrigger>
          <TabsTrigger value="results">Eredmenyek</TabsTrigger>
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
                  Valasszon egy fajlt a pipeline allapot megtekitesehez
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
