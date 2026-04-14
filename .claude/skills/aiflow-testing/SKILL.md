---
name: aiflow-testing
description: >
  AIFlow tesztelesi szabalyok, regresszio, coverage gate-ek. Hasznald amikor
  teszteket irsz, futtatod, regressziot ellenorizsz, vagy commit elott
  validalsz. SOHA ne mock/fake — valos PostgreSQL, Redis, LLM!
allowed-tools: Read, Bash, Grep, Glob
---

# AIFlow Testing Rules

## The Golden Rule

> **No code reaches main without ALL previous tests passing as regression.**
> This is a BLOCKING requirement.

## STRICT: Real Testing Only (SOHA NE MOCK/FAKE!)

- **API tesztek:** Valos FastAPI szerver, valos HTTP keresek (curl vagy Playwright)
- **Service tesztek:** Valos PostgreSQL + Redis (Docker), NEM in-memory mock
- **UI tesztek:** MCP Playwright valos bongeszioben, valos backendhez csatlakozva
- **LLM tesztek:** Valos LLM hivasok (Promptfoo), NEM hardcoded response mock
- **Upload/Process tesztek:** Valos PDF fajlok, valos Docling parse
- **DB migracio tesztek:** `alembic upgrade head && alembic downgrade -1 && alembic upgrade head`
- **Egy feature CSAK AKKOR "KESZ" ha Playwright E2E-vel vegig teszteltuk**

## Development Step Protocol

Every code change MUST follow:
1. **Write code** — implement
2. **Write tests IMMEDIATELY** — not later, NOW
   - Add `@test_registry` header to every test file
   - Minimum: 5 unit tests per new module, 3 per endpoint, 10 promptfoo per prompt
3. **Run local tests** — new + affected regression suites
4. **Verify ALL pass** — zero failures, coverage not decreased
5. **Only then commit** — include "Tests: X new, Y regression pass"

## What is FORBIDDEN

- Committing with any failing test — NEVER
- Commenting out or deleting a failing test
- Adding `@pytest.mark.skip` without tracking ticket
- Decreasing code coverage
- Skipping regression even for "quick fixes"
- Writing tests AFTER the commit
- Using `git add -A` (might include artifacts)

## Regression Levels

| Level | When | What runs | Max time |
|-------|------|-----------|----------|
| L1 Quick | Every commit | Affected unit suites | <60s |
| L2 Standard | Every PR | L1 + integration + skills | 2-5 min |
| L3 Full | Merge to main | ALL suites | 10-20 min |
| L4 Complete | Deploy staging | L3 + E2E + Playwright | 20-40 min |
| L5 Release | Deploy prod | L4 + perf + security | 30-60 min |

## Coverage Gates (BLOCKING — PR cannot merge if violated)

| Module | Minimum | Target |
|--------|---------|--------|
| core/ | 90% | 95% |
| engine/ | 85% | 90% |
| api/ | 80% | 90% |
| security/ | 90% | 95% |
| models/ | 80% | 85% |
| vectorstore/ | 75% | 80% |
| skills/*/workflows/ | 70% | 80% |
| **OVERALL** | **80%** | **85%** |

## Test File Registry Header (REQUIRED on every test file)

```python
"""
@test_registry:
    suite: engine-unit
    component: engine.dag
    covers: [src/aiflow/engine/dag.py]
    phase: 2
    priority: critical
    estimated_duration_ms: 500
    requires_services: []
    tags: [dag, validation]
"""
```

## Valos Teszteles Fazisokent

| Fazis | Mit tesztelunk | Eszkoz | Kriterium |
|-------|---------------|--------|-----------|
| Service | Redis cache, rate limit, config CRUD | curl + pytest | Cache <10ms, 429 |
| Doc Extractor | PDF extract + verify + save | curl + Playwright | Upload→extract→verify→save |
| Email | Email fetch + classify + route | curl + Playwright | Config→fetch→classify→route |
| RAG | Collection + ingest + query | curl + Playwright chat | Create→ingest→query→feedback |
| Pipeline | Pipeline vegigfut, cost tracking | /pipeline-test | Valos adat, DB sorok |

## Test Commands

```bash
pytest tests/unit/ -v                       # Unit tests
pytest tests/integration/ -v               # Integration (needs Docker)
pytest tests/unit/ --cov=aiflow --cov-report=term  # Coverage
npx promptfoo eval -c skills/*/tests/promptfooconfig.yaml  # Prompt tests
```

## Regression Matrix

When a source file changes, `tests/regression_matrix.yaml` determines which suites run.
Changes to core/, security/, or pyproject.toml trigger FULL regression.

## v2 Testing Requirements

- Backward compat regression: legacy pipeline YAML fixtures must still work
- Tenant isolation tests: all subsystems tenant-scoped
- Schema migration dry-run: alembic 029->036 chain forward + rollback
- Routing decision reproducibility: golden dataset assertions
- HITL SLA tests: escalation timing, assignment algorithm
- CI orchestration: lint -> unit -> backward-compat -> tenant-isolation -> migration -> E2E
