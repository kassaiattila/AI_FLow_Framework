.PHONY: help setup setup-full dev dev-docker api worker down down-volumes test test-cov test-integration test-e2e test-ui test-prompts test-all lint lint-fix migrate migrate-new db-reset lock clean skill-list workflow-list check-env deploy deploy-status deploy-down deploy-logs install-hooks openapi-snapshot

# Platform-aware venv paths
ifeq ($(OS),Windows_NT)
    VENV_BIN := .venv/Scripts
    PYTHON := .venv/Scripts/python.exe
    ACTIVATE := .venv/Scripts/activate
else
    VENV_BIN := .venv/bin
    PYTHON := .venv/bin/python
    ACTIVATE := .venv/bin/activate
endif

PYTEST := $(VENV_BIN)/pytest
RUFF := $(VENV_BIN)/ruff
MYPY := $(VENV_BIN)/mypy

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# === SETUP ===

setup: ## Create venv + install dev dependencies
	uv venv
	uv pip install -e ".[dev]"
	@if [ ! -f .env ]; then cp .env.example .env 2>/dev/null && echo ".env created from .env.example" || echo "No .env.example found"; fi
	@echo ""
	@echo "Setup DONE. Next: make dev (or 'make install-hooks' for pre-commit hook)"

install-hooks: ## Install git pre-commit hook (vite build on aiflow-admin/ changes)
	@mkdir -p .git/hooks
	@cp scripts/hooks/pre-commit .git/hooks/pre-commit
	@chmod +x .git/hooks/pre-commit
	@echo "[install-hooks] .git/hooks/pre-commit installed (Sprint U S153 SR-FU-5)."
	@echo "Bypass once: git commit --no-verify (use sparingly)."

openapi-snapshot: ## Refresh docs/api/openapi.json from live FastAPI source
	PYTHONPATH=src $(PYTHON) scripts/check_openapi_drift.py --update
	@echo "[openapi-snapshot] docs/api/openapi.json refreshed. Commit if intentional."

setup-full: ## Setup with all optional extras
	uv venv
	uv pip install -e ".[dev,vectorstore,rpa,ui]"
	@if [ ! -f .env ]; then cp .env.example .env 2>/dev/null || true; fi

# === DEVELOPMENT ===

dev: ## Start Docker services + run DB migrations
	docker compose up -d
	@echo "Waiting for PostgreSQL..."
	@sleep 3
	$(PYTHON) -m alembic upgrade head 2>/dev/null || echo "No migrations yet (expected in Phase 1)"
	@echo ""
	@echo "=== AIFlow Dev Environment Started ==="
	@echo "PostgreSQL: localhost:5432"
	@echo "Redis:      localhost:6379"
	@echo "Kroki:      localhost:8080"
	@echo ""
	@echo "Run 'make api' to start the API server"

dev-docker: ## Full environment in Docker (API + Worker in containers)
	docker compose --profile full up -d --build
	@sleep 5
	docker compose exec api alembic upgrade head 2>/dev/null || true

api: ## Run FastAPI locally with hot reload (set AIFLOW_DOCLING_WARMUP=true to pre-load docling)
	@if [ "$$AIFLOW_DOCLING_WARMUP" = "true" ]; then \
		echo "[api] AIFLOW_DOCLING_WARMUP=true — pre-loading docling (~60s cold-start)..."; \
		PYTHONPATH=src $(PYTHON) scripts/warmup_docling.py || echo "[api] docling warmup failed (continuing)"; \
	fi
	$(PYTHON) -m uvicorn aiflow.api.app:create_app --factory --reload --port 8000

worker: ## Run arq worker locally
	$(PYTHON) -m aiflow.execution.worker

down: ## Stop Docker services
	docker compose down

down-volumes: ## Stop Docker + delete all data (CAUTION!)
	docker compose down -v

# === TESTING ===

test: ## Run unit tests
	$(PYTEST) tests/unit/ -v --tb=short

test-cov: ## Run unit tests with coverage report
	$(PYTEST) tests/unit/ -v --cov=aiflow --cov-report=term-missing --cov-report=html

test-integration: ## Run integration tests (Docker services required)
	$(PYTEST) tests/integration/ -v

test-e2e: ## Run end-to-end tests (full system required)
	$(PYTEST) tests/e2e/ -v

test-ui: ## Run Playwright UI tests
	$(PYTEST) tests/ui/ -v

test-prompts: ## Run Promptfoo prompt tests
	npx promptfoo eval -c skills/*/tests/promptfooconfig.yaml

test-all: test test-integration test-prompts ## Run all tests (unit + integration + prompts)

# === CODE QUALITY ===

lint: ## Check code quality (ruff + mypy)
	$(RUFF) check src/aiflow/ tests/
	$(RUFF) format --check src/aiflow/ tests/
	$(MYPY) src/aiflow/

lint-fix: ## Auto-fix lint issues
	$(RUFF) check --fix src/aiflow/ tests/
	$(RUFF) format src/aiflow/ tests/

# === DATABASE ===

migrate: ## Run Alembic migrations (upgrade head)
	$(PYTHON) -m alembic upgrade head

migrate-new: ## Create new migration (usage: make migrate-new NAME=add_xyz)
	$(PYTHON) -m alembic revision --autogenerate -m "$(NAME)"

db-reset: ## Drop + recreate + migrate database (CAUTION!)
	docker compose exec db psql -U aiflow -c "DROP DATABASE IF EXISTS aiflow_dev;"
	docker compose exec db psql -U aiflow -c "CREATE DATABASE aiflow_dev;"
	$(PYTHON) -m alembic upgrade head

# === MAINTENANCE ===

lock: ## Regenerate uv.lock from pyproject.toml
	uv pip compile pyproject.toml -o uv.lock

clean: ## Remove temporary files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage coverage.xml
	rm -rf tests/artifacts/

check-env: ## Verify development environment
	@bash scripts/check_environment.sh

# === AIFLOW CLI ===

skill-list: ## List installed skills
	$(PYTHON) -m aiflow.cli.main skill list

workflow-list: ## List registered workflows
	$(PYTHON) -m aiflow.cli.main workflow list

# === PRODUCTION DEPLOY ===

deploy: ## Build + start production stack
	docker compose -f docker-compose.prod.yml up -d --build
	@echo "Waiting for services to start..."
	@sleep 10
	docker compose -f docker-compose.prod.yml exec api alembic upgrade head
	@echo ""
	@echo "=== AIFlow Production Stack Running ==="
	@echo "UI:     http://localhost:$${UI_PORT:-80}"
	@echo "Health: http://localhost:$${UI_PORT:-80}/health"
	@echo ""

deploy-status: ## Check production stack health
	docker compose -f docker-compose.prod.yml ps
	@echo ""
	@echo "--- Health Checks ---"
	@curl -sf http://localhost:$${UI_PORT:-80}/health-ui && echo " (UI OK)" || echo "UI: unreachable"
	@curl -sf http://localhost:$${UI_PORT:-80}/health | python -m json.tool 2>/dev/null || echo "API: checking..."

deploy-down: ## Stop production stack
	docker compose -f docker-compose.prod.yml down

deploy-logs: ## Show production logs
	docker compose -f docker-compose.prod.yml logs -f --tail=100
