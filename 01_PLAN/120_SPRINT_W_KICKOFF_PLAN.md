# AIFlow v1.7.0 Sprint W — DocRecognizer extraction + multi-tenant cleanup + UI live tests

> **Status:** PUBLISHED 2026-04-26 by post-Sprint-V audit session.
> **Branch convention:** `feature/w-sw{N}-*` (each session its own branch → PR → squash-merge).
> **Parent docs:**
> - `docs/post_sprint_v_audit.md` — operator-facing audit (SOURCE)
> - `docs/sprint_v_retro.md` — Sprint V follow-ups SV-FU-1..6
> **Predecessor:** v1.6.0 Sprint V (Generic Document Recognizer, MERGED)
> **Target tag (post-merge):** `v1.7.0`

---

## 1. Goal

Sprint W ships **production-readiness + multi-tenant cleanup** on top of the Sprint V doc_recognizer. The headline deliverable is **SV-FU-4** — wire the real PromptWorkflow extraction step into `recognize_and_extract` so the recognize endpoint produces fields, not just a doc-type match. After SW-1, operators can run the doc_recognizer end-to-end on real documents.

Beyond that, Sprint W cleans up two long-standing debts:
- **`customer` → `tenant_id`** model rename (SS-FU-1/5) — Sprint S half-migrated; Sprint W finishes
- **`AIFLOW_ENV=prod` boot guard** (SM-FU-2) — refuse Vault root tokens at boot in prod

Plus two safety-net additions:
- **Live Playwright spec** for `/document-recognizer` (SV-FU-3) + bundled with `/prompts/workflows` (SR-FU-4 carry from Sprint U)
- **Langfuse workflow listing surface** (SR-FU-6) + operator script `--output` migration completion (SU-FU-1)

### Capability cohort delta

| Cohort | Sprint V close | Sprint W close (target) |
|---|---|---|
| DocRecognizer extraction | classifier-only (empty fields) | **PromptWorkflow-driven extraction** for hu_invoice + hu_id_card |
| Live Playwright UI specs | `/budget-management`, `/extracted-fields`, `/rag/collections` | **+ `/document-recognizer`, + `/prompts/workflows`** |
| Multi-tenant column model | `customer` + `tenant_id` (parallel) | **`tenant_id` only** (Alembic 049 drops `customer`) |
| Prod-readiness guards | none | **`AIFLOW_ENV=prod` boot refuses Vault root tokens** |
| Langfuse-typed prompts visible in UI | local YAML only | **+ Langfuse listing** (admin UI source-toggle) |
| Operator scripts on uniform `--output` | 2 of 5 | **5 of 5** (SU-FU-1 closed) |
| Alembic head | 048 | 049 (`customer` column drop) |
| New endpoints / UI pages | — | 0 / 0 |

---

## 2. Sessions

### SW-1 — Real PromptWorkflow extraction wire-up (SV-FU-4)
**Scope.** The unblocker for production usage. SV-2 shipped the orchestrator that returns an EMPTY `DocExtractionResult` after classification; SW-1 wires the real LLM-driven extraction step.

1. **Extend `DocumentRecognizerOrchestrator.run()`** — after the classifier match, resolve the descriptor's `extraction.workflow` via `PromptWorkflowExecutor.resolve_for_skill("document_recognizer", descriptor.extraction.workflow)`.
2. **Per-step LLM invocation** — for each resolved `(step_id, prompt_def)`, build the input dict (parsed text + per-field schema), invoke the LLM (`models_client.generate(...)`), capture cost.
3. **Per-step cost preflight** — wire `CostPreflightGuardrail.check_step(step_name, model, input_tokens, max_output_tokens, ceiling_usd)` (Sprint U S154 API) using the descriptor step's `metadata.cost_ceiling_usd`. On `allowed=False` → raise `CostGuardrailRefused` (Sprint T S149 pattern).
4. **Field mapping** — parse the LLM JSON response, extract per-field values + confidences, build `dict[str, DocFieldValue]` according to the descriptor's `extraction.fields` schema. Apply field validators (regex, iso_date, money currency, enum) — failures produce `validation_warnings`, not crashes.
5. **Backward-compat for hu_invoice** — when descriptor is `hu_invoice`, the executor delegates to the existing `invoice_extraction_chain` workflow (Sprint T S149); UC1 invoice_processor's golden path stays byte-stable. The doc_recognizer becomes an alternative entry point that produces the same shape.
6. **Validators** — implement the 7 validator functions referenced by the doctype descriptors: `non_empty`, `regex:<pattern>`, `iso_date`, `before_today`, `after_today`, `min:N`, `max:N` — pure-Python in `src/aiflow/services/document_recognizer/validators.py`.

**Gate.**
- `hu_invoice` doctype on the 2 starter `.txt` fixtures: `invoice_number` + `total_gross` extracted with confidence ≥ 0.7 (real OpenAI gpt-4o-mini call, integration test skip-by-default behind `OPENAI_API_KEY`)
- `hu_id_card` doctype on the 2 starter `.txt` fixtures: `id_number` + `full_name` + `birth_date` extracted (real OpenAI integration test)
- UC1 `invoice_processor` golden-path slice (`tests/integration/skills/test_uc1_golden_path.py`) byte-stable: ≥ 75% / `invoice_number` ≥ 90% (regression check)
- UC2 MRR@5 ≥ 0.55 + UC3 4/4 unchanged
- Per-step `cost_ceiling_usd` enforcement: `id_card_extraction_chain.fields` step's 0.02 USD ceiling refuses an artificially-inflated test prompt (deterministic test, no real LLM call)

**Expected diff.** ~500 LOC across `services/document_recognizer/orchestrator.py` (extraction stage), `services/document_recognizer/validators.py` (new), `services/document_recognizer/orchestrator.py` (LLM client wiring). **+12 unit (validators × 7 + extraction stage shape × 5) + 2 integration (real OpenAI per doctype, skip-by-default behind `OPENAI_API_KEY`)**.

**Risk.** R1 — LLM cost amplification (mitigated by `check_step()` per-step gate); R2 — UC1 byte-stable regression (mitigated by reusing Sprint T `invoice_extraction_chain` for `hu_invoice`).

### SW-2 — Live Playwright specs + corpus extension (SV-FU-3 + SV-FU-1 optional + SR-FU-4)
**Scope.** Two live UI specs + corpus extension if operator-curated content is ready.

1. **`tests/ui-live/document-recognizer.md`** — Python Playwright spec on the live admin stack (mirror Sprint N S123 `/budget-management` pattern). 3 tests:
   - Test 1: navigate to `/document-recognizer`, list shows 5 bootstrap doctypes
   - Test 2: drag-drop `data/fixtures/doc_recognizer/hu_invoice/inv_001_simple.txt` → recognize → result panel shows extracted fields (post-SW-1)
   - Test 3: click "Override for tenant" on `hu_invoice` → edit YAML (change a regex weight) → save → refresh list → "Tenant override" badge appears
2. **`tests/ui-live/prompt-workflows.md`** (SR-FU-4 from Sprint U) — Python Playwright spec for `/prompts/workflows`. 2 tests:
   - Test 1: navigate to `/prompts/workflows`, list shows 6 workflow descriptors
   - Test 2: click `aszf_rag_chain_expert` → detail panel shows DAG with `system_expert` step + Test Run button → click → JSON output panel populated
3. **SV-FU-1 corpus extension** (operator-driven, optional in SW-2) — if anonymized real PDFs/scans available, add 5 per doctype × 5 doctypes = 25 files at `data/fixtures/doc_recognizer/<doctype>/`. Re-run `scripts/measure_doc_recognizer_accuracy.py --strict`; if SLOs hold, ship; otherwise defer the failing doctype's corpus to Sprint X.

**Gate.**
- `bash scripts/start_stack.sh --full` + both Playwright specs PASS
- `pytest tests/unit/` unchanged (Playwright lives in `tests/ui-live/`)
- Real-corpus measurement (if SV-FU-1 lands): each doctype meets its SLO

**Expected diff.** ~250 LOC Playwright + 25 fixture files (if SV-FU-1 lands) + tracker update. **0 unit / integration delta in code; +2 live Playwright + ≤+3 unit (per-validator regression checks if added).**

**Risk.** R3 — fixture anonymization timeline (operator-driven; mitigation: defer per-doctype corpus to SW-X if PDFs not ready).

### SW-3 — `customer` → `tenant_id` rename + Alembic 049 (SS-FU-1 / SS-FU-5)
**Scope.** Multi-tenant cleanup. Sprint S half-migrated; Sprint W finishes.

1. **Service code rename** — every `customer=` kwarg / `customer` column read in `src/aiflow/services/rag_engine/`, `src/aiflow/services/rag_metrics/`, `src/aiflow/api/v1/rag_collections.py`, `src/aiflow/api/v1/rag_engine.py` → `tenant_id`.
2. **Pydantic model alias** — `RagCollectionListItem`, `RagCollectionDetailResponse`, etc.: keep `customer` as deprecated read-alias for one minor version (`validation_alias=AliasChoices("tenant_id", "customer")`) so pre-S API clients don't break.
3. **Alembic 049** — `rag_collections.customer` column drop. Pre-flight: `SELECT COUNT(*) FROM rag_collections WHERE customer IS NOT NULL AND customer != tenant_id` → if non-zero, halt + manual review. Drop is metadata-only after the data check.
4. **Test suite update** — every `tests/` file referencing `customer=` updated to `tenant_id=`. Existing assertion patterns preserved.
5. **Backward-compat audit** — `scripts/audit_customer_references.py` (mirror S154 `audit_cost_recording.py` pattern). `--strict` exits non-zero on any remaining `customer` reference.

**Gate.**
- All references in `src/` migrated (audit script `--strict` passes)
- Sprint J UC2 MRR@5 ≥ 0.55 unchanged (RAG retrieval byte-stable)
- Alembic 049 round-trip clean
- API alias shim test: pre-S response shape with `customer` field deserializes cleanly

**Expected diff.** ~300 LOC + Alembic 049 + new audit script + ~10 unit tests. **+10 unit / +2 integration (alembic 049 round-trip + alias shim)**.

**Risk.** R4 — pre-S API consumer breakage (mitigated by Pydantic alias shim for one minor version).

### SW-4 — `AIFLOW_ENV=prod` guard + Langfuse listing + operator script `--output` (SM-FU-2 + SR-FU-6 + SU-FU-1)
**Scope.** Three small wins bundled to share a session.

1. **`AIFLOW_ENV=prod` boot guard (SM-FU-2)** — at FastAPI lifespan startup, if `settings.environment == "prod"` AND `VaultProvider` instantiated with a root token (detectable via the `aiflow-dev-root` literal or via `vault.is_root_token` introspection), refuse boot with a clear error (`AIFLOW_ENV=prod requires AppRole authentication, not a root token`). Add `docs/runbooks/vault_approle_iac.md` with a Terraform / Vault-CLI example for AppRole role/secret_id provisioning.
2. **Langfuse listing surface (SR-FU-6)** — `LangfuseClient.list_workflow_prompts()` helper + `/api/v1/prompt-workflows?source=langfuse` query param. Admin UI `/prompts/workflows` page gains a source-toggle (local YAML / Langfuse / both). When `source=langfuse`, the listing pulls from Langfuse-typed `workflow:<name>` JSON prompts.
3. **Operator script `--output` migration (SU-FU-1, 2 of 5 remaining)** — migrate `measure_uc1_golden_path.py` + `run_nightly_rag_metrics.py` to the S156 `argparse_output()` helper. After SW-4, all 5 operator scripts use the uniform flag.

**Gate.**
- Boot test: `AIFLOW_ENV=prod` + dev Vault root token → boot fails with the clear error message
- Boot test: `AIFLOW_ENV=prod` + AppRole credentials → boot succeeds
- `LangfuseClient.list_workflow_prompts()` integration test (skip-by-default behind `AIFLOW_RUN_LIVE_LANGFUSE=1`)
- `measure_uc1_golden_path.py --output json` produces structured payload; `run_nightly_rag_metrics.py --output text` produces human-readable

**Expected diff.** ~250 LOC across `aiflow/security/` (boot guard), `aiflow/contrib/langfuse_client.py` (listing helper), `aiflow/api/v1/prompt_workflows.py` (source query param), 2 operator scripts, 1 runbook. **+8 unit / +1 integration**.

**Risk.** R5 — false-positive on the Vault root token detection (mitigated by exact-string match against `aiflow-dev-root` literal + opt-out via `AIFLOW_VAULT__ALLOW_ROOT_TOKEN_IN_PROD=true` for emergency).

### SW-5 — Sprint W close + tag v1.7.0
**Scope.** Standard close session.

1. `docs/sprint_w_retro.md` — retrospective (decisions log SW-1..SW-4, what worked / what hurt, follow-ups)
2. `docs/sprint_w_pr_description.md` — cumulative PR description
3. `CLAUDE.md` — Sprint W DONE banner + key numbers (2606 → 2620+ unit, 5 → 6 ci.yml jobs unchanged, 6 → 7 PromptWorkflow descriptors if SW-1 ships a new one, 48 → 49 Alembic head)
4. `session_prompts/NEXT.md` → SX-1 prompt (Sprint X candidate or audit-gate session)
5. PR opened against `main`, tag `v1.7.0` queued

**Expected diff.** ~80 LOC docs. 0 code change.

**Risk.** R6 — Sprint scope creep into SW-5 (operator should freeze scope at SW-4 close).

---

## 3. Plan, gate matrix

| Session | Theme | Golden-path test | Threshold | Rollback path |
|---|---|---|---|---|
| SW-1 | Real PromptWorkflow extraction | UC1 invoice_processor regression check (existing path unchanged) + 2-doctype real-LLM round-trip | UC1 ≥ 75% / invoice_number ≥ 90% (regression); 2-doctype top-k extraction (invoice_number + total_gross + id_number + full_name + birth_date) confidence ≥ 0.7 | Revert squash; SW-1 is additive, no shared state with invoice_processor |
| SW-2 | Live Playwright + corpus | Both live specs PASS on clean dev stack; if SV-FU-1 corpus lands, 5 doctypes meet SLO | Specs PASS; corpus accuracy unchanged (or improved) | Revert per-spec squash; corpus is additive |
| SW-3 | customer → tenant_id rename | UC2 MRR@5 ≥ 0.55; alias shim alias resolution test | UC2 unchanged; audit script `--strict` reports 0 customer references in src/ | Revert squash; Pydantic alias keeps both names readable during transition |
| SW-4 | AIFLOW_ENV=prod guard + Langfuse listing + script --output | Boot guard fails on root-token-in-prod; live Langfuse integration (skip-by-default); 2 operator scripts emit --output cleanly | All assertions pass; `--output json` produces parseable payloads | Revert per-feature squash |

**Threshold column blocks merge.** Any session that fails its gate halts; the operator either rolls forward (debug) or reverts the session and reschedules.

---

## 4. Risk register

### R1 — LLM cost amplification in SW-1
Real-LLM extraction at SW-1 means every `recognize` call invokes the LLM. Mitigation: per-step `CostPreflightGuardrail.check_step()` (Sprint U S154 API) limits, descriptor-tunable `cost_ceiling_usd` per step, dry-run mode for tests.

### R2 — UC1 byte-stable regression in SW-1
SW-1 extends the doc_recognizer to call `invoice_extraction_chain` for `hu_invoice` — could accidentally change UC1 invoice_processor behavior. Mitigation: doc_recognizer is a separate entry point; Sprint Q UC1 golden-path slice gates SW-1; doc_recognizer's `recognize_and_extract` returns its own DocExtractionResult, not modifying `invoice_processor.workflows.process` outputs.

### R3 — SV-FU-1 fixture anonymization timeline
Real-document fixtures require operator-driven anonymization. If not ready, defer per-doctype corpus to Sprint X. SW-2 still ships the live Playwright specs without the corpus.

### R4 — pre-S API consumer breakage on SW-3
Older API consumers may still send `customer` field in PUT requests. Mitigation: Pydantic alias shim at the contract boundary (keep `customer` readable for one minor version); deprecation warning on first use; remove in v1.8.0.

### R5 — `AIFLOW_ENV=prod` false-positive on dev clusters
Operators experimenting with prod-like envs may accidentally trip the boot guard. Mitigation: clear error message pointing to `docs/runbooks/vault_approle_iac.md`; opt-out env `AIFLOW_VAULT__ALLOW_ROOT_TOKEN_IN_PROD=true` for emergency restoration.

### R6 — Sprint W scope creep into SW-5
SW-5 is close-only — the deliverables are docs + CLAUDE.md + tag. Mitigation: operator freezes scope at SW-4 close; any new debt found goes to Sprint X.

---

## 5. Definition of done

- [ ] All 4 execution sessions (SW-1..SW-4) merged on `main` with green CI
- [ ] DocRecognizer recognize endpoint returns populated `extracted_fields` for `hu_invoice` + `hu_id_card`
- [ ] UC1 invoice_processor golden-path slice unchanged (≥ 75% / `invoice_number` ≥ 90%)
- [ ] UC2 `aszf_rag_chat` MRR@5 ≥ 0.55 unchanged
- [ ] UC3 `email_intent_processor` 4/4 unchanged
- [ ] Alembic head: 049 (`customer` column dropped on `rag_collections`)
- [ ] No references to `customer` column in `src/` (audit script `--strict` clean)
- [ ] `AIFLOW_ENV=prod` boot guard active; AppRole runbook published at `docs/runbooks/vault_approle_iac.md`
- [ ] 5/5 operator scripts adopt `argparse_output()` helper
- [ ] Live Playwright `/document-recognizer` + `/prompts/workflows` PASS on clean dev stack
- [ ] OpenAPI drift gate `[ok]` (snapshot refreshed for any new query params)
- [ ] `tag v1.7.0` queued for post-merge
- [ ] `docs/sprint_w_retro.md` + `docs/sprint_w_pr_description.md` published
- [ ] `session_prompts/NEXT.md` → SX-1 or audit-gate prompt

---

## 6. Out of scope (deferred to Sprint X+)

- Coverage uplift 70% → 80% (SJ-FU-7) — dedicated cross-cutting sprint
- UI Monaco editor (SV-FU-5) — wait for operator feedback
- Vault rotation E2E + Langfuse v3→v4 — infrastructure sprint
- UC3 thread-aware classifier (SP-FU-3) — architecture sprint
- Doc_recognizer ML classifier — only if SV-FU-1 reveals rule-engine inadequacy
- Grafana cost panels (SN-FU-3) — observability sprint
- Sprint Q UC1 corpus extension to 25 fixtures (SQ-FU-3) — operator curation
- UC1 `invoice_date` SQL column rename (SU-FU-3) — no functional pressure
- `scripts/` ruff cleanup (SU-FU-2) — pure code hygiene
- UI bundle size guardrail (SV-FU-2) — bundle hasn't grown alarmingly

These accumulate as the Sprint X+ inventory.

---

## 7. Skipped items tracker (initial)

| ID | Hely | Mi | Unskip feltetel |
|---|---|---|---|
| SW-SKIP-1 (planned, SW-1) | `tests/integration/skills/test_doc_recognizer_extraction_real.py` | Real-OpenAI integration on hu_invoice + hu_id_card fixtures | `secrets.OPENAI_API_KEY` |
| SW-SKIP-2 (planned, SW-2) | `tests/ui-live/document-recognizer.md` | Live Playwright spec | Live admin stack (`bash scripts/start_stack.sh --full`) |
| SW-SKIP-3 (planned, SW-2) | `tests/ui-live/prompt-workflows.md` | Live Playwright spec for /prompts/workflows | Live admin stack |
| SW-SKIP-4 (planned, SW-4) | `tests/integration/test_langfuse_listing_live.py` | Live Langfuse integration | `AIFLOW_RUN_LIVE_LANGFUSE=1` + Langfuse server reachable |

Sprint V carry-forwards inherit unchanged: ST-SKIP-1, SU-SKIP-1, SU-SKIP-2, SS-SKIP-2, SV-SKIP-1.

---

## 8. STOP conditions

**HARD:**
1. UC1 `invoice_processor` golden-path regression on SW-1 — UC1 < 75% accuracy on the CI 3-fixture slice or `invoice_number` < 90%. The doc_recognizer's extraction wire-up must NOT touch UC1 behavior.
2. Alembic 049 fails the pre-flight check (any row with `customer != tenant_id`) → halt; manual data review before SW-3 proceeds.
3. SW-3 audit script `--strict` reports remaining `customer` references → halt + extend the migration scope.
4. SW-4 `AIFLOW_ENV=prod` guard accidentally trips on a non-prod test → halt; refine the detection logic.
5. SW-1 LLM cost per recognize call exceeds $0.05 on the starter corpus — investigate per-step ceilings + descriptor configuration.

**SOFT:**
- SV-FU-1 fixtures not ready by SW-2 — defer corpus extension to SW-X, ship Playwright specs only.
- Langfuse server unreachable during SW-4 — skip the live integration test; the listing helper unit tests still run.

---

## 9. Post-Sprint-W audit (DEFER — not Sprint W scope)

Topics queued for Sprint X audit:

- Coverage uplift 70% → 80% (SJ-FU-7)
- UC3 thread-aware classifier (SP-FU-3)
- Doc_recognizer ML classifier (kis fasttext / sklearn / kis BERT) — only if SW-2 corpus reveals rule-engine inadequacy
- Grafana cost panels (SN-FU-3) + ci-cross-uc UC1-General slot
- Vault rotation E2E + Langfuse v3→v4 server upgrade
- Sprint Q UC1 corpus extension to 25 fixtures (SQ-FU-3)

---

## 10. References

- Audit + Sprint W direction: `docs/post_sprint_v_audit.md`
- Sprint V retro: `docs/sprint_v_retro.md`
- Sprint V plan: `01_PLAN/119_SPRINT_V_DOCUMENT_RECOGNIZER_PLAN.md`
- UC trajectory: `01_PLAN/110_USE_CASE_FIRST_REPLAN.md`
- Sprint U plan: `01_PLAN/118_SPRINT_U_OPERATIONAL_HARDENING_PLAN.md`
- DocRecognizer service: `src/aiflow/services/document_recognizer/`
- DocRecognizer admin UI: `aiflow-admin/src/pages-new/DocumentRecognizer/`
- DocType descriptors: `data/doctypes/`
- PromptWorkflow descriptors: `prompts/workflows/`
- Existing reusable surfaces: `CostPreflightGuardrail.check_step()` (S154), `argparse_output()` (S156)
