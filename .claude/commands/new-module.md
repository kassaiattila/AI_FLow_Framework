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

Rules from CLAUDE.md:
- All public API must be typed (no `Any` without justification)
- Pydantic BaseModel for data classes
- async for I/O operations
- structlog for logging
- AIFlowError subclasses for errors

Environment: uses .venv (uv-managed), services in Docker.
See 01_PLAN/27_DEVELOPMENT_ENVIRONMENT.md for full setup.
