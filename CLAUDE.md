# AIFlow Project - Claude Code Context

## Project Overview
Enterprise AI Automation Framework for building, deploying, and operating
AI-powered automation workflows at scale. Python 3.12+, FastAPI, PostgreSQL, Redis.

## Architecture (Key Concepts)
- **Step** = atomic unit with `@step` decorator, takes dict -> returns dict
- **SkillRunner** = sequential step executor with service injection (models, prompts, ctx)
- **WorkflowRunner** = DAG executor with branching/checkpoints (for complex workflows)
- **Skill** = self-contained package (workflows + tools + prompts + tests + UI + skill.yaml). Types: ai, rpa, hybrid
- **ModelClient** = unified LLM facade (generate, embed) via LiteLLM backend
- **PromptManager** = YAML prompt loading with Jinja2 templates and cache
- **Skill Instance** = configured deployment of a Skill template per customer
- **VectorStore** = pgvector hybrid search (vector HNSW + BM25 tsvector + RRF)

## Skills (6 db)

### Working (tested with real data)
- **process_documentation** (ai) - Natural language -> BPMN diagrams (Mermaid + DrawIO + BPMN swimlane + SVG)
- **cubix_course_capture** (hybrid) - Video transcript pipeline (ffmpeg + Whisper STT + LLM structuring) + RPA (Robot Framework)
- **aszf_rag_chat** (ai) - RAG chat (docling PDF parse + pgvector + OpenAI + Open WebUI) - evaluation 86% pass
- **email_intent_processor** (ai) - Email + csatolmany feldolgozo (hibrid ML+LLM, intent discovery, JSON schema vezerelt)

### In Development
- **invoice_processor** (ai) - PDF szamla feldolgozas (Docling + gpt-4o extraction, CSV/Excel/JSON export) - Next.js UI + valos Docling integracio

### Stub
- **qbpp_test_automation** (rpa) - Insurance calculator test automation - STUB (__main__.py hianyzik)

## Architecture Patterns

### Configurable JSON Schema System
Skills use versioned JSON schemas for flexible, code-free configuration:
```
skills/{name}/schemas/v1/
  intents.json          # Intent definiciok (nev, peldak, routing)
  entities.json         # Entity tipusok (regex, LLM hint, validacio)
  document_types.json   # Csatolmany tipusok + feldolgozasi strategia
  routing_rules.json    # Routing matrix
```
This enables: new intents/entities without code changes, per-customer customization, versioning.

### Multi-layer Document Processing
1. **Docling** (local, free) - PDF/DOCX/XLSX/HTML - always first
2. **Azure Document Intelligence** (cloud) - scan/OCR/handwriting - if docling can't
3. **LLM Vision** (OpenAI) - image content interpretation - last resort

### Hybrid Classification
- **sklearn ML** (CFPB-ported TF-IDF + LinearSVC) - <1ms, $0 - fast screening
- **LLM** (gpt-4o-mini) - if ML confidence < threshold, refines the result

## MANDATORY Development Rules (NEVER skip these!)

### Before implementing ANY feature:
1. **Read the relevant plan** in `01_PLAN/` - EVERY feature has a plan document
2. **Check reference materials** - `skills/*/reference/` tartalmaz szakmai utmutatot (pl. Cubix RAG tananyag)
3. **Use Alembic** for ALL database changes - NEVER create tables with raw SQL
4. **Follow the Cubix RAG checklist** at `01_PLAN/30_RAG_PRODUCTION_PLAN.md` for RAG features
5. **Run `alembic upgrade head`** after any migration file change

### Before committing:
1. Run `pytest tests/unit/ -q` - all tests must pass
2. Check `git status` - no untracked files that should be tracked
3. Commit message: conventional commits (`feat`, `fix`, `docs`, `refactor`)

### Key plan documents:
- `01_PLAN/IMPLEMENTATION_PLAN.md` - Fazis A1-A5 (KESZ) + F1-F4 (aktualis) + B (jovobeli)
- `01_PLAN/29_OPTIMIZATION_PLAN.md` - O1-O3 (KESZ) + framework audit eredmeny
- `01_PLAN/30_RAG_PRODUCTION_PLAN.md` - RAG pipeline checklist (Cubix tananyag alapjan!)
- `01_PLAN/28_MODULAR_DEPLOYMENT.md` - Multi-customer instance architecture

### Database:
- PostgreSQL pgvector @ localhost:5433 (Docker: `docker compose up -d db`)
- Alembic: `alembic upgrade head` (26 migracio, 36 tabla + 13 view)
- **SOHA ne hozz letre tablat Alembic nelkul!**

## Tech Stack
- Python 3.12+, FastAPI (API), arq + Redis (async queue), PostgreSQL + pgvector (state + vectors)
- LiteLLM (multi-LLM), instructor (structured output), Langfuse (LLM observability)
- PyJWT[crypto] (RS256 JWT auth), bcrypt (hashing), APScheduler 4.x (async cron)
- Promptfoo (prompt testing), structlog (JSON logging), Alembic (DB migrations), ruff (lint+format)
- Next.js 16 + React 19 + TypeScript + shadcn/ui (production frontend - aiflow-ui/), typer (CLI)
- Playwright (GUI testing + RPA skills), ffmpeg (media processing in RPA skills)

## Development Environment
- **Python package manager: `uv`** (NOT pip, NOT poetry) - fast, lockfile-based, PEP 621
- **Virtual environment: `.venv/`** created by `uv venv`
- **Lockfile: `uv.lock`** - ALWAYS committed, used by CI AND Docker (reproducible builds)
- **Services (PostgreSQL, Redis, Kroki): ALWAYS in Docker** - never install locally
- **Python code (API, worker): runs locally** from .venv for IDE support + hot reload
- **Full Docker option:** `make dev-docker` runs everything in containers
- Setup: `uv venv && uv pip install -e ".[dev]" && cp .env.example .env && make dev`
- Details: `01_PLAN/27_DEVELOPMENT_ENVIRONMENT.md`

## Key Commands
```bash
# Setup (first time)
make setup                                  # Create .venv + install deps + copy .env
make dev                                    # Start Docker services + run DB migrations

# Daily development
make api                                    # Run FastAPI locally (hot reload)
make worker                                 # Run arq worker locally
make test                                   # Run all unit tests
make test-cov                               # Tests + coverage report
make lint                                   # ruff check + ruff format + mypy
make lint-fix                               # Auto-fix lint issues

# Database
make migrate                                # Alembic upgrade head
make migrate-new NAME=add_xyz               # Create new migration

# Testing
pytest tests/unit/ -v                       # Unit tests only
pytest tests/integration/ -v               # Integration tests (needs Docker)
npx promptfoo eval -c skills/*/tests/promptfooconfig.yaml  # Prompt tests

# Skill CLI (direct execution - recommended)
python -m skills.process_documentation --input "..." --output ./out
python -m skills.cubix_course_capture transcript --input video.mkv
python -m skills.cubix_course_capture capture --url "https://..."
python -m skills.aszf_rag_chat ingest --source ./docs/ --collection my-docs
python -m skills.aszf_rag_chat query --question "..." --role expert

# AIFlow CLI (framework management)
aiflow workflow list                        # List registered workflows
aiflow instance list                        # List skill instances
aiflow instance load deployments/bestix/deployment.yaml

# Lockfile
make lock                                   # Regenerate uv.lock from pyproject.toml
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
- `/update-plan` - **MANDATORY for plan changes**: propagate + 2-pass validation
- `/ui-component` - Generate shadcn/ui + TypeScript component for the dashboard
- `/ui-page` - Generate Next.js App Router page for the dashboard
- `/ui-viewer` - Generate skill-specific result viewer component
- `/ui-api-endpoint` - Generate FastAPI endpoint for the UI

## Directory Structure
```
src/aiflow/
    core/          # Config, context, errors, events, registry, types
    engine/        # Step, SkillRunner, WorkflowRunner, DAG, checkpoint
    models/        # ModelClient, LiteLLM backend, protocols
    prompts/       # PromptManager (YAML + Jinja2 + cache)
    skill_system/  # Skill manifest, loader, registry, instance (canonical)
    tools/         # Shell, Playwright, RobotFramework, HumanLoop, Kafka (canonical)
    vectorstore/   # VectorStore ABC, pgvector, HybridSearchEngine, embedder
    documents/     # DocumentRegistry, versioning, freshness
    ingestion/     # Parsers (PDF/DOCX), chunkers (semantic)
    state/         # SQLAlchemy ORM, repository, Alembic migrations
    security/      # JWT+API key auth, RBAC, audit
    api/v1/        # FastAPI endpoints (10 route files: health, workflows, chat, feedback, runs, costs, skills, emails, auth)
    observability/ # Tracing, cost_tracker (partial)
    cli/           # typer CLI
    skills/        # Backward compat re-exports -> skill_system/
    contrib/       # Backward compat re-exports -> tools/
skills/            # Self-contained skill packages (each with own tools, tests, UI)
  process_documentation/  # WORKING - diagram generation
  cubix_course_capture/   # WORKING - video transcript pipeline + RPA
  aszf_rag_chat/          # WORKING - RAG chat (86% eval pass)
  email_intent_processor/ # IN DEVELOPMENT - email + attachment processing
  invoice_processor/      # IN DEVELOPMENT - PDF invoice extraction + Next.js UI
  qbpp_test_automation/   # STUB - insurance calculator test automation
aiflow-ui/         # Next.js 16 + React 19 + shadcn/ui production dashboard (91 fajl)
  src/app/           # 11 oldal (/, /login, /costs, /runs, /runs/[id], 6 skill viewer)
  src/components/    # 47 komponens (ui/, invoice/, email/, rag-chat/, process-docs/, cubix/, workflow/, verification/ + standalone)
  src/lib/           # 9 fajl (types, data-store, backend, csv-export, i18n, api, utils, verification-types, document-layout)
  src/hooks/         # 4 hook (use-auth, use-i18n, use-verification-state, use-workflow-simulation)
  src/app/api/       # 18 API route (auth, documents, emails, rag, process-docs, cubix, runs)
  src/proxy.ts       # Auth proxy + RBAC (cookie JWT, login redirect, role check)
deployments/       # Per-customer deployment configs (AZHU, NPRA, BESTIX)
tests/             # unit/, integration/, e2e/, conftest.py
```

## Skill Running (two ways)
```bash
# CLI (recommended for testing):
python -m skills.process_documentation --input "Szamla feldolgozas..." --output ./out
python -m skills.cubix_course_capture transcript --input video.mkv --course Cubix_ML

# Programmatic (for integration):
from aiflow.engine.skill_runner import SkillRunner
runner = SkillRunner.from_env(prompt_dirs=["skills/X/prompts"])
result = await runner.run_steps([step1, step2], {"input": "..."})
```

## Coding Conventions
- **Every step MUST have typed Pydantic input/output** (BaseModel subclasses)
- **Steps MUST be stateless** - no instance variables modified during execute()
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
| api/ | 80% | 90% |
| security/ | 90% | 95% |
| models/ | 80% | 85% |
| vectorstore/ | 75% | 80% |
| skills/*/workflows/ | 70% | 80% |
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
- 22_API_SPECIFICATION (50+ endpoint), 23_CONFIGURATION_REFERENCE

**Environment:**
- **27_DEVELOPMENT_ENVIRONMENT** - uv, .venv, Docker Compose, Makefile, onboarding
- **28_MODULAR_DEPLOYMENT** - Skill Instance architecture, multi-customer, deployment profiles

**Dev Artifacts:**
- IMPLEMENTATION_PLAN.md, SKILL_DEVELOPMENT.md, AIFLOW_MASTER_PLAN.md
- 00_EXECUTIVE_SUMMARY.md, 00_GAPS_AND_FIXES.md
