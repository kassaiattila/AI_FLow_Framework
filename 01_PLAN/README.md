# AIFlow Plan Directory — Index

> **Version:** v1.4.0 | **Utolso frissites:** 2026-04-14
> **Kovetkezo sprint:** Sprint D — v2 Phase 1a (IntakePackage + domain contracts)

---

## v2 ARCHITEKTURA (100-106) — AKTIV, Phase 1a IMPLEMENTACIORA VAR

> Olvasasi sorrend: 104 (index) → 100 (overview) → 100_b (contracts) → 100_c (state) → 101 (components) → 106 (guide) → 100_d (migration)

| Fajl | Tartalom | Status |
|------|----------|--------|
| [100_AIFLOW_v2_ARCHITECTURE_REFINEMENT_OVERVIEW.md](100_AIFLOW_v2_ARCHITECTURE_REFINEMENT_OVERVIEW.md) | Executive overview: N-layer intake, R-layer routing, B-layer business | FINAL SIGNED |
| [100_b_AIFLOW_v2_DOMAIN_CONTRACTS.md](100_b_AIFLOW_v2_DOMAIN_CONTRACTS.md) | 13 Pydantic domain entity (IntakePackage → ProvenanceMap) | FINAL SIGNED |
| [100_c_AIFLOW_v2_STATE_LIFECYCLE_MODEL.md](100_c_AIFLOW_v2_STATE_LIFECYCLE_MODEL.md) | 7 state machine, idempotent replay, SLA escalation | FINAL SIGNED |
| [100_d_AIFLOW_v2_MIGRATION_PLAYBOOK.md](100_d_AIFLOW_v2_MIGRATION_PLAYBOOK.md) | Zero-downtime v1.3→v2, backward compat shim, rollback matrix | FINAL SIGNED |
| [100_e_AIFLOW_v2_CAPACITY_PLANNING.md](100_e_AIFLOW_v2_CAPACITY_PLANNING.md) | Hardware profiles A/B, throughput benchmarks, cost model | FINAL |
| [100_f_AIFLOW_v2_HITL_WORKLOAD_MODEL.md](100_f_AIFLOW_v2_HITL_WORKLOAD_MODEL.md) | HITL queue volumetria, SLA, assignment, bulk review | FINAL |
| [101_AIFLOW_v2_COMPONENT_TRANSFORMATION_PLAN.md](101_AIFLOW_v2_COMPONENT_TRANSFORMATION_PLAN.md) | 25+ komponens: N1-N15 intake→archival pipeline | FINAL |
| [102_AIFLOW_v2_FIRST_REVIEW_CYCLE.md](102_AIFLOW_v2_FIRST_REVIEW_CYCLE.md) | 1. review ciklus (7 Must + 5 Should) — torteneti | ARCHIV |
| [103_AIFLOW_v2_FINAL_VALIDATION.md](103_AIFLOW_v2_FINAL_VALIDATION.md) | 2. review + multi-tenant + CI orchestration | FINAL |
| [104_AIFLOW_v2_FINAL_MASTER_INDEX.md](104_AIFLOW_v2_FINAL_MASTER_INDEX.md) | Master index, olvasasi sorrend, sign-off matrix | FINAL |
| [105_AIFLOW_v2_P0_P4_HARDENING_RECORD.md](105_AIFLOW_v2_P0_P4_HARDENING_RECORD.md) | P0-P4 hardening closing record | FINAL |
| [106_AIFLOW_v2_PHASE_1a_IMPLEMENTATION_GUIDE.md](106_AIFLOW_v2_PHASE_1a_IMPLEMENTATION_GUIDE.md) | Sprint tervek, task prioritas, dev environment | FINAL |

---

## SPRINT TERVEK

| Fajl | Sprint | Status |
|------|--------|--------|
| [65_SPRINT_C_UI_JOURNEY_FIRST_PLAN.md](65_SPRINT_C_UI_JOURNEY_FIRST_PLAN.md) | Sprint C (v1.4.0) — UI Journey-First | COMPLETE |
| [58_POST_SPRINT_HARDENING_PLAN.md](58_POST_SPRINT_HARDENING_PLAN.md) | Sprint B (v1.3.0) — E2E Service Excellence | COMPLETE |
| [64_SPRINT_C_UI_FIX_PLAN.md](64_SPRINT_C_UI_FIX_PLAN.md) | Sprint C elokeszito terv | COMPLETE |

---

## REFERENCIA DOKUMENTUMOK

### Architektura & Technologia (00-27)
| Fajl | Tartalom |
|------|----------|
| [00_EXECUTIVE_SUMMARY.md](00_EXECUTIVE_SUMMARY.md) | Projekt osszefoglalo |
| [01_ARCHITECTURE.md](01_ARCHITECTURE.md) | Framework architektura (Step, Skill, Pipeline) |
| [02_DIRECTORY_STRUCTURE.md](02_DIRECTORY_STRUCTURE.md) | Konyvtar struktura |
| [03_DATABASE_SCHEMA.md](03_DATABASE_SCHEMA.md) | DB schema (48 tabla, 31 migracio) |
| [05_TECH_STACK.md](05_TECH_STACK.md) | Technologiai stack |
| [17_GIT_RULES.md](17_GIT_RULES.md) | Git workflow szabalyok |
| [20_SECURITY_HARDENING.md](20_SECURITY_HARDENING.md) | Biztonsagi hardening (JWT RS256, bcrypt) |
| [21_DEPLOYMENT_OPERATIONS.md](21_DEPLOYMENT_OPERATIONS.md) | Deploy es uzemeltetes |
| [22_API_SPECIFICATION.md](22_API_SPECIFICATION.md) | API spec (175 endpoint, 27 router) |
| [24_TESTING_REGRESSION_STRATEGY.md](24_TESTING_REGRESSION_STRATEGY.md) | Teszt strategia |
| [27_DEVELOPMENT_ENVIRONMENT.md](27_DEVELOPMENT_ENVIRONMENT.md) | Dev kornyezet (uv, Docker) |

### Szolgaltatasok & UI (30-63)
| Fajl | Tartalom |
|------|----------|
| [30_RAG_PRODUCTION_PLAN.md](30_RAG_PRODUCTION_PLAN.md) | RAG produktiv terv |
| [43_UI_RATIONALIZATION_PLAN.md](43_UI_RATIONALIZATION_PLAN.md) | UI racionalizalas (Untitled UI) |
| [48_ORCHESTRABLE_SERVICE_ARCHITECTURE.md](48_ORCHESTRABLE_SERVICE_ARCHITECTURE.md) | Service architektura |
| 49-54 | v1.2.0 reszletes tervek (stability, RAG, doc extract, HITL, frontend, quality) |
| [55_CLAUDE_CODE_CONFIGURATION.md](55_CLAUDE_CODE_CONFIGURATION.md) | Claude Code config |
| [59_COMMAND_WORKFLOW_AUDIT.md](59_COMMAND_WORKFLOW_AUDIT.md) | Command audit |
| [60_CLAUDE_CODE_BEST_PRACTICES_REFERENCE.md](60_CLAUDE_CODE_BEST_PRACTICES_REFERENCE.md) | Best practices |
| [63_UI_USER_JOURNEYS.md](63_UI_USER_JOURNEYS.md) | User journey definiciok (J1-J5) |

### Aktiv Journey definiciok
| Fajl | Journey |
|------|---------|
| [PIPELINE_UI_JOURNEY.md](PIPELINE_UI_JOURNEY.md) | Pipeline management |
| [QUALITY_DASHBOARD_JOURNEY.md](QUALITY_DASHBOARD_JOURNEY.md) | Quality dashboard |
| [SERVICE_CATALOG_JOURNEY.md](SERVICE_CATALOG_JOURNEY.md) | Service catalog |

---

## ARCHIV

```
archive/
├── sessions/
│   ├── legacy/              — Session 7-14 (pre-Sprint A)
│   ├── sprint_b/            — Session 19-36 (Sprint B, v1.3.0)
│   └── sprint_c/            — Session 37-43 (Sprint C, v1.4.0)
├── completed_sprints/       — Befejezett sprint tervek (v1.0.0-v1.2.1)
├── reference/               — F1-F6 journey archivok, Figma audit
├── ui_legacy/               — Regi UI tervek (React Admin, stb.)
├── status_reports/          — Audit, status riportok
└── misc/                    — CrewAI, document_pipeline, regi session promptok
```

> **Torteneti attekinteshez:** Archiv fajlok teljes git tortenete megmarad.
