# AIFlow Terv - Talalt Hianyossagok es Javitasok

**Datum:** 2026-03-28
**Kesziette:** Claude Code audit a 23 dokumentum attekintesebol

---

## 1. UJ DOKUMENTUMOK (hozzaadva 01_PLAN/-ba)

| Fajl | Tartalom | Indoklas |
|------|----------|----------|
| **03_DATABASE_SCHEMA_v2.md** | Teljes DB schema (23 tabla, 7 view) | Az eredeti 03-ban 10+ tabla hiányzott |
| **20_SECURITY_HARDENING.md** | Biztonsagi terv | Kritikus hiany: nem volt dedikalt security dokumentum |
| **21_DEPLOYMENT_OPERATIONS.md** | Uzemeltetesi utmutato | Kritikus hiany: nem volt deployment/ops guide |
| **22_API_SPECIFICATION.md** | Egysegese REST API spec | Endpointok szet voltak szorva 5+ dokumentumban |
| **23_CONFIGURATION_REFERENCE.md** | Konfiguracios referencia | Nem volt aiflow.yaml, .env, K8s config referencia |
| **00_GAPS_AND_FIXES.md** | Ez a fajl | Audit eredmeny osszefoglalo |

---

## 2. TALALT INKONZISZTENCIAK (javitando a meglevo dokumentumokban)

### 2.1 Idovonal Elteresek

| Dokumentum | Phase 7 | Osszes het |
|------------|---------|------------|
| 04_IMPLEMENTATION_PHASES.md | Het 19-21 | 21 het |
| AIFLOW_MASTER_PLAN.md | Het 19-22 | 22 het |
| IMPLEMENTATION_PLAN.md | Het 20-22 | 22 het |

**JAVITAS:** Egysegesen **22 het** legyen. Phase 7 = Het 19-22. Az IMPLEMENTATION_PLAN.md a korrekt.

### 2.2 Skill Szam Elteresek

| Dokumentum | Skill-ek szama |
|------------|---------------|
| 00_EXECUTIVE_SUMMARY.md | 3 skill (walking through) |
| 11_REAL_WORLD_SKILLS_WALKTHROUGH.md | 3 skill |
| IMPLEMENTATION_PLAN.md | 5 skill |
| 02_DIRECTORY_STRUCTURE.md | 5 skill |
| AIFLOW_MASTER_PLAN.md | 5 skill |

**JAVITAS (2026-03-29):** Egysegesen **5 skill** (process_doc, aszf_rag, email_intent, cubix_capture, qbpp_test).
A cfpb_complaint_router beolvadt az email_intent_processor-ba mint hibrid ML+LLM klasszifikacios reteg.

### 2.3 llm/ vs models/ Konyvtar

Az eredeti tervek `src/aiflow/llm/` konyvtarat hasznalnak (Phase 1-2), de a 15_ML_MODEL_INTEGRATION.md
lecsereli `src/aiflow/models/`-re. Nehol meg a regi llm/ hivatkozas maradt.

**JAVITAS:** Mindenhol `src/aiflow/models/` legyen. A `LLMClient = ModelClient` alias biztositja a backward compat-ot.
Erintett fajlok: 04_IMPLEMENTATION_PHASES.md Het 2 feladatok.

### 2.4 Plan Konyvtar Hivatkozasok

**MEGOLDVA (2026-03-28):** Minden terv MD fajl athelyezve `01_PLAN/` mappaba.
Root-ban csak a `CLAUDE.md` maradt (Claude Code projekt kontextus).
Belso kereszthivatkozasok frissitve.

---

## 3. HIANYZÓ TABLAK A DB SCHEMA-BAN (javitva a v2-ben)

| Tabla | Hivatkozva | Hiányzott az eredeti 03-bol |
|-------|-----------|---------------------------|
| model_registry | 15_ML_MODEL_INTEGRATION.md | IGEN |
| embedding_models | 16_RAG_VECTORSTORE.md (collections FK) | IGEN |
| documents | 16_RAG_VECTORSTORE.md | IGEN |
| chunks | 16_RAG_VECTORSTORE.md | IGEN |
| collections | 16_RAG_VECTORSTORE.md | IGEN |
| document_sync_schedules | 16_RAG_VECTORSTORE.md | IGEN |
| test_datasets | 18_TESTING_AUTOMATION.md | IGEN |
| test_cases | 18_TESTING_AUTOMATION.md | IGEN |
| test_results | 18_TESTING_AUTOMATION.md | IGEN |
| skill_prompt_versions | 07_VERSION_LIFECYCLE.md | IGEN |

**JAVITAS:** Mind a 10 tabla hozzaadva a 03_DATABASE_SCHEMA_v2.md-ben.

---

## 4. HIANYZÓ KONYVTAR BEJEGYZESEK (02_DIRECTORY_STRUCTURE.md)

| Hianyzó fajl/mappa | Hivatkozva |
|---------------------|-----------|
| src/aiflow/core/events.py | 13_GITHUB_RESEARCH (CrewAI event bus) |
| src/aiflow/engine/serialization.py | 13_GITHUB_RESEARCH (Haystack YAML serialize) |
| src/aiflow/execution/messaging.py | 09_MIDDLEWARE_INTEGRATION (MessageBroker ABC) |
| src/aiflow/contrib/docs/ | 10_BUSINESS_AUDIT_DOCS (auto-gen docs) |
| src/aiflow/contrib/mcp_server.py | 06_CLAUDE_CODE_INTEGRATION (MCP server) |
| src/aiflow/models/finetuning/ | 15_ML_MODEL_INTEGRATION (FineTuneManager) |
| skills/qbpp_test_automation/ | IMPLEMENTATION_PLAN (5. skill) |

**MEGJEGYZES:** Az AIFLOW_MASTER_PLAN.md konyvtar listaja MAR tartalmazza ezeket, de a reszletes 02_DIRECTORY_STRUCTURE.md nem.

---

## 5. HIANYZÓ FUGGOSEGEK (05_TECH_STACK.md)

| Csomag | Hasznalat | Hiányzik innen |
|--------|-----------|----------------|
| detect-secrets | Pre-commit hook (17_GIT_RULES) | dev dependencies |
| pytest-bdd | BDD tesztek (18_TESTING) | pyproject.toml optional deps |
| reflex | Frontend (14_FRONTEND) | [ui] optional deps |
| playwright | RPA + GUI teszt (19_RPA) | [rpa] optional deps - MEGVAN, de hiányzik a [dev]-bol |
| sentence-transformers | Lokalis ML (15_ML) | [local-models] optional deps |
| robotframework | RPA opcionalis (19_RPA) | [rpa] optional deps |
| libcst | Skill migracio AST (07_VERSION) | nincs sehol listazva |
| confluent-kafka | Kafka + Schema Registry (09_MIDDLEWARE) | [kafka] optional deps |

**JAVITAS:** A pyproject.toml-ban boviteni kell az optional dependency csoportokat.

---

## 6. HIANYZÓ IMPLEMENTACIOS FAZISOK (04_IMPLEMENTATION_PHASES.md)

A kovetkezo temak nincsenek fazisokba sorolva a 04-ben:

| Tema | Dokumentum | Javasolt Fazis |
|------|-----------|---------------|
| ML Model Registry + Protocols | 15_ML_MODEL_INTEGRATION | Phase 2 (Het 4-6) |
| VectorStore + Ingestion | 16_RAG_VECTORSTORE | Phase 2 (Het 6) + Phase 3 (Het 9) |
| Frontend (Reflex) | 14_FRONTEND | Phase 5 (Het 16) |
| RPA Framework (Playwright, Shell) | 19_RPA_AUTOMATION | Phase 4 (Het 13) |
| GUI Tesztek (Playwright) | 18_TESTING_AUTOMATION | Phase 6 (Het 18) |
| Security Hardening | 20_SECURITY_HARDENING | Phase 5 (Het 15) + Phase 7 (Het 20) |
| QBPP Skill | IMPLEMENTATION_PLAN | Phase 4 (Het 13) |

**MEGJEGYZES:** Az IMPLEMENTATION_PLAN.md MAR tartalmazza ezeket a bovitett fasizokat. A 04 frissitendo.

---

## 7. ELLENORZO LISTA A VEGREHAJTASHOZ

### Phase 1 elott (azonnal):
- [ ] GitHub repo letrehozasa
- [ ] .gitignore (17_GIT_RULES.md alapjan)
- [ ] .pre-commit-config.yaml (17_GIT_RULES.md 9. szekció)
- [ ] .github/CODEOWNERS (17_GIT_RULES.md 2. szekció)
- [ ] .env.example (23_CONFIGURATION_REFERENCE.md alapjan)
- [ ] PR template (.github/pull_request_template.md - 17_GIT_RULES.md 4. szekció)

### Phase 1-3 kozben:
- [ ] Docker Compose mukodik (pgvector + redis + api)
- [ ] Alembic migracio fut (001-004)
- [ ] LiteLLM + instructor hivas mukodik
- [ ] structlog JSON output mukodik
- [ ] Elso unit teszt zold

### Phase 4 kozben:
- [ ] process_documentation skill telepitve
- [ ] 100+ teszt eset (90%+ pass rate)
- [ ] Langfuse prompt sync mukodik

### Phase 5-6 kozben:
- [ ] FastAPI health endpoint mukodik
- [ ] JWT + API key auth mukodik
- [ ] Async workflow (Redis queue) mukodik
- [ ] CLI parancsok mukodnek
- [ ] Langfuse trace-ek megjelennek

### Phase 7:
- [ ] K8s deployment mukodik
- [ ] CI/CD pipeline zold (3 kulon pipeline)
- [ ] Blue-green deploy tesztelve
- [ ] SLA monitoring aktiv
- [ ] Audit log mukodik

---

## 8. KOCKAZATI ERTEKELES (Uj)

### Architekturalis Kockazatok

| Kockazat | Szint | Mitigacio |
|----------|-------|-----------|
| Reflex pre-v1.0 (frontend) | KOZEPES | Next.js fallback terv keszitve (14_FRONTEND) |
| pgvector skalazas (100k+ chunk) | ALACSONY | Qdrant migracios ut dokumentalva (16_RAG) |
| arq egyetlen Redis pont | KOZEPES | Redis Sentinel/Cluster HA terv kell |
| Monorepo meret (50+ skill) | ALACSONY | CODEOWNERS + path-alapu CI |

### Hianyzo Tervek (nem kritikus, de ajanlott)

| Tema | Prioritas | Indoklas |
|------|-----------|----------|
| Performance Benchmark terv | KOZEPES | Nincs definialva az elvart throughput |
| Data Migration Strategy | KOZEPES | Nincs terv a POC adatok migralasakor |
| Multi-tenancy reszletes terv | ALACSONY | Teams tabla van, de izolacio reszletei hianyznak |
| i18n/l10n strategia | ALACSONY | Magyar+angol, de nincs i18n framework valasztas |
| Mobile/responsive UI terv | ALACSONY | Nincs mobil strategia |
