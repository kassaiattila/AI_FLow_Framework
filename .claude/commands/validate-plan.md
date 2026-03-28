Validate the AIFlow plan documentation for consistency and completeness.

Check all documents in 01_PLAN/ for:

1. **Cross-reference consistency**:
   - DB table names match between 03_DATABASE_SCHEMA.md and all other docs
   - Directory paths match between 02_DIRECTORY_STRUCTURE.md and all other docs
   - Phase/week numbers consistent across all docs (Phase 7 = Het 19-22, total = 22)
   - Skill names consistent (6 skills: process_documentation, aszf_rag_chat, email_intent_processor, cfpb_complaint_router, cubix_course_capture, qbpp_test_automation)

2. **Broken links**:
   - All markdown links [text](file.md) point to existing files
   - No references to files outside 01_PLAN/ (except CLAUDE.md in root)

3. **Tech stack consistency**:
   - Package versions in 05_TECH_STACK.md match pyproject.toml examples
   - Docker images consistent across 21_DEPLOYMENT_OPERATIONS.md and 05_TECH_STACK.md

4. **API endpoint coverage**:
   - All endpoints in 22_API_SPECIFICATION.md mentioned in 01_ARCHITECTURE.md

5. **Test coverage**:
   - All modules in 02_DIRECTORY_STRUCTURE.md have corresponding test entries in 24_TESTING_REGRESSION_STRATEGY.md

Report issues sorted by severity: CRITICAL > HIGH > MEDIUM > LOW
