---
name: smoke-test
description: Gyors smoke teszt — API health, lint, tsc, E2E collect-only (<3 perc)
allowed-tools: Bash, Read, Grep
---

# Smoke Test — Gyors validacio (<3 perc)

## Folyamat

### 1. API Health Check
```bash
curl -s http://localhost:8102/health | python -m json.tool
```
Elvart: `{"status": "ready", ...}` — ha FAIL, az API nem fut.

### 2. Lint Check
```bash
python -m ruff check src/ tests/ --statistics
```
Elvart: 0 error.

### 3. TypeScript Check
```bash
cd aiflow-admin && npx tsc --noEmit
```
Elvart: 0 error.

### 4. E2E Collect-Only
```bash
python -m pytest tests/e2e/ --collect-only -q 2>&1 | tail -3
```
Elvart: `169 tests collected` (vagy tobb).

### 5. Unit Test Quick (optional, ha van ido)
```bash
python -m pytest tests/unit/ -x -q 2>&1 | tail -3
```
Elvart: `1443 passed` (vagy tobb).

## Output

```
## Smoke Test Report

| Check | Status | Details |
|-------|--------|---------|
| API Health | PASS/FAIL | ... |
| Ruff Lint | PASS/FAIL | ... |
| TSC | PASS/FAIL | ... |
| E2E Collect | PASS/FAIL | N tests |
| Unit Quick | PASS/FAIL/SKIP | N tests |

Verdict: ALL PASS / X FAILURES
```

## Ha FAIL
- API nem fut → `PYTHONPATH=src .venv/Scripts/python -m uvicorn aiflow.api.app:create_app --factory --port 8102`
- Lint hiba → `python -m ruff check --fix src/`
- TSC hiba → ellenorizd a `.tsx` fajlokat
- E2E collect FAIL → szintaktikai hiba a teszt fajlban
