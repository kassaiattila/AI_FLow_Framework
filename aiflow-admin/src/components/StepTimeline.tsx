import { useState } from "react";
import { useTranslate } from "react-admin";
import {
  Box, Typography, Chip, Stack, Collapse, IconButton,
  LinearProgress, Paper,
} from "@mui/material";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ErrorIcon from "@mui/icons-material/Error";
import RadioButtonUncheckedIcon from "@mui/icons-material/RadioButtonUnchecked";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import { keyframes } from "@mui/system";

const pulse = keyframes`
  0% { box-shadow: 0 0 0 0 rgba(99,102,241,0.4); }
  70% { box-shadow: 0 0 0 8px rgba(99,102,241,0); }
  100% { box-shadow: 0 0 0 0 rgba(99,102,241,0); }
`;

export interface TimelineStep {
  step_name: string;
  status: "pending" | "running" | "completed" | "failed";
  duration_ms?: number;
  tokens_used?: number;
  cost_usd?: number;
  confidence?: number;
  output_preview?: string;
  error?: string;
}

interface Props {
  steps: TimelineStep[];
}

function confidenceColor(c: number): "error" | "warning" | "success" {
  if (c < 0.5) return "error";
  if (c < 0.8) return "warning";
  return "success";
}

function StepNode({ step, isLast }: { step: TimelineStep; isLast: boolean }) {
  const [expanded, setExpanded] = useState(false);
  const hasDetail = !!step.output_preview || !!step.error;

  const icon =
    step.status === "completed" ? (
      <CheckCircleIcon sx={{ color: "success.main", fontSize: 24 }} />
    ) : step.status === "failed" ? (
      <ErrorIcon sx={{ color: "error.main", fontSize: 24 }} />
    ) : step.status === "running" ? (
      <Box
        sx={{
          width: 24, height: 24, borderRadius: "50%",
          bgcolor: "primary.main",
          animation: `${pulse} 1.5s infinite`,
        }}
      />
    ) : (
      <RadioButtonUncheckedIcon sx={{ color: "text.disabled", fontSize: 24 }} />
    );

  return (
    <Box sx={{ display: "flex", gap: 2 }}>
      {/* Timeline column */}
      <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center", width: 24 }}>
        {icon}
        {!isLast && (
          <Box
            sx={{
              width: 2, flex: 1, minHeight: 20,
              bgcolor: step.status === "completed" ? "success.main" : "divider",
              transition: "background-color 0.3s",
            }}
          />
        )}
      </Box>

      {/* Content */}
      <Paper
        variant="outlined"
        sx={{
          flex: 1, mb: isLast ? 0 : 1.5, p: 1.5,
          borderColor: step.status === "running" ? "primary.main" : step.status === "failed" ? "error.main" : "divider",
          opacity: step.status === "pending" ? 0.5 : 1,
          transition: "opacity 0.3s, border-color 0.3s",
        }}
      >
        <Stack direction="row" alignItems="center" justifyContent="space-between">
          <Typography variant="subtitle2">{step.step_name}</Typography>
          <Stack direction="row" spacing={0.5} alignItems="center">
            {step.duration_ms != null && (
              <Chip
                label={step.duration_ms < 1000 ? `${Math.round(step.duration_ms)}ms` : `${(step.duration_ms / 1000).toFixed(1)}s`}
                size="small"
                variant="outlined"
                sx={{ fontSize: "0.7rem", height: 20 }}
              />
            )}
            {step.tokens_used != null && step.tokens_used > 0 && (
              <Chip
                label={`${step.tokens_used} tok`}
                size="small"
                variant="outlined"
                sx={{ fontSize: "0.7rem", height: 20 }}
              />
            )}
            {step.cost_usd != null && step.cost_usd > 0 && (
              <Chip
                label={`$${step.cost_usd.toFixed(4)}`}
                size="small"
                variant="outlined"
                sx={{ fontSize: "0.7rem", height: 20 }}
              />
            )}
            {hasDetail && (
              <IconButton size="small" onClick={() => setExpanded(!expanded)} sx={{ p: 0.25 }}>
                {expanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
              </IconButton>
            )}
          </Stack>
        </Stack>

        {/* Confidence bar */}
        {step.confidence != null && step.status !== "pending" && (
          <Box sx={{ mt: 0.5, display: "flex", alignItems: "center", gap: 1 }}>
            <LinearProgress
              variant="determinate"
              value={step.confidence * 100}
              color={confidenceColor(step.confidence)}
              sx={{ flex: 1, height: 4, borderRadius: 2 }}
            />
            <Typography variant="caption" sx={{ minWidth: 32 }}>
              {(step.confidence * 100).toFixed(0)}%
            </Typography>
          </Box>
        )}

        {/* Expandable detail */}
        <Collapse in={expanded}>
          {step.output_preview && (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1, fontSize: "0.8rem" }}>
              {step.output_preview}
            </Typography>
          )}
          {step.error && (
            <Typography variant="body2" color="error" sx={{ mt: 1, fontSize: "0.8rem" }}>
              {step.error}
            </Typography>
          )}
        </Collapse>
      </Paper>
    </Box>
  );
}

export const StepTimeline = ({ steps }: Props) => {
  const translate = useTranslate();
  const completed = steps.filter((s) => s.status === "completed").length;
  const totalDuration = steps.reduce((s, st) => s + (st.duration_ms || 0), 0);
  const totalCost = steps.reduce((s, st) => s + (st.cost_usd || 0), 0);

  return (
    <Box>
      {/* Summary bar */}
      <Stack direction="row" spacing={1} sx={{ mb: 2 }} flexWrap="wrap" useFlexGap>
        <Chip label={`${completed}/${steps.length} ${translate("aiflow.pipeline.steps")}`} size="small" color="primary" />
        {totalDuration > 0 && (
          <Chip label={`${(totalDuration / 1000).toFixed(1)}s`} size="small" variant="outlined" />
        )}
        {totalCost > 0 && (
          <Chip label={`$${totalCost.toFixed(4)}`} size="small" variant="outlined" />
        )}
      </Stack>

      {/* Timeline */}
      {steps.map((step, i) => (
        <StepNode key={step.step_name} step={step} isLast={i === steps.length - 1} />
      ))}
    </Box>
  );
};
