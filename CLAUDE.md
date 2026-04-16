# AIFlow Project — Claude Code Context

## Overview
Enterprise AI Automation Framework. Python 3.12+, FastAPI, PostgreSQL, Redis.
**v1.4.1** — Phase 1b Source Adapters MERGED (tag `v1.4.1-phase-1b`, 2026-05-08) | API: 8102 | UI: 5174

## Structure
```
src/aiflow/         — Framework: core, engine, api, services, pipeline, guardrails, security
skills/             — 7 skill: process_docs, aszf_rag, email_intent, invoice_processor, invoice_finder, cubix, spec_writer
aiflow-admin/       — React 19 + Tailwind v4 + Vite (admin dashboard, 23 pages)
01_PLAN/            — Plans (58_POST_SPRINT_HARDENING_PLAN.md = CURRENT)
tests/              — unit/, integration/, e2e/
.claude/skills/     — 6 skill: aiflow-ui-pipeline, aiflow-testing, aiflow-pipeline, aiflow-services, aiflow-database, aiflow-observability
.claude/agents/     — 4 agent: architect, security-reviewer, qa-tester, plan-validator
.claude/commands/   — 27 slash command (Sprint D workflow, DOHA-aligned)
session_prompts/    — Session prompt archive + NEXT.md pointer (/next reads this)
```

## Key Numbers
27 services | 176 API endpoints (27 routers) | 49 DB tables | 35 Alembic migrations
22 pipeline adapters | 10 pipeline templates | 7 skills | 23 UI pages | 5 source adapters (Email, File, Folder, Batch, API)
1872 unit tests | 129 guardrail tests | 97 security tests | 96 promptfoo test cases | 403 E2E tests (169 pre-existing + 199 Phase 1a + 35 Phase 1b) | 38 integration tests

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
- Branch: `main` (Phase 1b merged 2026-05-08, tag `v1.4.1-phase-1b`). Next feature branch: Phase 1c association backfill. NEVER commit to main directly.
- Commits: conventional (`feat`, `fix`, `docs`, `refactor`) + Co-Authored-By
- NEVER commit: .env, credentials, API keys, failing tests
- Before commit: `/regression` + `/lint-check`

## Current Plan
`01_PLAN/session_S55_v1_4_1_phase_1b_sources_kickoff.md` — Phase 1b MERGED (2026-05-08, tag `v1.4.1-phase-1b`, PR #4). Next: Phase 1c (association backfill + G5/G8 follow-up tickets: issue #3 OpenAPI regen, issue #5 CI hygiene).

## Session Workflow (DOHA-aligned)
```
/clear → /next → [session munka] → /session-close → /clear → /next → ...
```
- `/next` beolvassa `session_prompts/NEXT.md`-t és elindítja a session-t
- `/session-close` generálja `session_prompts/NEXT.md` + archív másolat
- SessionStart hook kiírja ha van kész NEXT.md

## Slash Commands

**Session lifecycle:** `/next` → `/status` → `/implement` → `/dev-step` → `/review` → `/session-close`
**Quick checks:** `/smoke-test`, `/regression`, `/lint-check`
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
