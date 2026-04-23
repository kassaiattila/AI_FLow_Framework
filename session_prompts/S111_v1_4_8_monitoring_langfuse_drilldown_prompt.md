# AIFlow v1.4.8 Sprint L — Session 111 Prompt (S111 — Runs + Monitoring Langfuse drill-down)

> **Datum:** 2026-04-24 (tervezett folytatas)
> **Branch:** `feature/v1.4.8-monitoring-cost` — **UJ** branch, kiindulas `main` @ tag `v1.4.7`.
> **HEAD prereq:** PR #15 merged + `v1.4.7` tag pushed. Fallback: ha meg nem, allj meg es jelezd.
> **Port:** API 8102 | Frontend Vite 5173
> **Plan:** `01_PLAN/110_USE_CASE_FIRST_REPLAN.md` §4 Sprint L (S111 row — `Runs.tsx` + `Monitoring.tsx` Langfuse drill-down).
> **Session tipus:** IMPLEMENTATION — UI + backend Langfuse proxy. Code risk: MEDIUM (uj Langfuse API wrapping), process risk: LOW.

---

## KONTEXTUS

### Honnan jottunk (Sprint K DONE)

- Sprint K (v1.4.7) **DONE**, squash-merged 2026-04-23 (PR #15 / `2eecb20`), tag `v1.4.7` pushed.
- 9 feature commits + regression across S106-S110:
  - S106: `ClassificationResult` unify + `scan_and_classify` orchestrator + `POST /emails/scan/{config_id}`
  - S107: `IntentRoutingPolicy` + wiring + 4-way test
  - S108a-d: baseline + 3-way UI split + bug-fix + UX polish (retry/colors/processing pill)
  - S109a: Intent Rules CRUD (UI + backend + 5 tests)
  - S109b: Prompts YAML editor (GET/PUT detail + PromptDetail.tsx + 5 tests)
  - S110: UC3 golden-path Playwright E2E + `/live-test` framework + 3 catalog entries
- 67+ integration (100% PASS), 4 UC3 E2E (18s GREEN), 3 live-test katalog (emails + intent-rules + prompts).
- Live stack on `127.0.0.1:8102` + `:5173`, `admin@aiflow.local` / `AiFlowDev2026`.

### Hova tartunk — Sprint L S111 scope

Cel: Runs + Monitoring oldalakon **Langfuse trace drill-down**. A user minden workflow_run rekord-hoz egy kattintassal lasson trace-fat (span-ek + timing + token count + cost) a Langfuse-bol.

**Terv (replan §4 Sprint L):**

| Session | Scope | Acceptance |
|---|---|---|
| **S111 (this)** | `Runs.tsx` + `Monitoring.tsx`: Langfuse drill-down (trace tree, step timings, token counts). Backend proxies Langfuse API per tenant. | Playwright: open Runs → pick row → see tree. |
| **S112** | `Costs.tsx` + `CostAttribution` contract + `PolicyEngine.cost_cap` enforcement (429 on breach). | Cost cap integration test: 2 calls, second breaches cap → 429. |
| **S113** | Cross-UC regression pack: UC1 + UC2 + UC3 együtt a CI profilban ≤10 min. PR + tag `v1.4.8`. | CI profil <10 min GREEN. |

### Jelenlegi allapot (main @ v1.4.7)

```
27 service | 186 endpoint | 50 DB tabla | 42 Alembic migration (head: 042)
1997+ unit | 67+ integration | 417 E2E (413 + 4 UC3 golden-path)
8 skill | 24+ UI oldal (Emails / EmailConnectors / EmailDetail / IntentRules / PromptDetail uj)
Branch: feature/v1.4.8-monitoring-cost (uj, kiindulas main@v1.4.7)
Sprint K DONE | Sprint L S111 START
```

---

## ELOFELTELEK

```bash
git fetch origin --tags
git log --oneline main -1            # 2eecb20 v1.4.7 Sprint K
git tag -l "v1.4.7"                   # pontosan 1 sor
git checkout main && git pull origin main
git checkout -b feature/v1.4.8-monitoring-cost

.venv/Scripts/python.exe -m ruff check src/ tests/ --quiet
cd aiflow-admin && npx tsc --noEmit && cd ..
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/e2e/ --collect-only -q
# Expected: 417 tests collected
```

---

## FELADATOK

### LEPES 1 — Discovery (readonly ~15 min)

```bash
grep -rn "langfuse\|Langfuse" src/aiflow/observability/ 2>&1 | head -20
grep -rn "trace_id" src/aiflow/api/v1/ 2>&1 | head -10
ls aiflow-admin/src/pages-new/ | grep -iE "runs|monitoring"
```

Kerdesek:
- Mit exportal `aiflow.observability.tracing`?
- Melyik endpoint ad `trace_id`-t a response-ban (workflow_runs.trace_id)?
- Runs.tsx mar jelenit-e meg trace linket?

### LEPES 2 — Backend: Langfuse trace proxy

**Uj endpoint:** `GET /api/v1/runs/{run_id}/trace` → proxyzza `langfuse.get_trace(trace_id)`-t es visszaadja a span fat + timing + token + cost breakdown.

**Pydantic models:**
```python
class TraceSpan(BaseModel):
    id: str
    name: str
    start_ms: int          # relative to trace start
    duration_ms: int
    status: str            # ok | error
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None
    model: str | None = None
    children: list["TraceSpan"] = []

class TraceResponse(BaseModel):
    trace_id: str
    run_id: str
    total_duration_ms: int
    total_cost_usd: float
    root_spans: list[TraceSpan]
    source: str = "backend"
```

**Langfuse SDK:** `from langfuse import Langfuse` (mar dependency).

**Test:** `tests/integration/api/test_runs_trace.py` (3 szcenario: happy path / missing trace_id / Langfuse API hiba).

### LEPES 3 — Frontend: Runs + RunDetail drill-down

**`Runs.tsx`:** soronkent "Trace" oszlop — kattinthato link → `/runs/:id/trace` vagy Langfuse UI URL (env `AIFLOW_LANGFUSE_UI_URL`).

**`RunDetail.tsx`:** uj szekcio `TraceTree` komponenssel.

**Uj komponens:** `aiflow-admin/src/components-new/TraceTree.tsx` — react-aria Tree v recursive panel. Kollapsz/expand, click-re reszletek.

### LEPES 4 — Monitoring.tsx: aggregate span-metrics

Span-level aggregatumok legutolso 24h-bol: avg/p95 duration, token total, cost per model.

Backend: `GET /api/v1/monitoring/span-metrics?window_h=24`.

### LEPES 5 — Live-test + E2E catalog bovites

- `tests/ui-live/runs.md` — uj journey (Login → /runs → row click → /runs/:id → TraceTree expand).
- `tests/e2e/test_uc_monitoring_golden_path.py` — 3 smoke (runs list + detail + monitoring).

### LEPES 6 — Regression + session-close

```bash
.venv/Scripts/python.exe -m ruff check src/ tests/ --quiet
.venv/Scripts/python.exe -m ruff format --check src/ tests/
cd aiflow-admin && npx tsc --noEmit && cd ..
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/integration/api/test_runs_trace.py -q --no-cov
PYTHONPATH="src;." .venv/Scripts/python.exe scripts/export_openapi.py
# CLAUDE.md: 186 → 188 endpoints, 67 → 70 integration, 4 → 7 UC golden-path
/session-close S111
```

---

## STOP FELTETELEK

**HARD:**
1. Langfuse Python SDK API v2 breaking change → architect agent.
2. `trace_id` oszlop nincs `workflow_runs`-ban → Alembic 043 szukseges → scope novel + user decision.
3. Langfuse cloud rate-limit hit → caching/batch fetch → külön session.

**SOFT:**
1. TreeView Untitled UI primitive hianyzik → minimal recursive Tailwind component (acceptable).
2. p95 duration lassu nagyobb window-en → DB index, defer.

---

## SESSION VEGEN

```
/session-close S111
```

Utana `/clear` es S112 (Costs.tsx + cost-cap enforcement).
