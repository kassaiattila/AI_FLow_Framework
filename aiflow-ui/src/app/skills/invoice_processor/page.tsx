"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent } from "@/components/ui/card";
import { UploadZone } from "@/components/invoice/upload-zone";
import { DocumentTable, type SortField } from "@/components/invoice/document-table";
import { BatchBanner, type BatchState, type BatchItem, saveBatchToSession, loadBatchFromSession, clearBatchSession } from "@/components/invoice/batch-banner";
import { ScheduleDialog } from "@/components/invoice/schedule-dialog";
import { getDocStatus, type DocStatus } from "@/components/invoice/shared";
import { SkillViewerLayout, KpiCard } from "@/components/skill-viewer";
import { ExportButton } from "@/components/export-button";
import { useI18n } from "@/hooks/use-i18n";
import type { ProcessedInvoice, WorkflowRun } from "@/lib/types";

type StatusFilter = "all" | "new" | "completed" | "failed";
type TimeFilter = "all" | "24h" | "7d" | "30d";

export default function InvoiceProcessorPage() {
  const { t } = useI18n();
  const router = useRouter();
  const [invoices, setInvoices] = useState<ProcessedInvoice[]>([]);
  const [runs, setRuns] = useState<WorkflowRun[]>([]);
  const [docStatuses, setDocStatuses] = useState<Map<string, DocStatus>>(new Map());
  const [checkedIds, setCheckedIds] = useState<Set<string>>(new Set());
  const [sortField, setSortField] = useState<SortField>("date");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [timeFilter, setTimeFilter] = useState<TimeFilter>("all");
  const [onlyUnprocessed, setOnlyUnprocessed] = useState(false);
  const [autoProcess, setAutoProcess] = useState(false);
  const [scheduleOpen, setScheduleOpen] = useState(false);
  const [batchState, setBatchState] = useState<BatchState>({ status: "idle" });
  const [page, setPage] = useState(0);
  const batchAbortRef = useRef(false);
  const batchItemsRef = useRef<BatchItem[]>([]);

  // Restore batch state from sessionStorage (client-only, avoids hydration mismatch)
  useEffect(() => {
    const saved = loadBatchFromSession();
    if (!saved) return;
    if (saved.status === "running") {
      const items = saved.items || [];
      const succeeded = items.filter((i) => i.status === "completed").length;
      const failed = items.filter((i) => i.status === "failed").length;
      setBatchState({ status: "completed", total: saved.total, succeeded, failed, durationMs: 0, items });
    } else {
      setBatchState(saved);
    }
  }, []);

  // Load data from API
  const loadData = useCallback(() => {
    fetch("/api/documents")
      .then((r) => r.json())
      .then((data: { documents: ProcessedInvoice[] }) => {
        setInvoices(data.documents);
        const s = new Map<string, DocStatus>();
        for (const inv of data.documents) s.set(inv.source_file, getDocStatus(inv));
        setDocStatuses(s);
      })
      .catch(() => {});
    fetch("/api/runs?skill=invoice_processor")
      .then((r) => r.json())
      .then((data: { runs: WorkflowRun[] }) => setRuns(data.runs))
      .catch(() => {});
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  // Persist batch state to sessionStorage (survives navigation)
  useEffect(() => {
    saveBatchToSession(batchState);
  }, [batchState]);

  // Filtered invoices
  const filtered = invoices.filter((inv) => {
    if (statusFilter !== "all") {
      const s = docStatuses.get(inv.source_file) || "completed";
      if (s !== statusFilter) return false;
    }
    if (timeFilter !== "all") {
      const ms = timeFilter === "24h" ? 86400000 : timeFilter === "7d" ? 604800000 : 2592000000;
      if (Date.now() - new Date(inv.header.invoice_date).getTime() > ms) return false;
    }
    if (onlyUnprocessed) {
      const s = docStatuses.get(inv.source_file) || "completed";
      if (s !== "new") return false;
    }
    return true;
  });

  // Handlers
  const handleToggleCheck = useCallback((sf: string) => {
    setCheckedIds((prev) => { const n = new Set(prev); n.has(sf) ? n.delete(sf) : n.add(sf); return n; });
  }, []);

  const handleToggleAll = useCallback(() => {
    setCheckedIds((prev) => prev.size === filtered.length ? new Set() : new Set(filtered.map((i) => i.source_file)));
  }, [filtered]);

  const handleSelectUnprocessed = useCallback(() => {
    const unproc = invoices.filter((i) => (docStatuses.get(i.source_file) || "completed") === "new").map((i) => i.source_file);
    setCheckedIds(new Set(unproc));
  }, [invoices, docStatuses]);

  const handleOpenReview = useCallback((inv: ProcessedInvoice) => {
    const ids = filtered.map((i) => i.source_file);
    sessionStorage.setItem("review_queue", JSON.stringify(ids));
    router.push(`/skills/invoice_processor/review?file=${encodeURIComponent(inv.source_file)}`);
  }, [router, filtered]);

  // Upload — persist via API
  // Called after upload API has saved files + updated invoices.json
  const handleFilesUploaded = useCallback((fileNames: string[]) => {
    loadData(); // Reload to pick up the new entries

    if (autoProcess && fileNames.length > 0) {
      const ids = new Set(fileNames);
      setCheckedIds(ids);
      setTimeout(() => startBatch(ids), 500);
    }
  }, [autoProcess, loadData]);

  // Batch — calls API for each batch, results are persisted + items tracked
  const startBatch = useCallback(async (overrideIds?: Set<string>) => {
    const targets = overrideIds || checkedIds;
    const toProcess = Array.from(targets);
    if (toProcess.length === 0) return;

    batchAbortRef.current = false;
    const total = toProcess.length;
    const startedAt = Date.now();
    let current = 0;
    let succeeded = 0;
    let failed = 0;

    // Initialize batch items
    const items: BatchItem[] = toProcess.map((file) => ({
      file,
      displayName: file.replace(/\.pdf$/i, "").replace(/_/g, " ").slice(0, 25),
      status: "pending" as const,
    }));
    batchItemsRef.current = items;

    const updateItems = () => [...batchItemsRef.current];

    setBatchState({ status: "running", total, current: 0, currentFile: toProcess[0], startedAt, items: updateItems() });

    async function processNext() {
      if (batchAbortRef.current || current >= total) {
        setBatchState({ status: "completed", total, succeeded, failed, durationMs: Date.now() - startedAt, items: updateItems() });
        setCheckedIds(new Set());
        loadData();
        return;
      }

      const file = toProcess[current];

      // Update item to processing (no fake step names — honest progress)
      batchItemsRef.current[current] = { ...batchItemsRef.current[current], status: "processing" };
      setBatchState({ status: "running", total, current, currentFile: file, startedAt, items: updateItems() });
      setDocStatuses((p) => new Map(p).set(file, "processing"));

      try {
        const res = await fetch("/api/documents/process", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ files: [file] }),
        });
        const result = await res.json();

        const conf = result.processed?.[0]?.confidence || 0;
        if (result.processed?.[0]?.success) {
          succeeded++;
          batchItemsRef.current[current] = { ...batchItemsRef.current[current], status: "completed", step: undefined, confidence: conf };
          setDocStatuses((p) => new Map(p).set(file, "completed"));
        } else {
          failed++;
          batchItemsRef.current[current] = { ...batchItemsRef.current[current], status: "failed", step: undefined };
          setDocStatuses((p) => new Map(p).set(file, "failed"));
        }
      } catch {
        failed++;
        batchItemsRef.current[current] = { ...batchItemsRef.current[current], status: "failed", step: undefined };
        setDocStatuses((p) => new Map(p).set(file, "failed"));
      }

      current++;
      await processNext();
    }

    await processNext();
  }, [checkedIds, loadData]);

  const handleBatchStop = useCallback(() => { batchAbortRef.current = true; }, []);
  const handleBatchDismiss = useCallback(() => {
    setBatchState({ status: "idle" });
    clearBatchSession();
    setCheckedIds(new Set());
    loadData();
  }, [loadData]);

  // KPIs
  const completedCount = Array.from(docStatuses.values()).filter((s) => s === "completed" || s === "verified").length;
  const totalCost = runs.reduce((s, r) => s + r.total_cost_usd, 0);
  const totalHUF = invoices.filter((i) => i.header.currency === "HUF").reduce((s, i) => s + i.totals.gross_total, 0);

  return (
    <SkillViewerLayout
      skillName="invoice"
      source={null}
      loading={false}
      error={null}
      onRetry={() => loadData()}
      badgeFallbackKey="common.inDevelopment"
    >
      {/* 1. Input — upload zone */}
      <UploadZone onFilesUploaded={handleFilesUploaded} autoProcess={autoProcess} onAutoProcessChange={setAutoProcess} />

      {/* 2. KPIs — 4 columns */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KpiCard title={t("invoice.documents")} value={invoices.length.toString()} sub={`${completedCount} ${t("invoice.processed")}`} />
        <KpiCard title={t("invoice.hufTotal")} value={totalHUF >= 1000 ? `${Math.round(totalHUF / 1000)}k Ft` : `${totalHUF} Ft`} sub={`${invoices.filter((i) => i.header.currency === "HUF").length} ${t("invoice.invoiceUnit")}`} />
        <KpiCard title={t("invoice.runs")} value={runs.length.toString()} sub={`${runs.filter((r) => r.status === "completed").length} ${t("invoice.successful")}`} />
        <KpiCard title={t("invoice.llmCost")} value={`$${totalCost.toFixed(3)}`} sub={`${runs.length} ${t("invoice.fromRuns")}`} />
      </div>

      {batchState.status !== "idle" && (
        <BatchBanner state={batchState} onStop={handleBatchStop} onDismiss={handleBatchDismiss} />
      )}

      <Card>
        <CardContent className="py-3 px-4">
          <div className="flex items-center gap-3 flex-wrap">
            <select value={timeFilter} onChange={(e) => { setTimeFilter(e.target.value as TimeFilter); setPage(0); }} className="h-8 px-2 text-xs rounded-md border border-input bg-background">
              <option value="all">{t("invoice.timeAll")}</option>
              <option value="24h">{t("invoice.time24h")}</option>
              <option value="7d">{t("invoice.time7d")}</option>
              <option value="30d">{t("invoice.time30d")}</option>
            </select>
            <select value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value as StatusFilter); setPage(0); }} className="h-8 px-2 text-xs rounded-md border border-input bg-background">
              <option value="all">{t("invoice.statusAll")}</option>
              <option value="new">{t("invoice.statusNew")}</option>
              <option value="completed">{t("invoice.statusDone")}</option>
              <option value="failed">{t("invoice.statusFailed")}</option>
            </select>
            <label className="flex items-center gap-1.5 text-xs text-muted-foreground cursor-pointer">
              <input type="checkbox" checked={onlyUnprocessed} onChange={(e) => setOnlyUnprocessed(e.target.checked)} className="size-3.5 accent-primary" />
              {t("invoice.onlyUnprocessed")}
            </label>
            <div className="flex-1" />
            <ExportButton
              filename={`szamlak_${new Date().toISOString().slice(0, 10)}.csv`}
              headers={[t("common.file"), t("invoice.vendor"), t("invoice.invoiceNumber"), t("common.date"), t("invoice.netAmount"), t("invoice.vatRate"), t("invoice.grossAmount"), t("invoice.currency"), t("common.status")]}
              rows={filtered.map((inv) => [
                inv.source_file,
                inv.vendor?.name || "",
                inv.header?.invoice_number || "",
                inv.header?.invoice_date || "",
                String(inv.totals?.net_total || 0),
                String(inv.totals?.vat_total || 0),
                String(inv.totals?.gross_total || 0),
                inv.header?.currency || "HUF",
                inv.validation?.is_valid ? "valid" : "invalid",
              ])}
            />
            <button onClick={handleSelectUnprocessed} className="px-3 py-1.5 rounded-md text-xs border border-border text-muted-foreground hover:bg-muted">
              {t("invoice.selectUnprocessed")}
            </button>
            <button
              disabled={checkedIds.size === 0 || batchState.status === "running"}
              onClick={() => startBatch()}
              className="px-3 py-1.5 rounded-md text-xs font-medium bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-40"
            >
              {t("invoice.batchProcess")} ({checkedIds.size})
            </button>
            <button onClick={() => setScheduleOpen(true)} className="px-2 py-1.5 rounded-md text-xs border border-border hover:bg-muted" title={t("invoice.schedule")}>
              &#9200;
            </button>
            <button
              onClick={async () => {
                if (!confirm(t("invoice.resetConfirm"))) return;
                await fetch("/api/documents/reset", { method: "POST" });
                loadData();
              }}
              className="px-2 py-1.5 rounded-md text-xs border border-red-200 text-red-600 hover:bg-red-50"
              title={t("invoice.resetAll")}
            >
              Reset
            </button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-0">
          <DocumentTable
            invoices={filtered}
            docStatuses={docStatuses}
            checkedIds={checkedIds}
            onToggleCheck={handleToggleCheck}
            onToggleAll={handleToggleAll}
            onOpenReview={handleOpenReview}
            sortField={sortField}
            onSortChange={setSortField}
            page={page}
            pageSize={25}
            onPageChange={setPage}
          />
        </CardContent>
      </Card>

      <ScheduleDialog open={scheduleOpen} onClose={() => setScheduleOpen(false)} />
    </SkillViewerLayout>
  );
}
