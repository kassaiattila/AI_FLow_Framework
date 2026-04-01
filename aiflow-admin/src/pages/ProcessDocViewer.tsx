import { useState, useRef, useEffect, useCallback } from "react";
import { useTranslate, Title, useNotify } from "react-admin";
import {
  Card, CardContent, TextField, Button, Typography, CircularProgress,
  Alert, Chip, Box, Paper, Stack, useTheme,
  Table, TableHead, TableBody, TableRow, TableCell, TableContainer,
  IconButton, Dialog, DialogTitle, DialogContent, DialogActions,
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import DownloadIcon from "@mui/icons-material/Download";
import VisibilityIcon from "@mui/icons-material/Visibility";
import mermaid from "mermaid";
import { PipelineProgress, type PipelineStep } from "../components/PipelineProgress";

interface ReviewResult {
  score: number;
  is_acceptable: boolean;
  completeness_score: number;
  logic_score: number;
  actors_score: number;
  decisions_score: number;
  issues: string[];
  suggestions: string[];
  reasoning: string;
}

interface GenerateResult {
  doc_id: string;
  user_input: string;
  review?: ReviewResult;
  mermaid_code: string;
  created_at: string;
  source: "backend" | "subprocess" | "demo";
}

const PIPELINE_STEPS: PipelineStep[] = [
  { name: "Classify", estimated_ms: 2000, description: "Input kategorizalas" },
  { name: "Elaborate", estimated_ms: 3000, description: "Reszletes lepesek kibontas" },
  { name: "Extract", estimated_ms: 4000, description: "BPMN strukturalt kinyeres" },
  { name: "Review", estimated_ms: 3000, description: "Minoseg ellenorzes" },
  { name: "Generate", estimated_ms: 4000, description: "Mermaid diagram generalas" },
  { name: "Export", estimated_ms: 2000, description: "SVG + DrawIO + Markdown" },
];

const PRESETS = [
  { key: "invoice", text: "Szamla feldolgozasi folyamat: az ugyfél PDF szamlat told fel, a rendszer kiolvassa az adatokat (szallito, osszeg, tetelsorok), validalja, es CSV-be exportalja." },
  { key: "support", text: "Ugyfelszolgalati email feldolgozas: email erkezik, a rendszer felismeri a szandekot (reklamacio, kerdes, lemondas), kinyeri az entitasokat (szerzodessszam, nev), es a megfelelo osztalyra iranyitja." },
  { key: "onboarding", text: "Uj ugyfél onboarding folyamat: regisztracio, dokumentumok bekeres (szemelyi, lakcimkartya), azonossag ellenorzes, szerzodes generalas, digitalis alairas, aktivacio." },
];

interface SavedDiagram {
  id: string;
  user_input: string;
  mermaid_code: string;
  review?: ReviewResult | null;
  export_formats: string[];
  created_at: string;
  source: string;
}

export const ProcessDocViewer = () => {
  const translate = useTranslate();
  const notify = useNotify();
  const muiTheme = useTheme();
  const themeMode = muiTheme.palette.mode;
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<GenerateResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [savedDiagrams, setSavedDiagrams] = useState<SavedDiagram[]>([]);
  const [deleteDialogId, setDeleteDialogId] = useState<string | null>(null);
  const diagramRef = useRef<HTMLDivElement>(null);

  const fetchSavedDiagrams = useCallback(async () => {
    try {
      const res = await fetch("/api/v1/diagrams");
      if (res.ok) {
        const data = await res.json();
        setSavedDiagrams(data.diagrams || []);
      }
    } catch { /* ignore */ }
  }, []);

  useEffect(() => { fetchSavedDiagrams(); }, [fetchSavedDiagrams]);

  // Re-initialize mermaid when theme changes
  useEffect(() => {
    mermaid.initialize({
      startOnLoad: false,
      theme: themeMode === "dark" ? "dark" : "default",
      securityLevel: "loose",
      suppressErrorRendering: true,
    });
  }, [themeMode]);

  const handleGenerate = async (overrideInput?: string) => {
    const text = overrideInput || input.trim();
    if (!text) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      // Use the new persisting endpoint (F4a)
      const res = await fetch("/api/v1/diagrams/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_input: overrideInput || input }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || body?.error || `HTTP ${res.status}`);
      }
      const data = await res.json();
      setResult({ ...data, source: data.source || "backend" });
      fetchSavedDiagrams(); // Refresh the saved list
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteDiagram = async () => {
    if (!deleteDialogId) return;
    try {
      await fetch(`/api/v1/diagrams/${deleteDialogId}`, { method: "DELETE" });
      notify(translate("aiflow.processDocs.deleted"), { type: "success" });
      setDeleteDialogId(null);
      fetchSavedDiagrams();
    } catch {
      notify("Delete failed", { type: "error" });
    }
  };

  const handleExport = async (diagramId: string, fmt: string) => {
    try {
      const res = await fetch(`/api/v1/diagrams/${diagramId}/export/${fmt}`);
      if (!res.ok) throw new Error("Export failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `diagram-${diagramId.slice(0, 8)}.${fmt === "mermaid" ? "mmd" : fmt}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      notify("Export failed", { type: "error" });
    }
  };

  const handleViewSaved = (diagram: SavedDiagram) => {
    setResult({
      doc_id: diagram.id,
      user_input: diagram.user_input,
      mermaid_code: diagram.mermaid_code,
      review: diagram.review || undefined,
      created_at: diagram.created_at,
      source: (diagram.source as GenerateResult["source"]) || "backend",
    });
    setInput(diagram.user_input);
  };

  useEffect(() => {
    if (!result?.mermaid_code || !diagramRef.current) return;
    const el = diagramRef.current;
    let cancelled = false;
    el.innerHTML = "";

    // Mermaid 11.x render API: render(id, code) where id is a unique render key
    const renderId = `mermaid-render-${Date.now()}`;

    mermaid
      .render(renderId, result.mermaid_code)
      .then(({ svg }) => {
        if (cancelled) return;
        el.innerHTML = svg;
        const svgEl = el.querySelector("svg");
        if (svgEl) {
          svgEl.style.maxWidth = "100%";
          svgEl.style.height = "auto";
        }
      })
      .catch((err) => {
        if (cancelled) return;
        // Show the raw code as fallback with the error
        const errMsg = err instanceof Error ? err.message : String(err);
        el.innerHTML = `<div style="text-align:left;overflow:auto;padding:16px"><p style="color:#ef4444;margin-bottom:8px;font-size:13px">Mermaid syntax error: ${errMsg.replace(/</g, "&lt;")}</p><pre style="font-size:12px;white-space:pre-wrap">${result.mermaid_code.replace(/</g, "&lt;")}</pre></div>`;
      });

    return () => { cancelled = true; };
  }, [result?.mermaid_code, themeMode]);

  const review = result?.review;

  return (
    <Box sx={{ p: 2, maxWidth: 1600, mx: "auto" }}>
      <Title title={translate("aiflow.processDocs.title")} />

      {/* Split view: input left (35%) + result right (65%) when result exists */}
      <Box sx={{ display: "grid", gridTemplateColumns: result ? { xs: "1fr", md: "35% 65%" } : "1fr", gap: 2 }}>

        {/* Left: Input panel */}
        <Box>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                {translate("aiflow.processDocs.inputLabel")}
              </Typography>
              <TextField
                multiline
                minRows={result ? 8 : 4}
                maxRows={16}
                fullWidth
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={translate("aiflow.processDocs.placeholder")}
                disabled={loading}
              />
              <Button
                variant="contained"
                onClick={() => handleGenerate()}
                disabled={loading || !input.trim()}
                sx={{ mt: 2 }}
                fullWidth
              >
                {loading && <CircularProgress size={20} sx={{ mr: 1 }} />}
                {translate("aiflow.processDocs.generate")}
              </Button>

              {/* Preset buttons */}
              <Box sx={{ mt: 2 }}>
                <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5, display: "block" }}>
                  {translate("aiflow.processDocs.presets")}
                </Typography>
                <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                  {PRESETS.map((p) => (
                    <Chip
                      key={p.key}
                      label={translate(`aiflow.processDocs.preset_${p.key}`)}
                      variant="outlined"
                      size="small"
                      onClick={() => { setInput(p.text); }}
                      sx={{ cursor: "pointer" }}
                    />
                  ))}
                </Stack>
              </Box>

              {/* Refine buttons — shown below input when result exists */}
              {result && (
                <Stack direction="row" spacing={1} sx={{ mt: 2 }} flexWrap="wrap" useFlexGap>
                  <Button variant="outlined" size="small" onClick={() => handleGenerate(input + "\n\nKerlek, reszletesebb lepesekre bontva, tobb dontes ponttal.")} disabled={loading}>
                    {translate("aiflow.processDocs.moreDetail")}
                  </Button>
                  <Button variant="outlined" size="small" onClick={() => handleGenerate(input + "\n\nKerlek, egyszerubb, kevesebb lepessel.")} disabled={loading}>
                    {translate("aiflow.processDocs.simpler")}
                  </Button>
                  <Button variant="outlined" size="small" onClick={() => handleGenerate()} disabled={loading}>
                    {translate("aiflow.processDocs.regenerate")}
                  </Button>
                </Stack>
              )}
            </CardContent>
          </Card>

          {/* Pipeline progress */}
          {loading && (
            <Card sx={{ mt: 2 }}>
              <CardContent>
                <PipelineProgress steps={PIPELINE_STEPS} running={loading} completed={!!result} />
              </CardContent>
            </Card>
          )}

          {error && (
            <Alert severity="error" sx={{ mt: 2 }} action={
              <Button color="inherit" size="small" onClick={() => handleGenerate()}>
                {translate("aiflow.pipeline.retry")}
              </Button>
            }>
              {error}
            </Alert>
          )}
        </Box>

        {/* Right: Result panel */}
        {result && (
          <Box>
            <Chip
              label={translate(`aiflow.status.${result.source === "subprocess" ? "subprocess" : result.source}`)}
              color={result.source === "demo" ? "warning" : "success"}
              size="small"
              sx={{ mb: 1 }}
            />

            {/* Mermaid diagram */}
            <Card sx={{ mb: 2 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  {translate("aiflow.processDocs.diagram")}
                </Typography>
                <Paper
                  ref={diagramRef}
                  sx={{ p: 2, overflow: "auto", bgcolor: "background.default", textAlign: "center", minHeight: 300 }}
                />
              </CardContent>
            </Card>

            {/* Review */}
            {review && (
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    {translate("aiflow.processDocs.review")}
                  </Typography>
                  <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: 1 }}>
                    <Chip label={`Score: ${review.score}/10`} color={review.is_acceptable ? "success" : "warning"} />
                    <Chip label={`Completeness: ${review.completeness_score}`} variant="outlined" size="small" />
                    <Chip label={`Logic: ${review.logic_score}`} variant="outlined" size="small" />
                    <Chip label={`Actors: ${review.actors_score}`} variant="outlined" size="small" />
                    <Chip label={`Decisions: ${review.decisions_score}`} variant="outlined" size="small" />
                  </Stack>
                  {review.issues.length > 0 && (
                    <Box sx={{ mt: 1 }}>
                      <Typography variant="subtitle2" color="error">{translate("aiflow.processDocs.issues")}</Typography>
                      {review.issues.map((issue, i) => (
                        <Typography key={i} variant="body2">- {issue}</Typography>
                      ))}
                    </Box>
                  )}
                  {review.suggestions.length > 0 && (
                    <Box sx={{ mt: 1 }}>
                      <Typography variant="subtitle2" color="info.main">{translate("aiflow.processDocs.suggestions")}</Typography>
                      {review.suggestions.map((s, i) => (
                        <Typography key={i} variant="body2">- {s}</Typography>
                      ))}
                    </Box>
                  )}
                </CardContent>
              </Card>
            )}
          </Box>
        )}
      </Box>

      {/* Saved Diagrams Section */}
      {savedDiagrams.length > 0 && (
        <Card sx={{ mt: 3 }}>
          <CardContent sx={{ pb: 0 }}>
            <Stack direction="row" justifyContent="space-between" alignItems="center">
              <Typography variant="h6">{translate("aiflow.processDocs.savedDiagrams")}</Typography>
              <Typography variant="body2" color="text.secondary">
                {savedDiagrams.length} {savedDiagrams.length === 1 ? "diagram" : "diagrams"}
              </Typography>
            </Stack>
          </CardContent>
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>{translate("aiflow.processDocs.savedDescription")}</TableCell>
                  <TableCell>{translate("aiflow.processDocs.savedScore")}</TableCell>
                  <TableCell>{translate("aiflow.processDocs.savedCreated")}</TableCell>
                  <TableCell>{translate("aiflow.processDocs.savedActions")}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {savedDiagrams.map((d) => (
                  <TableRow key={d.id} hover>
                    <TableCell sx={{ maxWidth: 400, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {d.user_input.slice(0, 80)}{d.user_input.length > 80 ? "..." : ""}
                    </TableCell>
                    <TableCell>
                      {d.review?.score != null && (
                        <Chip label={`${d.review.score}/10`} size="small" color={d.review.score >= 7 ? "success" : "warning"} />
                      )}
                    </TableCell>
                    <TableCell>{new Date(d.created_at).toLocaleDateString()}</TableCell>
                    <TableCell>
                      <Stack direction="row" spacing={0.5}>
                        <IconButton size="small" title="View" onClick={() => handleViewSaved(d)}><VisibilityIcon fontSize="small" /></IconButton>
                        <IconButton size="small" title="Export SVG" onClick={() => handleExport(d.id, "svg")}><DownloadIcon fontSize="small" /></IconButton>
                        <IconButton size="small" title="Delete" color="error" onClick={() => setDeleteDialogId(d.id)}><DeleteIcon fontSize="small" /></IconButton>
                      </Stack>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Card>
      )}

      {/* Delete Confirm Dialog */}
      <Dialog open={!!deleteDialogId} onClose={() => setDeleteDialogId(null)}>
        <DialogTitle>{translate("aiflow.processDocs.deleteTitle")}</DialogTitle>
        <DialogContent>
          <Typography>{translate("aiflow.processDocs.deleteConfirm")}</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogId(null)}>{translate("ra.action.cancel")}</Button>
          <Button variant="contained" color="error" onClick={handleDeleteDiagram}>{translate("ra.action.delete")}</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};
