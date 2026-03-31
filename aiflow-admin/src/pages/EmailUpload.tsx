import { useState, useRef } from "react";
import { useTranslate, Title } from "react-admin";
import {
  Card, CardContent, Typography, Button, CircularProgress,
  Alert, Chip, Box, Stack, Paper,
} from "@mui/material";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import { PipelineProgress, type PipelineStep } from "../components/PipelineProgress";

const EMAIL_PIPELINE: PipelineStep[] = [
  { name: "Email parse", estimated_ms: 300, description: "Header + body + attachments" },
  { name: "ML classify", estimated_ms: 50, description: "sklearn TF-IDF" },
  { name: "LLM classify", estimated_ms: 3000, description: "GPT finomhangolas" },
  { name: "Entity extraction", estimated_ms: 700, description: "NER kinyeres" },
  { name: "Routing", estimated_ms: 300, description: "Osztaly + prioritas" },
];

interface UploadResult {
  uploaded: number;
  files: string[];
  errors: string[];
}

interface ProcessResult {
  file: string;
  source: string;
  intent?: { intent_display_name: string; confidence: number } | null;
  priority?: { priority_display_name: string } | null;
  error?: string;
  stdout?: string;
}

export const EmailUpload = () => {
  const translate = useTranslate();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);
  const [processResults, setProcessResults] = useState<ProcessResult[]>([]);
  const [error, setError] = useState<string | null>(null);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    setUploading(true);
    setError(null);
    setUploadResult(null);
    setProcessResults([]);

    const formData = new FormData();
    for (const file of Array.from(files)) {
      formData.append("files", file);
    }

    try {
      const res = await fetch("/api/v1/emails/upload", { method: "POST", body: formData });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.error || `HTTP ${res.status}`);
      }
      setUploadResult(await res.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleProcessAll = async () => {
    if (!uploadResult?.files.length) return;

    setProcessing(true);
    setError(null);
    setProcessResults([]);

    const results: ProcessResult[] = [];
    for (const file of uploadResult.files) {
      try {
        const res = await fetch("/api/v1/emails/process", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ file }),
        });
        const data = await res.json();
        results.push({ file, ...data });
      } catch (e) {
        results.push({ file, source: "error", error: e instanceof Error ? e.message : "Failed" });
      }
      // Update results progressively
      setProcessResults([...results]);
    }

    setProcessing(false);
  };

  return (
    <Box sx={{ p: 3, maxWidth: 1200, mx: "auto" }}>
      <Title title={translate("aiflow.emailUpload.title")} />
      <Typography variant="h6" sx={{ mb: 2 }}>{translate("aiflow.emailUpload.title")}</Typography>

      {/* Upload area */}
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <input
            ref={fileInputRef}
            type="file"
            accept=".eml,.msg,.txt"
            multiple
            style={{ display: "none" }}
            onChange={handleUpload}
          />
          <Paper
            sx={{
              p: 4, textAlign: "center", cursor: "pointer",
              border: "2px dashed", borderColor: "divider",
              "&:hover": { borderColor: "primary.main" },
            }}
            onClick={() => fileInputRef.current?.click()}
          >
            {uploading ? (
              <CircularProgress />
            ) : (
              <>
                <CloudUploadIcon sx={{ fontSize: 48, color: "text.secondary" }} />
                <Typography color="text.secondary">
                  {translate("aiflow.emailUpload.dropzone")}
                </Typography>
                <Typography variant="caption" color="text.secondary">.eml, .msg, .txt</Typography>
              </>
            )}
          </Paper>
        </CardContent>
      </Card>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {/* Upload result */}
      {uploadResult && (
        <Card sx={{ mb: 2 }}>
          <CardContent>
            <Typography variant="subtitle1" gutterBottom>
              {translate("aiflow.emailUpload.uploaded")}: {uploadResult.uploaded}
            </Typography>
            <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap sx={{ mb: 1 }}>
              {uploadResult.files.map((f) => (
                <Chip key={f} label={f} size="small" />
              ))}
            </Stack>
            {uploadResult.errors.length > 0 && (
              <Alert severity="warning" sx={{ mb: 1 }}>
                {uploadResult.errors.join(", ")}
              </Alert>
            )}
            <Button
              variant="contained"
              onClick={handleProcessAll}
              disabled={processing || uploadResult.files.length === 0}
              sx={{ mt: 1 }}
            >
              {processing && <CircularProgress size={20} sx={{ mr: 1 }} />}
              {translate("aiflow.emailUpload.process")}
            </Button>
            {processing && (
              <Box sx={{ mt: 2 }}>
                <PipelineProgress
                  steps={EMAIL_PIPELINE}
                  running={processing}
                  completed={processResults.length >= (uploadResult?.files.length || 0)}
                />
              </Box>
            )}
          </CardContent>
        </Card>
      )}

      {/* Process results */}
      {processResults.length > 0 && (
        <Card>
          <CardContent>
            <Typography variant="subtitle1" gutterBottom>
              {translate("aiflow.emailUpload.results")}
            </Typography>
            <Stack spacing={1}>
              {processResults.map((r) => (
                <Paper key={r.file} variant="outlined" sx={{ p: 1.5 }}>
                  <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
                    <Chip
                      label={r.error ? "FAIL" : "OK"}
                      color={r.error ? "error" : "success"}
                      size="small"
                    />
                    <Typography variant="body2" fontWeight="bold">{r.file}</Typography>
                    {r.source && (
                      <Chip label={r.source} size="small" variant="outlined" />
                    )}
                    {r.intent && (
                      <Chip
                        label={`${r.intent.intent_display_name} (${(r.intent.confidence * 100).toFixed(0)}%)`}
                        size="small"
                        color="primary"
                      />
                    )}
                    {r.priority && (
                      <Chip label={r.priority.priority_display_name} size="small" color="warning" />
                    )}
                    {r.error && (
                      <Typography variant="body2" color="error">{r.error}</Typography>
                    )}
                  </Stack>
                </Paper>
              ))}
            </Stack>
          </CardContent>
        </Card>
      )}
    </Box>
  );
};
