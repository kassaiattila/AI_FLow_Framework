import { useRef, useEffect } from "react";
import { useTranslate, useLocaleState } from "react-admin";
import {
  Box, Typography, Chip, Stack, IconButton, TextField, Paper, Divider,
} from "@mui/material";
import CheckIcon from "@mui/icons-material/Check";
import EditIcon from "@mui/icons-material/Edit";
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
}

export const DataPointEditor = ({
  dataPoints, hoveredPointId, selectedPointId, editingPointId, editBuffer,
  onHoverPoint, onSelectPoint, onStartEdit, onEditChange, onCommitEdit, onCancelEdit, onConfirmPoint,
}: Props) => {
  const translate = useTranslate();
  const [locale] = useLocaleState();
  const selectedRef = useRef<HTMLDivElement>(null);

  // Scroll to selected point
  useEffect(() => {
    if (selectedPointId && selectedRef.current) {
      selectedRef.current.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, [selectedPointId]);

  // Group by category
  const grouped = CATEGORY_ORDER.reduce<Record<string, DataPoint[]>>((acc, cat) => {
    const pts = dataPoints.filter((dp) => dp.category === cat);
    if (pts.length > 0) acc[cat] = pts;
    return acc;
  }, {});

  return (
    <Paper variant="outlined" sx={{ overflow: "auto", maxHeight: "70vh" }}>
      {Object.entries(grouped).map(([category, points]) => (
        <Box key={category}>
          <Box sx={{ px: 2, py: 1, bgcolor: "action.hover", position: "sticky", top: 0, zIndex: 1 }}>
            <Typography variant="subtitle2">
              {CATEGORY_LABELS[category as DataPointCategory]?.[locale === "en" ? "en" : "hu"] || category}
            </Typography>
          </Box>

          {points.map((dp) => {
            const isSelected = dp.id === selectedPointId;
            const isHovered = dp.id === hoveredPointId;
            const isEditing = dp.id === editingPointId;
            const level = getConfidenceLevel(dp.confidence);

            return (
              <Box
                key={dp.id}
                ref={isSelected ? selectedRef : undefined}
                onMouseEnter={() => onHoverPoint(dp.id)}
                onMouseLeave={() => onHoverPoint(null)}
                onClick={() => onSelectPoint(dp.id)}
                sx={{
                  px: 2, py: 0.75,
                  cursor: "pointer",
                  bgcolor: isSelected ? "rgba(99,102,241,0.12)" : isHovered ? "action.hover" : "transparent",
                  borderLeft: 3,
                  borderLeftColor: isSelected ? "primary.main" : "transparent",
                  transition: "background-color 0.15s",
                  "&:hover": { bgcolor: isSelected ? "rgba(99,102,241,0.16)" : "action.hover" },
                }}
              >
                <Stack direction="row" alignItems="center" spacing={1}>
                  {/* Label */}
                  <Typography variant="body2" sx={{ minWidth: 120, fontWeight: 500, fontSize: "0.8rem" }}>
                    {dp.line_item_index != null ? `#${dp.line_item_index + 1} ` : ""}
                    {dp.label}
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
                        }}
                        onBlur={onCommitEdit}
                        autoFocus
                        fullWidth
                        sx={{ "& .MuiInputBase-input": { fontSize: "0.8rem", py: 0.5 } }}
                      />
                    ) : (
                      <Typography
                        variant="body2"
                        onDoubleClick={() => onStartEdit(dp.id)}
                        sx={{
                          fontSize: "0.8rem",
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

                  {/* Confidence badge */}
                  <Chip
                    label={`${(dp.confidence * 100).toFixed(0)}%`}
                    color={CONFIDENCE_MUI_COLOR[level]}
                    size="small"
                    variant="outlined"
                    sx={{ fontSize: "0.65rem", height: 20, minWidth: 40 }}
                  />

                  {/* Status badge */}
                  <Chip
                    label={dp.status === "auto" ? "Auto" : dp.status === "corrected" ? "Jav." : "OK"}
                    color={STATUS_MUI_COLOR[dp.status]}
                    size="small"
                    sx={{ fontSize: "0.65rem", height: 20, minWidth: 32 }}
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
