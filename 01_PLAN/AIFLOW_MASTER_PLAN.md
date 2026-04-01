# AIFlow Master Plan v2.0 - Integralt Vallalati AI Automatizacios Keretrendszer

**Datum:** 2026-03-28
**Ceg:** BestIx Kft
**Status:** Integralt terv (27 reszterv + 4 fejlesztesi artefaktum = 31 dokumentum)

---

## I. VIZIÓ

Python-nativ vallalati keretrendszer **AI-alapu automatizacios workflow-ok** epitesere,
telepitesere es uzemeltetesere. 10-300+ workflow kezelesehez tervezve, Skill-alapu
modularitassal, teljes DEV-TEST-UAT-PROD eletciklussal.

**Architekturalis inspiracio (valos kodanalzis alapjan):**
- **LangGraph** (27.7k stars): RetryPolicy minta, checkpoint version tracking
- **CrewAI** (47.4k stars): Crews+Flows, memory composite scoring, event bus
- **Haystack** (24.6k stars): @component.output_types, socket-alapu tipusellenorzes, YAML serialize
- **Prefect** (22k stars): Decorator-alapu API, task caching
- **Dagster** (15.2k stars): Asset-first model, lineage tracking

---

## II. ALAPELVEK

| Elv | Forras | Jelentes |
|-----|--------|---------|
| 2-szintu max | Andrew Ng, Anthropic | Orchestrator + Specialist-ek. Tobb = debug lehetetlen |
| Stateless subagent | Iparagi consensus | "When you add state, you add bugs" |
| Evaluation-driven | Anthropic best practice | 100+ teszt eset MINIMUM, kulonben nem production |
| Skill = onallo csomag | CrewAI Skills + sajat | Workflow + agents + prompts + tests egyutt |
| Step = first-class | Haystack Component | Tipusos I/O, fuggetlenul tesztelheto, ujrahasznositphato |
| Prompt SSOT | Meglevo POC (bevalt) | Langfuse SSOT + YAML fallback + label-alapu kornyezetek |
| Explicit > implicit | Haystack pipeline | DAG builder explicit, nem magikus |

---

## III. RENDSZER ARCHITEKTURA

```
                     CLI (aiflow)  /  Claude Code (MCP)
                              |
                    FastAPI Application
                    /    |    |    \
            Auth/RBAC  API v1  Middleware  Event Bus
                    \    |    |    /
            +--------+---+----+---+--------+
            |       Workflow Engine          |
            |  DAG + Steps + Runner         |
            |  (checkpoint, retry, circuit) |
            +------+-----------+-----------+
                   |           |
        +----------+    +------+------+
        |  Skill   |    |   Skill     |
        |  System  |    |  Registry   |
        | (steps,  |    |  (install,  |
        |  tools)  |    |  upgrade)   |
        +----+-----+    +------+------+
             |                 |
        +----+-----+    +-----+------+
        |  Prompt  |    | Evaluation |
        | Platform |    | Framework  |
        | Langfuse |    | Promptfoo  |
        +----+-----+    +------+-----+
             |                 |
    +--------+-----------------+--------+
    |       Observability Platform       |
    |  Langfuse (LLM) + OTel (infra)   |
    |  Cost + SLA + Audit               |
    +----+-----------+-----------+------+
         |           |           |
    +----+-----+ +---+------+ +-+----------+
    |  State   | | Execution | | Messaging  |
    |  Store   | |  Queue    | | (Kafka etc)|
    | Postgres | | Redis+arq | | Adapter    |
    +----------+ +----------+ +------------+
```

---

## IV. CORE ABSTRACTIONS

### 4.1 Step (Atomi Epitoelem)

```python
@step(
    name="classify_intent",
    output_types={"category": str, "confidence": float},  # <- Haystack minta!
    retry=RetryPolicy(max_retries=2, backoff_base=1.0, jitter=True),  # <- LangGraph minta!
    timeout=30,
)
async def classify_intent(
    input_data: ClassifyInput,       # Pydantic BaseModel
    ctx: ExecutionContext,            # DI: trace, budget, label
    llm: LLMClient,                  # DI: LiteLLM + instructor
    prompts: PromptManager,          # DI: Langfuse SSOT
) -> ClassifyOutput:                 # Pydantic BaseModel
    prompt = await prompts.get("process-doc/classifier", label=ctx.prompt_label)
    return await llm.generate(
        messages=prompt.compile(message=input_data.message),
        response_model=ClassifyOutput,
    )
```

### 4.2 Workflow (DAG Builder)

```python
@workflow(name="process-documentation", version="2.0.0", skill="process_documentation")
def process_doc(wf: WorkflowBuilder):
    wf.step(classify_intent)
    wf.branch(on="classify_intent", when={
        "output.category == 'process'": ["elaborate"],
        "output.category == 'greeting'": ["respond_greeting"],
    }, otherwise="reject")

    wf.step(elaborate, depends_on=["classify_intent"])
    wf.step(extract, depends_on=["elaborate"])
    wf.step(review, depends_on=["extract"])

    wf.quality_gate(after="review", gate=QualityGate(
        metric="completeness", threshold=0.80,
        on_fail="refine", max_iterations=3, on_exhausted="human_review",
    ))
    wf.step(refine, depends_on=["review"])
    wf.edge("refine", "review")

    wf.step(generate_diagram, depends_on=["review"])
    wf.step(generate_table, depends_on=["review"])
    wf.join(["generate_diagram", "generate_table"], into="assemble_output")
    wf.step(assemble_output)
```

### 4.3 Specialist Agent (Stateless)

```python
class ExtractorAgent(SpecialistAgent[ExtractInput, ProcessExtraction]):
    @property
    def spec(self) -> AgentSpec:
        return AgentSpec(name="extractor", model="openai/gpt-4o",
                         input_type=ExtractInput, output_type=ProcessExtraction)

    async def execute(self, request: AgentRequest[ExtractInput],
                      ctx: ExecutionContext) -> AgentResponse[ProcessExtraction]:
        # Stateless! Minden szukseges adat a request-ben es ctx-ben van.
        prompt = await self.prompts.get("process-doc/extractor", label=ctx.prompt_label)
        result = await self.llm.generate(messages=prompt.compile(...), response_model=ProcessExtraction)
        return AgentResponse(status="success", output=result,
                             scores={"completeness": self._score(result)})
```

### 4.4 Skill (Onallo Csomag)

```yaml
# skills/process_documentation/skill.yaml
name: process_documentation
version: "2.0.0"
framework_requires: ">=1.0.0,<2.0.0"
display_name: "Process Documentation & Diagramming"
author: "BestIxCom Kft"
estimated_cost_per_run: 0.06
workflows: [process-documentation]
agent_types: [ClassifierAgent, ElaboratorAgent, ExtractorAgent, ReviewerAgent, DiagramAgent]
prompts: [process-doc/classifier, process-doc/elaborator, process-doc/extractor,
          process-doc/reviewer, process-doc/mermaid_flowchart]
required_models: ["openai/gpt-4o", "openai/gpt-4o-mini"]
tags: [bpmn, documentation, diagrams]
```

### 4.5 ExecutionContext (Minden Komponensen Atfoly)

```python
class ExecutionContext(BaseModel):
    run_id: str
    trace_context: TraceContext       # Langfuse + OTel
    team_id: str | None = None
    user_id: str | None = None
    prompt_label: str = "prod"        # DEV/TEST/UAT/PROD
    model_override: str | None = None
    budget_remaining_usd: float = 10.0
    checkpoint_data: dict | None = None  # Resume-hoz (LangGraph minta)
    checkpoint_version: int = 0          # Version tracking (LangGraph minta)
```

### 4.6 Skill Instance Architektura

#### Skill = Template, Instance = Futo Peldany

Egy skill NEM szingularis deployment. Egy skill SABLON (template), amibol
tobb PELDANY (instance) futhat kulonbozo konfiguracioval:

**AZHU (Allianz Hungaria):**
  - `aszf_rag_chat` instance **"HR Chat"** (hr_docs, HR promptok)
  - `aszf_rag_chat` instance **"Jogi Chat"** (legal_docs, jogi promptok)
  - `email_intent` instance **"Ugyfelszolgalat"** (5 intent)
  - `email_intent` instance **"Belso Ticketek"** (8 intent)
  - `qbpp_test_automation` instance **"Portal E2E"** (portal.allianz.hu)

**NPRA:**
  - `aszf_rag_chat` instance **"Policy Chat"** (policies, angol promptok)
  - `cubix_course_capture` instance **"Python Course"** (online platform)
  - `cubix_course_capture` instance **"ML Course"** (online platform)
  - `process_documentation` instance **"Process Docs"** (belso folyamatok)

**BESTIX (BestIxCom Kft - belso hasznalat, teszteles, demo):**
  - `process_documentation` instance **"Belso Folyamatok"** (framework validacio)
  - `aszf_rag_chat` instance **"Belso Docs Chat"** (belso dokumentumok)
  - `cubix_course_capture` instance **"Cubix Kurzus"** (Cubix AI/ML kurzusok)
  - `email_intent_processor` instance **"Support Email"** (support@bestix.hu, ML klasszifikacio integralt)
  - Minden skill sajat hasznalatra - teszteles, demo, belso automatizacio

Minden instance sajat: collection, prompt namespace, budget, SLA, adatforrasok.
Reszletek: [28_MODULAR_DEPLOYMENT.md](28_MODULAR_DEPLOYMENT.md)

---

## V. SKILL LIFECYCLE (Teljes Eletciklus)

```
1. SCAFFOLD    aiflow skill new <name> --template medium
2. DEVELOP     Kod (agents, prompts, models, tools)
3. VALIDATE    aiflow skill validate <name>
4. TEST        aiflow eval run --skill <name>         # 100+ teszt
5. INSTALL     aiflow skill install <path>             # 9 lepes (manifest -> workflow reg -> prompt sync -> test)
6. PROMOTE     aiflow prompt promote --from dev --to staging
7. UAT         Stakeholder validacio staging kornyezetben
8. RELEASE     aiflow prompt promote --from staging --to prod
               git tag v2.0.0 -> CI/CD deploy
9. MONITOR     Langfuse + Grafana + SLA alertek
10. ITERATE    Prompt javitas -> Promptfoo regresszio -> promocioas ut ujra
```

**Skill Install 9 Lepese:**
1. Manifest validacio (framework_requires check)
2. Fuggoseg ellenorzes (modellek, Python csomagok, mas skill-ek)
3. Schema validacio (DAG, agent spec-ek, tipusellenorzes)
4. Workflow regisztracio (PostgreSQL workflow_definitions)
5. Agent regisztracio (DI container)
6. Prompt sync (Langfuse-ba, namespace-elve)
7. Teszt futtatas (opcionalis)
8. Skill rekord mentes (skills tabla + audit_log)
9. Visszajelzes

---

## VI. KORNYEZETI IZOLACIO (DEV-TEST-UAT-PROD)

| Eroforras | DEV | TEST | UAT | PROD |
|-----------|-----|------|-----|------|
| PostgreSQL | aiflow_dev (local) | aiflow_test (CI) | aiflow_uat (staging) | aiflow_prod (managed) |
| Redis prefix | aiflow:dev: | aiflow:test: | aiflow:uat: | aiflow:prod: |
| Langfuse label | dev | test | staging | prod |
| Config | .env | CI secrets | Docker Compose .env + Vault | Docker Compose .env + Vault (K8s kesobb) |

**Prompt-ok fuggetlen eletciklusa** (nem kell deploy!):
```
aiflow prompt sync --label dev          # Fejlesztes
aiflow prompt test --label test         # CI/Promptfoo
aiflow prompt promote --to staging      # UAT
aiflow prompt promote --to prod         # Production (masodpercek!)
aiflow prompt rollback --to-version 4   # Azonnal, ha baj van
```

---

## VII. HIBAKEZELÉS

### Strukturalt Error Hierarchia
```
AIFlowError
  +-- TransientError (ujraprobalohato)
  |     +-- LLMTimeoutError
  |     +-- LLMRateLimitError
  |     +-- ExternalServiceError
  +-- PermanentError (emberi beavatkozas)
        +-- BudgetExceededError
        +-- QualityGateFailedError
        +-- InvalidInputError
        +-- AuthorizationError
```

### Resilience (LangGraph RetryPolicy minta)
```python
RetryPolicy(max_retries=3, backoff_base=1.0, backoff_max=60.0, jitter=True)
CircuitBreakerPolicy(failure_threshold=5, recovery_timeout=60)  # Redis-ben tarolt allapot
```

### Debugging
- **Langfuse trace deep-link**: `workflow_runs.trace_url`
- **Step replay**: `aiflow workflow replay --run-id X --from-step extract`
- **DLQ**: Auto-klasszifikacio -> kesleltett retry (transient) VAGY alert (permanent)
- **Alerting**: P1 (success rate <90%, 15min) -> P4 (egyedi hiba, next business day)

---

## VIII. MIDDLEWARE INTEGRACIO

### MessageBroker Adapter Pattern
```python
class MessageBroker(ABC):
    async def publish(self, topic: str, message: bytes, key: str | None = None) -> None: ...
    async def subscribe(self, topic: str, group_id: str) -> AsyncIterator[Message]: ...
```

| Adapter | Csomag | Telepites |
|---------|--------|-----------|
| Redis Streams | beepitett | `pip install aiflow` (default) |
| Kafka | aiokafka | `pip install aiflow[kafka]` |
| RabbitMQ | aio-pika | `pip install aiflow[rabbitmq]` |
| Azure Service Bus | azure-servicebus | `pip install aiflow[azure]` |
| AWS SQS | aiobotocore | `pip install aiflow[aws]` |

**Event trigger pelda (Kafka):**
```python
EventTrigger(source="kafka", topic="emails.incoming",
             group_id="aiflow-email-consumer",
             filter_expression="type == 'invoice'",
             workflow_name="invoice-processing")
```

---

## IX. OBSERVABILITY + AUDIT

### Tracing
```
Workflow Run (Langfuse Trace)
  +-- Step (Langfuse Span) -> LLM Call (Generation) -> Score
  +-- Cost: per-step, per-workflow, per-team, per-model
  +-- SLA: p50/p95/p99 latency, success rate
```

### Audit Trail (audit_log tabla)
Minden: workflow.run, skill.install, prompt.sync, user.role_change, budget.change

### Auto-Generalt Dokumentacio
```bash
aiflow workflow docs --name process-documentation --format full
# -> Mermaid DAG diagram + uzleti leiras + data flow + koltseg becsles
```

### Compliance Riportok
- **SOC2**: Access control, change management, incident management
- **GDPR**: `aiflow admin redact --run-id X` (PII torles audit trail-lel)

### Executive Dashboard (Grafana + SQL Views)
- v_workflow_metrics: futtatasok, success rate, koltseg, SLA
- v_team_budget: havi budget hasznalat per team
- v_model_usage: token/koltseg per model per nap

---

## X. VERZIKEZELES

### Fuggetlen Verziozas
| Entitas | Pelda | Valtozas tipusa |
|---------|-------|----------------|
| Framework | aiflow v1.2.0 | Havi release train |
| Skill | process_doc v2.1.0 | Continuous deploy |
| Prompt | classifier v6 (Langfuse) | Azonnali (label promo) |

### CI/CD Pipeline-ok (3 kulon, path-alapu trigger)
1. **Framework** (`src/aiflow/**`): lint + unit + integration + **MINDEN skill compat teszt**
2. **Skill** (`skills/<name>/**`): lint + skill tests + promptfoo + framework smoke
3. **Prompt** (`skills/*/prompts/**`): promptfoo eval + langfuse sync

### Git Branching
```
main (mindig deployolhato, CODEOWNERS vedett)
  +-- feature/AIFLOW-123  (framework)
  +-- skill/process-doc/X  (skill)
  +-- hotfix/Y              (bypass release train)
```

---

## XI. IMPLEMENTACIOS FAZISOK (Optimalizalt)

| Fazis | Het | Fo celkituzes | Kimenet | GitHub Mintak |
|-------|-----|---------------|---------|---------------|
| **1. Foundation** | 1-3 | Core, State, LLM, Docker, structlog | Dev kornyezet | - |
| **2. Engine** | 4-6 | Step (@output_types), DAG, Workflow Builder, Runner | Lokalis workflow | Haystack component, LangGraph retry |
| **3. Agents + Prompts** | 7-9 | Specialist, Orchestrator, QualityGate, Langfuse SSOT, Event Bus | Agentic workflow | CrewAI events |
| **4. Skills (5 db)** | 10-13 | POC portalas, 5 skill, 600+ teszt | Mukodo skill-ek | - |
| **5. Execution + API + Security** | 14-16 | Queue, Worker, FastAPI, RBAC, Frontend scaffold | Teljes API + UI | - |
| **6. CLI + Observability** | 17-19 | aiflow CLI, Langfuse+OTel tracing, Cost, SLA, Dashboards | Teljes lifecycle | - |
| **7. Production** | 20-22 | Checkpoint (LangGraph minta), HITL, Scheduler, Kafka adapter, Docker Compose prod, CI/CD, Audit | Production-ready | LangGraph checkpoint |

**Reszletes het-per-het bontas: lasd 04_IMPLEMENTATION_PHASES.md (a Phase 2 es 7 bovitve a GitHub tanulsagokkal)**

---

## XII. VALOS SKILL PELDAK

### Skill 1: Process Documentation (Medium, 3 het, $0.06/run)
POC adaptalas. 5 agent, 7 step DAG, quality gate + refine loop.
120 teszt eset. Prompt iteracios ciklus: 3 kor -> 96% pass rate.

### Skill 2: ASZF RAG Chat (Large, 5-6 het, $0.15/run)
35 dokumentum, 12k chunk, pgvector, multi-turn (CrewAI memory minta).
6 agent (max!). RAG-specifikus metriak: faithfulness, recall@5, citation accuracy.
150 teszt eset. "Nem tudom" felismeres kulonos figyelemmel.

### Skill 3: Email Intent Feldolgozo (Small-Medium, 2-3 het, $0.03/run)
Hibrid ML+LLM klasszifikacio (cfpb_complaint_router beolvasztva), 10 intent kategoria,
JSON schema vezerelt konfiguracio, csatolmany feldolgozas (Docling + Azure DI).
200 email teszt. Napi ~200 email, havi $180, ~80 ora/ho megtakaritas.

### Skill 4: Cubix Course Capture (Hybrid RPA, 4 het, ~$3/run)
Temporal->AIFlow migracio. Playwright web navigacio + operator lepesek + OpenAI STT + GPT strukturalas.
Reszletek: 19_RPA_AUTOMATION.md

### Skill 5: QBPP Test Automation (RPA, 2 het, ~$0.05/run)
Biztositasi kalkulátor teszteles. Registry-driven Playwright automatizacio.
BDD -> AIFlow workflow adaptalas. Strategy-based teszt generálas.

**Parhuzamos fejlesztes:** Mind az 5 skill fuggetlen.
**Osszes havi koltseg (Skill 1-5):** ~$1,230, ~500 futtatas/nap.

> **Megjegyzes:** A korabban tervezett `cfpb_complaint_router` skill beolvadt az `email_intent_processor`-ba
> mint hibrid ML+LLM klasszifikacios reteg (sklearn TF-IDF + LLM fallback).

---

## XIII. TECH STACK (Vegleges)

### Core
| Csomag | Verzio | Szerep |
|--------|--------|--------|
| Python | 3.12+ | Runtime |
| FastAPI | >= 0.110 | API |
| pydantic | >= 2.5 | Validacio |
| litellm | >= 1.40 | Multi-LLM |
| instructor | >= 1.4 | Structured output |
| langfuse | >= 2.40 | LLM observability + prompt SSOT |
| arq | >= 0.26 | Async Redis queue |
| asyncpg | >= 0.29 | PostgreSQL |
| structlog | >= 24.1 | JSON logging |
| typer | >= 0.12 | CLI |
| alembic | >= 1.13 | DB migraciok |

### Opcionalis
| Csomag | Telepites | Szerep |
|--------|-----------|--------|
| aiokafka | `aiflow[kafka]` | Kafka adapter |
| hvac | `aiflow[vault]` | Vault secrets |
| opentelemetry-sdk | `aiflow[otel]` | Infra tracing |
| pgvector | `aiflow[vectorstore]` | Vector DB (RAG) |
| tiktoken, pymupdf | `aiflow[vectorstore]` | Token szamlalas, PDF parser |
| playwright | `aiflow[rpa]` | Web automatizacio + GUI teszt |
| reflex | `aiflow[ui]` | Frontend UI |

### Infrastruktura
| Service | Dev (Docker) | Prod (Docker Compose, K8s kesobb) |
|---------|-------------|------------|
| PostgreSQL 16 + pgvector | pgvector/pgvector:pg16 | Managed DB + vectors |
| Redis 7 | redis:7-alpine | Redis cluster |
| AIFlow API | uvicorn --reload | 2-4 replica HPA |
| AIFlow Worker | arq worker | 2-20 replica HPA (queue depth) |
| Kroki | yuzutech/kroki | 1 replica |

---

## XIV. KONYVTAR STRUKTURA (Vegleges, bovitve GitHub tanulsagokkal)

```
aiflow/
|-- pyproject.toml
|-- alembic.ini
|-- aiflow.yaml
|-- docker-compose.yml / docker-compose.prod.yml
|-- Dockerfile / Makefile
|
|-- src/aiflow/
|   |-- __init__.py                 # Public API (stabil szerzodes)
|   |-- _version.py
|   |-- core/
|   |   |-- config.py               # AIFlowSettings
|   |   |-- context.py              # ExecutionContext (+ checkpoint_version)
|   |   |-- errors.py               # TransientError / PermanentError hierarchia
|   |   |-- events.py               # Event Bus (CrewAI minta)         <- UJ
|   |   |-- registry.py / types.py / di.py
|   |
|   |-- engine/
|   |   |-- step.py                 # @step + output_types (Haystack minta)  <- BOVITVE
|   |   |-- workflow.py             # @workflow + WorkflowBuilder
|   |   |-- dag.py                  # DAG (topological + priority queue optionalis)
|   |   |-- runner.py               # WorkflowRunner (sync + async)
|   |   |-- checkpoint.py           # Checkpoint + version tracking (LangGraph)  <- BOVITVE
|   |   |-- policies.py             # RetryPolicy (LangGraph 1:1), CircuitBreaker, Timeout
|   |   |-- conditions.py
|   |   |-- serialization.py        # Workflow YAML export/import (Haystack minta)  <- UJ
|   |
|   |-- skill_system/                     # Skill manifest, loader, registry, instance
|   |   |-- manifest.py / loader.py / registry.py / instance.py
|   |
|   |-- tools/                            # Shell, Playwright, RobotFramework, HumanLoop, Kafka
|   |
|   |-- skills/                           # Backward compat re-exports -> skill_system/
|   |   |-- base.py / manifest.py / loader.py / registry.py
|   |
|   |-- prompts/
|   |   |-- manager.py / sync.py / ab_testing.py / schema.py
|   |
|   |-- execution/
|   |   |-- queue.py / worker.py / scheduler.py / dlq.py / rate_limiter.py
|   |   |-- messaging.py            # MessageBroker abstract              <- UJ
|   |
|   |-- state/
|   |   |-- models.py / repository.py / migrations/
|   |
|   |-- observability/
|   |   |-- tracing.py / cost_tracker.py / sla_monitor.py / logging.py / metrics.py
|   |
|   |-- evaluation/
|   |   |-- framework.py / scorers.py / promptfoo.py / datasets.py
|   |
|   |-- security/
|   |   |-- auth.py / rbac.py / audit.py / secrets.py / guardrails.py
|   |
|   |-- api/v1/
|   |   |-- workflows.py / jobs.py / skills.py / prompts.py
|   |   |-- evaluations.py / schedules.py / admin.py / health.py
|   |
|   |-- models/                     # LECSERELI llm/-t (15_ML_MODEL_INTEGRATION)
|   |   |-- client.py               # ModelClient: generate, embed, classify, extract, vision
|   |   |-- registry.py             # DB-backed model registry + lifecycle
|   |   |-- router.py               # Cost/capability/latency routing + fallback
|   |   |-- protocols/              # Tipusos protokollok (generation, embedding, classification, etc.)
|   |   |-- backends/               # LiteLLM, local, server (Triton/vLLM), sidecar
|   |
|   |-- vectorstore/                # pgvector + hybrid search (16_RAG_VECTORSTORE)
|   |   |-- pgvector_store.py       # HNSW + BM25 + RRF
|   |   |-- embedder.py / search.py
|   |
|   |-- documents/                  # Dokumentum eletciklus (16_RAG_VECTORSTORE)
|   |   |-- registry.py / versioning.py / freshness.py / sync.py
|   |
|   |-- ingestion/                  # Dokumentum feldolgozas (16_RAG_VECTORSTORE)
|   |   |-- parsers/ (pdf, docx, xlsx) / chunkers/ (semantic, fixed, hierarchical)
|   |
|   |-- ui/                         # Frontend (14_FRONTEND)
|   |   |-- pages/ (operator, chat, developer, admin, reports)
|   |
|   |-- cli/commands/
|   |   |-- workflow.py / skill.py / prompt.py / eval.py / dev.py / deploy.py
|   |
|   |-- contrib/
|       |-- messaging/kafka.py, rabbitmq.py, azure_sb.py, aws_sqs.py
|       |-- playwright/browser.py, page_actions.py      # RPA (19_RPA_AUTOMATION)
|       |-- shell/executor.py, sandbox.py               # RPA ffmpeg/pandoc
|       |-- n8n/ / chainlit/ / kroki/ / miro/
|       |-- docs/generator.py, compliance.py
|       |-- mcp_server.py
|
|-- skills/
|   |-- process_documentation/       # Skill 1: AI (POC portalas)
|   |-- aszf_rag_chat/               # Skill 2: AI+RAG
|   |-- email_intent_processor/      # Skill 3: AI+Kafka (cfpb_complaint_router beolvasztva)
|   |-- cubix_course_capture/        # Skill 4: Hybrid RPA (19_RPA_AUTOMATION)
|   |-- qbpp_test_automation/        # Skill 5: RPA
|
|-- templates/ (small_linear, medium_branching, large_orchestrated, web_scraper, hybrid_automation)
|-- tests/ (unit, integration, e2e, ui/)
|-- k8s/ (base, overlays: dev/staging/prod)
|-- .github/workflows/ (ci-framework.yml, ci-skill.yml, ci-prompts.yml, ci-ui.yml, deploy-*)
```

---

## XV. DATABASE SCHEMA (Fo Tablak)

| Tabla | Rekordok | Fo haszanlat |
|-------|----------|-------------|
| workflow_runs | ~450/nap | Minden workflow futtatas |
| step_runs | ~2500/nap | Lepes szintu tracking + checkpoint |
| cost_records | ~5000/nap | Per-LLM/model hivas koltseg |
| model_registry | ~20-50 | LLM, embedding, classification, vision modellek |
| skills | ~10-50 | Telepitett skill-ek |
| workflow_definitions | ~20-100 | DAG definiciok |
| teams | ~5-20 | Csapatok + budget |
| users | ~20-100 | Felhasznalok + RBAC |
| audit_log | ~1000/nap | Teljes audit trail |
| schedules | ~10-50 | Cron/event/webhook triggerek |
| human_reviews | ~10-50/nap | HITL dontes rekordok |
| ab_experiments | ~2-5 aktiv | Prompt A/B tesztek |
| skill_prompt_versions | ~50-200 | Skill-Langfuse prompt mapping |
| documents | ~100-1000 | RAG forras dokumentumok |
| chunks | ~10,000-100,000 | Vector embedding chunks (pgvector) |
| collections | ~5-20 | Logikai chunk csoportok per skill |
| test_datasets | ~20-50 | Teszt adat csoportok |
| test_cases | ~5,000-50,000 | Centralizalt teszt esetek |
| test_results | ~napi 10,000+ | Teszt eredmenyek tortenete |

**SQL Views:** v_workflow_metrics, v_team_budget, v_model_usage, v_daily_team_costs, v_collection_health, v_document_freshness, v_test_trends

---

## XVI. KOCKAZATOK ES MITIGACIOK

| Kockazat | Valoszinuseg | Hatas | Mitigacio |
|----------|-------------|-------|-----------|
| LLM provider kiesés | Kozepes | Magas | LiteLLM fallback model + circuit breaker |
| Koltseg tulfutas | Magas | Kozepes | Per-run budget, per-team havi limit, 80% alert |
| Prompt regresszio | Magas | Magas | Promptfoo CI gate, A/B testing, rollback <10mp |
| Hallucinacio (RAG) | Magas | Magas | Quality gate + "nem tudom" detektalas + HITL |
| Skill fuggoseg torik | Alacsony | Magas | Framework compat test CI, framework_requires |
| Adat biztonsag | Alacsony | Kritikus | RBAC, audit, Vault secrets, GDPR redaction |

---

## XVII. SIKER KRITERIUMOK

| Metrika | Cel (6 ho) | Cel (12 ho) |
|---------|-----------|-------------|
| Aktiv skill-ek szama | 3-5 | 10-20 |
| Napi workflow futatasok | 500+ | 2000+ |
| Atlagos success rate | >95% | >98% |
| SLA compliance (p95) | >95% | >99% |
| Atlagos koltseg/futtatas | <$0.10 | <$0.08 |
| Havi osszes koltseg | <$2,000 | <$5,000 |
| Prompt regresszio | 0 prod incident | 0 prod incident |
| Mean time to new skill | 3-6 het | 1-3 het |

---

## XVIII. KOVETKEZO LEPES

**Azonnali (Jelen heten):**
1. `aiflow` repo letrehozasa (monorepo)
2. `pyproject.toml` + `src/aiflow/core/` scaffold
3. PostgreSQL + Redis Docker Compose
4. Elso unit teszt: `test_config.py`

**Fazis 1 vegen (Het 3):**
- Docker `aiflow-api` elindul
- DB migracio fut
- LLM hivas mukodik (LiteLLM + instructor)
- structlog JSON logging aktiv
- `pytest tests/unit/` zold

**A reszletes het-per-het feladatlista: [04_IMPLEMENTATION_PHASES.md](04_IMPLEMENTATION_PHASES.md)**

**Teljes terv (31 dokumentum):**
- Core: 01-05 (Architecture, Directory, DB Schema, Phases, Tech Stack)
- Operations: 06-08 (Claude Code, Version/Lifecycle, Error/Debug)
- Enterprise: 09-10 (Middleware, Audit/Compliance)
- Examples: 11-13 (Skills Walkthrough, Skill Integration, GitHub Research)
- Technical: 14-16 (Frontend, ML Models, RAG/VectorStore)
- Dev Rules: 17-19 (Git Rules, Testing/Playwright, RPA Automation)
- Deployment: 28 (Modular Deployment, Skill Instance architecture, multi-customer)
- Optimization: 29 (Framework + Skill rationalization), 30 (RAG Production Plan)
- UI/Design: 31-41 (Invoice Processor, Admin Dashboard, Figma Redesign)
- **Service Generalization: 42 (Altalanos szolgaltatasok atalakitasi terv — Email, Document, RAG, RPA, Media, Diagram)**
- Artifacts: CLAUDE.md, SKILL_DEVELOPMENT.md, AIFLOW_MASTER_PLAN.md, 00_EXECUTIVE_SUMMARY.md
