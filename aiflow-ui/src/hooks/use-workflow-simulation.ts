"use client";

import { useState, useCallback, useRef } from "react";
import type { StepExecution } from "@/lib/types";

const BASE_STEPS: Omit<StepExecution, "status">[] = [
  {
    step_name: "parse_pdf",
    duration_ms: 1400,
    input_preview: "document.pdf (2 pages, 148 KB)",
    output_preview: "Parsed 2 pages, 923 tokens extracted via Docling",
    cost_usd: 0,
    tokens_used: 0,
    confidence: 1.0,
    error: "",
  },
  {
    step_name: "extract_fields",
    duration_ms: 3200,
    input_preview: "Raw text: 923 tokens from PDF parse output",
    output_preview: "{vendor: '...', invoice_no: '...', gross: ... HUF, line items}",
    cost_usd: 0.0068,
    tokens_used: 1720,
    confidence: 0.95,
    error: "",
  },
  {
    step_name: "validate_output",
    duration_ms: 220,
    input_preview: "Extracted document JSON with line items",
    output_preview: "Valid: true, 0 errors, 1 warning",
    cost_usd: 0,
    tokens_used: 0,
    confidence: 0.95,
    error: "",
  },
  {
    step_name: "export_csv",
    duration_ms: 480,
    input_preview: "Validated document JSON",
    output_preview: "Exported to output/",
    cost_usd: 0,
    tokens_used: 0,
    confidence: 1.0,
    error: "",
  },
];

export type SimStatus = "idle" | "running" | "completed" | "failed";

export function useWorkflowSimulation(documentName?: string) {
  const [steps, setSteps] = useState<StepExecution[]>([]);
  const [simStatus, setSimStatus] = useState<SimStatus>("idle");
  const [elapsedMs, setElapsedMs] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const startTimeRef = useRef<number>(0);
  const timeoutsRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  const reset = useCallback(() => {
    if (timerRef.current) clearInterval(timerRef.current);
    for (const t of timeoutsRef.current) clearTimeout(t);
    timeoutsRef.current = [];
    setSteps([]);
    setSimStatus("idle");
    setElapsedMs(0);
  }, []);

  const start = useCallback(() => {
    reset();

    // Customize first step with document name
    const simSteps = BASE_STEPS.map((s, i) =>
      i === 0 && documentName
        ? { ...s, input_preview: `${documentName} (2 pages)` }
        : s
    );

    const initial: StepExecution[] = simSteps.map((s) => ({
      ...s,
      status: "pending" as const,
      duration_ms: 0,
      cost_usd: 0,
      tokens_used: 0,
      confidence: 0,
      output_preview: "",
    }));
    setSteps(initial);
    setSimStatus("running");
    startTimeRef.current = Date.now();

    timerRef.current = setInterval(() => {
      setElapsedMs(Date.now() - startTimeRef.current);
    }, 50);

    let cumulativeDelay = 300;

    simSteps.forEach((tmpl, idx) => {
      const t1 = setTimeout(() => {
        setSteps((prev) =>
          prev.map((s, i) => (i === idx ? { ...s, status: "running" as const } : s))
        );
      }, cumulativeDelay);
      timeoutsRef.current.push(t1);

      cumulativeDelay += tmpl.duration_ms;

      const t2 = setTimeout(() => {
        setSteps((prev) =>
          prev.map((s, i) => (i === idx ? { ...tmpl, status: "completed" as const } : s))
        );
        if (idx === simSteps.length - 1) {
          if (timerRef.current) clearInterval(timerRef.current);
          setElapsedMs(simSteps.reduce((sum, st) => sum + st.duration_ms, 0));
          setSimStatus("completed");
        }
      }, cumulativeDelay);
      timeoutsRef.current.push(t2);
    });
  }, [reset, documentName]);

  return { steps, simStatus, elapsedMs, start, reset };
}
