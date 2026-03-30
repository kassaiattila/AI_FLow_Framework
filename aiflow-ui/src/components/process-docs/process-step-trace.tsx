import { ProcessingPipeline } from "@/components/processing-pipeline";
import type { ProcessDocResult, StepExecution } from "@/lib/types";

interface ProcessStepTraceProps {
  doc: ProcessDocResult | null;
  source: "backend" | "subprocess" | "demo" | null;
  isProcessing?: boolean;
}

const PROCESS_STEPS = [
  "classify_intent",
  "elaborate",
  "extract",
  "review",
  "generate_diagram",
  "export_all",
];

export function ProcessStepTrace({ doc, source, isProcessing = false }: ProcessStepTraceProps) {
  const steps: StepExecution[] = PROCESS_STEPS.map((name) => {
    // Determine real status based on available data
    let status: StepExecution["status"] = "pending";
    let outputPreview = "";
    let confidence = 1;

    if (doc) {
      // If we have a doc, check what data is present to determine which steps actually ran
      const hasExtraction = doc.extraction?.steps?.length > 0;
      const hasReview = doc.review?.score > 0;
      const hasMermaid = doc.mermaid_code?.length > 0;

      switch (name) {
        case "classify_intent":
          status = "completed";
          outputPreview = doc.user_input.slice(0, 60) + "...";
          break;
        case "elaborate":
          status = "completed";
          break;
        case "extract":
          status = hasExtraction ? "completed" : "pending";
          outputPreview = hasExtraction
            ? `${doc.extraction.actors.length} actors, ${doc.extraction.steps.length} steps`
            : "";
          break;
        case "review":
          status = hasReview ? "completed" : "pending";
          outputPreview = hasReview ? `Score: ${doc.review.score}/10` : "";
          confidence = hasReview ? doc.review.score / 10 : 1;
          break;
        case "generate_diagram":
          status = hasMermaid ? "completed" : "pending";
          outputPreview = hasMermaid ? `Mermaid (${doc.mermaid_code.length} chars)` : "";
          break;
        case "export_all":
          status = hasMermaid ? "completed" : "pending";
          break;
      }
    }

    return {
      step_name: name,
      status,
      duration_ms: 0,
      input_preview: "",
      output_preview: outputPreview,
      cost_usd: 0,
      tokens_used: 0,
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
