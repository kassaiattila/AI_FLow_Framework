# F1: Production UI — AIFlow Workflow Viewer & Monitoring

> **IMPLEMENTACIOS STATUSZ (2026-03-30, P6 utan)**
>
> | Komponens | Statusz | Reszletek |
> |-----------|---------|-----------|
> | Next.js 16 + shadcn/ui | KESZ | `aiflow-ui/`, 91 forrasfajl |
> | Dashboard + /costs + /runs | KESZ | 6 skill kartya, KPI-k, koltseg bontas |
> | 5 skill viewer | KESZ | invoice, email, rag-chat, diagram, cubix |
> | Backend proxy | KESZ | FastAPI first (3s timeout), JSON fallback |
> | FastAPI backend | KESZ | 9 route file |
> | SSE streaming | KESZ | RAG chat token-by-token |
> | JWT auth + RBAC | KESZ | Login + proxy.ts + cookie + 3 role |
> | Verification audit log | KESZ | Edit/confirm/reset naplozas |
> | Dark mode | KESZ | theme-toggle, localStorage |
> | CSV + PDF export | KESZ | CSV 4 oldalon + print-button |
> | CI/CD | KESZ | GitHub Actions (Python + Next.js) |
> | E2E tesztek | KESZ | Playwright config + 8 smoke test |
> | i18n (hu/en) | KESZ | 80+ kulcs, HU/EN toggle, localStorage |
>
> A teljes UI Next.js 16-ra epul. 11 oldal, 18 API route, 43 komponens, middleware auth.

## Context

Az AIFlow framework 6 skill-lel rendelkezik. A production UI Next.js 16 + React 19 + shadcn/ui stackre epul (`aiflow-ui/`). ~~A meglévő Reflex skeleton~~ (torolve) ~~jó alap, de~~ A cel: generikus workflow viewer, skill-specifikus eredmeny nezet, es koltseg dashboard.

**Cél:** Egy generikus, skill-specifikus UI keretrendszer ami:
1. Minden skill-hez automatikusan generál step-by-step execution nézetet
2. Per-skill testreszabható eredmény viewer-t biztosít (side-by-side, confidence)
3. Költség/prompt monitoringot jelenít meg real-time
4. Éles környezetben menedzselhető, karbantartható

**Inspiráció (GitHub referenciák):**
- [Prefect](https://github.com/PrefectHQ/prefect) — Gantt chart execution timeline
- [Dagster](https://github.com/dagster-io/dagster) — Asset lineage graph, run details
- [Dify](https://github.com/langgenius/dify) — Visual workflow canvas, debugging
- [Arize Phoenix](https://github.com/Arize-ai/phoenix) — LLM trace viewer, quality metrics
- [Langfuse](https://github.com/langfuse/langfuse) — Cost per step, prompt versioning
- [n8n](https://github.com/n8n-io/n8n) — Node-based execution tracking

**Technológia:** Next.js 15 + TypeScript + shadcn/ui (ipari szabvány, jobb UX kontroll)
- Külön frontend projekt: `aiflow-ui/` (monorepo-ban vagy külön repo)
- API-first: minden adat FastAPI endpoint-okból jön
- Két container: API (Python/FastAPI) + Frontend (Next.js)
- Első viewer: **invoice_processor** (legkézzelfoghatóbb eredmény)

---

## Architektúra: 3 rétegű UI rendszer

```
1. GENERIKUS KERET (minden skill-hez automatikus)
   ├── WorkflowRunViewer — step timeline, status, duration, cost
   ├── StepDetailPanel — input/output JSON viewer
   ├── CostDashboard — KPI cards, per-step cost breakdown
   └── RunHistoryTable — korábbi futások listája

2. SKILL-SPECIFIKUS VIEWER (per-skill testreszabható)
   ├── invoice_processor: Számla kártya + tétel táblázat + validáció
   ├── aszf_rag_chat: Chat + citation panel + hallucination score
   ├── email_intent_processor: Email preview + intent badge + entity highlight
   └── process_documentation: Diagram preview + Mermaid render

3. OPERATOR DASHBOARD (áttekintő)
   ├── KPI összesítő (futások, sikeresség, költség)
   ├── Aktív/befejezett/hibás futások
   └── Költség riport (napi/heti/havi)
```

---

## Fázis 1: Generikus Workflow Viewer keret (1 hét)

### 1.1 WorkflowRunState — Reflex state management
**Fájl:** `src/aiflow/ui/state/workflow_state.py`

Generikus state ami BÁRMELY skill futását tudja megjeleníteni:
```python
class StepExecution(BaseModel):
    step_name: str
    status: str  # pending | running | completed | failed
    duration_ms: float
    input_preview: str  # JSON first 200 chars
    output_preview: str
    cost_usd: float
    tokens_used: int
    confidence: float  # 0.0-1.0, ha van
    error: str

class WorkflowRun(BaseModel):
    run_id: str
    skill_name: str
    status: str
    steps: list[StepExecution]
    total_duration_ms: float
    total_cost_usd: float
    started_at: str
    input_summary: str
    output_summary: str

class WorkflowRunState(rx.State):
    runs: list[WorkflowRun]
    selected_run: WorkflowRun | None
    selected_step: StepExecution | None

    async def load_runs(skill: str)
    async def select_run(run_id: str)
    def select_step(step_name: str)
```

### 1.2 WorkflowTimeline component
**Fájl:** `src/aiflow/ui/components/workflow/timeline.py`

Horizontális step timeline (Prefect/Dagster inspiráció):
```
[Parse] → [Classify] → [Extract] → [Validate] → [Store] → [Export]
  ✓ 0.1s    ✓ 0.0s     ✓ 9.1s      ✓ 0.0s     ✓ 0.4s    ✓ 0.7s
  $0.00      $0.00       $0.007      $0.00       $0.00      $0.00
```
- Zöld/piros/szürke/kék szín a státusz alapján
- Kattintható step-ek → StepDetailPanel megnyílik
- Duration + cost megjelenítés per step
- Animáció futás közben (pulsing running step)

### 1.3 StepDetailPanel component
**Fájl:** `src/aiflow/ui/components/workflow/step_detail.py`

Kiválasztott step részletei:
- Input JSON (collapsible, syntax highlighted)
- Output JSON (collapsible, syntax highlighted)
- Prompt (ha LLM step) — system + user message
- LLM válasz (raw text)
- Cost breakdown (model, input tokens, output tokens, cost)
- Confidence score (ha van)
- Duration és timing

### 1.4 CostSummaryBar component
**Fájl:** `src/aiflow/ui/components/workflow/cost_bar.py`

Vízszintes cost breakdown sáv:
```
Total: $0.007 | Parse: $0 | Classify: $0 | Extract: $0.007 (95%) | Validate: $0 | Store: $0 | Export: $0
```
- Proportional width per step
- Hover: részletes token count
- Piros ha budget limit közelében

### 1.5 RunHistoryTable component
**Fájl:** `src/aiflow/ui/components/workflow/run_history.py`

Korábbi futások táblázata:
| Időpont | Skill | Bemenet | Státusz | Idő | Költség | Confidence |
|---------|-------|---------|---------|-----|---------|-----------|
- Szűrhető: skill, dátum, státusz
- Kattintható → WorkflowRunViewer megnyílik
- Pagination

---

## Fázis 2: Skill-specifikus Viewer-ek (1-2 hét)

### 2.1 Skill Viewer registry pattern
**Fájl:** `src/aiflow/ui/viewers/__init__.py`

```python
SKILL_VIEWERS = {
    "invoice_processor": InvoiceResultViewer,
    "aszf_rag_chat": RagChatViewer,
    "email_intent_processor": EmailIntentViewer,
    "process_documentation": DiagramViewer,
}
```

Minden skill regisztrálhat egy custom viewer-t. Ha nincs → generikus JSON viewer.

### 2.2 InvoiceResultViewer
**Fájl:** `src/aiflow/ui/viewers/invoice_viewer.py`

Side-by-side nézet:
```
┌─────────────────────────┬──────────────────────────┐
│ EREDETI PDF (embedded)  │ KINYERT ADATOK           │
│                         │                          │
│ [PDF viewer iframe]     │ Szállító: Adattenger Kft │
│                         │ Adószám: 27752896-2-43   │
│                         │ Vevő: BestIxCom Kft      │
│                         │ Adószám: 28994028-2-42   │
│                         │ ───────────────────────  │
│                         │ TÉTELEK:                 │
│                         │ 1. Dataklub tagság       │
│                         │    1 hó × 7,500 Ft       │
│                         │    + 27% ÁFA = 9,525 Ft  │
│                         │ ───────────────────────  │
│                         │ Nettó:  7,500 Ft         │
│                         │ ÁFA:    2,025 Ft         │
│                         │ Bruttó: 9,525 Ft  ✓      │
│                         │ Confidence: 98%          │
└─────────────────────────┴──────────────────────────┘
```

Komponensek:
- `invoice_card()` — szállító/vevő adatok kártya
- `line_items_table()` — tételek táblázat
- `validation_badge()` — ✓ Valid / ⚠ Figyelmeztetés / ✗ Hiba
- `confidence_meter()` — vizuális confidence jelző

### 2.3 RagChatViewer (aszf_rag_chat)
**Fájl:** `src/aiflow/ui/viewers/rag_chat_viewer.py`

A meglévő chat_container.py (814 sor) bővítése:
- Hallucination score vizuális jelző (zöld/sárga/piros)
- Search results relevancia score sáv
- Step-by-step trace: rewrite → search → context → answer → cite → hallucination
- Chunk highlight: melyik chunk-ból jött a válasz

### 2.4 EmailIntentViewer
**Fájl:** `src/aiflow/ui/viewers/email_intent_viewer.py`

- Email preview (fejléc + body)
- Intent badge (szín + confidence %)
- Entity highlighting (eredeti szövegben kiemelve)
- ML vs LLM összehasonlítás (sklearn intent vs LLM intent)
- Routing döntés vizualizáció (department → queue)

### 2.5 DiagramViewer (process_documentation)
**Fájl:** `src/aiflow/ui/viewers/diagram_viewer.py`

- Mermaid diagram renderelés (iframe Kroki-val)
- DrawIO preview
- Step trace: classify → elaborate → extract → review → generate

---

## Fázis 3: Operator Dashboard + Cost Monitoring (1 hét)

### 3.1 Dashboard Page
**Fájl:** `src/aiflow/ui/pages/dashboard.py`

KPI kártyák (felső sor):
- Összes futás (ma/hét/hónap)
- Sikerességi ráta (%)
- Átlagos feldolgozási idő
- Összes költség ($)
- Aktív skill-ek száma

Alatta:
- Futási előzmények táblázat (szűrhető)
- Skill-enkénti költség diagram (bar chart)
- Napi/heti trend (line chart)

### 3.2 Cost Monitoring API integration
**Fájl:** `src/aiflow/ui/state/cost_state.py`

```python
class CostState(rx.State):
    daily_cost: float
    weekly_cost: float
    monthly_cost: float
    per_skill_cost: dict[str, float]
    per_model_cost: dict[str, float]
    budget_used_pct: float

    async def load_costs(period: str)
```

A meglévő `cost_tracker.py` infrastruktúrára épít.

### 3.3 Cost per-step integration a workflow-okba
Minden skill workflow-jában a step decorator bővítése:
- `result.cost_usd` mentése a step output-ba
- Összesítés a WorkflowRun-ban
- Real-time frissítés a UI-ban

---

## Fájl struktúra (Next.js)

```
aiflow-ui/                                  # Önálló frontend projekt
  package.json                              # Next.js 15 + TypeScript + shadcn/ui
  tsconfig.json
  next.config.ts
  tailwind.config.ts
  .env.local                                # NEXT_PUBLIC_API_URL=http://localhost:8000

  src/
    app/                                    # App Router (Next.js 15)
      layout.tsx                            # Root layout (sidebar + header)
      page.tsx                              # Dashboard (/)
      runs/
        page.tsx                            # Run history (/runs)
        [id]/page.tsx                       # Run detail (/runs/{id})
      skills/
        [skill]/[runId]/page.tsx            # Skill viewer (/skills/invoice_processor/{id})
      costs/
        page.tsx                            # Cost dashboard (/costs)

    components/
      layout/
        sidebar.tsx                         # Navigáció (skills, runs, costs)
        header.tsx                          # Top bar (skill selector, user)
      workflow/
        timeline.tsx                        # Step execution timeline
        step-detail.tsx                     # Step I/O viewer (JSON)
        cost-bar.tsx                        # Per-step cost breakdown
        run-table.tsx                       # Futási előzmények táblázat
      viewers/
        invoice-viewer.tsx                  # Számla side-by-side (ELSŐ)
        rag-chat-viewer.tsx                 # RAG chat + citations
        email-intent-viewer.tsx             # Intent + entity highlight
        diagram-viewer.tsx                  # Mermaid/DrawIO
      ui/                                   # shadcn/ui komponensek (auto-generated)
        button.tsx, card.tsx, table.tsx, badge.tsx, ...

    lib/
      api.ts                                # FastAPI client (fetch wrapper)
      types.ts                              # TypeScript típusok (WorkflowRun, StepExecution, etc.)
      utils.ts                              # Formatters (currency, date, duration)

    hooks/
      use-workflow-run.ts                   # SWR/React Query hook futásokhoz
      use-costs.ts                          # Cost data hook
      use-websocket.ts                      # Real-time futás követés
```

### Backend API bővítés (Python oldal)

```
src/aiflow/api/v1/
  runs.py                                   # ÚJ: GET /runs, GET /runs/{id}, GET /runs/{id}/steps/{step}
  costs.py                                  # ÚJ: GET /costs/summary, /costs/by-skill, /costs/by-model
```

---

## API bővítések (szükséges a UI-hoz)

| Endpoint | Cél | Prioritás |
|----------|-----|-----------|
| GET `/api/v1/runs` | Futási előzmények (szűrhető, lapozható) | P1 |
| GET `/api/v1/runs/{id}` | Egy futás részletei (step-ek, I/O, cost) | P1 |
| GET `/api/v1/runs/{id}/steps/{step}` | Step részletek (prompt, response) | P1 |
| GET `/api/v1/costs/summary` | Költség összesítő (napi/heti/havi) | P1 |
| GET `/api/v1/costs/by-skill` | Per-skill költség breakdown | P2 |
| GET `/api/v1/costs/by-model` | Per-model költség breakdown | P2 |
| WS `/ws/runs/{id}` | Real-time futás követés | P2 |

---

## Becsült munka

| Fázis | Idő | Tartalom |
|-------|-----|----------|
| 1: Generikus keret | 5 nap | State + timeline + step detail + cost bar + run history |
| 2: Skill viewer-ek | 5 nap | Invoice + RAG + Email + Diagram viewer-ek |
| 3: Dashboard + Cost | 3 nap | KPI dashboard + cost API + integration |
| 4: API bővítés | 2 nap | /runs, /costs endpoints |
| **Összesen** | **~3 hét** | |

---

## Docker Compose integráció

```yaml
# docker-compose.yml bővítés
  aiflow-ui:
    build: ./aiflow-ui
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://api:8000
    depends_on:
      - api
    profiles: ["full", "ui"]
```

---

## Implementációs sorrend

| Lépés | Idő | Tartalom |
|-------|-----|----------|
| 1. Next.js scaffold | 0.5 nap | create-next-app + shadcn/ui + tailwind + API client |
| 2. Layout + routing | 0.5 nap | Sidebar, header, app router pages |
| 3. Backend API: /runs + /costs | 1 nap | FastAPI endpoints (Python) |
| 4. WorkflowTimeline + StepDetail | 1 nap | Generikus komponensek |
| 5. RunHistory + Dashboard KPIs | 1 nap | Táblázat + KPI cards |
| 6. **Invoice Viewer** (első skill) | 2 nap | Side-by-side PDF + kinyert adatok |
| 7. Cost Dashboard | 1 nap | Per-skill, per-model, napi/heti chart |
| 8. Többi skill viewer | 3 nap | RAG chat, email intent, diagram |
| 9. Docker + CI | 0.5 nap | Dockerfile, compose, build |
| **Összesen** | **~11 nap** | **~2.5 hét** |

---

## Verifikáció

```bash
# Next.js dev szerver
cd aiflow-ui && npm run dev

# Dashboard: http://localhost:3000/
# Run detail: http://localhost:3000/runs/{id}
# Invoice viewer: http://localhost:3000/skills/invoice_processor/{id}
# Cost dashboard: http://localhost:3000/costs

# Backend API (szükséges a frontend-hez)
make api  # FastAPI http://localhost:8000

# Frontend tesztek
cd aiflow-ui && npm run test
cd aiflow-ui && npm run lint
```

---

## Design elvek

1. **API-first:** Minden adat FastAPI-ből, Next.js csak megjelenít
2. **Generikus-első:** Minden skill automatikusan kap timeline + step detail
3. **Skill-testreszabható:** Viewer registry (TypeScript) per-skill egyedi nézet
4. **Cost-aware:** Minden LLM hívás költsége látható per-step és összesítve
5. **Real-time:** WebSocket (vagy SSE) élő futás követés
6. **shadcn/ui:** Konzisztens, modern, dark/light mode, responsive
7. **TypeScript strict:** Minden típus definiált, nincs `any`
8. **i18n ready:** next-intl (magyar + angol)
