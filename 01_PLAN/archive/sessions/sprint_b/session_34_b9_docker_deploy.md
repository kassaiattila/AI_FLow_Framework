# AIFlow Sprint B — Session 34 Prompt (B9: Docker Containerization + Ügyfél-Ready Deploy)

> **Datum:** 2026-04-12
> **Branch:** `feature/v1.3.0-service-excellence` | **HEAD:** `05a21e5`
> **Port:** API 8102 (dev) / 8000 (Docker), Frontend 5174 (dev) / 80 (nginx)
> **Elozo session:** S33 — B8 DONE (UI Journey: 6 journey-based sidebar + breadcrumb + 4 dashboard journey card + J1/J2 finomitasok, 4 commit: 804baa7 + 86494b1 + 47e69e1 + 05a21e5)
> **Terv:** `01_PLAN/58_POST_SPRINT_HARDENING_PLAN.md` (B9 szekcio, sor 1674-1712)
> **Session tipus:** CODE + INFRA — Docker compose prod, UI container, pipeline trigger, E2E
> **Workflow:** Docker compose → UI Dockerfile → nginx → Pipeline trigger UI → Deploy teszt → E2E → Commit(ok)

---

## KONTEXTUS

### S33 Eredmenyek (B8 — DONE, 4 commit)

**B8 — UI Journey Implementacio (`804baa7` + `86494b1` + `47e69e1` + `05a21e5`):**
- `aiflow-admin/src/layout/Sidebar.tsx`: 6 journey-based csoport + bottom menu (RPA, Cubix)
- `aiflow-admin/src/components-new/Breadcrumb.tsx`: UJ route-based hierarchia
- `aiflow-admin/src/layout/AppShell.tsx`: Breadcrumb integracio
- `aiflow-admin/src/pages-new/Dashboard.tsx`: 4 journey kartya + alert banner
- `aiflow-admin/src/pages-new/Documents.tsx`: ?filter= URL param support
- `aiflow-admin/src/pages-new/ProcessDocs.tsx`: diagram_type 3 opcio selector
- `aiflow-admin/src/pages-new/Runs.tsx`: restart gomb
- `aiflow-admin/src/locales/{hu,en}.json`: ~24 uj i18n kulcs
- `tests/e2e/test_journey_navigation.py`: 5 E2E teszt
- Regresszio: 1443 unit PASS, ruff + tsc clean

**Infrastruktura (v1.3.0 — S33 utan):**
- 27 service | 175 API endpoint (27 router) | 48 DB tabla | 31 migracio
- 22 pipeline adapter | 10 pipeline template | 7 skill | 23 UI oldal
- **1443 unit test** | 129 guardrail teszt | 97 security teszt | **114 E2E** | **96 promptfoo test**

### Jelenlegi Docker Allapot (B9 elott — MI VAN MAR?)

```
=== MEGLEVO DOCKER INFRASTRUKTURA ===

docker-compose.yml (107 sor):
  CORE (always run — make dev):
    db:        pgvector/pgvector:pg16       5433:5432   healthcheck: pg_isready
    redis:     redis:7-alpine               6379:6379   healthcheck: redis-cli ping
    kroki:     yuzutech/kroki               8080:8000   (no healthcheck)

  PROFILE: "full" (make dev-docker):
    api:       build target: api            8000:8000   depends: db, redis
    worker:    build target: worker         —           depends: db, redis
    → EZEK MUKODNEK (Dockerfile mar van) de NEM TELJESEN TESZTELTEK

  PROFILE: "chat":
    open-webui: ghcr.io/open-webui          3100:8080   nem szukseges B9-hez

  PROFILE: "tools":
    pgadmin:   dpage/pgadmin4               5050:80     nem szukseges B9-hez

Dockerfile (50 sor, multi-stage):
  builder:     python:3.12-slim + uv + deps
  api:         uvicorn 0.0.0.0:8000, /health/live healthcheck, USER aiflow
  worker:      python -m aiflow.execution.worker
  rpa-worker:  playwright/python:v1.40.0 + ffmpeg + chromium

HIANYZO / B9-BEN LETREHOZANDO:
  ❌ aiflow-admin Dockerfile (Vite build → nginx) — NEM LETEZIK!
  ❌ nginx.conf (UI szerviralas + /api proxy → api:8000) — NEM LETEZIK!
  ❌ docker-compose.prod.yml (egylepteku deploy) — NEM LETEZIK!
  ❌ .dockerignore — NEM LETEZIK!
  ❌ UI "full Docker" mod: Vite proxy localhost:8102 → Docker-ben nginx kell
  ❌ README.md Docker szekció — nincs "Igy inditsd Docker-ben" guide
  ❌ Pipeline trigger UI gombok (Scan Mailbox, stb.) — reszben kesz

MEGLEVO + HASZNALHATO:
  ✅ Dockerfile (api + worker target — multi-stage)
  ✅ docker-compose.yml core services (db, redis, kroki)
  ✅ docker-compose.yml "full" profile (api, worker — alap)
  ✅ .env.example (28 sor)
  ✅ Makefile: dev, dev-docker, api, worker, down targetok
  ✅ /health/live + /health/ready + /health endpointok (health.py 287 sor)
  ✅ aiflow-admin/dist/ — mar van egy build output (index.html + assets/)
  ✅ vite.config.ts: proxy /api → localhost:8102, /health → localhost:8102
  ✅ 01_PLAN/62_DEPLOYMENT_ARCHITECTURE.md (249 sor, terv referencia)
```

---

## B9 FELADAT: 6 lepes — Docker files → UI container → Pipeline trigger → Deploy teszt → E2E → Commit

> **Gate:** `docker compose -f docker-compose.prod.yml up` → MINDEN szolgaltatas fut → UI-bol pipeline inditható → E2E PASS.
> **Eszkozok:** `/dev-step`, `/regression`, `/lint-check`, Playwright, Docker
> **Docker:** PostgreSQL (5433), Redis (6379), Kroki (8080) — KELL!

---

### LEPES 1: B9.1 — Docker alapok (.dockerignore + UI Dockerfile + nginx)

```
Hol: .dockerignore (UJ)
     aiflow-admin/Dockerfile (UJ)
     aiflow-admin/nginx.conf (UJ)

Cel: UI production container (Vite build → nginx), /api proxy az api containerhez.

KONKRET TEENDOK:

1. .dockerignore (projekt gyoker):
   node_modules/
   .venv/
   __pycache__/
   .git/
   out/
   *.pyc
   .env
   jwt_*.pem
   tests/
   01_PLAN/
   .claude/

2. aiflow-admin/Dockerfile (multi-stage):
   
   # Build stage
   FROM node:22-alpine AS build
   WORKDIR /app
   COPY package.json package-lock.json ./
   RUN npm ci
   COPY . .
   # API URL: nginx proxy, NEM localhost — build-time env
   ENV VITE_API_BASE_URL=""
   RUN npm run build
   
   # Production — nginx
   FROM nginx:alpine
   COPY --from=build /app/dist /usr/share/nginx/html
   COPY nginx.conf /etc/nginx/conf.d/default.conf
   EXPOSE 80
   HEALTHCHECK --interval=30s --timeout=3s \
     CMD wget -qO- http://localhost/health-ui || exit 1

3. aiflow-admin/nginx.conf:
   
   server {
     listen 80;
     root /usr/share/nginx/html;
     index index.html;
   
     # SPA fallback (hash router)
     location / {
       try_files $uri $uri/ /index.html;
     }
   
     # API proxy → FastAPI container
     location /api/ {
       proxy_pass http://api:8000;
       proxy_set_header Host $host;
       proxy_set_header X-Real-IP $remote_addr;
       proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
       # SSE: disable buffering
       proxy_buffering off;
       proxy_cache off;
       proxy_set_header Connection '';
       proxy_http_version 1.1;
       chunked_transfer_encoding off;
     }
   
     # Health proxy
     location /health {
       proxy_pass http://api:8000;
     }
   
     # UI health (nginx itself)
     location /health-ui {
       return 200 'ok';
       add_header Content-Type text/plain;
     }
   }

4. aiflow-admin/.dockerignore (UI-specifikus):
   node_modules/
   dist/
   .env
   *.md

Gate: `docker build -t aiflow-ui aiflow-admin/` → sikeres build,
      nginx elindithato, statikus fajlok szerviralatnak.
```

### LEPES 2: B9.2 — docker-compose.prod.yml

```
Hol: docker-compose.prod.yml (UJ fajl)

Cel: Egyetlen `docker compose -f docker-compose.prod.yml up` → MINDEN fut.

KONKRET TEENDOK:

1. docker-compose.prod.yml:

   services:
     # --- Infrastructure ---
     db:
       image: pgvector/pgvector:pg16
       environment:
         POSTGRES_DB: aiflow
         POSTGRES_USER: aiflow
         POSTGRES_PASSWORD: ${DB_PASSWORD:-aiflow_prod_password}
       volumes:
         - pgdata:/var/lib/postgresql/data
       healthcheck:
         test: ["CMD-SHELL", "pg_isready -U aiflow"]
         interval: 5s
         timeout: 5s
         retries: 5

     redis:
       image: redis:7-alpine
       command: >
         redis-server
         --maxmemory 512mb
         --maxmemory-policy volatile-lru
         --appendonly yes
         --requirepass ${REDIS_PASSWORD:-}
       volumes:
         - redisdata:/data
       healthcheck:
         test: ["CMD", "redis-cli", "ping"]
         interval: 5s
         retries: 5

     kroki:
       image: yuzutech/kroki
       healthcheck:
         test: ["CMD", "wget", "-qO-", "http://localhost:8000/"]
         interval: 30s
         retries: 3

     # --- Application ---
     api:
       build:
         context: .
         target: api
       environment:
         AIFLOW_DATABASE__URL: postgresql+asyncpg://aiflow:${DB_PASSWORD:-aiflow_prod_password}@db:5432/aiflow
         AIFLOW_REDIS__URL: redis://redis:6379/0
         AIFLOW_ENVIRONMENT: production
         AIFLOW_DEBUG: "false"
         AIFLOW_LOG_LEVEL: INFO
         OPENAI_API_KEY: ${OPENAI_API_KEY}
         AIFLOW_SECURITY__JWT_PRIVATE_KEY_PATH: /run/secrets/jwt_private
         AIFLOW_SECURITY__JWT_PUBLIC_KEY_PATH: /run/secrets/jwt_public
       depends_on:
         db: { condition: service_healthy }
         redis: { condition: service_healthy }
       healthcheck:
         test: ["CMD", "python", "-c", "import httpx; httpx.get('http://localhost:8000/health/live', timeout=3).raise_for_status()"]
         interval: 30s
         timeout: 5s
         retries: 3
       secrets:
         - jwt_private
         - jwt_public

     worker:
       build:
         context: .
         target: worker
       environment:
         AIFLOW_DATABASE__URL: postgresql+asyncpg://aiflow:${DB_PASSWORD:-aiflow_prod_password}@db:5432/aiflow
         AIFLOW_REDIS__URL: redis://redis:6379/0
         AIFLOW_ENVIRONMENT: production
         OPENAI_API_KEY: ${OPENAI_API_KEY}
       depends_on:
         db: { condition: service_healthy }
         redis: { condition: service_healthy }

     ui:
       build:
         context: ./aiflow-admin
       ports:
         - "${UI_PORT:-80}:80"
       depends_on:
         api: { condition: service_healthy }
       healthcheck:
         test: ["CMD", "wget", "-qO-", "http://localhost/health-ui"]
         interval: 30s
         retries: 3

   secrets:
     jwt_private:
       file: ./jwt_private.pem
     jwt_public:
       file: ./jwt_public.pem

   volumes:
     pgdata:
     redisdata:

2. API NEM expozdja a 8000 portot kozvetlenul — UI nginx proxy-za.
   Ha DEBUG kell, `docker compose -f docker-compose.prod.yml --profile debug up`
   ahol api portja 8000:8000.

3. FONTOS: a `make dev` workflow NEM VALTOZIK! A dev docker-compose.yml marad
   lokalis fejleszteshez. A prod.yml a deploy-hoz.

Gate: `docker compose -f docker-compose.prod.yml config` → valid YAML,
      minden service definialva, healthcheck-ek leteznek.
```

### LEPES 3: B9.3 — Makefile deploy targetok + .env.production.example

```
Hol: Makefile (bovites)
     .env.production.example (UJ)

Cel: Egyszerusitett deploy parancsok + production konfiguracio template.

KONKRET TEENDOK:

1. Makefile uj targetok:

   deploy: ## Build + start production stack
       docker compose -f docker-compose.prod.yml up -d --build
       @echo "Waiting for API..."
       @sleep 10
       docker compose -f docker-compose.prod.yml exec api alembic upgrade head
       @echo ""
       @echo "=== AIFlow Production Stack Running ==="
       @echo "UI:     http://localhost:${UI_PORT:-80}"
       @echo "Health: http://localhost:${UI_PORT:-80}/health"
       @echo ""

   deploy-status: ## Check production stack health
       docker compose -f docker-compose.prod.yml ps
       @echo ""
       @echo "--- Health Checks ---"
       curl -s http://localhost:${UI_PORT:-80}/health-ui && echo " (UI OK)"
       curl -s http://localhost:${UI_PORT:-80}/health | python -m json.tool 2>/dev/null || echo "API: checking..."

   deploy-down: ## Stop production stack
       docker compose -f docker-compose.prod.yml down

   deploy-logs: ## Show production logs
       docker compose -f docker-compose.prod.yml logs -f --tail=100

2. .env.production.example:

   # AIFlow Production Configuration
   # Copy to .env and fill in your values before `make deploy`

   # Database
   DB_PASSWORD=CHANGE_ME_STRONG_PASSWORD

   # LLM (at least one required)
   OPENAI_API_KEY=sk-your-production-key

   # UI Port (default: 80)
   UI_PORT=80

   # Redis (optional password)
   REDIS_PASSWORD=

   # Langfuse (recommended for production)
   AIFLOW_LANGFUSE__ENABLED=true
   AIFLOW_LANGFUSE__PUBLIC_KEY=pk-lf-...
   AIFLOW_LANGFUSE__SECRET_KEY=sk-lf-...
   AIFLOW_LANGFUSE__HOST=https://cloud.langfuse.com

Gate: `make deploy` parancs letezik, .env.production.example korrekt.
```

### LEPES 4: B9.4 — UI Pipeline Trigger integracio

```
Hol: aiflow-admin/src/pages-new/Emails.tsx (modositas — "Scan Mailbox" gomb)
     aiflow-admin/src/pages-new/Dashboard.tsx (bovites — pipeline status)

Cel: A USER az UI-bol inditja a pipeline-okat, NEM Claude-bol.

KONKRET TEENDOK:

1. Emails.tsx: "Scan Mailbox" gomb
   - Uj gomb a page tetejere: "Scan Mailbox" / "Levelada szkenneles"
   - Kattintas: POST /api/v1/pipelines/invoice_finder_v1/execute
   - Polling: useApi() refetchInterval-lal a futasi allapotot ellenorzi
   - Eredmeny: "3 uj szamla talalva" → Documents linkkel

2. ProcessDocs.tsx: mar KESZ (generate gomb meghivja a pipeline-t)
   → Csak ellenorizd hogy Docker-ben is mukodik (proxy helyes)

3. SpecWriter.tsx: mar KESZ (write gomb meghivja az API-t)
   → Csak ellenorizd hogy Docker-ben is mukodik

4. Dashboard.tsx: pipeline status banner
   - Ha van running pipeline: kis "Pipeline running..." banner a journey cards felett
   - Ha vegzett: "Pipeline completed — 3 documents found" → link

5. i18n: uj kulcsok (hu + en):
   - aiflow.emails.scanMailbox / "Scan Mailbox"
   - aiflow.emails.scanning / "Scanning..."
   - aiflow.emails.scanResult / "X new invoices found"
   - aiflow.dashboard.pipelineRunning / "Pipeline running..."
   - aiflow.dashboard.pipelineCompleted / "Pipeline completed"

FIGYELEM:
- Ellenorizd a pipeline execute endpoint-ot: 
  GET /api/v1/pipelines → listazza a pipeline-okat
  POST /api/v1/pipelines/{name}/execute → inditja a pipeline-t
  (Lehet hogy POST /api/v1/pipelines/run kell body-val — olvasd el a router.py-t!)
- Emails.tsx-nel olvasd el a meglevo Emails.tsx-t MIELOTT modositasz!

Gate: "Scan Mailbox" gomb lathato Emails oldalon, kattintas utan API-t hiv,
      valasz megjelenitve, tsc + ruff PASS.
```

### LEPES 5: B9.5 — Deploy teszteles + E2E

```
Hol: tests/e2e/test_docker_deploy.py (UJ fajl)
     A teljes Docker stack tesztelese

Cel: `docker compose -f docker-compose.prod.yml up` → healthy → E2E PASS.

KONKRET TEENDOK:

1. Docker build + start:
   a) docker compose -f docker-compose.prod.yml build
      → HIBA NELKUL (minden image epul)
   b) docker compose -f docker-compose.prod.yml up -d
      → Minden container "healthy" (max 60s varakozas)
   c) Alembic migration:
      docker compose -f docker-compose.prod.yml exec api alembic upgrade head

2. Manualis ellenorzes:
   a) http://localhost/health-ui → "ok" (nginx UI health)
   b) http://localhost/health → JSON (API health — PostgreSQL, Redis, version)
   c) http://localhost/ → AIFlow Dashboard (login oldal → bejelentkezes)
   d) Sidebar: 6 journey-based csoport + breadcrumb mukodik
   e) "Scan Mailbox" gomb → API hivas sikeres (vagy 404 ha nincs pipeline)

3. E2E teszt: tests/e2e/test_docker_deploy.py
   
   FONTOS: Ez a teszt CSAK AKKOR fut ha Docker stack fut!
   pytest.mark.skipif(not docker_available) dekorator!
   
   class TestDockerDeploy:
     def test_ui_serves_index(self):
       """nginx serves SPA index.html"""
       # HTTP GET http://localhost/ → 200, contains "AIFlow"
     
     def test_api_health_through_proxy(self):
       """API health accessible via nginx proxy"""
       # HTTP GET http://localhost/health → 200, JSON with "status"
     
     def test_login_and_dashboard(self, page: Page):
       """Full login flow in Docker environment"""
       # Navigate to http://localhost → login → dashboard
     
     def test_pipeline_trigger_available(self, authenticated_page: Page):
       """Pipeline trigger buttons visible in UI"""
       # Navigate to /emails → "Scan" gomb lathato

4. /regression → 1443+ unit + 114+ E2E — 0 uj fail
5. /lint-check → ruff + tsc → 0 warning
6. Docker down: docker compose -f docker-compose.prod.yml down

Gate: Docker build PASS, healthy, UI elerheto, API proxy mukodik,
      legalabb 2 Docker E2E PASS.
```

### LEPES 6: B9.6 — README + Plan update + Commit(ok)

```
Hol: README.md (bovites)
     01_PLAN/62_DEPLOYMENT_ARCHITECTURE.md (frissites)

1. README.md bovites (Docker szekció):

   ## Docker Deploy

   ```bash
   # 1. Configuration
   cp .env.production.example .env
   # Edit .env: set OPENAI_API_KEY, DB_PASSWORD

   # 2. Generate JWT keys (if not exists)
   openssl genrsa -out jwt_private.pem 2048
   openssl rsa -in jwt_private.pem -pubout -out jwt_public.pem

   # 3. Deploy
   make deploy

   # 4. Access
   open http://localhost    # AIFlow Dashboard
   ```

2. 62_DEPLOYMENT_ARCHITECTURE.md: kommentek frissitese → a tervezett docker-compose.prod.yml
   elrendezes mar IMPLEMENTALVA (B9).

3. /update-plan → 58 B9 row DONE + datum + commit SHA(k)
                CLAUDE.md + 01_PLAN/CLAUDE.md kulcsszamok frissitese

Commit strategia — KULON COMMITOK:
  1. feat(sprint-b): B9.1 docker production stack — UI container + nginx + compose
     (docker-compose.prod.yml + aiflow-admin/Dockerfile + nginx.conf + .dockerignore + Makefile)

  2. feat(sprint-b): B9.2 UI pipeline trigger — scan mailbox + pipeline status
     (Emails.tsx + Dashboard.tsx + i18n)

  3. test(sprint-b): B9.3 docker deploy E2E tests
     (tests/e2e/test_docker_deploy.py)

  4. docs(sprint-b): B9.4 deploy guide + plan update
     (README.md + 62_DEPLOYMENT_ARCHITECTURE.md + 58 plan)

Commit mindegyikhez:
  Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
```

---

## VEGREHAJTAS SORRENDJE

```
=== FAZIS A: DOCKER ALAPOK (LEPES 1-2) ===

--- LEPES 1: Docker files ---
.dockerignore UJ
aiflow-admin/Dockerfile UJ (node:22 → nginx)
aiflow-admin/nginx.conf UJ (/api proxy + SPA fallback)
aiflow-admin/.dockerignore UJ

--- LEPES 2: docker-compose.prod.yml ---
6 service: db + redis + kroki + api + worker + ui
Healthcheck minden service-en
Secrets: JWT kulcsok

>>> Docker build tesztelese: `docker compose -f docker-compose.prod.yml build`


=== FAZIS B: MAKEFILE + PIPELINE TRIGGER (LEPES 3-4) ===

--- LEPES 3: Makefile + .env ---
deploy, deploy-status, deploy-down, deploy-logs targetok
.env.production.example

--- LEPES 4: Pipeline trigger UI ---
Emails.tsx: "Scan Mailbox" gomb
Dashboard.tsx: pipeline status banner

>>> Docker stack inditasa: `make deploy`


=== FAZIS C: TESZTEK + LEZARAS (LEPES 5-6) ===

--- LEPES 5: Deploy teszt + E2E ---
Docker stack E2E tesztek
Manualis ellenorzes (UI + API + proxy)

--- LEPES 6: README + Plan + Commit ---
README.md Docker szekció
62_DEPLOYMENT_ARCHITECTURE.md frissites
3-4 commit
```

---

## KORNYEZET ELLENORZES

```bash
# Branch + HEAD
git branch --show-current     # → feature/v1.3.0-service-excellence
git log --oneline -5           # → 05a21e5 (B8 plan), 47e69e1 (B8 E2E), 86494b1 (B8 dashboard), ...

# Docker KELL!
docker --version               # → Docker 27+ (kell build + compose)
docker compose version         # → Docker Compose v2+
docker ps                      # → db, redis, kroki futnak (make dev)

# Meglevo Dockerfile:
cat Dockerfile                  # → 50 sor, multi-stage (builder → api → worker → rpa-worker)
wc -l docker-compose.yml        # → 107 sor (5 service + 4 profile)

# UI build:
ls aiflow-admin/dist/           # → index.html + assets/ (meglevo build output)
cat aiflow-admin/vite.config.ts  # → proxy /api → localhost:8102

# NEM LETEZIK (B9-ben letrehozando):
ls .dockerignore                 # → nincs
ls aiflow-admin/Dockerfile       # → nincs
ls aiflow-admin/nginx.conf       # → nincs
ls docker-compose.prod.yml       # → nincs
ls .env.production.example       # → nincs

# Health endpoint:
wc -l src/aiflow/api/v1/health.py  # → 287 sor (/health/live + /health/ready + /health)

# Makefile:
grep "deploy" Makefile            # → nincs deploy target meg

# Pipeline execute endpoint:
grep -n "execute" src/aiflow/api/v1/pipelines.py | head -10  # → endpoint szignatura

# Emails.tsx:
wc -l aiflow-admin/src/pages-new/Emails.tsx
```

---

## MEGLEVO KOD REFERENCIAK (olvasd el mielott irsz!)

```
# KRITIKUS — Docker alapok:
Dockerfile                                     — 50 sor, multi-stage (api/worker/rpa-worker)
docker-compose.yml                             — 107 sor, 5 service + 3 profile
.env.example                                   — 28 sor, fejlesztesi config
Makefile                                       — 136 sor, dev/test/lint targetok

# KRITIKUS — API:
src/aiflow/api/v1/health.py                   — 287 sor, health endpointok
src/aiflow/api/v1/pipelines.py                — pipeline execute endpoint
src/aiflow/api/app.py                          — FastAPI factory (router registracio)

# UI:
aiflow-admin/vite.config.ts                    — 36 sor, proxy config (dev: /api → 8102)
aiflow-admin/package.json                      — 58 sor, build: vite build
aiflow-admin/src/pages-new/Emails.tsx          — pipeline trigger gomb ide kerul
aiflow-admin/src/pages-new/Dashboard.tsx       — pipeline status banner ide kerul

# Deploy terv referencia:
01_PLAN/62_DEPLOYMENT_ARCHITECTURE.md          — 249 sor, architektura diagram
01_PLAN/58_POST_SPRINT_HARDENING_PLAN.md       — B9 szekcio (sor 1674-1712)

# Worker:
src/aiflow/execution/worker.py                — 74 sor, arq worker entry point

# E2E referencia:
tests/e2e/conftest.py                          — navigate_to(), authenticated_page
tests/e2e/test_journey_navigation.py           — 167 sor, B8 navigacio tesztek
```

---

## FONTOS SZABALYOK (CODE + INFRA session)

- **`make dev` NEM VALTOZIK!** A dev workflow marad. A prod.yml kulon fajl.
- **Port mapping:** Dev: API 8102, UI 5174. Prod: API 8000 (internal), UI 80 (nginx).
- **nginx proxy:** `/api/*` → `http://api:8000`, `/health` → `http://api:8000`, minden mas → SPA
- **SSE fontos:** nginx MUST disable buffering a `/api/v1/*/stream` endpointoknal!
- **Secrets:** JWT kulcsok Docker secrets-kent, NEM environment variable-kent.
- **Healthcheck:** MINDEN service-nek legyen healthcheck (db, redis, kroki, api, worker, ui).
- **Non-root:** API + worker container `aiflow` user-kent fut (mar igy van a Dockerfile-ban).
- **Async-first** — API kód async marad, nem kell valtoztatni.
- **i18n**: minden uj UI string `translate()`.
- **NE commitolj:** `.env`, `jwt_*.pem`, `.code-workspace`, `out/`, `100_*.md`, session prompt.
- **Branch:** SOHA NE commitolj main-ra.

---

## B9 GATE CHECKLIST

```
FAZIS A — DOCKER:

B9.1 — Docker files:
[ ] .dockerignore letezik (projekt gyoker)
[ ] aiflow-admin/Dockerfile letezik (node:22 → nginx multi-stage)
[ ] aiflow-admin/nginx.conf letezik (SPA fallback + /api proxy)
[ ] aiflow-admin/.dockerignore letezik
[ ] `docker build -t aiflow-ui aiflow-admin/` → sikeres

B9.2 — docker-compose.prod.yml:
[ ] docker-compose.prod.yml letezik (6 service)
[ ] Minden service-nek van healthcheck
[ ] `docker compose -f docker-compose.prod.yml config` → valid
[ ] `docker compose -f docker-compose.prod.yml build` → sikeres

FAZIS B — DEPLOY:

B9.3 — Makefile + env:
[ ] `make deploy` target letezik
[ ] `make deploy-status` target letezik
[ ] .env.production.example letezik

B9.4 — Pipeline trigger:
[ ] Emails.tsx: "Scan Mailbox" gomb lathato
[ ] Kattintas → API hivas (POST /api/v1/pipelines/.../execute)
[ ] tsc + ruff PASS

FAZIS C — TESZTEK:

B9.5 — Deploy teszt:
[ ] `docker compose -f docker-compose.prod.yml up -d` → healthy
[ ] http://localhost/ → AIFlow login
[ ] http://localhost/health → API health JSON
[ ] http://localhost/health-ui → "ok"
[ ] tests/e2e/test_docker_deploy.py letezik
[ ] /regression PASS (1443+ unit, 114+ E2E — 0 uj fail)
[ ] /lint-check PASS

B9.6 — Commit + Plan:
[ ] README.md Docker szekció
[ ] 3-4 commit
[ ] 58 plan B9 row DONE + datum + commit SHA
[ ] CLAUDE.md frissitese (E2E+)
```

---

## BECSULT SCOPE

- **4 uj Docker-fajl** (.dockerignore, aiflow-admin/Dockerfile, nginx.conf, docker-compose.prod.yml)
- **1 uj env template** (.env.production.example)
- **1 bovitett Makefile** (+4 target)
- **1-2 modositott UI oldal** (Emails.tsx pipeline trigger, Dashboard.tsx pipeline status)
- **~5 uj i18n kulcs** (hu + en)
- **~4 uj E2E teszt** (test_docker_deploy.py)
- **1 bovitett README.md** (Docker deploy guide)
- **1 frissitett deploy doc** (62_DEPLOYMENT_ARCHITECTURE.md)
- **3-4 commit**

**Becsult hossz:** 1 teljes session (3-4 ora). Legnagyobb idoigeny:
- Docker files + compose + build: ~1.5 ora
- Pipeline trigger UI + Makefile: ~1 ora
- Deploy teszt + E2E: ~1 ora
- README + plan + commit: ~30 perc

---

## SPRINT B UTEMTERV (S33 utan, frissitett)

```
S19: B0      — DONE (4b09aad)
S20: B1.1    — DONE (f6670a1)
S21: B1.2    — DONE (7cec90b)
S22: B2.1    — DONE (51ce1bf)
S23: B2.2    — DONE (62e829b)
S24: B3.1    — DONE (372e08b)
S25: B3.2    — DONE (aecce10)
S26a: B3.E2E — DONE (0b5e542 + f1f0029)
S27a: B3.E2E — DONE (8b10fd6 + 70f505f)
S27b: B3.5   — DONE (4579cd2)
S28: B4.1    — DONE (9eb2769)
S29: B4.2    — DONE (e4f322e)
S30: B5      — DONE (11364cd + a77a912 + 41d3e60 + c7079c6)
S31: B6      — DONE (8261e88) — Portal audit + 4 journey (design-only)
S32: B7      — DONE (f09f32e + 5464829 + a23db05) — Verification Page v2
S33: B8      — DONE (804baa7 + 86494b1 + 47e69e1 + 05a21e5) — UI Journey implementacio
S34: B9      ← KOVETKEZO SESSION — Docker deploy (THIS PROMPT)
S35: B10     — POST-AUDIT + javitasok
S36: B11     — v1.3.0 tag + merge
```

---

## KESZ JELENTES FORMATUM (B9 vege)

```
# S34 — B9 Docker Containerization DONE

## Kimenet
- .dockerignore: projekt-szintu Docker ignore
- aiflow-admin/Dockerfile: multi-stage (node:22 → nginx:alpine)
- aiflow-admin/nginx.conf: SPA + /api proxy + SSE support
- docker-compose.prod.yml: 6 service (db, redis, kroki, api, worker, ui)
- .env.production.example: production config template
- Makefile: deploy, deploy-status, deploy-down, deploy-logs targetok
- aiflow-admin/src/pages-new/Emails.tsx: "Scan Mailbox" pipeline trigger
- README.md: Docker deploy guide (3 lepes)
- tests/e2e/test_docker_deploy.py: {X} Docker E2E teszt

## Kulcsszamok
- E2E tesztek: 114 → {114+X}
- Unit tesztek: 1443 (valtozatlan)

## Tesztek
- Docker build: PASS (minden image epul)
- Docker stack: PASS (minden container healthy)
- /regression: PASS ({total} teszt, 0 uj fail)
- /lint-check: PASS (ruff + tsc)

## Commit(ok)
{SHA1} feat(sprint-b): B9.1 docker production stack — UI container + nginx + compose
{SHA2} feat(sprint-b): B9.2 UI pipeline trigger — scan mailbox + pipeline status
{SHA3} test(sprint-b): B9.3 docker deploy E2E tests
{SHA4} docs(sprint-b): B9.4 deploy guide + plan update

## Kovetkezo session
S35 = B10 — POST-AUDIT + javitasok
```

---

*Kovetkezo ervenyben: S34 = B9 (Docker deploy) → S35 = B10 (POST-AUDIT) → S36 = B11 (v1.3.0 tag + merge)*
