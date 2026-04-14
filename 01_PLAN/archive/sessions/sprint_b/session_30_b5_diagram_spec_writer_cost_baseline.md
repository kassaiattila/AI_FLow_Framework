# AIFlow Sprint B — Session 30 Prompt (B5: Diagram Generator Hardening + Spec Writer UJ Skill + Langfuse Cost Baseline)

> **Datum:** 2026-04-09
> **Branch:** `feature/v1.3.0-service-excellence` | **HEAD:** `82b1dd5`
> **Port:** API 8102, Frontend 5174
> **Elozo session:** S29 — B4.2 DONE (process_docs 14/14 + invoice_processor 14/14 + cubix_course_capture 12/12 + invoice_finder 12/12 promptfoo, +26 test, 54 → 80 promptfoo, cubix prompt SPLIT, invoice_finder UJ config, 0 regresszio 1424 unit)
> **Terv:** `01_PLAN/58_POST_SPRINT_HARDENING_PLAN.md` (B5 szekcio, sor 1256-1309)

---

## KONTEXTUS

### S29 Eredmenyek (B4.2 — DONE, commit `e4f322e` + `82b1dd5`)

**4 skill 95%+ promptfoo gate (mind 100%):**
- `process_documentation`: 10 → **14/14** (+4 strict): decision label enforcement, parallel branches (`& `), off-topic refusal (NOT_A_PROCESS), loop-back edge. Inline prompt strict shape mapping + few-shot.
- `invoice_processor`: 10 → **14/14** (+4 strict): HU thousands separator (`1.500.000,50 Ft` → `1500000.50`), AAM VAT-exempt (`vat_rate=0 + vat_status=exempt`), multi-currency (HUF+EUR egyetlen szamlan), multi-page continuation. "Literal VAT rate reading" szabaly (5% nem javitja 27%-ra).
- `cubix_course_capture`: 6 → **12/12** (+6) — **NAGY REFAKTOR**: `transcript_structurer.yaml` (1 monolit) **SPLIT** → 3 dedikalt prompt (`section_detector.yaml` + `summary_generator.yaml` + `vocabulary_extractor.yaml`). `transcript_pipeline.py` `structure_transcript` step `asyncio.gather` parallel hivja a 3-at. Deprecated jeloles megmaradt backward compat-ra. `test_structure_calls_llm` frissitve split-aware mock-kal.
- `invoice_finder`: 0 → **12/12** (UJ `promptfooconfig.yaml`!) — Router prompt 4 task-kal (`classify` / `extract` / `payment_status` / `report`) az 1-test-per-prompt cross-product trap elkerulesere. 12 test case Phase 0 valos email-ekre kalibralva (`data/e2e_results/outlook_fetch/invoice_candidates.json`, 9 valos email subject + crafted body). `guardrails.yaml` allowed_pii bovites: `email + hu_tax_number + hu_bank_account` + invoice-domain injection patterns.

**B4.1 leftover schema teszt javitas:**
- `email_intent_processor`: `test_intents_loads` 10→12 (invoice_received + calendar_invite), `test_entities_loads` 8→11 (tax_number + bank_account + postal_address).

**10-pt service hardening audit:** 4/4 skill 8/10 PRODUCTION-READY (gap: AIFlowError + README.md, nem-blocker).

**Tesztek + minoseg (S29 vegen):**
- 1424/1424 unit test PASS (0 regresszio)
- 154/154 skill test PASS (cubix split-aware mock + email schema fix)
- ruff skills/* tiszta (40 pre-existing scripts/ hiba nem B4.2 hatasa)

**Infrastruktura (v1.3.0 — S29 utan):**
- 26 service | 165 API endpoint (25 router) | 46 DB tabla | 29 migracio
- 21 pipeline adapter | 7 pipeline template | 6 skill | 22 UI oldal
- **1424 unit test** | 129 guardrail teszt | 97 security teszt | 104 E2E | **80 promptfoo teszt** (6 skill-en, mind 95%+)

### Jelenlegi Allapot (B5 cel — 3 komponens)

```
=== B5 KOMPONENSEK TERKEP (S30 cel) ===

### B5.1 — Diagram Generator Hardening ###

DiagramGeneratorService (LETEZIK, de reszleges):
  src/aiflow/services/diagram_generator/service.py — 238 sor
    DiagramGeneratorConfig (kroki_url, max_input_length)
    DiagramRecord (Pydantic)
    DiagramGeneratorService.generate(user_input, created_by)
      → KOZVETLENUL hivja a process_documentation skill step-jeit:
         classify_intent → elaborate → extract → review → generate_diagram → export_all
      → Persistalja: generated_diagrams table
      → Visszaad: DiagramRecord (mermaid_code, svg_content, drawio_xml, review, ...)
    service.list_diagrams / get_diagram / delete_diagram / export_diagram

API router:
  src/aiflow/api/v1/diagram_generator.py
    POST /api/v1/diagrams/generate
    GET  /api/v1/diagrams          — lista, pagination
    GET  /api/v1/diagrams/{id}     — single
    DELETE /api/v1/diagrams/{id}
    GET  /api/v1/diagrams/{id}/export?fmt=mermaid|svg|drawio|bpmn

Pipeline adapter:
  src/aiflow/pipeline/adapters/diagram_adapter.py
    DiagramGenerateAdapter (service_name='diagram_generator', method_name='generate')
    Input: GenerateDiagramInput (description, diagram_type)
    Output: GenerateDiagramOutput (diagram_id, mermaid_code, svg_content, diagram_type)
    ⚠ PROBLEMA: diagram_type input field LETEZIK, de NEM hasznaljuk!
                a service mindig csak mermaid flowchart-ot general.

UI oldal:
  aiflow-admin/src/pages-new/ProcessDocs.tsx
    useApi('/api/v1/diagrams') — lista + list DataTable
    ⚠ HIANYOSAG: csak listazas, NEM trigger-el generalast!

Tesztek:
  tests/unit/services/test_diagram_generator_service.py — letezik, mock-olja asyncpg-t
  NINCS: E2E teszt (szoveges leiras → rendered SVG)
  NINCS: promptfoo diagram_generator/tests/ mappa (a service NEM kulon prompt-okat hasznal)

Ismert hianyossagok a B5.1-hez:
  1. NINCS pipeline template (diagram_generator_v1.yaml)
  2. Csak MERMAID flowchart tamogatva — sequence diagram, BPMN swimlane, DrawIO
     kulon tipus valasztashoz szukseges
  3. NINCS dedikalt diagram_generator prompt set — jelenleg process_documentation
     prompts-ot hasznalja, de a B5 terve szerint kell 3 uj/modositott:
       - diagram_planner.yaml — leiras → diagram tipus + struktura valasztasa
       - mermaid_generator.yaml — struktura → mermaid syntax (komplex flow)
       - diagram_reviewer.yaml — szintaxis validacio + javitas
  4. NINCS promptfoo config a diagram_generator service-hez
  5. UI: nincs input textarea + diagram_type dropdown + "Generate" gomb + preview
  6. diagram_adapter.py: diagram_type NEM jut el a service-hez (elveszik a wrapping-ban)


### B5.2 — Spec Writer UJ Skill (NULLA kod!) ###

JELENLEG NEM LETEZIK SEMMI:
  NINCS src/aiflow/services/spec_writer/
  NINCS skills/spec_writer/
  NINCS pipeline template
  NINCS prompts
  NINCS adapter
  NINCS API router
  NINCS UI oldal
  NINCS CLI

Kell letrehozni:
  skills/spec_writer/
    skill.yaml              — manifest
    skill_config.yaml       — runtime config (models, output_dir, quality thresholds)
    __init__.py             — service init (SkillRunner.from_env pattern)
    __main__.py             — CLI entry: python -m skills.spec_writer --input "..." --type feature
    models/__init__.py      — Pydantic I/O (SpecInput, SpecAnalysis, SpecDraft, SpecReview, SpecOutput)
    prompts/
      spec_analyzer.yaml    — raw text → structured requirement JSON
      spec_generator.yaml   — requirement + template_type → markdown spec
      spec_reviewer.yaml    — markdown spec → quality score + missing sections
    workflows/
      spec_writing.py       — step-ek: analyze → select_template → generate → review → finalize
    tests/
      test_workflow.py      — 5+ unit test (mocked LLM, schema verification)
      promptfooconfig.yaml  — 6+ promptfoo test (feature spec, API spec, user story, HU+EN, hibas input)

Pipeline template:
  src/aiflow/pipeline/builtin_templates/spec_writer_v1.yaml
    5 step: analyze → select_template → generate → review → finalize
    Adapter: uj spec_writer_adapter.py (vagy generikus skill_adapter eleg ha mar van)

API endpoint:
  src/aiflow/api/v1/spec_writer.py
    POST /api/v1/specs/write — body: {input_text, spec_type, language}
    GET  /api/v1/specs — lista
    GET  /api/v1/specs/{id} — single
    GET  /api/v1/specs/{id}/export?fmt=markdown|html

DB tabla: generated_specs (id, input_text, spec_type, language, markdown_content, review, created_by, created_at, updated_at)
  → UJ Alembic migracio: 030_add_generated_specs.py

UI oldal:
  aiflow-admin/src/pages-new/SpecWriter.tsx (UJ)
    - Input textarea (szoveges leiras)
    - Dropdown: spec_type (feature / api / db / user_story)
    - Dropdown: language (hu / en)
    - "Write Spec" gomb → POST /api/v1/specs/write
    - Eredmeny: markdown preview (react-markdown vagy similar) + letoltes gomb

Promptfoo gate: 90%+ (prototipus, 95% Sprint C-ben)


### B5.3 — Langfuse Koltseg Baseline Riport ###

JELENLEG:
  cost_records tabla LETEZIK: 14 rekord
    oszlopok: id, workflow_run_id, step_name, model, provider,
              input_tokens, output_tokens, cost_usd, team_id, recorded_at
  CostTracker class LETEZIK:
    src/aiflow/observability/cost_tracker.py
    get_workflow_cost(run_id), get_team_usage(team_id, period),
    get_model_breakdown(run_id), record(cost_record)
    ⚠ In-memory default — NEM query-zi a cost_records tablat DIRECT-ben!

  Cost API LETEZIK:
    GET /api/v1/costs/summary → per_skill + daily aggregation
    GET /api/v1/costs/breakdown → per_model aggregation
    Costs.tsx UI oldal DataTable-kel

HIANYZIK (B5.3-ban megcsinalando):
  1. scripts/cost_baseline.py — egyszer lefuttatott riport generator script
     Query-zi a cost_records tablat, aggregal:
       - per workflow_run_id (melyik run mennyi)
       - per step_name (melyik adapter mennyi)
       - per model (gpt-4o-mini vs gpt-4o vs text-embedding-3-small)
       - per day (utolso 7 nap trend)
     Az LLM + embedding + whisper STT koltseget kulon!
  2. 01_PLAN/COST_BASELINE_REPORT.md generalas (markdown riport):
     - Header + generalasi datum + query range
     - Summary: total_runs, total_cost_usd, avg_cost_per_run, cheapest/priciest run
     - Per-service tabla: service_name | run_count | total_usd | avg_usd | % of total
     - Per-model tabla: model | request_count | total_usd | avg_per_request
     - Figyelmeztetesek: ha egy service > X USD/day vagy > Y USD/run
     - Javaslatok: melyik service erdemes gpt-4o-mini-re cserelni (gpt-4o-rol)
  3. (Opcionalis) Langfuse API integracio — fetch-eli a cloud-tarolt cost-okat is,
     osszehasonlitja a local cost_records-kel. Ha elter: warning.
```

---

## B5 FELADAT: 3 Komponens — Diagram hardening + UJ Spec writer skill + Cost baseline

> **Gate:**
> - B5.1: `diagram_generator_v1.yaml` pipeline template letezik, 3 diagram tipus (mermaid flowchart, sequence, BPMN swimlane) mukodik, 5+ promptfoo test 95%+, 5 uj unit test + 3 E2E PASS.
> - B5.2: `skills/spec_writer/` skill letezik (skill.yaml + 3 prompt + workflow + CLI + test_workflow), pipeline template, API endpoint, UI oldal, 6+ promptfoo test 90%+, 5 uj unit test PASS.
> - B5.3: `01_PLAN/COST_BASELINE_REPORT.md` generalt, `scripts/cost_baseline.py` futtathato, Langfuse integracio dokumentalva.
> **Eszkozok:** `/new-pipeline`, `/new-prompt`, `/dev-step`, `/service-hardening`, `/pipeline-test`, `/regression`

---

### LEPES 1: diagram_adapter Diagram Type Routing + 3 Uj Prompt

```
Hol: src/aiflow/pipeline/adapters/diagram_adapter.py
     src/aiflow/services/diagram_generator/service.py
     src/aiflow/services/diagram_generator/prompts/  (UJ MAPPA!)
     src/aiflow/pipeline/builtin_templates/diagram_generator_v1.yaml  (UJ FAJL!)

Cel 1: diagram_adapter a 'diagram_type' input-ot tenyleg atadja a service-nek.
Cel 2: 3 diagram tipus tamogatva — 'flowchart' (default), 'sequence', 'bpmn_swimlane'.
Cel 3: 3 UJ dedikalt service prompt ami a process_documentation skill-tol FUGGETLEN.
Cel 4: diagram_generator_v1.yaml pipeline template letrehozas.

KONKRET TEENDOK:

1. DiagramGeneratorService.generate signature bovites:
   async def generate(self, user_input: str, diagram_type: str = "flowchart",
                      created_by: str | None = None) -> DiagramRecord:
   - diagram_type = "flowchart" | "sequence" | "bpmn_swimlane"
   - "flowchart" esetben a meglevo process_documentation pipeline fut (ez az alap).
   - "sequence" + "bpmn_swimlane" eseten UJ prompt-alapu path az uj service prompt-okkal.

2. UJ src/aiflow/services/diagram_generator/prompts/ mappa + 3 YAML:

   a) diagram_planner.yaml:
      Bemenet: {user_input, requested_type}
      Kimenet: {
        "diagram_type": "flowchart|sequence|bpmn_swimlane",
        "actors": [...],
        "steps": [...],
        "interactions": [...]  (sequence-hez)
      }
      Cel: eldonteni hogy mi keszul + strukturalt JSON graf.
      Model: gpt-4o, temperature 0.1, response_format json_object.

   b) mermaid_generator.yaml:
      Bemenet: {diagram_type, structure_json}
      Kimenet: strict mermaid syntax (flowchart TD / sequenceDiagram / swimlane)
      System prompt: mindharom tipusra few-shot példák (3×2 = 6 pelda).
      Strict shape mapping (B4.2 tanulsagok alkalmazasa!):
        - Decision diamond `{...}` MUST have 2+ labeled edges
        - Sequence: `A->>B: message`, `B-->>A: response`
        - BPMN swimlane: `subgraph actor_name ... end`
      Temperature 0.1 (rendkivul determinisztikus).

   c) diagram_reviewer.yaml:
      Bemenet: {mermaid_code, diagram_type}
      Kimenet: {
        "valid": bool,
        "errors": [...],  (nem balanced brackets, hianyzo labels, invalid syntax)
        "suggestions": [...],
        "fixed_code": str | null  (ha tudja javitani, akkor a helyes kod)
      }
      System prompt: a hibas output auto-fix-elesere is.

3. diagram_adapter.py kijavitas:
   - DiagramGenerateAdapter._run atadja a diagram_type-ot a service-nek:
     result = await svc.generate(
         user_input=data.description,
         diagram_type=data.diagram_type,   # EZ MOST NEM MEGY AT!
         created_by=ctx.user_id,
     )
   - GenerateDiagramOutput marad ugyanaz, de a test-ben verify-old hogy a
     mermaid_code a megfelelo syntax-ot tartalmazza (flowchart/sequence/swimlane).

4. UJ diagram_generator_v1.yaml pipeline template:
   version: 1
   metadata:
     name: diagram_generator_v1
     description: "Natural language → structured diagram (mermaid / sequence / bpmn)"
     version: "1.0.0"
   steps:
     - name: plan
       adapter: diagram_generator.generate
       input:
         description: ${input.description}
         diagram_type: ${input.diagram_type}
     - name: review
       adapter: guardrail.output  (vagy common llm_check)
       depends_on: [plan]
   triggers: [manual, api]

5. Unit teszt bovites:
   tests/unit/services/test_diagram_generator_service.py-ba 5 uj teszt:
   - test_generate_flowchart_default (mar van, maradhat)
   - test_generate_sequence_diagram_new (UJ)
   - test_generate_bpmn_swimlane_new (UJ)
   - test_diagram_adapter_passes_type (UJ — verify input.diagram_type eljut a service-be)
   - test_diagram_reviewer_auto_fix (UJ — hibas input → fixed_code)
   - test_generate_invalid_type_fallback (UJ — 'gantt' → fallback flowchart-ra)

6. E2E teszt:
   tests/e2e/test_diagram_pipeline.py (UJ fajl, 3 test):
   - test_pipeline_flowchart_e2e: PipelineRunner → diagram_generator_v1 → svg file
   - test_pipeline_sequence_e2e: PipelineRunner → sequence output
   - test_pipeline_swimlane_e2e: PipelineRunner → swimlane output
   MINDEN valos LLM (gpt-4o-mini) + valos Kroki Docker + valos DB persist!

7. Promptfoo config:
   skills/ alatt NINCS diagram_generator (nem skill, service!), ezert:
   src/aiflow/services/diagram_generator/tests/promptfooconfig.yaml (UJ!)
   5+ test case:
   - test_flowchart_basic: "Vevo leadja rendelest..." → contains 'flowchart'
   - test_sequence_auth: "User login flow: user → frontend → backend → DB" → 'sequenceDiagram'
   - test_bpmn_swimlane: "HR es IT parallel onboarding" → 'subgraph'
   - test_complex_decision: ha-akkor dontesekkel → javascript: decision labels ok
   - test_invalid_fallback: "Hello, hogy vagy?" → NOT_A_DIAGRAM VAGY fallback

Gate: 5+ promptfoo 95%+, 5 uj unit + 3 E2E PASS, diagram_adapter type routing mukodik
```

### LEPES 2: spec_writer UJ Skill (NULLA-bol!)

```
Hol: skills/spec_writer/ (TELJES MAPPA KELL!)
     src/aiflow/pipeline/builtin_templates/spec_writer_v1.yaml
     src/aiflow/pipeline/adapters/spec_writer_adapter.py (opcionalis, ha van skill_adapter generic akkor eleg)
     src/aiflow/api/v1/spec_writer.py (UJ)
     src/aiflow/state/models/generated_specs.py (UJ)
     alembic/versions/030_add_generated_specs.py (UJ migracio!)
     aiflow-admin/src/pages-new/SpecWriter.tsx (UJ)

Cel: LLM-alapu specifikacio iro ami szobeli leirasbol strukturalt spec dokumentumot ir.

KONKRET TEENDOK:

1. Skill scaffold letrehozas (/archive:new-skill pattern szerint):
   skills/spec_writer/
     skill.yaml                 — name + version + capabilities
     skill_config.yaml          — models, output, quality thresholds
     __init__.py                — models_client + prompt_manager modul szintu singletonok
     __main__.py                — CLI: argparse --input --type --output
     models/__init__.py         — Pydantic schemak (lasd lent)
     prompts/                   — 3 YAML (lasd lent)
     workflows/
       __init__.py
       spec_writing.py          — 5 step @step dekorator-ral
     tests/
       test_workflow.py         — 5+ teszt
       promptfooconfig.yaml     — 6+ teszt

2. Pydantic modellek (models/__init__.py):
   class SpecInput(BaseModel):
       raw_text: str
       spec_type: Literal["feature", "api", "db", "user_story"] = "feature"
       language: Literal["hu", "en"] = "hu"
       context: str | None = None

   class SpecRequirement(BaseModel):
       title: str
       description: str
       actors: list[str]
       goals: list[str]
       constraints: list[str]
       inputs: list[dict[str, str]]   # [{name, type, description}]
       outputs: list[dict[str, str]]
       edge_cases: list[str]

   class SpecDraft(BaseModel):
       title: str
       spec_type: str
       language: str
       markdown: str
       sections_count: int
       word_count: int

   class SpecReview(BaseModel):
       is_acceptable: bool
       score: float        # 0-10
       missing_sections: list[str]
       questions: list[str]    # "Ezekre meg valasz kell..."
       suggestions: list[str]

   class SpecOutput(BaseModel):
       requirement: SpecRequirement
       draft: SpecDraft
       review: SpecReview
       final_markdown: str

3. 3 UJ prompt YAML (prompts/):

   a) spec_analyzer.yaml:
      name: spec-writer/analyzer
      system: |
        You are a requirement analyst. Extract structured requirements from
        a raw spec description. Identify: title, actors, goals, inputs, outputs,
        constraints, edge cases.
        Output HU if input is HU, EN if input is EN.
        Output JSON matching SpecRequirement schema.
      response_format: json_object
      temperature: 0.2

   b) spec_generator.yaml:
      name: spec-writer/generator
      system: |
        You are a technical writer. Given a structured requirement and a
        spec_type (feature/api/db/user_story), generate a valid Markdown spec.

        Template per spec_type:
        - feature: ## Overview / ## Goals / ## User Flow / ## Inputs / ## Outputs /
                   ## Edge Cases / ## Acceptance Criteria
        - api: ## Endpoint / ## Request / ## Response / ## Error Codes / ## Examples
        - db: ## Table / ## Columns / ## Indexes / ## Relationships / ## Migrations
        - user_story: ## As a / ## I want / ## So that / ## Acceptance Criteria

        Output ONLY valid markdown, NO markdown fences around the whole output.
      temperature: 0.3
      max_tokens: 4096

   c) spec_reviewer.yaml:
      name: spec-writer/reviewer
      system: |
        You are a spec quality reviewer. Given a draft markdown spec, score it
        (0-10), identify missing sections, list review questions ("Ezekre
        meg valasz kell..."), and suggest improvements.
        is_acceptable = true ha score >= 7.0
        Output JSON matching SpecReview schema.
      response_format: json_object
      temperature: 0.2

4. workflows/spec_writing.py:
   5 step:
     @step analyze(data) → SpecRequirement
     @step select_template(data) → {"template_type": ...}
     @step generate_draft(data) → SpecDraft
     @step review_draft(data) → SpecReview
     @step finalize(data) → SpecOutput
   @workflow(name="spec-writer", version="1.0.0", skill="spec_writer")
   def spec_writing(wf): step-ek depends_on-nal linkelve.

5. __main__.py CLI:
   python -m skills.spec_writer --input "leiras..." --type feature --language hu --output spec.md
   Output: spec.md (final_markdown) + spec.json (SpecOutput teljes)

6. Pipeline template (src/aiflow/pipeline/builtin_templates/spec_writer_v1.yaml):
   5 step diagram_generator_v1.yaml mintaul vevén, adapter: 'spec_writer.write'.

7. Adapter (ha NINCS generic skill_adapter):
   src/aiflow/pipeline/adapters/spec_writer_adapter.py
   SpecWriterAdapter.input_schema = SpecInput, output_schema = SpecOutput
   _run: SkillRunner.from_env().run_workflow('spec-writer', input)

8. DB migracio (alembic/versions/030_add_generated_specs.py):
   CREATE TABLE generated_specs (
     id UUID PRIMARY KEY,
     input_text TEXT NOT NULL,
     spec_type VARCHAR(50) NOT NULL,
     language VARCHAR(10) NOT NULL,
     markdown_content TEXT NOT NULL,
     requirement JSONB,
     review JSONB,
     created_by VARCHAR(255),
     created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
     updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
   );
   CREATE INDEX idx_generated_specs_created_at ON generated_specs(created_at DESC);

9. API endpoint (src/aiflow/api/v1/spec_writer.py):
   router = APIRouter(prefix="/api/v1/specs", tags=["specs"])
   POST /api/v1/specs/write — body: SpecInput, returns SpecOutput + id
   GET /api/v1/specs?limit=50&offset=0
   GET /api/v1/specs/{id}
   DELETE /api/v1/specs/{id}
   GET /api/v1/specs/{id}/export?fmt=markdown|html|json
   Minden response-ban: "source": "backend"
   Regisztracio: src/aiflow/api/v1/__init__.py-be (vagy app.py-be)

10. UI oldal (aiflow-admin/src/pages-new/SpecWriter.tsx):
    - Layout: PageLayout + Card wrappers
    - Input textarea (50% width)
    - Dropdown: spec_type (feature / api / db / user_story)
    - Dropdown: language (hu / en)
    - Button: "Write Spec" → POST /api/v1/specs/write
    - Right panel: markdown preview (react-markdown)
    - Save/Download button
    - Saved specs lista alul (DataTable)
    Route hozzaadas: App.tsx / router config
    i18n: translate kulcsok (hu + en)

11. Unit teszt (skills/spec_writer/tests/test_workflow.py):
    5+ teszt (cubix_course_capture/tests/test_workflow.py mintaul!):
    - test_analyze_structures_requirement (mock LLM, schema check)
    - test_generate_draft_hu_feature (mock LLM, markdown has '## Overview')
    - test_generate_draft_en_api (mock LLM, english sections)
    - test_review_acceptable_score (mock LLM, is_acceptable=true when score>=7)
    - test_review_missing_sections (mock LLM, lista returns non-empty)
    - test_full_pipeline_integration (5 step chained, mock LLM)

12. Promptfoo config (skills/spec_writer/tests/promptfooconfig.yaml):
    6+ test case, B4.2 router prompt mintaul ha tobb prompt kell!
    - test_feature_spec_hu: HU feature leiras → markdown has '## Celok' or '## Goals'
    - test_api_spec_en: EN API description → markdown has '## Endpoint'
    - test_user_story_format: "Mint user, szeretnem..." → has 'As a'
    - test_db_spec_columns: DB schema leiras → has '## Columns'
    - test_review_missing_edge_cases: spec without edge cases → review.missing contains 'edge'
    - test_too_short_input: "Make a thing" → review warns about insufficient detail
    Provider: openai:gpt-4o-mini, temperature 0, max_tokens 4096
    Gate: 90%+ (5/6 vagy 6/6)

Gate: skills/spec_writer/ minden fajl letezik, CLI mukodik valos input-on,
      UI oldal betoltodik, API POST /specs/write 200 OK, 6+ promptfoo 90%+,
      5+ unit test PASS
```

### LEPES 3: Langfuse Koltseg Baseline Riport

```
Hol: scripts/cost_baseline.py (UJ!)
     01_PLAN/COST_BASELINE_REPORT.md (UJ, generalt output!)

Cel 1: cost_records tabla aggregaciojabol riport generalasa.
Cel 2: Langfuse cloud integracio (opcionalis, dokumentalva).
Cel 3: 01_PLAN/COST_BASELINE_REPORT.md deploy-keszen.

KONKRET TEENDOK:

1. scripts/cost_baseline.py letrehozas (~200 sor):

   #!/usr/bin/env python
   """Cost baseline report generator — aggregates cost_records + writes Markdown."""
   import argparse
   import asyncio
   from datetime import datetime, timezone, timedelta
   from pathlib import Path

   import asyncpg
   import structlog

   logger = structlog.get_logger(__name__)

   async def fetch_cost_records(conn, since: datetime | None = None):
       query = "SELECT * FROM cost_records"
       if since:
           query += f" WHERE recorded_at >= '{since.isoformat()}'"
       return await conn.fetch(query + " ORDER BY recorded_at DESC")

   async def aggregate_per_service(records): ...
   async def aggregate_per_model(records): ...
   async def aggregate_per_day(records): ...

   def format_markdown_report(records, aggregations) -> str:
       # Fo szekciok:
       # # AIFlow Cost Baseline Report
       # Generated: {now}
       # Query range: {since} → {now}
       # ## Summary (total runs, total $, avg $/run, max/min)
       # ## Per-Service Breakdown (table)
       # ## Per-Model Breakdown (table)
       # ## Daily Trend (last 7 days)
       # ## Warnings (services > $0.10/run, models > $0.50/request)
       # ## Recommendations (gpt-4o → gpt-4o-mini ha latency elfogadhato)
       # ## Langfuse Integration (link to Langfuse trace)
       ...

   async def main():
       args = parse_args()
       conn = await asyncpg.connect(os.getenv("AIFLOW_DATABASE__URL", ...))
       records = await fetch_cost_records(conn, since=args.since)
       aggs = {
           "per_service": await aggregate_per_service(records),
           "per_model": await aggregate_per_model(records),
           "per_day": await aggregate_per_day(records),
       }
       markdown = format_markdown_report(records, aggs)
       Path(args.output).write_text(markdown, encoding="utf-8")
       logger.info("cost_baseline.done", output=args.output, records=len(records))
       await conn.close()

2. Futtatas:
   .venv/Scripts/python scripts/cost_baseline.py --output 01_PLAN/COST_BASELINE_REPORT.md

3. COST_BASELINE_REPORT.md struktura (generalt output):

   # AIFlow Cost Baseline Report
   > Generated: 2026-04-09T...
   > Query range: all records (14 rekord cost_records-ben S29 vegen)
   > Branch: feature/v1.3.0-service-excellence

   ## Summary
   - Total runs: N
   - Total cost: $X.XXX USD
   - Avg cost/run: $X.XXXX
   - Most expensive run: run_id X, $Y
   - Cheapest run: run_id X, $Y

   ## Per-Service Breakdown
   | Service | Run count | Total USD | Avg/run | % of total |
   |---------|-----------|-----------|---------|-----------|
   | diagram_generator | N | $X | $Y | Z% |
   | invoice_finder | N | $X | $Y | Z% |
   | aszf_rag_chat | N | $X | $Y | Z% |
   | ...

   ## Per-Model Breakdown
   | Model | Requests | Input tokens | Output tokens | Total USD |
   |-------|----------|--------------|---------------|-----------|
   | gpt-4o-mini | N | N | N | $X |
   | gpt-4o | N | N | N | $X |
   | text-embedding-3-small | N | N | 0 | $X |
   | whisper-1 | N | 0 | 0 | $X |

   ## Daily Trend (last 7 days)
   | Date | Runs | Total USD |
   |------|------|-----------|
   | 2026-04-03 | 2 | $0.004 |
   | 2026-04-04 | 5 | $0.012 |
   | ...

   ## Warnings
   - (ha van) Service X > $0.10/run average — vizsgalni erdemes
   - (ha van) Model Y > $0.50/request — gpt-4o-rol gpt-4o-mini-re cserelhet?

   ## Recommendations
   - (ha van) Service X gpt-4o-t hasznal — ha nem kritikus pontossag, gpt-4o-mini 10x olcsobb
   - ...

   ## Langfuse Integration
   - AIFLOW_LANGFUSE__ENABLED: true / false (.env-ben)
   - Langfuse host: {URL}
   - Hogyan osszehasonlitani a local cost_records-et a cloud Langfuse trace-ekkel:
     1. ...
     2. ...

4. Dokumentacio update (opcionalis):
   01_PLAN/58_POST_SPRINT_HARDENING_PLAN.md — B5.3 DONE markdown
   Bovitsd a /quality-check slash command dokumentaciojat is ha kell.

Gate: scripts/cost_baseline.py futtathato DB-vel, 01_PLAN/COST_BASELINE_REPORT.md
      letezik valos aggregalt adatokkal, 0 regresszio
```

### LEPES 4: /service-hardening 10-pt Audit + Regression

```
1. /service-hardening diagram_generator → 8+/10
   Varhato gyengeseg: #7 dokumentacio, #8 UI (ha valtoztatunk)
   Gap javitas szukseges fokent README.md + error handling

2. /service-hardening spec_writer → 8+/10
   Varhato gyengeseg: #1 unit test (UJ skill, elegendo test kell!),
                     #5 error handling (AIFlowError hasznalata!)
                     #7 dokumentacio

3. /lint-check → 0 error a uj fajlokban
   (scripts/ hiba pre-existing, NEM ez a sprint hatasa)

4. /regression → 1424+ unit test PASS, ne romoljon
   (1424 + ~10 uj B5.1 diagram + ~10 uj B5.2 spec = ~1444 unit test gate)

5. E2E teszt:
   tests/e2e/test_diagram_pipeline.py → 3/3 PASS
   (valos LLM + Kroki + DB)

6. git status ellenorzes:
   - .code-workspace NEM staged
   - document_pipeline.md NEM staged
   - 01_PLAN/100_* / 101_* / CrewAI_*.md NEM staged (nem B5 hatasa)
```

### LEPES 5: Plan + Commit

```
/update-plan → 58 B5 row DONE + datum + commit
CLAUDE.md + 01_PLAN/CLAUDE.md key numbers frissites:
  - 26 → 27 service (uj spec_writer)
  - 6 → 7 skill (uj spec_writer skill)
  - 165 → 170+ API endpoint (uj /api/v1/specs/*)
  - 29 → 30 Alembic migracio (030_add_generated_specs.py)
  - 7 → 9 pipeline template (diagram_generator_v1 + spec_writer_v1)
  - 21 → 22 pipeline adapter (spec_writer_adapter ha UJ)
  - 22 → 23 UI oldal (SpecWriter.tsx)
  - 1424 → ~1444 unit test (B5.1 +5 diagram + B5.2 +10 spec)
  - 80 → ~91 promptfoo test (B5.1 +5 diagram + B5.2 +6 spec)
  - 5 → 6 skill promptfoo config (spec_writer UJ)

Commit:
  feat(sprint-b): B5 diagram hardening + UJ spec_writer skill + cost baseline

  Body:
    - diagram_generator: diagram_type routing (flowchart + sequence + bpmn_swimlane)
      + 3 uj dedikalt prompt (diagram_planner, mermaid_generator, diagram_reviewer)
      + diagram_generator_v1.yaml pipeline template
      + 5 uj unit test + 3 uj E2E test PASS
    - spec_writer UJ SKILL: skills/spec_writer/ (skill.yaml, 3 prompt, workflow,
      5 step, CLI, test_workflow.py). skeleton + prompts + unit tests + promptfoo.
      Adapter + spec_writer_v1.yaml pipeline template. DB migracio 030.
      API endpoint /api/v1/specs/*. UI oldal SpecWriter.tsx.
    - Langfuse cost baseline: scripts/cost_baseline.py + COST_BASELINE_REPORT.md.
    - +11 promptfoo test (80 → 91), +2 pipeline template, +1 skill, +1 migracio

    Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
```

### Teszt Fajl Struktura (B5 vegen)

```
src/aiflow/services/diagram_generator/
  service.py                                         — B5.1 diagram_type routing bovites
  prompts/                                            — UJ MAPPA
    diagram_planner.yaml                              — UJ
    mermaid_generator.yaml                            — UJ
    diagram_reviewer.yaml                             — UJ
  tests/promptfooconfig.yaml                          — UJ 5+ test

src/aiflow/pipeline/adapters/diagram_adapter.py       — diagram_type passing fix
src/aiflow/pipeline/adapters/spec_writer_adapter.py   — UJ (ha generic nem eleg)
src/aiflow/pipeline/builtin_templates/
  diagram_generator_v1.yaml                           — UJ
  spec_writer_v1.yaml                                 — UJ

skills/spec_writer/                                   — TELJES UJ SKILL
  skill.yaml
  skill_config.yaml
  __init__.py
  __main__.py
  models/__init__.py
  prompts/
    spec_analyzer.yaml
    spec_generator.yaml
    spec_reviewer.yaml
  workflows/
    __init__.py
    spec_writing.py
  tests/
    test_workflow.py                                  — 5+ uj unit test
    promptfooconfig.yaml                              — 6+ uj promptfoo test

src/aiflow/api/v1/spec_writer.py                      — UJ API router
src/aiflow/state/models/generated_specs.py            — UJ ORM modell
alembic/versions/030_add_generated_specs.py           — UJ migracio

aiflow-admin/src/pages-new/SpecWriter.tsx             — UJ UI oldal

tests/unit/services/test_diagram_generator_service.py — +5 uj diagram test
tests/e2e/test_diagram_pipeline.py                    — UJ 3 E2E test

scripts/cost_baseline.py                              — UJ generator script
01_PLAN/COST_BASELINE_REPORT.md                       — UJ generalt riport

Osszesen:
  ~15 UJ fajl
  ~6 MODOSITOTT fajl
  1 UJ DB migracio
  +20 unit test (5 diagram + 15 spec)
  +11 promptfoo test (5 diagram + 6 spec)
  +3 E2E test
```

---

## VEGREHAJTAS SORRENDJE

```
--- LEPES 1: diagram_generator hardening ---
/dev-step "B5.1.1 — diagram_adapter diagram_type passing fix + unit test"
/dev-step "B5.1.2 — DiagramGeneratorService.generate signature diagram_type param"
/new-prompt src/aiflow/services/diagram_generator/prompts/diagram_planner.yaml
/new-prompt src/aiflow/services/diagram_generator/prompts/mermaid_generator.yaml
/new-prompt src/aiflow/services/diagram_generator/prompts/diagram_reviewer.yaml
/dev-step "B5.1.3 — diagram_generator_v1.yaml pipeline template"
/dev-step "B5.1.4 — 5 uj unit test (sequence, bpmn_swimlane, adapter passing, reviewer, fallback)"
/dev-step "B5.1.5 — promptfoo config 5+ teszt"
npx promptfoo eval -c src/aiflow/services/diagram_generator/tests/promptfooconfig.yaml  # gate 5/5
/dev-step "B5.1.6 — 3 E2E test (pipeline runner + valos LLM + Kroki + DB)"
/pipeline-test diagram_generator_v1
/service-hardening diagram_generator  # gate 8+/10

--- LEPES 2: spec_writer UJ SKILL ---
/dev-step "B5.2.1 — skills/spec_writer/ scaffold (skill.yaml, models, init)"
/new-prompt skills/spec_writer/prompts/spec_analyzer.yaml
/new-prompt skills/spec_writer/prompts/spec_generator.yaml
/new-prompt skills/spec_writer/prompts/spec_reviewer.yaml
/new-step skills/spec_writer/workflows/spec_writing.py  (5 step)
/dev-step "B5.2.2 — __main__.py CLI"
/dev-step "B5.2.3 — pipeline template spec_writer_v1.yaml"
/dev-step "B5.2.4 — spec_writer_adapter.py (ha kell)"
/dev-step "B5.2.5 — Alembic migracio 030_add_generated_specs.py + alembic upgrade head"
/dev-step "B5.2.6 — API endpoint src/aiflow/api/v1/spec_writer.py + router register"
/dev-step "B5.2.7 — UI oldal SpecWriter.tsx + route"
/new-test skills/spec_writer/tests/test_workflow.py  (5+ teszt)
/dev-step "B5.2.8 — promptfoo config 6+ teszt"
npx promptfoo eval -c skills/spec_writer/tests/promptfooconfig.yaml  # gate 90%+
/pipeline-test spec_writer_v1
/service-hardening spec_writer  # gate 8+/10

--- LEPES 3: cost baseline ---
/dev-step "B5.3.1 — scripts/cost_baseline.py (aggregation + markdown generation)"
.venv/Scripts/python scripts/cost_baseline.py --output 01_PLAN/COST_BASELINE_REPORT.md
# Verify: cat 01_PLAN/COST_BASELINE_REPORT.md — strukturalt, 14 rekordos riport

--- LEPES 4: regresszio + gate ---
/lint-check → 0 error a uj fajlokban
/regression → ~1444 unit test PASS
(pre-existing 40 scripts/ hiba NEM az uj munka hatasa)

--- LEPES 5: plan + commit ---
/update-plan → 58 B5 DONE + key numbers (26→27 service, 6→7 skill, 165→170+ endpoint,
                29→30 migracio, 7→9 pipeline template, 22→23 UI, 1424→~1444 unit,
                80→~91 promptfoo, 5→6 skill promptfoo config)
git commit feat(sprint-b): B5 diagram hardening + spec_writer UJ skill + cost baseline
git commit docs: session 30 prompt  (ha mar nem committed)
```

---

## KORNYEZET ELLENORZES

```bash
git branch --show-current                                              # → feature/v1.3.0-service-excellence
git log --oneline -3                                                   # → 82b1dd5, e4f322e, 9eb2769
.venv/Scripts/python -m pytest tests/unit/ -q --ignore=tests/unit/vectorstore/test_search.py 2>&1 | tail -1
                                                                       # → 1424 passed
.venv/Scripts/ruff check skills/ 2>&1 | tail -1                       # → All checks passed!

# Diagram generator verify (jelenlegi state):
ls src/aiflow/services/diagram_generator/service.py                    # letezik
ls src/aiflow/services/diagram_generator/prompts/ 2>&1                 # NINCS — UJ MAPPA KELL
ls src/aiflow/pipeline/builtin_templates/diagram_generator_v1.yaml 2>&1  # NINCS — UJ KELL
ls tests/unit/services/test_diagram_generator_service.py              # letezik

# Spec writer verify (jelenlegi state):
ls skills/spec_writer/ 2>&1                                            # NINCS — TELJES UJ SKILL
ls src/aiflow/api/v1/spec_writer.py 2>&1                               # NINCS — UJ
ls aiflow-admin/src/pages-new/SpecWriter.tsx 2>&1                      # NINCS — UJ

# Cost baseline verify (jelenlegi state):
ls scripts/cost_baseline.py 2>&1                                       # NINCS — UJ
ls 01_PLAN/COST_BASELINE_REPORT.md 2>&1                                # NINCS — UJ

# cost_records tabla (mar van adat):
.venv/Scripts/python -c "
import asyncpg, asyncio
async def m():
    c = await asyncpg.connect('postgresql://aiflow:aiflow_dev_password@localhost:5433/aiflow_dev')
    rows = await c.fetch('SELECT COUNT(*) AS n, SUM(cost_usd) AS total FROM cost_records')
    print(dict(rows[0]))
    await c.close()
asyncio.run(m())
"
# → {'n': 14, 'total': 0.X...}

# Docker services:
docker ps | grep -E "07_ai_flow.*(db|redis|kroki).*Up" | wc -l         # → 3

# Langfuse env:
grep "^AIFLOW_LANGFUSE__ENABLED" .env                                  # → true/false

# OPENAI_API_KEY:
grep -c "^OPENAI_API_KEY=" .env                                        # → 1

# npx promptfoo:
which npx 2>&1                                                         # → /c/Program Files/nodejs/npx
```

---

## S29 TANULSAGAI (alkalmazando S30-ban!)

1. **Promptfoo JS assertek `return` kotelezo** — multi-line `value: |` blokkban a last-expression nem auto-return-el. A B5.1 diagram_reviewer teszteknel es a B5.2 spec_reviewer teszteknel **mindig `return`-elj** az asszertekben. Single-line `value: "..."` form-nal nem kell.

2. **Router prompt pattern multi-task skill-nel** — ha tobb prompt-ot kellene promptfoo-ban tesztelni (pl. spec_writer: analyzer + generator + reviewer), a promptfoo 1-test-per-prompt cross-product trap-et elkerulendo **HASZNALJ ROUTER PROMPT-OT** `task` valtozoval. `skills/invoice_finder/tests/promptfooconfig.yaml` a mintai pelda. `defaultTest.vars: {...}` kell az unused vars-hoz hogy a strict template rendering ne bukjon.

3. **LLM literal reading** — a B4.2 invoice_processor kiabrandito tanulsag: a gpt-4o-mini 5%-ot "kijavitja" 27%-ra (Hungarian standard VAT). B5.1 diagram + B5.2 spec promptoknal **expliciten mondd**: "Read the X EXACTLY as given, DO NOT replace with standard/default values."

4. **max_tokens provider config szukseges ha json_object + hosszu output** — a B4.2 cubix teszt (30 min microservice transcript) JSON truncation miatt bukott amig nem adtunk `max_tokens: 4096`-ot a provider config-ba. B5.1 sequence diagram + B5.2 markdown spec hosszu output eseten allitsd be a providers.config.max_tokens-t.

5. **Workflow valtoztatas → valtoztasd a teszt mock-okat** — B4.2 cubix split miatt a `test_structure_calls_llm` eltort, mert a regi teszt `mock_prompts.get.assert_called_once_with(...)` egyet var, de most 3-szor hivjuk. A **teszt mock update-eket azonnal csinald meg a workflow refaktor utan**, ne varj a /regression-re.

6. **diagram_adapter input_schema fontos** — B5.1-ben a `GenerateDiagramInput` mar tartalmazza a `diagram_type` mezot, de a service NEM hasznalja! **Az uj adapter parameter passing tesztelhetoseget kulon unit teszttel fedd le** (`test_diagram_adapter_passes_type`).

7. **UJ skill létrehozása — /archive:new-skill HASZNALD** — ha letezik, a spec_writer skeleton kezdete scaffold-dal gyorsabb. Ha nem, masolasi mintaul **`skills/cubix_course_capture/`** (egyszeru LLM skill, nem tul komplex).

8. **B4.2 process_documentation eredmenyeinek ORZESE** — a diagram_generator service kozvetlenul hivja a process_documentation step-jeit. Ha refaktorálod, NE romlas a process_documentation promptfoo 14/14!

---

## MEGLEVO KOD REFERENCIAK (olvasd el mielott irsz!)

```
# Diagram generator (B5.1 alap):
src/aiflow/services/diagram_generator/service.py              — 238 sor, wraps process_documentation
src/aiflow/services/diagram_generator/__init__.py             — export
src/aiflow/api/v1/diagram_generator.py                        — CRUD API
src/aiflow/pipeline/adapters/diagram_adapter.py               — adapter (diagram_type bug!)
tests/unit/services/test_diagram_generator_service.py         — mock asyncpg tesztek
aiflow-admin/src/pages-new/ProcessDocs.tsx                    — UI lista (csak listazas)

# Process documentation (B4.2 hardened, referencia):
skills/process_documentation/workflow.py                       — 5 step pipeline
skills/process_documentation/prompts/                          — 5 YAML (classifier, elaborator, extractor, mermaid_flowchart, reviewer)
skills/process_documentation/tests/promptfooconfig.yaml        — 14/14 B4.2 (strict shape mapping pattern!)
skills/process_documentation/tools/drawio_exporter.py          — DrawIO XML export
skills/process_documentation/tools/kroki_renderer.py           — Kroki SVG render

# Skill mintaul (spec_writer letrehozashoz, egyszeru LLM skill):
skills/cubix_course_capture/
  skill.yaml
  skill_config.yaml
  __init__.py
  __main__.py
  models/__init__.py                                           — Pydantic models
  prompts/section_detector.yaml + summary_generator.yaml + vocabulary_extractor.yaml
  workflows/transcript_pipeline.py                             — 6 step DAG (B4.2 split!)
  tests/test_workflow.py                                       — 13 teszt
  tests/promptfooconfig.yaml                                   — 12 test case

skills/invoice_processor/
  workflows/process.py                                         — komplex workflow mintaul
  prompts/                                                     — 4 YAML
  tests/test_workflow.py                                       — 14 teszt

# Invoice finder (router prompt pattern B4.2-bol, spec_writer promptfoo mintaul):
skills/invoice_finder/tests/promptfooconfig.yaml               — router prompt 4 task-kal

# Cost tracker + cost API (B5.3 alap):
src/aiflow/observability/cost_tracker.py                       — CostTracker class
src/aiflow/api/v1/costs.py                                     — /api/v1/costs/summary + breakdown
aiflow-admin/src/pages-new/Costs.tsx                           — UI (DataTable)

# Alembic migracio mintaul:
alembic/versions/006_add_cost_records.py                       — cost_records creation
alembic/versions/029_*.py                                       — legutobbi migracio

# Pipeline template mintaul (B5.1 + B5.2 templ-hez):
src/aiflow/pipeline/builtin_templates/invoice_finder_v3.yaml   — 8 step template
src/aiflow/pipeline/builtin_templates/invoice_finder_v3_offline.yaml
src/aiflow/pipeline/builtin_templates/email_triage.yaml        — egyszerubb template

# Adapter mintaul:
src/aiflow/pipeline/adapters/diagram_adapter.py                — egyszeru adapter (B5.1-ben javitsd!)
src/aiflow/pipeline/adapters/invoice_field_extract_adapter.py  — (ha letezik) kompleksebb pelda

# UI oldal mintaul:
aiflow-admin/src/pages-new/ProcessDocs.tsx                     — diagram lista + render
aiflow-admin/src/pages-new/Rag.tsx                             — ha letezik, chat + markdown
aiflow-admin/src/pages-new/Costs.tsx                           — DataTable layout

# API endpoint mintaul:
src/aiflow/api/v1/diagram_generator.py                         — diagram CRUD router
src/aiflow/api/v1/invoice_finder.py                            — ha letezik

# Promptfoo + service-hardening slash commands:
.claude/commands/service-hardening.md                          — 10-point audit
.claude/commands/new-skill.md                                  — skill scaffold
.claude/commands/new-pipeline.md                               — pipeline template scaffold
.claude/commands/new-prompt.md                                 — prompt YAML scaffold
.claude/commands/new-step.md                                   — workflow step scaffold
.claude/commands/pipeline-test.md                              — E2E pipeline test
.claude/commands/dev-step.md                                   — standard dev cycle

# Memory files (S29-bol — alkalmazando B5-ben!):
memory/feedback_promptfoo_js_assertions.md                     — explicit `return` multi-line asszertben
memory/feedback_promptfoo_router_prompt.md                     — router prompt pattern multi-task skill-nel
memory/feedback_promptfoo_windows_infra.md                     — exec provider Windows fix (B5-ben direct provider kell, nem exec)
memory/feedback_aszf_rag_prompt_routing.md                     — role-routed prompt gotcha
```

---

## SPRINT B UTEMTERV (S29 utan, frissitett)

```
S19: B0      — DONE (4b09aad) — 5-layer arch + qbpp + prompt API + OpenAPI
S20: B1.1    — DONE (f6670a1) — 4 LLM guardrail prompt + llm_guards.py + 27 promptfoo
S21: B1.2    — DONE (7cec90b) — 5 guardrails.yaml + PIIMaskingMode + 31 teszt
S22: B2.1    — DONE (51ce1bf) — Core infra service tesztek (65 test, Tier 1)
S23: B2.2    — DONE (62e829b) — v1.2.0 service tesztek (65 test, Tier 2)
S24: B3.1    — DONE (372e08b) — Invoice Finder pipeline + email search + doc acquire (29 test)
S25: B3.2    — DONE (aecce10) — Invoice Finder extract + payment + report + notify (16 test)
S26a: B3.E2E.P0 — DONE (0b5e542) — Outlook COM multi-account fetch + email intent
S26a: B3.E2E.P1 — DONE (f1f0029) — offline invoice finder pipeline (20/20 PASS)
S27a: B3.E2E.P2 — DONE (8b10fd6) — PipelineRunner DB persistence integration
S27a: B3.E2E.P3 — DONE (70f505f) — full 8-step pipeline on 3 Outlook accounts
S27b: B3.5   — DONE (4579cd2) — confidence scoring hardening + review routing (36 test)
S28: B4.1    — DONE (9eb2769) — Skill hardening: aszf_rag 12/12 + email_intent 16/16, +9 promptfoo
S29: B4.2    — DONE (e4f322e) — Skill hardening: process_docs + invoice + cubix split + invoice_finder new, +26 promptfoo (80 total)
S30: B5      ← KOVETKEZO SESSION — Diagram hardening + spec_writer UJ skill + cost baseline
S31: B6      — Portal struktura + 4 journey tervezes + navigacio redesign
S32: B7      — Verification Page v2 (bounding box, diff, per-field confidence szin)
S33: B8      — UI Journey implementacio (top 3 journey + dark mode)
S34: B9      — Docker containerization + UI pipeline trigger + deploy teszt
S35: B10     — POST-AUDIT + javitasok
S36: B11     — v1.3.0 tag + merge
```

---

## FONTOS SZABALYOK (emlekeztetok)

- **NE BONTSD szét a B5.1-et + B5.2-t + B5.3-at kulon commit-ra** — egy feature commit ami mindharmat fedi (lasd a session prompt-ban a commit body sablon).
- **Spec_writer skill = LLM skill (workflow + prompts)** NEM szolgaltatas src/aiflow/services/ alatt (az infra) — a plan terve ezt mondja "Specifikacio Iro AIFlow Szolgaltatas"-nak de a CLI `python -m skills.spec_writer` pattern miatt skill-be kell.
- **Diagram generator = service** (src/aiflow/services/diagram_generator/) — NEM skill, mert mar letezik mint service es a process_documentation skillt wrappeli.
- **Alembic migracio = UJ FAJL, nem raw SQL** — per CLAUDE.md szabaly. `alembic revision --autogenerate -m "add generated_specs"` vagy manual 030_*.py fajl.
- **Async-first, Pydantic everywhere, structlog always** — per CLAUDE.md.
- **AIFlowError + is_transient flag** — az uj spec_writer workflow-ban pl. transient LLM hibahoz `is_transient=True`, permanent validacio-hoz `False`.
- **`/new-skill` + `/new-prompt` + `/new-pipeline`** — a slash command-ok hasznalata gyorsitja a scaffold-ot.
- **Valos teszteles, NEM mock** — E2E teszt valos LLM + valos Kroki Docker + valos DB. Mock csak unit teszt szintjen.
- **Langfuse cost tracking mar mukodik** — NE integralj ujra, csak a cost_records tabla query-jet ird + a riport markdown-generalasat.
- **`.code-workspace`, `document_pipeline.md`, `CrewAI_*.md`, `100_*.md`, `101_*.md` NE commitold** — ezek lokalis / kulso tervek.
- **24 uj promptfoo test cel** (5 diagram + 6 spec + tartalek) — de minimum 11 (5+6).
- **~20 uj unit test cel** (5 diagram B5.1 + 10-15 spec B5.2) — de minimum 15.
- **3 E2E test kotelezo B5.1-re** (flowchart + sequence + swimlane), valos LLM + Kroki.
- **UI oldal kotelezo B5.2-re** — CLI nem eleg, UI-bol is mukodni kell (source: backend badge!).
- **10-pt service hardening 8+/10 gate** — mind a ket service/skill.

---

## B5 GATE CHECKLIST

```
B5.1 — Diagram Generator Hardening:
[ ] diagram_adapter.py diagram_type passing fix
[ ] DiagramGeneratorService.generate signature bovites (diagram_type param)
[ ] src/aiflow/services/diagram_generator/prompts/ UJ MAPPA
[ ] diagram_planner.yaml UJ
[ ] mermaid_generator.yaml UJ (strict shape mapping + few-shot)
[ ] diagram_reviewer.yaml UJ (auto-fix output)
[ ] diagram_generator_v1.yaml pipeline template UJ
[ ] 5 uj unit test (sequence, swimlane, adapter passing, reviewer, fallback) PASS
[ ] 3 uj E2E test (valos LLM + Kroki + DB) PASS
[ ] promptfooconfig.yaml 5+ test case 95%+ pass rate
[ ] /service-hardening diagram_generator → 8+/10

B5.2 — Spec Writer UJ Skill:
[ ] skills/spec_writer/skill.yaml letrehozva
[ ] skills/spec_writer/skill_config.yaml letrehozva
[ ] skills/spec_writer/__init__.py + __main__.py (CLI)
[ ] models/__init__.py (5 Pydantic modell)
[ ] prompts/spec_analyzer.yaml
[ ] prompts/spec_generator.yaml
[ ] prompts/spec_reviewer.yaml
[ ] workflows/spec_writing.py (5 step)
[ ] tests/test_workflow.py 5+ teszt PASS
[ ] tests/promptfooconfig.yaml 6+ teszt 90%+ pass rate
[ ] src/aiflow/pipeline/builtin_templates/spec_writer_v1.yaml
[ ] src/aiflow/pipeline/adapters/spec_writer_adapter.py (ha kell)
[ ] alembic/versions/030_add_generated_specs.py + alembic upgrade head
[ ] src/aiflow/api/v1/spec_writer.py (router + register)
[ ] aiflow-admin/src/pages-new/SpecWriter.tsx (UI + route)
[ ] CLI futtathato: python -m skills.spec_writer --input "..." --type feature
[ ] POST /api/v1/specs/write 200 OK "source": "backend"
[ ] /service-hardening spec_writer → 8+/10

B5.3 — Cost Baseline Report:
[ ] scripts/cost_baseline.py letrehozva es futtathato
[ ] 01_PLAN/COST_BASELINE_REPORT.md generalt tartalommal
[ ] Langfuse integracio dokumentalva a riportban (vagy warning ha nem enabled)

Ossz:
[ ] /lint-check → 0 error uj fajlokban
[ ] /regression → ~1444 unit test PASS (+20 uj B5-bol)
[ ] E2E test: tests/e2e/test_diagram_pipeline.py 3/3 PASS
[ ] /update-plan → 58 B5 DONE + key numbers frissitve
[ ] git commit: feat(sprint-b): B5 diagram hardening + spec_writer UJ skill + cost baseline
[ ] git status sima — semmilyen lokalis state staged (sem code-workspace, sem document_pipeline.md)
[ ] Memory update (ha non-obvious gotcha kerult elo B5-ben)
```

---

## BECSULT SCOPE

- **~15 uj fajl** (3 diagram prompt + spec_writer teljes skill + pipeline + adapter + API + migracio + UI + cost_baseline script + report)
- **~6 modositott fajl** (diagram_adapter, diagram_generator service, test_diagram_generator_service, diagram_generator API, costs/analytics, 58_plan)
- **+20 unit test** (diagram 5 + spec 10-15)
- **+11 promptfoo test** (diagram 5 + spec 6)
- **+3 E2E test** (diagram pipeline)
- **+1 DB migracio** (030_add_generated_specs)
- **+2 pipeline template** (diagram_generator_v1 + spec_writer_v1)
- **+1 UJ skill** (spec_writer)
- **+1 UI oldal** (SpecWriter.tsx)

**Ez egy intenziv session** — a spec_writer nulla-bol valo letrehozasa a leghosszabb lepes. Ha szukseges, a 3 komponenst (B5.1 + B5.2 + B5.3) kulon session-re is lehet osztani, de az S30 cel mind a harom egyszerre.

---

*Kovetkezo ervenyben: S30 = B5 (Diagram + Spec writer + Cost baseline) → S31 = B6 (Portal ujratervezes + 4 journey tervezes)*
