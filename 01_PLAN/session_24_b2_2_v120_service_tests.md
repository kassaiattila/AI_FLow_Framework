# AIFlow Sprint B — Session 24 Prompt (B2.2: v1.2.0 Service Tesztek)

> **Datum:** 2026-04-06
> **Branch:** `feature/v1.3.0-service-excellence` | **HEAD:** `169a6d1`
> **Port:** API 8102, Frontend 5174
> **Elozo session:** S23 — B2.1 DONE (13 core service × 5 test = 65 unit test)
> **Terv:** `01_PLAN/58_POST_SPRINT_HARDENING_PLAN.md` (B2 szekció, sor 908+)

---

## KONTEXTUS

### B2.1 Eredmenyek (S23 — DONE)

- 13 Tier 1 service × 5 teszt = 65 unit teszt (commit 51ce1bf)
- `tests/unit/services/` konyvtar + conftest.py (mock_pool, mock_redis fixtures)
- Teszt fajlok: cache, rate_limiter, resilience, health_monitor, audit, schema_registry, notification, human_review, media_processor, diagram_generator, rpa_browser, classifier, email_connector
- Minden teszt PASS, 0 regresszio

### Infrastruktura (v1.3.0)

- 26 service | 165 API endpoint (25 router) | 46 DB tabla | 29 migracio
- 18 adapter | 6 template | 5 skill | 22 UI oldal
- 1260 unit test | 129 guardrail teszt | 97 security teszt | 54 promptfoo teszt
- Guardrail: A5 rule-based + B1.1 LLM fallback + B1.2 per-skill config

### Meglevo Teszt Infrastruktura (tests/unit/services/)

```
tests/unit/services/
  conftest.py          — mock_pool (MagicMock!), mock_redis, AsyncIterMock, AsyncPipelineMock
  __init__.py
  test_*_service.py    — 13 fajl (B2.1, 65 teszt)
```

---

## B2.2 FELADAT: v1.2.0 Service Tesztek (13 service, 65 test)

> **Gate:** 130 osszesen a `tests/unit/services/` konyvtarban (65 regi + 65 uj)
> **Eszkozok:** `/dev-step` (service-csoportonkent), `/regression`
> **Pattern:** Minden service-hez 5 unit teszt, a B2.1-ben kialakitott mock-pattern-nel

### 13 Tier 2 Service + Tesztelesi Terv

#### 1. data_router — `DataRouterService` (BaseService, in-memory)

```
Fajl: src/aiflow/services/data_router/service.py
Dep: nincs kulso (filesystem move, Jinja2 template)
Tesztek:
  test_filter_matching_items()         — filter condition → helyes FilterResult
  test_filter_no_match()               — filter → ures lista
  test_route_files_by_rules()          — route rules → helyes RoutedFile lista
  test_move_to_dir_template()          — Jinja2 template path → helyes cel konyvtar
  test_health_check()                  — health_check → True
```

#### 2. service_manager — `ServiceManagerService` (BaseService, SQLAlchemy)

```
Fajl: src/aiflow/services/service_manager/service.py
Dep: SQLAlchemy async_sessionmaker (optional)
Tesztek:
  test_list_services()                 — list → ServiceSummary lista
  test_get_service_detail()            — get by name → ServiceDetail
  test_restart_service()               — restart → True
  test_get_service_metrics()           — metrics → ServiceMetrics (avg/p95)
  test_record_metric()                 — record → nem dob hibat
```

#### 3. reranker — `RerankerService` (BaseService, in-memory)

```
Fajl: src/aiflow/services/reranker/service.py
Dep: nincs kulso (keyword scoring)
Tesztek:
  test_rerank_keyword_strategy()       — rerank → sorted RankedResult lista
  test_rerank_empty_candidates()       — ures lista → ures eredmeny
  test_rerank_top_k_limit()            — top_k=2 → max 2 eredmeny
  test_rerank_score_ordering()         — score descending sorrend
  test_health_check()                  — health_check → True
```

#### 4. advanced_chunker — `AdvancedChunkerService` (BaseService, in-memory)

```
Fajl: src/aiflow/services/advanced_chunker/service.py
Dep: nincs kulso (text processing)
Tesztek:
  test_chunk_fixed_strategy()          — fixed size → ChunkResult
  test_chunk_sentence_strategy()       — sentence split → helyes chunk-ok
  test_chunk_respects_max_size()       — max chunk_size betartva
  test_chunk_overlap()                 — overlap param → atfedo chunk-ok
  test_chunk_empty_text()              — ures text → ures ChunkResult
```

#### 5. data_cleaner — `DataCleanerService` (BaseService, in-memory)

```
Fajl: src/aiflow/services/data_cleaner/service.py
Dep: nincs kulso (text normalization)
Tesztek:
  test_clean_normalizes_whitespace()   — clean → normalized text
  test_clean_removes_html()            — HTML tags eltavolitva
  test_clean_batch()                   — batch → lista CleanedDocument
  test_clean_preserves_content()       — lenyegi tartalom megmarad
  test_health_check()                  — health_check → True
```

#### 6. metadata_enricher — `MetadataEnricherService` (BaseService, in-memory)

```
Fajl: src/aiflow/services/metadata_enricher/service.py
Dep: nincs kulso (regex/heuristic)
Tesztek:
  test_enrich_extracts_language()      — enrich → detected language
  test_enrich_extracts_word_count()    — enrich → word_count stat
  test_enrich_detects_entities()       — enrich → entity lista
  test_enrich_empty_text()             — ures text → minimal metadata
  test_health_check()                  — health_check → True
```

#### 7. vector_ops — `VectorOpsService` (BaseService, SQLAlchemy)

```
Fajl: src/aiflow/services/vector_ops/service.py
Dep: SQLAlchemy async_sessionmaker (optional)
Tesztek:
  test_get_collection_health()         — health → CollectionHealth
  test_optimize_index()                — optimize → result dict
  test_bulk_delete()                   — bulk_delete → deleted count
  test_health_check_no_db()            — health_check DB nelkul → True
  test_service_name()                  — service_name == "vector_ops"
```

#### 8. advanced_parser — `AdvancedParserService` (BaseService, in-memory)

```
Fajl: src/aiflow/services/advanced_parser/service.py
Dep: nincs kulso (file I/O, text extraction)
Tesztek:
  test_parse_text_file()               — .txt parse → ParsedDocument
  test_parse_unknown_format()          — ismeretlen formatum → fallback/hiba
  test_parse_config_override()         — custom ParserConfig → hasznalva
  test_parsed_document_fields()        — ParsedDocument mezoi helyesek
  test_health_check()                  — health_check → True
```

#### 9. graph_rag — `GraphRAGService` (BaseService, in-memory)

```
Fajl: src/aiflow/services/graph_rag/service.py
Dep: nincs kulso (entity extraction, in-memory graph)
Tesztek:
  test_extract_entities()              — extract → entity lista
  test_build_graph()                   — build → graph dict (nodes, edges)
  test_query_graph()                   — query → result dict
  test_extract_entities_empty()        — ures text → ures lista
  test_health_check()                  — health_check → True
```

#### 10. quality — `QualityService` (BaseService, in-memory)

```
Fajl: src/aiflow/services/quality/service.py
Dep: nincs kulso (rubric eval, cost calc)
Tesztek:
  test_get_overview()                  — overview → QualityOverview
  test_estimate_pipeline_cost()        — estimate → CostEstimate
  test_list_rubrics()                  — list → non-empty dict
  test_evaluate_rubric_no_llm()        — evaluate without LLM → result/fallback
  test_health_check()                  — health_check → True
```

#### 11. rag_engine — `RAGEngineService` (BaseService, SQLAlchemy)

```
Fajl: src/aiflow/services/rag_engine/service.py
Dep: SQLAlchemy async_sessionmaker
Tesztek:
  test_list_collections()              — list → CollectionInfo lista
  test_get_collection()                — get by id → CollectionInfo | None
  test_delete_collection()             — delete → True
  test_get_collection_stats()          — stats → CollectionStats
  test_health_check()                  — health_check (DB-vel/nelkul)
```

#### 12. document_extractor — `DocumentExtractorService` (BaseService, SQLAlchemy)

```
Fajl: src/aiflow/services/document_extractor/service.py
Dep: SQLAlchemy async_sessionmaker
Tesztek:
  test_list_configs()                  — list → DocumentTypeConfig lista
  test_get_config()                    — get by name → DocumentTypeConfig | None
  test_create_config()                 — create → persisted DocumentTypeConfig
  test_get_invoice()                   — get invoice → dict | None
  test_health_check()                  — health_check → True/False
```

#### 13. extra coverage (5 teszt) — legalacsonyabb coverage potlas

```
Az extra 5 teszt a legalacsonyabb coverage-u service-re kerul.
Valaszd ki a coverage riport alapjan (pytest --cov=src/aiflow/services/)
es pótold a hiányzo edge-case-eket.
Peldak:
  - error handling (hibas input, connection failure)
  - edge case (ures lista, None parameter)
  - config defaults (default config helyes ertekekkel indul)
  - model serialization (Pydantic model → dict → model roundtrip)
  - lifecycle (start → stop → restart pattern)
```

### Teszt Fajl Struktura (UJ fajlok)

```
tests/unit/services/           ← MEGLEVO konyvtar (B2.1-bol)
  # Meglevo: conftest.py + 13 fajl (65 teszt)
  # UJ:
  test_data_router_service.py      — 5 test
  test_service_manager_service.py  — 5 test
  test_reranker_service.py         — 5 test
  test_advanced_chunker_service.py — 5 test
  test_data_cleaner_service.py     — 5 test
  test_metadata_enricher_service.py — 5 test
  test_vector_ops_service.py       — 5 test
  test_advanced_parser_service.py  — 5 test
  test_graph_rag_service.py        — 5 test
  test_quality_service.py          — 5 test
  test_rag_engine_service.py       — 5 test
  test_document_extractor_service.py — 5 test
  test_extra_coverage.py           — 5 test (edge cases)
```

### Tesztelesi Szabalyok (mint B2.1!)

1. **Async tesztek** — `async def test_*` + `@pytest.mark.asyncio`
2. **SQLAlchemy-fuggo** — mock `session_factory` (lasd `test_email_connector_service.py` mintat!)
3. **BaseService-fuggo** — constructor-ba config inject, nincs kulso dep
4. **`@test_registry` header** — MINDEN teszt fajl elejen
5. **Nincs valos external service** — ez unit teszt, NEM integration teszt!
6. **mock_pool pattern** — `MagicMock()` (NEM `AsyncMock`!) az asyncpg pool-hoz → `ctx.__aenter__ = AsyncMock(return_value=conn)`
7. **Lazy import patch** — `sys.modules` injection, NEM `patch("module.submodule.func")`

### Mock Strategia (service tipusonkent)

```python
# In-memory service-ek (data_router, reranker, chunker, cleaner, stb.)
@pytest.fixture()
def svc() -> XxxService:
    return XxxService(config=XxxConfig())
# → Nincs mock szukseg, valos logikat tesztelunk!

# SQLAlchemy-fuggo service-ek (service_manager, vector_ops, rag_engine, doc_extractor)
@pytest.fixture()
def mock_session_factory():
    session = AsyncMock()
    factory = MagicMock()
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=False)
    factory.return_value = ctx
    return factory, session

@pytest.fixture()
def svc(mock_session_factory) -> XxxService:
    factory, _session = mock_session_factory
    return XxxService(session_factory=factory, config=XxxConfig())
```

---

## VEGREHAJTAS SORRENDJE

```
--- LEPES 1: In-memory service-ek (nincs external dep) ---
/dev-step "B2.2.1 — data_router + reranker + advanced_chunker tesztek (15 test)"
  - 3 fajl × 5 teszt = 15 teszt
  - Ezek a legegyszerubbek: valos logika, nincs mock

--- LEPES 2: Tovabbi in-memory service-ek ---
/dev-step "B2.2.2 — data_cleaner + metadata_enricher + advanced_parser + graph_rag tesztek (20 test)"
  - 4 fajl × 5 teszt = 20 teszt
  - Text processing / NLP logika

--- LEPES 3: Quality service ---
/dev-step "B2.2.3 — quality + service_manager tesztek (10 test)"
  - quality: rubric eval, cost estimate (in-memory + optional LLM)
  - service_manager: SQLAlchemy mock pattern

--- LEPES 4: SQLAlchemy-fuggo service-ek ---
/dev-step "B2.2.4 — vector_ops + rag_engine + document_extractor tesztek (15 test)"
  - SQLAlchemy session mock pattern (mint email_connector B2.1-bol)
  - 3 fajl × 5 teszt = 15 teszt

--- LEPES 5: Extra coverage ---
/dev-step "B2.2.5 — extra coverage tesztek (5 test)"
  - pytest --cov=src/aiflow/services/ → legalacsonyabb coverage kivalasztas
  - 5 edge-case teszt a leggyengebb service-re

--- SESSION LEZARAS ---
/lint-check → 0 error
/regression → ALL PASS (1260 + 65 = 1325 unit test)
/update-plan → 58 progress B2.2 DONE, B2 GATE TELJESITVE
```

---

## KORNYEZET ELLENORZES

```bash
git branch --show-current                                    # → feature/v1.3.0-service-excellence
git log --oneline -3                                         # → 169a6d1, 51ce1bf, d03be2f
python -m pytest tests/unit/services/ -q 2>&1 | tail -1      # → 65 passed
.venv/Scripts/ruff check src/ tests/ 2>&1 | tail -1          # → All checks passed!
ls src/aiflow/services/ | wc -l                              # → 26+ service
ls tests/unit/services/test_*.py | wc -l                     # → 13 (B2.1)
```

---

## S23 TANULSAGAI (alkalmazando S24-ben!)

1. **`mock_pool` = `MagicMock()`** — NEM `AsyncMock`! asyncpg `pool.acquire()` szinkron hivas, ami async ctx manager-t ad vissza. Ha `AsyncMock`-ot hasznalsz, `TypeError: 'coroutine' object does not support the asynchronous context manager protocol` hibat kapsz.
2. **Lazy import patch** — `from skills.X import Y` az `async def generate()` belsejeben NEM patchelheto `patch("module.func")`-kal. Haszalj `sys.modules` injection-t (`types.ModuleType` + `sys.modules[pkg] = mod`).
3. **Log-dampened keyword confidence** — A ClassifierService `log(1+raw)/log(2+raw)` formulat hasznal. 5/5 keyword hit kell a 0.5+ score-hoz. Tesztekben hasznalj eleg keyword-ot a szovegben!
4. **Mock row dict vs tuple** — asyncpg `fetchrow` dict-et ad vissza (key=column_name), de SQLAlchemy `fetchone` tuple-t. A ket pattern KULONBOZIK!
5. **`_make_row()` helper** — B2.1-ben minden teszt fajlban kulon `_make_row()` helper van a mock DB sorokhoz. Kovetsd ezt a patternt!
6. **PostToolUse ruff hook** — automatikusan formattal Write/Edit utan. Import + hasznalat EGYSZERRE kell!

---

## SPRINT B UTEMTERV

```
S19: B0   — DONE (4b09aad) — 5-layer arch + qbpp + prompt API + OpenAPI
S20: B1.1 — DONE (f6670a1) — 4 LLM guardrail prompt + llm_guards.py + 27 promptfoo
S21: B1.2 — DONE (7cec90b) — 5 guardrails.yaml + PIIMaskingMode + 31 teszt
S22: B2.1 — DONE (51ce1bf) — Core infra service tesztek (65 test, Tier 1)
S23: B2.2 ← JELEN SESSION — v1.2.0 service tesztek (65 test, Tier 2)
S24: B3.1 — Invoice Finder: pipeline design + email + doc acquisition
S25: B3.2 — Invoice Finder: extract + report + notification (valos adat!)
S26: B3.5 — Konfidencia scoring hardening + confidence→review routing
S27: B4.1 — Skill hardening: aszf_rag + email_intent
S28: B4.2 — Skill hardening: process_docs + invoice + cubix + diagram
S29: B5   — Spec writer + diagram pipeline + koltseg baseline
S30: B6   — UI Journey audit + 4 journey tervezes + navigacio redesign
S31: B7   — Verification Page v2 (bounding box, diff, per-field confidence szin)
S32: B8   — UI Journey implementacio (top 3 journey + dark mode)
S33: B9   — Docker containerization + UI pipeline trigger + deploy teszt
S34: B10  — POST-AUDIT + javitasok
S35: B11  — v1.3.0 tag + merge
```

---

## FONTOS SZABALYOK (emlekeztetok)

- **`/dev-step` HASZNALANDÓ** — minden service-csoport kulon dev-step
- **Unit test = mock** — ez NEM integration test! Ne inditsd el a PostgreSQL/Redis-t, mockold.
- **Async pattern** — `@pytest.mark.asyncio` + `async def test_*()` — MINDEN tesztben
- **`@test_registry` header** — MINDEN teszt fajl elejen (lasd B2.1 mintat!)
- **Fajlnev konvencio:** `test_{service_name}_service.py`
- **In-memory service-eknel** — valos logikat tesztelunk, NEM mockolt hivas!
- **conftest.py MEGLEVO** — ne duplikald, hasznad a `mock_pool` es `mock_redis` fixture-oket
- **Ne duplikald** a B2.1 teszteket — csak az UJ 13 service-hez irj tesztet
- **Feedback:** Session vegen command_feedback.md KOTELEZO

---

## B2 GATE CHECKLIST (B2.2 vegen — TELJES B2 GATE!)

```
[ ] B2.1: 13 Tier 1 service × 5 teszt = 65 PASS (DONE — 51ce1bf)
[ ] B2.2: 13 Tier 2 service × 5 teszt = 65 PASS
[ ] Osszesen: 130 service unit teszt PASS
[ ] Minden teszt fajlban @test_registry header
[ ] /lint-check → 0 error
[ ] /regression → ALL PASS (1325+ unit test)
[ ] Nincs regresszio a meglevo tesztekben
[ ] conftest.py kozos fixture-ok bovitve (ha szukseges)
```
