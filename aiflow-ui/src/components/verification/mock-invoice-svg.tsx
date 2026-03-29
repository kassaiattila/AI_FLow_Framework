import type { ProcessedInvoice } from "@/lib/types";
import { PAGE } from "@/lib/document-layout";

/** Renders a ProcessedInvoice as an A4-like SVG document */
export function MockInvoiceSvg({ invoice }: { invoice: ProcessedInvoice }) {
  const fmt = (n: number) => n.toLocaleString("hu-HU");

  return (
    <svg viewBox={`0 0 ${PAGE.w} ${PAGE.h}`} className="w-full h-full" xmlns="http://www.w3.org/2000/svg">
      {/* Page */}
      <rect width={PAGE.w} height={PAGE.h} fill="#f8f8f8" />
      <rect x="18" y="18" width="559" height="806" fill="#fff" stroke="#ddd" strokeWidth="0.5" rx="1" />

      {/* Logo area */}
      <rect x="30" y="28" width="100" height="30" fill="#f0f9ff" stroke="#bfdbfe" strokeWidth="0.5" rx="3" />
      <text x="48" y="48" fontSize="10" fontWeight="bold" fill="#1e40af" fontFamily="sans-serif">
        {invoice.vendor.name.split(" ")[0] || "DOC"}
      </text>

      {/* Title */}
      <text x="298" y="42" fontSize="18" fontWeight="bold" fill="#111" fontFamily="sans-serif" textAnchor="middle">
        SZAMLA
      </text>

      {/* Invoice number */}
      <text x="440" y="52" fontSize="10" fill="#444" fontFamily="monospace">
        {invoice.header.invoice_number}
      </text>

      {/* Divider */}
      <line x1="30" y1="72" x2="565" y2="72" stroke="#e5e7eb" strokeWidth="0.5" />

      {/* VENDOR label */}
      <text x="35" y="90" fontSize="7" fill="#999" fontFamily="sans-serif" fontWeight="bold" letterSpacing="1">SZALLITO</text>
      {/* Vendor fields — positions match STATIC_FIELDS exactly */}
      <text x="35" y="110" fontSize="11" fontWeight="600" fill="#111" fontFamily="sans-serif">{invoice.vendor.name}</text>
      <text x="35" y="130" fontSize="9" fill="#444" fontFamily="sans-serif">{invoice.vendor.address || "\u2014"}</text>
      <text x="35" y="155" fontSize="8" fill="#666" fontFamily="monospace">
        <tspan fill="#999">Ado: </tspan>{invoice.vendor.tax_number || "\u2014"}
      </text>
      <text x="35" y="178" fontSize="8" fill="#666" fontFamily="monospace">
        <tspan fill="#999">Bankszla: </tspan>{invoice.vendor.bank_account || "\u2014"}
      </text>
      <text x="35" y="201" fontSize="8" fill="#666" fontFamily="sans-serif">{invoice.vendor.bank_name || ""}</text>

      {/* BUYER label */}
      <text x="335" y="90" fontSize="7" fill="#999" fontFamily="sans-serif" fontWeight="bold" letterSpacing="1">VEVO</text>
      {/* Buyer fields */}
      <text x="335" y="110" fontSize="11" fontWeight="600" fill="#111" fontFamily="sans-serif">{invoice.buyer.name}</text>
      <text x="335" y="130" fontSize="9" fill="#444" fontFamily="sans-serif">{invoice.buyer.address || "\u2014"}</text>
      <text x="335" y="155" fontSize="8" fill="#666" fontFamily="monospace">
        <tspan fill="#999">Ado: </tspan>{invoice.buyer.tax_number || "\u2014"}
      </text>

      {/* Divider */}
      <line x1="30" y1="220" x2="565" y2="220" stroke="#e5e7eb" strokeWidth="0.5" />

      {/* Header fields row — labels */}
      <text x="35" y="240" fontSize="7" fill="#999" fontFamily="sans-serif">Kelt</text>
      <text x="140" y="240" fontSize="7" fill="#999" fontFamily="sans-serif">Teljesites</text>
      <text x="245" y="240" fontSize="7" fill="#999" fontFamily="sans-serif">Fiz. hatarido</text>
      <text x="350" y="240" fontSize="7" fill="#999" fontFamily="sans-serif">Penznem</text>
      <text x="420" y="240" fontSize="7" fill="#999" fontFamily="sans-serif">Fizetesi mod</text>

      {/* Header fields row — values (positions match STATIC_FIELDS) */}
      <text x="35" y="256" fontSize="9" fill="#111" fontFamily="monospace">{invoice.header.invoice_date}</text>
      <text x="140" y="256" fontSize="9" fill="#111" fontFamily="monospace">{invoice.header.fulfillment_date || "\u2014"}</text>
      <text x="245" y="256" fontSize="9" fill="#111" fontFamily="monospace">{invoice.header.due_date || "\u2014"}</text>
      <text x="350" y="256" fontSize="9" fontWeight="600" fill="#111" fontFamily="monospace">{invoice.header.currency}</text>
      <text x="420" y="256" fontSize="9" fill="#111" fontFamily="sans-serif">{invoice.header.payment_method || "\u2014"}</text>

      {/* Divider */}
      <line x1="30" y1="270" x2="565" y2="270" stroke="#e5e7eb" strokeWidth="0.5" />

      {/* Table header */}
      <rect x="30" y="278" width="535" height="20" fill="#f8fafc" />
      <text x="40" y="292" fontSize="7" fill="#666" fontWeight="bold" fontFamily="sans-serif">#</text>
      <text x="65" y="292" fontSize="7" fill="#666" fontWeight="bold" fontFamily="sans-serif">MEGNEVEZES</text>
      <text x="288" y="292" fontSize="7" fill="#666" fontWeight="bold" fontFamily="sans-serif">MENNY.</text>
      <text x="355" y="292" fontSize="7" fill="#666" fontWeight="bold" fontFamily="sans-serif">NETTO</text>
      <text x="435" y="292" fontSize="7" fill="#666" fontWeight="bold" fontFamily="sans-serif">AFA%</text>
      <text x="495" y="292" fontSize="7" fill="#666" fontWeight="bold" fontFamily="sans-serif">BRUTTO</text>
      <line x1="30" y1="300" x2="565" y2="300" stroke="#e5e7eb" strokeWidth="0.5" />

      {/* Line items — positions match lineItemFields() exactly */}
      {invoice.line_items.slice(0, 6).map((item, i) => {
        const y = 335 + i * 35;
        return (
          <g key={i}>
            <text x="40" y={y} fontSize="9" fill="#888" fontFamily="monospace">{item.line_number}</text>
            <text x="65" y={y} fontSize="9" fill="#111" fontFamily="sans-serif">{item.description}</text>
            <text x="288" y={y} fontSize="9" fill="#111" fontFamily="monospace">{item.quantity} {item.unit}</text>
            <text x="355" y={y} fontSize="9" fill="#111" fontFamily="monospace">{fmt(item.net_amount)}</text>
            <text x="435" y={y} fontSize="9" fill="#111" fontFamily="monospace">{item.vat_rate}%</text>
            <text x="495" y={y} fontSize="9" fontWeight="600" fill="#111" fontFamily="monospace">{fmt(item.gross_amount)}</text>
            {i < invoice.line_items.length - 1 && (
              <line x1="55" y1={y + 10} x2="565" y2={y + 10} stroke="#f1f5f9" strokeWidth="0.5" />
            )}
          </g>
        );
      })}

      {/* Totals divider */}
      <line x1="30" y1="420" x2="565" y2="420" stroke="#d1d5db" strokeWidth="0.5" />

      {/* Totals — positions match STATIC_FIELDS */}
      <text x="380" y="455" fontSize="9" fill="#666" fontFamily="sans-serif" textAnchor="end">Netto osszesen:</text>
      <text x="440" y="455" fontSize="10" fill="#111" fontFamily="monospace">{fmt(invoice.totals.net_total)} {invoice.header.currency}</text>

      <text x="380" y="480" fontSize="9" fill="#666" fontFamily="sans-serif" textAnchor="end">AFA:</text>
      <text x="440" y="480" fontSize="10" fill="#111" fontFamily="monospace">{fmt(invoice.totals.vat_total)} {invoice.header.currency}</text>

      <line x1="380" y1="490" x2="560" y2="490" stroke="#111" strokeWidth="1" />

      <text x="380" y="512" fontSize="10" fontWeight="bold" fill="#111" fontFamily="sans-serif" textAnchor="end">Brutto:</text>
      <text x="430" y="512" fontSize="13" fontWeight="bold" fill="#111" fontFamily="monospace">{fmt(invoice.totals.gross_total)} {invoice.header.currency}</text>

      {/* Footer */}
      <line x1="30" y1="740" x2="565" y2="740" stroke="#e5e7eb" strokeWidth="0.5" />
      <text x="298" y="758" fontSize="7" fill="#bbb" fontFamily="sans-serif" textAnchor="middle">
        {invoice.source_file} &middot; Parser: {invoice.parser_used}
      </text>
    </svg>
  );
}
