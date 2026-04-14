---
name: aiflow-pipeline
description: >
  AIFlow pipeline, adapter es orchestration fejlesztesi szabalyok. Hasznald
  amikor pipeline YAML-t, adaptert irsz, PipelineRunner/Compiler-rel
  dolgozol, vagy Docker deploy-t keszitesz.
allowed-tools: Read, Write, Grep, Glob, Bash
---

# AIFlow Pipeline Development Rules

## API Compatibility (SOHA ne torj meg meglevo API-t!)

- Uj mezok: MINDIG optional (default ertekkel)
- Mezo torles: TILOS — deprecation + 2 minor version utan optional-la
- Endpoint atnevezes: TILOS — uj endpoint + redirect a regirol
- Response format valtozas: TILOS — uj mezo OK, tipus valtozas NEM
- `/api/v1/*` meglevo endpointok FROZEN — KIZAROLAG bugfix

## DB Migration Safety

- Uj oszlop meglevo tablaban: KOTELEZO `nullable=True` vagy `server_default`
- Oszlop torles: TILOS egybol — eloszor nullable, kovetkezo release-ben torold
- Index: `CREATE INDEX CONCURRENTLY`
- FK: `ON DELETE SET NULL` (nem cascade varatlanul)
- Teszt: `alembic upgrade head && alembic downgrade -1 && alembic upgrade head` HIBA NELKUL

## Pipeline Development Rules

- MINDEN pipeline YAML: `src/aiflow/pipeline/builtin_templates/`
- MINDEN step: `service` + `method` (adapter registry-ben LETEZIK)
- `for_each`: CSAK Jinja2 expression ami list-et ad vissza
- `condition`: CSAK `output.field op value` formatum
- `retry`: KOTELEZO minden kulso service hivasra (LLM, email, HTTP)
- Jinja2: NEM hasznalhato `__dunder__`, `callable`, `import`
- MINDEN pipeline YAML-hoz KOTELEZO teszt: `tests/pipeline/test_{name}.py`
- Cost tracking: MINDEN pipeline futtas cost_records-ba logolva

## Adapter Development Rules

- Adapter = thin wrapper, NEM modositja az eredeti service-t
- File: `src/aiflow/pipeline/adapters/{service}_adapter.py`
- KOTELEZO: `input_schema`, `output_schema` (Pydantic), `execute()` method
- `for_each`: adapter belul kezeli `asyncio.Semaphore`-ral (concurrency limit)
- MINDEN adapter-hez unit test: `tests/unit/pipeline/test_{service}_adapter.py`

## Service Isolation (fejlesztes alatt)

- Meglevo service-ek: KIZAROLAG bugfix. Feature bovites TILOS.
- Adapter reteg: WRAPPER-eket ir, NEM modositja az eredeti service-t.
- Uj service-ek: Kulon mappa, kulon adapter, kulon migracio.
- Meglevo API router-ek: CSAK bugfix. Uj feature → uj router fajl.

## L0 Smoke Test

```bash
./scripts/smoke_test.sh  # 30s, health + 4 core endpoint + source=backend
```

## Notification & HITL Rules

- Notification templates: `prompts/notifications/` YAML Jinja2
- Channel credentials: MINDIG encrypted DB-ben
- HITL create_and_wait: Checkpoint+Resume pattern (NEM blokkolo)
- SLA config: KOTELEZO minden review queue-ra
- Review dontes: MINDIG logolva (reviewer + timestamp + comment)

## Document Extraction & Intent Rules

- Document type configs: KOTELEZO `auto_approve_threshold`, `review_threshold`, `reject_threshold`
- Intent schemas: YAML-loadable + DB-storable
- Extraction history: MINDEN attempt logolva (confidence score-ral)
- Parser fallback lanc: Docling → Azure DI → Tesseract (LlamaParse KIHAGYVA)

## Meglevo Keretrendszer (NEM ujraepitendo!)

| Komponens | Hol |
|-----------|-----|
| PipelineRunner + Compiler | pipeline/ |
| 22 Adapter | pipeline/adapters/ |
| 10 Pipeline Template | pipeline/builtin_templates/ |
| PromptManager | prompts/manager.py |
| DocumentRegistry | documents/ |
| AzureDocIntelligence | tools/azure_doc_intelligence.py |
| HumanReviewService | services/human_review/ |
| NotificationService | services/notification/ |
| StateRepository | state/repository.py |
| JobQueue + Worker | execution/ |

## Technology Decisions (VEGLEGES)

- Reranker: bge-reranker-v2-m3 (primary), FlashRank (CPU fallback)
- Chunking: Sajat implementacio (6 strategia) + Chonkie
- GraphRAG: Microsoft GraphRAG + LazyGraphRAG
- Chat UI: react-markdown + Shiki
- Kafka: HALASZTVA post-v1.3.0 (in-memory MessageBroker)
- LlamaParse: KIHAGYVA (cloud-only, privacy)

## v2 Pipeline Concepts (Phase 1a)

- IntakePackage normalization: multi-source intake (email + file + folder + batch + API)
- Cost-aware routing: provider selection with policy constraints + cost cap
- Provider abstraction: parser/classifier/extractor/embedder as pluggable interfaces
- Feature flags: `AIFLOW_FEATURE_*` env vars for Phase 2+ opt-in
- Fallback chain: primary -> secondary -> tertiary provider with automatic retry
