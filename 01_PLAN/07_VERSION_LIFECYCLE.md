# AIFlow - Verzikezeles es Eletciklus

## 1. Verzikezeles Strategia

### 1.1 Framework vs Skill Fuggetlen Verziozas

```
aiflow (framework)          skills/process_doc...    skills/invoice_proc...
    v1.0.0                     v2.0.0                   v1.0.0
    v1.1.0                     v2.1.0                   v1.1.0
    v1.2.0                     v2.1.1                   v1.1.1
    v2.0.0 (BREAKING)          v3.0.0 (adaptalva)       v2.0.0 (adaptalva)
```

**Framework** (src/aiflow/):
- MAJOR: Breaking API (Step decorator, BaseWorkflow, SpecialistAgent, ExecutionContext)
- MINOR: Uj feature-ok, backward compat
- PATCH: Bugfix, nincs API valtozas

**Skill** (skills/<name>/):
- MAJOR: Mas DAG struktura, inkompatibilis output schema
- MINOR: Uj lepes, uj prompt variant
- PATCH: Prompt finomhangolas, teszt bovites

### 1.2 Fuggoseg Megkotozese

```yaml
# skills/process_documentation/skill.yaml
name: process_documentation
version: "2.1.0"
framework_requires: ">=1.0.0,<2.0.0"  # Kompatibilis barmelyik 1.x-szel
```

A `aiflow skill install` validalja a framework_requires constraint-et.
Ha a telepitett framework 1.3.0 es a skill-nek `>=2.0.0` kell -> hiba.

### 1.3 Framework Upgrade 50+ Skill Eseten

**MINOR verzio (1.1 -> 1.2):** Semmi nem torik. Skill-ek valtozatlanul mukodnek.

**MAJOR verzio (1.x -> 2.0):**

1. **Deprecation window:** Framework 1.9.0-ban `DeprecationWarning` az elavult API-kra
2. **Compatibility shim:** `aiflow.engine.compat` modul az atmeneti idoszakra
3. **Automatikus migracio:** `aiflow skill migrate --to 2.0.0` (AST transzformacio libcst-vel)
4. **Fokozatos bevezetes:** Monorepo-ban egyetlen branch frissiti a framework + osszes skill-t

### 1.4 Prompt Verziozas Illesztese

```
Langfuse Prompt: process-doc/classifier
    |-- version 4 (label: prod)       <- Produkcioban aktiv
    |-- version 5 (label: staging)    <- UAT-ban tesztelve
    |-- version 6 (label: dev)        <- Fejlesztes alatt
```

Skill manifest deklaralja a validalt prompt verziokat:

```yaml
prompts:
  - name: process-doc/classifier
    langfuse_version: 5
    min_langfuse_version: 4
```

**Uj DB tabla:**

```sql
CREATE TABLE skill_prompt_versions (
    skill_name VARCHAR(255) NOT NULL,
    skill_version VARCHAR(50) NOT NULL,
    prompt_name VARCHAR(255) NOT NULL,
    langfuse_version INT NOT NULL,
    validated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (skill_name, skill_version, prompt_name)
);
```

---

## 2. Framework vs Skill Fejlesztes Szetvlasztasa

### 2.1 Monorepo Strategia

```
aiflow/
    src/aiflow/          # Framework (framework-team CODEOWNERS)
    skills/
        process_documentation/   # Skill team A
        invoice_processing/      # Skill team B
        contract_review/         # Skill team C
```

**Miert monorepo?**
- Atomikus commit-ok framework + skill valtozasokra
- Kozos CI/CD infrastruktura
- Nincs verzio drift

**Kulso skill-ek:** Sajat repo-ban, `pip install aiflow>=1.0.0,<2.0.0`

### 2.2 Skill Team Izolacioja

Egy skill team fejlesztesi ciklusa:

1. **Csak a skills/<nev>/ mappaban dolgoznak** - Soha nem editaljak src/aiflow/
2. **Framework public API-t importalnak:**
   ```python
   from aiflow.engine import step, workflow
   from aiflow.engine.skill_runner import SkillRunner
   from aiflow.prompts import PromptManager
   ```
3. **Sajat skill tesztjeiket futtatjak:** `aiflow eval run --skill <name>`
4. **PR-juk skill-specifikus CI pipeline-on megy at** (lasd 4.2)

### 2.3 Public API Surface (Szerzodes)

`src/aiflow/__init__.py` az explicit szerzodes:

```python
# Csak ezek az exportok stabilak skill-ek szamara
from aiflow.engine.step import step
from aiflow.engine.workflow import workflow
from aiflow.engine.skill_runner import SkillRunner
from aiflow.core.context import ExecutionContext
from aiflow.core.errors import AIFlowError
from aiflow.models.client import ModelClient
from aiflow.prompts.manager import PromptManager
```

| Stabilitasi szint | Jelentes | API-k |
|-------------------|----------|-------|
| **Stable** | Semver kovetkezetesen. Torese csak MAJOR-ban. | @step, @workflow, SpecialistAgent, ExecutionContext |
| **Beta** | Valtozhat MINOR-ban deprecation warning-gel | ABTest, HumanReviewRequest, Scheduler |
| **Internal** | Barmikar valtozhat. Skill-ek NE hasznaljak. | DAG, WorkflowRunner, StateRepository |

### 2.4 .github/CODEOWNERS

```
/src/aiflow/                        @bestixcom/framework-team
/skills/process_documentation/      @bestixcom/process-doc-team
/skills/invoice_processing/         @bestixcom/invoice-team
/k8s/                               @bestixcom/devops-team
/.github/                           @bestixcom/devops-team
```

---

## 3. DEV-TEST-UAT-PROD Eletciklus

### 3.1 Kornyezeti Izolacio

| Eroforras | DEV | TEST | UAT | PROD |
|-----------|-----|------|-----|------|
| PostgreSQL | aiflow_dev (local Docker) | aiflow_test (CI) | aiflow_uat (shared staging) | aiflow_prod (managed) |
| Redis | localhost:6379/0 | ci-redis:6379/1 | staging-redis:6379/0 | prod-redis:6379/0 |
| Redis prefix | aiflow:dev: | aiflow:test: | aiflow:uat: | aiflow:prod: |
| Langfuse label | dev | test | staging | prod |
| API URL | localhost:8000 | CI container | staging.aiflow.internal | aiflow.company.com |
| Config | .env fajl | CI secrets | K8s ConfigMap + Vault | K8s ConfigMap + Vault |

### 3.2 Promociós Ut

```
DEV (fejleszto laptop / feature branch)
  |  PR merge -> main automatikusan triggereli -->
TEST (CI pipeline, automatikus kapuk)
  |  Manualis jovahagyas -->
UAT (staging kornyezet, stakeholder validacio)
  |  Release jovahagyas -->
PROD (production deployment)
```

### 3.3 Prompt Promócio (Kodtol Fuggetlen!)

Prompt-ok fuggetlen eletciklussal birnak - nem kell uj Docker image:

```bash
# 1. Fejleszto szerkeszti a YAML-t, sync-eli Langfuse-ba
aiflow prompt sync --label dev

# 2. CI/CD Promptfoo tesztek futnak
aiflow prompt test --label test

# 3. UAT-ba prommocio
aiflow prompt promote --from test --to staging

# 4. Produkcioba prompcio (jovahagyas utan)
aiflow prompt promote --from staging --to prod

# 5. Rollback ha szukseges
aiflow prompt rollback --name process-doc/classifier --to-version 4 --label prod
```

**Miert jo?** A prompt frissites percek alatt produkcioban van, nincs build/deploy.

### 3.4 Prompt Parhuzamos Szerkesztes Kezelese

**Elv:** Git a single source of truth. Langfuse sync egyiranyu (Git -> Langfuse).

**Konfliktus megoldas:**
1. Ket fejleszto modositja ugyanazt a prompt YAML-t -> Git merge conflict
2. CODEOWNERS: prompt konyvtarak review-t igenyelnek a skill team-tol
3. CI gate: `aiflow prompt sync --check` ellenorzi hogy Langfuse sync-ben van Git-tel
4. Label promociok (staging->prod) kizarolag CI/CD pipeline-bol, nem kezzel

**Vedelem:** Langfuse-ban direkt szerkesztes TILTOTT production label-ekre.
Csak a sync pipeline irhat prod label-re.

### 3.5 Rollback Strategia

| Mit | Hogyan | Ido |
|-----|--------|-----|
| Skill | K8s deployment rollback elozo image tag-re | ~2 perc |
| Prompt | Langfuse label atallitas elozo verziora | ~10 masodperc |
| Framework | K8s deployment rollback (skills framework_requires range-en belul) | ~2 perc |
| Database | `alembic downgrade -1` (additive migraciok, safe rollback) | ~1 perc |

### 3.6 Instance Verziokezeles

A Skill Instance-ok fuggetlen eletciklussal birnak a framework-tol es a skill template-tol:

**Instance config verziozas:**
- Az instance YAML konfiguraciok (pl. `deployments/azhu/instances/hr_aszf_chat.yaml`) Git-ben verziozottak
- Minden config valtozas PR-ben kovetett, CODEOWNERS review-vel

**Instance NEM kovet framework vagy skill verziokat:**
- A skill template (kod) frissulhet anelkul hogy az instance config valtozna
- Az instance config frissulhet (pl. uj prompt, mas collection) anelkul hogy a skill kod valtozna
- Fuggetlen deployment ciklus: instance config deploy != skill deploy

**Prompt namespace izolacio:**
- Minden instance sajat Langfuse prompt namespace-szel rendelkezik
- Pelda: `allianz/hr_aszf/` vs `allianz/legal_aszf/` vs `allianz/it_aszf/`
- Igy kulonbozo system prompt-ok, valasz stilusok hasznalhatok instance-onkent

**Instance allapot eletciklus:**
```
active -> paused -> active     (ideiglenes leallitas)
active -> disabled              (vegleg leallitva, de megmarad)
disabled -> active              (ujrainditas)
active/paused/disabled -> deleted  (torlest csak admin vegezheti)
```

---

## 4. Fejlesztesi Orchestracio

### 4.1 Git Branching

```
main                          # Mindig deployolhato. Vedett branch.
  |
  +-- feature/AIFLOW-123-...  # Framework valtozasok
  |
  +-- skill/process-doc/...   # Skill fejlesztes
  |
  +-- hotfix/...              # Production hotfix-ek
```

### 4.2 CI/CD Pipeline-ok (Path-alapu Trigger)

**Pipeline A: Framework Valtozas** (`src/aiflow/**` modosult)

```yaml
jobs:
  lint:                 # ruff + black + mypy
  unit-tests:           # pytest tests/unit/
  integration:          # pytest tests/integration/ (Docker services)
  skill-compat:         # MINDEN skill tesztjenek futtatasa!
                        # Ha barmelyik skill torik -> PR nem mergeleheto
```

**Pipeline B: Skill Valtozas** (`skills/<name>/**` modosult)

```yaml
jobs:
  detect-changed:       # Melyik skill valtozott
  lint:                 # ruff a modosult skill-en
  skill-tests:          # pytest skills/<name>/tests/ (csak a valtozott)
  promptfoo:            # Promptfoo eval (csak a valtozott)
  framework-smoke:      # pytest tests/unit/ (gyors sanity check)
```

**Pipeline C: Prompt Valtozas** (`skills/*/prompts/**` modosult)

```yaml
jobs:
  detect-changed:       # Melyik prompt valtozott
  promptfoo-eval:       # Promptfoo tesztek az erintett prompt-okra
  sync-to-langfuse:     # aiflow prompt sync --label test
```

### 4.3 Release Strategia

- **Skill-ek:** Continuous deployment (PR merge utan azonnal)
- **Framework:** Havi release train (elso hetfo)
- **Prompt-ok:** Fuggetlen, barmikor deployolhato
- **Hotfix-ek:** Mindharom eseten bypass a train-t
