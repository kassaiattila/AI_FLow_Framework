# AIFlow Project — Claude Code Context

## Overview
Enterprise AI Automation Framework. Python 3.12+, FastAPI, PostgreSQL, Redis.
**v1.4.3** — Phase 1d Adapter Orchestration MERGED 2026-04-24 (PR #9, tag `v1.4.3-phase-1d`, G0.1-G0.8) | API: 8102 | UI: 5174

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
27 services | 177 API endpoints (27 routers) | 49 DB tables | 37 Alembic migrations
22 pipeline adapters | 10 pipeline templates | 7 skills | 23 UI pages | 5 source adapters (Email, File, Folder, Batch, API)
1886 unit tests | 129 guardrail tests | 97 security tests | 96 promptfoo test cases | 403 E2E tests (169 pre-existing + 199 Phase 1a + 35 Phase 1b) | 42 integration tests (incl. 4 alembic association_mode)

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
- Base: `main` @ tag `v1.4.3-phase-1d` (Phase 1d merged 2026-04-24, PR #9). Phase 1c merged 2026-04-16, tag `v1.4.2-phase-1c`. Future work cuts a fresh feature branch from `main`. NEVER commit to main directly.
- Commits: conventional (`feat`, `fix`, `docs`, `refactor`) + Co-Authored-By
- NEVER commit: .env, credentials, API keys, failing tests
- Before commit: `/regression` + `/lint-check`

## Current Plan
`01_PLAN/session_S80_v1_4_3_phase_1d_kickoff.md` — **Phase 1d MERGED 2026-04-24**, tag `v1.4.3-phase-1d`, PR #9 merge commit `0d669aa`. Scope delivered: G0.1 writer audit + kickoff, G0.2 Email adapter + `IntakePackageSink` + associator helper extraction, G0.3 File + Folder adapters + `upload_package` HTTP collapse + sink label fix + autouse pool reset conftest, G0.4 Batch + Api adapters, G0.5 multi_source_e2e triage (sink-routed), G0.6 webhook router sink wiring (Path A) + status 202→201, G0.7 G-matrix evidence + PR draft + issue #7 decision, G0.8 OpenAPI drift regen + PR cut + tag + retro. Artifacts: `docs/phase_1d_pr_description.md`, `docs/phase_1d_retro.md`. Open follow-ups: issue #7 (coverage 65.67%→80%) DEFERRED to v1.4.4; stale `test_alembic_034` assertion queued for v1.4.4. Predecessor: Phase 1c MERGED, tag `v1.4.2-phase-1c`, PR #6.

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
