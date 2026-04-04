# AIFlow v1.2.1 — Session 13 Prompt (S10 CI/CD + S11 Free Text, Tier B+C)

> **Datum:** 2026-04-04 (session 12 utan)
> **Elozo session:** S8 + S9 DONE + Quality external tools bonus (session 12)
> **Branch:** feature/v1.2.1-production-ready (20 commit, main-bol branched)
> **Port:** API 8102, Frontend 5174 (Vite proxy → 8102)
> **Utolso commit:** `89aa76a` docs: S9 commit hash updated

---

## AKTUALIS TERV

**`01_PLAN/57_PRODUCTION_READY_SPRINT.md`** — 14 ciklus (S1-S14), ~7-9 session.

---

## ALLAPOT

### Tier A: UI Integration & Unified Experience — COMPLETE (session 10)

| Ciklus | Commit    | Tartalom                                                                 |
| ------ | --------- | ------------------------------------------------------------------------ |
| S1     | `1dff737` | Chat UI: ChatMarkdown bekotes, @tanstack/react-virtual, Cmd+Enter/Escape |
| S2     | `65fc403` | In-app notifications: 4 API endpoint + NotificationBell + dropdown       |
| S3     | `788c1e5` | Quality Dashboard: 7 HARD GATE, 5 KPI card, rubrics tabla, evaluate form |
| S4     | `238ee7f` | Service Catalog: 16 service card, search+filter, pipeline integration    |
| S5     | `47992bc` | Design tokens @theme, ErrorBoundary, aria-label accessibility            |
| S6     | `b38b156` | CubixViewer MUI→Tailwind, 0 @mui import, LegacyPage wrapper torolve     |

### Tier B: Quality & Observability — COMPLETE (session 11-12)

| Ciklus | Commit    | Tartalom                                                                |
| ------ | --------- | ----------------------------------------------------------------------- |
| S7     | `6e46fed` | Langfuse valos integracio (tracing, cost, health) + prompt sync bonus   |
| S8     | `dfbb8e4` | Promptfoo 6 skill config (51 test case) + nightly-eval.yml CI/CD        |
| S9     | `65dfcdf` | E2E Playwright test suite: 54 teszt, 17 oldal, Page Object Model        |
| S8+    | `8d112fd` | Quality dashboard: Promptfoo + Langfuse external tool linkek            |

### Session 12 reszletes deliverables:

**S8 — Promptfoo skill configs:**
- 5 uj promptfooconfig.yaml (email_intent 12, process_doc 10, invoice 10, cubix 6, qbpp 6)
- Meglevo aszf_rag_chat 7 = **51 test case osszesen**
- `.github/workflows/nightly-eval.yml`: cron 02:00 UTC, matrix 6 skill, summary job
- Valos tesztelesi eredmenyek: email 91.67%, process_doc 100%, invoice 100%, cubix 100%, qbpp 100%
- **Fontos tanulsag:** Promptfoo JS assertions-ben `const` NEM hasznalhato — csak single expression
- **Fontos tanulsag:** Invoice prompt-ban explicit ISO 4217 currency kodokat kell kerni (HUF, EUR, USD, GBP), kulonben symbolokat ad vissza (€, $, £)

**S9 — E2E Playwright test suite:**
- `tests/e2e/conftest.py`: `authenticated_page` fixture (login → wait for nav), `navigate_to()`, `assert_no_console_errors()`
- `tests/e2e/pages/`: Page Object Model (BasePage, LoginPage, DashboardPage)
- `tests/e2e/test_smoke.py`: 40 teszt — Login (4), SmokeAllPages (34 = 17 page × 2 check), Sidebar (2)
- `tests/e2e/test_quality.py`: 4 teszt — page loads, content/error, external tools, links
- `tests/e2e/test_documents.py`: 3 teszt — table, action area, source indicator
- `tests/e2e/test_pipelines.py`: 3 teszt — pipelines loads, services catalog, list/empty
- `tests/e2e/test_notifications.py`: 2 teszt — bell icon, dropdown toggle
- `tests/e2e/test_i18n.py`: 2 teszt — Magyar/English locale toggle
- **54/54 PASS** (146s, Chromium headless)
- **Fontos tanulsag:** Hash router URL-eket `BASE_URL + "/#" + path` formaban kell megadni
- **Fontos tanulsag:** Login wait-nal `page.locator("nav").wait_for(state="visible")` a legmegbizhatobb (nem `wait_for_url` vagy `wait_for_function`)
- **Fontos tanulsag:** LOCALES = `[{code: "hu", name: "Magyar"}, {code: "en", name: "English"}]` — NEM "HU"/"EN"
- **pytest-playwright** installalva a `.venv`-ben (`uv pip install pytest-playwright`)

**Bonus — Quality dashboard external tools:**
- Promptfoo (localhost:15500) + Langfuse (cloud.langfuse.com) link kartyak a `/quality` oldal aljan
- Langfuse URL dinamikusan a `/health` endpoint-bol (fallback: cloud.langfuse.com)
- i18n HU/EN, dark mode, hover states, `target="_blank"`

### Infrastruktura (valtozatlan v1.2.0-bol)

- **26 service**, 18 pipeline adapter, 6 pipeline template
- **~159 API endpoint** (155 + 4 uj notification), **24 router**
- **45 DB tabla**, 29 Alembic migracio
- **332 pipeline unit test** PASS, **74 observability teszt** PASS, **45 prompt teszt** PASS
- **51 Promptfoo test case** (6 skill), **54 E2E Playwright teszt** (17 oldal)
- **Docker:** PostgreSQL 5433, Redis 6379
- **Auth:** admin@bestix.hu / admin (username mezo!)
- **Langfuse:** ENABLED, connected, 9 prompt szinkronizalva
- **Promptfoo viewer:** `npx promptfoo view` → localhost:15500

### Meglevo CI/CD fajlok (`.github/workflows/`):

| Fajl | Trigger | Mit csinal |
|------|---------|------------|
| `ci.yml` | push/PR to main | ruff lint + unit tests + ~~Next.js build~~ (ELAVULT — aiflow-ui torolve!) |
| `ci-framework.yml` | ? | ? (valoszinuleg framework specifikus) |
| `ci-prompts.yml` | ? | ? (prompt valtozasokra) |
| `ci-skill.yml` | ? | ? (skill valtozasokra) |
| `deploy-prod.yml` | ? | Production deploy |
| `deploy-staging.yml` | ? | Staging deploy |
| `nightly-eval.yml` | cron 02:00 UTC | Promptfoo eval 6 skill (S8-ban letrehozva) |
| `prompt-eval.yml` | PR (skills/*/prompts/**) | Promptfoo eval + pass rate check |

**FONTOS:** `ci.yml` ELAVULT — meg a regi `aiflow-ui` (Next.js) build-et tartalmazza, ami mar torolve van! Ezt S10-ben kell javitani.

### Post-Sprint TODO (57_PRODUCTION_READY_SPRINT.md Section 8)

- **P1 (HIGH):** Pipelines oldal templates szekció — `/templates/list` endpoint mukodik de UI nem hivja
- **P2 (MEDIUM):** `/api/v1/pipelines/templates` route conflict (UUID parse hiba)
- ~~**P3 (DONE)**:~~ Langfuse Prompt Management — megcsinalva S7-ben
- **P4 (HIGH):** Placeholder/Stub Audit — teljes codebase stub felmerés

---

## KOVETKEZO FELADATOK: S10 (CI/CD) + S11 (Free Text + Intent Schema)

### S10: CI/CD Regresszios Pipeline

**Cel:** Modernizalt GitHub Actions CI/CD — frissitett `ci.yml` (aiflow-admin Vite build, nem Next.js!) + nightly regresszio + smoke test bovites.

### Lepesek

```
1. TERVEZES:
   - Olvasd el 57_PRODUCTION_READY_SPRINT.md S10 szekciojat (sor ~410)
   - Olvasd el a meglevo ci.yml-t (ELAVULT Next.js referencia!)
   - Nezd meg scripts/smoke_test.sh jelenlegi allapotat

2. FEJLESZTES:
   a) .github/workflows/ci.yml FRISSITES (fo CI pipeline):
      - Torolni: nextjs-build job (aiflow-ui mar nem letezik!)
      - Hozzaadni: aiflow-admin Vite build job:
        - cd aiflow-admin && npm ci && npx tsc --noEmit && npm run build
      - Python lint: ruff check + ruff format --check
      - Unit tests: pytest tests/unit/ -q --cov=aiflow --junitxml
      - Coverage gate: >= 80%
   b) .github/workflows/nightly-regression.yml (UJ):
      - Cron: 03:00 UTC (nightly-eval utan!)
      - Jobs: unit tests + integration tests (Docker) + E2E (Playwright)
      - Summary report: GitHub Step Summary
      - Artifact upload: test results, coverage
   c) scripts/smoke_test.sh BOVITES:
      - Uj endpointok: /quality/overview, /notifications/in-app, /pipelines/templates/list
      - Health endpoint: /api/v1/health (nem /health!)
   d) tests/regression_matrix.yaml frissites (ha letezik)

3. TESZTELES:
   - YAML szintaktika validacio minden workflow-ra
   - smoke_test.sh lokal futatas → PASS
   - ci.yml dryrun: ruff + tsc + pytest lokalis futatas

4. DOKUMENTALAS:
   - git commit
   - 57_PRODUCTION_READY_SPRINT.md: S10 = DONE
```

### S11: Free Text Extraction + Intent Schema CRUD

**Cel:** Ket uj backend feature — free text extraction API es intent schema CRUD endpointok.

### Lepesek

```
1. TERVEZES:
   - Olvasd el 57_PRODUCTION_READY_SPRINT.md S11 szekciojat (sor ~457)
   - Nezd meg a meglevo document_extractor service-t
   - Nezd meg a meglevo email_intent_processor schemas/ strukturat

2. FEJLESZTES:
   a) Free text extraction:
      - src/aiflow/services/document_extractor/ bovites: free_text.py
      - Prompt YAML: prompts/extraction/free_text.yaml (Jinja2)
      - API: POST /api/v1/documents/{id}/extract-free
      - Pipeline adapter: extract_free_text
   b) Intent schema CRUD:
      - Uj router: src/aiflow/api/v1/intent_schemas.py
      - GET/POST/PUT/DELETE /api/v1/intent-schemas
      - POST /api/v1/intent-schemas/{id}/test
   c) Unit tesztek: min 5 per modul

3. TESZTELES:
   - curl: POST /documents/{id}/extract-free → valos result
   - curl: CRUD /intent-schemas → 200 OK, source=backend
   - pytest tests/unit/ -q → PASS

4. DOKUMENTALAS:
   - git commit
   - 57_PRODUCTION_READY_SPRINT.md: S11 = DONE
```

---

## TIER B+C VEGREHAJTASI TERV (S7-S12)

```
S7:  Langfuse valos integracio ────── DONE ✓ (session 11)
S8:  Promptfoo 6 skill config ─────── DONE ✓ (session 12)
S9:  E2E Playwright test suite ────── DONE ✓ (session 12)
S10: CI/CD regresszios pipeline ───── KOVETKEZO ← ITT VAGYUNK
S11: Free text + intent schema ────── KOVETKEZO (ha S10 gyorsan megy)
S12: SLA + cost estimation ────────── TODO
```

---

## KOTELEZOEN BETARTANDO SZABALYOK

### Session 12 tanulsagai:

1. **Promptfoo JS assertions** — `const` NEM hasznalhato! Csak single expression: `JSON.parse(output).field === 'value'`
2. **Invoice prompt currency** — Explicit ISO 4217 kodokat kell kerni a promptban (HUF, EUR, USD, GBP), kulonben a model symbolokat ad (€, $, £)
3. **Playwright login wait** — `page.locator("nav").wait_for(state="visible")` a legmegbizhatobb minta hash router-hez
4. **Locale buttons** — "Magyar" es "English" a szoveg, NEM "HU"/"EN" (LOCALES config)
5. **Quality page loading** — Ha API lassu, a Quality oldal loading/error state-ben marad. Tesztek legyenek resilient.
6. **@mui ZERO** — Minden MUI import eltavolitva (S6). NE adjunk hozza ujat!
7. **ci.yml ELAVULT** — Meg Next.js (aiflow-ui) build-et tartalmazza, ami torolve van! S10-ben KELL frissiteni.

### Elozo session tanulsagai:

8. **Langfuse v4 API** — A v2/v3 doksi NEM ervenyes! `client.start_observation()`, `client.create_score()`, trace ID: `uuid4().hex` (32 hex, NO dashes)
9. **Stale bytecache** — Ha a szerver nem veszi eszre a valtozast: `rm -f src/aiflow/**/__pycache__/*.pyc` + restart
10. **Langfuse keys** — `.env`-ben `AIFLOW_LANGFUSE__HOST` (NEM `BASE_URL`), `AIFLOW_LANGFUSE__ENABLED=true`

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
S7:     Langfuse integracio ───────────── DONE (session 11)
S8:     Promptfoo 6 skill ─────────────── DONE (session 12)
S9:     E2E Playwright suite ──────────── DONE (session 12)
S10:    CI/CD pipeline ────────────────── KOVETKEZO ← ITT VAGYUNK
S11:    Free text + intent schema ─────── KOVETKEZO
S12:    SLA + cost estimation ─────────── TODO
S13:    Integralt E2E teszteles ────────── TODO
S14:    Vegleges polish ───────────────── PWA, a11y, v1.2.1 tag
```
