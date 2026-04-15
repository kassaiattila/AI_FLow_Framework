# AIFlow — Feature List

> **Verzio:** v1.4.0 (Phase 1a Foundation) | **Datum:** 2026-04-17 | **Kovetkezo:** v1.4.1 (Phase 1b — source adapters)

## Framework

| Feature | Allapot | Megjegyzes |
|---------|---------|------------|
| Step + SkillRunner engine | Production | @step dekorator, sequential execution |
| WorkflowRunner (DAG) | Production | Topologiai rendezes, checkpoint, resume |
| Pipeline as Code (YAML) | Production | 19 adapter, 6 template, PipelineRunner |
| ModelClient (LLM) | Production | LiteLLM backend, generate + embed |
| PromptManager (YAML+Jinja2) | Production | Langfuse v4 SDK, cache, label-based |
| VectorStore (pgvector) | Production | Hybrid search: HNSW + BM25 + RRF |
| Guardrail Framework | Production | InputGuard, OutputGuard, ScopeGuard (A5) |
| JWT RS256 Auth | Production | PyJWT, API key, RBAC (A3) |
| Execution Queue | Production | JobQueue, Worker, Scheduler, DLQ |
| Notification Service | Production | Email, Slack, webhook, in-app |
| Human Review | Production | Pending/approve/reject workflow |
| Cost Tracking | Production | Per-step LLM cost, Langfuse integration |

## Skills (5 db)

| Skill | Tipus | Allapot | Promptfoo |
|-------|-------|---------|-----------|
| process_documentation | AI | Production | 10 test, 90% |
| aszf_rag_chat | AI | Production | 7 test, 86% |
| email_intent_processor | AI | Development | 14 test, 85% |
| invoice_processor | AI | Development | 11 test, 80% |
| cubix_course_capture | Hybrid | Production | 6 test, 90% |

## Services (25 db)

| Service | Sorok | Teszt | Allapot |
|---------|-------|-------|---------|
| email_connector | 1271 | 5 | Production |
| rag_engine | 681 | 5 | Production |
| notification | 625 | 5 | Production |
| document_extractor | 542 | 0 | Development |
| classifier | 493 | 5 | Production |
| advanced_parser | 367 | 0 | Development |
| quality | 333 | 0 | Development |
| service_manager | 331 | 5 | Development |
| vector_ops | 314 | 0 | Development |
| data_router | 306 | 5 | Development |
| metadata_enricher | 305 | 0 | Development |
| advanced_chunker | 298 | 0 | Development |
| human_review | 290 | 0 | Development |
| graph_rag | 286 | 0 | Development |
| rpa_browser | 263 | 0 | Development |
| reranker | 259 | 0 | Development |
| media_processor | 256 | 0 | Development |
| diagram_generator | 238 | 0 | Development |
| cache | 234 | 0 | Development |
| resilience | 232 | 0 | Development |
| health_monitor | 225 | 0 | Development |
| data_cleaner | 191 | 0 | Development |
| rate_limiter | 179 | 0 | Development |
| schema_registry | 151 | 0 | Development |
| audit | 139 | 0 | Development |

## Pipeline Templates (6 db)

| Template | Allapot | Leiras |
|----------|---------|--------|
| invoice_automation_v1 | Ready | Email → classify → extract |
| invoice_automation_v2 | Ready | Enhanced invoice processing |
| email_triage | Ready | Email routing |
| advanced_rag_ingest | Ready | RAG document ingestion |
| contract_analysis | Ready | Contract processing |
| knowledge_base_update | Ready | KB updates |

## API (142 endpoint, 25 router)

| Router | Endpoint db | Fo funkciok |
|--------|------------|-------------|
| rag_engine | 17 | Ingest, query, collections |
| emails | 17 | Fetch, send, connectors |
| pipelines | 15 | CRUD, run, validate |
| documents | 15 | Upload, manage, version |
| services | 12 | Discovery, health, config |
| notifications | 10 | Multi-channel send |
| admin | 10 | Team/user management |
| human_review | 9 | Queue, approve/reject |
| + 17 tovabbi | 37 | Lasd 22_API_SPECIFICATION.md |

## UI (aiflow-admin, 17 oldal)

| Oldal | Allapot | Megjegyzes |
|-------|---------|------------|
| Dashboard | Mukodik | KPI kartyak, attekintes |
| Documents | Mukodik | Upload, lista, statusz |
| Emails | Mukodik | Inbox, connectors |
| RAG Chat | Mukodik | Query, collections |
| Quality | Mukodik | Eval dashboard |
| Process Docs | Reszleges | Diagram generalas |
| + 11 tovabbi | Vegyes | Monitoring, admin, stb. |

## Infrastruktura

| Metrika | Ertek |
|---------|-------|
| API endpointok | 175 (27 router) |
| DB tablak | 49 |
| Pipeline adapterek | 22 |
| Unit tesztek | 1674 PASS |
| Guardrail tesztek | 129 PASS |
| Security tesztek | 97 PASS |
| E2E tesztek | 368 PASS (169 pre-existing + 199 Phase 1a) |
| Promptfoo tesztek | 96 test case |
| Ruff lint | 0 hiba |
| TypeScript | 0 hiba |
| Alembic migraciok | 33 |
| Pydantic domain contracts | 13 (IntakePackage + 12 altal, Phase 1a) |
| State machines | 7 (idempotent replay, Phase 1a) |
| Provider ABC | 4 (parser/classifier/extractor/embedder, Phase 1a) |

## Verziok

| Verzio | Datum | Fo deliverable |
|--------|-------|---------------|
| v1.0.0 | 2026-04-02 | Service Generalization (F0-F5) |
| v1.1.4 | 2026-04-03 | UI Modernization (Untitled UI + Tailwind v4) |
| v1.2.0 | 2026-04-03 | Pipeline as Code (C0-C20) |
| v1.2.1 | 2026-04-04 | Production Ready Sprint (S1-S14) |
| v1.2.2 | 2026-04-05 | Infrastructure + Security + Guardrails (Sprint A) |
| v1.3.0 | 2026-04-09 | E2E Service Excellence (Sprint B, B0-B11) |
| v1.4.0 | 2026-04-17 | Phase 1a Foundation — IntakePackage contracts (13 Pydantic) + 7 state machines, PolicyEngine + profile A/B overrides, ProviderRegistry + 4 ABC (parser/classifier/extractor/embedder), SkillInstance.policy_override, backward compat shim + pipeline auto-upgrade (v1.3 -> v1.4), 199 Phase 1a E2E, Alembic 032 intake_tables + 033 policy_overrides |
