# Post-Sprint-W Audit — operator-facing summary

> **Date:** 2026-04-26
> **Trigger:** Sprint W SW-5 close PR #60 merged on `main` (commit `fed97af`); v1.7.0 tag queued post-merge.
> **Audit reference:** `01_PLAN/120_SPRINT_W_KICKOFF_PLAN.md` §9 + `docs/sprint_w_retro.md` §5.
> **Output:** Sprint X kickoff plan at `01_PLAN/121_SPRINT_X_INTAKE_PIPELINE_RAG_CHAT_PLAN.md`.
> **Companion audit:** `docs/honest_alignment_audit.md` (drift recap across Sprint J–W; binding "one use-case per sprint" policy review).

## Operator-directed multi-UC deviation note

`docs/honest_alignment_audit.md` identifies that 6 sprints (M, N, R, S,
U, W) violated the `110_USE_CASE_FIRST_REPLAN.md` "one use-case per
sprint" rule. **Sprint X is a deliberate, operator-directed deviation
from that rule** — a multi-UC pipeline-unification sprint touching UC3
intent + DocRecognizer doc-intent + UC2 RAG chat.

**Why:** the three pipeline gaps Sprint W exposed (see below) are
structurally coupled. UC3 → DocRecognizer routing is unobservable
without the routing trace; the chat surface is unsuitable for
production without conversation persistence; conversation persistence
without the routing context the user is debugging is half-useful.
Splitting into three single-UC sprints would ship the wiring before
the observability that validates it.

**Mitigation:** every session in this multi-UC sprint carries a
**byte-stable golden-path gate** for the UCs it touches. Default-off
rollout discipline (`AIFLOW_UC3_DOC_RECOGNIZER_ROUTING__ENABLED=false`,
existing `/aszf/chat` retrieval API unchanged) ensures the deviation
ships as additive capability, not as a behaviour change. Sprint Y
returns to single-UC quality push (UC2 MRR@5 0.55 → ≥ 0.72).

## State of the project (post Sprint W)

| Layer | Status |
|-------|--------|
| **UC1 invoice extraction** | byte-stable (Sprint Q `issue_date` polish merged S156); `invoice_processor` workflow unchanged in Sprint W |
| **UC2 RAG chat** | byte-stable; baseline + expert + mentor on workflow shim (S150 + S155); query path on `tenant_id` since S143; **no conversation persistence** (every turn is a fresh request); persona only switchable via API param, not via UI |
| **UC3 email intent** | byte-stable (4% misclass since Sprint P); EXTRACT path **hardcoded** to `invoice_processor` (Sprint Q S135); does not consult DocRecognizer for doc-type-aware routing |
| **UC4 monitoring + cost** | per-tenant budgets + preflight guardrail (Sprint N + Sprint U S154 consolidation) |
| **UC1-General DocRecognizer** | **production-usable** — recognize endpoint produces populated `extracted_fields` (SW-1 wired the real PromptWorkflow extraction); 5 doctypes; rule engine 100% top-1 on starter corpus |
| **Multi-tenant column model** | `tenant_id` only on `rag_collections` (Alembic 049 dropped `customer`); other domains (`skill_instances` / `intent_schemas` / `document_extractor`) still on `customer` |
| **Prod-readiness guards** | `AIFLOW_ENVIRONMENT=prod` boot guard refuses Vault root tokens (SW-4); AppRole runbook published |
| **Routing trace** | none — emails are processed but operators cannot see why a doctype was picked or which extraction path ran |

## Sprint W trajectory recap — what shipped vs. what didn't

**Shipped:** SW-1 (SV-FU-4 extraction wire-up) · SW-2 (SV-FU-3 + SR-FU-4 live Playwright) · SW-3 (SS-FU-1 + SS-FU-5 `customer` rename + Alembic 049) · SW-4 (SM-FU-2 + SR-FU-6 + SU-FU-1 prod guard + Langfuse listing surface + script `--output`).

**Did not ship (Sprint X+ inventory):** SW-FU-1 Langfuse SDK (blocked upstream) · SW-FU-2 admin UI source-toggle widget · SW-FU-3 audit script extension · SW-FU-4 Vault AppRole IaC E2E · SW-FU-5 real-document corpus (operator-driven).

## The pipeline gap Sprint W exposes

Sprint W wired DocRecognizer extraction. UC3 (Sprint P) classifies emails. UC2 (Sprint J) answers questions over RAG. **These three skills do not yet form a pipeline.**

Concretely:
1. **UC3 EXTRACT path is hardcoded.** Sprint Q S135's `_maybe_extract_invoice_fields` calls `invoice_processor.workflows.process` directly. It does not consult DocRecognizer to decide whether the attachment is an invoice, an ID card, a contract, or a passport. Every EXTRACT email is treated as `hu_invoice` regardless of content.
2. **No routing trace.** When an email lands and produces extracted fields, there is no operator-visible record of *why* a doctype was picked, *which* extraction path ran, *whether* the rule engine matched or fell through to LLM fallback. Operators debug by reading logs.
3. **RAG chat is a stateless API.** `/aszf/chat` accepts a question, returns an answer with citations, forgets the turn. No conversation persistence, no per-tenant collection picker in the UI, no persona switcher in the UI, no cost meter per turn, no transcript export. Operators cannot offer this as a polished customer-facing chat surface.

The Sprint W deliverables are individually production-ready. As a pipeline, they are unwired.

## Cumulative test deltas since v1.6.0 (Sprint V close → Sprint W close)

| Suite | v1.6.0 | v1.7.0 | Delta |
|---|---|---|---|
| unit | 2606 | 2641 | **+35** |
| integration alembic | 50 | 51 | +1 (049 round-trip) |
| live Playwright (markdown specs) | 6 | 8 | +2 (`document-recognizer.md`, `prompt-workflows.md`) |
| operator scripts on uniform `--output` | 3 | 5 | +2 (full coverage) |
| Alembic head | 048 | 049 | +1 |
| endpoints / routers / UI pages | 201 / 32 / 27 | 201 / 32 / 27 | unchanged |

## Capability cohort delta — cumulative

| Cohort | v1.5.0 (Sprint Q) baseline | v1.7.0 (Sprint W close) |
|---|---|---|
| UC1 invoice extraction (byte-stable golden path) | 85.7% accuracy on 10-fixture corpus | unchanged |
| UC2 RAG retrieval | NULL-fallback, single profile | NULL-fallback + Profile A (BGE-M3 1024-dim) + Profile B surrogate |
| UC3 email intent classifier | 4% misclass on 25-fixture corpus | unchanged; EXTRACT hardcoded to `invoice_processor` |
| UC4 cost guardrails | reactive cap (S112) | reactive + per-step preflight + per-tenant budgets + cost umbrella |
| DocRecognizer | n/a (introduced Sprint V) | classifier + **PromptWorkflow-driven extraction** for hu_invoice + hu_id_card |
| Multi-tenant model | `customer` + `tenant_id` (parallel) on rag_collections | `tenant_id` only on rag_collections |
| Live Playwright UI specs | 4 | 8 |

## Audit topics — scope, risk, effort, SLO

### TOP PRIORITY

#### 1. UC3 → DocRecognizer routing layer (NEW, addresses pipeline gap §1)

**Scope.** Replace the Sprint Q hardcoded `invoice_processor` call with a DocRecognizer-mediated dispatch:
- UC3 detects EXTRACT intent (Sprint P)
- For each EXTRACT email, run DocRecognizer.classify on every attachment
- Dispatch by detected doctype: `hu_invoice` → existing `invoice_processor` (byte-stable); other doctypes → DocRecognizer's `PromptWorkflowExecutor` extraction (SW-1); unrecognized → existing rag_ingest fallback
- Default-off behind `AIFLOW_UC3_DOC_RECOGNIZER_ROUTING__ENABLED=false` so flag-off path is byte-identical to Sprint W

**Why now.** Sprint W wired DocRecognizer extraction. Without this routing layer, the only way to use it is via the `/api/v1/document-recognizer/recognize` admin endpoint. The actual production EXTRACT path (UC3 email orchestrator) cannot route to it. Sprint X turns DocRecognizer from "shipped" to "consumed".

**What changes if we ship.**
- An EXTRACT email with an ID card attachment produces extracted fields via DocRecognizer (not silently misrouted to invoice_processor and failing)
- An EXTRACT email with a passport / address card / contract attachment likewise routes correctly
- UC1 invoice_processor remains the byte-stable handler for `hu_invoice` (no behaviour change)

**What changes if we defer.** DocRecognizer remains an admin-only feature; production email flow can only handle invoices.

**Effort:** 1 session (~250 LOC + 12 unit + 2 integration). Risk class: medium (changes UC3 EXTRACT path; mitigated by flag-off default + UC1 byte-stable gate).

**SLO:** UC3 4/4 unchanged on flag-off; on flag-on, UC1 invoice 4/4 unchanged (hu_invoice routes to existing invoice_processor) AND a new id_card test fixture extracts ≥ 3 fields with confidence ≥ 0.7.

---

#### 2. Routing trace audit table + admin UI panel (NEW, addresses pipeline gap §2)

**Scope.** Per-email routing audit trail:
- Alembic 050 — `routing_runs` table (UUID PK, `email_id` FK, `intent_class`, `doctype_detected`, `doctype_confidence`, `extraction_path` enum {`invoice_processor` | `doc_recognizer_workflow` | `rag_ingest_fallback`}, `extraction_outcome` enum {`success` | `partial` | `failed` | `refused_cost`}, `cost_usd`, `latency_ms`, `created_at`)
- `RoutingRunRepository` write at every UC3 EXTRACT decision point (4 call sites; each writes a `routing_runs` row before returning)
- 3-route admin API at `/api/v1/routing-runs` (GET list with filters, GET detail, GET aggregate-stats)
- Admin UI page `/routing-runs` — table + detail drawer; filter by intent_class / doctype / outcome / time window; per-row "View original email" deep-link

**Why now.** Without observability into routing decisions, SX-2's flag-on rollout is operating blind. Operators need to see "this email chose hu_invoice with confidence 0.92 and ran invoice_processor in 1.2s for $0.0004" before they trust the new routing layer. Ships in the same sprint as SX-2 so the rollout has telemetry from day one.

**Effort:** 1 session (~400 LOC: Alembic + repository + 3-route router + UI page + locale + 12 unit + 3 integration). Risk class: low (purely additive; reads are observation-only).

**SLO:** Every UC3 EXTRACT email post-SX-3 produces exactly one `routing_runs` row; admin UI lists rows with sub-second filter responsiveness on a 1000-row seed.

---

#### 3. Professional RAG chat management (NEW, addresses pipeline gap §3)

**Scope.** Turn `/aszf/chat` from a stateless API into a polished customer-facing surface:
- Alembic 051 — `aszf_conversations` table (UUID PK, `tenant_id`, `created_by`, `persona`, `collection_name`, `created_at`, `updated_at`, `title` nullable) + `aszf_conversation_turns` table (UUID PK, `conversation_id` FK, `turn_index`, `role` enum {`user` | `assistant`}, `content`, `citations` JSONB, `cost_usd`, `latency_ms`, `created_at`)
- `ConversationService` — create / list / get / append-turn / delete; tenant-scoped
- 4-route API at `/api/v1/conversations` (GET list, POST create, GET detail with turns, POST `/{id}/turns` to append)
- Admin UI page `/aszf/chat` upgrade — conversation history sidebar (left), turn stream (center), persona switcher visible (top, baseline / expert / mentor segmented control), per-tenant collection picker (top), citation card per assistant turn (clickable source attribution), cost meter (per-turn USD, per-conversation total), transcript export (JSON / markdown)

**Why now.** UC2 has shipped retrieval quality (Sprint J MRR@5 ≥ 0.55) and persona descriptors (Sprint S/T/U). The user-facing surface lags behind: every chat session forgets prior turns, persona switching requires API calls, cost is invisible. Sprint X promotes the RAG surface from "demo" to "professional".

**Effort:** 1 session (~500 LOC: Alembic + service + 4-route router + UI page upgrade + locale + 15 unit + 3 integration + 1 live Playwright). Risk class: low-medium (UI surface changes; mitigated by additive routes — existing `/api/v1/aszf/chat` retrieval API stays byte-stable; conversation persistence is opt-in for the admin UI).

**SLO:** UC2 MRR@5 ≥ 0.55 unchanged on existing chat retrieval API; admin UI conversation persists across page reload (turn count + content match); persona switcher round-trip selects the corresponding persona descriptor; citation cards link to source documents in the live RAG collection.

---

#### 4. Sprint W follow-ups bundled (lower priority but cheap)

**Scope.** SW-FU-2 (admin UI source-toggle on `/prompts/workflows`) + SW-FU-3 (audit script extension to `skill_instances` / `intent_schemas` / `document_extractor`).

**Why now.** Both are < 0.5 session each. Bundle them into the close session so Sprint X doesn't accumulate Sprint W follow-up debt while shipping new capability.

**Effort:** 0.5 session combined. Risk class: low.

**SLO:** Toggle renders + URL-persists; audit script reports per-domain counts in `--strict` mode.

---

### MEDIUM PRIORITY (deferred to Sprint Y unless trivially in-scope)

| ID | Topic | Reason for deferral |
|----|-------|---------------------|
| SW-FU-1 | Langfuse v4 SDK helper | Blocked on upstream SDK release |
| SW-FU-4 | Vault AppRole IaC E2E test | Infrastructure sprint candidate |
| SW-FU-5 / SV-FU-1 | DocRecognizer real-document corpus | Operator-driven anonymization |
| SV-FU-2 | UI bundle CI guardrail | Polish; bundle still small |
| SV-FU-5 | Monaco editor for doctype YAML | Polish; textarea works |

### DEFERRED (Sprint Y or later)

- Coverage uplift 70% → 80% (SJ-FU-7) — dedicated cross-cutting sprint
- Vault rotation E2E + Langfuse v3→v4 — infrastructure sprint
- UC3 thread-aware classifier (SP-FU-3) — architecture sprint
- DocRecognizer ML classifier — gated on real-document corpus signal
- Skill multi-tenancy cleanup (`skill_instances.customer`) — gated on SX audit publishing the backlog
- Grafana cost panels (SN-FU-3) — observability sprint
- UC1 corpus extension to 25 fixtures (SQ-FU-3) — operator curation
- UC1 `invoice_date` SQL column rename (SU-FU-3)
- `scripts/` ruff cleanup (SU-FU-2)

## Recommended Sprint X shape

5 sessions, ~1.5 calendar days target (this is a capability sprint, larger than Sprint W's polish-only run):

| Session | Topic | Effort | Risk | UC golden-path gate |
|---------|-------|--------|------|---------------------|
| **SX-1** | Post-Sprint-W audit + Sprint X kickoff plan publish | 0.5 | low | n/a (planning) |
| **SX-2** | UC3 → DocRecognizer routing layer (intent EXTRACT → DocRecognizer.classify → per-doctype dispatch) | 1.0 | medium | UC3 4/4 unchanged on flag-off; UC1 4/4 unchanged on flag-on (hu_invoice path) |
| **SX-3** | Routing trace `routing_runs` Alembic 050 + 3-route API + `/routing-runs` admin UI page | 1.0 | low | UC3 4/4 + UC1 4/4 unchanged (observation-only writes) |
| **SX-4** | Professional RAG chat management — conversation persistence Alembic 051 + 4-route API + `/aszf/chat` UI upgrade | 1.0 | low-medium | UC2 MRR@5 ≥ 0.55 unchanged on existing retrieval API |
| **SX-5** | Sprint X close + bundled Sprint W follow-ups (SW-FU-2 toggle widget + SW-FU-3 audit extension) + retro + tag `v1.8.0` | 0.5 | low | n/a (close) |

**Sprint X close target tag:** `v1.8.0` (minor — new capability cohorts: UC3 doc-aware routing + routing trace + RAG chat conversation persistence).

**Total expected deltas:**
- ~+50 unit (routing layer × 12 + trace × 12 + chat × 15 + toggle × 4 + audit × 3 + buffer)
- ~+8 integration (alembic 050 + 051 round-trip × 2 + routing-runs API × 3 + conversations API × 3)
- +7 endpoints (3 routing-runs + 4 conversations) → 201 → 208
- +2 routers → 32 → 34
- +1 UI page (`/routing-runs`) + 1 UI page upgrade (`/aszf/chat`) → 27 → 28
- +2 Alembic migrations (050 routing_runs, 051 conversations) → head 049 → 051
- +1 PromptWorkflow descriptor possibility (only if SX-2 introduces a doctype handler the existing 6 don't cover; default no)
- +2 live Playwright spec updates (`/aszf/chat` upgrade, `/routing-runs` new spec)

## Operator decision points

1. **SX-2 default-on vs. default-off rollout.** Recommendation: default-off (`AIFLOW_UC3_DOC_RECOGNIZER_ROUTING__ENABLED=false`) for v1.8.0; flip default-on in v1.8.1 after one calendar week of routing trace observation. Mirrors Sprint Q UC3-extraction pattern.
2. **SX-4 conversation persistence retention.** New `aszf_conversation_turns` table will grow per chat turn. Recommendation: ship without TTL in v1.8.0; add a `conversations:retention_days` knob in v1.8.1 once operators have feedback on conversation lifetimes.
3. **SX-5 bundling.** SW-FU-2 + SW-FU-3 are cheap close-session additions. If SX-2/SX-3/SX-4 burn long, drop the follow-up bundle from SX-5; they re-queue for Sprint Y.
4. **Tag bump.** `v1.8.0` (minor) reflects new capability cohorts. If operator prefers conservative versioning, `v1.7.1` is acceptable but understates the routing + persistence additions.

## STOP conditions if Sprint X is delayed

**HARD:**
- None time-sensitive at the project level. The pipeline gap is real but not externally pressured.

**SOFT:**
- If Sprint X is delayed > 2 calendar weeks past Sprint W close, re-audit before kickoff — operator priorities may have shifted toward infrastructure or coverage.

## Out of scope for Sprint X

- Coverage uplift 70%→80% (SJ-FU-7)
- Vault rotation E2E + Langfuse v3→v4
- UC3 thread-aware classifier (SP-FU-3)
- DocRecognizer ML classifier
- `skill_instances.customer` rename + Alembic 052+
- Grafana cost panels (SN-FU-3)
- UC1 corpus extension to 25 fixtures (SQ-FU-3)
- UI bundle CI guardrail (SV-FU-2)
- Monaco editor (SV-FU-5)

These accumulate as the Sprint Y+ inventory.
