# Post-Sprint-V Audit — operator-facing summary

> **Date:** 2026-04-26
> **Trigger:** Sprint V SV-5 close PR #54 merged on `main` (commit `ee3f5ff`); v1.6.0 tag queued.
> **Audit reference:** `01_PLAN/119_SPRINT_V_DOCUMENT_RECOGNIZER_PLAN.md` §9 + `01_PLAN/AUDIT_2026_04_26_SPRINT_V_DIRECTION.md` §"Post-Sprint-V audit gate".
> **Output:** Sprint W kickoff plan at `01_PLAN/120_SPRINT_W_KICKOFF_PLAN.md`.

## State of the project (post Sprint V)

| Layer | Status |
|-------|--------|
| **UC1 invoice extraction** | byte-stable (Sprint Q `issue_date` polish merged S156); `invoice_processor` workflow unchanged in Sprint V |
| **UC2 RAG chat** | byte-stable; baseline persona on workflow shim, expert + mentor on workflow shim (S150 + S155) |
| **UC3 email intent** | byte-stable (4% misclass since Sprint P) |
| **UC4 monitoring + cost** | per-tenant budgets + preflight guardrail (Sprint N + Sprint U S154 consolidation) |
| **UC1-General DocRecognizer** | shipped Sprint V; 5 doctypes; rule engine 100% top-1 on starter corpus |
| **Default-off rollout** | preserved on every flag (`AIFLOW_PROMPT_WORKFLOWS__*`, `AIFLOW_COST_GUARDRAIL__*`, `AIFLOW_DOCLING_WARMUP`, doc_recognizer's `pii_redaction` per descriptor) |
| **CI gates** | 5 ci.yml jobs (lint+test, admin-build, openapi-drift, integration-1024-dim, doc-recognizer-accuracy) + 6 nightly jobs |
| **Pre-commit hooks** | 1 (vite build via `make install-hooks`) |
| **Coverage** | ~70% local; SJ-FU-7 trajectory 70%→80% still dormant |

## Audit topics — scope, risk, effort, SLO

### TOP PRIORITY

#### 1. SV-FU-4 — Real PromptWorkflow extraction wire-up

**Scope.** SV-2 shipped the orchestrator that returns an EMPTY `DocExtractionResult` after classification. The `recognize_and_extract` orchestrator's stage-3 (extraction) needs to invoke the resolved per-doctype PromptWorkflow descriptor (`invoice_extraction_chain` for `hu_invoice`, `id_card_extraction_chain` for `hu_id_card`, etc.) via `PromptWorkflowExecutor` + execute the LLM calls + map results into `DocFieldValue` entries.

**Why now.** Without this, the recognize endpoint produces a doc-type match + intent decision but **zero extracted fields**. Operators cannot use the doc_recognizer for anything beyond classification. This is the single biggest blocker on the path from "Sprint V shipped" to "production-usable".

**What changes if we ship.**
- `recognize_and_extract` returns populated `DocExtractionResult.extracted_fields`
- Per-step cost ceilings enforced via Sprint U S154 `CostPreflightGuardrail.check_step()`
- Real-LLM integration test on `hu_invoice` + `hu_id_card` fixtures (skip-by-default behind `OPENAI_API_KEY`)
- Operator can run the doc_recognizer end-to-end on real documents

**What changes if we defer.**
- Doc_recognizer remains a classifier-only tool
- Operators stuck on `invoice_processor` for invoice extraction; can't reuse the generic skill for ID cards / passports / contracts
- The 5 doctype descriptors plus `id_card_extraction_chain` PromptWorkflow descriptor become "documentation-only"

**Effort:** 1 session (~400-500 LOC + ~12 unit + 2 integration tests). Risk class: medium (LLM cost + parsing edge cases).

**SLO:** UC1 invoice_processor unchanged byte-for-byte; doc_recognizer + `hu_invoice` produces invoice_number + total_gross fields with confidence ≥ 0.7 on the 2 starter `hu_invoice` fixtures (real OpenAI gpt-4o-mini call).

---

#### 2. SV-FU-3 — Live Playwright `/document-recognizer` spec

**Scope.** `tests/ui-live/document-recognizer.md` (Python Playwright on the live admin stack). Mirror the Sprint N S123 `/budget-management` pattern. 3 tests: list 5 doctypes / drag-drop file → recognize / per-tenant override save → re-recognize uses override.

**Why now.** The SV-4 admin UI ships untested in CI. The S153 `vite build` pre-commit hook catches type errors but not user-flow breakage. A live spec gives a safety net for SW-1 (which touches the recognize endpoint).

**Effort:** 0.5 session (~150 LOC Playwright spec + fixture seed). Risk: low (additive test, no production code change).

**SLO:** `bash scripts/start_stack.sh --full` + `pytest tests/ui-live/document-recognizer.md` PASS on a clean dev stack.

---

#### 3. SS-FU-1 / SS-FU-5 — `customer` → `tenant_id` rename

**Scope.** Sprint S half-migrated to multi-tenant; the `rag_collections.customer` column still exists alongside `tenant_id`. SS-FU-1 = service code rename (caller-facing), SS-FU-5 = Alembic 049 column drop. Cross-cutting refactor.

**Why now.** Three sprints have shipped on top of the half-migration (S, T, V). Every new feature has to consider whether it should write `customer` or `tenant_id`. The doc_recognizer wrote `tenant_id` cleanly; the next refactor sprint will be cleaner if `customer` is gone.

**Effort:** 1.5 sessions (~300 LOC + Alembic 049 + ~10 unit tests). Risk class: medium (DB schema change with backward-compat shim).

**SLO:** Zero references to `customer` column in `src/aiflow/`; Alembic 049 round-trip clean; UC2 RAG MRR@5 unchanged.

---

#### 4. SM-FU-2 — `AIFLOW_ENV=prod` boot guard + AppRole IaC

**Scope.** Refuse Vault root tokens at boot when `AIFLOW_ENV=prod`. Prod operators must use AppRole. Plus an example IaC snippet (Terraform / Vault CLI) for AppRole role/secret_id provisioning.

**Why now.** Sprint M shipped Vault dev integration; production deployment story is incomplete. Adding `AIFLOW_ENV` checks before any prod-shipping gate is cheap insurance.

**Effort:** 0.5 session (~80 LOC + 1 integration test). Risk: low (boot-time check; default off on dev).

**SLO:** Boot fails with clear error when `AIFLOW_ENV=prod` + root token detected; AppRole-based boot succeeds.

---

### MEDIUM PRIORITY

#### 5. SV-FU-1 — Real-document fixture corpus extension

**Scope.** Replace synthetic `.txt` fixtures with anonymized real PDFs/scans. 5 per doctype × 5 = 25 files. Extends the `data/fixtures/doc_recognizer/<doctype>/` corpus.

**Why now.** Synthetic fixtures score 100% trivially (same words as the rule engine pattern). Real OCR'd PDFs / scans expose real classifier weaknesses.

**Effort:** 1 session **operator-driven** (anonymization is operator work). The session itself is a measurement run + corpus update.

**SLO:** All 5 doctypes still meet their per-doctype SLO on the real corpus (hu_invoice ≥90%, hu_id_card ≥80%, pdf_contract ≥80%, hu_address_card ≥70%, eu_passport ≥70%).

---

#### 6. SU-FU-1 — Operator-script `--output` migration (3 of 5 done; 2 remaining)

**Scope.** Migrate `measure_uc1_golden_path.py` + `run_nightly_rag_metrics.py` to use the S156 `argparse_output()` helper. Already migrated: `audit_cost_recording.py` (S156) + `measure_doc_recognizer_accuracy.py` (SV-5).

**Effort:** 0.25 session (~50 LOC per script + 4 unit tests).

**SLO:** Both scripts emit `--output {text,json,jsonl}` consistently.

---

#### 7. SR-FU-4 / SR-FU-6 — Live Playwright `/prompts/workflows` + Langfuse listing

**Scope.** SR-FU-4 = live Playwright spec for `/prompts/workflows` admin page. SR-FU-6 = `LangfuseClient.list_workflow_prompts()` + admin UI source-toggle (Langfuse vs local YAML). Both deferred from Sprint U S155 rescope.

**Effort:** 0.5 session each. Total 1 session if bundled.

**SLO:** Live Playwright PASS on `/prompts/workflows`; admin UI shows Langfuse-typed prompts when `AIFLOW_LANGFUSE__ENABLED=true`.

---

### DEFERRED (Sprint X or later)

| ID | Topic | Reason |
|----|-------|--------|
| SU-FU-2 | `scripts/` ruff cleanup (7 files) | Pure code hygiene; no functional impact |
| SU-FU-3 | Alembic `invoice_date` SQL column rename | DocRecognizer doesn't depend on it; UC1 byte-stable preserves the legacy name |
| SU-FU-4 | UC1 full-corpus `issue_date` ≥ 90% verification | Operator-driven measurement run; can be triggered ad-hoc |
| SV-FU-2 | UI bundle size guardrail in pre-commit hook | Bundle hasn't grown alarmingly; no urgency |
| SV-FU-5 | Monaco YAML editor for DocTypeDetailDrawer | Wait for operator feedback on textarea ergonomics |
| SJ-FU-7 | Coverage uplift 70% → 80% | Cross-cutting; better as a Sprint X dedicated coverage sprint |
| SS-SKIP-2 | Profile B Azure live MRR@5 | Azure credit pending |
| SP-FU-1 | UC3 `024_complaint_about_invoice` body-vs-attachment | Intractable 1/25 conflict; needs UI escalation flow |
| SP-FU-3 | UC3 thread-aware classifier | Architecture change; better as dedicated sprint |
| Cost panels | Grafana panels for cost_guardrail_refused, etc. | Observability sprint |
| Vault rotation E2E | Live token rotation E2E test | Infrastructure sprint |
| Langfuse v3→v4 | Server upgrade | Infrastructure sprint |

## Recommended Sprint W shape

5 sessions, ~1.5 weeks:

| Session | Topic | Effort | Risk |
|---------|-------|--------|------|
| **SW-1** | SV-FU-4 — Real PromptWorkflow extraction wire-up | 1.0 | medium |
| **SW-2** | SV-FU-3 — Live Playwright `/document-recognizer` + SR-FU-4 — Live Playwright `/prompts/workflows` (bundle 2 specs together) | 1.0 | low |
| **SW-3** | SS-FU-1 — `customer` → `tenant_id` service code rename + Alembic 049 deprecation column | 1.0 | medium |
| **SW-4** | SM-FU-2 — `AIFLOW_ENV=prod` boot guard + SR-FU-6 Langfuse listing surface + SU-FU-1 operator-script `--output` migration (the 2 remaining) | 1.0 | low |
| **SW-5** | Sprint W close — retro + PR description + tag `v1.7.0` + NEXT.md | 0.5 | low |

Sprint W close target tag: `v1.7.0`.

## Operator decision points

1. **SW-1 vs SW-3 ordering.** SW-1 (extraction wire-up) unblocks customer-facing usage; SW-3 (`customer` rename) reduces refactor friction for everything after. Recommendation: SW-1 first (faster customer impact).
2. **Real-document fixtures (SV-FU-1).** Operator-driven, blocks on anonymized real PDFs/scans being available. If they're ready, slot as SW-2 alongside the Playwright work; if not, defer to Sprint X.
3. **Profile B Azure live (SS-SKIP-2).** Out of operator hands until Azure credit lands. Auto-pulled into the next sprint if credit lands mid-W.

## Out of scope for Sprint W

- Coverage uplift 70%→80% (SJ-FU-7) — needs a dedicated cross-cutting sprint
- UI Monaco editor (SV-FU-5) — wait for operator feedback
- Vault rotation E2E + Langfuse v3→v4 — infrastructure sprint
- UC3 thread-aware classifier (SP-FU-3) — architecture sprint
- Doc_recognizer ML classifier — only if SV-FU-1 reveals rule-engine inadequacy

These accumulate as the Sprint X+ inventory.
