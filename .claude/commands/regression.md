Run regression tests for the current changes.

Arguments: $ARGUMENTS
(Optional: L1/L2/L3/L4/L5 to specify level, or "full" for L3)

## Context (v1.3.0)
Branch: feature/v1.3.0-service-excellence
Expected test count: 1164+ unit tests, 76 guardrail tests, 97 security tests
Coverage baseline: 80% minimum

Steps:
1. Run `git diff --name-only HEAD` to identify changed files
2. Read `tests/regression_matrix.yaml` to determine affected suites
3. If any changed file triggers FULL regression (core/, security/, pyproject.toml):
   - Run ALL test suites
4. Otherwise, run only the affected suites

Ensure .venv is active (uv-managed). For each suite:
```bash
.venv/Scripts/pytest {suite_path} -v --tb=short --cov=aiflow --cov-report=term-missing
```
(On Unix use `.venv/bin/pytest`)

After running:
1. Report results in a table:
   | Suite | Tests | Passed | Failed | Coverage | Duration |
2. If ANY test failed:
   - Show the failure details
   - Identify if it's a REGRESSION (previously passing test now fails)
   - DO NOT proceed to commit
3. If all passed:
   - Show coverage summary
   - Confirm coverage didn't decrease
   - Report: "Regression L{X}: {total} tests, ALL PASS, coverage {pct}%"

If `tests/regression_matrix.yaml` doesn't exist yet (early development):
- Run `pytest tests/ -v --cov=aiflow` (everything that exists)

IMPORTANT: This command MUST be run before every commit. It is NOT optional.

## VALOS teszteles kovetelmeny:
- Integration tesztek valos PostgreSQL + Redis (Docker) ellen futnak, NEM in-memory mock
- Ha service generalizacios fazisban vagyunk (F0-F5): service-specifikus tesztek is futnak
- `curl` hivással valos API endpointok ellenorzese — NEM csak pytest, hanem valos HTTP keresek
- Coverage NEM csokkenhet — ha csokken, az regresszio es BLOCK!
- Mock/fake eredmennyel NEM lehet atmenni — valos backend, valos DB, valos adat
