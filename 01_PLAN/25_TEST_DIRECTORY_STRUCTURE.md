# AIFlow - Teszt Mappaszerkezet es Registry Formatum

---

## 1. Teljes Teszt Konyvtar Struktura

```
tests/
|
|-- conftest.py                          # Globalis fixtures (mock_ctx, mock_llm, test_settings)
|-- test_suites.yaml                     # Suite definiciok (lasd 24_TESTING_REGRESSION.md)
|-- regression_matrix.yaml               # Valtozas -> erintett suite-ok mapping
|-- pytest.ini                           # pytest globalis konfig (markers, asyncio_mode)
|
|-- unit/                                # UNIT TESZTEK (mock-okkal, nincs kulso fuggoseg)
|   |-- conftest.py                      # Unit-specifikus fixtures
|   |-- core/
|   |   |-- test_config.py               # AIFlowSettings tesztek
|   |   |-- test_context.py              # ExecutionContext tesztek
|   |   |-- test_errors.py               # Exception hierarchia tesztek
|   |   |-- test_events.py               # Event Bus tesztek
|   |   |-- test_registry.py             # Registry tesztek
|   |   |-- test_di.py                   # DI container tesztek
|   |-- engine/
|   |   |-- test_step.py                 # @step decorator + output_types
|   |   |-- test_dag.py                  # DAG topological sort, validation
|   |   |-- test_workflow.py             # @workflow + WorkflowBuilder
|   |   |-- test_runner.py               # WorkflowRunner (mock state/queue)
|   |   |-- test_policies.py             # RetryPolicy, CircuitBreaker, Timeout
|   |   |-- test_checkpoint.py           # Checkpoint/resume
|   |   |-- test_conditions.py           # Elagazas feltetel kiertekeles
|   |   |-- test_serialization.py        # YAML export/import
|   |-- agents/
|   |   |-- test_specialist.py           # SpecialistAgent base
|   |   |-- test_orchestrator.py         # OrchestratorAgent (max 6 check)
|   |   |-- test_quality_gate.py         # Score-alapu kapuk
|   |   |-- test_human_loop.py           # HumanReviewRequest
|   |   |-- test_reflection.py           # Generate-Critique-Improve
|   |   |-- test_messages.py             # AgentRequest/Response
|   |-- models/
|   |   |-- test_client.py               # ModelClient facade
|   |   |-- test_registry.py             # ModelRegistry CRUD
|   |   |-- test_router.py              # Cost/capability routing
|   |   |-- test_cost.py                # ModelCostCalculator
|   |   |-- test_protocols.py           # Protocol tipusellenorzes
|   |-- prompts/
|   |   |-- test_manager.py              # PromptManager (Langfuse + fallback)
|   |   |-- test_sync.py                # YAML -> Langfuse sync
|   |   |-- test_ab_testing.py           # Traffic splitting
|   |   |-- test_schema.py              # Prompt YAML validacio
|   |-- security/
|   |   |-- test_auth.py                 # JWT + API key
|   |   |-- test_rbac.py                 # Role-based access
|   |   |-- test_guardrails.py           # Input/output guardrails
|   |-- vectorstore/
|   |   |-- test_pgvector.py             # pgvector operations (mock DB)
|   |   |-- test_search.py              # HybridSearchEngine (mock)
|   |   |-- test_embedder.py            # Embedding wrapper
|   |-- documents/
|   |   |-- test_registry.py            # DocumentRegistry lifecycle
|   |   |-- test_freshness.py           # FreshnessEnforcer
|   |   |-- test_versioning.py          # Supersession
|   |-- skills/
|   |   |-- test_manifest.py            # SkillManifest parsing
|   |   |-- test_loader.py             # Skill loading
|   |   |-- test_skill_registry.py     # SkillRegistry
|   |-- execution/
|   |   |-- test_dlq.py                # Dead Letter Queue logic
|   |   |-- test_rate_limiter.py       # Rate limiting logic
|   |-- cli/
|       |-- test_commands.py           # CLI command parsing (typer)
|
|-- integration/                         # INTEGRACIOS TESZTEK (valos Docker services)
|   |-- conftest.py                      # testcontainers fixtures (postgres, redis)
|   |-- test_api.py                      # FastAPI TestClient (minden endpoint)
|   |-- test_api_auth.py                 # Auth + RBAC endpoint tesztek
|   |-- test_queue.py                    # arq enqueue/dequeue/DLQ (valos Redis)
|   |-- test_state_store.py              # PostgreSQL CRUD + migrations
|   |-- test_vectorstore.py              # pgvector upsert + hybrid search (valos PG)
|   |-- test_skill_install.py            # 9-lepes skill install (valos DB)
|   |-- test_prompt_sync.py              # Langfuse sync (mock vagy valos)
|   |-- test_workflow_execution.py       # Workflow futtatás valos state store-ral
|
|-- e2e/                                 # END-TO-END TESZTEK (teljes rendszer)
|   |-- conftest.py                      # Running system fixtures
|   |-- test_full_pipeline.py            # API -> queue -> worker -> result
|   |-- test_skill_lifecycle.py          # Install -> run -> monitor -> upgrade
|   |-- test_prompt_lifecycle.py         # Sync -> test -> promote -> rollback
|
|-- ui/                                  # FRONTEND GUI TESZTEK (Playwright)
|   |-- conftest.py                      # Playwright browser fixtures
|   |-- pages/                           # Page Object Model
|   |   |-- login_page.py
|   |   |-- dashboard_page.py
|   |   |-- chat_page.py
|   |   |-- admin_page.py
|   |   |-- developer_page.py
|   |-- test_login.py
|   |-- test_dashboard.py
|   |-- test_chat.py
|   |-- test_admin.py
|   |-- test_accessibility.py            # WCAG 2.1 AA
|   |-- test_visual_regression.py        # Screenshot baseline osszehasonlitas
|
|-- artifacts/                           # TESZT ARTEFAKTUMOK (gitignored!)
|   |-- .gitkeep
|   |-- {YYYY-MM-DD}/
|   |   |-- {run_id}/
|   |       |-- summary.json
|   |       |-- junit.xml
|   |       |-- coverage.xml
|   |       |-- coverage_html/
|   |       |-- failed_tests.json
|   |       |-- regression_diff.json
|   |       |-- screenshots/
|   |       |-- traces/
|   |       |-- promptfoo_results/
|   |       |-- logs/
|
|-- fixtures/                            # MEGOSZTOTT TESZT ADATOK
|   |-- sample_workflow.py               # Pelda workflow (3-step linearis)
|   |-- sample_agents.py                 # Mock agent implementaciok
|   |-- sample_prompts/                  # Teszt prompt YAML-ok
|   |   |-- test_classifier.yaml
|   |   |-- test_extractor.yaml
|   |-- sample_documents/                # Teszt dokumentumok (RAG)
|   |   |-- test_aszf.pdf
|   |   |-- test_szabalyzat.docx
|   |-- sample_emails/                   # Teszt email-ek
|   |   |-- complaint_hu.json
|   |   |-- inquiry_en.json
|
|-- scripts/                             # CI/CD HELPER SCRIPTEK
|   |-- resolve_regression_matrix.py     # Valtozas -> suite-ok feloldas
|   |-- run_suite.py                     # Suite futtato (pytest wrapper)
|   |-- check_coverage_gate.py           # Coverage kapu ellenorzes
|   |-- generate_regression_diff.py      # Elozo futassal osszehasonlitas
|   |-- save_regression_record.py        # DB-be mentes
|   |-- generate_weekly_report.py        # Heti regresszios riport
|   |-- detect_flaky_tests.py            # Flaky teszt detektalas
|   |-- validate_test_registry.py        # @test_registry fejlec ellenorzes
```

---

## 2. Skill Teszt Konyvtar Struktura (Skill-enkent)

```
skills/{skill_name}/tests/
|-- __init__.py
|-- conftest.py                          # Skill-specifikus fixtures
|-- promptfooconfig.yaml                 # Promptfoo teszt konfiguracio
|-- test_workflow.py                     # Teljes workflow integracio
|-- test_classifier.py                   # Agent-specifikus tesztek
|-- test_extractor.py
|-- test_{agent_name}.py
|-- datasets/
|   |-- classification_{N}.json          # Teszt adatok (N = eset szam)
|   |-- extraction_{N}.json
|   |-- edge_cases.json
|   |-- adversarial.json
|-- baselines/                           # Prompt test baseline eredmenyek
|   |-- classifier_v{X}_baseline.json    # Adott prompt verzio elvart eredmenyei
|-- artifacts/                           # Skill-specifikus artefaktumok (gitignored)
    |-- .gitkeep
```

---

## 3. @test_registry Fejlec Formatum (Kotelezo)

Minden teszt fajlban az ELSO docstring-ben:

```python
"""
@test_registry:
    suite: engine-unit                    # KOTELEZO: melyik suite-ban van
    component: engine.dag                 # KOTELEZO: melyik komponenst teszteli
    covers:                               # KOTELEZO: mely forrasfajlokat fedi le
        - src/aiflow/engine/dag.py
        - src/aiflow/engine/conditions.py
    phase: 2                              # KOTELEZO: melyik fazisban keszult
    priority: critical                    # KOTELEZO: critical|high|medium|low
    estimated_duration_ms: 500            # AJANLOTT: becsult futasi ido
    requires_services: []                 # KOTELEZO: [] vagy [postgres, redis, langfuse]
    tags: [dag, topological-sort]         # AJANLOTT: szabad cimkek
    added_in_step: DS-2026-0328-003       # AJANLOTT: fejlesztesi lepes referencia
"""
```

**Validacio:** A `scripts/validate_test_registry.py` ellenorzi CI-ban hogy
MINDEN teszt fajlnak van-e valid @test_registry fejlece. Ha nincs -> CI FAIL.

---

## 4. test_suites.yaml Formatum

```yaml
# tests/test_suites.yaml
# Kozponti suite definiciok - a CI pipeline ebbol dolgozik

version: 1
suites:
  engine-unit:
    description: "Workflow engine unit tesztek"
    path: "tests/unit/engine/"
    suite_type: unit
    run_on: [commit, pr, merge]
    priority: critical
    max_duration_seconds: 60
    coverage_target: 90.0
    requires_services: []
    components:
      - engine.step
      - engine.dag
      - engine.workflow
      - engine.runner
      - engine.policies
      - engine.checkpoint
    source_files:
      - src/aiflow/engine/*.py

  # ... tobbi suite (lasd 24_TESTING_REGRESSION_STRATEGY.md)
```

---

## 5. regression_matrix.yaml Formatum

```yaml
# tests/regression_matrix.yaml
# Valtozas -> erintett suite-ok mapping

version: 1
rules:
  # FULL regresszio triggerek
  - pattern: "src/aiflow/core/**"
    suites: FULL
    reason: "Core kernel valtozas MINDEN komponenst erint"

  - pattern: "src/aiflow/security/**"
    suites: FULL
    reason: "Security valtozas MINDENT erinthet"

  - pattern: "pyproject.toml"
    suites: FULL
    reason: "Fuggoseg valtozas MINDENT erinthet"

  # Szelektiv triggerek
  - pattern: "src/aiflow/engine/step.py"
    suites:
      - engine-unit
      - agents-unit
      - integration-api
      - e2e-pipeline
      - skill-process-doc
      - skill-aszf-rag
      - skill-email-intent
      - skill-cfpb
      - skill-cubix
      - skill-qbpp
    reason: "Step decorator minden workflow-t erint"

  # ... (teljes matrix a 24-es dokumentumban)

# Default: ha nem illeszkedik egyetlen rule-ra sem
default_suites:
  - core-unit
  - engine-unit
```

---

## 6. Artefaktum Formatum: summary.json

```json
{
  "run_id": "reg-2026-03-28-003",
  "run_code": "reg-2026-03-28-003",
  "timestamp": "2026-03-28T14:30:00Z",
  "trigger": {
    "type": "pr",
    "ref": "PR #42",
    "branch": "feature/AIFLOW-42-retry-policy",
    "commit": "abc1234def5678"
  },
  "regression_level": "L2",
  "development_step": "DS-2026-0328-003",
  "suites_executed": [
    {
      "name": "engine-unit",
      "status": "passed",
      "tests": 45,
      "passed": 45,
      "failed": 0,
      "duration_ms": 12400,
      "coverage_pct": 89.2
    },
    {
      "name": "integration-api",
      "status": "passed",
      "tests": 23,
      "passed": 23,
      "failed": 0,
      "duration_ms": 34500,
      "coverage_pct": 81.5
    }
  ],
  "totals": {
    "suites_run": 2,
    "suites_passed": 2,
    "suites_failed": 0,
    "total_tests": 68,
    "passed": 68,
    "failed": 0,
    "skipped": 0,
    "new_tests": 12,
    "regressions": 0
  },
  "coverage": {
    "total_pct": 83.4,
    "previous_pct": 82.1,
    "change_pct": 1.3,
    "gate_passed": true
  },
  "duration_total_seconds": 47,
  "cost_usd": 0.0,
  "overall_result": "ALL_PASS",
  "gate_decision": "APPROVED"
}
```

---

## 7. Artefaktum Formatum: regression_diff.json

```json
{
  "run_id": "reg-2026-03-28-003",
  "previous_run_id": "reg-2026-03-27-042",
  "comparison": {
    "tests_added": [
      "tests/unit/engine/test_policies.py::test_exponential_backoff",
      "tests/unit/engine/test_policies.py::test_jitter_randomness"
    ],
    "tests_removed": [],
    "regressions": [],
    "new_failures": [],
    "fixed_tests": [],
    "flaky_suspects": [],
    "performance_changes": [
      {
        "suite": "engine-unit",
        "previous_ms": 11200,
        "current_ms": 12400,
        "change_pct": 10.7,
        "verdict": "acceptable"
      }
    ]
  },
  "verdict": "NO_REGRESSIONS"
}
```

---

## 8. .gitignore Kiegeszites

```gitignore
# Teszt artefaktumok (NEM commitolando)
tests/artifacts/
!tests/artifacts/.gitkeep
skills/*/tests/artifacts/
!skills/*/tests/artifacts/.gitkeep

# Coverage
htmlcov/
.coverage
coverage.xml

# Playwright
tests/ui/test-results/

# Promptfoo
.promptfoo/
```

---

## 9. conftest.py Vazlat

```python
# tests/conftest.py
"""
Globalis teszt fixtures az AIFlow projekthez.
Minden teszt fajl automatikusan hozzafer ezekhez.
"""
import pytest
from aiflow.core.config import AIFlowSettings
from aiflow.core.context import ExecutionContext

@pytest.fixture(scope="session")
def test_settings():
    """Test-specifikus beallitasok (nincs valos LLM, nincs valos Langfuse)."""
    return AIFlowSettings(
        database_url="postgresql+asyncpg://test:test@localhost:5432/aiflow_test",
        redis_url="redis://localhost:6379/1",
        langfuse_public_key=None,
        langfuse_secret_key=None,
        default_model="openai/gpt-4o-mini",
        log_level="DEBUG",
        environment="test",
    )

@pytest.fixture
def mock_ctx():
    """Mock ExecutionContext - minden unit tesztben hasznalhato."""
    return ExecutionContext(
        run_id="test-run-001",
        prompt_label="test",
        budget_remaining_usd=10.0,
    )

@pytest.fixture
def mock_llm(mocker):
    """Mock LLM client - nem kell valos API hivas unit tesztben."""
    client = mocker.AsyncMock()
    client.generate.return_value = mocker.MagicMock(text='{"result": "ok"}')
    return client

@pytest.fixture
def mock_prompts(mocker):
    """Mock PromptManager - YAML-bol tolt, nem Langfuse-bol."""
    manager = mocker.AsyncMock()
    prompt = mocker.MagicMock()
    prompt.compile.return_value = [{"role": "user", "content": "test"}]
    manager.get.return_value = prompt
    return manager
```
