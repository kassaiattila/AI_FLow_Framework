# AIFlow v1.8.0 Sprint X — Intake pipeline unification + Professional RAG chat management

> **Status:** PUBLISHED 2026-04-26 by post-Sprint-W audit session SX-1.
> **Branch convention:** `feature/x-sx{N}-*` (each session its own branch → PR → squash-merge).
> **Parent docs:**
> - `docs/post_sprint_w_audit.md` — operator-facing audit (SOURCE)
> - `docs/sprint_w_retro.md` — Sprint W follow-ups SW-FU-1..5
> **Predecessor:** v1.7.0 Sprint W (production-readiness + multi-tenant cleanup, MERGED)
> **Target tag (post-merge):** `v1.8.0` (minor — new capability cohorts)

---

## 1. Goal

Sprint X turns three skills that ship individually (UC3 intent, DocRecognizer doc-intent, UC2 RAG chat) into a **single intake-to-chat pipeline** with operator-grade observability and a professional chat surface.

Three pipeline gaps Sprint W exposed but did not close:

1. **UC3 EXTRACT path is hardcoded to `invoice_processor`** (Sprint Q S135). It does not consult DocRecognizer. Every EXTRACT email is treated as `hu_invoice` regardless of attachment content. **SX-2** replaces the hardcoded call with DocRecognizer-mediated dispatch.

2. **No routing trace.** Operators cannot see why a doctype was picked, which extraction path ran, or whether the rule engine matched. **SX-3** ships an Alembic 050 `routing_runs` table + 3-route API + admin UI page so every routing decision is observable.

3. **RAG chat is a stateless API.** `/aszf/chat` accepts a question, returns an answer, forgets the turn. No conversation persistence, no UI persona switcher, no per-tenant collection picker, no cost meter, no transcript export. **SX-4** promotes the RAG surface from "demo" to "professional".

Sprint W follow-ups SW-FU-2 (admin UI source-toggle on `/prompts/workflows`) and SW-FU-3 (audit script extension) bundle into **SX-5** alongside the close session.

### Capability cohort delta

| Cohort | Sprint W close | Sprint X close (target) |
|---|---|---|
| UC3 EXTRACT path | hardcoded `invoice_processor` | **DocRecognizer-mediated dispatch** by detected doctype (default-off; UC1 byte-stable on flag-on) |
| Routing observability | none | **`routing_runs` audit trail** + 3-route API + `/routing-runs` admin UI |
| RAG chat | stateless `/aszf/chat` API | **DB-backed conversation persistence** + admin UI persona switcher + collection picker + citation card + cost meter + transcript export |
| `/prompts/workflows` UI source-toggle | router accepts `?source=`, UI does not | **3-option segmented control** (closes SW-FU-2) |
| Multi-tenant audit coverage | `rag_collections` only | **+ `skill_instances` / `intent_schemas` / `document_extractor`** read-only audit (closes SW-FU-3) |
| Endpoints / routers | 201 / 32 | **208 / 34** (+3 routing-runs + 4 conversations) |
| UI pages | 27 | **28** (+ `/routing-runs`; `/aszf/chat` upgraded in place) |
| Alembic head | 049 | **051** (050 routing_runs, 051 aszf_conversations + aszf_conversation_turns) |
| ci.yml jobs | 5 | 5 (no new CI gates this sprint) |

---

## 2. Sessions

### SX-1 — Post-Sprint-W audit + Sprint X kickoff (THIS SESSION)
**Scope.** Pure planning + docs. No code changes.

1. Publish `docs/post_sprint_w_audit.md`.
2. Publish `01_PLAN/121_SPRINT_X_INTAKE_PIPELINE_RAG_CHAT_PLAN.md` (this file).
3. Generate `session_prompts/NEXT.md` → SX-2 prompt.
4. Update CLAUDE.md banner with Sprint X kickoff.
5. Open PR against `main`.

**Gate.** All 4 deliverables present; PR opens cleanly; no code changes.

**Expected diff.** ~700 LOC docs / 0 LOC code.

**Risk.** None — planning-only.

**UC golden-path gate.** n/a (planning).

---

### SX-2 — UC3 → DocRecognizer routing layer
**Scope.** Replace Sprint Q S135's hardcoded `invoice_processor` call with DocRecognizer-mediated dispatch. Default-off; flag-on path UC1 byte-stable on `hu_invoice`.

1. **Settings.** New `UC3DocRecognizerRoutingSettings`:
   - `enabled: bool = False` (env `AIFLOW_UC3_DOC_RECOGNIZER_ROUTING__ENABLED`)
   - `confidence_threshold: float = 0.6` (below threshold → fall through to existing `invoice_processor` byte-stable; mirrors Sprint Q `_intent_class_is_extract` gate pattern)
   - `total_budget_seconds: float = 30.0` (`asyncio.wait_for` wrap; Sprint Q pattern)
   - `unknown_doctype_action: Literal["fallback_invoice_processor", "rag_ingest", "skip"] = "fallback_invoice_processor"` (preserves Sprint Q behaviour as the "fallback_invoice_processor" default)
2. **Routing helper.** New `_route_extract_by_doctype(email, attachments) -> ExtractionDecision` in `email_intent_processor`:
   - For each attachment, call `DocumentRecognizerOrchestrator.classify(...)` (lazy import to avoid import-time cycles)
   - Pick top-1 doctype if confidence ≥ threshold, else fall through
   - Dispatch:
     - `hu_invoice` → existing `invoice_processor.workflows.process(...)` (byte-stable; reuses Sprint T `invoice_extraction_chain`)
     - other doctypes (`hu_id_card` / `hu_address_card` / `eu_passport` / `pdf_contract`) → `DocumentRecognizerOrchestrator.run(...)` (Sprint W SW-1 extraction wire-up)
     - unrecognized → `unknown_doctype_action` config (default: existing `invoice_processor`)
3. **Wire into `_maybe_extract_invoice_fields`** (Sprint Q S135). When `routing.enabled` is true AND intent is EXTRACT, the helper dispatches via `_route_extract_by_doctype`. When disabled, the existing direct `invoice_processor` call runs (byte-stable).
4. **Per-extraction cost ceiling** — reuse Sprint U S154 `CostPreflightGuardrail.check_step()` per doctype. Each routed extraction respects the per-step `cost_ceiling_usd` from the descriptor.
5. **Per-extraction error isolation** — one attachment failure does not poison the rest. Mirrors Sprint Q per-file isolation pattern.
6. **Decision payload to `EmailDetailResponse`** — additive `routing_decision: Optional[RoutingDecisionView]` field on the existing response (Sprint Q already extended `extracted_fields`; SX-2 adds the routing trace summary). Backward-compat: absent when flag is off.

**Gate.**
- UC3 4/4 unchanged on flag-off (`tests/integration/skills/test_uc3_4_intents.py`)
- UC1 invoice 4/4 unchanged on flag-on (`tests/integration/skills/test_uc1_golden_path.py`) — `hu_invoice` routes to existing `invoice_processor`
- New unit: `_route_extract_by_doctype` dispatches correctly for each of 5 doctypes (5 cases)
- New unit: confidence below threshold → falls through to byte-stable path (1 case)
- New unit: `unknown_doctype_action` config respected (3 cases × 3 actions)
- New unit: per-extraction error isolation (1 case)
- New unit: cost ceiling refusal raises `CostGuardrailRefused` (2 cases)
- New integration: real PG + real OpenAI on a 2-fixture sample (1 hu_invoice + 1 hu_id_card), skip-by-default behind `OPENAI_API_KEY`
- OpenAPI snapshot refresh for `routing_decision` field

**Expected diff.** ~250 LOC service code + ~100 LOC settings/contracts + 12 unit + 1 integration. **+12 unit / +1 integration / 0 endpoint / 0 router**.

**Risk.** R1 — UC3 EXTRACT regression on flag-on. Mitigation: UC1 byte-stable test as the primary gate; default-off rollout; rollback path is the flag flip.

**Risk.** R2 — DocRecognizer per-attachment latency on emails with many attachments. Mitigation: `total_budget_seconds=30.0` cap; per-attachment timeout via `asyncio.wait_for`; partial-result return (some attachments routed, others fall through).

**UC golden-path gate.** UC3 4/4 (flag-off) + UC1 4/4 (flag-on hu_invoice path).

---

### SX-3 — Routing trace audit table + admin UI
**Scope.** Per-email routing observability. Purely additive (writes-only at the orchestrator boundary; reads via new admin API).

1. **Alembic 050** — `routing_runs` table:
   - `id UUID PRIMARY KEY`
   - `tenant_id TEXT NOT NULL DEFAULT 'default'`
   - `email_id UUID` (FK to existing `emails` table; SET NULL on delete)
   - `intent_class TEXT NOT NULL` (matches Sprint O FU-2 `intent_class` resolver)
   - `doctype_detected TEXT NULL` (NULL when classifier fell through)
   - `doctype_confidence FLOAT NULL`
   - `extraction_path TEXT NOT NULL` (CHECK in `('invoice_processor', 'doc_recognizer_workflow', 'rag_ingest_fallback', 'skipped')`)
   - `extraction_outcome TEXT NOT NULL` (CHECK in `('success', 'partial', 'failed', 'refused_cost', 'skipped')`)
   - `cost_usd FLOAT NULL`
   - `latency_ms INTEGER NULL`
   - `metadata JSONB NULL` (per-attachment detail; capped at 8 KB)
   - `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`
   - Indexes: `(tenant_id, created_at DESC)`, `(email_id)`, `(extraction_outcome)`
2. **Repository.** `RoutingRunRepository` with `insert(row) → id`, `list(tenant_id, filters, limit, offset) → list[RoutingRunSummary]`, `get(id) → RoutingRunDetail`, `aggregate_stats(tenant_id, time_window) → RoutingStatsResponse`.
3. **Service-layer write.** `EmailIntentOrchestrator` writes a `routing_runs` row at the SX-2 dispatch boundary. PII redaction: `metadata` JSONB filtered through the existing redaction boundary (DocRecognizer pattern from SV-3).
4. **API.** New router `/api/v1/routing-runs`:
   - `GET /` — list with filters (`tenant_id`, `intent_class`, `doctype_detected`, `extraction_outcome`, `since`, `until`, `limit`, `offset`)
   - `GET /{id}` — detail
   - `GET /stats` — aggregate counts (per-doctype, per-outcome, mean cost, p50/p95 latency)
5. **Admin UI page.** `/routing-runs` — Untitled UI table with filter chips + side drawer for detail. Stats panel at top (5 doctype distribution + outcome distribution). Each row has "View original email" deep-link. EN/HU locale.
6. **OpenAPI snapshot** refreshed (3 new paths + 4 new schemas).

**Gate.**
- Alembic 050 round-trip clean (upgrade + downgrade)
- 12 unit tests (repository × 6 + router × 6)
- 3 integration tests (real PG: insert + list + stats)
- UC3 4/4 + UC1 4/4 unchanged (observation-only writes; no behaviour change)
- Admin UI live Playwright spec `tests/ui-live/routing-runs.md` (3 tests: list renders, filter by doctype works, detail drawer opens)
- OpenAPI drift gate `[ok]` after snapshot refresh

**Expected diff.** ~150 LOC Alembic + ~150 LOC repository + ~120 LOC router + ~250 LOC UI page + locale + Playwright. **+12 unit / +3 integration / +3 endpoints / +1 router / +1 UI page / +1 Alembic (head 049 → 050)**.

**Risk.** R3 — `metadata` JSONB blow-up on emails with many attachments. Mitigation: 8 KB cap at write time; truncation logged at WARN.

**UC golden-path gate.** UC3 4/4 + UC1 4/4 (writes are observation-only).

---

### SX-4 — Professional RAG chat management
**Scope.** Promote `/aszf/chat` from stateless API to polished customer-facing surface with operator-grade management.

1. **Alembic 051** — two tables:
   - `aszf_conversations` (UUID PK, `tenant_id`, `created_by` TEXT, `persona` enum {`baseline` | `expert` | `mentor`}, `collection_name`, `title` nullable, `created_at`, `updated_at`)
   - `aszf_conversation_turns` (UUID PK, `conversation_id` FK, `turn_index` int, `role` enum {`user` | `assistant`}, `content` TEXT, `citations` JSONB, `cost_usd` FLOAT, `latency_ms` INT, `created_at`)
   - Indexes: `aszf_conversations(tenant_id, updated_at DESC)`, `aszf_conversation_turns(conversation_id, turn_index)`
2. **Service.** `ConversationService`:
   - `create(tenant_id, persona, collection_name, title) → ConversationDetail`
   - `list(tenant_id, limit, offset) → list[ConversationSummary]`
   - `get(id, tenant_id) → ConversationDetail` (includes turns)
   - `append_turn(conversation_id, role, content, citations, cost_usd, latency_ms) → TurnDetail`
   - `delete(id, tenant_id) → None`
3. **API.** New router `/api/v1/conversations`:
   - `GET /` — list per tenant
   - `POST /` — create
   - `GET /{id}` — detail with turns
   - `POST /{id}/turns` — append a turn
   - (Delete intentionally deferred to v1.8.1 — operators ask for it after seeing usage patterns)
4. **`/aszf/chat` retrieval API stays byte-stable.** SX-4 does NOT change the existing `POST /api/v1/aszf/chat` retrieval endpoint. UC2 MRR@5 ≥ 0.55 unchanged. Conversation persistence is a layer above retrieval — the UI calls `POST /conversations` to start, then for each turn calls `POST /aszf/chat` (byte-stable) AND `POST /conversations/{id}/turns` (new) to persist.
5. **Admin UI `/aszf/chat` upgrade.** Replace existing minimalist page with:
   - **Left sidebar** — conversation history list (per-tenant, sorted by `updated_at DESC`); click loads conversation; "New conversation" button at top
   - **Top bar** — persona switcher (segmented control: baseline / expert / mentor; defaults to `baseline`); per-tenant collection picker (dropdown of available `rag_collections` for current tenant; defaults to first); cost meter (cumulative USD for current conversation)
   - **Center panel** — turn stream; user turns right-aligned, assistant turns left-aligned with citation card below; assistant turn has cost chip (USD + latency); transcript export button (JSON / markdown download)
   - **Citation card** — clickable; opens deep-link to source document in the live RAG collection (existing `/api/v1/rag/collections/{name}/documents/{id}` route)
   - EN/HU locale
6. **Live Playwright spec `tests/ui-live/aszf-chat.md`** — 4 tests:
   - Test 1: create conversation, ask question, persona switcher selected = `baseline`, citation card renders, cost chip non-zero
   - Test 2: refresh page → conversation persists in sidebar; click → turns reload
   - Test 3: switch persona to `expert` mid-conversation → next turn uses `aszf_rag_chain_expert` descriptor (Sprint U S155)
   - Test 4: transcript export downloads JSON with all turns

**Gate.**
- Alembic 051 round-trip clean
- 15 unit tests (service × 9 + router × 6)
- 3 integration tests (real PG: create + append + list + get)
- UC2 MRR@5 ≥ 0.55 unchanged (existing `/aszf/chat` retrieval API byte-stable)
- Admin UI live Playwright PASS on a clean dev stack
- OpenAPI drift gate `[ok]`

**Expected diff.** ~200 LOC Alembic + ~250 LOC service + ~180 LOC router + ~600 LOC UI page upgrade + locale + Playwright. **+15 unit / +3 integration / +4 endpoints / +1 router / +1 UI page upgrade / +1 Alembic (head 050 → 051)**.

**Risk.** R4 — `aszf_conversation_turns.citations` JSONB schema drift across personas. Mitigation: shared `Citation` Pydantic model on the response boundary; per-persona descriptors already produce the same `extract_citations` step shape (Sprint T S150 + Sprint U S155 baseline + expert + mentor parity).

**Risk.** R5 — UI persona switcher mid-conversation creates inconsistent answer style. Mitigation: persona is per-conversation in the data model; switching mid-conversation creates a visible "persona changed" marker in the turn stream (operator-visible).

**UC golden-path gate.** UC2 MRR@5 ≥ 0.55 (existing chat retrieval byte-stable).

---

### SX-5 — Sprint X close + Sprint W follow-up bundle + tag v1.8.0
**Scope.** Standard close session plus the cheap Sprint W follow-ups.

1. **SW-FU-2 — Admin UI source-toggle widget on `/prompts/workflows`** (~120 LOC React + 30 LOC locale). 3-option segmented control (local / langfuse / both); URL search-param persistence; default `local` byte-stable. Live Playwright `prompt-workflows.md` adds Test 4 (toggle to Langfuse → empty-state hint).
2. **SW-FU-3 — `audit_customer_references.py` extension** (~80 LOC + 3 unit). `--domain {rag_collections,skill_instances,intent_schemas,document_extractor,all}` flag. `--strict` exits non-zero on any domain hit. Documents Alembic 052/053/054 backlog.
3. `docs/sprint_x_retro.md` — retrospective (decisions log SX-1..SX-4, what worked / what hurt, follow-ups).
4. `docs/sprint_x_pr_description.md` — cumulative PR description.
5. `CLAUDE.md` — Sprint X DONE banner + key numbers (2641 → 2691+ unit, 201 → 208 endpoints, 32 → 34 routers, 27 → 28 UI pages, 049 → 051 Alembic head).
6. `session_prompts/NEXT.md` → SY-1 prompt (Sprint Y candidate or audit-gate session).
7. PR opened against `main`, tag `v1.8.0` queued.

**Gate.**
- All bundled follow-ups pass their per-feature gates
- Sprint X cumulative test deltas match the plan (~+50 unit, ~+8 integration)
- Tag `v1.8.0` queued

**Expected diff.** ~120 LOC React + ~30 LOC locale + ~80 LOC script + 3 unit + ~150 LOC docs. **+7 unit (4 toggle + 3 audit) + 0 integration / 0 endpoint / 0 router / 0 UI page**.

**Risk.** R6 — Sprint X scope creep into SX-5. Mitigation: operator freezes scope at SX-4 close; if SX-2..SX-4 burn long, drop SW-FU-2 + SW-FU-3 bundle from SX-5 (re-queue for Sprint Y).

**UC golden-path gate.** All four UCs unchanged (close session is additive only).

---

## 3. Plan, gate matrix

| Session | Theme | Golden-path test | Threshold | Rollback path |
|---|---|---|---|---|
| SX-2 | UC3 → DocRecognizer routing | UC3 4/4 (flag-off) + UC1 4/4 (flag-on hu_invoice) | All four UC3 intents unchanged; UC1 ≥ 75% / `invoice_number` ≥ 90% | Flip `AIFLOW_UC3_DOC_RECOGNIZER_ROUTING__ENABLED=false`; revert squash if needed |
| SX-3 | Routing trace + admin UI | UC3 4/4 + UC1 4/4; routing_runs row written per EXTRACT email | observation-only writes; no behaviour delta | Alembic 050 downgrade; revert squash; routing_runs writes are decoupled from the dispatch decision |
| SX-4 | Professional RAG chat | UC2 MRR@5 ≥ 0.55 unchanged on `/aszf/chat` retrieval API | retrieval API byte-stable; conversation persistence opt-in for UI | Revert UI page; conversations API can stay (orphaned); Alembic 051 downgrade |
| SX-5 | Close + SW-FU bundle | All four UCs unchanged | Sprint X cumulative gate | Revert per-feature squash |

**Threshold column blocks merge.**

---

## 4. Risk register

### R1 — UC3 EXTRACT regression on SX-2 flag-on
The biggest risk in Sprint X. SX-2 changes the UC3 EXTRACT path. Mitigation: default-off; UC1 byte-stable test on flag-on for the `hu_invoice` path; rollback is a flag flip (no migration).

### R2 — DocRecognizer per-attachment latency on emails with many attachments
Per-attachment classify call adds latency. Mitigation: `total_budget_seconds=30.0` cap + `asyncio.wait_for` per attachment + partial-result return + Sprint Q S135 isolation pattern.

### R3 — `routing_runs.metadata` JSONB blow-up
8 KB cap at write time; truncation logged WARN. Operators see truncation in the UI detail drawer.

### R4 — Citation JSONB schema drift across personas
Mitigation: shared `Citation` Pydantic model on response boundary; persona descriptors already produce parity output (Sprint T + Sprint U).

### R5 — UI persona switcher mid-conversation
Persona switch mid-conversation creates inconsistent answer style. Mitigation: persona is per-conversation in the data model; mid-conversation switch creates a "persona changed" marker.

### R6 — SX-5 scope creep
Mitigation: scope freeze at SX-4 close; drop SW-FU bundle if SX-2..SX-4 burned long.

### R7 — Operator-driven SW-FU-5 corpus availability
If anonymized real-document corpus arrives mid-sprint, swap part of SX-5 for corpus measurement (operator decision at SX-4 close).

---

## 5. Definition of done

- [ ] All 4 execution sessions (SX-2..SX-5) merged on `main` with green CI
- [ ] UC3 EXTRACT routes through DocRecognizer when flag-on; falls back to byte-stable invoice_processor when flag-off
- [ ] UC1 invoice golden-path slice unchanged (≥ 75% / `invoice_number` ≥ 90%) on flag-off AND flag-on (hu_invoice path)
- [ ] UC2 `aszf_rag_chat` MRR@5 ≥ 0.55 unchanged on existing `/aszf/chat` retrieval API
- [ ] UC3 `email_intent_processor` 4/4 unchanged on flag-off
- [ ] DocRecognizer 5-doctype top-1 accuracy unchanged on starter corpus
- [ ] Alembic head: 051 (050 routing_runs + 051 conversations + conversation_turns)
- [ ] Every UC3 EXTRACT email post-Sprint-X writes one `routing_runs` row
- [ ] `/routing-runs` admin UI live + filter by doctype/outcome works
- [ ] `/aszf/chat` admin UI conversation persists across page reload
- [ ] Persona switcher in UI selects matching `aszf_rag_chain_<persona>` descriptor
- [ ] Citation card + cost meter render per assistant turn
- [ ] Transcript export downloads JSON
- [ ] OpenAPI drift gate `[ok]` (snapshot refreshed for 7 new paths + new schemas)
- [ ] `/prompts/workflows` UI source-toggle renders + URL-persists (SW-FU-2)
- [ ] `audit_customer_references.py --strict --domain all` exits non-zero with per-domain counts (SW-FU-3)
- [ ] Live Playwright `routing-runs.md` + `aszf-chat.md` PASS on clean dev stack
- [ ] Live Playwright `prompt-workflows.md` Test 4 (toggle) PASS
- [ ] `tag v1.8.0` queued for post-merge
- [ ] `docs/sprint_x_retro.md` + `docs/sprint_x_pr_description.md` published
- [ ] `session_prompts/NEXT.md` → SY-1 prompt

---

## 6. Out of scope (deferred to Sprint Y+)

- SW-FU-1 Langfuse v4 SDK helper — blocked on upstream SDK
- SW-FU-4 Vault AppRole IaC E2E test — infrastructure sprint
- SW-FU-5 / SV-FU-1 DocRecognizer real-document corpus — operator-driven anonymization
- Coverage uplift 70% → 80% (SJ-FU-7)
- Vault rotation E2E + Langfuse v3→v4 server upgrade
- UC3 thread-aware classifier (SP-FU-3)
- DocRecognizer ML classifier
- `skill_instances.customer` / `intent_schemas.customer` / `document_extractor.customer` rename + Alembic 052/053/054 (gated on SX-5 audit baseline publishing the backlog)
- `aszf_conversations` retention TTL — slated for v1.8.1 once operators have feedback on conversation lifetimes
- Conversation delete API — slated for v1.8.1 once operators ask
- Grafana cost panels for routing_runs distributions (SN-FU-3 extension)
- UC1 corpus extension to 25 fixtures (SQ-FU-3)
- UI bundle CI guardrail (SV-FU-2)
- Monaco editor (SV-FU-5)

---

## 7. Skipped items tracker (initial)

| ID | Hely | Mi | Unskip feltetel |
|---|---|---|---|
| SX-SKIP-1 (planned, SX-2) | `tests/integration/skills/test_uc3_doc_recognizer_routing_real.py` | Real-OpenAI 2-fixture routing integration | `secrets.OPENAI_API_KEY` |
| SX-SKIP-2 (planned, SX-3) | `tests/ui-live/routing-runs.md` | Live Playwright spec | Live admin stack (`bash scripts/start_stack.sh --full`) |
| SX-SKIP-3 (planned, SX-4) | `tests/ui-live/aszf-chat.md` | Live Playwright spec | Live admin stack |
| SX-SKIP-4 (planned, SX-5) | `tests/ui-live/prompt-workflows.md` Test 4 | Live Playwright source-toggle assertion | Live admin stack |

Sprint W carry-forwards inherit unchanged: SW-SKIP-1..4 + Sprint V carry-forwards.

---

## 8. STOP conditions

**HARD:**
1. **UC3 4/4 regression on SX-2 flag-off.** By definition the flag-off path is byte-stable. Any 4/4 break is a HARD stop.
2. **UC1 invoice 4/4 regression on SX-2 flag-on.** `hu_invoice` MUST route to existing `invoice_processor`. Any UC1 regression is a HARD stop.
3. **UC2 MRR@5 < 0.55 on SX-4.** Existing `/aszf/chat` retrieval API is byte-stable; conversation persistence is layered above. Any retrieval regression is a HARD stop.
4. **Alembic 050 / 051 round-trip failure.** Halt; downgrade scripts validated independently before merge.
5. **OpenAPI drift gate failure after snapshot refresh.** Halt; reconcile router and snapshot before merge.

**SOFT:**
- SX-2 latency on emails with > 5 attachments exceeds the 30 s budget. Tune per-attachment timeout or `confidence_threshold` to reduce DocRecognizer calls.
- SX-3 `metadata` JSONB blow-up. Tighten 8 KB cap or move detail to dedicated detail table.
- SX-4 persona switcher mid-conversation creates poor UX. Add a confirmation modal in v1.8.1.
- SW-FU-5 corpus arrives mid-sprint. Swap part of SX-5 (operator decision).

---

## 9. Post-Sprint-X audit (DEFER — not Sprint X scope)

Topics queued for Sprint Y audit:

- Coverage uplift 70% → 80% (SJ-FU-7)
- UC3 thread-aware classifier (SP-FU-3)
- DocRecognizer ML classifier (gated on SW-FU-5 corpus signal)
- Grafana cost panels (SN-FU-3 extension to routing_runs)
- Vault rotation E2E + Langfuse v3→v4
- UC1 corpus extension to 25 fixtures (SQ-FU-3)
- Alembic 052/053/054 to drop `customer` from `skill_instances` / `intent_schemas` / `document_extractor` (gated on SX-5 audit)
- `aszf_conversations` retention TTL + delete API (v1.8.1)
- DocRecognizer flag default-on (after one calendar week of routing trace observation)

---

## 10. References

- Audit + Sprint X direction: `docs/post_sprint_w_audit.md`
- Sprint W retro: `docs/sprint_w_retro.md`
- Sprint W plan: `01_PLAN/120_SPRINT_W_KICKOFF_PLAN.md`
- UC trajectory: `01_PLAN/110_USE_CASE_FIRST_REPLAN.md`
- DocRecognizer service: `src/aiflow/services/document_recognizer/`
- DocRecognizer admin UI: `aiflow-admin/src/pages-new/DocumentRecognizer/`
- Existing UC3 EXTRACT path: `skills/email_intent_processor/orchestrator.py` (Sprint Q S135 `_maybe_extract_invoice_fields`)
- Existing UC2 RAG chat surface: `skills/aszf_rag_chat/` + `aiflow-admin/src/pages-new/AszfChat/` + `src/aiflow/api/v1/aszf.py`
- Existing UC1 invoice processor: `skills/invoice_processor/`
- Existing reusable surfaces: `CostPreflightGuardrail.check_step()` (S154), `argparse_output()` (S156), `useTranslate` hook (S140), `bash scripts/start_stack.sh --full` (live stack), Untitled UI primitives + Tailwind v4 + React Aria
- PromptWorkflow descriptors: `prompts/workflows/` (6 total — `aszf_rag_chain` + `aszf_rag_chain_expert` + `aszf_rag_chain_mentor` + `email_intent_chain` + `invoice_extraction_chain` + `id_card_extraction_chain` + `uc3_intent_and_extract`)
- DocType descriptors: `data/doctypes/` (5 total — hu_invoice, hu_id_card, hu_address_card, eu_passport, pdf_contract)
