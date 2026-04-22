# AIFlow v1.4.6 Sprint J — Session 102 Prompt (UC2 RAG UI: Rag.tsx + RagDetail.tsx + ChunkViewer)

> **Datum:** 2026-04-24 (tervezett folytatás)
> **Branch:** `feature/v1.4.6-rag-chat` — folytasd ugyanezen.
> **HEAD prereq:** `953e7cd` — `feat(sprint_j): S101 — UC2 RAG Parser→Chunker→Embedder wiring + ChunkerProvider`.
> **Port:** API 8102 | Frontend Vite :5174
> **Plan:** `01_PLAN/110_USE_CASE_FIRST_REPLAN.md` §4 Sprint J third row (UI UC2 = S102).
> **Session tipus:** UI IMPLEMENTATION — 7 HARD GATE pipeline (aiflow-ui-pipeline skill). Untitled UI + Tailwind v4 + React Aria. Code risk: MEDIUM. Process risk: LOW (nincs backend változás).

---

## KONTEXTUS

### Honnan jöttünk

- **S100 ZÁRVA (9b3c610):** `EmbedderProvider` ABC + BGE-M3 (Profile A) + Azure OpenAI (Profile B) + `EmbeddingDecision` contract + `PolicyEngine.pick_embedder` + alembic 040 `embedding_decisions`.
- **S101 ZÁRVA (953e7cd):** `ChunkResult` contract + `ChunkerProvider` ABC (5. registry slot) + `UnstructuredChunker` (tiktoken cl100k_base, 512/50) + `rag_engine.ingest_documents` opt-in provider-registry path (`use_provider_registry=True`) + alembic 041 `rag_chunks.embedding_dim` + `set_embedder_provider_override()` test hook + 2 integration tesztek (real Docker PG, fake 1536-dim embedder).
- Counts: 1993 unit PASS / 2 skip (+23), 55 integration PASS (+4), 410 E2E collected, ruff clean, alembic head 041, no OpenAPI drift.
- **NYITOTT S101-ből:** retrieval baseline (`test_retrieval_baseline.py`) DEFERRED — Profile A `sentence_transformers` hiányzik, Profile B `AIFLOW_AZURE_OPENAI__*` env nincs beállítva. S102 NEM blokkolja; UI query a legacy path-ot hívja (default `use_provider_registry=False`).

### Hova tartunk — Sprint J harmadik sora (UI)

- **Cél:** `aiflow-admin/` admin dashboard-on UC2 RAG két oldala — `Rag.tsx` (collections list) + `RagDetail.tsx` (collection-level details + dokumentumok + chunk viewer). Aktiválja az S100+S101 backend flow-t a felhasználó szemszögéből.
- Acceptance: Playwright E2E (169 pre-existing + 199 Phase 1a + 35 Phase 1b + 7 Phase 1d = 410 → cél ≥415) PASS, **Rag oldal összes CTA működik real adattal** (collection create, docs upload, query, feedback).
- **A feature is DONE only after Playwright E2E passes with real data** (CLAUDE.md IMPORTANT rule).

### Jelenlegi állapot (induláskor várt)

```
27 service | 181 endpoint | 50 DB tábla | 41 Alembic migration (head: 041)
1993 unit PASS / 0 FAIL / 2 SKIP | 410 E2E collected | 55 integration PASS
0 ruff error | 0 ts error
Branch: feature/v1.4.6-rag-chat (3 commit ahead of main)
```

---

## ELŐFELTÉTELEK

```bash
git branch --show-current                                              # feature/v1.4.6-rag-chat
git log --oneline -3                                                   # HEAD: 953e7cd
.venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov             # 1993 PASS / 2 SKIP
.venv/Scripts/python.exe -m ruff check src/ tests/ --quiet             # exit 0
PYTHONPATH=src .venv/Scripts/python.exe -m alembic current             # 041
docker ps --filter "name=07_ai_flow_framwork" --format "table {{.Names}}\t{{.Status}}"
# db + redis healthy — ha nem: docker compose up -d db redis
cd aiflow-admin && npx tsc --noEmit && cd ..                           # 0 error baseline
```

---

## 7 HARD GATE (aiflow-ui-pipeline skill — KÖTELEZŐ, NE skip!)

A skill automatikusan betöltődik amikor UI munkát kezdünk. Az alábbi 7 gate mindegyikét ÁT KELL MENNI sorrendben, mielőtt a következő GATE lépésbe mész:

1. **Journey (`/ui-journey`):** Felhasználói útvonal definíció — user → Rag list → create collection → upload docs → query → feedback. Minden CTA-nak kellene működnie. ACCEPTANCE: `01_PLAN/` alá mentett journey doc.
2. **API endpoints (`/ui-api-endpoint`):** Ellenőrizd a meglévő `/api/v1/rag_engine/*` útvonalakat. Ha hiányzik endpoint (pl. chunk-level browse), generáld. SOHA ne mock silent — minden válaszban `source: "live" | "demo"` tag.
3. **Figma design (`/ui-design`):** Real Untitled UI komponensekkel (SOHA placeholder wireframe). `feedback_figma_quality` memória szerint Step 8-nál minőség-check.
4. **Page (`/ui-page`) + Component (`/ui-component`):** `aiflow-admin/src/pages/Rag.tsx` + `aiflow-admin/src/pages/RagDetail.tsx` + új `ChunkViewer.tsx` komponens. React 19 + Tailwind v4 + Untitled UI.
5. **Viewer (`/ui-viewer`):** ha skill-specifikus result viewer kell (chunk+similarity megjelenítés) — opcionális.
6. **Physical `ls` file checks** (NEM grep) minden gate után — `feedback_gate_enforcement` memória szerint.
7. **Playwright E2E** (FULL pipeline gyakorlás): collection create → PDF upload (valós fájl) → query → feedback. Nem csak empty list page (`feedback_real_e2e_testing`).

---

## FELADATOK

### LÉPÉS 1 — Journey + Endpoints audit (`/ui-journey` + `/ui-api-endpoint`)

- Definiáld a UC2 RAG user journey-t `01_PLAN/UC2_RAG_USER_JOURNEY.md`-ben:
  1. Admin megnyitja a "RAG" menüpontot → `Rag.tsx` (collections list).
  2. "New Collection" CTA → modal → POST `/api/v1/rag_engine/collections`.
  3. Sor kattintás → `RagDetail.tsx` — collection info + dokumentumok grid + chunks viewer.
  4. "Upload documents" CTA → multi-file → POST `/api/v1/rag_engine/collections/{id}/ingest`.
  5. Query box → POST `/api/v1/rag_engine/collections/{id}/query` → válasz + sources.
  6. Feedback (👍/👎) → POST `/api/v1/rag_engine/feedback`.
- Auditáld: minden endpoint létezik (`src/aiflow/api/v1/rag_engine.py`)? Ha hiányzik chunk-level browse (pl. `GET /collections/{id}/chunks?page=...`) — generáld.

**Exit:** Journey doc committed, endpoint audit eredmény (minden OK vagy list of gaps).

### LÉPÉS 2 — `Rag.tsx` — Collections list page

Hely: `aiflow-admin/src/pages/Rag.tsx` (új vagy meglévő).

- Untitled UI Table komponens (collection sor): name, language, document_count, chunk_count, last_ingest_at, actions (view / delete).
- Top-right "New Collection" CTA → Dialog (Untitled UI) form: name*, description, language (select: hu/en), embedding_model (select, alapértelmezett `openai/text-embedding-3-small`).
- Empty state: Untitled UI EmptyState + "Create your first collection" CTA.
- Live/Demo tag a header-ben a `source` flag alapján.

**Exit:** Page renderel valós API-ról, "New Collection" CTA létrehoz, sor kattintás navigál `/rag/{id}`-re.

### LÉPÉS 3 — `RagDetail.tsx` — Collection detail + chunks viewer

Hely: `aiflow-admin/src/pages/RagDetail.tsx` (új).

- Header: collection name, language, document_count, chunk_count, embedding_model, last_ingest_at.
- Tabs (React Aria Tabs):
  1. **Documents** — uploaded fájlok listája + "Upload" CTA (multi-file).
  2. **Query** — text input + top_k slider + role select (expert/assistant) + "Ask" CTA → válasz card + sources accordion.
  3. **Chunks** — `ChunkViewer.tsx` — pageable table: chunk_index, document_name, text (trunc 200 char), token_count, embedding_dim (S101 új mező!). Sor click → modal teljes szöveggel.
  4. **Feedback** — recent feedback timeline.

**Exit:** Minden 4 tab működik valós adattal; Upload CTA végigmegy az ingest-en; Query CTA teljesít LLM választ; ChunkViewer oldalaz 25-ös page size-ban.

### LÉPÉS 4 — `ChunkViewer.tsx` komponens

Hely: `aiflow-admin/src/components/rag/ChunkViewer.tsx` (új).

- Props: `collectionId: string`, `pageSize?: number = 25`.
- React Aria Table + Pagination. Data fetch: `GET /api/v1/rag_engine/collections/{id}/chunks?page=N&size=M`.
- Renderel: chunk_index, document_name, text (`line-clamp-3`), token_count, embedding_dim badge.
- Row click → Untitled UI Modal full text + metadata JSON.
- Loading skeleton, empty state, error state mindhárom valós.

**Exit:** Komponens 100% typescript clean, Storybook-kompatibilis (csak ha a repo használja).

### LÉPÉS 5 — Playwright E2E (CRITICAL)

Hely: `tests/ui/rag/test_rag_uc2.spec.ts` (új) vagy meglévő E2E suite bővítés.

- **Golden path:** Login → /rag → "New Collection" → create (valós DB row) → navigate detail → upload 1 PDF (e2e-audit/test-data/rag-docs/) → Query tab → kérdés ("Mit tartalmaz a biztosítás?") → válasz kapott + sources render → Chunks tab → látszik ≥1 chunk embedding_dim badge-dzsel → feedback 👍.
- **Edge cases:**
  - Empty collection → ChunkViewer empty state.
  - Delete collection → confirm modal → sor eltűnik.
- **No silent mock!** `feedback_no_silent_mock` + `feedback_real_e2e_testing` memóriák szerint.

**Exit:** E2E PASS Playwright-ben, 410 → ≥415 collected.

### LÉPÉS 6 — Regression + session-close

```bash
.venv/Scripts/python.exe -m ruff check src/ tests/ --quiet
cd aiflow-admin && npx tsc --noEmit && cd ..
.venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov                        # 1993+ PASS
.venv/Scripts/python.exe -m pytest tests/integration/services/rag_engine/         # 2 PASS
.venv/Scripts/python.exe -m pytest tests/e2e/ --collect-only -q                   # 415+
npx playwright test tests/ui/rag/                                                 # NEW E2E green
PYTHONPATH=src .venv/Scripts/python.exe scripts/export_openapi.py                 # drift check

/session-close S102
```

---

## STOP FELTÉTELEK

- **HARD:** Backend endpoint hiányzik a journey-ből és nem triviális hozzáadni (pl. `/collections/{id}/chunks?page=...` komplex SQL) → zárd LÉPÉS 1-2 után, chunk viewer-t deferráld S103-ra.
- **HARD:** Untitled UI komponens hiányzik Figma MCP-ben — SOHA NE placeholder wireframe (`feedback_figma_quality`). Kérdezd a usert.
- **HARD:** Playwright E2E >2 próba után FAIL a golden path-on → debug-old root cause (`feedback_real_e2e_testing`), ne skip-eld.
- **HARD:** TypeScript error az `aiflow-admin/`-ban amit nem tudsz 2 próba után fix-elni.
- **SOFT:** Ha a retrieval minőség (query tab) a legacy OpenAI path-on gyenge (top-k nem releváns) — NE változtass a backend flow-n S102-ben, ütemezd a Profile A bootstrap + baseline munkát S103-ra.

---

## NYITOTT TECHNIKAI ADÓSSÁG (S102-be nem visszük)

- **Retrieval baseline (`tests/fixtures/rag/baseline_2026_04_23.json` + `test_retrieval_baseline.py`):** Profile A `sentence_transformers` install + BGE-M3 model cache (>500MB) → külön kickoff session S103-ban.
- **pgvector flex-dim:** `rag_chunks.embedding vector(1536)` jelenleg fix; BGE-M3 (1024) nem fér el. S103+ alembic migration az `embedding vector(1024)` külön táblával (multi-collection per-dim) vagy `VECTOR` dinamikus dim (pgvector 0.7+ feature check).

---

## SESSION VÉGÉN

```
/session-close S102
```

Utána `/clear` és S103 (Profile A bootstrap + retrieval baseline + pgvector flex-dim, a backend stabilizálása mielőtt Sprint J-t zárjuk).
