import { useState, useRef, useEffect } from "react";
import { useTranslate, Title } from "react-admin";
import {
  Card, CardContent, TextField, Button, Typography, CircularProgress,
  Alert, Chip, Box, Paper, Stack, useTheme,
} from "@mui/material";
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
  { name: "Folyamat elemzes", estimated_ms: 2500, description: "NL → strukturalt elemzes" },
  { name: "BPMN generalas", estimated_ms: 2000, description: "Swimlane diagram" },
  { name: "Mermaid kod", estimated_ms: 900, description: "Flowchart generalas" },
  { name: "Rendereles", estimated_ms: 1600, description: "SVG + DrawIO" },
];

const PRESETS = [
  { key: "invoice", text: "Szamla feldolgozasi folyamat: az ugyfél PDF szamlat told fel, a rendszer kiolvassa az adatokat (szallito, osszeg, tetelsorok), validalja, es CSV-be exportalja." },
  { key: "support", text: "Ugyfelszolgalati email feldolgozas: email erkezik, a rendszer felismeri a szandekot (reklamacio, kerdes, lemondas), kinyeri az entitasokat (szerzodessszam, nev), es a megfelelo osztalyra iranyitja." },
  { key: "onboarding", text: "Uj ugyfél onboarding folyamat: regisztracio, dokumentumok bekeres (szemelyi, lakcimkartya), azonossag ellenorzes, szerzodes generalas, digitalis alairas, aktivacio." },
];

export const ProcessDocViewer = () => {
  const translate = useTranslate();
  const muiTheme = useTheme();
  const themeMode = muiTheme.palette.mode;
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<GenerateResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const diagramRef = useRef<HTMLDivElement>(null);

  // Re-initialize mermaid when theme changes
  useEffect(() => {
    mermaid.initialize({ startOnLoad: false, theme: themeMode === "dark" ? "dark" : "default" });
  }, [themeMode]);

  const handleGenerate = async (overrideInput?: string) => {
    const text = overrideInput || input.trim();
    if (!text) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch("/api/process-docs/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_input: overrideInput || input }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.error || `HTTP ${res.status}`);
      }
      setResult(await res.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!result?.mermaid_code || !diagramRef.current) return;
    const el = diagramRef.current;
    let cancelled = false;
    el.innerHTML = "";

    // Create a dedicated container for mermaid (it needs an element in the DOM)
    const container = document.createElement("div");
    container.id = `mermaid-${Date.now()}`;
    el.appendChild(container);

    mermaid
      .render(container.id, result.mermaid_code)
      .then(({ svg }) => {
        if (cancelled) return;
        el.innerHTML = svg;
        // Ensure SVG scales to container
        const svgEl = el.querySelector("svg");
        if (svgEl) {
          svgEl.style.maxWidth = "100%";
          svgEl.style.height = "auto";
        }
      })
      .catch(() => {
        if (cancelled) return;
        el.innerHTML = `<pre style="text-align:left;overflow:auto;font-size:12px;padding:16px">${result.mermaid_code}</pre>`;
      });

    return () => { cancelled = true; };
  }, [result?.mermaid_code, themeMode]);

  const review = result?.review;

  return (
    <Box sx={{ p: 3, maxWidth: 1200, mx: "auto" }}>
      <Title title={translate("aiflow.processDocs.title")} />

      {/* Input form */}
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            {translate("aiflow.processDocs.inputLabel")}
          </Typography>
          <TextField
            multiline
            minRows={4}
            maxRows={12}
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
          >
            {loading && <CircularProgress size={20} sx={{ mr: 1 }} />}
            {translate("aiflow.processDocs.generate")}
          </Button>

          {/* Preset buttons (Pattern #4: Prompt Presets) */}
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
        </CardContent>
      </Card>

      {/* Pipeline progress (visible during generation) */}
      {loading && (
        <Card sx={{ mb: 2 }}>
          <CardContent>
            <PipelineProgress
              steps={PIPELINE_STEPS}
              running={loading}
              completed={!!result}
            />
          </CardContent>
        </Card>
      )}

      {error && (
        <Alert
          severity="error"
          sx={{ mb: 2 }}
          action={
            <Button color="inherit" size="small" onClick={() => handleGenerate()}>
              {translate("aiflow.pipeline.retry")}
            </Button>
          }
        >
          {error}
        </Alert>
      )}

      {result && (
        <>
          <Chip
            label={translate(`aiflow.status.${result.source === "subprocess" ? "subprocess" : result.source}`)}
            color={result.source === "demo" ? "warning" : "success"}
            size="small"
            sx={{ mb: 2 }}
          />

          {/* Mermaid diagram */}
          <Card sx={{ mb: 2 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                {translate("aiflow.processDocs.diagram")}
              </Typography>
              <Paper
                ref={diagramRef}
                sx={{ p: 2, overflow: "auto", bgcolor: "background.default", textAlign: "center", minHeight: 200 }}
              />
              {/* Refine Output buttons (Pattern #1) */}
              <Stack direction="row" spacing={1} sx={{ mt: 2 }}>
                <Button
                  variant="outlined"
                  size="small"
                  onClick={() => handleGenerate(input + "\n\nKerlek, reszletesebb lepesekre bontva, tobb dontes ponttal.")}
                  disabled={loading}
                >
                  {translate("aiflow.processDocs.moreDetail")}
                </Button>
                <Button
                  variant="outlined"
                  size="small"
                  onClick={() => handleGenerate(input + "\n\nKerlek, egyszerubb, kevesebb lepessel.")}
                  disabled={loading}
                >
                  {translate("aiflow.processDocs.simpler")}
                </Button>
                <Button
                  variant="outlined"
                  size="small"
                  onClick={() => handleGenerate()}
                  disabled={loading}
                >
                  {translate("aiflow.processDocs.regenerate")}
                </Button>
              </Stack>
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
                    <Typography variant="subtitle2" color="error">
                      {translate("aiflow.processDocs.issues")}
                    </Typography>
                    {review.issues.map((issue, i) => (
                      <Typography key={i} variant="body2">- {issue}</Typography>
                    ))}
                  </Box>
                )}
                {review.suggestions.length > 0 && (
                  <Box sx={{ mt: 1 }}>
                    <Typography variant="subtitle2" color="info.main">
                      {translate("aiflow.processDocs.suggestions")}
                    </Typography>
                    {review.suggestions.map((s, i) => (
                      <Typography key={i} variant="body2">- {s}</Typography>
                    ))}
                  </Box>
                )}
              </CardContent>
            </Card>
          )}
        </>
      )}
    </Box>
  );
};
