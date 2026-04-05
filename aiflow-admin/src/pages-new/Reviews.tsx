/**
 * AIFlow Reviews — F6.4 pending + history.
 */

import { useTranslate } from "../lib/i18n";
import { useApi } from "../lib/hooks";
import { fetchApi } from "../lib/api-client";
import { PageLayout } from "../layout/PageLayout";
import { ErrorState } from "../components-new/ErrorState";
import { DataTable, type Column } from "../components-new/DataTable";

interface ReviewItem { id: string; title: string; type: string; priority: string; created_at: string; status: string; reviewer: string | null; comment: string | null; reviewed_at: string | null; }
interface PendingResponse { reviews: ReviewItem[]; total: number; source: string; }
interface HistoryResponse { reviews: ReviewItem[]; total: number; source: string; }

export function Reviews() {
  const translate = useTranslate();
  const { data: pending, loading: pl, error: pe, refetch: pr } = useApi<PendingResponse>("/api/v1/reviews/pending");
  const { data: history, loading: hl, error: he, refetch: hr } = useApi<HistoryResponse>("/api/v1/reviews/history");

  const handleAction = async (id: string, action: "approve" | "reject") => {
    try { await fetchApi("POST", `/api/v1/reviews/${id}/${action}`, { comment: "" }); pr(); hr(); } catch { /* */ }
  };

  const priorityColor: Record<string, string> = {
    critical: "bg-red-50 text-red-700", high: "bg-amber-50 text-amber-700", normal: "bg-gray-100 text-gray-600", low: "bg-gray-50 text-gray-500",
  };

  const pendingCols: Column<Record<string, unknown>>[] = [
    { key: "title", label: translate("aiflow.reviews.itemTitle"), render: (item) => <span className="font-medium text-gray-900 dark:text-gray-100">{String(item.title)}</span> },
    { key: "type", label: translate("aiflow.reviews.type") },
    { key: "priority", label: translate("aiflow.reviews.priority"), render: (item) => <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${priorityColor[String(item.priority)] ?? priorityColor.normal}`}>{String(item.priority)}</span> },
    { key: "created_at", label: translate("aiflow.reviews.created"), render: (item) => <span className="text-xs text-gray-500">{new Date(String(item.created_at)).toLocaleString()}</span> },
    { key: "actions", label: translate("aiflow.reviews.actions"), sortable: false, render: (item) => (
      <div className="flex gap-1">
        <button onClick={() => handleAction(String(item.id), "approve")} className="rounded-md bg-green-50 px-2 py-1 text-xs font-medium text-green-700 hover:bg-green-100">{translate("aiflow.reviews.approve")}</button>
        <button onClick={() => handleAction(String(item.id), "reject")} className="rounded-md bg-red-50 px-2 py-1 text-xs font-medium text-red-700 hover:bg-red-100">{translate("aiflow.reviews.reject")}</button>
      </div>
    )},
  ];

  const historyCols: Column<Record<string, unknown>>[] = [
    { key: "title", label: translate("aiflow.reviews.itemTitle"), render: (item) => <span className="font-medium text-gray-900 dark:text-gray-100">{String(item.title)}</span> },
    { key: "status", label: translate("aiflow.reviews.decision"), render: (item) => {
      const s = String(item.status);
      return <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${s === "approved" ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"}`}>{s}</span>;
    }},
    { key: "reviewer", label: translate("aiflow.reviews.reviewer"), render: (item) => <span className="text-gray-500">{String(item.reviewer ?? "—")}</span> },
    { key: "comment", label: translate("aiflow.reviews.comment"), render: (item) => <span className="text-xs text-gray-500">{String(item.comment ?? "—")}</span> },
    { key: "reviewed_at", label: translate("aiflow.reviews.reviewed"), render: (item) => <span className="text-xs text-gray-500">{item.reviewed_at ? new Date(String(item.reviewed_at)).toLocaleString() : "—"}</span> },
  ];

  return (
    <PageLayout titleKey="aiflow.reviews.title" subtitleKey="aiflow.reviews.subtitle" source={pending?.source}>
      <h3 className="mb-2 text-base font-semibold text-gray-900 dark:text-gray-100">
        {translate("aiflow.reviews.pendingTitle")} <span className="ml-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700">{pending?.total ?? 0}</span>
      </h3>
      {pe ? <ErrorState error={pe} onRetry={pr} /> :
        <DataTable data={(pending?.reviews ?? []) as unknown as Record<string, unknown>[]} columns={pendingCols} loading={pl} emptyMessageKey="aiflow.reviews.noPending" />
      }

      <h3 className="mb-2 mt-6 text-base font-semibold text-gray-900 dark:text-gray-100">{translate("aiflow.reviews.historyTitle")}</h3>
      {he ? <ErrorState error={he} onRetry={hr} /> :
        <DataTable data={(history?.reviews ?? []) as unknown as Record<string, unknown>[]} columns={historyCols} loading={hl} emptyMessageKey="aiflow.reviews.noHistory" />
      }
    </PageLayout>
  );
}
