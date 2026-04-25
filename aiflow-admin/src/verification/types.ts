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

export type DetectedDocumentType =
  | "invoice"
  | "receipt"
  | "contract"
  | "credit_note"
  | "proforma"
  | "unknown";
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

export function getConfidenceLevel(
  confidence: number,
): "high" | "medium" | "low" {
  if (confidence >= CONFIDENCE_THRESHOLDS.HIGH) return "high";
  if (confidence >= CONFIDENCE_THRESHOLDS.MEDIUM) return "medium";
  return "low";
}

export const CATEGORY_ORDER: DataPointCategory[] = [
  "document_meta",
  "vendor",
  "buyer",
  "header",
  "line_item",
  "totals",
];

// --- Field-type validators ---

export interface ValidationResult {
  valid: boolean;
  error?: string;
}

const numericPattern = /^[\d\s.,+-]+$/;
const datePattern =
  /^(\d{4}[-./]\d{2}[-./]\d{2}\.?|\d{2}[-./]\d{2}[-./]\d{4})$/;
const taxNumberPattern = /^\d{8}(-\d{1,2}-\d{2})?$/;

function validateNumeric(value: string): ValidationResult {
  if (!value) return { valid: true };
  return numericPattern.test(value.trim())
    ? { valid: true }
    : { valid: false, error: "Szam formatum szukseges (pl. 1234.56)" };
}

function validateDate(value: string): ValidationResult {
  if (!value) return { valid: true };
  return datePattern.test(value.trim())
    ? { valid: true }
    : { valid: false, error: "Datum formatum: YYYY-MM-DD vagy YYYY.MM.DD." };
}

function validateTaxNumber(value: string): ValidationResult {
  if (!value) return { valid: true };
  return taxNumberPattern.test(value.trim())
    ? { valid: true }
    : {
        valid: false,
        error: "Adoszam: 8 vagy 11 jegy (12345678 vagy 12345678-1-23)",
      };
}

const FIELD_VALIDATORS: Record<string, (v: string) => ValidationResult> = {
  "totals.net_total": validateNumeric,
  "totals.vat_total": validateNumeric,
  "totals.gross_total": validateNumeric,
  "header.invoice_date": validateDate,
  "header.fulfillment_date": validateDate,
  "header.due_date": validateDate,
  "vendor.tax_number": validateTaxNumber,
  "buyer.tax_number": validateTaxNumber,
};

// Line item numeric fields
for (let i = 0; i < 10; i++) {
  FIELD_VALIDATORS[`line_items.${i}.net_amount`] = validateNumeric;
  FIELD_VALIDATORS[`line_items.${i}.gross_amount`] = validateNumeric;
  FIELD_VALIDATORS[`line_items.${i}.quantity`] = validateNumeric;
  FIELD_VALIDATORS[`line_items.${i}.vat_rate`] = validateNumeric;
}

export function validateField(
  fieldName: string,
  value: string,
): ValidationResult {
  const validator = FIELD_VALIDATORS[fieldName];
  if (!validator) return { valid: true };
  return validator(value);
}
