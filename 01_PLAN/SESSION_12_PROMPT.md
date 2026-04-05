# AIFlow v1.2.1 — Session 12 Prompt (S8 Promptfoo — Tier B Quality & Observability cont.)

> **Datum:** 2026-04-04 (session 11 utan)
> **Elozo session:** S7 DONE + Langfuse prompt sync bonus (session 11)
> **Branch:** feature/v1.2.1-production-ready (14 commit, main-bol branched)
> **Port:** API 8102, Frontend 5174 (Vite proxy → 8102)
> **Utolso commit:** `f2694cd` docs: P3 Langfuse Prompt Management DONE

---

## AKTUALIS TERV

**`01_PLAN/57_PRODUCTION_READY_SPRINT.md`** — 14 ciklus (S1-S14), ~7-9 session.

---

## ALLAPOT

### Tier A: UI Integration & Unified Experience — COMPLETE (session 10)

| Ciklus | Commit      | Tartalom                                                                 |
| ------ | ----------- | ------------------------------------------------------------------------ |
| S1     | `1dff737` | Chat UI: ChatMarkdown bekotes, @tanstack/react-virtual, Cmd+Enter/Escape |
| S2     | `65fc403` | In-app notifications: 4 API endpoint + NotificationBell + dropdown       |
| S3     | `788c1e5` | Quality Dashboard: 7 HARD GATE, 5 KPI card, rubrics tabla, evaluate form |
| S4     | `238ee7f` | Service Catalog: 16 service card, search+filter, pipeline integration    |
| S5     | `47992bc` | Design tokens @theme, ErrorBoundary, aria-label accessibility            |
| S6     | `b38b156` | CubixViewer MUI→Tailwind, 0 @mui import, LegacyPage wrapper torolve     |

### Tier B (eddig): S7 — COMPLETE (session 11)

| Ciklus | Commit      | Tartalom                                                                 |
| ------ | ----------- | ------------------------------------------------------------------------ |
| S7     | `6e46fed` | Langfuse valos integracio (tracing, cost, health) |
| S7+    | `08c6bfa` | Langfuse v4 prompt sync: push/fetch/diff (9 prompt szinkronizalva) |

### Session 11 reszletes deliverables:

**Langfuse tracing (valos, tesztelt a cloud dashboardon):**
- `src/aiflow/observability/tracing.py`: LangfuseTracer stub → real Langfuse v4 SDK
  - `start_observation()` (trace), `start_observation()` child (span), `create_score()`, generation
  - `@trace_llm_call` decorator: auto-traces async functions
  - `check_health()` → `/health` endpoint-ben Langfuse status
  - App startup/shutdown lifecycle (`app.py` lifespan)
- `src/aiflow/pipeline/runner.py`: Langfuse trace per pipeline run, span per step, cost_records persist
- 24 uj unit teszt (test_langfuse_tracing.py)

**Langfuse prompt management (valos, tesztelt):**
- `src/aiflow/prompts/sync.py`: `_push_to_langfuse` → `create_prompt(type=chat)`, `_fetch_remote` → `get_prompt()`
- `src/aiflow/prompts/manager.py`: `_fetch_from_langfuse` → `get_prompt()` → PromptDefinition reconstruction
- 9 prompt sikeresen push-olva Langfuse cloud-ba (email-intent/classifier, aszf-rag/*, process-doc/extractor)
- `_compute_diff`: real system/user/config osszehasonlitas

**Fontos Langfuse v4 API tanulsagok (az alabbi NEM mukodik v4-ben):**
- ~~`client.trace()`~~ → `client.start_observation(trace_context={"trace_id": hex32})`
- ~~`client.score()`~~ → `client.create_score(trace_id=..., name=..., value=...)`
- ~~`trace.span()`~~ → `root_span.start_observation(name=..., as_type="span")`
- ~~`trace.generation()`~~ → `root_span.start_observation(as_type="generation", model=...)`
- Trace ID: `uuid4().hex` (32 hex chars, NO dashes!)
- ChatPromptClient: `.name`, `.version`, `.config`, `.prompt` direkt attributumok (NEM `.prompt.name`)

### Infrastruktura (valtozatlan v1.2.0-bol)

- **26 service**, 18 pipeline adapter, 6 pipeline template
- **~159 API endpoint** (155 + 4 uj notification), **24 router**
- **45 DB tabla**, 29 Alembic migracio
- **332 pipeline unit test** PASS, **74 observability teszt** PASS, **45 prompt teszt** PASS
- **Docker:** PostgreSQL 5433, Redis 6379
- **Auth:** admin@bestix.hu / admin (username mezo!)
- **Langfuse:** ENABLED, connected, 9 prompt szinkronizalva

### Post-Sprint TODO (57_PRODUCTION_READY_SPRINT.md Section 8)

- **P1 (HIGH):** Pipelines oldal templates szekció — `/templates/list` endpoint mukodik de UI nem hivja
- **P2 (MEDIUM):** `/api/v1/pipelines/templates` route conflict (UUID parse hiba)
- ~~**P3 (DONE)**:~~ Langfuse Prompt Management — megcsinalva session 11-ben
- **P4 (HIGH):** Placeholder/Stub Audit — teljes codebase stub felmerés (PrometheusMetrics, SLAMonitor, stb.)

---

## KOVETKEZO FELADAT: S8 (Promptfoo 6 Skill Config + CI/CD)

### Cel

Minden 6 skill-hez Promptfoo config YAML kell (5 uj + 1 meglevo aszf_rag_chat), plusz nightly CI/CD job.

### Lepesek

```
1. TERVEZES:
   - Olvasd el 57_PRODUCTION_READY_SPRINT.md S8 szekciojat (sor ~316)
   - Nezd meg a meglevo aszf_rag_chat promptfooconfig.yaml-t referenciakent
   - Nezd meg a skills/*/prompts/*.yaml fajlokat (prompt formatumok)

2. FEJLESZTES:
   a) skills/email_intent_processor/tests/promptfooconfig.yaml
      - 10+ test case: email subject+body → intent (invoice, complaint, inquiry, ...)
      - Provider: openai:gpt-4o-mini
      - Assertions: llm-rubric (intent_correctness)
   b) skills/process_documentation/tests/promptfooconfig.yaml
      - 10+ test case: process description → Mermaid/BPMN output
      - Assertions: contains "graph"/"flowchart", valid Mermaid syntax
   c) skills/invoice_processor/tests/promptfooconfig.yaml
      - 10+ test case: szamla PDF text → extracted fields
      - Assertions: extraction_accuracy rubric, field presence
   d) skills/cubix_course_capture/tests/promptfooconfig.yaml
      - 5+ test case: transcript → structured course outline
   e) skills/qbpp_test_automation/tests/promptfooconfig.yaml
      - 5+ test case: test scenario → Robot Framework script
   f) .github/workflows/nightly-eval.yml:
      - Cron: 02:00 UTC
      - Run: npx promptfoo eval -c skills/*/tests/promptfooconfig.yaml
      - Check: min 90% pass rate

3. TESZTELES:
   - npx promptfoo eval -c skills/aszf_rag_chat/tests/promptfooconfig.yaml → 90%+
   - Legalabb 1 uj config valos futtatasa
   - YAML szintaktika validacio mindegyikre

4. DOKUMENTALAS:
   - git commit
   - 57_PRODUCTION_READY_SPRINT.md: S8 = DONE

5. KOVETKEZO: S9 (E2E Playwright test suite)
```

---

## TIER B VEGREHAJTASI TERV (S7-S10)

```
S7:  Langfuse valos integracio ────── DONE ✓ (+ prompt sync bonus)
S8:  Promptfoo 6 skill config ─────── KOVETKEZO ← ITT VAGYUNK
S9:  E2E Playwright test suite ────── 10+ teszt
S10: CI/CD regresszios pipeline ───── GitHub Actions
```

---

## KOTELEZOEN BETARTANDO SZABALYOK

### Session 11 tanulsagai:

1. **Langfuse v4 API** — A v2/v3 doksi NEM ervenyes! Lasd "Fontos Langfuse v4 API tanulsagok" fent.
2. **Stale bytecache** — Ha a szerver nem veszi eszre a valtozast, `rm -f src/aiflow/**/__pycache__/*.pyc` + restart.
   Port 8102-n levo process killelese: `PID=$(netstat -aon | grep ':8102' | grep LISTEN | awk '{print $NF}') && taskkill //PID $PID //F`
3. **@mui ZERO** — Minden MUI import eltavolitva (S6). NE adjunk hozza ujat!
4. **Langfuse keys** — `.env`-ben `AIFLOW_LANGFUSE__HOST` (NEM `BASE_URL`), `AIFLOW_LANGFUSE__ENABLED=true`

---

## SZERVER INDITAS

```bash
docker compose up -d db redis
.venv\Scripts\python.exe -B -m uvicorn aiflow.api.app:create_app --factory --port 8102
cd aiflow-admin && npm run dev
```

---

## TELJES VEGREHAJTASI TERV (v1.2.1)

```
S1-S6:  Tier A — UI Integracio ────────── DONE (session 10)
S7:     Langfuse integracio ───────────── DONE (session 11) + prompt sync
S8:     Promptfoo 6 skill ─────────────── KOVETKEZO
S9:     E2E Playwright suite ──────────── 10+ teszt
S10:    CI/CD pipeline ────────────────── GitHub Actions
S11:    Free text + intent schema ─────── uj funkciok
S12:    SLA + cost estimation ─────────── APScheduler + tiktoken
S13:    Integralt E2E teszteles ────────── full journey-k
S14:    Vegleges polish ───────────────── PWA, a11y, v1.2.1 tag
```
