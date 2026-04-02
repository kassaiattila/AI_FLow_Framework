# F3 RAG Engine — User Journey

> **Fazis:** F3 (RAG Engine)
> **Forras skill:** `skills/aszf_rag_chat/` (86% eval pass)
> **Service:** `src/aiflow/services/rag_engine/` (UJ)
> **API:** `src/aiflow/api/v1/rag_engine.py` (UJ)
> **Letezo modulok:** `src/aiflow/vectorstore/`, `src/aiflow/ingestion/`, `api/v1/chat_completions.py`, `api/v1/feedback.py`
> **UI:** `aiflow-admin/src/pages/RagChat.tsx` (ATALAKITAS) + uj oldalak
> **Tag:** `v0.11.0-rag-engine`

---

## Actor

**Tudasbazis kezeleo / Domain expert** — dokumentumgyujtemenyeket (jogszabalyok, belso szabalyzatok, technikai dokumentaciok) tolt fel a rendszerbe, kollekciot konfigural, es a RAG chat-en keresztul kerdez. Ellenorzi az AI valaszok minosseget feedback-kel, es figyeli a statisztikakat. Nem fejleszto, de a szakterulet szakertoje.

## Goal

Barmilyen dokumentumgyujtemenyt tudasbazissa alakitani: kollekcio letrehozas → dokumentumok feltoltese (ingest) → hibrid kereseses RAG chat → felhasznaloi feedback → minosegi statisztikak — egyetlen admin feluletrol, tobbfele kollekcio parhuzamos kezelesevel.

## Preconditions

- FastAPI backend fut (`localhost:8100`), PostgreSQL + pgvector + Redis Docker-ben
- Alembic migraciok lefutottak (001-017 + uj F3 migraciok: `collections`, `chunks`)
- HybridSearchEngine mukodik (pgvector HNSW + BM25 tsvector + RRF)
- Embedder konfiguralt (default: OpenAI `text-embedding-3-small`)
- LLM elerheto (default: `openai/gpt-4o`)
- Vite frontend fut (`localhost:5174`)

---

## Steps (User Journey)

### 1. Kollekcio letrehozas (Collection Manager oldal)

**URL:** `/rag` → **Collections** tab (v1.1 konszolidacio: `/rag/collections` → `/rag`)
**Felhasznalo:** Megnyitja a "RAG" oldalt a sidebar menubol (alapertelmezett: Collections tab).

- Latja a meglevo kollekcok listaját: nev, leiras, dok szam, chunk szam, letrehozva, statusz
- **Uj kollekcio:** "+ Uj kollekcio" gomb → dialog:
  - Nev (kotelezo, egyedi)
  - Leiras (opcionalis)
  - Nyelv (hu/en/auto)
  - Embedding modell (default: text-embedding-3-small)
- **API:** `POST /api/v1/rag/collections`
- **Eredmeny:** Uj kollekcio megjelenik a listaban, "ures" statuszban

### 2. Dokumentumok feltoltese (Ingestion)

**URL:** `/rag/{id}` (kollekcio reszletezo oldal, v1.1: `/rag/collections/{id}` → `/rag/{id}`)
**Felhasznalo:** A kollekcio sorara kattint, vagy "Ingest" gyors gomb.

- Drag-and-drop zona: PDF, DOCX, TXT, MD, XLSX fajlok (tobb fajl egyszerre)
- **API:** `POST /api/v1/rag/collections/{id}/ingest` (multipart form)
- Feldolgozasi pipeline fajlonkent:
  1. **Parse** — Docling (PDF/DOCX/XLSX) vagy plain text
  2. **Chunk** — RecursiveChunker (~2000 kar, 200 overlap)
  3. **Embed** — OpenAI text-embedding-3-small (batch)
  4. **Store** — PgVectorStore upsert (pgvector + tsvector)
- Valos ideju progress: fajlonkent statusz + chunk szam + idotartam
- **Eredmeny:** Kollekcio statisztikak frissulnek (dok szam, chunk szam)

### 3. Kollekcio statisztikak megtekintese

**URL:** `/rag/collections/{id}` (reszletezio oldal also resze)
**Felhasznalo:** A kollekcio reszletezio oldalon latja:

- **API:** `GET /api/v1/rag/collections/{id}/stats`
- KPI kartyak: dokumentum szam, chunk szam, osszes lekerdezeses szam, atlag valaszido
- Feedback osszesites: pozitiv/negativ arany, atlag ertekeles
- Koltseg: osszes es per-lekerdezeses koltseg
- Hallucination score eloszlas (ha volt query)

### 4. RAG Chat — kerdes feltevese

**URL:** `/rag/chat` (vagy `/rag/collections/{id}/chat`)
**Felhasznalo:** A "RAG Chat" oldalt nyitja meg.

- **Kollekcio valaszto:** legordulo menu az elerheto kollekcokkal
  - **API:** `GET /api/v1/rag/collections` (dinamikus lista)
- **Role valaszto:** baseline / mentor / expert (befolyasolja a valasz stilusat)
- **Preset kerdesek:** kollekcio-specifikus gyors kerdesek (opcionalis)
- Kerdes beírasa → Enter (Shift+Enter = uj sor)
- **API:** `POST /api/v1/rag/collections/{id}/query` (streaming SSE)
  - Request: `{question, role, top_k, stream: true}`
- Valos ideju RAG pipeline vizualizacio:
  1. Query rewrite (magyar szinonimak)
  2. Embedding (vektor generalas)
  3. Hybrid search (vector + BM25 + RRF)
  4. Context building (top-5 chunk)
  5. LLM generation (streaming)
  6. Hallucination check (grounding score)
- **Eredmeny:** AI valasz hivatkozasokkal ([1], [2], ...), forras dokumentumok, metaadatok

### 5. Valasz ertekeles (Feedback)

**Felhasznalo:** A valasz alatt feedback gombra kattint.

- Thumbs up / Thumbs down gombok (MINDEN valasznal)
- **API:** `POST /api/v1/rag/collections/{id}/feedback`
  - Request: `{query_id, thumbs_up: bool, comment: string | null}`
- Vizualis visszajelzes: gomb szin valtozas (kek = kivalasztott)
- A feedback a `rag_query_log` tabla-ba vagy kulon `feedback` tablaba kerul

### 6. Valasz metaadatok megtekintese

**Felhasznalo:** A valasz under latja a reszleteket.

- Feldolgozasi ido (ms)
- Token hasznalat (input + output)
- Koltseg (USD)
- Hallucination score (0.0 = hallucinated, 1.0 = fully grounded)
- Forras dokumentumok: nev, szekció, oldalszam, relevancia score

### 7. Chunk kezeles (admin, opcionalis)

**URL:** `/rag/collections/{id}/chunks`
**Felhasznalo:** Kollekcio admin megnezi / torli az egyes chunk-okat.

- **API:** `GET /api/v1/rag/collections/{id}/chunks?limit=50&offset=0`
- Tablazat: chunk_id, tartalom (elonezet), forras dokumentum, letrehozva
- Kereses chunk tartalomban
- Torles per-chunk: `DELETE /api/v1/rag/collections/{id}/chunks/{chunk_id}`

### 8. Kollekcio modositas / torles

**Felhasznalo:** A kollekcio listaban szerkesztes vagy torles.

- **Modositas:** `PUT /api/v1/rag/collections/{id}` (nev, leiras)
- **Torles:** `DELETE /api/v1/rag/collections/{id}` (CASCADE: chunks + query_log is torlodik)
  - Megerosito dialog: "Ez torolni fogja a kollekciot es az osszes benne levo dokumentumot. Biztosan?"

---

## API Endpoints (teljes lista — F3 uj endpointok)

### Collection CRUD
| # | Method | Path | Purpose |
|---|--------|------|---------|
| 1 | GET | `/api/v1/rag/collections` | Kollekcok listazasa |
| 2 | POST | `/api/v1/rag/collections` | Uj kollekcio letrehozas |
| 3 | GET | `/api/v1/rag/collections/{id}` | Kollekcio reszletezio |
| 4 | PUT | `/api/v1/rag/collections/{id}` | Kollekcio modositas |
| 5 | DELETE | `/api/v1/rag/collections/{id}` | Kollekcio torles (CASCADE) |

### Ingestion
| # | Method | Path | Purpose |
|---|--------|------|---------|
| 6 | POST | `/api/v1/rag/collections/{id}/ingest` | Dokumentumok feltoltese es feldolgozasa |
| 7 | GET | `/api/v1/rag/collections/{id}/ingest-status` | Feldolgozasi statusz |

### Query
| # | Method | Path | Purpose |
|---|--------|------|---------|
| 8 | POST | `/api/v1/rag/collections/{id}/query` | Kerdes (streaming SSE) |

### Feedback & Stats
| # | Method | Path | Purpose |
|---|--------|------|---------|
| 9 | POST | `/api/v1/rag/collections/{id}/feedback` | Valasz ertekeles |
| 10 | GET | `/api/v1/rag/collections/{id}/stats` | Kollekcio statisztikak |

### Chunks
| # | Method | Path | Purpose |
|---|--------|------|---------|
| 11 | GET | `/api/v1/rag/collections/{id}/chunks` | Chunk-ok listazasa (paginated) |
| 12 | DELETE | `/api/v1/rag/collections/{id}/chunks/{chunk_id}` | Chunk torles |

### Meglevo endpointok (ujrafelhasznalt)
| # | Method | Path | Purpose |
|---|--------|------|---------|
| 13 | POST | `/api/v1/chat/completions` | OpenAI-kompatibilis chat (frissites: kollekcio valasztas) |
| 14 | GET | `/api/v1/models` | Elerheto modellek (frissites: kollekcio lista) |
| 15 | GET | `/api/v1/feedback/stats` | Globalis feedback statisztikak |

## UI Pages

| Oldal | Route | Komponens | Fo funkció |
|-------|-------|-----------|------------|
| Collection Manager | `/rag/collections` | `CollectionManager.tsx` (UJ) | Kollekcio CRUD lista |
| Collection Detail | `/rag/collections/{id}` | `CollectionDetail.tsx` (UJ) | Ingest zona + stats + chunks |
| RAG Chat | `/rag/chat` | `RagChat.tsx` (ATALAKITAS) | Kollekcio valaszto + role + feedback wiring |

## Success Criteria

1. Kollekcio CRUD (create/list/update/delete) mukodik valos backend-del (`source: "backend"`)
2. PDF ingest: feltoltes → parse → chunk → embed → store — valos adattal
3. RAG query: kerdes → hibrid kereseses → LLM valasz hivatkozasokkal — valos adattal
4. Feedback gombok mukodnek: thumbs up/down → API POST → DB mentes
5. Kollekcio stats: query szam, atlag valaszido, feedback osszesites
6. Kollekcio valaszto a Chat UI-ban: dinamikus lista API-bol
7. Role valaszto (baseline/mentor/expert) befolyasolja a valaszt
8. Regi `aszf_rag_chat` skill backward kompatibilis (CLI mukodik)
9. Alembic migracio (collections + chunks tablak) hiba nelkul
10. HU/EN nyelv valtas MINDEN stringet frissit
11. 0 JavaScript konzol hiba
12. Playwright E2E: create collection → ingest PDF → query → feedback → stats — PASS

## Error Scenarios

| Hiba | UI viselkedes |
|------|--------------|
| Backend nem elerheto | Chat: "Backend offline" banner, lista: fallback demo |
| Kollekcio ures (nincs chunk) | Query: "A kollekcio ures. Tolts fel dokumentumokat eloszor." |
| Ingest sikertelen (rossz PDF) | Fajl sor: piros X + parser hiba, tobbi fajl folytatodik |
| LLM timeout | Valasz: "A valaszgeneralas idotullipesre futott. Probald ujra." |
| Embedding API hiba | Ingest: hiba az embed lepesnel, partial ingest mentve |
| Kollekcio nem talalhato | 404 redirect a collection manager-re |
| Hallucination score alacsony (<0.5) | Valasz: figyelmeztetei banner "Alacsony grounding score" |
| Feedback mentes sikertelen | Toaszt: "Feedback mentes sikertelen" (non-blocking) |

---

## Database Tables (F3 uj)

### `collections` (Alembic migracio)
| Mezo | Tipus | Leiras |
|------|-------|--------|
| id | UUID PK | Kollekcio azonosito |
| name | VARCHAR(255) UNIQUE | Kollekcio nev |
| description | TEXT | Leiras |
| language | VARCHAR(10) | Nyelv (hu/en/auto) |
| embedding_model | VARCHAR(255) | Embedding modell |
| chunk_config | JSONB | Chunking konfiguracio |
| doc_count | INTEGER | Dokumentum szam (denormalizalt) |
| chunk_count | INTEGER | Chunk szam (denormalizalt) |
| owner_id | UUID | Tulajdonos (FK → users, jovobeli) |
| created_at | TIMESTAMPTZ | Letrehozas |
| updated_at | TIMESTAMPTZ | Utolso modositas |

### `rag_query_log` bovites
| Mezo | Tipus | Leiras |
|------|-------|--------|
| collection_id | UUID FK | Kollekcio referencia (UJ mezo) |

### `feedback` (uj tabla VAGY `rag_query_log` bovites)
| Mezo | Tipus | Leiras |
|------|-------|--------|
| id | UUID PK | Feedback azonosito |
| query_id | UUID FK | Query referencia |
| collection_id | UUID FK | Kollekcio referencia |
| thumbs_up | BOOLEAN | Pozitiv/negativ |
| comment | TEXT | Opcionalis megjegyzes |
| created_at | TIMESTAMPTZ | Idopont |

## Service Dependencies

- **RAGEngineService** (`src/aiflow/services/rag_engine/`) — UJ, kollekcio CRUD + ingest + query
- **HybridSearchEngine** (`src/aiflow/vectorstore/`) — Meglevo, ujrafelhasznalt (vektor + BM25 + RRF)
- **Embedder** (`src/aiflow/vectorstore/embedder.py`) — Meglevo, text-embedding-3-small
- **IngestionPipeline** (`src/aiflow/ingestion/`) — Meglevo, Docling + chunkers
- **ModelClient** (`src/aiflow/models/`) — Meglevo, LLM hivasok (LiteLLM)
- **aszf_rag_chat** (`skills/aszf_rag_chat/`) — Forras skill, backward compat
- **PostgreSQL + pgvector** — Chunk tarolasa + hibrid kereses
- **Redis** — Cache (opcionalis, query eredmenyek cache)

## Meglevo modulok ujrafelhasznalasa

| Modul | Hol | Mire hasznalja F3 |
|-------|-----|-------------------|
| `vectorstore/search.py` | HybridSearchEngine | Kereseses (valtozatlan) |
| `vectorstore/pgvector.py` | PgVectorStore | Chunk tarolas + kereseses |
| `vectorstore/embedder.py` | Embedder | Szoveg → vektor |
| `ingestion/parsers/` | DoclingParser | PDF/DOCX parse |
| `ingestion/chunkers/` | RecursiveChunker | Szoveg darabolás |
| `api/v1/chat_completions.py` | POST /v1/chat/completions | OpenAI-kompatibilis chat |
| `api/v1/feedback.py` | POST /v1/feedback | Feedback fogadas |
