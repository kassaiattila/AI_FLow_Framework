"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useI18n } from "@/hooks/use-i18n";
import type { RoutingDecision, PriorityResult } from "@/lib/types";
import { PriorityBadge } from "./shared";

interface RoutingCardProps {
  routing: RoutingDecision;
  priority: PriorityResult;
}

export function RoutingCard({ routing, priority }: RoutingCardProps) {
  const { t } = useI18n();
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm">{t("email.routing")}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <div className="p-2 bg-muted/50 rounded">
            <p className="text-xs text-muted-foreground">{t("email.priorityLabel")}</p>
            <div className="flex items-center gap-2 mt-1">
              <PriorityBadge level={priority.priority_level} />
              <span className="text-xs">SLA: {priority.sla_hours}h</span>
            </div>
          </div>
          <div className="p-2 bg-muted/50 rounded">
            <p className="text-xs text-muted-foreground">{t("email.department")}</p>
            <p className="text-sm font-medium mt-1">{routing.department_name}</p>
          </div>
          <div className="p-2 bg-muted/50 rounded">
            <p className="text-xs text-muted-foreground">{t("email.queue")}</p>
            <p className="text-sm font-medium mt-1">{routing.queue_name}</p>
          </div>
          <div className="p-2 bg-muted/50 rounded">
            <p className="text-xs text-muted-foreground">{t("email.escalation")}</p>
            <p className="text-sm font-medium mt-1">
              {routing.auto_escalate_after_minutes > 0
                ? `${Math.round(routing.auto_escalate_after_minutes / 60)}h`
                : t("email.noEscalation")}
            </p>
          </div>
        </div>

        {priority.boosts_applied.length > 0 && (
          <div className="text-xs">
            <span className="text-muted-foreground">{t("email.boost")}: </span>
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
