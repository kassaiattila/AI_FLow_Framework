/**
 * AIFlow RoutingRuns — Sprint X / SX-3.
 *
 * Audit page for the UC3 EXTRACT routing trail. Renders the per-tenant
 * stats panel (doctype + outcome distributions, mean cost, latency
 * centiles) above a sortable, filterable table backed by
 * /api/v1/routing-runs/. Clicking a row opens a side drawer with the
 * full ``metadata`` JSONB pretty-printed plus a deep-link back to the
 * originating email.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslate } from "../lib/i18n";
import { fetchApi, ApiClientError } from "../lib/api-client";
import { PageLayout } from "../layout/PageLayout";

// --- Types (mirrors src/aiflow/services/routing_runs/schemas.py) ---

type ExtractionPath =
  | "invoice_processor"
  | "doc_recognizer_workflow"
  | "rag_ingest_fallback"
  | "skipped";

type ExtractionOutcome =
  | "success"
  | "partial"
  | "failed"
  | "refused_cost"
  | "skipped";

interface RoutingRunSummary {
  id: string;
  tenant_id: string;
  email_id: string | null;
  intent_class: string;
  doctype_detected: string | null;
  doctype_confidence: number | null;
  extraction_path: ExtractionPath;
  extraction_outcome: ExtractionOutcome;
  cost_usd: number | null;
  latency_ms: number | null;
  created_at: string;
}

interface RoutingRunDetail extends RoutingRunSummary {
  metadata: Record<string, unknown> | null;
  metadata_truncated: boolean;
  metadata_truncated_count: number;
}

interface RoutingStatsBucket {
  key: string;
  count: number;
}

interface RoutingStatsResponse {
  since: string;
  until: string;
  total_runs: number;
  by_doctype: RoutingStatsBucket[];
  by_outcome: RoutingStatsBucket[];
  by_extraction_path: RoutingStatsBucket[];
  mean_cost_usd: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
}

// --- Helpers ---

const OUTCOME_PILL_CLASS: Record<ExtractionOutcome, string> = {
  success:
    "bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
  partial:
    "bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
  failed: "bg-rose-50 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400",
  refused_cost:
    "bg-violet-50 text-violet-700 dark:bg-violet-900/30 dark:text-violet-400",
  skipped: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400",
};

function formatCost(cost: number | null): string {
  if (cost == null || cost === 0) return "—";
  if (cost < 0.0001) return "<$0.0001";
  if (cost < 0.01) return `$${cost.toFixed(4)}`;
  return `$${cost.toFixed(2)}`;
}

function formatLatency(ms: number | null): string {
  if (ms == null) return "—";
  if (ms < 1000) return `${ms} ms`;
  return `${(ms / 1000).toFixed(2)} s`;
}

function formatConfidence(c: number | null): string {
  if (c == null) return "—";
  return `${(c * 100).toFixed(0)}%`;
}

function formatTimestamp(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleString();
  } catch {
    return iso;
  }
}

function buildListPath(params: {
  tenantId: string;
  intentClass: string;
  doctypeDetected: string;
  extractionOutcome: string;
  since: string;
  until: string;
  limit: number;
  offset: number;
}): string {
  const usp = new URLSearchParams();
  usp.set("tenant_id", params.tenantId);
  if (params.intentClass) usp.set("intent_class", params.intentClass);
  if (params.doctypeDetected) usp.set("doctype_detected", params.doctypeDetected);
  if (params.extractionOutcome)
    usp.set("extraction_outcome", params.extractionOutcome);
  if (params.since) usp.set("since", new Date(params.since).toISOString());
  if (params.until) usp.set("until", new Date(params.until).toISOString());
  usp.set("limit", String(params.limit));
  usp.set("offset", String(params.offset));
  return `/api/v1/routing-runs/?${usp.toString()}`;
}

function buildStatsPath(tenantId: string, since: string, until: string): string {
  const usp = new URLSearchParams();
  usp.set("tenant_id", tenantId);
  if (since) usp.set("since", new Date(since).toISOString());
  if (until) usp.set("until", new Date(until).toISOString());
  return `/api/v1/routing-runs/stats?${usp.toString()}`;
}

// --- Page ---

const PAGE_LIMIT = 50;

export function RoutingRuns() {
  const translate = useTranslate();
  const navigate = useNavigate();

  // Filter state
  const [tenantId, setTenantId] = useState("default");
  const [intentClass, setIntentClass] = useState("");
  const [doctypeDetected, setDoctypeDetected] = useState("");
  const [extractionOutcome, setExtractionOutcome] = useState("");
  const [since, setSince] = useState("");
  const [until, setUntil] = useState("");
  const [offset, setOffset] = useState(0);

  const [rows, setRows] = useState<RoutingRunSummary[]>([]);
  const [stats, setStats] = useState<RoutingStatsResponse | null>(null);
  const [listLoading, setListLoading] = useState(true);
  const [statsLoading, setStatsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Drawer state
  const [drawerRow, setDrawerRow] = useState<RoutingRunDetail | null>(null);
  const [drawerLoading, setDrawerLoading] = useState(false);

  const listPath = useMemo(
    () =>
      buildListPath({
        tenantId,
        intentClass,
        doctypeDetected,
        extractionOutcome,
        since,
        until,
        limit: PAGE_LIMIT,
        offset,
      }),
    [
      tenantId,
      intentClass,
      doctypeDetected,
      extractionOutcome,
      since,
      until,
      offset,
    ],
  );
  const statsPath = useMemo(
    () => buildStatsPath(tenantId, since, until),
    [tenantId, since, until],
  );

  const refetchList = useCallback(async () => {
    setListLoading(true);
    setError(null);
    try {
      const data = await fetchApi<RoutingRunSummary[]>("GET", listPath);
      setRows(data);
    } catch (e) {
      const msg =
        e instanceof ApiClientError ? `${e.status}: ${e.message}` : String(e);
      setError(msg);
    } finally {
      setListLoading(false);
    }
  }, [listPath]);

  const refetchStats = useCallback(async () => {
    setStatsLoading(true);
    try {
      const data = await fetchApi<RoutingStatsResponse>("GET", statsPath);
      setStats(data);
    } catch {
      setStats(null);
    } finally {
      setStatsLoading(false);
    }
  }, [statsPath]);

  useEffect(() => {
    refetchList();
  }, [refetchList]);
  useEffect(() => {
    refetchStats();
  }, [refetchStats]);

  const openDrawer = useCallback(
    async (row: RoutingRunSummary) => {
      setDrawerLoading(true);
      setDrawerRow({
        ...row,
        metadata: null,
        metadata_truncated: false,
        metadata_truncated_count: 0,
      });
      try {
        const detail = await fetchApi<RoutingRunDetail>(
          "GET",
          `/api/v1/routing-runs/${row.id}?tenant_id=${encodeURIComponent(tenantId)}`,
        );
        setDrawerRow(detail);
      } catch {
        // keep partial drawer; user can close + retry
      } finally {
        setDrawerLoading(false);
      }
    },
    [tenantId],
  );

  const closeDrawer = useCallback(() => setDrawerRow(null), []);

  // Sprint X / SX-3 — drawer closes on ESC. Found in live Playwright run
  // (test 8 of tests/ui-live/routing-runs.md) — only X + backdrop closed
  // before this. Listener attaches only while the drawer is open so we
  // don't intercept ESC for the rest of the page.
  useEffect(() => {
    if (!drawerRow) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") closeDrawer();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [drawerRow, closeDrawer]);

  return (
    <PageLayout
      titleKey="aiflow.routingRuns.title"
      subtitleKey="aiflow.routingRuns.subtitle"
      actions={
        <button
          onClick={() => {
            setOffset(0);
            refetchList();
            refetchStats();
          }}
          className="rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700"
        >
          {translate("aiflow.common.refresh")}
        </button>
      }
    >
      {/* Stats panel */}
      <section
        aria-label="routing-runs-stats"
        className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4"
      >
        <StatsCard
          titleKey="aiflow.routingRuns.totalRuns"
          value={statsLoading ? "…" : (stats?.total_runs ?? 0).toString()}
        />
        <StatsCard
          titleKey="aiflow.routingRuns.meanCost"
          value={statsLoading ? "…" : formatCost(stats?.mean_cost_usd ?? 0)}
        />
        <StatsCard
          titleKey="aiflow.routingRuns.p50Latency"
          value={
            statsLoading ? "…" : formatLatency(stats?.p50_latency_ms ?? 0)
          }
        />
        <StatsCard
          titleKey="aiflow.routingRuns.p95Latency"
          value={
            statsLoading ? "…" : formatLatency(stats?.p95_latency_ms ?? 0)
          }
        />
        <DistributionCard
          titleKey="aiflow.routingRuns.byDoctype"
          buckets={stats?.by_doctype ?? []}
          loading={statsLoading}
        />
        <DistributionCard
          titleKey="aiflow.routingRuns.byOutcome"
          buckets={stats?.by_outcome ?? []}
          loading={statsLoading}
        />
        <DistributionCard
          titleKey="aiflow.routingRuns.byExtractionPath"
          buckets={stats?.by_extraction_path ?? []}
          loading={statsLoading}
        />
      </section>

      {/* Filter chips */}
      <section
        aria-label="routing-runs-filters"
        className="mb-4 flex flex-wrap items-end gap-2"
      >
        <FilterField label="aiflow.routingRuns.tenantId">
          <input
            type="text"
            value={tenantId}
            onChange={(e) => {
              setTenantId(e.target.value || "default");
              setOffset(0);
            }}
            className="rounded border border-gray-300 bg-white px-2 py-1 text-sm dark:border-gray-700 dark:bg-gray-800"
          />
        </FilterField>
        <FilterField label="aiflow.routingRuns.intentClass">
          <input
            type="text"
            value={intentClass}
            onChange={(e) => {
              setIntentClass(e.target.value);
              setOffset(0);
            }}
            placeholder="EXTRACT"
            className="rounded border border-gray-300 bg-white px-2 py-1 text-sm dark:border-gray-700 dark:bg-gray-800"
          />
        </FilterField>
        <FilterField label="aiflow.routingRuns.doctypeDetected">
          <input
            type="text"
            value={doctypeDetected}
            onChange={(e) => {
              setDoctypeDetected(e.target.value);
              setOffset(0);
            }}
            placeholder="hu_invoice"
            className="rounded border border-gray-300 bg-white px-2 py-1 text-sm dark:border-gray-700 dark:bg-gray-800"
          />
        </FilterField>
        <FilterField label="aiflow.routingRuns.extractionOutcome">
          <select
            value={extractionOutcome}
            onChange={(e) => {
              setExtractionOutcome(e.target.value);
              setOffset(0);
            }}
            className="rounded border border-gray-300 bg-white px-2 py-1 text-sm dark:border-gray-700 dark:bg-gray-800"
          >
            <option value="">{translate("aiflow.routingRuns.any")}</option>
            <option value="success">success</option>
            <option value="partial">partial</option>
            <option value="failed">failed</option>
            <option value="refused_cost">refused_cost</option>
            <option value="skipped">skipped</option>
          </select>
        </FilterField>
        <FilterField label="aiflow.routingRuns.since">
          <input
            type="datetime-local"
            value={since}
            onChange={(e) => {
              setSince(e.target.value);
              setOffset(0);
            }}
            className="rounded border border-gray-300 bg-white px-2 py-1 text-sm dark:border-gray-700 dark:bg-gray-800"
          />
        </FilterField>
        <FilterField label="aiflow.routingRuns.until">
          <input
            type="datetime-local"
            value={until}
            onChange={(e) => {
              setUntil(e.target.value);
              setOffset(0);
            }}
            className="rounded border border-gray-300 bg-white px-2 py-1 text-sm dark:border-gray-700 dark:bg-gray-800"
          />
        </FilterField>
      </section>

      {/* Table */}
      {error ? (
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-800 dark:bg-rose-900/30 dark:text-rose-300">
          {error}
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700">
          <table
            aria-label="routing-runs-table"
            className="min-w-full divide-y divide-gray-200 dark:divide-gray-700"
          >
            <thead className="bg-gray-50 dark:bg-gray-800">
              <tr>
                <Th>{translate("aiflow.routingRuns.col.createdAt")}</Th>
                <Th>{translate("aiflow.routingRuns.col.emailId")}</Th>
                <Th>{translate("aiflow.routingRuns.col.intentClass")}</Th>
                <Th>{translate("aiflow.routingRuns.col.doctypeDetected")}</Th>
                <Th>{translate("aiflow.routingRuns.col.extractionPath")}</Th>
                <Th>{translate("aiflow.routingRuns.col.extractionOutcome")}</Th>
                <Th>{translate("aiflow.routingRuns.col.costUsd")}</Th>
                <Th>{translate("aiflow.routingRuns.col.latencyMs")}</Th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 bg-white dark:divide-gray-700 dark:bg-gray-900">
              {listLoading && rows.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-6 text-center text-sm text-gray-500">
                    {translate("aiflow.common.loading")}
                  </td>
                </tr>
              ) : rows.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-6 text-center text-sm text-gray-500">
                    {translate("aiflow.routingRuns.empty")}
                  </td>
                </tr>
              ) : (
                rows.map((row) => (
                  <tr
                    key={row.id}
                    onClick={() => openDrawer(row)}
                    className="cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800"
                  >
                    <Td>{formatTimestamp(row.created_at)}</Td>
                    <Td>
                      {row.email_id ? (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            navigate(`/emails/${row.email_id}`);
                          }}
                          className="font-mono text-xs text-brand-600 hover:underline dark:text-brand-400"
                        >
                          {row.email_id.slice(0, 8)}…
                        </button>
                      ) : (
                        <span className="text-gray-400">—</span>
                      )}
                    </Td>
                    <Td>
                      <span className="rounded bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-700 dark:bg-gray-800 dark:text-gray-300">
                        {row.intent_class}
                      </span>
                    </Td>
                    <Td>
                      {row.doctype_detected ? (
                        <span className="inline-flex items-center gap-1">
                          <span className="font-medium">
                            {row.doctype_detected}
                          </span>
                          <span className="rounded bg-gray-100 px-1.5 py-0.5 text-[10px] font-mono text-gray-500 dark:bg-gray-800 dark:text-gray-400">
                            {formatConfidence(row.doctype_confidence)}
                          </span>
                        </span>
                      ) : (
                        <span className="text-gray-400">—</span>
                      )}
                    </Td>
                    <Td>
                      <span className="rounded bg-gray-100 px-2 py-0.5 text-xs font-mono text-gray-700 dark:bg-gray-800 dark:text-gray-300">
                        {row.extraction_path}
                      </span>
                    </Td>
                    <Td>
                      <span
                        className={`rounded px-2 py-0.5 text-xs font-medium ${OUTCOME_PILL_CLASS[row.extraction_outcome]}`}
                      >
                        {row.extraction_outcome}
                      </span>
                    </Td>
                    <Td>{formatCost(row.cost_usd)}</Td>
                    <Td>{formatLatency(row.latency_ms)}</Td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      <div className="mt-4 flex items-center justify-between text-sm">
        <span className="text-gray-500">
          {translate("aiflow.routingRuns.page")}{" "}
          {Math.floor(offset / PAGE_LIMIT) + 1}
        </span>
        <div className="flex gap-2">
          <button
            onClick={() => setOffset(Math.max(0, offset - PAGE_LIMIT))}
            disabled={offset === 0}
            className="rounded border border-gray-300 px-3 py-1 text-sm disabled:opacity-50 dark:border-gray-700"
          >
            {translate("aiflow.common.prev")}
          </button>
          <button
            onClick={() => setOffset(offset + PAGE_LIMIT)}
            disabled={rows.length < PAGE_LIMIT}
            className="rounded border border-gray-300 px-3 py-1 text-sm disabled:opacity-50 dark:border-gray-700"
          >
            {translate("aiflow.common.next")}
          </button>
        </div>
      </div>

      {/* Side drawer */}
      {drawerRow && (
        <div
          aria-label="routing-run-drawer"
          className="fixed inset-0 z-40 flex justify-end"
          onClick={closeDrawer}
        >
          <div
            className="absolute inset-0 bg-black/30"
            aria-hidden="true"
          ></div>
          <aside
            onClick={(e) => e.stopPropagation()}
            className="relative z-50 flex h-full w-full max-w-2xl flex-col overflow-y-auto border-l border-gray-200 bg-white p-6 shadow-2xl dark:border-gray-700 dark:bg-gray-900"
          >
            <div className="mb-4 flex items-start justify-between">
              <div>
                <h2 className="text-lg font-bold text-gray-900 dark:text-gray-100">
                  {translate("aiflow.routingRuns.detail.title")}
                </h2>
                <p className="mt-1 font-mono text-xs text-gray-500">
                  {drawerRow.id}
                </p>
              </div>
              <button
                onClick={closeDrawer}
                aria-label="close-drawer"
                className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-700 dark:hover:bg-gray-800"
              >
                ✕
              </button>
            </div>

            <div className="mb-4 grid grid-cols-2 gap-3 text-sm">
              <DrawerField label="created_at">
                {formatTimestamp(drawerRow.created_at)}
              </DrawerField>
              <DrawerField label="tenant_id">{drawerRow.tenant_id}</DrawerField>
              <DrawerField label="intent_class">
                {drawerRow.intent_class}
              </DrawerField>
              <DrawerField label="doctype_detected">
                {drawerRow.doctype_detected ?? "—"}
                {drawerRow.doctype_confidence != null && (
                  <span className="ml-2 text-xs text-gray-500">
                    ({formatConfidence(drawerRow.doctype_confidence)})
                  </span>
                )}
              </DrawerField>
              <DrawerField label="extraction_path">
                {drawerRow.extraction_path}
              </DrawerField>
              <DrawerField label="extraction_outcome">
                <span
                  className={`rounded px-2 py-0.5 text-xs font-medium ${OUTCOME_PILL_CLASS[drawerRow.extraction_outcome]}`}
                >
                  {drawerRow.extraction_outcome}
                </span>
              </DrawerField>
              <DrawerField label="cost_usd">
                {formatCost(drawerRow.cost_usd)}
              </DrawerField>
              <DrawerField label="latency_ms">
                {formatLatency(drawerRow.latency_ms)}
              </DrawerField>
            </div>

            {drawerRow.email_id && (
              <button
                onClick={() => navigate(`/emails/${drawerRow.email_id}`)}
                className="mb-4 inline-flex items-center gap-1 self-start rounded-lg border border-brand-300 bg-brand-50 px-3 py-1.5 text-sm font-medium text-brand-700 hover:bg-brand-100 dark:border-brand-700 dark:bg-brand-900/30 dark:text-brand-300"
              >
                {translate("aiflow.routingRuns.detail.viewEmail")} →
              </button>
            )}

            {drawerRow.metadata_truncated && (
              <div className="mb-3 rounded border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700 dark:border-amber-700 dark:bg-amber-900/30 dark:text-amber-300">
                ⚠ {translate("aiflow.routingRuns.detail.truncated")} (
                {drawerRow.metadata_truncated_count})
              </div>
            )}

            <div className="flex-1 overflow-auto">
              <h3 className="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">
                {translate("aiflow.routingRuns.detail.metadata")}
              </h3>
              {drawerLoading ? (
                <p className="text-sm text-gray-500">
                  {translate("aiflow.common.loading")}
                </p>
              ) : (
                <pre className="overflow-auto rounded-lg bg-gray-50 p-3 font-mono text-xs text-gray-800 dark:bg-gray-800 dark:text-gray-200">
                  {JSON.stringify(drawerRow.metadata ?? {}, null, 2)}
                </pre>
              )}
            </div>
          </aside>
        </div>
      )}
    </PageLayout>
  );
}

// --- Subcomponents ---

function Th({ children }: { children: React.ReactNode }) {
  return (
    <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
      {children}
    </th>
  );
}

function Td({ children }: { children: React.ReactNode }) {
  return (
    <td className="whitespace-nowrap px-3 py-2 text-sm text-gray-700 dark:text-gray-200">
      {children}
    </td>
  );
}

function FilterField({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  const translate = useTranslate();
  return (
    <label className="flex flex-col text-xs font-medium text-gray-500 dark:text-gray-400">
      <span className="mb-1">{translate(label)}</span>
      {children}
    </label>
  );
}

function StatsCard({ titleKey, value }: { titleKey: string; value: string }) {
  const translate = useTranslate();
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-900">
      <p className="text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">
        {translate(titleKey)}
      </p>
      <p className="mt-1 text-xl font-bold text-gray-900 dark:text-gray-100">
        {value}
      </p>
    </div>
  );
}

function DistributionCard({
  titleKey,
  buckets,
  loading,
}: {
  titleKey: string;
  buckets: RoutingStatsBucket[];
  loading: boolean;
}) {
  const translate = useTranslate();
  const total = buckets.reduce((s, b) => s + b.count, 0);
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-900">
      <p className="mb-2 text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">
        {translate(titleKey)}
      </p>
      {loading ? (
        <p className="text-xs text-gray-500">…</p>
      ) : buckets.length === 0 ? (
        <p className="text-xs text-gray-500">—</p>
      ) : (
        <ul className="space-y-1">
          {buckets.slice(0, 5).map((b) => {
            const pct = total > 0 ? Math.round((b.count / total) * 100) : 0;
            return (
              <li
                key={b.key}
                className="flex items-center justify-between text-xs"
              >
                <span className="truncate font-mono text-gray-700 dark:text-gray-300">
                  {b.key}
                </span>
                <span className="ml-2 shrink-0 text-gray-500">
                  {b.count} ({pct}%)
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

function DrawerField({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <p className="text-[10px] font-semibold uppercase tracking-wider text-gray-400">
        {label}
      </p>
      <p className="mt-0.5 text-sm text-gray-800 dark:text-gray-200">
        {children}
      </p>
    </div>
  );
}
