# AIFlow

Enterprise AI Automation Framework for building, deploying, and operating
AI-powered automation workflows at scale.

## Quick Start

```bash
# Setup
make setup    # Create venv + install deps
make dev      # Start Docker services (PostgreSQL, Redis, Kroki)

# Development
make api      # Run API with hot reload
make test     # Run unit tests
make lint     # Check code quality
```

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
# UI:     http://localhost       (nginx → React SPA)
# Health: http://localhost/health (API health via nginx proxy)
```

**Stack:** PostgreSQL + Redis + Kroki + FastAPI + Worker + nginx (React SPA)

```bash
make deploy-status  # Check service health
make deploy-logs    # Tail logs
make deploy-down    # Stop everything
```

## Documentation

See `01_PLAN/` for complete project documentation (34 documents).
Start with `01_PLAN/AIFLOW_MASTER_PLAN.md`.
