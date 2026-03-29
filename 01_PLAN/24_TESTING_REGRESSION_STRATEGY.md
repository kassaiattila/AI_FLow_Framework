# AIFlow - Tesztelesi es Regresszios Strategia

**Datum:** 2026-03-28
**Status:** KOTELEZO ELEIRAS - minden fejlesztesi lepesre vonatkozik
**Eletciklus:** Vegtelen - a keretrendszer es skill-ek fejlesztese sosem er veget

---

## 0. ALAPELV

> **Egyetlen sor kod sem kerulhet main branch-re anelkul, hogy MINDEN korabbi teszt
> regresszios ujrafuttatasa ZOLD lenne.**

Ez nem ajanlás. Ez **blokkolo kovetelmeny**. A CI pipeline automatikusan kikenyszeriti,
de a fejleszto (es Claude Code) felelossege is betartani lokálisan.

---

## 1. FEJLESZTESI LEPES DEFINICIOJA

### 1.1 Mi Szamit Fejlesztesi Lepesnek?

Minden **atomikus, onalloan tesztelheto valtozas** egy fejlesztesi lepes (Development Step):

| Tipus | Pelda | Teszt kovetelmeny |
|-------|-------|-------------------|
| Uj modul | `src/aiflow/engine/dag.py` | Unit tesztek + regresszio |
| Uj feature | retry policy hozzaadasa | Unit + integracio + regresszio |
| Bug fix | timeout szamitas javitas | Regresszios teszt (reprodukalo) + regresszio |
| Prompt valtozas | classifier.yaml v7 | Promptfoo + regresszio |
| Skill fejlesztes | uj agent hozzaadasa | Skill tesztek + regresszio |
| Refactoring | DI container atszervezes | TELJES regresszio (nincs uj teszt, de minden regi fut) |
| Dependency frissites | litellm 1.40 -> 1.45 | TELJES regresszio |
| Config valtozas | aiflow.yaml modositas | Integracio + regresszio |

### 1.2 Fejlesztesi Lepes Eletciklusa

```
1. PLAN        Lepes megtervezese, erintett komponensek azonositasa
2. IMPLEMENT   Kod megirasa
3. NEW TESTS   Uj tesztek irasa az uj/valtoztatott funkcionalitasra
4. LOCAL RUN   Lokalis tesztfuttatas (uj + regresszio)
5. COMMIT      Commit (csak ha lokalis tesztek ZOLDEK)
6. CI GATE     CI pipeline: lint + TELJES regresszio + coverage
7. REVIEW      Code review (teszt coverage ellenorzese is!)
8. MERGE       Merge main-re (csak ha CI ZOLD + review APPROVED)
9. RECORD      Fejlesztesi lepes rogzitese a nyilvantartasba
```

**FONTOS:** A 4. lepes (LOCAL RUN) NEM opcionalis. Claude Code MINDIG futtassa
a lokalis regressziot fejlesztes utan, MIELOTT commitolna.

---

## 2. TESZT REGISTRY (Kozponti Nyilvantartas)

### 2.1 Miert Kell Registry?

50+ modullal, 6+ skill-lel, 1000+ teszt esettel a kovetkezo kerdesekre kell valasz:
- Melyik teszt melyik komponenst fedi le?
- Ha `engine/dag.py` valtozik, mely teszteket KELL futtatni?
- Mikor futott utoljara a `test_quality_gate.py` es mi volt az eredmenye?
- Van-e lefedetlen funkcionalitas?
- Melyik teszt a leglassabb/legdragabb?

### 2.2 Test Registry Struktura (Fajl-alapu + DB-backed)

Minden teszt fajl **fejleccel** rendelkezik:

```python
# tests/unit/engine/test_dag.py
"""
@test_registry:
    suite: engine-unit
    component: engine.dag
    covers:
        - src/aiflow/engine/dag.py
        - src/aiflow/engine/conditions.py
    phase: 2
    priority: critical
    estimated_duration_ms: 500
    requires_services: []
    tags: [dag, topological-sort, validation]
"""
import pytest
# ... tesztek ...
```

**A registry metaadatok:**

| Mezo | Tipus | Celj |
|------|-------|------|
| suite | str | Teszt suite neve (regresszios csoportositas) |
| component | str | Melyik komponenst teszteli (dotted path) |
| covers | list[str] | Mely forrasfajlokat fedi le |
| phase | int | Melyik fazisban keszult (1-7) |
| priority | enum | critical / high / medium / low |
| estimated_duration_ms | int | Becsult futasi ido |
| requires_services | list | Docker szolgaltatasok (postgres, redis, langfuse) |
| tags | list[str] | Szabad cimkek |

### 2.3 Test Suite Definiciok

```yaml
# tests/test_suites.yaml
suites:
  # === FRAMEWORK SUITES ===
  core-unit:
    description: "Core kernel unit tesztek"
    path: "tests/unit/core/"
    run_on: [commit, pr, merge]
    max_duration_seconds: 30
    coverage_target: 95
    components: [core.config, core.context, core.errors, core.events, core.registry, core.di]

  engine-unit:
    description: "Workflow engine unit tesztek"
    path: "tests/unit/engine/"
    run_on: [commit, pr, merge]
    max_duration_seconds: 60
    coverage_target: 90
    components: [engine.step, engine.dag, engine.workflow, engine.runner, engine.policies, engine.checkpoint]

  models-unit:
    description: "Model client unit tesztek"
    path: "tests/unit/models/"
    run_on: [pr, merge]
    max_duration_seconds: 30
    coverage_target: 85
    components: [models.client, models.registry, models.router]

  prompts-unit:
    description: "Prompt platform unit tesztek"
    path: "tests/unit/prompts/"
    run_on: [pr, merge]
    max_duration_seconds: 20
    coverage_target: 85
    components: [prompts.manager, prompts.sync, prompts.ab_testing]

  security-unit:
    description: "Security unit tesztek"
    path: "tests/unit/security/"
    run_on: [commit, pr, merge]
    max_duration_seconds: 20
    coverage_target: 95
    components: [security.auth, security.rbac, security.guardrails]

  vectorstore-unit:
    description: "VectorStore unit tesztek"
    path: "tests/unit/vectorstore/"
    run_on: [pr, merge]
    max_duration_seconds: 30
    coverage_target: 80
    components: [vectorstore.pgvector, vectorstore.search, vectorstore.embedder]

  integration-api:
    description: "API integracios tesztek"
    path: "tests/integration/test_api.py"
    run_on: [pr, merge]
    max_duration_seconds: 120
    requires_services: [postgres, redis]
    components: [api.*]

  integration-queue:
    description: "Queue integracios tesztek"
    path: "tests/integration/test_queue.py"
    run_on: [pr, merge]
    max_duration_seconds: 60
    requires_services: [redis]
    components: [execution.queue, execution.worker, execution.dlq]

  integration-state:
    description: "State store integracios tesztek"
    path: "tests/integration/test_state_store.py"
    run_on: [pr, merge]
    max_duration_seconds: 60
    requires_services: [postgres]
    components: [state.*]

  integration-vectorstore:
    description: "VectorStore integracios tesztek"
    path: "tests/integration/test_vectorstore.py"
    run_on: [pr, merge]
    max_duration_seconds: 90
    requires_services: [postgres]
    components: [vectorstore.*, documents.*, ingestion.*]

  e2e-pipeline:
    description: "Teljes pipeline E2E tesztek"
    path: "tests/e2e/"
    run_on: [merge, deploy]
    max_duration_seconds: 300
    requires_services: [postgres, redis, langfuse]
    components: ["*"]

  ui-playwright:
    description: "Frontend GUI tesztek"
    path: "tests/ui/"
    run_on: [merge, deploy]
    max_duration_seconds: 180
    requires_services: [postgres, redis]
    components: [ui.*]

  # === SKILL SUITES ===
  skill-process-doc:
    description: "Process Documentation skill tesztek"
    path: "skills/process_documentation/tests/"
    run_on: [pr, merge]
    max_duration_seconds: 120
    skill: process_documentation
    components: [skills.process_documentation.*]

  skill-aszf-rag:
    description: "ASZF RAG Chat skill tesztek"
    path: "skills/aszf_rag_chat/tests/"
    run_on: [pr, merge]
    max_duration_seconds: 180
    skill: aszf_rag_chat
    requires_services: [postgres]
    components: [skills.aszf_rag_chat.*]

  skill-email-intent:
    description: "Email Intent skill tesztek"
    path: "skills/email_intent_processor/tests/"
    run_on: [pr, merge]
    max_duration_seconds: 120
    skill: email_intent_processor
    components: [skills.email_intent_processor.*]

  skill-cubix:
    description: "Cubix Course Capture skill tesztek"
    path: "skills/cubix_course_capture/tests/"
    run_on: [pr, merge]
    max_duration_seconds: 120
    skill: cubix_course_capture
    requires_services: [postgres]
    components: [skills.cubix_course_capture.*]

  skill-qbpp:
    description: "QBPP Test Automation skill tesztek"
    path: "skills/qbpp_test_automation/tests/"
    run_on: [pr, merge]
    max_duration_seconds: 120
    skill: qbpp_test_automation
    components: [skills.qbpp_test_automation.*]

  # === PROMPT SUITES ===
  promptfoo-all:
    description: "Osszes skill Promptfoo tesztek"
    path: "skills/*/tests/promptfooconfig.yaml"
    run_on: [pr, merge]
    max_duration_seconds: 600
    requires_services: [langfuse]
    cost_usd_estimated: 2.00
    components: [prompts.*]
```

---

## 3. REGRESSZIOS MATRIX

### 3.1 Valtozas -> Erintett Suite-ok Mapping

Ha egy forrasfajl valtozik, a regression matrix megmondja mely suite-okat KELL futtatni:

```yaml
# tests/regression_matrix.yaml
#
# Minta: ha <path_pattern> valtozik -> ezeket a suite-okat futtasd
# "FULL" = minden suite (teljes regresszio)

rules:
  # --- CORE ---
  "src/aiflow/core/**":
    suites: FULL
    reason: "Core kernel valtozas MINDEN komponenst erint"

  "src/aiflow/core/config.py":
    suites: FULL
    reason: "Config valtozas MINDENT erinthet"

  # --- ENGINE ---
  "src/aiflow/engine/step.py":
    suites: [engine-unit, integration-api, e2e-pipeline,
             skill-process-doc, skill-aszf-rag, skill-email-intent,
             skill-cubix, skill-qbpp]
    reason: "Step decorator MINDEN workflow-t es skill-t erint"

  "src/aiflow/engine/dag.py":
    suites: [engine-unit, integration-api, e2e-pipeline]

  "src/aiflow/engine/runner.py":
    suites: [engine-unit, integration-api, integration-queue, e2e-pipeline]

  "src/aiflow/engine/policies.py":
    suites: [engine-unit, integration-api]

  # --- SKILL SYSTEM ---
  "src/aiflow/skill_system/**":
    suites: [skills-unit, integration-api, e2e-pipeline,
             skill-process-doc, skill-aszf-rag, skill-email-intent]

  # --- TOOLS ---
  "src/aiflow/tools/**":
    suites: [skills-unit, integration-api, e2e-pipeline]

  # --- MODELS ---
  "src/aiflow/models/**":
    suites: [models-unit, integration-api, e2e-pipeline, promptfoo-all,
             skill-process-doc, skill-aszf-rag, skill-email-intent]

  # --- PROMPTS ---
  "src/aiflow/prompts/**":
    suites: [prompts-unit, integration-api, promptfoo-all]

  # --- API ---
  "src/aiflow/api/**":
    suites: [integration-api, e2e-pipeline, ui-playwright]

  # --- SECURITY ---
  "src/aiflow/security/**":
    suites: FULL
    reason: "Security valtozas MINDENT erinthet"

  # --- EXECUTION ---
  "src/aiflow/execution/**":
    suites: [integration-queue, integration-api, e2e-pipeline]

  # --- STATE ---
  "src/aiflow/state/**":
    suites: [integration-state, integration-api, e2e-pipeline]

  # --- VECTORSTORE ---
  "src/aiflow/vectorstore/**":
    suites: [vectorstore-unit, integration-vectorstore, skill-aszf-rag]

  # --- DOCUMENTS / INGESTION ---
  "src/aiflow/documents/**":
    suites: [integration-vectorstore, skill-aszf-rag]
  "src/aiflow/ingestion/**":
    suites: [integration-vectorstore, skill-aszf-rag]

  # --- UI ---
  "src/aiflow/ui/**":
    suites: [ui-playwright]

  # --- SKILLS ---
  "skills/process_documentation/**":
    suites: [skill-process-doc, promptfoo-all]
  "skills/aszf_rag_chat/**":
    suites: [skill-aszf-rag, promptfoo-all]
  "skills/email_intent_processor/**":
    suites: [skill-email-intent, promptfoo-all]
  "skills/cubix_course_capture/**":
    suites: [skill-cubix]
  "skills/qbpp_test_automation/**":
    suites: [skill-qbpp]

  # --- PROMPTS (skill-specifikus) ---
  "skills/*/prompts/**":
    suites: [promptfoo-all]

  # --- CONFIG / INFRA ---
  "pyproject.toml":
    suites: FULL
    reason: "Fuggoseg valtozas MINDENT erinthet"
  "docker-compose*.yml":
    suites: [integration-state, integration-queue, integration-vectorstore, e2e-pipeline]
  "alembic/**":
    suites: [integration-state, integration-vectorstore]
  "k8s/**":
    suites: [e2e-pipeline]
```

### 3.2 Regresszio Futtatasi Szintek

| Szint | Mikor | Mit futtat | Ido | Koltseg |
|-------|-------|-----------|-----|---------|
| **L1: Quick** | Minden commit | Erintett unit suites | <60 mp | $0 |
| **L2: Standard** | Minden PR | L1 + erintett integration + erintett skill | 2-5 perc | ~$0.10 |
| **L3: Full** | Merge to main | MINDEN suite (unit + integration + skill + promptfoo) | 10-20 perc | ~$2.00 |
| **L4: Complete** | Deploy staging | L3 + E2E + UI Playwright | 20-40 perc | ~$3.00 |
| **L5: Release** | Deploy prod | L4 + performance benchmark + security scan | 30-60 perc | ~$5.00 |

---

## 4. GATE POLICY (Kapuk)

### 4.1 Merge Gate (PR -> main)

```yaml
# .github/workflows/regression-gate.yml koncepcioja
merge_requirements:
  mandatory:
    - all_new_tests_pass: true
    - all_regression_suites_pass: true      # Regression matrix alapjan
    - no_new_test_failures: true            # Semmi regresszio
    - coverage_not_decreased: true          # Coverage nem csokkenhet
    - coverage_minimum_met: true            # 80% globalis minimum
    - lint_pass: true                       # ruff + black + mypy
    - security_scan_pass: true              # detect-secrets
  conditional:
    - promptfoo_pass: true                  # Ha prompt valtozas volt
    - ui_tests_pass: true                   # Ha UI valtozas volt
  informational:
    - performance_regression: warn          # Lassulast jelezzuk de nem blokkoljuk
    - cost_increase: warn                   # Koltseg novekedes figyelmeztes
```

### 4.2 Coverage Gate Reszletek

| Terulet | Minimum | Cel | Blokkolo? |
|---------|---------|-----|-----------|
| src/aiflow/core/ | 90% | 95% | IGEN |
| src/aiflow/engine/ | 85% | 90% | IGEN |
| src/aiflow/agents/ | 80% | 85% | IGEN |
| src/aiflow/api/ | 80% | 90% | IGEN |
| src/aiflow/security/ | 90% | 95% | IGEN |
| src/aiflow/models/ | 80% | 85% | IGEN |
| src/aiflow/vectorstore/ | 75% | 80% | IGEN |
| skills/*/agents/ | 70% | 80% | IGEN |
| **Osszes** | **80%** | **85%** | **IGEN** |

**Szabaly:** Coverage NEM csokkenhet egy PR-ben. Ha uj kod kerul be, annak
teszttel kell LEGALABB az adott modul minimalis coverage szintjet tartania.

### 4.3 Uj Teszt Kovetelmeny

| Valtozas tipusa | Minimum uj tesztek |
|-----------------|-------------------|
| Uj modul (*.py) | Min 5 unit teszt |
| Uj endpoint | Min 3 API teszt (success, auth fail, validation) |
| Uj step | Min 3 teszt (happy path, error, edge case) |
| Uj agent | Min 5 teszt (execute, quality gate, timeout, invalid input, edge case) |
| Uj prompt YAML | Min 10 Promptfoo teszt eset |
| Uj skill | Min 100 teszt eset (lasd 18_TESTING) |
| Bug fix | Min 1 reprodukalo regresszios teszt |
| Refactoring | 0 uj teszt DE minden meglevo MUST pass |

---

## 5. TESZT ARTEFAKTUM MEGORZESEK

### 5.1 Mit Orizunk Meg?

Minden regresszios futtas az alabbi artefaktumokat menti:

```
tests/artifacts/
    {YYYY-MM-DD}/
        {run_id}/
            summary.json              # Osszefoglalo (pass/fail/skip szamok, ido, koltseg)
            junit.xml                 # JUnit XML riport (CI tools szamara)
            coverage.xml              # Coverage riport
            coverage_html/            # HTML coverage riport
            failed_tests.json         # Bukott tesztek reszletei
            regression_diff.json      # Mi valtozott az elozo futashoz kepest
            screenshots/              # Playwright screenshot-ok (ha UI teszt)
            traces/                   # Playwright trace fajlok (ha UI teszt)
            promptfoo_results/        # Promptfoo eredmenyek (ha prompt teszt)
            logs/                     # structlog output a futasbol
```

### 5.2 Retention Policy

| Artefaktum | Megorzesi ido | Tarolasi hely |
|------------|--------------|---------------|
| summary.json | Vegtelen | PostgreSQL (test_results) |
| junit.xml | 90 nap | Fajlrendszer / S3 |
| coverage riportok | 30 nap | Fajlrendszer / S3 |
| failed_tests.json | 180 nap | PostgreSQL + fajlrendszer |
| regression_diff.json | 180 nap | PostgreSQL |
| screenshots | 30 nap | S3 |
| Playwright traces | 14 nap | S3 |
| Promptfoo eredmenyek | Vegtelen | PostgreSQL |
| Logok | 30 nap | ELK / Loki |

### 5.3 Regression Diff Format

Minden futtas osszehasonlitja az eredmenyt az elozo futtatassal:

```json
{
  "run_id": "reg-2026-03-28-001",
  "previous_run_id": "reg-2026-03-27-042",
  "trigger": "PR #145 merge to main",
  "summary": {
    "total": 847,
    "passed": 842,
    "failed": 3,
    "skipped": 2,
    "new_tests": 8,
    "removed_tests": 0
  },
  "regressions": [
    {
      "test": "tests/unit/engine/test_runner.py::test_budget_enforcement",
      "previous_status": "passed",
      "current_status": "failed",
      "error": "AssertionError: expected budget_remaining=5.0, got 4.998",
      "component": "engine.runner",
      "severity": "high",
      "introduced_by": "commit abc1234"
    }
  ],
  "new_passes": [],
  "flaky_tests": [
    {
      "test": "tests/integration/test_queue.py::test_concurrent_workers",
      "flaky_count_last_10": 2,
      "action": "investigate"
    }
  ],
  "performance_changes": [
    {
      "suite": "engine-unit",
      "previous_duration_ms": 12400,
      "current_duration_ms": 13800,
      "change_pct": 11.3,
      "action": "warn"
    }
  ]
}
```

---

## 6. FEJLESZTESI LEPES NYILVANTARTAS

### 6.1 Development Step Record

Minden fejlesztesi lepes rogzitve van, a hozza tartozo teszt eredmenyekkel:

```json
{
  "step_id": "DS-2026-0328-003",
  "date": "2026-03-28",
  "phase": 2,
  "developer": "kassai.attila",
  "ai_assisted": true,
  "type": "feature",
  "title": "Add RetryPolicy with exponential backoff and jitter",
  "description": "LangGraph-inspired retry policy implementation",
  "files_changed": [
    "src/aiflow/engine/policies.py",
    "tests/unit/engine/test_policies.py"
  ],
  "commit": "abc1234",
  "pr": "#42",
  "branch": "feature/AIFLOW-42-retry-policy",
  "tests": {
    "new_tests_added": 12,
    "new_test_files": ["tests/unit/engine/test_policies.py"],
    "regression_level": "L2",
    "regression_run_id": "reg-2026-03-28-003",
    "regression_result": "ALL_PASS",
    "total_tests_run": 234,
    "passed": 234,
    "failed": 0,
    "coverage_before": 82.1,
    "coverage_after": 83.4,
    "duration_seconds": 145
  },
  "review": {
    "reviewer": "framework-team",
    "approved_at": "2026-03-28T15:30:00Z"
  }
}
```

### 6.2 Heti Regresszios Riport

Minden hetfo reggel automatikusan generalodik:

```
=== AIFlow Heti Regresszios Riport - Het 12 (2026-03-23 -- 2026-03-28) ===

Fejlesztesi lepesek: 14
Osszes regresszios futtas: 38
Osszes teszt vegrehajtás: 14,230 (38 futtas * ~375 atlag)
Bukott regressziok: 2 (mindketto javitva 24 oran belul)

Uj tesztek hozzaadva: +67
Torolt tesztek: -3 (deprecated API)
Osszes aktiv teszt: 847

Coverage trend:
  core/     95.2% (+0.3%)
  engine/   88.7% (+1.2%)
  agents/   83.4% (valtozatlan)
  api/      81.2% (+2.1%)
  OSSZES    82.8% (+0.9%)

Flaky tesztek (3+/10 futasbol bukott):
  - test_concurrent_workers: 3/10 -> VIZSGALANDO

Leglassabb suite-ok:
  - promptfoo-all: 342s (cel: <600s) OK
  - e2e-pipeline: 287s (cel: <300s) FIGYELEM

LLM teszt koltseg (het): $14.20
```

---

## 7. CLAUDE CODE TESZTELESI PROTOKOLL

### 7.1 Kotelezo Lepesek Minden Fejlesztes Utan

```
Claude Code fejlesztesi ciklus:

1. KOD IRAS
   - Uj funkcionalitas implementalasa

2. TESZTEK IRASA (AZONNAL, NEM KESOBB!)
   - Unit tesztek a megirt kodhoz
   - @test_registry fejlec kitoltese
   - Edge case-ek es hibakezeles tesztelese

3. LOKALIS TESZTFUTTAS
   a) Uj tesztek futtatasa:
      pytest tests/unit/engine/test_new_feature.py -v

   b) Erintett suite-ok futtatasa (regression_matrix alapjan):
      pytest tests/unit/engine/ -v
      pytest tests/integration/test_api.py -v

   c) Coverage ellenorzes:
      pytest tests/unit/ --cov=aiflow --cov-report=term-missing

4. EREDMENY ERTEKELES
   - MINDEN teszt ZOLD? -> folytat a commit-tal
   - Barmelyik PIROS? -> ELOSZOR javitani, AZTAN commitolni
   - Coverage csokent? -> Tobb tesztet irni

5. COMMIT
   - Csak ZOLD tesztek eseten
   - Commit message-ben: "Tests: X new, Y regression pass"
```

### 7.2 Claude Code TILOS Listaja

| Tiltas | Indoklas |
|--------|----------|
| Commitolas bukott teszttel | Soha, semmilyen korulmenyek kozott |
| Teszt kikommentalasa | Inkabb javitsd a kodot |
| `@pytest.mark.skip` uj tesztre | Csak ideiglenesen, JIRA ticket-tel |
| `# type: ignore` teszyben | Soha |
| Mock MINDEN-t | Integracios teszt valos DB-vel KELL |
| Teszt irasa commit UTAN | Mindig ELOTTE |
| Coverage csokkentes | Soha nem megengedett |
| Regresszio kihagyasa | Soha, meg "gyors fix" eseten sem |

---

## 8. FLAKY TEST KEZELES

### 8.1 Definicio

Flaky teszt = ugyanaz a teszt kulonbozo futasokban kulonbozo eredmenyt ad
(neha pass, neha fail) anelkul hogy a kod valtozott volna.

### 8.2 Flaky Test Policy

```
1. DETEKTALAS: Ha egy teszt 3x bukik 10 futtasbol -> flaky cimke
2. KARANTEN: Flaky teszt kulon suite-ba kerul: "quarantine"
3. VIZSGALAT: Max 5 munkanap alatt ki kell vizsgalni
4. JAVITAS: Root cause fix (timing, resource, ordering)
5. VISSZAHELYEZES: Javitas utan 10 sikeres futtas -> visszakerul

FONTOS: Flaky teszt NEM torolheto! Vagy javitjuk, vagy lecsereljuk stabilra.
A karanten suite-ok FUTNAK, de NEM blokkolnak merge-ot.
```

### 8.3 Flaky Test DB Tracking

```sql
CREATE TABLE flaky_test_tracking (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_path VARCHAR(500) NOT NULL,
    suite_name VARCHAR(255) NOT NULL,
    first_detected_at TIMESTAMPTZ NOT NULL,
    flaky_count INT DEFAULT 0,
    total_runs INT DEFAULT 0,
    status VARCHAR(20) DEFAULT 'detected',  -- detected, investigating, fixing, resolved
    root_cause TEXT,
    fix_commit VARCHAR(40),
    assigned_to VARCHAR(255),
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 9. SKILL FEJLESZTES TESZTELESI KOVETELMENYEI

### 9.1 Uj Skill Minimum Teszt Kovetelmeny

| Kategoria | Min. tesztszam | Arany |
|-----------|---------------|-------|
| Pozitiv (helyes kimenet) | 40 | 40% |
| Negativ (elutasitando) | 20 | 20% |
| Edge case (hatar) | 20 | 20% |
| Adversarial (tamadas) | 10 | 10% |
| Multi-language | 10 | 10% |
| **OSSZES** | **100** | **100%** |

### 9.2 Skill Regresszio

Skill fejlesztes soran a regresszio KET szinten tortenik:

1. **Skill-szintu regresszio:** A skill OSSZES sajat tesztje
2. **Framework regresszio:** Ha a skill framework API-t hasznal,
   a framework tesztek is futnak

### 9.3 Prompt Valtozas Regresszio

Prompt YAML modositasa utan:
1. Promptfoo tesztek (skill-specifikus)
2. Ha a prompt TOBBI skill-ben is hasznalt -> azok Promptfoo-ja is fut
3. A/B teszt eredmenyek ellenorzese (ha van aktiv experiment)

---

## 10. CI/CD REGRESSZIOS PIPELINE

### 10.1 Pipeline Logika (Pszeudokod)

```python
# .github/workflows/regression.yml logikaja

def on_pull_request(changed_files):
    # 1. Melyik suite-ok erintettek?
    affected_suites = resolve_regression_matrix(changed_files)

    # 2. Ha FULL regresszio kell (core, security, pyproject.toml)
    if "FULL" in affected_suites:
        affected_suites = ALL_SUITES

    # 3. Suite-ok futtatasa prioritas szerint
    results = []
    # Eloszor: critical suite-ok (parhuzamosan)
    results += run_parallel([s for s in affected_suites if s.priority == "critical"])
    # Ha barmi bukott -> STOP, nem futtatjuk a tobbit
    if any_failed(results):
        report_failure(results)
        return BLOCKED

    # Aztan: high + medium (parhuzamosan)
    results += run_parallel([s for s in affected_suites if s.priority in ("high", "medium")])
    if any_failed(results):
        report_failure(results)
        return BLOCKED

    # Vegul: low priority
    results += run_parallel([s for s in affected_suites if s.priority == "low"])

    # 4. Coverage ellenorzes
    coverage = measure_coverage()
    if coverage.decreased():
        return BLOCKED

    # 5. Regresszios diff generalas
    diff = compare_with_previous_run(results)
    save_regression_diff(diff)

    # 6. Eredmeny
    if all_passed(results):
        return APPROVED
    else:
        return BLOCKED
```

### 10.2 GitHub Actions Implementation

```yaml
# .github/workflows/regression-gate.yml
name: Regression Gate
on:
  pull_request:
    branches: [main]

jobs:
  detect-changes:
    runs-on: ubuntu-latest
    outputs:
      suites: ${{ steps.matrix.outputs.suites }}
      is_full: ${{ steps.matrix.outputs.is_full }}
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - id: matrix
        run: python scripts/resolve_regression_matrix.py

  regression:
    needs: detect-changes
    runs-on: ubuntu-latest
    strategy:
      fail-fast: true  # Elso bukas utan STOP
      matrix:
        suite: ${{ fromJson(needs.detect-changes.outputs.suites) }}
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env: { POSTGRES_DB: aiflow_test, POSTGRES_PASSWORD: test }
        ports: ['5432:5432']
      redis:
        image: redis:7-alpine
        ports: ['6379:6379']
    steps:
      - uses: actions/checkout@v4
      - run: pip install -e ".[dev,vectorstore]"
      - run: python scripts/run_suite.py ${{ matrix.suite }}
      - run: python scripts/check_coverage_gate.py
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: test-artifacts-${{ matrix.suite }}
          path: tests/artifacts/

  regression-report:
    needs: regression
    if: always()
    runs-on: ubuntu-latest
    steps:
      - run: python scripts/generate_regression_diff.py
      - run: python scripts/save_regression_record.py
```

---

## 11. HOSSZU TAVU FENNTARTHATOSAG

### 11.1 Teszt Karbantartas

| Feladat | Gyakorisag | Ki |
|---------|-----------|-----|
| Flaky teszt vizsgalat | Heti | Framework team |
| Teszt suite ido optimalizacio | 2 hetente | Framework team |
| Coverage riport attekintes | Heti | Team leads |
| Elavult teszt torles | Havonta | Skill teams |
| Teszt adatbazis cleanup | Havonta | DevOps |
| Regression matrix frissites | Uj modul/skill hozzaadasakor | Fejleszto |
| Promptfoo teszt eset bovites | Folyamatosan | Skill teams |
| Performance baseline frissites | Negyedevente | Framework team |

### 11.2 Teszt Metrikak Dashboard

| Metrika | Cel | Alert ha |
|---------|-----|----------|
| Osszes teszt szam | Monoton novekvo | Csokken (teszt torolve?) |
| Globalis pass rate | >99% | <98% |
| Regressziok szama/het | <3 | >5 |
| Atlagos regresszio javitasi ido | <24 ora | >48 ora |
| Flaky tesztek szama | <5 | >10 |
| Coverage (osszes) | >82% | <80% |
| CI pipeline ido (L3 Full) | <20 perc | >30 perc |
| Heti LLM teszt koltseg | <$20 | >$30 |

### 11.3 Skalazasi Terv

| Merfokobol | Teszt szam | Strategia |
|-----------|-----------|-----------|
| Phase 1-3 | ~200 | Minden fut mindig |
| Phase 4-5 | ~800 | Regression matrix alapu szelektiv |
| Phase 6-7 | ~1500 | Parhuzamos CI (matrix strategy) |
| 10 skill | ~3000 | Skill-izolalt pipeline + framework smoke |
| 50 skill | ~10000 | Erintett skill-ek only + nightly full |
| 100+ skill | ~30000+ | Distributed test runner + test sharding |

---

## 12. IMPLEMENTACIOS UTMUTATO

### Phase 1 Tesztelesi Kovetelmeny (Het 1-3)

```
Letrehozando:
  tests/conftest.py                    # Kozos fixtures
  tests/test_suites.yaml               # Suite definiciok (elso 3 suite)
  tests/regression_matrix.yaml         # Elso szabalyok
  tests/unit/core/test_config.py       # Min 5 teszt
  tests/unit/core/test_context.py      # Min 5 teszt
  tests/unit/core/test_errors.py       # Min 3 teszt
  tests/unit/core/test_registry.py     # Min 5 teszt
  scripts/resolve_regression_matrix.py # CI helper
  scripts/run_suite.py                 # Suite futtato
  scripts/check_coverage_gate.py       # Coverage kapu

Regresszio: Phase 1 vegen ~25 teszt, L1 regresszio minden commit-on
```

### Phase 2+ Kovetelmeny

Minden phase BOVITI a test_suites.yaml-t es regression_matrix.yaml-t
az uj modulokkal. A regresszio automatikusan novekszik.

---

## 13. OSSZEFOGLALO TABLAZAT

| Szempont | Szabaly |
|----------|--------|
| Teszt irasa | KOTELEZO, MINDEN uj kodhoz, AZONNAL (nem utólag) |
| Regresszio | KOTELEZO, MINDEN PR-nal, matrix alapjan |
| Coverage | NEM CSOKKENHET, modul-szintu minimumok |
| Flaky tesztek | Karanten + max 5 nap javitas |
| Artefaktumok | Mentve, retention policy szerint |
| Nyilvantartas | DB-ben, heti riport |
| CI gate | Blokkolo - nincs merge bukott teszttel |
| Claude Code | Lokalis regresszio futtatása KÖTELEZO commit elott |
| Skill tesztek | Min 100 eset, 90%+ pass rate |
| Prompt tesztek | Promptfoo, minden valtozas utan |
| Eletciklus | VEGTELEN - folyamatos karbantartas |
