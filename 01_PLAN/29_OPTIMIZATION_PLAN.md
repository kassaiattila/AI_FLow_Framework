# AIFlow Optimalizacios Terv - Framework + Skill Racionalizalas

**Datum:** 2026-03-28
**Alapja:** Valos tesztek eredmenyei (process_documentation + cubix_course_capture)

---

## 1. Jelenlegi helyzet (audit eredmenyek)

### Mi MUKODIK es erteket ad
| Komponens | Hasznalat | Ertek |
|-----------|-----------|-------|
| **ModelClient** | Minden LLM hivas | Egysitett LLM interface, backend csere nelkul |
| **PromptManager** | Minden prompt | YAML betoltes, Jinja2 template, cache |
| **@step decorator** | Minden lepes | Metadata, logging, retry/timeout |
| **structlog** | Mindenhol | Strukturalt logging |
| **Pydantic modellek** | I/O tipusok | Validacio, serialization |
| **FileStateManager** | Cubix pipeline | Resume, allapot kovetes |

### Mi NEM hasznalt (holt kod)
| Komponens | Meret | Miert felesleges |
|-----------|-------|-----------------|
| **WorkflowRunner** | ~200 sor | Stepeket kozvetlenul hivjuk, nem runner-en at |
| **DI Container** | ~150 sor | Closure-ok, nem injection |
| **ExecutionContext** | ~60 sor | Stepek nem kapjak meg (runner nem adja at) |
| **Agent system** | ~800 sor | Specialist/Orchestrator nincs hasznalva |
| **API endpoints** | ~500 sor | Stubbok, nem funkcionalis |
| **DAG vegrehajtas** | ~300 sor | DAG definialt de nem futtatott |

### Architektura mismatch
- **Tervezett:** DI -> Runner -> DAG -> Steps (ctx, models, prompts injektalva)
- **Valos:** Module-level singletons -> direct step calls -> dict I/O

---

## 2. Javasolt optimalizacio (3 fazis)

### FAZIS O1: Framework slim-down (1 het)
**Cel:** A keret csak azt tartalmazza amit a skillek tenylegesen hasznalnak.

#### O1.1 Runner service injection (megoldja a closure problemat)
```python
# JELENLEGI (closure):
_backend = LiteLLMBackend()
models_client = ModelClient(generation_backend=_backend)

@step(name="classify")
async def classify(data: dict) -> dict:
    result = await models_client.generate(...)  # modul-szintu closure

# UJ (runner inject):
@step(name="classify")
async def classify(data: dict, *, models: ModelClient, prompts: PromptManager) -> dict:
    result = await models.generate(...)  # parameter, nem closure
```

**Megvalositas:**
- `WorkflowRunner._execute_step()`: inspektalja a step fuggveny signaturet
- Ha 1 param: `await step_func(input_data)` (backward compat)
- Ha tobb: `await step_func(input_data, models=models, prompts=prompts, ctx=ctx)`
- A skill `__init__.py`-bol eltunik a modul-szintu singleton

#### O1.2 SkillRunner: egyszeru skill futtato
```python
class SkillRunner:
    """Leegyszerusitett skill futtato - nem DAG, hanem szekvencialis."""

    def __init__(self, models: ModelClient, prompts: PromptManager):
        self.models = models
        self.prompts = prompts

    async def run_steps(self, steps: list[Callable], input_data: dict) -> dict:
        """Futtassa a stepeket sorban, az elozostep outputja a kovetkezo inputja."""
        data = input_data
        for step_fn in steps:
            data = await step_fn(data, models=self.models, prompts=self.prompts)
        return data

    async def run_skill(self, skill_name: str, input_data: dict) -> dict:
        """Skill neve alapjan betolti a skill.yaml-t, megkeresi a stepeket, futtatja."""
```

Ez az amit a test scriptek mar csinalnak, csak formalizalva. A `WorkflowRunner` marad aki a DAG-ot is kezeli.

#### O1.3 Holt kod soft-deprecation
- `src/aiflow/agents/` -> `DEPRECATED` flag a docstring-ben
- `src/aiflow/core/di.py` -> `DEPRECATED`
- Nem toroljuk, hanem jeloljuk hogy Phase B-ben lesz hasznalva (ha lesz)

### FAZIS O2: Skill onallosag (1-2 het)
**Cel:** Minden skill futtathatoegy paranccsal, fuggetlen a framework reszleteitol.

#### O2.1 Skill entry point (`__main__.py`)
```python
# skills/process_documentation/__main__.py
"""python -m skills.process_documentation --input "Szabadsag igenyeles..."  --output ./output"""

async def main(input_text: str, output_dir: str) -> None:
    runner = SkillRunner.from_env()  # .env-bol OPENAI_API_KEY, stb.
    result = await runner.run_steps(
        [classify_intent, elaborate, extract, review, generate_diagram, export_all],
        {"user_input": input_text, "output_dir": output_dir},
    )
```

#### O2.2 Skill config egysegesites
Minden skill kap egy `skill_config.yaml` (nem csak `skill.yaml` manifest):
```yaml
# skills/process_documentation/skill_config.yaml
default_model: openai/gpt-4o-mini
fallback_model: openai/gpt-4o
prompt_dir: ./prompts
output_dir: ./output
kroki_url: http://localhost:8000
miro_api_token: ${MIRO_API_TOKEN}  # env var ref
```

#### O2.3 Skill teszteles egyszerusites
```bash
# Jelenlegi (bonyolult):
python scripts/test_real_skills.py --input-dir ... --output-dir ...

# Uj (egyszeru):
python -m skills.process_documentation --input "Szabadsag igenyeles..." --output ./out
python -m skills.cubix_course_capture transcript --input video.mkv --output ./out
python -m skills.cubix_course_capture capture --url "https://cubixedu.com/..." --output ./out
```

### FAZIS O3: Keretrendszer koherencia (2-3 het)
**Cel:** A framework es skillek kozotti interface tiszta, jol definialt.

#### O3.1 Mappa vegleges rendrakas
```
src/aiflow/                        # Framework
  core/                            # config, errors, registry, types
  engine/                          # step, SkillRunner, WorkflowRunner (optional)
  models/                          # ModelClient, LiteLLM backend
  prompts/                         # PromptManager, PromptDefinition
  skill_system/                    # manifest, loader, registry, instance
  tools/                           # shell, playwright, robotframework, human_loop
  state/                           # ORM (optional, ha DB backend)

skills/                            # Onallo skill csomagok
  process_documentation/           # Teljes skill sajat drawio, tools, tests, stb.
  cubix_course_capture/            # Teljes skill sajat robot, platforms, state, stb.
  aszf_rag_chat/                   # (jovobeli)
  ...
```

#### O3.2 Torolheto mappak
| Mappa | Miert torolheto | Alternativa |
|-------|----------------|-------------|
| `src/aiflow/agents/` | Nem hasznalt | Torles vagy Phase B-re halasztva |
| `src/aiflow/core/di.py` | Nem hasznalt | SkillRunner.from_env() helyettesiti |
| `src/aiflow/api/v1/` | Stubbok | API Phase B-ben, ha kell |
| `src/aiflow/ui/` | Ures | Phase B |
| `src/aiflow/contrib/` | Atemelve tools/-ba | Torles (backward compat atmeneti) |

#### O3.3 Dependency cleanup
```toml
# pyproject.toml - csak ami tenyleg kell:
[project]
dependencies = [
    "litellm>=1.40",          # LLM calls
    "instructor>=1.4",         # Structured output
    "openai>=1.10",           # STT API
    "pydantic>=2.0",          # Models
    "pydantic-settings>=2.0", # Config
    "structlog>=24.0",        # Logging
    "pyyaml>=6.0",            # Prompts
    "jinja2>=3.0",            # Templates
    "httpx>=0.25",            # HTTP (Kroki, Miro)
]

[project.optional-dependencies]
rpa = ["playwright>=1.40", "robotframework>=7.0", "robotframework-browser>=19.0"]
db = ["sqlalchemy[asyncio]>=2.0", "alembic>=1.13", "asyncpg>=0.29"]
```

---

## 3. Skill fejlesztes es bovites stratgia

### Uj skill hozzaadasa (sablon)
```bash
# Kovetendo lepes sorrend:
1. Pilot projekt elemzes (mukodo kod azonositasa)
2. /new-skill command -> scaffold generalas
3. Pilot kod portalasa (modellek, promptok, logika) - 1. KORBEN MINDENT
4. Prompt YAML adaptacio (PromptDefinition schema)
5. Step fuggvenyek (egyenként tesztelve)
6. __main__.py entry point
7. Unit tesztek (mockolt LLM)
8. Integracios teszt (valos LLM/API)
9. skill_config.yaml + skill.yaml
10. Dokumentacio (README.md a skill-ben)
```

### Prioritasi sorrend (kovetkezo skillek)
| # | Skill | Forras | Kifejtett ertek |
|---|-------|--------|-----------------|
| 1 | **aszf_rag_chat** | allianz-rag-unified | Multi-instance RAG, 3 ugyfel |
| 2 | **email_intent_processor** | uj fejlesztes | Kafka trigger, intent routing |
| 3 | **qbpp_test_automation** | MultiApp_AutoTester | Playwright E2E tesztek |
| 4 | **cfpb_complaint_router** | 01_cfpb_complaints | sklearn ML pipeline |

### Skill versioning es release
- Semantic versioning: `skill.yaml` version mezo
- Git tag: `skill/process_documentation/v2.1.0`
- Instance config: `version: "2.1.0"` (ugyfel-specifikus pin)
- Backward compat: regi instance config mukodik uj skill verzioval

---

## 4. Skalazhatosag es karbantarthatosag

### Monitoring (amit be kell koni)
- Langfuse integracio (PromptManager Phase B)
- Koltseg tracking per skill/instance (mar van, de DB nelkul)
- SLA monitoring (valaszidok per step)

### CI/CD (amit le kell tesztelni)
- `pytest tests/unit/` - minden commit
- `pytest skills/*/tests/` - erintett skill commit
- Valos LLM integracios teszt - nightly/weekly
- Promptfoo eval - prompt modositasnal

### Dokumentacio
- Minden skill: `README.md` a skill mappaban (hasznalat, konfiguracio, teszteles)
- Framework: `src/aiflow/README.md` (architektura, API, bovites)
- Terv: `01_PLAN/` marad a fo referencia

---

## 5. Vegrehajtasi idovonal

```
Het 1: FAZIS O1 - Framework slim-down
  - Runner service injection
  - SkillRunner implementacio
  - Holt kod deprecation

Het 2: FAZIS O2 - Skill onallosag
  - __main__.py entry pointok
  - skill_config.yaml
  - CLI futtathatosag

Het 3-4: FAZIS O3 - Koherencia
  - Mappa vegleges rendrakas
  - Dependency cleanup
  - Dokumentacio

Het 5+: Kovetkezo skillek portalasa (aszf_rag_chat elso)
```

---

## 6. Docling integracio (dokumentum feldolgozas)

### Cel
A `docling` (docling.ai) az egyseges dokumentum feldolgozo megoldas az AIFlow-ban.
Egyetlen library kezeli: PDF (tablazat/layout feismeres), DOCX, PPTX, XLSX, HTML, kepek.

### Implementacio
- **Fajl:** `src/aiflow/ingestion/parsers/docling_parser.py` - KESZ
- **Osztaly:** `DoclingParser` - universal parser `parse()` es `parse_batch()` metodusokkal
- **Output:** `ParsedDocument` (text, markdown, tables, metadata, word/char count)
- **Integracio:** RAG ingest workflow `parse_documents` step docling-ot hasznal elsosorban
- **Fallback:** Ha docling nincs telepitve, pymupdf/python-docx fallback

### Miert docling es nem egyedi parserek?
1. Egyetlen dependency 15+ formatum helyett (PDF, DOCX, PPTX, XLSX, HTML, kep)
2. Tablazat struktura felismeres (mas parserek ezt nem tudjak)
3. Layout/olvasasi sorrend analizis (fontos biztositasi dokumentumoknal)
4. Aktivan karbantartott (IBM-hez kotheto projekt)
5. Lokalis feldolgozas (nincs cloud fuggoseg - fontos GDPR szempontbol)

### Hasznalat mas skillekben
Barmelyik skill ami dokumentumokat dolgoz fel, hasznalhatja:
```python
from aiflow.ingestion.parsers.docling_parser import DoclingParser
parser = DoclingParser()
result = parser.parse("document.pdf")
# result.text, result.markdown, result.tables
```

---

## 7. Sikerkritérium

| Metrika | Jelenlegi | Cel |
|---------|-----------|-----|
| Skill futtathatosag | Script + manualis | `python -m skills.X --input ...` |
| Framework hasznalati rata | ~30% (3/10 komponens) | ~80% (hasznalt vagy torolt) |
| Uj skill scaffold ido | ~1 nap | ~2 ora (sablon + /new-skill) |
| Teszt coverage | 80% framework, 0% skill integration | 80% mindenre |
| Deployment | Nincs | Docker Compose per customer |
