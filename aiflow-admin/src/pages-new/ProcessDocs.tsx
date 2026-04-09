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
import { FileProgressRow, type FileProgress } from "../components-new/FileProgress";
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
  const [diagramType, setDiagramType] = useState<"flowchart" | "sequence" | "bpmn_swimlane">("flowchart");
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [fileProgress, setFileProgress] = useState<FileProgress[]>([]);
  const [genError, setGenError] = useState<string | null>(null);
  const { data, loading, error, refetch } = useApi<DiagramsResponse>("/api/v1/diagrams");

  const handleGenerate = async () => {
    if (!input.trim()) return;
    setGenerating(true);
    setResult(null);
    setGenError(null);

    const defaultSteps = ["classify", "elaborate", "extract", "review", "generate", "export"];
    setFileProgress([{
      name: "BPMN Diagram",
      status: "pending",
      steps: defaultSteps.map(s => ({ name: s, status: "pending" as const })),
    }]);

    try {
      const token = localStorage.getItem("aiflow_token");
      const resp = await fetch("/api/v1/process-docs/generate-stream", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ user_input: input, diagram_type: diagramType }),
      });

      if (!resp.ok || !resp.body) {
        // Fallback to regular endpoint
        const res = await fetchApi<{ mermaid_code: string }>("POST", "/api/v1/process-docs/generate", { user_input: input, diagram_type: diagramType });
        setResult(res.mermaid_code);
        setFileProgress(prev => prev.map(fp => ({ ...fp, status: "done" as const, steps: fp.steps.map(s => ({ ...s, status: "done" as const })) })));
        refetch();
        return;
      }

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const msg = JSON.parse(line.slice(6));

            if (msg.event === "file_start") {
              setFileProgress(prev => prev.map((fp, i) =>
                i === 0 ? { ...fp, status: "processing" } : fp
              ));
            }

            if (msg.event === "file_step" && msg.step_index !== undefined) {
              setFileProgress(prev => prev.map((fp, i) => {
                if (i !== 0) return fp;
                return {
                  ...fp,
                  steps: fp.steps.map((s, si) => {
                    if (si !== msg.step_index) return s;
                    return { ...s, status: msg.status === "done" ? "done" as const : "running" as const, elapsed_ms: msg.elapsed_ms ?? s.elapsed_ms };
                  }),
                };
              }));
            }

            if (msg.event === "file_error") {
              setFileProgress(prev => prev.map((fp, i) =>
                i === 0 ? { ...fp, status: "error", error: msg.error } : fp
              ));
              setGenError(msg.error);
            }

            if (msg.event === "file_done") {
              setFileProgress(prev => prev.map((fp, i) =>
                i === 0 ? { ...fp, status: msg.ok ? "done" as const : "error" as const } : fp
              ));
            }

            if (msg.event === "complete") {
              if (msg.mermaid_code) {
                setResult(msg.mermaid_code);
                refetch();
              }
              if (msg.error) setGenError(msg.error);
            }

            if (msg.event === "error") {
              setGenError(msg.error ?? "Generation failed");
            }
          } catch { /* skip non-json */ }
        }
      }
    } catch (e) {
      setGenError(e instanceof Error ? e.message : "Generation failed");
    } finally {
      setGenerating(false);
    }
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
          <div className="mt-3 flex items-center gap-2">
            <select
              value={diagramType}
              onChange={(e) => setDiagramType(e.target.value as "flowchart" | "sequence" | "bpmn_swimlane")}
              className="rounded-lg border border-gray-300 bg-white px-2 py-2 text-xs text-gray-600 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-400"
            >
              <option value="flowchart">Flowchart</option>
              <option value="sequence">Sequence</option>
              <option value="bpmn_swimlane">BPMN Swimlane</option>
            </select>
            <button onClick={handleGenerate} disabled={generating || !input.trim()}
              className="flex-1 rounded-lg bg-brand-500 py-2 text-sm font-semibold text-white hover:bg-brand-600 disabled:opacity-50">
              {generating ? translate("aiflow.common.loading") : translate("aiflow.processDocs.generate")}
            </button>
          </div>
        </div>
        {/* Output */}
        <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
          <p className="mb-2 text-sm font-medium text-gray-700 dark:text-gray-300">{translate("aiflow.processDocs.diagram")}</p>
          <div className="flex min-h-48 items-center justify-center rounded-lg bg-gray-50 p-2 text-sm text-gray-400 dark:bg-gray-800">
            {result ? <MermaidDiagram code={result} /> : translate("aiflow.processDocs.diagramPlaceholder")}
          </div>
        </div>
      </div>

      {/* Pipeline progress */}
      {fileProgress.length > 0 && (
        <div className="mb-4 rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
          <p className="mb-2 text-sm font-medium text-gray-700 dark:text-gray-300">
            {translate("aiflow.pipeline.title")}
          </p>
          {fileProgress.map((fp, i) => (
            <FileProgressRow key={i} fp={fp} />
          ))}
        </div>
      )}
      {genError && <ErrorState error={genError} onRetry={handleGenerate} />}

      <h3 className="mb-2 text-base font-semibold text-gray-900 dark:text-gray-100">{translate("aiflow.processDocs.savedDiagrams")}</h3>
      {error ? <ErrorState error={error} onRetry={refetch} /> :
        <DataTable data={(data?.diagrams ?? []) as unknown as Record<string, unknown>[]} columns={columns} loading={loading} searchKeys={["user_input"]} />
      }
    </PageLayout>
  );
}
