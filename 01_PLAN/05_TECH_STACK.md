# AIFlow - Tech Stack es Fuggosegek

## Core Dependencies

### Python Runtime
- **Python 3.12+** - legujabb stabil, tipusrendszer tamogatas

### Web Framework
| Csomag | Verzio | Szerep |
|--------|--------|--------|
| fastapi | >= 0.110 | REST API framework |
| uvicorn[standard] | >= 0.27 | ASGI server |
| pydantic | >= 2.5 | Data validation, settings |
| pydantic-settings | >= 2.1 | Environment-based config |
| httpx | >= 0.27 | Async HTTP client |

### LLM
| Csomag | Verzio | Szerep |
|--------|--------|--------|
| litellm | >= 1.40 | Multi-provider LLM abstraction |
| instructor | >= 1.4 | Structured output (Pydantic response) |
| openai | >= 1.10 | OpenAI API client |

### Observability
| Csomag | Verzio | Szerep |
|--------|--------|--------|
| langfuse | >= 2.40 | LLM tracing + prompt SSOT |
| structlog | >= 24.1 | Structured JSON logging |
| opentelemetry-api | >= 1.22 | Infra tracing API |
| opentelemetry-sdk | >= 1.22 | Infra tracing SDK |
| opentelemetry-exporter-otlp | >= 1.22 | OTLP exporter |
| prometheus-client | >= 0.20 | Prometheus metriak |

### Database & Queue
| Csomag | Verzio | Szerep |
|--------|--------|--------|
| asyncpg | >= 0.29 | PostgreSQL async driver |
| sqlalchemy[asyncio] | >= 2.0 | ORM (opcionalis, SQL builder) |
| alembic | >= 1.13 | DB migraciok |
| arq | >= 0.26 | Async Redis job queue |
| redis[hiredis] | >= 5.0 | Redis async client |

### Security
| Csomag | Verzio | Szerep |
|--------|--------|--------|
| PyJWT[crypto] | >= 2.8 | JWT token kezeles (RS256) |
| bcrypt | >= 4.1 | API key + password hashing |
| hvac | >= 2.1 | HashiCorp Vault client |

### CLI
| Csomag | Verzio | Szerep |
|--------|--------|--------|
| typer | >= 0.12 | CLI framework |
| rich | >= 13.7 | Terminal output formatting |

### Scheduling
| Csomag | Verzio | Szerep |
|--------|--------|--------|
| apscheduler | >= 4.0 | Async cron scheduling (nativ asyncio) |

### Prompt Engineering
| Csomag | Verzio | Szerep |
|--------|--------|--------|
| pyyaml | >= 6.0 | YAML prompt loading |
| jinja2 | >= 3.1 | Prompt template rendering |

### Opcionalis (Funkcionalis)
| Csomag | Extra | Szerep |
|--------|-------|--------|
| pgvector | `aiflow[vectorstore]` | pgvector Python bindings |
| tiktoken | `aiflow[vectorstore]` | Token counting (chunking) |
| pymupdf | `aiflow[vectorstore]` | PDF parser |
| playwright | `aiflow[rpa]` | Web automatizacio + GUI teszt |
| robotframework | `aiflow[rpa]` | Opcionalis RPA framework |
| reflex | `aiflow[ui]` | Python frontend framework |
| aiokafka | `aiflow[kafka]` | Kafka adapter |
| hvac | `aiflow[vault]` | HashiCorp Vault |
| opentelemetry-sdk | `aiflow[otel]` | Infra tracing |
| sentence-transformers | `aiflow[local-models]` | Lokalis ML modellek |

### Opcionalis (Skill-specifikus)
| Csomag | Verzio | Szerep | Skill |
|--------|--------|--------|-------|
| python-docx | >= 1.1 | Word export | process_documentation |
| openpyxl | >= 3.1 | Excel export | process_documentation, qbpp_test |
| drawpyo | >= 0.2 | Draw.io XML | process_documentation |
| scikit-learn | >= 1.4 | ML pipeline | cfpb_complaint_router |
| xgboost | >= 2.0 | Gradient boosting | cfpb_complaint_router |
| pdfplumber | >= 0.10 | PDF extraction | aszf_rag_chat |
| beautifulsoup4 | >= 4.12 | Web scraping | aszf_rag_chat |

---

## Dev Dependencies

| Csomag | Verzio | Szerep |
|--------|--------|--------|
| pytest | >= 8.0 | Test framework |
| pytest-asyncio | >= 0.23 | Async test support |
| pytest-cov | >= 4.1 | Code coverage |
| pytest-bdd | >= 8.0 | BDD/Gherkin tesztek |
| pytest-playwright | >= 0.4 | Playwright GUI tesztek |
| pytest-xdist | >= 3.5 | Parhuzamos tesztfuttatas |
| testcontainers | >= 4.0 | Docker test fixtures |
| ruff | >= 0.3 | Linting + formatting (replaces flake8, isort, black) |
| mypy | >= 1.8 | Static type checking |
| pre-commit | >= 3.6 | Git pre-commit hooks |
| detect-secrets | >= 1.4 | Secret detection pre-commit |
| libcst | >= 1.1 | AST-based skill migration |

---

## Infrastructure

### Docker Images
| Service | Image | Port | Szerep |
|---------|-------|------|--------|
| PostgreSQL+pgvector | pgvector/pgvector:pg16 | 5432 | Fo adatbazis + vector store |
| Redis | redis:7-alpine | 6379 | Job queue + cache |
| AIFlow API | custom (Dockerfile) | 8000 | FastAPI alkalmazas |
| AIFlow Worker | custom (Dockerfile) | - | Queue worker (N replica) |
| Kroki | yuzutech/kroki | 8080 | Diagram rendereles |
| Mermaid | yuzutech/kroki-mermaid | - | Mermaid engine |
| n8n (opt) | n8nio/n8n:latest | 5678 | Vizualis workflow editor |
| Grafana (opt) | grafana/grafana | 3000 | Dashboard-ok |

### Kubernetes (Production)
| Komponens | Replicas | Autoscaling |
|-----------|----------|-------------|
| API | 2-4 | CPU-based HPA |
| Worker | 2-20 | Queue depth-based HPA |
| Scheduler | 1 | - (singleton) |
| PostgreSQL | 1 (StatefulSet) | Vertical |
| Redis | 1 (HA optionalis) | - |

---

## External Services

| Service | Hasznalat | Kotelezo? |
|---------|-----------|-----------|
| OpenAI API | LLM hivasok (GPT-4o, GPT-4o-mini) | Igen (vagy mas LLM provider) |
| Langfuse Cloud | Prompt SSOT + LLM tracing | Igen (vagy self-hosted) |
| HashiCorp Vault | Secrets management (prod) | Nem (dev-ben .env) |
| GitHub | Forras kontroll + CI/CD | Igen |
| Miro API | Board export (opcionalis) | Nem |

---

## pyproject.toml Pelda

```toml
[project]
name = "aiflow"
version = "0.1.0"
description = "Enterprise AI Automation Framework"
requires-python = ">=3.12"

dependencies = [
    # Web
    "fastapi>=0.110",
    "uvicorn[standard]>=0.27",
    "pydantic>=2.5",
    "pydantic-settings>=2.1",
    "httpx>=0.27",

    # LLM
    "litellm>=1.40",
    "instructor>=1.4",
    "openai>=1.10",

    # Observability
    "langfuse>=2.40",
    "structlog>=24.1",
    "opentelemetry-api>=1.22",
    "opentelemetry-sdk>=1.22",
    "prometheus-client>=0.20",

    # Database & Queue
    "asyncpg>=0.29",
    "sqlalchemy[asyncio]>=2.0",
    "alembic>=1.13",
    "arq>=0.26",
    "redis[hiredis]>=5.0",

    # Security
    "PyJWT[crypto]>=2.8",
    "bcrypt>=4.1",

    # CLI
    "typer>=0.12",
    "rich>=13.7",

    # Prompts
    "pyyaml>=6.0",
    "jinja2>=3.1",

    # Scheduling
    "apscheduler>=4.0",
]

[project.optional-dependencies]
vault = ["hvac>=2.1"]
otel = ["opentelemetry-exporter-otlp>=1.22"]
ui = ["reflex>=0.6"]
rpa = ["playwright>=1.40"]
local-models = ["sentence-transformers>=3.0"]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-cov>=4.1",
    "ruff>=0.3",
    "mypy>=1.8",
    "pre-commit>=3.6",
    "detect-secrets>=1.4",
    "libcst>=1.1",
]

[project.scripts]
aiflow = "aiflow.cli.main:app"

[tool.ruff]
line-length = 100
select = ["E", "F", "I", "N", "W", "UP"]
format = { line-length = 100 }

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.mypy]
python_version = "3.12"
strict = true
```
