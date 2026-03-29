"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { ProcessedInvoice } from "@/lib/types";
import { ConfidenceBadge } from "./shared";

interface DocumentDetailProps {
  invoice: ProcessedInvoice;
}

export function DocumentDetail({ invoice }: DocumentDetailProps) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* Left: parties + header */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center justify-between">
            {invoice.source_file}
            <ConfidenceBadge value={invoice.extraction_confidence || invoice.validation.confidence_score} />
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <div className="grid grid-cols-2 gap-4">
            <PartyBlock label="SZALLITO" party={invoice.vendor} />
            <PartyBlock label="VEVO" party={invoice.buyer} />
          </div>

          <div className="grid grid-cols-3 gap-2 pt-2 border-t">
            <Field label="Szamlaszam" value={invoice.header.invoice_number} mono />
            <Field label="Datum" value={invoice.header.invoice_date} mono />
            <Field label="Fiz. hatarido" value={invoice.header.due_date || "\u2014"} mono />
          </div>

          <div className="grid grid-cols-3 gap-2">
            <Field label="Penznem" value={invoice.header.currency} mono bold />
            <Field label="Fizetesi mod" value={invoice.header.payment_method || "\u2014"} />
            <Field label="Parser" value={invoice.parser_used} />
          </div>

          {(invoice.validation.errors.length > 0 || invoice.validation.warnings.length > 0) && (
            <div className="pt-2 border-t space-y-1">
              {invoice.validation.errors.map((e, i) => (
                <p key={i} className="text-xs text-red-600">HIBA: {e}</p>
              ))}
              {invoice.validation.warnings.map((w, i) => (
                <p key={i} className="text-xs text-yellow-600">FIGY: {w}</p>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Right: line items + totals */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Tetelek ({invoice.line_items.length} db)</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-10">#</TableHead>
                <TableHead className="min-w-[180px]">Megnevezes</TableHead>
                <TableHead className="w-20 text-right">Menny.</TableHead>
                <TableHead className="w-24 text-right">Netto</TableHead>
                <TableHead className="w-16 text-right">AFA</TableHead>
                <TableHead className="w-28 text-right">Brutto</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {invoice.line_items.map((item, i) => (
                <TableRow key={i}>
                  <TableCell className="text-xs font-mono">{item.line_number}</TableCell>
                  <TableCell className="text-xs">{item.description}</TableCell>
                  <TableCell className="text-right text-xs font-mono">{item.quantity} {item.unit}</TableCell>
                  <TableCell className="text-right text-xs font-mono">{item.net_amount.toLocaleString("hu-HU")}</TableCell>
                  <TableCell className="text-right text-xs font-mono">{item.vat_rate}%</TableCell>
                  <TableCell className="text-right text-xs font-mono font-semibold">{item.gross_amount.toLocaleString("hu-HU")}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          <div className="mt-3 pt-2 border-t space-y-1">
            <TotalRow label="Netto" value={invoice.totals.net_total} currency={invoice.header.currency} />
            <TotalRow label="AFA" value={invoice.totals.vat_total} currency={invoice.header.currency} />
            <div className="flex justify-between text-sm font-bold pt-1 border-t">
              <span>Brutto</span>
              <span className="font-mono">{invoice.totals.gross_total.toLocaleString("hu-HU")} {invoice.header.currency}</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function PartyBlock({ label, party }: { label: string; party: { name?: string; address?: string; tax_number?: string; bank_account?: string; bank_name?: string } | null | undefined }) {
  if (!party) return <div><p className="text-[10px] font-bold text-muted-foreground uppercase">{label}</p><p className="text-xs text-muted-foreground">Nincs adat</p></div>;
  return (
    <div>
      <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider mb-1">{label}</p>
      <p className="font-medium text-sm">{party.name || "—"}</p>
      {party.address && <p className="text-xs text-muted-foreground">{party.address}</p>}
      {party.tax_number && <p className="text-xs font-mono">{party.tax_number}</p>}
      {party.bank_account && <p className="text-[10px] text-muted-foreground font-mono mt-0.5">{party.bank_account}</p>}
    </div>
  );
}

function Field({ label, value, mono, bold }: { label: string; value: string; mono?: boolean; bold?: boolean }) {
  return (
    <div>
      <p className="text-[10px] text-muted-foreground">{label}</p>
      <p className={`text-xs ${mono ? "font-mono" : ""} ${bold ? "font-semibold" : ""}`}>{value}</p>
    </div>
  );
}

function TotalRow({ label, value, currency }: { label: string; value: number; currency: string }) {
  return (
    <div className="flex justify-between text-xs">
      <span className="text-muted-foreground">{label}:</span>
      <span className="font-mono">{value.toLocaleString("hu-HU")} {currency}</span>
    </div>
  );
}
