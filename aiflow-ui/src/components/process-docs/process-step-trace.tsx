import type { ProcessDocResult, StepExecution } from "@/lib/types";
import { WorkflowTimeline } from "@/components/workflow/workflow-timeline";

interface ProcessStepTraceProps {
  doc: ProcessDocResult;
}

const PROCESS_STEPS = [
  "classify_intent",
  "elaborate",
  "extract",
  "review",
  "generate_diagram",
  "export_all",
];

export function ProcessStepTrace({ doc }: ProcessStepTraceProps) {
  const steps: StepExecution[] = PROCESS_STEPS.map((name) => ({
    step_name: name,
    status: "completed",
    duration_ms: 0,
    input_preview:
      name === "classify_intent"
        ? doc.user_input.slice(0, 60) + "..."
        : "",
    output_preview:
      name === "extract"
        ? `${doc.extraction.actors.length} actors, ${doc.extraction.steps.length} steps`
        : name === "review"
          ? `Score: ${doc.review.score}/10`
          : name === "generate_diagram"
            ? `Mermaid (${doc.mermaid_code.length} chars)`
            : "",
    cost_usd: 0,
    tokens_used: 0,
    confidence:
      name === "review" ? doc.review.score / 10 : 1,
    error: "",
  }));

  return <WorkflowTimeline steps={steps} />;
}
