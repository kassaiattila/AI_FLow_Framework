/**
 * AIFlow TraceTree — S111 recursive Langfuse trace viewer.
 *
 * Renders a collapsible span tree. Each node shows the span name, duration
 * (ms), status, optional model, token counts, and cost. Children are lazily
 * expanded via local state.
 */
import { useState } from "react";

export interface TraceSpan {
  id: string;
  name: string;
  start_ms: number;
  duration_ms: number;
  status: string;
  input_tokens: number | null;
  output_tokens: number | null;
  cost_usd: number | null;
  model: string | null;
  children: TraceSpan[];
}

export interface TraceData {
  trace_id: string;
  run_id: string;
  total_duration_ms: number;
  total_cost_usd: number;
  root_spans: TraceSpan[];
}

interface NodeProps {
  span: TraceSpan;
  depth: number;
  traceStart: number;
  traceDuration: number;
}

function SpanNode({ span, depth, traceStart, traceDuration }: NodeProps) {
  const [open, setOpen] = useState(depth < 1);
  const hasChildren = span.children.length > 0;
  const statusColor =
    span.status === "error"
      ? "bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400"
      : "bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400";

  const barLeftPct =
    traceDuration > 0
      ? Math.max(0, ((span.start_ms - traceStart) / traceDuration) * 100)
      : 0;
  const barWidthPct =
    traceDuration > 0
      ? Math.max(0.5, (span.duration_ms / traceDuration) * 100)
      : 1;

  return (
    <div>
      <div
        className="group flex items-center gap-2 border-b border-gray-100 px-2 py-1.5 text-sm hover:bg-gray-50 dark:border-gray-800 dark:hover:bg-gray-900/50"
        style={{ paddingLeft: `${8 + depth * 16}px` }}
      >
        <button
          type="button"
          onClick={() => hasChildren && setOpen((v) => !v)}
          disabled={!hasChildren}
          className="w-4 text-xs text-gray-500 disabled:text-transparent"
          aria-label={open ? "collapse" : "expand"}
        >
          {hasChildren ? (open ? "▾" : "▸") : "·"}
        </button>
        <span className="flex-1 truncate font-medium text-gray-900 dark:text-gray-100">
          {span.name}
        </span>
        {span.model && (
          <span className="hidden font-mono text-xs text-gray-500 md:inline">
            {span.model}
          </span>
        )}
        {(span.input_tokens != null || span.output_tokens != null) && (
          <span className="hidden text-xs text-gray-500 md:inline">
            {span.input_tokens ?? 0} / {span.output_tokens ?? 0} tok
          </span>
        )}
        {span.cost_usd != null && span.cost_usd > 0 && (
          <span className="text-xs text-gray-500">
            ${span.cost_usd.toFixed(4)}
          </span>
        )}
        <span className="text-xs tabular-nums text-gray-500">
          {span.duration_ms} ms
        </span>
        <span
          className={`rounded-full px-1.5 py-0.5 text-[10px] font-medium ${statusColor}`}
        >
          {span.status}
        </span>
      </div>
      {/* Gantt bar */}
      <div
        className="relative h-1.5 px-2"
        style={{ paddingLeft: `${8 + depth * 16}px` }}
      >
        <div className="relative h-full w-full rounded bg-gray-100 dark:bg-gray-800">
          <div
            className={`absolute top-0 h-full rounded ${span.status === "error" ? "bg-red-400" : "bg-brand-500"}`}
            style={{ left: `${barLeftPct}%`, width: `${barWidthPct}%` }}
          />
        </div>
      </div>
      {open && hasChildren && (
        <div>
          {span.children.map((child) => (
            <SpanNode
              key={child.id}
              span={child}
              depth={depth + 1}
              traceStart={traceStart}
              traceDuration={traceDuration}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export function TraceTree({ trace }: { trace: TraceData }) {
  if (!trace.root_spans.length) {
    return (
      <p className="px-2 py-6 text-center text-sm text-gray-500">
        No spans recorded
      </p>
    );
  }
  const traceStart = trace.root_spans[0]?.start_ms ?? 0;
  const traceDuration = Math.max(1, trace.total_duration_ms);
  return (
    <div className="rounded-xl border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-900">
      <div className="flex items-center justify-between border-b border-gray-100 px-3 py-2 dark:border-gray-800">
        <div className="text-xs text-gray-500">
          Trace{" "}
          <span className="font-mono text-gray-700 dark:text-gray-300">
            {trace.trace_id.slice(0, 12)}
          </span>
        </div>
        <div className="text-xs text-gray-500">
          {trace.total_duration_ms} ms · ${trace.total_cost_usd.toFixed(4)}
        </div>
      </div>
      {trace.root_spans.map((span) => (
        <SpanNode
          key={span.id}
          span={span}
          depth={0}
          traceStart={traceStart}
          traceDuration={traceDuration}
        />
      ))}
    </div>
  );
}
