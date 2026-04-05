# AIFlow v1.2.1 — Session 11 Prompt (S7 Langfuse — Tier B Quality & Observability Start)

> **Datum:** 2026-04-04 (session 10 utan)
> **Elozo session:** S1-S6 DONE (Tier A: UI Integration & Unified Experience COMPLETE)
> **Branch:** feature/v1.2.1-production-ready (7 commit, main-bol branched)
> **Port:** API 8102, Frontend 5174 (Vite proxy → 8102)
> **Utolso commit:** `06b60fa` docs: update S6 commit hash + post-sprint TODO

---

## AKTUALIS TERV

**`01_PLAN/57_PRODUCTION_READY_SPRINT.md`** — 14 ciklus (S1-S14), ~7-9 session.

---

## ALLAPOT

### Tier A: UI Integration & Unified Experience — COMPLETE (session 10)

| Ciklus | Commit | Tartalom |
|--------|--------|----------|
| S1 | `1dff737` | Chat UI: ChatMarkdown bekotes, @tanstack/react-virtual, Cmd+Enter/Escape |
| S2 | `65fc403` | In-app notifications: 4 API endpoint + NotificationBell + dropdown |
| S3 | `788c1e5` | Quality Dashboard: 7 HARD GATE, 5 KPI card, rubrics tabla, evaluate form |
| S4 | `238ee7f` | Service Catalog: 16 service card, search+filter, pipeline integration |
| S5 | `47992bc` | Design tokens @theme, ErrorBoundary, aria-label accessibility |
| S6 | `b38b156` | CubixViewer MUI→Tailwind, 0 @mui import, LegacyPage wrapper torolve |

### Uj UI oldalak (session 10)
- `/quality` — Quality Dashboard (KPI + rubrics + evaluate form)
- `/services` — Service Catalog (16 service, search, filter)
- `/cubix` — Cubix Kurzusok (Tailwind, nem MUI)

### Uj API endpointok (session 10)
- `GET /api/v1/notifications/in-app` — in-app lista
- `GET /api/v1/notifications/in-app/unread-count` — olvasatlan szam
- `POST /api/v1/notifications/in-app/{id}/read` — olvasottra jeloles
- `POST /api/v1/notifications/in-app/read-all` — osszes olvasott

### Infrastruktura (valtozatlan v1.2.0-bol)
- **26 service**, 18 pipeline adapter, 6 pipeline template
- **~159 API endpoint** (155 + 4 uj notification), **24 router**
- **45 DB tabla**, 29 Alembic migracio
- **332 pipeline unit test** PASS
- **Docker:** PostgreSQL 5433, Redis 6379
- **Auth:** admin@bestix.hu / admin (username mezo!)

### Post-Sprint TODO (felirva 57_PRODUCTION_READY_SPRINT.md Section 8)
- **P1 (HIGH):** Pipelines oldal templates szekció — `/templates/list` endpoint mukodik (6 template) de a UI nem hivja
- **P2 (MEDIUM):** `/api/v1/pipelines/templates` route conflict (UUID parse hiba) — workaround: `/templates/list`

---

## KOVETKEZO FELADAT: S7 (Langfuse Valos Integracio)

### Cel
A Langfuse stub implementaciot valos tracinggel es pipeline cost loggolassal kell felcserelni.

### Lepesek

```
1. TERVEZES:
   - Olvasd el 57_PRODUCTION_READY_SPRINT.md S7 szekciojat (sor ~268)
   - Nezzd meg src/aiflow/observability/ jelenlegi allapotat
   - Nezzd meg a Langfuse config-ot (.env, LANGFUSE_*)

2. FEJLESZTES:
   a) Langfuse tracing decorator: @traced wrapper step/skill futasokhoz
   b) Pipeline cost tracking: minden pipeline run cost_records-ba logolva
   c) Dashboard integration: cost_today, cost_month valos adatokbol
   d) Langfuse health check: /health endpoint-ban Langfuse status

3. TESZTELES:
   - Valos Langfuse hivas (ha van API key) VAGY mock fallback
   - curl: /health → langfuse status
   - Pipeline run → cost_records tabla sor letrejott
   - pytest: tracing decorator unit test

4. DOKUMENTALAS:
   - git commit
   - 57_PRODUCTION_READY_SPRINT.md: S7 = DONE

5. KOVETKEZO: S8 (Promptfoo 5 skill config)
```

---

## TIER B VEGREHAJTASI TERV (S7-S10)

```
S7:  Langfuse valos integracio ────── KOVETKEZO ← ITT VAGYUNK
S8:  Promptfoo 5 skill config ─────── YAML configs + CI
S9:  E2E Playwright test suite ────── 10+ teszt
S10: CI/CD regresszios pipeline ───── GitHub Actions
```

---

## KOTELEZOEN BETARTANDO SZABALYOK

### Session 10 tanulsagai:

1. **HMR context loss** — Vite HMR tobbszor elrontotta a React context-et (I18nProvider).
   Megoldas: uj tab/browser session, NEM reload.

2. **PageLayout props** — `titleKey`/`subtitleKey` (NEM `title`/`subtitle`), `source` (NEM `badge`)

3. **Figma WebSocket** — Bun runtime kell (`socket.js` Bun.serve()-t hasznal).
   Bun telepitve: `$HOME/.bun/bin/bun`. Inditas: `bun dist/socket.js`.
   VAGY: hivatalos Figma MCP (OAuth, mar konfigolva).

4. **Pipelines oldal bug** — Csak 2 DB-beli pipeline-t mutat, nem a 6 template-et.
   Post-sprint TODO-ban felirva (P1).

5. **@mui ZERO** — Minden MUI import eltavolitva (S6). NE adjunk hozza ujat!

6. **Notification bell** — TopBar-ban, 30s polling, click outside bezarás

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
S7:     Langfuse integracio ───────────── KOVETKEZO
S8:     Promptfoo 6 skill ─────────────── YAML configs + CI
S9:     E2E Playwright suite ──────────── 10+ teszt
S10:    CI/CD pipeline ────────────────── GitHub Actions
S11:    Free text + intent schema ─────── uj funkciok
S12:    SLA + cost estimation ─────────── APScheduler + tiktoken
S13:    Integralt E2E teszteles ────────── full journey-k
S14:    Vegleges polish ───────────────── PWA, a11y, v1.2.1 tag
```
