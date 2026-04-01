# AIFlow Project - Claude Code Context

## Project Overview
Enterprise AI Automation Framework for building, deploying, and operating
AI-powered automation workflows at scale. Python 3.12+, FastAPI, PostgreSQL, Redis.

## Architecture (Key Concepts)
- **Step** = atomic unit with `@step` decorator, takes dict -> returns dict
- **SkillRunner** = sequential step executor with service injection (models, prompts, ctx)
- **WorkflowRunner** = DAG executor with branching/checkpoints (for complex workflows)
- **Skill** = self-contained package (workflows + tools + prompts + tests + UI + skill.yaml). Types: ai, rpa, hybrid
- **Service** = altalanos, ujrahasznalato epitokocka (src/aiflow/services/) — skill-ek ezekbol epulnek
- **ModelClient** = unified LLM facade (generate, embed) via LiteLLM backend
- **PromptManager** = YAML prompt loading with Jinja2 templates and cache
- **Skill Instance** = configured deployment of a Skill template per customer
- **VectorStore** = pgvector hybrid search (vector HNSW + BM25 tsvector + RRF)

## Current Phase: Service Generalization (v0.9.0-stable → v1.0.0)
**Terv:** `01_PLAN/42_SERVICE_GENERALIZATION_PLAN.md`

Skill-specifikus kodot altalanos, konfiguralhato szolgaltatasokka alakitjuk:
- **Email Connector** (O365/Gmail/IMAP) ← email_intent_processor
- **Document Extractor** (barmilyen doc tipus) ← invoice_processor
- **RAG Engine** (cserelheto tudasbazis + chat UI) ← aszf_rag_chat
- **Intent Classifier** (hibrid ML+LLM) ← email_intent_processor
- **RPA Browser** (YAML-alapu automatizalas) ← cubix_course_capture
- **Media Processor** (video→szoveg) ← cubix_course_capture
- **Diagram Generator** (DrawIO/SVG) ← process_documentation

Infrastruktura epitokockak: Cache Layer, Event Bus, Config Versioning, Health Monitoring,
Rate Limiter, Circuit Breaker, Human Review, Audit Trail, Schema Registry.

**Fazisok:** F0 (infra) → F1 (Email+Doc+Classifier) → F2 (RAG+Monitoring) → F3 (RPA+Media) → F4 (Governance)

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
2. **Read `01_PLAN/42_SERVICE_GENERALIZATION_PLAN.md`** - check if it affects a service
3. **Check reference materials** - `skills/*/reference/` tartalmaz szakmai utmutatot
4. **Use Alembic** for ALL database changes - NEVER create tables with raw SQL
5. **Follow the Cubix RAG checklist** at `01_PLAN/30_RAG_PRODUCTION_PLAN.md` for RAG features
6. **Run `alembic upgrade head`** after any migration file change

### Before committing:
1. Run `pytest tests/unit/ -q` - all tests must pass
2. Check `git status` - no untracked files that should be tracked
3. Commit message: conventional commits (`feat`, `fix`, `docs`, `refactor`)

### STRICT: Real Testing Only (SOHA NE MOCK/FAKE!)
> **Csak valos, sikeres teszteles utan szabad tovabblepni. SOHA NE mockolt/fake adatokkal!**

- **API tesztek:** Valos FastAPI szerver fut, valos HTTP keresek (curl vagy Playwright)
- **Service tesztek:** Valos fuggoosegek (PostgreSQL, Redis Docker-ben), NEM in-memory mock
- **UI tesztek:** MCP Playwright-tal valos bongeszben, valos backendhez csatlakozva
- **LLM tesztek:** Valos LLM hivasok (Promptfoo), NEM hardcoded response mock
- **Upload/Process tesztek:** Valos PDF fajlok, valos Docling parse, valos eredmeny ellenorzes
- **Egy feature CSAK AKKOR "KESZ" ha Playwright-tal end-to-end vegig teszteltuk**
- **Ha egy teszt sikertelen, NEM lepunk tovabb** — elobb javitjuk, ujra teszteljuk

### Key plan documents:
- **`01_PLAN/42_SERVICE_GENERALIZATION_PLAN.md`** - AKTUALIS: Service generalizalas terv (F0-F4), infra epitokockak, domain szolgaltatasok
- `01_PLAN/IMPLEMENTATION_PLAN.md` - Legacy fazisok (A1-A5 KESZ). Aktualis: ld. 42_SERVICE_GENERALIZATION_PLAN F0-F4
- `01_PLAN/29_OPTIMIZATION_PLAN.md` - O1-O3 (KESZ) + framework audit eredmeny
- `01_PLAN/30_RAG_PRODUCTION_PLAN.md` - RAG pipeline checklist (Cubix tananyag alapjan!)
- `01_PLAN/28_MODULAR_DEPLOYMENT.md` - Multi-customer instance architecture
- `01_PLAN/22_API_SPECIFICATION.md` - API specifikacio (50+ endpoint, 58% implementalt)

### Database:
- PostgreSQL pgvector @ localhost:5433 (Docker: `docker compose up -d db`)
- Alembic: `alembic upgrade head` (migraciok az alembic/versions/-ben)
- **SOHA ne hozz letre tablat Alembic nelkul!**

## Tech Stack
- Python 3.12+, FastAPI (API), arq + Redis (async queue), PostgreSQL + pgvector (state + vectors)
- LiteLLM (multi-LLM), instructor (structured output), Langfuse (LLM observability)
- PyJWT[crypto] (RS256 JWT auth), bcrypt (hashing), APScheduler 4.x (async cron)
- Promptfoo (prompt testing), structlog (JSON logging), Alembic (DB migrations), ruff (lint+format)
- React Admin + Vite + React 19 + MUI (production admin dashboard - **aiflow-admin/**)
- Legacy: Next.js 16 + shadcn/ui (aiflow-ui/ — deprecated, kept for compatibility)
- typer (CLI), Playwright (GUI testing + RPA skills), ffmpeg (media processing in RPA skills)

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

### Fejlesztes + Teszteles
- `/dev-step` - **FO PARANCS**: fejlesztes + valos teszt + commit. Playwright E2E teszteles KOTELEZO!
- `/regression` - **MANDATORY before commit**: regresszios tesztek az erintett fajlokra
- `/new-test` - Generate tests for existing code (with @test_registry header)

### Generatorok
- `/new-step` - Generate new Step with @step decorator, I/O models, tests, prompt YAML
- `/new-skill` - Generate complete Skill scaffold (15-20 files)
- `/new-module` - Generate framework module + tests + registry updates
- `/new-prompt` - Generate prompt YAML + Promptfoo test cases

### UI
- `/ui-component` - Generate shadcn/ui + TypeScript component for the dashboard
- `/ui-page` - Generate Next.js App Router page for the dashboard
- `/ui-viewer` - Generate skill-specific result viewer component
- `/ui-api-endpoint` - Generate FastAPI endpoint for the UI

### Tervek + Audit
- `/phase-status` - Check implementation progress for a phase (F0-F4)
- `/validate-plan` - Validate plan document consistency
- `/update-plan` - **MANDATORY for plan changes**: propagate + 2-pass validation

## Directory Structure
```
src/aiflow/
    core/          # Config, context, errors, events, registry, types
    engine/        # Step, SkillRunner, WorkflowRunner, DAG, checkpoint
    models/        # ModelClient, LiteLLM backend, protocols
    prompts/       # PromptManager (YAML + Jinja2 + cache)
    services/      # TERVEZETT (42_SERVICE_GENERALIZATION_PLAN): email_connector, document_extractor, rag_engine, classifier, rpa_browser, media_processor, diagram_generator, cache, events, monitoring, resilience, human_review, audit, schema_registry
    skill_system/  # Skill manifest, loader, registry, instance (canonical)
    tools/         # Shell, Playwright, RobotFramework, HumanLoop, Kafka (canonical)
    vectorstore/   # VectorStore ABC, pgvector, HybridSearchEngine, embedder
    documents/     # DocumentRegistry, versioning, freshness
    ingestion/     # Parsers (PDF/DOCX), chunkers (semantic)
    state/         # SQLAlchemy ORM, repository, Alembic migrations
    security/      # JWT+API key auth, RBAC, audit
    api/v1/        # FastAPI endpoints (12 route files: health, workflows, chat, feedback, runs, costs, skills, emails, auth, documents, process_docs, cubix)
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
aiflow-admin/      # React Admin + Vite + React 19 + MUI (AKTIV production dashboard)
  src/pages/         # Oldalak (Dashboard, InvoiceUpload, stb.)
  src/resources/     # React Admin resource definiciok (InvoiceList, InvoiceShow, stb.)
  src/components/    # Komponensek (PipelineProgress, stb.)
  src/verification/  # Szamla verifikacio (DocumentCanvas, VerificationPanel, MockInvoiceSvg)
  src/dataProvider.ts # FastAPI → React Admin adatkapcsolat
  vite.config.ts     # Vite config + API proxy (localhost:8100)
aiflow-ui/         # LEGACY Next.js 16 + shadcn/ui (deprecated, kept for reference)
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

## MANDATORY Admin UI Development Rules (aiflow-admin/ — Vite + React Admin)

### The Depth Rule
> **Finish ONE feature properly before starting the next.**
> Never build 5 viewers in parallel — build 1, test it manually, fix it, THEN move to the next.
> A feature is NOT "KESZ" until Playwright E2E teszten atment.

### i18n Rules (NEVER skip!)
- **EVERY user-visible string MUST use `useTranslate()` from react-admin** — no exceptions
- Wire i18n AS YOU BUILD — not after
- Check: page titles, button labels, table headers, KPI labels, error messages, empty states
- Test: click HU/EN toggle → EVERY string on screen must change

### Vite + React Admin Rules (avoid common pitfalls!)
- **vite.config.ts** tartalmazza az API proxy-t (`/api` → `localhost:8100`) — NEM proxy.ts/middleware.ts
- **No hardcoded `localhost` URLs** — use relative paths via `/api/` proxy routes
- **Data fetches: dataProvider.ts** → FastAPI `/api/v1/*` endpointok
- **No `localStorage` in `useState()` initializer** — causes hydration mismatch. Use `useEffect`
- **React Admin resource-ok** a `src/resources/` mappaban

### UI Component Checklist (verify BEFORE marking done)
Every new page/component MUST have:
1. [ ] `useTranslate()` hook imported and all strings use `translate()`
2. [ ] Loading state (show spinner/skeleton while data loads)
3. [ ] Error state (show error message + retry button)
4. [ ] Empty state (meaningful message when no data)
5. [ ] Data fetched via dataProvider or `/api/` routes
6. [ ] No hardcoded Hungarian/English strings
7. [ ] Works in both light and dark mode
8. [ ] **Playwright E2E teszt:** navigate → snapshot → click → screenshot → console check

### UI Testing Protocol
```bash
# After EVERY UI change:
cd aiflow-admin && npx tsc --noEmit     # TypeScript hiba nelkul
# Playwright MCP teszteles (valos bongeszioben, valos backend-del):
# browser_navigate → browser_snapshot → browser_click → browser_take_screenshot
# browser_console_messages → nincs JS hiba?
```

## MANDATORY: No Silent Mock Data (STRICT!)

### The Honesty Rule
> **A user MUST always know whether they see real or demo data.**
> Silent fallback to mock data is FORBIDDEN. Every mock must be visibly labeled.

### Backend Connection Rules
- Every API route that uses `fetchBackend()` MUST return a `source` field: `"backend"` or `"demo"`
- Every page MUST show "Demo mod" banner when `source === "demo"`
- NEVER pretend mock data is real (no fake streaming of hardcoded answers)
- Connection status (`useBackendStatus` hook) MUST be visible in the sidebar

### Viewer Completeness Rules
- A viewer is NOT complete unless it has: INPUT mechanism → REAL PROCESSING → REAL OUTPUT
- If a skill cannot process (backend down), show "Demo" label + mock data
- If a skill has no input mechanism, it's a "Results Viewer" not a "Viewer"
- Status badges must be honest: "Production" only if actually works, "Demo" if mock, "Results Viewer" if read-only
- NEVER mark a viewer as "KESZ" or "Production" if it only shows mock data

### Subprocess Pattern (for skill execution from UI)
- Reference implementation: `aiflow-ui/src/app/api/documents/process/route.ts`
- Pattern: `execFileAsync(PYTHON, ["-m", "skills.<name>", ...args])`
- Priority: 1. FastAPI backend (fetchBackend) → 2. subprocess (Python CLI) → 3. mock (labeled as demo)
- ALWAYS tag output with `source` field

### Viewer Checklist (extends the UI Component Checklist above)
10. [ ] API route returns `source: "backend"|"demo"` field
11. [ ] Page shows Demo/Live badge based on source
12. [ ] Input mechanism exists (upload, text form, URL input)
13. [ ] Real processing callable (subprocess or FastAPI)
14. [ ] Mock data clearly labeled — NEVER silent fallback

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

**Service Generalization:**
- **42_SERVICE_GENERALIZATION_PLAN** - Teljes atalakitasi terv: 7 domain service + 9 infra epitokocka + 5 fazis

**Dev Artifacts:**
- IMPLEMENTATION_PLAN.md, SKILL_DEVELOPMENT.md, AIFLOW_MASTER_PLAN.md
- 00_EXECUTIVE_SUMMARY.md, 00_GAPS_AND_FIXES.md
