/**
 * Document Recognizer admin UI types — Sprint V SV-4.
 *
 * Mirrors aiflow.contracts.doc_recognition Pydantic shapes + the SV-3
 * router response models in src/aiflow/api/v1/document_recognizer.py.
 */

export type PiiLevel = "low" | "medium" | "high";
export type DocIntent =
  | "process"
  | "route_to_human"
  | "rag_ingest"
  | "respond"
  | "reject";

export interface DoctypeListItem {
  name: string;
  display_name: string;
  language: string;
  category: string;
  version: number;
  pii_level: PiiLevel;
  field_count: number;
  has_tenant_override: boolean;
}

export interface DoctypeListResponse {
  count: number;
  items: DoctypeListItem[];
}

export interface RuleSpec {
  kind: "regex" | "keyword_list" | "structure_hint" | "filename_match" | "parser_metadata";
  weight: number;
  pattern?: string | null;
  keywords?: string[] | null;
  threshold?: number | null;
  hint?: string | null;
}

export interface FieldSpec {
  name: string;
  type: string;
  required: boolean;
  validators: string[];
  enum?: string[] | null;
  currency_default?: string | null;
  schema_ref?: string | null;
}

export interface IntentRoutingRule {
  if: string; // YAML alias preserved
  intent: DocIntent;
  reason: string;
}

export interface DocTypeDescriptor {
  name: string;
  display_name: string;
  description?: string | null;
  language: string;
  category: string;
  version: number;
  pii_level: PiiLevel;
  parser_preferences: string[];
  type_classifier: {
    rules: RuleSpec[];
    llm_fallback: boolean;
    llm_threshold_below: number;
  };
  extraction: {
    workflow: string;
    fields: FieldSpec[];
  };
  intent_routing: {
    default: DocIntent;
    pii_redaction: boolean;
    conditions: IntentRoutingRule[];
  };
}

export interface DoctypeDetailResponse {
  descriptor: DocTypeDescriptor;
  has_tenant_override: boolean;
  source: "bootstrap" | "tenant_override";
}

export interface DocTypeMatch {
  doc_type: string;
  confidence: number;
  alternatives: [string, number][];
}

export interface DocFieldValue {
  value: string | number | boolean | null;
  confidence: number;
  source_text_hint?: string | null;
}

export interface DocExtractionResult {
  doc_type: string;
  extracted_fields: Record<string, DocFieldValue>;
  validation_warnings: string[];
  cost_usd: number;
  extraction_time_ms: number;
}

export interface DocIntentDecision {
  intent: DocIntent;
  reason: string;
  next_action?: string | null;
}

export interface RecognizeResponse {
  run_id: string;
  match: DocTypeMatch;
  extraction: DocExtractionResult;
  intent: DocIntentDecision;
  classification_method: "rule_engine" | "llm_fallback" | "hint";
  pii_redacted: boolean;
}

export interface DoctypeOverrideResponse {
  name: string;
  tenant_id: string;
  saved_path: string;
}
