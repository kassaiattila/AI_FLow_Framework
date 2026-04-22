# AIFlow v1.4.6 Sprint J — Session 104 Prompt (UC2 close: PR + tag v1.4.5-sprint-j-uc2 + retro)

> **Datum:** 2026-04-25 (tervezett folytatas)
> **Branch:** `feature/v1.4.6-rag-chat` — folytasd ugyanezen.
> **HEAD prereq:** `fa6324a` — `feat(sprint_j): S103 — UC2 retrieval baseline + BGE-M3 Profile A + pgvector flex-dim`.
> **Port:** API 8102 | Frontend Vite 5174
> **Plan:** `01_PLAN/110_USE_CASE_FIRST_REPLAN.md` §4 Sprint J — final PR + tag + retro.
> **Session tipus:** RELEASE / DOCS — Sprint J zaro release: PR cut, openapi drift snapshot, tag, retro doc, plan update. Code risk: LOW. Process risk: LOW-MEDIUM (main branch merge).

---

## KONTEXTUS

### Honnan jottunk

- **S100 (9b3c610):** `EmbedderProvider` ABC + BGE-M3 (Profile A) + Azure OpenAI (Profile B) + alembic 040 + PolicyEngine.pick_embedder.
- **S101 (953e7cd):** `UnstructuredChunker` + `ChunkerProvider` + provider-registry ingest path + alembic 041 `rag_chunks.embedding_dim`.
- **S102 (37d5ba7):** UC2 RAG UI — `ChunkViewer` + chunks API provenance fields + 3 E2E teszt.
- **S103 (fa6324a):** Retrieval baseline — BGE-M3 Profile A bootstrap (`sentence-transformers` install + model cache), alembic 042 pgvector flex-dim + `rag_collections.embedding_dim`, `OpenAIEmbedder` (Profile B surrogate), `test_retrieval_baseline.py` (MRR@5 ≥ 0.55 mindket profile-on), reranker fallback hardening.

### Hova tartunk — Sprint J lezarasa

- **Cel:** Sprint J UC2 hivatalos lezaras. PR #?? `main` ellen, tag `v1.4.5-sprint-j-uc2`, retro `docs/sprint_j_retro.md`, terv-frissites `01_PLAN/110_USE_CASE_FIRST_REPLAN.md` §4 `done` statuszra, CLAUDE.md counts frissitese.
- **Acceptance:** PR cut + zold CI, tag pushed, retro commit, NEXT.md generalt az S105-os (UC3 kezdes vagy Phase 1.5 kovetkezo block) elokeszitesehez.

### Jelenlegi allapot (indulaskor varhato)

```
27 service | 181 endpoint | 50 DB tabla | 42 Alembic migration (head: 042)
1994 unit PASS / 0 FAIL / 1 skip / 1 deselect (pre-existing resilience flake)
413 E2E collected | 55+ integration PASS (incl. 5 rag_engine UC2)
0 ruff error | 0 ts error
Branch: feature/v1.4.6-rag-chat (5 commit ahead of main, S100-S103 + session-close commits)
```

---

## ELOFELTELEK

```bash
git branch --show-current                                              # feature/v1.4.6-rag-chat
git log --oneline -3                                                   # HEAD: fa6324a
.venv/Scripts/python.exe -m ruff check src/ tests/ --quiet             # exit 0
.venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov \
  --deselect tests/unit/services/test_resilience_service.py::TestResilienceService::test_circuit_opens_on_failures
# 1994 PASS / 1 SKIP / 1 DESELECTED
PYTHONPATH=src .venv/Scripts/python.exe -m alembic current             # 042
# Live baseline sanity (Profile B uses real OpenAI — costs ~$0.001):
# AIFLOW_RUN_LIVE_RAG_BASELINE=1 AIFLOW_BGE_M3__CACHE_FOLDER=.cache/models/bge-m3 \
#   PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/integration/services/rag_engine/test_retrieval_baseline.py -q --no-cov
```

---

## FELADATOK

### LEPES 1 — Resilience flake quarantine + ticket

A `test_circuit_opens_on_failures` time-sensitive (50ms recovery window), full-suite load alatt flaky, isolation-ban PASS. Per testing policy "quarantine + fix within 5 days, never delete":

- Jelold `@pytest.mark.flaky` (vagy xfail `strict=False` + reason) a test funcion.
- Logold az issue-t `docs/quarantine.md`-be (vagy hozd letre) HEAD+date+owner mezokkel.
- Ne bomld be a session-t vele, csak regisztrald es lepj tovabb.

**Exit:** `pytest tests/unit/ -q` exit 0 deselect nelkul is.

### LEPES 2 — OpenAPI drift snapshot

S103 modositotta a `CollectionInfo` belso modelt (`embedding_dim` hozzaadasa), de az API schema valtozatlan maradt. Biztositasul regeneraljuk:

```bash
PYTHONPATH=src .venv/Scripts/python.exe scripts/export_openapi.py
git diff --stat docs/api/openapi.*
```

Ha **van** drift → commit `docs(openapi): regen after Sprint J`. Ha nincs, `docs/api/openapi.*` erintetlen.

### LEPES 3 — Sprint J retro dokumentum

```
docs/sprint_j_retro.md
```

Tartalom:
- **Session table** S100–S104, rovid scope + commit hash.
- **Key numbers delta:** 40 → 42 migration, 1990 → 1994 unit, 55 → 55+ integration, uj: 2 retrieval baseline teszt.
- **Contracts delivered:** EmbedderProvider ABC, ChunkerProvider ABC, EmbeddingDecision contract, pgvector flex-dim strategia.
- **Issues / follow-ups:**
  - #?: reranker model preload scripttel kiegesziteni (hasonlon mint `bootstrap_bge_m3.py`), hogy `_rerank_cross_encoder` ne csak fallback path-on menjen.
  - #?: `query()` metodus collection-scoped embedder selection (jelenleg csak `_ingest_via_provider_registry` adaptiv, a `query()` a legacy `Embedder`-rel megy — 1024-dim kollekcio nem kereshato a jelenlegi API-n).
  - #?: Azure OpenAI Profile B valodi teszt (credits hianyaban jelenleg OpenAI surrogate).
  - #?: Resilience test flake — LEPES 1 quarantine es valodi root-cause vizsgalat.
- **Decisions log:** Strategy B (flex-dim) valasztas indoka, OpenAIEmbedder mint Profile B fallback, `sentence-transformers` mint optional `local-models` extra.

### LEPES 4 — Terv + CLAUDE.md update

- `01_PLAN/110_USE_CASE_FIRST_REPLAN.md` §4 Sprint J → status `done`, acceptance checkbox-ok.
- `CLAUDE.md`:
  - "Current Plan" blokk: v1.4.5 Sprint J MERGED, tag `v1.4.5-sprint-j-uc2`, UC2 done.
  - Key numbers: 42 Alembic migration (head 042), 1994 unit, 413 E2E, uj: `OpenAIEmbedder` provider + retrieval baseline teszt.

### LEPES 5 — PR cut + tag

```bash
gh pr create --base main --title "v1.4.5 Sprint J — UC2 RAG (retrieval baseline + multi-profile embedders + pgvector flex-dim)" \
  --body-file docs/sprint_j_pr_description.md
```

PR description keszitese `docs/sprint_j_pr_description.md`-ben: scope, 5 session osszefoglalo, acceptance criteria checklist, test evidence (baseline MRR@5 szamok), follow-up issue-k.

CI zoldre es user review utan:

```bash
git tag v1.4.5-sprint-j-uc2
git push origin v1.4.5-sprint-j-uc2
```

**Merge ne automatikus — user jovahagyast var.**

### LEPES 6 — Regression + session-close

```bash
.venv/Scripts/python.exe -m ruff check src/ tests/ --quiet
cd aiflow-admin && npx tsc --noEmit && cd ..
.venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov        # 1995 PASS if quarantine done properly
.venv/Scripts/python.exe -m pytest tests/e2e/ --collect-only -q   # 413+
PYTHONPATH=src .venv/Scripts/python.exe scripts/export_openapi.py # drift check
PYTHONPATH=src .venv/Scripts/python.exe -m alembic current        # 042

/session-close S104
```

---

## STOP FELTETELEK

- **HARD:** CI piros a PR cut utan — ne zard le, kerj user jovahagyast a fix strategiara.
- **HARD:** Resilience test quarantine utan is nem-triviallis uj FAIL — STOP.
- **HARD:** Terv `done` statusz ertelmezesi kerdes (pl. UC2 done-hoz kell meg `query()` refactor is?) — user jovahagyast var.
- **SOFT:** OpenAPI drift nagy (>20 sor) — dokumentald extranak, kesobbi session scope.
- **SOFT:** PR review kommentek merge elott — hagyd ra user-re, ne zard le a PR-t magad.

---

## SESSION VEGEN

```
/session-close S104
```

Utana `/clear` es S105 (UC3 kickoff vagy Phase 1.5 kovetkezo Vault block, fuggoen a `110_USE_CASE_FIRST_REPLAN.md` §5-os szekciotol).
