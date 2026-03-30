"use client";

import { useEffect, useState, useCallback } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { EmailTable } from "@/components/email/email-table";
import { EmailPreview } from "@/components/email/email-preview";
import { IntentBadgeDetail } from "@/components/email/intent-badge";
import { EntityList } from "@/components/email/entity-list";
import { RoutingCard } from "@/components/email/routing-card";
import { ExportButton } from "@/components/export-button";
import { useI18n } from "@/hooks/use-i18n";
import type { EmailProcessingResult } from "@/lib/types";

function KpiCard({ title, value, sub }: { title: string; value: string; sub: string }) {
  return (
    <Card>
      <CardContent className="pt-4">
        <p className="text-xs text-muted-foreground">{title}</p>
        <p className="text-2xl font-bold">{value}</p>
        <p className="text-xs text-muted-foreground">{sub}</p>
      </CardContent>
    </Card>
  );
}

export default function EmailIntentProcessorPage() {
  const { t } = useI18n();
  const [emails, setEmails] = useState<EmailProcessingResult[]>([]);
  const [selected, setSelected] = useState<EmailProcessingResult | null>(null);
  const [highlightedEntity, setHighlightedEntity] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(() => {
    setLoading(true);
    setError(null);
    fetch("/api/emails")
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data: { emails: EmailProcessingResult[] }) => {
        setEmails(data.emails);
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

  // KPI calculations
  const totalEmails = emails.length;
  const avgConfidence =
    emails.length > 0
      ? emails.reduce((sum, e) => sum + (e.intent?.confidence || 0), 0) / emails.length
      : 0;
  const avgProcessingMs =
    emails.length > 0
      ? emails.reduce((sum, e) => sum + e.processing_time_ms, 0) / emails.length
      : 0;
  const methodBreakdown = emails.reduce(
    (acc, e) => {
      const m = e.intent?.method || "unknown";
      acc[m] = (acc[m] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>
  );

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">{t("email.title")}</h2>
          <p className="text-muted-foreground">
            {t("email.desc")}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <ExportButton
            filename={`emails_${new Date().toISOString().slice(0, 10)}.csv`}
            headers={["ID", "Felado", "Targy", "Intent", "Confidence", "Prioritas", "Osztaly", "Datum"]}
            rows={emails.map((e) => [
              e.email_id,
              e.sender,
              e.subject,
              e.intent?.intent_display_name || "",
              String(e.intent?.confidence || 0),
              String(e.priority?.priority_level || ""),
              e.routing?.department_name || "",
              e.received_date,
            ])}
          />
          <Badge className="bg-blue-100 text-blue-800 text-sm px-3 py-1">{t("common.inDevelopment")}</Badge>
        </div>
      </div>

      {loading && (
        <Card><CardContent className="py-12 text-center text-muted-foreground">{t("common.loading")}</CardContent></Card>
      )}

      {error && (
        <Card><CardContent className="py-8 text-center">
          <p className="text-red-600 text-sm mb-2">{t("common.errorPrefix")}{error}</p>
          <button onClick={loadData} className="text-sm text-blue-600 underline">{t("common.retry")}</button>
        </CardContent></Card>
      )}

      {!loading && !error && <>
      {/* KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <KpiCard
          title={t("email.processed")}
          value={String(totalEmails)}
          sub={t("email.emailUnit")}
        />
        <KpiCard
          title={t("email.avgConfidence")}
          value={`${(avgConfidence * 100).toFixed(1)}%`}
          sub={t("email.intentRecognition")}
        />
        <KpiCard
          title={t("email.avgProcessing")}
          value={`${avgProcessingMs.toFixed(0)} ms`}
          sub={t("email.perEmail")}
        />
        <KpiCard
          title={t("email.methodLabel")}
          value={Object.entries(methodBreakdown)
            .map(([k, v]) => `${k}: ${v}`)
            .join(", ") || "-"}
          sub={t("email.methodTypes")}
        />
      </div>

      {/* Main content: table + detail */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Email list */}
        <div>
          <EmailTable
            emails={emails}
            selectedId={selected?.email_id || null}
            onSelect={setSelected}
          />
        </div>

        {/* Right: Detail panel */}
        <div>
          {selected ? (
            <Tabs defaultValue="preview">
              <TabsList>
                <TabsTrigger value="preview">{t("email.tabEmail")}</TabsTrigger>
                <TabsTrigger value="intent">{t("email.tabIntent")}</TabsTrigger>
                <TabsTrigger value="entities">{t("email.tabEntities")}</TabsTrigger>
                <TabsTrigger value="routing">{t("email.tabRouting")}</TabsTrigger>
              </TabsList>

              <TabsContent value="preview" className="mt-4">
                <EmailPreview
                  email={selected}
                  highlightedEntity={highlightedEntity}
                />
              </TabsContent>

              <TabsContent value="intent" className="mt-4">
                {selected.intent ? (
                  <IntentBadgeDetail intent={selected.intent} />
                ) : (
                  <p className="text-muted-foreground text-sm">{t("email.noIntent")}</p>
                )}
              </TabsContent>

              <TabsContent value="entities" className="mt-4">
                {selected.entities ? (
                  <EntityList
                    entities={selected.entities}
                    highlightedEntity={highlightedEntity}
                    onEntityHover={setHighlightedEntity}
                  />
                ) : (
                  <p className="text-muted-foreground text-sm">{t("email.noEntity")}</p>
                )}
              </TabsContent>

              <TabsContent value="routing" className="mt-4">
                {selected.routing && selected.priority ? (
                  <RoutingCard routing={selected.routing} priority={selected.priority} />
                ) : (
                  <p className="text-muted-foreground text-sm">{t("email.noRouting")}</p>
                )}
              </TabsContent>
            </Tabs>
          ) : (
            <Card>
              <CardContent className="py-12 text-center text-muted-foreground">
                {t("email.selectEmail")}
              </CardContent>
            </Card>
          )}
        </div>
      </div>
      </>}
    </div>
  );
}
