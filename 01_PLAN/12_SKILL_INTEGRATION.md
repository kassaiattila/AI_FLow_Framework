# AIFlow - Skill Integracio a Keretrendszerhez

## 1. Mikor Tortenik a Skill Integracio?

```
Skill Fejlesztes Eletciklusa:

1. SCAFFOLD     aiflow skill new <name>           # Skeleton generalas
2. DEVELOP      Kodolas (agents, prompts, models)  # Fuggetlen fejlesztes
3. VALIDATE     aiflow skill validate <name>       # Manifest + schema check
4. TEST         aiflow eval run --skill <name>     # 100+ teszt eset
5. INSTALL      aiflow skill install <path>        # <-- INTEGRACIO ITT
6. DEPLOY       aiflow deploy staging/prod         # Kornyezeti deployment
```

**Az integracio a 5. lepesben tortenik:** `aiflow skill install`

---

## 2. Mi Tortenik az `aiflow skill install` Soran?

### 2.1 Teljes Installacios Folyamat

```
aiflow skill install ./skills/process_documentation

Step 1: MANIFEST VALIDACIO
  |-- skill.yaml betoltes es parse-olas
  |-- framework_requires ellenorzes (pl. ">=1.0.0,<2.0.0")
  |-- Ha a framework verzio nem felel meg -> HIBA, install megall
  |-- Kotelezo mezok ellenorzese (name, version, workflows, agents)

Step 2: FUGGOSEG ELLENORZES
  |-- required_models ellenorzes (elerheto-e a konfiguralt LLM provider?)
  |-- Python fuggosegek ellenorzese (ha a skill-nek extra pip csomagok kellenek)
  |-- Mas skill-fuggosegek (ha egy skill mas skill-re epit)
  |-- Ha barmi hianyzik -> FIGYELMEZTETES vagy HIBA

Step 3: SCHEMA VALIDACIO
  |-- Minden workflow DAG validacioja:
  |     |-- Van-e start node?
  |     |-- Elerheto-e minden node a start-bol?
  |     |-- Tipusok egyeznek-e a step inputok/outputok kozott?
  |     |-- Quality gate-ek hivatkozott metrikai leteznek-e?
  |-- Minden agent spec validacioja:
  |     |-- Van-e execute() metodus?
  |     |-- Input/output tipusok Pydantic BaseModel leszarmazottak?
  |-- Ha validacio sikertelen -> HIBA, reszletes hibauzenet

Step 4: WORKFLOW REGISZTRACIO
  |-- Workflow definiciok betoltese workflow.py-bol
  |-- DAG szerializalasa JSONB formatumba
  |-- workflow_definitions tablaba iras:
  |     INSERT INTO workflow_definitions (name, skill_id, version, dag_definition, ...)
  |-- Ha mar letezik azonos nevu workflow -> verzio ellenorzes:
  |     |-- Ujabb verzio? -> UPDATE
  |     |-- Regebbi verzio? -> FIGYELMEZTETES

Step 5: AGENT REGISZTRACIO
  |-- Agent osztalyok betoltese az agents/ mappabol
  |-- Agent spec-ek regisztracioja a belso registry-be
  |-- DI container frissitese (agent factory-k)

Step 6: PROMPT SYNC (Langfuse)
  |-- prompts/ mappa YAML fajlok felderitese
  |-- Mindegyik prompt sync-elese Langfuse-ba:
  |     |-- Nev: <skill_name>/<prompt_name> (pl. "process-doc/classifier")
  |     |-- Label: "dev" (alapertelmezett uj installaciokor)
  |     |-- Ha mar letezik Langfuse-ban -> verzio osszehasonlitas
  |-- skill_prompt_versions tabla frissitese

Step 7: TESZT FUTTATAS (opcionalis, --skip-tests kikapcsolja)
  |-- pytest skills/<name>/tests/ futtatas
  |-- Promptfoo tesztek futtatas (ha van promptfooconfig.yaml)
  |-- Eredmenyek osszefoglalasa
  |-- Ha tesztek buknak -> FIGYELMEZTETES (nem blokkolo alapertelmezetten)
  |                        --strict mod eseten -> HIBA, install megall

Step 8: SKILL REKORD MENTESE
  |-- skills tablaba iras:
  |     INSERT INTO skills (name, version, manifest, enabled, installed_at)
  |-- audit_log bejegyzes: "skill.install" action

Step 9: VISSZAJELZES
  |-- "Skill 'process_documentation' v2.0.0 successfully installed"
  |-- "Workflows registered: process-documentation"
  |-- "Prompts synced to Langfuse: 5 (label: dev)"
  |-- "Tests: 118/120 passed (98.3%)"
```

### 2.2 Install Parancs Opciok

```bash
# Alap install
aiflow skill install ./skills/process_documentation

# Tesztek nelkul (gyorsabb, fejleszteshez)
aiflow skill install ./skills/process_documentation --skip-tests

# Strict mod (tesztek MUST pass)
aiflow skill install ./skills/process_documentation --strict

# Prompt sync label megadasa
aiflow skill install ./skills/process_documentation --label staging

# Dry run (nem ir semmit, csak validalja)
aiflow skill install ./skills/process_documentation --dry-run

# Upgrade (mar telepitett skill frissitese)
aiflow skill upgrade ./skills/process_documentation

# Eltavolitas
aiflow skill uninstall process_documentation
```

---

## 3. Skill Integracio a Runtime-ban

### 3.1 Hogyan Talal Meg a Framework Egy Skill-t Futaskor?

```
API Request: POST /api/v1/workflows/process-documentation/run
  |
  +-- WorkflowRouter keresi a workflow_definitions tablaban:
  |     SELECT * FROM workflow_definitions WHERE name = 'process-documentation'
  |
  +-- Skill loader betolti a skill Python modult:
  |     from skills.process_documentation import workflow, agents
  |     (Lazy loading - csak akkor tolti be ha kell)
  |
  +-- WorkflowRunner peldanyositja a workflow-t:
  |     workflow = WorkflowBuilder.from_definition(dag_definition)
  |
  +-- Step-ek DI-val kapjak meg a fuggosegeiket:
  |     step_fn(input_data, ctx=ExecutionContext, llm=LLMClient, prompts=PromptManager)
  |
  +-- Prompt-ok Langfuse-bol tolodnek be:
  |     prompt = prompts.get("process-doc/classifier", label=ctx.prompt_label)
  |
  +-- Futtatas a WorkflowRunner altal
```

### 3.2 Skill Izolacioja

```
Skill A (process_documentation)          Skill B (email_intent)
  |                                        |
  +-- Sajat workflow definiciok            +-- Sajat workflow definiciok
  +-- Sajat agent osztalyok                +-- Sajat agent osztalyok
  +-- Sajat Langfuse prompt namespace      +-- Sajat Langfuse prompt namespace
  |     "process-doc/*"                    |     "email/*"
  +-- Sajat teszt adatok                   +-- Sajat teszt adatok
  +-- Sajat koltseg tracking               +-- Sajat koltseg tracking
  |     (workflow_runs.skill_name)         |     (workflow_runs.skill_name)
  |                                        |
  +---- Kozos Framework Szolgaltatasok ----+
        |-- LLMClient (LiteLLM)
        |-- PromptManager (Langfuse)
        |-- StateStore (PostgreSQL)
        |-- JobQueue (Redis)
        |-- Tracer (Langfuse + OTel)
        |-- CostTracker
        |-- RBAC
```

---

## 4. Skill Frissites (Upgrade)

### 4.1 Mikor Kell Upgrade?

- Prompt szoveg valtozas -> **NEM kell upgrade** (Langfuse-ban frissitheto)
- Agent logika valtozas -> **Kell upgrade** (Python kod valtozik)
- Uj step hozzaadasa -> **Kell upgrade** (DAG valtozik)
- Modell csere -> **Fugg** (ha prompt config-ban -> Langfuse; ha agent kodban -> upgrade)

### 4.2 Upgrade Folyamat

```bash
aiflow skill upgrade ./skills/process_documentation
```

```
Step 1: Uj verzio manifest betoltese
Step 2: Verzio osszehasonlitas (regibb nem telepitheto!)
Step 3: Schema validacio (uj DAG valid-e?)
Step 4: Backward kompatibilitas ellenorzes:
  |-- Valtoztak-e a workflow input/output tipusok?
  |-- Ha igen -> FIGYELMEZTETES (API klienseket erintheti!)
Step 5: workflow_definitions UPDATE
Step 6: Prompt sync (uj/modositott prompt-ok)
Step 7: Tesztek (opcionalis)
Step 8: skills tabla UPDATE (uj verzio)
Step 9: audit_log bejegyzes: "skill.upgrade"
```

**Fontos:** A mar futo workflow-k a regi verzioban fejezodik be!
Csak az uj futatasok hasznaljak az uj verziolt.

---

## 5. Skill Inter-Dependency (Skill-ek Kozotti Fuggoseg)

### 5.1 Pelda: Email Skill Hasznalja a Process Doc Skill-t

```yaml
# skills/email_intent_processor/skill.yaml
name: email_intent_processor
version: "1.0.0"
framework_requires: ">=1.0.0"

depends_on:
  - skill: process_documentation
    version: ">=2.0.0"
    optional: true  # Ha nincs telepitve, a feature kikapcsol
```

### 5.2 Sub-Workflow Hivas

```python
# email_intent_processor/workflow.py
@workflow(name="email-with-process-doc")
def email_with_process(wf: WorkflowBuilder):
    wf.step(classify_email)
    wf.branch(
        on="classify_email",
        when={
            "output.contains_process": ["extract_and_document"],
        },
        otherwise="standard_routing",
    )
    # Masik skill workflow-jat sub-workflow-kent hasznaljuk
    wf.subworkflow(
        name="extract_and_document",
        workflow="process-documentation",  # <- Process Doc Skill workflow-ja!
        input_mapping={"message": "output.process_description"},
        depends_on=["classify_email"],
    )
```

---

## 6. Skill Eltavolitas (Uninstall)

```bash
aiflow skill uninstall process_documentation
```

```
Step 1: Fuggoseg ellenorzes
  |-- Van-e mas skill ami fugg ettol? -> HIBA ha igen (--force nelkul)
Step 2: Futo workflow-k ellenorzese
  |-- Vannak-e futo (status=running/paused) workflow-k? -> FIGYELMEZTETES
Step 3: workflow_definitions torles (soft delete: enabled=false)
Step 4: skills tabla frissites (enabled=false)
Step 5: Langfuse prompt-ok megtartasa (nem toroljuk - audit okok)
Step 6: audit_log bejegyzes: "skill.uninstall"
```

---

## 7. Dokumentacios Kovetelmeny

### 7.1 Minden Skill-nek Kell

| Dokumentum | Cel | Generalas |
|------------|-----|-----------|
| skill.yaml | Manifest (gep-olvashato) | Kezzel irt |
| README.md | Fejlesztoi dokumentacio | Kezzel irt |
| Auto-gen docs | Uzleti dokumentacio (DAG, data flow) | `aiflow workflow docs` |
| PROMPT_CHANGELOG.md | Prompt verziok tortenete | Auto-generalt sync soran |
| tests/ | Teszt esetek | Kezzel irt (100+ min) |

### 7.2 Skill Install Soran Generalt Dokumentacio

```bash
aiflow skill install ./skills/process_documentation

# Automatikusan generalja:
# 1. Workflow DAG diagram (Mermaid -> SVG)
# 2. Data flow dokumentum (input/output tipusok per step)
# 3. Koltseg becsles (model + token becsles alapjan)
# 4. Fuggoseg grafikon (skill -> framework, skill -> skill)
```

---

## 8. Integracio Verifikacioja

### 8.1 Hogyan Ellenorizzuk hogy a Skill Jol Integralt?

```bash
# 1. Skill lista - megjelenik-e?
aiflow skill list
# process_documentation  v2.0.0  enabled  5 workflows  5 agents

# 2. Workflow lista - regisztralodott-e?
aiflow workflow list
# process-documentation  v2.0.0  skill:process_documentation  medium

# 3. Workflow inspect - DAG helyes-e?
aiflow workflow inspect process-documentation
# [DAG vizualizacio, step lista, tipusok]

# 4. Prompt-ok elhetok-e Langfuse-ban?
aiflow prompt list --skill process_documentation
# process-doc/classifier  v5  labels: [dev, test, staging, prod]
# process-doc/elaborator  v3  labels: [dev]

# 5. Health check - API-n elerheto-e?
curl http://localhost:8000/api/v1/workflows/process-documentation
# {"name": "process-documentation", "version": "2.0.0", "status": "active"}

# 6. Teszt futtatas
aiflow workflow run process-documentation --input '{"message": "Szabadsag igenyles"}' --mode sync
# {"status": "completed", "cost_usd": 0.058, "duration_ms": 11200, ...}
```
