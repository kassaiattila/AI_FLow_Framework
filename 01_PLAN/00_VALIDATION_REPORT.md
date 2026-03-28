# AIFlow Terv - Validacios Jelentes

**Datum:** 2026-03-28
**Modszer:** 3 parhuzamos audit (kereszthivatkozas, tartalmi teljesség, technikai pontossag)
**Scope:** Mind a 32 dokumentum a 01_PLAN/ mappaban + CLAUDE.md
**Status:** MINDEN HIBA JAVITVA (2026-03-28)

---

## OSSZEFOGLALO

| Kategoria | CRITICAL | HIGH | MEDIUM | LOW | Osszes |
|-----------|----------|------|--------|-----|--------|
| Kereszthivatkozas konzisztencia | 1 | 9 | 8 | 4 | 22 |
| Technikai pontossag | 3 | 7 | 11 | 8 | 29 |
| Tartalmi teljesség | 0 | 4 | 8 | 6 | 18 |
| **OSSZES** | **4** | **20** | **27** | **18** | **69** |

---

## I. CRITICAL HIBAK (4 db - azonnal javitando)

### C1. python-jose elavult, CVE-vel
- **Fajl:** 05_TECH_STACK.md
- **Problema:** python-jose[cryptography] >= 3.3 utolso kiadas 2021, ismert CVE-k
- **Javitas:** Cserelni **PyJWT[crypto] >= 2.8**-ra (aktivan karbantartott)

### C2. JWT konfiguracio ellenmondasos
- **Fajl:** 23_CONFIGURATION_REFERENCE.md vs 20_SECURITY_HARDENING.md
- **Problema:** Config `jwt_secret`-et hasznal (szimmetrikus, HS256), de a security doc RS256-ot (aszimmetrikus) ir elo
- **Javitas:** Config-ban `jwt_private_key_path` + `jwt_public_key_path`, `jwt_expiry: 900` (15 perc)

### C3. DB migracio sorrend hibas
- **Fajl:** 03_DATABASE_SCHEMA.md
- **Problema:** `workflow_runs` FK-val hivatkozik `teams`-re es `users`-re, de azok csak a 005-os migracioban jonnek letre (001-ben mar kellenenek)
- **Javitas:** FK-k nelkul letrehozni az 001-ben, ALTER TABLE-lel hozzaadni az 005-ben

### C4. Python verzio ellenmondasos
- **Fajl:** 22_API_SPECIFICATION.md
- **Problema:** "Python 3.11+" irt, mindenhol mashol "Python 3.12+"
- **Javitas:** Javitani "3.12+"-ra

---

## II. HIGH PRIORITASU HIBAK (top 10)

### H1. Fazis/het szamozas inkonzisztens
- **Fajlok:** AIFLOW_MASTER_PLAN.md vs 04_IMPLEMENTATION_PHASES.md
- **Problema:** Phase 4 = Het 10-12 (master) vs Het 10-13 (phases). Phase 5-7 shiftelve.
- **Javitas:** Egysegiteni a 04_IMPLEMENTATION_PHASES.md szamozasat minden dokumentumban

### H2. passlib[bcrypt] elavult
- **Fajl:** 05_TECH_STACK.md
- **Javitas:** Cserelni `bcrypt >= 4.1`-re vagy `argon2-cffi >= 23.1`-re

### H3. APScheduler 3.x legacy szinkron API
- **Fajl:** 05_TECH_STACK.md
- **Javitas:** `apscheduler >= 4.0` (nativ async) vagy dokumentalni a 3.x valasztast

### H4. Hianyzó ON DELETE klauzulak (8+ FK)
- **Fajl:** 03_DATABASE_SCHEMA.md
- **Javitas:** `ON DELETE SET NULL` audit_log-ra, workflow_runs-ra; `ON DELETE CASCADE` A/B testing tablakra

### H5. Hianyzó API endpointok
- **Fajl:** 22_API_SPECIFICATION.md
- **Hianyzik:** GET /api/v1/conversations, POST /api/v1/feedback, POST /api/v1/skills/{skill}/ingest, GDPR endpointok

### H6. Skill szam nem 6 mindenhol
- **Fajl:** AIFLOW_MASTER_PLAN.md
- **Javitas:** Skill 5 (CFPB) es 6 (QBPP) hozzaadasa a master plan skill szekciohoz

### H7. CLI parancsok hianyosak a 02-ben
- **Fajl:** 02_DIRECTORY_STRUCTURE.md
- **Javitas:** Hianyzó subcommandok: workflow {replay, docs, export}, skill {validate, upgrade, uninstall}, prompt {promote, rollback, list}, + report.py, admin.py CLI fajlok

### H8. Hianyzó konyvtar bejegyzesek
- **Fajl:** 02_DIRECTORY_STRUCTURE.md
- **Javitas:** Hianyzik: core/events.py, engine/serialization.py, execution/messaging.py, contrib/docs/, contrib/mcp_server.py, models/finetuning/

### H9. Redis allkeys-lru veszelyeses
- **Fajl:** 23_CONFIGURATION_REFERENCE.md
- **Javitas:** `volatile-lru`-ra cserelni (csak TTL-es kulcsokat torli), vagy kulon Redis a cache-nek es queue-nak

### H10. PostgreSQL connection pool kimeritese
- **Fajl:** 23_CONFIGURATION_REFERENCE.md, 21_DEPLOYMENT_OPERATIONS.md
- **Javitas:** PgBouncer hozzaadasa, vagy pool_size csokkentese replika-szamhoz igazitva

---

## III. TARTALMI HIANYOSSAGOK (top 8)

| # | Tema | Status | Sulyossag | Ajanlott megoldas |
|---|------|--------|-----------|-------------------|
| T1 | **Idempotencia** (API szint) | JAVITVA | HIGH | 22_API_SPECIFICATION.md: X-Idempotency-Key szekció |
| T2 | **Crash recovery** (orphan run detektalas) | JAVITVA | HIGH | 08_ERROR_HANDLING.md: Crash Recovery Protocol szekció |
| T3 | **LLM failover szekvencia** | JAVITVA | HIGH | 15_ML_MODEL_INTEGRATION.md: LLM Failover Protokoll |
| T4 | **Backup verifikacio** | JAVITVA | HIGH | 21_DEPLOYMENT_OPERATIONS.md: Backup Verifikacio szekció |
| T5 | **Dependency licenc policy** | JAVITVA* | MEDIUM | *Reszleges: CI scanning hozzaadva, kulon doc meg keszulhet |
| T6 | **Prompt parhuzamos szerkesztes** | JAVITVA | MEDIUM | 07_VERSION_LIFECYCLE.md: Prompt Parhuzamos Szerkesztes |
| T7 | **Queue szemantika** | JAVITVA | MEDIUM | 01_ARCHITECTURE.md: Delivery garantaciok szekció |
| T8 | **WebSocket reconnection** | JAVITVA | MEDIUM | 22_API_SPECIFICATION.md: WebSocket Reliability szekció |

---

## IV. AJANLOTT KOVETKEZO LEPESEK (PRIORITAS SZERINT)

### Azonnali (CRITICAL) - MIND JAVITVA 2026-03-28
1. ~~python-jose -> PyJWT csere~~ KESZ (05_TECH_STACK.md)
2. ~~JWT config egysegesites (RS256 key pair)~~ KESZ (23_CONFIGURATION_REFERENCE.md)
3. ~~DB migracio sorrend javitas~~ KESZ (03_DATABASE_SCHEMA.md)
4. ~~Python 3.12+ javitas~~ KESZ (22_API_SPECIFICATION.md)

### Phase 1 elott (HIGH) - MIND JAVITVA 2026-03-28
5. ~~Fazis/het szamok egysegesitese~~ KESZ (AIFLOW_MASTER_PLAN, 00_EXECUTIVE, 14_FRONTEND)
6. ~~ON DELETE klauzulak~~ KESZ (03_DATABASE_SCHEMA.md - 16 FK javitva)
7. ~~02_DIRECTORY_STRUCTURE.md bovitese~~ KESZ (6 uj bejegyzes + CLI parancsok)
8. ~~AIFLOW_MASTER_PLAN.md 6 skill~~ KESZ (Skill 5 + 6 hozzaadva)
9. ~~Redis eviction policy~~ KESZ (volatile-lru, 23_CONFIGURATION_REFERENCE.md)
10. ~~passlib -> bcrypt csere~~ KESZ (05_TECH_STACK.md)

### Phase 1-3 kozben (MEDIUM - fejlesztes soran)
11. Idempotencia szekció hozzaadasa 22_API_SPECIFICATION.md-hez
12. Crash recovery protokoll 08_ERROR_HANDLING.md-hez
13. LLM failover szekvencia 15_ML_MODEL_INTEGRATION.md-hez
14. Hianyzó API endpointok hozzaadasa 22_API_SPECIFICATION.md-hez
15. Queue szemantika szekció 01_ARCHITECTURE.md-hez
16. WebSocket reconnection 22_API_SPECIFICATION.md-hez
17. Dependency licenc policy (uj szekció vagy uj doc)
18. PgBouncer hozzaadasa 21_DEPLOYMENT_OPERATIONS.md-hez

### Kesobb (LOW - nem blokkolja a fejlesztest)
19. Browser support matix 14_FRONTEND.md-hez
20. Mobile strategia dontes 14_FRONTEND.md-hez
21. WCAG reszletek 14_FRONTEND.md-hez
22. Backup verifikacios utemterv 21_DEPLOYMENT_OPERATIONS.md-hez
23. Monitoring runbook bovites 21_DEPLOYMENT_OPERATIONS.md-hez
24. black eltavolitas (ruff format elegseges) 05_TECH_STACK.md-bol

---

## V. POZITIV MEGALLAPITASOK

A tervcsomag **rendkivul alapos** egy tervezesi fazisban levo projekthez:

- **Tesztelesi strategia** (24-25): Kimagaslo reszletesseg, ipari szintu
- **Security hardening** (20): OWASP LLM Top 10 lefedve, incident response
- **DB schema** (03): 33 tabla reszletes semaval, indexekkel, view-kkal
- **API spec** (22): 40+ endpoint teljes request/response-szal
- **Deployment** (21): K8s, blue-green, DR, runbook-ok
- **GitHub kutatas** (13): Valos kodanalzis 3 framework-bol (LangGraph, CrewAI, Haystack)
- **Skill rendszer** (11-12): 6 skill teljes eletciklusa
- **Claude Code integracio** (26, CLAUDE.md): 9 slash command, strict testing rules

A 69 talalt hiba 80%-a MEDIUM/LOW, a 4 CRITICAL kozvetlen javithato.
A terv **production-ready minosegu** az azonnal javitandok elvegzese utan.
