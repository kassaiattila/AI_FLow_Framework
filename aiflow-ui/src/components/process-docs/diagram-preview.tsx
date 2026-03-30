"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useI18n } from "@/hooks/use-i18n";

interface DiagramPreviewProps {
  mermaidCode: string;
  title: string;
}

export function DiagramPreview({ mermaidCode, title }: DiagramPreviewProps) {
  const { t } = useI18n();
  const [svgHtml, setSvgHtml] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const renderIdRef = useRef(0);

  const renderDiagram = useCallback(async (code: string) => {
    if (!code) return;

    setLoading(true);
    setError(null);
    setSvgHtml(null);
    renderIdRef.current++;
    const currentId = renderIdRef.current;

    try {
      // Client-side Mermaid rendering (no server dependency)
      const mermaid = (await import("mermaid")).default;
      mermaid.initialize({
        startOnLoad: false,
        theme: "default",
        securityLevel: "loose",
        fontFamily: "var(--font-sans)",
      });

      const { svg } = await mermaid.render(`mermaid-${currentId}`, code);
      if (currentId === renderIdRef.current) {
        setSvgHtml(svg);
      }
    } catch (mermaidErr) {
      // Mermaid failed — try Kroki as fallback
      try {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 3000);
        const res = await fetch("/api/kroki", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ diagram_type: "mermaid", source: code, output_format: "svg" }),
          signal: controller.signal,
        });
        clearTimeout(timeout);
        if (res.ok) {
          const svg = await res.text();
          if (currentId === renderIdRef.current) setSvgHtml(svg);
        } else {
          throw new Error("Kroki failed");
        }
      } catch {
        if (currentId === renderIdRef.current) {
          const msg = mermaidErr instanceof Error ? mermaidErr.message : "";
          setError(msg ? `Mermaid: ${msg}` : t("processdoc.krokiError"));
        }
      }
    } finally {
      if (currentId === renderIdRef.current) setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    renderDiagram(mermaidCode);
  }, [mermaidCode, renderDiagram]);

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="diagram">
          <TabsList>
            <TabsTrigger value="diagram">{t("processdoc.diagram")}</TabsTrigger>
            <TabsTrigger value="code">{t("processdoc.tabMermaid")}</TabsTrigger>
          </TabsList>

          <TabsContent value="diagram" className="mt-3">
            {loading && (
              <div className="flex items-center justify-center py-12 text-sm text-muted-foreground">
                <div className="w-32 h-1.5 bg-muted rounded-full overflow-hidden">
                  <div className="h-full w-1/3 bg-primary rounded-full animate-pulse" />
                </div>
                <span className="ml-3">{t("processdoc.renderLoading")}</span>
              </div>
            )}
            {!loading && svgHtml && (
              <div
                ref={containerRef}
                className="w-full overflow-auto border rounded p-4 bg-white dark:bg-muted/30"
                dangerouslySetInnerHTML={{ __html: svgHtml }}
              />
            )}
            {!loading && error && (
              <div className="space-y-2">
                <p className="text-xs text-muted-foreground">{error}</p>
                <pre className="p-4 bg-muted rounded text-xs overflow-x-auto whitespace-pre-wrap font-mono">
                  {mermaidCode}
                </pre>
              </div>
            )}
            {!loading && !svgHtml && !error && !mermaidCode && (
              <div className="text-center text-muted-foreground py-12 text-sm">
                {t("processdoc.emptyDiagram")}
              </div>
            )}
          </TabsContent>

          <TabsContent value="code" className="mt-3">
            <pre className="p-4 bg-muted rounded text-xs overflow-x-auto whitespace-pre-wrap font-mono">
              {mermaidCode || t("processdoc.noMermaid")}
            </pre>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
