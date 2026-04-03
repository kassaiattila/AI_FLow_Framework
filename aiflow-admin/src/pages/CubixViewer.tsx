import { useState, useEffect } from "react";
import { useTranslate, Title } from "react-admin";
import {
  Card, CardContent, Typography, CircularProgress,
  Alert, Chip, Box, Stack,
} from "@mui/material";

interface CubixCourse {
  course_id: string;
  course_name?: string;
  title?: string;
  status?: string;
  sections?: Array<{ title: string; duration_sec?: number }>;
  total_duration_sec?: number;
  transcript_files?: string[];
  [key: string]: unknown;
}

export const CubixViewer = () => {
  const translate = useTranslate();
  const [courses, setCourses] = useState<CubixCourse[]>([]);
  const [source, setSource] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("aiflow_token");
    fetch("/api/v1/cubix", {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => {
        setCourses(data.courses || []);
        setSource(data.source || null);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const formatDuration = (sec?: number) => {
    if (!sec) return "-";
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return m > 0 ? `${m}m ${s}s` : `${s}s`;
  };

  return (
    <Box sx={{ p: 3, maxWidth: 1200, mx: "auto" }}>
      <Title title={translate("aiflow.cubix.title")} />

      <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2 }}>
        <Typography variant="h6">{translate("aiflow.cubix.title")}</Typography>
        {source && (
          <Chip
            label={translate(`aiflow.status.${source === "filesystem" ? "subprocess" : source}`)}
            color={source === "demo" ? "warning" : "success"}
            size="small"
          />
        )}
      </Stack>

      {loading && <CircularProgress />}
      {error && <Alert severity="error">{error}</Alert>}

      {!loading && courses.length === 0 && !error && (
        <Alert severity="info">{translate("aiflow.cubix.empty")}</Alert>
      )}

      <Stack spacing={2}>
        {courses.map((course) => (
          <Card key={course.course_id}>
            <CardContent>
              <Typography variant="h6">
                {course.course_name || course.title || course.course_id}
              </Typography>
              {course.status && (
                <Chip label={course.status} size="small" sx={{ mt: 0.5, mb: 1 }} />
              )}
              {course.total_duration_sec != null && (
                <Typography variant="body2" color="text.secondary">
                  {translate("aiflow.cubix.duration")}: {formatDuration(course.total_duration_sec)}
                </Typography>
              )}

              {/* Sections */}
              {course.sections && course.sections.length > 0 && (
                <Box sx={{ mt: 1 }}>
                  <Typography variant="subtitle2">{translate("aiflow.cubix.sections")}</Typography>
                  {course.sections.map((sec, i) => (
                    <Typography key={i} variant="body2" sx={{ ml: 2 }}>
                      {i + 1}. {sec.title}
                      {sec.duration_sec != null && ` (${formatDuration(sec.duration_sec)})`}
                    </Typography>
                  ))}
                </Box>
              )}

              {/* Transcript files */}
              {course.transcript_files && course.transcript_files.length > 0 && (
                <Box sx={{ mt: 1 }}>
                  <Typography variant="subtitle2">{translate("aiflow.cubix.transcripts")}</Typography>
                  <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap sx={{ mt: 0.5 }}>
                    {course.transcript_files.map((f, i) => (
                      <Chip key={i} label={f} size="small" variant="outlined" />
                    ))}
                  </Stack>
                </Box>
              )}
            </CardContent>
          </Card>
        ))}
      </Stack>
    </Box>
  );
};
