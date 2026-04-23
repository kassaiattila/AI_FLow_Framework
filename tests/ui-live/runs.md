# Live E2E: Runs + Monitoring (Langfuse drill-down)

> **Module:** `aiflow-admin/src/pages-new/Runs.tsx` + `RunDetail.tsx` + `Monitoring.tsx`
> **Component:** `aiflow-admin/src/components-new/TraceTree.tsx`
> **API:** `GET /api/v1/runs/{run_id}/trace`, `GET /api/v1/monitoring/span-metrics?window_h=24`
> **Verzio:** v1.4.8 Sprint L S111

## Elofeltetelek

```
curl -sf http://127.0.0.1:8102/health
curl -sf http://127.0.0.1:5173
```

## Journey

### 1. Login + runs list

```
navigate -> http://localhost:5173/#/runs
```

**Expect**

- Table with columns: Run ID / skill / status / duration / cost / started / **Trace** / actions
- Trace column shows `- trace` button for rows with `trace_id`, em-dash for rows without
- Click on Trace button navigates to `/runs/:id#trace`
- Row click (anywhere else) navigates to `/runs/:id`

### 2. Run detail drill-down

```
click first row -> /runs/:id
```

**Expect**

- KPI cards (pipeline / duration / cost / started)
- Step Log table renders step rows (or empty state if no steps)
- New section "Trace Tree" / "Trace fa" appears under the step log
  - If Langfuse is NOT configured OR trace not recorded: friendly empty state
    ("No Langfuse trace recorded for this run.")
  - If trace found: recursive `TraceTree` with Gantt bars, span names, durations,
    optional model / token / cost columns
- Expand/collapse chevrons on spans with children

### 3. Monitoring span metrics

```
navigate -> http://localhost:5173/#/monitoring
```

**Expect**

- Heading "LLM Spans - 24h"
- Table with columns: Model / Spans / Avg ms / P95 ms / Tokens (in/out) / Cost USD
- If Langfuse unconfigured OR no spans in 24h: graceful notice
  ("Span metrics unavailable" / "No spans in the last 24h")

## Sikerkriteriumok (PASS)

- [ ] 0 console error
- [ ] Trace column renders without crash on runs list
- [ ] RunDetail does not crash when trace_id is null (empty state must show)
- [ ] Monitoring page still loads even when Langfuse is disabled (warning banner OK)

## Utolso futtatas

### 2026-04-23 — **SCHEDULED (S111 kickoff)**

- Tool csomag: `mcp__plugin_playwright_playwright__*`
- Integration tests PASS (5/5): `tests/integration/api/test_runs_trace.py`
- E2E smoke (3 cases): `tests/e2e/test_uc_monitoring_golden_path.py` — requires live stack
- Live browser walk-through: pending user run on `127.0.0.1:8102` + `:5173`
