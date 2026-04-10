/**
 * AIFlow RPA — F6.4 configs + execution log.
 */

import { useTranslate } from "../lib/i18n";
import { useApi } from "../lib/hooks";
import { fetchApi } from "../lib/api-client";
import { PageLayout } from "../layout/PageLayout";
import { ErrorState } from "../components-new/ErrorState";
import { DataTable, type Column } from "../components-new/DataTable";

interface RpaConfig { id: string; name: string; target_url: string; steps_count: number; is_active: boolean; schedule: string | null; created_at: string; }
interface RpaLog { id: string; config_name: string; status: string; steps_completed: number; steps_total: number; duration_ms: number | null; started_at: string; error: string | null; }
interface ConfigsResponse { configs: RpaConfig[]; total: number; source: string; }
interface LogsResponse { logs: RpaLog[]; total: number; source: string; }

export function Rpa() {
  const translate = useTranslate();
  const { data: configsData, loading: cl, error: ce, refetch: cr } = useApi<ConfigsResponse>("/api/v1/rpa/configs");
  const { data: logsData, loading: ll, error: le, refetch: lr } = useApi<LogsResponse>("/api/v1/rpa/logs");

  const handleRun = async (id: string) => {
    try { await fetchApi("POST", "/api/v1/rpa/execute", { config_id: id }); lr(); } catch { /* */ }
  };

  const configCols: Column<Record<string, unknown>>[] = [
    { key: "name", label: translate("aiflow.rpa.name"), render: (item) => <span className="font-medium text-gray-900 dark:text-gray-100">{String(item.name)}</span> },
    { key: "target_url", label: translate("aiflow.rpa.targetUrl"), render: (item) => <span className="text-xs text-gray-500">{String(item.target_url)}</span> },
    { key: "steps_count", label: translate("aiflow.rpa.steps"), getValue: (item) => item.steps_count as number },
    { key: "is_active", label: translate("aiflow.rpa.status"), render: (item) => {
      const active = item.is_active as boolean;
      return <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${active ? "bg-green-50 text-green-700" : "bg-gray-100 text-gray-500"}`}>{active ? translate("aiflow.rpa.active") : translate("aiflow.rpa.inactive")}</span>;
    }},
    { key: "actions", label: translate("aiflow.rpa.actions"), sortable: false, render: (item) => (
      <button onClick={() => handleRun(String(item.id))} className="rounded-md bg-brand-50 px-2 py-1 text-xs font-medium text-brand-600 hover:bg-brand-100">
        {translate("aiflow.rpa.run")}
      </button>
    )},
  ];

  const logCols: Column<Record<string, unknown>>[] = [
    { key: "config_name", label: translate("aiflow.rpa.config"), render: (item) => <span className="font-medium text-gray-900 dark:text-gray-100">{String(item.config_name)}</span> },
    { key: "status", label: translate("aiflow.rpa.status"), render: (item) => {
      const s = String(item.status);
      const color = s === "completed" ? "bg-green-50 text-green-700" : s === "failed" ? "bg-red-50 text-red-700" : s === "running" ? "bg-blue-50 text-blue-700" : "bg-gray-100 text-gray-600";
      return <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${color}`}>{s}</span>;
    }},
    { key: "steps_completed", label: translate("aiflow.rpa.stepsProgress"), render: (item) => <span className="text-gray-600">{String(item.steps_completed)}/{String(item.steps_total)}</span> },
    { key: "duration_ms", label: translate("aiflow.rpa.duration"), getValue: (item) => item.duration_ms as number ?? 0, render: (item) => <span className="text-gray-500">{item.duration_ms ? `${((item.duration_ms as number)/1000).toFixed(1)}s` : "—"}</span> },
    { key: "started_at", label: translate("aiflow.rpa.started"), render: (item) => <span className="text-xs text-gray-500">{new Date(String(item.started_at)).toLocaleString()}</span> },
  ];

  return (
    <PageLayout titleKey="aiflow.rpa.title" subtitleKey="aiflow.rpa.subtitle" source={configsData?.source}
      actions={<button className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-600">{translate("aiflow.rpa.newConfig")}</button>}
    >
      <h3 className="mb-2 text-base font-semibold text-gray-900 dark:text-gray-100">{translate("aiflow.rpa.configsTitle")}</h3>
      {ce ? <ErrorState error={ce} onRetry={cr} /> :
        <DataTable data={(configsData?.configs ?? []) as unknown as Record<string, unknown>[]} columns={configCols} loading={cl} searchKeys={["name", "target_url"]} />
      }

      <h3 className="mb-2 mt-6 text-base font-semibold text-gray-900 dark:text-gray-100">{translate("aiflow.rpa.logsTitle")}</h3>
      {le ? <ErrorState error={le} onRetry={lr} /> :
        <DataTable data={(logsData?.logs ?? []) as unknown as Record<string, unknown>[]} columns={logCols} loading={ll} searchKeys={["config_name", "status"]} />
      }
    </PageLayout>
  );
}
