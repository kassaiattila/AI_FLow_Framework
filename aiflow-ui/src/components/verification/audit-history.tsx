import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { AuditEntry } from "@/hooks/use-verification-state";

interface AuditHistoryProps {
  entries: AuditEntry[];
}

const ACTION_LABELS: Record<string, { label: string; color: string }> = {
  edit: { label: "Szerkesztes", color: "bg-blue-100 text-blue-800" },
  confirm: { label: "Jovahagyas", color: "bg-green-100 text-green-800" },
  confirm_all: { label: "Mind jovahagyva", color: "bg-green-100 text-green-800" },
  reset: { label: "Visszaallitas", color: "bg-yellow-100 text-yellow-800" },
};

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("hu-HU", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function AuditHistory({ entries }: AuditHistoryProps) {
  if (entries.length === 0) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Audit naplo</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-muted-foreground text-center py-4">
            Nincs valtozas
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm">Audit naplo</CardTitle>
          <Badge className="bg-gray-100 text-gray-700 text-[9px]">{entries.length}</Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-1.5 max-h-[300px] overflow-y-auto">
          {[...entries].reverse().map((entry, idx) => {
            const action = ACTION_LABELS[entry.action] || { label: entry.action, color: "bg-gray-100 text-gray-700" };
            return (
              <div key={idx} className="flex items-start gap-2 text-xs p-1.5 rounded hover:bg-muted/50">
                <span className="text-muted-foreground w-14 shrink-0">
                  {formatTime(entry.timestamp)}
                </span>
                <Badge className={`${action.color} text-[9px] shrink-0`}>{action.label}</Badge>
                <div className="min-w-0">
                  {entry.field_id && (
                    <span className="font-medium">{entry.field_id}</span>
                  )}
                  {entry.old_value && entry.new_value && (
                    <span className="text-muted-foreground">
                      {" "}{entry.old_value} &rarr; {entry.new_value}
                    </span>
                  )}
                  {!entry.field_id && entry.new_value && (
                    <span className="text-muted-foreground">{entry.new_value}</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
