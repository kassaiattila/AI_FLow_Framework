# AIFlow Implementation Plan - Claude Code Execution Guide

**Cel:** Ez a fajl a Claude Code szamara keszult, hogy a teljes AIFlow keretrendszert
es a 6 skill-t felepigtse, lepesrol lepesre. A `` mappa 23 dokumentuma alapjan,
6 meglevo pilot projekt mintainak felhasznalasaval.

---

## PILOT PROJEKT HIVATKOZASOK (Forras kod)

| # | Skill | Pilot Projekt | Hely | Fo Tanulsagok |
|---|-------|--------------|------|---------------|
| 1 | Process Documentation | Diagram Gen AI Agent | `06_Diagram_Gen_AI_Agent/src/` | Langfuse SSOT, Workflow Registry, Promptfoo |
| 2 | ASZF RAG Chat | Allianz RAG Unified | `94_Cubix_RAG_AI/allianz-rag-unified/` | pgvector, hybrid search, reranker, Next.js UI |
| 3 | Email Intent | (uj, nincs pilot) | - | Kafka trigger minta a 19_RPA-bol |
| 4 | Cubix Course Capture | Cubix Automation + Transcript | `Cubix_AI_ML/automation/` + `transcript_pipeline/` | Temporal->AIFlow, Playwright, ffmpeg, STT |
| 5 | CFPB Complaint Router | CFPB ML Pilot | `Cubix_AI_ML/01_Pilot_ML/01_cfpb_complaints/` | sklearn pipeline, TF-IDF, FastAPI serving |
| 6 | QBPP Test Automation | AZHU MultiApp AutoTester | `50_AZHU/03_AZHU_AutoTest/MultiApp_AutoTester/` | Playwright, registry-driven, BDD, strategy-based |

---

## FAZIS 1: FOUNDATION (Het 1-3)

### Het 1: Monorepo + Core Kernel

```
FELADATOK:
1. GitHub repo: aiflow (monorepo)
2. pyproject.toml (fuggosegek: 05_TECH_STACK.md alapjan)
3. src/aiflow/__init__.py - public API exports
4. src/aiflow/_version.py - "0.1.0"
5. src/aiflow/core/config.py - AIFlowSettings (pydantic-settings)
   MINTA: 06_Diagram_Gen_AI_Agent/src/config.py (52-162 sor)
6. src/aiflow/core/types.py - Status enum, kozos tipusok
7. src/aiflow/core/errors.py - TransientError/PermanentError hierarchia
   RESZLETEK: 08_ERROR_HANDLING_DEBUGGING.md 1.1 szekció
8. src/aiflow/core/context.py - ExecutionContext
   RESZLETEK: 01_ARCHITECTURE.md 2.1 szekció
9. src/aiflow/core/events.py - Event Bus (CrewAI minta)
10. src/aiflow/core/registry.py - univerzalis registry
11. src/aiflow/core/di.py - DI container
12. .pre-commit-config.yaml (17_GIT_RULES.md 9. szekció)
13. .github/CODEOWNERS (17_GIT_RULES.md 2. szekció)

TESZTEK: tests/unit/core/test_config.py, test_context.py, test_errors.py, test_registry.py
VERIFIKACIO: pytest tests/unit/core/ -v -> ZOLD
```

### Het 2: State + LLM

```
FELADATOK:
1. src/aiflow/state/models.py - SQLAlchemy ORM
   TABLAK: workflow_runs, step_runs (03_DATABASE_SCHEMA.md 1. szekció)
2. src/aiflow/state/repository.py - CRUD muveletek
3. alembic/ setup + 001_initial_schema.py migracio
4. src/aiflow/models/metadata.py - ModelType, ModelLifecycle, ModelMetadata enums
   RESZLETEK: 15_ML_MODEL_INTEGRATION.md
5. src/aiflow/models/protocols/generation.py - TextGenerationProtocol
6. src/aiflow/models/protocols/embedding.py - EmbeddingProtocol
7. src/aiflow/models/backends/litellm_backend.py - LiteLLM wrapper
   MINTA: 06_Diagram_Gen_AI_Agent/src/config.py _setup_litellm_langfuse_callback
8. src/aiflow/models/client.py - ModelClient (generate + embed)
   BACKWARD COMPAT: LLMClient = ModelClient alias
9. src/aiflow/models/registry.py - ModelRegistry (DB-backed)

TESZTEK: tests/unit/models/test_client.py, tests/integration/test_state_store.py
VERIFIKACIO: alembic upgrade head + pytest -> ZOLD
```

### Het 3: Docker + Logging + CI

```
FELADATOK:
1. docker-compose.yml - pgvector/pgvector:pg16, redis:7-alpine, aiflow-api
   MINTA: 06_Diagram_Gen_AI_Agent/docker-compose.yml
2. Dockerfile - Python 3.12 + uvicorn
3. aiflow.yaml - framework config
4. .env.example - titkok template
5. src/aiflow/observability/logging.py - structlog JSON
6. Makefile (make dev, make test, make lint, make migrate)
7. .github/workflows/ci-framework.yml
   RESZLETEK: 18_TESTING_AUTOMATION.md 3. szekció

VERIFIKACIO: docker compose up -d, curl localhost:8000/api/v1/health -> {"status": "healthy"}
```

---

## FAZIS 2: ENGINE + MODELS (Het 4-6)

### Het 4: Step + DAG

```
FELADATOK:
1. src/aiflow/engine/step.py - @step decorator + output_types
   MINTA: Haystack @component.output_types (13_GITHUB_RESEARCH.md 3.1)
2. src/aiflow/engine/dag.py - DAG (add_node, add_edge, topological_sort, validate)
3. src/aiflow/engine/conditions.py - Condition kiertekeles elagazasokhoz
4. src/aiflow/engine/policies.py - RetryPolicy, CircuitBreaker, Timeout
   MINTA: LangGraph RetryPolicy 1:1 (13_GITHUB_RESEARCH.md 1.3)

TESZTEK: tests/unit/engine/test_step.py, test_dag.py, test_policies.py
```

### Het 5: Workflow Builder + Runner

```
FELADATOK:
1. src/aiflow/engine/workflow.py - @workflow + WorkflowBuilder
   API: step(), branch(), edge(), join(), quality_gate(), subworkflow(), parallel_map(), for_each()
   RESZLETEK: 01_ARCHITECTURE.md 3.2 szekció
2. src/aiflow/engine/runner.py - WorkflowRunner
   RESZLETEK: 01_ARCHITECTURE.md 3.4 szekció
3. src/aiflow/engine/checkpoint.py - version tracking (LangGraph minta)
4. src/aiflow/engine/serialization.py - Workflow YAML export/import (Haystack minta)

TESZTEK: tests/unit/engine/test_workflow.py, test_runner.py
VERIFIKACIO: Egyszeru 3-step workflow futtatasa kodbol -> WorkflowRun(status=completed)
```

### Het 6: Model Protocols + Vector Foundation

```
FELADATOK:
1. src/aiflow/models/protocols/classification.py
2. src/aiflow/models/protocols/extraction.py
3. src/aiflow/models/router.py - cost/capability routing + fallback
4. src/aiflow/vectorstore/base.py - VectorStore ABC, SearchResult, SearchFilter
5. src/aiflow/vectorstore/pgvector_store.py - HNSW + BM25
   MINTA: allianz-rag-unified/backend/services/vector_store.py
6. src/aiflow/vectorstore/embedder.py
7. src/aiflow/vectorstore/search.py - HybridSearchEngine (RRF)
   MINTA: allianz-rag-unified/backend/scripts/create_hybrid_search.py
8. DB migracio: model_registry, documents, chunks, collections tablak
   RESZLETEK: 15_ML_MODEL_INTEGRATION.md + 16_RAG_VECTORSTORE.md

TESZTEK: tests/unit/models/test_router.py, tests/unit/vectorstore/test_pgvector.py
```

---

## FAZIS 3: AGENTS + PROMPTS + DOCUMENTS (Het 7-9)

### Het 7: Agent System

```
FELADATOK:
1. src/aiflow/agents/specialist.py - SpecialistAgent base
2. src/aiflow/agents/messages.py - AgentRequest/AgentResponse (generikus)
3. src/aiflow/agents/orchestrator.py - OrchestratorAgent (max 6 specialist!)
4. src/aiflow/agents/quality_gate.py - QualityGate + score-alapu kapuk
5. src/aiflow/agents/human_loop.py - HumanReviewRequest + pauzalas
6. src/aiflow/agents/reflection.py - Generate-Critique-Improve

TESZTEK: tests/unit/agents/test_specialist.py, test_quality_gate.py
```

### Het 8: Prompt Platform

```
FELADATOK:
1. src/aiflow/prompts/schema.py - PromptDefinition YAML schema
2. src/aiflow/prompts/manager.py - PromptManager (Langfuse SSOT + YAML fallback + cache)
   MINTA: 06_Diagram_Gen_AI_Agent/src/langfuse_prompts.py
3. src/aiflow/prompts/sync.py - YAML -> Langfuse sync pipeline
   MINTA: 06_Diagram_Gen_AI_Agent/scripts/migrate_prompts_to_langfuse.py
4. src/aiflow/prompts/ab_testing.py - A/B testing traffic splitting

TESZTEK: tests/unit/prompts/test_manager.py, test_sync.py
```

### Het 9: Document Management + Ingestion

```
FELADATOK:
1. src/aiflow/documents/registry.py - DocumentRegistry (lifecycle: draft->active->superseded)
2. src/aiflow/documents/versioning.py
3. src/aiflow/documents/freshness.py - FreshnessEnforcer
4. src/aiflow/ingestion/parsers/pdf_parser.py
   MINTA: allianz-rag-unified/backend/services/pdf_processor.py
5. src/aiflow/ingestion/parsers/docx_parser.py
6. src/aiflow/ingestion/chunkers/semantic_chunker.py
   MINTA: allianz-rag-unified chunking (2500 char, 300 overlap)
7. src/aiflow/ingestion/pipeline.py

TESZTEK: tests/unit/documents/test_registry.py, tests/unit/ingestion/test_chunker.py
```

---

## FAZIS 4: SKILL-EK PORTALASA (Het 10-13)

### Het 10: Skill System + 1. Skill (Process Documentation)

```
FELADATOK:
1. src/aiflow/skills/manifest.py, base.py, loader.py, registry.py
2. skills/process_documentation/ - PORTALAS a POC-bol:
   FORRAS: 06_Diagram_Gen_AI_Agent/src/workflows/process_doc/workflow.py
   FORRAS: 06_Diagram_Gen_AI_Agent/src/tools/ (diagram_generator, table_generator, drawio, miro)
   FORRAS: 06_Diagram_Gen_AI_Agent/prompts/_source/process-doc/*.yaml
   FORRAS: 06_Diagram_Gen_AI_Agent/src/models/process.py
3. 120+ teszt eset (meglevo POC tesztek + bovites)
   FORRAS: 06_Diagram_Gen_AI_Agent/tests/promptfoo/

VERIFIKACIO: aiflow skill install ./skills/process_documentation -> 9 lepes OK
```

### Het 11: 2. Skill (ASZF RAG Chat)

```
FELADATOK:
1. skills/aszf_rag_chat/ - PORTALAS az Allianz RAG-bol:
   FORRAS: allianz-rag-unified/backend/services/ (embedding_service, vector_store, reranker, mmr)
   FORRAS: allianz-rag-unified/backend/config/system_prompts/ (baseline, mentor, expert)
   FORRAS: allianz-rag-unified/backend/database/models.py (Document, DocumentChunk schema)
   FORRAS: allianz-rag-unified/backend/api/routers/rag.py (query endpoint)
2. Ingestion workflow (document-ingest)
3. Q&A workflow (classify -> search -> rerank -> answer -> cite)
4. Multi-role support (baseline, mentor, expert prompts)
5. 150+ teszt eset (faithfulness, recall@5, citation accuracy, "nem tudom")

VERIFIKACIO: aiflow skill install + teszt dokumentum ingest + Q&A kerdes -> helyes valasz citacioval
```

### Het 12: 3. Skill (CFPB ML Complaint Router)

```
FELADATOK:
1. skills/cfpb_complaint_router/ - PORTALAS az ML pilot-bol:
   FORRAS: 01_cfpb_complaints/src/pipeline.py (train, predict, predict_proba)
   FORRAS: 01_cfpb_complaints/src/api.py (FastAPI endpoints)
   FORRAS: 01_cfpb_complaints/models/intent_routing_model.joblib
   ADAPTACIO: sklearn Pipeline -> AIFlow LocalModelBackend
   ADAPTACIO: intent_mapping dict -> AIFlow config
2. AIFlow workflow: clean_text -> classify -> route -> respond
3. 100+ teszt eset (10 routing group, edge cases)

VERIFIKACIO: aiflow workflow run cfpb-complaint-router --input '{"text": "..."}'
```

### Het 13: 4+5. Skill (Cubix RPA + QBPP Test)

```
FELADATOK:
1. skills/cubix_course_capture/ - PORTALAS:
   FORRAS: Cubix_AI_ML/automation/src/ (activities, workflows)
   FORRAS: Cubix_AI_ML/transcript_pipeline/src/ (transcribe, structure, merge)
   ADAPTACIO: Temporal -> AIFlow workflow DAG
   ADAPTACIO: Robot Framework -> Playwright step-ek
   src/aiflow/contrib/playwright/browser.py
   src/aiflow/contrib/shell/executor.py (ffmpeg sandbox)

2. skills/qbpp_test_automation/ - PORTALAS:
   FORRAS: MultiApp_AutoTester/config/field_registry_complete.json
   FORRAS: MultiApp_AutoTester/generators/orchestrator.py
   FORRAS: MultiApp_AutoTester/src/pages/generic_page_registry.py
   FORRAS: MultiApp_AutoTester/tests/step_defs/common_steps.py
   ADAPTACIO: pytest-bdd -> AIFlow workflow (registry load -> generate -> run -> analyze)
```

---

## FAZIS 5: EXECUTION + API + FRONTEND (Het 14-16)

### Het 14: Queue + Worker

```
1. src/aiflow/execution/queue.py - arq + Redis
2. src/aiflow/execution/worker.py
3. src/aiflow/execution/dlq.py
4. src/aiflow/execution/rate_limiter.py
5. docker-compose.yml: worker service hozzaadas
```

### Het 15: FastAPI + Security

```
1. src/aiflow/api/app.py - create_app() factory
2. src/aiflow/api/v1/ - minden endpoint (01_ARCHITECTURE.md 7.2)
3. src/aiflow/security/auth.py - JWT + API key
4. src/aiflow/security/rbac.py
5. src/aiflow/security/guardrails.py
6. DB migracio: teams, users, audit_log
```

### Het 16: Frontend (Reflex)

```
1. src/aiflow/ui/ scaffold (Reflex)
   RESZLETEK: 14_FRONTEND.md
2. Operator Dashboard (KPI, jobs, alerts)
3. Chat Interface (RAG, streaming, citacio)
   MINTA: allianz-rag-unified/frontend/src/components/chat/
4. Developer Portal (DAG viewer, prompt editor)
5. Admin Panel (users, teams, RBAC, audit)
```

---

## FAZIS 6: CLI + OBSERVABILITY (Het 17-19)

```
1. src/aiflow/cli/ - typer (workflow, skill, prompt, eval, dev, deploy)
2. src/aiflow/observability/tracing.py - Langfuse + OTel
3. src/aiflow/observability/cost_tracker.py
4. src/aiflow/observability/sla_monitor.py
5. Grafana dashboards (SQL views)
6. tests/e2e/test_full_pipeline.py
7. tests/ui/ - Playwright GUI tesztek (18_TESTING_AUTOMATION.md 7. szekció)
```

---

## FAZIS 7: PRODUCTION (Het 20-22)

```
1. src/aiflow/execution/scheduler.py - cron, event, webhook
2. src/aiflow/contrib/messaging/kafka.py - Kafka adapter
3. src/aiflow/documents/sync.py - SharePoint/S3/GDrive sync
4. src/aiflow/security/audit.py - teljes audit trail
5. src/aiflow/security/secrets.py - Vault integracio
6. k8s/ - Kubernetes manifests (base + overlays)
7. .github/workflows/ - deploy-staging.yml, deploy-prod.yml
8. Evaluation framework: test_datasets/test_cases DB tablak
   RESZLETEK: 18_TESTING_AUTOMATION.md 6. szekció
```

---

## VERIFIKACIO MINDEN FAZIS VEGEN

```bash
# Automatikus (CI)
make lint                                    # ruff + black + mypy
pytest tests/unit/ -v --cov=aiflow          # Unit tesztek + coverage
pytest tests/integration/ -v                # Integracio (Docker)

# Fazis 4+:
aiflow skill list                           # Skill-ek megjelennek
aiflow workflow list                        # Workflow-k regisztralva
npx promptfoo eval -c skills/*/tests/promptfooconfig.yaml  # Prompt tesztek

# Fazis 5+:
curl localhost:8000/api/v1/health           # API elerheto
aiflow workflow run process-documentation --input '{"message": "Szabadsag igenyles"}' --mode sync

# Fazis 6+:
pytest tests/e2e/ -v                        # E2E
pytest tests/ui/ -v                         # Playwright GUI

# Fazis 7:
docker compose -f docker-compose.prod.yml up  # Production stack
```

---

## GIT WORKFLOW MINDEN FAZISBAN

```bash
# Branch
git checkout -b feature/AIFLOW-{ticket}-{leiras}

# Fejlesztes (Claude Code)
# ... kodolas ...

# Commit (Conventional Commits)
git add src/aiflow/core/config.py tests/unit/core/test_config.py
git commit -m "feat(core): add AIFlowSettings with pydantic-settings

Co-Authored-By: Claude Code <noreply@anthropic.com>"

# PR
gh pr create --title "feat(core): add AIFlowSettings" --body "..."

# Merge (squash)
# CI zold + review -> squash merge to main
```
