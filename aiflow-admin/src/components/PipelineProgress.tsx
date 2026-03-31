import { useState, useEffect, useRef } from "react";
import {
  Box, Typography, LinearProgress, Stack, Chip,
} from "@mui/material";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import RadioButtonUncheckedIcon from "@mui/icons-material/RadioButtonUnchecked";
import { keyframes } from "@mui/system";

const pulse = keyframes`
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
`;

export interface PipelineStep {
  name: string;
  description: string;
}

interface Props {
  steps: PipelineStep[];
  /** Number of steps actually completed (from backend SSE) */
  completedSteps: number;
  running: boolean;
  completed?: boolean;
  /** Real elapsed ms per completed step (from backend SSE) */
  stepTimings?: number[];
}

export const PipelineProgress = ({ steps, completedSteps, running, completed, stepTimings = [] }: Props) => {
  const [elapsed, setElapsed] = useState(0);
  const startRef = useRef<number>(0);
  const timerRef = useRef<ReturnType<typeof setInterval>>();

  // Elapsed time counter — only real wall-clock time
  useEffect(() => {
    if (!running) {
      if (timerRef.current) clearInterval(timerRef.current);
      return;
    }

    startRef.current = Date.now();
    setElapsed(0);

    timerRef.current = setInterval(() => {
      setElapsed(Date.now() - startRef.current);
    }, 100);

    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [running]);

  // Stop timer when completed
  useEffect(() => {
    if (completed && timerRef.current) {
      clearInterval(timerRef.current);
    }
  }, [completed]);

  const totalSteps = steps.length;
  const done = completed ? totalSteps : completedSteps;
  const progressPct = totalSteps > 0 ? (done / totalSteps) * 100 : 0;
  const elapsedSec = (elapsed / 1000).toFixed(1);

  return (
    <Box sx={{ py: 1 }}>
      {/* Overall progress bar — real progress based on completed steps */}
      <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1.5 }}>
        <LinearProgress
          variant={running && completedSteps === 0 ? "indeterminate" : "determinate"}
          value={progressPct}
          sx={{ flex: 1, height: 6, borderRadius: 3 }}
        />
        <Typography variant="caption" sx={{ minWidth: 60, textAlign: "right" }}>
          {completed ? `${elapsedSec}s` : `${elapsedSec}s`}
        </Typography>
      </Stack>

      {/* Step indicators — driven by real backend events */}
      <Stack spacing={0.75}>
        {steps.map((step, i) => {
          const isDone = completed || i < completedSteps;
          const isActive = !completed && i === completedSteps && running;
          const isPending = !completed && i > completedSteps;
          const timing = stepTimings[i];

          return (
            <Stack key={step.name} direction="row" alignItems="center" spacing={1}>
              {isDone ? (
                <CheckCircleIcon sx={{ fontSize: 18, color: "success.main" }} />
              ) : isActive ? (
                <Box
                  sx={{
                    width: 18, height: 18, borderRadius: "50%",
                    bgcolor: "primary.main",
                    animation: `${pulse} 1s infinite`,
                  }}
                />
              ) : (
                <RadioButtonUncheckedIcon sx={{ fontSize: 18, color: "text.disabled" }} />
              )}
              <Typography
                variant="body2"
                sx={{
                  fontWeight: isActive ? 600 : 400,
                  color: isPending ? "text.disabled" : "text.primary",
                }}
              >
                {step.name}
              </Typography>
              <Typography variant="caption" color="text.secondary" sx={{ flex: 1 }}>
                {step.description}
              </Typography>
              {/* Show real elapsed time per step when available */}
              {isDone && timing !== undefined && (
                <Chip
                  label={timing < 1000 ? `${timing}ms` : `${(timing / 1000).toFixed(1)}s`}
                  size="small"
                  color="success"
                  variant="outlined"
                  sx={{ fontSize: "0.65rem", height: 18 }}
                />
              )}
            </Stack>
          );
        })}
      </Stack>
    </Box>
  );
};
