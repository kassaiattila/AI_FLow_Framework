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
- **58**: **FO TERV** — Sprint A DONE (v1.2.2) + Sprint B AKTUALIS (v1.3.0, B0-B11)
- **49-54**: v1.2.0 reszletes tervek (stability, RAG, doc extract, HITL, frontend, quality)
- **README.md**: Plan mappa index (aktualis + archiv)
- **DEVELOPMENT_ROADMAP.md**: Feature roadmap
- **Archiv:** `archive/` — befejezett sprintek (42,43,48,56,57), session promptok, regi UI tervek, referencia dok

## When editing plan documents
- Keep the Hungarian-English mixed style (Hungarian explanations, English technical terms)
- Use consistent terminology: Step, Workflow, Skill, Agent, Prompt, ExecutionContext
- Cross-references use relative links: `[text](filename.md)` (all files are in same directory)
- DB table names must match 03_DATABASE_SCHEMA.md exactly
- API endpoints must match 22_API_SPECIFICATION.md
- 5 skills: process_documentation, aszf_rag_chat, email_intent_processor, cubix_course_capture, invoice_processor (qbpp TOROLVE v1.3.0-ban)

## Key numbers to keep consistent
- 46 DB tables, 6 views, 29 Alembic migracio (001-029, mind letezik), 60+ indexes
- Framework: 22 weeks, 7 phases (Phase 1-7 KESZ)
- Service Generalization: Fazis 0-5 KESZ (v1.0.0, 2026-04-02)
- UI Modernization: F6 KESZ (v1.1.4, 2026-04-03)
- **v1.2.0 Orchestration: COMPLETE (C0-C20, tag v1.2.0)**
- **v1.2.1 Production Ready Sprint: COMPLETE (S1-S14, 2026-04-04) — UI integracio, observability, quality, 102 E2E teszt, v1.2.1 tag**
- **v1.2.2: Sprint A COMPLETE (A0-A8, 2026-04-05) — infra+security+guardrails+audit**
- **v1.3.0: `01_PLAN/58_POST_SPRINT_HARDENING_PLAN.md` — Sprint B: service excellence (B0-B11)**
- 26 service, 165 endpoint (25 router), 46 DB tabla, 29 Alembic migracio
- 18 pipeline adapter, 6 pipeline template
- 1379 unit test, 129 guardrail teszt, 97 security teszt, 157 skill test, 104 E2E, 54 promptfoo test case
- v1.2.2 Sprint A COMPLETE (A0-A8, 2026-04-05)
- 5 skill (qbpp TOROLVE v1.3.0 B0-ban), 22 UI oldal
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
