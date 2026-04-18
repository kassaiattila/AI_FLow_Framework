/**
 * AIFlow Dashboard — F6.1 implementation.
 * Dynamic skill cards, KPI sparklines, active pipelines.
 * Replaces old MUI Dashboard.tsx.
 */

import { useNavigate } from "react-router-dom";
import { LineChart, Line, ResponsiveContainer } from "recharts";
import { useTranslate } from "../lib/i18n";
import { useApi, useBackendStatus } from "../lib/hooks";
import { PageLayout } from "../layout/PageLayout";
import { LoadingState } from "../components-new/LoadingState";
import { ErrorState } from "../components-new/ErrorState";
import { EmptyState } from "../components-new/EmptyState";

interface SkillSummary {
  name: string;
  display_name: string;
  status: string;
  description: string;
  run_count: number;
  last_run_at: string | null;
  success_rate: number;
}

interface SkillsResponse {
  skills: SkillSummary[];
  total: number;
  source: string;
}

interface DailyStat {
  date: string;
  run_count: number;
  cost_usd: number;
  success_count: number;
  failed_count: number;
}

interface StatsResponse {
  daily: DailyStat[];
  total_runs: number;
  total_cost_usd: number;
  success_rate: number;
  source: string;
}

interface RunItem {
  run_id: string;
  workflow_name: string;
  skill_name: string | null;
  status: string;
  started_at: string | null;
  total_duration_ms: number | null;
  total_cost_usd: number;
}

interface RunsResponse {
  runs: RunItem[];
  total: number;
}

interface ServiceItem {
  name: string;
  status: string;
}

interface ServicesResponse {
  services: ServiceItem[];
  total: number;
}

interface CollectionItem {
  id: string;
  name: string;
  document_count: number;
  chunk_count: number;
}

interface CollectionsResponse {
  collections: CollectionItem[];
  total: number;
}

interface DocsCountResponse {
  documents: { id: string; extraction_confidence: number | null }[];
  total: number;
}

// DiagramsCountResponse and SpecsCountResponse removed — J4 archived (Sprint C)

interface JourneyCard {
  titleKey: string;
  subtitleKey: string;
  icon: string;
  color: string;
  borderColor: string;
  path: string;
  stat1: { label: string; value: string };
  stat2: { label: string; value: string };
}

function JourneyIcon({ name, className }: { name: string; className?: string }) {
  const icons: Record<string, string> = {
    "file-text": "M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z M14 2v6h6 M16 13H8 M16 17H8 M10 9H8",
    "book-open": "M2 3h6a4 4 0 014 4v14a3 3 0 00-3-3H2z M22 3h-6a4 4 0 00-4 4v14a3 3 0 013-3h7z",
    "git-branch": "M6 3v12 M18 9a3 3 0 100-6 3 3 0 000 6z M6 21a3 3 0 100-6 3 3 0 000 6z M18 9a9 9 0 01-9 9",
    activity: "M22 12h-4l-3 9L9 3l-3 9H2",
  };
  return (
    <svg className={className ?? "h-6 w-6"} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      {(icons[name] || icons["file-text"]).split(" M").map((segment, i) => (
        <path key={i} d={i === 0 ? segment : `M${segment}`} />
      ))}
    </svg>
  );
}

const STATUS_COLORS: Record<string, string> = {
  production: "bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  in_development: "bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  stub: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400",
};

const SKILL_ROUTES: Record<string, string> = {
  process_documentation: "/process-docs",
  aszf_rag_chat: "/rag",
  email_intent_processor: "/emails",
  invoice_processor: "/documents",
  cubix_course_capture: "/cubix",
};

function timeAgo(isoDate: string | null): string {
  if (!isoDate) return "—";
  const diff = Date.now() - new Date(isoDate).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export function DashboardNew() {
  const translate = useTranslate();
  const navigate = useNavigate();
  const backendStatus = useBackendStatus();
  const { data: skills, loading: skillsLoading, error: skillsError, refetch: refetchSkills } =
    useApi<SkillsResponse>("/api/v1/skills/summary");
  const { data: stats, loading: statsLoading } =
    useApi<StatsResponse>("/api/v1/runs/stats");
  const { data: runs, loading: runsLoading } =
    useApi<RunsResponse>("/api/v1/runs?limit=5&status=running");

  // Journey card data
  const { data: docsData } = useApi<DocsCountResponse>("/api/v1/documents?limit=1");
  const { data: collections } = useApi<CollectionsResponse>("/api/v1/rag/collections");
  const { data: services } = useApi<ServicesResponse>("/api/v1/services");

  const serviceUp = services?.services?.filter(s => s.status === "healthy" || s.status === "production").length ?? 0;
  const serviceDown = services?.services?.filter(s => s.status === "down" || s.status === "degraded").length ?? 0;
  const totalChunks = collections?.collections?.reduce((sum, c) => sum + (c.chunk_count ?? 0), 0) ?? 0;

  const journeyCards: JourneyCard[] = [
    {
      titleKey: "aiflow.menu.documentProcessing",
      subtitleKey: "aiflow.dashboard.journeyDocSub",
      icon: "file-text",
      color: "text-brand-600 dark:text-brand-400",
      borderColor: "border-brand-200 dark:border-brand-800 hover:border-brand-400 dark:hover:border-brand-600",
      path: "/emails",
      stat1: { label: translate("aiflow.menu.documents"), value: String(docsData?.total ?? "—") },
      stat2: { label: translate("aiflow.menu.verification"), value: "—" },
    },
    {
      titleKey: "aiflow.menu.knowledgeBase",
      subtitleKey: "aiflow.dashboard.journeyRagSub",
      icon: "book-open",
      color: "text-emerald-600 dark:text-emerald-400",
      borderColor: "border-emerald-200 dark:border-emerald-800 hover:border-emerald-400 dark:hover:border-emerald-600",
      path: "/rag",
      stat1: { label: translate("aiflow.menu.collections"), value: String(collections?.total ?? "—") },
      stat2: { label: "Chunks", value: totalChunks > 0 ? totalChunks.toLocaleString() : "—" },
    },
    {
      titleKey: "aiflow.menu.monitoring",
      subtitleKey: "aiflow.dashboard.journeyMonSub",
      icon: "activity",
      color: "text-amber-600 dark:text-amber-400",
      borderColor: "border-amber-200 dark:border-amber-800 hover:border-amber-400 dark:hover:border-amber-600",
      path: "/runs",
      stat1: { label: "Service UP", value: String(serviceUp) },
      stat2: { label: "Alerts", value: serviceDown > 0 ? String(serviceDown) : "0" },
    },
  ];

  const recentRuns = runs?.runs ?? [];
  const runningPipelines = recentRuns.filter(r => r.status === "running");
  const dailyData = stats?.daily ?? [];

  return (
    <PageLayout
      titleKey="aiflow.dashboard.title"
      subtitleKey="aiflow.dashboard.subtitle"
      source={skills?.source ?? (backendStatus === "connected" ? "backend" : "demo")}
    >
      {/* Alert banner — service DOWN */}
      {serviceDown > 0 && (
        <div
          className="mb-4 flex cursor-pointer items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm font-medium text-red-700 transition-colors hover:bg-red-100 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400 dark:hover:bg-red-900/30"
          onClick={() => navigate("/monitoring")}
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
          {serviceDown} {serviceDown === 1 ? "service needs attention" : "services need attention"}
        </div>
      )}

      {/* Pipeline running banner */}
      {runningPipelines.length > 0 && (
        <div
          className="mb-4 flex cursor-pointer items-center gap-2 rounded-lg border border-blue-200 bg-blue-50 px-4 py-2 text-sm font-medium text-blue-700 transition-colors hover:bg-blue-100 dark:border-blue-800 dark:bg-blue-900/20 dark:text-blue-400 dark:hover:bg-blue-900/30"
          onClick={() => navigate("/runs")}
        >
          <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          {translate("aiflow.dashboard.pipelineRunning")} ({runningPipelines.length})
        </div>
      )}

      {/* Journey Cards */}
      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {journeyCards.map((card) => (
          <div
            key={card.path}
            data-testid="journey-card"
            onClick={() => navigate(card.path)}
            className={`cursor-pointer rounded-xl border bg-white p-4 shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md dark:bg-gray-900 ${card.borderColor}`}
          >
            <div className="mb-3 flex items-center gap-2">
              <JourneyIcon name={card.icon} className={`h-5 w-5 ${card.color}`} />
              <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                {translate(card.titleKey)}
              </h3>
            </div>
            <div className="flex items-end justify-between">
              <div className="space-y-1">
                <p className="text-xs text-gray-500 dark:text-gray-400">{card.stat1.label}</p>
                <p className="text-lg font-bold text-gray-900 dark:text-gray-100">{card.stat1.value}</p>
              </div>
              <div className="text-right">
                <p className="text-xs text-gray-500 dark:text-gray-400">{card.stat2.label}</p>
                <p className="text-sm font-semibold text-gray-700 dark:text-gray-300">{card.stat2.value}</p>
              </div>
            </div>
            <p className={`mt-2 text-xs font-medium ${card.color}`}>
              {translate("aiflow.dashboard.openViewer")} →
            </p>
          </div>
        ))}
      </div>

      {/* KPI Cards */}
      <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-3">
        {/* Total Runs */}
        <div className="rounded-xl border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-900">
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
            {translate("aiflow.dashboard.allRuns")}
          </p>
          <div className="mt-1 flex items-end justify-between">
            <span className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              {statsLoading ? "—" : (stats?.total_runs ?? 0).toLocaleString()}
            </span>
            <div className="h-10 w-24">
              {dailyData.length > 1 && (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={dailyData}>
                    <Line type="monotone" dataKey="run_count" stroke="#4f46e5" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>
          {stats && (
            <p className="mt-1 text-xs text-green-600 dark:text-green-400">
              ↑ {stats.success_rate}% {translate("aiflow.monitoring.successRate")}
            </p>
          )}
        </div>

        {/* Today Cost */}
        <div className="rounded-xl border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-900">
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
            {translate("aiflow.dashboard.todayCost")}
          </p>
          <div className="mt-1 flex items-end justify-between">
            <span className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              ${statsLoading ? "—" : (stats?.total_cost_usd ?? 0).toFixed(2)}
            </span>
            <div className="h-10 w-24">
              {dailyData.length > 1 && (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={dailyData}>
                    <Line type="monotone" dataKey="cost_usd" stroke="#059669" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>
          <p className="mt-1 text-xs text-gray-400">$50/day budget limit</p>
        </div>

        {/* Success Rate */}
        <div className="rounded-xl border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-900">
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
            {translate("aiflow.monitoring.successRate")}
          </p>
          <div className="mt-1 flex items-end justify-between">
            <span className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              {statsLoading ? "—" : `${stats?.success_rate ?? 0}%`}
            </span>
            <div className="h-10 w-24">
              {dailyData.length > 1 && (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={dailyData}>
                    <Line type="monotone" dataKey="success_count" stroke="#7c3aed" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>
          {stats && stats.total_runs > 0 && (
            <p className="mt-1 text-xs text-gray-400">
              {stats.total_runs - Math.round(stats.total_runs * stats.success_rate / 100)} failed of {stats.total_runs}
            </p>
          )}
        </div>
      </div>

      {/* Active Pipelines */}
      <div className="mb-6">
        <h2 className="mb-3 text-base font-semibold text-gray-900 dark:text-gray-100">
          Active Pipelines
        </h2>
        <div className="rounded-xl border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-900">
          {runsLoading ? (
            <div className="p-4"><LoadingState rows={3} /></div>
          ) : recentRuns.length === 0 ? (
            <div className="p-4">
              <EmptyState messageKey="aiflow.common.empty" icon="inbox" />
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:border-gray-800 dark:text-gray-400">
                  <th className="px-4 py-3">Pipeline</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Duration</th>
                  <th className="px-4 py-3">Cost</th>
                  <th className="px-4 py-3">Started</th>
                </tr>
              </thead>
              <tbody>
                {recentRuns.map((run) => (
                  <tr
                    key={run.run_id}
                    className="border-b border-gray-50 hover:bg-gray-50 dark:border-gray-800 dark:hover:bg-gray-800/50"
                  >
                    <td className="px-4 py-3">
                      <span className="font-medium text-gray-900 dark:text-gray-100">
                        {run.skill_name ?? run.workflow_name}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                        run.status === "completed" ? "bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-400" :
                        run.status === "running" ? "bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400" :
                        run.status === "failed" ? "bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-400" :
                        "bg-gray-100 text-gray-600"
                      }`}>
                        {run.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-600 dark:text-gray-400">
                      {run.total_duration_ms ? `${(run.total_duration_ms / 1000).toFixed(1)}s` : "—"}
                    </td>
                    <td className="px-4 py-3 text-gray-600 dark:text-gray-400">
                      {run.total_cost_usd > 0 ? `$${run.total_cost_usd.toFixed(3)}` : "—"}
                    </td>
                    <td className="px-4 py-3 text-gray-500 dark:text-gray-400">
                      {timeAgo(run.started_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Skills */}
      <div>
        <h2 className="mb-3 text-base font-semibold text-gray-900 dark:text-gray-100">
          {translate("aiflow.dashboard.skills")}
        </h2>
        {skillsLoading ? (
          <LoadingState rows={3} />
        ) : skillsError ? (
          <ErrorState error={skillsError} onRetry={refetchSkills} />
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {(skills?.skills ?? []).map((skill) => (
              <div
                key={skill.name}
                onClick={() => {
                  const route = SKILL_ROUTES[skill.name];
                  if (route) navigate(route);
                }}
                className={`rounded-xl border border-gray-200 bg-white p-4 transition-all dark:border-gray-700 dark:bg-gray-900 ${
                  SKILL_ROUTES[skill.name]
                    ? "cursor-pointer hover:-translate-y-0.5 hover:shadow-md"
                    : ""
                }`}
              >
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold text-gray-900 dark:text-gray-100">
                    {skill.display_name}
                  </h3>
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[skill.status] ?? STATUS_COLORS.stub}`}>
                    {skill.status.replace("_", " ")}
                  </span>
                </div>
                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  {skill.description}
                </p>
                <div className="mt-3 flex items-center gap-3 text-xs">
                  <span className="font-medium text-brand-500">{skill.run_count} runs</span>
                  {skill.last_run_at && (
                    <span className="text-gray-400">Last: {timeAgo(skill.last_run_at)}</span>
                  )}
                  {SKILL_ROUTES[skill.name] && (
                    <span className="ml-auto font-medium text-brand-500">
                      {translate("aiflow.dashboard.openViewer")} →
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </PageLayout>
  );
}
