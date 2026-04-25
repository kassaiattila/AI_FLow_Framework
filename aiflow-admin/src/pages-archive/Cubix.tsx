/**
 * Cubix Course Viewer — migrated from MUI to Untitled UI + Tailwind.
 * S6: UI polish, MUI removal.
 */

import { useState, useEffect } from "react";
import { fetchApi } from "../lib/api-client";
import { useTranslate } from "../lib/i18n";
import { PageLayout } from "../layout/PageLayout";

interface CubixCourse {
  course_id: string;
  course_name?: string;
  title?: string;
  status?: string;
  sections?: Array<{ title: string; duration_sec?: number }>;
  total_duration_sec?: number;
  transcript_files?: string[];
}

interface CubixResponse {
  courses: CubixCourse[];
  source: string;
}

function formatDuration(sec?: number): string {
  if (!sec) return "-";
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

export function Cubix() {
  const translate = useTranslate();
  const [courses, setCourses] = useState<CubixCourse[]>([]);
  const [source, setSource] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchApi<CubixResponse>("GET", "/api/v1/cubix")
      .then((data) => {
        setCourses(data.courses || []);
        setSource(data.source || null);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <PageLayout titleKey="aiflow.cubix.title">
        <div className="flex h-64 items-center justify-center">
          <span className="h-8 w-8 animate-spin rounded-full border-4 border-gray-300 border-t-brand-500" />
        </div>
      </PageLayout>
    );
  }

  if (error) {
    return (
      <PageLayout titleKey="aiflow.cubix.title">
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-950/20 dark:text-red-400">
          {error}
        </div>
      </PageLayout>
    );
  }

  return (
    <PageLayout titleKey="aiflow.cubix.title" source={source}>
      {courses.length === 0 ? (
        <div className="py-12 text-center text-sm text-gray-400">
          {translate("aiflow.cubix.empty")}
        </div>
      ) : (
        <div className="space-y-4">
          {courses.map((course) => (
            <div
              key={course.course_id}
              className="rounded-lg border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-800"
            >
              <div className="flex items-start justify-between">
                <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100">
                  {course.course_name || course.title || course.course_id}
                </h3>
                {course.status && (
                  <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600 dark:bg-gray-700 dark:text-gray-400">
                    {course.status}
                  </span>
                )}
              </div>

              {course.total_duration_sec != null && (
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                  {translate("aiflow.cubix.duration")}:{" "}
                  {formatDuration(course.total_duration_sec)}
                </p>
              )}

              {course.sections && course.sections.length > 0 && (
                <div className="mt-3">
                  <p className="text-xs font-medium text-gray-500 dark:text-gray-400">
                    {translate("aiflow.cubix.sections")}
                  </p>
                  <ul className="mt-1 space-y-0.5">
                    {course.sections.map((sec, i) => (
                      <li
                        key={i}
                        className="ml-4 text-sm text-gray-700 dark:text-gray-300"
                      >
                        {i + 1}. {sec.title}
                        {sec.duration_sec != null && (
                          <span className="text-gray-400">
                            {" "}
                            ({formatDuration(sec.duration_sec)})
                          </span>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {course.transcript_files &&
                course.transcript_files.length > 0 && (
                  <div className="mt-3">
                    <p className="text-xs font-medium text-gray-500 dark:text-gray-400">
                      {translate("aiflow.cubix.transcripts")}
                    </p>
                    <div className="mt-1 flex flex-wrap gap-1">
                      {course.transcript_files.map((f, i) => (
                        <span
                          key={i}
                          className="rounded border border-gray-300 px-2 py-0.5 text-xs text-gray-600 dark:border-gray-600 dark:text-gray-400"
                        >
                          {f}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
            </div>
          ))}
        </div>
      )}
    </PageLayout>
  );
}
