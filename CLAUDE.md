# AIFlow Project — Claude Code Context

## Overview
Enterprise AI Automation Framework. Python 3.12+, FastAPI, PostgreSQL, Redis.
Branch: `feature/v1.3.0-service-excellence` | API: 8102 | UI: 5174

## Structure
```
src/aiflow/         — Framework: core, engine, api, services, pipeline, guardrails, security
skills/             — 5 skill: process_docs, aszf_rag, email_intent, invoice, cubix
aiflow-admin/       — React 19 + Tailwind v4 + Vite (admin dashboard, 22 pages)
01_PLAN/            — Plans (58_POST_SPRINT_HARDENING_PLAN.md = CURRENT)
tests/              — unit/, integration/, e2e/
.claude/skills/     — 4 skill: aiflow-ui-pipeline, aiflow-testing, aiflow-pipeline, aiflow-services
.claude/agents/     — 3 agent: security-reviewer, qa-tester, plan-validator
.claude/commands/   — 20 slash command (Sprint B workflow)
```

## Key Numbers
26 services | 165 API endpoints (25 routers) | 46 DB tables | 29 Alembic migrations
18 pipeline adapters | 6 pipeline templates | 5 skills | 22 UI pages
1164 unit tests | 76 guardrail tests | 97 security tests | 54 promptfoo test cases

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
- Branch: `feature/v1.3.0-service-excellence` — NEVER commit to main directly
- Commits: conventional (`feat`, `fix`, `docs`, `refactor`) + Co-Authored-By
- NEVER commit: .env, credentials, API keys, failing tests
- Before commit: `/regression` + `/lint-check`

## Current Plan
`01_PLAN/58_POST_SPRINT_HARDENING_PLAN.md` — Sprint B (B0-B11), v1.3.0

## Slash Commands

**Every task:** `/dev-step`, `/regression`, `/lint-check`
**Prompts:** `/new-prompt`, `/prompt-tuning`, `/quality-check`
**Services:** `/service-test`, `/service-hardening`, `/pipeline-test`, `/new-pipeline`
**Generators:** `/new-step`, `/new-test`
**UI (order!):** `/ui-journey` → `/ui-api-endpoint` → `/ui-design` → `/ui-page` / `/ui-component`
**Plans:** `/update-plan`, `/validate-plan`

## IMPORTANT

- **REAL testing only** — never mock PostgreSQL/Redis/LLM. Docker for real services.
- **After EVERY session:** `/update-plan` → 58 progress table + key numbers
- **UI work:** 7 HARD GATES enforced — see skill `aiflow-ui-pipeline`
- **A feature is DONE only after** Playwright E2E passes with real data
- **Detailed testing rules:** see skill `aiflow-testing` (auto-loaded when testing)
- **Pipeline dev rules:** see skill `aiflow-pipeline` (auto-loaded for pipeline work)
- **Service conventions:** see skill `aiflow-services` (auto-loaded for service work)
- **Best practices reference:** `01_PLAN/60_CLAUDE_CODE_BEST_PRACTICES_REFERENCE.md`

## IMPORTANT: On Compaction
Preserve: modified files list + test status + current B-phase + which command was running.

## References
- Sprint B plan: `01_PLAN/58_POST_SPRINT_HARDENING_PLAN.md`
- Command audit: `01_PLAN/59_COMMAND_WORKFLOW_AUDIT.md`
- Best practices: `01_PLAN/60_CLAUDE_CODE_BEST_PRACTICES_REFERENCE.md`
- Gap analysis: `01_PLAN/60_GAP_ANALYSIS_AND_ACTION_PLAN.md`
- Full CLAUDE.md backup: `.claude/CLAUDE_v1.2.2_FULL_BACKUP.md`
