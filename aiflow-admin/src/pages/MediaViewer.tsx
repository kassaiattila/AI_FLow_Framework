import { useState, useEffect, useCallback, useRef } from "react";
import { useTranslate, Title, useNotify } from "react-admin";
import {
  Box, Typography, Button, Stack, Card, CardContent, Chip,
  Table, TableHead, TableBody, TableRow, TableCell, TableContainer,
  CircularProgress, Alert, IconButton, TablePagination,
} from "@mui/material";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import DeleteIcon from "@mui/icons-material/Delete";
import VisibilityIcon from "@mui/icons-material/Visibility";

interface MediaJob {
  id: string;
  filename: string;
  media_type: string;
  file_size_bytes: number | null;
  duration_seconds: number | null;
  stt_provider: string;
  status: string;
  transcript_raw: string | null;
  transcript_structured: Record<string, unknown> | null;
  error: string | null;
  processing_time_ms: number | null;
  created_at: string;
  source: string;
}

export const MediaViewer = () => {
  const translate = useTranslate();
  const notify = useNotify();
  const [jobs, setJobs] = useState<MediaJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedJob, setSelectedJob] = useState<MediaJob | null>(null);
  const [page, setPage] = useState(0);
  const [total, setTotal] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchJobs = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/v1/media?limit=50&offset=${page * 50}`);
      if (res.ok) {
        const data = await res.json();
        setJobs(data.jobs || []);
        setTotal(data.total || 0);
      }
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => { fetchJobs(); }, [fetchJobs]);

  const handleUpload = async (files: FileList) => {
    if (files.length === 0) return;
    setUploading(true);
    try {
      for (const file of Array.from(files)) {
        const formData = new FormData();
        formData.append("file", file);
        const res = await fetch("/api/v1/media/upload", { method: "POST", body: formData });
        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
          throw new Error(err.detail || "Upload failed");
        }
      }
      notify(translate("aiflow.media.uploadSuccess"), { type: "success" });
      fetchJobs();
    } catch (e) {
      notify(e instanceof Error ? e.message : "Upload failed", { type: "error" });
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (jobId: string) => {
    try {
      await fetch(`/api/v1/media/${jobId}`, { method: "DELETE" });
      notify("aiflow.media.deleted", { type: "success" });
      if (selectedJob?.id === jobId) setSelectedJob(null);
      fetchJobs();
    } catch {
      notify("Delete failed", { type: "error" });
    }
  };

  const statusColor = (s: string) => {
    if (s === "completed") return "success";
    if (s === "running") return "warning";
    if (s === "failed") return "error";
    return "default";
  };

  return (
    <Box sx={{ p: 3 }}>
      <Title title={translate("aiflow.media.title")} />

      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 3 }}>
        <Box>
          <Typography variant="h5" fontWeight={600}>{translate("aiflow.media.title")}</Typography>
          <Typography variant="body2" color="text.secondary">{translate("aiflow.media.subtitle")}</Typography>
        </Box>
      </Stack>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {/* Upload Zone */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box
            onClick={() => fileInputRef.current?.click()}
            onDrop={(e) => { e.preventDefault(); handleUpload(e.dataTransfer.files); }}
            onDragOver={(e) => e.preventDefault()}
            sx={{
              border: "2px dashed", borderColor: "divider", borderRadius: 2, p: 4,
              textAlign: "center", cursor: "pointer",
              "&:hover": { borderColor: "primary.main", bgcolor: "action.hover" },
            }}
          >
            {uploading ? (
              <CircularProgress size={40} />
            ) : (
              <>
                <CloudUploadIcon sx={{ fontSize: 40, color: "primary.main", mb: 1 }} />
                <Typography color="primary" fontWeight={500}>{translate("aiflow.media.dropzone")}</Typography>
                <Typography variant="body2" color="text.secondary">MP4, MKV, MP3, WAV, M4A, WebM, OGG</Typography>
              </>
            )}
            <input ref={fileInputRef} type="file" multiple accept=".mp4,.mkv,.mp3,.wav,.m4a,.webm,.ogg" hidden onChange={(e) => e.target.files && handleUpload(e.target.files)} />
          </Box>
        </CardContent>
      </Card>

      <Box sx={{ display: "grid", gridTemplateColumns: selectedJob ? { xs: "1fr", md: "1fr 1fr" } : "1fr", gap: 2 }}>
        {/* Jobs Table */}
        <Card>
          <CardContent sx={{ pb: 0 }}>
            <Typography variant="h6">{translate("aiflow.media.jobsTitle")}</Typography>
          </CardContent>
          {loading ? (
            <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}><CircularProgress /></Box>
          ) : (
            <>
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>{translate("aiflow.media.filename")}</TableCell>
                      <TableCell>{translate("aiflow.media.status")}</TableCell>
                      <TableCell>{translate("aiflow.media.provider")}</TableCell>
                      <TableCell>{translate("aiflow.media.duration")}</TableCell>
                      <TableCell>{translate("aiflow.media.actions")}</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {jobs.map((job) => (
                      <TableRow key={job.id} hover selected={selectedJob?.id === job.id}>
                        <TableCell><Typography variant="body2" fontWeight={500}>{job.filename}</Typography></TableCell>
                        <TableCell><Chip label={job.status} size="small" color={statusColor(job.status)} /></TableCell>
                        <TableCell>{job.stt_provider}</TableCell>
                        <TableCell>{job.duration_seconds ? `${job.duration_seconds.toFixed(1)}s` : "—"}</TableCell>
                        <TableCell>
                          <Stack direction="row" spacing={0.5}>
                            {job.status === "completed" && (
                              <IconButton size="small" title="View" onClick={() => setSelectedJob(job)}><VisibilityIcon fontSize="small" /></IconButton>
                            )}
                            <IconButton size="small" color="error" title="Delete" onClick={() => handleDelete(job.id)}><DeleteIcon fontSize="small" /></IconButton>
                          </Stack>
                        </TableCell>
                      </TableRow>
                    ))}
                    {jobs.length === 0 && (
                      <TableRow><TableCell colSpan={5} align="center"><Typography color="text.secondary" py={3}>{translate("aiflow.media.noJobs")}</Typography></TableCell></TableRow>
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
              <TablePagination component="div" count={total} page={page} onPageChange={(_, p) => setPage(p)} rowsPerPage={50} onRowsPerPageChange={() => {}} rowsPerPageOptions={[50]} />
            </>
          )}
        </Card>

        {/* Transcript Viewer */}
        {selectedJob && (
          <Card>
            <CardContent>
              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                <Typography variant="h6">{translate("aiflow.media.transcript")}</Typography>
                <Chip label={selectedJob.stt_provider} size="small" variant="outlined" />
              </Stack>
              {selectedJob.processing_time_ms && (
                <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
                  {translate("aiflow.media.processingTime")}: {(selectedJob.processing_time_ms / 1000).toFixed(1)}s
                </Typography>
              )}
              {selectedJob.error && (
                <Alert severity="error" sx={{ mb: 2 }}>{selectedJob.error}</Alert>
              )}
              {selectedJob.transcript_raw && (
                <Box sx={{ maxHeight: 500, overflow: "auto", bgcolor: "background.default", p: 2, borderRadius: 1 }}>
                  <Typography variant="body2" sx={{ whiteSpace: "pre-wrap", fontFamily: "monospace", fontSize: 13 }}>
                    {selectedJob.transcript_raw}
                  </Typography>
                </Box>
              )}
              {!selectedJob.transcript_raw && !selectedJob.error && (
                <Typography color="text.secondary">{translate("aiflow.media.noTranscript")}</Typography>
              )}
            </CardContent>
          </Card>
        )}
      </Box>
    </Box>
  );
};
