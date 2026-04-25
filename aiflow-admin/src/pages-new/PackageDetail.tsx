/**
 * AIFlow PackageDetail — read-only viewer for a v2 IntakePackage.
 * Route: /packages/:id
 * Source: 01_PLAN/110_USE_CASE_FIRST_REPLAN.md §4 Sprint I / UC1 S97.
 *
 * Surfaces the aggregate returned by
 * `GET /api/v1/document-extractor/packages/{id}` with a parser-used badge,
 * extraction JSON tab (empty in S97 until extraction persistence lands in
 * S97.5), routing tab, and PII tab. A Langfuse trace link is rendered only
 * when `VITE_LANGFUSE_HOST` is set.
 */

import { useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { PageLayout } from "../layout/PageLayout";
import { LoadingState } from "../components-new/LoadingState";
import { ErrorState } from "../components-new/ErrorState";
import { useApi } from "../lib/hooks";

type ParserName =
  | "docling_standard"
  | "unstructured_fast"
  | "azure_document_intelligence"
  | "skipped_policy"
  | "unknown";

interface PackageFile {
  file_id: string;
  file_name: string;
  mime_type: string;
  size_bytes: number;
  sha256: string;
  sequence_index: number | null;
}

interface RoutingDecisionView {
  id: string;
  file_id: string;
  chosen_parser: string;
  reason: string;
  signals: Record<string, unknown>;
  fallback_chain: string[];
  cost_estimate: number;
  decided_at: string;
}

interface ExtractionView {
  extraction_id?: string;
  file_id?: string;
  parser_used?: string;
  extracted_text?: string;
  structured_fields?: Record<string, unknown>;
  confidence?: number;
  langfuse_trace_id?: string | null;
  pii_redaction_report_id?: string | null;
}

interface PackageDetailData {
  package_id: string;
  tenant_id: string;
  source_type: string;
  status: string;
  created_at: string;
  files: PackageFile[];
  routing_decisions: RoutingDecisionView[];
  extractions: ExtractionView[];
  source: string;
}

const BADGE_STYLES: Record<ParserName, string> = {
  docling_standard:
    "bg-indigo-50 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300",
  unstructured_fast:
    "bg-sky-50 text-sky-700 dark:bg-sky-900/30 dark:text-sky-300",
  azure_document_intelligence:
    "bg-violet-50 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300",
  skipped_policy:
    "bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300",
  unknown: "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300",
};

function parserVariant(name: string | undefined | null): ParserName {
  if (!name) return "unknown";
  if (name in BADGE_STYLES) return name as ParserName;
  return "unknown";
}

function ParserBadge({ parser }: { parser: string | undefined | null }) {
  const variant = parserVariant(parser);
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${BADGE_STYLES[variant]}`}
      data-testid="parser-badge"
      data-parser={variant}
    >
      {parser ?? "unknown"}
    </span>
  );
}

function langfuseTraceUrl(traceId: string): string | null {
  const host = import.meta.env.VITE_LANGFUSE_HOST;
  if (!host) return null;
  const trimmed = String(host).replace(/\/$/, "");
  return `${trimmed}/trace/${encodeURIComponent(traceId)}`;
}

type TabKey = "overview" | "extraction" | "routing" | "pii";

const TABS: { key: TabKey; label: string }[] = [
  { key: "overview", label: "Overview" },
  { key: "extraction", label: "Extraction JSON" },
  { key: "routing", label: "Routing" },
  { key: "pii", label: "PII" },
];

export function PackageDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [tab, setTab] = useState<TabKey>("overview");

  const { data, loading, error, refetch } = useApi<PackageDetailData>(
    id ? `/api/v1/document-extractor/packages/${id}` : null,
  );

  const primaryParser = useMemo<string>(() => {
    if (!data) return "unknown";
    const parsers = data.extractions
      .map((e) => e.parser_used)
      .filter((p): p is string => Boolean(p));
    if (parsers.length > 0) return parsers[0];
    const routed = data.routing_decisions.map((d) => d.chosen_parser);
    if (routed.length > 0) return routed[0];
    return "unknown";
  }, [data]);

  if (loading) {
    return (
      <PageLayout titleKey="aiflow.packageDetail.title">
        <LoadingState fullPage />
      </PageLayout>
    );
  }

  if (error || !data) {
    return (
      <PageLayout titleKey="aiflow.packageDetail.title">
        <ErrorState error={error || "Package not found"} onRetry={refetch} />
      </PageLayout>
    );
  }

  return (
    <PageLayout titleKey="aiflow.packageDetail.title" source={data.source}>
      <button
        onClick={() => navigate("/documents")}
        className="mb-3 inline-flex items-center gap-1 text-sm font-medium text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
      >
        <svg
          className="h-4 w-4"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M15 19l-7-7 7-7"
          />
        </svg>
        Back
      </button>

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <h2 className="text-lg font-bold text-gray-900 dark:text-gray-100">
          {data.package_id}
        </h2>
        <ParserBadge parser={primaryParser} />
        <span className="rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-700 dark:bg-gray-800 dark:text-gray-300">
          {data.status}
        </span>
        <span className="text-sm text-gray-500">
          {data.source_type} · {data.files.length} file
          {data.files.length === 1 ? "" : "s"}
        </span>
      </div>

      <div className="mb-4 border-b border-gray-200 dark:border-gray-800">
        <nav className="-mb-px flex gap-4">
          {TABS.map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`border-b-2 px-1 py-2 text-sm font-medium transition ${
                tab === t.key
                  ? "border-brand-500 text-brand-600 dark:text-brand-400"
                  : "border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
              }`}
              data-testid={`tab-${t.key}`}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </div>

      {tab === "overview" && <OverviewTab data={data} />}
      {tab === "extraction" && <ExtractionTab extractions={data.extractions} />}
      {tab === "routing" && <RoutingTab decisions={data.routing_decisions} />}
      {tab === "pii" && <PiiTab extractions={data.extractions} />}
    </PageLayout>
  );
}

function OverviewTab({ data }: { data: PackageDetailData }) {
  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-gray-500">
          Package
        </h3>
        <dl className="grid grid-cols-1 gap-2 md:grid-cols-2">
          <Field label="Tenant" value={data.tenant_id} />
          <Field label="Source" value={data.source_type} />
          <Field label="Status" value={data.status} />
          <Field label="Created" value={data.created_at} />
        </dl>
      </div>
      <div className="rounded-xl border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-900">
        <div className="border-b border-gray-100 px-4 py-3 dark:border-gray-800">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
            Files ({data.files.length})
          </h3>
        </div>
        {data.files.length === 0 ? (
          <p className="px-4 py-3 text-sm text-gray-500">No files.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 text-left dark:border-gray-800">
                <th className="px-4 py-2 text-xs font-medium uppercase text-gray-500">
                  File
                </th>
                <th className="px-4 py-2 text-xs font-medium uppercase text-gray-500">
                  MIME
                </th>
                <th className="px-4 py-2 text-xs font-medium uppercase text-gray-500 text-right">
                  Size
                </th>
              </tr>
            </thead>
            <tbody>
              {data.files.map((f) => (
                <tr
                  key={f.file_id}
                  className="border-b border-gray-50 dark:border-gray-800"
                >
                  <td className="px-4 py-2 font-medium text-gray-900 dark:text-gray-100">
                    {f.file_name}
                  </td>
                  <td className="px-4 py-2 text-gray-600 dark:text-gray-400">
                    {f.mime_type}
                  </td>
                  <td className="px-4 py-2 text-right text-gray-600 dark:text-gray-400">
                    {f.size_bytes.toLocaleString()} B
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function ExtractionTab({ extractions }: { extractions: ExtractionView[] }) {
  if (extractions.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-gray-300 bg-gray-50 p-6 text-center text-sm text-gray-500 dark:border-gray-700 dark:bg-gray-900/40">
        No persisted extractions yet. Extraction persistence is queued for
        S97.5.
      </div>
    );
  }
  return (
    <div className="space-y-4">
      {extractions.map((ex, idx) => (
        <div
          key={ex.extraction_id ?? idx}
          className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900"
        >
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <ParserBadge parser={ex.parser_used} />
            {typeof ex.confidence === "number" && (
              <span className="text-xs text-gray-500">
                confidence {(ex.confidence * 100).toFixed(0)}%
              </span>
            )}
            {ex.langfuse_trace_id &&
              (() => {
                const url = langfuseTraceUrl(ex.langfuse_trace_id);
                return url ? (
                  <a
                    href={url}
                    target="_blank"
                    rel="noreferrer noopener"
                    className="text-xs font-medium text-brand-600 hover:underline"
                    data-testid="langfuse-link"
                  >
                    Langfuse trace →
                  </a>
                ) : null;
              })()}
          </div>
          <pre className="overflow-x-auto rounded-lg bg-gray-50 p-3 text-xs text-gray-800 dark:bg-gray-950 dark:text-gray-200">
            <code>{JSON.stringify(ex, null, 2)}</code>
          </pre>
        </div>
      ))}
    </div>
  );
}

function RoutingTab({ decisions }: { decisions: RoutingDecisionView[] }) {
  if (decisions.length === 0) {
    return (
      <p className="text-sm text-gray-500">
        No routing decisions recorded for this package.
      </p>
    );
  }
  return (
    <div className="space-y-3">
      {decisions.map((d) => (
        <div
          key={d.id}
          className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900"
        >
          <div className="mb-2 flex items-center gap-2">
            <ParserBadge parser={d.chosen_parser} />
            <span className="text-xs text-gray-500">file {d.file_id}</span>
          </div>
          <p className="mb-3 text-sm text-gray-700 dark:text-gray-300">
            {d.reason}
          </p>
          {d.fallback_chain.length > 0 && (
            <div className="mb-3 flex flex-wrap gap-1">
              {d.fallback_chain.map((f) => (
                <span
                  key={f}
                  className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-700 dark:bg-gray-800 dark:text-gray-300"
                >
                  {f}
                </span>
              ))}
            </div>
          )}
          <pre className="overflow-x-auto rounded-lg bg-gray-50 p-3 text-xs text-gray-700 dark:bg-gray-950 dark:text-gray-300">
            <code>{JSON.stringify(d.signals, null, 2)}</code>
          </pre>
        </div>
      ))}
    </div>
  );
}

function PiiTab({ extractions }: { extractions: ExtractionView[] }) {
  const reports = extractions.filter((e) => e.pii_redaction_report_id);
  if (reports.length === 0) {
    return (
      <p className="text-sm text-gray-500">
        No PII redaction reports attached. Gate wiring lands in S97.5.
      </p>
    );
  }
  return (
    <ul className="space-y-2">
      {reports.map((e, i) => (
        <li
          key={e.pii_redaction_report_id ?? i}
          className="rounded border border-gray-200 bg-white px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-900"
        >
          report {e.pii_redaction_report_id}
        </li>
      ))}
    </ul>
  );
}

function Field({
  label,
  value,
}: {
  label: string;
  value: string | number | null | undefined;
}) {
  return (
    <div>
      <dt className="text-xs font-medium text-gray-500">{label}</dt>
      <dd className="text-sm font-medium text-gray-900 dark:text-gray-100">
        {value ?? "—"}
      </dd>
    </div>
  );
}
