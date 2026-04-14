Validate the AIFlow plan documentation for consistency and completeness.

Check all documents in 01_PLAN/ for:

1. **Cross-reference consistency**:
   - DB table names match between 03_DATABASE_SCHEMA.md and all other docs
   - Directory paths match between 02_DIRECTORY_STRUCTURE.md and all other docs
   - **Phase systems:** Phase 1-7 (framework, Het 1-22, KESZ) es Fazis 0-5 (service gen, AKTUALIS) — ne keveredjenek!
   - Skill names consistent (7 skill: process_docs, aszf_rag, email_intent, invoice_processor, invoice_finder, cubix, spec_writer)
   - **DB szamok:** 48 tabla, 6 view, 31 migracio (001-031)
   - **Infra szamok:** 27 service, 175 endpoint (27 router), 22 adapter, 10 pipeline template
   - **Archiv fajlok:** 01_PLAN/archive/ — ELLENORIZD hogy a hivatkozott fajl nem archivalt-e!
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
