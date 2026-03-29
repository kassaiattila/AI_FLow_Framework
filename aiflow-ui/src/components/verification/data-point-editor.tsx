"use client";

import { useRef, useEffect } from "react";
import { Badge } from "@/components/ui/badge";
import type { DataPoint, DataPointCategory } from "@/lib/verification-types";
import {
  getConfidenceColor,
  CONFIDENCE_STYLES,
  STATUS_STYLES,
  CATEGORY_LABELS,
  CATEGORY_ORDER,
} from "@/lib/verification-types";

interface DataPointEditorProps {
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

export function DataPointEditor({
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
}: DataPointEditorProps) {
  // Group by category
  const groups = new Map<DataPointCategory, DataPoint[]>();
  for (const dp of dataPoints) {
    const list = groups.get(dp.category) || [];
    list.push(dp);
    groups.set(dp.category, list);
  }

  return (
    <div className="space-y-1 p-3">
      {CATEGORY_ORDER.map((cat) => {
        const points = groups.get(cat);
        if (!points || points.length === 0) return null;
        return (
          <CategorySection key={cat} category={cat} label={CATEGORY_LABELS[cat]}>
            {points.map((dp) => (
              <FieldRow
                key={dp.id}
                point={dp}
                isHovered={hoveredPointId === dp.id}
                isSelected={selectedPointId === dp.id}
                isEditing={editingPointId === dp.id}
                editBuffer={editBuffer}
                onHoverPoint={onHoverPoint}
                onSelectPoint={onSelectPoint}
                onStartEdit={onStartEdit}
                onEditChange={onEditChange}
                onCommitEdit={onCommitEdit}
                onCancelEdit={onCancelEdit}
                onConfirmPoint={onConfirmPoint}
              />
            ))}
          </CategorySection>
        );
      })}
    </div>
  );
}

function CategorySection({
  category,
  label,
  children,
}: {
  category: DataPointCategory;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="mb-3">
      <div className="flex items-center gap-2 mb-1.5 px-1">
        <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
          {label}
        </span>
        <div className="flex-1 h-px bg-border" />
      </div>
      <div className="space-y-0.5">{children}</div>
    </div>
  );
}

function FieldRow({
  point,
  isHovered,
  isSelected,
  isEditing,
  editBuffer,
  onHoverPoint,
  onSelectPoint,
  onStartEdit,
  onEditChange,
  onCommitEdit,
  onCancelEdit,
  onConfirmPoint,
}: {
  point: DataPoint;
  isHovered: boolean;
  isSelected: boolean;
  isEditing: boolean;
  editBuffer: string;
  onHoverPoint: (id: string | null) => void;
  onSelectPoint: (id: string) => void;
  onStartEdit: (id: string) => void;
  onEditChange: (value: string) => void;
  onCommitEdit: () => void;
  onCancelEdit: () => void;
  onConfirmPoint: (id: string) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const color = getConfidenceColor(point.confidence);
  const confStyles = CONFIDENCE_STYLES[color];
  const statusStyle = STATUS_STYLES[point.status];

  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [isEditing]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") onCommitEdit();
    if (e.key === "Escape") onCancelEdit();
  };

  return (
    <div
      className={`flex items-center gap-2 px-2 py-1.5 rounded-md text-sm transition-colors cursor-pointer ${
        isSelected
          ? `${confStyles.bg} border-l-2 ${confStyles.border}`
          : isHovered
          ? "bg-muted/60 border-l-2 border-muted-foreground/20"
          : "border-l-2 border-transparent hover:bg-muted/40"
      }`}
      onMouseEnter={() => onHoverPoint(point.id)}
      onMouseLeave={() => onHoverPoint(null)}
      onClick={() => onSelectPoint(point.id)}
    >
      {/* Confidence dot */}
      <div
        className={`w-2 h-2 rounded-full shrink-0`}
        style={{ backgroundColor: CONFIDENCE_STYLES[color].stroke }}
        title={`${(point.confidence * 100).toFixed(0)}%`}
      />

      {/* Label */}
      <span className="text-xs text-muted-foreground w-28 shrink-0 truncate">
        {point.line_item_index !== undefined
          ? `#${point.line_item_index + 1} ${point.label}`
          : point.label}
      </span>

      {/* Value or edit input */}
      <div className="flex-1 min-w-0">
        {isEditing ? (
          <input
            ref={inputRef}
            type="text"
            value={editBuffer}
            onChange={(e) => onEditChange(e.target.value)}
            onKeyDown={handleKeyDown}
            onBlur={onCommitEdit}
            className="w-full h-6 px-1.5 text-xs rounded border border-input bg-background font-mono focus:outline-none focus:ring-2 focus:ring-ring"
          />
        ) : (
          <span
            className="text-xs font-mono truncate block"
            onDoubleClick={() => onStartEdit(point.id)}
          >
            {point.current_value}
          </span>
        )}
      </div>

      {/* Confidence badge */}
      <Badge className={`${confStyles.badge} text-[9px] px-1 py-0 shrink-0`}>
        {(point.confidence * 100).toFixed(0)}%
      </Badge>

      {/* Status badge */}
      <Badge className={`${statusStyle.badge} text-[9px] px-1 py-0 shrink-0`}>
        {statusStyle.label}
      </Badge>

      {/* Actions */}
      <div className="flex items-center gap-0.5 shrink-0">
        {!isEditing && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onStartEdit(point.id);
            }}
            className="p-0.5 rounded hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
            title="Szerkesztes"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M17 3a2.85 2.85 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z" />
            </svg>
          </button>
        )}
        {point.status !== "confirmed" && !isEditing && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onConfirmPoint(point.id);
            }}
            className="p-0.5 rounded hover:bg-green-100 text-muted-foreground hover:text-green-700 transition-colors"
            title="Jovahagyas"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="20 6 9 17 4 12" />
            </svg>
          </button>
        )}
      </div>
    </div>
  );
}
