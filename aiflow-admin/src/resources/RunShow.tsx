import {
  Show, useTranslate, useRecordContext,
} from "react-admin";
import { Chip, Typography, Box, Divider, Stack, Button, Paper } from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import { useNavigate } from "react-router-dom";
import { StepTimeline, type TimelineStep } from "../components/StepTimeline";

const StepsTimeline = () => {
  const record = useRecordContext();
  if (!record?.steps) return null;
  return <StepTimeline steps={record.steps as TimelineStep[]} />;
};

// Compact label-value pair
const Field = ({ label, children }: { label: string; children: React.ReactNode }) => (
  <Box>
    <Typography variant="caption" color="text.secondary" sx={{ display: "block", lineHeight: 1.2 }}>
      {label}
    </Typography>
    <Typography variant="body2" sx={{ fontWeight: 500 }}>
      {children}
    </Typography>
  </Box>
);

const RunShowContent = () => {
  const translate = useTranslate();
  const navigate = useNavigate();
  const record = useRecordContext();
  if (!record) return null;

  const durationStr = record.total_duration_ms < 1000
    ? `${record.total_duration_ms}ms`
    : `${(record.total_duration_ms / 1000).toFixed(1)}s`;

  const startedStr = record.started_at
    ? new Date(record.started_at).toLocaleString()
    : "-";

  const costStr = `$${Number(record.total_cost_usd || 0).toFixed(4)}`;

  return (
    <Box sx={{ p: 2 }}>
      {/* Back button */}
      <Button
        startIcon={<ArrowBackIcon />}
        onClick={() => navigate("/runs")}
        size="small"
        sx={{ mb: 1.5 }}
      >
        {translate("ra.action.back")}
      </Button>

      {/* Compact header grid */}
      <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
        <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr 1fr", md: "1fr 1fr 1fr 1fr" }, gap: 2 }}>
          <Field label="Run ID">
            <Typography variant="body2" sx={{ fontWeight: 500, fontSize: "0.8rem", wordBreak: "break-all" }}>
              {record.run_id}
            </Typography>
          </Field>
          <Field label={translate("aiflow.runs.skill")}>
            {record.skill_name}
          </Field>
          <Field label={translate("aiflow.runs.status")}>
            <Chip
              label={record.status}
              color={record.status === "completed" ? "success" : "error"}
              size="small"
            />
          </Field>
          <Field label={translate("aiflow.runs.duration")}>
            {durationStr}
          </Field>
          <Field label={translate("aiflow.runs.cost")}>
            {costStr}
          </Field>
          <Field label={translate("aiflow.runs.started")}>
            {startedStr}
          </Field>
          <Field label="Input">
            {record.input_summary || "-"}
          </Field>
          <Field label="Output">
            {record.output_summary || "-"}
          </Field>
        </Box>
      </Paper>

      <Divider sx={{ mb: 2 }} />

      <Typography variant="h6" gutterBottom>
        {translate("aiflow.pipeline.title")}
      </Typography>
      <StepsTimeline />
    </Box>
  );
};

export const RunShow = () => {
  const translate = useTranslate();
  return (
    <Show>
      <RunShowContent />
    </Show>
  );
};
