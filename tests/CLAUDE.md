# AIFlow Test Suite

## Test Types
- tests/unit/ - Mock-based, no external services, <30s total
- tests/integration/ - Real PostgreSQL + Redis (testcontainers), 2-5 min
- tests/e2e/ - Full pipeline, all services running
- tests/ui/ - Playwright GUI tests (Page Object Model)
- skills/*/tests/ - Per-skill tests + Promptfoo

## MANDATORY Rules
- @test_registry header on EVERY test file
- Regression MUST run before every commit (/regression command)
- Coverage MUST NOT decrease (80% global minimum)
- Flaky tests: quarantine, fix within 5 days, NEVER delete
- Full details: 01_PLAN/24_TESTING_REGRESSION_STRATEGY.md

## Key Files
- tests/conftest.py - Global fixtures (mock_ctx, mock_llm)
- tests/test_suites.yaml - Suite definitions
- tests/regression_matrix.yaml - Change -> suite mapping
