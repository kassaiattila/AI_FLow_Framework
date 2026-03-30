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

// ── Email Intent Processor types ──

export interface AttachmentInfo {
  filename: string;
  mime_type: string;
  size_bytes: number;
  extracted_text: string;
  extracted_fields: Record<string, unknown>;
  document_type: string;
  processor_used: string;
  error: string;
}

export interface IntentResult {
  intent_id: string;
  intent_display_name: string;
  confidence: number;
  sub_intent: string | null;
  method: string;
  sklearn_intent: string | null;
  sklearn_confidence: number;
  llm_intent: string | null;
  llm_confidence: number;
  alternatives: Array<Record<string, unknown>>;
  reasoning: string;
}

export interface Entity {
  entity_type: string;
  value: string;
  normalized_value: string;
  confidence: number;
  source: string;
  extraction_method: string;
  start_offset: number | null;
  end_offset: number | null;
}

export interface EntityResult {
  entities: Entity[];
  entity_count: number;
  extraction_methods_used: string[];
}

export interface PriorityResult {
  priority_level: number;
  priority_name: string;
  priority_display_name: string;
  sla_hours: number;
  matched_rule: string;
  boosts_applied: string[];
  reasoning: string;
}

export interface RoutingDecision {
  queue_id: string;
  queue_name: string;
  department_id: string;
  department_name: string;
  department_email: string;
  auto_escalate_after_minutes: number;
  matched_rule: string;
  escalation_triggered: boolean;
  escalation_reason: string;
  notes: string;
}

export interface EmailProcessingResult {
  email_id: string;
  subject: string;
  sender: string;
  received_date: string;
  body: string;
  has_attachments: boolean;
  attachment_count: number;
  intent: IntentResult | null;
  entities: EntityResult | null;
  priority: PriorityResult | null;
  routing: RoutingDecision | null;
  attachment_summaries: AttachmentInfo[];
  processing_time_ms: number;
  pipeline_version: string;
  errors: string[];
  warnings: string[];
}

// ── ASZF RAG Chat types ──

export interface RagMessage {
  role: "user" | "assistant";
  content: string;
  query_output?: QueryOutput;
}

export interface SearchResult {
  chunk_id: string;
  content: string;
  similarity_score: number;
  document_name: string;
  document_category: string;
  chunk_index: number;
  metadata: Record<string, unknown>;
}

export interface Citation {
  document_name: string;
  section: string;
  page: number | null;
  chunk_index: number;
  relevance_score: number;
  excerpt: string;
}

export interface QueryOutput {
  answer: string;
  citations: Citation[];
  search_results: SearchResult[];
  hallucination_score: number;
  processing_time_ms: number;
  tokens_used: number;
  cost_usd: number;
}

export interface RagConversation {
  conversation_id: string;
  title: string;
  collection: string;
  created_at: string;
  messages: RagMessage[];
}

// ── Process Documentation types ──

export type StepType =
  | "start_event"
  | "end_event"
  | "user_task"
  | "service_task"
  | "exclusive_gateway"
  | "parallel_gateway"
  | "inclusive_gateway"
  | "subprocess";

export interface Actor {
  id: string;
  name: string;
  role: string | null;
  description: string | null;
}

export interface Decision {
  condition: string;
  yes_target: string;
  no_target: string;
  yes_label: string;
  no_label: string;
}

export interface ProcessStep {
  id: string;
  name: string;
  description: string | null;
  step_type: StepType;
  actor: string | null;
  next_steps: string[];
  decision: Decision | null;
  duration: string | null;
  inputs: string[];
  outputs: string[];
  notes: string | null;
}

export interface ProcessExtraction {
  title: string;
  description: string | null;
  actors: Actor[];
  steps: ProcessStep[];
  start_step_id: string;
  metadata: Record<string, unknown>;
}

export interface ReviewOutput {
  score: number;
  is_acceptable: boolean;
  completeness_score: number;
  logic_score: number;
  actors_score: number;
  decisions_score: number;
  issues: string[];
  suggestions: string[];
  reasoning: string;
}

export interface ProcessDocResult {
  doc_id: string;
  user_input: string;
  extraction: ProcessExtraction;
  review: ReviewOutput;
  mermaid_code: string;
  svg_url: string | null;
  drawio_url: string | null;
  created_at: string;
}

// ── Cubix Course Capture types ──

export type StageStatus = "pending" | "in_progress" | "completed" | "failed" | "skipped";

export interface TranscriptSegment {
  id: number;
  start: number;
  end: number;
  text: string;
  confidence: number;
}

export interface TopicSection {
  title: string;
  start_time: number;
  end_time: number;
  summary: string;
  content: string;
}

export interface VocabularyItem {
  term: string;
  definition: string;
}

export interface StructuredTranscript {
  title: string;
  summary: string;
  key_topics: string[];
  sections: TopicSection[];
  vocabulary: VocabularyItem[];
  cleaned_text: string;
  structuring_cost: number;
}

export interface LessonInfo {
  index: number;
  title: string;
  url: string;
  has_video: boolean;
  duration: string;
  duration_seconds: number;
}

export interface WeekInfo {
  index: number;
  title: string;
  number: string;
  lesson_count: number;
  lessons: LessonInfo[];
}

export interface CourseStructure {
  title: string;
  url: string;
  platform: string;
  weeks: WeekInfo[];
  total_lessons: number;
  total_video_lessons: number;
  scanned_at: string;
}

export interface FileProcessingState {
  global_index: number;
  slug: string;
  title: string;
  week_index: number;
  lesson_index: number;
  probe: StageStatus;
  extract: StageStatus;
  chunk: StageStatus;
  transcribe: StageStatus;
  merge: StageStatus;
  structure: StageStatus;
  duration_seconds: number;
  chunk_count: number;
  stt_cost: number;
  structuring_cost: number;
  total_cost: number;
  last_error: string;
}

export interface PipelineState {
  course_name: string;
  course_url: string;
  course_title: string;
  version: string;
  started_at: string;
  updated_at: string;
  files: Record<string, FileProcessingState>;
  total_cost_usd: number;
  total_files: number;
  completed_files: number;
  failed_files: number;
}

export interface LessonResult {
  week_index: number;
  lesson_index: number;
  slug: string;
  title: string;
  status: "pending" | "completed" | "failed" | "skipped";
  cost_usd: number;
  error: string;
}

export interface CubixCourseResult {
  course_id: string;
  course_name: string;
  course_title: string;
  structure: CourseStructure;
  pipeline_state: PipelineState;
  results: LessonResult[];
  total_cost_usd: number;
  created_at: string;
}

// ── Skill constants ──

export const SKILLS: SkillInfo[] = [
  { name: "process_documentation", display_name: "Process Documentation", status: "production", test_count: 13, description: "BPMN diagrams from natural language" },
  { name: "aszf_rag_chat", display_name: "ASZF RAG Chat", status: "85%", test_count: 52, description: "Legal document RAG chat" },
  { name: "email_intent_processor", display_name: "Email Intent Processor", status: "90%", test_count: 54, description: "Email classification & routing" },
  { name: "invoice_processor", display_name: "Invoice Processor", status: "70%", test_count: 22, description: "PDF invoice data extraction" },
  { name: "cubix_course_capture", display_name: "Cubix Course Capture", status: "75%", test_count: 13, description: "Video transcript pipeline" },
  { name: "qbpp_test_automation", display_name: "QBPP Test Automation", status: "stub", test_count: 3, description: "Insurance calculator testing" },
];
