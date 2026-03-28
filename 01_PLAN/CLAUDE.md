# AIFlow Plan Documentation Context

You are working in the `01_PLAN/` directory which contains the complete AIFlow project plan (30 documents).

## Structure
- **00-05**: Core architecture, DB schema (35 tables, 12 views), implementation phases (22 weeks), tech stack
- **06-10**: Operations (Claude Code, versioning, errors, middleware, audit)
- **11-13**: Examples (3+3 skill walkthroughs, skill integration, GitHub research)
- **14-16**: Technical deep-dives (frontend, ML models, RAG/vectorstore)
- **17-19**: Dev rules (git, testing, RPA)
- **20-25**: New additions (security, deployment, API spec, config, testing/regression strategy, test structure)
- **AIFLOW_MASTER_PLAN.md**: Integrated overview of everything
- **IMPLEMENTATION_PLAN.md**: Step-by-step execution guide with pilot project references
- **SKILL_DEVELOPMENT.md**: How to create new skills

## When editing plan documents
- Keep the Hungarian-English mixed style (Hungarian explanations, English technical terms)
- Use consistent terminology: Step, Workflow, Skill, Agent, Prompt, ExecutionContext
- Cross-references use relative links: `[text](filename.md)` (all files are in same directory)
- DB table names must match 03_DATABASE_SCHEMA.md exactly
- Phase numbers and week ranges must match 04_IMPLEMENTATION_PHASES.md
- API endpoints must match 22_API_SPECIFICATION.md
- 6 skills: process_documentation, aszf_rag_chat, email_intent_processor, cfpb_complaint_router, cubix_course_capture, qbpp_test_automation

## Key numbers to keep consistent
- 35 DB tables, 13 views, 19 migrations, 60+ indexes
- 22 weeks, 7 phases (Phase 4=Het 10-13, Phase 5=14-16, Phase 6=17-19, Phase 7=20-22)
- 6 skills, 33 plan documents
- Max 6 specialist agents per orchestrator
- 100+ test cases per skill minimum
- Tech: PyJWT (NOT python-jose), bcrypt (NOT passlib), APScheduler 4.x (NOT 3.x)
- API key prefix: "aiflow_sk_" (NOT "af_sk_" or "aif_sk_")
- JWT: RS256 (asymmetric key pair, NOT HS256 symmetric secret)
- Redis eviction: volatile-lru (NOT allkeys-lru)
