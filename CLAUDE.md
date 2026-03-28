# AIFlow Project - Claude Code Context

## Project Overview
Enterprise AI Automation Framework for building, deploying, and operating
AI-powered automation workflows at scale. Python 3.12+, FastAPI, PostgreSQL, Redis.

## Architecture (Key Concepts)
- **Step** = atomic unit with typed Pydantic I/O, `@step` decorator, DI injection
- **Workflow** = DAG of Steps built with `WorkflowBuilder` (branch, loop, join, subworkflow, parallel_map, for_each)
- **Specialist Agent** = stateless, single-responsibility, max 6 per orchestrator
- **Skill** = self-contained package (workflow + agents + prompts + tests + skill.yaml manifest). Types: ai, rpa, hybrid
- **Prompt** = YAML source -> Langfuse SSOT -> runtime cache, label-based env (dev/test/staging/prod)
- **ExecutionContext** = request-scoped context flowing through all components (trace, budget, label)
- **ModelClient** = unified facade: generate (LLM), embed, classify, extract, vision, predict
- **VectorStore** = pgvector hybrid search (vector HNSW + BM25 tsvector + RRF)

## Tech Stack
- Python 3.12+, FastAPI (API), arq + Redis (async queue), PostgreSQL + pgvector (state + vectors)
- LiteLLM (multi-LLM), instructor (structured output), Langfuse (LLM observability)
- PyJWT[crypto] (RS256 JWT auth), bcrypt (hashing), APScheduler 4.x (async cron)
- Promptfoo (prompt testing), structlog (JSON logging), Alembic (DB migrations), ruff (lint+format)
- Reflex or NiceGUI or Next.js (frontend - see 01_PLAN/14_FRONTEND.md), typer (CLI)
- Playwright (GUI testing + RPA skills), ffmpeg (media processing in RPA skills)

## Key Commands
```bash
make dev                                    # Start dev environment (docker compose)
make test                                   # Run all tests
make lint                                   # ruff + black + mypy
pytest tests/unit/ -v                       # Unit tests only
pytest tests/integration/ -v               # Integration tests (needs Docker)
npx promptfoo eval -c skills/*/tests/promptfooconfig.yaml  # Prompt tests
aiflow workflow list                        # List registered workflows
aiflow workflow run <name> --input '{}'     # Run workflow
aiflow skill install ./skills/<name>        # Install skill (9-step process)
aiflow prompt sync --label dev              # Sync YAML prompts to Langfuse
aiflow eval run --skill <name>              # Run evaluation suite (100+ tests)
alembic upgrade head                        # Run DB migrations
```

## Claude Code Slash Commands (use these during development!)
- `/new-step` - Generate new Step with @step decorator, I/O models, tests, prompt YAML
- `/new-skill` - Generate complete Skill scaffold (15-20 files)
- `/new-module` - Generate framework module + tests + registry updates
- `/new-test` - Generate tests for existing code (with @test_registry header)
- `/new-prompt` - Generate prompt YAML + Promptfoo test cases
- `/regression` - **MANDATORY before commit**: run regression tests for changed files
- `/dev-step` - Complete development step: regression + record + commit suggestion
- `/phase-status` - Check implementation progress for a phase (1-7)
- `/validate-plan` - Validate plan document consistency

## Directory Structure
```
src/aiflow/
    core/          # Config, context, errors, events, DI, registry
    engine/        # Step, workflow, DAG, runner, checkpoint, policies
    agents/        # Specialist, orchestrator, quality_gate, human_loop
    skills/        # Skill base, manifest, loader, registry
    prompts/       # PromptManager (Langfuse SSOT), sync, A/B testing
    models/        # ModelClient (LLM+embedding+classify+extract+vision), registry, router, backends
    execution/     # JobQueue (arq), worker, scheduler, DLQ, rate_limiter, messaging adapters
    state/         # SQLAlchemy ORM, repository, Alembic migrations
    observability/ # Langfuse+OTel tracing, cost_tracker, SLA, structlog, Prometheus
    evaluation/    # EvalSuite, scorers, Promptfoo integration, datasets
    security/      # JWT+API key auth, RBAC, audit, Vault secrets, guardrails
    api/v1/        # FastAPI endpoints (workflows, jobs, skills, prompts, admin, health)
    vectorstore/   # VectorStore ABC, pgvector, HybridSearchEngine, embedder
    documents/     # DocumentRegistry, versioning, freshness, external sync
    ingestion/     # Parsers (PDF/DOCX/XLSX), chunkers (semantic/fixed/hierarchical)
    ui/            # Reflex/NiceGUI frontend (operator, chat, developer, admin, reports)
    cli/           # typer CLI (workflow, skill, prompt, eval, dev, deploy)
    contrib/       # Optional: n8n, chainlit, kroki, miro, messaging, MCP, playwright, shell
skills/            # Installed skills (process_doc, aszf_rag, email_intent, cubix_capture, ...)
templates/         # Workflow scaffolding templates (small, medium, large)
tests/             # unit/, integration/, e2e/, conftest.py
```

## Coding Conventions
- **Every step MUST have typed Pydantic input/output** (BaseModel subclasses)
- **Max 6 specialist agent types** per orchestrator (2-level rule)
- **Specialists MUST be stateless** - no instance variables modified during execute()
- **Prompts MUST be in YAML**, synced to Langfuse - never hardcode prompt text in Python
- **Every skill MUST have 100+ test cases** (Promptfoo + pytest)
- **structlog for logging** - never print(), always `logger.info("event", key=value)`
- **Async-first** - all I/O operations are async (await)
- **Pydantic everywhere** - config, API models, step I/O, agent messages, DB schemas
- All errors inherit from `AIFlowError` with `is_transient` flag for retry decisions

## MANDATORY Testing & Regression Rules (STRICT - NO EXCEPTIONS)

### The Golden Rule
> **No code reaches main without ALL previous tests passing as regression.**
> This is a BLOCKING requirement enforced by CI and by the developer.

### Development Step Protocol
Every code change MUST follow this exact sequence:
1. **Write code** - implement the change
2. **Write tests IMMEDIATELY** - not later, not "after commit", NOW
   - Add `@test_registry` header to every test file (suite, component, covers, phase, priority)
   - Minimum: 5 unit tests per new module, 3 per endpoint, 10 promptfoo per prompt
3. **Run local tests** - new tests + affected regression suites
   ```bash
   pytest tests/unit/<affected>/ -v                    # New + related unit tests
   pytest tests/unit/ --cov=aiflow --cov-report=term   # Coverage check
   ```
4. **Verify ALL pass** - zero failures, coverage not decreased
5. **Only then commit** - include "Tests: X new, Y regression pass" in commit message

### What is FORBIDDEN
- Committing with any failing test - NEVER, under ANY circumstances
- Commenting out or deleting a failing test to make CI pass
- Adding `@pytest.mark.skip` without a tracking ticket
- Decreasing code coverage in any module
- Skipping regression even for "quick fixes"
- Writing tests AFTER the commit (tests must be written BEFORE commit)
- Using `git add -A` (might include test artifacts, .env)

### Regression Levels
| Level | When | What runs | Max time |
|-------|------|-----------|----------|
| L1 Quick | Every commit | Affected unit suites | <60s |
| L2 Standard | Every PR | L1 + affected integration + affected skills | 2-5 min |
| L3 Full | Merge to main | ALL suites (unit + integration + skill + promptfoo) | 10-20 min |
| L4 Complete | Deploy staging | L3 + E2E + UI Playwright | 20-40 min |
| L5 Release | Deploy prod | L4 + perf benchmark + security scan | 30-60 min |

### Coverage Gates (BLOCKING - PR cannot merge if violated)
| Module | Minimum | Target |
|--------|---------|--------|
| core/ | 90% | 95% |
| engine/ | 85% | 90% |
| agents/ | 80% | 85% |
| api/ | 80% | 90% |
| security/ | 90% | 95% |
| models/ | 80% | 85% |
| vectorstore/ | 75% | 80% |
| skills/*/agents/ | 70% | 80% |
| **OVERALL** | **80%** | **85%** |

### Test File Registry Header (REQUIRED on every test file)
```python
"""
@test_registry:
    suite: engine-unit
    component: engine.dag
    covers: [src/aiflow/engine/dag.py]
    phase: 2
    priority: critical
    estimated_duration_ms: 500
    requires_services: []
    tags: [dag, validation]
"""
```

### Regression Matrix
When a source file changes, the regression matrix (tests/regression_matrix.yaml) determines
which test suites MUST run. Changes to core/, security/, or pyproject.toml trigger FULL regression.
See: `01_PLAN/24_TESTING_REGRESSION_STRATEGY.md` for complete matrix.

### Test Artifacts
Every regression run saves: summary.json, junit.xml, coverage.xml, failed_tests.json,
regression_diff.json. Stored in tests/artifacts/{date}/{run_id}/

## Git Conventions
- **Conventional Commits**: `feat(engine): add retry policy`, `fix(api): handle timeout`
- **Squash merge** to main (clean history)
- **Branch naming**: `feature/AIFLOW-{id}-{desc}`, `skill/{name}/{desc}`, `prompt/{name}/{desc}`
- **NEVER commit** .env, credentials, API keys
- **Co-Authored-By**: always add when Claude Code assists
- **CODEOWNERS**: framework-team owns src/aiflow/, skill teams own their skills/

## Testing Rules
- Unit tests: mock LLM calls, test logic only, <30s total, @test_registry header REQUIRED
- Integration tests: testcontainers (real PostgreSQL + Redis), 2-5 min
- Prompt tests: Promptfoo, real LLM calls, per-skill config, 90%+ pass rate required
- API tests: FastAPI TestClient, test auth/RBAC/endpoints
- E2E tests: full pipeline (API -> queue -> worker -> DB), on main merge only
- GUI tests: Playwright (Page Object Model), same stack as RPA skills
- Test data: PostgreSQL test_datasets/test_cases tables for 10,000+ cases at scale
- Coverage gate: 80% minimum, PR blocked if below, NEVER decrease coverage
- **Regression: MANDATORY on every PR** - regression_matrix.yaml determines affected suites
- **Regression artifacts: ALWAYS saved** - summary.json, junit.xml, coverage.xml, regression_diff.json
- **Flaky tests: quarantine within 24h, fix within 5 business days, NEVER delete**
- **Development step tracking: every change recorded in development_steps DB table**
- Full strategy: `01_PLAN/24_TESTING_REGRESSION_STRATEGY.md`

## Plan Reference (All docs in 01_PLAN/)
Start here: `01_PLAN/AIFLOW_MASTER_PLAN.md` - Integrated overview

**Core:**
- 01_ARCHITECTURE, 02_DIRECTORY_STRUCTURE, 03_DATABASE_SCHEMA (35 tabla, 13 view, konszolidalt)
- 04_IMPLEMENTATION_PHASES (22 het, konszolidalt), 05_TECH_STACK (PyJWT, bcrypt, APScheduler 4.x)

**Operations:**
- 06_CLAUDE_CODE_INTEGRATION, 07_VERSION_LIFECYCLE, 08_ERROR_HANDLING_DEBUGGING

**Enterprise:**
- 09_MIDDLEWARE_INTEGRATION, 10_BUSINESS_AUDIT_DOCS

**Examples:**
- 11_REAL_WORLD_SKILLS_WALKTHROUGH, 12_SKILL_INTEGRATION, 13_GITHUB_RESEARCH

**Technical:**
- 14_FRONTEND, 15_ML_MODEL_INTEGRATION, 16_RAG_VECTORSTORE

**Dev Rules & Testing:**
- 17_GIT_RULES, 18_TESTING_AUTOMATION, 19_RPA_AUTOMATION
- **24_TESTING_REGRESSION_STRATEGY** - MANDATORY tesztelesi es regresszios rendszer
- **25_TEST_DIRECTORY_STRUCTURE** - Teszt mappaszerkezet es registry formatum

**Security & Operations:**
- 20_SECURITY_HARDENING, 21_DEPLOYMENT_OPERATIONS
- 22_API_SPECIFICATION (40+ endpoint), 23_CONFIGURATION_REFERENCE

**Dev Artifacts:**
- IMPLEMENTATION_PLAN.md, SKILL_DEVELOPMENT.md, AIFLOW_MASTER_PLAN.md
- 00_EXECUTIVE_SUMMARY.md, 00_GAPS_AND_FIXES.md
