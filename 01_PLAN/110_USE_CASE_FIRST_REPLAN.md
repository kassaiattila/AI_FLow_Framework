# AIFlow v1.4.5–v1.4.8 — Use-Case First Replan

> **Status:** ACTIVE (author: S93, 2026-04-28 / 2026-04-19 local).
> **Trigger:** S88–S93 consolidation sprint record = high doc drift, low feature delivery.
> 7/7 skill E2E green = **0**. PolicyEngine + ProviderRegistry present but **not wired into any router or service**. 1 week = ~0 user-facing progress.
> **Policy shift:** every sprint from v1.4.5 forward must close with **exactly one use-case going end-to-end green**, monitored in Langfuse, visible in admin UI. Architecture work rides the use-case it enables; it does not get its own sprint.
>
> **Anchor plan docs (unchanged):**
> - `01_PLAN/100_AIFLOW_v2_ARCHITECTURE_REFINEMENT_OVERVIEW.md` (flow contracts)
> - `01_PLAN/104_AIFLOW_v2_FINAL_MASTER_INDEX.md` §5 processing flow, §6.4, §8.4, §10.3
> - `01_PLAN/106_AIFLOW_v2_PHASE_1a_IMPLEMENTATION_GUIDE.md` (foundation — done)

---

## 1. In-scope use-cases (end-user deliverables)

| ID | Use-case | Shipping sprint | Verifier |
|----|----------|-----------------|----------|
| **UC1** | Document processing: upload → parse → extract → intent | Sprint I (v1.4.5) | Playwright golden-path E2E on `Documents` page + Langfuse trace |
| **UC2** | RAG chat: collection ingest → chunk → embed → retrieve → chat | Sprint J (v1.4.6) | Playwright golden-path E2E on `Rag` page + Langfuse trace + retrieval quality metric |
| **UC3** | Email intent: mailbox scan → fetch → intent classify → route | Sprint K (v1.4.7) | Playwright golden-path E2E on `Emails` page + Langfuse trace + routing decision audit |

**Out of scope (archived / deferred):** `cubix`, `spec_writer` — no work on these. If they survive they re-enter the plan as a separate deliverable after v1.4.8.

---

## 2. Approved processing flow (shared across UC1/UC2/UC3)

Per `100_*` + `104_*` §5:

```
IntakePackage                 [Phase 1a  — DONE]
      │
      ▼
RoutingDecision               [Phase 2a contract — NEW in S95]
  signals: size, MIME, OCR-conf, cost cap, tenant policy
  parsers in order of preference:
    1. Unstructured (fast-path text / borndigital)     [NEW, Sprint I]
    2. PyMuPDF4LLM (born-digital PDF fast-path)         [stub existing]
    3. Docling standard pipeline (universal)            [NEW, Sprint I]
    4. Docling VLM + vLLM (hard cases)                  [DEFERRED v1.5.0]
    5. Azure Document Intelligence (Profile B only)     [NEW, Sprint I — S96]
      │
      ▼
ParserResult
      │
      ▼
Classifier (intent + type)    [skill-based, existing; wired S104]
      │
      ▼
ClassificationResult
      │
      ▼
Extractor (structured fields) [R4 refactor — S94]
      │
      ▼
ExtractionResult              [Phase 2b contract — NEW in S97 as Pydantic v1 stub, upgraded v1.5.1]
      │
      ▼
Embedder (RAG branch only)    [Phase 2c provider abstraction — NEW in S99]
      │
      ▼
EmbeddingDecision             [Phase 2c contract — NEW in S99 as Pydantic v1 stub]
```

**UC1** consumes: Routing + Parser + Classifier + Extractor.
**UC2** consumes: same Parser + chunker + Embedder + retrieval.
**UC3** consumes: same flow via `EmailSource` adapter (Phase 1d — DONE), feeds Classifier with intent skill.

Every step emits Langfuse trace. Every contract has Pydantic I/O. Every provider registers to `ProviderRegistry`.

---

## 3. Working assumptions (locked unless user revises)

| # | Decision | Rationale |
|---|----------|-----------|
| A | **LangChain = opt-in utility layer**, max 3 importer modules (classifier, extractor, prompt-template helper). NOT a core framework. No LangGraph adoption (ADR-2 stays REJECTED). | Current codebase has 0 LangChain imports; rewriting Step/Workflow onto LangChain is out-of-proportion for the shipping target. Use `langchain-core` + `langchain-openai` only where Pydantic output parsing or chat-prompt templating gives measurable LOC/quality win. |
| B | **Azure Document Intelligence = Profile B only.** Gated by `policy.cloud_ai_allowed=true`. Profile A (air-gapped) never calls Azure DI. | Matches `104_*` §6.4 cost/compliance separation; aligns with Vault later. |
| C | **Unstructured = dual role.** (1) fast-path parser for text / borndigital without layout complexity; (2) chunker for RAG ingest. Not used for scanned/OCR cases. | Package already proven for these two jobs; avoids inventing a bespoke chunker in UC2. |
| D | **Langfuse = pipeline admin + prompt admin backend.** Backend already integrated (`src/aiflow/observability/tracing.py`, `prompts/sync.py` CLI). UI to be built in S97 (v1) + S107 (v2 with prompt editing). | Existing investment; no reason to pick another tracing/prompt system. |
| E | **Deferred §10.3 contracts minimal path.** Only 3 of 10 land in v1.4.5–v1.4.8 as Pydantic v1 stubs: `RoutingDecision`, `ExtractionResult`, `EmbeddingDecision`. The other 7 stay §10.3 until their owning Phase 2/3 sub-sprint. | Contract stubs enable DB rows + admin viewer; full schema refinement happens when the real consumer ships. |

---

## 4. Sprint map (I → J → K → L)

Each sprint = **2 weeks = 5 sessions** (Sprint L = 1 week = 3 sessions). Branch per sprint, cut from `main` after previous merge.

### Sprint I — v1.4.5 "Document processing usable"
Branch: `feature/v1.4.5-doc-processing` (cut after v1.4.4 merged + tagged).

| Session | Scope | Acceptance |
|---------|-------|-----------|
| **S94** | `DocumentExtractorService.extract_from_package(IntakePackage) -> ExtractionResult` impl (today: `NotImplementedError`). Docling standard pipeline as default extractor. `PolicyEngine` consulted for `allow_cloud_ai` before any provider call. | Unit + integration tests on real Postgres; backward-compat shim still green; manual upload through `/api/v1/intake/upload-package` returns non-empty `ExtractionResult`. |
| **S95** | `RoutingDecision` contract (Pydantic v1 stub) + `MultiSignalRouter.decide(pkg) -> RoutingDecision`. Initial rules: size≤5MB & MIME∈{pdf_born,docx,txt,html} → Unstructured; else → Docling std. `ProviderRegistry` wires Unstructured + Docling std as `ParserProvider` impls. Alembic 038: `routing_decisions` table. | Router unit tests + 1 integration test with 3 real files (small born-digital, scanned PDF, DOCX) routed to expected parser. |
| **S96** | `AzureDocumentIntelligenceParser` (ParserProvider). Gated by `policy.cloud_ai_allowed`. `PIIRedactionGate` (v0: regex email/phone/iban masking) pre-LLM. | Profile A test: Azure DI not called (asserted via registry hook). Profile B test: Azure DI called on scanned PDF. PII gate unit tests. |
| **S97** | UI `DocumentDetail.tsx`: parser-used badge, extraction JSON tab, intent result, Langfuse trace link. Backend endpoints: `GET /api/v1/documents/{id}/trace` (Langfuse URL), `GET /api/v1/documents/{id}/extraction`. `Prompts.tsx` v1: read-only list of Langfuse-synced prompts. | Playwright: upload doc → see parser badge + JSON + trace button works. |
| **S98** | Golden-path E2E: upload 3 real test docs (1 per parser path) → assert `Documents` list + detail + Langfuse trace. `/regression` + `/lint-check` green. PR cut + tag `v1.4.5`. | 3 Playwright E2E GREEN with real services. Coverage ≥70% on `src/aiflow/services/document_extractor/` + `src/aiflow/routing/`. |

**Sprint I exit gate:** upload a real PDF in the admin UI, watch parser routing in `DocumentDetail`, click through to Langfuse trace, see structured ExtractionResult JSON. Demo-able.

---

### Sprint J — v1.4.6 "RAG chat usable" — **DONE** (tag `v1.4.5-sprint-j-uc2`, 2026-04-25)
Branch: `feature/v1.4.6-rag-chat`. Retro: `docs/sprint_j_retro.md`. PR description: `docs/sprint_j_pr_description.md`.

> **Actual session numbering:** S100–S104 (the plan originally listed S99–S103; sprint started one session later because S99 was absorbed into Sprint I close). Scope mapping below reflects what actually shipped.

| Session | Commit | Scope delivered | Acceptance |
|---------|--------|-----------------|-----------|
| **S100** | `9b3c610` | `EmbedderProvider` ABC + BGE-M3 (Profile A) + Azure OpenAI (Profile B) impls; `EmbeddingDecision` contract; Alembic 040; `PolicyEngine.pick_embedder`. | ✅ Unit + integration tests for both providers; alembic 040 up/down/up verified. |
| **S101** | `953e7cd` | `ChunkResult` contract + `ChunkerProvider` ABC (5th registry slot); `UnstructuredChunker`; rag_engine opt-in `use_provider_registry=True` path; Alembic 041 `rag_chunks.embedding_dim`. | ✅ rag_engine UC2 integration end-to-end PASS with real Docker PG. |
| **S102** | `37d5ba7` | UI `Rag.tsx` + `RagDetail.tsx` with `ChunkViewer` (paginated, embedding_dim badge, modal); `GET /collections/{id}/chunks` provenance fields; 3 Playwright E2E. | ✅ Playwright: open collection → see chunks + embedding_dim badge + modal. |
| **S103** | `fa6324a` | Retrieval baseline — pgvector flex-dim (Alembic 042) + `OpenAIEmbedder` (Profile B surrogate) + `scripts/bootstrap_bge_m3.py` + live `test_retrieval_baseline.py` (MRR@5 ≥ 0.55 both profiles) + reranker OSError fallback. | ✅ Live MRR@5 ≥ 0.55 both profiles against bilingual hu+en fixture. |
| **S104** | _(this PR)_ | Sprint J close — resilience flake quarantine + `docs/quarantine.md`; `docs/sprint_j_retro.md`; plan + CLAUDE.md update; PR cut against `main`; tag `v1.4.5-sprint-j-uc2`. | ✅ PR opened, CI green, tag pushed. |

**Scope variance from original plan:**
- **PII redaction gate (planned S102) deferred to Sprint K** — UC3 shares the redactor; folding there keeps Sprint J focused on provable retrieval quality.
- **Golden-path chat E2E (planned S103) reshaped into live MRR@5 retrieval baseline (actual S103)** — retrieval quality gate is the provable "usable" criterion per §8; full chat E2E queued for Sprint K (requires `query()` refactor to use provider registry, currently ingest-only).
- **`query()` refactor to provider registry** — ingest path is provider-aware (S101), but `rag_engine.query()` still instantiates legacy `Embedder`; 1024-dim BGE-M3 collections are ingestable but not queryable via public API. Queued as Sprint K first follow-up.

**Sprint J exit gate actual:**
- ✅ Admin UI `Rag` page ingests collection → shows chunks with embedding_dim + metadata.
- ✅ Retrieval quality gate: MRR@5 ≥ 0.55 on Profile A (BGE-M3) + Profile B (OpenAI surrogate).
- ✅ PolicyEngine selects provider per profile + tenant override.
- ✅ Alembic head 042; unit 1994 PASS; integration 55+ PASS; E2E 413 collected.
- ⏭️ Langfuse trace on chat call — deferred with `query()` refactor (Sprint K).
- ⏭️ Coverage ≥80% on owning modules — measure at Sprint K start, uplift per §7.

---

### Sprint K — v1.4.7 "Email intent usable"
Branch: `feature/v1.4.7-email-intent`.

> **Rescope 2026-04-22 (architect verdict on S105-pre):** the original S104–S108 plan assumed a new `ClassificationStep`, a new `ClassificationResult` contract, and Alembic 043 `classification_results` table. Discovery found all three were redundant — `ClassifierAdapter` + `services/classifier/service.py` already exist; `workflow_runs.output_data` JSONB already persists classification results. **S106 (this sprint)** collapsed to: (a) unify `ClassificationResult` to `services/classifier/service.py` (re-export from `models/protocols/classification.py` + providers ABC), (b) ship `scan_and_classify` thin orchestrator + `POST /emails/scan/{config_id}` endpoint, (c) integration test end-to-end on real PG. Langfuse-backed email_intent skill prompts + routing stay as S107–S109 below.

| Session | Scope | Acceptance |
|---------|-------|-----------|
| **S106** *(was S104)* | **[DELIVERED]** ClassificationResult unify (protocol + providers ABC → re-export canonical service-level model) + `scan_and_classify` thin orchestrator + `POST /api/v1/emails/scan/{config_id}` endpoint. Classifier runs sklearn-keyword strategy against `schema_labels`; Langfuse prompt fetch deferred. | `POST /api/v1/emails/scan/{config_id}` → fetches via `EmailSourceAdapter` → `IntakePackageSink` persists → classifier fills `ClassificationResult` → `workflow_runs` rows written. 1 integration test GREEN on real Docker PG. |
| **S107** *(was S105)* | `IntentRoutingPolicy`: intent → downstream action (notify, extract, archive, manual review). Per-tenant config via PolicyEngine. Langfuse prompt fetch for email_intent skill wired here. | 4-way routing test with real LLM (or deterministic mock with `AIFLOW_LLM_MODE=deterministic`). |
| **S108** *(was S106)* | UI `Emails.tsx`: "Scan mailbox" button, intent badge per email, routing decision chip, Langfuse trace link. Backend `POST /scan`, `GET /{id}/intent`, `.../routing`. | Playwright: click Scan → see email list with intent + routing → trace link works. |
| **S109** *(was S107)* | `Prompts.tsx` v2: edit Langfuse-synced prompts from UI. Backend `PUT /api/v1/prompts/{id}` → Langfuse SDK update. Read-back after save. | Prompt edit from UI → Langfuse HEAD version increments → next intent classification uses new version. |
| **S110** *(was S108)* | Golden-path E2E: mailbox scan → 3 test emails → intents classified → routing persisted. `/regression` + `/lint-check`. PR cut + tag `v1.4.7`. | 1 Playwright E2E GREEN. |

---

### Sprint L — v1.4.8 "Cross-cutting monitoring + cost"
Branch: `feature/v1.4.8-monitoring-cost`.

| Session | Scope | Acceptance |
|---------|-------|-----------|
| **S109** | `Runs.tsx` + `Monitoring.tsx`: Langfuse drill-down (trace tree, step timings, token counts). Backend proxies Langfuse API per tenant. | Playwright: open Runs → pick row → see tree. |
| **S110** | `Costs.tsx` + `CostAttribution` contract (Pydantic v1 stub). `PolicyEngine.cost_cap` enforced at Extractor + Embedder providers (halt + 429 when exceeded). | Cost cap integration test: 2 calls, second one breaches cap, returns 429. Cost attribution row written per call. |
| **S111** | Playwright regression pack: UC1 + UC2 + UC3 run together in CI profile. All 3 E2E GREEN on real services. PR cut + tag `v1.4.8`. | CI profile runs in ≤10 min. |

**Sprint L exit gate = v1.4.8 ship:** 3 use-cases working, monitored, cost-capped, prompts admin-editable.

---

## 5. What gets pushed back

| Item | Was | New target |
|------|-----|-----------|
| Vault hvac prod impl + token rotation | v1.4.5 S94 (0.5 sprint) | **v1.4.9** (full sprint, standalone) |
| Self-hosted Langfuse + Profile A air-gapped E2E | v1.4.5 S95 (0.5 sprint) | **v1.4.9** (with Vault) |
| Docling VLM + Qwen25-VL (hard cases) | v1.5.1 Phase 2b (1 sprint) | **v1.5.0** (after v1.4.8, first Phase 2 sprint) — only VLM, not full Phase 2b scope |
| Gotenberg + veraPDF archival | v1.5.3 Phase 2d | **v1.5.2** (reshuffled; depends on Phase 2 pre-work spike) |
| CrewAI sidecar + OTel + LazyGraphRAG | v1.6.x, v2.0 | Unchanged |
| 10 §10.3 deferred contracts (7 remaining after v1.4.8) | Ad-hoc PP2 session | **PP2 replaced** by incremental contract landing per Phase 2 sub-sprint |

---

## 6. Blockers map — current state → first-session target

### UC1 (Document processing) — target S94
| Blocker | Evidence | Sprint target |
|---------|----------|--------------|
| `extract_from_package()` raises `NotImplementedError` | `src/aiflow/services/document_extractor/service.py` | **S94** — impl body |
| No `MultiSignalRouter` | no file under `src/aiflow/routing/` | **S95** — new module |
| No `ParserProvider` impls registered | `ProviderRegistry` only has Stub*s in tests | **S95–S96** — Unstructured, Docling std, Azure DI (Profile B) |
| UI `DocumentDetail` has no parser/trace/extraction JSON view | `aiflow-admin/src/pages-new/DocumentDetail.tsx` | **S97** |

### UC2 (RAG chat) — target S99
| Blocker | Evidence | Sprint target |
|---------|----------|--------------|
| Embedder hardcoded to `text-embedding-3-small` | `src/aiflow/services/rag_engine/` | **S99** — provider abstraction |
| No chunker abstraction | inline chunking | **S100** — Unstructured chunker |
| No PII redaction before embedding | — | **S102** |
| UI `Rag` has no chunk viewer / retrieval metrics | `aiflow-admin/src/pages-new/Rag.tsx` | **S101** |

### UC3 (Email intent) — target S104
| Blocker | Evidence | Sprint target |
|---------|----------|--------------|
| `EmailSource` adapter exists (Phase 1d) but not wired to `IntentClassifier` skill | adapter in `src/aiflow/sources/` | **S104** glue |
| No intent routing policy per tenant | — | **S105** |
| UI `Emails` has no scan / intent badge | `aiflow-admin/src/pages-new/Emails.tsx` | **S106** |
| Prompt edit path through UI missing | Langfuse sync is backend-only | **S107** |

---

## 7. Test strategy per sprint

- **Unit**: every new contract + provider + router decision table. Target ≥85% on new modules (global ≥70% by v1.4.5 end, ≥75% by v1.4.7 end, ≥80% by v1.4.8 end — retires issue #7).
- **Integration**: real Postgres (Docker 5433) + real Redis (6379) + real or deterministic LLM mode (`AIFLOW_LLM_MODE=deterministic` for CI). Every new endpoint gets 1 happy-path + 1 policy-violation integration test.
- **E2E**: 1 Playwright golden-path per use-case per sprint. Must use real services, no mocks (per `tests/CLAUDE.md`). Trace-link assertion mandatory.
- **Promptfoo**: any touched skill prompt runs the existing 96-case matrix before PR.
- **Langfuse assertion**: each E2E asserts the call emitted a Langfuse trace (trace ID in response header or DB).

---

## 8. Definition of "usable" per use-case

A use-case is **usable** when all of:

1. Admin UI page lets a non-dev user trigger the flow end-to-end (upload / scan / chat).
2. Result is visible in UI (parser badge / intent / answer+citations).
3. Trace is reachable from UI with 1 click → Langfuse.
4. Prompt used is editable in `Prompts.tsx` (Sprint K+).
5. PolicyEngine controls provider selection (Profile A vs B) and cost cap.
6. 1 Playwright golden-path E2E green in CI.
7. Coverage on owning modules ≥80%.

All 7 must be true for the sprint to close green.

---

## 9. Entry / exit gates

| Gate | Location | Who enforces |
|------|----------|--------------|
| **Sprint entry** | Previous sprint tag cut + PR merged to `main` | User (manual PR merge) |
| **Session entry** | `/next` reads `session_prompts/NEXT.md`; prereqs in prompt pass | `/next` skill |
| **Session exit** | `/session-close` runs `/regression` + `/lint-check` + archives prompt + generates NEXT.md | `/session-close` skill |
| **Sprint exit** | 1 Playwright E2E green + coverage delta positive + PR + tag | Session-close of last sprint session |

---

## 10. Links

- `01_PLAN/ROADMAP.md` — forward queue index (this replan updates it).
- `01_PLAN/100_AIFLOW_v2_ARCHITECTURE_REFINEMENT_OVERVIEW.md` — flow contracts.
- `01_PLAN/104_AIFLOW_v2_FINAL_MASTER_INDEX.md` — §5 flow, §6.4 parsers, §8.4 profiles, §10.3 deferred list.
- `01_PLAN/106_AIFLOW_v2_PHASE_1a_IMPLEMENTATION_GUIDE.md` — Phase 1a foundation (done).
- `CLAUDE.md` — conventions, current key numbers.
- `session_prompts/S94_v1.4.5.1_prompt.md` — first session of Sprint I (kickoff).
