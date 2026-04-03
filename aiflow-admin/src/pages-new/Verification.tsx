/**
 * AIFlow Verification — F6.2 Tailwind verification page.
 * Split-screen: PDF canvas (55%) + Data Editor (45%).
 * Replaces legacy MUI VerificationPanel + DocumentCanvas + DataPointEditor.
 */

import { useEffect, useState, useCallback, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useTranslate, useLocale } from "../lib/i18n";
import { fetchApi } from "../lib/api-client";
import { LoadingState } from "../components-new/LoadingState";
import { ErrorState } from "../components-new/ErrorState";
import { StatusBadge } from "../components-new/StatusBadge";
import { useVerificationState } from "../verification/use-verification-state";
import { getAllFields, fieldToBBox, resolvePath, PAGE } from "../verification/document-layout";
import { MockDocumentSvg } from "../verification/MockDocumentSvg";
import type { DataPoint, DataPointCategory, DocumentVerificationData } from "../verification/types";
import { getConfidenceLevel, CATEGORY_ORDER } from "../verification/types";

// --- Tailwind color mappings ---

const CONFIDENCE_COLORS = {
  high: {
    fill: "rgba(16,185,129,0.15)",
    fillHl: "rgba(16,185,129,0.3)",
    stroke: "rgb(16,185,129)",
  },
  medium: {
    fill: "rgba(245,158,11,0.15)",
    fillHl: "rgba(245,158,11,0.3)",
    stroke: "rgb(245,158,11)",
  },
  low: {
    fill: "rgba(239,68,68,0.2)",
    fillHl: "rgba(239,68,68,0.35)",
    stroke: "rgb(239,68,68)",
  },
} as const;

const CATEGORY_LABELS: Record<DataPointCategory, { hu: string; en: string }> = {
  document_meta: { hu: "Dokumentum", en: "Document" },
  vendor: { hu: "Szallito", en: "Vendor" },
  buyer: { hu: "Vevo", en: "Buyer" },
  header: { hu: "Fejlec", en: "Header" },
  line_item: { hu: "Tetelek", en: "Line Items" },
  totals: { hu: "Osszesites", en: "Totals" },
};

// --- Data generation ---

function generateVerificationData(
  invoice: Record<string, unknown>,
  index: number,
): DocumentVerificationData {
  const lineItems = (invoice.line_items as unknown[]) || [];
  const fields = getAllFields(lineItems.length);
  const dataPoints: DataPoint[] = fields.map((f) => {
    const value = resolvePath(invoice, f.fieldPath);
    const confidence = (invoice.extraction_confidence as number) || 0.8;
    return {
      id: f.id,
      category: f.category as DataPointCategory,
      field_name: f.fieldPath,
      label: f.label,
      labelEn: f.labelEn,
      extracted_value: value,
      current_value: value,
      confidence,
      bounding_box: fieldToBBox(f),
      status: "auto",
      line_item_index: f.lineIndex,
    };
  });

  return {
    document_index: index,
    source_file: (invoice.source_file as string) || "",
    document_meta: {
      document_type: "invoice",
      document_type_confidence: 0.97,
      direction: (invoice.direction as "incoming" | "outgoing") || "incoming",
      direction_confidence: 0.94,
      language: "hu",
      language_confidence: 0.99,
    },
    data_points: dataPoints,
    page_dimensions: { width: 595, height: 842 },
  };
}

// ============================================================
// Document Canvas — left panel (55%)
// ============================================================

type OverlayMode = "all" | "low" | "off";
type ViewMode = "real" | "mock";

function DocumentCanvas({
  invoice,
  dataPoints,
  hoveredPointId,
  selectedPointId,
  onHoverPoint,
  onSelectPoint,
}: {
  invoice: Record<string, unknown>;
  dataPoints: DataPoint[];
  hoveredPointId: string | null;
  selectedPointId: string | null;
  onHoverPoint: (id: string | null) => void;
  onSelectPoint: (id: string) => void;
}) {
  const translate = useTranslate();
  const [overlayMode, setOverlayMode] = useState<OverlayMode>("all");
  const [zoom, setZoom] = useState(100);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [hasRealImage, setHasRealImage] = useState(false);
  const [viewMode, setViewMode] = useState<ViewMode>("real");

  const sourceFile = (invoice.source_file as string) || "";
  // Extract just the filename (strip directory path with / or \)
  const fileName = sourceFile.split(/[/\\]/).pop() || sourceFile;

  // Try to load the real rendered PNG image from FastAPI (with auth)
  useEffect(() => {
    if (!fileName) return;
    let revoked = false;
    const imgPath = `/api/v1/documents/images/${encodeURIComponent(fileName)}/page_1.png`;

    fetchApi<Response>("GET", imgPath, undefined, { rawResponse: true })
      .then(async (res) => {
        const blob = await (res as unknown as Response).blob();
        if (revoked) return;
        const url = URL.createObjectURL(blob);
        setImageUrl(url);
        setHasRealImage(true);
        setViewMode("real");
      })
      .catch(() => {
        if (revoked) return;
        setHasRealImage(false);
        setViewMode("mock");
      });

    return () => { revoked = true; };
  }, [fileName]);

  const filteredPoints = dataPoints.filter((dp) => {
    if (!dp.bounding_box) return false;
    if (overlayMode === "off") return false;
    if (overlayMode === "low") return dp.confidence < 0.9;
    return true;
  });

  const w = PAGE.w * (zoom / 100);
  const h = PAGE.h * (zoom / 100);

  const overlayModes: { mode: OverlayMode; key: string; icon: React.ReactNode }[] = [
    {
      mode: "all",
      key: "aiflow.verification.overlayAll",
      icon: (
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01" />
        </svg>
      ),
    },
    {
      mode: "low",
      key: "aiflow.verification.overlayLow",
      icon: (
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
      ),
    },
    {
      mode: "off",
      key: "aiflow.verification.overlayOff",
      icon: (
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
        </svg>
      ),
    },
  ];

  return (
    <div className="flex flex-col overflow-hidden rounded-xl border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-900">
      {/* Toolbar */}
      <div className="flex items-center gap-2 border-b border-gray-200 px-3 py-1.5 dark:border-gray-700">
        {/* Overlay mode toggle */}
        <div className="flex rounded-lg border border-gray-200 dark:border-gray-700">
          {overlayModes.map(({ mode, key, icon }) => (
            <button
              key={mode}
              onClick={() => setOverlayMode(mode)}
              title={translate(key)}
              className={`px-2 py-1 text-xs font-medium transition-colors first:rounded-l-md last:rounded-r-md ${
                overlayMode === mode
                  ? "bg-brand-500 text-white"
                  : "text-gray-500 hover:bg-gray-50 dark:text-gray-400 dark:hover:bg-gray-800"
              }`}
            >
              {icon}
            </button>
          ))}
        </div>

        {/* Zoom slider */}
        <div className="flex flex-1 items-center gap-2 px-2">
          <svg className="h-4 w-4 shrink-0 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v3m0 0v3m0-3h3m-3 0H7" />
          </svg>
          <input
            type="range"
            min={50}
            max={200}
            step={10}
            value={zoom}
            onChange={(e) => setZoom(Number(e.target.value))}
            className="h-1.5 flex-1 cursor-pointer appearance-none rounded-full bg-gray-200 accent-brand-500 dark:bg-gray-700"
          />
          <span className="min-w-[32px] text-right text-xs text-gray-400">{zoom}%</span>
        </div>

        {/* View mode toggle */}
        <div className="flex rounded-lg border border-gray-200 dark:border-gray-700">
          {hasRealImage && (
            <button
              onClick={() => setViewMode("real")}
              title={translate("aiflow.verification.realImage")}
              className={`rounded-l-md px-2 py-1 text-xs font-medium transition-colors ${
                viewMode === "real"
                  ? "bg-brand-500 text-white"
                  : "text-gray-500 hover:bg-gray-50 dark:text-gray-400 dark:hover:bg-gray-800"
              }`}
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
            </button>
          )}
          <button
            onClick={() => setViewMode("mock")}
            title={translate("aiflow.verification.mockImage")}
            className={`px-2 py-1 text-xs font-medium transition-colors ${hasRealImage ? "rounded-r-md" : "rounded-md"} ${
              viewMode === "mock"
                ? "bg-brand-500 text-white"
                : "text-gray-500 hover:bg-gray-50 dark:text-gray-400 dark:hover:bg-gray-800"
            }`}
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z" />
            </svg>
          </button>
        </div>
      </div>

      {/* Canvas area */}
      <div className="overflow-auto p-2" style={{ maxHeight: "70vh" }}>
        <div className="relative mx-auto" style={{ width: w, height: h }}>
          {/* Background: real image or mock SVG */}
          <div className="absolute inset-0">
            {viewMode === "real" && imageUrl ? (
              <img
                src={imageUrl}
                alt={sourceFile}
                style={{ width: w, height: h, objectFit: "contain" }}
              />
            ) : (
              <MockDocumentSvg invoice={invoice} width={w} height={h} />
            )}
          </div>

          {/* Bounding box overlays */}
          {overlayMode !== "off" && (
            <svg
              viewBox={`0 0 ${PAGE.w} ${PAGE.h}`}
              className="absolute inset-0 h-full w-full"
              style={{ pointerEvents: "none" }}
            >
              {filteredPoints.map((dp) => {
                const bb = dp.bounding_box!;
                const level = getConfidenceLevel(dp.confidence);
                const colors = CONFIDENCE_COLORS[level];
                const isHl = dp.id === hoveredPointId || dp.id === selectedPointId;
                return (
                  <rect
                    key={dp.id}
                    x={bb.x * PAGE.w}
                    y={bb.y * PAGE.h}
                    width={bb.width * PAGE.w}
                    height={bb.height * PAGE.h}
                    fill={isHl ? colors.fillHl : colors.fill}
                    stroke={colors.stroke}
                    strokeWidth={isHl ? 2 : 1}
                    rx={2}
                    style={{ pointerEvents: "all", cursor: "pointer" }}
                    onMouseEnter={() => onHoverPoint(dp.id)}
                    onMouseLeave={() => onHoverPoint(null)}
                    onClick={() => onSelectPoint(dp.id)}
                  />
                );
              })}
            </svg>
          )}
        </div>
      </div>
    </div>
  );
}

// ============================================================
// Data Point Editor — right panel (45%)
// ============================================================

function DataPointEditor({
  dataPoints,
  hoveredPointId,
  selectedPointId,
  editingPointId,
  editBuffer,
  onHoverPoint,
  onSelectPoint,
  onStartEdit,
  onEditChange,
  onCommitEdit,
  onCancelEdit,
  onConfirmPoint,
  onNextPoint,
  onPrevPoint,
}: {
  dataPoints: DataPoint[];
  hoveredPointId: string | null;
  selectedPointId: string | null;
  editingPointId: string | null;
  editBuffer: string;
  onHoverPoint: (id: string | null) => void;
  onSelectPoint: (id: string) => void;
  onStartEdit: (id: string) => void;
  onEditChange: (value: string) => void;
  onCommitEdit: () => void;
  onCancelEdit: () => void;
  onConfirmPoint: (id: string) => void;
  onNextPoint?: () => void;
  onPrevPoint?: () => void;
}) {
  const translate = useTranslate();
  const { locale } = useLocale();
  const selectedRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});

  // Scroll to selected point
  useEffect(() => {
    if (selectedPointId && selectedRef.current) {
      selectedRef.current.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, [selectedPointId]);

  // Keyboard navigation handler
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (editingPointId) return;
      switch (e.key) {
        case "Tab":
          e.preventDefault();
          e.shiftKey ? onPrevPoint?.() : onNextPoint?.();
          break;
        case "Enter":
          if (selectedPointId) {
            e.preventDefault();
            onConfirmPoint(selectedPointId);
          }
          break;
        case "e":
        case "E":
          if (selectedPointId) {
            e.preventDefault();
            onStartEdit(selectedPointId);
          }
          break;
        case "Escape":
          e.preventDefault();
          onCancelEdit();
          break;
      }
    },
    [editingPointId, selectedPointId, onNextPoint, onPrevPoint, onConfirmPoint, onStartEdit, onCancelEdit],
  );

  // Group by category
  const grouped = CATEGORY_ORDER.reduce<Record<string, DataPoint[]>>((acc, cat) => {
    const pts = dataPoints.filter((dp) => dp.category === cat);
    if (pts.length > 0) acc[cat] = pts;
    return acc;
  }, {});

  const toggleSection = (cat: string) => {
    setCollapsed((prev) => ({ ...prev, [cat]: !prev[cat] }));
  };

  return (
    <div
      ref={containerRef}
      className="flex flex-col overflow-auto rounded-xl border border-gray-200 bg-white outline-none dark:border-gray-700 dark:bg-gray-900"
      tabIndex={0}
      onKeyDown={handleKeyDown}
    >
      {/* Keyboard hint */}
      <div className="flex items-center gap-1.5 border-b border-gray-200 bg-gray-50 px-3 py-1 dark:border-gray-700 dark:bg-gray-800/50">
        <svg className="h-3.5 w-3.5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
        </svg>
        <span className="text-[11px] text-gray-400">
          Tab: {translate("aiflow.verification.kbNav")} · Enter: {translate("aiflow.verification.kbConfirm")} · E: {translate("aiflow.verification.kbEdit")} · Esc: {translate("aiflow.verification.kbCancel")}
        </span>
      </div>

      {/* Grouped data points */}
      {Object.entries(grouped).map(([category, points]) => {
        const isCollapsed = collapsed[category];
        const catLabel = CATEGORY_LABELS[category as DataPointCategory];

        return (
          <div key={category}>
            {/* Section header — collapsible */}
            <button
              onClick={() => toggleSection(category)}
              className="flex w-full items-center justify-between bg-gray-50 px-3 py-1.5 text-left dark:bg-gray-800/50"
            >
              <span className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
                {locale === "en" ? catLabel.en : catLabel.hu}
              </span>
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-gray-400">{points.length}</span>
                <svg
                  className={`h-3.5 w-3.5 text-gray-400 transition-transform ${isCollapsed ? "" : "rotate-180"}`}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                </svg>
              </div>
            </button>

            {/* Data points rows */}
            {!isCollapsed &&
              points.map((dp) => {
                const isSelected = dp.id === selectedPointId;
                const isHovered = dp.id === hoveredPointId;
                const isEditing = dp.id === editingPointId;
                const level = getConfidenceLevel(dp.confidence);

                // Static Tailwind classes for confidence-based styling
                const borderClass = isSelected
                  ? "border-l-brand-500"
                  : level === "low"
                    ? "border-l-red-500"
                    : level === "medium"
                      ? "border-l-amber-500"
                      : "border-l-transparent";

                const bgClass = isSelected
                  ? "bg-brand-50/50 dark:bg-brand-900/20"
                  : isHovered
                    ? "bg-gray-50 dark:bg-gray-800/30"
                    : level === "low"
                      ? "bg-red-50/30 dark:bg-red-900/10"
                      : "";

                const confBarClass =
                  level === "high"
                    ? "bg-green-500"
                    : level === "medium"
                      ? "bg-amber-500"
                      : "bg-red-500";

                const confTextClass =
                  level === "high"
                    ? "text-green-600 dark:text-green-400"
                    : level === "medium"
                      ? "text-amber-600 dark:text-amber-400"
                      : "text-red-600 dark:text-red-400";

                const statusClasses =
                  dp.status === "confirmed"
                    ? "bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                    : dp.status === "corrected"
                      ? "bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
                      : "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400";

                const statusLabel =
                  dp.status === "corrected"
                    ? translate("aiflow.verification.corrected")
                    : dp.status === "confirmed"
                      ? "OK"
                      : "Auto";

                return (
                  <div
                    key={dp.id}
                    ref={isSelected ? selectedRef : undefined}
                    onMouseEnter={() => onHoverPoint(dp.id)}
                    onMouseLeave={() => onHoverPoint(null)}
                    onClick={() => onSelectPoint(dp.id)}
                    className={`flex cursor-pointer items-center gap-2 border-l-[3px] px-3 py-1.5 transition-colors hover:bg-gray-50 dark:hover:bg-gray-800/30 ${borderClass} ${bgClass}`}
                  >
                    {/* Label */}
                    <span className="min-w-[100px] text-xs font-medium text-gray-700 dark:text-gray-300">
                      {dp.line_item_index != null ? `#${dp.line_item_index + 1} ` : ""}
                      {locale === "en" ? dp.labelEn : dp.label}
                    </span>

                    {/* Value or edit input */}
                    <div className="flex-1">
                      {isEditing ? (
                        <input
                          type="text"
                          value={editBuffer}
                          onChange={(e) => onEditChange(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") onCommitEdit();
                            if (e.key === "Escape") onCancelEdit();
                            e.stopPropagation();
                          }}
                          onBlur={onCommitEdit}
                          autoFocus
                          className="w-full rounded border border-brand-300 bg-white px-2 py-0.5 text-xs text-gray-900 outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
                        />
                      ) : (
                        <span
                          onDoubleClick={() => onStartEdit(dp.id)}
                          className={`block truncate text-xs ${dp.current_value ? "text-gray-900 dark:text-gray-100" : "text-gray-400"}`}
                        >
                          {dp.current_value || "\u2014"}
                        </span>
                      )}
                    </div>

                    {/* Confidence bar */}
                    <div
                      className="flex min-w-[60px] items-center gap-1"
                      title={`${(dp.confidence * 100).toFixed(0)}%`}
                    >
                      <div className="h-1 flex-1 rounded-full bg-gray-200 dark:bg-gray-700">
                        <div
                          className={`h-1 rounded-full ${confBarClass}`}
                          style={{ width: `${dp.confidence * 100}%` }}
                        />
                      </div>
                      <span className={`text-[10px] font-medium ${confTextClass}`}>
                        {(dp.confidence * 100).toFixed(0)}%
                      </span>
                    </div>

                    {/* Status badge */}
                    <span
                      className={`inline-flex rounded-full px-1.5 py-0.5 text-[10px] font-medium ${statusClasses}`}
                    >
                      {statusLabel}
                    </span>

                    {/* Action buttons */}
                    {!isEditing && (
                      <div className="flex gap-0.5">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onStartEdit(dp.id);
                          }}
                          className="rounded p-0.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-800 dark:hover:text-gray-300"
                          title={translate("aiflow.common.edit")}
                        >
                          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                          </svg>
                        </button>
                        {dp.status !== "confirmed" && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              onConfirmPoint(dp.id);
                            }}
                            className="rounded p-0.5 text-green-500 hover:bg-green-50 hover:text-green-700 dark:hover:bg-green-900/20"
                          >
                            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                            </svg>
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}

            {/* Section divider */}
            <div className="border-b border-gray-100 dark:border-gray-800" />
          </div>
        );
      })}
    </div>
  );
}

// ============================================================
// Main Verification Page
// ============================================================

interface DocumentResponse {
  id?: string;
  source_file?: string;
  direction?: string;
  extraction_confidence?: number;
  source?: string;
  [key: string]: unknown;
}

interface DocumentListResponse {
  documents: DocumentResponse[];
  source?: string;
}

export function Verification() {
  const translate = useTranslate();
  const navigate = useNavigate();
  const { id: rawId } = useParams<{ id: string }>();
  const id = rawId ? decodeURIComponent(rawId) : null;

  const [invoice, setInvoice] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<"idle" | "saved" | "error">("idle");
  const [source, setSource] = useState<string | null>(null);
  const [docIds, setDocIds] = useState<string[]>([]);

  const vs = useVerificationState();
  const docListRef = useRef<DocumentResponse[]>([]);

  // Helper: ensure doc list is loaded (cached in ref)
  const ensureDocList = useCallback(async () => {
    if (docListRef.current.length > 0) return docListRef.current;
    const listData = await fetchApi<DocumentListResponse>("GET", `/api/v1/documents?limit=500`);
    const allDocs = listData.documents || [];
    docListRef.current = allDocs;
    setDocIds(allDocs.filter((d) => d.id).map((d) => d.id!));
    setSource(listData.source ?? "backend");
    return allDocs;
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Load current document + ensure list is available
  useEffect(() => {
    if (!id) {
      setLoading(false);
      return;
    }
    setLoading(true);
    const isUuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id);

    const loadDoc = async () => {
      try {
        const allDocs = await ensureDocList();
        let found: DocumentResponse | undefined;
        if (isUuid) {
          found = allDocs.find((d) => d.id === id);
          if (!found) {
            found = await fetchApi<DocumentResponse>("GET", `/api/v1/documents/by-id/${id}`);
          }
        } else {
          found = allDocs.find((d) => d.source_file === id);
        }

        if (found) {
          setInvoice(found as Record<string, unknown>);
          const idx = allDocs.indexOf(found);
          vs.loadData(generateVerificationData(found as Record<string, unknown>, idx >= 0 ? idx : 0));
        }
      } catch { /* not found */ }
      finally { setLoading(false); }
    };
    loadDoc();
  }, [id, ensureDocList]); // eslint-disable-line react-hooks/exhaustive-deps

  // Prev/Next document navigation
  const currentIdx = docIds.indexOf(id ?? "");
  const prevDocId = currentIdx > 0 ? docIds[currentIdx - 1] : null;
  const nextDocId = currentIdx >= 0 && currentIdx < docIds.length - 1 ? docIds[currentIdx + 1] : null;

  const goToDoc = useCallback(
    (docId: string) => navigate(`/documents/${encodeURIComponent(docId)}/verify`),
    [navigate],
  );

  // Save handler — calls real backend verify API
  const handleSave = useCallback(async () => {
    setSaving(true);
    setSaveStatus("idle");
    try {
      const verifiedFields: Record<string, unknown> = {};
      for (const dp of vs.dataPoints) {
        if (dp.status === "corrected" || dp.status === "confirmed") {
          verifiedFields[dp.field_name] = dp.current_value;
        }
      }

      const invoiceId = (invoice as Record<string, unknown>)?.id as string;
      if (invoiceId) {
        await fetchApi("POST", `/api/v1/documents/${invoiceId}/verify`, {
          verified_fields: verifiedFields,
          verified_by: "user",
        });
      }

      // Backup to localStorage
      localStorage.setItem(
        `aiflow_verification_${id}`,
        JSON.stringify({ verified_fields: verifiedFields, confirmed: vs.stats.confirmed }),
      );
      setSaveStatus("saved");
      setTimeout(() => setSaveStatus("idle"), 3000);
    } catch {
      setSaveStatus("error");
    } finally {
      setSaving(false);
    }
  }, [vs.dataPoints, vs.stats.confirmed, id, invoice]);

  // Loading state
  if (loading) return <LoadingState fullPage />;

  // Not found state
  if (!invoice) {
    return (
      <div className="mx-auto max-w-7xl">
        <ErrorState error={`Document not found: ${id}`} />
        <button
          onClick={() => navigate("/documents")}
          className="mt-4 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300"
        >
          {translate("common.action.back")}
        </button>
      </div>
    );
  }

  const progress =
    vs.stats.total > 0 ? ((vs.stats.confirmed + vs.stats.corrected) / vs.stats.total) * 100 : 0;

  return (
    <div className="mx-auto flex h-[calc(100vh-64px)] max-w-[1400px] flex-col px-2 py-2">
      {/* Header — Row 1: back button + title + source badge */}
      <div className="mb-1 flex items-center gap-2">
        <button
          onClick={() => navigate("/documents")}
          className="flex items-center gap-1 rounded-lg px-2 py-1 text-sm text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
          {translate("common.action.back")}
        </button>

        <h1 className="flex-1 truncate text-base font-semibold text-gray-900 dark:text-gray-100">
          {(invoice.source_file as string) || id}
        </h1>

        {/* Document counter + Prev/Next */}
        {docIds.length > 1 && (
          <div className="flex items-center gap-1">
            <span className="mr-1 text-xs text-gray-400">
              {currentIdx + 1} / {docIds.length}
            </span>
            <button
              onClick={() => prevDocId && goToDoc(prevDocId)}
              disabled={!prevDocId}
              className="rounded-md border border-gray-300 p-1 text-gray-500 hover:bg-gray-100 disabled:opacity-30 dark:border-gray-600 dark:text-gray-400 dark:hover:bg-gray-800"
              title={translate("common.navigation.previous")}
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
              </svg>
            </button>
            <button
              onClick={() => nextDocId && goToDoc(nextDocId)}
              disabled={!nextDocId}
              className="rounded-md border border-gray-300 p-1 text-gray-500 hover:bg-gray-100 disabled:opacity-30 dark:border-gray-600 dark:text-gray-400 dark:hover:bg-gray-800"
              title={translate("common.navigation.next")}
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
              </svg>
            </button>
          </div>
        )}

        {source && <StatusBadge source={source} />}
      </div>

      {/* Header — Row 2: meta chips + stats + progress bar */}
      <div className="mb-2 flex flex-wrap items-center gap-2">
        {vs.documentMeta && (
          <>
            <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600 dark:bg-gray-800 dark:text-gray-400">
              {vs.documentMeta.document_type}
            </span>
            <span className="rounded-full border border-gray-200 px-2 py-0.5 text-xs text-gray-500 dark:border-gray-700 dark:text-gray-400">
              {vs.documentMeta.direction}
            </span>
            <div className="h-4 w-px bg-gray-200 dark:bg-gray-700" />
          </>
        )}

        <span className="rounded-full border border-gray-200 px-2 py-0.5 text-xs text-gray-500 dark:border-gray-700 dark:text-gray-400">
          Auto: {vs.stats.auto}
        </span>
        <span className="rounded-full border border-blue-200 px-2 py-0.5 text-xs text-blue-600 dark:border-blue-800 dark:text-blue-400">
          {translate("aiflow.verification.corrected")}: {vs.stats.corrected}
        </span>
        <span className="rounded-full border border-green-200 px-2 py-0.5 text-xs text-green-600 dark:border-green-800 dark:text-green-400">
          OK: {vs.stats.confirmed}
        </span>

        {/* Progress bar */}
        <div className="ml-2 flex flex-1 items-center gap-2">
          <div className="h-1.5 flex-1 rounded-full bg-gray-200 dark:bg-gray-700">
            <div
              className="h-1.5 rounded-full bg-brand-500 transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
          <span className="whitespace-nowrap text-xs text-gray-400">
            {Math.round(progress)}% {translate("aiflow.verification.verified")}
          </span>
        </div>
      </div>

      {/* Split layout — fills remaining height */}
      <div className="grid min-h-0 flex-1 grid-cols-1 gap-3 overflow-hidden md:grid-cols-[55%_45%]">
        <DocumentCanvas
          invoice={invoice}
          dataPoints={vs.dataPoints}
          hoveredPointId={vs.hoveredPointId}
          selectedPointId={vs.selectedPointId}
          onHoverPoint={vs.hoverPoint}
          onSelectPoint={vs.selectPoint}
        />
        <DataPointEditor
          dataPoints={vs.dataPoints}
          hoveredPointId={vs.hoveredPointId}
          selectedPointId={vs.selectedPointId}
          editingPointId={vs.editingPointId}
          editBuffer={vs.editBuffer}
          onHoverPoint={vs.hoverPoint}
          onSelectPoint={vs.selectPoint}
          onStartEdit={vs.startEdit}
          onEditChange={vs.editChange}
          onCommitEdit={vs.commitEdit}
          onCancelEdit={vs.cancelEdit}
          onConfirmPoint={vs.confirmPoint}
          onNextPoint={vs.nextPoint}
          onPrevPoint={vs.prevPoint}
        />
      </div>

      {/* Sticky action bar */}
      <div className="mt-2 flex items-center justify-between rounded-xl border border-gray-200 bg-white px-4 py-2 dark:border-gray-700 dark:bg-gray-900">
        {/* Left side: save status + counter */}
        <div className="flex items-center gap-2">
          {saveStatus === "saved" && (
            <span className="rounded-full bg-green-50 px-2 py-0.5 text-xs font-medium text-green-700 dark:bg-green-900/30 dark:text-green-400">
              {translate("aiflow.verification.saved")}
            </span>
          )}
          {saveStatus === "error" && (
            <span className="rounded-full bg-red-50 px-2 py-0.5 text-xs font-medium text-red-700 dark:bg-red-900/30 dark:text-red-400">
              {translate("aiflow.common.error")}
            </span>
          )}
          <span className="whitespace-nowrap text-xs text-gray-400">
            {vs.stats.confirmed + vs.stats.corrected}/{vs.stats.total}{" "}
            {translate("aiflow.verification.verified")}
          </span>
        </div>

        {/* Right side: action buttons */}
        <div className="flex items-center gap-2">
          {/* Reset */}
          <button
            onClick={vs.reset}
            className="flex items-center gap-1 rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-400 dark:hover:bg-gray-800"
          >
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Reset
          </button>

          {/* Confirm All */}
          <button
            onClick={vs.confirmAll}
            className="flex items-center gap-1 rounded-lg border border-green-300 px-3 py-1.5 text-xs font-medium text-green-700 hover:bg-green-50 dark:border-green-700 dark:text-green-400 dark:hover:bg-green-900/20"
          >
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
            {translate("aiflow.verification.confirmAll")}
          </button>

          {/* Save */}
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-1 rounded-lg bg-brand-500 px-4 py-1.5 text-xs font-semibold text-white hover:bg-brand-600 disabled:opacity-50"
          >
            {saving ? (
              <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/30 border-t-white" />
            ) : (
              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4" />
              </svg>
            )}
            {translate("aiflow.common.save")}
          </button>
        </div>
      </div>
    </div>
  );
}
