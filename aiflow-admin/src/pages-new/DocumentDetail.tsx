/**
 * AIFlow DocumentDetail — read-only document detail view.
 * Route: /documents/:id/show
 * Shows header, vendor, buyer, line items, validation section.
 */

import { useParams, useNavigate } from "react-router-dom";
import { useTranslate } from "../lib/i18n";
import { useApi } from "../lib/hooks";
import { PageLayout } from "../layout/PageLayout";
import { LoadingState } from "../components-new/LoadingState";
import { ErrorState } from "../components-new/ErrorState";

interface DocumentDetailData {
  id: string;
  source_file: string;
  direction: string;
  config_name: string;
  vendor_name: string;
  vendor_address: string;
  vendor_tax_number: string;
  buyer_name: string;
  buyer_address: string;
  buyer_tax_number: string;
  invoice_number: string;
  invoice_date: string;
  currency: string;
  net_total: number;
  vat_total: number;
  gross_total: number;
  is_valid: boolean;
  validation_errors: string[];
  confidence_score: number | null;
  parser_used: string;
  verified: boolean;
  verified_by: string;
  verified_at: string | null;
  line_items?: LineItem[];
  created_at: string;
  source: string;
}

interface LineItem {
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

function fileName(path: string): string {
  return path.split(/[/\\]/).pop() ?? path;
}

function InfoCard({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
      <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
        {label}
      </h3>
      {children}
    </div>
  );
}

function Field({ label, value }: { label: string; value: string | number | null | undefined }) {
  return (
    <div className="mb-2">
      <dt className="text-xs font-medium text-gray-500 dark:text-gray-400">{label}</dt>
      <dd className="text-sm font-medium text-gray-900 dark:text-gray-100">{value ?? "—"}</dd>
    </div>
  );
}

export function DocumentDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const translate = useTranslate();

  const { data: doc, loading, error, refetch } = useApi<DocumentDetailData>(
    id ? `/api/v1/documents/by-id/${id}` : null,
  );

  // Also fetch line items from the list endpoint (by-id doesn't include them)
  const { data: listData } = useApi<{ documents: Array<{ id: string; line_items: LineItem[] }> }>(
    id ? `/api/v1/documents?limit=100` : null,
  );
  const lineItems = listData?.documents?.find(d => d.id === id)?.line_items ?? [];

  if (loading) {
    return <PageLayout titleKey="aiflow.documents.title"><LoadingState fullPage /></PageLayout>;
  }

  if (error || !doc) {
    return <PageLayout titleKey="aiflow.documents.title"><ErrorState error={error || "Not found"} onRetry={refetch} /></PageLayout>;
  }

  const confidence = doc.confidence_score != null
    ? doc.confidence_score <= 1 ? Math.round(doc.confidence_score * 100) : Math.round(doc.confidence_score)
    : null;

  return (
    <PageLayout titleKey="aiflow.documents.title" source={doc.source}>
      {/* Back + File name */}
      <button
        onClick={() => navigate("/documents")}
        className="mb-3 inline-flex items-center gap-1 text-sm font-medium text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
      >
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
        </svg>
        {translate("aiflow.documents.title")}
      </button>

      <div className="mb-4 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-gray-900 dark:text-gray-100">{fileName(doc.source_file)}</h2>
          <p className="text-sm text-gray-500">{doc.invoice_number} &middot; {doc.invoice_date}</p>
        </div>
        <div className="flex items-center gap-2">
          <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${
            doc.is_valid
              ? "bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-400"
              : "bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-400"
          }`}>
            {doc.is_valid ? "Valid" : "Invalid"}
          </span>
          {confidence !== null && (
            <span className={`text-sm font-semibold ${
              confidence >= 90 ? "text-green-600" : confidence >= 70 ? "text-amber-600" : "text-red-600"
            }`}>
              {confidence}%
            </span>
          )}
          <button
            onClick={() => navigate(`/documents/${id}/verify`)}
            className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-600"
          >
            {translate("aiflow.documents.valid")} / Verify
          </button>
        </div>
      </div>

      {/* 3-column grid: Header, Vendor, Buyer */}
      <div className="mb-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <InfoCard label={translate("aiflow.documents.headerSection")}>
          <Field label={translate("aiflow.documents.invoiceNumber")} value={doc.invoice_number} />
          <Field label={translate("aiflow.documents.date")} value={doc.invoice_date} />
          <Field label={translate("aiflow.documents.currency")} value={doc.currency} />
          <Field label={translate("aiflow.documents.parser")} value={doc.parser_used} />
          <Field label="Direction" value={doc.direction} />
        </InfoCard>

        <InfoCard label={translate("aiflow.documents.vendorSection")}>
          <Field label={translate("aiflow.documents.name")} value={doc.vendor_name} />
          <Field label={translate("aiflow.documents.address")} value={doc.vendor_address} />
          <Field label={translate("aiflow.documents.taxNumber")} value={doc.vendor_tax_number} />
        </InfoCard>

        <InfoCard label={translate("aiflow.documents.buyerSection")}>
          <Field label={translate("aiflow.documents.name")} value={doc.buyer_name} />
          <Field label={translate("aiflow.documents.address")} value={doc.buyer_address} />
          <Field label={translate("aiflow.documents.taxNumber")} value={doc.buyer_tax_number} />
        </InfoCard>
      </div>

      {/* Totals */}
      <div className="mb-4 grid grid-cols-1 gap-4 md:grid-cols-3">
        <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
          <p className="text-xs font-medium text-gray-500">{translate("aiflow.documents.netTotal")}</p>
          <p className="mt-1 text-xl font-bold text-gray-900 dark:text-gray-100">
            {doc.net_total?.toLocaleString()} {doc.currency}
          </p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
          <p className="text-xs font-medium text-gray-500">VAT</p>
          <p className="mt-1 text-xl font-bold text-gray-900 dark:text-gray-100">
            {doc.vat_total?.toLocaleString()} {doc.currency}
          </p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
          <p className="text-xs font-medium text-gray-500">{translate("aiflow.documents.grossTotal")}</p>
          <p className="mt-1 text-xl font-bold text-green-600 dark:text-green-400">
            {doc.gross_total?.toLocaleString()} {doc.currency}
          </p>
        </div>
      </div>

      {/* Line Items */}
      {lineItems.length > 0 && (
        <div className="mb-4 rounded-xl border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-900">
          <div className="border-b border-gray-100 px-4 py-3 dark:border-gray-800">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
              {translate("aiflow.documents.lineItems")} ({lineItems.length})
            </h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 text-left dark:border-gray-800">
                  <th className="px-4 py-2 text-xs font-medium uppercase text-gray-500">#</th>
                  <th className="px-4 py-2 text-xs font-medium uppercase text-gray-500">{translate("aiflow.documents.description")}</th>
                  <th className="px-4 py-2 text-xs font-medium uppercase text-gray-500">{translate("aiflow.documents.quantity")}</th>
                  <th className="px-4 py-2 text-xs font-medium uppercase text-gray-500">{translate("aiflow.documents.unit")}</th>
                  <th className="px-4 py-2 text-xs font-medium uppercase text-gray-500 text-right">{translate("aiflow.documents.unitPrice")}</th>
                  <th className="px-4 py-2 text-xs font-medium uppercase text-gray-500 text-right">{translate("aiflow.documents.netAmount")}</th>
                  <th className="px-4 py-2 text-xs font-medium uppercase text-gray-500 text-right">{translate("aiflow.documents.vatRate")}</th>
                  <th className="px-4 py-2 text-xs font-medium uppercase text-gray-500 text-right">{translate("aiflow.documents.grossAmount")}</th>
                </tr>
              </thead>
              <tbody>
                {lineItems.map((li) => (
                  <tr key={li.line_number} className="border-b border-gray-50 dark:border-gray-800">
                    <td className="px-4 py-2 text-gray-500">{li.line_number}</td>
                    <td className="px-4 py-2 font-medium text-gray-900 dark:text-gray-100">{li.description}</td>
                    <td className="px-4 py-2 text-gray-600 dark:text-gray-400">{li.quantity}</td>
                    <td className="px-4 py-2 text-gray-600 dark:text-gray-400">{li.unit}</td>
                    <td className="px-4 py-2 text-right text-gray-600 dark:text-gray-400">{li.unit_price?.toLocaleString()}</td>
                    <td className="px-4 py-2 text-right text-gray-600 dark:text-gray-400">{li.net_amount?.toLocaleString()}</td>
                    <td className="px-4 py-2 text-right text-gray-600 dark:text-gray-400">{li.vat_rate}%</td>
                    <td className="px-4 py-2 text-right font-medium text-gray-900 dark:text-gray-100">{li.gross_amount?.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Validation */}
      {doc.validation_errors && doc.validation_errors.length > 0 && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 dark:border-red-800 dark:bg-red-900/20">
          <h3 className="mb-2 text-sm font-semibold text-red-700 dark:text-red-400">
            {translate("aiflow.documents.errors")}
          </h3>
          <ul className="space-y-1">
            {doc.validation_errors.map((err, i) => (
              <li key={i} className="text-xs text-red-600 dark:text-red-400">{err}</li>
            ))}
          </ul>
        </div>
      )}
    </PageLayout>
  );
}
