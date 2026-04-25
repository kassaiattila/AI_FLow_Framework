/**
 * AIFlow ExtractedFieldsCard — Sprint Q / S136.
 *
 * Renders the ``output_data.extracted_fields`` payload produced by
 * Sprint Q's invoice_processor wiring (S135). Each attachment becomes
 * its own sub-card with vendor / buyer / header / line items / totals
 * and a confidence + cost chip.
 *
 * Renders nothing when the payload is empty or absent (avoids the
 * empty-card flash on flag-off runs).
 */

import { useTranslate } from "../lib/i18n";

export interface ExtractedParty {
  name?: string;
  tax_id?: string;
}

export interface ExtractedHeader {
  invoice_number?: string;
  currency?: string;
  issue_date?: string;
  due_date?: string;
}

export interface ExtractedLineItem {
  description?: string;
  quantity?: number;
  unit_price?: number;
  total?: number;
}

export interface ExtractedTotals {
  net_total?: number;
  vat_total?: number;
  gross_total?: number;
}

export interface ExtractedInvoice {
  vendor?: ExtractedParty;
  buyer?: ExtractedParty;
  header?: ExtractedHeader;
  line_items?: ExtractedLineItem[];
  totals?: ExtractedTotals;
  extraction_confidence?: number;
  extraction_time_ms?: number;
  cost_usd?: number;
  error?: string;
}

interface ExtractedFieldsCardProps {
  extractedFields: Record<string, ExtractedInvoice> | null | undefined;
}

function ConfidenceBadge({ value }: { value: number | undefined }) {
  if (value === undefined || value === null) return null;
  const pct = Math.round(value * 100);
  const tone =
    pct >= 80
      ? "bg-emerald-50 text-emerald-700 ring-emerald-600/20 dark:bg-emerald-500/10 dark:text-emerald-300"
      : pct >= 50
        ? "bg-amber-50 text-amber-700 ring-amber-600/30 dark:bg-amber-500/10 dark:text-amber-200"
        : "bg-rose-50 text-rose-700 ring-rose-600/20 dark:bg-rose-500/10 dark:text-rose-300";
  return (
    <span
      className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${tone}`}
    >
      {pct}%
    </span>
  );
}

function PartyBlock({
  label,
  party,
}: {
  label: string;
  party: ExtractedParty | undefined;
}) {
  if (!party || (!party.name && !party.tax_id)) return null;
  return (
    <div className="flex-1">
      <dt className="mb-0.5 text-[10px] font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
        {label}
      </dt>
      <dd className="text-sm text-gray-900 dark:text-gray-100">
        <div className="font-medium">{party.name ?? "—"}</div>
        {party.tax_id && (
          <div className="font-mono text-xs text-gray-500 dark:text-gray-400">
            {party.tax_id}
          </div>
        )}
      </dd>
    </div>
  );
}

function InvoiceBlock({
  filename,
  invoice,
}: {
  filename: string;
  invoice: ExtractedInvoice;
}) {
  const translate = useTranslate();

  if (invoice.error) {
    return (
      <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-300">
        <div className="font-mono text-xs">{filename}</div>
        <div className="mt-1">{invoice.error}</div>
      </div>
    );
  }

  const header = invoice.header ?? {};
  const totals = invoice.totals ?? {};
  const items = invoice.line_items ?? [];
  const currency = header.currency ?? "";

  const fmt = (n: number | undefined) => {
    if (n === undefined || n === null) return "—";
    return `${n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${currency}`.trim();
  };

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
      {/* Header row */}
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <span className="font-mono text-xs text-gray-500 dark:text-gray-400">
          {filename}
        </span>
        <span
          data-testid="extracted-fields-invoice-number"
          className="font-mono text-sm font-semibold text-gray-900 dark:text-gray-100"
        >
          {header.invoice_number ?? "—"}
        </span>
        <ConfidenceBadge value={invoice.extraction_confidence} />
        {typeof invoice.cost_usd === "number" && invoice.cost_usd > 0 && (
          <span className="ml-auto font-mono text-xs text-gray-500 dark:text-gray-400">
            ${invoice.cost_usd.toFixed(4)}
          </span>
        )}
      </div>

      {/* Vendor / Buyer */}
      <dl className="mb-4 flex gap-4">
        <PartyBlock
          label={translate("aiflow.emails.extractedFields.vendor")}
          party={invoice.vendor}
        />
        <PartyBlock
          label={translate("aiflow.emails.extractedFields.buyer")}
          party={invoice.buyer}
        />
      </dl>

      {/* Header fields */}
      <dl className="mb-4 grid grid-cols-2 gap-x-4 gap-y-2 text-sm sm:grid-cols-3">
        <div>
          <dt className="text-[10px] font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
            {translate("aiflow.emails.extractedFields.currency")}
          </dt>
          <dd className="font-mono text-gray-900 dark:text-gray-100">
            {header.currency ?? "—"}
          </dd>
        </div>
        <div>
          <dt className="text-[10px] font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
            {translate("aiflow.emails.extractedFields.issueDate")}
          </dt>
          <dd className="font-mono text-gray-900 dark:text-gray-100">
            {header.issue_date ?? "—"}
          </dd>
        </div>
        <div>
          <dt className="text-[10px] font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
            {translate("aiflow.emails.extractedFields.dueDate")}
          </dt>
          <dd className="font-mono text-gray-900 dark:text-gray-100">
            {header.due_date ?? "—"}
          </dd>
        </div>
      </dl>

      {/* Line items (top 3, with `<details>` expansion for the rest) */}
      {items.length > 0 && (
        <div className="mb-4">
          <div className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
            {translate("aiflow.emails.extractedFields.lineItems")} (
            {items.length})
          </div>
          <ul className="divide-y divide-gray-100 text-sm dark:divide-gray-700">
            {items.slice(0, 3).map((li, idx) => (
              <li
                key={idx}
                className="flex items-baseline justify-between gap-3 py-1"
              >
                <span className="flex-1 truncate">{li.description ?? "—"}</span>
                <span className="font-mono tabular-nums text-gray-900 dark:text-gray-100">
                  {fmt(li.total)}
                </span>
              </li>
            ))}
            {items.length > 3 && (
              <details className="mt-1 text-xs text-gray-600 dark:text-gray-400">
                <summary className="cursor-pointer select-none py-1">
                  {translate("aiflow.emails.extractedFields.showMore", {
                    count: items.length - 3,
                  })}
                </summary>
                <ul className="divide-y divide-gray-100 dark:divide-gray-700">
                  {items.slice(3).map((li, idx) => (
                    <li
                      key={idx + 3}
                      className="flex items-baseline justify-between gap-3 py-1"
                    >
                      <span className="flex-1 truncate">
                        {li.description ?? "—"}
                      </span>
                      <span className="font-mono tabular-nums text-gray-900 dark:text-gray-100">
                        {fmt(li.total)}
                      </span>
                    </li>
                  ))}
                </ul>
              </details>
            )}
          </ul>
        </div>
      )}

      {/* Totals */}
      <dl className="grid grid-cols-3 gap-2 border-t border-gray-200 pt-3 text-sm dark:border-gray-700">
        <div>
          <dt className="text-[10px] font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
            {translate("aiflow.emails.extractedFields.netTotal")}
          </dt>
          <dd className="font-mono tabular-nums text-gray-900 dark:text-gray-100">
            {fmt(totals.net_total)}
          </dd>
        </div>
        <div>
          <dt className="text-[10px] font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
            {translate("aiflow.emails.extractedFields.vatTotal")}
          </dt>
          <dd className="font-mono tabular-nums text-gray-900 dark:text-gray-100">
            {fmt(totals.vat_total)}
          </dd>
        </div>
        <div>
          <dt className="text-[10px] font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
            {translate("aiflow.emails.extractedFields.grossTotal")}
          </dt>
          <dd
            data-testid="extracted-fields-gross-total"
            className="font-mono text-base font-semibold tabular-nums text-gray-900 dark:text-gray-100"
          >
            {fmt(totals.gross_total)}
          </dd>
        </div>
      </dl>
    </div>
  );
}

export function ExtractedFieldsCard({
  extractedFields,
}: ExtractedFieldsCardProps) {
  const translate = useTranslate();

  if (!extractedFields) return null;
  const entries = Object.entries(extractedFields);
  if (entries.length === 0) return null;

  return (
    <div
      data-testid="extracted-fields-card"
      className="mb-4 rounded-xl border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-900"
    >
      <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
        {translate("aiflow.emails.extractedFields.title")}
      </h3>
      <div className="space-y-3">
        {entries.map(([filename, invoice]) => (
          <InvoiceBlock key={filename} filename={filename} invoice={invoice} />
        ))}
      </div>
    </div>
  );
}
