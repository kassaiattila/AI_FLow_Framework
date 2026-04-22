# AIFlow v1.4.6 Sprint J — Session 103 Prompt (UC2 RAG: retrieval baseline + Profile A bootstrap + pgvector flex-dim)

> **Datum:** 2026-04-25 (tervezett folytatas)
> **Branch:** `feature/v1.4.6-rag-chat` — folytasd ugyanezen.
> **HEAD prereq:** `37d5ba7` — `feat(sprint_j): S102 — UC2 RAG UI (ChunkViewer + chunks API provenance fields)`.
> **Port:** API 8102 | Frontend Vite 5174
> **Plan:** `01_PLAN/110_USE_CASE_FIRST_REPLAN.md` §4 Sprint J — retrieval quality + Profile A bootstrap.
> **Session tipus:** BACKEND / TESTING / INFRA — Sprint J zaro backend stabilizacio mielott UC2-t vegleges `done` allapotba tesszuk. Code risk: MEDIUM (pgvector alembic + modell cache). Process risk: MEDIUM (>500MB BGE-M3 letoltes).

---

## KONTEXTUS

### Honnan jottunk

- **S100 (9b3c610):** `EmbedderProvider` ABC + BGE-M3 (Profile A) + Azure OpenAI (Profile B) + `EmbeddingDecision` + `PolicyEngine.pick_embedder` + alembic 040.
- **S101 (953e7cd):** `UnstructuredChunker` (tiktoken cl100k_base, 512/50) + `ChunkerProvider` + opt-in provider registry path (`use_provider_registry=True`) + alembic 041 `rag_chunks.embedding_dim` + 2 integration teszt.
- **S102 (37d5ba7):** UC2 RAG UI — `ChunkViewer` komponens + chunks API provenance fields (`chunk_index`, `token_count`, `embedding_dim`, `metadata`) + 3 E2E teszt + `01_PLAN/UC2_RAG_USER_JOURNEY.md`.
- **Counts:** 1993 unit PASS / 2 skip (baseline), 55+ integration PASS (incl. 2 rag_engine UC2), 413 E2E collected (+3 S102), ruff clean, alembic head 041, tsc clean.
- **Nyitott adossag S101-bol:** retrieval baseline (`test_retrieval_baseline.py`) DEFERRED — Profile A `sentence_transformers` hianyzik, Profile B `AIFLOW_AZURE_OPENAI__*` env nincs beallitva; pgvector `rag_chunks.embedding vector(1536)` jelenleg fix → BGE-M3 (1024) nem fer el.

### Hova tartunk — Sprint J zaro lepes

- **Cel:** UC2 `done` kriteriumok teljes lefedese: (1) retrieval baseline halojsitas valos adatokon, (2) BGE-M3 Profile A bootstrap (model cache + install), (3) pgvector multi-dim strategiadonte (vagy kulon tabla / vagy flex-dim `VECTOR` tipus pgvector 0.7+ feature-check utan).
- **Acceptance:** `tests/fixtures/rag/baseline_2026_04_25.json` + `test_retrieval_baseline.py` PASS mindket profile-on (hu + en query-k), Profile A ingestion end-to-end 1024-dim vektorokkal, nincs regression a meglevo 55 integration teszten.
- **A feature is DONE only after** a retrieval baseline PASS (top-5 MRR ≥ 0.55 a Profile B legacy OpenAI path-on vs BGE-M3 paritas ±5%). Pontos kuszobok a session soran donthetoek.

### Jelenlegi allapot (indulaskor varhato)

```
27 service | 181 endpoint | 50 DB tabla | 41 Alembic migration (head: 041)
1993 unit PASS / 0 FAIL / 2 SKIP | 413 E2E collected | 55+ integration PASS
0 ruff error | 0 ts error
Branch: feature/v1.4.6-rag-chat (4 commit ahead of main)
```

---

## ELOFELTELEK

```bash
git branch --show-current                                              # feature/v1.4.6-rag-chat
git log --oneline -3                                                   # HEAD: 37d5ba7
.venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov             # 1993 PASS / 2 SKIP
.venv/Scripts/python.exe -m ruff check src/ tests/ --quiet             # exit 0
PYTHONPATH=src .venv/Scripts/python.exe -m alembic current             # 041
docker ps --filter "name=07_ai_flow_framwork" --format "table {{.Names}}\t{{.Status}}"
# db + redis healthy — ha nem: docker compose up -d db redis
# Profile A eloszto: python -c "import sentence_transformers" — ha ImportError, uv add sentence-transformers
# Profile B eloszto: printenv | grep AIFLOW_AZURE_OPENAI
```

---

## FELADATOK

### LEPES 1 — Profile A bootstrap (`sentence-transformers` install + BGE-M3 model cache)

- `uv add sentence-transformers` (+ torch deps). Ellenorizd licenselhetoseget (Apache-2.0).
- Model preload script: `scripts/bootstrap_bge_m3.py` — lokalis `.cache/models/bge-m3` konyvtarba menti a sulyokat (~550MB), idempotens (ha mar letezik, skip).
- `tests/unit/providers/embedder/test_bge_m3.py` live-mode opcional: env-varral (`AIFLOW_RUN_LIVE_BGE_M3=1`) aktivalhato 1 smoke test.

**Exit:** `python -c "from aiflow.providers.embedder.bge_m3 import BGEM3Embedder; e=BGEM3Embedder(); print(e.dim)"` → `1024`.

### LEPES 2 — pgvector multi-dim strategia (alembic 042)

**Dontes (architect agent ajanlott):**
- **A:** Kulon tablak per-dim (`rag_chunks_1024`, `rag_chunks_1536`) — egyszeru, stabil, konyvtarkezeles enyhul.
- **B:** Flex-dim oszlop `VECTOR` (pgvector 0.7+) — egy tabla marad, de feature-check kell.

Eldontve + `alembic/versions/042_rag_chunks_multi_dim.py` migracio. `rag_collections.embedding_dim` oszlop ajanlott (NOT NULL, default 1536) → collection-scoped routing.

**Exit:** alembic head 042, meglevo collection `embedding_dim=1536` backfill, uj collection create-kor ertek kitoltodik a `EmbedderProvider.dim`-bol.

### LEPES 3 — Retrieval baseline fixture + test

- `tests/fixtures/rag/baseline_2026_04_25.json` — 10-15 question/expected_chunk_id par 2 nyelven (hu/en), 2-3 seed dokumentumbol.
- `tests/integration/services/rag_engine/test_retrieval_baseline.py`:
  - Profile B (Azure OpenAI legacy) baseline futas → MRR@5 mereshez.
  - Profile A (BGE-M3) paritas check (±5% MRR).
- Quarantine helyett tolerance-based assertion (a modell minosege valtozhat).

**Exit:** baseline teszt PASS mindket profile-on.

### LEPES 4 — Regression + session-close

```bash
.venv/Scripts/python.exe -m ruff check src/ tests/ --quiet
cd aiflow-admin && npx tsc --noEmit && cd ..
.venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov                        # 1993+ PASS
.venv/Scripts/python.exe -m pytest tests/integration/services/rag_engine/         # 3+ PASS (ezzel a bazeline)
.venv/Scripts/python.exe -m pytest tests/e2e/ --collect-only -q                   # 413+
PYTHONPATH=src .venv/Scripts/python.exe scripts/export_openapi.py                 # drift check
PYTHONPATH=src .venv/Scripts/python.exe -m alembic current                        # 042

/session-close S103
```

---

## STOP FELTETELEK

- **HARD:** `sentence-transformers` install ronda tranzitiv konfliktusok (torch/numpy) — STOP, architect agent hivas, donts uv extras `[embedders]` group-rol.
- **HARD:** pgvector 0.7+ nem elerheto Docker db imagen — STOP, frissits postgres imaget vagy valaszd Strategy A-t.
- **HARD:** BGE-M3 model letoltes >10 perc vagy >1GB — STOP, jelezz a usernek.
- **HARD:** Retrieval baseline MRR@5 <0.40 a legacy path-on → alap minoseg gyenge → iranyitasi ertekeles szukseges.
- **SOFT:** Azure OpenAI env hianyzik → Profile B baseline skip, Profile A-ra fokuszalj, sprint zaro PR-be jelezd ki.

---

## SESSION VEGEN

```
/session-close S103
```

Utana `/clear` es S104 (Sprint J vegleges PR + tag `v1.4.5-sprint-j-uc2` elkeszitese + retro, ha UC2 done).
