Validate the AIFlow plan documentation for consistency and completeness.

Check all documents in 01_PLAN/ for:

1. **Cross-reference consistency**:
   - DB table names match between 03_DATABASE_SCHEMA.md and all other docs
   - Directory paths match between 02_DIRECTORY_STRUCTURE.md and all other docs
   - **Phase systems:** Phase 1-7 (framework, Het 1-22, KESZ) es Fazis 0-4 (service gen, AKTUALIS) — ne keveredjenek!
   - Skill names consistent (6 skills: process_documentation, aszf_rag_chat, email_intent_processor, cubix_course_capture, invoice_processor, qbpp_test_automation)
   - **DB szamok:** 36 tabla, 13 view, 13 letezo migracio (001-013), 11 tervezett (014-024)
   - **Directory:** src/aiflow/ 18 alkonyvtar (core, engine, models, prompts, services[tervezett], execution, evaluation, skill_system, tools, vectorstore, documents, ingestion, state, security, api, observability, cli, contrib)
   - **Atnevezesek:** llm/ → models/ (MINDENHOL models/ kell legyen), agents/ → torolve

2. **Broken links**:
   - All markdown links [text](file.md) point to existing files
   - No references to files outside 01_PLAN/ (except CLAUDE.md in root)

3. **Tech stack consistency**:
   - Package versions in 05_TECH_STACK.md match pyproject.toml examples
   - Docker images consistent across 21_DEPLOYMENT_OPERATIONS.md and 05_TECH_STACK.md

4. **API endpoint coverage**:
   - All endpoints in 22_API_SPECIFICATION.md mentioned in 01_ARCHITECTURE.md
   - **42_SERVICE_GENERALIZATION_PLAN tervezett endpointok** (Email Connector, Document Extractor, RAG Engine) — jelolve vannak-e mint "tervezett"?

5. **Test coverage**:
   - All modules in 02_DIRECTORY_STRUCTURE.md have corresponding test entries in 24_TESTING_REGRESSION_STRATEGY.md

6. **Valos teszteles kovetelmeny**:
   - Minden fazis sikerkriteriuma (42_SERVICE_GENERALIZATION_PLAN Section 8) tartalmaz VALOS TESZT sort?
   - Nincs "KESZ" jeloles mock/fake tesztelesre hivatkozva?

Report issues sorted by severity: CRITICAL > HIGH > MEDIUM > LOW
