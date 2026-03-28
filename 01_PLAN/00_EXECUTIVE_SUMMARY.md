# AIFlow - Vallalati AI Automatizacios Keretrendszer

## Zoldmezos Terv - Executive Summary

**Projekt:** AIFlow Enterprise AI Automation Framework
**Ceg:** BestIx Kft (BestIxCom Kft)
**Datum:** 2026-03-27
**Status:** Terv

---

## Mi az AIFlow?

Python-nativ vallalati keretrendszer AI-alapu automatizacios workflow-ok epitesere, uzemeltetesere es skalazasara. Architekturalis inspiracio: FastAPI (clean DX), Celery (distributed execution), dbt (config-as-code + testing).

## Miert zoldmezos?

A meglevo POC (Process Doc AI Agent v1.2.0) ertekei:
- Bevalt mintak: Workflow Registry, Langfuse SSOT, Promptfoo teszteles
- Iparagi best practice-ek dokumentalva (Andrew Ng 4 minta, 2-szintu architektura)
- Executive briefing 8 pillere

De a POC korlatai (linearis pipeline, in-memory state, tight coupling) nem bovithetok 100-300+ workflow-ra. Tiszta lap kell.

## Fobb Architekturalis Dontesek

| Dontes | Indoklas |
|--------|----------|
| DAG-alapu workflow engine | Nem linearis - elagazas, ciklus, sub-workflow |
| Step mint first-class citizen | Ujrahasznosithato, tipusos I/O, fuggetlenul tesztelheto |
| 2-szintu agent rendszer | Andrew Ng: max 6 specialist, orchestrator + specialist |
| Skill = onallo csomag | Workflow + agents + prompts + tests egyutt, plugin-szeru |
| arq + Redis queue | Nativ asyncio, horizontalis skalazas worker-ekkel |
| PostgreSQL state | Elosztott, checkpoint/resume, audit, cost tracking |
| Langfuse + OpenTelemetry | LLM observability + infra tracing kulon-kulon |
| Evaluation-driven | 100+ teszt eset minimum, Promptfoo + egyedi scorers |

## Meglevo POC Sorsa

A POC-ot az **elso Skill**-kent portoljuk at az uj keretrendszerbe:
`skills/process_documentation/` - teljes workflow, agents, prompts, tests

## Implementacios Fazisok

| Fazis | Het | Tartalom |
|-------|-----|----------|
| 1. Foundation | 1-3 | Core, State, LLM, Docker, structlog |
| 2. Engine + Models | 4-6 | Step, DAG, Workflow, Runner, ModelClient, RetryPolicy |
| 3. Agents + Prompts + Vectors | 7-9 | Agent system, Langfuse SSOT, Embedding, pgvector |
| 4. Skills (6 db) | 10-13 | POC portalas, 6 skill, 600+ teszt |
| 5. Execution + API + Security | 14-16 | Queue, Worker, FastAPI, RBAC, Frontend scaffold |
| 6. CLI + Observability | 17-19 | CLI, Tracing, Cost, SLA, Dashboards |
| 7. Production | 20-22 | Checkpoint, HITL, Scheduler, Kafka, K8s, CI/CD, Audit |

## Dokumentumok

### Core Architektura
| Fajl | Tartalom |
|------|----------|
| [01_ARCHITECTURE.md](01_ARCHITECTURE.md) | Reszletes architektura (Engine, Agents, Skills, Prompts, Execution, Security) |
| [02_DIRECTORY_STRUCTURE.md](02_DIRECTORY_STRUCTURE.md) | Teljes konyvtar struktura |
| [03_DATABASE_SCHEMA.md](03_DATABASE_SCHEMA.md) | PostgreSQL schema (35 tabla, 12 view, indexek) |
| [04_IMPLEMENTATION_PHASES.md](04_IMPLEMENTATION_PHASES.md) | 7 fazis, 22 het, heti lebontas |
| [05_TECH_STACK.md](05_TECH_STACK.md) | Tech stack, fuggosegek, pyproject.toml |
| [06_CLAUDE_CODE_INTEGRATION.md](06_CLAUDE_CODE_INTEGRATION.md) | Claude Code + MCP a teljes eletciklusban |

### Vallalati Kovetelmernyek
| Fajl | Tartalom |
|------|----------|
| [07_VERSION_LIFECYCLE.md](07_VERSION_LIFECYCLE.md) | Verzikezeles, DEV-TEST-UAT-PROD, CI/CD, Git branching |
| [08_ERROR_HANDLING_DEBUGGING.md](08_ERROR_HANDLING_DEBUGGING.md) | Hibakezelés, debugging, DLQ, alerting |
| [09_MIDDLEWARE_INTEGRATION.md](09_MIDDLEWARE_INTEGRATION.md) | Kafka, RabbitMQ, Azure SB, AWS SQS integracio |
| [10_BUSINESS_AUDIT_DOCS.md](10_BUSINESS_AUDIT_DOCS.md) | Uzleti dokumentacio, audit trail, compliance, dashboards |

### Valosagos Peldak
| Fajl | Tartalom |
|------|----------|
| [11_REAL_WORLD_SKILLS_WALKTHROUGH.md](11_REAL_WORLD_SKILLS_WALKTHROUGH.md) | 3 skill teljes eletciklusa: Diagram Generator, ASZF RAG Chat, Email Intent |
| [12_SKILL_INTEGRATION.md](12_SKILL_INTEGRATION.md) | Skill integracio: install, runtime, upgrade, fuggosegek |
| [13_GITHUB_RESEARCH.md](13_GITHUB_RESEARCH.md) | LangGraph + CrewAI + Haystack valos kodelemzes, adoptalhato mintak |

### Technikai Melyites
| Fajl | Tartalom |
|------|----------|
| [14_FRONTEND.md](14_FRONTEND.md) | Frontend: Reflex vs NiceGUI vs Next.js, 5 UI modul, Claude Code DX |
| [15_ML_MODEL_INTEGRATION.md](15_ML_MODEL_INTEGRATION.md) | ML modell reteg: LLM + embedding + classification + NER + vision + routing |
| [16_RAG_VECTORSTORE.md](16_RAG_VECTORSTORE.md) | pgvector, dokumentum eletciklus, ingestion pipeline, freshness, sync |
| [17_GIT_RULES.md](17_GIT_RULES.md) | Git branching, Conventional Commits, CODEOWNERS, PR szabalyok, pre-commit |
| [18_TESTING_AUTOMATION.md](18_TESTING_AUTOMATION.md) | Teszt piramis, CI/CD, Playwright GUI, teszt DB, prompt/API/E2E tesztek |
| [19_RPA_AUTOMATION.md](19_RPA_AUTOMATION.md) | RPA/feluleti automatizacio: Playwright, ffmpeg, operator-assisted, Cubix POC |

### Fejlesztesi Artefaktumok
| Fajl | Tartalom |
|------|----------|
| [CLAUDE.md](CLAUDE.md) | Claude Code projekt kontextus (fejleszteshez) |
| [SKILL_DEVELOPMENT.md](SKILL_DEVELOPMENT.md) | Skill fejlesztesi utmutato (uj skill letrehozasahoz) |
| [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) | **Komplett implementacios terv 6 pilot + framework, het-per-het** |
