# AIFlow v1.2.0 — Session 9 Prompt (C7 Notification Service — Tier 2 Start)

> **Datum:** 2026-04-04 (session 8 utan)
> **Elozo session:** Tier 1.5 COMPLETE (C6) — Invoice pipeline E2E PASS, merged to main, tag v1.2.0-beta
> **Branch:** main (v1.2.0-beta)
> **Port:** API 8102, Frontend 5173 (Vite proxy → 8102)
> **Utolso commit:** `c4df803` feat: v1.2.0-beta — C6 Invoice Use Case, pipeline E2E with real services

---

## ⚠ KOTELEZOEN BETARTANDO SZABALYOK — OLVASD EL ELOSZOR!

> **A session 8-ban C6 HAROM iteracion ment at mire valos E2E-t ert el.**
> **Az alabbi szabalyok MEGELOZIK a kodolast. NINCS kiveteles.**

### 1. TERVEK OLVASASA KOTELEZO FEJLESZTES ELOTT
- **Fo terv:** `01_PLAN/48_ORCHESTRABLE_SERVICE_ARCHITECTURE.md` — Phase 6A szekcioja
- **Reszletes terv:** `01_PLAN/52_HUMAN_IN_THE_LOOP_NOTIFICATION.md` — Section 3 (Notification Service)
- **Execution plan:** `01_PLAN/56_EXECUTION_PLAN.md` — C7 sor
- **TILOS kodot irni a tervek elolvasasa NELKUL!**

### 2. FEJLESZTESI CIKLUS (6 LEPES — SORREND KOTELEZO!)
```
1. TERVEZES    — terv olvasas, scope pontositas
2. FEJLESZTES  — kod iras (Alembic → Service → Adapter → API → teszt)
3. TESZTELES   — unit + E2E VALOS adatokkal (SOHA NE MOCK!)
4. DOKUMENTALAS — commit, terv frissites
5. FINOMHANGOLAS — review, bug fix
6. SESSION PROMPT — kovetkezo session kontextus
```

### 3. CIKLUS LEZARAS ELOTT CHECKLIST (MIND PASS KELL!)
```bash
pytest tests/unit/<affected>/ -v     # Uj + erintett tesztek PASS
./scripts/smoke_test.sh              # L0: regresszio ellenorzes
ruff check src/ skills/              # NEM szabad uj hibat bevezetni
cd aiflow-admin && npx tsc --noEmit  # Frontend HIBA NELKUL
```

### 4. MERGE FELTETEL (Tier 2 branch → main)
> **CLAUDE.md 541:** "Merge to main: CSAK ha L0 smoke test PASS + Tier MINDEN ciklusa DONE"
> **56_EXECUTION_PLAN.md 155:** "Merge to main: invoice V2 E2E PASS → squash merge → tag v1.2.0-rc1"
> **Tier 2 MIND A 4 ciklusa (C7-C10) kell a merge-hoz!** Nem egyenkent merge-olunk.

### 5. BRANCH STRATEGIA
```bash
# Tier 2 branch — C7-C10 MIND EZEN a branch-en!
git checkout -b feature/v1.2.0-tier2-supporting-services
# Squash merge main-re CSAK Tier 2 vegen (C10 utan)
```

### 6. DB MIGRATION SZABALYOK (CLAUDE.md)
- Uj oszlop: KOTELEZO `nullable=True` vagy `server_default`
- Oszlop torles: TILOS egybol
- Teszt: `alembic upgrade head && alembic downgrade -1 && alembic upgrade head` HIBA NELKUL
- **SOHA ne hozz letre tablat Alembic NELKUL!**

### 7. SERVICE IZOLACIO (CLAUDE.md)
- Meglevo service-ek: KIZAROLAG bugfix, feature bovites TILOS
- Uj service: kulon mappa, kulon adapter, kulon migracio
- Meglevo API router-ek: CSAK bugfix, uj feature → uj router fajl

### 8. VALOS TESZTELES (SOHA NE MOCK!)
- API tesztek: valos FastAPI szerver + valos HTTP
- Service tesztek: valos PostgreSQL (Docker), NEM in-memory mock
- Notification teszt: valos SMTP kuldes VAGY valos Slack webhook
- **Egy feature CSAK AKKOR "KESZ" ha valos adatokkal tesztelve**

---

## ALLAPOT

### Tier 1 + 1.5: KESZ (v1.2.0-beta, 2026-04-04)

| Ciklus | Fazis | Tartalom | Allapot |
|--------|-------|----------|---------|
| C0 | Elokeszites | Untitled UI init, smoke test fix, ruff config | DONE |
| C1 | P1 Adapter | ServiceAdapter protocol + 7 adapter + 40 test | DONE |
| C2 | P2 Schema | YAML schema + Jinja2 + compiler + parser + 61 test | DONE |
| C3 | P3 Runner+DB | PipelineRunner + Alembic 027 + repository + 9 test | DONE |
| C4 | P4 API | 10 endpoint (incl. POST /run), curl-tesztelve | DONE |
| C5 | P5 UI | Pipelines + PipelineDetail, 7 HARD GATE, E2E PASS | DONE |
| C6 | Invoice v1 | E2E: Outlook COM → 3 email → classify → extract → COMPLETED | DONE |

### Pipeline Modul (KESZ, NEM MODOSITJUK — kiveve adapter hozzaadas)

```
src/aiflow/pipeline/
├── __init__.py        # Public API exports
├── adapter_base.py    # ServiceAdapter Protocol + BaseAdapter + AdapterRegistry
├── adapters/          # 6 modul (7 adapter: RAG has ingest+query)
│   ├── email_adapter.py, classifier_adapter.py, document_adapter.py
│   ├── rag_adapter.py (ingest + query), media_adapter.py, diagram_adapter.py
│   └── *** notification_adapter.py → C7-BEN HOZZUK LETRE ***
├── schema.py          # PipelineDefinition, StepDef, TriggerDef, RetryPolicy
├── template.py        # Jinja2 SandboxedEnvironment + compile_expression
├── compiler.py        # PipelineCompiler → DAG + step_funcs (for_each FIXED)
├── parser.py          # YAML/file/dict → PipelineDefinition
├── repository.py      # Async CRUD for pipeline_definitions
├── runner.py          # PipelineRunner: run(id), run_from_yaml()
└── builtin_templates/ # invoice_automation_v1.yaml (C6)
```

### Infrastruktura szamok
- **DB:** 27 Alembic migracio, 42 tabla (*** 028 = notification_channels, notification_log ***)
- **API:** 122+ endpoint, 20 router (*** +1 notifications router C7-ben ***)
- **Pipeline adapters:** 7 db (*** +1 notification_adapter C7-ben ***)
- **Unit tests:** 837 PASS (147 pipeline)
- **Tags:** v1.2.0-alpha (Tier 1), v1.2.0-beta (Tier 1.5)

---

## KOVETKEZO FELADAT: C7 Ciklus (Notification Service)

### Cel
Uj NotificationService — multi-channel ertesites kuldes (email SMTP, Slack webhook, generic webhook). Pipeline adapter-rel hasznalhato.

### Branch
```bash
git checkout -b feature/v1.2.0-tier2-supporting-services
```

### Tervek (OLVASD ELOSZOR!)
1. **`01_PLAN/48_ORCHESTRABLE_SERVICE_ARCHITECTURE.md`** — Phase 6A szekció
2. **`01_PLAN/52_HUMAN_IN_THE_LOOP_NOTIFICATION.md`** — Section 3 (Notification Service, 3.1-3.4)

### Lepesek (SORREND KOTELEZO!)

```
1. TERVEZES:
   - Olvasd el 48 Phase 6A + 52 Section 3 (teljes!)
   - Listazd ki: service metodik, DB tablak, API endpointok, adapter

2. FEJLESZTES (SORREND!):
   a) Alembic 028: notification_channels + notification_log tablak
      - alembic upgrade head && alembic downgrade -1 && alembic upgrade head → HIBA NELKUL
   b) src/aiflow/services/notification/service.py (NotificationService)
      - BaseService, send(), list_channels(), create_channel(), test_channel()
      - Csatornak: email (aiosmtplib), slack (httpx webhook), generic webhook (httpx)
      - Template: Jinja2 render (YAML-bol)
   c) src/aiflow/services/notification/__init__.py (exports)
   d) src/aiflow/pipeline/adapters/notification_adapter.py
      - NotificationAdapter: service=notification, method=send
      - Input: channel, template, data, recipients
      - Output: sent, message_id, error
   e) src/aiflow/api/v1/notifications.py (uj router!)
      - POST /api/v1/notifications/send
      - GET/POST/DELETE /api/v1/notifications/channels
      - POST /api/v1/notifications/channels/{id}/test
   f) Notification YAML template (prompts/notifications/ mappa)

3. TESZTELES (VALOS!):
   - alembic upgrade head + downgrade + upgrade (PASS)
   - Unit tesztek: service, adapter, API models
   - curl: MINDEN endpoint 200 OK + source=backend
   - Valos SMTP (aiosmtplib) VAGY valos Slack webhook teszt
   - Pipeline integracio: notification step az invoice pipeline vegehez
   - L0 smoke test PASS

4. DOKUMENTALAS:
   - git commit (conventional commits)
   - 56_EXECUTION_PLAN.md: C7 = DONE

5. FINOMHANGOLAS: ruff, tsc

6. SESSION PROMPT: "C7 KESZ, kovetkezo C8 (Data Router)"
```

### NotificationService interface (52_HUMAN_IN_THE_LOOP_NOTIFICATION.md-bol):
```python
class NotificationService(BaseService):
    async def send(channel, template, data, recipients, config_name) -> NotificationResult
    async def send_batch(notifications) -> list[NotificationResult]
    async def list_channels() -> list[ChannelConfig]
    async def create_channel(config) -> ChannelConfig
    async def update_channel(channel_id, config) -> ChannelConfig
    async def delete_channel(channel_id) -> bool
    async def test_channel(channel_id) -> bool
```

### DB tablak (52, Section 3.4 — Alembic 028):
```sql
notification_channels (id, name, channel_type, config JSONB, enabled, team_id, created_at, updated_at)
notification_log (id, channel_id, channel_type, recipient, template_name, subject, status, error, pipeline_run_id FK, sent_at)
in_app_notifications (id, user_id FK, title, body, link, read, created_at)
```

### FONTOS KORLATOZ ASOK
- **Ez NEM UI ciklus** — nincs UI fejlesztes C7-ben (UI a C9-C10-ben johet)
- **Meglevo service-ek:** NEM modositjuk (email_connector, classifier, stb.)
- **Meglevo API router-ek:** NEM modositjuk (emails.py, pipelines.py, stb.)
- **aiosmtplib** fuggoseg kell — `uv add aiosmtplib` (ha meg nincs)
- **Notification templates:** `prompts/notifications/` mappa (Jinja2 YAML)

---

## SZERVER INDITAS

```bash
# Docker (ha meg nem fut):
docker compose up -d db redis

# API szerver:
.venv\Scripts\python.exe -B -m uvicorn aiflow.api.app:create_app --factory --port 8102

# Frontend (ha kell):
cd aiflow-admin && npm run dev
```

---

## VEGREHAJTASI TERV (frissitett)

```
C0-C5:  Tier 1 Core ──── DONE (v1.2.0-alpha) ✓
C6:     Invoice v1 ────── DONE (v1.2.0-beta) ✓
C7:     Notification ──── KOVETKEZO ← ITT VAGYUNK
C8:     Data Router ────── Tier 2 folytatas
C9:     Invoice v2 ─────── Tier 2 integracio
C10:    Service Mgr ────── Tier 2 vege → merge main → v1.2.0-rc1
C11-16: Tier 3 RAG ────── 3-4 session
C17-20: Tier 4 Polish ─── 1-2 session
```

---

## INFRASTRUKTURA

- PostgreSQL 5433, Redis 6379 (Docker)
- Auth: admin@bestix.hu / admin (username mezo!)
- 27 Alembic migracio (028 = notification), 42 DB tabla, 122+ endpoint, 20 router
- 19 UI oldal, 15 service (+1 notification = 16)
- Tag: v1.2.0-beta (Tier 1.5 complete)
- **Outlook COM connector:** `f522575b-ff3b-44a6-9a70-b68592a01b7c` (mukodik!)
- **IMAP connector:** `9bce0db7-59f5-48b3-a337-434ae97157d0` (mukodik, de ures mailbox)

---

## EMLEKEZTETOK (korabbi session-ok tanulsagai)

1. **Adapter service resolution:** Az adaptereknek kozvetlenul kell letrehozni a service-t (NEM ServiceRegistry-bol). Minta: `email_adapter.py` `_get_service()` — async, `get_session_factory()`.
2. **Jinja2 for_each:** A `compile_expression` adja vissza a native Python objektumot (lista, dict), NEM string rendereles.
3. **Auth:** Login endpoint `username` mezot var (NEM `email`).
4. **Ures for_each:** Ha a lista ures, `{"results": [], "count": 0}` jon vissza (nincs hiba).
5. **Session factory:** `get_session_factory()` mar letezik `src/aiflow/api/deps.py`-ben, hasznald!
