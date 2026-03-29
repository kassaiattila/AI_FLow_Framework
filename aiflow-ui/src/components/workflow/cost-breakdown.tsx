"use client";

import type { StepExecution } from "@/lib/types";

const STEP_COLORS = [
  "bg-blue-500",
  "bg-emerald-500",
  "bg-amber-500",
  "bg-purple-500",
  "bg-rose-500",
  "bg-cyan-500",
  "bg-orange-500",
  "bg-indigo-500",
];

interface CostBreakdownProps {
  steps: StepExecution[];
  totalCost: number;
}

export function CostBreakdown({ steps, totalCost }: CostBreakdownProps) {
  const stepsWithCost = steps.filter((s) => s.cost_usd > 0);

  if (totalCost === 0) {
    return (
      <div className="text-xs text-muted-foreground italic">No LLM cost in this run (local processing only)</div>
    );
  }

  return (
    <div className="space-y-2">
      {/* Stacked bar */}
      <div className="flex h-6 rounded-full overflow-hidden bg-muted">
        {stepsWithCost.map((step, i) => {
          const pct = (step.cost_usd / totalCost) * 100;
          return (
            <div
              key={step.step_name}
              className={`${STEP_COLORS[i % STEP_COLORS.length]} transition-all hover:opacity-80 cursor-pointer`}
              style={{ width: `${Math.max(pct, 2)}%` }}
              title={`${step.step_name}: $${step.cost_usd.toFixed(4)} (${pct.toFixed(0)}%)`}
            />
          );
        })}
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-x-4 gap-y-1">
        {stepsWithCost.map((step, i) => (
          <div key={step.step_name} className="flex items-center gap-1.5 text-xs">
            <div className={`w-2.5 h-2.5 rounded-full ${STEP_COLORS[i % STEP_COLORS.length]}`} />
            <span className="text-muted-foreground">{step.step_name}</span>
            <span className="font-mono font-medium">${step.cost_usd.toFixed(4)}</span>
          </div>
        ))}
      </div>

      {/* Total */}
      <div className="flex justify-end text-xs font-medium">
        Total: <span className="font-mono ml-1">${totalCost.toFixed(4)}</span>
      </div>
    </div>
  );
}
