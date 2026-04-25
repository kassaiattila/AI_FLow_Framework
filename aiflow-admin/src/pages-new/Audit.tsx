/**
 * AIFlow Audit — F6.5 audit trail with DataTable.
 * S39: C2.6 — Filter dropdowns + CSV export.
 */
import { useState, useMemo } from "react";
import { useTranslate } from "../lib/i18n";
import { useApi } from "../lib/hooks";
import { PageLayout } from "../layout/PageLayout";
import { ErrorState } from "../components-new/ErrorState";
import { DataTable, type Column } from "../components-new/DataTable";

interface AuditEntry {
  id: string;
  action: string;
  resource: string;
  user_id: string;
  details: Record<string, unknown> | null;
  created_at: string;
}
interface AuditResponse {
  entries: AuditEntry[];
  total: number;
  source: string;
}

export function Audit() {
  const translate = useTranslate();
  const [filterAction, setFilterAction] = useState("");
  const [filterEntity, setFilterEntity] = useState("");

  const auditUrl = useMemo(() => {
    const p = new URLSearchParams();
    if (filterAction) p.set("action", filterAction);
    if (filterEntity) p.set("entity_type", filterEntity);
    const qs = p.toString();
    return `/api/v1/admin/audit${qs ? `?${qs}` : ""}`;
  }, [filterAction, filterEntity]);

  const { data, loading, error, refetch } = useApi<AuditResponse>(auditUrl);

  const handleExportCsv = () => {
    if (!data?.entries?.length) return;
    const header = "timestamp,action,resource,user_id,details\n";
    const rows = data.entries
      .map(
        (e) =>
          `"${e.created_at}","${e.action}","${e.resource}","${e.user_id}","${JSON.stringify(e.details ?? {}).replace(/"/g, '""')}"`,
      )
      .join("\n");
    const blob = new Blob([header + rows], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `audit-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const columns: Column<Record<string, unknown>>[] = [
    {
      key: "created_at",
      label: translate("aiflow.audit.timestamp"),
      render: (item) => (
        <span className="text-xs text-gray-500">
          {new Date(String(item.created_at)).toLocaleString()}
        </span>
      ),
    },
    {
      key: "action",
      label: translate("aiflow.audit.action"),
      render: (item) => (
        <span className="rounded-full bg-brand-50 px-2 py-0.5 text-xs font-medium text-brand-700 dark:bg-brand-900/30 dark:text-brand-400">
          {String(item.action)}
        </span>
      ),
    },
    {
      key: "resource",
      label: translate("aiflow.audit.resource"),
      render: (item) => (
        <span className="text-gray-600 dark:text-gray-400">
          {String(item.resource)}
        </span>
      ),
    },
    {
      key: "user_id",
      label: translate("aiflow.audit.user"),
      render: (item) => (
        <span className="text-gray-500 text-xs">
          {String(item.user_id).substring(0, 8)}...
        </span>
      ),
    },
    {
      key: "details",
      label: translate("aiflow.audit.details"),
      sortable: false,
      render: (item) => (
        <span className="text-xs text-gray-400">
          {item.details ? JSON.stringify(item.details).substring(0, 50) : "—"}
        </span>
      ),
    },
  ];

  return (
    <PageLayout
      titleKey="aiflow.audit.title"
      subtitleKey="aiflow.audit.subtitle"
      source={data?.source}
      actions={
        <button
          onClick={handleExportCsv}
          className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-400 dark:hover:bg-gray-800"
        >
          {translate("aiflow.audit.exportCsv")}
        </button>
      }
    >
      {/* Filter controls */}
      <div className="mb-4 flex items-center gap-3">
        <select
          value={filterAction}
          onChange={(e) => setFilterAction(e.target.value)}
          className="rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300"
        >
          <option value="">
            {translate("aiflow.audit.all")} —{" "}
            {translate("aiflow.audit.filterAction")}
          </option>
          <option value="create">create</option>
          <option value="update">update</option>
          <option value="delete">delete</option>
          <option value="login">login</option>
          <option value="evaluate">evaluate</option>
        </select>
        <select
          value={filterEntity}
          onChange={(e) => setFilterEntity(e.target.value)}
          className="rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300"
        >
          <option value="">
            {translate("aiflow.audit.all")} —{" "}
            {translate("aiflow.audit.filterEntity")}
          </option>
          <option value="user">user</option>
          <option value="api_key">api_key</option>
          <option value="document">document</option>
          <option value="pipeline">pipeline</option>
          <option value="collection">collection</option>
        </select>
      </div>

      {error ? (
        <ErrorState error={error} onRetry={refetch} />
      ) : (
        <DataTable
          data={(data?.entries ?? []) as unknown as Record<string, unknown>[]}
          columns={columns}
          loading={loading}
          searchKeys={["action", "resource", "user_id"]}
        />
      )}
    </PageLayout>
  );
}
