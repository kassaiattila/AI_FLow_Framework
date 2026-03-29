"use client";

import { useEffect, useMemo, useCallback, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { useVerificationState } from "@/hooks/use-verification-state";
import { DocumentCanvas } from "./document-canvas";
import { DataPointEditor } from "./data-point-editor";
import { VerificationHeader } from "./verification-header";
import { VerificationActions } from "./verification-actions";
import type { ProcessedInvoice } from "@/lib/types";
import type { InvoiceVerificationData, DataPoint } from "@/lib/verification-types";
import { getAllFields, fieldToBBox, resolvePath, PAGE } from "@/lib/document-layout";

// --- Generate verification data from a real ProcessedInvoice ---

function generateVerificationData(
  invoice: ProcessedInvoice
): InvoiceVerificationData {
  const fields = getAllFields(invoice.line_items.length);

  // Simulate per-field confidence: base from invoice confidence, vary per field
  const baseConf = invoice.extraction_confidence || invoice.validation.confidence_score || 0.9;

  // Deterministic pseudo-variation based on field id
  function fieldConfidence(id: string): number {
    let hash = 0;
    for (let i = 0; i < id.length; i++) hash = (hash * 31 + id.charCodeAt(i)) | 0;
    const variation = ((hash & 0xff) / 255) * 0.2 - 0.1; // -0.1 to +0.1
    return Math.max(0.45, Math.min(0.99, baseConf + variation));
  }

  const dataPoints: DataPoint[] = [];
  for (const f of fields) {
    const value = resolvePath(
      invoice as unknown as Record<string, unknown>,
      f.fieldPath
    );
    if (!value && value !== "0") continue;
    dataPoints.push({
      id: f.id,
      category: f.category,
      field_name: f.fieldPath.split(".").pop() || f.fieldPath,
      label: f.label,
      extracted_value: value,
      current_value: value,
      confidence: fieldConfidence(f.id),
      bounding_box: fieldToBBox(f),
      status: "auto" as const,
      line_item_index: f.lineIndex,
    });
  }

  return {
    invoice_index: 0,
    source_file: invoice.source_file,
    document_meta: {
      document_type: "invoice",
      document_type_confidence: 0.97,
      direction: (invoice.direction as "incoming" | "outgoing") || "incoming",
      direction_confidence: 0.94,
      language: "hu",
      language_confidence: 0.99,
    },
    data_points: dataPoints,
    page_dimensions: { width: PAGE.w, height: PAGE.h },
  };
}

// --- localStorage helpers ---

const STORAGE_PREFIX = "aiflow_verification_";

interface SavedCorrections {
  corrections: Record<string, string>; // id -> corrected value
  confirmed: string[]; // ids that were confirmed
}

function loadCorrections(sourceFile: string): SavedCorrections | null {
  try {
    const raw = localStorage.getItem(STORAGE_PREFIX + sourceFile);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function saveCorrections(sourceFile: string, dataPoints: DataPoint[]) {
  const corrections: Record<string, string> = {};
  const confirmed: string[] = [];
  for (const dp of dataPoints) {
    if (dp.status === "corrected") corrections[dp.id] = dp.current_value;
    if (dp.status === "confirmed") confirmed.push(dp.id);
  }
  const data: SavedCorrections = { corrections, confirmed };
  localStorage.setItem(STORAGE_PREFIX + sourceFile, JSON.stringify(data));
}

// --- Panel ---

interface VerificationPanelProps {
  invoice: ProcessedInvoice;
}

export function VerificationPanel({ invoice }: VerificationPanelProps) {
  const state = useVerificationState();

  // Generate verification data from real invoice
  const verificationData = useMemo(
    () => generateVerificationData(invoice),
    [invoice]
  );

  // Load on mount + restore saved corrections
  useEffect(() => {
    state.loadData(verificationData);

    // Restore saved corrections from localStorage
    const saved = loadCorrections(invoice.source_file);
    if (saved) {
      // Apply corrections via individual edits
      for (const [id, value] of Object.entries(saved.corrections)) {
        state.startEdit(id);
        state.editChange(value);
        state.commitEdit();
      }
      for (const id of saved.confirmed) {
        state.confirmPoint(id);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [invoice.source_file]);

  const [saveStatus, setSaveStatus] = useState<"" | "saving" | "saved" | "error">("");

  const handleSave = useCallback(async () => {
    setSaveStatus("saving");
    // Save to localStorage (offline backup)
    saveCorrections(invoice.source_file, state.dataPoints);

    // Save to backend API
    try {
      const corrections: Record<string, string> = {};
      const confirmed: string[] = [];
      for (const dp of state.dataPoints) {
        if (dp.status === "corrected") corrections[dp.id] = dp.current_value;
        if (dp.status === "confirmed") confirmed.push(dp.id);
      }

      const res = await fetch(`/api/documents/${encodeURIComponent(invoice.source_file)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          verification: { corrections, confirmed, stats: state.stats },
          validation: {
            ...invoice.validation,
            is_valid: state.stats.auto === 0,
            confidence_score: state.dataPoints.reduce((s, dp) => s + dp.confidence, 0) / state.dataPoints.length,
          },
        }),
      });

      if (res.ok) {
        setSaveStatus("saved");
      } else {
        setSaveStatus("error");
      }
    } catch {
      setSaveStatus("error");
    }
    setTimeout(() => setSaveStatus(""), 3000);
  }, [invoice.source_file, invoice.validation, state.dataPoints, state.stats]);

  if (state.dataPoints.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-muted-foreground">
          Dokumentum verifikacios adatok betoltese...
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-3">
      {/* Header */}
      <Card>
        <CardContent className="py-3 px-4">
          <VerificationHeader
            meta={state.documentMeta}
            sourceFile={invoice.source_file}
            stats={state.stats}
          />
        </CardContent>
      </Card>

      {/* Split panel */}
      <div className="grid grid-cols-1 lg:grid-cols-[55fr_45fr] gap-3" style={{ minHeight: "480px" }}>
        <Card className="overflow-hidden">
          <CardContent className="p-2">
            <DocumentCanvas
              invoice={invoice}
              dataPoints={state.dataPoints}
              hoveredPointId={state.hoveredPointId}
              selectedPointId={state.selectedPointId}
              onHoverPoint={state.hoverPoint}
              onSelectPoint={state.selectPoint}
            />
          </CardContent>
        </Card>

        <Card className="overflow-y-auto" style={{ maxHeight: "72vh" }}>
          <DataPointEditor
            dataPoints={state.dataPoints}
            hoveredPointId={state.hoveredPointId}
            selectedPointId={state.selectedPointId}
            editingPointId={state.editingPointId}
            editBuffer={state.editBuffer}
            onHoverPoint={state.hoverPoint}
            onSelectPoint={state.selectPoint}
            onStartEdit={state.startEdit}
            onEditChange={state.editChange}
            onCommitEdit={state.commitEdit}
            onCancelEdit={state.cancelEdit}
            onConfirmPoint={state.confirmPoint}
          />
        </Card>
      </div>

      {/* Actions */}
      <Card>
        <CardContent className="py-3 px-4">
          <VerificationActions
            stats={state.stats}
            onConfirmAll={state.confirmAll}
            onSave={handleSave}
            onReset={state.reset}
            saveStatus={saveStatus}
          />
        </CardContent>
      </Card>
    </div>
  );
}
