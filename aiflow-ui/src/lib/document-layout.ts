// Shared layout constants for document SVG rendering and bounding box generation.
// SVG viewBox: 595 x 842 (A4 proportions). All values in SVG units.
// Bounding boxes are computed from these same values → guaranteed alignment.

export const PAGE = { w: 595, h: 842 } as const;
const PAD_X = 4;
const PAD_Y = 2;

/** A positioned field on the SVG: where to render text AND where the bbox is */
export interface FieldLayout {
  id: string;
  /** SVG text x */
  x: number;
  /** SVG text y (baseline) */
  y: number;
  /** Font size in SVG units */
  fontSize: number;
  /** Estimated text width (SVG units). Used for bbox width. */
  estWidth: number;
  /** Category for grouping in the editor */
  category: "vendor" | "buyer" | "header" | "line_item" | "totals";
  /** Display label (Hungarian) */
  label: string;
  /** Path into ProcessedInvoice to get the value, e.g. "vendor.name" */
  fieldPath: string;
  /** For line items: which line item index this belongs to */
  lineIndex?: number;
}

// Compute normalized bounding box from SVG positions
export function fieldToBBox(f: FieldLayout) {
  return {
    x: (f.x - PAD_X) / PAGE.w,
    y: (f.y - f.fontSize - PAD_Y) / PAGE.h,
    width: (f.estWidth + PAD_X * 2) / PAGE.w,
    height: (f.fontSize + PAD_Y * 2 + 4) / PAGE.h,
    page: 0,
  };
}

// --- Static field positions (vendor, buyer, header, totals) ---

export const STATIC_FIELDS: FieldLayout[] = [
  // Vendor
  { id: "vendor.name", x: 35, y: 110, fontSize: 11, estWidth: 160, category: "vendor", label: "Szallito neve", fieldPath: "vendor.name" },
  { id: "vendor.address", x: 35, y: 130, fontSize: 9, estWidth: 220, category: "vendor", label: "Szallito cim", fieldPath: "vendor.address" },
  { id: "vendor.tax_number", x: 115, y: 155, fontSize: 8, estWidth: 110, category: "vendor", label: "Szallito adoszam", fieldPath: "vendor.tax_number" },
  { id: "vendor.bank_account", x: 135, y: 178, fontSize: 8, estWidth: 140, category: "vendor", label: "Bankszamla", fieldPath: "vendor.bank_account" },
  { id: "vendor.bank_name", x: 35, y: 201, fontSize: 8, estWidth: 120, category: "vendor", label: "Bank neve", fieldPath: "vendor.bank_name" },

  // Buyer
  { id: "buyer.name", x: 335, y: 110, fontSize: 11, estWidth: 160, category: "buyer", label: "Vevo neve", fieldPath: "buyer.name" },
  { id: "buyer.address", x: 335, y: 130, fontSize: 9, estWidth: 200, category: "buyer", label: "Vevo cim", fieldPath: "buyer.address" },
  { id: "buyer.tax_number", x: 415, y: 155, fontSize: 8, estWidth: 110, category: "buyer", label: "Vevo adoszam", fieldPath: "buyer.tax_number" },

  // Header
  { id: "header.invoice_number", x: 440, y: 52, fontSize: 10, estWidth: 110, category: "header", label: "Szamlaszam", fieldPath: "header.invoice_number" },
  { id: "header.invoice_date", x: 35, y: 256, fontSize: 9, estWidth: 80, category: "header", label: "Szamla kelte", fieldPath: "header.invoice_date" },
  { id: "header.fulfillment_date", x: 140, y: 256, fontSize: 9, estWidth: 80, category: "header", label: "Teljesites", fieldPath: "header.fulfillment_date" },
  { id: "header.due_date", x: 245, y: 256, fontSize: 9, estWidth: 80, category: "header", label: "Fiz. hatarido", fieldPath: "header.due_date" },
  { id: "header.currency", x: 350, y: 256, fontSize: 9, estWidth: 35, category: "header", label: "Penznem", fieldPath: "header.currency" },
  { id: "header.payment_method", x: 420, y: 256, fontSize: 9, estWidth: 80, category: "header", label: "Fizetesi mod", fieldPath: "header.payment_method" },

  // Totals
  { id: "totals.net_total", x: 440, y: 455, fontSize: 10, estWidth: 105, category: "totals", label: "Netto osszesen", fieldPath: "totals.net_total" },
  { id: "totals.vat_total", x: 440, y: 480, fontSize: 10, estWidth: 105, category: "totals", label: "AFA osszesen", fieldPath: "totals.vat_total" },
  { id: "totals.gross_total", x: 430, y: 512, fontSize: 13, estWidth: 115, category: "totals", label: "Brutto osszesen", fieldPath: "totals.gross_total" },
];

// --- Line item field positions (computed per row) ---

const LINE_Y_START = 335;
const LINE_Y_STEP = 35;

export function lineItemFields(lineIndex: number): FieldLayout[] {
  const y = LINE_Y_START + lineIndex * LINE_Y_STEP;
  const prefix = `line_items.${lineIndex}`;
  return [
    { id: `${prefix}.description`, x: 65, y, fontSize: 9, estWidth: 230, category: "line_item", label: "Megnevezes", fieldPath: `line_items.${lineIndex}.description`, lineIndex },
    { id: `${prefix}.quantity`, x: 288, y, fontSize: 9, estWidth: 30, category: "line_item", label: "Mennyiseg", fieldPath: `line_items.${lineIndex}.quantity`, lineIndex },
    { id: `${prefix}.net_amount`, x: 355, y, fontSize: 9, estWidth: 55, category: "line_item", label: "Netto", fieldPath: `line_items.${lineIndex}.net_amount`, lineIndex },
    { id: `${prefix}.vat_rate`, x: 435, y, fontSize: 9, estWidth: 30, category: "line_item", label: "AFA %", fieldPath: `line_items.${lineIndex}.vat_rate`, lineIndex },
    { id: `${prefix}.gross_amount`, x: 495, y, fontSize: 9, estWidth: 55, category: "line_item", label: "Brutto", fieldPath: `line_items.${lineIndex}.gross_amount`, lineIndex },
  ];
}

/** Get all field layouts for an invoice with N line items */
export function getAllFields(lineCount: number): FieldLayout[] {
  const lines: FieldLayout[] = [];
  for (let i = 0; i < Math.min(lineCount, 6); i++) {
    lines.push(...lineItemFields(i));
  }
  return [...STATIC_FIELDS, ...lines];
}

/** Resolve a dot-path like "vendor.name" on a ProcessedInvoice object */
export function resolvePath(obj: Record<string, unknown>, path: string): string {
  const parts = path.split(".");
  let current: unknown = obj;
  for (const part of parts) {
    if (current === null || current === undefined) return "";
    if (Array.isArray(current)) {
      const idx = parseInt(part, 10);
      current = current[idx];
    } else if (typeof current === "object") {
      current = (current as Record<string, unknown>)[part];
    } else {
      return "";
    }
  }
  if (current === null || current === undefined) return "";
  if (typeof current === "number") {
    return current.toLocaleString("hu-HU");
  }
  return String(current);
}
