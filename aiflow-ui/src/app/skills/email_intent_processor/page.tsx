"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { EmailTable } from "@/components/email/email-table";
import { EmailPreview } from "@/components/email/email-preview";
import { IntentBadgeDetail } from "@/components/email/intent-badge";
import { EntityList } from "@/components/email/entity-list";
import { RoutingCard } from "@/components/email/routing-card";
import { EmailUploadZone } from "@/components/email/email-upload-zone";
import { ProcessingPipeline } from "@/components/processing-pipeline";
import { ExportButton } from "@/components/export-button";
import { SkillViewerLayout, KpiCard } from "@/components/skill-viewer";
import { useI18n } from "@/hooks/use-i18n";
import type { EmailProcessingResult, StepExecution } from "@/lib/types";

const EMAIL_STEP_NAMES = [
  "parse_email",
  "process_attachments",
  "classify_intent",
  "extract_entities",
  "score_priority",
  "decide_routing",
];

function buildEmailPipelineSteps(email: EmailProcessingResult | null): StepExecution[] {
  return EMAIL_STEP_NAMES.map((name) => {
    let status: StepExecution["status"] = "pending";
    let outputPreview = "";
    let confidence = 1;

    if (email) {
      switch (name) {
        case "parse_email":
          status = "completed";
          outputPreview = email.subject || "";
          break;
        case "process_attachments":
          status = "completed";
          outputPreview = email.has_attachments ? `${email.attachment_count || 0} attachments` : "no attachments";
          break;
        case "classify_intent":
          status = email.intent ? "completed" : "pending";
          outputPreview = email.intent
            ? `${email.intent.intent_display_name} (${email.intent.method})`
            : "";
          confidence = email.intent?.confidence || 1;
          break;
        case "extract_entities":
          status = email.entities ? "completed" : "pending";
          outputPreview = email.entities
            ? `${email.entities.entities?.length || 0} entities`
            : "";
          break;
        case "score_priority":
          status = email.priority ? "completed" : "pending";
          outputPreview = email.priority
            ? `P${email.priority.priority_level} — ${email.priority.priority_name}`
            : "";
          break;
        case "decide_routing":
          status = email.routing ? "completed" : "pending";
          outputPreview = email.routing
            ? `${email.routing.department_name} → ${email.routing.queue_id}`
            : "";
          break;
      }
    }

    return {
      step_name: name,
      status,
      duration_ms: 0,
      input_preview: "",
      output_preview: outputPreview,
      cost_usd: 0,
      tokens_used: 0,
      confidence,
      error: "",
    };
  });
}

export default function EmailIntentProcessorPage() {
  const { t } = useI18n();
  const [emails, setEmails] = useState<EmailProcessingResult[]>([]);
  const [selected, setSelected] = useState<EmailProcessingResult | null>(null);
  const [highlightedEntity, setHighlightedEntity] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [intentFilter, setIntentFilter] = useState("all");
  const [priorityFilter, setPriorityFilter] = useState("all");
  const [uploadedFiles, setUploadedFiles] = useState<string[]>([]);
  const [processing, setProcessing] = useState(false);
  const [source, setSource] = useState<"backend" | "subprocess" | "demo" | null>(null);

  const loadData = useCallback(() => {
    setLoading(true);
    setError(null);
    fetch("/api/emails")
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data: { emails: EmailProcessingResult[]; source?: string }) => {
        setEmails(data.emails);
        if (data.source) setSource(data.source as "backend" | "demo");
        if (data.emails.length > 0 && !selected) {
          setSelected(data.emails[0]);
        }
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleFilesUploaded = useCallback((files: string[]) => {
    setUploadedFiles((prev) => [...prev, ...files]);
  }, []);

  const handleProcess = useCallback(async () => {
    if (uploadedFiles.length === 0) return;
    setProcessing(true);
    for (const file of uploadedFiles) {
      try {
        const res = await fetch("/api/emails/process", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ file }),
        });
        if (res.ok) {
          const data = await res.json();
          if (data.source) setSource(data.source as "backend" | "subprocess");
        }
      } catch {
        // continue with next file
      }
    }
    setUploadedFiles([]);
    setProcessing(false);
    loadData();
  }, [uploadedFiles, loadData]);

  const intentOptions = useMemo(() => {
    const intents = new Set(emails.map((e) => e.intent?.intent_id).filter(Boolean));
    return [...intents] as string[];
  }, [emails]);

  const priorityOptions = useMemo(() => {
    const priorities = new Set(emails.map((e) => e.priority?.priority_level).filter(Boolean));
    return [...priorities].sort() as number[];
  }, [emails]);

  const filtered = useMemo(() => {
    return emails.filter((e) => {
      if (intentFilter !== "all" && e.intent?.intent_id !== intentFilter) return false;
      if (priorityFilter !== "all" && String(e.priority?.priority_level) !== priorityFilter) return false;
      return true;
    });
  }, [emails, intentFilter, priorityFilter]);

  const totalEmails = emails.length;
  const avgConfidence = totalEmails > 0
    ? emails.reduce((sum, e) => sum + (e.intent?.confidence || 0), 0) / totalEmails
    : 0;
  const mlCount = emails.filter((e) => e.intent?.method === "sklearn").length;
  const mlRate = totalEmails > 0 ? (mlCount / totalEmails) * 100 : 0;
  const highPriorityCount = emails.filter((e) => (e.priority?.priority_level || 5) <= 2).length;
  const withAttachments = emails.filter((e) => e.has_attachments).length;

  const exportButton = (
    <ExportButton
      filename={`emails_${new Date().toISOString().slice(0, 10)}.csv`}
      headers={[t("table.sender"), t("table.subject"), t("table.intent"), "Confidence", t("table.priority"), t("email.department"), t("common.date")]}
      rows={filtered.map((e) => [
        e.sender, e.subject, e.intent?.intent_display_name || "",
        String(e.intent?.confidence || 0), String(e.priority?.priority_level || ""),
        e.routing?.department_name || "", e.received_date,
      ])}
    />
  );

  return (
    <SkillViewerLayout
      skillName="email"
      source={source}
      loading={loading}
      error={error}
      onRetry={loadData}
      badgeFallbackKey="common.inDevelopment"
      headerActions={exportButton}
    >
      {/* Upload zone + process button */}
      <div className="flex items-center gap-3">
        <div className="flex-1">
          <EmailUploadZone onFilesUploaded={handleFilesUploaded} />
        </div>
        {uploadedFiles.length > 0 && (
          <button
            onClick={handleProcess}
            disabled={processing}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium disabled:opacity-50"
          >
            {processing ? t("email.processing") : `${t("email.processBtn")} (${uploadedFiles.length})`}
          </button>
        )}
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <KpiCard title={t("email.processed")} value={String(totalEmails)} sub={`${filtered.length} ${t("email.emailUnit")}`} />
        <KpiCard title={t("email.avgConfidence")} value={`${(avgConfidence * 100).toFixed(0)}%`} sub={t("email.intentRecognition")} />
        <KpiCard title={t("email.mlRate")} value={`${mlRate.toFixed(0)}%`} sub={`${mlCount} / ${totalEmails}`} />
        <KpiCard title={t("email.highPriority")} value={String(highPriorityCount)} sub="P1-P2" />
        <KpiCard title={t("email.withAttachments")} value={String(withAttachments)} sub={`/ ${totalEmails}`} />
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        <select value={intentFilter} onChange={(e) => setIntentFilter(e.target.value)} className="h-8 px-2 text-xs rounded-md border border-input bg-background">
          <option value="all">{t("email.filterAll")} — Intent</option>
          {intentOptions.map((intent) => <option key={intent} value={intent}>{intent}</option>)}
        </select>
        <select value={priorityFilter} onChange={(e) => setPriorityFilter(e.target.value)} className="h-8 px-2 text-xs rounded-md border border-input bg-background">
          <option value="all">{t("email.filterAll")} — {t("table.priority")}</option>
          {priorityOptions.map((p) => <option key={p} value={String(p)}>P{p}</option>)}
        </select>
        {(intentFilter !== "all" || priorityFilter !== "all") && (
          <button onClick={() => { setIntentFilter("all"); setPriorityFilter("all"); }} className="text-xs text-blue-600 underline">{t("common.reset")}</button>
        )}
        <span className="text-xs text-muted-foreground ml-auto">{filtered.length} / {totalEmails}</span>
      </div>

      {/* Main content: table + detail */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div>
          <EmailTable emails={filtered} selectedId={selected?.email_id || null} onSelect={setSelected} />
        </div>
        <div>
          {selected ? (
            <Tabs defaultValue="preview">
              <TabsList>
                <TabsTrigger value="preview">{t("email.tabEmail")}</TabsTrigger>
                <TabsTrigger value="intent">{t("email.tabIntent")}</TabsTrigger>
                <TabsTrigger value="entities">{t("email.tabEntities")}</TabsTrigger>
                <TabsTrigger value="routing">{t("email.tabRouting")}</TabsTrigger>
                <TabsTrigger value="pipeline">{t("pipeline.title")}</TabsTrigger>
              </TabsList>

              <TabsContent value="preview" className="mt-4">
                <EmailPreview email={selected} highlightedEntity={highlightedEntity} />
              </TabsContent>
              <TabsContent value="intent" className="mt-4">
                {selected.intent ? <IntentBadgeDetail intent={selected.intent} /> : <p className="text-muted-foreground text-sm">{t("email.noIntent")}</p>}
              </TabsContent>
              <TabsContent value="entities" className="mt-4">
                {selected.entities ? <EntityList entities={selected.entities} highlightedEntity={highlightedEntity} onEntityHover={setHighlightedEntity} /> : <p className="text-muted-foreground text-sm">{t("email.noEntity")}</p>}
              </TabsContent>
              <TabsContent value="routing" className="mt-4">
                {selected.routing && selected.priority ? <RoutingCard routing={selected.routing} priority={selected.priority} /> : <p className="text-muted-foreground text-sm">{t("email.noRouting")}</p>}
              </TabsContent>
              <TabsContent value="pipeline" className="mt-4">
                <ProcessingPipeline steps={buildEmailPipelineSteps(selected)} source={source} isProcessing={processing} />
              </TabsContent>
            </Tabs>
          ) : (
            <Card><CardContent className="py-12 text-center text-muted-foreground">{t("email.selectEmail")}</CardContent></Card>
          )}
        </div>
      </div>
    </SkillViewerLayout>
  );
}
