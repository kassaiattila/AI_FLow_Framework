# AIFlow Stub Inventory

> Last updated: 2026-04-04 (Session 16, A4 stub audit)
> All stubs listed here are **intentional** and tracked.

## Deferred Modules (post-v1.2.x)

| Module | Status | Planned | Rationale |
|--------|--------|---------|-----------|
| `tools/kafka.py` | Stub (logs only) | v1.4.0+ | In-memory MessageBroker sufficient; Kafka needs multi-node deployment |
| `security/secrets.py:VaultSecretProvider` | NotImplementedError | v1.3.0+ | HashiCorp Vault integration; EnvSecretProvider covers current needs |

## CLI Commands (planned for v1.3.0)

| Command | File | Status |
|---------|------|--------|
| `aiflow skill install` | `cli/commands/skill.py` | Prints planned message |
| `aiflow skill validate` | `cli/commands/skill.py` | Prints planned message |
| `aiflow skill uninstall` | `cli/commands/skill.py` | Prints planned message |
| `aiflow eval run` | `cli/commands/eval_cmd.py` | Prints planned message (use Promptfoo) |
| `aiflow eval report` | `cli/commands/eval_cmd.py` | Prints planned message (use Promptfoo) |
| `aiflow prompt sync` | `cli/commands/prompt.py` | Prints planned message |
| `aiflow prompt diff` | `cli/commands/prompt.py` | Prints planned message |
| `aiflow prompt promote` | `cli/commands/prompt.py` | Prints planned message |
| `aiflow workflow run` | `cli/commands/workflow.py` | Prints planned message |
| `aiflow workflow inspect` | `cli/commands/workflow.py` | Prints planned message |
| `aiflow workflow docs` | `cli/commands/workflow.py` | Prints planned message |

## Deprecated Modules (backward compat only)

| Module | Replacement | Notes |
|--------|-------------|-------|
| `ingestion/parsers/pdf_parser.py` | `ingestion/parsers/docling_parser.py` | DoclingParser handles PDF/DOCX/XLSX/HTML |
| `ingestion/parsers/docx_parser.py` | `ingestion/parsers/docling_parser.py` | DoclingParser handles PDF/DOCX/XLSX/HTML |
| `skills/__init__.py` | `skill_system/` | Re-exports for backward compatibility |

## Abstract Interfaces (by design)

| Class | File | Notes |
|-------|------|-------|
| `JobQueue` (ABC methods) | `execution/queue.py` | ArqJobQueue is the concrete impl |
| `RateLimiter` (ABC) | `execution/rate_limiter.py` | services/rate_limiter/service.py is the concrete impl |
| `BaseAdapter._run()` | `pipeline/adapter_base.py` | ABC — each adapter implements this |

## Known Partial Implementations

| Area | File | Detail |
|------|------|--------|
| API v1 workflows | `api/v1/workflows.py` | Placeholder workflow registry; pipelines API is the production path |
| Observability metrics | `observability/metrics.py` | Placeholder for Prometheus; Langfuse is the active observability system |
| Ingestion pipeline step 4 | `ingestion/pipeline.py:121` | Embedding+upsert stub; RAG engine handles this in production |
