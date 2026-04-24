/**
 * TypeScript mirror of the FastAPI prompt-workflow contracts
 * (Sprint R / S140). Shape sourced from
 * src/aiflow/api/v1/prompt_workflows.py + src/aiflow/prompts/workflow.py.
 */

export interface PromptWorkflowStep {
  id: string;
  prompt_name: string;
  description: string | null;
  required: boolean;
  depends_on: string[];
  output_key: string | null;
  metadata: Record<string, unknown>;
}

export interface PromptWorkflow {
  name: string;
  version: string;
  description: string | null;
  steps: PromptWorkflowStep[];
  tags: string[];
  default_label: string;
}

export interface PromptWorkflowListItem {
  name: string;
  version: string;
  step_count: number;
  tags: string[];
  default_label: string;
}

export interface PromptWorkflowListResponse {
  workflows: PromptWorkflowListItem[];
  total: number;
  source: string;
}

export interface ResolvedPromptDefinition {
  name: string;
  version: string;
  description: string;
  system: string;
  user: string;
  config?: Record<string, unknown>;
}

export interface PromptWorkflowDryRunResponse {
  workflow: PromptWorkflow;
  steps: Record<string, ResolvedPromptDefinition>;
  resolved_label: string;
  source: string;
}
