import type { QueryOutput, StepExecution } from "@/lib/types";
import { WorkflowTimeline } from "@/components/workflow/workflow-timeline";

interface StepTraceProps {
  queryOutput: QueryOutput;
}

const RAG_STEPS = [
  "rewrite_query",
  "search_documents",
  "build_context",
  "generate_answer",
  "extract_citations",
  "detect_hallucination",
  "log_query",
];

export function StepTrace({ queryOutput }: StepTraceProps) {
  // Map QueryOutput to StepExecution[] for the timeline
  const steps: StepExecution[] = RAG_STEPS.map((name, idx) => ({
    step_name: name,
    status: "completed",
    duration_ms: Math.round(queryOutput.processing_time_ms / RAG_STEPS.length),
    input_preview: idx === 0 ? "question" : RAG_STEPS[idx - 1],
    output_preview:
      name === "generate_answer"
        ? queryOutput.answer.slice(0, 80) + "..."
        : name === "extract_citations"
          ? `${queryOutput.citations.length} citations`
          : name === "detect_hallucination"
            ? `score: ${queryOutput.hallucination_score.toFixed(2)}`
            : "",
    cost_usd: name === "generate_answer" ? queryOutput.cost_usd : 0,
    tokens_used: name === "generate_answer" ? queryOutput.tokens_used : 0,
    confidence:
      name === "detect_hallucination"
        ? queryOutput.hallucination_score
        : name === "search_documents" && queryOutput.search_results.length > 0
          ? queryOutput.search_results[0].similarity_score
          : 1,
    error: "",
  }));

  return <WorkflowTimeline steps={steps} />;
}
