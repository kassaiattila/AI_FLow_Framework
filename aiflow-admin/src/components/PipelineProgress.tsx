import { useState, useEffect, useRef } from "react";
import { useTranslate } from "react-admin";
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
  estimated_ms: number;
  description: string;
}

interface Props {
  steps: PipelineStep[];
  running: boolean;
  completed?: boolean;
}

export const PipelineProgress = ({ steps, running, completed }: Props) => {
  const translate = useTranslate();
  const [currentStep, setCurrentStep] = useState(-1);
  const [elapsed, setElapsed] = useState(0);
  const startRef = useRef<number>(0);
  const timerRef = useRef<ReturnType<typeof setInterval>>();

  const totalEstimated = steps.reduce((s, st) => s + st.estimated_ms, 0);

  // Simulate step progression
  useEffect(() => {
    if (!running) {
      if (completed) {
        setCurrentStep(steps.length);
        setElapsed(totalEstimated);
      }
      if (timerRef.current) clearInterval(timerRef.current);
      return;
    }

    startRef.current = Date.now();
    setCurrentStep(0);
    setElapsed(0);

    timerRef.current = setInterval(() => {
      const now = Date.now();
      const el = now - startRef.current;
      setElapsed(el);

      // Determine which step we're on based on elapsed time
      let accum = 0;
      for (let i = 0; i < steps.length; i++) {
        accum += steps[i].estimated_ms;
        if (el < accum) {
          setCurrentStep(i);
          return;
        }
      }
      // Past all estimated times — stay on last step (still waiting for API)
      setCurrentStep(steps.length - 1);
    }, 100);

    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [running, completed, steps, totalEstimated]);

  // If completed externally, jump to done
  useEffect(() => {
    if (completed) {
      setCurrentStep(steps.length);
      if (timerRef.current) clearInterval(timerRef.current);
    }
  }, [completed, steps.length]);

  const progressPct = completed
    ? 100
    : Math.min(99, (elapsed / totalEstimated) * 100);

  const elapsedSec = (elapsed / 1000).toFixed(1);

  return (
    <Box sx={{ py: 1 }}>
      {/* Overall progress bar */}
      <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1.5 }}>
        <LinearProgress
          variant="determinate"
          value={progressPct}
          sx={{ flex: 1, height: 6, borderRadius: 3 }}
        />
        <Typography variant="caption" sx={{ minWidth: 60, textAlign: "right" }}>
          {completed
            ? translate("aiflow.pipeline.done")
            : `${elapsedSec}s / ~${(totalEstimated / 1000).toFixed(0)}s`}
        </Typography>
      </Stack>

      {/* Step indicators */}
      <Stack spacing={0.75}>
        {steps.map((step, i) => {
          const isDone = completed || i < currentStep;
          const isActive = !completed && i === currentStep;
          const isPending = !completed && i > currentStep;

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
              <Chip
                label={`~${step.estimated_ms < 1000 ? `${step.estimated_ms}ms` : `${(step.estimated_ms / 1000).toFixed(1)}s`}`}
                size="small"
                variant="outlined"
                sx={{ fontSize: "0.65rem", height: 18, opacity: isPending ? 0.4 : 1 }}
              />
            </Stack>
          );
        })}
      </Stack>
    </Box>
  );
};
