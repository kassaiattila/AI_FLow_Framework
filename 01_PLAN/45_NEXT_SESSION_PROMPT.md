# AIFlow v1.1.3 — Következő Session Prompt

> **Datum:** 2026-04-03 (3. session)
> **Előző session:** 25 commit, 32 fajl, 3440+ sor, teljes feature + bug fix sprint
> **Branch:** main (bed4efc)
> **Port:** API 8102-n fut (8101 zombie socket). Vite proxy `vite.config.ts`-ben átállítva 8102-re.

---

## FONTOS: Szerver indítás

```bash
# A 8101 porton zombie processek lehetnek (Windows ghost socket)
# Használd a 8102 portot:
.venv\Scripts\python.exe -B -m uvicorn aiflow.api.app:create_app --factory --port 8102

# Frontend (vite.config.ts proxy → 8102)
cd aiflow-admin && npm run dev

# Ha a 8101 felszabadul, állítsd vissza a vite.config.ts-t 8101-re
```

---

## Elvégzett munka (ebben a session-ben)

### Features (25 commit)
1. DELETE gombok (Documents + RAG) + confirm dialog
2. DataTable multi-select (checkbox, select all, bulk action bar)
3. Documents + RAG bulk delete (backend POST /delete-bulk + frontend)
4. RAG ingested documents DataTable + single/bulk delete
5. Document Detail oldal (`/documents/:id/show`) — 3 oszlop, line items, totals
6. LLM cost tracking — token count a process pipeline-ból → cost_records DB
7. RAG Collection stats KPI bővítés (5 kártya: docs, chunks, queries, avg time, feedback)
8. Costs oldal redesign — model/token breakdown tábla + daily cost bar chart
9. RAG ingest SSE progress bar (valós lépésenként: upload→parse→chunk→embed→store)
10. Persistent cost recording (cost_recorder.py → cost_records tábla)
11. Docling nagy PDF fallback (max_pages=50 → Azure DI → pypdfium2)
12. Audit log valós CRUD események (delete/bulk_delete → audit_log tábla)
13. Figma sync (7 frame frissítve valós tartalommal)

### Bug fixek
- DELETE 204 No Content parse bug (api-client.ts)
- documents/by-id source kwarg duplikálás
- DataTable onSelectionChange infinite re-render loop (useRef fix)
- Verification PDF kép auth (fetchApi blob URL)
- cost_records FK constraint (workflow_run_id nullable, FK dropped)
- Table overflow/scroll (truncate + max-width)
- Cubix viewer auth header
- Dokumentáció port fix (8100→8101), API spec +7 endpoint, oldalszám 14→16

---

## HÁTRALEVŐ FELADATOK (prioritás sorrendben)

### 1. Document process: fájlonkénti progress (NEM fázisonkénti)
**Probléma:** A jelenlegi SSE progress bar fázisonként halad (parse→classify→extract→validate→store→export), de ha 5 fájl van, mind 5-öt egyszerre dolgozza fel fázisonként.
**Elvárt:** Fájlonkénti haladás: `file1: parse→extract→store ✓`, `file2: parse→extract... ▶`, `file3: pending`
**Érintett fájlok:**
- `src/aiflow/api/v1/documents.py` (process-stream SSE endpoint, ~250-390. sor)
- `aiflow-admin/src/pages-new/Documents.tsx` (UploadTab, steps state, progress bar render)
**Megoldás:** A backend-ben fájlonként futtatni a pipeline-t és SSE event-et küldeni: `{"event": "file_start", "file": "invoice_001.pdf", "step": 0}` ... `{"event": "file_done", "file": "invoice_001.pdf"}`. A frontend-en per-file progress grid.

### 2. Verification: overlay auto-hide + szép toggle kapcsoló
**Probléma:**
- A bal oldali PDF kép nézetnél ("real image" mód) a bounding box overlay-ek zavaróak és pontatlanok → automatikusan el kell tüntetni real image módban
- A Real/Mock váltó gombok és az overlay módok (All/Low/Off) jelenleg egyszerű gombok → szép toggle switch-ként kell megvalósítani
**Érintett fájlok:**
- `aiflow-admin/src/pages-new/Verification.tsx` (overlay logic ~140-155. sor, toggle render ~220-250. sor)
**Megoldás:** 
- `viewMode === "real"` esetén `filteredPoints = []` (nincs overlay)
- Toggle switch komponens: `<label className="relative inline-flex items-center cursor-pointer"><input type="checkbox" className="sr-only peer" /><div className="w-11 h-6 bg-gray-200 peer-checked:bg-brand-500 rounded-full" /></label>`

### 3. Admin Figma frame frissítés
- A scan timeout-olt az előző session-ben
- Frame ID: `11662:113180`
- Tartalom: "Users & Keys", users tábla, API keys tábla

### 4. Egyéb design finomítások
- A Documents tábla jobb oldali oszlopai (Verify + Delete gombok) még mindig szorosan vannak laptop méreten
- A RAG Chat tab-on a forrás hivatkozások formázása javítható

---

## Jelenlegi rendszer állapot

### Infrastruktúra
- PostgreSQL 5433 (Docker), Redis 6379 (Docker)
- API: port 8102 (`-B` flag a pyc cache kihagyásához)
- Frontend: port 5173 (Vite, proxy → 8102)
- Auth: admin@bestix.hu / admin, localStorage key: `aiflow_token`
- Azure DI: konfigurálva (.env: AZURE_DI_ENDPOINT, AZURE_DI_API_KEY, AZURE_DI_ENABLED=true)
- Figma MCP channel: `6c582ayf`

### DB adatok
| Tábla | Rekord |
|-------|--------|
| invoices | ~7 (session közben töröltek miatt csökkent) |
| workflow_runs | 13+ |
| rag_collections | 5 |
| rag_chunks | ~4900 |
| generated_diagrams | 11+ |
| cost_records | frissen létrehozva, FK constraint eltávolítva |
| audit_log | CRUD események rögzítve |

### Tesztadatok
- `e2e-audit/test-data/invoices/` (3 PDF)
- `e2e-audit/test-data/rag-docs/` (50+ Allianz PDF)

---

## Fájl referencia (legfontosabb módosított fájlok)

### Frontend
| Fájl | Szerep |
|------|--------|
| `components-new/DataTable.tsx` | Multi-select, checkbox, bulk action support |
| `pages-new/Documents.tsx` | Bulk delete, selectable, row→Detail navigáció |
| `pages-new/DocumentDetail.tsx` | ÚJ: 3 oszlop layout, line items, totals |
| `pages-new/Rag.tsx` | Bulk delete, selectable collections |
| `pages-new/RagDetail.tsx` | SSE ingest progress, ingested docs DataTable, 5 KPI |
| `pages-new/Costs.tsx` | Daily chart, model/token breakdown tábla |
| `pages-new/Verification.tsx` | PDF auth fix (fetchApi blob URL) |
| `lib/api-client.ts` | 204 No Content fix |

### Backend
| Fájl | Szerep |
|------|--------|
| `api/cost_recorder.py` | ÚJ: record_cost() → cost_records (FK nullable) |
| `api/audit_helper.py` | ÚJ: audit_log() → audit_log tábla |
| `api/v1/documents.py` | Bulk delete, cost recording, audit log |
| `api/v1/rag_engine.py` | SSE ingest-stream, doc list/delete, bulk delete, cost recording |
| `api/v1/costs.py` | /breakdown endpoint (model/token aggregáció) |
| `api/v1/process_docs.py` | BPMN cost recording |
| `ingestion/parsers/docling_parser.py` | max_pages + Azure DI fallback + pypdfium2 |

### Hasznos parancsok
```bash
# Login token
TOKEN=$(curl -s -X POST http://localhost:8102/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin@bestix.hu","password":"admin"}' | python -c "import sys,json; print(json.load(sys.stdin)['token'])")

# Quick health
curl -s http://localhost:8102/health | python -m json.tool

# Cost breakdown
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8102/api/v1/costs/breakdown | python -m json.tool

# RAG collection docs
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8102/api/v1/rag/collections/{id}/documents | python -m json.tool
```
