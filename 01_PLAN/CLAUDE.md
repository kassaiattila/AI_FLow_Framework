# AIFlow Plan Documentation Context

You are working in the `01_PLAN/` directory which contains the complete AIFlow project plan.

## Phase Relationship (FONTOS!)
> **Phase 1-7 (Het 1-22):** Eredeti framework implementacio — KESZ (v0.1.0 → v0.9.0-stable)
> **Fazis 0-5 (Service Generalization, vertikalis szeletek):** UJ fejezet — skill → altalanos szolgaltatas (v0.9.1 → v1.0.0-rc1)
> A ket fazis-rendszer FUGGETLEN. Phase 1-7 a framework magot epitette, Fazis 0-5 a service reteget.

## Structure
- **00-05**: Core architecture, DB schema, implementation phases (22 weeks), tech stack
- **06-10**: Operations (Claude Code, versioning, errors, middleware, audit)
- **11-13**: Examples (3+3 skill walkthroughs, skill integration, GitHub research)
- **14-16**: Technical deep-dives (frontend, ML models, RAG/vectorstore)
- **17-19**: Dev rules (git, testing, RPA)
- **20-27**: Security, deployment, API spec, config, testing/regression, test structure, Claude Code setup, dev environment
- **28**: Modular Deployment (Skill Instance architecture, multi-customer deployment)
- **42**: Service Generalization Plan (F0-F5 KESZ, v1.0.0)
- **43**: UI Rationalization Plan (F6.0-F6.6, v1.1.0)
- **48-56**: **v1.2.0 Orchestrable Service Architecture** (AKTUALIS):
  - **48**: Fo terv (Pipeline as Code, Tier 1-3, 8 fazis)
  - **49**: Stability & Regression (API compat, DB safety, L0-L4 tesztek)
  - **50**: RAG & Context-as-a-Service (OCR, chunking, reranking, VectorOps, GraphRAG)
  - **51**: Document Extraction & Intent (param. doc tipusok, szamla use case)
  - **52**: Human-in-the-Loop & Notification (review, email/Slack/webhook)
  - **53**: Frontend Design System (Untitled UI, chat UI, user journey, PWA)
  - **54**: LLM Quality & Cost (Promptfoo CI/CD, rubric scoring)
  - **55**: Claude Code Configuration (CLAUDE.md, commands, MCP)
  - **56**: Execution Plan (20 ciklus, session sablon, progress)
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
- 45 DB tables, 6 views, 29 Alembic migracio (001-029, mind letezik), 60+ indexes
- Framework: 22 weeks, 7 phases (Phase 1-7 KESZ)
- Service Generalization: Fazis 0-5 KESZ (v1.0.0, 2026-04-02)
- UI Modernization: F6 KESZ (v1.1.4, 2026-04-03)
- **v1.2.0 Orchestration: COMPLETE (C0-C20, tag v1.2.0)**
- **v1.2.1 Production Ready Sprint: `01_PLAN/57_PRODUCTION_READY_SPRINT.md` — S1-S14 ciklus (UI integracio, observability, quality, polish)**
- 26 service (15 eredeti + 11 uj v1.2.0: notification, data_router, service_manager, reranker, advanced_chunker, data_cleaner, metadata_enricher, vector_ops, advanced_parser, graph_rag, quality)
- ~155 endpoint (112 eredeti + 15 Tier 2 + 7 Tier 3 + pipeline 13 + quality 4 + templates 3)
- 18 pipeline adapter (7 eredeti + 3 Tier 2 + 7 Tier 3 + 1 Tier 4)
- 24 API router (19 eredeti + pipelines + notifications + data_router + rag_advanced + quality)
- 6 pipeline templates (v1, v2, kb_update, email_triage, advanced_rag, contract)
- 332 pipeline unit test, 51 promptfoo test case (6 skill), 21 fejlesztesi ciklus (C0-C20, MIND DONE), v1.2.0 COMPLETE
- 6 skills, src/aiflow/ 19 alkonyvtar (+pipeline/ az uj modul)
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
