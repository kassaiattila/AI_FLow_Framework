// Document Verification — TypeScript types (ported from aiflow-ui)

export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
  page: number;
}

export type DataPointCategory =
  | "document_meta"
  | "vendor"
  | "buyer"
  | "header"
  | "line_item"
  | "totals";

export type VerificationStatus = "auto" | "corrected" | "confirmed";

export interface DataPoint {
  id: string;
  category: DataPointCategory;
  field_name: string;
  label: string;
  labelEn: string;
  extracted_value: string;
  current_value: string;
  confidence: number;
  bounding_box: BoundingBox | null;
  status: VerificationStatus;
  line_item_index?: number;
}

export type DetectedDocumentType = "invoice" | "receipt" | "contract" | "credit_note" | "proforma" | "unknown";
export type DetectedDirection = "incoming" | "outgoing" | "unknown";

export interface DocumentMeta {
  document_type: DetectedDocumentType;
  document_type_confidence: number;
  direction: DetectedDirection;
  direction_confidence: number;
  language: string;
  language_confidence: number;
}

export interface DocumentVerificationData {
  document_index: number;
  source_file: string;
  document_meta: DocumentMeta;
  data_points: DataPoint[];
  page_dimensions: { width: number; height: number };
}

export const CONFIDENCE_THRESHOLDS = { HIGH: 0.9, MEDIUM: 0.7 } as const;

export function getConfidenceLevel(confidence: number): "high" | "medium" | "low" {
  if (confidence >= CONFIDENCE_THRESHOLDS.HIGH) return "high";
  if (confidence >= CONFIDENCE_THRESHOLDS.MEDIUM) return "medium";
  return "low";
}

export const CATEGORY_ORDER: DataPointCategory[] = [
  "document_meta", "vendor", "buyer", "header", "line_item", "totals",
];
