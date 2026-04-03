# AIFlow v1.2.0 — Stability & Regression Protection Plan

> **Szulo terv:** `48_ORCHESTRABLE_SERVICE_ARCHITECTURE.md`
> **Cel:** A meglevo 15 service, 112+ endpoint, 17 UI oldal TORETLENUL mukodjon az uj fejlesztesek mellett.

---

## 1. Jelenlegi Allapot

| Metrika | Ertek |
|---------|-------|
| Services | 15 (7 BaseService + 8 standalone) |
| API endpoints | 112+ (19 router) |
| UI oldalak | 17 (Untitled UI + Tailwind v4) |
| DB tablak | 41 + 6 view |
| Alembic migraciok | 26 |
| Mukodo skill-ek | 4 (process_doc, cubix, aszf_rag, email_intent) |

---

## 1.1 Branch Strategy

**Tier-enkent feature branch, merge to main Tier vegen.**

```
main (stabil, v1.1.4)
  ├── feature/v1.2.0-tier1-pipeline-orchestrator   ← C0-C5
  ├── feature/v1.2.0-tier1.5-invoice-usecase       ← C6
  ├── feature/v1.2.0-tier2-supporting-services     ← C7-C10
  ├── feature/v1.2.0-tier3-advanced-rag            ← C11-C16
  └── feature/v1.2.0-tier4-polish                  ← C17-C20
```

- **main MINDIG stabil** — SOHA ne commitolj kozvetlenul main-re v1.2.0 fejlesztes soran
- **Merge to main:** CSAK ha L0 smoke PASS + Tier MINDEN ciklusa DONE
- **Merge tipus:** squash merge (clean history)
- **Tag-eles:** Tier 1 → v1.2.0-alpha, Tier 1.5 → v1.2.0-beta, Tier 2 → v1.2.0-rc1, Tier 3 → v1.2.0-rc2, Tier 4 → v1.2.0
- **Hotfix main-re:** `hotfix/...` branch, cherry-pick tier branch-re
- **Rebase:** Tier branch rendszeresen rebase-eli main-t merge conflict elkerulesere

---

## 2. Stabilitasi Strategia

### 2.1 API Compatibility Rules

**SOHA ne torj meg meglevo API-t:**
- Uj mezok hozzaadasa MINDIG optional (default ertekkel)
- Mezo torles TILOS — deprecation-nel jelold es 2 minor version utan tedd optional-la
- Endpoint atnevezes TILOS — uj endpoint + redirect a regirol
- Response format valtozas TILOS — uj mezo OK, mezo tipus valtozas NEM

**Verziozas:**
- Jelenlegi: `/api/v1/*` — ez FROZEN az orchestration fejlesztes alatt
- Uj pipeline endpointok: `/api/v1/pipelines/*` — uj router, nem modositja a meglevoket
- Ha breaking change kell: `/api/v2/*` prefix es parhuzamos mukodes

### 2.2 Database Migration Safety

**Alembic szabalyok:**
- Minden migracio KOTELEZO: `upgrade` + `downgrade` tesztelve
- Uj tabla: OK (nem erint meglevo adatot)
- Uj oszlop meglevo tablaban: KOTELEZO `nullable=True` vagy `server_default`
- Oszlop torles: TILOS egybol — eloszor `nullable=True`, kovetkezo release-ben torlod
- Index hozzaadas: `CREATE INDEX CONCURRENTLY` (nem zarolja a tablat)
- FK hozzaadas: `ON DELETE SET NULL` (nem cascadol varatlanul)

**Migracio teszt:**
```bash
alembic upgrade head && alembic downgrade -1 && alembic upgrade head
# Mind a 3 HIBA NELKUL kell fusson
```

### 2.3 Service Isolation

**Elv:** Uj szolgaltatasok (pipeline, notification, stb.) NEM modositjak a meglevo service kodjat.

| Reteg | Szabaly |
|-------|--------|
| **Meglevo service-ek** | KIZAROLAG bugfix. Feature bovites TILOS az orchestration fejlesztes alatt. |
| **Adapter reteg** | A `pipeline/adapters/` mappa WRAPPER-eket ir, NEM modositja az eredeti service-t. |
| **Uj service-ek** | Kulon mappa (`services/{name}/`), kulon adapter, kulon migracio. |
| **API router-ek** | Uj router-ek uj fajlba. Meglevo router CSAK bugfix-re nyulhato. |

### 2.4 Frontend Stability

**Elv:** Meglevo oldalak MUKODNEK az uj fejlesztesek alatt.

- Meglevo `pages-new/*.tsx` fajlok: KIZAROLAG bugfix
- Uj oldalak: uj fajlok (`Pipelines.tsx`, `PipelineDetail.tsx`, stb.)
- Kozos komponensek (`DataTable`, `PageLayout`, stb.): modositas CSAK ha 100% backward-compatible
- `router.tsx`: uj route-ok HOZZAADHATOAK, meglevo route-ok NEM modosulnak
- `locales/*.json`: uj kulcsok HOZZAADHATOAK, meglevo kulcsok NEM modosulnak

---

## 3. Regresszios Teszt Strategia

### 3.1 Teszt Szintek

| Szint | Mikor | Mit futtat | Max ido |
|-------|-------|-----------|---------|
| **L0 Smoke** | Minden kod mentes | API health + 3 fo endpoint + UI betolt | <30s |
| **L1 Unit** | Minden commit | Erintett modul unit tesztjei | <60s |
| **L2 API** | Minden PR | Minden API endpoint (curl, validi response) | 2-5 min |
| **L3 E2E** | Merge to main | Playwright: minden UI oldal betolt + fo funkciok | 10-20 min |
| **L4 Full** | Release elott | L0-L3 + skill tesztek + Promptfoo | 30-60 min |

### 3.2 L0 Smoke Test (MINDEN fejlesztes elott es utan)

```bash
#!/bin/bash
# smoke_test.sh — 30 masodperc alatt lefut
set -e

TOKEN=$(curl -sf -X POST http://localhost:8102/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin@bestix.hu","password":"admin"}' | python -c "import sys,json; print(json.load(sys.stdin)['token'])")

# Health
curl -sf http://localhost:8102/api/v1/health | python -c "import sys,json; d=json.load(sys.stdin); assert d['status']=='ok'"

# Core endpoints (source: backend)
for ep in documents emails/inbox rag/collections services; do
  curl -sf -H "Authorization: Bearer $TOKEN" "http://localhost:8102/api/v1/$ep" \
    | python -c "import sys,json; d=json.load(sys.stdin); assert d.get('source')=='backend', f'{d}'"
done

echo "SMOKE TEST: ALL PASS"
```

### 3.3 L2 API Regression Matrix

Minden meglevo endpoint curl-lel tesztelve MINDEN PR-ben:

| Router | Endpoints | Teszt |
|--------|-----------|-------|
| health | GET /health | status=ok |
| auth | POST /login, GET /me | token returned, user info |
| documents | GET /list, POST /process-stream | lista + SSE format |
| emails | GET /inbox, GET /connectors, POST /fetch-and-process-stream | lista + config CRUD |
| rag_engine | GET /collections, POST /ingest-stream, POST /query | collection CRUD + query |
| process_docs | POST /generate-stream | SSE pipeline |
| media_processor | GET /jobs | job lista |
| costs | GET /daily | cost adatok |
| runs | GET /list | run lista |
| skills_api | GET /list | skill lista |
| human_review | GET /pending, POST /approve | review CRUD |
| admin | GET /api-keys | admin funkciok |

### 3.4 L3 Playwright E2E Checklist

Minden UI oldal:
1. Navigate → oldal betolt (nincs JS hiba a console-ban)
2. Adatok megjelennek (nem "loading" orokre)
3. HU/EN nyelv toggle mukodik
4. Dark/Light mode toggle mukodik
5. Fo interakciok mukodnek (kattintas, form submit)

---

## 4. Fejlesztesi Workflow

### 4.1 Minden kod valtozas elott

```bash
# 1. Smoke test PASS?
./scripts/smoke_test.sh

# 2. TypeScript HIBA NELKUL?
cd aiflow-admin && npx tsc --noEmit

# 3. Python lint CLEAN?
ruff check src/ skills/
```

### 4.2 Minden kod valtozas utan

```bash
# 1. Smoke test PASS? (regresszio ellenorzes)
./scripts/smoke_test.sh

# 2. Erintett unit tesztek PASS?
pytest tests/unit/<affected>/ -v

# 3. TypeScript HIBA NELKUL?
cd aiflow-admin && npx tsc --noEmit

# 4. Uj tesztek irva?
# MINDEN uj modra KOTELEZO test
```

### 4.3 Commit elott

```bash
# Teljes regresszio az erintett teruletre
pytest tests/unit/ -v --tb=short
./scripts/smoke_test.sh
cd aiflow-admin && npx tsc --noEmit
```

---

## 5. Monitoring & Alerting

### 5.1 API Health Dashboard

Az Admin UI Dashboard oldalon:
- Minden service health status (zold/piros)
- API response time atlag (utolso 1 ora)
- Error rate (utolso 1 ora)
- DB connection pool status

### 5.2 Reszletes Loggolas

Minden service hivas structlog-gal logolva:
```python
logger.info("service_call", service=name, method=method, duration_ms=dur, success=True)
logger.error("service_error", service=name, method=method, error=str(exc))
```

---

## 6. Rollback Strategia

**Ha valami elromlik:**

1. **Kod rollback:** `git revert <commit>` — NEM `reset --hard`
2. **DB rollback:** `alembic downgrade -1` — CSAK ha a migracio downgrade-je tesztelve volt
3. **Service rollback:** Adapter torles + service registry-bol kivetel — eredeti service erintetlen marad
4. **UI rollback:** Route torles `router.tsx`-bol — meglevo oldalak erintetlenek

---

## 7. Fajl Osszefoglalas

| Uj fajl | Cel |
|---------|-----|
| `scripts/smoke_test.sh` | L0 smoke test script |
| `scripts/api_regression.sh` | L2 API regresszio |
| `tests/regression/test_api_endpoints.py` | Automatizalt API regresszio |
| `tests/regression/test_ui_smoke.py` | Playwright smoke test |
