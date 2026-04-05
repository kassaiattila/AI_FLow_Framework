# AIFlow Plan Documentation — Index

> **Utolso frissites:** 2026-04-05 (Sprint A v1.2.2 DONE, Sprint B tervezes KESZ)
> **Aktualis verzio:** v1.2.2
> **Kovetkezo sprint:** Sprint B (v1.3.0) — `58_POST_SPRINT_HARDENING_PLAN.md`

---

## Aktualis (Sprint B-hez szukseges)

| Fajl | Tartalom | Allapot |
|------|----------|---------|
| **58_POST_SPRINT_HARDENING_PLAN.md** | Sprint A (DONE) + Sprint B (AKTUALIS) fo terv | **AKTIV** |
| **CLAUDE.md** | Plan-szintu Claude Code konfiguracio | AKTIV |
| **DEVELOPMENT_ROADMAP.md** | Stub/feature roadmap (A4-bol) | AKTIV |

## Alapdokumentacio (referencia, reszben elavult de hasznos)

| Fajl | Tartalom | Megjegyzes |
|------|----------|------------|
| 00_EXECUTIVE_SUMMARY.md | Projekt attekintes | Frissitesre szorul |
| 01_ARCHITECTURE.md | Core architektura (Step, Skill, Pipeline) | Releváns |
| 02_DIRECTORY_STRUCTURE.md | Mappaszerkezet | Reszben elavult |
| 03_DATABASE_SCHEMA.md | 45 DB tabla, 6 view | Releváns (de 29 migracio ota frissitesre szorul) |
| 05_TECH_STACK.md | Technologiai dontesek | Releváns |
| 17_GIT_RULES.md | Git konvenciok | Releváns |
| 20_SECURITY_HARDENING.md | Biztonsagi iranyelvek | Sprint A frissitette (JWT RS256, stb.) |
| 21_DEPLOYMENT_OPERATIONS.md | Deploy operaciok | Releváns (B9 Docker deploy frissiti) |
| 22_API_SPECIFICATION.md | 142 API endpoint | Releváns |
| 24_TESTING_REGRESSION_STRATEGY.md | Tesztelesi strategia | Releváns |
| 27_DEVELOPMENT_ENVIRONMENT.md | Dev kornyezet (uv, Docker) | Releváns |
| 30_RAG_PRODUCTION_PLAN.md | RAG pipeline checklist | Releváns (B4 aszf_rag-hoz) |

## v1.2.0 Reszletes Tervek (Sprint B referencia)

| Fajl | Tartalom | Sprint B hasznalat |
|------|----------|-------------------|
| 49_STABILITY_REGRESSION.md | API compat, DB safety, L0-L4 tesztek | B2, B10 |
| 50_RAG_VECTOR_CONTEXT_SERVICE.md | Advanced RAG, chunking, reranking | B4 (aszf_rag) |
| 51_DOCUMENT_EXTRACTION_INTENT.md | Doc tipusok, intent routing, szamla | B3 (Invoice Finder) |
| 52_HUMAN_IN_THE_LOOP_NOTIFICATION.md | Review workflow, multi-channel | B7 (Verification) |
| 53_FRONTEND_DESIGN_SYSTEM.md | Untitled UI, chat UI, PWA | B6, B7, B8 |
| 54_LLM_QUALITY_COST_OPTIMIZATION.md | Promptfoo CI/CD, koltseg | B4, B5 |

## User Journey Dokumentumok (B6 input)

| Fajl | Tartalom | Allapot |
|------|----------|---------|
| F1_DOCUMENT_EXTRACTOR_JOURNEY.md | Dokumentum feldolgozo journey | v1.0.0 (B6 felulvizsgalja) |
| F2_EMAIL_CONNECTOR_JOURNEY.md | Email feldolgozo journey | v1.0.0 |
| F3_RAG_ENGINE_JOURNEY.md | RAG chat journey | v1.0.0 |
| F4_RPA_MEDIA_DIAGRAM_JOURNEY.md | RPA + diagram journey | v1.0.0 |
| F5_MONITORING_GOVERNANCE_JOURNEY.md | Monitoring journey | v1.0.0 |
| F6_UI_RATIONALIZATION_JOURNEY.md | UI migracio journey | v1.1.4 |
| PIPELINE_UI_JOURNEY.md | Pipeline UI journey | v1.2.0 |
| QUALITY_DASHBOARD_JOURNEY.md | Quality dashboard journey | v1.2.1 |
| SERVICE_CATALOG_JOURNEY.md | Service catalog journey | v1.2.1 |

## Archiv (01_PLAN/archive/)

| Mappa | Tartalom | Db |
|-------|----------|-----|
| archive/sessions/ | Session promptok (S7-S18) | ~16 fajl |
| archive/ui_legacy/ | Regi UI tervek (React Admin, stb.) | ~10 fajl |
| archive/completed_sprints/ | Befejezett sprint tervek (v1.0.0-v1.2.1) | ~9 fajl |
| archive/status_reports/ | Audit, status riportok | ~8 fajl |
| archive/reference/ | Regi referencia dokumentumok | ~23 fajl |

> **Torteneti attekinteshez:** Archiv fajlok teljes git tortenete megmarad.
> **Hivatkozashoz:** `01_PLAN/archive/{mappa}/{fajlnev}` utvonal hasznalando.
