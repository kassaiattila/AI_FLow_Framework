# AIFlow v1.4.6 Sprint J — Session 101 Prompt (UC2 RAG: UnstructuredChunker + Parser→Chunker→Embedder wiring)

> **Datum:** 2026-04-23 (tervezett folytatás)
> **Branch:** `feature/v1.4.6-rag-chat` — S100 zárta a branch első commitját (`9b3c610`). Folytasd ugyanezen.
> **HEAD prereq:** `9b3c610` — `feat(sprint_j): S100 — UC2 RAG kickoff (EmbedderProvider + EmbeddingDecision + alembic 040)`.
> **Port:** API 8102 | Frontend Vite :5174
> **Plan:** `01_PLAN/110_USE_CASE_FIRST_REPLAN.md` §4 Sprint J second row (a replan "S100" jelölésű rubrikája = ez a session = sequential ID szerint **S101**).
> **Session tipus:** IMPLEMENTATION — Chunker réteg bevezetése + a meglévő hardcoded `text-embedding-3-small` ingest path cseréje a `Parser → Chunker → Embedder` pipeline-ra. Code risk: MEDIUM-HIGH (rag_engine service átírás). Process risk: MEDIUM (regression a top-k retrieval baseline-hez képest).

---

## KONTEXTUS

### Honnan jöttünk

- **S100 ZÁRVA** — `EmbedderProvider` ABC élesítve (`embedding_dim`, `model_name`), új `src/aiflow/providers/embedder/` csomag (BGEM3Embedder = Profile A, AzureOpenAIEmbedder = Profile B), `EmbeddingDecision` Pydantic v1 stub, Alembic 040 `embedding_decisions` tábla (index + CHECK profile IN ('A','B')), `PolicyEngine.pick_embedder` tenant-override támogatással. Commit: `9b3c610`.
- Counts: 1970 unit PASS (+21), 51 integration PASS (+2 alembic 040), 410 E2E collected, ruff clean, tsc clean, nincs OpenAPI drift.
- Profile A live embed teszt `sentence_transformers` hiányában skip-el (S101 scope: _nem_ a deps install, csak a chunker). Profile B live teszt Azure OpenAI kulcs hiányában skip-el.

### Hova tartunk — Sprint J második sora

- **Cél:** UC2 RAG pipeline `Parser → Chunker → Embedder` közös flow-ra állítása. A meglévő hardcoded `text-embedding-3-small` ingest útvonalat (rag_engine) cserélni — most a Chunker réteg kerül be közéjük, és az Embedder oldalról már a S100 provider registry jön.
- Acceptance: valós 5 PDF collection ingest, cosine sim retrieve, **no regression a jelenlegi hardcoded baseline top-k-hez képest**.

### Jelenlegi állapot (induláskor várt)

```
27 service | 181 endpoint | 50 DB tábla | 40 Alembic migration (head: 040)
1970 unit PASS / 0 FAIL / 2 SKIP | 410 E2E collected | 51 integration PASS
0 ruff error | 0 ts error
Branch: feature/v1.4.6-rag-chat (1 commit ahead of main)
```

---

## ELŐFELTÉTELEK

```bash
git branch --show-current                                              # feature/v1.4.6-rag-chat
git log --oneline -3                                                   # HEAD: 9b3c610
.venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov             # 1970 PASS / 2 SKIP
.venv/Scripts/python.exe -m ruff check src/ tests/ --quiet             # exit 0
PYTHONPATH=src .venv/Scripts/python.exe -m alembic current             # 040
docker ps --filter "name=07_ai_flow_framwork" --format "table {{.Names}}\t{{.Status}}"
# db + redis healthy — ha nem: docker compose up -d db redis
```

---

## FELADATOK

### LÉPÉS 1 — Chunker contract + ABC

Hely: `src/aiflow/contracts/chunk_result.py` (új) és `src/aiflow/providers/chunker/` (új csomag, `base.py` + `__init__.py`).

- `ChunkResult` Pydantic v1 stub: `chunk_id: UUID`, `source_file_id: UUID`, `package_id: UUID`, `tenant_id: str`, `text: str`, `token_count: int`, `chunk_index: int`, `metadata: dict[str, Any]`. `extra="forbid"`.
- `ChunkerProvider` ABC: `async chunk(parser_result: ParserResult, context: IntakePackage) -> list[ChunkResult]` + `metadata: ProviderMetadata` + `health_check`.
- Bővítsd a `ProviderRegistry`-t egy 5. slot-tal: `register_chunker` / `get_chunker` / `list_chunkers`.
- Exportálj: `aiflow.contracts.ChunkResult`, `aiflow.providers.chunker.ChunkerProvider`.

**Exit:** `tests/unit/contracts/test_chunk_result.py` + `tests/unit/providers/chunker/test_registry_slot.py` happy + invalid paths.

### LÉPÉS 2 — `UnstructuredChunker` impl

Hely: `src/aiflow/providers/chunker/unstructured.py`.

- Használd az `unstructured` library-t (ellenőrizd `.venv`-ben: `.venv/Scripts/python.exe -c "import unstructured"`). Ha nincs, a Sprint I parser-stack már telepítette — `pyproject.toml` extra ellenőrzéssel validáld. Fallback: ha `unstructured` hiányzik → skippelj `importorskip`-pel és használj egy nagyon egyszerű default `_SimpleSentenceChunker`-t a `ParserResult.text`-ből (newline + heurisztika).
- Chunking params: `chunk_size_tokens=512`, `overlap_tokens=50`. Tokenizer: `tiktoken` `cl100k_base` (openai kompatibilis) — ha nincs: byte-length fallback.
- Emit `ChunkResult` instance-eket file-id + package-id visszavezetéssel.

**Exit:** `tests/unit/providers/chunker/test_unstructured.py` — minimum 3 teszt: (a) valós `ParserResult.text`-ből ≥1 chunk, (b) chunk_index monoton növekvő, (c) overlap ≥ 1 tokent megőriz a szomszédos chunk-ok között. SOHA mock text — használj fixture-öket valós PDF-kből kinyert parser outputból (Sprint I S96 tesztekben már van ilyen fixture, reuse).

### LÉPÉS 3 — `rag_engine` szolgáltatás átállítása a Parser→Chunker→Embedder flow-ra

Hely: `src/aiflow/services/rag_engine/ingest.py` (meglévő).

- Olvasd be a jelenlegi kódot: keresd a `text-embedding-3-small` hardcoded hívásait. Minden közvetlen `openai.embeddings.create`-et cserélj ki erre a sorrendre:
  1. `parser = registry.get_parser(policy.pick_parser(...))`; `parser_result = await parser.parse(...)`.
  2. `chunker = registry.get_chunker("unstructured")`; `chunks = await chunker.chunk(parser_result, package)`.
  3. `profile = "B" if policy_allows_cloud else "A"`; `embedder_cls = policy.pick_embedder(tenant_id, profile)`; `embedder = embedder_cls()`; `vectors = await embedder.embed([c.text for c in chunks])`.
  4. pgvector insert: `chunks[i].text` + `vectors[i]` + `chunks[i].chunk_id` + `embedding_dim` oszlop.
- Ha a `rag_collections` tábla `embedding_dim` oszlopa nem létezik → Alembic 041 (új rev): additive `embedding_dim INTEGER NULL` + backfill-hoz external script S102-ben.
- Persist `EmbeddingDecision`-t minden ingest-hívásra (alembic 040 táblába, Sprint J S100 contract).

**Exit:** `tests/integration/services/rag_engine/test_ingest_uc2.py` — valós Docker PG + Redis, 1 db kis PDF (≤5 oldal, fixture), `rag_collections` row írás, `embedding_decisions` row írás, vector dim assert egyezzen a választott provider `embedding_dim`-jével.

### LÉPÉS 4 — Retrieval baseline smoke

Hely: `tests/integration/services/rag_engine/test_retrieval_baseline.py`.

- Ingestelj 5 valós PDF-et (kérd el a usertől vagy használd a meglévő `tests/fixtures/pdfs/` alatti fixtureöket — `data/uploads/invoices` NEM mehet git-be, lásd `feedback_real_invoices_local_only`).
- Futtass egy cosine-sim retrieve-t 3 mintakérdéssel, jegyezd fel a top-1 + top-3 doc_id-kat.
- Hasonlítsd össze a korábbi hardcoded baseline-nal (ha nincs baseline fájl → LÉPÉS 4 első feladata: egy `baseline.json` commit a régi path outputjával **mielőtt** átváltasz — tehát időbeli sorrend: `git checkout 9b3c610` sanity → generálj baseline.json-t → `git switch -` → implementáld az új flow-t → fuss ellenőrzés).
- PASS feltétel: top-1 egyezik, top-3 minimum 2/3 átfedés.

**Exit:** baseline.json bekerül a repo-ba (`tests/fixtures/rag/baseline_2026_04_23.json`), teszt zöld.

### LÉPÉS 5 — Regression + session-close

```bash
.venv/Scripts/python.exe -m ruff check src/ tests/ --quiet
.venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov                                  # cél: 1970 + ~10 új
.venv/Scripts/python.exe -m pytest tests/integration/ --no-cov                              # cél: 51+2 PASS
PYTHONPATH=src .venv/Scripts/python.exe scripts/export_openapi.py                           # OpenAPI drift gate
.venv/Scripts/python.exe -m pytest tests/integration/services/rag_engine/ --no-cov -v       # spot check

/session-close S101
```

---

## STOP FELTÉTELEK

- **HARD:** `unstructured` library API változott és a chunking deterministic-e nem garantált → fallback a `_SimpleSentenceChunker`-hoz és külön session (S102) az upstream upgrade-hez.
- **HARD:** A jelenlegi `rag_engine` ingest path _nem_ hardcoded `text-embedding-3-small`, hanem már provider-aware (S99 közben bekerült valami) → re-scope szükséges, kérdezz.
- **HARD:** A baseline cosine-sim összevetés >30% top-3 drop → NE commitold az új path-t, analizáld a chunking/embedder különbséget (chunk size? overlap? dim mismatch 1024 vs 1536?).
- **HARD:** BGE-M3 model letöltés szükséges az integration teszthez és >500MB, nincs lokális cache → a ingest teszt használja Profile B-t helyette (ha Azure OpenAI kulcs van `.env`-ben), különben skip és ütemezd a Profile A bootstrap-et S102-re.
- **HARD:** Alembic 041 (ha kell) downgrade NEM tiszta → stop, ne erőltesd.
- **SOFT:** Ha LÉPÉS 4 baseline fixture hiányzik és nem triviális generálni → zárd a session-t LÉPÉS 1-3 + unit tesztekkel, LÉPÉS 4-et ütemezd S102-re.

---

## SESSION VÉGÉN

```
/session-close S101
```

Utána `/clear` és S102 (UI `Rag.tsx` + `RagDetail.tsx` + collection chunk viewer — replan §4 Sprint J third row).
