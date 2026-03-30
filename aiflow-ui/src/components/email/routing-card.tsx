import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { RoutingDecision, PriorityResult } from "@/lib/types";
import { PriorityBadge } from "./shared";

interface RoutingCardProps {
  routing: RoutingDecision;
  priority: PriorityResult;
}

export function RoutingCard({ routing, priority }: RoutingCardProps) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm">Routing</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <div className="p-2 bg-muted/50 rounded">
            <p className="text-xs text-muted-foreground">Prioritás</p>
            <div className="flex items-center gap-2 mt-1">
              <PriorityBadge level={priority.priority_level} />
              <span className="text-xs">SLA: {priority.sla_hours}h</span>
            </div>
          </div>
          <div className="p-2 bg-muted/50 rounded">
            <p className="text-xs text-muted-foreground">Osztály</p>
            <p className="text-sm font-medium mt-1">{routing.department_name}</p>
          </div>
          <div className="p-2 bg-muted/50 rounded">
            <p className="text-xs text-muted-foreground">Sor</p>
            <p className="text-sm font-medium mt-1">{routing.queue_name}</p>
          </div>
          <div className="p-2 bg-muted/50 rounded">
            <p className="text-xs text-muted-foreground">Eszkaláció</p>
            <p className="text-sm font-medium mt-1">
              {routing.auto_escalate_after_minutes > 0
                ? `${Math.round(routing.auto_escalate_after_minutes / 60)}h`
                : "Nincs"}
            </p>
          </div>
        </div>

        {priority.boosts_applied.length > 0 && (
          <div className="text-xs">
            <span className="text-muted-foreground">Boost: </span>
            {priority.boosts_applied.join(", ")}
          </div>
        )}

        {priority.reasoning && (
          <p className="text-xs text-muted-foreground border-t pt-2">{priority.reasoning}</p>
        )}
      </CardContent>
    </Card>
  );
}
