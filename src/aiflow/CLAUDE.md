# AIFlow Framework Source Code

## Module Map
- core/ - Kernel (config, context, errors, events, DI, registry, types)
- engine/ - Workflow execution (step, dag, workflow, runner) [Phase 2]
- models/ - ML model abstraction [Phase 2]
- prompts/ - Langfuse SSOT prompt management [Phase 3]
- execution/ - Async queue (arq), worker, scheduler [Phase 5]
- state/ - PostgreSQL ORM, Alembic migrations [Phase 1 Het 2]
- observability/ - Langfuse+OTel tracing, cost_tracker [Phase 6]
- evaluation/ - EvalSuite, scorers, Promptfoo [Phase 4]
- security/ - JWT+API key auth, RBAC, audit [Phase 5]
- api/v1/ - FastAPI endpoints [Phase 5]
- vectorstore/ - pgvector hybrid search [Phase 2]
- documents/ - Document lifecycle [Phase 3]
- ingestion/ - Parsers, chunkers [Phase 3]
- ui/ - Reflex frontend [Phase 5]
- cli/ - typer CLI [Phase 6]
- contrib/ - Optional integrations [Phase 5+]

## Rules
- Every public function MUST have type annotations
- Every module MUST have __all__ exports
- Use structlog: `logger = structlog.get_logger(__name__)`
- Errors MUST subclass AIFlowError
- I/O operations MUST be async
- Config via DI (never import settings directly in business logic)
- Pydantic BaseModel for all data classes
