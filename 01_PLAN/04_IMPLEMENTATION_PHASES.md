# AIFlow - Implementacios Fazisok v2 (Egysegitett)

## Valtozas a v1-hez kepest
- Egysegitett idovonal: 22 het (7 fazis)
- Integralt: ML Model reteg (15_ML), VectorStore (16_RAG), Frontend (14_FRONTEND), RPA (19_RPA)
- Integralt: 5 skill (cfpb_complaint_router beolvadt email_intent_processor-ba)
- Integralt: Security hardening (20_SECURITY)
- Integralt: GUI tesztek (18_TESTING)
- Javitva: llm/ -> models/ konyvtar mindenhol

---

## Attekintes

| Fazis | Het | Fo celkituzes | Kimenet |
|-------|-----|---------------|---------|
| 1. Foundation | 1-3 | Core kernel, State, Models, Docker, structlog | Mukodo dev kornyezet |
| 2. Engine + Vector | 4-6 | Step, DAG, Workflow, Runner, ModelRouter, VectorStore | Lokalis workflow futtatas |
| 3. Agents + Prompts + Docs | 7-9 | Agent system, Langfuse SSOT, Document lifecycle | Agentic workflow-k |
| 4. Skills (5 db) | 10-13 | POC portalas, 5 skill, 600+ teszt | Mukodo skill-ek |
| 5. Execution + API + Security | 14-16 | Queue, Worker, FastAPI, RBAC, Frontend scaffold | Teljes API + UI |
| 6. CLI + Observability | 17-19 | CLI, Tracing, Cost, SLA, Dashboards, E2E tesztek | Teljes lifecycle |
| 7. Production | 20-22 | Checkpoint, HITL, Scheduler, Kafka, K8s, CI/CD, Audit | Production-ready |

---

## Phase 1: Foundation (Het 1-3)

### Het 1: Projekt scaffold + Core kernel

**Fejlesztoi kornyezet (27_DEVELOPMENT_ENVIRONMENT.md):**
- `uv` telepitese (Python package manager) - `pip install uv`
- `uv venv` -> `.venv/` letrehozas
- `uv pip install -e ".[dev]"` -> fuggosegek
- `uv.lock` generalas es commitolas (reprodukalhato build)

**Feladatok:**
1. `pyproject.toml` - PEP 621 format, uv kompatibilis (05_TECH_STACK alapjan)
2. `uv.lock` - lockfile generalas (`uv pip compile pyproject.toml -o uv.lock`)
3. `Makefile` - 20+ target (27_DEVELOPMENT_ENVIRONMENT.md 5. szekció)
4. `src/aiflow/__init__.py` - public API exports
5. `src/aiflow/_version.py` - "0.1.0"
6. `src/aiflow/core/config.py` - AIFlowSettings (pydantic-settings)
7. `src/aiflow/core/types.py` - Status enum, kozos tipusok
8. `src/aiflow/core/errors.py` - TransientError/PermanentError hierarchia
9. `src/aiflow/core/context.py` - ExecutionContext (+ checkpoint_version)
10. `src/aiflow/core/events.py` - Event Bus (CrewAI minta)
11. `src/aiflow/core/registry.py` - univerzalis registry
12. `src/aiflow/core/di.py` - DI container
13. `.pre-commit-config.yaml`, `.github/CODEOWNERS`, PR template
14. `src/aiflow/CLAUDE.md` - Framework kontextus (26_CLAUDE_CODE_SETUP.md)
15. `tests/CLAUDE.md` - Test kontextus
16. `tests/conftest.py`, `tests/test_suites.yaml`, `tests/regression_matrix.yaml`
17. `scripts/check_environment.sh` - Kornyezet ellenorzo

**Teszt:** `tests/unit/core/test_config.py`, `test_context.py`, `test_errors.py`, `test_registry.py`

### Het 2: State + Model Client

**Feladatok:**
1. `src/aiflow/state/models.py` - SQLAlchemy ORM (workflow_runs, step_runs)
2. `src/aiflow/state/repository.py` - CRUD muveletek
3. `alembic/` - setup + 001_initial_core.py migracio
4. `src/aiflow/models/metadata.py` - ModelType, ModelLifecycle, ModelMetadata
5. `src/aiflow/models/protocols/base.py` - BaseModelProtocol, ModelCallResult
6. `src/aiflow/models/protocols/generation.py` - TextGenerationProtocol
7. `src/aiflow/models/protocols/embedding.py` - EmbeddingProtocol
8. `src/aiflow/models/backends/litellm_backend.py` - LiteLLM wrapper
9. `src/aiflow/models/client.py` - ModelClient (generate + embed) + LLMClient alias
10. `src/aiflow/models/registry.py` - ModelRegistry (in-memory, DB-backed kesobb)

**Teszt:** `tests/unit/models/test_client.py`, `tests/integration/test_state_store.py`

### Het 3: Docker + Logging + CI scaffold

**Feladatok:**
1. `docker-compose.yml` - pgvector, redis, kroki + profiles (27_DEVELOPMENT_ENVIRONMENT.md 6. sz.)
2. `Dockerfile` - uv-alapu multi-stage: api, worker, rpa-worker (27_DEVELOPMENT_ENVIRONMENT.md 8. sz.)
3. `aiflow.yaml` - default framework config (23_CONFIGURATION_REFERENCE.md)
4. `.env.example` - titkok template (23_CONFIGURATION_REFERENCE.md 3. szekció)
5. `src/aiflow/observability/logging.py` - structlog JSON
6. `.github/workflows/ci-framework.yml` - uv setup + `uv pip sync uv.lock` (reprodukalhato!)
7. `.vscode/settings.json` + `.vscode/extensions.json` (26_CLAUDE_CODE_SETUP.md 6. sz.)

**Milestone:**
```bash
uv venv && uv pip install -e ".[dev]"     # Kornyezet felall
make dev                                    # Docker szolgaltatasok + DB migracio
pytest tests/unit/ -v                       # Tesztek ZOLDEK
curl http://localhost:8000/health           # API elerheto (ha make dev-docker)
```

---

## Phase 2: Engine + Vector Foundation (Het 4-6)

### Het 4: Step + DAG + Policies

**Feladatok:**
1. `src/aiflow/engine/step.py` - @step decorator + output_types (Haystack minta)
2. `src/aiflow/engine/dag.py` - DAG (add_node, add_edge, topological_sort, validate)
3. `src/aiflow/engine/conditions.py` - Condition kiertekeles elagazasokhoz
4. `src/aiflow/engine/policies.py` - RetryPolicy (LangGraph 1:1), CircuitBreaker, Timeout

**Teszt:** `tests/unit/engine/test_step.py`, `test_dag.py`, `test_policies.py`

### Het 5: Workflow Builder + Runner

**Feladatok:**
1. `src/aiflow/engine/workflow.py` - @workflow + WorkflowBuilder
   - API: step(), branch(), edge(), join(), quality_gate(), subworkflow(), parallel_map(), for_each()
2. `src/aiflow/engine/runner.py` - WorkflowRunner (lokalis sync futtatas)
3. `src/aiflow/engine/checkpoint.py` - version tracking (LangGraph minta)
4. `src/aiflow/engine/serialization.py` - Workflow YAML export/import (Haystack minta)
5. DB migracio: 002_add_catalog.py (skills, workflow_definitions, skill_prompt_versions)

**Teszt:** `tests/unit/engine/test_workflow.py`, `test_runner.py`

### Het 6: Model Protocols + VectorStore

**Feladatok:**
1. `src/aiflow/models/protocols/classification.py` - ClassificationProtocol
2. `src/aiflow/models/protocols/extraction.py` - ExtractionProtocol
3. `src/aiflow/models/router.py` - cost/capability routing + fallback chain
4. `src/aiflow/models/cost.py` - ModelCostCalculator
5. `src/aiflow/vectorstore/base.py` - VectorStore ABC, SearchResult, SearchFilter
6. `src/aiflow/vectorstore/pgvector_store.py` - HNSW + BM25 implementacio
7. `src/aiflow/vectorstore/embedder.py` - Embedding generalas wrapper
8. `src/aiflow/vectorstore/search.py` - HybridSearchEngine (RRF)
9. DB migracio: 003_add_model_registry.py + 004_add_vectorstore.py

**Milestone:** 3-step workflow futtatás kodbol mukodik, pgvector upsert + search mukodik

---

## Phase 3: Prompts + Documents (Het 7-9)

### Het 7: Skill System + Tools

**Feladatok:**
1. `src/aiflow/skill_system/manifest.py` - SkillManifest (progressive disclosure)
2. `src/aiflow/skill_system/loader.py` - Skill felfedeztes es betoltes
3. `src/aiflow/skill_system/registry.py` - Skill registry
4. `src/aiflow/skill_system/instance.py` - Skill Instance (multi-customer)
5. `src/aiflow/tools/` - Shell, Playwright, HumanLoop, Kafka integraciok

> **Megjegyzes:** Az agents/ modul torolve lett. A Step + SkillRunner architektura
> helyettesiti - lasd engine/skill_runner.py.

**Teszt:** `tests/unit/skill_system/test_manifest.py`, `test_loader.py`

### Het 8: Prompt Platform

**Feladatok:**
1. `src/aiflow/prompts/schema.py` - PromptDefinition YAML schema
2. `src/aiflow/prompts/manager.py` - PromptManager (Langfuse SSOT + YAML fallback + cache)
3. `src/aiflow/prompts/sync.py` - YAML -> Langfuse sync pipeline
4. `src/aiflow/prompts/ab_testing.py` - A/B testing traffic splitting

**Teszt:** `tests/unit/prompts/test_manager.py`, `test_sync.py`

### Het 9: Document Management + Ingestion

**Feladatok:**
1. `src/aiflow/documents/registry.py` - DocumentRegistry (lifecycle: draft->active->superseded)
2. `src/aiflow/documents/versioning.py` - Verziokezeles, supersession
3. `src/aiflow/documents/freshness.py` - FreshnessEnforcer
4. `src/aiflow/ingestion/parsers/pdf_parser.py` - PyMuPDF
5. `src/aiflow/ingestion/parsers/docx_parser.py` - python-docx
6. `src/aiflow/ingestion/chunkers/semantic_chunker.py` - Szemantikus chunking
7. `src/aiflow/ingestion/pipeline.py` - IngestionPipeline (AIFlow workflow!)

**Milestone:** Skill system mukodik Langfuse promptokkal, document ingest pipeline mukodik

---

## Phase 4: 5 Skill Portalasa (Het 10-13)

### Het 10: Skill System + Skill 1 (Process Documentation)

**Feladatok:**
1. `src/aiflow/skills/manifest.py`, `base.py`, `loader.py`, `registry.py`
2. `skills/process_documentation/` - POC portalas (06_Diagram_Gen_AI_Agent)
   - 5 agent, 5 prompt YAML, workflow DAG, Pydantic modellek, tools
3. 120+ teszt eset (meglevo POC tesztek + bovites)
4. `src/aiflow/evaluation/framework.py` - EvalSuite, EvalCase
5. `src/aiflow/evaluation/scorers.py` - beepitett scorers
6. `src/aiflow/evaluation/promptfoo.py` - Promptfoo integracio

**Verifikacio:** `aiflow skill install ./skills/process_documentation` -> 9 lepes OK

### Het 11: Skill 2 (ASZF RAG Chat) + Skill 3 (Email Intent)

**Feladatok:**
1. `skills/aszf_rag_chat/` - Allianz RAG portalas
   - Ingestion workflow + Q&A workflow + 6 agent + 150+ teszt
2. `skills/email_intent_processor/` - Uj skill (cfpb_complaint_router beolvasztva)
   - Hibrid ML+LLM klasszifikacio, 10 intent, JSON schema vezerelt, 200 teszt eset

### Het 12: Skill 4 (Cubix RPA)

**Feladatok:**
1. `skills/cubix_course_capture/` - Temporal->AIFlow migracio
   - `src/aiflow/contrib/playwright/browser.py` - PlaywrightBrowser DI
   - `src/aiflow/contrib/shell/executor.py` - ShellExecutor (ffmpeg sandbox)
   - Playwright + ffmpeg + OpenAI STT + GPT workflow-k

### Het 13: Skill 5 (QBPP Test) + Evaluation finalizalas

**Feladatok:**
1. `skills/qbpp_test_automation/` - MultiApp AutoTester portalas
   - Registry-driven, Playwright, BDD -> AIFlow workflow
2. `src/aiflow/evaluation/datasets.py` - Teszt dataset kezeles
3. `src/aiflow/evaluation/reports.py` - Evaluacios riportok
4. Minden skill: 90%+ pass rate ellenorzes

**Milestone:** 5 skill telepitve, 600+ teszt eset ossz., mind 90%+ pass rate

---

## Phase 5: Execution + API + Security + Frontend (Het 14-16)

### Het 14: Queue + Worker

**Feladatok:**
1. `src/aiflow/execution/queue.py` - JobQueue (arq + Redis)
2. `src/aiflow/execution/worker.py` - WorkflowWorker
3. `src/aiflow/execution/dlq.py` - Dead Letter Queue
4. `src/aiflow/execution/rate_limiter.py` - Redis distributed rate limiting
5. `src/aiflow/execution/messaging.py` - MessageBroker ABC
6. Docker compose: worker service hozzaadas

**Teszt:** `tests/integration/test_queue.py`

### Het 15: FastAPI + Security

**Feladatok:**
1. `src/aiflow/api/app.py` - create_app() factory
2. `src/aiflow/api/deps.py` - DI route-okhoz
3. `src/aiflow/api/middleware.py` - CORS, request ID, logging, rate limiting
4. `src/aiflow/api/v1/` - minden endpoint (22_API_SPECIFICATION alapjan)
5. `src/aiflow/security/auth.py` - JWT + API key authentication
6. `src/aiflow/security/rbac.py` - Role-Based Access Control
7. `src/aiflow/security/guardrails.py` - Input/output guardrails
8. DB migracio: 005_add_security.py (teams, users, audit_log)

**Teszt:** `tests/integration/test_api.py`

### Het 16: Frontend (Reflex) scaffold

**Feladatok:**
1. `src/aiflow/ui/` scaffold (Reflex framework)
2. Operator Dashboard (KPI kartyak, job management)
3. Chat Interface skeleton (RAG, streaming)
4. Developer Portal skeleton (DAG viewer, prompt editor)
5. Admin Panel skeleton (users, teams, RBAC)
6. Login + Auth integracio

**Milestone:** Teljes API mukodik auth-tal, async workflow queue-val, alapszintu UI

---

## Phase 6: CLI + Observability (Het 17-19)

### Het 17: CLI

**Feladatok:**
1. `src/aiflow/cli/main.py` - typer fo alkalmazas
2. `src/aiflow/cli/commands/workflow.py` - workflow {new, list, run, test, inspect, replay, docs, export}
3. `src/aiflow/cli/commands/skill.py` - skill {new, install, list, test, validate, upgrade, uninstall}
4. `src/aiflow/cli/commands/prompt.py` - prompt {sync, test, diff, promote, rollback, list}
5. `src/aiflow/cli/commands/eval.py` - eval {run, report}
6. `src/aiflow/cli/commands/dev.py` - dev {up, logs, shell}
7. `src/aiflow/cli/commands/deploy.py` - deploy {staging, prod}
8. `pyproject.toml` script entry point: `aiflow = "aiflow.cli.main:app"`

### Het 18: Observability + Dashboards

**Feladatok:**
1. `src/aiflow/observability/tracing.py` - Langfuse + OTel unified tracer
2. `src/aiflow/observability/cost_tracker.py` - cost tracking + budget enforcement
3. `src/aiflow/observability/sla_monitor.py` - SLA monitoring + alerting
4. `src/aiflow/observability/metrics.py` - Prometheus metriak
5. DB migracio: 006_add_cost_tracking.py (cost_records, cost views)
6. Grafana dashboard template-ek (SQL view-k alapjan)

### Het 19: E2E + GUI Tesztek + Frontend polish

**Feladatok:**
1. `tests/e2e/test_full_pipeline.py` - API -> queue -> worker -> result
2. `tests/ui/` - Playwright GUI tesztek (Page Object Model)
   - test_login.py, test_dashboard.py, test_chat.py, test_admin.py
3. Frontend polish: streaming chat, citacio kartyak, budget progressbar
4. `.github/workflows/ci-skill.yml`, `ci-prompts.yml`, `ci-ui.yml`
5. `src/aiflow/contrib/mcp_server.py` - MCP server (Claude Code integracio)

**Milestone:** Teljes lifecycle: CLI -> API -> Queue -> Worker -> Observability -> UI

---

## Phase 7: Production Hardening (Het 20-22)

### Het 20: Advanced Features

**Feladatok:**
1. `src/aiflow/engine/checkpoint.py` - checkpoint/resume hosszu workflow-khoz (bovitett)
2. `src/aiflow/tools/human_loop.py` - Human-in-the-loop teljes implementacio
3. `src/aiflow/execution/scheduler.py` - cron, event, webhook triggerek
4. DB migracio: 007_add_scheduling.py, 008_add_human_reviews.py

### Het 21: Security hardening + Audit + Messaging

**Feladatok:**
1. `src/aiflow/security/secrets.py` - Vault integracio (prod)
2. `src/aiflow/security/audit.py` - teljes audit trail
3. `src/aiflow/contrib/messaging/kafka.py` - Kafka adapter
4. `src/aiflow/contrib/messaging/rabbitmq.py` - RabbitMQ adapter (opcionalis)
5. `src/aiflow/documents/sync.py` - SharePoint/S3/GDrive sync
6. DB migracio: 009_add_ab_testing.py, 010_add_test_management.py, 011_add_monitoring_views.py
7. OWASP security audit (20_SECURITY_HARDENING alapjan)

### Het 22: Kubernetes + CI/CD + Final polish

**Feladatok:**
1. `k8s/base/` - namespace, configmap, secrets, deployments, services
2. `k8s/overlays/dev/`, `staging/`, `prod/` - kornyezeti overrides
3. Worker HPA (queue depth alapu auto-scaling)
4. `.github/workflows/deploy-staging.yml`, `deploy-prod.yml` - blue-green
5. `src/aiflow/contrib/docs/generator.py` - auto-gen workflow docs
6. `src/aiflow/contrib/docs/compliance.py` - compliance riport generator
7. Compliance riportok: AI Governance, GDPR, SOC2 elokeszites
8. Performance benchmark + load test

**Milestone:** Production-ready: K8s deployment, CI/CD, audit, checkpoint/resume, 5 skill mukodik

---

## Verifikacio Minden Fazis Vegen

```bash
# Phase 1 (Het 3):
docker compose up -d && curl localhost:8000/api/v1/health
pytest tests/unit/ -v

# Phase 2 (Het 6):
# 3-step workflow futtatás Python kodbol -> WorkflowRun(status=completed)
pytest tests/unit/engine/ -v && pytest tests/unit/vectorstore/ -v

# Phase 3 (Het 9):
# Skill system + prompt platform mukodik -> trace megjelenik
pytest tests/unit/skill_system/ -v && pytest tests/unit/prompts/ -v

# Phase 4 (Het 13):
aiflow skill list  # 5 skill megjelenik
aiflow eval run --skill process_documentation  # 90%+
npx promptfoo eval -c skills/*/tests/promptfooconfig.yaml

# Phase 5 (Het 16):
curl localhost:8000/api/v1/workflows  # API mukodik
aiflow workflow run process-documentation --input '{"message": "Szabadsag igenyles"}' --mode async

# Phase 6 (Het 19):
pytest tests/e2e/ -v
pytest tests/ui/ -v
aiflow workflow inspect process-documentation  # CLI mukodik

# Phase 7 (Het 22):
kubectl get pods -n aiflow  # K8s mukodik
aiflow report compliance --period 2026-Q2
```
