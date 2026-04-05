---
name: aiflow-services
description: >
  AIFlow service architektura, konvenciok, technologiai dontesek. Hasznald
  amikor service-t fejlesztesz, guardrail-t konfiguralsz, skill-t hardeningsz,
  vagy az architektura mintakrol kell donteni.
allowed-tools: Read, Write, Grep, Glob, Bash
---

# AIFlow Service Architecture

## Architecture Patterns

- **Step** = atomic unit with `@step` decorator, takes dict → returns dict
- **SkillRunner** = sequential step executor with service injection (models, prompts, ctx)
- **WorkflowRunner** = DAG executor with branching/checkpoints (complex workflows)
- **Skill** = self-contained package (workflows + tools + prompts + tests + UI + skill.yaml)
  Types: ai, rpa, hybrid
- **Service** = altalanos, ujrahasznalato epitokocka (src/aiflow/services/)
- **ModelClient** = unified LLM facade (generate, embed) via LiteLLM backend
- **PromptManager** = YAML prompt loading with Jinja2 templates + Langfuse sync + cache
- **Skill Instance** = configured deployment of a Skill template per customer

## Configurable JSON Schema System

Skills use versioned JSON schemas:
```
skills/{name}/schemas/v1/
  intents.json          # Intent definiciok
  entities.json         # Entity tipusok
  document_types.json   # Csatolmany tipusok
  routing_rules.json    # Routing matrix
```

## Multi-layer Document Processing

1. **Docling** (local, free) — PDF/DOCX/XLSX/HTML — always first
2. **Azure Document Intelligence** (cloud) — scan/OCR/handwriting — if docling fails
3. **LLM Vision** (OpenAI) — image content — last resort

## Hybrid Classification

- **sklearn ML** (TF-IDF + LinearSVC) — <1ms, $0 — fast screening
- **LLM** (gpt-4o-mini) — if ML confidence < threshold

## Skills (5 db)

| Skill | Tipus | Allapot | Promptfoo |
|-------|-------|---------|-----------|
| process_documentation | AI | Production | 90% |
| aszf_rag_chat | AI | Production | 86% |
| email_intent_processor | AI | Development | 85% |
| invoice_processor | AI | Development | 80% |
| cubix_course_capture | Hybrid | Production | 90% |

## Skill Running

```bash
# CLI (recommended for testing):
python -m skills.process_documentation --input "..." --output ./out
python -m skills.cubix_course_capture transcript --input video.mkv
python -m skills.aszf_rag_chat ingest --source ./docs/ --collection my-docs
python -m skills.aszf_rag_chat query --question "..." --role expert

# Programmatic:
from aiflow.engine.skill_runner import SkillRunner
runner = SkillRunner.from_env(prompt_dirs=["skills/X/prompts"])
result = await runner.run_steps([step1, step2], {"input": "..."})
```

## Guardrail Framework (Sprint A-bol)

```
src/aiflow/guardrails/
  base.py          # GuardrailBase ABC
  input_guard.py   # Prompt injection, PII, length
  output_guard.py  # Content safety, hallucination, PII leak
  scope_guard.py   # In-scope / Out-of-scope / Dangerous
  config.py        # Per-service YAML config loader
```

Rule-based (gyors, $0) → LLM-based (preciz, Sprint B B1) → Per-service config (B1.2)

## 10-Point Production Checklist (per service/skill)

1. UNIT TESZT — >= 5 teszt, >= 70% coverage
2. INTEGRACIO — >= 1 valos DB-vel (ha DB-t hasznal)
3. API TESZT — minden endpoint curl, source=backend
4. PROMPT TESZT — promptfoo >= 95% pass (ha LLM-et hasznal)
5. ERROR HANDLING — AIFlowError leszarmazott, is_transient flag
6. LOGGING — structlog, NEM print(), event+key=value
7. DOKUMENTACIO — docstring fo osztaly + publikus metodus
8. UI — oldal mukodik, source badge, 0 console error
9. INPUT GUARDRAIL — injection + PII (per-skill config!)
10. OUTPUT GUARDRAIL — hallucination, scope, PII leak check

## Frontend Stability

- Meglevo `pages/*.tsx`: KIZAROLAG bugfix
- Kozos komponensek (DataTable, PageLayout): modositas CSAK backward-compatible
- `router.tsx`: uj route hozzaadhato, meglevo NEM modosul
- `locales/*.json`: uj kulcs hozzaadhato, meglevo NEM modosul

## Deployments

- `deployments/{customer}/deployment.yaml` — per-customer config
- Skill Instance = running config (YAML), multiple instances per customer
- Docker Compose: PostgreSQL 5433, Redis 6379, Kroki 8000, API 8102, UI 5174
