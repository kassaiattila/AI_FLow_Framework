import { useRef, useEffect, useCallback } from "react";
import { useTranslate, useLocaleState } from "react-admin";
import {
  Box, Typography, Chip, Stack, IconButton, TextField, Paper, Divider, LinearProgress, Tooltip,
} from "@mui/material";
import CheckIcon from "@mui/icons-material/Check";
import EditIcon from "@mui/icons-material/Edit";
import KeyboardIcon from "@mui/icons-material/Keyboard";
import type { DataPoint, DataPointCategory } from "./types";
import { getConfidenceLevel, CONFIDENCE_MUI_COLOR, STATUS_MUI_COLOR, CATEGORY_ORDER } from "./types";

const CATEGORY_LABELS: Record<DataPointCategory, { hu: string; en: string }> = {
  document_meta: { hu: "Dokumentum", en: "Document" },
  vendor: { hu: "Szallito", en: "Vendor" },
  buyer: { hu: "Vevo", en: "Buyer" },
  header: { hu: "Fejlec", en: "Header" },
  line_item: { hu: "Tetelek", en: "Line Items" },
  totals: { hu: "Osszesites", en: "Totals" },
};

// Confidence-based row styling
const CONFIDENCE_ROW_STYLE: Record<string, { borderLeftColor: string; bgcolor: string }> = {
  low: { borderLeftColor: "error.main", bgcolor: "rgba(239,68,68,0.06)" },
  medium: { borderLeftColor: "warning.main", bgcolor: "transparent" },
  high: { borderLeftColor: "transparent", bgcolor: "transparent" },
};

interface Props {
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
}

export const DataPointEditor = ({
  dataPoints, hoveredPointId, selectedPointId, editingPointId, editBuffer,
  onHoverPoint, onSelectPoint, onStartEdit, onEditChange, onCommitEdit, onCancelEdit, onConfirmPoint,
  onNextPoint, onPrevPoint,
}: Props) => {
  const translate = useTranslate();
  const [locale] = useLocaleState();
  const selectedRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Scroll to selected point
  useEffect(() => {
    if (selectedPointId && selectedRef.current) {
      selectedRef.current.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, [selectedPointId]);

  // Keyboard navigation handler
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    // Don't capture keys when editing
    if (editingPointId) return;

    switch (e.key) {
      case "Tab":
        e.preventDefault();
        if (e.shiftKey) {
          onPrevPoint?.();
        } else {
          onNextPoint?.();
        }
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
  }, [editingPointId, selectedPointId, onNextPoint, onPrevPoint, onConfirmPoint, onStartEdit, onCancelEdit]);

  // Group by category
  const grouped = CATEGORY_ORDER.reduce<Record<string, DataPoint[]>>((acc, cat) => {
    const pts = dataPoints.filter((dp) => dp.category === cat);
    if (pts.length > 0) acc[cat] = pts;
    return acc;
  }, {});

  return (
    <Paper
      ref={containerRef}
      variant="outlined"
      sx={{ overflow: "auto", maxHeight: "100%", outline: "none" }}
      tabIndex={0}
      onKeyDown={handleKeyDown}
    >
      {/* Keyboard hint */}
      <Box sx={{ px: 2, py: 0.5, bgcolor: "action.hover", borderBottom: 1, borderColor: "divider" }}>
        <Stack direction="row" alignItems="center" spacing={0.5}>
          <KeyboardIcon sx={{ fontSize: 14, color: "text.disabled" }} />
          <Typography variant="caption" color="text.disabled">
            Tab/Shift+Tab: {translate("aiflow.verification.kbNav")} · Enter: {translate("aiflow.verification.kbConfirm")} · E: {translate("aiflow.verification.kbEdit")} · Esc: {translate("aiflow.verification.kbCancel")}
          </Typography>
        </Stack>
      </Box>

      {Object.entries(grouped).map(([category, points]) => (
        <Box key={category}>
          <Box sx={{ px: 2, py: 0.75, bgcolor: "action.hover", position: "sticky", top: 0, zIndex: 1 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 600, fontSize: "0.8rem" }}>
              {CATEGORY_LABELS[category as DataPointCategory]?.[locale === "en" ? "en" : "hu"] || category}
            </Typography>
          </Box>

          {points.map((dp) => {
            const isSelected = dp.id === selectedPointId;
            const isHovered = dp.id === hoveredPointId;
            const isEditing = dp.id === editingPointId;
            const level = getConfidenceLevel(dp.confidence);
            const rowStyle = CONFIDENCE_ROW_STYLE[level];

            return (
              <Box
                key={dp.id}
                ref={isSelected ? selectedRef : undefined}
                onMouseEnter={() => onHoverPoint(dp.id)}
                onMouseLeave={() => onHoverPoint(null)}
                onClick={() => onSelectPoint(dp.id)}
                sx={{
                  px: 2, py: 0.5,
                  cursor: "pointer",
                  bgcolor: isSelected ? "rgba(99,102,241,0.12)" : isHovered ? "action.hover" : rowStyle.bgcolor,
                  borderLeft: 3,
                  borderLeftColor: isSelected ? "primary.main" : rowStyle.borderLeftColor,
                  transition: "background-color 0.15s",
                  "&:hover": { bgcolor: isSelected ? "rgba(99,102,241,0.16)" : "action.hover" },
                }}
              >
                <Stack direction="row" alignItems="center" spacing={0.75}>
                  {/* Label */}
                  <Typography variant="body2" sx={{ minWidth: 110, fontWeight: 500, fontSize: "0.78rem" }}>
                    {dp.line_item_index != null ? `#${dp.line_item_index + 1} ` : ""}
                    {locale === "en" ? dp.labelEn : dp.label}
                  </Typography>

                  {/* Value or edit input */}
                  <Box sx={{ flex: 1 }}>
                    {isEditing ? (
                      <TextField
                        size="small"
                        value={editBuffer}
                        onChange={(e) => onEditChange(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") onCommitEdit();
                          if (e.key === "Escape") onCancelEdit();
                          e.stopPropagation(); // prevent container keyboard handler
                        }}
                        onBlur={onCommitEdit}
                        autoFocus
                        fullWidth
                        sx={{ "& .MuiInputBase-input": { fontSize: "0.78rem", py: 0.4 } }}
                      />
                    ) : (
                      <Typography
                        variant="body2"
                        onDoubleClick={() => onStartEdit(dp.id)}
                        sx={{
                          fontSize: "0.78rem",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                          color: dp.current_value ? "text.primary" : "text.disabled",
                        }}
                      >
                        {dp.current_value || "-"}
                      </Typography>
                    )}
                  </Box>

                  {/* Confidence mini progress bar */}
                  <Tooltip title={`${(dp.confidence * 100).toFixed(0)}%`}>
                    <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, minWidth: 70 }}>
                      <LinearProgress
                        variant="determinate"
                        value={dp.confidence * 100}
                        color={CONFIDENCE_MUI_COLOR[level]}
                        sx={{ flex: 1, height: 4, borderRadius: 2 }}
                      />
                      <Typography variant="caption" sx={{ fontSize: "0.65rem", minWidth: 28, textAlign: "right", color: `${CONFIDENCE_MUI_COLOR[level]}.main` }}>
                        {(dp.confidence * 100).toFixed(0)}%
                      </Typography>
                    </Box>
                  </Tooltip>

                  {/* Status badge */}
                  <Chip
                    label={dp.status === "auto" ? "Auto" : dp.status === "corrected" ? translate("aiflow.verification.corrected") : "OK"}
                    color={STATUS_MUI_COLOR[dp.status]}
                    size="small"
                    sx={{ fontSize: "0.6rem", height: 18, minWidth: 28 }}
                  />

                  {/* Action buttons */}
                  {!isEditing && (
                    <Stack direction="row" spacing={0}>
                      <IconButton size="small" onClick={(e) => { e.stopPropagation(); onStartEdit(dp.id); }} sx={{ p: 0.25 }}>
                        <EditIcon sx={{ fontSize: 14 }} />
                      </IconButton>
                      {dp.status !== "confirmed" && (
                        <IconButton size="small" color="success" onClick={(e) => { e.stopPropagation(); onConfirmPoint(dp.id); }} sx={{ p: 0.25 }}>
                          <CheckIcon sx={{ fontSize: 14 }} />
                        </IconButton>
                      )}
                    </Stack>
                  )}
                </Stack>
              </Box>
            );
          })}
          <Divider />
        </Box>
      ))}
    </Paper>
  );
};
