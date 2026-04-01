Generate test file(s) for existing AIFlow code.

Arguments: $ARGUMENTS

If no arguments given, ask me for:
1. Which source file to test (e.g., src/aiflow/engine/dag.py)
2. Test type: unit / integration / e2e / prompt

Then:
1. READ the source file thoroughly
2. Identify ALL public functions, methods, and classes
3. Generate comprehensive tests with MANDATORY `@test_registry` header:

```python
"""
@test_registry:
    suite: {appropriate-suite}
    component: {dotted.component.path}
    covers: [{source_file_path}]
    phase: {current_phase}
    priority: {critical|high|medium|low}
    estimated_duration_ms: {estimate}
    requires_services: {[] or [postgres, redis]}
    tags: [{relevant, tags}]
"""
```

4. Generate tests covering:
   - Happy path (40%) - normal, expected behavior
   - Error cases (20%) - invalid input, exceptions, error handling
   - Edge cases (20%) - empty inputs, boundary values, None/null
   - Concurrency (10%) - async behavior, timeout, cancellation
   - Security (10%) - if applicable (auth, injection, validation)

5. For each test:
   - Clear, descriptive test name: `test_{what}_{scenario}_{expected}`
   - Docstring explaining what is being tested
   - Proper fixtures (mock_ctx, mock_llm from conftest.py)
   - Assert specific values, not just "not None"

6. Run the tests to verify they pass (if code exists)
7. Check coverage: `pytest {test_file} --cov={module} --cov-report=term-missing`

NEVER generate tests that:
- Test private methods directly (test through public API)
- Use `@pytest.mark.skip` without a reason
- Have no assertions
- Test implementation details instead of behavior
- **Mock-olnak ami VALOS fuggooseggel tesztelheto** (PostgreSQL, Redis, Docling — Docker-ben futnak!)

## VALOS teszteles kovetelmeny (SOHA ne mock/fake!):
- **Integration tesztek:** Valos PostgreSQL + Redis (Docker), testcontainers ha kell
- **API tesztek:** Valos FastAPI szerver, valos HTTP keresek — NEM csak 200 OK, TARTALOM ellenorzes!
- **LLM tesztek:** Promptfoo valos LLM hivassal (gpt-4o-mini), NEM hardcoded response
- **UI tesztek:** Playwright MCP E2E — navigate → snapshot → click → screenshot → console check
- **DB tesztek:** Valos migracio (`alembic upgrade head` + `downgrade -1`), valos CRUD
- **Service tesztek (F0+):** Valos Redis cache, valos rate limit, valos config versioning
- **Elfogadhatatlan:** in-memory SQLite mock produkcio PostgreSQL helyett, hardcoded JSON response LLM helyett
