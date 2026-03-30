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
          <h2 className="text-2xl font-bold">Email Intent Processor</h2>
          <p className="text-muted-foreground">
            Email + csatolmany feldolgozo (hibrid ML+LLM)
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
          <Badge className="bg-blue-100 text-blue-800 text-sm px-3 py-1">In Development</Badge>
        </div>
      </div>

      {loading && (
        <Card><CardContent className="py-12 text-center text-muted-foreground">Betoltes...</CardContent></Card>
      )}

      {error && (
        <Card><CardContent className="py-8 text-center">
          <p className="text-red-600 text-sm mb-2">Hiba: {error}</p>
          <button onClick={loadData} className="text-sm text-blue-600 underline">Ujraprobalkozas</button>
        </CardContent></Card>
      )}

      {!loading && !error && <>
      {/* KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <KpiCard
          title="Feldolgozott"
          value={String(totalEmails)}
          sub="email"
        />
        <KpiCard
          title="Atl. confidence"
          value={`${(avgConfidence * 100).toFixed(1)}%`}
          sub="intent felismeres"
        />
        <KpiCard
          title="Atl. feldolgozas"
          value={`${avgProcessingMs.toFixed(0)} ms`}
          sub="per email"
        />
        <KpiCard
          title="Modszer"
          value={Object.entries(methodBreakdown)
            .map(([k, v]) => `${k}: ${v}`)
            .join(", ") || "-"}
          sub="ML / LLM / hybrid"
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
                <TabsTrigger value="preview">Email</TabsTrigger>
                <TabsTrigger value="intent">Intent</TabsTrigger>
                <TabsTrigger value="entities">Entitasok</TabsTrigger>
                <TabsTrigger value="routing">Routing</TabsTrigger>
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
                  <p className="text-muted-foreground text-sm">Nincs intent adat</p>
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
                  <p className="text-muted-foreground text-sm">Nincs entity adat</p>
                )}
              </TabsContent>

              <TabsContent value="routing" className="mt-4">
                {selected.routing && selected.priority ? (
                  <RoutingCard routing={selected.routing} priority={selected.priority} />
                ) : (
                  <p className="text-muted-foreground text-sm">Nincs routing adat</p>
                )}
              </TabsContent>
            </Tabs>
          ) : (
            <Card>
              <CardContent className="py-12 text-center text-muted-foreground">
                Valassz egy emailt a listabol
              </CardContent>
            </Card>
          )}
        </div>
      </div>
      </>}
    </div>
  );
}
