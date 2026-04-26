# Sprint W (v1.7.0) — production-readiness + multi-tenant cleanup

> **Tag:** `v1.7.0` (queued post-merge)
> **Predecessor:** v1.6.0 Sprint V (Generic Document Recognizer)
> **Branches squash-merged:** `feature/w-sw1-prompt-workflow-extraction` (PR #56),
> `feature/w-sw2-live-playwright` (PR #57),
> `feature/w-sw3-tenant-id-rename` (PR #58),
> `feature/w-sw4-prod-guard-langfuse-listing` (PR #59),
> `feature/w-sw5-sprint-close` (this PR).

## TL;DR

Sprint W ships **5 sessions in 1 day**:

* **SW-1** wires real PromptWorkflow extraction into the Sprint V
  `DocumentRecognizerOrchestrator`. The recognize endpoint now produces
  populated `extracted_fields` for `hu_invoice` + `hu_id_card` (closes
  SV-FU-4).
* **SW-2** ships markdown live-Playwright journeys for
  `/document-recognizer` + `/prompts/workflows` (closes SV-FU-3 + SR-FU-4).
* **SW-3** finishes the long-deferred `customer` → `tenant_id` rename:
  Alembic 049 drops the column, the rag_engine service uses `tenant_id`
  end-to-end, and `scripts/audit_customer_references.py` enforces it
  in CI (closes SS-FU-1 / SS-FU-5).
* **SW-4** lands `AIFLOW_ENVIRONMENT=prod` boot guard refusing Vault
  root tokens, a Langfuse workflow listing surface stub, and the final
  2 operator scripts on the uniform `--output` flag (closes SM-FU-2 +
  SR-FU-6 + SU-FU-1).
* **SW-5** (this PR) — retro + PR description + CLAUDE.md banner +
  `tag v1.7.0` queued.

UC1 invoice_processor remains byte-stable. UC2 RAG retrieval unchanged
(query path was already on `tenant_id` since Sprint S S143). UC3 email
intent untouched.

## Test deltas

* **Unit:** 2606 → 2641 (+35)
* **Integration alembic:** 50 → 51 (+1)
* **Live Playwright (markdown):** 6 → 8 (+2)
* **Endpoints / routers / UI pages:** unchanged (201 / 32 / 27)
* **Alembic head:** 048 → **049**
* **Operator scripts on `argparse_output`:** 3 → **5**

## What changed at the boundary

* **API:** `/api/v1/prompts/workflows` accepts a new `?source={local,langfuse,both}`
  query param. The response shape is unchanged.
* **DB:** `rag_collections.customer` column dropped. `idx_rag_collections_customer`
  dropped. `tenant_id` (server default `'default'`) is the sole tenant
  scope key.
* **Boot:** `AIFLOW_ENVIRONMENT=prod` + dev/root Vault token refuses
  start. Bypass via `AIFLOW_VAULT__ALLOW_ROOT_TOKEN_IN_PROD=true`
  (audit-logged WARN every boot).
* **Operator scripts:** `measure_uc1_golden_path.py` +
  `run_nightly_rag_metrics.py` adopt `argparse_output()`. The
  `--output` flag accepts `text`, `json`, `jsonl`. All 5 operator
  scripts now uniform.

## Risk register status

* **R1** (LLM cost amplification): mitigated by per-step
  `CostPreflightGuardrail.check_step()` + descriptor-tunable
  `cost_ceiling_usd` ✅
* **R2** (UC1 byte-stable regression): mitigated by reusing
  `invoice_extraction_chain` for `hu_invoice` ✅
* **R3** (SV-FU-1 fixture anonymization timeline): not addressed in
  Sprint W; carried as SW-FU-5
* **R4** (pre-S API consumer breakage on rename): n/a — API never
  exposed `customer` ✅
* **R5** (`AIFLOW_ENV=prod` false-positive): mitigated by bypass env
  + `hvs.CAES` AppRole positive signal ✅
* **R6** (scope creep into SW-5): SW-5 stayed close-only ✅

## STOP conditions — none triggered

* UC1 invoice_processor golden-path: byte-stable
* UC2 MRR@5: unchanged (no query path touched)
* UC3 misclass: unchanged
* Alembic 049 pre-flight: dev DB clean (0 rows with `customer != tenant_id`)
* Boot guard test: violation triggers correctly; bypass path documented
* Live Playwright specs: operator-runnable on clean dev stack

## Out of scope (carried to Sprint X+)

* Coverage uplift 70% → 80% (SJ-FU-7) — dedicated cross-cutting sprint
* UI Monaco editor (SV-FU-5) — operator feedback first
* Vault rotation E2E + Langfuse v3→v4 — infrastructure sprint
* UC3 thread-aware classifier (SP-FU-3) — architecture sprint
* DocRecognizer ML classifier — only if SW-2 corpus reveals rule-engine inadequacy
* Grafana cost panels (SN-FU-3) — observability sprint
* UC1 corpus extension to 25 fixtures (SQ-FU-3) — operator curation
* DocRecognizer real-document corpus (SV-FU-1 carry, now SW-FU-5)
* Langfuse v4 list-by-prefix SDK helper (SW-FU-1)
* Admin UI source-toggle widget (SW-FU-2)
* `audit_customer_references` extension (SW-FU-3)
* Vault AppRole IaC end-to-end test (SW-FU-4)

## See also

* `docs/sprint_w_retro.md` — full retrospective (decisions log, what
  worked / what hurt, follow-ups)
* `01_PLAN/120_SPRINT_W_KICKOFF_PLAN.md` — Sprint W scope plan
* `docs/runbooks/vault_approle_iac.md` — SW-4 AppRole runbook
