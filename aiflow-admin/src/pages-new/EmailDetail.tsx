/**
 * AIFlow EmailDetail — S108c drilldown view.
 * Backend: GET /api/v1/emails/{id}.
 */

import { useParams, useNavigate } from "react-router-dom";
import { useTranslate } from "../lib/i18n";
import { useApi } from "../lib/hooks";
import { PageLayout } from "../layout/PageLayout";
import { LoadingState } from "../components-new/LoadingState";
import { ErrorState } from "../components-new/ErrorState";
import {
  AttachmentSignalsCard,
  type AttachmentFeatures,
} from "../components-new/AttachmentSignalsCard";
import {
  ExtractedFieldsCard,
  type ExtractedInvoice,
} from "../components-new/ExtractedFieldsCard";

interface EmailDetail {
  email_id: string;
  subject: string;
  sender: string;
  recipients: string[];
  received_date: string | null;
  body: string;
  body_html: string;
  intent: Record<string, unknown> | null;
  entities: Record<string, unknown> | null;
  priority: Record<string, unknown> | null;
  routing: Record<string, unknown> | null;
  attachment_summaries: Array<Record<string, unknown>>;
  attachment_features: AttachmentFeatures | null;
  classification_method: string | null;
  intent_class: string | null;
  extracted_fields: Record<string, ExtractedInvoice> | null;
  processing_time_ms: number;
  status: string;
  source: string;
}

function Card({
  title,
  headerExtra,
  children,
}: {
  title: string;
  headerExtra?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
      <h3 className="mb-2 flex items-center text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
        <span>{title}</span>
        {headerExtra}
      </h3>
      {children}
    </div>
  );
}

const INTENT_CLASS_TONE: Record<string, string> = {
  EXTRACT:
    "bg-blue-50 text-blue-700 ring-blue-600/20 dark:bg-blue-500/10 dark:text-blue-300",
  INFORMATION_REQUEST:
    "bg-indigo-50 text-indigo-700 ring-indigo-600/20 dark:bg-indigo-500/10 dark:text-indigo-300",
  SUPPORT:
    "bg-emerald-50 text-emerald-700 ring-emerald-600/20 dark:bg-emerald-500/10 dark:text-emerald-300",
  SPAM: "bg-rose-50 text-rose-700 ring-rose-600/20 dark:bg-rose-500/10 dark:text-rose-300",
  OTHER:
    "bg-gray-50 text-gray-700 ring-gray-500/20 dark:bg-gray-700/40 dark:text-gray-300",
};

function IntentClassBadge({ value }: { value: string | null }) {
  if (!value) return null;
  const tone = INTENT_CLASS_TONE[value] ?? INTENT_CLASS_TONE.OTHER;
  return (
    <span
      data-testid="intent-class-badge"
      className={`ml-2 inline-flex items-center rounded-md px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ring-1 ring-inset ${tone}`}
    >
      {value}
    </span>
  );
}

function KV({ label, value }: { label: string; value: string | number | null | undefined }) {
  if (value === null || value === undefined || value === "") return null;
  return (
    <div className="flex items-baseline justify-between gap-3 py-1 text-sm">
      <span className="text-gray-500 dark:text-gray-400">{label}</span>
      <span className="font-mono text-gray-900 dark:text-gray-100">{String(value)}</span>
    </div>
  );
}

export function EmailDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const translate = useTranslate();
  const { data, loading, error } = useApi<EmailDetail>(id ? `/api/v1/emails/${id}` : null);

  if (loading) return <LoadingState />;
  if (error) return <ErrorState error={error} onRetry={() => window.location.reload()} />;
  if (!data) return null;

  const intent = data.intent ?? {};
  const priority = data.priority ?? {};
  const routing = data.routing ?? {};
  const entities = data.entities ?? {};

  const receivedFmt = data.received_date ? new Date(data.received_date).toLocaleString() : "—";

  return (
    <PageLayout titleKey="aiflow.emails.title" subtitleKey="aiflow.emails.detail">
      <div className="mb-4 flex items-center gap-3">
        <button
          onClick={() => navigate("/emails")}
          className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-400"
        >
          ← {translate("common.action.back")}
        </button>
        <span className="text-xs text-gray-500">{data.source === "backend" ? "Live" : "Demo"}</span>
      </div>

      <div className="mb-4 rounded-xl border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-900">
        <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
          {data.subject || "(no subject)"}
        </h1>
        <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
          <span className="font-medium">{data.sender || "—"}</span>
          {data.recipients.length > 0 && <span> → {data.recipients.join(", ")}</span>}
          <span className="ml-3 text-gray-400">{receivedFmt}</span>
        </p>
      </div>

      <div className="mb-4 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card title="Intent" headerExtra={<IntentClassBadge value={data.intent_class} />}>
          <KV label="Label" value={String(intent.intent_id ?? "—")} />
          <KV label="Display" value={String(intent.intent_display_name ?? "—")} />
          <KV
            label="Confidence"
            value={intent.confidence !== undefined ? `${Math.round(Number(intent.confidence) * 100)}%` : "—"}
          />
          <KV label="Method" value={String(intent.method ?? "—")} />
        </Card>
        <Card title="Priority">
          <KV label="Level" value={priority.priority_level ? `P${priority.priority_level}` : "—"} />
          <KV label="Name" value={String(priority.priority_name ?? "—")} />
        </Card>
        <Card title="Routing">
          <KV label="Department" value={String(routing.department_name ?? "—")} />
          <KV label="Queue" value={String(routing.queue_name ?? "—")} />
          <KV
            label="Escalation"
            value={routing.escalation_triggered ? `yes (${String(routing.escalation_reason ?? "")})` : "no"}
          />
        </Card>
        <Card title="Meta">
          <KV label="Entities" value={Number(entities.entity_count ?? 0)} />
          <KV label="Attachments" value={data.attachment_summaries.length} />
          <KV label="Processing" value={`${Math.round(data.processing_time_ms)}ms`} />
          <KV label="Status" value={data.status} />
        </Card>
      </div>

      <AttachmentSignalsCard
        features={data.attachment_features}
        classificationMethod={data.classification_method}
      />

      <ExtractedFieldsCard extractedFields={data.extracted_fields} />

      {data.body && (
        <div className="mb-4 rounded-xl border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-900">
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">Body</h3>
          <pre className="max-h-[400px] overflow-auto whitespace-pre-wrap font-sans text-sm text-gray-800 dark:text-gray-200">
            {data.body}
          </pre>
        </div>
      )}

      {data.attachment_summaries.length > 0 && (
        <div className="mb-4 rounded-xl border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-900">
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
            Attachments ({data.attachment_summaries.length})
          </h3>
          <ul className="space-y-1 text-sm text-gray-700 dark:text-gray-300">
            {data.attachment_summaries.map((a, i) => (
              <li key={i} className="font-mono">
                {String(a.filename ?? "—")} ({String(a.size ?? "?")})
              </li>
            ))}
          </ul>
        </div>
      )}
    </PageLayout>
  );
}
