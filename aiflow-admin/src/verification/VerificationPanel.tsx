import { useEffect, useState, useCallback } from "react";
import { useTranslate, Title } from "react-admin";
import { useParams, useNavigate } from "react-router-dom";
import {
  Box, Typography, Chip, Stack, LinearProgress, Button, Paper,
  Divider, Alert, CircularProgress,
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import CheckIcon from "@mui/icons-material/Check";
import RestoreIcon from "@mui/icons-material/Restore";
import SaveIcon from "@mui/icons-material/Save";
import { useVerificationState } from "./use-verification-state";
import { DocumentCanvas } from "./DocumentCanvas";
import { DataPointEditor } from "./DataPointEditor";
import { getAllFields, fieldToBBox, resolvePath } from "./document-layout";
import type { DataPoint, InvoiceVerificationData, DataPointCategory } from "./types";

function generateVerificationData(invoice: Record<string, unknown>, index: number): InvoiceVerificationData {
  const lineItems = (invoice.line_items as unknown[]) || [];
  const fields = getAllFields(lineItems.length);
  const dataPoints: DataPoint[] = fields.map((f) => {
    const value = resolvePath(invoice, f.fieldPath);
    const baseConf = (invoice.extraction_confidence as number) || 0.8;
    const jitter = (Math.sin(f.id.length * 7) * 0.15);
    const confidence = Math.max(0.3, Math.min(1, baseConf + jitter));
    return {
      id: f.id,
      category: f.category as DataPointCategory,
      field_name: f.fieldPath,
      label: f.label,
      labelEn: f.labelEn,
      extracted_value: value,
      current_value: value,
      confidence,
      bounding_box: fieldToBBox(f),
      status: "auto",
      line_item_index: f.lineIndex,
    };
  });

  return {
    invoice_index: index,
    source_file: (invoice.source_file as string) || "",
    document_meta: {
      document_type: "invoice",
      document_type_confidence: 0.97,
      direction: (invoice.direction as "incoming" | "outgoing") || "incoming",
      direction_confidence: 0.94,
      language: "hu",
      language_confidence: 0.99,
    },
    data_points: dataPoints,
    page_dimensions: { width: 595, height: 842 },
  };
}

export const VerificationPanel = () => {
  const translate = useTranslate();
  const navigate = useNavigate();
  const { id: rawId } = useParams<{ id: string }>();
  const id = rawId ? decodeURIComponent(rawId) : null;
  const [invoice, setInvoice] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<"idle" | "saved" | "error">("idle");

  const vs = useVerificationState();

  // Load invoice
  useEffect(() => {
    if (!id) { setLoading(false); return; }
    fetch("/api/documents")
      .then((r) => r.json())
      .then((data) => {
        const docs = (data.documents || []) as Record<string, unknown>[];
        const found = docs.find((d) => d.source_file === id);
        if (found) {
          setInvoice(found);
          const vd = generateVerificationData(found, docs.indexOf(found));
          vs.loadData(vd);
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  // Save handler
  const handleSave = useCallback(async () => {
    setSaving(true);
    setSaveStatus("idle");
    try {
      const corrections: Record<string, string> = {};
      for (const dp of vs.dataPoints) {
        if (dp.status === "corrected") {
          corrections[dp.id] = dp.current_value;
        }
      }
      // Save to localStorage as backup
      localStorage.setItem(`aiflow_verification_${id}`, JSON.stringify({ corrections, confirmed: vs.stats.confirmed }));
      setSaveStatus("saved");
      setTimeout(() => setSaveStatus("idle"), 3000);
    } catch {
      setSaveStatus("error");
    } finally {
      setSaving(false);
    }
  }, [vs.dataPoints, vs.stats.confirmed, id]);

  if (loading) return <Box sx={{ p: 4, textAlign: "center" }}><CircularProgress /></Box>;
  if (!invoice) return <Alert severity="error">Invoice not found: {id}</Alert>;

  const progress = vs.stats.total > 0 ? ((vs.stats.confirmed + vs.stats.corrected) / vs.stats.total) * 100 : 0;

  return (
    <Box sx={{ p: 2, maxWidth: 1400, mx: "auto", display: "flex", flexDirection: "column", height: "calc(100vh - 64px)" }}>
      <Title title={`${translate("aiflow.verification.title")} — ${id}`} />

      {/* Header — Row 1: navigation */}
      <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 0.5 }}>
        <Button startIcon={<ArrowBackIcon />} onClick={() => navigate("/invoices")} size="small">
          {translate("ra.action.back")}
        </Button>
        <Typography variant="h6" sx={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {id}
        </Typography>
        <Button
          startIcon={<InfoOutlinedIcon />}
          onClick={() => navigate(`/invoices/${encodeURIComponent(id!)}/show`)}
          size="small"
          variant="outlined"
          color="inherit"
        >
          {translate("ra.message.details")}
        </Button>
      </Stack>

      {/* Header — Row 2: meta chips + stats + progress */}
      <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1.5 }}>
        {vs.documentMeta && (
          <>
            <Chip label={vs.documentMeta.document_type} size="small" />
            <Chip label={vs.documentMeta.direction} size="small" variant="outlined" />
            <Divider orientation="vertical" flexItem />
          </>
        )}
        <Chip label={`Auto: ${vs.stats.auto}`} size="small" variant="outlined" />
        <Chip label={`${translate("aiflow.verification.corrected")}: ${vs.stats.corrected}`} size="small" variant="outlined" color="info" />
        <Chip label={`OK: ${vs.stats.confirmed}`} size="small" variant="outlined" color="success" />
        <LinearProgress
          variant="determinate"
          value={progress}
          sx={{ flex: 1, height: 6, borderRadius: 3, ml: 1 }}
        />
        <Typography variant="caption" color="text.secondary" sx={{ whiteSpace: "nowrap" }}>
          {Math.round(progress)}%
        </Typography>
      </Stack>

      {/* Side-by-side layout — fills remaining space */}
      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "55% 45%" }, gap: 2, flex: 1, minHeight: 0, overflow: "hidden" }}>
        {/* Left: Document Canvas */}
        <DocumentCanvas
          invoice={invoice}
          dataPoints={vs.dataPoints}
          hoveredPointId={vs.hoveredPointId}
          selectedPointId={vs.selectedPointId}
          onHoverPoint={vs.hoverPoint}
          onSelectPoint={vs.selectPoint}
        />

        {/* Right: Data Point Editor */}
        <DataPointEditor
          dataPoints={vs.dataPoints}
          hoveredPointId={vs.hoveredPointId}
          selectedPointId={vs.selectedPointId}
          editingPointId={vs.editingPointId}
          editBuffer={vs.editBuffer}
          onHoverPoint={vs.hoverPoint}
          onSelectPoint={vs.selectPoint}
          onStartEdit={vs.startEdit}
          onEditChange={vs.editChange}
          onCommitEdit={vs.commitEdit}
          onCancelEdit={vs.cancelEdit}
          onConfirmPoint={vs.confirmPoint}
          onNextPoint={vs.nextPoint}
          onPrevPoint={vs.prevPoint}
        />
      </Box>

      {/* Sticky action bar — always visible */}
      <Paper
        variant="outlined"
        sx={{
          p: 1, mt: 1,
          position: "sticky", bottom: 0, zIndex: 10,
          bgcolor: "background.paper",
          borderTop: 2, borderColor: "divider",
        }}
      >
        <Stack direction="row" spacing={1} alignItems="center" justifyContent="space-between">
          <Stack direction="row" spacing={1}>
            <Button variant="outlined" startIcon={<RestoreIcon />} onClick={vs.reset} size="small">
              Reset
            </Button>
            <Button variant="outlined" color="success" startIcon={<CheckIcon />} onClick={vs.confirmAll} size="small">
              {translate("aiflow.verification.confirmAll")}
            </Button>
            <Button variant="contained" startIcon={saving ? <CircularProgress size={16} /> : <SaveIcon />} onClick={handleSave} disabled={saving} size="small">
              {translate("ra.action.save")}
            </Button>
          </Stack>
          <Stack direction="row" spacing={1} alignItems="center">
            {saveStatus === "saved" && <Chip label={translate("aiflow.verification.saved")} color="success" size="small" />}
            {saveStatus === "error" && <Chip label="Error" color="error" size="small" />}
            <Typography variant="caption" color="text.secondary" sx={{ whiteSpace: "nowrap" }}>
              {vs.stats.confirmed + vs.stats.corrected}/{vs.stats.total} {translate("aiflow.verification.verified")}
            </Typography>
          </Stack>
        </Stack>
      </Paper>
    </Box>
  );
};
