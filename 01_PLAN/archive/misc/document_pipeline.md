# Claude Code Prompt — Meglévő AI dokumentumfeldolgozó architektúra finomhangolása, gap elemzés, módosítási terv

Act as a senior enterprise solution architect, lead Python platform engineer, AI systems architect, DevOps architect, and compliance-aware document processing expert.

Your task is NOT to design a new system from scratch.

Your task is to review, refine, and harden an EXISTING document processing architecture baseline.

You must produce:

1. a precise baseline interpretation
2. a re-checked gap analysis
3. a target-state refinement for two deployment profiles
4. a controlled modification plan
5. explicit validation / review cycles
6. concrete acceptance criteria

---

## Critical working rules

- Do NOT redesign the platform from zero.
- Do NOT split it into two separate products or codebases.
- Assume the core architecture already exists.
- Work from the provided baseline only.
- Preserve valid existing design decisions wherever possible.
- Only propose changes where there is a real gap, risk, inconsistency, missing control, or unnecessary complexity.
- Do NOT introduce random alternative technologies.
- Treat the fixed technology choices below as the intended direction.
- If a fixed component seems problematic, do NOT replace it automatically.
- Instead, flag it as a GAP and explain the required refinement.

---

## Scope clarification

This platform is NOT email-only.

It must support a generalized **multi-source document intake and interpretation pipeline**.

It must handle:

- email + attachments + email body context
- uploaded single files
- uploaded file bundles
- batch-imported files
- files from folder/object storage/repository sources
- scanned and already digitized files
- associated free-text descriptions
- case notes
- form inputs
- package-level context
- file-level context
- ambiguous file-to-description relationships

The platform must process not only isolated files, but also **intake packages** that may contain:

- multiple files
- multiple free-text descriptions
- structured source metadata
- case / request identifiers
- provenance references
- package-level context

This means the review must cover not only document parsing, but also:

- intake normalization
- context association
- file-to-description linking
- package-level interpretation
- cross-document context handling
- review fallback for ambiguous associations

---

## Deployment profiles to support from one shared codebase

### Profile A — Cloud AI disallowed

- no public cloud AI parsing, OCR, extraction, classification, or embedding
- document content must remain in customer-controlled infrastructure
- all document AI must be self-hosted or customer-controlled
- self-hosted storage, metadata DB, vector store, and inference stack required
- policy engine must explicitly block cloud provider selection
- air-gapped / semi-isolated operation must remain possible
- embedding is optional
- PII embedding must require explicit policy approval

### Profile B — Cloud AI allowed, Azure-optimized

- Azure services may be used where tenant/customer policy allows
- Azure AI Document Intelligence may be used for parsing / layout / extraction
- Azure AI Search may be used for retrieval / vector / hybrid search
- Azure OpenAI / Azure Foundry embedding may be used if policy allows
- hybrid combinations must remain possible, for example:
  - Azure parsing + self-hosted embedding
  - self-hosted parsing + Azure search
  - Azure parsing + Azure search + embedding disabled for PII
- cloud use must be policy-controlled
- self-hosted fallback must remain possible where required

---

## Fixed technology direction — follow this, do not improvise replacements

Treat the following as the intended architecture direction.

### Intake and email parsing

- Intake source adapter layer is required
- Email intake direction: **Unstructured OSS**
- Use it for:
  - EML / MSG parsing
  - attachment extraction
  - email metadata extraction
  - email body text as context

### Intake normalization and package handling

Required logical layers:

- intake source adapter layer
- intake normalization layer
- intake package model
- source text ingestion
- source text normalization
- file-to-description association logic
- package-level context handling
- cross-document context handling

### Fast digital PDF parsing

- Fixed component: **PyMuPDF4LLM**
- Use as the primary fast-path parser for born-digital PDFs
- GPU-free path
- not the universal parser
- selected by routing logic

### Structured / deep parsing

- Fixed component: **Docling standard pipeline**
- Use for:
  - complex PDFs
  - scanned documents
  - DOCX / PPTX / XLSX / HTML / image inputs
  - OCR / table / structured layout extraction

### Hard-case VLM parsing

- Fixed direction:
  - **Docling VLM pipeline**
  - **vLLM** runtime where relevant
- Use only for difficult cases, not as universal default

### Self-hosted visual classification and extraction

- Fixed model direction:
  - **Qwen2.5-VL-7B-Instruct**
  - served via **vLLM**
- Use for:
  - page-level or segment-level document classification
  - document boundary support
  - page grouping support
  - structured field extraction

### Routing

- Fixed direction: **multi-signal routing engine**
- Must choose among:
  - PyMuPDF4LLM fast path
  - Docling standard path
  - Docling VLM hard path
  - Azure DI path when allowed
  - self-hosted VLM classification / extraction path
  - Azure-based extraction path when allowed
- Routing must use:
  - file type
  - text layer presence
  - OCR need
  - image dominance
  - table suspicion
  - layout complexity
  - page variance
  - intake package context
  - source text relevance
  - tenant policy
  - provider availability
  - fallback order

### Archival conversion

- Fixed component: **Gotenberg**
- Use for PDF conversion / PDF-A generation / derivative generation

### PDF/A validation

- Fixed component: **veraPDF**
- Validation must be a separate explicit control step
- archival status must not be assumed without validation

### Metadata and self-hosted vector store

- Fixed direction:
  - **PostgreSQL**
  - **pgvector**
- Use for:
  - metadata persistence
  - extraction results
  - processing state
  - lineage / provenance links
  - chunk metadata
  - self-hosted embeddings

### Object storage

- Self-hosted profile:
  - local or S3-compatible object storage
- Azure profile:
  - Azure Blob Storage may be used
- original and derived artifacts must be handled separately

### Self-hosted embedding

- Fixed primary model: **BGE-M3**
- Fixed fallback direction: **multilingual-e5-large-instruct**
- embedding must be optional
- PII embedding must require explicit policy permission
- redaction / masking gate must be supported

### Cloud parsing / extraction

- Fixed Azure component: **Azure AI Document Intelligence**
- Use as provider, not as a separate architecture

### Cloud retrieval / vector search

- Fixed Azure component: **Azure AI Search**
- Use as provider, not as a domain-model replacement

### Cloud embedding

- Fixed Azure direction:
  - **Azure OpenAI / Azure Foundry embeddings**
  - preferred models:
    - `text-embedding-3-large`
    - `text-embedding-3-small`

### Orchestration

- Treat current orchestration approach as baseline
- If state-machine formalization is needed, **LangGraph-compatible direction** is acceptable
- queue-driven worker execution should remain if baseline already uses it

### HITL / manual review

- Keep current workflow / webhook / review-task direction as baseline
- Do not replace it automatically
- Manual review must cover:
  - low confidence extraction
  - ambiguous document boundary
  - ambiguous provider selection
  - ambiguous file-to-description association
  - ambiguous package context interpretation

---

## What you must deliver

Produce the output in this exact structure.

### 1. Baseline interpretation

Summarize how you understand the provided existing architecture.

### 2. Keep-as-is decisions

List which existing architectural decisions are valid and should remain unchanged.

### 3. Re-checked gap analysis

Provide a precise gap analysis across:

- functional gaps
- architectural gaps
- provider abstraction gaps
- configuration gaps
- policy enforcement gaps
- compliance gaps
- archival gaps
- security gaps
- operational gaps
- performance / scaling gaps
- testability gaps
- observability gaps
- audit / traceability gaps
- multi-source intake gaps
- package interpretation gaps
- file-to-description association gaps
- context handling gaps

For each gap include:

- gap name
- description
- affected components
- affected profile(s)
- severity: critical / high / medium / low
- intervention type: mandatory / recommended / optional
- relation to fixed technology direction
- proposed change

### 4. Refined target architecture by profile

Provide separate refinement for:

- Profile A — cloud AI disallowed
- Profile B — cloud AI allowed / Azure-optimized

For each relevant component specify:

- role
- function
- assigned provider / component
- prohibited or discouraged direction
- inputs / outputs
- interface / contract expectations
- configuration parameters
- policy dependencies
- fallback behavior
- error handling expectations
- audit / trace expectations
- compliance constraints

### 5. Single-codebase refinement principles

Explain how both profiles remain inside one codebase using:

- shared core
- provider interfaces
- provider adapters
- policy engine
- config profiles
- tenant overrides
- feature flags
- deployment composition
- strict no-code-fork rule

### 6. Configuration and policy plan

You must explicitly define and interpret at least these parameters:

- `cloud_ai_allowed`
- `cloud_storage_allowed`
- `document_content_may_leave_tenant`
- `embedding_enabled`
- `pii_embedding_allowed`
- `self_hosted_parsing_enabled`
- `azure_di_enabled`
- `azure_search_enabled`
- `azure_embedding_enabled`
- `archival_pdfa_required`
- `pdfa_validation_required`
- `manual_review_confidence_threshold`
- `default_parser_provider`
- `default_classifier_provider`
- `default_extractor_provider`
- `default_embedding_provider`
- `vector_store_provider`
- `object_store_provider`
- `tenant_override_enabled`
- `fallback_provider_order`
- `docling_vlm_enabled`
- `qwen_vllm_enabled`
- `self_hosted_embedding_model`
- `azure_embedding_model`
- `redaction_before_embedding_required`
- `source_adapter_type`
- `intake_package_enabled`
- `source_text_ingestion_enabled`
- `file_description_association_mode`
- `package_level_context_enabled`
- `cross_document_context_enabled`

For each parameter define:

- meaning
- allowed values
- recommended default
- consuming component(s)
- mandatory or optional by profile
- pipeline decisions affected

### 7. Required component-by-component review scope

Your review must explicitly include:

- intake source adapter layer
- email intake
- attachment extraction
- intake normalization layer
- intake package model
- source text ingestion
- source text normalization
- file-to-description association logic
- package-level context handling
- cross-document context handling
- MIME / file detection
- preprocessing
- routing engine
- policy engine
- provider registry / provider selection
- fast parser
- structured parser
- OCR layer
- VLM / classifier
- document boundary detection
- page grouping / split logic
- field extraction
- extraction schema management
- confidence handling
- HITL / manual review
- archival conversion
- PDF/A validation
- metadata handling
- object storage
- metadata database
- vector storage
- chunking layer
- embedding provider
- retrieval preparation
- orchestration / workflow engine
- worker execution model
- retry / resumability / idempotency
- configuration management
- tenant override mechanism
- monitoring / metrics / tracing
- audit logging
- security / access control
- compliance control points
- deployment packaging
- provenance mapping across files and descriptions

### 8. Required processing flows

You must explicitly design and review at least these flows:

1. Email + attachments + email body context
2. Single uploaded file without email
3. Multi-file upload package with one shared free-text description
4. Multi-file upload package with multiple free-text descriptions
5. Batch import from storage without email metadata
6. Scanned file bundle with manually entered case description
7. Mixed package where free text applies only to a subset of files
8. Ambiguous association case requiring manual review
9. Cloud-disallowed package processing
10. Cloud-allowed package processing with Azure parsing

For each flow include:

- intake form
- package model
- context association logic
- routing decisions
- parsing / extraction path
- storage and metadata steps
- review branch if needed
- audit / trace points

### 9. Modification plan

Break changes into:

- structural changes
- intake model changes
- context association changes
- provider interface changes
- parser routing changes
- classifier / extractor changes
- archival pipeline changes
- validation control changes
- embedding governance changes
- storage changes
- configuration changes
- tenant override changes
- security and compliance changes
- monitoring / traceability changes
- testing changes

For each modification define:

- name
- purpose
- why needed
- affected components
- dependencies
- complexity: low / medium / high
- risk
- expected result

### 10. Review and validation cycles

Design these review cycles:

1. baseline consistency review
2. fixed component alignment review
3. multi-source intake review
4. context association review
5. provider abstraction review
6. policy enforcement review
7. config profile review
8. archival + PDF/A validation review
9. security + tenant boundary review
10. functional flow review
11. testability review
12. performance and capacity review
13. deployment review
14. final architecture sign-off review

For each cycle define:

- objective
- input
- checks to perform
- output
- exit criteria
- red flags
- required decisions

### 11. Acceptance criteria

Provide explicit acceptance criteria for:

- shared codebase
- self-hosted profile
- Azure profile
- provider switching
- policy enforcement
- embedding governance
- archival + veraPDF validation
- audit / provenance / lineage
- source-agnostic intake model
- file bundle + free-text context handling
- file-to-description association auditability

### 12. Prioritization

Rank changes as:

- Phase 1 — critical corrections
- Phase 2 — architectural refinements
- Phase 3 — governance and operational hardening
- Phase 4 — optimizations

### 13. Open questions

List remaining decisions across:

- business
- compliance
- security
- operations
- data governance
- tenant model
- embedding policy
- free-text association policy
- package interpretation rules

---

## Output quality requirements

Your output must be:

- precise
- implementation-oriented
- architecturally disciplined
- based on the fixed technology direction
- free from unnecessary redesign
- explicit about what remains unchanged vs what must change
- explicit about single-codebase support for both profiles
- explicit about multi-source intake and free-text context interpretation
- detailed enough to guide architecture refinement and implementation planning

At the end, provide a short final summary with exactly these 3 sections:

1. What can remain unchanged
2. What is the most critical modification
3. Recommended execution order for refinement

---

## Baseline architecture input

Use the following existing architecture as baseline:

[PASTE THE EXISTING ARCHITECTURE HERE]
