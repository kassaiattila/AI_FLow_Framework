"use client";

import { Button } from "@/components/ui/button";
import { toCsv, downloadCsv } from "@/lib/csv-export";

interface ExportButtonProps {
  filename: string;
  headers: string[];
  rows: string[][];
  label?: string;
}

export function ExportButton({ filename, headers, rows, label = "CSV Export" }: ExportButtonProps) {
  const handleExport = () => {
    const csv = toCsv(headers, rows);
    downloadCsv(filename, csv);
  };

  return (
    <Button variant="outline" size="sm" onClick={handleExport} disabled={rows.length === 0}>
      {label}
    </Button>
  );
}
