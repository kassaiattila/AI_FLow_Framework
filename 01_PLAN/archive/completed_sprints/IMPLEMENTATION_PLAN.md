# AIFlow Implementation Plan - Claude Code Execution Guide

**Cel:** Ez a fajl a Claude Code szamara keszult, hogy a teljes AIFlow keretrendszert
es a 6 skill-t felepigtse, lepesrol lepesre. A `01_PLAN/` mappa dokumentumai alapjan.

**Utolso frissites:** 2026-04-01 (konzisztencia audit alapjan)
**Statusz:** Framework KESZ (Phase 1-7), 4/6 skill WORKING, 1/6 IN DEV, 1/6 STUB. Aktualis: Service Generalization (Fazis 0-5, vertikalis szeletek) → ld. `42_SERVICE_GENERALIZATION_PLAN.md`

---

## PILOT PROJEKT HIVATKOZASOK (Forras kod)

| # | Skill | Pilot Projekt | Pontos Eleresi Ut | Fo Tanulsagok |
|---|-------|--------------|-------------------|---------------|
| 1 | process_documentation | Diagram Gen AI Agent | `C:\Users\kassaiattila\OneDrive - BestIxCom Kft\00_BESTIX_KFT\11_DEV\80_Sample_Projects\06_Diagram_Gen_AI_Agent\data` | Langfuse SSOT, Workflow Registry, Promptfoo |
| 2 | aszf_rag_chat | Allianz RAG Unified | `C:\Users\kassaiattila\OneDrive - BestIxCom Kft\00_BESTIX_KFT\11_DEV\94_Cubix_RAG_AI\allianz-rag-unified\` | pgvector, hybrid search, reranker, Next.js UI |
| 3 | email_intent_processor | CFPB ML Pilot + uj | CFPB sklearn logika beepitve | Hibrid ML+LLM, JSON schema vezerelt, 10 intent |
| 4 | cubix_course_capture | Cubix Automation + Transcript | `C:\Users\kassaiattila\BestIxCom Kft\Bestix Kft. - Documents\07_Szakmai_Anyagok\AI\Cubix_AI_ML\automation\` ES `C:\Users\kassaiattila\BestIxCom Kft\Bestix Kft. - Documents\07_Szakmai_Anyagok\AI\Cubix_AI_ML\transcript_pipeline\` | Temporal->AIFlow, Playwright, ffmpeg, STT |
| 5 | qbpp_test_automation | AZHU MultiApp AutoTester | `C:\Users\kassaiattila\OneDrive - BestIxCom Kft\00_BESTIX_KFT\11_DEV\50_AZHU\03_AZHU_AutoTest\MultiApp_AutoTester\` | Playwright, registry-driven, BDD, strategy-based |

> **Megjegyzes:** A cfpb_complaint_router (korabbi #5) osszevonva az email_intent_processor-ral (2026-03-29).
> Az sklearn classifier logika (TF-IDF + LinearSVC) mar az email_intent_processor reszekent mukodik.

---

## SKILL DASHBOARD (frissitve: 2026-03-29 session vege)

| # | Skill | Statusz | Tesztek | Ugyfelek | Megjegyzes |
|---|-------|---------|---------|----------|------------|
| 1 | process_documentation | **PRODUCTION** | 13 | BESTIX | 5 step, multi-format export |
| 2 | cubix_course_capture | **75%** | 13 | BESTIX | Transcript pipeline mukodik, RPA reszleges |
| 3 | aszf_rag_chat | **85%** | **52** | AZHU, NPRA, BESTIX | RAG pipeline + tesztek KESZ |
| 4 | email_intent_processor | **90%** | **54** | AZHU, BESTIX | Discovery pipeline, ugyfal-schema, hibrid ML+LLM |
| 5 | invoice_processor | **70%** | **22** | BESTIX | **UJ** - 20 valos szamla feldolgozva, CSV/Excel/JSON |
| 6 | qbpp_test_automation | **STUB** | 3 | AZHU, NPRA | Varja az AZHU portal hozzaferest |

**Osszesen: 6 skill, 157 teszt fuggveny, 869 framework+skill teszt PASS**

---

## HATRALEVO FEJLESZTESI FAZISOK (prioritas szerint)

### F1: Production UI - Workflow Viewer + Validacio (2-3 het)
Cel: Minden AIFlow skill-hez atlathato, validalhato UI felulet
- Step-by-step vizualizacio (input/output megtekintheto)
- Side-by-side nézet: eredeti dokumentum vs kinyert adat
- Confidence score megjelenes per step
- Prompt/LLM koltseg monitoring real-time
- Technologia: Reflex (skeleton mar letezik src/aiflow/ui/)
- Reszletes terv: 01_PLAN/14_FRONTEND.md

### F2: Cost Monitoring + Prompt Tracking (1 het)
Cel: Minden LLM hivas koltseget kovetni, jelezni, riportalni
- src/aiflow/observability/cost_tracker.py MAR LETEZIK (infrastruktura kesz)
- Hianyzik: per-skill integration (csak aszf_rag_chat hasznalta eddig)
- Hianyzik: dashboard UI (KPI card skeleton van, de nincs page)
- Hianyzik: prompt versioning + A/B teszt koltseg osszehasonlitas
- Cel: koltseg/szamla, koltseg/email, koltseg/query metrikak

### F3: ML Training Pipeline (1-2 het)
Reszletes terv: 01_PLAN/31_INTENT_DISCOVERY_ML_PIPELINE.md
- Fazis C: LLM Labeling (llm_labeler.py, label_reviewer.py)
- Fazis D: sklearn Trainer (trainer.py, evaluator.py)
- Fazis E: Continuous Learning (collector.py)
- Fazis F: Claude Code slash commands (/train-model, /evaluate-model)

### F4: AZHU Deployment (1 het)
- Per-customer Docker Compose
- Streaming SSE valasz (chat_completions.py)
- Instance config injection (singleton refactor)
- JWT auth bekotes
- Golden dataset bovites (14 -> 50+)

### F5: Tovabbi Skillek (folyamatos)
- qbpp_test_automation: AZHU portal hozzaferes utan (2-3 het)
- cubix_course_capture: RPA pipeline befejezese (1 het)
- invoice_processor: Alembic migracio + DB storage (1 nap)

---

## FAZIS 1-7: FRAMEWORK IMPLEMENTACIO - KESZ

> **Statusz:** Az alabbi fazisok (Het 1-22) leirasa eredeti tervkent keszult.
> A framework kod (`src/aiflow/`) 2026-03-28-29-en teljes egeszeben implementalva lett.
> Az `agents/` modul torolve (2026-03-29, egyetlen skill sem hasznalta).
> Reszletes modulterkep: `src/aiflow/CLAUDE.md`

### Fazis 1 (Het 1-3): Foundation - KESZ
- core/ (config, context, DI, errors, events, registry, types)
- state/ (SQLAlchemy ORM, repository, 13 Alembic migracio, 25+ tabla)
- Docker Compose, Makefile, CI/CD

### Fazis 2 (Het 4-6): Engine + Models + VectorStore - KESZ
- engine/ (@step, DAG, WorkflowRunner, SkillRunner, checkpoint, policies)
- models/ (ModelClient, LiteLLM, 5 protocol, cost, router)
- vectorstore/ (pgvector, hybrid search, embedder)

### Fazis 3 (Het 7-9): Prompts + Documents + Ingestion - KESZ
- prompts/ (PromptManager, YAML + Jinja2, A/B testing)
- documents/ (DocumentRegistry, versioning, freshness)
- ingestion/ (PDF/DOCX/Docling parsers, recursive/semantic chunkers)

### Fazis 4 (Het 10-13): Skills - RESZLEGES (lasd dashboard fent)

### Fazis 5 (Het 14-16): Execution + API + Security - KESZ
- execution/ (JobQueue, Worker, Scheduler, RateLimiter, DLQ)
- api/v1/ (FastAPI, health, chat_completions, feedback)
- security/ (JWT RS256, RBAC 4 role, audit, guardrails)

### Fazis 6 (Het 17-19): CLI + Observability - KESZ
- cli/ (typer, 6 command group)
- observability/ (tracing, cost_tracker, metrics, SLA) - Langfuse TODO-k megmaradtak

### Fazis 7 (Het 20-22): Production - RESZLEGES
- K8s base manifesztek kesz, overlay-ek uresek
- Vault integracio TODO
- CI/CD workflow-ok kesz

---

## RESZLETES EREDETI TERVEK (referencia)

> Az alabbi reszletes fazis leirasok az eredeti terv reszei.
> A framework implementacio soran keszultek el. Referenciakent megorizve.

## FAZIS 1: FOUNDATION (Het 1-3)

### Het 1: Monorepo + Core Kernel

```
FEJLESZTOI KORNYEZET (27_DEVELOPMENT_ENVIRONMENT.md):
- Python 3.12+ + uv (package manager) KOTELEZO a fejleszto gepen
- `uv venv` -> .venv/ letrehozas
- `uv pip install -e ".[dev]"` -> fuggosegek
- `uv.lock` -> MINDIG commitolva (reprodukalhato build)
- Docker szolgaltatasok: `make dev` (postgres + redis + kroki)
- Kod fut lokálisan .venv-bol (IDE tamogatas, hot reload)

FELADATOK:
1. GitHub repo: aiflow (monorepo) - MAR KESZ (baseline commit)
2. pyproject.toml (fuggosegek: 05_TECH_STACK.md alapjan, uv kompatibilis PEP 621)
3. uv.lock generalas: `uv pip compile pyproject.toml -o uv.lock`
4. Makefile (27_DEVELOPMENT_ENVIRONMENT.md 5. szekció - 20+ target)
5. src/aiflow/__init__.py - public API exports
6. src/aiflow/_version.py - "0.1.0"
7. src/aiflow/core/config.py - AIFlowSettings (pydantic-settings)
   MINTA: 06_Diagram_Gen_AI_Agent/src/config.py (52-162 sor)
8. src/aiflow/core/types.py - Status enum, kozos tipusok
9. src/aiflow/core/errors.py - TransientError/PermanentError hierarchia
   RESZLETEK: 08_ERROR_HANDLING_DEBUGGING.md 1.1 szekció
10. src/aiflow/core/context.py - ExecutionContext
    RESZLETEK: 01_ARCHITECTURE.md 2.1 szekció
11. src/aiflow/core/events.py - Event Bus (CrewAI minta)
12. src/aiflow/core/registry.py - univerzalis registry
13. src/aiflow/core/di.py - DI container
14. .pre-commit-config.yaml (17_GIT_RULES.md 9. szekció)
15. .github/CODEOWNERS (17_GIT_RULES.md 2. szekció)
16. src/aiflow/CLAUDE.md - Framework kontextus (26_CLAUDE_CODE_SETUP.md)
17. tests/CLAUDE.md - Test kontextus (26_CLAUDE_CODE_SETUP.md)
18. tests/conftest.py - Globalis fixtures (25_TEST_DIRECTORY_STRUCTURE.md 9. szekció)
19. tests/test_suites.yaml - Elso suite definiciok (24_TESTING_REGRESSION_STRATEGY.md)
20. tests/regression_matrix.yaml - Elso matrix szabalyok (24_TESTING_REGRESSION_STRATEGY.md)
21. scripts/check_environment.sh - Kornyezet ellenorzo (27_DEVELOPMENT_ENVIRONMENT.md 10. szekció)

TESZTEK: tests/unit/core/test_config.py, test_context.py, test_errors.py, test_registry.py
VERIFIKACIO:
  uv venv && uv pip install -e ".[dev]"    # Kornyezet mukodik
  make dev                                  # Docker szolgaltatasok elindulnak
  pytest tests/unit/core/ -v               # ZOLD
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
1. docker-compose.yml - pgvector/pgvector:pg16, redis:7-alpine, kroki
   RESZLETEK: 27_DEVELOPMENT_ENVIRONMENT.md 6. szekció (profiles: core/full/tools)
2. Dockerfile - uv-alapu multi-stage (api, worker, rpa-worker)
   RESZLETEK: 27_DEVELOPMENT_ENVIRONMENT.md 8. szekció
3. aiflow.yaml - framework config (23_CONFIGURATION_REFERENCE.md)
4. .env.example - titkok template (23_CONFIGURATION_REFERENCE.md 3. szekció)
5. src/aiflow/observability/logging.py - structlog JSON
6. .github/workflows/ci-framework.yml (uv pip sync uv.lock - reprodukalhato!)
   RESZLETEK: 27_DEVELOPMENT_ENVIRONMENT.md 7. szekció
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

### ~~Het 12: CFPB ML Complaint Router~~ - OSSZEVONVA email_intent_processor-ral (2026-03-29)
> Az sklearn classifier logika (TF-IDF + LinearSVC) beepult az email_intent_processor skillbe.
> Lasd: skills/email_intent_processor/classifiers/sklearn_classifier.py

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
6. Docker Compose prod per-customer (K8s manifests kesobb, amikor cluster elerheto)
7. .github/workflows/ - deploy-staging.yml, deploy-prod.yml
8. Evaluation framework: test_datasets/test_cases DB tablak
   RESZLETEK: 18_TESTING_AUTOMATION.md 6. szekció
```

---

## VERIFIKACIO MINDEN FAZIS VEGEN

```bash
# Kornyezet ellenorzes (27_DEVELOPMENT_ENVIRONMENT.md)
bash scripts/check_environment.sh            # Python, uv, Docker, .venv, .env ellenorzes

# Automatikus (CI - uv.lock-bol reprodukalhatoan)
make lint                                    # ruff check + ruff format + mypy
make test-cov                                # Unit tesztek + coverage
make test-integration                        # Integracio (Docker szolgaltatasok kellenek)

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

---

## FAZIS A-E: MODULAR DEPLOYMENT + VALOS SKILL-EK

### FAZIS A: Instance Infrastruktura (1-2 het) - KESZ 2026-03-28

```
STATUSZ: KESZ
FELADATOK:
1. [KESZ] skill_instances DB tabla + 012_add_skill_instances.py migracio
2. [KESZ] src/aiflow/skills/instance.py - SkillInstance model + InstanceManager
3. [KESZ] deployments/ konyvtar struktura + DeploymentManifest model
4. [KESZ] CLI: aiflow instance create/list/configure
5. [KESZ] workflow_runs.instance_id FK bovites
6. [KESZ] Instance YAML loader + registry (instance_loader.py, instance_registry.py)
7. [KESZ] ExecutionContext bovites (instance_id, customer, prompt_namespace)
8. [KESZ] 42 uj unit teszt (803/803 PASSED)
9. [KESZ] 3 ugyfel deployment config (AZHU, NPRA, BESTIX)
```

### FAZIS A2: Valos Skill Implementacio - KESZ 2026-03-28

```
STATUSZ: KESZ (process_documentation + cubix transcript pipeline)

PROCESS DOCUMENTATION SKILL:
1. [KESZ] Pydantic I/O modellek (ProcessExtraction, ClassifyOutput, ReviewOutput)
2. [KESZ] 5 prompt YAML (classifier, elaborator, extractor, reviewer, mermaid_flowchart)
3. [KESZ] 5+1 step fuggveny (classify, elaborate, extract, review, generate_diagram, export_all)
4. [KESZ] Multi-format export: .mmd + .svg (Kroki) + .drawio (XML) + .md tablazat + .json
5. [KESZ] Miro API export (opcionalis, ha MIRO_API_TOKEN konfiguralt)
6. [KESZ] Template-alapu diagram generator (LLM nelkul)
7. [KESZ] 13 unit teszt + valos LLM integracios teszt (3 magyar folyamat)
8. [KESZ] Valos output: test_output/diagrams/{folyamat_nev}/

CUBIX TRANSCRIPT PIPELINE:
1. [KESZ] 10 Pydantic model (AudioProbeResult -> StructuredTranscript)
2. [KESZ] TranscriptPipelineConfig (ffmpeg, STT, chunk parameterek)
3. [KESZ] 6 step fuggveny (probe, extract_audio, chunk, transcribe, merge, structure)
4. [KESZ] 1 prompt YAML (transcript_structurer)
5. [KESZ] 13 unit teszt + valos STT integracios teszt (3 MKV feldolgozva)
6. [KESZ] Valos output: test_output/*.json, *.txt

CONTRIB MODULOK:
1. [KESZ] src/aiflow/contrib/shell/executor.py - ShellExecutor (ffmpeg/ffprobe wrapper)
2. [KESZ] src/aiflow/contrib/playwright/browser.py - PlaywrightBrowser (RPA)
3. [KESZ] src/aiflow/contrib/human_loop/manager.py - HumanLoopManager (HITL)

CUBIX RPA PIPELINE (teljes):
1. [KESZ] course_capture.py - 4 step (resolve_and_login, scan_structure, process_all_lessons, report)
2. [KESZ] Platform config: cubixedu.py (szelektorok, JS snippetek)
3. [KESZ] File state manager (pipeline_state.json, resume tamogatas)
4. [KESZ] Kurzus-szintu output konyvtar (Cubix_ML_Course/week_XX/lesson_YY/)
```

### FAZIS A3: DrawIO Portalas + RF Integration + Mappa Refactor - KESZ 2026-03-28

```
STATUSZ: KESZ

MAPPA REFACTOR:
1. [KESZ] src/aiflow/skills/ -> src/aiflow/skill_system/ (backward compat re-export)
2. [KESZ] Ket skills/ mappa problema tisztazva

DRAWIO PORTALAS (Lesotho DHA projekt):
1. [KESZ] skills/process_documentation/drawio/builder.py - DrawioBuilder (18KB, teljes port)
2. [KESZ] skills/process_documentation/drawio/bpmn.py - BPMNDiagram (15KB, swimlane BPMN)
3. [KESZ] skills/process_documentation/drawio/colors.py - 14 arch + 5 lane + 9 BPMN szin
4. [KESZ] skills/process_documentation/drawio/stencils.py - Stencil loader (3423 shape)
5. [KESZ] skills/process_documentation/drawio/stencil_catalog.json - 5.7MB stencil gyujtemeny
6. [KESZ] drawio_exporter.py ujrairva DrawioBuilder-rel + BPMN swimlane export
7. [KESZ] export_all step: diagram.drawio + diagram_bpmn.drawio + diagram.svg + .mmd + .md + .json

ROBOT FRAMEWORK INTEGRACIO:
1. [KESZ] src/aiflow/tools/robotframework_runner.py - RobotFrameworkRunner (async subprocess)
2. [KESZ] skills/cubix_course_capture/robot/ - 5 .robot + 4 .js portolva pilot-bol
3. [KESZ] course_capture.py - RF/Playwright dual mode (automatikus valasztas)
4. [KESZ] Robot Framework 7.4.2 telepitve es verifikalt
```

### FAZIS A4: AIFlow Keretrendszer Felulvizsgalat - AUDIT KESZ 2026-03-28

```
STATUSZ: AUDIT KESZ, OPTIMALIZACIO TERVEZETT
RESZLETES TERV: 01_PLAN/29_OPTIMIZATION_PLAN.md

AUDIT EREDMENYEK (valos hasznalat alapjan):
  HASZNALT (ertekes): ModelClient, PromptManager, @step, structlog, Pydantic, FileStateManager
  NEM HASZNALT (holt kod): WorkflowRunner, DI Container, ExecutionContext, Agent system, API stubbok

OPTIMALIZACIOS FAZISOK:
  O1 [KESZ]: Runner service injection + SkillRunner + CLI entry pointok
  O2 [KESZ]: skill_config.yaml mindket skillhez
  O3 [KESZ]: tools/ merge (contrib/ -> tools/ flat), holt kod deprecation
  KOVETKEZO: RAG production pipeline + OpenChat UI
```

### FAZIS A5: ASZF RAG Chat + Docling + Alembic - KESZ 2026-03-29

```
STATUSZ: KESZ

RAG SKILL:
1. [KESZ] 9 Pydantic model (QueryInput/Output, SearchResult, Citation, IngestInput/Output)
2. [KESZ] 7 prompt YAML (query_rewriter, answer_generator, citation, hallucination, 3 role)
3. [KESZ] Ingest workflow: 6 step (load, parse/docling, chunk, embed, store/pgvector, verify)
4. [KESZ] Query workflow: 6 step (rewrite, search, context, answer, cite, hallucination)
5. [KESZ] CLI: python -m skills.aszf_rag_chat ingest/query
6. [KESZ] Valos teszt: 2 Allianz PDF -> 28 chunk -> pgvector -> query 5 talalat

DOCLING INTEGRACIO:
1. [KESZ] src/aiflow/ingestion/parsers/docling_parser.py - Universal parser
2. [KESZ] PDF tabla/layout felismeres mukodik

ALEMBIC MIGRACIK:
1. [KESZ] 005 javitva (duplicate column fix)
2. [KESZ] 011 javitva (finished_at -> completed_at)
3. [KESZ] 001-012 mind lefutott tiszta DB-n
4. [KESZ] 25 tabla + 3 view + rag_chunks

VECTORSTORE:
1. [KESZ] pgvector_store.py - dual backend (asyncpg + in-memory)
2. [KESZ] embedder.py - batch embedding (text-embedding-3-small, batch=5)
3. [KESZ] search.py - HybridSearchEngine (RRF)

REFLEX GUI:
1. [KESZ] ChatGPT/Claude stilusu chat interface
2. [BOVITENDO] OpenChat UI integracio (F1 fazis)

CUBIX REFERENCIA TANANYAG:
1. [KESZ] 4 utmutato + 2 kodpelda bemasoltuk reference/ mappaba
2. [BOVITENDO] Checklist kovetese (recursive chunking, evaluation)
```

### AKTUALIS FAZISOK (2026-03-29):

```
RESZLETES TERV: 01_PLAN/30_RAG_PRODUCTION_PLAN.md

F1 (1-2 nap): OpenAI-kompatibilis API endpoint + OpenChat UI Docker
  - POST /v1/chat/completions (universal bridge - barmely chat UI)
  - OpenChat UI mint Docker service
  - Reflex UI -> admin/operator feluletre atalakitas

F2 (2-3 nap): RAG Production Pipeline (Cubix tananyag kovetese)
  - Recursive chunking (02_rag_pipeline ajanlasa)
  - Heading-based chunking (docling fejlec felismeres)
  - Evaluation framework: golden dataset (50+ Q/A), LLM-as-Judge
  - Promptfoo integracio

F3 (1-2 nap): Multi-tenant collection konfig
  - Per-collection chunking/embedding/search strategia
  - Instance config -> collection config integralas
  - CLI: --config deployments/azhu/instances/azhu-aszf-rag.yaml

F4 (1 nap): DB infra (Alembic 013+)
  - rag_collections tabla
  - rag_query_log tabla (monitoring)
  - Per-collection statisztikak view
```

### FAZIS A6: Modul 06-07 (CI/CD + Monitoring) - KESZ 2026-03-29

```
STATUSZ: KESZ

MODUL 06 (CI/CD):
1. [KESZ] Promptfoo config (7 teszt eset, provider script)
2. [KESZ] Feedback API (POST /v1/feedback + GET /v1/feedback/stats)

MODUL 07 (Monitoring):
1. [KESZ] Query logging (log_query step -> rag_query_log tabla)
2. [KESZ] Health endpoint (valos DB/pgvector/Redis/RAG check)

CUBIX RAG CHECKLIST: MIND A 7 MODUL ALAPSZINTEN TELJESITVE
```

### AKTUALIS: Email + Csatolmany Feldolgozo Szolgaltatas

```
RESZLETES TERV: .claude/plans/delegated-nibbling-summit.md (v7)
REFERENCIA: CFPB ML pilot (sklearn TF-IDF + LinearSVC, 10 routing csoport)

ARCHITEKTURA:
  1. Konfiguralhato JSON schema rendszer (schemas/v1/*.json)
     - intents.json, entities.json, document_types.json, routing_rules.json
     - Verziozott, ugyfal-specifikus, kodmodositas nelkul bovitheto
  2. Harom retegu csatolmany feldolgozas
     - Docling (lokalis) -> Azure Document Intelligence (felho/OCR) -> LLM Vision
  3. Hibrid intent klasszifikacio
     - sklearn ML (CFPB port, <1ms) + LLM finomitas (gpt-4o-mini)
     - Intent meghatarozas email + csatolmany EGYUTTES tartalmabol
  4. Strukturalt adatpont tarolas
     - email_processing_results tabla (JSONB: entitasok, csatolmanyok, routing)
     - Csatolmany-specifikus mező kinyerés (document_types.json vezerelt)

FAZISOK:
  E1 (1 nap): Framework eszkozok (email_parser, attachment_processor, azure_di, schema_registry)
  E2 (2-3 nap): Email Intent skill (models, classifiers, workflow, prompts, schemas)
  E3 (0.5 nap): API integracio
  E4 (1 nap): Tesztek + evaluation
```

### FAZIS B: Hatra levo framework munka (2-3 het)

```
FELADATOK:
1. Langfuse integracio (PromptManager Phase B)
2. Streaming valasz (SSE/WebSocket)
3. CI/CD pipeline (GitHub Actions + Promptfoo)
4. Tovabbi skillek (qbpp_test_automation)
5. Multi-tenant deployment veglegesites
```

### FAZIS C: Skill Portalas - Prioritasi Sorrend (12-16 het)

> **Portalasi prioritas:** A pilot projektek mind mukodnek a sajat kornyezetukben.
> A sorrend figyelembe veszi: framework validacio, ugyfel igeny, fuggosegek.

```
PORTALASI PRIORITAS:

1. process_documentation (Diagram Gen) - 2-3 het
   BESTIX belso, jo framework validacios darab (5 agent, quality gate, refine loop)
   FORRAS: C:\Users\kassaiattila\OneDrive - BestIxCom Kft\00_BESTIX_KFT\11_DEV\80_Sample_Projects\06_Diagram_Gen_AI_Agent\data
   UGYFELEK: BESTIX
   FELADATOK:
   - Modellek, promptok, agent-ek portalasa AIFlow keretbe
   - 120+ teszt eset
   - Elso instance: deployments/bestix/instances/bestix-process-docs.yaml

2. aszf_rag_chat (RAG Chat) - 3-4 het
   Mind a 3 ugyfel hasznalja (AZHU, NPRA, BESTIX), legmagasabb uzleti prioritas
   FORRAS: C:\Users\kassaiattila\OneDrive - BestIxCom Kft\00_BESTIX_KFT\11_DEV\94_Cubix_RAG_AI\allianz-rag-unified\
   UGYFELEK: AZHU, NPRA, BESTIX
   FELADATOK:
   - Multi-instance tamogatas (collection, prompt namespace per instance)
   - 150+ teszt eset
   - Instance-ok: azhu/hr_aszf_chat, npra/faq_rag, bestix/internal_rag

3. cubix_course_capture + transcript_pipeline - 4-5 het
   BESTIX belso hasznalat (Cubix AI/ML kurzusok rogzitese)
   FORRAS: C:\Users\kassaiattila\BestIxCom Kft\Bestix Kft. - Documents\07_Szakmai_Anyagok\AI\Cubix_AI_ML\automation\
           C:\Users\kassaiattila\BestIxCom Kft\Bestix Kft. - Documents\07_Szakmai_Anyagok\AI\Cubix_AI_ML\transcript_pipeline\
   UGYFELEK: BESTIX (+ NPRA kesobb)
   FELADATOK:
   - Temporal->AIFlow migracio, Playwright + ffmpeg + STT pipeline
   - Operator-assisted lepesek (HumanReviewRequiredError)
   - Instance: deployments/bestix/instances/bestix-cubix-capture.yaml

4. qbpp_test_automation - 2-3 het
   AZHU + NPRA ugyfel igeny (biztositasi kalkulator teszteles)
   FORRAS: C:\Users\kassaiattila\OneDrive - BestIxCom Kft\00_BESTIX_KFT\11_DEV\50_AZHU\03_AZHU_AutoTest\MultiApp_AutoTester\
   UGYFELEK: AZHU, NPRA
   FELADATOK:
   - pytest-bdd -> AIFlow workflow (registry load -> generate -> run -> analyze)
   - Instance: deployments/azhu/instances/azhu-portal-test.yaml

5. email_intent_processor - AKTIV FEJLESZTES (2026-03-29)
   Hibrid ML+LLM email feldolgozo (CFPB sklearn logika beepitve)
   UGYFELEK: AZHU, BESTIX
   STATUSZ: 80% kesz, 10 intent, JSON schema vezerelt
   KOVETKEZO: Intent discovery valos adatokbol, Docling/AzureDI quality routing

   > cfpb_complaint_router osszevonva ide (2026-03-29)
```

### FAZIS D: Customer Deployment Infra (2-3 het, parhuzamos a skill portalassal)

```
FELADATOK:
1. Per-customer Docker Compose config (K8s kesobb)
   - deployments/azhu/docker-compose.yml
   - deployments/npra/docker-compose.yml
   - deployments/bestix/docker-compose.yml
2. CI Pipeline D (customer deployment validacio - 3 ugyfel)
3. Staging Docker kornyezetek (BESTIX eloszor mint belso teszt)
4. Elso customer deployment teszt
5. BESTIX deployment mint "dogfooding" - belso hasznalat validalja a framework-ot
```

### FAZIS E: Production Deployment (2-3 het)

```
FELADATOK:
1. BESTIX deployment veglegesites (belso teszt + demo environment)
2. AZHU production deployment (enterprise - 4 instance)
3. NPRA production deployment (business - 3 instance)
4. Monitoring + alerting setup per customer (Langfuse + Grafana)
5. Dokumentacio: operations runbook per customer
```
