// Document SVG layout — ported from aiflow-ui (unchanged logic)

export const PAGE = { w: 595, h: 842 } as const;
const PAD_X = 4;
const PAD_Y = 2;

export interface FieldLayout {
  id: string;
  x: number;
  y: number;
  fontSize: number;
  estWidth: number;
  category: "vendor" | "buyer" | "header" | "line_item" | "totals";
  label: string;
  labelEn: string;
  fieldPath: string;
  lineIndex?: number;
}

export function fieldToBBox(f: FieldLayout) {
  return {
    x: (f.x - PAD_X) / PAGE.w,
    y: (f.y - f.fontSize - PAD_Y) / PAGE.h,
    width: (f.estWidth + PAD_X * 2) / PAGE.w,
    height: (f.fontSize + PAD_Y * 2 + 4) / PAGE.h,
    page: 0,
  };
}

export const STATIC_FIELDS: FieldLayout[] = [
  { id: "vendor.name", x: 35, y: 110, fontSize: 11, estWidth: 160, category: "vendor", label: "Szallito neve", labelEn: "Vendor Name", fieldPath: "vendor.name" },
  { id: "vendor.address", x: 35, y: 130, fontSize: 9, estWidth: 220, category: "vendor", label: "Szallito cim", labelEn: "Vendor Address", fieldPath: "vendor.address" },
  { id: "vendor.tax_number", x: 115, y: 155, fontSize: 8, estWidth: 110, category: "vendor", label: "Szallito adoszam", labelEn: "Vendor Tax #", fieldPath: "vendor.tax_number" },
  { id: "vendor.bank_account", x: 135, y: 178, fontSize: 8, estWidth: 140, category: "vendor", label: "Bankszamla", labelEn: "Bank Account", fieldPath: "vendor.bank_account" },
  { id: "vendor.bank_name", x: 35, y: 201, fontSize: 8, estWidth: 120, category: "vendor", label: "Bank neve", labelEn: "Bank Name", fieldPath: "vendor.bank_name" },
  { id: "buyer.name", x: 335, y: 110, fontSize: 11, estWidth: 160, category: "buyer", label: "Vevo neve", labelEn: "Buyer Name", fieldPath: "buyer.name" },
  { id: "buyer.address", x: 335, y: 130, fontSize: 9, estWidth: 200, category: "buyer", label: "Vevo cim", labelEn: "Buyer Address", fieldPath: "buyer.address" },
  { id: "buyer.tax_number", x: 415, y: 155, fontSize: 8, estWidth: 110, category: "buyer", label: "Vevo adoszam", labelEn: "Buyer Tax #", fieldPath: "buyer.tax_number" },
  { id: "header.invoice_number", x: 440, y: 52, fontSize: 10, estWidth: 110, category: "header", label: "Szamlaszam", labelEn: "Invoice #", fieldPath: "header.invoice_number" },
  { id: "header.invoice_date", x: 35, y: 256, fontSize: 9, estWidth: 80, category: "header", label: "Szamla kelte", labelEn: "Invoice Date", fieldPath: "header.invoice_date" },
  { id: "header.fulfillment_date", x: 140, y: 256, fontSize: 9, estWidth: 80, category: "header", label: "Teljesites", labelEn: "Fulfillment", fieldPath: "header.fulfillment_date" },
  { id: "header.due_date", x: 245, y: 256, fontSize: 9, estWidth: 80, category: "header", label: "Fiz. hatarido", labelEn: "Due Date", fieldPath: "header.due_date" },
  { id: "header.currency", x: 350, y: 256, fontSize: 9, estWidth: 35, category: "header", label: "Penznem", labelEn: "Currency", fieldPath: "header.currency" },
  { id: "header.payment_method", x: 420, y: 256, fontSize: 9, estWidth: 80, category: "header", label: "Fizetesi mod", labelEn: "Payment Method", fieldPath: "header.payment_method" },
  { id: "totals.net_total", x: 440, y: 455, fontSize: 10, estWidth: 105, category: "totals", label: "Netto osszesen", labelEn: "Net Total", fieldPath: "totals.net_total" },
  { id: "totals.vat_total", x: 440, y: 480, fontSize: 10, estWidth: 105, category: "totals", label: "AFA osszesen", labelEn: "VAT Total", fieldPath: "totals.vat_total" },
  { id: "totals.gross_total", x: 430, y: 512, fontSize: 13, estWidth: 115, category: "totals", label: "Brutto osszesen", labelEn: "Gross Total", fieldPath: "totals.gross_total" },
];

export function lineItemFields(lineIndex: number): FieldLayout[] {
  const y = 335 + lineIndex * 35;
  const prefix = `line_items.${lineIndex}`;
  return [
    { id: `${prefix}.description`, x: 65, y, fontSize: 9, estWidth: 230, category: "line_item", label: "Megnevezes", labelEn: "Description", fieldPath: `${prefix}.description`, lineIndex },
    { id: `${prefix}.quantity`, x: 288, y, fontSize: 9, estWidth: 30, category: "line_item", label: "Mennyiseg", labelEn: "Qty", fieldPath: `${prefix}.quantity`, lineIndex },
    { id: `${prefix}.net_amount`, x: 355, y, fontSize: 9, estWidth: 55, category: "line_item", label: "Netto", labelEn: "Net", fieldPath: `${prefix}.net_amount`, lineIndex },
    { id: `${prefix}.vat_rate`, x: 435, y, fontSize: 9, estWidth: 30, category: "line_item", label: "AFA %", labelEn: "VAT %", fieldPath: `${prefix}.vat_rate`, lineIndex },
    { id: `${prefix}.gross_amount`, x: 495, y, fontSize: 9, estWidth: 55, category: "line_item", label: "Brutto", labelEn: "Gross", fieldPath: `${prefix}.gross_amount`, lineIndex },
  ];
}

export function getAllFields(lineCount: number): FieldLayout[] {
  const lines: FieldLayout[] = [];
  for (let i = 0; i < Math.min(lineCount, 6); i++) {
    lines.push(...lineItemFields(i));
  }
  return [...STATIC_FIELDS, ...lines];
}

export function resolvePath(obj: Record<string, unknown>, path: string): string {
  const parts = path.split(".");
  let current: unknown = obj;
  for (const part of parts) {
    if (current == null) return "";
    if (Array.isArray(current)) {
      current = current[parseInt(part, 10)];
    } else if (typeof current === "object") {
      current = (current as Record<string, unknown>)[part];
    } else {
      return "";
    }
  }
  if (current == null) return "";
  return typeof current === "number" ? current.toLocaleString("hu-HU") : String(current);
}
