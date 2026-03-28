# AIFlow Skills Directory

## Installed Skills
- process_documentation (ai) - BPMN diagrams from natural language
- aszf_rag_chat (ai) - RAG chat for legal documents
- email_intent_processor (ai) - Email classification and routing
- cfpb_complaint_router (ai) - ML-based complaint classification
- cubix_course_capture (hybrid) - Web course capture with RPA + AI
- qbpp_test_automation (rpa) - Insurance calculator test automation

## Rules
- Max 6 specialist agents per skill
- All agents MUST be stateless
- Prompts in YAML only (never hardcode in Python)
- Minimum 100 test cases per skill
- @test_registry header on every test file
- skill.yaml MUST include framework_requires
- See: 01_PLAN/SKILL_DEVELOPMENT.md
