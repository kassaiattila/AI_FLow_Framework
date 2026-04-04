# AIFlow v1.2.0 — Session 8 Prompt (C6 Invoice Use Case)

> **Datum:** 2026-04-04 (session 7 utan)
> **Elozo session:** Tier 1 COMPLETE (C0-C5) — Pipeline Orchestrator merged to main, tag v1.2.0-alpha
> **Branch:** main (v1.2.0-alpha)
> **Port:** API 8102, Frontend 5173 (Vite proxy → 8102)
> **Utolso commit:** `19f612a` feat: v1.2.0-alpha — Tier 1 Pipeline Orchestrator (C0-C5)

---

## ALLAPOT

### Tier 1 Core Orchestration: KESZ (v1.2.0-alpha, 2026-04-04)

| Ciklus | Fazis | Tartalom | Allapot |
|--------|-------|----------|---------|
| C0 | Elokeszites | Untitled UI init, smoke test fix, ruff config | DONE |
| C1 | P1 Adapter | ServiceAdapter protocol + 7 adapter + 40 test | DONE |
| C2 | P2 Schema | YAML schema + Jinja2 + compiler + parser + 61 test | DONE |
| C3 | P3 Runner+DB | PipelineRunner + Alembic 027 + repository + 9 test | DONE |
| C4 | P4 API | 9 endpoint, curl-tesztelve, source=backend | DONE |
| C5 | P5 UI | Pipelines + PipelineDetail, 7 HARD GATE, E2E PASS | DONE |

### Pipeline Modul Strukturra (KESZ)

```
src/aiflow/pipeline/
├── __init__.py        # Public API exports
├── adapter_base.py    # ServiceAdapter Protocol + BaseAdapter + AdapterRegistry
├── adapters/          # 6 adapter module (7 adapter: RAG has ingest+query)
│   ├── email_adapter.py
│   ├── classifier_adapter.py
│   ├── document_adapter.py
│   ├── rag_adapter.py
│   ├── media_adapter.py
│   └── diagram_adapter.py
├── schema.py          # PipelineDefinition, StepDef, TriggerDef, RetryPolicy
├── template.py        # Jinja2 SandboxedEnvironment + StrictUndefined
├── compiler.py        # PipelineCompiler → DAG + step_funcs
├── parser.py          # YAML/file/dict → PipelineDefinition
├── repository.py      # Async CRUD for pipeline_definitions table
└── runner.py          # PipelineRunner: run(id), run_from_yaml()
```

### DB: 27 Alembic migracio, 42 tabla, pipeline_definitions tabla + workflow_runs.pipeline_id FK
### API: 121+ endpoint (20 router), 9 pipeline endpoint
### UI: 19 oldal (+ Pipelines, PipelineDetail)
### Tesztek: 110 pipeline unit test PASS

---

## KOVETKEZO FELADAT: C6 Ciklus (Invoice Automation Pipeline)

### Cel
Bizonyitani, hogy a pipeline orchestrator MUKODIK valos adatokkal. Meglevo service-eket lancoljuk ossze YAML pipeline-nal.

### Branch
```bash
git checkout -b feature/v1.2.0-tier1.5-invoice-usecase
```

### Lepesek

```
1. TERVEZES: Olvasd 48 Phase C6 + 51 (document extraction)
2. FEJLESZTES:
   - src/aiflow/pipeline/builtin_templates/invoice_automation_v1.yaml
   - POST /api/v1/pipelines/{id}/run endpoint (meg nem implementalt C4-ben!)
   - PipelineRunner integracio az API-ba
3. TESZTELES:
   - Valos futatas: YAML → compile → run → workflow_runs + step_runs sorok
   - curl: POST /pipelines → POST /pipelines/{id}/run → GET /pipelines/{id}/runs/{run_id}
   - L0 smoke test PASS
4. DOKUMENTALAS: commit, 56 frissites
5. SESSION PROMPT: "C6 KESZ, kovetkezo C7 (Notification)"
```

### Invoice Pipeline YAML (tervezett)
```yaml
name: invoice_automation_v1
version: "1.0.0"
description: "Email → classify → extract attachments → process documents"
trigger:
  type: manual
input_schema:
  connector_id: { type: string, required: true }
  days: { type: integer, default: 7 }
steps:
  - name: fetch_emails
    service: email_connector
    method: fetch_emails
    config:
      connector_id: "{{ input.connector_id }}"
      limit: 10
      since_days: "{{ input.days }}"
  - name: classify_intent
    service: classifier
    method: classify
    depends_on: [fetch_emails]
    for_each: "{{ fetch_emails.output.emails }}"
    config:
      text: "{{ item.subject }} {{ item.body_text }}"
  - name: extract_documents
    service: document_extractor
    method: extract
    depends_on: [classify_intent]
    config:
      file_path: "{{ item.file_path }}"
```

### FONTOS
- Ez NEM uj service fejlesztes — meglevo service-eket lancoljuk
- A `/run` endpoint meg NEM letezik az API-ban — C6-ban implementaljuk
- Valos teszteles: valos email connector config, valos PDF, valos classify

---

## SZERVER INDITAS

```bash
.venv\Scripts\python.exe -B -m uvicorn aiflow.api.app:create_app --factory --port 8102
cd aiflow-admin && npm run dev
```

---

## VEGREHAJTASI TERV (frissitett)

```
C0-C5:  Tier 1 Core ──── DONE (v1.2.0-alpha) ✓
C6:     Invoice v1 ────── KOVETKEZO
C7-C10: Tier 2 ────────── 2-3 session
C11-16: Tier 3 RAG ────── 3-4 session
C17-20: Tier 4 Polish ─── 1-2 session
```

---

## INFRASTRUKTURA

- PostgreSQL 5433, Redis 6379 (Docker)
- Auth: admin@bestix.hu / admin
- 27 Alembic migracio, 42 DB tabla, 121+ endpoint, 20 router, 19 UI oldal, 15 service
- Tag: v1.2.0-alpha (Tier 1 complete)
