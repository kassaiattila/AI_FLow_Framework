# AIFlow v1.0.0-rc1 → v1.0.0 — Audit Javitasi Terv

**Alapja:** `01_PLAN/AUDIT_REPORT_v1.0.0-rc1.md`
**Cel:** Minden KRITIKUS es MAGAS prioritasu problema javitasa, v1.0.0 final release

---

## Sprint 1: KRITIKUS Security (becsult: 6 ora)

### T1. Hardcoded credentials torlese
**Fajl:** `src/aiflow/api/v1/auth.py:18-22`
**Jelenlegi:** `_USERS = {"admin": {"password": "admin", ...}}`
**Javitas:**
- Torolni a `_USERS` dict-et
- Login endpoint: `users` tablabol olvas (mar letezik, migration 005)
- Jelszavak bcrypt hash-sel tarolva (bcrypt mar a tech stack-ben)
- `POST /api/v1/auth/register` NINCS — csak admin hozhat letre usert (`POST /admin/users`)
- Seed script: `scripts/seed_admin.py` — elso admin user letrehozasa bcrypt hash-sel
**Teszt:** `curl -X POST /auth/login -d '{"username":"admin","password":"admin"}'` → 401

### T2. JWT secret kotelezove tetele
**Fajl:** `src/aiflow/api/v1/auth.py:24`
**Jelenlegi:** `os.getenv("AIFLOW_JWT_SECRET", "dev-secret-change-in-production")`
**Javitas:**
- Dev/test: default maradhat
- Production: `if settings.is_production and not AIFLOW_JWT_SECRET: raise RuntimeError`
- RS256 (asszimetrikus) — mar a tervben van (CLAUDE.md: "JWT: RS256")
- Minimum 32 byte secret validacio
**Teszt:** `AIFLOW_ENVIRONMENT=prod` inditasnal hiba ha nincs secret

### T3. CORS whitelist
**Fajl:** `src/aiflow/api/app.py:27`
**Jelenlegi:** `allow_origins=["*"]`
**Javitas:**
- `AIFLOW_CORS_ORIGINS` env var (comma-separated)
- Default dev: `["http://localhost:5173", "http://localhost:5174"]`
- Production: explicit whitelist KOTELEZO
**Teszt:** Mas origin-rol jovo request → 403

### T4. Traceback elrejtese
**Fajl:** `src/aiflow/api/app.py:72-79`
**Jelenlegi:** `content={"detail": str(exc), "traceback": tb[:1000]}`
**Javitas:**
- Production: `content={"detail": "Internal server error", "error_id": uuid4()}`
- Dev: traceback maradhat (debug=True eseten)
- Szerver-oldali log MINDIG tartalmazza a teljes traceback-et
**Teszt:** Production modban 500-as valasz NEM tartalmaz traceback-et

---

## Sprint 2: Auth Middleware + Connection Pool (becsult: 12 ora)

### T5. Auth middleware minden endpoint-ra
**Fajlok:** `src/aiflow/api/app.py` + uj `src/aiflow/api/middleware/auth.py`
**Jelenlegi:** Csak auth.py ellenorzi a token-t, tobbi endpoint nyitott
**Javitas:**
- FastAPI middleware: minden `/api/v1/*` request-nel Bearer token VAGY API key ellenorzes
- Kivetel (whitelist): `/health/*`, `/api/v1/auth/login`, `/docs`, `/redoc`
- `request.state.user_id` es `request.state.role` injektalas
- RBAC: admin endpoint-ok (admin.py) → csak admin role
**Teszt:** Token nelkuli request → 401; viewer role + admin endpoint → 403

### T6. Connection pooling centralizalas
**Fajlok:** Osszes `api/v1/*.py` ahol `_get_db_url()` vagy `asyncpg.connect()` van
**Jelenlegi:** Minden endpoint sajat connection-t nyit, nincs pool
**Javitas:**
- `src/aiflow/api/deps.py` — kozponti `get_db_session()` dependency
- `create_session_factory()` (mar letezik `state/repository.py:21`)
- App startup: session factory letrehozas, app.state-be mentes
- Osszes endpoint: `Depends(get_db_session)` hasznalat
- Torolni: minden lokalis `_get_db_url()` fuggvenyt
**Erintett fajlok:** runs.py, documents.py, emails.py, rag_engine.py, diagram_generator.py, media_processor.py, rpa_browser.py, human_review.py, admin.py (9 fajl)
**Teszt:** Load test: 50 parhuzamos request → nincs connection exhaustion

### T7. API key endpoint konszolidacio
**Fajlok:** `api/v1/auth.py` + `api/v1/admin.py`
**Jelenlegi:** Ket kulon API key kezeles (auth.py in-memory, admin.py DB)
**Javitas:**
- auth.py API key endpoint-ok TORLESE (in-memory kezeles)
- admin.py API key endpoint-ok MARADNAK (DB-alapu, aiflow_sk_ prefix)
- Auth middleware: API key validacio az `api_keys` tablabol (prefix lookup → hash verify)
**Teszt:** `curl -H "Authorization: Bearer aiflow_sk_..."` → autentikalt

---

## Sprint 3: Dokumentacio frissites (becsult: 3 ora)

### T8. 03_DATABASE_SCHEMA.md frissites
**Jelenlegi:** "36 tabla, 13 view, 13 migracio"
**Javitas:**
- Tabla szam: 49 (pontos lista a migraciokbol)
- View szam: 3 (pontos lista)
- Migracio szam: 24 (001-024 teljes lista)
- Minden tabla: nev + oszlopok + indexek + FK
**Modszer:** `alembic upgrade head` utan introspect: `\dt` + `\dv`

### T9. 42_SERVICE_GENERALIZATION_PLAN.md frissites
**Jelenlegi:** F0-F5 status "PLANNING"
**Javitas:**
- Minden fazis: status = COMPLETE, datum, tag
- Success criteria: checked/unchecked → jelolve melyik teljesult
- Endpoint lista: 114 (a teny szam, nem 50+)
- Referencia az AUDIT_REPORT-ra

### T10. API prefix standardizalas dokumentalas
**Jelenlegi:** 3 fele prefix (/, /v1, /api/v1)
**Javitas:**
- health.py, chat_completions.py, feedback.py prefix frissites → /api/v1/*
- 22_API_SPECIFICATION.md frissites az uj path-okkal
- Vite proxy config ellenorzes

---

## Sprint 4: Kod minoseg (becsult: 8 ora)

### T11. Singleton service-ek → Depends()
**Fajlok:** diagram_generator.py, media_processor.py, rpa_browser.py, human_review.py, admin.py
**Jelenlegi:** `_service = None; def _get_svc(): global _service; ...`
**Javitas:**
- FastAPI Depends() + lifespan event
- Service instance az app.state-ben
- Thread-safe, tesztelheto

### T12. TODO/FIXME befejezese (13 db)
**Langfuse (6 TODO):** `observability/tracing.py` — stub implementacio VAGY kitorles
**Vault (4 TODO):** `security/secrets.py` — EnvSecretProvider marad default, Vault opcionalis
**Egyeb (3):** kisebb cleanup

### T13. Nem hasznalt DB view-k auditja
**View-k:** v_daily_team_costs, v_monthly_budget, v_skill_performance, v_error_metrics
**Dontes:** expose-olni API-n keresztul VAGY torolni
**Ajanlat:** Costs endpoint-ba integralni a view-kat (v_daily_team_costs mar hasznos lenne)

---

## Osszefoglalo tablazat

| Task | Sprint | Ora | Prioritas | Fajl(ok) |
|------|--------|-----|-----------|----------|
| T1 Credentials | 1 | 2 | 🔴 KRIT | auth.py |
| T2 JWT secret | 1 | 1 | 🔴 KRIT | auth.py |
| T3 CORS | 1 | 1 | 🔴 KRIT | app.py |
| T4 Traceback | 1 | 1 | 🔴 KRIT | app.py |
| T5 Auth middleware | 2 | 6 | 🟡 MAGAS | app.py + uj middleware |
| T6 Connection pool | 2 | 4 | 🟡 MAGAS | 9 API fajl |
| T7 API key konsz. | 2 | 2 | 🟡 MAGAS | auth.py, admin.py |
| T8 DB schema doc | 3 | 1 | 🟠 KOZ | 03_DATABASE_SCHEMA.md |
| T9 Plan frissites | 3 | 1 | 🟠 KOZ | 42_SERVICE_GEN.md |
| T10 API prefix | 3 | 1 | 🟠 KOZ | 3 API fajl + docs |
| T11 Depends() | 4 | 4 | 🟢 NORM | 5 API fajl |
| T12 TODO cleanup | 4 | 2 | 🟢 NORM | tracing.py, secrets.py |
| T13 View audit | 4 | 2 | 🟢 NORM | costs.py + migracio |
| **TOTAL** | **4 sprint** | **~28 ora** | | |

---

## Definition of Done: v1.0.0 final

- [ ] T1-T4 KESZ (Sprint 1) — nincs hardcoded credential, nincs traceback leak
- [ ] T5-T7 KESZ (Sprint 2) — auth middleware, connection pool, API key egysites
- [ ] T8-T10 KESZ (Sprint 3) — dokumentacio naprakesz
- [ ] Osszes letezo Playwright E2E teszt PASS
- [ ] `alembic upgrade head` + `alembic downgrade -1` + `alembic upgrade head` HIBA NELKUL
- [ ] `npx tsc --noEmit` PASS (UI)
- [ ] v1.0.0 tag + release notes
