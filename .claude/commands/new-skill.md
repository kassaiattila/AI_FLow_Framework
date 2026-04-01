Generate a complete new AIFlow Skill scaffold.

Ask me for:
1. Skill name (snake_case)
2. Display name
3. Skill type: ai / rpa / hybrid
4. Brief description
5. Required LLM models
6. Workflow steps and their responsibilities
7. Pilot project path (if porting from existing code)

## MANDATORY checklist before generating:

1. **Read the relevant plan** in `01_PLAN/` for this skill
2. **Check pilot project** - if porting, read the pilot code FIRST and port ALL functionality
3. **Read reference materials** - check `skills/*/reference/` for relevant guides
4. **Follow `01_PLAN/30_RAG_PRODUCTION_PLAN.md`** for RAG skills
5. **Use Alembic** for any new DB tables (NEVER raw SQL)

## Generate the FULL skill directory:

```
skills/{name}/
    skill.yaml            # Manifest (name, version, models, workflows)
    skill_config.yaml     # Runtime config (models, thresholds, output)
    __init__.py           # Service init (ModelClient, PromptManager)
    __main__.py           # CLI entry point: python -m skills.{name}
    workflow.py            # Re-exports from workflows/

    workflows/
        __init__.py
        {pipeline_name}.py  # Step functions with @step + @workflow

    models/
        __init__.py         # Pydantic I/O models for every step

    schemas/                # Configurable JSON schema definitions (versioned!)
        v1/
            intents.json    # Intent definitions (if classification skill)
            entities.json   # Entity types + extraction methods
            document_types.json  # Attachment processing strategies
            routing_rules.json   # Routing matrix

    prompts/
        {step_name}.yaml    # PromptDefinition YAML for each LLM step

    classifiers/            # ML + LLM classifiers (if hybrid skill)
        sklearn_classifier.py   # Classical ML (if porting from pilot)
        llm_classifier.py       # LLM-based classification

    tools/                  # Skill-specific tools (drawio, ffmpeg, etc.)

    tests/
        __init__.py
        test_workflow.py    # Unit tests (mocked LLM) - @test_registry header!
        test_integration.py # Real LLM tests (@pytest.mark.integration)
        datasets/
            sample_data.yaml

    reference/              # If porting: copy relevant pilot docs/guides
        CLAUDE.md           # "NE modositsd - fix referencia"

    ui/                     # Skill-specific Reflex components (if GUI needed)
```

## Critical rules:

- Every step: `async def step_fn(data: dict) -> dict`
- Use `ModelClient(generation_backend=backend, embedding_backend=backend)` - BOTH backends!
- Use `PromptDefinition.compile(variables={...})` for all LLM calls
- Use `structlog` for logging, NEVER print()
- Run `pytest` after generating - must pass
- If RAG skill: follow `01_PLAN/30_RAG_PRODUCTION_PLAN.md` checklist
- If DB needed: create Alembic migration, not raw SQL
- **If service generalization**: check `01_PLAN/42_SERVICE_GENERALIZATION_PLAN.md` — skill a megfelelo service-bol epitkezik?

## VALOS teszteles (SOHA ne mock/fake!):
- **CLI teszt:** `python -m skills.{name} --input test_data --output ./out` — valos output ellenorzes
- **Promptfoo:** Minimum 10 valos LLM teszt eset (4 pozitiv, 2 negativ, 2 edge, 1 adversarial, 1 nyelvi)
- **Integration:** Valos fuggoosegek (PostgreSQL, Redis, Docling) — NEM in-memory mock
- **Ha UI van:** Playwright E2E teszt (navigate → upload → process → result → screenshot)
- **Egy skill CSAK AKKOR "KESZ" ha end-to-end valos adat feldolgozason atment**
