# AIFlow - Reszletes Architektura

## 1. Rendszer Attekintes

```
                          CLI (aiflow)
                              |
                    FastAPI Application
                    /    |    |    \
            Auth/RBAC  API v1  Middleware
                    \    |    |    /
            +--------+---+----+---+--------+
            |       Workflow Engine          |
            |  (DAG, Steps, Runner)         |
            +------+-----------+-----------+
                   |           |
        +----------+    +------+------+
        |  Agent   |    |   Skill     |
        |  System  |    |  Registry   |
        +----+-----+    +------+------+
             |                 |
        +----+-----+    +-----+------+
        |  Prompt  |    | Evaluation |
        | Platform |    | Framework  |
        +----+-----+    +------+-----+
             |                 |
        +----+-----------------+-----+
        |    Observability Platform   |
        |  (Langfuse + OpenTelemetry) |
        +----+-----------+-----------+
             |           |
        +----+-----+ +---+------+
        |  State   | | Execution |
        |  Store   | |  Queue    |
        | (Postgres)| | (Redis)   |
        +----------+ +----------+
```

---

## 2. Core Framework (Kernel)

### 2.1 ExecutionContext - A rendszer kozponti idegrendszere

Minden komponensen atfoly, request-scoped:

```python
class ExecutionContext(BaseModel):
    """Request-scoped context that flows through every component."""
    run_id: str                          # Unique workflow run ID
    trace_context: TraceContext           # Langfuse + OTel trace
    team_id: str | None = None           # Team scoping
    user_id: str | None = None           # User identity
    prompt_label: str = "prod"           # Langfuse prompt label
    model_override: str | None = None    # Override default model
    budget_remaining_usd: float = 10.0   # Cost budget for this run
    metadata: dict[str, Any] = {}        # Custom metadata

    # Runtime state (set by engine)
    checkpoint_data: dict | None = None  # For resume from checkpoint
    dry_run: bool = False                # Validate without executing
```

### 2.2 Dependency Injection Container

```python
class Container:
    """Lightweight DI container for framework services."""
    settings: AIFlowSettings
    state_store: StateStore
    job_queue: JobQueue
    prompt_manager: PromptManager
    tracer: Tracer
    cost_tracker: CostTracker
    rbac: RBACManager
    audit: AuditLogger
    llm_client: LLMClient
    skill_registry: SkillRegistry
```

### 2.3 Exception Hierarchy

```python
class AIFlowError(Exception): ...
class WorkflowNotFoundError(AIFlowError): ...
class StepExecutionError(AIFlowError): ...
class BudgetExceededError(AIFlowError): ...
class QualityGateFailedError(AIFlowError): ...
class CircuitBreakerOpenError(AIFlowError): ...
class AuthorizationError(AIFlowError): ...
class HumanReviewRequiredError(AIFlowError): ...
```

---

## 3. Workflow Engine

### 3.1 Step - Az atomi epitoelem

```python
@step(
    name="classify_intent",
    input_type=ClassifyInput,
    output_type=ClassifyOutput,
    retry=RetryPolicy(max_retries=2),
    timeout=30,
)
async def classify_intent(
    input_data: ClassifyInput,
    ctx: ExecutionContext,
    llm: LLMClient,
    prompts: PromptManager,
) -> ClassifyOutput:
    prompt = await prompts.get("process-doc/classifier", label=ctx.prompt_label)
    response = await llm.generate(
        model=ctx.model_override or "openai/gpt-4o-mini",
        messages=prompt.compile(message=input_data.message),
        response_model=ClassifyOutput,
    )
    return response
```

**Jellemzok:**
- Tipusos input/output (Pydantic BaseModel)
- Automatikus retry exponential backoff-fal
- Timeout kikenyszerites
- DI: llm, prompts, ctx automatikusan injektalva
- Onalloan tesztelheto

### 3.2 Workflow - DAG epitovel

```python
@workflow(
    name="process-documentation",
    version="2.0.0",
    skill="process_documentation",
    complexity="medium",
)
def process_doc_workflow(wf: WorkflowBuilder):
    # Linearis resz
    wf.step(classify_intent)

    # Elagazas a klasszifikacio alapjan
    wf.branch(
        on="classify_intent",
        when={
            "output.category == 'process'": ["elaborate"],
            "output.category == 'greeting'": ["respond_greeting"],
        },
        otherwise="reject",
    )

    # Process ag
    wf.step(elaborate, depends_on=["classify_intent"])
    wf.step(extract, depends_on=["elaborate"])
    wf.step(review, depends_on=["extract"])

    # Quality gate: review score >= 8 -> generate, kulonben refine
    wf.branch(
        on="review",
        when={"output.score >= 8": ["generate"]},
        otherwise="refine",
    )

    # Refine loop (max 3 iteracio)
    wf.step(refine, depends_on=["review"], max_iterations=3)
    wf.edge("refine", "review")  # Visszahurkolodik

    # Parhuzamos kimenet-generalas
    wf.step(generate_diagram, depends_on=["review"])
    wf.step(generate_table, depends_on=["review"])
    wf.join(["generate_diagram", "generate_table"], into="assemble_output")

    wf.step(assemble_output)

    # Terminal lepesek
    wf.step(respond_greeting, terminal=True)
    wf.step(reject, terminal=True)
```

### 3.3 DAG Engine

```python
class DAG:
    """Directed Acyclic Graph with cycle detection (loops allowed via max_iterations)."""

    def add_node(self, step_name: str, step_def: StepDefinition) -> None: ...
    def add_edge(self, from_step: str, to_step: str, condition: Condition | None = None) -> None: ...
    def topological_sort(self) -> list[str]: ...
    def get_ready_steps(self, completed: set[str]) -> list[str]: ...
    def validate(self) -> list[str]:  # Returns validation errors
```

### 3.4 Workflow Runner

```python
class WorkflowRunner:
    """Executes workflow DAG, managing state, checkpoints, and observability."""

    async def run(self, workflow: Workflow, input_data: dict,
                  *, context: ExecutionContext) -> WorkflowRun:
        """
        Execution loop:
        1. Persist workflow_run (status=running)
        2. Get topologically sorted step order
        3. For each ready step:
           a. Check circuit breaker
           b. Check budget
           c. Execute with retry policy
           d. Persist step_run
           e. Save checkpoint
           f. Update cost tracker
           g. Evaluate conditions for next steps
        4. On success: persist final output
        5. On failure: persist error, move to DLQ if exhausted
        """
        ...

    async def resume(self, run_id: str) -> WorkflowRun:
        """Resume from last successful checkpoint."""
        ...
```

### 3.5 Resilience Policies

```python
class RetryPolicy(BaseModel):
    max_retries: int = 3
    backoff_base: float = 1.0
    backoff_max: float = 60.0
    backoff_jitter: bool = True
    retry_on: list[str] = ["TimeoutError", "ConnectionError", "RateLimitError"]

class CircuitBreakerPolicy(BaseModel):
    failure_threshold: int = 5       # Failures before opening
    recovery_timeout: int = 60       # Seconds before half-open
    half_open_max_calls: int = 3     # Calls in half-open state

class TimeoutPolicy(BaseModel):
    timeout_seconds: int = 60
    on_timeout: Literal["fail", "skip", "fallback"] = "fail"
    fallback_step: str | None = None  # Step to run on timeout
```

---

## 4. Agent System (2-Level)

### 4.1 Architekturalis Elv

```
Orchestrator (Level 1) - egyetlen, allapotot tart
    |
    +-- Specialist A (Level 2) - stateless, pure function
    +-- Specialist B (Level 2) - stateless, pure function
    +-- Specialist C (Level 2) - stateless, pure function
    ... max 6 specialist tipus!
```

**Miert max 2 szint, max 6 specialist?**
- Andrew Ng, Anthropic, Microsoft consensus: tobb = tulkomplex, debug lehetetlen
- "When you add state, you add bugs" - stateless subagent = megbizhato

### 4.2 Specialist Agent

```python
class SpecialistAgent(ABC, Generic[TInput, TOutput]):
    """Stateless, single-responsibility agent."""

    @property
    @abstractmethod
    def spec(self) -> AgentSpec:
        """Name, description, input/output types, capabilities."""
        ...

    @abstractmethod
    async def execute(
        self,
        request: AgentRequest[TInput],
        ctx: ExecutionContext,
    ) -> AgentResponse[TOutput]:
        """Execute task. MUST be stateless and idempotent."""
        ...

# Pelda: Extractor Agent
class ExtractorAgent(SpecialistAgent[ExtractInput, ProcessExtraction]):
    @property
    def spec(self) -> AgentSpec:
        return AgentSpec(
            name="extractor",
            description="Extract structured process data from text",
            input_type=ExtractInput,
            output_type=ProcessExtraction,
            model="openai/gpt-4o",
        )

    async def execute(self, request, ctx):
        prompt = await self.prompts.get("process-doc/extractor", label=ctx.prompt_label)
        result = await self.llm.generate(
            messages=prompt.compile(text=request.input_data.text),
            response_model=ProcessExtraction,
        )
        return AgentResponse(
            status="success",
            output=result,
            scores={"completeness": self._score_completeness(result)},
        )
```

### 4.3 Orchestrator Agent

```python
class OrchestratorAgent:
    """Routes tasks to specialists, holds state, enforces quality gates."""

    def __init__(self, specialists: list[type[SpecialistAgent]], quality_gates: list[QualityGate]):
        assert len(specialists) <= 6, "Max 6 specialist types!"
        ...

    async def run(self, task: OrchestratorTask, ctx: ExecutionContext) -> OrchestratorResult:
        """
        1. Analyze task
        2. Route to appropriate specialist
        3. Check quality gate on result
        4. If gate fails: retry, escalate, or request human review
        5. Aggregate and return
        """
        ...
```

### 4.4 Quality Gate

```python
class QualityGate(BaseModel):
    name: str
    metric: str                    # Score neve (pl. "completeness")
    threshold: float               # Minimum (0.0-1.0)
    on_fail: Literal["retry", "escalate", "reject", "human_review"] = "retry"
    max_retries: int = 2

# Hasznalat:
quality_gates = [
    QualityGate(name="extraction_quality", metric="completeness", threshold=0.8),
    QualityGate(name="review_score", metric="review_score", threshold=0.8, on_fail="human_review"),
]
```

### 4.5 Human-in-the-Loop

```python
class HumanReviewRequest(BaseModel):
    workflow_run_id: str
    step_name: str
    question: str
    context: dict[str, Any]
    options: list[str] | None = None
    priority: Literal["low", "medium", "high", "critical"] = "medium"
    deadline: datetime | None = None

# Ha a quality gate human_review-t kerdez:
# 1. Workflow pauzalodik (status="awaiting_review")
# 2. HumanReviewRequest bekerül a human_reviews tablaba
# 3. Notification megy (webhook/Slack/email)
# 4. Reviewer dontest hoz (API-n vagy UI-on)
# 5. Workflow folytatodik a dontes alapjan
```

---

## 5. Skill System (Domain Knowledge Packages)

### 5.1 Koncepció

Egy Skill = onallo, telepitheto Python csomag:
- Workflow-k (DAG definiciok)
- Agent-ek (Specialist implementaciok)
- Prompt-ok (YAML + Langfuse sync)
- Modellek (Pydantic schemak)
- Tesztek (Promptfoo + pytest)

### 5.2 Skill Manifest (Progressive Disclosure)

```yaml
# skills/process_documentation/skill.yaml
name: process_documentation
display_name: "Process Documentation & Diagramming"
version: "2.0.0"
description: "Natural language -> structured BPMN documentation + diagrams"
author: "BestIxCom Kft"

capabilities:
  - intent_classification
  - text_elaboration
  - process_extraction
  - quality_review
  - diagram_generation
  - table_generation

required_models:
  - "openai/gpt-4o"        # Extraction, review
  - "openai/gpt-4o-mini"   # Classification, diagrams

workflows:
  - process-documentation

agent_types:
  - ClassifierAgent
  - ElaboratorAgent
  - ExtractorAgent
  - ReviewerAgent
  - DiagramGeneratorAgent

prompts:
  - process-doc/classifier
  - process-doc/elaborator
  - process-doc/extractor
  - process-doc/reviewer
  - process-doc/mermaid_flowchart

estimated_cost_per_run: 0.06

tags: [bpmn, documentation, diagrams, hungarian, english]
```

**Progressive Disclosure:** A keretrendszer eloszor csak a manifest-et tolti be (metadata). A Skill reszleteit (workflow definicio, agent kod, prompts) csak akkor tolti be, amikor tenylegesen szukseg van rajuk.

### 5.3 Skill Telepites

```bash
aiflow skill install ./skills/process_documentation
# 1. Manifest betoltes es validalas
# 2. Fuggoseg-ellenorzes (required_models elerheto?)
# 3. Workflow-k regisztracio a catalogba
# 4. Agent-ek regisztracio a registrybe
# 5. Prompt YAML-ok sync Langfuse-ba (dev label)
# 6. Tesztek futtatas (opcionalis: --skip-tests)
```

### 5.5 Skill Instance Reteg

Egy Skill SABLON (template), amibol tobb PELDANY (instance) futhat kulonbozo konfiguracioval:

```
Skill Template (kod) -> skills/aszf_rag_chat/ (agents, workflow, models)
  |
Skill Instance Config -> instances/allianz/hr_aszf_chat.yaml (collection, prompts, data)
  |
Skill Instance Runtime -> PostgreSQL: skill_instances tabla (metrics, cost, status)
```

Pelda: Ugyanazon aszf_rag_chat skill-bol 3 instance egy ugyfélnel:
- "HR Szabalyzat Chat" (hr_docs collection, HR promptok)
- "Jogi Dokumentum Chat" (legal_docs collection, jogi promptok)
- "IT Policy Chat" (it_docs collection, IT promptok)

Minden instance sajat:
- VectorStore collection (kulonbozo dokumentumok)
- Langfuse prompt namespace (kulonbozo system prompt-ok)
- Budget es SLA (kulonbozo koltseg keretek)
- Adatforrasok (kulonbozo SharePoint/S3/upload)

---

## 6. Prompt Platform

### 6.1 Langfuse SSOT + YAML Fallback

```
YAML Source (Git)  -->  Langfuse (Cloud SSOT)  -->  Runtime Cache (5 min TTL)
                                                         |
                                                    Application
                                                         |
                                              Fallback to local YAML
                                              (ha Langfuse elerheto)
```

### 6.2 Prompt YAML Format

```yaml
name: process-doc/classifier
version: 3
description: "Classify user input as process/greeting/off_topic"

system: |
  You are a process documentation assistant.
  Classify the user's message.

user: |
  Message: {{ message }}

  Respond in JSON: {"category": "process|greeting|off_topic", "confidence": 0.0-1.0}

config:
  model: openai/gpt-4o-mini
  temperature: 0.1
  max_tokens: 200
  response_format: {"type": "json_object"}

metadata:
  language: hu
  tags: [classification, routing]

examples:
  - user: "Szabadsag igenylesi folyamat"
    assistant: '{"category": "process", "confidence": 0.95}'
  - user: "Szia, segitesz?"
    assistant: '{"category": "greeting", "confidence": 0.9}'

langfuse:
  sync: true
  labels: [dev, test]
```

### 6.3 A/B Testing

```python
class ABTest(BaseModel):
    name: str
    prompt_name: str
    variants: dict[str, str]  # variant_name -> langfuse_label
    traffic_split: dict[str, float]  # variant_name -> percentage
    metrics: list[str]  # Scores to track

# Pelda:
ab_test = ABTest(
    name="classifier-v3-vs-v4",
    prompt_name="process-doc/classifier",
    variants={"control": "prod", "treatment": "prod-v4"},
    traffic_split={"control": 0.9, "treatment": 0.1},
    metrics=["accuracy", "latency_ms"],
)
```

---

## 7. Execution Platform

### 7.1 Queue Architektura

```
API Request
    |
    v
JobQueue (Redis + arq)
    |
    +-- critical_queue  (SLA < 5s)
    +-- high_queue      (SLA < 30s)
    +-- normal_queue    (SLA < 120s)
    +-- low_queue       (batch, hatter)
    +-- dlq             (failed, retry exhausted)
    |
    v
Worker Pool (N replica)
    |
    v
WorkflowRunner
```

**Delivery garantaciok:**
- At-least-once delivery (arq + Redis)
- FIFO within same priority queue
- No global ordering across different priority queues
- Duplicate execution mitigation: X-Idempotency-Key (lasd [22_API_SPECIFICATION](22_API_SPECIFICATION.md))

### 7.2 API - Sync es Async mod

```python
# Sync (kicsi workflow-k, azonnali valasz)
POST /api/v1/workflows/classify/run
{"input": {"message": "..."}, "mode": "sync"}
-> 200 OK {"result": {...}, "trace_id": "..."}

# Async (kozepmeretű es nagy workflow-k)
POST /api/v1/workflows/process-documentation/run
{"input": {"message": "..."}, "mode": "async", "priority": "normal"}
-> 202 Accepted {"job_id": "...", "status_url": "/api/v1/jobs/..."}

# Job statusz lekerdezes
GET /api/v1/jobs/{job_id}
-> 200 OK {"status": "running", "steps_completed": 3, "steps_total": 7}

# Job eredmeny
GET /api/v1/jobs/{job_id}/result
-> 200 OK {"result": {...}, "cost_usd": 0.058, "duration_ms": 12340}
```

### 7.3 Scheduler

```python
# Cron trigger
POST /api/v1/schedules
{
    "name": "daily-report",
    "workflow": "generate-report",
    "trigger": "cron",
    "cron": "0 8 * * 1-5",
    "input": {"report_type": "daily"}
}

# Event trigger (Redis pub/sub)
POST /api/v1/schedules
{
    "name": "on-document-upload",
    "workflow": "process-document",
    "trigger": "event",
    "event_pattern": "document.uploaded.*"
}

# Webhook trigger
POST /api/v1/schedules
{
    "name": "external-webhook",
    "workflow": "handle-external",
    "trigger": "webhook",
    "webhook_path": "/hooks/external-event"
}
```

---

## 8. Observability Platform

### 8.1 Tracing Hierarchia

```
Workflow Run (Langfuse Trace)
    |
    +-- Step: classify_intent (Langfuse Span)
    |   +-- LLM Call: gpt-4o-mini (Langfuse Generation)
    |   +-- Score: accuracy=0.95
    |
    +-- Step: elaborate (Langfuse Span)
    |   +-- LLM Call: gpt-4o (Langfuse Generation)
    |
    +-- Step: extract (Langfuse Span)
    |   +-- LLM Call: gpt-4o (Langfuse Generation)
    |   +-- Score: completeness=0.87
    |
    +-- Step: review (Langfuse Span)
    |   +-- LLM Call: gpt-4o (Langfuse Generation)
    |   +-- Score: review_score=0.82
    |   +-- Quality Gate: PASSED (threshold=0.8)
    |
    +-- Step: generate_diagram (Langfuse Span)
    |   +-- LLM Call: gpt-4o-mini (Langfuse Generation)
    |
    +-- Workflow Score: total_cost_usd=0.058
    +-- Workflow Score: sla_met=true
```

### 8.2 Cost Tracking

```
Per-step:     step_runs.cost_usd
Per-workflow:  workflow_runs.total_cost_usd (SUM of steps)
Per-team:      teams.budget_used_usd (SUM of workflow runs)
Per-model:     cost_records aggregated by model

Budget enforcement:
1. Before each LLM call: check ctx.budget_remaining_usd
2. Before each workflow: check team monthly budget
3. Alert at 80% budget usage
4. Block at 100% budget usage (configurable)
```

### 8.3 SLA Monitoring

```python
class SLADefinition(BaseModel):
    workflow_name: str
    max_duration_seconds: int
    target_success_rate: float = 0.99
    alert_channels: list[str] = ["slack"]

# SLA breach -> alert webhook
# SLA report: p50, p95, p99 latency + success rate per workflow
```

---

## 9. Security & Governance

### 9.1 Authentication Flow

```
Client -> API Gateway
    |
    +-- API Key: "aiflow_sk_..." -> Lookup in users table
    +-- JWT Token: Bearer ... -> Validate signature + claims
    |
    v
ExecutionContext.user_id + team_id beallitva
    |
    v
RBAC check: user.role + permissions vs requested action
```

### 9.2 Roles

| Role | Jogosultsagok |
|------|---------------|
| admin | Minden |
| developer | Workflow CRUD, Skill install, Prompt sync, Eval run |
| operator | Workflow run, Eval run |
| viewer | Read-only minden |

### 9.3 Audit Trail

Minden szignifikans muvelet loggolva:
- workflow_run (ki, mit, mikor, mennyi koltseg)
- workflow_create/modify/delete
- skill_install/uninstall
- prompt_sync/update
- user_create/role_change
- budget_change
- config_change
