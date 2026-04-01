# AIFlow Session Restart — F3 RAG Engine (Figma + UI)

Masold be ezt a promptot uj Claude Code session indulaskor:

---

## Kontextus

AIFlow Enterprise AI Automation Framework — F3 RAG Engine fazisban vagyunk.
**FONTOS:** Hivatalos Figma MCP szerver lett telepitve (`https://mcp.figma.com/mcp`) — az elso Figma hivasnal OAuth login kell a bongeszben!

### Kiindulas

- **Git branch:** `main`
- **Utolso session (2026-04-01):** F3 backend KESZ + Figma redesign FOLYAMATBAN
- **F3 backend commit:** `b6890e3` — Alembic 018 + RAGEngineService + 12 API endpoint

### F3 Pipeline allaspont (12 lepesbol 7 KESZ)

```
Step 1: Elofeltetel          ✅ PASS
Step 2: Terv beolvasas       ✅ PASS
Step 3: Alembic 018          ✅ PASS (upgrade/downgrade/upgrade)
Step 4: RAGEngineService     ✅ PASS (import OK)
Step 5: API /api/v1/rag/*    ✅ PASS (12 route, 9/9 curl OK, source:"backend")
Step 6: Unit teszt           ✅ PASS (690 passed, 1 pre-existing flaky)
Step 7: Journey GATE         ✅ PASS (01_PLAN/F3_RAG_ENGINE_JOURNEY.md letezik)
--- BACKEND COMMIT KÉSZ: b6890e3 ---
Step 8: Figma design         ⚠️ FOLYAMATBAN — Figma finomitas kell!
Step 9: UI implementacio     ⏳ PENDING (Step 8 utan!)
Step 10: Playwright E2E      ⏳ PENDING
Step 11: Backward compat     ⏳ PENDING
Step 12: Git tag              ⏳ PENDING
```

### Mi keszult el eddig (F0-F3 backend)

```
alembic/versions/018_extend_rag_collections.py     # F3 migracio
src/aiflow/services/rag_engine/                      # RAGEngineService
  __init__.py, service.py                            # CRUD + ingest + query + feedback + stats
src/aiflow/api/v1/rag_engine.py                     # 12 endpoint
src/aiflow/api/app.py                               # rag_router regisztralva

01_PLAN/F1_DOCUMENT_EXTRACTOR_JOURNEY.md             # Gate 1 retroaktiv
01_PLAN/F2_EMAIL_CONNECTOR_JOURNEY.md                # Gate 1 retroaktiv  
01_PLAN/F3_RAG_ENGINE_JOURNEY.md                     # Gate 1 PASS

aiflow-admin/figma-sync/PAGE_SPECS.md                # Figma node registry + Document atnevezes
```

### FIGMA ALLAPOT (KRITIKUS — ez a fo feladat!)

**Hivatalos Figma MCP:** `https://mcp.figma.com/mcp` (HTTP, OAuth auth)
- Az elso hivasnal bongeszben Figma OAuth login szukseges
- Regi MCP (ClaudeTalkToFigma) WebSocket-tel mukodott de timeout-olt nagy frame-eknel

**13 AIFlow Figma oldal letezik:**

| Oldal | Figma Page ID | Allapot |
|-------|--------------|---------|
| Dashboard | `11638:24254` | Runs layout klonozva, szoveg csere KELL |
| Runs | `11623:13186` | ✅ JO (Untitled UI) |
| Documents | `11623:13187` | ✅ Szovegek frissitve (Invoice→Document) |
| Emails | `11623:13188` | ✅ JO (Untitled UI) |
| Costs | `11623:13189` | ✅ JO (Untitled UI) |
| Process Docs | `11625:10531` | ✅ JO (Untitled UI) |
| RAG Chat | `11625:10532` | ✅ JO (Untitled UI) — F3 collection selector kell |
| Document Upload | `11625:10533` | ✅ Szovegek frissitve |
| Verification | `11625:10534` | ✅ JO (Untitled UI) |
| Email Connectors | `11638:24255` | ⚠️ WIREFRAME — Untitled UI komponensek kellenek |
| Email Detail | `11638:24256` | ⚠️ WIREFRAME — szekciok szoveggel, nincs komponens |
| Email Upload | `11638:24257` | ⚠️ WIREFRAME — upload zona szoveggel |
| RAG Collections | `11638:24258` | ⚠️ WIREFRAME — collection lista szoveggel |

**FELADAT:** Az 5 wireframe oldalt (Dashboard, Email Connectors, Email Detail, Email Upload, RAG Collections) professzionalis szintre hozni valodi Untitled UI komponensekkel:
- Sidebar: klonozni a Runs oldalrol (`11623:11465`)
- Tablak: klonozni a Documents/Runs tabla komponenst
- Gombok, badge-ek, inputok: Untitled UI component instance-ok
- Minden oldalon: Loading / Error / Empty state design

### Szerverek inditasa

```bash
docker compose up -d db redis
.venv/Scripts/python -m uvicorn aiflow.api.app:create_app --factory --port 8100
cd aiflow-admin && npx vite --port 5174
```

### FO FELADATOK (sorrendben!)

1. **Figma finomitas** — Az 5 wireframe oldal professzionalis redesign-ja a hivatalos Figma MCP-vel
   - Dashboard: KPI cards + skill cards + active pipelines
   - Email Connectors: tabla + CRUD dialog + action buttons
   - Email Detail: 2-column layout szekciokkal (intent, routing, entities, attachments)
   - Email Upload: drag-drop zona + processing pipeline + result cards
   - RAG Collections: collection tabla + create dialog + ingest zona
   - RAG Chat: collection selector dropdown + role selector hozzaadasa

2. **Step 9: UI implementacio** — CSAK ha Step 8 Figma design PASS
   - CollectionManager.tsx (uj)
   - RagChat.tsx redesign (collection selector + feedback wiring)
   
3. **Step 10: Playwright E2E** — valos backend-del

4. **Step 11-12:** Backward compat + git tag `v0.11.0-rag-engine`

### API ENDPOINTOK (F3 — mar KESZEN vannak!)

```
GET    /api/v1/rag/collections              # Lista
POST   /api/v1/rag/collections              # Letrehozas
GET    /api/v1/rag/collections/{id}         # Reszletezio
PUT    /api/v1/rag/collections/{id}         # Modositas
DELETE /api/v1/rag/collections/{id}         # Torles
POST   /api/v1/rag/collections/{id}/ingest  # Dokumentum ingest
GET    /api/v1/rag/collections/{id}/ingest-status
POST   /api/v1/rag/collections/{id}/query   # RAG kerdes
POST   /api/v1/rag/collections/{id}/feedback # Feedback
GET    /api/v1/rag/collections/{id}/stats   # Statisztikak
GET    /api/v1/rag/collections/{id}/chunks  # Chunk lista
DELETE /api/v1/rag/collections/{id}/chunks/{chunk_id}
```

### KRITIKUS SZABALYOK

1. **Hivatalos Figma MCP:** `https://mcp.figma.com/mcp` — OAuth login az elso hivasnal
2. **7 HARD GATE pipeline:** Step 8 (Figma) PASS kell Step 9 (UI kod) elott!
3. **Figma minoseg:** Valodi Untitled UI komponensek, NEM szoveges placeholder-ek!
4. **VALOS TESZTELES:** Playwright E2E + curl + valos DB — SOHA ne mock!
5. **Document, NEM Invoice:** F1 UI atnevezes KESZ
6. **Journey fajlok:** F1+F2+F3 KESZEK (`01_PLAN/F{X}_*_JOURNEY.md`)

---
