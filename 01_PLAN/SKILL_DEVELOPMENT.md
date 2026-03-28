# AIFlow - Skill Fejlesztesi Utmutato (SKILL.md)

Ez a dokumentum a Claude Code es fejlesztok szamara keszult,
uj AIFlow Skill-ek letrehozasanak es karbantartasanak utmutatoja.

---

## Gyorsinditas: Uj Skill Letrehozasa

```bash
# 1. Scaffold generalas
aiflow skill new my_skill --template medium_branching

# 2. Fejlesztes (agents, prompts, models, tools)
# ... kod iras ...

# 3. Validacio
aiflow skill validate my_skill

# 4. Teszteles
aiflow eval run --skill my_skill

# 5. Telepites
aiflow skill install ./skills/my_skill

# 6. Prompt sync
aiflow prompt sync --skill my_skill --label dev
```

---

## Skill Struktura

```
skills/my_skill/
    skill.yaml                  # KOTELEZO: manifest
    __init__.py
    workflow.py                 # KOTELEZO: workflow(ok) definicio
    agents/                     # KOTELEZO: specialist agent-ek
        __init__.py
        classifier.py           # Pelda agent
        extractor.py
    models/                     # Pydantic modellek (step I/O)
        __init__.py
        my_models.py
    prompts/                    # KOTELEZO: YAML prompt fajlok
        classifier.yaml
        extractor.yaml
    tools/                      # Opcionalis: kulso integraciok
        my_tool.py
    tests/                      # KOTELEZO: 100+ teszt eset
        promptfooconfig.yaml    # Promptfoo config
        test_workflow.py        # pytest tesztek
        datasets/
            test_cases.json     # Teszt adatok
    README.md                   # Skill dokumentacio
```

---

## skill.yaml (Manifest)

```yaml
name: my_skill                           # Egyedi nev (snake_case)
display_name: "My Awesome Skill"         # Megjelenitesi nev
version: "1.0.0"                         # Semantic versioning
description: "What this skill does"
author: "BestIxCom Kft"
framework_requires: ">=1.0.0,<2.0.0"    # Framework kompatibilitas

capabilities:
  - intent_classification
  - data_extraction

required_models:
  - name: "openai/gpt-4o"
    type: llm
    usage: "Primary extraction"
  - name: "openai/gpt-4o-mini"
    type: llm
    usage: "Classification (cost-efficient)"
  - name: "openai/text-embedding-3-small"   # Ha RAG kell
    type: embedding
    usage: "Document embedding"
    optional: true

workflows:
  - my-workflow-name

agent_types:
  - ClassifierAgent
  - ExtractorAgent

prompts:
  - my-skill/classifier
  - my-skill/extractor

estimated_cost_per_run: 0.05

tags: [classification, extraction, hungarian]

# Opcionalis: vector store (RAG skill-ekhez)
vectorstore:
  collections:
    - name: my_documents
      shared: false
      embedding_model: "openai/text-embedding-3-small"
      chunking:
        strategy: semantic
        target_chunk_tokens: 500

# Opcionalis: mas skill fuggoseg
depends_on:
  - skill: process_documentation
    version: ">=2.0.0"
    optional: true
```

---

## Step Iras

```python
# agents/classifier.py
from aiflow.engine import step
from aiflow.engine.policies import RetryPolicy
from aiflow.core.context import ExecutionContext
from aiflow.models.client import ModelClient
from aiflow.prompts import PromptManager
from pydantic import BaseModel

# 1. Input/Output tipusok KOTELESEK (Pydantic)
class ClassifyInput(BaseModel):
    message: str

class ClassifyOutput(BaseModel):
    category: str           # "relevant" | "irrelevant"
    confidence: float       # 0.0 - 1.0
    reasoning: str

# 2. Step definicio
@step(
    name="classify",
    output_types={"category": str, "confidence": float, "reasoning": str},
    retry=RetryPolicy(max_retries=2, backoff_base=1.0),
    timeout=30,
)
async def classify(
    input_data: ClassifyInput,
    ctx: ExecutionContext,       # DI: trace, budget, prompt_label
    models: ModelClient,         # DI: LLM/embedding/classify
    prompts: PromptManager,     # DI: Langfuse SSOT
) -> ClassifyOutput:
    # Prompt betoltes Langfuse-bol (kornyezet-fuggoen: dev/test/staging/prod)
    prompt = await prompts.get("my-skill/classifier", label=ctx.prompt_label)

    # LLM hivas structured output-tal
    result = await models.generate(
        messages=prompt.compile(message=input_data.message),
        response_model=ClassifyOutput,      # instructor: Pydantic validacio
        model="openai/gpt-4o-mini",         # Olcso modell classification-hoz
    )
    return result
```

---

## Workflow Iras

```python
# workflow.py
from aiflow.engine import workflow, WorkflowBuilder
from aiflow.agents.quality_gate import QualityGate
from .agents.classifier import classify
from .agents.extractor import extract

@workflow(
    name="my-workflow",
    version="1.0.0",
    skill="my_skill",
    complexity="medium",
)
def my_workflow(wf: WorkflowBuilder):
    # Linearis resz
    wf.step(classify)

    # Elagazas
    wf.branch(
        on="classify",
        when={"output.category == 'relevant'": ["extract"]},
        otherwise="reject",
    )

    # Kinyeres + minosegi kapu
    wf.step(extract, depends_on=["classify"])
    wf.quality_gate(
        after="extract",
        gate=QualityGate(
            metric="completeness",
            threshold=0.80,
            on_fail="retry",        # Automatikus ujraprobas
            max_iterations=2,
            on_exhausted="human_review",  # Ha 2x sem sikerul -> ember
        ),
    )

    # Terminal
    wf.step(reject, terminal=True)
```

---

## Prompt YAML Iras

```yaml
# prompts/classifier.yaml
name: my-skill/classifier
version: 1
description: "Classify user input as relevant or irrelevant"

system: |
  You are a classification assistant.
  Classify the user's message.

user: |
  Message: {{ message }}

  Respond in JSON:
  {"category": "relevant|irrelevant", "confidence": 0.0-1.0, "reasoning": "..."}

config:
  model: openai/gpt-4o-mini
  temperature: 0.1
  max_tokens: 300
  response_format: {"type": "json_object"}

metadata:
  language: hu
  tags: [classification]

examples:
  - user: "Peldaul egy relevans input"
    assistant: '{"category": "relevant", "confidence": 0.95, "reasoning": "..."}'
  - user: "Peldaul egy irrelevans input"
    assistant: '{"category": "irrelevant", "confidence": 0.9, "reasoning": "..."}'

langfuse:
  sync: true
  labels: [dev, test]
```

---

## Teszteles

### Minimum Kovetelmeny: 100+ Teszt Eset

| Kategoria | Arany | Pelda |
|-----------|-------|-------|
| Pozitiv (helyes kimenet) | 40% | Tipikus, elvart inputok |
| Negativ (elutasitando) | 20% | Off-topic, spam, irrelevans |
| Edge case (hataresetek) | 20% | Ures input, tul hosszu, tobbertelmű |
| Adversarial (tamadas) | 10% | Prompt injection, jailbreak |
| Multi-language | 10% | Angol, nemet (ha releváns) |

### pytest Teszt Pelda

```python
# tests/test_workflow.py
import pytest
from aiflow.core.context import ExecutionContext

@pytest.fixture
def ctx():
    return ExecutionContext(run_id="test", prompt_label="test")

async def test_classify_relevant_input(ctx, mock_llm):
    from skills.my_skill.agents.classifier import classify, ClassifyInput
    result = await classify(ClassifyInput(message="Relevans szoveg..."), ctx=ctx, models=mock_llm, prompts=mock_prompts)
    assert result.category == "relevant"
    assert result.confidence > 0.5
```

### Promptfoo Config Pelda

```yaml
# tests/promptfooconfig.yaml
providers:
  - id: langfuse:my-skill/classifier:test
tests:
  - vars: {message: "Relevans input..."}
    assert:
      - type: is-json
      - type: javascript
        value: "JSON.parse(output).category === 'relevant'"
  - vars: {message: "Teljesen irrelevans kerdes"}
    assert:
      - type: javascript
        value: "JSON.parse(output).category === 'irrelevant'"
```

---

## Skill Eletciklus

```
1. aiflow skill new <name>          # Scaffold
2. Fejlesztes (agents, prompts)     # Claude Code segitsegevel
3. aiflow skill validate <name>     # Manifest + schema check
4. aiflow eval run --skill <name>   # 100+ teszt, 90%+ kell
5. aiflow prompt sync --label dev   # Langfuse sync
6. aiflow skill install <path>      # 9-lepes install
7. aiflow prompt promote --to staging  # UAT
8. Stakeholder validacio            # 5-10 valos eset
9. aiflow prompt promote --to prod  # Production!
10. Monitor (Langfuse + Grafana)    # Folytamatos
```

---

## Claude Code Hasznalat Skill Fejleszteshez

### Uj Skill Generalas
```
"Keszits egy uj skill-t szamla-feldolgozasra:
 - Classifier: szamla tipus (bejovo/kimeno/proforma)
 - Extractor: szamla adatok (osszeg, datum, partner, tetelsor)
 - Validator: adatok ellenorzese (NAV szabalyok)
 - Router: jovahagyas utonal (osszeg alapu)
 Hasznalja a medium_branching template-et."
```

### Prompt Iteracio
```
"Az extractor prompt nem kezeli jol a devizas szamlakat.
 Elemezd a hibas teszt eseteket es javitsd a prompt-ot."
```

### Teszt Bovites
```
"Generald le a 100+ teszt esetet a classifier-hez.
 Kell: magyar es angol szamlak, scan PDF-ek, email mellekletek."
```

---

## RPA / Hybrid Skill Fejlesztes

Az AIFlow 3 skill tipust tamogat:

| Tipus | Jellemzo | Pelda |
|-------|----------|-------|
| **ai** | Tisztan LLM/ML alapu | Process Documentation, Email Intent |
| **rpa** | Feluleti automatizacio (Playwright, ffmpeg) | Web scraping, fajl feldolgozas |
| **hybrid** | RPA + AI + operatori lepesek | Cubix Course Capture + Transcription |

### RPA Skill Manifest

```yaml
# skill.yaml
name: my_rpa_skill
skill_type: hybrid                       # ai | rpa | hybrid
required_tools:                          # Kulso eszkozok (nem Python csomagok!)
  - {name: playwright, version: ">=1.40"}
  - {name: ffmpeg, version: ">=6.0"}
```

### Playwright Step (Web Automatizacio)

```python
@step(name="scrape_page", timeout=60, step_type="playwright")
async def scrape_page(
    input_data: ScrapeInput,
    ctx: ExecutionContext,
    browser: PlaywrightBrowser,          # DI: Playwright browser
) -> ScrapeOutput:
    page = await browser.new_page()
    await page.goto(input_data.url)
    data = await page.evaluate("() => document.querySelector('.data').textContent")
    await page.close()
    return ScrapeOutput(content=data)
```

### Shell Step (ffmpeg, pandoc, etc.)

```python
@step(name="extract_audio", timeout=300, step_type="shell")
async def extract_audio(
    input_data: AudioInput,
    ctx: ExecutionContext,
    shell: ShellExecutor,                # DI: sandboxed shell
) -> AudioOutput:
    result = await shell.run(f"ffmpeg -i {input_data.video} -vn -ar 16000 {input_data.output}")
    return AudioOutput(audio_path=input_data.output)
```

### Operator Step (Emberi Beavatkozas)

```python
@step(name="wait_for_operator", timeout=3600, step_type="human")
async def wait_for_operator(input_data, ctx):
    raise HumanReviewRequiredError(
        question="Inditsa el a rogzitest!",
        context={"url": input_data.video_url},
        options=["Kesz", "Kihagyas"],
        deadline_minutes=60,
    )
    # Workflow pauzal -> operator az UI-on/API-n valaszol -> folytatodik
```

### RPA Skill Peldak

- `skills/cubix_course_capture/` - Web kurzus rogzites + transzkripció
- `skills/invoice_scraper/` - Szamla portal automatikus letoltes
- `skills/hr_report_generator/` - HR riport generalas webes feluleten
- Reszletek: `19_RPA_AUTOMATION.md`

---

## Git Szabalyok (Skill Fejleszteshez)

- **Branch:** `skill/{skill-nev}/{leiras}` (pl. `skill/process-doc/add-quality-gate`)
- **Commit:** Conventional Commits (`skill(process-doc): add quality gate`)
- **PR:** Min 1 review a skill team-tol, CI MUST pass (lint + skill tests + promptfoo)
- **SOHA:** `.env`, credentials, API key commit
- **MINDIG:** Co-Authored-By header ha Claude Code segitett
- Reszletek: `17_GIT_RULES.md`

---

## Gyakori Hibak (Keruld!)

| Hiba | Helyes megoldas |
|------|----------------|
| Prompt szoveg Python kodban | YAML fajl + Langfuse sync |
| Agent state (self.x = ...) | Stateless! Minden adat input_data-ban vagy ctx-ben |
| 7+ specialist agent | Max 6! Ha tobb kell, bontsd sub-workflow-kra |
| Teszt esetek < 50 | Minimum 100+, kulonben nem production-ready |
| `print()` debugging | `structlog.get_logger().info("event", key=val)` |
| `git add -A` | Specifikus fajlok hozzaadasa, .env SOHA |
| Prompt valtozas utan nincs teszt | MINDIG futtass promptfoo-t prompt valtozas utan |
| Playwright headless=False prod-ban | MINDIG headless=True production-ben |
| Shell command injection | ShellExecutor allowlist-et hasznal, soha ne raw shell |
