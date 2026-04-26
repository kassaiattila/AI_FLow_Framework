# AIFlow Sprint History

> **Status:** continuously updated — every sprint-close appends a new section here
> instead of expanding the CLAUDE.md banner.
> **Source:** archived from CLAUDE.md banner on 2026-04-26 (SX-1 honest alignment audit).
> **For current sprint:** see `01_PLAN/ROADMAP.md` + `session_prompts/NEXT.md`.

This file is the chronological trajectory recap. Per-sprint retrospective
documents live at `docs/sprint_<letter>_retro.md`.

---

## v1.7.0 — Sprint W (2026-04-26)

**Theme:** Production-readiness + multi-tenant cleanup. **(drift: polish)** —
the Sprint V audit said "defer until 4 UC szilardan mukodik"; Sprint W
shipped these prematurely. See `docs/honest_alignment_audit.md`.

Tag `v1.7.0` (queued post-merge). Squashes `7509613` (#56, SW-1) +
`600193c` (#57, SW-2) + `7162a34` (#58, SW-3) + `ad1b708` (#59, SW-4) on
top of Sprint V tag `v1.6.0` (`ee3f5ff`). 5 sessions in 1 calendar day,
every change default-off at the user-visible layer.

- **SW-1 (DocRecognizer extraction wire-up, SV-FU-4):** `DocumentRecognizerOrchestrator.run()` wires `PromptWorkflowExecutor.resolve_for_skill("document_recognizer", descriptor.extraction.workflow)` + per-step LLM invocation via `models_client.generate(...)` + per-step `CostPreflightGuardrail.check_step()` (Sprint U S154 API) refusing on ceiling breach + 7 pure-Python validators (`non_empty`, `regex:<pattern>`, `iso_date`, `before_today`, `after_today`, `min:N`, `max:N`) + graceful `extract_fn=None` fallback when wiring fails. UC1 invoice_processor byte-stable (`hu_invoice` reuses Sprint T `invoice_extraction_chain`). **+14 unit**.
- **SW-2 (live Playwright, SV-FU-3 + SR-FU-4):** `tests/ui-live/document-recognizer.md` (3-test journey: browse 5 doctypes / recognize file upload / per-tenant YAML override save+refresh+delete) + `tests/ui-live/prompt-workflows.md` (3-test journey: browse 6 descriptors / detail+dry-run / source-toggle pre-publish placeholder). Markdown journey scripts run via Playwright MCP, NOT pytest.
- **SW-3 (customer → tenant_id rename, SS-FU-1 / SS-FU-5):** Alembic 049 drops `rag_collections.customer` column + `idx_rag_collections_customer` index (downgrade restores nullable + index, lossy per SS-FU-5 authorization) + `RAGEngineService.create_collection(tenant_id=...)` + `list_collections(tenant_id=...)` + INSERT writes `tenant_id` instead of `customer` + `scripts/audit_customer_references.py` strict mode (0 hits on rag_collections surface). Test fixtures in 4 files updated to drop `customer` from seed INSERTs. **+1 alembic integration round-trip**. Out of scope (intentional): `skill_instances.customer`, `intent_schemas.customer`, `document_extractor` config — separate domains.
- **SW-4 (prod guard + Langfuse + script --output, SM-FU-2 + SR-FU-6 + SU-FU-1):** `src/aiflow/security/boot_guards.py` refuses prod boot with Vault root token (detects `aiflow-dev-root` literal + `hvs.` prefix excluding `hvs.CAES` AppRole-derived) + `enforce_boot_guards()` first in `create_app().lifespan` + `BootGuardError` on violation + `AIFLOW_VAULT__ALLOW_ROOT_TOKEN_IN_PROD` bypass (audit-WARN-logged) + `VaultSettings.allow_root_token_in_prod: bool = False` field + `docs/runbooks/vault_approle_iac.md` AppRole runbook (Vault CLI + Terraform reference). `PromptManager.list_langfuse_workflows()` stub returning [] until v4 SDK ships list-by-prefix + `/api/v1/prompts/workflows?source={local,langfuse,both}` query param (response shape unchanged, `source: "backend"` stays as provenance). `measure_uc1_golden_path.py` + `run_nightly_rag_metrics.py` adopt `argparse_output()` — **5/5 operator scripts** uniform. **+12 boot guard + +4 router source-toggle**.
- **SW-5 close** publishes `docs/sprint_w_retro.md` + `docs/sprint_w_pr_description.md` + CLAUDE.md banner.

**Total Sprint W deltas:** +35 unit (2606 → 2641) / +1 integration alembic / 0 endpoints / 0 routers / 0 UI / +1 Alembic (head 048 → 049) / 0 PromptWorkflow descriptors / 0 doctype descriptors / 0 CI jobs / +2 live Playwright markdown specs / +2 operator scripts on uniform `--output` (3 → 5).

**Open follow-ups:** SW-FU-1 Langfuse v4 list-by-prefix SDK helper, SW-FU-2 admin UI source-toggle widget, SW-FU-3 audit script extension to other tables, SW-FU-4 Vault AppRole IaC E2E test, SW-FU-5 DocRecognizer real-document corpus (carry from SV-FU-1).

References: `01_PLAN/120_SPRINT_W_KICKOFF_PLAN.md`, `docs/sprint_w_retro.md`, `docs/sprint_w_pr_description.md`, `docs/runbooks/vault_approle_iac.md`.

---

## v1.6.0 — Sprint V (2026-04-26)

**Theme:** Generic Document Recognizer skill (UC1-General). **(use-case-zar: new UC)** —
shipped a parametrizable, pluggable doc-type registry that replaces the
legacy `invoice_finder` scaffold.

Tag `v1.6.0` (queued post-merge). Squashes `7f8b6fa` (#50, SV-1) + `d2addd1` (#51, SV-2) + `6eeb871` (#52, SV-3) + `b4a0358` (#53, SV-4) on top of Sprint U tag `v1.5.4` (`d949391`).

**5 initial doctypes ship:** `hu_invoice` (reuses Sprint T `invoice_extraction_chain`), `hu_id_card` (PII high, `id_card_extraction_chain` 4-step DAG), `hu_address_card` (PII medium), `eu_passport` (PII high, MRZ regex), `pdf_contract` (legal, default `rag_ingest`). **100% top-1 accuracy** on the 8-fixture synthetic starter corpus. UC1 `invoice_processor` byte-stable; the doc_recognizer is additive.

- **SV-1 (foundation, +66 unit):** 8 Pydantic contracts + 4 nested config types · DocTypeRegistry skeleton (per-tenant override + runtime register, resilient to invalid YAML) · `safe_eval_intent_rule` (`simpleeval` wrapper, restricted operators + name space, NOT Python eval) · skill rename `invoice_finder` → `document_recognizer` (`git mv` preserves history) · deprecated alias shim.
- **SV-2 (classifier, +46 unit):** 5 rule kinds (regex / keyword_list / structure_hint / filename_match / parser_metadata) · `classify_doctype` with score normalization + top-k · `DocumentRecognizerOrchestrator` 4 entry points (classify / route_intent / run / to_audit_payload) + LLM fallback graceful degradation · `id_card_extraction_chain.yaml` PromptWorkflow descriptor (4-step: ocr_normalize → fields → confidence → validate; `validate.required: false` Sprint T S149 pattern).
- **SV-3 (API, +20 unit):** 5 routes mounted at `/api/v1/document-recognizer` (POST recognize, GET doctypes, GET doctypes/{name}, PUT doctypes/{name}, DELETE doctypes/{name}) · Alembic 048 `doc_recognition_runs` (13 columns + 4 CHECK + 3 indexes) · `DocRecognitionRepository` with PII redaction boundary · OpenAPI snapshot refreshed.
- **SV-4 (admin UI, 0 net unit):** Admin UI page `/document-recognizer` (Browse + Recognize tabs + DocTypeDetailDrawer with YAML editor + tenant override save/delete + RecognizePanel multipart upload + PiiBadge Tailwind v4) · 5th doctype `eu_passport.yaml`.
- **SV-5 (corpus + close):** 8 synthetic `.txt` fixtures across 5 doctypes · `scripts/measure_doc_recognizer_accuracy.py` (S156 `argparse_output()` helper, `--strict` SLO gate) · CI `doc-recognizer-accuracy` job in `ci.yml` · weekly `doc-recognizer-weekly-matrix` Mon 08:00 UTC in `nightly-regression.yml` · Sprint V close docs.

**Total Sprint V deltas:** +131 unit / 0 integration delta / +5 endpoints / +1 router (32 total) / +1 UI page (27 total) / +1 Alembic (head 048) / +1 DB table / +5 doctype descriptors / +1 PromptWorkflow descriptor (6 total) / +2 CI jobs / +8 starter fixtures.

**Open follow-ups:** SV-FU-4 wire real PromptWorkflow extraction (Sprint W kickoff priority — closed in SW-1), SV-FU-1 real-document fixture corpus (deferred to Sprint X SX-3), SV-FU-3 live Playwright (closed in SW-2), SV-FU-2 UI bundle guardrail, SV-FU-5 Monaco editor (if needed), SV-FU-6 live Playwright `/prompts/workflows` (closed in SW-2).

References: `01_PLAN/119_SPRINT_V_DOCUMENT_RECOGNIZER_PLAN.md`, `docs/sprint_v_retro.md`, `docs/sprint_v_pr_description.md`.

---

## v1.5.4 — Sprint U (2026-04-26)

**Theme:** Operational hardening + carry-forward catch-up. **(drift: polish)** —
own plan declares "Zero new functional capability; the win is operability".

Tag `v1.5.4` (queued post-merge). Squashes `b0d430a` (#44, S152) + `4e63525` (#45, S153) + `fd69764` (#46, S154) + `97eb09b` (#47, S155) + `f5c0234` (#48, S156) on top of Sprint T tag `v1.5.3` (`fd2a8bc`). 5 PRs merged in 2 calendar days.

- **S153 (CI hookups + tooling, 5 micro-wins):** OpenAPI drift CI step (`openapi-drift` job in `ci.yml`; **caught real Sprint S S144 drift on first run** — 3 paths + 1 tag + 4 schemas missing from snapshot, refreshed in same commit) + weekly UC3 4-combo matrix as GHA (Mon 07:00 UTC + workflow_dispatch, `OPENAI_API_KEY`-gated) + `vite build` pre-commit hook (`scripts/hooks/pre-commit` + `make install-hooks`) + `extend-unsafe-fixes = ["F401"]` ruff config (mid-Edit unused-import auto-removal mitigation, ST-FU-5) + BGE-M3 weight cache promoted from nightly to PR-time CI (new `integration-1024-dim` job). Plus `01_PLAN/AUDIT_2026_04_26_SPRINT_V_DIRECTION.md` audit doc published in same PR (S155 rescope + Sprint V direction).
- **S154 (cost/settings consolidation, 4 wins):** `CostSettings` umbrella (`AIFLOW_COST__*` env prefix; legacy `AIFLOW_BUDGET__*` + `AIFLOW_COST_GUARDRAIL__*` continue to work) + `record_cost(...)` rewritten as thin shim over `CostAttributionRepository.insert_attribution(...)` (single DB-write path; **inline DDL hack removed**) + `CostPreflightGuardrail.check_step()` per-step API + 4 new `PreflightReason` literals (ST-FU-3) + `tier_fallback_*_per_1k` env-tunable JSON via `CostGuardrailSettings` (SN-FU-2). **+22 unit**.
- **S155 (RESCOPED to ST-FU-2 only):** 2 new persona PromptWorkflow descriptors (`aszf_rag_chain_expert.yaml` + `aszf_rag_chain_mentor.yaml`, 4-step DAG mirroring baseline with `system_<role>` step pinned) + `_PERSONA_WORKFLOW_MAP` + `_PERSONA_SYSTEM_STEP_MAP` in `query.py` (persona-aware `generate_answer` no longer hard-codes `system_baseline`). 4 existing S150 "expert/mentor always falls through" tests UPDATED + 4 new flag-OFF parity tests. SR-FU-4 + SR-FU-6 deferred to Sprint V/W per audit. **+4 net unit**.
- **S156 (Sprint Q polish, 4 wins):** `issue_date` prompt + schema fix (SQ-FU-1; `Field(validation_alias=AliasChoices(...))`, no Alembic, dict normalization, SQL INSERT prefers `issue_date`, `inv.header.invoice_date` `@property`) + `_parse_date_iso` ISO normalizer at JSON-payload boundary (SQ-FU-4; regex char-class bug fix `[./-]`) + `make api` docling warmup gate (`AIFLOW_DOCLING_WARMUP=true`, default off; SQ-FU-2) + `argparse_output()` helper + `audit_cost_recording.py` migration (ST-FU-4; 4 remaining scripts tracked as ST-FU-4-followup). **+25 unit**.

**Total Sprint U deltas:** +51 unit / 0 integration / 0 endpoint / 0 UI / 0 Alembic / +2 PromptWorkflow descriptors (3→5) / +2 ci.yml jobs (2→4) / +1 nightly weekly job / +1 pre-commit hook.

**Open follow-ups:** SU-FU-1 operator-script `--output` migration (closed in SW-4), SU-FU-2 `scripts/` ruff cleanup, SU-FU-3 Alembic `048` `invoice_date` SQL column rename, SU-FU-4 UC1 full-corpus `issue_date` ≥ 90% verification (carried into Sprint X SX-2).

References: `01_PLAN/118_SPRINT_U_OPERATIONAL_HARDENING_PLAN.md`, `docs/sprint_u_retro.md`, `docs/sprint_u_pr_description.md`, `01_PLAN/AUDIT_2026_04_26_SPRINT_V_DIRECTION.md`.

---

## v1.5.3 — Sprint T (2026-04-25)

**Theme:** PromptWorkflow per-skill consumer migrations. **(drift: refactor)** —
3 skill (UC1+UC2+UC3) erintett, mindharom byte-stable maradt — semmi
minosegi javulas.

Tag `v1.5.3` (queued post-merge). Squashes `aa74e02` (#40, S148) + `e936eb3` (#41, S149) + `ee2b431` (#42, S150) on top of Sprint S tag `v1.5.2` (`20fb792`).

PromptWorkflow per-skill consumer migrations close the loop Sprint R left scaffolded but unconsumed: 3 skills × 3 descriptors wired (`email_intent_chain` ✓ | `invoice_extraction_chain` ✓ | `aszf_rag_chain` ✓ baseline persona only). **Default-off rollout** — `AIFLOW_PROMPT_WORKFLOWS__ENABLED=false` + `AIFLOW_PROMPT_WORKFLOWS__SKILLS_CSV=""` defaults preserved → zero behaviour change for any tenant that hasn't flipped both flags.

- **S148** `email_intent_processor` consumes `email_intent_chain` 1 LLM call site (LLM-aware branch wrapped, sklearn / `_keywords_first` early-return preserved byte-for-byte) +10 unit / +1 integration.
- **S149** `invoice_processor.workflows.process` consumes `invoice_extraction_chain` 3 LLM call sites (`classify` / `extract_header` / `extract_lines`) + per-step cost ceilings (0.02 / 0.03 USD via local `CostEstimator` + `CostGuardrailRefused` raise) + `validate` step `required: false` → pure-Python legacy path + `EmailDetailResponse.extracted_fields` schema-stable, +15 unit / +1 integration.
- **S150** `aszf_rag_chat.workflows.query` baseline persona consumes `aszf_rag_chain` 3 mappable call sites + `_resolve_workflow_for_persona(role)` carve-out (expert/mentor on legacy direct-prompt path) + descriptor's `answer` step has no matching legacy call (legacy generates the answer directly from `system_prompt_<role>` in one LLM hop) so executor stays resolution-only no new call site introduced, +19 unit / +1 integration.
- **S151 close** — retro + PR description + CLAUDE.md banner + ST-FU-1 fix.

**Total Sprint T deltas:** +45 unit / +3 integration / +0 E2E / +3 skill consumers.

**Open follow-ups:** ST-FU-2 expert/mentor persona descriptors (closed S155), ST-FU-3 per-step cost ceiling consolidation (closed S154), ST-FU-4 operator parity scripts uniform `--output` flag (closed S156+SW-4), ST-FU-5 ruff-strips-imports tooling fix (closed S153).

References: `01_PLAN/117_SPRINT_T_PROMPTWORKFLOW_MIGRATION_PLAN.md`, `docs/sprint_t_retro.md`, `docs/sprint_t_pr_description.md`.

---

## v1.5.2 — Sprint S (2026-04-25 → 2026-04-26)

**Theme:** Multi-tenant + multi-profile vector DB. **(drift: infra-only)** —
tenant filter + embedder profile editor — UI shipped de UC2 retrieval
quality nem javult.

Tag `v1.5.2` (queued post-merge). Squashes `95ec89e` (#34, S143) + `bc59a8f` (#35, S144) + `d6ee813` (#37, S145), plus side-branch `ec3e672` (#36, chore env consolidation).

- **S143:** Query-path ProviderRegistry refactor closes Sprint J FU-1 (1024-dim BGE-M3 collections now queryable). Alembic 046 additive: `rag_collections.tenant_id TEXT NOT NULL DEFAULT 'default'` + `rag_collections.embedder_profile_id TEXT NULL` + `ix_rag_collections_tenant_id`. `RAGEngineService.query()` gains `_resolve_query_embedder(coll)`: NULL profile → legacy fallback (byte-for-byte identical), known alias → adapter, unknown → `UnknownEmbedderProfile`.
- **S144:** Operator-facing admin UI for the multi-tenant + multi-profile vector DB: `RAGEngineService.set_embedder_profile()` mutation with `DimensionMismatch` (HTTP 409) guard, 3-route `/api/v1/rag-collections` admin router, new admin page `/rag/collections` with tenant filter + side drawer + EN/HU locales. Path note: hyphenated route avoids colliding with legacy `/api/v1/rag/collections`.
- **S145:** SS-FU-3 nightly MRR@5 retrieval-quality harness (`src/aiflow/services/rag_metrics/` + 20-item HU UC2 query corpus + Grafana panel JSON + operator runbook), SS-FU-4 Alembic 047 swap of legacy `UNIQUE (name)` for `UNIQUE (tenant_id, name)`, BGE-M3 weight `actions/cache@v4` step. Pre-flight duplicate scan returned 0 rows.

References: `docs/sprint_s_retro.md`, `docs/sprint_s_pr_description.md`, `01_PLAN/116_SPRINT_S_FUNCTIONAL_VECTOR_DB_PLAN.md`.

---

## v1.5.1 — Sprint R (2026-05-14)

**Theme:** PromptWorkflow foundation. **(drift: scaffold-only)** —
"Per-skill code migration explicitly deferred" violated the
"one use-case per sprint" policy.

Tag `v1.5.1` queued post-merge. Multi-step prompt chains become first-class artifacts: YAML descriptor + Pydantic model with full DAG validation (Kahn topological sort, dedup, cycle detection) + 3-layer lookup (cache → Langfuse `workflow:<name>` JSON-typed prompt → local YAML) + admin UI listing/detail/dry-run + per-skill opt-in executor scaffold. **Flag-off default** — zero behaviour change for any skill.

- **S139** `PromptWorkflow` + `PromptWorkflowStep` + `PromptWorkflowLoader` + `PromptManager.get_workflow()` + `FeatureDisabled` (HTTP 503) + 24 unit tests + example descriptor `prompts/workflows/uc3_intent_and_extract.yaml`.
- **S140** admin UI `/prompts/workflows` page (React 19 + Tailwind v4: table list + DAG-indented detail panel + Test Run dry-run JSON output) + 3-route GET-only router + EN/HU locale + sidebar nav + 10 router unit tests + OpenAPI snapshot refresh.
- **S141** `PromptWorkflowExecutor` scaffold (resolution-only, never invokes LLM, returns None on every failure mode for clean fallback) + `PromptWorkflowSettings.skills_csv` per-skill opt-in + 3 ready-to-consume descriptors (`email_intent_chain`, `invoice_extraction_chain`, `aszf_rag_chain` baseline) + 17 unit tests.
- **S142** retro + PR.

**Total Sprint R deltas:** 0 Alembic migrations, 0 skill code changes, 0 golden-path regressions.

**Open follow-ups:** S141-FU-1/2/3 per-skill migrations (closed Sprint T), SR-FU-4 live-stack Playwright (closed SW-2), SR-FU-5 vite-build pre-commit hook (closed S153), SR-FU-6 Langfuse workflow listing (closed SW-4 stub).

References: `01_PLAN/114_CAPABILITY_ROADMAP_Q_R_S.md` §3, `docs/sprint_r_retro.md`, `docs/sprint_r_pr_description.md`.

---

## v1.5.0 — Sprint Q (2026-05-10)

**Theme:** Intent + extraction unification. **(use-case-zar: UC1)** —
First UC1 end-to-end validation since Phase 1d.

Tag `v1.5.0` (PR #29 squash `c4ded1d`). UC3 intent classifier (Sprint P, 4% misclass) now chains into `skills.invoice_processor` on EXTRACT emails; admin UI surfaces vendor/buyer/header/items/totals via new `ExtractedFieldsCard`.

- **85.7% accuracy** on 10-fixture reportlab corpus (target ≥ 80%), invoice_number/vendor/buyer/currency/due_date/gross_total all 100%, only `issue_date` misses systematically (SQ-FU-1, polished S156, deep-fix carried to Sprint X SX-2).
- **S135** `UC3ExtractionSettings` flag (`AIFLOW_UC3_EXTRACTION__ENABLED=false` default) + `_maybe_extract_invoice_fields` orchestrator helper + `_intent_class_is_extract` gate + lazy import + `asyncio.wait_for(total_budget_seconds)` wrap + per-file error isolation + per-invoice USD budget ceiling + 14 unit + 3 settings + 1 intent-gate + 1 real-stack integration.
- **S136** `EmailDetailResponse.extracted_fields` additive + `ExtractedFieldsCard.tsx` (Tailwind v4, dark-mode, confidence + cost chips) + EN/HU locale + 1 Playwright E2E on **live dev stack**.
- **S137** 10-fixture UC1 golden-path corpus (HU/EN/mixed, simple/tabular/multi-section) + `data/fixtures/invoices_sprint_q/{manifest.yaml,generate_invoices.py}` idempotent reportlab generator + `scripts/measure_uc1_golden_path.py` operator script + `docs/uc1_golden_path_report.md` (85.7% accuracy, $0.0004 mean cost, 96 s wall) + `tests/integration/skills/test_uc1_golden_path.py` CI slice.
- **S138** retro + PR.

**Open follow-ups:** SQ-FU-1 `issue_date` prompt/schema fix (closed S156), SQ-FU-2 pre-boot docling warmup (closed S156), SQ-FU-3 corpus extension to 25 (carried to Sprint X SX-2), SQ-FU-4 `_parse_date` ISO roundtrip (closed S156).

References: `01_PLAN/115_SPRINT_Q_INTENT_EXTRACTION_UNIFICATION.md`, `docs/sprint_q_retro.md`, `docs/sprint_q_pr_description.md`.

---

## v1.4.12 — Sprint P (2026-05-06)

**Theme:** UC3 LLM-fallback + body-only/mixed cohort coverage. **(use-case-zar: UC3)**.

Tag `v1.4.12` (PR #25 squash `390d4d5`). Classifier strategy on the attachment-intent flag-on path flips from `SKLEARN_ONLY` to `SKLEARN_FIRST` (new `AIFLOW_UC3_ATTACHMENT_INTENT__CLASSIFIER_STRATEGY` knob, default `sklearn_first`); `_keywords_first` gains a pre-LLM attachment-signal early-return that preserves Sprint O behaviour on NDA/SLA/MSA contracts.

**Misclass headline:** **32% → 4%** on the 25-fixture corpus (87.5% relative drop from Sprint O; 93% drop from the Sprint K 56% body-only baseline). Body_only 3/6 → 6/6, Mixed 3/7 → 6/7, Contract 5/6 → 6/6, Invoice 6/6 unchanged. Only remaining miss: `024_complaint_about_invoice` — legitimate body-vs-attachment conflict (SP-FU-1, carried to Sprint X SX-4). 0 Alembic migrations. LLM cost per 25-fixture run: ~$0.002.

- **S131** 4-combo measurement matrix + plan + baseline `docs/uc3_llm_context_baseline.md`.
- **S132** `UC3AttachmentIntentSettings.classifier_strategy` + orchestrator strategy override + `_attachment_signal_is_strong` helper + `_keywords_first` early-return + 10 unit / 2 integration / 1 Playwright E2E.
- **S133** skipped (S132 already exceeded plan §7 target 4x).
- **S134** retro + PR.

**Open follow-ups:** SP-FU-1 `024_complaint` body-vs-attachment intractable conflict (carried Sprint X SX-4), SP-FU-3 thread-aware classifier (carried Sprint X SX-4).

References: `01_PLAN/113_SPRINT_P_LLM_CONTEXT_BODY_MIXED_PLAN.md`, `docs/sprint_p_retro.md`, `docs/sprint_p_pr_description.md`.

---

## v1.4.11 — Sprint O (2026-05-04)

**Theme:** UC3 attachment-aware intent. **(use-case-zar: UC3)**.

Tag `v1.4.11` (PR #19 squash `ea695cc`). Classifier reads PDF/DOCX attachments through reused `AttachmentProcessor`; flag-gated.

**Misclass headline:** **56% → 32%** (24 pts absolute / 42.9% relative drop), invoice_attachment 6/6 + contract_docx 5/6, body_only/mixed unchanged (no attachment to help).

- **S126** 25-fixture corpus + Sprint K body-only baseline **56% misclass / 40% manual-review-like / p95 95ms** (GATE PASS).
- **S127** pure-function `extract_attachment_features` + `AttachmentFeatures` + flag-gated orchestrator hook (lazy `AttachmentProcessor` import + `asyncio.wait_for(total_budget_seconds)`).
- **S128** `ClassifierService.classify(... context=None)` + signal-aligned EXTRACT rule boost (`invoice_number_detected → invoice_received`, `keyword_buckets["contract"] → order`, body-label gate `unknown ∪ EXTRACT_INTENT_IDS` to protect non-EXTRACT body labels) + opt-in LLM-context system message.
- **S129** `AttachmentSignalsCard` + EN/HU locales + `EmailDetailResponse.attachment_features/classification_method` extension + 1 Playwright E2E (route-mocked).
- **S130** retro + PR.

**Post-Sprint-O follow-ups all merged:** FU-1 (live-API E2E + OpenAPI drift detector, `9cc74b1`), FU-2 (intent_class schema + UI badge, PR #20 `36a0e18`), FU-4 (docling warmup, PR #21 `dc0f2f4`), FU-5 (resilience Clock seam unquarantine), FU-7 (per-attachment cost accounting, PR #22 `bdfe149`).

References: `01_PLAN/112_SPRINT_O_UC3_ATTACHMENT_INTENT_PLAN.md`, `docs/sprint_o_retro.md`, `docs/sprint_o_pr_description.md`.

---

## v1.4.10 — Sprint N (2026-04-29)

**Theme:** LLM cost guardrail + per-tenant budget. **(drift: infra-only)** —
nem koncentralt UC1/2/3 melyitesere.

Tag `v1.4.10` (PR #18 squash `13a2f08`). S125 post-merge coverage uplift landed (+83 tools tests, 65.6%→68.5% local; `email_parser.py` Linux OSError guard).

References: `01_PLAN/111_SPRINT_N_COST_GUARDRAIL_BUDGET_PLAN.md`, `docs/sprint_n_retro.md`, `docs/sprint_n_pr_description.md`.

---

## v1.4.9 — Sprint M (2026-04-29)

**Theme:** Vault hvac + self-hosted Langfuse + air-gap Profile A. **(drift: infra-only)** —
Phase 3 munka, de a `110_*` szabaly szerint use-case-en kellett volna ride-olnia.

Tag `v1.4.9` (PR #17 squash `94750d9`).

References: `docs/sprint_m_retro.md`, `docs/runbooks/vault_rotation.md`, `docs/airgapped_deployment.md`.

---

## v1.4.8 — Sprint L (2026-04-23)

**Theme:** Cross-cutting monitoring + cost. **(use-case-zar: UC4 monitoring)**.

Tag `v1.4.8` (PR #16 squash `ab63c93`). 3 use-case running, monitored, cost-capped, prompts admin-editable. ci-cross-uc 42-test suite.

---

## v1.4.7 — Sprint K (2026-04-20)

**Theme:** UC3 Email Intent. **(use-case-zar: UC3)**.

Tag `v1.4.7` (PR #15 squash `2eecb20`). 4-test golden path, intent classifier baseline (56% misclass, improved Sprint O onward).

---

## v1.4.5 — Sprint J (2026-04-25)

**Theme:** UC2 RAG. **(use-case-zar: UC2)**.

Tag `v1.4.5-sprint-j-uc2`. RAG providers + UnstructuredChunker + MRR@5 0.55 baseline. EmbedderProvider ABC + BGE-M3 (Profile A) + Azure OpenAI (Profile B) + ChunkerProvider ABC + UnstructuredChunker + rag_engine opt-in provider-registry + Alembic 040 + 041 + 042 (pgvector flex-dim) + UI ChunkViewer + 3 Playwright E2E + retrieval baseline (live MRR@5 ≥ 0.55 both profiles).

---

## v1.4.3 — Phase 1d (2026-04-24)

Adapter orchestration + IntakePackageSink. PR #9 / `0d669aa`. Tag `v1.4.3-phase-1d`.

---

## Earlier history

For Sprint A (v1.2.2), Sprint B (v1.3.0), Phase 1a/1b/1c — see git log + the per-sprint retro
documents under `docs/`.

---

## Service & port snapshot

- API: 8102
- UI: 5173
- Vault dev: 8210
- Langfuse dev: 3000
- Langfuse Postgres: 5434
