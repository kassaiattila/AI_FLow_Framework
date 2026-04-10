/**
 * Quality Dashboard — LLM quality monitoring, rubric evaluation, cost tracking.
 * S3: v1.2.1 Production Ready Sprint
 */

import { useState, useEffect, useCallback } from "react";
import { fetchApi } from "../lib/api-client";
import { useTranslate } from "../lib/i18n";
import { PageLayout } from "../layout/PageLayout";

interface QualityOverview {
  total_evaluations: number;
  avg_score: number;
  pass_rate: number;
  cost_today: number;
  cost_month: number;
  source: string;
}

interface RubricsResponse {
  rubrics: Record<string, string>;
  source: string;
}

interface EvalResult {
  score: number;
  pass: boolean;
  reasoning: string;
  source: string;
}

export function Quality() {
  const translate = useTranslate();
  const [overview, setOverview] = useState<QualityOverview | null>(null);
  const [rubrics, setRubrics] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Evaluate form state
  const [selectedRubric, setSelectedRubric] = useState("");
  const [actualOutput, setActualOutput] = useState("");
  const [expectedOutput, setExpectedOutput] = useState("");
  const [evalLoading, setEvalLoading] = useState(false);
  const [evalResult, setEvalResult] = useState<EvalResult | null>(null);
  const [langfuseUrl, setLangfuseUrl] = useState("https://cloud.langfuse.com");

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [ov, rb] = await Promise.all([
        fetchApi<QualityOverview>("GET", "/api/v1/quality/overview"),
        fetchApi<RubricsResponse>("GET", "/api/v1/quality/rubrics"),
      ]);
      setOverview(ov);
      setRubrics(rb.rubrics);
      // Fetch Langfuse URL from health endpoint
      try {
        const health = await fetchApi<{ services?: { langfuse?: { host?: string } } }>("GET", "/api/v1/health");
        if (health.services?.langfuse?.host) setLangfuseUrl(health.services.langfuse.host);
      } catch { /* keep default */ }
      if (!selectedRubric && Object.keys(rb.rubrics).length > 0) {
        setSelectedRubric(Object.keys(rb.rubrics)[0]);
      }
    } catch {
      setError("Failed to load quality data");
    } finally {
      setLoading(false);
    }
  }, [selectedRubric]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleEvaluate = async () => {
    if (!actualOutput.trim() || !selectedRubric) return;
    setEvalLoading(true);
    setEvalResult(null);
    try {
      const res = await fetchApi<EvalResult>("POST", "/api/v1/quality/evaluate", {
        actual: actualOutput,
        rubric: selectedRubric,
        expected: expectedOutput || undefined,
      });
      setEvalResult(res);
    } catch {
      setEvalResult({ score: 0, pass: false, reasoning: "Evaluation failed", source: "error" });
    } finally {
      setEvalLoading(false);
    }
  };

  if (loading) {
    return (
      <PageLayout titleKey="aiflow.quality.title" subtitleKey="aiflow.quality.subtitle">
        <div className="flex h-64 items-center justify-center">
          <span className="h-8 w-8 animate-spin rounded-full border-4 border-gray-300 border-t-brand-500" />
        </div>
      </PageLayout>
    );
  }

  if (error) {
    return (
      <PageLayout titleKey="aiflow.quality.title" subtitleKey="aiflow.quality.subtitle">
        <div className="flex h-64 flex-col items-center justify-center gap-3">
          <p className="text-sm text-red-500">{error}</p>
          <button onClick={fetchData} className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-medium text-white hover:bg-brand-600">
            {translate("ra.action.retry")}
          </button>
        </div>
      </PageLayout>
    );
  }

  const kpis = [
    { label: translate("aiflow.quality.totalEvals"), value: String(overview?.total_evaluations ?? 0) },
    { label: translate("aiflow.quality.avgScore"), value: `${((overview?.avg_score ?? 0) * 100).toFixed(1)}%` },
    { label: translate("aiflow.quality.passRate"), value: `${((overview?.pass_rate ?? 0) * 100).toFixed(1)}%`, green: true },
    { label: translate("aiflow.quality.costToday"), value: `$${(overview?.cost_today ?? 0).toFixed(2)}` },
    { label: translate("aiflow.quality.costMonth"), value: `$${(overview?.cost_month ?? 0).toFixed(2)}` },
  ];

  const rubricEntries = Object.entries(rubrics);

  return (
    <PageLayout
      titleKey="aiflow.quality.title"
      subtitleKey="aiflow.quality.subtitle"
      source={overview?.source}
    >
      {/* KPI Cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        {kpis.map((kpi) => (
          <div key={kpi.label} className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
            <p className="text-xs text-gray-500 dark:text-gray-400">{kpi.label}</p>
            <p className={`mt-1 text-2xl font-bold ${kpi.green ? "text-green-600 dark:text-green-400" : "text-gray-900 dark:text-gray-100"}`}>
              {kpi.value}
            </p>
          </div>
        ))}
      </div>

      {/* Two-column: Rubrics + Evaluate */}
      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        {/* Rubrics Table */}
        <div>
          <h2 className="mb-3 text-lg font-semibold text-gray-900 dark:text-gray-100">
            {translate("aiflow.quality.rubrics")}
          </h2>
          <div className="overflow-hidden rounded-lg border border-gray-200 dark:border-gray-700">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 dark:bg-gray-800">
                <tr>
                  <th className="px-4 py-2.5 text-left text-xs font-medium text-gray-500 dark:text-gray-400">
                    {translate("aiflow.quality.rubricName")}
                  </th>
                  <th className="px-4 py-2.5 text-left text-xs font-medium text-gray-500 dark:text-gray-400">
                    {translate("aiflow.quality.rubricDesc")}
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {rubricEntries.map(([name, desc]) => (
                  <tr
                    key={name}
                    onClick={() => setSelectedRubric(name)}
                    className={`cursor-pointer transition-colors ${
                      selectedRubric === name
                        ? "bg-brand-50/50 dark:bg-brand-900/10"
                        : "bg-white hover:bg-gray-50 dark:bg-gray-900 dark:hover:bg-gray-800"
                    }`}
                  >
                    <td className="px-4 py-2.5 font-medium text-gray-900 dark:text-gray-100">{name}</td>
                    <td className="px-4 py-2.5 text-gray-600 dark:text-gray-400">{desc}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Evaluate Form */}
        <div>
          <h2 className="mb-3 text-lg font-semibold text-gray-900 dark:text-gray-100">
            {translate("aiflow.quality.evaluate")}
          </h2>
          <div className="space-y-4 rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
            {/* Rubric select */}
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400">
                {translate("aiflow.quality.selectRubric")}
              </label>
              <select
                value={selectedRubric}
                onChange={(e) => setSelectedRubric(e.target.value)}
                className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100"
              >
                {rubricEntries.map(([name]) => (
                  <option key={name} value={name}>{name}</option>
                ))}
              </select>
            </div>

            {/* Actual output */}
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400">
                {translate("aiflow.quality.actualOutput")}
              </label>
              <textarea
                value={actualOutput}
                onChange={(e) => setActualOutput(e.target.value)}
                rows={3}
                className="w-full resize-none rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100"
                placeholder={translate("aiflow.quality.actualOutput")}
              />
            </div>

            {/* Expected output (optional) */}
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400">
                {translate("aiflow.quality.expectedOutput")}
              </label>
              <textarea
                value={expectedOutput}
                onChange={(e) => setExpectedOutput(e.target.value)}
                rows={2}
                className="w-full resize-none rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100"
                placeholder={translate("aiflow.quality.expectedOutput")}
              />
            </div>

            {/* Evaluate button */}
            <button
              onClick={handleEvaluate}
              disabled={!actualOutput.trim() || evalLoading}
              className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-medium text-white hover:bg-brand-600 disabled:opacity-50"
            >
              {evalLoading ? (
                <span className="flex items-center gap-2">
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                  {translate("aiflow.quality.evaluate")}...
                </span>
              ) : translate("aiflow.quality.evaluate")}
            </button>

            {/* Result */}
            {evalResult && (
              <div className="mt-3 rounded-lg border border-gray-200 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-900">
                <div className="flex items-center gap-3">
                  <span className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                    {(evalResult.score * 100).toFixed(0)}%
                  </span>
                  <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                    evalResult.pass
                      ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                      : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
                  }`}>
                    {evalResult.pass ? translate("aiflow.quality.pass") : translate("aiflow.quality.fail")}
                  </span>
                </div>
                <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">{evalResult.reasoning}</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* External Quality Tools */}
      <div className="mt-6">
        <h2 className="mb-3 text-lg font-semibold text-gray-900 dark:text-gray-100">
          {translate("aiflow.quality.externalTools")}
        </h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <a
            href="http://localhost:15500"
            target="_blank"
            rel="noopener noreferrer"
            className="group flex items-start gap-4 rounded-lg border border-gray-200 bg-white p-4 transition-colors hover:border-brand-300 hover:bg-brand-50 dark:border-gray-700 dark:bg-gray-800 dark:hover:border-brand-600 dark:hover:bg-gray-750"
          >
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-purple-100 text-purple-600 dark:bg-purple-900/30 dark:text-purple-400">
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div className="min-w-0">
              <p className="font-medium text-gray-900 group-hover:text-brand-600 dark:text-gray-100 dark:group-hover:text-brand-400">
                Promptfoo
              </p>
              <p className="mt-0.5 text-sm text-gray-500 dark:text-gray-400">
                {translate("aiflow.quality.promptfooDesc")}
              </p>
              <p className="mt-1 text-xs text-gray-400 dark:text-gray-500">localhost:15500</p>
            </div>
            <svg className="ml-auto h-5 w-5 shrink-0 text-gray-400 group-hover:text-brand-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          </a>

          <a
            href={langfuseUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="group flex items-start gap-4 rounded-lg border border-gray-200 bg-white p-4 transition-colors hover:border-brand-300 hover:bg-brand-50 dark:border-gray-700 dark:bg-gray-800 dark:hover:border-brand-600 dark:hover:bg-gray-750"
          >
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-orange-100 text-orange-600 dark:bg-orange-900/30 dark:text-orange-400">
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
            </div>
            <div className="min-w-0">
              <p className="font-medium text-gray-900 group-hover:text-brand-600 dark:text-gray-100 dark:group-hover:text-brand-400">
                Langfuse
              </p>
              <p className="mt-0.5 text-sm text-gray-500 dark:text-gray-400">
                {translate("aiflow.quality.langfuseDesc")}
              </p>
              <p className="mt-1 text-xs text-gray-400 dark:text-gray-500">{langfuseUrl}</p>
            </div>
            <svg className="ml-auto h-5 w-5 shrink-0 text-gray-400 group-hover:text-brand-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          </a>
        </div>
      </div>
    </PageLayout>
  );
}
