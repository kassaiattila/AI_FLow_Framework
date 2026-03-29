"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import type { ProcessedInvoice } from "@/lib/types";

export default function InvoiceViewerPage() {
  const [invoices, setInvoices] = useState<ProcessedInvoice[]>([]);
  const [selected, setSelected] = useState<ProcessedInvoice | null>(null);

  useEffect(() => {
    fetch("/data/invoices.json")
      .then((r) => r.json())
      .then((data) => setInvoices(data))
      .catch(() => setInvoices([]));
  }, []);

  const totalGrossHUF = invoices
    .filter((i) => i.header.currency === "HUF")
    .reduce((sum, i) => sum + i.totals.gross_total, 0);
  const totalGrossUSD = invoices
    .filter((i) => i.header.currency === "USD")
    .reduce((sum, i) => sum + i.totals.gross_total, 0);
  const totalGrossEUR = invoices
    .filter((i) => i.header.currency === "EUR")
    .reduce((sum, i) => sum + i.totals.gross_total, 0);

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Invoice Processor</h2>
          <p className="text-muted-foreground">
            {invoices.length} szamla feldolgozva
          </p>
        </div>
        <Badge className="bg-blue-100 text-blue-800 hover:bg-blue-100 text-sm px-3 py-1">
          70% complete
        </Badge>
      </div>

      {/* KPI */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">Szamlak</p>
            <p className="text-3xl font-bold">{invoices.length}</p>
            <p className="text-xs text-muted-foreground">
              {invoices.filter((i) => i.validation.is_valid).length} valid
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">HUF osszesen</p>
            <p className="text-3xl font-bold">
              {totalGrossHUF.toLocaleString("hu-HU")}
            </p>
            <p className="text-xs text-muted-foreground">Ft</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">EUR osszesen</p>
            <p className="text-3xl font-bold">
              {totalGrossEUR.toLocaleString("hu-HU", { minimumFractionDigits: 2 })}
            </p>
            <p className="text-xs text-muted-foreground">EUR</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">USD osszesen</p>
            <p className="text-3xl font-bold">
              {totalGrossUSD.toLocaleString("hu-HU", { minimumFractionDigits: 2 })}
            </p>
            <p className="text-xs text-muted-foreground">USD</p>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="list">
        <TabsList>
          <TabsTrigger value="list">Szamla lista</TabsTrigger>
          <TabsTrigger value="detail">Reszletek</TabsTrigger>
        </TabsList>

        {/* Invoice list */}
        <TabsContent value="list">
          <Card>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-8">V</TableHead>
                    <TableHead>Szallito</TableHead>
                    <TableHead>Szamlaszam</TableHead>
                    <TableHead>Datum</TableHead>
                    <TableHead>Vevo</TableHead>
                    <TableHead className="text-right">Brutto</TableHead>
                    <TableHead className="text-right">Conf.</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {invoices.map((inv, idx) => (
                    <TableRow
                      key={idx}
                      className="cursor-pointer hover:bg-muted/50"
                      onClick={() => setSelected(inv)}
                    >
                      <TableCell>
                        {inv.validation.is_valid ? (
                          <span className="text-green-600">&#10003;</span>
                        ) : (
                          <span className="text-red-600">!</span>
                        )}
                      </TableCell>
                      <TableCell className="font-medium text-sm">
                        {inv.vendor.name}
                      </TableCell>
                      <TableCell className="text-sm">
                        {inv.header.invoice_number}
                      </TableCell>
                      <TableCell className="text-sm">
                        {inv.header.invoice_date}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {inv.buyer.name}
                        {inv.buyer.tax_number && (
                          <span className="ml-1 text-xs">
                            ({inv.buyer.tax_number})
                          </span>
                        )}
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm">
                        {inv.totals.gross_total.toLocaleString("hu-HU")}{" "}
                        {inv.header.currency}
                      </TableCell>
                      <TableCell className="text-right">
                        <ConfidenceBadge value={inv.extraction_confidence || inv.validation.confidence_score} />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Invoice detail */}
        <TabsContent value="detail">
          {selected ? (
            <InvoiceDetail invoice={selected} />
          ) : (
            <Card>
              <CardContent className="py-12 text-center text-muted-foreground">
                Valassz egy szamlat a listabol
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}

function InvoiceDetail({ invoice }: { invoice: ProcessedInvoice }) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* Left: Header data */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center justify-between">
            {invoice.source_file}
            <ConfidenceBadge value={invoice.extraction_confidence || invoice.validation.confidence_score} />
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs font-semibold text-muted-foreground uppercase">Szallito</p>
              <p className="font-medium">{invoice.vendor.name}</p>
              {invoice.vendor.address && <p className="text-sm text-muted-foreground">{invoice.vendor.address}</p>}
              {invoice.vendor.tax_number && <p className="text-sm font-mono">{invoice.vendor.tax_number}</p>}
              {invoice.vendor.bank_account && (
                <p className="text-xs text-muted-foreground mt-1">Bank: {invoice.vendor.bank_account}</p>
              )}
            </div>
            <div>
              <p className="text-xs font-semibold text-muted-foreground uppercase">Vevo</p>
              <p className="font-medium">{invoice.buyer.name}</p>
              {invoice.buyer.address && <p className="text-sm text-muted-foreground">{invoice.buyer.address}</p>}
              {invoice.buyer.tax_number && <p className="text-sm font-mono">{invoice.buyer.tax_number}</p>}
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3 pt-2 border-t">
            <div>
              <p className="text-xs text-muted-foreground">Szamlaszam</p>
              <p className="text-sm font-mono">{invoice.header.invoice_number}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Datum</p>
              <p className="text-sm">{invoice.header.invoice_date}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Fizetesi hatarido</p>
              <p className="text-sm">{invoice.header.due_date || "-"}</p>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <p className="text-xs text-muted-foreground">Penznem</p>
              <p className="text-sm font-semibold">{invoice.header.currency}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Fizetesi mod</p>
              <p className="text-sm">{invoice.header.payment_method || "-"}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Parser</p>
              <p className="text-sm">{invoice.parser_used}</p>
            </div>
          </div>

          {/* Validation */}
          {(invoice.validation.errors.length > 0 || invoice.validation.warnings.length > 0) && (
            <div className="pt-2 border-t space-y-1">
              {invoice.validation.errors.map((e, i) => (
                <p key={i} className="text-sm text-red-600">HIBA: {e}</p>
              ))}
              {invoice.validation.warnings.map((w, i) => (
                <p key={i} className="text-sm text-yellow-600">FIGY: {w}</p>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Right: Line items + totals */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            Tetelek ({invoice.line_items.length} db)
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>#</TableHead>
                <TableHead>Megnevezes</TableHead>
                <TableHead className="text-right">Menny.</TableHead>
                <TableHead className="text-right">Netto</TableHead>
                <TableHead className="text-right">AFA</TableHead>
                <TableHead className="text-right">Brutto</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {invoice.line_items.map((item, i) => (
                <TableRow key={i}>
                  <TableCell className="text-xs">{item.line_number}</TableCell>
                  <TableCell className="text-sm">{item.description}</TableCell>
                  <TableCell className="text-right text-sm">
                    {item.quantity} {item.unit}
                  </TableCell>
                  <TableCell className="text-right font-mono text-sm">
                    {item.net_amount.toLocaleString("hu-HU")}
                  </TableCell>
                  <TableCell className="text-right text-sm">
                    {item.vat_rate}%
                  </TableCell>
                  <TableCell className="text-right font-mono text-sm font-semibold">
                    {item.gross_amount.toLocaleString("hu-HU")}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          {/* Totals */}
          <div className="mt-4 pt-3 border-t space-y-1">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Netto:</span>
              <span className="font-mono">
                {invoice.totals.net_total.toLocaleString("hu-HU")} {invoice.header.currency}
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">AFA:</span>
              <span className="font-mono">
                {invoice.totals.vat_total.toLocaleString("hu-HU")} {invoice.header.currency}
              </span>
            </div>
            <div className="flex justify-between text-base font-bold pt-1 border-t">
              <span>Brutto:</span>
              <span className="font-mono">
                {invoice.totals.gross_total.toLocaleString("hu-HU")} {invoice.header.currency}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function ConfidenceBadge({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color = pct >= 90 ? "bg-green-100 text-green-800" : pct >= 70 ? "bg-yellow-100 text-yellow-800" : "bg-red-100 text-red-800";
  return <Badge className={`${color} hover:${color} text-xs`}>{pct}%</Badge>;
}
