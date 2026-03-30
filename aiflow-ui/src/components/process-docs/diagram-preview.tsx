"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

interface DiagramPreviewProps {
  mermaidCode: string;
  title: string;
}

export function DiagramPreview({ mermaidCode, title }: DiagramPreviewProps) {
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
        setSvgError("Kroki szerver nem elerheto — nyers Mermaid kod megjelenitese");
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
            <TabsTrigger value="diagram">Diagram</TabsTrigger>
            <TabsTrigger value="code">Mermaid kod</TabsTrigger>
          </TabsList>

          <TabsContent value="diagram" className="mt-3">
            {loading && (
              <div className="flex items-center justify-center py-12 text-sm text-muted-foreground">
                Diagram renderelese...
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
                Generaljon egy diagramot a folyamat leirasabol
              </div>
            )}
          </TabsContent>

          <TabsContent value="code" className="mt-3">
            <pre className="p-4 bg-muted rounded text-xs overflow-x-auto whitespace-pre-wrap font-mono">
              {mermaidCode || "Nincs mermaid kod"}
            </pre>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
