# AIFlow Skills Directory

## Working Skills (tested with real data)
- **process_documentation** (ai) - BPMN diagrams from natural language
  - 5-step pipeline: classify -> elaborate -> extract -> review -> generate + export
  - Output: .mmd, .svg, .drawio, .drawio (BPMN swimlane), .md, .json
  - DrawIO: Lesotho-grade builder (3423 stencils, native mxgraph shapes)
  - Run: `python -m skills.process_documentation --input "..." --output ./out`

- **cubix_course_capture** (hybrid) - Course video capture + transcript
  - Transcript pipeline: probe -> extract_audio -> chunk -> STT -> merge -> structure
  - RPA: Robot Framework (login, scan, video open) + Playwright (fallback)
  - State: pipeline_state.json with resume support
  - Run: `python -m skills.cubix_course_capture transcript --input video.mkv`

## Planned Skills
- **aszf_rag_chat** (ai) - RAG chat for legal documents (IN PROGRESS)
- **email_intent_processor** (ai) - Email classification and routing (TODO)
- **cfpb_complaint_router** (ai) - ML-based complaint classification (TODO)
- **qbpp_test_automation** (rpa) - Insurance calculator test automation (TODO)

## Skill Structure (every skill is self-contained)
```
skills/<name>/
  skill.yaml           # Manifest (name, version, capabilities, models, workflows)
  skill_config.yaml    # Runtime config (models, output, quality thresholds)
  __init__.py          # Service initialization
  __main__.py          # CLI entry point (python -m skills.<name>)
  models/              # Pydantic I/O models
  prompts/             # YAML prompts (PromptDefinition format)
  workflows/           # Step functions + @workflow registration
  tools/               # Skill-specific tools (drawio, kroki, etc.)
  tests/               # Unit + integration tests + datasets/
  ui/                  # Skill-specific Reflex UI components
```

## Rules
- Prompts in YAML only (PromptDefinition format with Jinja2 templates)
- @test_registry header on every test file
- skill.yaml + skill_config.yaml MUST exist
- __main__.py CLI entry point MUST exist
- Use SkillRunner.from_env() for service initialization
