# AIFlow Project — Claude Code Context

## Overview
Enterprise AI Automation Framework. Python 3.12+, FastAPI, PostgreSQL, Redis.
**v1.5.1 Sprint R** — **CLOSE 2026-05-14**, tag `v1.5.1` queued post-merge, PR opened against `main` (see `docs/sprint_r_pr_description.md`). PromptWorkflow foundation. Multi-step prompt chains become first-class artifacts: YAML descriptor + Pydantic model with full DAG validation (Kahn topological sort, dedup, cycle detection) + 3-layer lookup (cache → Langfuse `workflow:<name>` JSON-typed prompt → local YAML) + admin UI listing/detail/dry-run + per-skill opt-in executor scaffold. **Flag-off default** (`AIFLOW_PROMPT_WORKFLOWS__ENABLED=false`, `AIFLOW_PROMPT_WORKFLOWS__SKILLS_CSV=""`) — zero behaviour change for any skill. **Per-skill code migration explicitly deferred** to S141-FU-1/2/3 to keep Sprint K UC3, Sprint Q UC1, Sprint J UC2 golden paths untouched. Scope delivered across S139-S142: S139 `PromptWorkflow` + `PromptWorkflowStep` + `PromptWorkflowLoader` + `PromptManager.get_workflow()` + `FeatureDisabled` (HTTP 503) + 24 unit tests + example descriptor `prompts/workflows/uc3_intent_and_extract.yaml`; S140 admin UI `/prompts/workflows` page (React 19 + Tailwind v4: table list + DAG-indented detail panel + Test Run dry-run JSON output) + 3-route GET-only router (`prompt_workflows.py` mounted BEFORE prompts router catch-all) + EN/HU locale + sidebar nav + `get_prompt_manager()` extension auto-registers skill prompts when flag is on + 10 router unit tests + OpenAPI snapshot refresh + mid-PR `react-i18next`→`useTranslate` fix (CI-caught); S141 `PromptWorkflowExecutor` scaffold (resolution-only, never invokes LLM, returns None on every failure mode for clean fallback) + `PromptWorkflowSettings.skills_csv` per-skill opt-in (raw string + parsed `.skills` property) + 3 ready-to-consume descriptors (`email_intent_chain` 3 steps, `invoice_extraction_chain` 4 steps with full DAG + cost ceilings, `aszf_rag_chain` 4 steps baseline persona) + 17 unit tests; S142 retro + PR. 0 Alembic migrations, 0 skill code changes, 0 golden-path regressions. Open follow-ups: S141-FU-1/2/3 per-skill migrations (each with golden-path gate), SR-FU-4 live-stack Playwright for workflows page, SR-FU-5 vite-build pre-commit hook, SR-FU-6 Langfuse workflow listing. See `01_PLAN/114_CAPABILITY_ROADMAP_Q_R_S.md` §3 + `docs/sprint_r_retro.md` + `docs/sprint_r_pr_description.md`. Predecessor: **v1.5.0 Sprint Q** — **MERGED 2026-05-10**, PR #29 squash `c4ded1d`, tag `v1.5.0`. Intent + extraction unification. UC3 intent classifier (Sprint P, 4% misclass) now chains into `skills.invoice_processor` on EXTRACT emails; admin UI surfaces vendor/buyer/header/items/totals via new `ExtractedFieldsCard`. First UC1 end-to-end validation since Phase 1d — **85.7% accuracy** on 10-fixture reportlab corpus (target ≥ 80%), invoice_number/vendor/buyer/currency/due_date/gross_total all 100%, only `issue_date` misses systematically (SQ-FU-1). Scope delivered across S135-S138: S135 `UC3ExtractionSettings` flag (`AIFLOW_UC3_EXTRACTION__ENABLED=false` default) + `_maybe_extract_invoice_fields` orchestrator helper + `_intent_class_is_extract` gate (reuses Sprint O FU-2 `_resolve_intent_class`) + lazy import of `skills.invoice_processor.workflows.process` + `asyncio.wait_for(total_budget_seconds)` wrap + per-file error isolation + per-invoice USD budget ceiling + 14 unit + 3 settings + 1 intent-gate + 1 real-stack integration (real PG + real docling + real OpenAI on `001_invoice_march.eml` → `INV-2026-0001`); S136 `EmailDetailResponse.extracted_fields` additive + `ExtractedFieldsCard.tsx` (Tailwind v4, dark-mode, confidence + cost chips, `<details>` line-items expand) + EN/HU locale + 1 Playwright E2E on **live dev stack** (no route mock — seeds DB, hits real API with signed JWT); S137 10-fixture UC1 golden-path corpus (HU/EN/mixed, simple/tabular/multi-section) + `data/fixtures/invoices_sprint_q/{manifest.yaml,generate_invoices.py}` idempotent reportlab generator + `scripts/measure_uc1_golden_path.py` operator script + `docs/uc1_golden_path_report.md` (85.7% accuracy, $0.0004 mean cost, 96 s wall) + `tests/integration/skills/test_uc1_golden_path.py` CI slice (3 fixtures, overall ≥ 75% / invoice_number ≥ 90%); S138 retro + PR. 0 Alembic migrations, 0 new endpoints, 0 new UI pages. Cost per 10-fixture run: ~$0.004. Open follow-ups: SQ-FU-1 `issue_date` prompt/schema fix, SQ-FU-2 pre-boot docling warmup in `make api`, SQ-FU-3 corpus extension to 25, SQ-FU-4 `_parse_date` ISO roundtrip. See `01_PLAN/115_SPRINT_Q_INTENT_EXTRACTION_UNIFICATION.md` + `01_PLAN/114_CAPABILITY_ROADMAP_Q_R_S.md` + `docs/sprint_q_retro.md` + `docs/sprint_q_pr_description.md`. Predecessor: **v1.4.12 Sprint P** — **MERGED 2026-05-06**, PR #25 squash `390d4d5`, tag `v1.4.12`. LLM-fallback + body-only/mixed cohort coverage. Classifier strategy on the attachment-intent flag-on path flips from `SKLEARN_ONLY` to `SKLEARN_FIRST` (new `AIFLOW_UC3_ATTACHMENT_INTENT__CLASSIFIER_STRATEGY` knob, default `sklearn_first`); `_keywords_first` gains a pre-LLM attachment-signal early-return that preserves Sprint O behaviour on NDA/SLA/MSA contracts. Scope delivered across S131-S134: S131 4-combo measurement matrix (strategy × LLM-context) + plan + baseline `docs/uc3_llm_context_baseline.md`; S132 `UC3AttachmentIntentSettings.classifier_strategy` + orchestrator strategy override + `_attachment_signal_is_strong` helper + `_keywords_first` early-return + 10 unit / 2 integration (real OpenAI + real PG) / 1 Playwright E2E (live stack); S133 skipped (S132 already exceeded plan §7 target 4x); S134 retro + PR. Misclass headline: **32% → 4%** on the 25-fixture corpus (87.5% relative drop from Sprint O; 93% drop from the Sprint K 56% body-only baseline). Body_only 3/6 → 6/6, Mixed 3/7 → 6/7, Contract 5/6 → 6/6, Invoice 6/6 unchanged. Only remaining miss: `024_complaint_about_invoice` — legitimate body-vs-attachment conflict (SP-FU-1). 0 Alembic migrations, 0 new endpoints, 0 new UI pages. LLM cost per 25-fixture run: ~$0.002. See `01_PLAN/113_SPRINT_P_LLM_CONTEXT_BODY_MIXED_PLAN.md` + `docs/sprint_p_retro.md` + `docs/sprint_p_pr_description.md`. Predecessor: **v1.4.11 Sprint O** — **MERGED 2026-05-04**, PR #19 squash `ea695cc`, tag `v1.4.11`. UC3 attachment-aware intent (extractor + classifier rule boost + UI). Post-Sprint-O follow-ups all merged: FU-1 (live-API E2E + OpenAPI drift detector, `9cc74b1`), FU-2 (intent_class schema + UI badge, PR #20 `36a0e18`), FU-4 (docling warmup, PR #21 `dc0f2f4`), FU-5 (resilience Clock seam unquarantine), FU-7 (per-attachment cost accounting, PR #22 `bdfe149`). Sprint P closes FU-3 + FU-6. Predecessor: **v1.4.10 Sprint N** — **MERGED 2026-04-29**, PR #18 squash `13a2f08`, tag `v1.4.10`. UC3 attachment-aware intent on `feature/v1.4.11-uc3-attachment-intent` (cut from `main` @ `13a2f08`). Classifier reads PDF/DOCX attachments through reused `AttachmentProcessor`; flag-gated (`AIFLOW_UC3_ATTACHMENT_INTENT__ENABLED=false`, `__LLM_CONTEXT=false` defaults). Scope delivered across S126-S130: S126 25-fixture corpus + Sprint K body-only baseline **56% misclass / 40% manual-review-like / p95 95ms** (GATE PASS); S127 pure-function `extract_attachment_features` + `AttachmentFeatures` + flag-gated orchestrator hook (lazy `AttachmentProcessor` import + `asyncio.wait_for(total_budget_seconds)`); S128 `ClassifierService.classify(... context=None)` + signal-aligned EXTRACT rule boost (`invoice_number_detected → invoice_received`, `keyword_buckets["contract"] → order`, body-label gate `unknown ∪ EXTRACT_INTENT_IDS` to protect non-EXTRACT body labels) + opt-in LLM-context system message; S129 `AttachmentSignalsCard` + EN/HU locales + `EmailDetailResponse.attachment_features/classification_method` extension + 1 Playwright E2E (route-mocked); S130 retro + PR. Misclass headline: **56% → 32%** (24 pts absolute / 42.9% relative drop), invoice_attachment 6/6 + contract_docx 5/6, body_only/mixed unchanged (no attachment to help). 0 Alembic migrations. Open follow-ups: `make api` restart for live API surface, `intent.intent_class` schema field, body-only/mixed cohort coverage (Sprint P), docling p95 cold-start (Sprint J carry), resilience `Clock` seam (Sprint J carry, deadline 4 days past), LLM-context fixture measurement, per-attachment cost accounting. See `01_PLAN/112_SPRINT_O_UC3_ATTACHMENT_INTENT_PLAN.md` + `docs/sprint_o_retro.md` + `docs/sprint_o_pr_description.md`. Predecessor: **v1.4.10 Sprint N** — **MERGED 2026-04-29**, PR #18 squash `13a2f08`, tag `v1.4.10`. LLM cost guardrail + per-tenant budget. S125 post-merge coverage uplift landed (+83 tools tests, 65.6%→68.5% local; `email_parser.py` Linux OSError guard). Predecessor: **v1.4.10 Sprint N** — **MERGED 2026-04-29**, PR #18 squash `13a2f08`, tag `v1.4.10`. LLM cost guardrail + per-tenant budget. S125 post-merge coverage uplift landed (+83 tools tests, 65.6%→68.5% local; `email_parser.py` Linux OSError guard). Predecessors: **v1.4.9 Sprint M** — **MERGED 2026-04-29**, PR #17 squash `94750d9`, tag `v1.4.9`. Vault hvac + self-hosted Langfuse + air-gap Profile A. **v1.4.8 Sprint L** Monitoring + Cost Enforcement (MERGED 2026-04-23, PR #16, squash `ab63c93`, tag `v1.4.8`); **v1.4.7 Sprint K** UC3 Email Intent (MERGED 2026-04-20, PR #15, squash `2eecb20`, tag `v1.4.7`); **v1.4.5 Sprint J** UC2 RAG (queued); **v1.4.3** Phase 1d (MERGED 2026-04-24, PR #9, tag `v1.4.3-phase-1d`). | API: 8102 | UI: 5173 | Vault dev: 8210 | Langfuse dev: 3000 | Langfuse Postgres: 5434

## Structure
```
src/aiflow/         — Framework: core, engine, api, services, pipeline, guardrails, security
skills/             — 8 skill: aszf_rag_chat, cubix_course_capture, email_intent_processor, invoice_finder, invoice_processor, process_documentation, qbpp_test_automation, spec_writer
aiflow-admin/       — React 19 + Tailwind v4 + Vite (admin dashboard, 24 pages)
01_PLAN/            — Plans (58_POST_SPRINT_HARDENING_PLAN.md = CURRENT)
tests/              — unit/, integration/, e2e/
.claude/skills/     — 6 skill: aiflow-ui-pipeline, aiflow-testing, aiflow-pipeline, aiflow-services, aiflow-database, aiflow-observability
.claude/agents/     — 4 agent: architect, security-reviewer, qa-tester, plan-validator
.claude/commands/   — 27 slash command (Sprint D workflow, DOHA-aligned)
session_prompts/    — Session prompt archive + NEXT.md pointer (/next reads this)
```

## Key Numbers
27 services | 193 API endpoints (30 routers — Sprint R S140 adds `prompt-workflows`) | 50 DB tables | 45 Alembic migrations (head: 045 — Sprint N S121 `tenant_budgets` additive table with `(tenant_id, period)` unique, `limit_usd >= 0`, `alert_threshold_pct integer[]`)
22 pipeline adapters | 10 pipeline templates | 8 skills (aszf_rag_chat, cubix_course_capture, email_intent_processor, invoice_finder, invoice_processor, process_documentation, qbpp_test_automation, spec_writer) | 25 UI pages | 5 source adapters (Email, File, Folder, Batch, API)
3 embedder providers (BGE-M3 Profile A, Azure OpenAI Profile B, OpenAI surrogate) | 1 chunker provider (UnstructuredChunker) | 5 provider-registry ABC slots (parser, classifier, extractor, embedder, chunker)
2347 unit tests (Sprint R S139 +24 PromptWorkflow model/loader/manager/settings + S140 +10 prompt-workflows router + S141 +17 PromptWorkflowExecutor/skills_csv; Sprint Q S135 +18 extraction-wiring/settings/intent-gate; Sprint P S132 +10 strategy-switch + early-return; Sprint O FU-7 +12 per-attachment cost; Sprint O FU-4 +7 docling warmup; Sprint O FU-2 +7 intent_class resolver; Sprint O S127 +22 attachment-features/wiring + S128 +23 rule-boost/LLM-context; S125 +83 tools/* coverage uplift: shell/email_parser/schema_registry/attachment_processor/human_loop/azure_doc_intelligence/playwright_browser/robotframework_runner; Sprint N S121: +16 tenant_budgets + S122: +24 cost_preflight/estimator/wiring; Sprint M S116: +22 VaultProvider + S117: +13 VaultSettings/resolver; 1 xfail-quarantined: resilience 50ms timing flake) | 129 guardrail tests | 97 security tests | 96 promptfoo test cases | 429 E2E tests (169 pre-existing + 199 Phase 1a + 35 Phase 1b + 7 Phase 1d + 3 UC2 S102 + 3 Sprint L S111 Monitoring + 2 Sprint M S118 air-gap skip-by-default + 2 Sprint N S123 budget-management + 1 Sprint O S129 attachment-signals + 1 Sprint P S132 strategy-switch + 1 Sprint O FU-1 live-API + 1 Sprint O FU-2 intent-class-badge + 1 Sprint O FU-5 resilience-clock + 1 Sprint O FU-7 per-attachment-cost + 1 Sprint Q S136 extracted-fields-card) | ~103 integration tests (incl. 4 alembic association_mode + 3 alembic 040/041/042 + 5 rag_engine UC2 + 1 UC3 scan_and_classify + 1 UC3 intent_routing + 5 UC3 intent_rules_crud + 5 S109b prompt_edit + 5 S111 trace+span-metrics + 3 S112 cost_cap_enforcement + 10 Sprint M S116 vault-provider-live + 3 Sprint M S117 resolver-live + 1 Sprint M S117 resolver-disabled + 2 Sprint N S121 alembic 045 + 3 Sprint N S121 tenant_budgets_api + 3 Sprint N S122 cost_preflight_guardrail + 1 Sprint O S128 UC3 attachment-intent classify + 2 Sprint P S132 strategy-switch-contract + 1 Sprint Q S135 extraction_real + 1 Sprint Q S137 uc1-golden-path-slice) | 7 UC golden-path E2E (4 Sprint K UC3 emails + 3 Sprint L S111 Monitoring/Runs) | `ci-cross-uc` suite (Sprint L S113): 42 tests, 19s wall-clock (UC1 invoice + UC2 RAG + UC3 email + UC4 monitoring/costs)

## Build & Test
```bash
make api            # FastAPI hot reload
make test           # Unit tests
make lint           # ruff + format
pytest tests/unit/ -v                     # Specific tests
cd aiflow-admin && npx tsc --noEmit       # TypeScript check
alembic upgrade head                      # DB migrations
```

## Code Conventions
- **Async-first** — all I/O is async (await)
- **Pydantic everywhere** — config, API models, step I/O, DB schemas
- **structlog** — never print(), always `logger.info("event", key=value)`
- **Steps** — `@step` decorator, typed BaseModel I/O, stateless
- **Prompts** — YAML only (never hardcode), Langfuse sync, Jinja2 templates
- **Errors** — inherit AIFlowError with `is_transient` flag for retry
- **DB changes** — ALWAYS Alembic (never raw SQL), `nullable=True` for new columns
- **Auth** — PyJWT RS256 (NOT python-jose), bcrypt (NOT passlib), API key prefix `aiflow_sk_`
- **Package manager** — uv (NOT pip, NOT poetry), lockfile: uv.lock
- **Services in Docker** (PostgreSQL 5433, Redis 6379, Kroki 8000), Python code locally from .venv

## Git Workflow
- Base: `main` @ tag `v1.4.3-phase-1d` (Phase 1d merged 2026-04-24, PR #9). Sprint J PR queued for tag `v1.4.5-sprint-j-uc2`. Phase 1c merged 2026-04-16, tag `v1.4.2-phase-1c`. Future work cuts a fresh feature branch from `main` after Sprint J merge. NEVER commit to main directly.
- Commits: conventional (`feat`, `fix`, `docs`, `refactor`) + Co-Authored-By
- NEVER commit: .env, credentials, API keys, failing tests
- Before commit: `/regression` + `/lint-check`

## Current Plan
`01_PLAN/110_USE_CASE_FIRST_REPLAN.md` — ACTIVE use-case-first replan (UC1 Sprint I v1.4.5, UC2 Sprint J v1.4.6 DONE, UC3 Sprint K v1.4.7 next, Sprint L v1.4.8 cross-cutting, Sprint M v1.4.9 DONE, Sprint N v1.4.10 DONE). Policy: every sprint closes with exactly one use-case end-to-end green.

`01_PLAN/111_SPRINT_N_COST_GUARDRAIL_BUDGET_PLAN.md` Sprint N — **DONE 2026-04-28**, tag `v1.4.10` (queued post-merge), PR opened against `main` queued behind Sprint M PR #17 (see `docs/sprint_n_pr_description.md`). Scope delivered across S120-S124: S120 cost-surface inventory (5 recorder / 2 cap-check / 4 aggregation / 2 config / **0 pre-flight** — the GAP) + Sprint N plan doc + `docs/sprint_n_plan.md` + CLAUDE.md banner; S121 Alembic 045 `tenant_budgets` (UUID PK, `(tenant_id, period)` unique, `CHECK period IN ('daily','monthly')`, `CHECK limit_usd >= 0`, `alert_threshold_pct integer[]`, `enabled`, timestamps) + `TenantBudgetService` (`get` / `list` / `upsert` / `delete` / `get_remaining` over `CostAttributionRepository.aggregate_running_cost`) + `/api/v1/tenants/{tenant_id}/budget[/{period}]` router (list / get / upsert / delete, `Annotated` path validators, `TenantBudgetUpsertRequest` threshold `[1,100]` validator with dedup+sort, `BudgetView` live projection) + 16 unit / 2 Alembic integration / 3 API integration; S122 `CostEstimator` (wraps `litellm.cost_per_token` + per-tier fallback) + `CostPreflightGuardrail` + `PreflightDecision` + `PreflightReason` enum (pure decision, caller raises) + `CostGuardrailRefused` error (HTTP 429, structured `{refused, tenant_id, projected_usd, remaining_usd, period, reason, dry_run}` payload) + 3 wiring points (`pipeline/runner.py` step-count scaled, `services/rag_engine/service.py` above the existing S112 reactive cap, `models/client.py` LLM-client backstop via optional `tenant_id=` kwarg) + `CostGuardrailSettings` (env prefix `AIFLOW_COST_GUARDRAIL__`, `enabled=false` / `dry_run=true` defaults) + 24 unit / 3 integration (real Postgres: under-budget / over-budget-enforced / over-budget-dry-run); S123 `/budget-management` admin page (`BudgetCard` + `ThresholdEditor` React Aria chip input + `types.ts` mirroring contracts + `aiflow.menu.budgets` Monitoring nav + EN/HU locales + deep-link `?tenant=`) + 2 Python Playwright E2E (`test_budget_management.py` render round-trip + edit + hard-reload regression) + `/live-test` PASS report (`tests/ui-live/budget-management.md`); S124 Sprint close — `docs/sprint_n_retro.md` (scope, test deltas, decisions log SN-1..SN-7, 12 follow-ups) + `docs/sprint_n_pr_description.md` + CLAUDE.md numbers (189→190 endpoints / 28→29 routers / 44→45 Alembic / 2073→2113 unit / 422→424 E2E / 23→24 UI pages) + PR cut against `main` with Sprint M PR #17 rebase dependency noted. 1 Alembic migration (045 additive). Open follow-ups: `CostAttributionRepository` ↔ `record_cost` consolidation, model-tier fallback ceilings → `CostGuardrailSettings`, Grafana panel for `cost_guardrail_refused` vs `cost_cap_breached`, litellm pricing coverage audit as CI step, `/status` OpenAPI tag diff to catch stale-uvicorn, `CostSettings` umbrella (consolidate `BudgetSettings` + `CostGuardrailSettings`), soft-quota / over-draft semantics, `scripts/seed_tenant_budgets_dev.py`. Carried: Sprint M (live rotation E2E, `AIFLOW_ENV=prod` guard, `make langfuse-bootstrap`, AppRole prod IaC, Langfuse v3→v4, `SecretProvider` registry slot); Sprint J (BGE-M3 weight cache, Profile B live, resilience `Clock` seam deadline 2026-04-30, coverage issue #7).

`01_PLAN/110_USE_CASE_FIRST_REPLAN.md` §5 Sprint M — **DONE 2026-04-25**, tag `v1.4.9` (queued post-merge), PR opened against `main` (see `docs/sprint_m_pr_description.md`). Scope delivered across S115-S119: S115 `docker-compose.vault.yml` (dev port 8210) + `docs/secrets_inventory.md` (15 secrets cataloged) + `docs/sprint_m_plan.md`; S116 `VaultSecretProvider` (hvac KV v2 + `path#field` grammar + token/AppRole auth) + `VaultTokenRotator` (plain threading, APScheduler 4.x alpha rejected) + `SecretManager.fallback` + negative-cache TTL (+22 unit / +10 live-vault integration tests); S117 `VaultSettings` nested config + `aiflow.security.resolver.get_secret_manager()` singleton + `env_alias=` namespace mapping + 7 consumer migrations (OpenAI / AzureOpenAI / AzureDI + docling 3-alias / Langfuse / webhook HMAC / JWT PEMs / DB DSN) + `scripts/seed_vault_dev.py` (+13 unit / +4 resolver-live tests); S118 self-hosted Langfuse v3 + Postgres 16 overlay (ports 3000 / 5434) + `scripts/bootstrap_langfuse.py` TRPC keypair discovery + air-gap Profile A E2E harness (2 tests, skip-by-default, `socket.getaddrinfo` allow-list guard) + `docs/airgapped_deployment.md` operator runbook; S119 Sprint close — `docs/sprint_m_retro.md` + `docs/runbooks/vault_rotation.md` + `docs/sprint_m_pr_description.md` + CLAUDE.md numbers. 0 Alembic migrations (code/infra only). Open follow-ups: live rotation E2E, `AIFLOW_ENV=prod` root-token guard, `make langfuse-bootstrap` target, AppRole prod IaC example, Langfuse v4 self-host migration, `SecretProvider` slot on `ProviderRegistry`, BGE-M3 weight cache as CI artifact (carried from Sprint J), resilience `Clock` seam (carried, deadline 2026-04-30), Azure OpenAI Profile B live (credits pending), Playwright `--network=none` variant.

`01_PLAN/110_USE_CASE_FIRST_REPLAN.md` §4 Sprint J — **DONE 2026-04-25**, tag `v1.4.5-sprint-j-uc2` (queued), PR opened against `main`. Scope delivered across S100-S104: S100 `EmbedderProvider` ABC + BGE-M3 (Profile A) + Azure OpenAI (Profile B) + `EmbeddingDecision` + Alembic 040 + `PolicyEngine.pick_embedder`; S101 `ChunkerProvider` ABC (5th registry slot) + `UnstructuredChunker` + rag_engine opt-in provider-registry ingest path + Alembic 041 `rag_chunks.embedding_dim`; S102 UC2 RAG UI (`ChunkViewer` + chunks API provenance fields + 3 Playwright E2E); S103 retrieval baseline (pgvector flex-dim Alembic 042 + `OpenAIEmbedder` Profile B surrogate + live MRR@5 ≥ 0.55 both profiles + `scripts/bootstrap_bge_m3.py` + reranker OSError fallback); S104 resilience flake quarantine + retro + PR cut + tag. Artifacts: `docs/sprint_j_retro.md`, `docs/sprint_j_pr_description.md`, `docs/quarantine.md`. Open follow-ups: `query()` refactor to provider registry (1024-dim collections not queryable yet — Sprint K S105); reranker model preload script; Azure OpenAI Profile B live (credits pending); resilience `Clock` seam (quarantine fix deadline 2026-04-30); BGE-M3 weight cache as CI artifact; PII redaction gate (deferred to Sprint K UC3); coverage uplift (issue #7, 65.67%→80% trajectory per replan §7). Predecessor: **v1.4.3 Phase 1d** MERGED 2026-04-24, tag `v1.4.3-phase-1d`, PR #9 / `0d669aa` (adapter orchestration + IntakePackageSink).

## Session Workflow (DOHA-aligned)

**Manuális:**
```
/clear → /next → [session munka] → /session-close → /clear → /next → ...
```
- `/next` beolvassa `session_prompts/NEXT.md`-t és elindítja a session-t
- `/session-close` generálja `session_prompts/NEXT.md` + archív másolat
- SessionStart hook kiírja ha van kész NEXT.md

**Auto-sprint (autonóm lánc, DOHA mintára):**
```
/auto-sprint max_sessions=16 notify=stop_only
```
- Egy indítás után végigfut a queue-olt session-eken `ScheduleWakeup ~90s` loop-pal
- STOP feltételen vagy `max_sessions` cap-en megáll, log entry-vel
- State: `session_prompts/.auto_sprint_state.json` (gitignored, durable)
- Log: `session_prompts/.notifications.log` (gitignored, append-only — `tail -f`-elheted)
- Default file-log mode (`AIFLOW_AUTOSPRINT_NO_EMAIL=1` a `.claude/settings.json`-ban)
- Helper: `scripts/send_notification.py --kind {info|done|stop|cap} --subject ... --body ...`
- Reference (Gmail variant, Phase 2): `DOHA/01_PLAN/19_DOHA_AUTO_SPRINT_GUIDE.md`

## Slash Commands

**Session lifecycle:** `/next` → `/status` → `/implement` → `/dev-step` → `/review` → `/session-close`
**Auto session:** `/auto-sprint max_sessions=N notify=stop_only|all` (autonóm lánc, lásd Session Workflow)
**Quick checks:** `/smoke-test`, `/regression`, `/lint-check`, `/live-test <module>` (UI browser journey Playwright MCP-n át)
**Prompts:** `/new-prompt`, `/prompt-tuning`, `/quality-check`
**Services:** `/service-test`, `/service-hardening`, `/pipeline-test`, `/new-pipeline`
**Generators:** `/new-step`, `/new-test`
**UI (order!):** `/ui-journey` → `/ui-api-endpoint` → `/ui-design` → `/ui-page` / `/ui-component`
**Plans:** `/update-plan`, `/validate-plan`

## IMPORTANT

- **REAL testing only** — never mock PostgreSQL/Redis/LLM. Docker for real services.
- **Session end:** `/session-close` generates next session prompt (DOHA-style chaining)
- **After EVERY session:** `/update-plan` → progress table + key numbers
- **UI work:** 7 HARD GATES enforced — see skill `aiflow-ui-pipeline`
- **A feature is DONE only after** Playwright E2E passes with real data
- **UI változás után KÖTELEZŐ `/live-test <module>`** — session-time browser journey a Playwright MCP-n át (`tests/ui-live/`). NEM helyettesíti a CI specet, de minden UI PR-ban friss riport kell mellette.
- **Detailed testing rules:** see skill `aiflow-testing` (auto-loaded when testing)
- **Pipeline dev rules:** see skill `aiflow-pipeline` (auto-loaded for pipeline work)
- **Service conventions:** see skill `aiflow-services` (auto-loaded for service work)
- **Best practices reference:** `01_PLAN/60_CLAUDE_CODE_BEST_PRACTICES_REFERENCE.md`
- **DB changes:** see skill `aiflow-database` (Alembic rules, zero-downtime migration)
- **Observability:** see skill `aiflow-observability` (structlog, Langfuse, metrics)
- **Architecture review:** use agent `architect` for Go/No-Go decisions

## v2 Architecture (Phase 1a — next sprint)
- 13 Pydantic domain contracts (IntakePackage, RoutingDecision, ExtractionResult...)
- 7 state machines with idempotent replay
- Multi-tenant isolation (tenant_id boundary on DB + storage + API)
- Cost-aware routing (policy constraints + cost cap)
- Provider abstraction (parser/classifier/extractor/embedder pluggable)
- Plans: `01_PLAN/100_*` through `01_PLAN/106_*`

## IMPORTANT: On Compaction
Preserve: modified files list + test status + current C-phase + which command was running.

## References
- v2 Architecture: `01_PLAN/100_AIFLOW_v2_ARCHITECTURE_REFINEMENT_OVERVIEW.md` (+ 100_b through 106)
- Sprint C plan: `01_PLAN/65_SPRINT_C_UI_JOURNEY_FIRST_PLAN.md`
- Sprint B plan: `01_PLAN/58_POST_SPRINT_HARDENING_PLAN.md`
- Best practices: `01_PLAN/60_CLAUDE_CODE_BEST_PRACTICES_REFERENCE.md`
- DOHA governance patterns: `DOHA/design_claude/` (reference implementation)
- Full CLAUDE.md backup: `.claude/CLAUDE_v1.2.2_FULL_BACKUP.md`
