"use client";

import { useState, useEffect } from "react";
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
  const [svgError, setSvgError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!mermaidCode) return;

    setLoading(true);
    setSvgError(null);

    // Try Kroki server for rendering (2s timeout)
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 2000);

    fetch("/api/kroki", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ diagram_type: "mermaid", source: mermaidCode, output_format: "svg" }),
      signal: controller.signal,
    })
      .then((r) => {
        if (!r.ok) throw new Error(`Kroki ${r.status}`);
        return r.text();
      })
      .then((svg) => setSvgHtml(svg))
      .catch(() => {
        setSvgError(t("processdoc.krokiError"));
      })
      .finally(() => {
        clearTimeout(timeout);
        setLoading(false);
      });
  }, [mermaidCode]);

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
                {t("processdoc.rendering")}
              </div>
            )}
            {!loading && svgHtml && (
              <div
                className="w-full overflow-auto border rounded p-4 bg-white"
                dangerouslySetInnerHTML={{ __html: svgHtml }}
              />
            )}
            {!loading && svgError && (
              <div className="space-y-2">
                <p className="text-xs text-muted-foreground">{svgError}</p>
                <pre className="p-4 bg-muted rounded text-xs overflow-x-auto whitespace-pre-wrap font-mono">
                  {mermaidCode}
                </pre>
              </div>
            )}
            {!loading && !svgHtml && !svgError && !mermaidCode && (
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
