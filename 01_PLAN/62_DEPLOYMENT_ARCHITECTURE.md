# AIFlow Deployment Architecture

> **Verzio:** 1.0 | **Datum:** 2026-04-05
> **Kontextus:** Sprint B B0.4 — Fejlesztesi vs uzemeltetesi kornyezet megkulonboztetes

---

## 1. Ket Kornyezet — Kulcsfontossagu Megkulonboztetes

```
FEJLESZTESI IDO (Claude Code tamogatja)
+------------------------------------------------------------+
| Tervezes → Fejlesztes → TESZTELES → Karbantartas → Debug   |
|                                                             |
| Claude Code SZEREPE:                                        |
|   - Tervez (session prompt, /dev-step)                      |
|   - Fejleszt (kod iras, /new-prompt, /new-pipeline)         |
|   - TESZTEL (pytest, Promptfoo, Playwright, /regression)    |
|   - Karbantart (/service-hardening, /quality-check)         |
|   - Dokumental (/update-plan, CLAUDE.md)                    |
|                                                             |
| Claude Code NEM futtatja uzemszeruen az AIFlow-kat!         |
+----------------------------+-------------------------------+
                             | deploy (Docker)
                             v
UZEMELTETESI IDO (Docker containers, ugyfel-ready)
+------------------------------------------------------------+
| Claude Code NEM SZUKSEGES — minden ONALLOAN fut!            |
|                                                             |
| +--------------------------------------------------------+ |
| | aiflow-admin UI (React 19 + Tailwind v4)               | |
| |  - Pipeline trigger (user inditja az Invoice Findert)  | |
| |  - User interakcio (Verification, Chat, Dashboard)     | |
| |  - Monitoring (Health, Costs, Audit)                   | |
| +-----------------------+--------------------------------+ |
|                         | API call (fetch /api/v1/*)       |
| +-----------------------v--------------------------------+ |
| | FastAPI (src/aiflow/)                                  | |
| |  - PipelineRunner (YAML-bol vezerelt)                  | |
| |  - Service orchestration + Guardrails                  | |
| |  - Notification (email riport automatikusan)           | |
| +-----------------------+--------------------------------+ |
|                         |                                   |
| +-----------------------v--------------------------------+ |
| | Infrastructure (Docker Compose)                        | |
| |  PostgreSQL 5433 | Redis 6379 | Kroki 8000             | |
| |  LLM API-k (OpenAI, Azure) → kulso hivasok            | |
| +--------------------------------------------------------+ |
+------------------------------------------------------------+
```

---

## 2. Fejlesztesi Ciklus (Claude Code)

### Eszkozok

| Eszkoz | Mikor | Parancs |
|--------|-------|---------|
| `/dev-step` | Minden kodvaltozas | CHECK → CODE → TEST → LINT → COMMIT |
| `/regression` | Commit elott | pytest + coverage |
| `/lint-check` | Minden session | ruff + tsc |
| `/new-prompt` | Uj prompt | YAML + Promptfoo generalas |
| `/prompt-tuning` | Prompt finomhangolas | 6 lepesu lifecycle |
| `/quality-check` | LLM minoseg | Promptfoo eval + koltseg |
| `/service-hardening` | Skill audit | 10-pontos checklist |
| `/pipeline-test` | Pipeline E2E | Valos futatas + cost + DB |
| `/update-plan` | Session vege | Progress + szamok |

### Fejlesztesi Infrastructure

- **Python:** 3.12+, `.venv/` (uv-managed), NOT system Python
- **Docker:** PostgreSQL 5433, Redis 6379, Kroki 8000 — fejlesztesi instance-ok
- **UI dev:** Vite 5174 (hot reload), proxy → API 8102
- **Langfuse:** Cloud instance, prompt versioning + tracing
- **Promptfoo:** 54 test case, valos LLM hivasok

---

## 3. Uzemeltetesi Architektura (Docker Compose)

### docker-compose.yml (dev)

```yaml
services:
  # --- Infrastructure ---
  postgres:
    image: pgvector/pgvector:pg16
    ports: ["5433:5432"]
    volumes: [pgdata:/var/lib/postgresql/data]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  kroki:
    image: yuzutech/kroki
    ports: ["8000:8000"]

  # --- Application (B9-ben containerizaljuk) ---
  # api:
  #   build: .
  #   ports: ["8102:8102"]
  #   depends_on: [postgres, redis]
  #
  # worker:
  #   build: .
  #   command: arq aiflow.execution.worker.WorkerSettings
  #   depends_on: [postgres, redis]
  #
  # ui:
  #   build: ./aiflow-admin
  #   ports: ["5174:80"]
```

### docker-compose.prod.yml — IMPLEMENTALVA (B9, 2026-04-09)

```yaml
# 6 service: db + redis + kroki + api + worker + ui
# Inditás: make deploy (vagy: docker compose -f docker-compose.prod.yml up -d --build)
services:
  db:        pgvector/pgvector:pg16      # healthcheck: pg_isready
  redis:     redis:7-alpine              # healthcheck: redis-cli ping, 512mb, volatile-lru
  kroki:     yuzutech/kroki              # healthcheck: wget
  api:       build target: api           # healthcheck: httpx /health/live, JWT secrets mount
  worker:    build target: worker        # depends: db, redis
  ui:        build: ./aiflow-admin       # node:22→nginx multi-stage, port 80, /api proxy → api:8000

# Fajlok:
#   docker-compose.prod.yml  — production compose (6 service)
#   aiflow-admin/Dockerfile  — multi-stage (node:22-alpine build → nginx:alpine)
#   aiflow-admin/nginx.conf  — SPA fallback + /api proxy + SSE support + gzip
#   .dockerignore            — projekt szintu
#   .env.production.example  — production config template
#   Makefile: deploy, deploy-status, deploy-down, deploy-logs targetok
```

---

## 4. Deploy Folyamat

```
DEV (helyi)
  Claude Code + Docker infra
  Fejlesztes + teszteles
       |
       v
STAGING / PRODUCTION (B9 — IMPLEMENTALVA)
  make deploy  # docker compose -f docker-compose.prod.yml up -d --build
  Teljes E2E teszt Docker-ben
  Playwright UI-bol pipeline trigger
       |
       v
PRODUCTION (v1.3.0+)
  Ugyanaz a Docker Compose
  .env.production konfiguracio
  SSL terminalas (reverse proxy)
```

---

## 5. Prompt Lifecycle (Release Nelkuli Frissites!)

```
1. DIAGNOZIS    — Langfuse trace → gyenge pontok
2. FEJLESZTES   — prompt YAML ujrairas (Claude Code)
3. TESZTELES    — Promptfoo eval (valos LLM, 95%+ gate)
4. VALIDACIO    — human review
5. ELESITES     — Langfuse label swap: "dev" → "prod"
                  NEM KELL: Docker rebuild, deploy, git tag!
                  PromptManager cache: 5p auto VAGY API invalidate
6. MONITORING   — Langfuse trace osszehasonlitas

Meglevo:
  - PromptManager (prompts/manager.py): cache → Langfuse → YAML fallback
  - POST /api/v1/prompts/{name}/invalidate (B0.5-ben)
  - POST /api/v1/prompts/reload-all (B0.5-ben)
```

---

## 6. UI Pipeline Trigger (Uzemeltetesi Mod)

A USER az UI-bol inditja a pipeline-okat:

| Journey | UI Trigger | API | Pipeline |
|---------|-----------|-----|----------|
| Invoice Finder | "Scan Mailbox" gomb | POST /api/v1/pipelines/run | invoice_finder_v1 |
| Diagram Generator | "Generate" gomb | POST /api/v1/pipelines/run | diagram_generator_v1 |
| Spec Writer | "Write Spec" gomb | POST /api/v1/pipelines/run | spec_writer_v1 |
| RAG Ingest | "Upload & Ingest" gomb | POST /api/v1/rag/ingest | advanced_rag_ingest |

Pipeline statusz: UI polling / WebSocket → futasi allapot megjelenitese.
Eredmeny: UI-ban megjelenitett output (riport, diagram, spec, chat).

---

## 7. Konfiguracio

### .env.example (fejlesztesi)

```bash
# Database
DATABASE_URL=postgresql+asyncpg://aiflow:aiflow@localhost:5433/aiflow

# Redis
REDIS_URL=redis://localhost:6379

# LLM
OPENAI_API_KEY=sk-...
AIFLOW_DEFAULT_MODEL=gpt-4o-mini

# Langfuse
AIFLOW_LANGFUSE__ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-...
LANGFUSE_SECRET_KEY=sk-...

# Azure Document Intelligence (optional)
AZURE_DI_ENDPOINT=https://...
AZURE_DI_API_KEY=...

# Auth
JWT_PRIVATE_KEY_PATH=jwt_private.pem
JWT_PUBLIC_KEY_PATH=jwt_public.pem

# Server
AIFLOW_HOST=0.0.0.0
AIFLOW_PORT=8102
```
