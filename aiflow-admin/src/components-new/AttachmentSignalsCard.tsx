/**
 * AIFlow AttachmentSignalsCard — UC3 Sprint O / S129.
 *
 * Renders the ``output_data.attachment_features`` payload that the
 * email-connector orchestrator produces when
 * ``AIFLOW_UC3_ATTACHMENT_INTENT__ENABLED=true`` (S127). Surfaces the
 * booleans + mime profile + top keyword buckets + boost indicator
 * (``classification_method`` carries ``+attachment_rule`` when the
 * S128 rule boost fired).
 *
 * Renders nothing when the payload is absent or when no attachments
 * were considered (avoids empty-card flash on body-only runs).
 */

import { useTranslate } from "../lib/i18n";

export interface AttachmentFeatures {
  invoice_number_detected?: boolean;
  total_value_detected?: boolean;
  table_count?: number;
  mime_profile?: string;
  keyword_buckets?: Record<string, number>;
  text_quality?: number;
  attachments_considered?: number;
  attachments_skipped?: number;
  // FU-7 — per-attachment processing cost (docling=$0, Azure DI per-page,
  // LLM vision per-image). Aggregated across all considered attachments.
  total_cost_usd?: number;
  total_pages_processed?: number;
}

interface AttachmentSignalsCardProps {
  features: AttachmentFeatures | null | undefined;
  classificationMethod?: string | null;
}

function Badge({ on, label }: { on: boolean; label: string }) {
  const tone = on
    ? "bg-emerald-50 text-emerald-700 ring-emerald-600/20 dark:bg-emerald-500/10 dark:text-emerald-300"
    : "bg-gray-50 text-gray-600 ring-gray-500/20 dark:bg-gray-700/40 dark:text-gray-400";
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${tone}`}
    >
      <span aria-hidden>{on ? "✓" : "○"}</span>
      {label}
    </span>
  );
}

function KeywordChip({ name, count }: { name: string; count: number }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-md bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700 ring-1 ring-inset ring-blue-600/20 dark:bg-blue-500/10 dark:text-blue-300">
      {name}
      <span className="rounded bg-blue-100 px-1 text-[10px] tabular-nums text-blue-800 dark:bg-blue-500/20 dark:text-blue-200">
        {count}
      </span>
    </span>
  );
}

export function AttachmentSignalsCard({
  features,
  classificationMethod,
}: AttachmentSignalsCardProps) {
  const translate = useTranslate();
  if (!features) return null;
  const considered = features.attachments_considered ?? 0;
  if (considered === 0) return null;

  const boosted = (classificationMethod ?? "").includes("attachment_rule");
  const buckets = features.keyword_buckets ?? {};
  const topBuckets = Object.entries(buckets)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 3);
  const quality = features.text_quality ?? 0;
  const qualityPct = `${Math.round(quality * 100)}%`;

  return (
    <div className="mb-4 rounded-xl border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-900">
      <div className="mb-3 flex flex-wrap items-center gap-3">
        <h3
          className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400"
          data-testid="attachment-signals-heading"
        >
          {translate("aiflow.emails.attachmentSignals.title")}
        </h3>
        {boosted && (
          <span
            data-testid="attachment-signals-boosted"
            className="inline-flex items-center gap-1 rounded-md bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-800 ring-1 ring-inset ring-amber-600/30 dark:bg-amber-500/10 dark:text-amber-200"
          >
            ★ {translate("aiflow.emails.attachmentSignals.boostedIndicator")}
          </span>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Badge
          on={Boolean(features.invoice_number_detected)}
          label={translate("aiflow.emails.attachmentSignals.invoiceNumberDetected")}
        />
        <Badge
          on={Boolean(features.total_value_detected)}
          label={translate("aiflow.emails.attachmentSignals.totalValueDetected")}
        />
      </div>

      <dl className="mt-4 grid grid-cols-2 gap-x-6 gap-y-2 text-sm sm:grid-cols-3">
        <div>
          <dt className="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
            {translate("aiflow.emails.attachmentSignals.mimeProfile")}
          </dt>
          <dd className="font-mono text-gray-900 dark:text-gray-100">
            {features.mime_profile ?? "—"}
          </dd>
        </div>
        <div>
          <dt className="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
            {translate("aiflow.emails.attachmentSignals.tableCount")}
          </dt>
          <dd className="tabular-nums text-gray-900 dark:text-gray-100">
            {features.table_count ?? 0}
          </dd>
        </div>
        <div>
          <dt className="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
            {translate("aiflow.emails.attachmentSignals.textQuality")}
          </dt>
          <dd className="tabular-nums text-gray-900 dark:text-gray-100">{qualityPct}</dd>
        </div>
        {typeof features.total_cost_usd === "number" && features.total_cost_usd > 0 && (
          <div data-testid="attachment-signals-cost">
            <dt className="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
              {translate("aiflow.emails.attachmentSignals.costUsd")}
            </dt>
            <dd className="tabular-nums text-gray-900 dark:text-gray-100">
              ${features.total_cost_usd.toFixed(4)}
              {typeof features.total_pages_processed === "number" &&
                features.total_pages_processed > 0 && (
                  <span className="ml-1 text-xs text-gray-500 dark:text-gray-400">
                    ({features.total_pages_processed}{" "}
                    {translate("aiflow.emails.attachmentSignals.pages")})
                  </span>
                )}
            </dd>
          </div>
        )}
      </dl>

      {topBuckets.length > 0 && (
        <div className="mt-4">
          <div className="mb-1 text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
            {translate("aiflow.emails.attachmentSignals.keywordBuckets")}
          </div>
          <div className="flex flex-wrap gap-2">
            {topBuckets.map(([name, count]) => (
              <KeywordChip key={name} name={name} count={count} />
            ))}
          </div>
        </div>
      )}

      <p className="mt-3 text-xs text-gray-500 dark:text-gray-400">
        {translate("aiflow.emails.attachmentSignals.consideredSkipped", {
          considered,
          skipped: features.attachments_skipped ?? 0,
        })}
      </p>
    </div>
  );
}
