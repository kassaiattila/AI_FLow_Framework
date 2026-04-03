# AIFlow v1.2.0 — Orchestrable Service Architecture

## Context

AIFlow v1.1.4 has 15 working services that operate independently. The goal: **YAML-defined, orchestratable pipelines** that chain services together. The approach: **Pipeline as Code** — YAML definitions developed with Claude Code assistance, NOT a graphical drag-and-drop builder (which leads to unmaintainable spaghetti for complex logic).

The framework already has a mature WorkflowRunner + DAG engine, ServiceRegistry, EventBus, Scheduler, JobQueue. The orchestration layer is a **thin bridge** connecting existing pieces.

**Design Principles:**
- **Modular:** Each service is independently deployable, testable, and removable
- **Pipeline as Code:** YAML pipelines are version-controlled, code-reviewed, Claude Code-assisted
- **Plugin architecture:** New services added without touching core — just implement adapter + register
- **No GUI pipeline builder:** Complex pipelines are maintained as code (YAML + Jinja2), not as visual graphs
- **Unknown future needs:** The adapter registry + YAML schema is open for extension

**Prerequisite:** Commit all session 4 changes first (20+ modified files, uncommitted on main). ✅ DONE (61ce21e)

---

## Reszletes Tervek (kulon fajlok)

| Fajl | Tema | Allapot |
|------|------|---------|
| [49_STABILITY_REGRESSION.md](49_STABILITY_REGRESSION.md) | API/DB/UI stabilitas, regresszios tesztek | KESZ |
| [50_RAG_VECTOR_CONTEXT_SERVICE.md](50_RAG_VECTOR_CONTEXT_SERVICE.md) | Advanced RAG: OCR, chunking, metadata, reranking, VectorOps, GraphRAG | KESZ |
| [51_DOCUMENT_EXTRACTION_INTENT.md](51_DOCUMENT_EXTRACTION_INTENT.md) | Parameterezheeto dokumentumtipusok, intent routing, szamla use case | KESZ |
| [52_HUMAN_IN_THE_LOOP_NOTIFICATION.md](52_HUMAN_IN_THE_LOOP_NOTIFICATION.md) | Professzionalis review UI, multi-channel ertesitesek | KESZ |
| [53_FRONTEND_DESIGN_SYSTEM.md](53_FRONTEND_DESIGN_SYSTEM.md) | UI konyvtar, Untitled UI audit, chat UI, user journey, cross-platform | KESZ |
| [54_LLM_QUALITY_COST_OPTIMIZATION.md](54_LLM_QUALITY_COST_OPTIMIZATION.md) | Promptfoo CI/CD, LLM rubric scoring, koltseg optimalizalas, Gotenberg | KESZ |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ ADMIN UI                                                     │
│ Pipeline List │ YAML Editor + Validator │ Run Monitor         │
│ (NO drag-and-drop — Pipeline as Code approach)               │
└──────────┬──────────────────────────────────────────────────┘
           │ fetchApi
┌──────────▼──────────────────────────────────────────────────┐
│ API Layer (/api/v1/pipelines)                                │
│ CRUD │ Run │ Validate │ Import/Export │ Templates │ Webhook   │
└──────────┬──────────────────────────────────────────────────┘
           │
┌──────────▼──────────────────────────────────────────────────┐
│ PIPELINE ORCHESTRATOR (src/aiflow/pipeline/)                 │
│ PipelineRunner → Compiler → WorkflowRunner (existing DAG)    │
│ Jinja2 Templates │ for_each │ Conditions │ Checkpoints       │
└──────────┬──────────────────────────────────────────────────┘
           │ AdapterRegistry (plugin discovery)
┌──────────▼──────────────────────────────────────────────────┐
│ SERVICE ADAPTERS — unified execute(input, config, ctx)→dict  │
├──────────────────────┬──────────────────────────────────────┤
│ Tier 1: CORE (P1-5)  │ Tier 2: SUPPORTING (P6)              │
│ ● email_connector    │ ● notification (email/slack/webhook)  │
│ ● classifier         │ ● kafka_broker (middleware)            │
│ ● document_extractor │ ● service_manager (lifecycle)          │
│ ● rag_engine         ├──────────────────────────────────────┤
│ ● media_processor    │ Tier 3: ADVANCED RAG (P7)             │
│ ● diagram_generator  │ ● data_cleaner (LLM cleaning)         │
│                      │ ● advanced_chunker (6 strategies)      │
│                      │ ● metadata_enricher (auto-metadata)    │
│                      │ ● reranker (cross-encoder)             │
│                      │ ● graph_rag (Neo4j, optional)          │
│                      │ ● vector_ops (index lifecycle)          │
│                      │ ● advanced_parser (OCR, multi-backend) │
└──────────────────────┴──────────────────────────────────────┘
```

**Plugin megkozelites:** Uj szolgaltatas hozzaadasa 3 lepesben:
1. Implementald a `BaseService`-t (`src/aiflow/services/{name}/service.py`)
2. Ird meg az adaptert (`src/aiflow/pipeline/adapters/{name}_adapter.py`)
3. Regisztrald az `AdapterRegistry`-ben — azonnal hasznalhato YAML pipeline-okban

---

## Tier 1: Core Orchestration (Phase 1-5)

### Phase 1: Service Adapter Layer

**Goal:** Unified `execute(input, config, ctx) -> dict` wrapper over existing services.

**New files:**
- `src/aiflow/pipeline/__init__.py`
- `src/aiflow/pipeline/adapter_base.py` — `ServiceAdapter` protocol + `AdapterRegistry`
- `src/aiflow/pipeline/adapters/__init__.py` — auto-discovery of adapter modules
- `src/aiflow/pipeline/adapters/email_adapter.py`
- `src/aiflow/pipeline/adapters/classifier_adapter.py`
- `src/aiflow/pipeline/adapters/document_adapter.py`
- `src/aiflow/pipeline/adapters/rag_adapter.py`
- `src/aiflow/pipeline/adapters/media_adapter.py`
- `src/aiflow/pipeline/adapters/diagram_adapter.py`

**Key design:**
```python
class ServiceAdapter(Protocol):
    service_name: str
    method_name: str
    input_schema: type[BaseModel]
    output_schema: type[BaseModel]
    async def execute(self, input_data: dict, config: dict, ctx: ExecutionContext) -> dict: ...

class AdapterRegistry:
    _adapters: dict[tuple[str, str], ServiceAdapter]
    def register(self, adapter: ServiceAdapter) -> None
    def get(self, service_name: str, method_name: str) -> ServiceAdapter
    def list_adapters(self) -> list[tuple[str, str]]
    def discover(self, package: str = "aiflow.pipeline.adapters") -> None:
        """Auto-import all adapter modules in package → self-registering."""
```

Each adapter: gets service from `ServiceRegistry` (or instantiates standalone), translates config → kwargs, calls method, returns `.model_dump()`. Handles `for_each` internally with `asyncio.Semaphore(concurrency)`.

**Reuses:** `src/aiflow/services/registry.py`, `src/aiflow/core/context.py`

---

### Phase 2: YAML Pipeline Schema + Compiler

**Goal:** Parse YAML → existing `DAG` + `step_funcs` for `WorkflowRunner.run()`.

**New files:**
- `src/aiflow/pipeline/schema.py` — Pydantic models
- `src/aiflow/pipeline/template.py` — Jinja2 `SandboxedEnvironment` + `StrictUndefined`
- `src/aiflow/pipeline/compiler.py` — `PipelineDefinition` → `(DAG, step_funcs)`
- `src/aiflow/pipeline/parser.py` — YAML loading + validation

**YAML format:**
```yaml
name: email_to_document
version: "1.0.0"
description: "Email → classify → extract attachments → process documents"
trigger:
  type: manual  # manual | cron | event | webhook
input_schema:
  connector_id: { type: string, required: true }
  days: { type: integer, default: 7 }

steps:
  - name: fetch_emails
    service: email_connector
    method: fetch_emails
    config:
      connector_id: "{{ input.connector_id }}"
      days: "{{ input.days }}"

  - name: classify_intent
    service: classifier
    method: classify
    depends_on: [fetch_emails]
    for_each: "{{ fetch_emails.output.emails }}"
    config:
      text: "{{ item.subject }} {{ item.body_text }}"

  - name: extract_documents
    service: document_extractor
    method: extract
    depends_on: [classify_intent]
    condition: "output.intent_id in ['invoice', 'contract']"
    for_each: "{{ classify_intent.output.results }}"
    config:
      file_path: "{{ item.attachments[0].path }}"
    retry:
      max_retries: 2
```

**Pydantic schema:**
```python
class PipelineStepDef(BaseModel):
    name: str
    service: str
    method: str
    config: dict[str, Any] = {}
    depends_on: list[str] = []
    for_each: str | None = None       # Jinja2 expression → list
    condition: str | None = None      # "output.field op value"
    retry: RetryPolicy | None = None
    timeout: int | None = None
    concurrency: int = 5

class PipelineDefinition(BaseModel):
    name: str
    version: str = "1.0.0"
    description: str = ""
    trigger: PipelineTriggerDef
    input_schema: dict[str, Any] = {}
    steps: list[PipelineStepDef]
    metadata: dict[str, Any] = {}
```

**Jinja2:** `SandboxedEnvironment` + `StrictUndefined`. Context: `{"input": ..., "<step_name>": {"output": ...}, "item": ...}`.

**Compiler:** For each step → DAGNode + wrapper function. For each depends_on → DAGEdge + Condition. Calls `dag.validate()`.

**Reuses:** `src/aiflow/engine/dag.py`, `conditions.py`, `policies.py`

---

### Phase 3: Pipeline Runner + DB Storage

**Goal:** End-to-end execution persisted to existing `workflow_runs`/`step_runs`.

**New files:**
- `src/aiflow/pipeline/runner.py` — `PipelineRunner`
- `src/aiflow/pipeline/repository.py` — `PipelineRepository` CRUD
- `alembic/versions/027_add_pipeline_definitions.py`

**PipelineRunner:**
```python
class PipelineRunner:
    async def run(self, pipeline_id, input_data, ctx=None) -> WorkflowResult:
        # Load from DB → compile → create workflow_run → WorkflowRunner.run() → update result
    async def resume(self, pipeline_id, run_id) -> WorkflowResult:
    async def run_from_yaml(self, yaml_str, input_data) -> WorkflowResult:  # ad-hoc
```

**Migration 027:**
```sql
CREATE TABLE pipeline_definitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    version VARCHAR(50) NOT NULL DEFAULT '1.0.0',
    description TEXT,
    yaml_source TEXT NOT NULL,
    definition JSONB NOT NULL,
    trigger_config JSONB DEFAULT '{}',
    input_schema JSONB DEFAULT '{}',
    enabled BOOLEAN DEFAULT true,
    team_id UUID REFERENCES teams(id),
    created_by VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(name, version)
);
ALTER TABLE workflow_runs ADD COLUMN pipeline_id UUID
    REFERENCES pipeline_definitions(id) ON DELETE SET NULL;
```

**Reuses:** `WorkflowRunner.run()`, `CheckpointManager`, `state/models.py`

---

### Phase 4: API Endpoints + Triggers

**New files:**
- `src/aiflow/api/v1/pipelines.py` — FastAPI router
- `src/aiflow/pipeline/triggers.py`

**Endpoints (`/api/v1/pipelines`):**

| Method | Path | Description |
|--------|------|-------------|
| GET | `/pipelines` | List all |
| POST | `/pipelines` | Create from YAML |
| GET | `/pipelines/{id}` | Detail + stats |
| PUT | `/pipelines/{id}` | Update YAML |
| DELETE | `/pipelines/{id}` | Delete |
| POST | `/pipelines/{id}/run` | Execute (202 Accepted) |
| GET | `/pipelines/{id}/runs` | Execution history |
| POST | `/pipelines/{id}/validate` | Dry-run validation |
| GET | `/pipelines/{id}/yaml` | Export YAML |
| POST | `/pipelines/import` | Import YAML |
| GET | `/pipelines/templates` | List builtin templates |
| POST | `/pipelines/templates/{name}/deploy` | Deploy template |
| GET | `/pipelines/adapters` | List available service adapters |

**Triggers:** `cron` → existing Scheduler, `event` → existing EventBus, `webhook` → lookup table.

**Modified:** `src/aiflow/api/app.py` (register router), `src/aiflow/core/errors.py` (pipeline errors)

---

### Phase 5: Admin UI — Pipeline as Code

**NO drag-and-drop builder.** Instead: YAML editor + validator + execution monitor.

**Gate prerequisite:** Journey → API → Figma → Code → E2E

**New files:**
- `aiflow-admin/src/pages-new/Pipelines.tsx` — List + YAML create
- `aiflow-admin/src/pages-new/PipelineDetail.tsx` — Edit + runs + validation

**Pipeline list page:**
- DataTable: Name, Version, Trigger, Enabled, Last Run, Run Count
- "Create Pipeline" → modal with YAML textarea + live validation
- Import YAML file upload

**Pipeline detail page:**
- **Definition tab:** YAML source with syntax highlighting + "Validate" button (calls `/validate` API)
- **Runs tab:** Filtered workflow_runs for this pipeline (reuses existing Runs component pattern)
- **Info tab:** Required services (green/red availability), input schema, trigger config
- "Run" button → JSON input form → execute → redirect to run detail

**Pipeline as Code workflow (Claude Code integration):**
```
1. User: "Csinaljunk egy email → invoice pipeline-t"
2. Claude Code: Generates YAML pipeline definition based on available adapters
3. User: Reviews YAML, commits to git
4. Claude Code: Calls POST /api/v1/pipelines to register
5. User: Triggers via UI or schedule
```

**Slash command:** `/new-pipeline` — Claude Code generates pipeline YAML scaffold based on available adapters and user description.

**Modified:** `router.tsx`, `Sidebar.tsx`, `en.json`, `hu.json`

---

## Tier 2: Supporting Services (Phase 6)

Each service is **independent** — implement any subset, in any order, after Tier 1.

### 6A: NotificationService

**File:** `src/aiflow/services/notification/service.py`

```python
class NotificationService(BaseService):
    async def send(self, channel: str, template: str, data: dict, recipients: list[str]) -> NotificationResult
```

**Channels:** email (SMTP/aiosmtplib), Slack (webhook), MS Teams (webhook), generic webhook (httpx POST)

**DB:** `notification_channels` table (Alembic 028) — channel configs + encrypted credentials

**Adapter:** `src/aiflow/pipeline/adapters/notification_adapter.py`

**Pipeline YAML:**
```yaml
- name: notify_admin
  service: notification
  method: send
  config:
    channel: slack
    template: "Invoice processed: {{ extract.output.summary }}"
    recipients: ["#invoices"]
```

### 6B: Kafka Middleware

**Pluggable backend** for existing MessageBroker — NOT a rewrite.

**Files:**
- `src/aiflow/execution/kafka_backend.py` — `KafkaMessageBroker` (aiokafka)
- `src/aiflow/execution/broker_factory.py` — `AIFLOW_BROKER=kafka` env switch

Same `publish/subscribe` interface as existing `MessageBroker`. Pipeline event triggers work over Kafka topics automatically.

**Dep:** `aiokafka` (optional: `pip install aiflow[kafka]`)

### 6C: API Service Manager

**File:** `src/aiflow/services/service_manager/service.py`

```python
class ServiceManagerService(BaseService):
    async def list_services(self) -> list[ServiceStatus]
    async def get_service_detail(self, name: str) -> ServiceDetail
    async def update_service_config(self, name: str, config: dict) -> None
    async def restart_service(self, name: str) -> bool
    async def get_service_metrics(self, name: str, period: str) -> ServiceMetrics
```

Exposes: health, metrics (call count, avg duration, error rate, cost), config, registered adapters, used-in-pipelines.

**API:** `GET/PUT /api/v1/services/manager/{name}`

---

## Tier 3: Advanced RAG Pipeline Services (Phase 7)

**Goal:** Enterprise-grade RAG data preparation. Each service is **independently usable** — via pipeline YAML or direct API call. Implement any subset in any order.

### Service Catalog

| Service | Rol | Input → Output | Fuggoseg |
|---------|-----|----------------|----------|
| **data_cleaner** | LLM-alapu dokumentum tisztitas | raw text → cleaned text + corrections | gpt-4o-mini |
| **advanced_chunker** | 6 chunking strategia | text → chunks[] | sentence-transformers (semantic) |
| **metadata_enricher** | Auto metadata kinyeres | text → {title, author, date, entities, keywords} | gpt-4o-mini |
| **reranker** | Cross-encoder ujrarangsorolas | (query, candidates[]) → ranked results[] | cross-encoder model (local) |
| **graph_rag** | Tudasgraf epiteses + kereses | text → entities + relationships (Neo4j) | Neo4j (optional Docker) |
| **vector_ops** | Vektor index eletciklus | collection_id → stats, optimize, reindex | pgvector |
| **advanced_parser** | Multi-backend parszolas + OCR | file → parsed text + tables + images | unstructured, llamaparse, tesseract |

### 7A: DataCleanerService

**File:** `src/aiflow/services/data_cleaner/service.py`

Remove noise (headers/footers/boilerplate), fix OCR errors, normalize whitespace. Uses cheap LLM (gpt-4o-mini).

```python
class DataCleanerService(BaseService):
    async def clean(self, text: str, config: CleaningConfig) -> CleanedDocument
    async def clean_batch(self, documents: list[str], config: CleaningConfig) -> list[CleanedDocument]
```

Config: `remove_headers_footers`, `fix_ocr_errors`, `normalize_whitespace`, `remove_boilerplate`, `language`, `custom_rules[]`

### 7B: AdvancedChunkerService

**File:** `src/aiflow/services/advanced_chunker/service.py`

6 strategy: `fixed` (jelenlegi), `recursive`, `semantic` (embedding-based split), `sentence_window`, `document_aware` (heading detection), `parent_child` (parent context + child precision).

```python
class AdvancedChunkerService(BaseService):
    async def chunk(self, text: str, strategy: str, config: ChunkConfig) -> ChunkResult
```

Config strategy-specifikus: `similarity_threshold` (semantic), `window_size` (sentence_window), `heading_patterns` (document_aware), `parent_chunk_size` (parent_child).

### 7C: MetadataEnricherService

**File:** `src/aiflow/services/metadata_enricher/service.py`

Auto-extract: title, author, date, version, language, category, keywords, named entities, summary, document_type. Enables filtered vector search (pl. "csak a 2026-os szerzodes").

```python
class MetadataEnricherService(BaseService):
    async def enrich(self, text: str, config: EnrichmentConfig) -> EnrichedMetadata
    async def enrich_chunks(self, chunks: list[Chunk], config: EnrichmentConfig) -> list[EnrichedChunk]
```

### 7D: RerankerService

**File:** `src/aiflow/services/reranker/service.py`

Cross-encoder reranking after initial hybrid search. Default: local `cross-encoder/ms-marco-MiniLM-L-6-v2` (~5ms/doc). Fallback: Cohere rerank API, GPT-4o-mini as LLM-reranker.

```python
class RerankerService(BaseService):
    async def rerank(self, query: str, candidates: list[SearchResult], config: RerankConfig) -> list[RankedResult]
```

### 7E: GraphRAGService (optional — requires Neo4j)

**File:** `src/aiflow/services/graph_rag/service.py`

Entity + relationship extraction (LLM), Neo4j graph build, Cypher query generation, hybrid vector+graph search.

```python
class GraphRAGService(BaseService):
    async def extract_entities(self, text: str) -> list[Entity]
    async def build_graph(self, entities: list[Entity], collection_id: str) -> GraphBuildResult
    async def query_graph(self, question: str, collection_id: str) -> GraphQueryResult
    async def hybrid_query(self, question: str, collection_id: str, vector_results: list) -> HybridResult
```

Entity types: Person, Organization, Document, Concept, Date, Amount. Relationship types: AUTHORED, REFERENCES, SIGNED_BY, CONTAINS, PART_OF.

### 7F: VectorOpsService

**File:** `src/aiflow/services/vector_ops/service.py`

Index lifecycle: optimize HNSW/IVF params, bulk update/delete, collection health stats, reindex, version snapshots.

```python
class VectorOpsService(BaseService):
    async def optimize_index(self, collection_id: str, config: IndexConfig) -> IndexStats
    async def bulk_update(self, collection_id: str, updates: list) -> int
    async def bulk_delete(self, collection_id: str, filter: dict) -> int
    async def reindex(self, collection_id: str, new_config: IndexConfig) -> ReindexResult
    async def version_snapshot(self, collection_id: str) -> str
```

### 7G: AdvancedParserService (multi-backend + OCR)

Extends `DocumentExtractorService` with pluggable parser backends:

| Parser | Mikor | Elony |
|--------|-------|-------|
| `docling` (jelenlegi) | PDF, DOCX, XLSX | Gyors, ingyenes |
| `unstructured` | Komplex tablazatok | Jobb tablazat-felismeres |
| `llamaparse` | Szkennelt PDF-ek | LLM-alapu, nagyon pontos |
| `tesseract` | Kepes fajlok | Ingyenes OCR |
| `azure_di` (jelenlegi) | Kezirasos | Legjobb OCR |

**Files:** `src/aiflow/services/document_extractor/parsers/{backend}_parser.py` + `parser_factory.py`

Auto-fallback lanc: docling → unstructured → llamaparse → tesseract → azure.

### Example: Complete Advanced RAG Pipeline

```yaml
name: advanced_rag_ingestion
description: "Enterprise RAG data preparation"
steps:
  - name: parse
    service: document_extractor
    method: parse
    config: { parser: auto, ocr_enabled: true }

  - name: clean
    service: data_cleaner
    method: clean_batch
    depends_on: [parse]
    for_each: "{{ parse.output.documents }}"
    config: { fix_ocr_errors: true, remove_boilerplate: true }

  - name: enrich
    service: metadata_enricher
    method: enrich
    depends_on: [clean]
    config: { extract_entities: true, auto_categorize: true }

  - name: chunk
    service: advanced_chunker
    method: chunk
    depends_on: [enrich]
    config: { strategy: semantic, chunk_size: 512 }

  - name: embed_and_store
    service: rag_engine
    method: ingest_chunks
    depends_on: [chunk]
    config: { collection_id: "{{ input.collection_id }}" }

  - name: build_graph
    service: graph_rag
    method: build_graph
    depends_on: [enrich]
    condition: "input.enable_graph_rag == true"

  - name: optimize
    service: vector_ops
    method: optimize_index
    depends_on: [embed_and_store]
```

---

## Phase 8: Pipeline Templates

**Built-in YAML templates** deployable with one API call or UI click.

**File:** `src/aiflow/pipeline/templates.py` — `TemplateRegistry`
**Dir:** `src/aiflow/pipeline/builtin_templates/` — YAML files

| Template | Steps |
|----------|-------|
| **invoice_automation** | email → classify → extract invoice → verify → export CSV → notify |
| **knowledge_base_update** | email → filter → clean → chunk → RAG ingest → notify |
| **media_to_documentation** | STT → clean → BPMN diagram → RAG ingest |
| **contract_analysis** | parse → entities → metadata → graph → RAG ingest |
| **email_triage** | fetch → classify → route by priority → notify per channel |
| **advanced_rag_ingest** | parse → clean → enrich → semantic chunk → embed → optimize |

**API:** `GET /api/v1/pipelines/templates`, `POST /api/v1/pipelines/templates/{name}/deploy`
**UI:** Template list in Pipelines page → deploy modal with config overrides

---

## Claude Code Integration

### `/new-pipeline` slash command

```
User: /new-pipeline email szamla feldolgozas automatizacio
Claude Code:
1. GET /api/v1/pipelines/adapters → list available adapters
2. Generate YAML based on description + available services
3. POST /api/v1/pipelines/validate → validate
4. Show YAML to user for review
5. On approval: POST /api/v1/pipelines → register
```

### Pipeline development workflow

```
1. User describes business process
2. Claude Code generates pipeline YAML
3. Git commit + code review
4. Deploy via API or /new-pipeline
5. Monitor via UI (Pipelines page → Runs tab)
6. Iterate: modify YAML → validate → redeploy
```

This approach is **more maintainable** than drag-and-drop because:
- YAML is version-controlled (git blame, diff, revert)
- Code review catches logic errors before deployment
- Claude Code can analyze the full pipeline context
- Complex conditions and Jinja2 templates are readable in code form
- No visual spaghetti from 20+ connected nodes

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| UI approach | YAML editor + validator (NO drag-and-drop) | Complex pipelines = spaghetti in visual builders. Code is reviewable, versionable, Claude Code-assisted |
| `for_each` | Adapter-level iteration (single DAG node) | Static DAG, no engine modification needed |
| Pipeline storage | DB + filesystem YAML (import/export) | API-friendly + git-versionable |
| Cross-step refs | Jinja2 SandboxedEnvironment + StrictUndefined | Safe, fail-fast |
| New services | BaseService subclass + adapter + register | 3-step plugin pattern |
| Kafka | Pluggable MessageBroker backend | Zero change to existing code, env switch |
| Reranker | Local cross-encoder default | Fast, free, no API key needed |
| GraphRAG | Optional (Neo4j Docker) | Only when entity-relationship search needed |
| Chunking | Strategy pattern (6 strategies) | YAML-selectable, independently testable |
| OCR | Auto-fallback chain | Best quality/cost tradeoff per document type |
| Templates | Built-in YAML + API deploy | One-click deploy, but customizable |

---

## Implementation Priority & Dependencies

```
Phase 0: Git commit (prereq)
    │
Phase 1: Adapter Layer ──┐
Phase 2: YAML Schema     ├─ Tier 1: Core (MUST do first, sequential)
Phase 3: Runner + DB     │
Phase 4: API endpoints   │
Phase 5: Admin UI ───────┘
    │
    ├── Phase 6A: Notification     ┐
    ├── Phase 6B: Kafka            ├─ Tier 2: Independent, any order
    ├── Phase 6C: Service Manager  ┘
    │
    ├── Phase 7A: Data Cleaner      ┐
    ├── Phase 7B: Advanced Chunker  │
    ├── Phase 7C: Metadata Enricher │
    ├── Phase 7D: Reranker          ├─ Tier 3: Independent, any order
    ├── Phase 7E: GraphRAG          │
    ├── Phase 7F: VectorOps         │
    ├── Phase 7G: Advanced Parser   ┘
    │
    └── Phase 8: Templates (after enough services exist)
```

**Tier 1** (Phase 1-5): Sequential, ~3-4 sessions
**Tier 2** (Phase 6): Each ~1 session, independent
**Tier 3** (Phase 7): Each ~1 session, independent
**Phase 8**: ~1 session after services are ready

---

## Verification Plan

**Per-phase:**
1. Phase 1: Unit tests per adapter (mock service → verify I/O mapping)
2. Phase 2: Unit tests for YAML parse, Jinja2 resolve, DAG compile
3. Phase 3: Integration: YAML → compile → WorkflowRunner → check DB rows
4. Phase 4: `curl` every endpoint (CRUD + run + validate)
5. Phase 5: Playwright E2E (navigate → list → create → run → view runs)
6-8: Unit + integration per service, adapter registered + YAML pipeline test

**End-to-end smoke test:**
```bash
# Create + run + verify
TOKEN=$(curl -s -X POST localhost:8102/api/v1/auth/login ...)
curl -X POST /api/v1/pipelines -d '{"yaml_source": "..."}'
curl -X POST /api/v1/pipelines/{id}/run -d '{"connector_id": "..."}'
curl /api/v1/pipelines/{id}/runs  # Check status + results
```

---

## File Change Summary

| Phase | Action | File |
|-------|--------|------|
| 1 | CREATE | `src/aiflow/pipeline/__init__.py` |
| 1 | CREATE | `src/aiflow/pipeline/adapter_base.py` |
| 1 | CREATE | `src/aiflow/pipeline/adapters/*.py` (7 adapter files) |
| 2 | CREATE | `src/aiflow/pipeline/schema.py`, `template.py`, `compiler.py`, `parser.py` |
| 3 | CREATE | `src/aiflow/pipeline/runner.py`, `repository.py` |
| 3 | CREATE | `alembic/versions/027_add_pipeline_definitions.py` |
| 3 | MODIFY | `src/aiflow/state/models.py` — add pipeline_id to WorkflowRunModel |
| 4 | CREATE | `src/aiflow/api/v1/pipelines.py`, `src/aiflow/pipeline/triggers.py` |
| 4 | MODIFY | `src/aiflow/api/app.py`, `src/aiflow/core/errors.py` |
| 5 | CREATE | `aiflow-admin/src/pages-new/Pipelines.tsx`, `PipelineDetail.tsx` |
| 5 | MODIFY | `router.tsx`, `Sidebar.tsx`, `en.json`, `hu.json` |
| 6A | CREATE | `src/aiflow/services/notification/service.py` + adapter |
| 6B | CREATE | `src/aiflow/execution/kafka_backend.py`, `broker_factory.py` |
| 6C | CREATE | `src/aiflow/services/service_manager/service.py` |
| 7A-G | CREATE | `src/aiflow/services/{name}/service.py` + adapter (7 services) |
| 8 | CREATE | `src/aiflow/pipeline/templates.py`, `builtin_templates/*.yaml` |
