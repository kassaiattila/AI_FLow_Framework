import { useState, useRef, useEffect } from "react";
import { useTranslate, Title } from "react-admin";
import {
  Card, CardContent, Typography, Button, CircularProgress,
  Alert, Chip, Box, Stack, Paper, LinearProgress,
} from "@mui/material";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ErrorIcon from "@mui/icons-material/Error";
import HourglassEmptyIcon from "@mui/icons-material/HourglassEmpty";
import VerifiedIcon from "@mui/icons-material/Verified";
import RestartAltIcon from "@mui/icons-material/RestartAlt";
import { useNavigate } from "react-router-dom";
import { PipelineProgress, type PipelineStep } from "../components/PipelineProgress";

const DOCUMENT_PIPELINE: PipelineStep[] = [
  { name: "PDF parse", description: "Docling inicializacio + parse" },
  { name: "Classify", description: "Irany felismeres" },
  { name: "Field extraction", description: "LLM header + tetelek" },
  { name: "Validation", description: "Ellenorzes" },
  { name: "Store", description: "DB mentes" },
  { name: "Export", description: "CSV/JSON/Excel" },
];

interface UploadResult {
  uploaded: string[];   // filenames returned by API
  count: number;
  files: string[];      // computed alias for uploaded
  errors: string[];
}

interface ProcessedFile {
  file: string;
  success: boolean;
  confidence: number;
  run_id: string;
  pages: number;
  error?: string;
}

type FileStatus = "pending" | "processing" | "done" | "error";

export const DocumentUpload = () => {
  const translate = useTranslate();
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);
  const [fileStatuses, setFileStatuses] = useState<Map<string, FileStatus>>(new Map());
  const [processResults, setProcessResults] = useState<Map<string, ProcessedFile>>(new Map());
  const [currentFileIndex, setCurrentFileIndex] = useState(-1);
  const [stepProgress, setStepProgress] = useState<Map<string, number>>(new Map());
  const [stepTimings, setStepTimings] = useState<Map<string, number[]>>(new Map());
  const [error, setError] = useState<string | null>(null);
  const [apiOnline, setApiOnline] = useState<boolean | null>(null);

  // Check API health on mount
  useEffect(() => {
    fetch("/health")
      .then((r) => r.json())
      .then(() => setApiOnline(true))
      .catch(() => setApiOnline(false));
  }, []);

  // Restore state from sessionStorage on mount
  useEffect(() => {
    try {
      const saved = sessionStorage.getItem("aiflow_documentUpload");
      if (saved) {
        const s = JSON.parse(saved);
        if (s.uploadResult) setUploadResult(s.uploadResult);
        if (s.fileStatuses) setFileStatuses(new Map(Object.entries(s.fileStatuses)));
        if (s.processResults) setProcessResults(new Map(Object.entries(s.processResults)));
      }
    } catch { /* ignore corrupt data */ }
  }, []);

  // Persist state to sessionStorage on change
  useEffect(() => {
    if (!uploadResult) { sessionStorage.removeItem("aiflow_documentUpload"); return; }
    sessionStorage.setItem("aiflow_documentUpload", JSON.stringify({
      uploadResult,
      fileStatuses: Object.fromEntries(fileStatuses),
      processResults: Object.fromEntries(processResults),
    }));
  }, [uploadResult, fileStatuses, processResults]);

  const handleReset = () => {
    setUploadResult(null);
    setFileStatuses(new Map());
    setProcessResults(new Map());
    setStepProgress(new Map());
    setStepTimings(new Map());
    setCurrentFileIndex(-1);
    setError(null);
    sessionStorage.removeItem("aiflow_documentUpload");
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    setUploading(true);
    setError(null);
    setUploadResult(null);
    setProcessResults(new Map());
    setFileStatuses(new Map());

    const formData = new FormData();
    for (const file of Array.from(files)) formData.append("files", file);

    try {
      const res = await fetch("/api/v1/documents/upload", { method: "POST", body: formData });
      if (!res.ok) throw new Error((await res.json().catch(() => null))?.error || `HTTP ${res.status}`);
      const raw = await res.json();
      // API returns {uploaded: string[], count: number} — normalize to UploadResult
      const result: UploadResult = {
        uploaded: raw.uploaded || [],
        count: raw.count || 0,
        files: Array.isArray(raw.uploaded) ? raw.uploaded : (raw.files || []),
        errors: raw.errors || [],
      };
      setUploadResult(result);
      const statuses = new Map<string, FileStatus>();
      result.files.forEach((f) => statuses.set(f, "pending"));
      setFileStatuses(statuses);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  // Per-file sequential processing via SSE stream (real progress)
  const handleProcess = async () => {
    if (!uploadResult?.files.length) return;
    setProcessing(true);
    setError(null);
    const results = new Map<string, ProcessedFile>();

    for (let i = 0; i < uploadResult.files.length; i++) {
      const file = uploadResult.files[i];
      setCurrentFileIndex(i);
      setFileStatuses((prev) => new Map(prev).set(file, "processing"));
      setStepProgress((prev) => new Map(prev).set(file, 0));
      setStepTimings((prev) => new Map(prev).set(file, []));

      try {
        const res = await fetch("/api/v1/documents/process-stream", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ files: [file] }),
        });

        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const reader = res.body!.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let fileResult: ProcessedFile | null = null;

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });

          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            try {
              const event = JSON.parse(line.slice(6));

              if (event.event === "step_done") {
                setStepProgress((prev) => new Map(prev).set(file, event.step + 1));
                setStepTimings((prev) => {
                  const timings = [...(prev.get(file) || [])];
                  timings[event.step] = event.elapsed_ms;
                  return new Map(prev).set(file, timings);
                });
              } else if (event.event === "complete") {
                const r = event.results?.[0];
                fileResult = {
                  file,
                  success: r ? r.is_valid !== false && !r.error : false,
                  confidence: r?.confidence || 0,
                  run_id: "",
                  pages: 0,
                  error: r?.error || undefined,
                };
              } else if (event.event === "error") {
                fileResult = {
                  file, success: false, confidence: 0, run_id: "", pages: 0,
                  error: event.error || "Processing failed",
                };
              }
            } catch { /* skip malformed SSE lines */ }
          }
        }

        const result = fileResult || { file, success: false, confidence: 0, run_id: "", pages: 0, error: "No result" };
        results.set(file, result);
        setProcessResults(new Map(results));
        setStepProgress((prev) => new Map(prev).set(file, DOCUMENT_PIPELINE.length));
        setFileStatuses((prev) => new Map(prev).set(file, result.success ? "done" : "error"));
      } catch (e) {
        const errResult: ProcessedFile = { file, success: false, confidence: 0, run_id: "", pages: 0, error: e instanceof Error ? e.message : "Failed" };
        results.set(file, errResult);
        setProcessResults(new Map(results));
        setFileStatuses((prev) => new Map(prev).set(file, "error"));
      }
    }

    setCurrentFileIndex(-1);
    setProcessing(false);
  };

  const totalFiles = uploadResult?.files.length || 0;
  const doneFiles = [...fileStatuses.values()].filter((s) => s === "done" || s === "error").length;
  const overallProgress = totalFiles > 0 ? (doneFiles / totalFiles) * 100 : 0;

  return (
    <Box sx={{ p: 3, maxWidth: 1200, mx: "auto" }}>
      <Title title={translate("aiflow.documentUpload.title")} />
      <Typography variant="h6" sx={{ mb: 2 }}>{translate("aiflow.documentUpload.title")}</Typography>

      {apiOnline === false && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          {translate("aiflow.documentUpload.apiOffline")}
        </Alert>
      )}

      {/* Upload area */}
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <input ref={fileInputRef} type="file" accept=".pdf" multiple style={{ display: "none" }} onChange={handleUpload} />
          <Paper
            sx={{
              p: 4, textAlign: "center", cursor: "pointer",
              border: "2px dashed", borderColor: "divider",
              transition: "border-color 0.2s",
              "&:hover": { borderColor: "primary.main", bgcolor: "action.hover" },
            }}
            onClick={() => fileInputRef.current?.click()}
          >
            {uploading ? (
              <CircularProgress />
            ) : (
              <>
                <CloudUploadIcon sx={{ fontSize: 48, color: "text.secondary", mb: 1 }} />
                <Typography color="text.secondary">{translate("aiflow.documentUpload.dropzone")}</Typography>
                <Typography variant="caption" color="text.secondary">PDF, max 20MB</Typography>
              </>
            )}
          </Paper>
        </CardContent>
      </Card>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {/* File list with per-file status */}
      {uploadResult && (
        <Card sx={{ mb: 2 }}>
          <CardContent>
            {/* Batch progress header */}
            <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1.5 }}>
              <Typography variant="subtitle1">
                {translate("aiflow.documentUpload.files")}: {totalFiles} db
              </Typography>
              {processing && (
                <Chip label={`${doneFiles}/${totalFiles} ${translate("aiflow.pipeline.done")}`} color="primary" size="small" />
              )}
            </Stack>

            {/* Overall progress bar */}
            {(processing || doneFiles > 0) && (
              <Box sx={{ mb: 2 }}>
                <LinearProgress
                  variant="determinate"
                  value={overallProgress}
                  sx={{ height: 8, borderRadius: 4, mb: 0.5 }}
                />
                <Typography variant="caption" color="text.secondary">
                  {processing
                    ? `${translate("aiflow.documentUpload.processingFile")} ${currentFileIndex + 1}/${totalFiles}...`
                    : doneFiles === totalFiles ? translate("aiflow.pipeline.done") : ""}
                </Typography>
              </Box>
            )}

            {/* Per-file rows */}
            <Stack spacing={1}>
              {uploadResult.files.map((file) => {
                const status = fileStatuses.get(file) || "pending";
                const result = processResults.get(file);
                const isActive = status === "processing";

                return (
                  <Paper
                    key={file}
                    variant="outlined"
                    sx={{
                      p: 1.5,
                      borderColor: isActive ? "primary.main" : result?.success === false ? "error.main" : "divider",
                      borderWidth: isActive ? 2 : 1,
                    }}
                  >
                    <Stack direction="row" spacing={1} alignItems="center">
                      {/* Status icon */}
                      {status === "done" && <CheckCircleIcon color="success" sx={{ fontSize: 20 }} />}
                      {status === "error" && <ErrorIcon color="error" sx={{ fontSize: 20 }} />}
                      {status === "processing" && <CircularProgress size={18} />}
                      {status === "pending" && <HourglassEmptyIcon sx={{ fontSize: 20, color: "text.disabled" }} />}

                      {/* File name */}
                      <Typography variant="body2" fontWeight={isActive ? 600 : 400} sx={{ flex: 1 }}>
                        {file}
                      </Typography>

                      {/* Result info */}
                      {result?.success && (
                        <>
                          <Chip label={`${(result.confidence * 100).toFixed(0)}%`} size="small" color="success" variant="outlined" />
                          <Typography variant="caption" color="text.secondary">{result.pages} old.</Typography>
                          <Button
                            size="small"
                            startIcon={<VerifiedIcon />}
                            onClick={() => navigate(`/documents/${encodeURIComponent(file)}/verify`)}
                            sx={{ textTransform: "none", fontSize: "0.75rem" }}
                          >
                            {translate("aiflow.verification.verify")}
                          </Button>
                        </>
                      )}
                      {result?.error && (
                        <Typography variant="caption" color="error">{result.error}</Typography>
                      )}
                    </Stack>

                    {/* Per-file pipeline progress */}
                    {(isActive || status === "done") && (
                      <Box sx={{ mt: 1 }}>
                        <PipelineProgress
                          steps={DOCUMENT_PIPELINE}
                          completedSteps={stepProgress.get(file) || 0}
                          running={isActive}
                          completed={status === "done"}
                          stepTimings={stepTimings.get(file) || []}
                        />
                      </Box>
                    )}
                  </Paper>
                );
              })}
            </Stack>

            {/* Process button */}
            {!processing && doneFiles < totalFiles && (
              <Button
                variant="contained"
                onClick={handleProcess}
                disabled={processing}
                fullWidth
                sx={{ mt: 2 }}
              >
                {translate("aiflow.documentUpload.process")} ({totalFiles} {translate("aiflow.documentUpload.files")})
              </Button>
            )}

            {uploadResult.errors.length > 0 && (
              <Alert severity="warning" sx={{ mt: 1 }}>{uploadResult.errors.join(", ")}</Alert>
            )}

            {/* Reset button — always visible when there's an upload result */}
            {!processing && (
              <Button
                variant="outlined"
                color="secondary"
                startIcon={<RestartAltIcon />}
                onClick={handleReset}
                fullWidth
                sx={{ mt: 1 }}
              >
                {translate("aiflow.documentUpload.newBatch")}
              </Button>
            )}
          </CardContent>
        </Card>
      )}
    </Box>
  );
};
