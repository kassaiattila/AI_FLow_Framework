import { ProcessingPipeline } from "@/components/processing-pipeline";
import type { QueryOutput, StepExecution } from "@/lib/types";

interface StepTraceProps {
  queryOutput: QueryOutput;
  source: "backend" | "demo" | null;
  isProcessing?: boolean;
}

const RAG_STEPS = [
  "rewrite_query",
  "search_documents",
  "build_context",
  "generate_answer",
  "extract_citations",
  "detect_hallucination",
];

export function StepTrace({ queryOutput, source, isProcessing = false }: StepTraceProps) {
  const hasAnswer = queryOutput.answer.length > 0;
  const hasCitations = queryOutput.citations.length > 0;
  const hasSearch = queryOutput.search_results.length > 0;

  const steps: StepExecution[] = RAG_STEPS.map((name) => {
    let status: StepExecution["status"] = hasAnswer ? "completed" : "pending";
    let outputPreview = "";
    let confidence = 1;
    let cost = 0;
    let tokens = 0;
    const duration = hasAnswer ? Math.round(queryOutput.processing_time_ms / RAG_STEPS.length) : 0;

    switch (name) {
      case "search_documents":
        status = hasSearch ? "completed" : hasAnswer ? "completed" : "pending";
        outputPreview = hasSearch ? `${queryOutput.search_results.length} results` : "";
        confidence = hasSearch ? queryOutput.search_results[0].similarity_score : 1;
        break;
      case "generate_answer":
        status = hasAnswer ? "completed" : "pending";
        outputPreview = hasAnswer ? queryOutput.answer.slice(0, 80) + "..." : "";
        cost = queryOutput.cost_usd;
        tokens = queryOutput.tokens_used;
        break;
      case "extract_citations":
        status = hasCitations ? "completed" : hasAnswer ? "completed" : "pending";
        outputPreview = hasCitations ? `${queryOutput.citations.length} citations` : "";
        break;
      case "detect_hallucination":
        status = hasAnswer ? "completed" : "pending";
        outputPreview = hasAnswer ? `score: ${queryOutput.hallucination_score.toFixed(2)}` : "";
        confidence = queryOutput.hallucination_score;
        break;
    }

    return {
      step_name: name,
      status,
      duration_ms: duration,
      input_preview: "",
      output_preview: outputPreview,
      cost_usd: cost,
      tokens_used: tokens,
      confidence,
      error: "",
    };
  });

  return (
    <ProcessingPipeline
      steps={steps}
      source={source}
      isProcessing={isProcessing}
    />
  );
}
