"use client";

import { Badge } from "@/components/ui/badge";

interface VerificationActionsProps {
  stats: {
    total: number;
    auto: number;
    corrected: number;
    confirmed: number;
  };
  onConfirmAll: () => void;
  onSave: () => void;
  onReset: () => void;
  saveStatus?: "" | "saving" | "saved" | "error";
}

export function VerificationActions({
  stats,
  onConfirmAll,
  onSave,
  onReset,
  saveStatus = "",
}: VerificationActionsProps) {
  const hasUnconfirmed = stats.auto > 0 || stats.corrected > 0;
  const hasChanges = stats.corrected > 0 || stats.confirmed > 0;

  return (
    <div className="flex items-center gap-3 flex-wrap">
      {/* Status badges */}
      <div className="flex items-center gap-2">
        {stats.auto > 0 && (
          <Badge className="bg-gray-100 text-gray-600 text-xs">{stats.auto} ellenorizetlen</Badge>
        )}
        {stats.corrected > 0 && (
          <Badge className="bg-blue-100 text-blue-700 text-xs">{stats.corrected} javitva</Badge>
        )}
        {stats.confirmed > 0 && (
          <Badge className="bg-green-100 text-green-700 text-xs">{stats.confirmed} jovahagyva</Badge>
        )}
      </div>

      {/* Save status indicator */}
      {saveStatus === "saving" && <span className="text-xs text-blue-600 animate-pulse">Mentes...</span>}
      {saveStatus === "saved" && <span className="text-xs text-green-600">Mentve!</span>}
      {saveStatus === "error" && <span className="text-xs text-red-600">Mentesi hiba!</span>}

      <div className="flex-1" />

      {/* Action buttons */}
      <button
        onClick={onReset}
        disabled={!hasChanges}
        className="px-3 py-1.5 rounded-md text-xs font-medium border border-border text-muted-foreground hover:bg-muted disabled:opacity-40 transition-colors"
      >
        Visszaallitas
      </button>
      <button
        onClick={onConfirmAll}
        disabled={!hasUnconfirmed}
        className="px-3 py-1.5 rounded-md text-xs font-medium bg-green-600 text-white hover:bg-green-700 disabled:opacity-40 transition-colors"
      >
        Mind jovahagyva
      </button>
      <button
        onClick={onSave}
        disabled={saveStatus === "saving"}
        className="px-3 py-1.5 rounded-md text-xs font-medium bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-40 transition-colors"
      >
        {saveStatus === "saving" ? "Mentes..." : "Mentes"}
      </button>
    </div>
  );
}
