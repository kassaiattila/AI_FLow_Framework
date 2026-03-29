"use client";

import { useEffect, useState, useMemo, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { VerificationPanel } from "@/components/verification/verification-panel";
import { DocumentDetail } from "@/components/invoice/document-detail";
import { ProcessingTab } from "@/components/invoice/processing-tab";
import { ConfidenceBadge } from "@/components/invoice/shared";
import type { ProcessedInvoice, WorkflowRun } from "@/lib/types";

function ReviewContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const currentFile = searchParams.get("file") || "";

  const [invoices, setInvoices] = useState<ProcessedInvoice[]>([]);
  const [runs, setRuns] = useState<WorkflowRun[]>([]);
  const [tab, setTab] = useState("verifikacio");

  // Load data from API
  useEffect(() => {
    fetch("/api/documents").then((r) => r.json()).then((d: { documents: ProcessedInvoice[] }) => setInvoices(d.documents)).catch(() => {});
    fetch("/api/runs?skill=invoice_processor").then((r) => r.json()).then((d: { runs: WorkflowRun[] }) => setRuns(d.runs)).catch(() => {});
  }, []);

  // Current invoice
  const invoice = useMemo(
    () => invoices.find((i) => i.source_file === currentFile) || null,
    [invoices, currentFile]
  );

  // Queue from sessionStorage for prev/next
  const queue = useMemo(() => {
    try {
      const raw = sessionStorage.getItem("review_queue");
      return raw ? JSON.parse(raw) as string[] : invoices.map((i) => i.source_file);
    } catch {
      return invoices.map((i) => i.source_file);
    }
  }, [invoices]);

  const currentIdx = queue.indexOf(currentFile);
  const prevFile = currentIdx > 0 ? queue[currentIdx - 1] : null;
  const nextFile = currentIdx < queue.length - 1 ? queue[currentIdx + 1] : null;

  const goTo = (file: string) => router.push(`/skills/invoice_processor/review?file=${encodeURIComponent(file)}`);

  if (!invoice) {
    return (
      <div className="p-6">
        <p className="text-muted-foreground">Dokumentum betoltese...</p>
      </div>
    );
  }

  const conf = invoice.extraction_confidence || invoice.validation.confidence_score;

  return (
    <div className="flex flex-col h-screen">
      {/* Top nav bar */}
      <div className="shrink-0 border-b px-4 py-2 flex items-center gap-3 bg-background">
        <button
          onClick={() => router.push("/skills/invoice_processor")}
          className="text-sm text-muted-foreground hover:text-foreground"
        >
          &larr; Vissza
        </button>
        <div className="h-4 w-px bg-border" />
        <span className="text-sm font-medium truncate max-w-[300px]">{invoice.vendor.name || invoice.source_file}</span>
        <Badge variant="outline" className="text-[10px]">{invoice.header.invoice_number}</Badge>
        {conf > 0 && <ConfidenceBadge value={conf} />}

        <div className="flex-1" />

        <span className="text-xs text-muted-foreground">
          {currentIdx + 1}/{queue.length}
        </span>
        <button
          disabled={!prevFile}
          onClick={() => prevFile && goTo(prevFile)}
          className="px-2 py-1 rounded text-xs border border-border disabled:opacity-30 hover:bg-muted"
        >
          &#9664; Elozo
        </button>
        <button
          disabled={!nextFile}
          onClick={() => nextFile && goTo(nextFile)}
          className="px-2 py-1 rounded text-xs border border-border disabled:opacity-30 hover:bg-muted"
        >
          Kovetkezo &#9654;
        </button>
      </div>

      {/* Content with tabs */}
      <Tabs value={tab} onValueChange={setTab} className="flex-1 flex flex-col min-h-0">
        <div className="shrink-0 px-4 pt-2">
          <TabsList>
            <TabsTrigger value="verifikacio">Dok. verifikacio</TabsTrigger>
            <TabsTrigger value="reszletek">Reszletek</TabsTrigger>
            <TabsTrigger value="feldolgozas">Feldolgozas</TabsTrigger>
          </TabsList>
        </div>

        <TabsContent value="verifikacio" className="flex-1 overflow-y-auto p-4">
          <VerificationPanel key={invoice.source_file} invoice={invoice} />
        </TabsContent>

        <TabsContent value="reszletek" className="flex-1 overflow-y-auto p-4">
          <DocumentDetail invoice={invoice} />
        </TabsContent>

        <TabsContent value="feldolgozas" className="flex-1 overflow-y-auto p-4">
          <ProcessingTab key={invoice.source_file} invoice={invoice} runs={runs} />
        </TabsContent>
      </Tabs>
    </div>
  );
}

export default function ReviewPage() {
  return (
    <Suspense fallback={<div className="p-6 text-muted-foreground">Betoltes...</div>}>
      <ReviewContent />
    </Suspense>
  );
}
