/**
 * AIFlow Monitoring — F6.5 service health + metrics.
 */
import { useState, useEffect } from "react";
import { useTranslate } from "../lib/i18n";
import { useApi } from "../lib/hooks";
import { fetchApi } from "../lib/api-client";
import { PageLayout } from "../layout/PageLayout";
import { LoadingState } from "../components-new/LoadingState";
import { ErrorState } from "../components-new/ErrorState";
import { ConfirmDialog } from "../components-new/ConfirmDialog";

interface ServiceHealth { service_name: string; status: string; latency_ms: number; details: Record<string, unknown> | null; }
interface HealthResponse { services: ServiceHealth[]; total: number; overall_status: string; source: string; }
interface ServiceMetric { service_name: string; avg_latency_ms: number; p95_latency_ms: number; success_rate: number; }
interface MetricsResponse { metrics: ServiceMetric[]; source: string; }

export function Monitoring() {
  const translate = useTranslate();
  const { data: health, loading: hl, error: he, refetch } = useApi<HealthResponse>("/api/v1/admin/health");
  const { data: metrics } = useApi<MetricsResponse>("/api/v1/admin/metrics");

  const [restartTarget, setRestartTarget] = useState<string | null>(null);
  const [restarting, setRestarting] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState<number | null>(null);

  useEffect(() => {
    if (!autoRefresh) return;
    const timer = setInterval(() => refetch(), autoRefresh);
    return () => clearInterval(timer);
  }, [autoRefresh, refetch]);

  async function handleRestart() {
    if (!restartTarget) return;
    setRestarting(true);
    try {
      await fetchApi<unknown>("POST", `/api/v1/admin/services/${restartTarget}/restart`);
      setRestartTarget(null);
      refetch();
    } catch {
      /* ErrorState will handle */
    } finally {
      setRestarting(false);
    }
  }

  const getMetric = (name: string) => metrics?.metrics.find(m => m.service_name === name);
  const healthy = health?.services.filter(s => s.status === "healthy").length ?? 0;

  return (
    <PageLayout titleKey="aiflow.monitoring.title" subtitleKey="aiflow.monitoring.subtitle" source={health?.source}
      actions={
        <div className="flex items-center gap-2">
          <select
            value={autoRefresh ?? ""}
            onChange={(e) => setAutoRefresh(e.target.value ? Number(e.target.value) : null)}
            className="rounded-lg border border-gray-300 px-2 py-1.5 text-xs text-gray-600 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-400"
          >
            <option value="">{translate("aiflow.monitoring.autoRefresh")}: Off</option>
            <option value="10000">10s</option>
            <option value="30000">30s</option>
            <option value="60000">60s</option>
          </select>
          <button onClick={refetch} className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-400">{translate("aiflow.monitoring.refresh")}</button>
        </div>
      }
    >
      {hl ? <LoadingState fullPage /> : he ? <ErrorState error={he} onRetry={refetch} /> : health ? (
        <>
          {/* Status banner */}
          <div className={`mb-4 rounded-lg p-3 text-sm font-medium ${health.overall_status === "healthy" ? "bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400" : "bg-amber-50 text-amber-700"}`}>
            {health.overall_status === "healthy" ? translate("aiflow.monitoring.allOperational") : translate("aiflow.monitoring.degradedBanner")} — {healthy}/{health.total} {translate("aiflow.monitoring.servicesHealthy")}
          </div>

          {/* KPIs */}
          <div className="mb-4 grid grid-cols-1 gap-4 md:grid-cols-3">
            <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
              <p className="text-xs font-medium text-gray-500">{translate("aiflow.monitoring.totalServices")}</p>
              <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-gray-100">{health.total}</p>
            </div>
            <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
              <p className="text-xs font-medium text-gray-500">{translate("aiflow.monitoring.avgLatency")}</p>
              <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-gray-100">{Math.round(health.services.reduce((s, svc) => s + svc.latency_ms, 0) / health.total)}ms</p>
            </div>
            <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
              <p className="text-xs font-medium text-gray-500">{translate("aiflow.monitoring.overallUptime")}</p>
              <p className="mt-1 text-2xl font-bold text-green-600">{metrics?.metrics.length ? (metrics.metrics.reduce((s, m) => s + m.success_rate, 0) / metrics.metrics.length).toFixed(1) : "—"}%</p>
            </div>
          </div>

          {/* Service cards */}
          <h3 className="mb-2 text-base font-semibold text-gray-900 dark:text-gray-100">{translate("aiflow.monitoring.serviceHealth")}</h3>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {health.services.map((svc) => {
              const m = getMetric(svc.service_name);
              const icon = svc.status === "healthy" ? "✓" : svc.status === "degraded" ? "⚠" : "✗";
              const color = svc.status === "healthy" ? "border-green-200 dark:border-green-800" : svc.status === "degraded" ? "border-amber-200" : "border-red-200";
              return (
                <div key={svc.service_name} className={`rounded-xl border bg-white p-3 dark:bg-gray-900 ${color}`}>
                  <div className="flex items-center gap-2">
                    <span className={`text-sm ${svc.status === "healthy" ? "text-green-600" : svc.status === "degraded" ? "text-amber-600" : "text-red-600"}`}>{icon}</span>
                    <span className="text-sm font-medium text-gray-900 dark:text-gray-100">{svc.service_name.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase())}</span>
                  </div>
                  <div className="mt-1 text-xs text-gray-500">
                    {Math.round(svc.latency_ms)}ms{m ? ` · p95: ${Math.round(m.p95_latency_ms)}ms · ${m.success_rate}%` : ""}
                  </div>
                  <button
                    onClick={() => setRestartTarget(svc.service_name)}
                    className="mt-2 rounded-md border border-gray-300 px-2 py-0.5 text-xs font-medium text-gray-600 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-400 dark:hover:bg-gray-800"
                  >
                    ↻ Restart
                  </button>
                </div>
              );
            })}
          </div>
        </>
      ) : null}

      <ConfirmDialog
        open={!!restartTarget}
        title={translate("aiflow.monitoring.restartConfirm").replace("{{service}}", restartTarget ?? "")}
        message={`Service: ${restartTarget}`}
        variant="danger"
        loading={restarting}
        confirmLabel="Restart"
        onConfirm={handleRestart}
        onCancel={() => setRestartTarget(null)}
      />
    </PageLayout>
  );
}
