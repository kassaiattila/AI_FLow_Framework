"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export interface ScheduleConfig {
  frequency: "daily" | "weekly" | "once";
  time: string;
  statusFilter: "new" | "failed" | "all";
  timeFilter: "24h" | "7d" | "30d" | "all";
  enabled: boolean;
}

const STORAGE_KEY = "aiflow_schedule_config";

function loadSchedule(): ScheduleConfig | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function saveSchedule(config: ScheduleConfig) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(config));
}

interface ScheduleDialogProps {
  open: boolean;
  onClose: () => void;
}

export function ScheduleDialog({ open, onClose }: ScheduleDialogProps) {
  const [config, setConfig] = useState<ScheduleConfig>({
    frequency: "daily",
    time: "08:00",
    statusFilter: "new",
    timeFilter: "24h",
    enabled: false,
  });

  useEffect(() => {
    const saved = loadSchedule();
    if (saved) setConfig(saved);
  }, [open]);

  if (!open) return null;

  const handleSave = () => {
    saveSchedule({ ...config, enabled: true });
    onClose();
  };

  // Compute next run time display
  const now = new Date();
  const [h, m] = config.time.split(":").map(Number);
  const next = new Date(now);
  next.setHours(h, m, 0, 0);
  if (next <= now) next.setDate(next.getDate() + 1);
  if (config.frequency === "weekly") {
    const daysUntilMonday = (8 - next.getDay()) % 7 || 7;
    if (next <= now || next.getDay() !== 1) next.setDate(next.getDate() + daysUntilMonday);
  }
  const nextStr = next.toLocaleString("hu-HU", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onClose}>
      <Card className="w-[400px] shadow-xl" onClick={(e) => e.stopPropagation()}>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Utemezes beallitasa</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Frequency */}
          <div>
            <label className="text-xs font-medium text-muted-foreground">Gyakorisag</label>
            <div className="flex gap-2 mt-1">
              {(["daily", "weekly", "once"] as const).map((f) => (
                <button
                  key={f}
                  onClick={() => setConfig((c) => ({ ...c, frequency: f }))}
                  className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                    config.frequency === f ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground hover:bg-muted/80"
                  }`}
                >
                  {f === "daily" ? "Naponta" : f === "weekly" ? "Hetente" : "Egyedi"}
                </button>
              ))}
            </div>
          </div>

          {/* Time */}
          <div>
            <label className="text-xs font-medium text-muted-foreground">Idopont</label>
            <input
              type="time"
              value={config.time}
              onChange={(e) => setConfig((c) => ({ ...c, time: e.target.value }))}
              className="mt-1 block w-full h-8 px-2 text-sm rounded-md border border-input bg-background font-mono focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>

          {/* Status filter */}
          <div>
            <label className="text-xs font-medium text-muted-foreground">Dokumentum szures</label>
            <div className="flex gap-2 mt-1">
              {([
                { v: "new" as const, l: "Nem feldolgozott" },
                { v: "failed" as const, l: "Hibas" },
                { v: "all" as const, l: "Osszes" },
              ]).map(({ v, l }) => (
                <button
                  key={v}
                  onClick={() => setConfig((c) => ({ ...c, statusFilter: v }))}
                  className={`px-2 py-1 rounded text-xs transition-colors ${
                    config.statusFilter === v ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"
                  }`}
                >
                  {l}
                </button>
              ))}
            </div>
          </div>

          {/* Time filter */}
          <div>
            <label className="text-xs font-medium text-muted-foreground">Ido szures</label>
            <div className="flex gap-2 mt-1">
              {([
                { v: "24h" as const, l: "24 ora" },
                { v: "7d" as const, l: "7 nap" },
                { v: "30d" as const, l: "30 nap" },
                { v: "all" as const, l: "Osszes" },
              ]).map(({ v, l }) => (
                <button
                  key={v}
                  onClick={() => setConfig((c) => ({ ...c, timeFilter: v }))}
                  className={`px-2 py-1 rounded text-xs transition-colors ${
                    config.timeFilter === v ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"
                  }`}
                >
                  {l}
                </button>
              ))}
            </div>
          </div>

          {/* Next run */}
          <div className="rounded-md bg-muted p-2 text-xs text-muted-foreground">
            Kovetkezo futas: <span className="font-mono font-medium text-foreground">{nextStr}</span>
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-2 pt-2">
            <button onClick={onClose} className="px-3 py-1.5 rounded-md text-xs border border-border text-muted-foreground hover:bg-muted">
              Megse
            </button>
            <button onClick={handleSave} className="px-3 py-1.5 rounded-md text-xs bg-primary text-primary-foreground hover:bg-primary/90">
              Utemezes mentese
            </button>
          </div>

          {/* Existing schedule info */}
          {loadSchedule()?.enabled && (
            <div className="flex items-center gap-2 pt-1">
              <Badge className="bg-green-100 text-green-700 text-[10px]">Aktiv</Badge>
              <span className="text-[10px] text-muted-foreground">
                {loadSchedule()?.frequency === "daily" ? "Naponta" : loadSchedule()?.frequency === "weekly" ? "Hetente" : "Egyedi"}{" "}
                {loadSchedule()?.time}
              </span>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
