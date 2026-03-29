"use client";

import { useMemo } from "react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import type { ProcessedInvoice } from "@/lib/types";
import { DocStatusIcon, formatCompactAmount, ConfidenceBadge, type DocStatus } from "./shared";

export type SortField = "date" | "vendor" | "confidence" | "amount";

interface DocumentTableProps {
  invoices: ProcessedInvoice[];
  docStatuses: Map<string, DocStatus>;
  checkedIds: Set<string>;
  onToggleCheck: (sf: string) => void;
  onToggleAll: () => void;
  onOpenReview: (inv: ProcessedInvoice) => void;
  sortField: SortField;
  onSortChange: (f: SortField) => void;
  page: number;
  pageSize: number;
  onPageChange: (p: number) => void;
}

export function DocumentTable({
  invoices,
  docStatuses,
  checkedIds,
  onToggleCheck,
  onToggleAll,
  onOpenReview,
  sortField,
  onSortChange,
  page,
  pageSize,
  onPageChange,
}: DocumentTableProps) {
  // Sort
  const sorted = useMemo(() => {
    const arr = [...invoices];
    switch (sortField) {
      case "date": arr.sort((a, b) => b.header.invoice_date.localeCompare(a.header.invoice_date)); break;
      case "vendor": arr.sort((a, b) => a.vendor.name.localeCompare(b.vendor.name)); break;
      case "confidence": arr.sort((a, b) => (a.extraction_confidence || a.validation.confidence_score) - (b.extraction_confidence || b.validation.confidence_score)); break;
      case "amount": arr.sort((a, b) => b.totals.gross_total - a.totals.gross_total); break;
    }
    return arr;
  }, [invoices, sortField]);

  // Paginate
  const totalPages = Math.max(1, Math.ceil(sorted.length / pageSize));
  const paginated = sorted.slice(page * pageSize, (page + 1) * pageSize);

  const pageIds = paginated.map((inv) => inv.source_file);
  const allOnPageChecked = paginated.length > 0 && pageIds.every((id) => checkedIds.has(id));
  const someChecked = pageIds.some((id) => checkedIds.has(id));

  // Per-page toggle: only affect items on current page
  const handleTogglePage = () => {
    if (allOnPageChecked) {
      // Uncheck all on this page
      const next = new Set(checkedIds);
      for (const id of pageIds) next.delete(id);
      // We need to call onToggleCheck for each, or pass a bulk handler
      // For now, toggle each one
      for (const id of pageIds) onToggleCheck(id);
    } else {
      // Check all on this page
      for (const id of pageIds) {
        if (!checkedIds.has(id)) onToggleCheck(id);
      }
    }
  };

  function SortHeader({ field, children }: { field: SortField; children: React.ReactNode }) {
    const active = sortField === field;
    return (
      <button
        onClick={() => onSortChange(field)}
        className={`inline-flex items-center gap-1 text-xs ${active ? "font-bold text-foreground" : "text-muted-foreground hover:text-foreground"}`}
      >
        {children}
        {active && <span className="text-[10px]">▼</span>}
      </button>
    );
  }

  return (
    <div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-10">
              <input
                type="checkbox"
                checked={allOnPageChecked}
                ref={(el) => { if (el) el.indeterminate = someChecked && !allOnPageChecked; }}
                onChange={handleTogglePage}
                className="size-3.5 accent-primary"
              />
            </TableHead>
            <TableHead className="w-10">St.</TableHead>
            <TableHead className="min-w-[160px]"><SortHeader field="vendor">Szallito</SortHeader></TableHead>
            <TableHead className="w-36">Szamlaszam</TableHead>
            <TableHead className="w-24"><SortHeader field="date">Datum</SortHeader></TableHead>
            <TableHead className="w-28 text-right"><SortHeader field="amount">Brutto</SortHeader></TableHead>
            <TableHead className="w-16 text-center"><SortHeader field="confidence">Conf.</SortHeader></TableHead>
            <TableHead className="w-20 text-center">Review</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {paginated.map((inv) => {
            const status = docStatuses.get(inv.source_file) || "completed";
            const conf = inv.extraction_confidence || inv.validation.confidence_score;
            return (
              <TableRow
                key={inv.source_file}
                className="cursor-pointer hover:bg-muted/50"
                onClick={() => onOpenReview(inv)}
              >
                <TableCell onClick={(e) => e.stopPropagation()}>
                  <input
                    type="checkbox"
                    checked={checkedIds.has(inv.source_file)}
                    onChange={() => onToggleCheck(inv.source_file)}
                    className="size-3.5 accent-primary"
                  />
                </TableCell>
                <TableCell><DocStatusIcon status={status} /></TableCell>
                <TableCell className="text-sm font-medium truncate max-w-[200px]">{inv.vendor.name || inv.source_file}</TableCell>
                <TableCell className="text-xs font-mono text-muted-foreground">{inv.header.invoice_number}</TableCell>
                <TableCell className="text-xs font-mono">{inv.header.invoice_date}</TableCell>
                <TableCell className="text-right text-xs font-mono">{formatCompactAmount(inv)}</TableCell>
                <TableCell className="text-center">{conf > 0 ? <ConfidenceBadge value={conf} /> : <span className="text-xs text-muted-foreground">—</span>}</TableCell>
                <TableCell className="text-center" onClick={(e) => e.stopPropagation()}>
                  <button
                    onClick={() => onOpenReview(inv)}
                    className="px-2 py-0.5 rounded text-[10px] font-medium bg-primary/10 text-primary hover:bg-primary/20"
                  >
                    Review
                  </button>
                </TableCell>
              </TableRow>
            );
          })}
          {paginated.length === 0 && (
            <TableRow>
              <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">Nincs talalat</TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between px-4 py-3 border-t">
          <span className="text-xs text-muted-foreground">
            {sorted.length} dokumentum &middot; Oldal {page + 1}/{totalPages}
          </span>
          <div className="flex gap-1">
            <button
              disabled={page === 0}
              onClick={() => onPageChange(page - 1)}
              className="px-2 py-1 rounded text-xs border border-border disabled:opacity-40 hover:bg-muted"
            >
              Elozo
            </button>
            <button
              disabled={page >= totalPages - 1}
              onClick={() => onPageChange(page + 1)}
              className="px-2 py-1 rounded text-xs border border-border disabled:opacity-40 hover:bg-muted"
            >
              Kovetkezo
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
