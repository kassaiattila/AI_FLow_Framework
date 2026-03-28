# AIFlow - Fejlesztoi Kornyezet Specifikacio

**Alapelv:** Minden szolgaltatas Docker-ben fut. A fejleszto gepere CSAK Python + uv + Git kell.
A teljes kornyezet egyetlen `make dev` paranccsal elindul.

---

## 1. Architektura Dontes

```
Fejleszto gepe                          Docker (docker compose)
+---------------------------+           +----------------------------------+
| Python 3.12 (rendszer)    |           | postgres (pgvector:pg16)  :5432  |
| uv (package manager)      |           | redis (7-alpine)          :6379  |
| .venv/ (virtualis korny.) |           | kroki (yuzutech/kroki)    :8080  |
| IDE (VS Code / JetBrains) |           | pgadmin (optional)        :5050  |
+---------------------------+           | grafana (optional)        :3000  |
         |                              +----------------------------------+
         |  uvicorn --reload                        |
         +---> FastAPI API (localhost:8000)          |
         |  arq worker                              |
         +---> Worker (localhost)                    |
         |                                          |
         +--- asyncpg -----> postgres:5432 ---------+
         +--- redis -------> redis:6379 ------------+
```

**Miert ez a modell?**
- **Szolgaltatasok (DB, cache, tools):** MINDIG Docker-ben -> nincs "de az en gepemen mukodott"
- **Python kod (API, worker):** Lokalisan fut .venv-bol -> IDE autocomplete, debugger, hot reload
- **Alternativa (full Docker dev):** Elerheto `make dev-docker`-rel, de nem az alapertelmezett
  (IDE integracio nehezebb container-bol)

---

## 2. Kotelező Eszkozok a Fejlesztoi Gepen

| Eszkoz | Minimum verzio | Telepites | Ellenorzes |
|--------|---------------|-----------|------------|
| **Python** | 3.12+ | python.org / pyenv / winget | `python --version` |
| **uv** | 0.5+ | `pip install uv` vagy `curl -LsSf https://astral.sh/uv/install.sh \| sh` | `uv --version` |
| **Git** | 2.40+ | git-scm.com | `git --version` |
| **Docker** | 24+ | Docker Desktop (Win/Mac) vagy docker.io (Linux) | `docker --version` |
| **Docker Compose** | v2.20+ | Docker Desktop-tal jon | `docker compose version` |
| **Node.js** | 20+ LTS | nodejs.org (Promptfoo-hoz) | `node --version` |
| **Make** | any | Windows: `winget install GnuWin32.Make` vagy Git Bash | `make --version` |

**Opcionalis:**
- VS Code + ajanlott extension-ok (lasd 26_CLAUDE_CODE_SETUP.md)
- Playwright (`npx playwright install chromium`) - GUI tesztekhez / RPA-hoz

---

## 3. Elso Inditas (Onboarding) - Clone-tol Mukodo Kornyezetig

```bash
# 1. Repo klonozas
git clone https://github.com/kassaiattila/AI_FLow_Framework.git
cd AI_FLow_Framework

# 2. Python virtualis kornyezet + fuggosegek
uv venv                              # Letrehozza .venv/-t
uv pip install -e ".[dev]"           # Minden dev fuggoseg telepitese

# 3. Konfiguracio
cp .env.example .env                 # Titkok kitoltese (API kulcsok)

# 4. Docker szolgaltatasok inditasa + DB migracio + health check
make dev                             # Egyetlen parancs!

# 5. Ellenorzes
pytest tests/unit/ -v                # Unit tesztek
curl http://localhost:8000/health    # API elerheto
```

**Ido:** ~5 perc (fuggoseg letoltes + Docker image pull)

---

## 4. uv Mint Hivatalos Python Package Manager

### Miert uv?

| Szempont | pip | poetry | uv |
|----------|-----|--------|----|
| Sebesseg | Lassu | Kozepes | **10-100x gyorsabb** |
| Lockfile | Nincs | poetry.lock | **uv.lock** |
| PEP 621 kompatibilis | Igen | Nem (sajat format) | **Igen** |
| Virtualis kornyezet | Kulon (venv) | Beepitett | **Beepitett** |
| Reprodukalhato build | Nem | Igen | **Igen** |
| Docker optimalizalt | Nem | Nem | **Igen (--system)** |

### Napi Hasznalat

```bash
# Virtualis kornyezet letrehozasa
uv venv                               # -> .venv/ (automatikusan Python 3.12+)

# Fuggosegek telepitese
uv pip install -e ".[dev]"            # Dev fuggosegek
uv pip install -e ".[dev,vectorstore,rpa]"  # Minden extra

# Uj fuggoseg hozzaadasa
# 1. pyproject.toml-ban hozzaadni
# 2. uv pip install -e ".[dev]"
# 3. uv pip compile pyproject.toml -o uv.lock  # Lockfile frissites

# Lockfile-bol telepites (reprodukalhato)
uv pip sync uv.lock                    # Pontosan ugyanazok a verziok

# Kornyezet ujraepitese
uv venv --force                        # Torol + ujrahoz
uv pip install -e ".[dev]"
```

### uv.lock Kezeles

```
uv.lock = EGYETLEN IGAZSAG FORRAS a fuggoseg verziokhoz.

pyproject.toml    -> MIT akarunk (pl. "fastapi>=0.115")
uv.lock           -> PONTOSAN MIT kapunk (pl. "fastapi==0.115.6")

Szabalyok:
- uv.lock MINDIG COMMITOLVA (Git-ben)
- CI uv.lock-bol telepit (reprodukalhato)
- Docker uv.lock-bol telepit (reprodukalhato)
- Ha pyproject.toml valtozik -> `uv pip compile` -> uv.lock frissul -> commit
```

---

## 5. Makefile (Teljes Tartalom)

```makefile
.PHONY: help setup dev dev-docker down test lint migrate seed clean

# Platformfuggetlen Python path
VENV_BIN := $(if $(filter Windows_NT,$(OS)),.venv/Scripts,.venv/bin)
PYTHON := $(VENV_BIN)/python
PYTEST := $(VENV_BIN)/pytest

help: ## Elerheto parancsok listazasa
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# === SETUP ===

setup: ## Virtualis kornyezet + fuggosegek telepitese
	uv venv
	uv pip install -e ".[dev]"
	cp -n .env.example .env 2>/dev/null || true
	@echo "Setup KESZ. Kovetkezo: make dev"

setup-full: ## Setup + vectorstore + rpa extrakkal
	uv venv
	uv pip install -e ".[dev,vectorstore,rpa,ui]"
	cp -n .env.example .env 2>/dev/null || true

# === DEVELOPMENT ===

dev: ## Docker szolgaltatasok + DB migracio + health check
	docker compose up -d
	@echo "Varakozas a PostgreSQL-re..."
	@sleep 3
	$(PYTHON) -m alembic upgrade head
	@echo ""
	@echo "=== AIFlow Dev Kornyezet Elindult ==="
	@echo "API:      http://localhost:8000"
	@echo "pgAdmin:  http://localhost:5050 (docker compose --profile tools up)"
	@echo "Kroki:    http://localhost:8080"

dev-docker: ## Teljes kornyezet Docker-ben (API + Worker is)
	docker compose --profile full up -d --build
	@sleep 5
	docker compose exec api alembic upgrade head

api: ## FastAPI inditasa lokálisan (hot reload)
	$(PYTHON) -m uvicorn aiflow.api.app:create_app --factory --reload --port 8000

worker: ## arq Worker inditasa lokálisan
	$(PYTHON) -m aiflow.execution.worker

down: ## Docker szolgaltatasok leallitasa
	docker compose down

down-volumes: ## Docker leallitas + adatok torlese (VIGYAZAT!)
	docker compose down -v

# === TESTING ===

test: ## Osszes unit teszt futtatasa
	$(PYTEST) tests/unit/ -v --tb=short

test-cov: ## Unit tesztek + coverage riport
	$(PYTEST) tests/unit/ -v --cov=aiflow --cov-report=term-missing --cov-report=html

test-integration: ## Integracios tesztek (Docker kell)
	$(PYTEST) tests/integration/ -v

test-e2e: ## E2E tesztek (teljes rendszer kell)
	$(PYTEST) tests/e2e/ -v

test-ui: ## Playwright GUI tesztek
	$(PYTEST) tests/ui/ -v

test-prompts: ## Promptfoo tesztek
	npx promptfoo eval -c skills/*/tests/promptfooconfig.yaml

test-all: test test-integration test-prompts ## Minden teszt (unit + integration + prompt)

# === CODE QUALITY ===

lint: ## Lint + format ellenorzes
	$(VENV_BIN)/ruff check src/aiflow/ tests/ skills/
	$(VENV_BIN)/ruff format --check src/aiflow/ tests/ skills/
	$(VENV_BIN)/mypy src/aiflow/

lint-fix: ## Lint + format automatikus javitas
	$(VENV_BIN)/ruff check --fix src/aiflow/ tests/ skills/
	$(VENV_BIN)/ruff format src/aiflow/ tests/ skills/

# === DATABASE ===

migrate: ## Alembic migracio futtatasa (upgrade head)
	$(PYTHON) -m alembic upgrade head

migrate-new: ## Uj migracio generalas (NAME=migration_name)
	$(PYTHON) -m alembic revision --autogenerate -m "$(NAME)"

db-reset: ## DB torles + ujrainicializalas (VIGYAZAT!)
	docker compose exec db psql -U aiflow -c "DROP DATABASE IF EXISTS aiflow_dev;"
	docker compose exec db psql -U aiflow -c "CREATE DATABASE aiflow_dev;"
	$(PYTHON) -m alembic upgrade head

# === MAINTENANCE ===

lock: ## uv.lock frissitese pyproject.toml alapjan
	uv pip compile pyproject.toml -o uv.lock

clean: ## Ideiglenes fajlok torlese
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage coverage.xml
	rm -rf tests/artifacts/

# === AIFLOW CLI ===

skill-list: ## Telepitett skill-ek listazasa
	$(PYTHON) -m aiflow.cli.main skill list

workflow-list: ## Regisztralt workflow-k listazasa
	$(PYTHON) -m aiflow.cli.main workflow list
```

---

## 6. Docker Compose (Dev) Kiegeszites

### docker-compose.yml (Vegleges Terv)

```yaml
services:
  # === CORE SERVICES (mindig futnak) ===
  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: aiflow_dev
      POSTGRES_USER: aiflow
      POSTGRES_PASSWORD: aiflow_dev_password
    ports:
      - "5432:5432"
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
      --maxmemory 256mb
      --maxmemory-policy volatile-lru
      --appendonly yes
    ports:
      - "6379:6379"
    volumes:
      - redisdata:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  kroki:
    image: yuzutech/kroki
    ports:
      - "8080:8000"

  # === FULL PROFILE (docker compose --profile full up) ===
  api:
    build:
      context: .
      target: api
    profiles: ["full"]
    environment:
      AIFLOW_DATABASE__URL: postgresql+asyncpg://aiflow:aiflow_dev_password@db:5432/aiflow_dev
      AIFLOW_REDIS__URL: redis://redis:6379/0
      AIFLOW_ENVIRONMENT: dev
    ports:
      - "8000:8000"
    depends_on:
      db: { condition: service_healthy }
      redis: { condition: service_healthy }

  worker:
    build:
      context: .
      target: worker
    profiles: ["full"]
    environment:
      AIFLOW_DATABASE__URL: postgresql+asyncpg://aiflow:aiflow_dev_password@db:5432/aiflow_dev
      AIFLOW_REDIS__URL: redis://redis:6379/0
      AIFLOW_ENVIRONMENT: dev
    depends_on:
      db: { condition: service_healthy }
      redis: { condition: service_healthy }

  # === TOOLS PROFILE (docker compose --profile tools up) ===
  pgadmin:
    image: dpage/pgadmin4:latest
    profiles: ["tools"]
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@aiflow.local
      PGADMIN_DEFAULT_PASSWORD: admin
    ports:
      - "5050:80"

  grafana:
    image: grafana/grafana:latest
    profiles: ["tools"]
    ports:
      - "3000:3000"
    volumes:
      - grafanadata:/var/lib/grafana

volumes:
  pgdata:
  redisdata:
  grafanadata:
```

### Hasznalati Modok

```bash
# Alap fejlesztes (szolgaltatasok Docker-ben, kod lokalisan)
make dev                                    # db + redis + kroki
make api                                    # FastAPI lokalisan (hot reload)
make worker                                 # Worker lokalisan

# Teljes Docker (minden container-ben)
make dev-docker                             # db + redis + kroki + api + worker

# Kiegeszito eszkozok
docker compose --profile tools up -d        # + pgAdmin + Grafana
```

---

## 7. CI Reprodukalhatosag (uv.lock)

```yaml
# .github/workflows/ci-framework.yml (reszlet)
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4         # uv telepites
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: uv venv
      - run: uv pip sync uv.lock            # LOCKFILE-bol (reprodukalhato!)
      - run: uv pip install -e ".[dev]" --no-deps  # Csak a projekt maga
      - run: pytest tests/unit/ -v --cov=aiflow
```

**Fontos:** CI-ban `uv pip sync uv.lock` (lockfile-bol) es NEM `uv pip install` (resolver).
Igy a CI PONTOSAN ugyanazt a kornyezetet kapja mint a fejleszto es a Docker.

---

## 8. Dockerfile (uv-alapu, Multi-Stage)

```dockerfile
# === BUILD STAGE ===
FROM python:3.12-slim AS builder
RUN pip install uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv pip install --system --no-cache -r uv.lock

# === API ===
FROM python:3.12-slim AS api
RUN useradd -m -s /bin/bash aiflow
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
WORKDIR /app
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini .
USER aiflow
EXPOSE 8000
CMD ["uvicorn", "aiflow.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]

# === WORKER ===
FROM api AS worker
CMD ["python", "-m", "aiflow.execution.worker"]

# === RPA WORKER (Playwright + ffmpeg) ===
FROM mcr.microsoft.com/playwright/python:v1.40.0 AS rpa-worker
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
WORKDIR /app
COPY src/ ./src/
RUN playwright install chromium
CMD ["python", "-m", "aiflow.execution.worker"]
```

---

## 9. Windows-Specifikus Megjegyzesek

A fo fejleszto Windows 11-en dolgozik. Kulonbsegek:

| Tema | Unix | Windows |
|------|------|---------|
| venv Python path | `.venv/bin/python` | `.venv/Scripts/python.exe` |
| Makefile | Nativ | `winget install GnuWin32.Make` vagy Git Bash `make` |
| Docker | docker.io | Docker Desktop |
| Shell | bash/zsh | Git Bash / PowerShell |
| Line endings | LF | CRLF (git config `core.autocrlf=true`) |

**Megoldas:** A Makefile platformfuggetlen VENV_BIN valtozot hasznal:
```makefile
VENV_BIN := $(if $(filter Windows_NT,$(OS)),.venv/Scripts,.venv/bin)
```

**.vscode/settings.json** cross-platform:
```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/Scripts/python.exe"
}
```
(VS Code automatikusan felismeri a .venv-et mindket platformon)

---

## 10. Kornyezet Ellenorzo Script

```bash
#!/bin/bash
# scripts/check_environment.sh
# Fejlesztoi kornyezet ellenorzes

echo "=== AIFlow Development Environment Check ==="
echo ""

errors=0

check() {
    if command -v "$1" &> /dev/null; then
        echo "  [OK] $1: $(eval "$2")"
    else
        echo "  [HIBA] $1: NEM TALALHATO"
        errors=$((errors + 1))
    fi
}

check "python" "python --version 2>&1"
check "uv" "uv --version 2>&1"
check "git" "git --version 2>&1"
check "docker" "docker --version 2>&1"
check "docker" "docker compose version 2>&1"
check "node" "node --version 2>&1"
check "make" "make --version 2>&1 | head -1"

echo ""
if [ -d ".venv" ]; then
    echo "  [OK] .venv/ letezik"
else
    echo "  [HIBA] .venv/ nem letezik (futtasd: make setup)"
    errors=$((errors + 1))
fi

if [ -f ".env" ]; then
    echo "  [OK] .env letezik"
else
    echo "  [HIBA] .env nem letezik (futtasd: cp .env.example .env)"
    errors=$((errors + 1))
fi

if docker compose ps --status running 2>/dev/null | grep -q "db"; then
    echo "  [OK] PostgreSQL fut"
else
    echo "  [INFO] PostgreSQL nem fut (futtasd: make dev)"
fi

if docker compose ps --status running 2>/dev/null | grep -q "redis"; then
    echo "  [OK] Redis fut"
else
    echo "  [INFO] Redis nem fut (futtasd: make dev)"
fi

echo ""
if [ $errors -eq 0 ]; then
    echo "=== MINDEN RENDBEN - fejlesztes megkezdheto ==="
else
    echo "=== $errors HIBA TALALHATO - javitsd elobb! ==="
    exit 1
fi
```
