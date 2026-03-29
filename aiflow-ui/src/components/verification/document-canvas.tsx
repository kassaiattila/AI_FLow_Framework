"use client";

import { memo, useState, useEffect } from "react";
import type { DataPoint } from "@/lib/verification-types";
import { getConfidenceColor, CONFIDENCE_STYLES } from "@/lib/verification-types";
import type { ProcessedInvoice } from "@/lib/types";
import { PAGE } from "@/lib/document-layout";
import { MockInvoiceSvg } from "./mock-invoice-svg";

interface OcrBlock {
  page: number;
  text: string;
  bbox: { x: number; y: number; width: number; height: number };
}

interface DocumentCanvasProps {
  invoice: ProcessedInvoice;
  dataPoints: DataPoint[];
  hoveredPointId: string | null;
  selectedPointId: string | null;
  onHoverPoint: (id: string | null) => void;
  onSelectPoint: (id: string) => void;
}

type OverlayMode = "all" | "low" | "off";

export function DocumentCanvas({
  invoice,
  dataPoints,
  hoveredPointId,
  selectedPointId,
  onHoverPoint,
  onSelectPoint,
}: DocumentCanvasProps) {
  const [zoom, setZoom] = useState(100);
  const [pdfImageUrl, setPdfImageUrl] = useState<string | null>(null);
  const [ocrBlocks, setOcrBlocks] = useState<OcrBlock[]>([]);
  const [overlayMode, setOverlayMode] = useState<OverlayMode>("all");

  const docBasePath = `/images/documents/${invoice.source_file.replace(/\.pdf$/i, "")}`;

  // Check if a real PDF page image exists
  useEffect(() => {
    const imgPath = `${docBasePath}/page_1.png`;
    const img = new Image();
    img.onload = () => setPdfImageUrl(imgPath);
    img.onerror = () => setPdfImageUrl(null);
    img.src = `${imgPath}?t=${Date.now()}`;
  }, [docBasePath]);

  // Load OCR bounding boxes if they exist
  useEffect(() => {
    fetch(`${docBasePath}/bboxes.json?t=${Date.now()}`)
      .then((r) => { if (!r.ok) throw new Error("no bboxes"); return r.json(); })
      .then((data: { blocks: OcrBlock[] }) => setOcrBlocks(data.blocks || []))
      .catch(() => setOcrBlocks([]));
  }, [docBasePath]);

  const hasRealImage = !!pdfImageUrl;
  const hasOcrBoxes = ocrBlocks.length > 0;

  // For real PDF: match OCR blocks to data points by text similarity
  const matchedBlocks = hasRealImage && hasOcrBoxes
    ? matchOcrToDataPoints(ocrBlocks, dataPoints)
    : [];

  // For mock SVG: use layout-computed bboxes
  const mockPoints = !hasRealImage ? dataPoints : [];

  const visibleMock = overlayMode === "off" ? [] : overlayMode === "low" ? mockPoints.filter((dp) => dp.confidence < 0.9) : mockPoints;
  const visibleReal = overlayMode === "off" ? [] : overlayMode === "low" ? matchedBlocks.filter((b) => b.confidence < 0.9) : matchedBlocks;

  const lowConfCount = dataPoints.filter((dp) => dp.confidence < 0.9).length;

  return (
    <div className="space-y-2">
      {/* Controls */}
      <div className="flex items-center justify-between px-1 gap-2">
        <div className="flex items-center gap-2">
          {hasRealImage ? (
            <span className="text-[10px] text-green-700 bg-green-50 border border-green-200 rounded px-1.5 py-0.5">
              Eredeti dokumentum {hasOcrBoxes && `· ${ocrBlocks.length} OCR blokk`}
            </span>
          ) : (
            <span className="text-[10px] text-muted-foreground bg-yellow-50 border border-yellow-200 rounded px-1.5 py-0.5">
              Szimulalt nezet
            </span>
          )}

          {/* Overlay toggle */}
          <div className="flex rounded-md border border-border overflow-hidden">
            {([
              { v: "all" as const, l: "Osszes" },
              { v: "low" as const, l: `Alacsony (${lowConfCount})` },
              { v: "off" as const, l: "Ki" },
            ]).map(({ v, l }) => (
              <button
                key={v}
                onClick={() => setOverlayMode(v)}
                className={`px-1.5 py-0.5 text-[9px] transition-colors ${overlayMode === v ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted"}`}
              >
                {l}
              </button>
            ))}
          </div>
        </div>

        {/* Zoom */}
        <div className="flex items-center gap-1">
          <button onClick={() => setZoom((z) => Math.max(50, z - 25))} className="size-6 rounded border border-border text-xs flex items-center justify-center hover:bg-muted">&minus;</button>
          <span className="text-[10px] font-mono w-10 text-center">{zoom}%</span>
          <button onClick={() => setZoom((z) => Math.min(200, z + 25))} className="size-6 rounded border border-border text-xs flex items-center justify-center hover:bg-muted">+</button>
          <button onClick={() => setZoom(100)} className="px-1.5 py-0.5 rounded border border-border text-[10px] hover:bg-muted ml-1">Reset</button>
        </div>
      </div>

      {/* Canvas */}
      <div className="overflow-auto rounded-md border border-border bg-gray-50" style={{ maxHeight: "65vh" }}>
        <div className="relative origin-top-left" style={{ width: `${zoom}%`, aspectRatio: `${PAGE.w} / ${PAGE.h}` }}>
          {/* Background */}
          <div className="absolute inset-0">
            {hasRealImage ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={pdfImageUrl} alt="Document" className="w-full h-full object-contain" />
            ) : (
              <MockInvoiceSvg invoice={invoice} />
            )}
          </div>

          {/* Overlay: mock SVG bounding boxes */}
          {!hasRealImage && visibleMock.length > 0 && (
            <svg className="absolute inset-0 w-full h-full" viewBox={`0 0 ${PAGE.w} ${PAGE.h}`} style={{ pointerEvents: "none" }}>
              {visibleMock.map((dp) => {
                if (!dp.bounding_box) return null;
                const bb = dp.bounding_box;
                const active = hoveredPointId === dp.id || selectedPointId === dp.id;
                const color = getConfidenceColor(dp.confidence);
                const styles = CONFIDENCE_STYLES[color];
                const thick = dp.confidence < 0.9 ? 2 : 1;
                return (
                  <BBoxRect key={dp.id}
                    x={bb.x * PAGE.w} y={bb.y * PAGE.h} width={bb.width * PAGE.w} height={bb.height * PAGE.h}
                    fill={active ? styles.fillHover : styles.fill} stroke={active ? styles.strokeHover : styles.stroke}
                    strokeWidth={active ? thick + 1 : thick}
                    label={`${dp.label}: ${dp.current_value} (${Math.round(dp.confidence * 100)}%)`}
                    onMouseEnter={() => onHoverPoint(dp.id)} onMouseLeave={() => onHoverPoint(null)} onClick={() => onSelectPoint(dp.id)}
                  />
                );
              })}
            </svg>
          )}

          {/* Overlay: REAL OCR bounding boxes on PDF image */}
          {hasRealImage && visibleReal.length > 0 && (
            <div className="absolute inset-0" style={{ pointerEvents: "none" }}>
              {visibleReal.map((block, idx) => {
                const active = hoveredPointId === block.matchedId || selectedPointId === block.matchedId;
                const color = getConfidenceColor(block.confidence);
                const styles = CONFIDENCE_STYLES[color];
                const thick = block.confidence < 0.9;

                return (
                  <div
                    key={idx}
                    className="absolute transition-all"
                    style={{
                      left: `${block.bbox.x * 100}%`,
                      top: `${block.bbox.y * 100}%`,
                      width: `${block.bbox.width * 100}%`,
                      height: `${block.bbox.height * 100}%`,
                      backgroundColor: active ? styles.fillHover : styles.fill,
                      border: `${active ? (thick ? 3 : 2) : (thick ? 2 : 1)}px solid ${active ? styles.strokeHover : styles.stroke}`,
                      borderRadius: "2px",
                      pointerEvents: "auto",
                      cursor: "pointer",
                    }}
                    title={`${block.label}: ${block.text.slice(0, 60)} (${Math.round(block.confidence * 100)}%)`}
                    onMouseEnter={() => block.matchedId && onHoverPoint(block.matchedId)}
                    onMouseLeave={() => onHoverPoint(null)}
                    onClick={() => block.matchedId && onSelectPoint(block.matchedId)}
                  />
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Legend */}
      {overlayMode !== "off" && (
        <div className="flex items-center gap-3 px-1 text-[9px] text-muted-foreground">
          <span className="flex items-center gap-1"><span className="w-3 h-2 rounded-sm bg-green-500/30 border border-green-500" /> 90%+</span>
          <span className="flex items-center gap-1"><span className="w-3 h-2 rounded-sm bg-yellow-500/30 border border-yellow-500" /> 70-90%</span>
          <span className="flex items-center gap-1"><span className="w-3 h-2 rounded-sm bg-red-500/30 border-2 border-red-500" /> &lt;70%</span>
          <span className="text-muted-foreground/50">|</span>
          <span>{hasRealImage ? "OCR blokkok az eredeti dokumentumon" : "Kattints egy keretbe a mezo kivalasztasahoz"}</span>
        </div>
      )}
    </div>
  );
}

// --- Match OCR blocks to extracted data points by text similarity ---

interface MatchedBlock {
  bbox: { x: number; y: number; width: number; height: number };
  text: string;
  label: string;
  confidence: number;
  matchedId: string | null;
}

function matchOcrToDataPoints(blocks: OcrBlock[], dataPoints: DataPoint[]): MatchedBlock[] {
  const results: MatchedBlock[] = [];

  for (const block of blocks) {
    const blockText = block.text.toLowerCase();

    // Find data points whose extracted_value appears in this OCR block
    let bestMatch: DataPoint | null = null;
    let bestScore = 0;

    for (const dp of dataPoints) {
      const val = dp.current_value.toLowerCase();
      if (val.length < 2) continue;

      if (blockText.includes(val)) {
        const score = val.length / blockText.length;
        if (score > bestScore) {
          bestScore = score;
          bestMatch = dp;
        }
      }
    }

    // If matched, assign the data point's confidence; otherwise use a default
    results.push({
      bbox: block.bbox,
      text: block.text,
      label: bestMatch?.label || "OCR blokk",
      confidence: bestMatch?.confidence || 0.85,
      matchedId: bestMatch?.id || null,
    });
  }

  return results;
}

// --- BBox rect (memo for SVG overlay) ---

interface BBoxRectProps {
  x: number; y: number; width: number; height: number;
  fill: string; stroke: string; strokeWidth: number; label: string;
  onMouseEnter: () => void; onMouseLeave: () => void; onClick: () => void;
}

const BBoxRect = memo(function BBoxRect({ x, y, width, height, fill, stroke, strokeWidth, label, onMouseEnter, onMouseLeave, onClick }: BBoxRectProps) {
  return (
    <rect x={x} y={y} width={width} height={height} fill={fill} stroke={stroke} strokeWidth={strokeWidth} rx={2}
      style={{ pointerEvents: "auto", cursor: "pointer", transition: "all 0.15s ease" }}
      onMouseEnter={onMouseEnter} onMouseLeave={onMouseLeave} onClick={onClick}>
      <title>{label}</title>
    </rect>
  );
});
