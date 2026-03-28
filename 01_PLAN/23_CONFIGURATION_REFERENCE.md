# AIFlow -- Configuration Reference

> Minden konfiguracios ertek harom szinten toltodik be (priority order):
> **environment variable > aiflow.yaml > hardcoded default**.

---

## 1. `aiflow.yaml` -- Full Schema

```yaml
# ── Application ────────────────────────────────────────────
app:
  name: "aiflow"                       # Alkalmazas neve (megjelenik logokban, tracing span-ekben)
  version: "0.1.0"                     # SemVer -- a /health endpoint is visszaadja
  environment: "dev"                   # dev | test | staging | prod
  debug: true                          # true eseten reszletes stack-trace + SQL echo

# ── Database (PostgreSQL + asyncpg) ───────────────────────
database:
  url: "postgresql+asyncpg://aiflow:secret@localhost:5432/aiflow"
  pool_size: 20                        # Alap connection-pool meret
  pool_overflow: 10                    # Extra connection-ok max szama csucs-terheles eseten
  echo: false                          # SQL statement logging (debug-hoz hasznos)
  # **Production:** PgBouncer ajanlott K8s-ben (replika_szam * pool_size meghaladhatja PostgreSQL max_connections-t)

# ── Redis ──────────────────────────────────────────────────
redis:
  url: "redis://localhost:6379/0"
  prefix: "aiflow:"                    # Minden Redis key elott -- elkeruli a collision-t
  max_connections: 50

# ── API Server ─────────────────────────────────────────────
api:
  host: "0.0.0.0"
  port: 8000
  cors_origins: ["http://localhost:3000"]
  docs_enabled: true                   # Swagger UI + ReDoc (prod-ban false)

# ── LLM Defaults ──────────────────────────────────────────
llm:
  default_model: "gpt-4o"
  fallback_model: "gpt-4o-mini"
  timeout: 120                         # Masodpercben -- per-request timeout
  max_retries: 3                       # Exponential backoff-fal

# ── Langfuse Observability ─────────────────────────────────
langfuse:
  public_key: ""
  secret_key: ""
  host: "https://cloud.langfuse.com"
  enabled: true
  cache_ttl: 300                       # Prompt-cache TTL masodpercben

# ── Background Queue (ARQ) ────────────────────────────────
queue:
  worker_count: 4
  max_jobs: 1000
  job_timeout: 600                     # 10 perc -- egyetlen job max futasideje
  dlq_max_retries: 5                   # Dead-letter queue-ba kuldedes elotti retry

# ── Security ───────────────────────────────────────────────
security:
  jwt_private_key_path: "/etc/aiflow/keys/jwt-private.pem"
  jwt_public_key_path: "/etc/aiflow/keys/jwt-public.pem"
  jwt_access_token_ttl: 900            # 15 perc masodpercben
  jwt_refresh_token_ttl: 604800        # 7 nap masodpercben
  api_key_prefix: "aiflow_"           # API kulcsok prefixe (azonositas)
  password_min_length: 12

# ── Observability / Logging ────────────────────────────────
observability:
  log_level: "INFO"                    # DEBUG | INFO | WARNING | ERROR | CRITICAL
  log_format: "json"                   # json | console (dev-hez a console olvashatobb)
  otel_endpoint: "http://localhost:4317"
  prometheus_enabled: true

# ── Vector Store ───────────────────────────────────────────
vectorstore:
  default_embedding_model: "text-embedding-3-small"
  default_chunk_size: 512
  default_overlap: 64

# ── Messaging / Event Bus ─────────────────────────────────
messaging:
  broker: "redis_streams"              # redis_streams | kafka | rabbitmq
  redis_streams:
    stream_prefix: "aiflow:stream:"
    consumer_group: "aiflow-workers"
    block_ms: 5000
  kafka:
    bootstrap_servers: "localhost:9092"
    group_id: "aiflow"
    auto_offset_reset: "earliest"
  rabbitmq:
    url: "amqp://guest:guest@localhost:5672/"
    exchange: "aiflow.events"
    prefetch_count: 10

# ── Model Routing ──────────────────────────────────────────
models:
  routing_strategy: "cost_optimized"   # cost_optimized | latency_first | quality_first
  fallback_chains:
    default: ["gpt-4o", "gpt-4o-mini", "anthropic/claude-sonnet-4-20250514"]
    embedding: ["text-embedding-3-small", "text-embedding-ada-002"]

# ── Budget / Cost Guard ───────────────────────────────────
budget:
  default_per_run: 0.50                # USD -- egyetlen flow-futtas koltseg-limitje
  alert_threshold_pct: 80             # Figyelmeztetes a limit 80%-anal
```

---

## 2. Environment Variables Reference

Minden valtozo `AIFLOW_` prefix-szel kerul felolvasasra.
A Pydantic Settings automatikusan mapeli: `AIFLOW_DATABASE__URL` -> `database.url`.

| Variable | Type | Default | Req? | Leiras |
|---|---|---|---|---|
| **App** | | | | |
| `AIFLOW_APP__NAME` | str | `aiflow` | - | Alkalmazas neve |
| `AIFLOW_APP__VERSION` | str | `0.1.0` | - | Verzio |
| `AIFLOW_APP__ENVIRONMENT` | str | `dev` | - | dev/test/staging/prod |
| `AIFLOW_APP__DEBUG` | bool | `true` | - | Debug mod |
| **Database** | | | | |
| `AIFLOW_DATABASE__URL` | str | - | YES | PostgreSQL connection string |
| `AIFLOW_DATABASE__POOL_SIZE` | int | `20` | - | Pool meret |
| `AIFLOW_DATABASE__POOL_OVERFLOW` | int | `10` | - | Max extra conn |
| **Redis** | | | | |
| `AIFLOW_REDIS__URL` | str | - | YES | Redis URI |
| `AIFLOW_REDIS__PREFIX` | str | `aiflow:` | - | Key prefix |
| `AIFLOW_REDIS__MAX_CONNECTIONS` | int | `50` | - | Max conn |
| **API** | | | | |
| `AIFLOW_API__HOST` | str | `0.0.0.0` | - | Bind address |
| `AIFLOW_API__PORT` | int | `8000` | - | Listen port |
| `AIFLOW_API__CORS_ORIGINS` | json | `["http://localhost:3000"]` | - | CORS whitelist |
| `AIFLOW_API__DOCS_ENABLED` | bool | `true` | - | Swagger UI |
| **LLM** | | | | |
| `AIFLOW_LLM__DEFAULT_MODEL` | str | `gpt-4o` | - | Alap LLM |
| `AIFLOW_LLM__FALLBACK_MODEL` | str | `gpt-4o-mini` | - | Fallback LLM |
| `AIFLOW_LLM__TIMEOUT` | int | `120` | - | Request timeout (sec) |
| `AIFLOW_LLM__MAX_RETRIES` | int | `3` | - | Retry count |
| **Langfuse** | | | | |
| `AIFLOW_LANGFUSE__PUBLIC_KEY` | str | - | YES* | *Ha enabled=true |
| `AIFLOW_LANGFUSE__SECRET_KEY` | str | - | YES* | *Ha enabled=true |
| `AIFLOW_LANGFUSE__HOST` | str | `https://cloud.langfuse.com` | - | Langfuse host |
| `AIFLOW_LANGFUSE__ENABLED` | bool | `true` | - | Tracing on/off |
| **Security** | | | | |
| `AIFLOW_SECURITY__JWT_PRIVATE_KEY_PATH` | str | - | YES | RS256 private key PEM path |
| `AIFLOW_SECURITY__JWT_PUBLIC_KEY_PATH` | str | - | YES | RS256 public key PEM path |
| `AIFLOW_SECURITY__JWT_ACCESS_TOKEN_TTL` | int | `900` | - | Access token TTL (sec, 15 min) |
| `AIFLOW_SECURITY__JWT_REFRESH_TOKEN_TTL` | int | `604800` | - | Refresh token TTL (sec, 7 days) |
| **Observability** | | | | |
| `AIFLOW_OBSERVABILITY__LOG_LEVEL` | str | `INFO` | - | Log szint |
| `AIFLOW_OBSERVABILITY__LOG_FORMAT` | str | `json` | - | json / console |
| `AIFLOW_OBSERVABILITY__OTEL_ENDPOINT` | str | `http://localhost:4317` | - | OTLP gRPC |
| `AIFLOW_OBSERVABILITY__PROMETHEUS_ENABLED` | bool | `true` | - | Metrics export |
| **Budget** | | | | |
| `AIFLOW_BUDGET__DEFAULT_PER_RUN` | float | `0.50` | - | USD/run limit |
| `AIFLOW_BUDGET__ALERT_THRESHOLD_PCT` | int | `80` | - | Alert kuszob % |

---

## 3. `.env.example`

```bash
# ── AIFlow .env ── Copy to .env and fill in values ──

# App
AIFLOW_APP__ENVIRONMENT=dev
AIFLOW_APP__DEBUG=true

# Database (REQUIRED)
AIFLOW_DATABASE__URL=postgresql+asyncpg://aiflow:secret@localhost:5432/aiflow
AIFLOW_DATABASE__POOL_SIZE=20

# Redis (REQUIRED)
AIFLOW_REDIS__URL=redis://localhost:6379/0

# API
AIFLOW_API__PORT=8000
AIFLOW_API__CORS_ORIGINS=["http://localhost:3000"]

# LLM
AIFLOW_LLM__DEFAULT_MODEL=gpt-4o
AIFLOW_LLM__TIMEOUT=120

# Langfuse (REQUIRED if enabled)
AIFLOW_LANGFUSE__PUBLIC_KEY=pk-lf-...
AIFLOW_LANGFUSE__SECRET_KEY=sk-lf-...
AIFLOW_LANGFUSE__ENABLED=true

# Security (REQUIRED)
AIFLOW_SECURITY__JWT_PRIVATE_KEY_PATH=/etc/aiflow/keys/jwt-private.pem
AIFLOW_SECURITY__JWT_PUBLIC_KEY_PATH=/etc/aiflow/keys/jwt-public.pem

# Observability
AIFLOW_OBSERVABILITY__LOG_LEVEL=INFO
AIFLOW_OBSERVABILITY__LOG_FORMAT=json
AIFLOW_OBSERVABILITY__OTEL_ENDPOINT=http://localhost:4317

# Budget
AIFLOW_BUDGET__DEFAULT_PER_RUN=0.50
```

---

## 4. Docker Compose Variables Mapping

```yaml
# docker-compose.yml -- env_file + valtozok osszekotese
services:
  api:
    env_file: .env
    environment:
      AIFLOW_DATABASE__URL: "postgresql+asyncpg://aiflow:${POSTGRES_PASSWORD}@db:5432/aiflow"
      AIFLOW_REDIS__URL: "redis://redis:6379/0"
      AIFLOW_OBSERVABILITY__OTEL_ENDPOINT: "http://otel-collector:4317"

  worker:
    env_file: .env
    environment:
      AIFLOW_DATABASE__URL: "postgresql+asyncpg://aiflow:${POSTGRES_PASSWORD}@db:5432/aiflow"
      AIFLOW_REDIS__URL: "redis://redis:6379/0"
      AIFLOW_API__DOCS_ENABLED: "false"   # worker-nek nem kell Swagger

  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: aiflow
      POSTGRES_PASSWORD: "${POSTGRES_PASSWORD}"
      POSTGRES_DB: aiflow

  redis:
    image: redis:7-alpine
    command: redis-server --maxmemory 256mb --maxmemory-policy volatile-lru
    # volatile-lru: only evicts keys with TTL, protects queue data
```

---

## 5. K8s ConfigMap (nem-szenzitiv config)

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: aiflow-config
  namespace: aiflow
data:
  AIFLOW_APP__ENVIRONMENT: "prod"
  AIFLOW_APP__DEBUG: "false"
  AIFLOW_API__PORT: "8000"
  AIFLOW_API__CORS_ORIGINS: '["https://app.example.com"]'
  AIFLOW_API__DOCS_ENABLED: "false"
  AIFLOW_LLM__DEFAULT_MODEL: "gpt-4o"
  AIFLOW_LLM__TIMEOUT: "120"
  AIFLOW_DATABASE__POOL_SIZE: "30"
  AIFLOW_OBSERVABILITY__LOG_LEVEL: "WARNING"
  AIFLOW_OBSERVABILITY__LOG_FORMAT: "json"
  AIFLOW_OBSERVABILITY__OTEL_ENDPOINT: "http://otel-collector.monitoring:4317"
  AIFLOW_OBSERVABILITY__PROMETHEUS_ENABLED: "true"
  AIFLOW_BUDGET__DEFAULT_PER_RUN: "0.50"
  AIFLOW_LANGFUSE__HOST: "https://langfuse.internal.example.com"
  AIFLOW_LANGFUSE__ENABLED: "true"
```

---

## 6. K8s Secret + Vault Integration

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: aiflow-secrets
  namespace: aiflow
  annotations:
    # Vault Agent Injector -- automatikus sync Vault-bol
    vault.hashicorp.com/agent-inject: "true"
    vault.hashicorp.com/role: "aiflow-prod"
    vault.hashicorp.com/agent-inject-secret-db: "secret/data/aiflow/database"
type: Opaque
stringData:
  AIFLOW_DATABASE__URL: "postgresql+asyncpg://aiflow:VAULT_INJECTED@db:5432/aiflow"
  AIFLOW_REDIS__URL: "redis://:VAULT_INJECTED@redis:6379/0"
  AIFLOW_SECURITY__JWT_PRIVATE_KEY_PATH: "/etc/aiflow/keys/jwt-private.pem"
  AIFLOW_SECURITY__JWT_PUBLIC_KEY_PATH: "/etc/aiflow/keys/jwt-public.pem"
  AIFLOW_LANGFUSE__PUBLIC_KEY: "pk-lf-..."
  AIFLOW_LANGFUSE__SECRET_KEY: "sk-lf-..."
```

Deployment referencialas:

```yaml
# deployment.yml -- reszlet
spec:
  containers:
    - name: aiflow-api
      envFrom:
        - configMapRef:
            name: aiflow-config
        - secretRef:
            name: aiflow-secrets
```

---

## 7. Pydantic Settings Class

```python
"""aiflow/core/config.py -- Konfiguracio betoltesi sorrend: env > yaml > default."""

from __future__ import annotations
from pathlib import Path
from functools import lru_cache
from typing import Literal

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseModel):
    name: str = "aiflow"
    version: str = "0.1.0"
    environment: Literal["dev", "test", "staging", "prod"] = "dev"
    debug: bool = True


class DatabaseConfig(BaseModel):
    url: str = "postgresql+asyncpg://aiflow:secret@localhost:5432/aiflow"
    pool_size: int = 20
    pool_overflow: int = 10
    echo: bool = False


class RedisConfig(BaseModel):
    url: str = "redis://localhost:6379/0"
    prefix: str = "aiflow:"
    max_connections: int = 50


class ApiConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = ["http://localhost:3000"]
    docs_enabled: bool = True


class LlmConfig(BaseModel):
    default_model: str = "gpt-4o"
    fallback_model: str = "gpt-4o-mini"
    timeout: int = 120
    max_retries: int = 3


class LangfuseConfig(BaseModel):
    public_key: str = ""
    secret_key: str = ""
    host: str = "https://cloud.langfuse.com"
    enabled: bool = True
    cache_ttl: int = 300


class SecurityConfig(BaseModel):
    jwt_private_key_path: str = "/etc/aiflow/keys/jwt-private.pem"
    jwt_public_key_path: str = "/etc/aiflow/keys/jwt-public.pem"
    jwt_access_token_ttl: int = 900
    jwt_refresh_token_ttl: int = 604800
    api_key_prefix: str = "aiflow_"
    password_min_length: int = 12


class ObservabilityConfig(BaseModel):
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: Literal["json", "console"] = "json"
    otel_endpoint: str = "http://localhost:4317"
    prometheus_enabled: bool = True


class BudgetConfig(BaseModel):
    default_per_run: float = 0.50
    alert_threshold_pct: int = 80


class AIFlowSettings(BaseSettings):
    """Harom retegu config: env var > aiflow.yaml > default ertek."""

    model_config = SettingsConfigDict(
        env_prefix="AIFLOW_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    app: AppConfig = AppConfig()
    database: DatabaseConfig = DatabaseConfig()
    redis: RedisConfig = RedisConfig()
    api: ApiConfig = ApiConfig()
    llm: LlmConfig = LlmConfig()
    langfuse: LangfuseConfig = LangfuseConfig()
    security: SecurityConfig = SecurityConfig()
    observability: ObservabilityConfig = ObservabilityConfig()
    budget: BudgetConfig = BudgetConfig()

    @classmethod
    def _load_yaml(cls, path: Path) -> dict:
        if path.exists():
            return yaml.safe_load(path.read_text()) or {}
        return {}

    @classmethod
    def from_yaml_and_env(cls, path: Path | None = None) -> "AIFlowSettings":
        """YAML-bol betolti az alapot, majd az env var-ok felulirjak."""
        yaml_path = path or Path("aiflow.yaml")
        yaml_data = cls._load_yaml(yaml_path)
        return cls(**yaml_data)


@lru_cache
def get_settings() -> AIFlowSettings:
    """Singleton -- az egesz app-ban ugyanazt a peldanyt kapjuk."""
    return AIFlowSettings.from_yaml_and_env()
```

---

## 8. Per-Skill Configuration (`skill.yaml`)

Minden skill a sajat konyvtaraban felulirhatja a framework default-okat.

```yaml
# skills/summarizer/skill.yaml
skill:
  name: "summarizer"
  version: "1.0.0"

# Framework-default feluliras erre a skill-re
overrides:
  llm:
    default_model: "gpt-4o-mini"        # Olcsobb model eleg a summary-hoz
    timeout: 60
  budget:
    default_per_run: 0.10                # Szigorubb limit

# Skill-specifikus parameterek
params:
  max_input_tokens: 8000
  output_style: "bullet_points"          # bullet_points | paragraph | structured
  language: "hu"
```

Betoltes a framework-ben:

```python
# aiflow/skills/loader.py
from pathlib import Path
from aiflow.core.config import get_settings

def load_skill_config(skill_dir: Path) -> dict:
    """Skill-config merge: framework defaults + skill overrides."""
    base = get_settings().model_dump()
    skill_yaml = yaml.safe_load((skill_dir / "skill.yaml").read_text())

    # Az overrides szekcion beluli ertekek felulirjak a base-t
    for section, values in skill_yaml.get("overrides", {}).items():
        if section in base:
            base[section].update(values)

    base["_skill_params"] = skill_yaml.get("params", {})
    return base
```

---

## 9. Logging Configuration

```python
"""aiflow/core/logging.py -- structlog setup."""

import logging
import structlog


def setup_logging(log_level: str = "INFO", log_format: str = "json") -> None:
    """Strukturalt logging konfiguracio -- JSON prod-hoz, console dev-hez."""

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if log_format == "json":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[*shared_processors, renderer],
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(getattr(logging, log_level))

    # Per-module log level override -- zajos library-k csondben maradnak
    for module, level in {
        "httpcore": "WARNING",
        "httpx": "WARNING",
        "sqlalchemy.engine": "WARNING",
        "uvicorn.access": "INFO",
        "aiflow.skills": "DEBUG",
    }.items():
        logging.getLogger(module).setLevel(getattr(logging, level))
```

---

## 10. Configuration Validation

### Startup Checks

```python
"""aiflow/core/startup.py -- Indulaskor lefuto validaciok."""

from aiflow.core.config import get_settings

async def validate_config() -> list[str]:
    """Kritikus konfiguracios ertekek ellenorzese -- hiba eseten nem indul az app."""
    s = get_settings()
    errors: list[str] = []

    # Kotelezo ertekek
    if not Path(s.security.jwt_private_key_path).exists():
        errors.append("security.jwt_private_key_path nem talalhato (RS256 private key kotelezo)")
    if not Path(s.security.jwt_public_key_path).exists():
        errors.append("security.jwt_public_key_path nem talalhato (RS256 public key kotelezo)")

    if s.langfuse.enabled and not s.langfuse.public_key:
        errors.append("langfuse.enabled=true, de public_key ures")

    if not s.database.url:
        errors.append("database.url kotelezo -- nincs megadva")

    # Ertelmessegi vizsgalatok
    if s.database.pool_size < 5:
        errors.append(f"database.pool_size={s.database.pool_size} tul alacsony (min 5)")

    if s.budget.default_per_run <= 0:
        errors.append("budget.default_per_run pozitiv szam kell legyen")

    if s.app.environment == "prod" and s.app.debug:
        errors.append("FIGYELEM: prod environment-ben debug=true -- biztonsagi kockazat")

    if s.app.environment == "prod" and s.api.docs_enabled:
        errors.append("FIGYELEM: prod-ban docs_enabled=true -- ajanlott kikapcsolni")

    return errors
```

### Health Endpoint Config Verification

```python
"""aiflow/api/health.py -- /health endpoint config riporttal."""

from fastapi import APIRouter
from aiflow.core.config import get_settings

router = APIRouter()

@router.get("/health")
async def health_check() -> dict:
    s = get_settings()
    return {
        "status": "ok",
        "version": s.app.version,
        "environment": s.app.environment,
        "config": {
            "database_pool": s.database.pool_size,
            "llm_model": s.llm.default_model,
            "langfuse_enabled": s.langfuse.enabled,
            "log_level": s.observability.log_level,
            "prometheus": s.observability.prometheus_enabled,
            "budget_per_run": s.budget.default_per_run,
        },
    }
```

### Shell: gyors config-ellenorzes inditaskor

```bash
#!/usr/bin/env bash
# scripts/check_config.sh -- Inditas elotti gyors teszt
set -euo pipefail

echo "=== AIFlow Config Check ==="

: "${AIFLOW_DATABASE__URL:?HIBA: AIFLOW_DATABASE__URL nincs beallitva}"
: "${AIFLOW_REDIS__URL:?HIBA: AIFLOW_REDIS__URL nincs beallitva}"
: "${AIFLOW_SECURITY__JWT_PRIVATE_KEY_PATH:?HIBA: AIFLOW_SECURITY__JWT_PRIVATE_KEY_PATH nincs beallitva}"
: "${AIFLOW_SECURITY__JWT_PUBLIC_KEY_PATH:?HIBA: AIFLOW_SECURITY__JWT_PUBLIC_KEY_PATH nincs beallitva}"

if [ "${AIFLOW_APP__ENVIRONMENT:-dev}" = "prod" ]; then
  if [ "${AIFLOW_APP__DEBUG:-false}" = "true" ]; then
    echo "WARN: debug=true prod environment-ben"
  fi
  if [ "${AIFLOW_API__DOCS_ENABLED:-true}" = "true" ]; then
    echo "WARN: Swagger UI aktiv prod-ban"
  fi
fi

echo "Config OK -- inditas folytatodik."
```
