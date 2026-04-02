/**
 * AIFlow Audit — F6.5 audit trail with DataTable.
 */
import { useTranslate } from "../lib/i18n";
import { useApi } from "../lib/hooks";
import { PageLayout } from "../layout/PageLayout";
import { ErrorState } from "../components-new/ErrorState";
import { DataTable, type Column } from "../components-new/DataTable";

interface AuditEntry { id: string; action: string; resource: string; user_id: string; details: Record<string, unknown> | null; created_at: string; }
interface AuditResponse { entries: AuditEntry[]; total: number; source: string; }

export function Audit() {
  const translate = useTranslate();
  const { data, loading, error, refetch } = useApi<AuditResponse>("/api/v1/admin/audit");

  const columns: Column<Record<string, unknown>>[] = [
    { key: "created_at", label: translate("aiflow.audit.timestamp"), render: (item) => <span className="text-xs text-gray-500">{new Date(String(item.created_at)).toLocaleString()}</span> },
    { key: "action", label: translate("aiflow.audit.action"), render: (item) => <span className="rounded-full bg-brand-50 px-2 py-0.5 text-xs font-medium text-brand-700 dark:bg-brand-900/30 dark:text-brand-400">{String(item.action)}</span> },
    { key: "resource", label: translate("aiflow.audit.resource"), render: (item) => <span className="text-gray-600 dark:text-gray-400">{String(item.resource)}</span> },
    { key: "user_id", label: translate("aiflow.audit.user"), render: (item) => <span className="text-gray-500 text-xs">{String(item.user_id).substring(0, 8)}...</span> },
    { key: "details", label: translate("aiflow.audit.details"), sortable: false, render: (item) => <span className="text-xs text-gray-400">{item.details ? JSON.stringify(item.details).substring(0, 50) : "—"}</span> },
  ];

  return (
    <PageLayout titleKey="aiflow.audit.title" subtitleKey="aiflow.audit.subtitle" source={data?.source}
      actions={<button className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-400">{translate("aiflow.audit.export")}</button>}
    >
      {error ? <ErrorState error={error} onRetry={refetch} /> :
        <DataTable data={(data?.entries ?? []) as unknown as Record<string, unknown>[]} columns={columns} loading={loading} searchKeys={["action", "resource", "user_id"]} />
      }
    </PageLayout>
  );
}
