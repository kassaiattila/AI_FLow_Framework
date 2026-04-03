# AIFlow v1.1.1 — Kovetkezo Session Prompt

> **Datum:** 2026-04-03
> **Elozo session:** Teljes rendszer audit + E2E teszteles + 20+ bug fix + 3 uj feature
> **Branch:** main (3 commit: a58fadf, 669ae4e, d01f2c8)
> **Statusz:** 25/25 API OK, 16/16 UI oldal mukodik, 28 doc + 2 RAG collection + 12 run perzisztalva

---

## Mi tortent az elozo session-ben

### Elvegzett munka (3 session, ~8 ora)

**1. Teljes rendszer audit es E2E teszteles**
- 25 API endpoint tesztelve curl-lel — mind 200 OK
- 16 UI oldal Playwright-tal screenshotolva (55+ evidencia)
- Valos adatokkal: 28 szamla (Docling+GPT), 2 RAG kollekcio (131+260 chunk), 12 workflow run

**2. Javitott bugok (20+)**
- Costs page crash (API mezo nevek mismatch)
- Document confidence 1% → 100% (0-1 skala konverzio)
- Verification PDF kep NEM jelent meg → JAVITVA (filename extract + path normalize)
- Verification prev/next navigacio race condition → JAVITVA (cached doc list)
- Document process-stream 401 auth → JAVITVA (fetch-alapu SSE)
- SSE event format mismatch → JAVITVA (step_start/step_done/complete)
- CSV Export auth hiba → JAVITVA (fetchApi blob letoltes)
- RAG LiteLLM import hiba → JAVITVA (backends/ path)
- RAG DATABASE_URL env hiba → JAVITVA (AIFLOW_DATABASE__URL fallback)
- RAG chunks metadata → JAVITVA (document_name root szinten)
- Monitoring i18n "ra.action.refresh" → JAVITVA
- Documents oszlopok hardcoded angol → JAVITVA (i18n)

**3. Uj feature-ok**
- RagDetail.tsx — kollekcio reszletezo oldal (Ingest/Chat/Chunks tabok)
- ChatPanel.tsx — ujrahasznalhato RAG chat komponens (full-height, forrasok mindig lathatoak)
- Rag.tsx — Uj Kollekcio dialog (nev, leiras, nyelv)
- ProcessDocs.tsx — Mermaid diagram vizualis renderejes
- Documents CSV/JSON export endpointok
- Documents DELETE endpoint
- Documents Extractor Config dropdown
- RAG file perzisztencia (data/uploads/rag/{id}/, nem temp)

---

## Jelenlegi rendszer allapot

### Infrastruktura
- PostgreSQL 5433 (Docker), Redis 6379 (Docker), Kroki 8000 (Docker)
- API: `uvicorn aiflow.api.app:create_app --factory --port 8101`
- Frontend: `cd aiflow-admin && npm run dev` (5173, proxy → 8101)
- Auth: admin@bestix.hu / admin (bcrypt, JWT)

### Adatok (DB-ben, perzisztens)
| Tabla | Rekord |
|-------|--------|
| invoices | 28 |
| invoice_line_items | 30 |
| workflow_runs | 12 |
| step_runs | 72 |
| rag_collections | 2 (ASZF: 131 chunk, Test AZHU: 260 chunk) |
| rag_chunks | 4922 |
| generated_diagrams | 10 |
| users | 2 (admin + viewer) |
| api_keys | 1 |

### Tesztadatok eleresehez
- Szamlak: `e2e-audit/test-data/invoices/` (3 db, projekt mappaban)
- RAG docs: `e2e-audit/test-data/rag-docs/` (50+ Allianz PDF)
- Eredeti forras: `C:\Users\kassaiattila\OneDrive - BestIxCom Kft\00_BESTIX_KFT\02_Szamlak\Bejovo\2021\`

---

## Dokumentacio inkonzisztenciak (JAVITANDO!)

| Fajl | Problema | Prioritas |
|------|----------|-----------|
| CLAUDE.md | Port 8100 → valoban 8101 (tobb helyen) | KRITIKUS |
| F1_DOCUMENT_EXTRACTOR_JOURNEY.md | Port 8100→8101, Frontend 5174→5173 | KRITIKUS |
| F3_RAG_ENGINE_JOURNEY.md | Port 8100→8101, Frontend 5174→5173 | KRITIKUS |
| 22_API_SPECIFICATION.md | Hianyzik: /export/csv, /export/json, /delete/{id}, /by-id/{id} | MAGAS |
| 43_UI_RATIONALIZATION_PLAN.md | Oldal szam: tervben 14, valosagban 16 | KOZEPES |

---

## Ebben a session-ben KESZ (NEM kell ujra csinalni)

| Feature | Statusz | Bizonyitek |
|---------|---------|------------|
| Verification valos PDF kep (bal oldal) | KESZ | Screenshot #49 — bounding box + adatpontok |
| Verification prev/next navigacio | KESZ | Cached doc list, nincs race condition |
| CSV/JSON Export backend endpoint | KESZ | GET /export/csv 200 OK, valos CSV adat |
| CSV Export frontend gomb (auth-os) | KESZ | fetchApi blob letoltes (nem bare `<a href>`) |
| RAG chunks document_name megjelenitese | KESZ | Screenshot #50 — forras oszlop mutatja a fajlnevet |
| ChatPanel full-height layout | KESZ | Screenshot #51-52 — calc(100vh-320px) |
| ChatPanel forrasok mindig lathatok | KESZ | Nem `<details>`, hanem mindig open szekco |
| RAG file perzisztencia | KESZ | data/uploads/rag/{collection_id}/ (nem temp) |
| Documents oszlopok i18n | KESZ | Screenshot #53-54 — HU/EN valt |
| Extractor Config dropdown | KESZ | Screenshot #53 — "Mind" dropdown a fejlecben |
| Document DELETE backend | KESZ | DELETE /delete/{id} → 204, tesztelve curl-lel |
| Mermaid render komponens | KESZ (KOD) | MermaidDiagram + mermaid.render() — E2E NEM tesztelve |

## HATRALEVO feladatok (kovetkezo session)

### ROVID TAV — 1-2 ora

#### 1. Dokumentacio fix (30 perc) — KRITIKUS
- CLAUDE.md: port 8100 → 8101 (tobb helyen)
- F1_DOCUMENT_EXTRACTOR_JOURNEY.md: port 8100→8101, frontend 5174→5173
- F3_RAG_ENGINE_JOURNEY.md: port 8100→8101, frontend 5174→5173
- 22_API_SPECIFICATION.md: 5 uj endpoint dokumentalasa (export/csv, export/json, delete, by-id, extractor/configs)
- 43_UI_RATIONALIZATION_PLAN.md: oldalszam 14→16

#### 2. UI torles gombok (45 perc) — HIANYZIK, backend KESZ
- Documents lista: DELETE ikon/gomb minden sorban
  - Backend: `DELETE /api/v1/documents/delete/{id}` MAR KESZ es tesztelve!
  - Frontend: Documents.tsx-ben uj oszlop vagy a Verify gomb melle torles ikon
  - Megerosito dialog: "Biztosan torli ezt a dokumentumot?"
- RAG collections lista: DELETE gomb
  - Backend: `DELETE /api/v1/rag/collections/{id}` MAR KESZ!
  - Frontend: Rag.tsx collection tablaban torles gomb
- E2E teszt: torles → listabol eltűnik + DB-bol is torlodik

#### 3. Mermaid E2E teszt (15 perc) — KOD KESZ, NINCS E2E TESZT
- Playwright: navigate /process-docs → szoveg beiras → "Generate Diagram" → varakoazas
- Ellenorzes: a jobb oldalon vizualis SVG megjelenik (nem szoveges Mermaid kod)
- Ha nem renderel: MermaidDiagram komponens debug (mermaid.render hiba?)

### KOZEP TAV — 3-5 ora

#### 4. Document Detail oldal (60 perc) — TELJESEN HIANYZIK
- Uj fajl: `pages-new/DocumentDetail.tsx`
- Route: `/documents/{id}/show`
- Journey step 5 szerint: 3 oszlopos layout (fejlec, szallito, vevo)
- Tetelsor tablazat (invoice_line_items)
- Validacio szekció (errors, confidence)
- "Verify" gomb → navigacio `/documents/{id}/verify`

#### 5. LLM cost tracking (45 perc) — NEM MUKODIK
- Jelenlegi: invoice_processor nem irja be a GPT API koltsseget a workflow_runs-ba
- Szukseges: token count * model rate → total_cost_usd mezo kitoltese
- Erintett fajlok: skills/invoice_processor/workflows/process.py (extract step), documents.py (run create)

#### 6. RAG Collection stats KPI bovites (30 perc) — RESZBEN KESZ
- Backend: GET /rag/collections/{id}/stats MAR LETEZIK (query count, avg time, feedback)
- Frontend RagDetail.tsx: jelenleg csak doc_count + chunk_count KPI
- Bovites: query_count, avg_response_time, thumbs_up/down kartyak

#### 7. Document kereses/szures bovites (60 perc)
- Jelenlegi: globalis string kereses a DataTable-ben
- Szukseges: vendor szuro, datum range, osszeg range, config szuro
- Opcionalis: backend query filter (?vendor=X&date_from=Y)

### HOSSZU TAV — 1-2 nap

#### 8. Email Upload implementacio (2-3 ora)
- .eml/.msg fajl parser backend
- Email torzs + csatolmanyok kinyerese
- Intent classification integracio

#### 9. Audit log valos esemeny rogzites (60 perc)
- Minden API muvelet (create/update/delete) audit bejegyzest general
- AuditTrailService.log_event() hivasok az endpointokba

#### 10. Production deployment (2-3 ora)
- Docker Compose production profil
- Nginx reverse proxy
- JWT RS256 kulcs generalas (jelenleg dev HS256 secret)
- .env.production sablon

---

## Hasznos parancsok a session inditasahoz

```bash
# Infrastruktura inditasa
docker compose up -d

# API inditasa
cd "C:\Users\kassaiattila\OneDrive - BestIxCom Kft\00_BESTIX_KFT\11_DEV\80_Sample_Projects\07_AI_Flow_Framwork"
.venv/Scripts/python.exe -m uvicorn aiflow.api.app:create_app --factory --port 8101

# Frontend inditasa
cd aiflow-admin && npm run dev

# API teszt
curl -s http://localhost:8101/health | python -m json.tool

# Login token keres
TOKEN=$(curl -s -X POST http://localhost:8101/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin@bestix.hu","password":"admin"}' | python -c "import sys,json; print(json.load(sys.stdin)['token'])")

# Dokumentumok
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8101/api/v1/documents | python -c "import sys,json; print(json.load(sys.stdin)['total'])"

# RAG kollekcio
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8101/api/v1/rag/collections | python -m json.tool
```

---

## Fajl referencia (legfontosabb)

### Frontend (aiflow-admin/src/)
| Fajl | Szerepe |
|------|---------|
| pages-new/Dashboard.tsx | Fo dashboard KPI-kkal |
| pages-new/Documents.tsx | Dokumentum lista + upload + export |
| pages-new/Verification.tsx | Split-screen PDF verify (921 sor) |
| pages-new/Rag.tsx | RAG kollekcio lista + chat + uj kollekcio dialog |
| pages-new/RagDetail.tsx | Kollekcio reszletei: Ingest/Chat/Chunks |
| components-new/ChatPanel.tsx | Ujrahasznalhato RAG chat |
| components-new/DataTable.tsx | Altalanos tablazat (sort/search/page) |
| lib/api-client.ts | fetchApi, uploadFile, streamApi (auth-os) |
| lib/i18n.ts | useTranslate hook |
| locales/hu.json, en.json | Magyar/Angol forditasok |
| router.tsx | Osszes route definicio |

### Backend (src/aiflow/)
| Fajl | Szerepe |
|------|---------|
| api/v1/documents.py | Dokumentum CRUD + process + export + verify |
| api/v1/rag_engine.py | RAG CRUD + ingest + query + chunks |
| api/v1/admin.py | Users + API keys + audit + health |
| api/v1/runs.py | Workflow run lista + stats |
| api/v1/costs.py | Koltseg osszesites |
| services/rag_engine/service.py | RAG pipeline (Docling+Embed+Search+LLM) |
| api/middleware.py | JWT/API key auth middleware |
| api/deps.py | DB engine/pool singleton |

### Terv dokumentumok
| Fajl | Tartalom |
|------|----------|
| 01_PLAN/44_E2E_BUGFIX_UX_REDESIGN.md | Aktualis fejlesztesi terv (F1-F6) |
| 01_PLAN/45_NEXT_SESSION_PROMPT.md | EZ A FAJL — kovetkezo session kontextus |
| 01_PLAN/F1_DOCUMENT_EXTRACTOR_JOURNEY.md | Dokumentum feldolgozo user journey |
| 01_PLAN/F3_RAG_ENGINE_JOURNEY.md | RAG pipeline user journey |
