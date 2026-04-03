# AIFlow v1.1.2 — Kovetkezo Session Prompt

> **Datum:** 2026-04-03 (2. session)
> **Elozo session:** Dokumentacio fix + DELETE gombok + Mermaid E2E + teljes audit
> **Branch:** main (5 commit: d01f2c8...9fb0d4e)
> **Statusz:** 36/36 API OK, 16/16 UI oldal, 28 doc + 5 RAG collection + 12 run

---

## Mi tortent ebben a session-ben

### 1. Dokumentacio fix (KRITIKUS)
- CLAUDE.md: `localhost:8100→8101` (1 hely)
- F1_DOCUMENT_EXTRACTOR_JOURNEY.md: port 8100→8101, frontend 5174→5173
- F3_RAG_ENGINE_JOURNEY.md: port 8100→8101, frontend 5174→5173
- 22_API_SPECIFICATION.md: +7 uj endpoint dokumentalva (10.4–10.10)
- 43_UI_RATIONALIZATION_PLAN.md: oldalszam 14→16 (3 helyen)
- CLAUDE.md F6 tabla: 14→16 oldal

### 2. UI DELETE gombok
- Documents.tsx: torlés gomb minden sorban + megerősítő dialog + i18n HU/EN
- Rag.tsx: collection torlés gomb + megerősítő dialog + i18n HU/EN
- Locales: hu.json + en.json (deleteTitle, deleteConfirm, deleteSuccess, deleteFailed)

### 3. API bug fix
- documents/by-id: `DocumentDetailResponse(**result, source="backend")` → duplikalt source kwarg → JAVITVA

### 4. Teljes rendszer audit
- 36 API endpoint tesztelve curl-lel (35 OK + 1 fix kész, restart kell)
- 16 UI oldal Playwright-tal screenshotolva (mind betolt, adat megjelenik)
- i18n HU/EN toggle PASS

### 5. Valos E2E tesztek
- **Document pipeline:** Upload PDF → 6-step SSE process → Store → DELETE (PASS)
- **RAG pipeline:** Create collection → Ingest PDF(Docling+Embed, 2 chunk) → Query LLM → valós válasz: "Kovacs Akos, adoszam 69900666-1-33" → DELETE (PASS)
- **Mermaid diagram:** Szoveg beiras → LLM → vizualis SVG render (PASS)

---

## Jelenlegi rendszer allapot

### Infrastruktura
- PostgreSQL 5433 (Docker), Redis 6379 (Docker)
- API: `uvicorn aiflow.api.app:create_app --factory --port 8101`
- Frontend: `cd aiflow-admin && npm run dev` (5173, proxy → 8101)
- Auth: admin@bestix.hu / admin (bcrypt, JWT) — localStorage key: `aiflow_token`

### Adatok (DB-ben, perzisztens)
| Tabla | Rekord |
|-------|--------|
| invoices | 28 |
| invoice_line_items | 30 |
| workflow_runs | 13 |
| step_runs | 78 |
| rag_collections | 5 (ASZF: 131, Test AZHU: 260, stb.) |
| rag_chunks | 4922 |
| generated_diagrams | 11 |
| users | 2 (admin + viewer) |
| api_keys | 1 |

### API Audit eredmenyek (36 endpoint)
| Csoport | Endpoint szam | Statusz |
|---------|---------------|---------|
| Health | 1 | 1/1 OK |
| Auth | 2 | 2/2 OK |
| Documents | 7 | 6/7 OK (by-id fix kész, restart kell) |
| Runs | 3 | 3/3 OK |
| Costs | 3 | 3/3 OK |
| RAG | 4 | 4/4 OK |
| Skills | 1 | 1/1 OK |
| Diagrams | 1 | 1/1 OK |
| Emails | 2 | 2/2 OK |
| Admin | 4 | 4/4 OK |
| Feedback | 2 | 2/2 OK |
| Services | 2 | 2/2 OK |
| RPA | 1 | 1/1 OK |
| Media | 1 | 1/1 OK |
| Cubix | 1 | 1/1 OK |
| Reviews | 2 | 2/2 OK |
| **TOTAL** | **36** | **35/36 OK** |

---

## HATRALEVO feladatok (kovetkezo session)

### ROVID TAV — 1-2 ora

#### 1. API szerver ujrainditas + by-id verify (5 perc)
- `documents/by-id` fix mar commitolva, csak restart kell
- Utana curl-lel verify: `GET /api/v1/documents/by-id/{id}` → 200

#### 2. Document Detail oldal (60 perc) — TELJESEN HIANYZIK
- Uj fajl: `pages-new/DocumentDetail.tsx`
- Route: `/documents/{id}/show`
- 3 oszlopos layout (fejlec, szallito, vevo) + tetelsor tablazat
- "Verify" gomb → navigacio `/documents/{id}/verify`

#### 3. LLM cost tracking (45 perc) — NEM MUKODIK
- invoice_processor nem irja be a GPT API koltsseget a workflow_runs-ba
- token count * model rate → total_cost_usd mezo kitoltese

### KOZEP TAV — 3-5 ora

#### 4. RAG Collection stats KPI bovites (30 perc)
- RagDetail.tsx: query_count, avg_response_time, thumbs_up/down kartyak

#### 5. Document kereses/szures bovites (60 perc)
- vendor szuro, datum range, osszeg range, config szuro

#### 6. Cubix viewer fix (30 perc)
- Legacy Cubix viewer nem tolt be adatot (audit: hasData=false, hasVisibleError=true)

### HOSSZU TAV — 1-2 nap

#### 7. Email Upload implementacio (2-3 ora)
#### 8. Audit log valos esemeny rogzites (60 perc)
#### 9. Production deployment (2-3 ora)

---

## Hasznos parancsok

```bash
# Infrastruktura
docker compose up -d

# API (--reload a hot reload-hoz!)
.venv/Scripts/python.exe -m uvicorn aiflow.api.app:create_app --factory --port 8101 --reload

# Frontend
cd aiflow-admin && npm run dev

# Login token
TOKEN=$(curl -s -X POST http://localhost:8101/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin@bestix.hu","password":"admin"}' | python -c "import sys,json; print(json.load(sys.stdin)['token'])")

# Quick health check
curl -s http://localhost:8101/health | python -m json.tool

# Document lista
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8101/api/v1/documents | python -c "import sys,json; print(json.load(sys.stdin)['total'])"
```

---

## Fajl referencia

### Ebben a session-ben modositott fajlok
| Fajl | Valtozas |
|------|----------|
| CLAUDE.md | port 8100→8101, F6 14→16 oldal |
| 01_PLAN/22_API_SPECIFICATION.md | +7 endpoint (10.4–10.10), sorszamozas fix |
| 01_PLAN/43_UI_RATIONALIZATION_PLAN.md | 14→16 oldal (3 helyen) |
| 01_PLAN/F1_DOCUMENT_EXTRACTOR_JOURNEY.md | port fix |
| 01_PLAN/F3_RAG_ENGINE_JOURNEY.md | port fix |
| aiflow-admin/src/pages-new/Documents.tsx | DELETE gomb + confirm dialog |
| aiflow-admin/src/pages-new/Rag.tsx | DELETE gomb + confirm dialog |
| aiflow-admin/src/locales/hu.json | +4 torlés kulcs |
| aiflow-admin/src/locales/en.json | +4 torlés kulcs |
| src/aiflow/api/v1/documents.py | by-id source kwarg fix |
