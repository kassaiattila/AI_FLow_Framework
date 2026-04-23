# AIFlow Project — Claude Code Context

## Overview
Enterprise AI Automation Framework. Python 3.12+, FastAPI, PostgreSQL, Redis.
**v1.4.8 Sprint L** — Monitoring + Cost Enforcement, PR queued against `main`, tag `v1.4.8` queued (S111-S113 on `feature/v1.4.8-monitoring-cost`). Predecessors: **v1.4.5 Sprint J** UC2 RAG (queued), **v1.4.3** Phase 1d (MERGED 2026-04-24, PR #9, tag `v1.4.3-phase-1d`). | API: 8102 | UI: 5173

## Structure
```
src/aiflow/         — Framework: core, engine, api, services, pipeline, guardrails, security
skills/             — 8 skill: aszf_rag_chat, cubix_course_capture, email_intent_processor, invoice_finder, invoice_processor, process_documentation, qbpp_test_automation, spec_writer
aiflow-admin/       — React 19 + Tailwind v4 + Vite (admin dashboard, 23 pages)
01_PLAN/            — Plans (58_POST_SPRINT_HARDENING_PLAN.md = CURRENT)
tests/              — unit/, integration/, e2e/
.claude/skills/     — 6 skill: aiflow-ui-pipeline, aiflow-testing, aiflow-pipeline, aiflow-services, aiflow-database, aiflow-observability
.claude/agents/     — 4 agent: architect, security-reviewer, qa-tester, plan-validator
.claude/commands/   — 27 slash command (Sprint D workflow, DOHA-aligned)
session_prompts/    — Session prompt archive + NEXT.md pointer (/next reads this)
```

## Key Numbers
27 services | 189 API endpoints (28 routers — S112 adds `costs.cap_status`) | 50 DB tables | 44 Alembic migrations (head: 044 — Sprint L S112 follow-up: cost_records.workflow_run_id → NULL-able for tenant-level cap aggregation)
22 pipeline adapters | 10 pipeline templates | 8 skills (aszf_rag_chat, cubix_course_capture, email_intent_processor, invoice_finder, invoice_processor, process_documentation, qbpp_test_automation, spec_writer) | 23 UI pages | 5 source adapters (Email, File, Folder, Batch, API)
3 embedder providers (BGE-M3 Profile A, Azure OpenAI Profile B, OpenAI surrogate) | 1 chunker provider (UnstructuredChunker) | 5 provider-registry ABC slots (parser, classifier, extractor, embedder, chunker)
2002 unit tests (1 xfail-quarantined: resilience 50ms timing flake) | 129 guardrail tests | 97 security tests | 96 promptfoo test cases | 420 E2E tests (169 pre-existing + 199 Phase 1a + 35 Phase 1b + 7 Phase 1d + 3 UC2 S102 + 3 Sprint L S111 Monitoring) | 75+ integration tests (incl. 4 alembic association_mode + 3 alembic 040/041/042 + 5 rag_engine UC2 + 1 UC3 scan_and_classify + 1 UC3 intent_routing + 5 UC3 intent_rules_crud + 5 S109b prompt_edit + 5 S111 trace+span-metrics + 3 S112 cost_cap_enforcement) | 7 UC golden-path E2E (4 Sprint K UC3 emails + 3 Sprint L S111 Monitoring/Runs) | `ci-cross-uc` suite (Sprint L S113): 42 tests, 19s wall-clock (UC1 invoice + UC2 RAG + UC3 email + UC4 monitoring/costs)

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
`01_PLAN/110_USE_CASE_FIRST_REPLAN.md` — ACTIVE use-case-first replan (UC1 Sprint I v1.4.5, UC2 Sprint J v1.4.6 DONE, UC3 Sprint K v1.4.7 next, Sprint L v1.4.8 cross-cutting). Policy: every sprint closes with exactly one use-case end-to-end green.

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
