Generate a new AIFlow framework module with full boilerplate.

Arguments: $ARGUMENTS
(e.g., "src/aiflow/engine/policies.py" or just "engine.policies")

Ask me for:
1. Module path (e.g., src/aiflow/engine/policies.py)
2. Brief description
3. Key classes/functions to implement

Then generate:
1. **The module file** with:
   - Module docstring
   - Proper imports (from aiflow.core.*, typing, pydantic)
   - `__all__` export list
   - Classes with full type annotations
   - structlog logger: `logger = structlog.get_logger(__name__)`
   - Proper async patterns where I/O is involved

2. **The test file** at the corresponding test path:
   - `tests/unit/{module_path}/test_{name}.py`
   - `@test_registry` header (MANDATORY)
   - Minimum 5 tests per public class/function
   - Fixtures using conftest.py (mock_ctx, mock_llm)

3. **Update test_suites.yaml** if a new suite is needed

4. **Update regression_matrix.yaml** with the new module's mapping

5. **After generating**, run `/regression` to verify nothing broke

6. **If new service module**: check `01_PLAN/42_SERVICE_GENERALIZATION_PLAN.md` Section 3-4 — illik-e a tervezett service architekturaba?

7. **VALOS teszteles** (SOHA ne mock/fake!):
   - Ha DB-t hasznal: valos PostgreSQL (Docker), `alembic upgrade head` + `downgrade -1` + `upgrade head`
   - Ha Redis-t hasznal: valos Redis (Docker), cache hit/miss + rate limit teszt
   - Ha API endpoint: `curl` hivással valos adat ellenorzes (NEM csak 200 OK!)
   - Ha UI komponens: Playwright E2E (navigate → snapshot → click → screenshot)
   - **A modul CSAK AKKOR "KESZ" ha valos teszteken atment**

Rules from CLAUDE.md:
- All public API must be typed (no `Any` without justification)
- Pydantic BaseModel for data classes
- async for I/O operations
- structlog for logging
- AIFlowError subclasses for errors

Environment: uses .venv (uv-managed), services in Docker.
See 01_PLAN/27_DEVELOPMENT_ENVIRONMENT.md for full setup.
