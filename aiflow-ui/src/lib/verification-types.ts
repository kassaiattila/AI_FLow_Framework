// Invoice Verification UI — TypeScript types and constants

/** Normalized coordinates (0-1 range relative to page dimensions) */
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

export interface InvoiceVerificationData {
  invoice_index: number;
  source_file: string;
  document_meta: DocumentMeta;
  data_points: DataPoint[];
  page_dimensions: { width: number; height: number };
}

// --- Confidence helpers ---

export const CONFIDENCE_THRESHOLDS = {
  HIGH: 0.9,
  MEDIUM: 0.7,
} as const;

export function getConfidenceColor(
  confidence: number
): "green" | "yellow" | "red" {
  if (confidence >= CONFIDENCE_THRESHOLDS.HIGH) return "green";
  if (confidence >= CONFIDENCE_THRESHOLDS.MEDIUM) return "yellow";
  return "red";
}

export const CONFIDENCE_STYLES = {
  green: {
    badge: "bg-green-100 text-green-800",
    border: "border-green-500",
    fill: "rgba(34,197,94,0.15)",
    stroke: "rgb(34,197,94)",
    fillHover: "rgba(34,197,94,0.35)",
    strokeHover: "rgb(22,163,74)",
    bg: "bg-green-50",
  },
  yellow: {
    badge: "bg-yellow-100 text-yellow-800",
    border: "border-yellow-500",
    fill: "rgba(234,179,8,0.15)",
    stroke: "rgb(234,179,8)",
    fillHover: "rgba(234,179,8,0.35)",
    strokeHover: "rgb(202,138,4)",
    bg: "bg-yellow-50",
  },
  red: {
    badge: "bg-red-100 text-red-800",
    border: "border-red-500",
    fill: "rgba(239,68,68,0.15)",
    stroke: "rgb(239,68,68)",
    fillHover: "rgba(239,68,68,0.35)",
    strokeHover: "rgb(220,38,38)",
    bg: "bg-red-50",
  },
} as const;

export const STATUS_STYLES = {
  auto: { badge: "bg-gray-100 text-gray-600", label: "Auto" },
  corrected: { badge: "bg-blue-100 text-blue-700", label: "Javitva" },
  confirmed: { badge: "bg-green-100 text-green-700", label: "OK" },
} as const;

export const CATEGORY_LABELS: Record<DataPointCategory, string> = {
  document_meta: "Dokumentum",
  vendor: "Szallito",
  buyer: "Vevo",
  header: "Fejlec",
  line_item: "Tetelek",
  totals: "Osszesites",
};

export const CATEGORY_ORDER: DataPointCategory[] = [
  "document_meta",
  "vendor",
  "buyer",
  "header",
  "line_item",
  "totals",
];
