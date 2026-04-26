# AIFlow Project — Claude Code Context

## Overview

Enterprise AI Automation Framework. Python 3.12+, FastAPI, PostgreSQL, Redis.
**Latest tag:** `v1.7.0` (Sprint W, queued). **Current sprint:** Sprint X
"UC1 + UC3 + DocRecognizer Quality Push" (`v1.8.0`, in progress).

**Use-case status snapshot (2026-04-26):**
- UC1 invoice extraction: 85.7% / 10-fixture synthetic — Sprint X SX-2 push to ≥ 92%
- UC2 RAG chat: MRR@5 = 0.55 baseline — Sprint Y push to ≥ 0.72
- UC3 email intent: 4% misclass / 25-fixture — Sprint X SX-4 push to ≤ 1%
- DocRecognizer: 100% / synthetic 8-fixture — Sprint X SX-3 push to real-corpus ≥ 80%

**Binding policy:** every sprint closes with measurable quality improvement on
exactly one use-case. See `docs/honest_alignment_audit.md` for the drift recap
and `01_PLAN/110_USE_CASE_FIRST_REPLAN.md` for the original policy.

For sprint-by-sprint trajectory: `docs/SPRINT_HISTORY.md`.

## Structure

```
src/aiflow/         — Framework: core, engine, api, services, pipeline, guardrails, security
skills/             — 8 skills (aszf_rag_chat, document_recognizer, email_intent_processor, invoice_processor, ...)
aiflow-admin/       — React 19 + Tailwind v4 + Vite (admin dashboard, 27 pages)
01_PLAN/            — Plans (121_SPRINT_X_QUALITY_PUSH_PLAN.md = CURRENT, ROADMAP.md = forward queue)
tests/              — unit/, integration/, e2e/, ui-live/ (markdown journey scripts)
data/doctypes/      — DocRecognizer doctype YAML descriptors (5 doctypes)
data/fixtures/      — Test corpus per use-case
prompts/workflows/  — PromptWorkflow YAML descriptors (6 chains)
docs/               — retros, runbooks, audit docs, SPRINT_HISTORY.md
.claude/skills/     — 6 skills (aiflow-{ui-pipeline,testing,pipeline,services,database,observability})
.claude/agents/     — 4 agents (architect, security-reviewer, qa-tester, plan-validator)
.claude/commands/   — 27 slash commands
session_prompts/    — _TEMPLATE.md (mandatory Quality target header), NEXT.md (current), archive/
scripts/            — operator scripts (5/5 on uniform argparse_output --output flag), run_quality_baseline.sh
```

## Key numbers (snapshot)

- 27 services | 201 API endpoints (32 routers) | 51 DB tables | 49 Alembic migrations (head: 049)
- 6 PromptWorkflow descriptors | 5 DocType descriptors | 8 skills | 27 admin UI pages
- 22 pipeline adapters | 10 pipeline templates | 5 source adapters
- 3 embedder providers (BGE-M3, Azure OpenAI, OpenAI surrogate) | 1 chunker | 5 ProviderRegistry slots
- 2641 unit tests | ~116 integration | 430 E2E | 7 UC golden-path | ci-cross-uc 42-test suite
- 5 ci.yml jobs | 6 nightly-regression.yml jobs | 1 pre-commit hook
- AIFLOW_ENVIRONMENT=prod boot guard (Sprint W) refuses Vault root tokens

For per-sprint trajectory (Sprint J–W) see `docs/SPRINT_HISTORY.md`.

## Build & Test

```bash
make api                                  # FastAPI hot reload
make test                                 # Unit tests
make lint                                 # ruff + format
pytest tests/unit/ -v                     # Specific tests
cd aiflow-admin && npx tsc --noEmit       # TypeScript check
alembic upgrade head                      # DB migrations
bash scripts/run_quality_baseline.sh      # 4 UC measurement (Sprint X gate)
```

## Code conventions

- **Async-first** — all I/O is async (await)
- **Pydantic everywhere** — config, API models, step I/O, DB schemas
- **structlog** — never `print()`, always `logger.info("event", key=value)`
- **Steps** — `@step` decorator, typed BaseModel I/O, stateless
- **Prompts** — YAML only (never hardcode), Langfuse sync, Jinja2 templates
- **Errors** — inherit `AIFlowError` with `is_transient` flag for retry
- **DB changes** — ALWAYS Alembic (never raw SQL), `nullable=True` for new columns
- **Auth** — PyJWT RS256 (NOT python-jose), bcrypt (NOT passlib), API key prefix `aiflow_sk_`
- **Package manager** — uv (NOT pip, NOT poetry), lockfile: `uv.lock`
- **Services in Docker** (PostgreSQL 5433, Redis 6379, Kroki 8000), Python code locally from `.venv`

## Git workflow

- Base: `main` @ tag `v1.7.0` (Sprint W close, queued post-merge). Branch per session: `feature/x-sx{N}-*`. NEVER commit to main directly.
- Commits: conventional (`feat`, `fix`, `docs`, `refactor`) + `Co-Authored-By` trailer
- NEVER commit: `.env`, credentials, API keys, failing tests
- Before commit: `/regression` + `/lint-check`

## Current plan

- **Active sprint:** Sprint X — `01_PLAN/121_SPRINT_X_QUALITY_PUSH_PLAN.md`
- **Forward queue:** `01_PLAN/ROADMAP.md`
- **Binding policy:** `01_PLAN/110_USE_CASE_FIRST_REPLAN.md` + `docs/honest_alignment_audit.md`

## Session workflow (DOHA-aligned)

**Manual:** `/clear → /next → [session work] → /session-close → /clear → /next → ...`
- `/next` reads `session_prompts/NEXT.md` and starts the session
- Every `NEXT.md` MUST start with the **Quality target** header (see `session_prompts/_TEMPLATE.md`)
- `/session-close` generates the next `NEXT.md` + archive copy
- SessionStart hook prints the queued NEXT prompt status

**Auto-sprint (autonomous chain):** `/auto-sprint max_sessions=N notify=stop_only`
- Runs through queued sessions with `ScheduleWakeup ~90s` loop
- STOP feltetelen vagy `max_sessions` cap-en megall, log entry-vel
- State: `session_prompts/.auto_sprint_state.json` (gitignored)
- Log: `session_prompts/.notifications.log` (gitignored, append-only)
- Reference: `DOHA/01_PLAN/19_DOHA_AUTO_SPRINT_GUIDE.md`

## Slash commands

- **Lifecycle:** `/next` → `/status` → `/implement` → `/dev-step` → `/review` → `/session-close`
- **Auto:** `/auto-sprint max_sessions=N notify=stop_only|all`
- **Quick checks:** `/smoke-test`, `/regression`, `/lint-check`, `/live-test <module>`
- **Prompts:** `/new-prompt`, `/prompt-tuning`, `/quality-check`
- **Services:** `/service-test`, `/service-hardening`, `/pipeline-test`, `/new-pipeline`
- **Generators:** `/new-step`, `/new-test`
- **UI (order!):** `/ui-journey` → `/ui-api-endpoint` → `/ui-design` → `/ui-page` / `/ui-component`
- **Plans:** `/update-plan`, `/validate-plan`

## IMPORTANT

- **REAL testing only** — never mock PostgreSQL/Redis/LLM. Docker for real services. See skill `aiflow-testing`.
- **Sprint-close metric gate** — every sprint-close runs `bash scripts/run_quality_baseline.sh --strict`. If the affected UC metric did not improve, the close STOPs.
- **Quality target header mandatory** — every `session_prompts/NEXT.md` MUST start with the Quality target block (use-case + metric + baseline + target + measurement command). Without it, `/next` blocks.
- **UI work:** 7 HARD GATES enforced — see skill `aiflow-ui-pipeline`.
- **A feature is DONE only after** Playwright E2E passes with real data.
- **UI valtozas utan KOTELEZO `/live-test <module>`** — session-time browser journey via Playwright MCP (`tests/ui-live/`).
- **DB changes:** see skill `aiflow-database` (Alembic rules, zero-downtime migration).
- **Observability:** see skill `aiflow-observability` (structlog, Langfuse, metrics).
- **Architecture review:** use agent `architect` for Go/No-Go decisions.

## On compaction

Preserve: modified files list + test status + current Sprint X session id + which command was running.

## References

- **Honest alignment audit (binding):** `docs/honest_alignment_audit.md`
- **Forward queue:** `01_PLAN/ROADMAP.md`
- **Current sprint plan:** `01_PLAN/121_SPRINT_X_QUALITY_PUSH_PLAN.md`
- **Use-case-first replan (policy source):** `01_PLAN/110_USE_CASE_FIRST_REPLAN.md`
- **Sprint history:** `docs/SPRINT_HISTORY.md`
- **Session-prompt template:** `session_prompts/_TEMPLATE.md`
- **Quality baseline script:** `scripts/run_quality_baseline.sh`
- **Master architecture index:** `01_PLAN/104_AIFLOW_v2_FINAL_MASTER_INDEX.md`
- **Best practices:** `01_PLAN/60_CLAUDE_CODE_BEST_PRACTICES_REFERENCE.md`
- **DOHA governance patterns:** `DOHA/design_claude/`

## Service ports (snapshot)

API 8102 | UI 5173 | PostgreSQL 5433 | Redis 6379 | Vault dev 8210 | Langfuse dev 3000 | Langfuse Postgres 5434 | Kroki 8000
