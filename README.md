# AIFlow — Enterprise AI Automation Framework

Use-case-first, multi-tenant Python framework for building, deploying, and operating AI-powered automation pipelines (invoice processing, RAG chat, email intent classification, monitoring + cost guardrails). Production-ready as of **v1.5.3 Sprint T** (PromptWorkflow per-skill consumer migrations) on top of v1.5.2 Sprint S (multi-tenant + multi-profile vector DB).

> **Tech stack:** Python 3.12 · FastAPI · PostgreSQL 16 + pgvector · Redis 7 · React 19 + Tailwind v4 + Vite · Alembic · uv · structlog · Langfuse · pytest · Playwright

---

## ⚡ One-command start

```bash
# Linux / macOS / Git Bash on Windows
bash scripts/start_stack.sh --with-api --with-ui

# Windows native (cmd / PowerShell — wraps Git Bash)
scripts\start_stack.cmd --with-api --with-ui
```

A teljes parancssor:

| Flag | Mit indít |
|------|-----------|
| *(none)* | Docker core: PostgreSQL :5433 + Redis :6379 + Kroki :8080 + Alembic migrate |
| `--with-api` | FastAPI :8102 (uvicorn, hot-reload, logs in `.stack_logs/api.log`) |
| `--with-ui` | Vite dev :5173 (logs in `.stack_logs/ui.log`, auto `npm install` if needed) |
| `--with-vault` | HashiCorp Vault dev :8210 (root token: `aiflow-dev-root`) + auto-seed |
| `--with-langfuse` | Self-hosted Langfuse :3000 + dedicated Postgres :5434 |
| `--full` | Mind a fenti |
| `--validate-only` | Csak health check (semmit nem indít) |
| `--down` | Mindent leállít (volumes megmaradnak) |

A script automatikusan:
1. ellenőrzi a prereq-eket (`docker`, `uv`, `.env`, `uv.lock`),
2. helyreállítja a `aiflow` editable install-ot ha sérült (pl. mappa költöztetés után),
3. megvárja amíg PostgreSQL és Redis healthy,
4. lefuttatja `alembic upgrade head`-et,
5. opcionálisan elindít további szolgáltatásokat,
6. health-summary táblát ír.

---

## 🗺 Architecture overview

```
┌─────────────────────────────────────────────────────────────────────┐
│  Admin UI (React 19 + Tailwind v4)         Vite :5173               │
└─────┬───────────────────────────────────────────────────────────────┘
      │  REST / SSE
┌─────▼───────────────────────────────────────────────────────────────┐
│  FastAPI                                    :8102                   │
│   31 routers · 196 endpoints · OpenAPI · JWT (RS256)                │
├─────────────────────────────────────────────────────────────────────┤
│  Services layer                                                     │
│   27 services: rag_engine · email_connector · classifier            │
│                document_extractor · diagram_generator · cache       │
│                rate_limiter · resilience · audit · …                │
├─────────────────────────────────────────────────────────────────────┤
│  Engine + Pipeline + PromptWorkflow                                 │
│   22 adapters · 10 templates · 8 skills · 5 source adapters         │
│   Multi-step prompt chains (DAG, Kahn topo-sort, 3-layer lookup)    │
├─────────────────────────────────────────────────────────────────────┤
│  Provider Registry (5 ABC slots)                                    │
│   parser · classifier · extractor · embedder · chunker              │
│   3 embedder profiles: BGE-M3 (A) · Azure OpenAI (B) · OpenAI       │
├─────────────────────────────────────────────────────────────────────┤
│  PostgreSQL :5433 (50 tables, 47 migrations, pgvector flex-dim)     │
│  Redis :6379 (queue, cache)                                         │
│  Kroki :8080 (diagram render)                                       │
│  Langfuse cloud or self-hosted :3000 (observability)                │
│  Vault :8210 dev / external prod (secrets)                          │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📦 Components inventory

### 8 Skills (`skills/`)

| Skill | Use case | Status |
|-------|----------|--------|
| **`invoice_processor`** | UC1 — invoice extraction (vendor/buyer/header/items/totals); reportlab corpus 85.7% accuracy, `invoice_extraction_chain` PromptWorkflow consumed (S149) | Sprint Q + T |
| **`aszf_rag_chat`** | UC2 — Hungarian ÁSZF RAG chat; multi-profile (BGE-M3 1024-dim / Azure OpenAI / OpenAI surrogate); `aszf_rag_chain` baseline persona via PromptWorkflow (S150) | Sprint J + S + T |
| **`email_intent_processor`** | UC3 — email intent classification + attachment-aware extraction; sklearn-first + LLM fallback strategy; `email_intent_chain` PromptWorkflow (S148) | Sprint K → T |
| **`invoice_finder`** | UC1.5 — Outlook/folder invoice discovery + classification | Sprint I |
| **`process_documentation`** | Diagram generation from process descriptions (Kroki + mermaid + bpmn + excalidraw) | Tier 1 |
| **`cubix_course_capture`** | RPA + transcript pipeline (Playwright + ffmpeg + STT) | Tier 2 |
| **`qbpp_test_automation`** | Multi-app autotester (Playwright + BDD + strategy-based) | Tier 2 |
| **`spec_writer`** | Specification authoring assistant | Tier 2 |

### 27 Services (`src/aiflow/services/`)

Core: `rag_engine`, `rag_metrics`, `email_connector`, `classifier`, `document_extractor`, `advanced_parser`, `advanced_chunker`, `diagram_generator`, `media_processor`, `rpa_browser`, `metadata_enricher`, `data_cleaner`, `data_router`, `quality`, `graph_rag`, `reranker`, `human_review`.

Cross-cutting: `cache`, `rate_limiter`, `resilience`, `audit`, `health_monitor`, `notification`, `schema_registry`, `service_manager`, `config`.

### 31 API routers (`src/aiflow/api/v1/`) → 196 endpoints

Auth + users · documents · emails · prompts · prompt_workflows · pipelines · runs · runs_trace · services · skills · costs · monitoring · feedback · quality · notifications · intake · intent_schemas · sources_webhook · rag_engine · rag_advanced · rag_collections · diagram_generator · document_extractor · media_processor · process_docs · spec_writer · cubix · rpa_browser · human_review · admin · health · chat_completions · tenant_budgets · verifications · data_router.

### 26 Admin UI pages (`aiflow-admin/src/pages-new/`)

Dashboard · Login · Documents (+ DocumentDetail) · Emails (+ EmailDetail) · EmailConnectors · IntentRules · Pipelines (+ PipelineDetail) · Runs (+ RunDetail) · PackageDetail · Prompts (+ PromptDetail) · PromptWorkflows · Quality · Verification · Reviews · Rag (+ RagDetail) · RagCollections · Services · Costs · BudgetManagement · Monitoring · Audit · Admin.

### Database — 50 tables, 47 migrations, head **047**

Recent: `047` swap legacy `UNIQUE (name)` → `UNIQUE (tenant_id, name)` on `rag_collections` (Sprint S S145) · `046` add `tenant_id` + `embedder_profile_id` (Sprint S S143) · `045` `tenant_budgets` (Sprint N) · `043` cost_records tenant index (Sprint L) · `040`–`042` embedding decisions + chunk dim + pgvector flex-dim (Sprint J).

### Pipeline + Sources

22 pipeline adapters · 10 built-in templates · 5 source adapters: **Email**, **File**, **Folder**, **Batch**, **API** (+ webhook signed-payload router).

### Embedder profiles (Provider Registry)

| Profile | Model | Dim | Status |
|---------|-------|-----|--------|
| **A — BGE-M3** | `BAAI/bge-m3` (local sentence-transformers) | 1024 | Default, air-gap-safe, MRR@5 ≥ 0.55 baseline |
| **B — Azure OpenAI** | `text-embedding-3-large` | 1536 | Live measurement pending (credits) |
| **— OpenAI surrogate** | `text-embedding-3-large` | 1536 | Profile B surrogate when Azure offline |

---

## 🔌 Service ports (default)

| Service | Port | Override env | Health URL |
|---------|------|--------------|------------|
| FastAPI | `8102` | — | http://localhost:8102/health |
| Vite UI | `5173` | — | http://localhost:5173 |
| PostgreSQL (AIFlow) | `5433` | `AIFLOW_DB_PORT` | `pg_isready -U aiflow` |
| Redis | `6379` | — | `redis-cli ping` |
| Kroki (diagrams) | `8080` | — | http://localhost:8080 |
| Vault (dev) | `8210` | `AIFLOW_VAULT_PORT` | http://localhost:8210/v1/sys/health |
| Langfuse (self-host) | `3000` | — | http://localhost:3000/api/public/health |
| Langfuse Postgres | `5434` | — | — |

---

## 🚀 Quick start (manual)

### 1. Setup (first time)

```bash
make setup                  # creates .venv, installs deps via uv
cp .env.example .env        # then edit: OPENAI_API_KEY, JWT keys, ...
bash scripts/generate_jwt_keys.sh   # creates jwt_private.pem / jwt_public.pem
```

### 2. Sanity check the environment

```bash
bash scripts/check_environment.sh   # checks: python, uv, docker, .venv, .env, uv.lock
```

### 3. Start everything

```bash
bash scripts/start_stack.sh --full
```

### 4. Seed admin user

```bash
.venv/Scripts/python.exe scripts/seed_admin.py
# uses AIFLOW_ADMIN_EMAIL / AIFLOW_ADMIN_PASSWORD from .env
# default: admin@bestix.hu / AiFlowDev2026!
```

### 5. Smoke test

```bash
bash scripts/smoke_test.sh        # <30s: auth + health + 4 core endpoints + source=backend
```

---

## 🛠 Development

### Make targets

| Target | What it does |
|--------|--------------|
| `make setup` / `make setup-full` | Create venv + install deps (`-full` adds vectorstore/rpa/ui extras) |
| `make dev` | Docker services up + DB migrate |
| `make api` | FastAPI on :8102 with hot-reload |
| `make worker` | arq worker (Redis queue consumer) |
| `make test` | Unit tests |
| `make test-cov` | Unit tests + coverage report |
| `make test-integration` | Integration tests (real PG + Redis) |
| `make test-ui` | Playwright UI tests |
| `make test-prompts` | Promptfoo prompt tests |
| `make test-all` | Unit + integration + prompts |
| `make lint` / `make lint-fix` | ruff + mypy (auto-fix variant) |
| `make migrate` / `make migrate-new NAME=add_xyz` | Apply / create migration |
| `make db-reset` | Drop + recreate + migrate (CAUTION) |
| `make lock` | Regenerate `uv.lock` |
| `make clean` | Remove temp files (incl. `__pycache__`) |
| `make check-env` | Verify dev environment |
| `make skill-list` / `make workflow-list` | List skills / workflows |
| `make deploy` / `make deploy-status` / `make deploy-logs` / `make deploy-down` | Production stack (nginx + React SPA) |

### Testing levels

| Level | Path | Real services | Duration |
|-------|------|---------------|----------|
| **Unit** | `tests/unit/` | none (mocks for LLM only) | ~7 min, 2424 tests |
| **Integration** | `tests/integration/` | real PG + Redis + (optional) real OpenAI | ~5 min, 125 tests |
| **E2E** (Phase 1a/1b/UC) | `tests/e2e/v1_4_*` `tests/e2e/v1_5_*` | real PG + Redis | ~2 min, 232 tests |
| **E2E live UI** | `tests/e2e/test_*.py` | API :8102 + Vite :5173 | session-time only |
| **`ci-cross-uc`** | mixed (4 UC smoke) | PG + Redis | <10 min, 42 tests |
| **Guardrails** | `tests/guardrails/` (promptfoo) | OpenAI (cost) | varies |

> **Real services only.** No mocked PostgreSQL, Redis, or LLM in integration / E2E. See `tests/CLAUDE.md` and `01_PLAN/24_TESTING_REGRESSION_STRATEGY.md`.

> **Langfuse cloud teardown hang:** when `AIFLOW_LANGFUSE__ENABLED=true` + `HOST=https://cloud.langfuse.com`, FastAPI lifespan teardown can stall on `langfuse._score_ingestion_queue.join()`. Workaround for tests: `AIFLOW_LANGFUSE__ENABLED=false pytest tests/integration/`.

### Slash commands (Claude Code)

Session lifecycle: `/next` → `/status` → `/implement` → `/dev-step` → `/review` → `/session-close`

Quality gates: `/smoke-test`, `/regression`, `/lint-check`, `/live-test <module>`

UI pipeline (7 hard gates, strict order): `/ui-journey` → `/ui-api-endpoint` → `/ui-design` → `/ui-page` / `/ui-component` → `/live-test`

Plans: `/update-plan`, `/validate-plan`

Prompts / services: `/new-prompt`, `/prompt-tuning`, `/quality-check`, `/service-test`, `/service-hardening`, `/pipeline-test`, `/new-pipeline`, `/new-step`, `/new-test`

Auto-sprint: `/auto-sprint max_sessions=N notify=stop_only|all` (autonomous DOHA-style chaining)

---

## 📁 Project structure

```
src/aiflow/         Framework: core, engine, api, services, pipeline, guardrails, security
skills/             8 skills (each with prompts/, workflows/, tests/)
aiflow-admin/       React 19 + Tailwind v4 + Vite admin dashboard (26 pages)
01_PLAN/            58+ planning docs (110_USE_CASE_FIRST_REPLAN.md = active)
tests/              unit/ · integration/ · e2e/ · guardrails/ · ui-live/
alembic/            47 versioned migrations
scripts/            Operator + dev scripts (start_stack.sh, seed_admin.py, …)
deployments/        Tenant-specific deployment YAMLs (BestIx Kft sample)
docs/               Sprint retros, PR descriptions, runbooks, OpenAPI snapshot
prompts/            Workflow + sessions prompts (Langfuse-synced)
session_prompts/    DOHA-style session prompt archive + NEXT.md pointer
.claude/            Skills · agents · slash commands · settings · hooks
out/                One-off architecture review reports
data/fixtures/      Test fixtures (UC1 invoices, UC2 RAG, UC3 emails)
```

---

## 🔐 Environment & secrets

`.env` in repo root (gitignored). Copy from `.env.example`:

| Variable | Purpose | Example |
|----------|---------|---------|
| `AIFLOW_DATABASE__URL` | PG DSN | `postgresql+asyncpg://aiflow:aiflow_dev_password@localhost:5433/aiflow_dev` |
| `AIFLOW_REDIS__URL` | Redis DSN | `redis://localhost:6379/0` |
| `AIFLOW_ENVIRONMENT` | `dev` / `staging` / `prod` | `dev` |
| `AIFLOW_DB_PORT` | Override Docker PG port | `5433` |
| `AIFLOW_VAULT_PORT` | Override Docker Vault port | `8210` |
| `OPENAI_API_KEY` | LLM | `sk-...` |
| `AIFLOW_LANGFUSE__ENABLED` | Trace export gate | `true` |
| `AIFLOW_LANGFUSE__HOST` | Cloud or self-host URL | `https://cloud.langfuse.com` or `http://localhost:3000` |
| `AIFLOW_LANGFUSE__PUBLIC_KEY` / `__SECRET_KEY` | Project keys | `pk-lf-...` / `sk-lf-...` |
| `AIFLOW_SECURITY__JWT_PRIVATE_KEY_PATH` / `__JWT_PUBLIC_KEY_PATH` | RS256 PEMs | `./jwt_private.pem` |
| `AIFLOW_ADMIN_EMAIL` / `AIFLOW_ADMIN_PASSWORD` | Bootstrap admin | — |
| `AZURE_DI_*` | Azure Document Intelligence (optional OCR) | — |
| `IMAP_*` / `EMAIL_PASSWORD` | UC3 email source (Office 365 / Gmail) | — |
| `AIFLOW_PROMPT_WORKFLOWS__ENABLED` / `__SKILLS_CSV` | PromptWorkflow per-skill rollout | `false` / `""` (default off) |
| `AIFLOW_UC3_*` | UC3 attachment-intent / extraction flags | per-feature |
| `AIFLOW_COST_GUARDRAIL__ENABLED` / `__DRY_RUN` | Pre-flight cost gate | `false` / `true` |

> **Secrets management:** in dev, `.env`. In prod, Vault (`docker-compose.vault.yml` for local, external cluster + AppRole for production). See `docs/runbooks/vault_rotation.md` and `docs/secrets_inventory.md` (15 secrets cataloged).

> **Air-gap deployment:** Profile A (BGE-M3 + self-hosted Langfuse + Vault dev) covered by `docs/airgapped_deployment.md`.

---

## ✅ Validation matrix (post-startup checklist)

```bash
# 1. Health summary (no startup)
bash scripts/start_stack.sh --validate-only

# 2. Smoke test (auth + 8 endpoints, <30s)
bash scripts/smoke_test.sh

# 3. Regression — unit (~7m, 2424 tests, ≥65% coverage)
.venv/Scripts/python.exe -m pytest tests/unit/ --cov=aiflow

# 4. Regression — integration (~5m, real PG + Redis + OpenAI)
AIFLOW_LANGFUSE__ENABLED=false PYTHONPATH=src .venv/Scripts/python.exe \
    -m pytest tests/integration/ --timeout=300 --timeout-method=thread

# 5. Regression — E2E phase 1a/1b/UC (~2m)
AIFLOW_LANGFUSE__ENABLED=false PYTHONPATH=src .venv/Scripts/python.exe \
    -m pytest tests/e2e/v1_4_0_phase_1a tests/e2e/v1_4_1_phase_1b \
              tests/e2e/v1_4_11_uc3_attachment tests/e2e/v1_5_0_q_s136_extraction

# 6. UI tsc check
cd aiflow-admin && npx tsc --noEmit

# 7. Live UI journey (Playwright MCP, after starting stack with --with-api --with-ui)
# Use Claude Code: /live-test <module>
```

---

## 📊 Key numbers (v1.5.3 Sprint T)

| Metric | Value |
|--------|-------|
| Routers / endpoints | 31 / 196 |
| DB tables / migrations | 50 / 47 (head: 047) |
| Pipeline adapters / templates | 22 / 10 |
| Skills | 8 |
| Source adapters | 5 (Email · File · Folder · Batch · API) |
| Embedder profiles | 3 (BGE-M3 / Azure OAI / OAI surrogate) |
| UI pages | 26 |
| Unit tests | 2424 |
| Integration tests | ~125 |
| E2E tests (Phase 1a/1b/UC) | ~430 (incl. journey suites) |
| Guardrail tests | 129 |
| Security tests | 97 |
| Promptfoo cases | 96 |
| Coverage (unit) | 69.81% (gate ≥65%, trajectory → 80%) |
| `ci-cross-uc` (4 UC smoke) | 42 tests, 19s wall-clock |

---

## 🐳 Docker compose files

- `docker-compose.yml` — core (db, redis, kroki) + `chat` profile (Open WebUI :3100) + `full` profile (Dockerized API + worker) + `tools` profile (pgadmin :5050)
- `docker-compose.vault.yml` — Vault dev :8210 overlay
- `docker-compose.langfuse.yml` — self-hosted Langfuse :3000 + Postgres :5434 overlay
- `docker-compose.prod.yml` — production stack (nginx + React SPA) used by `make deploy`

```bash
# Just the core
docker compose up -d

# Core + Vault
docker compose -f docker-compose.yml -f docker-compose.vault.yml up -d

# Production
make deploy
```

---

## 📚 Documentation

- **Active plan:** `01_PLAN/110_USE_CASE_FIRST_REPLAN.md`
- **Architecture (v2):** `01_PLAN/100_AIFLOW_v2_ARCHITECTURE_REFINEMENT_OVERVIEW.md` (+ 100_b through 106)
- **Best practices:** `01_PLAN/60_CLAUDE_CODE_BEST_PRACTICES_REFERENCE.md`
- **Master plan:** `01_PLAN/AIFLOW_MASTER_PLAN.md`
- **Sprint retros:** `docs/sprint_*_retro.md` (Sprint K–T)
- **Runbooks:** `docs/runbooks/vault_rotation.md`, `docs/airgapped_deployment.md`, `docs/uc1_golden_path_report.md`
- **OpenAPI:** `docs/api/openapi.yaml` (regenerate via `scripts/export_openapi.py`)
- **Sample deployment:** `deployments/bestix/` (3 instance YAMLs for BestIxCom Kft)
- **Project context for Claude:** `CLAUDE.md` (sprint history banner) and skill `.claude/skills/aiflow-*` (auto-loaded by Claude Code)

---

## 🛡 Conventions

- **Async-first** — all I/O is `await`-ed.
- **Pydantic everywhere** — config, API models, step I/O, DB schemas.
- **structlog only** — never `print()`; always `logger.info("event", key=value)`.
- **Steps** — `@step` decorator, typed `BaseModel` I/O, stateless.
- **Prompts** — YAML only (`prompts/` + `skills/*/prompts/`); Langfuse-synced; Jinja2 templating.
- **Errors** — inherit `AIFlowError`, set `is_transient=True/False` for retry semantics.
- **DB changes** — always via Alembic; new columns `nullable=True` initially.
- **Auth** — PyJWT RS256 (NOT python-jose); bcrypt (NOT passlib); API key prefix `aiflow_sk_`.
- **Package manager** — `uv` (lockfile: `uv.lock`); never `pip install` outside venv.
- **Services in Docker** (PG :5433, Redis :6379, Kroki :8080), Python locally from `.venv`.
- **Real testing only** — never mock PG/Redis/LLM. Docker for real services.
- **Branch policy** — base `main`; feature branches `feature/<sprint-letter>-s<N>-<topic>`; squash-merge with conventional commits + Co-Authored-By.

---

## 🔄 Session workflow (Claude Code, DOHA-aligned)

```
/clear → /next → [session work] → /session-close → /clear → /next → ...
```

Auto-sprint (autonomous): `/auto-sprint max_sessions=16 notify=stop_only` — chains sessions via `ScheduleWakeup ~90s`, persists state in `session_prompts/.auto_sprint_state.json`, logs to `session_prompts/.notifications.log`.

---

## 🆘 Troubleshooting

| Symptom | Fix |
|---------|-----|
| `ModuleNotFoundError: No module named 'aiflow'` after moving project folder | `bash scripts/start_stack.sh` (auto-fixes) or manually `uv pip install -e .` |
| `pytest` hangs in TestClient teardown | Set `AIFLOW_LANGFUSE__ENABLED=false` for the run |
| Stale paths in tracebacks (e.g. old OneDrive path) | Purge bytecode caches: `find . -name __pycache__ -type d -exec rm -rf {} +` |
| Kroki :8080 fails to start | Another container has the port — non-fatal, diagrams unavailable |
| `pgvector` extension missing | Use the `pgvector/pgvector:pg16` image (already in `docker-compose.yml`) |
| Coverage drops below 65% | The pre-commit hook will block; coverage trajectory is 65.67% → 80% |
| BGE-M3 weights missing | `python scripts/bootstrap_bge_m3.py` |
| Langfuse keypair missing on self-host | `python scripts/bootstrap_langfuse.py` |
| Phase-1a regression count drift (199 vs 198) | Pre-existing stale gate in `tests/e2e/v1_4_1_phase_1b/test_multi_source_e2e.py:586` |

---

## License

MIT — see `pyproject.toml`. Author: BestIxCom Kft (`dev@bestixcom.hu`).
