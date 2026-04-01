import { useState, useEffect } from "react";
import {
  Box, Paper, ToggleButtonGroup, ToggleButton, Stack, Slider, Tooltip, Typography,
} from "@mui/material";
import LayersIcon from "@mui/icons-material/Layers";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import VisibilityOffIcon from "@mui/icons-material/VisibilityOff";
import PhotoIcon from "@mui/icons-material/Photo";
import GridOnIcon from "@mui/icons-material/GridOn";
import ZoomInIcon from "@mui/icons-material/ZoomIn";
import { useTranslate } from "react-admin";
import type { DataPoint } from "./types";
import { getConfidenceLevel } from "./types";
import { PAGE } from "./document-layout";
import { MockDocumentSvg } from "./MockDocumentSvg";

const CONFIDENCE_FILL: Record<string, string> = {
  high: "rgba(16,185,129,0.15)",
  medium: "rgba(245,158,11,0.15)",
  low: "rgba(239,68,68,0.2)",
};
const CONFIDENCE_FILL_HIGHLIGHT: Record<string, string> = {
  high: "rgba(16,185,129,0.3)",
  medium: "rgba(245,158,11,0.3)",
  low: "rgba(239,68,68,0.35)",
};
const CONFIDENCE_STROKE: Record<string, string> = {
  high: "rgb(16,185,129)",
  medium: "rgb(245,158,11)",
  low: "rgb(239,68,68)",
};

type OverlayMode = "all" | "low" | "off";
type ImageMode = "loading" | "real" | "mock";
type ViewMode = "real" | "mock";

interface Props {
  invoice: Record<string, unknown>;
  dataPoints: DataPoint[];
  hoveredPointId: string | null;
  selectedPointId: string | null;
  onHoverPoint: (id: string | null) => void;
  onSelectPoint: (id: string) => void;
}

export const DocumentCanvas = ({
  invoice, dataPoints, hoveredPointId, selectedPointId, onHoverPoint, onSelectPoint,
}: Props) => {
  const translate = useTranslate();
  const [overlayMode, setOverlayMode] = useState<OverlayMode>("all");
  const [zoom, setZoom] = useState(100);
  const [imageMode, setImageMode] = useState<ImageMode>("loading");
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>("mock");
  const hasRealImage = imageMode === "real" && !!imageUrl;

  const sourceFile = (invoice.source_file as string) || "";
  const baseName = sourceFile.replace(/\.[^.]+$/, "");

  // Try to load the real rendered PNG image from FastAPI
  useEffect(() => {
    if (!sourceFile) { setImageMode("mock"); return; }

    const imgPath = `/api/v1/documents/images/${encodeURIComponent(sourceFile)}/page_1.png`;
    const img = new Image();
    img.onload = () => { setImageUrl(imgPath); setImageMode("real"); setViewMode("real"); };
    img.onerror = () => { setImageMode("mock"); setViewMode("mock"); };
    img.src = imgPath;
  }, [sourceFile]);

  const filteredPoints = dataPoints.filter((dp) => {
    if (!dp.bounding_box) return false;
    if (overlayMode === "off") return false;
    if (overlayMode === "low") return dp.confidence < 0.9;
    return true;
  });

  const w = PAGE.w * (zoom / 100);
  const h = PAGE.h * (zoom / 100);

  return (
    <Paper variant="outlined" sx={{ overflow: "hidden" }}>
      {/* Compact icon toolbar */}
      <Stack direction="row" alignItems="center" sx={{ px: 1, py: 0.5, borderBottom: 1, borderColor: "divider", gap: 0.5 }}>
        {/* Left: Overlay mode icons */}
        <ToggleButtonGroup
          size="small"
          value={overlayMode}
          exclusive
          onChange={(_, v) => v && setOverlayMode(v)}
          sx={{ "& .MuiToggleButton-root": { px: 1, py: 0.5 } }}
        >
          <ToggleButton value="all">
            <Tooltip title={translate("aiflow.verification.overlayAll")}><LayersIcon fontSize="small" /></Tooltip>
          </ToggleButton>
          <ToggleButton value="low">
            <Tooltip title={translate("aiflow.verification.overlayLow")}><WarningAmberIcon fontSize="small" /></Tooltip>
          </ToggleButton>
          <ToggleButton value="off">
            <Tooltip title={translate("aiflow.verification.overlayOff")}><VisibilityOffIcon fontSize="small" /></Tooltip>
          </ToggleButton>
        </ToggleButtonGroup>

        {/* Center: Compact zoom */}
        <Stack direction="row" spacing={0.5} alignItems="center" sx={{ flex: 1, maxWidth: 160, mx: 1 }}>
          <ZoomInIcon fontSize="small" color="action" />
          <Slider
            size="small"
            value={zoom}
            onChange={(_, v) => setZoom(v as number)}
            min={50}
            max={200}
            step={10}
            valueLabelDisplay="auto"
            valueLabelFormat={(v) => `${v}%`}
          />
          <Typography variant="caption" color="text.secondary" sx={{ minWidth: 32 }}>{zoom}%</Typography>
        </Stack>

        {/* Right: Image mode icons */}
        <ToggleButtonGroup
          size="small"
          value={viewMode}
          exclusive
          onChange={(_, v) => v && setViewMode(v)}
          sx={{ "& .MuiToggleButton-root": { px: 1, py: 0.5 } }}
        >
          {hasRealImage && (
            <ToggleButton value="real">
              <Tooltip title={translate("aiflow.verification.realImage")}><PhotoIcon fontSize="small" /></Tooltip>
            </ToggleButton>
          )}
          <ToggleButton value="mock">
            <Tooltip title={translate("aiflow.verification.mockImage")}><GridOnIcon fontSize="small" /></Tooltip>
          </ToggleButton>
        </ToggleButtonGroup>
      </Stack>

      {/* Document area */}
      <Box sx={{ overflow: "auto", maxHeight: "70vh", p: 1 }}>
        <Box sx={{ position: "relative", width: w, height: h, mx: "auto" }}>
          {/* Background: real image or mock SVG */}
          <Box sx={{ position: "absolute", inset: 0 }}>
            {viewMode === "real" && imageUrl ? (
              <img
                src={imageUrl}
                alt={sourceFile}
                style={{ width: w, height: h, objectFit: "contain", display: "block" }}
              />
            ) : (
              <MockDocumentSvg invoice={invoice} width={w} height={h} />
            )}
          </Box>

          {/* Bbox overlays — shown in both views (toggle controls visibility) */}
          {overlayMode !== "off" && (
          <svg
            viewBox={`0 0 ${PAGE.w} ${PAGE.h}`}
            style={{ position: "absolute", inset: 0, width: "100%", height: "100%", pointerEvents: "none" }}
          >
            {filteredPoints.map((dp) => {
              const bb = dp.bounding_box!;
              const level = getConfidenceLevel(dp.confidence);
              const isHighlighted = dp.id === hoveredPointId || dp.id === selectedPointId;
              return (
                <rect
                  key={dp.id}
                  x={bb.x * PAGE.w}
                  y={bb.y * PAGE.h}
                  width={bb.width * PAGE.w}
                  height={bb.height * PAGE.h}
                  fill={isHighlighted ? CONFIDENCE_FILL_HIGHLIGHT[level] : CONFIDENCE_FILL[level]}
                  stroke={CONFIDENCE_STROKE[level]}
                  strokeWidth={isHighlighted ? 2 : 1}
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
        </Box>
      </Box>
    </Paper>
  );
};
