# AIFlow v1.2.1 — Production Ready Sprint

> **Szulo terv:** `48_ORCHESTRABLE_SERVICE_ARCHITECTURE.md` + v1.2.0 audit eredmenyek
> **Elozmeny:** v1.2.0 COMPLETE (C0-C20, 2026-04-04) — architektura es service-ek KESZ
> **Cel:** A megepitett szolgaltatasok valos hasznalhatova tetele — integracio, polish, teszteles, UI teljeskoruseg

---

## 0. Problemadefinicio

A v1.2.0 megepitette a **26 service-t, 18 adaptert, 6 pipeline template-et, 155 API endpointot**,
de a kovetkezo tersegek **nem keszek produkciohoz:**

| Kategoria | Problema | Hatas |
|-----------|---------|-------|
| **UI integracio** | ChatMarkdown megvan de nem bekotott, Quality oldal nincs, in-app notifications UI nincs | Felhasznalok nem latjak az eredmenyeket |
| **Observability** | Langfuse 100% stub, rubric scores nem logolva | Koltseg es minoseg nem kovetheto |
| **Quality assurance** | 5/6 skill Promptfoo config hianyzik, E2E tesztek uresek | Minoseg nem merheto, regresszio nem detektalhato |
| **Hianyzo funkciok** | Free text extraction, SLA eszkalacio, intent schema CRUD | Use case-ek nem teljesek |
| **Design rendszer** | Design tokens nem hasznalva, nem minden oldal migralva | Inkonzisztens UI |

---

## 1. Fejlesztesi Ciklus Modell (valtozatlan)

Minden ciklus (S1-S12) ugyanazt a 6 lepest koveti mint v1.2.0:

```
TERVEZES → FEJLESZTES → TESZTELES → DOKUMENTALAS → FINOMHANGOLAS → SESSION PROMPT
```

### STRICT: Ciklus lezaras KOTELEZO lepesek (session 9 tanulsag!)
1. `pytest tests/unit/ -q` — PASS
2. `ruff check` uj fajlokon — CLEAN
3. `cd aiflow-admin && npx tsc --noEmit` — 0 error
4. **56_EXECUTION_PLAN.md** frissites (progress tabla, output szekciok)
5. **01_PLAN/CLAUDE.md** szamok frissites
6. **Root CLAUDE.md** infrastruktura szamok frissites
7. `python -c "import pypdfium2; import docling; import aiosmtplib"` — dep check

---

## 2. Branch Strategia

```
main (v1.2.0 — stabil)
  │
  └── feature/v1.2.1-production-ready
        ├── S1-S4: UI & Integracio
        ├── S5-S8: Quality & Observability
        ├── S9-S10: Hianyzo funkciok
        ├── S11-S12: E2E & Polish
        └── merge to main → tag v1.2.1
```

---

## 3. Vegrehajtasi Sorrend (12 ciklus, ~6-8 session)

### Tier A: UI Integracio & Polish (S1-S4)

| Ciklus | Tartalom | Teszt | Becsult meret |
|--------|----------|-------|---------------|
| **S1** | Chat UI integracio: ChatMarkdown → ChatPanel, virtual scroll | Playwright: markdown render, code block, copy | ~200 loc |
| **S2** | In-app notifications: API endpoints + TopBar bell icon + dropdown | curl + Playwright: bell, unread count, mark read | ~400 loc |
| **S3** | Quality dashboard UI: /quality oldal + router + sidebar | Playwright: KPI cards, rubric list, cost chart | ~350 loc |
| **S4** | Design system teljeskoruseg: tokens → Tailwind config, komponens audit | tsc + vizualis audit, dark mode | ~300 loc |

#### S1 Reszletes: Chat UI Integracio
```
FEJLESZTES:
  a) ChatPanel/MessageBubble.tsx: import ChatMarkdown, replace plain text render
  b) Hosszu beszelgetesekhez: @tanstack/react-virtual (npm install)
  c) Keyboard shortcut: Cmd+Enter → submit, Escape → clear
  d) Mobile responsive: bottom-fixed input, drawer sidebar < 768px

TESZTELES:
  - Playwright: kuldd el "**bold** and `code`" → rendereles helyes?
  - Playwright: ``` code block ``` → CodeBlock komponens jelenik meg?
  - Playwright: 50+ uzenet → smooth scroll?
  - Playwright: 375px viewport → responsive?

GATE: tsc --noEmit PASS, 0 console error, markdown renderel
```

#### S2 Reszletes: In-app Notifications
```
FEJLESZTES:
  a) API endpoints (uj router VAGY notifications.py bovites):
     - GET /api/v1/notifications/in-app — lista (user_id szures, unread first)
     - POST /api/v1/notifications/in-app/{id}/read — mark as read
     - POST /api/v1/notifications/in-app/read-all — mark all read
     - GET /api/v1/notifications/in-app/unread-count — szam
  b) TopBar.tsx: bell icon (@untitledui/icons Bell01)
     - Unread count badge (piros kor szammal)
     - Click → dropdown panel (legutolso 10 notification)
     - "Mark all read" gomb
     - Click notification → navigate to link
  c) Pipeline runner integracio: notify in-app on pipeline complete/fail

TESZTELES:
  - curl: POST /send channel=in_app → GET /in-app → megjelenik
  - curl: POST /{id}/read → GET /unread-count csokkent
  - Playwright: bell icon lathato, kattintas → dropdown, count frissul

GATE: API 200 OK source=backend, bell icon mukodik, unread count helyes
```

#### S3 Reszletes: Quality Dashboard
```
ELOFELTETEL: 7 HARD GATE UI pipeline! Journey → API → Figma → UI → E2E
  GATE 1: /ui-journey → 01_PLAN/QUALITY_DASHBOARD_JOURNEY.md
  GATE 2-3: curl /quality/overview, /quality/rubrics → 200 OK (MAR LETEZIK!)
  GATE 4: /ui-design → PAGE_SPECS.md frissites
  GATE 5: Quality.tsx implementacio
  GATE 6: Playwright E2E
  GATE 7: PAGE_SPECS.md konzisztencia

FEJLESZTES:
  a) Quality.tsx oldal:
     - KPI cards: total evaluations, avg score, pass rate, cost today/month
     - Rubric lista tabla (DataTable): nev, leiras, utolso score, trend
     - Cost chart (recharts BarChart): napi/heti koltseg service-enkent
     - Evaluate form: actual text + rubric valasztas → POST /evaluate → score
  b) router.tsx: /quality route hozzaadas
  c) Sidebar.tsx: Quality menu item (Operations csoport)
  d) i18n: hu.json + en.json quality kulcsok

TESZTELES:
  - Playwright: /quality betolt, KPI cards adatot mutatnak
  - Playwright: rubric tablazat 6 sort mutat
  - Playwright: evaluate form → score megjelenik

GATE: 7 HARD GATE MIND PASS
```

#### S4 Reszletes: Design System Teljeskoruseg
```
FEJLESZTES:
  a) tailwind.config.ts: design tokens mapping
     ```ts
     theme: {
       extend: {
         spacing: {
           'aiflow-xs': 'var(--aiflow-spacing-xs)',
           'aiflow-sm': 'var(--aiflow-spacing-sm)',
           // ...
         },
         borderRadius: {
           'aiflow-sm': 'var(--aiflow-radius-sm)',
           // ...
         },
       },
     },
     ```
  b) Komponens audit — MINDEN pages-new/*.tsx atnezes:
     - Hardcoded px/rem ertekek → design token valtozok
     - Inkonzisztens szinek → brand/semantic token
     - Hianyzó dark mode variansok → dark: prefix
  c) Accessibility pass:
     - aria-label minden icon-only gombon
     - role attributumok formokhoz
     - Focus indicator (outline) konzisztens
  d) Error boundary komponens: ErrorBoundary.tsx + integration

TESZTELES:
  - tsc --noEmit: 0 error
  - Vizualis audit: light + dark mode MINDEN oldalon
  - Accessibility: Tab navigacio fo oldalakon
  - Mobile: 375px, 768px, 1024px breakpointok

GATE: konzisztens design, dark mode mukodik, 0 accessibility hiba
```

---

### Tier B: Quality & Observability (S5-S8)

| Ciklus | Tartalom | Teszt | Becsult meret |
|--------|----------|-------|---------------|
| **S5** | Langfuse valos integracio: tracing decorator, pipeline cost log | Valos Langfuse dashboard | ~300 loc |
| **S6** | Promptfoo 5 skill config + CI/CD nightly job | npx promptfoo eval → 90%+ | ~500 loc (YAML) |
| **S7** | E2E Playwright test suite: 10+ oldal, reusable Page Objects | pytest-playwright PASS | ~800 loc |
| **S8** | Regresszios automatizacio: L2 API + L3 UI + GitHub Actions nightly | CI/CD pipeline PASS | ~400 loc |

#### S5 Reszletes: Langfuse Valos Integracio
```
FEJLESZTES:
  a) src/aiflow/observability/tracing.py: replace stubs with real Langfuse client
     - Langfuse(public_key, secret_key, host) from settings
     - create_trace() → langfuse.trace()
     - create_span() → trace.span()
     - finish_span/trace → flush
  b) Tracing decorator: @trace_llm_call
     ```python
     @trace_llm_call(name="classifier.classify")
     async def classify(self, text, ...):
         # Automatically logs: input, output, duration, tokens, cost
     ```
  c) Pipeline runner integracio:
     - Minden step futashoz Langfuse span
     - Pipeline run = Langfuse trace
     - Step cost → trace metadata
  d) Rubric scoring → Langfuse score
     - evaluate_rubric() eredmeny → langfuse.score(trace_id, rubric, value)

TESZTELES:
  - .env: LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY beallitva
  - Pipeline futtas → Langfuse dashboard-on megjelenik trace
  - Rubric ertekeles → Langfuse score megjelenik

GATE: valos trace a Langfuse UI-ban, koltseg lathato, 0 hiba
MEGJEGYZES: Ha Langfuse account nincs → stub marad de LOGOL structlog-ba
```

#### S6 Reszletes: Promptfoo 5 Skill Config
```
FEJLESZTES:
  a) skills/email_intent_processor/tests/promptfooconfig.yaml
     - 10+ test case: email subject+body → intent label (invoice, contract, inquiry, ...)
     - Providers: [openai:gpt-4o-mini]
     - Assertions: type=llm-rubric (intent_correctness rubric)
  b) skills/process_documentation/tests/promptfooconfig.yaml
     - 10+ test case: process description → Mermaid/BPMN output
     - Assertions: contains "graph", "flowchart", valid Mermaid syntax
  c) skills/invoice_processor/tests/promptfooconfig.yaml
     - 10+ test case: szamla PDF text → extracted fields (vendor, amount, date)
     - Assertions: extraction_accuracy rubric, field presence
  d) skills/cubix_course_capture/tests/promptfooconfig.yaml
     - 5+ test case: transcript → structured course outline
     - Assertions: completeness rubric
  e) skills/qbpp_test_automation/tests/promptfooconfig.yaml
     - 5+ test case: test scenario → Robot Framework script
     - Assertions: valid RF syntax
  f) .github/workflows/nightly-eval.yml:
     - Cron: 02:00 UTC naponta
     - Run: npx promptfoo eval -c skills/*/tests/promptfooconfig.yaml
     - Check: scripts/check_promptfoo_results.py --min-pass-rate 0.9
     - Notify: Slack webhook on failure

TESZTELES:
  - npx promptfoo eval -c skills/aszf_rag_chat/tests/promptfooconfig.yaml → 90%+
  - npx promptfoo eval -c skills/email_intent_processor/tests/promptfooconfig.yaml → 90%+
  - Osszes config szintaktikailag valid

GATE: 6/6 skill config letezik, mindegyik 90%+ pass rate
```

#### S7 Reszletes: E2E Playwright Test Suite
```
FEJLESZTES:
  a) tests/e2e/conftest.py: Playwright fixtures (browser, page, auth)
  b) tests/e2e/pages/: Page Object Model
     - BasePage(page): navigate(), wait_loaded(), screenshot()
     - LoginPage: login(user, pass)
     - DashboardPage: check_kpis(), check_sidebar()
     - DocumentsPage: upload(file), list(), verify(id)
     - EmailsPage: list_inbox(), list_connectors()
     - RagPage: list_collections(), open(id), ingest(file), query(text)
     - PipelinesPage: list(), detail(id), run(id, input)
     - QualityPage: overview(), evaluate(text, rubric)
     - ReviewsPage: list(), approve(id), reject(id)
  c) tests/e2e/test_smoke.py: 10+ teszt (minden fo oldal betolt, nincs console error)
  d) tests/e2e/test_documents.py: upload → process → verify → list
  e) tests/e2e/test_rag.py: create collection → ingest → query → answer
  f) tests/e2e/test_pipelines.py: template deploy → run → check status
  g) tests/e2e/test_chat.py: send markdown message → render check
  h) tests/e2e/test_notifications.py: bell icon → dropdown → mark read

TESZTELES:
  - pytest tests/e2e/ -v --headed (lokal)
  - MINDEN teszt VALOS backend-del (Docker PostgreSQL + Redis)

GATE: 10+ E2E teszt PASS, 0 console error, osszes fo oldal tesztelve
```

#### S8 Reszletes: CI/CD Regresszios Pipeline
```
FEJLESZTES:
  a) .github/workflows/ci.yml (fo CI pipeline):
     ```yaml
     on: [pull_request]
     jobs:
       lint:
         - ruff check src/
         - cd aiflow-admin && npx tsc --noEmit
       unit-tests:
         - pytest tests/unit/ -q --cov=aiflow
         - coverage >= 80% gate
       integration-tests:
         - docker compose up -d db redis
         - alembic upgrade head
         - pytest tests/integration/ -v
     ```
  b) .github/workflows/nightly-regression.yml:
     ```yaml
     on:
       schedule: [{cron: "0 3 * * *"}]
     jobs:
       l3-regression:
         - pytest tests/unit/ + tests/integration/ + tests/e2e/
         - npx promptfoo eval (all skills)
         - Slack notification on failure
     ```
  c) tests/regression_matrix.yaml frissites: uj fajlok hozzaadasa
  d) scripts/smoke_test.sh bovites: uj endpointok (quality, templates, in-app)

TESZTELES:
  - CI workflow YAML szintaktikailag valid
  - smoke_test.sh lokalis futatas → PASS

GATE: CI/CD YAML-ok leteznek es szintaktikailag helyesek
```

---

### Tier C: Hianyzo Funkciok (S9-S10)

| Ciklus | Tartalom | Teszt | Becsult meret |
|--------|----------|-------|---------------|
| **S9** | Free text extraction + intent schema CRUD API | curl: extract → result, schema CRUD | ~400 loc |
| **S10** | SLA eszkalacio (APScheduler) + pre-execution cost estimation | Integration: SLA trigger, cost estimate | ~350 loc |

#### S9 Reszletes: Free Text Extraction + Intent Schema
```
FEJLESZTES:
  a) src/aiflow/services/document_extractor/free_text.py:
     - extract_free_text(document_text, queries) → list[ExtractionResult]
     - Prompt: "Given the document, answer these queries: {queries}"
     - Jinja2 template: prompts/extraction/free_text.yaml
  b) API endpoints (documents.py bovites):
     - POST /api/v1/documents/{id}/extract-free — body: {queries: [...]}
     - Response: {results: [{query, answer, confidence, source_span}]}
  c) Intent schema CRUD (uj router: intent_schemas.py):
     - GET /api/v1/intent-schemas — lista
     - POST /api/v1/intent-schemas — letrehozas (YAML body)
     - PUT /api/v1/intent-schemas/{id} — frissites
     - DELETE /api/v1/intent-schemas/{id} — torles
     - POST /api/v1/intent-schemas/{id}/test — teszt (text → classification)
  d) Pipeline adapter: document_extractor/extract_free_text

TESZTELES:
  - curl: POST /documents/{id}/extract-free → valos extrakcio
  - curl: CRUD /intent-schemas → source=backend
  - Unit: free_text prompt + parser

GATE: valos extrakcio mukodik, CRUD endpointok 200 OK
```

#### S10 Reszletes: SLA Eszkalacio + Cost Estimation
```
FEJLESZTES:
  a) src/aiflow/services/human_review/service.py bovites:
     - escalate(review_id, reason) → EscalationResult
     - check_sla_deadlines() → list[OverdueReview]
     - Konfiguralhato SLA: review_sla_hours (default: 24)
  b) APScheduler job: minden 15 percben check_sla_deadlines()
     - Lejart review → escalate() → notification kuld (email + in_app)
     - src/aiflow/execution/scheduler.py bovites
  c) Pre-execution cost estimation (quality/service.py bovites):
     - estimate_pipeline_cost() → tokenizerrel szamol (tiktoken)
     - API: POST /api/v1/pipelines/{id}/estimate-cost → {estimated_cost_usd, per_step}
  d) Budget alert integracio:
     - Ha becsult koltseg > team budget 80% → warning notification
     - Ha > 100% → block execution

TESZTELES:
  - Integration: create review → varj SLA lejarat → escalation tortent?
  - curl: POST /pipelines/{id}/estimate-cost → valos becslest ad
  - Unit: tiktoken token szamolas helyes

GATE: SLA eszkalacio mukodik, cost estimation +-20% pontos
```

---

### Tier D: Veglegesites & Teljeskoruseg (S11-S12)

| Ciklus | Tartalom | Teszt | Becsult meret |
|--------|----------|-------|---------------|
| **S11** | UI teljeskoruseg: MUI→Untitled UI migracio MINDEN oldalon | Playwright: minden oldal renderel, dark mode | ~600 loc |
| **S12** | Vegleges polish: PWA teszt, accessibility audit, dokumentacio, v1.2.1 tag | Teljes L4 regresszio | ~300 loc |

#### S11 Reszletes: UI Teljeskoruseg
```
FEJLESZTES:
  a) Megmaradt MUI referenciák eltavolitasa:
     - CubixViewer.tsx: MUI → Untitled UI + Tailwind
     - Barmely components/ (regi) MUI import → components-new/ vagy Tailwind
  b) Minden pages-new/*.tsx audit:
     - Loading skeleton MINDEN oldalon
     - Error state retry gombbal
     - Empty state uzenettel
     - i18n: MINDEN string translate()-vel
     - Dark mode: MINDEN szin dark: prefix-szel
  c) Responsive audit:
     - 375px (mobil), 768px (tablet), 1024px+ (desktop)
     - Sidebar collapse < 768px
     - DataTable horizontal scroll < 768px
  d) Custom komponensek:
     - JsonViewer.tsx: fa nezetű JSON megjelenitoCollapsible
     - KeyValueList.tsx: key-value par lista
     - PipelineYamlEditor.tsx: textarea + syntax highlight

TESZTELES:
  - Playwright: MINDEN oldal betolt (20 route), 0 console error
  - Playwright: dark mode toggle → MINDEN szin valtozik
  - Playwright: 375px viewport → responsive layout
  - tsc --noEmit: 0 error

GATE: 0 MUI import, 0 console error, dark mode PASS, responsive PASS
```

#### S12 Reszletes: Vegleges Polish + v1.2.1 Tag
```
FEJLESZTES:
  a) PWA teszteles:
     - Service worker regisztracio ellenorzes
     - Offline: cached assets betoltodnek
     - Manifest: installable (Chrome dev tools)
  b) Accessibility audit:
     - WAVE tool vagy Lighthouse audit
     - WCAG AA szintu kontraszt
     - Keyboard navigacio MINDEN oldalon
  c) Dokumentacio frissites:
     - CLAUDE.md vegleges szamok
     - 01_PLAN/57_PRODUCTION_READY_SPRINT.md: progress tabla frissites
     - README.md frissites (ha van)
  d) Vegleges regresszio:
     - pytest tests/unit/ → ALL PASS
     - pytest tests/e2e/ → ALL PASS
     - npx promptfoo eval → 90%+
     - ruff check → new files CLEAN
     - tsc --noEmit → 0 error
  e) Version bump + tag:
     - pyproject.toml version → 1.2.1
     - git tag v1.2.1

TESZTELES:
  - Teljes L4 regresszio (unit + integration + E2E + Promptfoo)
  - PWA install teszt (Chrome)
  - Accessibility Lighthouse score ≥ 90

GATE: MINDEN teszt PASS, PWA installable, v1.2.1 tag
```

---

## 4. Sikerkriteriumok (v1.2.1 DONE feltetel)

| # | Kriterium | Mertek |
|---|-----------|--------|
| 1 | Chat UI markdown rendereles | Playwright: bold, code, list → helyes |
| 2 | In-app notifications | Bell icon + unread count + mark read mukodik |
| 3 | Quality dashboard | /quality oldal: KPI cards, rubric tabla, evaluate form |
| 4 | Design tokens hasznalva | tailwind.config.ts-ben mappelve, 0 hardcoded ertek |
| 5 | Langfuse traces | Pipeline run megjelenik Langfuse dashboard-on |
| 6 | Promptfoo 6/6 skill | Minden config 90%+ pass rate |
| 7 | E2E tesztek | 10+ Playwright teszt PASS, 0 console error |
| 8 | CI/CD pipeline | GitHub Actions: lint + test + coverage + nightly |
| 9 | Free text extraction | POST /extract-free → valos eredmeny |
| 10 | SLA eszkalacio | Lejart review → automatikus notification |
| 11 | UI teljeskoruseg | 0 MUI import, dark mode, responsive, i18n |
| 12 | PWA | Installable, service worker registered |
| 13 | Accessibility | Lighthouse ≥ 90, keyboard nav, aria-labels |
| 14 | v1.2.1 tag | Squash merge main-re, clean history |

---

## 5. Kockazatok

| Kockazat | Valoszinuseg | Hatas | Megoldas |
|----------|-------------|-------|---------|
| Langfuse API kulcs nincs | Kozep | Kozep | Stub marad, structlog-ba logol |
| Promptfoo LLM koltseg | Alacsony | Alacsony | gpt-4o-mini ($0.15/1M token) |
| MUI eltavolitas torik oldalakat | Kozep | Kozep | Oldalankent, tsc + Playwright ellenorzes |
| E2E tesztek instabilak | Kozep | Kozep | Retry + explicit wait-ek |
| OneDrive .venv locking | Magas | Alacsony | UV_LINK_MODE=copy, dep check |

---

## 6. Idovonal

```
S1-S4:   UI & Integracio ──────── 2 session
S5-S8:   Quality & Observability ─ 2-3 session
S9-S10:  Hianyzo funkciok ──────── 1 session
S11-S12: Veglegesites ──────────── 1-2 session
                                   ──────────
                                   ~6-8 session osszesen
```

---

## 7. Progress Tracking

## Progress (utolso frissites: —)

| Ciklus | Tartalom | Allapot | Datum | Commit |
|--------|----------|---------|-------|--------|
| S1 | Chat UI integracio | TODO | — | — |
| S2 | In-app notifications | TODO | — | — |
| S3 | Quality dashboard UI | TODO | — | — |
| S4 | Design system teljeskoruseg | TODO | — | — |
| S5 | Langfuse valos integracio | TODO | — | — |
| S6 | Promptfoo 5 skill config | TODO | — | — |
| S7 | E2E Playwright test suite | TODO | — | — |
| S8 | CI/CD regresszios pipeline | TODO | — | — |
| S9 | Free text extraction + intent schema | TODO | — | — |
| S10 | SLA eszkalacio + cost estimation | TODO | — | — |
| S11 | UI teljeskoruseg | TODO | — | — |
| S12 | Vegleges polish + v1.2.1 tag | TODO | — | — |
