/**
 * AIFlow Process Docs — F6.4 diagram generation + saved diagrams.
 */

import { useState, useEffect, useRef } from "react";
import { useTranslate } from "../lib/i18n";
import { useApi } from "../lib/hooks";
import { fetchApi } from "../lib/api-client";
import { PageLayout } from "../layout/PageLayout";
import { ErrorState } from "../components-new/ErrorState";
import { DataTable, type Column } from "../components-new/DataTable";
import mermaid from "mermaid";

mermaid.initialize({ startOnLoad: false, theme: "dark", securityLevel: "loose" });

function MermaidDiagram({ code }: { code: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const [svg, setSvg] = useState("");
  useEffect(() => {
    let cancelled = false;
    const id = `mermaid-${Date.now()}`;
    mermaid.render(id, code).then(({ svg: rendered }) => {
      if (!cancelled) setSvg(rendered);
    }).catch(() => {
      if (!cancelled) setSvg("");
    });
    return () => { cancelled = true; };
  }, [code]);
  if (!svg) return <pre className="overflow-auto text-xs text-gray-600 dark:text-gray-300">{code}</pre>;
  return <div ref={ref} className="overflow-auto" dangerouslySetInnerHTML={{ __html: svg }} />;
}

interface Diagram {
  id: string;
  user_input: string;
  review: { score?: number } | null;
  created_at: string;
  source: string;
}

interface DiagramsResponse {
  diagrams: Diagram[];
  total: number;
  source: string;
}

export function ProcessDocs() {
  const translate = useTranslate();
  const [input, setInput] = useState("");
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const { data, loading, error, refetch } = useApi<DiagramsResponse>("/api/v1/diagrams");

  const handleGenerate = async () => {
    if (!input.trim()) return;
    setGenerating(true);
    try {
      const res = await fetchApi<{ mermaid_code: string }>("POST", "/api/v1/diagrams/generate", { user_input: input });
      setResult(res.mermaid_code);
      refetch();
    } catch { setResult(null); }
    finally { setGenerating(false); }
  };

  const columns: Column<Record<string, unknown>>[] = [
    { key: "user_input", label: translate("aiflow.processDocs.inputLabel"), render: (item) => <span className="text-gray-700 dark:text-gray-300 text-xs">{String(item.user_input).substring(0, 80)}...</span> },
    { key: "review.score", label: translate("aiflow.processDocs.review"), getValue: (item) => (item.review as Diagram["review"])?.score ?? 0, render: (item) => { const s = (item.review as Diagram["review"])?.score; return <span className={`font-medium ${s && s >= 7 ? "text-green-600" : "text-amber-600"}`}>{s ? `${s}/10` : "—"}</span>; }},
    { key: "created_at", label: translate("aiflow.processDocs.savedCreated"), render: (item) => <span className="text-xs text-gray-500">{new Date(String(item.created_at)).toLocaleDateString()}</span> },
  ];

  return (
    <PageLayout titleKey="aiflow.processDocs.title" source={data?.source}>
      <div className="mb-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Input */}
        <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
          <p className="mb-2 text-sm font-medium text-gray-700 dark:text-gray-300">{translate("aiflow.processDocs.inputLabel")}</p>
          <textarea value={input} onChange={(e) => setInput(e.target.value)} rows={6} placeholder={translate("aiflow.processDocs.placeholder")}
            className="w-full rounded-lg border border-gray-300 bg-white p-3 text-sm text-gray-700 placeholder-gray-400 focus:border-brand-500 focus:outline-none dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200" />
          <div className="mt-2 flex gap-2">
            {["preset_invoice", "preset_support", "preset_onboarding"].map((p) => (
              <button key={p} onClick={() => setInput(translate(`aiflow.processDocs.${p}`))} className="rounded-md border border-gray-300 px-2 py-1 text-xs text-gray-600 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-400">
                {translate(`aiflow.processDocs.${p}`)}
              </button>
            ))}
          </div>
          <button onClick={handleGenerate} disabled={generating || !input.trim()}
            className="mt-3 w-full rounded-lg bg-brand-500 py-2 text-sm font-semibold text-white hover:bg-brand-600 disabled:opacity-50">
            {generating ? translate("aiflow.common.loading") : translate("aiflow.processDocs.generate")}
          </button>
        </div>
        {/* Output */}
        <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
          <p className="mb-2 text-sm font-medium text-gray-700 dark:text-gray-300">{translate("aiflow.processDocs.diagram")}</p>
          <div className="flex min-h-48 items-center justify-center rounded-lg bg-gray-50 p-2 text-sm text-gray-400 dark:bg-gray-800">
            {result ? <MermaidDiagram code={result} /> : translate("aiflow.processDocs.diagramPlaceholder")}
          </div>
        </div>
      </div>

      <h3 className="mb-2 text-base font-semibold text-gray-900 dark:text-gray-100">{translate("aiflow.processDocs.savedDiagrams")}</h3>
      {error ? <ErrorState error={error} onRetry={refetch} /> :
        <DataTable data={(data?.diagrams ?? []) as unknown as Record<string, unknown>[]} columns={columns} loading={loading} searchKeys={["user_input"]} />
      }
    </PageLayout>
  );
}
