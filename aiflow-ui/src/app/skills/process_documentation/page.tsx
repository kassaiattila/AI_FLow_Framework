"use client";

import { useEffect, useState, useCallback } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useI18n } from "@/hooks/use-i18n";
import { SkillViewerLayout, KpiCard } from "@/components/skill-viewer";
import { TextInputForm } from "@/components/process-docs/text-input-form";
import { DiagramPreview } from "@/components/process-docs/diagram-preview";
import { ReviewScores } from "@/components/process-docs/review-scores";
import { GenerationGallery } from "@/components/process-docs/generation-gallery";
import { ProcessStepTrace } from "@/components/process-docs/process-step-trace";
import type { ProcessDocResult } from "@/lib/types";

export default function ProcessDocumentationPage() {
  const { t } = useI18n();
  const [documents, setDocuments] = useState<ProcessDocResult[]>([]);
  const [selected, setSelected] = useState<ProcessDocResult | null>(null);
  const [generating, setGenerating] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [source, setSource] = useState<"backend" | "subprocess" | "demo" | null>(null);

  const loadData = useCallback(() => {
    setLoading(true);
    setError(null);
    fetch("/api/process-docs")
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data: { documents: ProcessDocResult[] }) => {
        setDocuments(data.documents);
        if (data.documents.length > 0 && !selected) {
          setSelected(data.documents[0]);
        }
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleGenerate = async (userInput: string) => {
    setGenerating(true);
    try {
      const res = await fetch("/api/process-docs/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_input: userInput }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const { source: src, ...doc } = data as ProcessDocResult & { source?: string };
      if (src) setSource(src as "backend" | "subprocess" | "demo");
      setSelected(doc as ProcessDocResult);
      loadData();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("processdoc.generateError"));
    } finally {
      setGenerating(false);
    }
  };

  const totalDocs = documents.length;
  const avgScore = documents.length > 0
    ? documents.reduce((sum, d) => sum + d.review.score, 0) / documents.length
    : 0;
  const totalActors = documents.reduce((sum, d) => sum + d.extraction.actors.length, 0);
  const totalSteps = documents.reduce((sum, d) => sum + d.extraction.steps.length, 0);

  return (
    <SkillViewerLayout
      skillName="processdoc"
      source={source}
      loading={loading}
      error={error}
      onRetry={loadData}
      badgeFallbackKey="processdoc.title"
    >
      {/* KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <KpiCard title={t("processdoc.generated")} value={String(totalDocs)} sub={t("common.total")} />
        <KpiCard title={t("processdoc.avgScore")} value={avgScore.toFixed(1)} sub="/ 10" />
        <KpiCard title={t("processdoc.actors")} value={String(totalActors)} sub={t("common.total")} />
        <KpiCard title={t("processdoc.steps")} value={String(totalSteps)} sub={t("common.total")} />
      </div>

      {/* Input form */}
      <TextInputForm onGenerate={handleGenerate} disabled={generating} />

      {/* Results */}
      {selected ? (
        <Tabs defaultValue="diagram">
          <TabsList>
            <TabsTrigger value="diagram">{t("processdoc.diagram")}</TabsTrigger>
            <TabsTrigger value="review">{t("processdoc.review")}</TabsTrigger>
            <TabsTrigger value="trace">{t("processdoc.pipeline")}</TabsTrigger>
            <TabsTrigger value="gallery">
              {t("processdoc.gallery")}
              <Badge className="ml-1 bg-gray-100 text-gray-700 text-[9px]">{totalDocs}</Badge>
            </TabsTrigger>
          </TabsList>

          <TabsContent value="diagram" className="mt-4">
            <DiagramPreview mermaidCode={selected.mermaid_code} title={selected.extraction.title} />
          </TabsContent>

          <TabsContent value="review" className="mt-4">
            <ReviewScores review={selected.review} />
          </TabsContent>

          <TabsContent value="trace" className="mt-4">
            <ProcessStepTrace doc={selected} source={source} isProcessing={generating} />
          </TabsContent>

          <TabsContent value="gallery" className="mt-4">
            <GenerationGallery documents={documents} selectedId={selected.doc_id} onSelect={setSelected} />
          </TabsContent>
        </Tabs>
      ) : (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            {t("processdoc.emptyState")}
          </CardContent>
        </Card>
      )}
    </SkillViewerLayout>
  );
}
