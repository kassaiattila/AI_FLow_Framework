// AIFlow UI - TypeScript types matching Python Pydantic models

export interface StepExecution {
  step_name: string;
  status: "pending" | "running" | "completed" | "failed";
  duration_ms: number;
  input_preview: string;
  output_preview: string;
  cost_usd: number;
  tokens_used: number;
  confidence: number;
  error: string;
}

export interface WorkflowRun {
  run_id: string;
  skill_name: string;
  status: "pending" | "running" | "completed" | "failed";
  steps: StepExecution[];
  total_duration_ms: number;
  total_cost_usd: number;
  started_at: string;
  input_summary: string;
  output_summary: string;
}

export interface InvoiceParty {
  name: string;
  address: string;
  tax_number: string;
  bank_account: string;
  bank_name: string;
}

export interface InvoiceHeader {
  invoice_number: string;
  invoice_date: string;
  fulfillment_date: string;
  due_date: string;
  currency: string;
  payment_method: string;
  invoice_type: string;
}

export interface LineItem {
  line_number: number;
  description: string;
  quantity: number;
  unit: string;
  unit_price: number;
  net_amount: number;
  vat_rate: number;
  vat_amount: number;
  gross_amount: number;
}

export interface InvoiceTotals {
  net_total: number;
  vat_total: number;
  gross_total: number;
}

export interface InvoiceValidation {
  is_valid: boolean;
  errors: string[];
  warnings: string[];
  confidence_score: number;
}

export interface ProcessedInvoice {
  source_file: string;
  direction: string;
  vendor: InvoiceParty;
  buyer: InvoiceParty;
  header: InvoiceHeader;
  line_items: LineItem[];
  totals: InvoiceTotals;
  validation: InvoiceValidation;
  parser_used: string;
  extraction_confidence: number;
}

export interface CostSummary {
  daily_cost: number;
  weekly_cost: number;
  monthly_cost: number;
  per_skill: Record<string, number>;
  per_model: Record<string, number>;
}

export interface SkillInfo {
  name: string;
  display_name: string;
  status: string;
  test_count: number;
  description: string;
}

export const SKILLS: SkillInfo[] = [
  { name: "process_documentation", display_name: "Process Documentation", status: "production", test_count: 13, description: "BPMN diagrams from natural language" },
  { name: "aszf_rag_chat", display_name: "ASZF RAG Chat", status: "85%", test_count: 52, description: "Legal document RAG chat" },
  { name: "email_intent_processor", display_name: "Email Intent Processor", status: "90%", test_count: 54, description: "Email classification & routing" },
  { name: "invoice_processor", display_name: "Invoice Processor", status: "70%", test_count: 22, description: "PDF invoice data extraction" },
  { name: "cubix_course_capture", display_name: "Cubix Course Capture", status: "75%", test_count: 13, description: "Video transcript pipeline" },
  { name: "qbpp_test_automation", display_name: "QBPP Test Automation", status: "stub", test_count: 3, description: "Insurance calculator testing" },
];
