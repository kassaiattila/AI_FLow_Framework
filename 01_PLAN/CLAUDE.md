# AIFlow Plan Documentation Context

You are working in the `01_PLAN/` directory which contains the complete AIFlow project plan.

## Phase Relationship (FONTOS!)
> **Phase 1-7 (Het 1-22):** Eredeti framework implementacio — KESZ (v0.1.0 → v0.9.0-stable)
> **Fazis 0-5 (Service Generalization, vertikalis szeletek):** UJ fejezet — skill → altalanos szolgaltatas (v0.9.1 → v1.0.0-rc1)
> A ket fazis-rendszer FUGGETLEN. Phase 1-7 a framework magot epitette, Fazis 0-5 a service reteget.

## Structure
- **00-05**: Core architecture, DB schema (36 tables, 13 views), implementation phases (22 weeks), tech stack
- **06-10**: Operations (Claude Code, versioning, errors, middleware, audit)
- **11-13**: Examples (3+3 skill walkthroughs, skill integration, GitHub research)
- **14-16**: Technical deep-dives (frontend, ML models, RAG/vectorstore)
- **17-19**: Dev rules (git, testing, RPA)
- **20-27**: Security, deployment, API spec, config, testing/regression, test structure, Claude Code setup, dev environment
- **28**: Modular Deployment (Skill Instance architecture, multi-customer deployment)
- **42**: Service Generalization Plan (7 domain service + 9 infra epitokocka + Fazis 0-5 vertikalis szeletek)
- **AIFLOW_MASTER_PLAN.md**: Integrated overview of everything
- **IMPLEMENTATION_PLAN.md**: Step-by-step execution guide (Phase 1-7 KESZ, Fazis 0-5 → ld. 42_)
- **SKILL_DEVELOPMENT.md**: How to create new skills

## When editing plan documents
- Keep the Hungarian-English mixed style (Hungarian explanations, English technical terms)
- Use consistent terminology: Step, Workflow, Skill, Agent, Prompt, ExecutionContext
- Cross-references use relative links: `[text](filename.md)` (all files are in same directory)
- DB table names must match 03_DATABASE_SCHEMA.md exactly
- Phase numbers and week ranges must match 04_IMPLEMENTATION_PHASES.md (legacy) and 42_SERVICE_GENERALIZATION_PLAN.md (aktualis)
- API endpoints must match 22_API_SPECIFICATION.md (+ 42_ tervezett service endpointok)
- 6 skills: process_documentation, aszf_rag_chat, email_intent_processor, cubix_course_capture, invoice_processor, qbpp_test_automation (cfpb_complaint_router merged into email_intent_processor)

## Key numbers to keep consistent
- 41 DB tables, 6 views, 25 Alembic migracio (001-025, mind letezik), 60+ indexes
- Framework: 22 weeks, 7 phases (Phase 1-7 KESZ)
- Service Generalization: Fazis 0-5 vertikalis szelet (F0=infra, F1=Document Extractor, F2=Email+Classifier, F3=RAG Engine, F4=RPA+Media+Diagram, F5=Monitoring+Governance)
- 6 skills, src/aiflow/ 18 alkonyvtar (core, engine, models, prompts, services[tervezett], execution, evaluation, skill_system, tools, vectorstore, documents, ingestion, state, security, api, observability, cli, skills, contrib)
- Python package manager: uv (NOT pip, NOT poetry), lockfile: uv.lock
- Services in Docker, Python code locally from .venv/
- Step + SkillRunner architecture (agents/ module removed, llm/ → models/ atnevezve)
- 100+ test cases per skill minimum
- Tech: PyJWT (NOT python-jose), bcrypt (NOT passlib), APScheduler 4.x (NOT 3.x)
- API key prefix: "aiflow_sk_" (NOT "af_sk_" or "aif_sk_")
- JWT: RS256 (asymmetric key pair, NOT HS256 symmetric secret)
- Redis eviction: volatile-lru (NOT allkeys-lru)
- Skill = template (code), Instance = running config (YAML). Multiple instances per customer.
- deployments/{customer}/deployment.yaml defines which skills+instances per customer

## MANDATORY: Valos teszteles MINDEN fazisban
> **SOHA ne mockolt/fake adatokkal!** Minden uj szolgaltatas valos backend-del, valos DB-vel, valos fajlokkal tesztelendo.
> Fazis CSAK AKKOR "KESZ" ha MINDEN sikerkriteriuma teljesul (42_SERVICE_GENERALIZATION_PLAN.md Section 8).
