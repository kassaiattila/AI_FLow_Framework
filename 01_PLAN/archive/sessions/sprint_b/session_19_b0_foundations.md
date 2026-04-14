# AIFlow Sprint B — Session 19 Prompt (B0: Guardrail Per-Function + Alapok)

> **Datum:** 2026-04-05 (session 18 utan)
> **Elozo session:** S18 — Sprint A lezaras (A6+A7+A8, v1.2.2 tag, PR merged to main)
> **Branch:** `feature/v1.3.0-service-excellence` (UJ BRANCH — main-rol leagaztatni!)
> **Port:** API 8102, Frontend 5174 (Vite proxy → 8102)
> **Utolso commit:** `6610ec5` fix(docs): remove nested code fences
> **Elozo PR:** #1 merged to main (v1.2.2)

---

## AKTUALIS TERV

**`01_PLAN/58_POST_SPRINT_HARDENING_PLAN.md`** — Sprint B (v1.3.0): B0-B11, ~17 session (S19-S35).

---

## KONTEXTUS

### Sprint A Eredmenyek (v1.2.2 — COMPLETE)

| Fazis | Tartalom | Commit |
|-------|----------|--------|
| A0 | CI/CD Green | 27e9c82 |
| A1 | Ruff 1,234 → 0 | a32a84d |
| A2 | Halott kod audit | 2c0e078 |
| A3 | Security hardening (JWT RS256, CORS, rate limit, headers) | 176f137 |
| A4 | Stub cleanup (-1149 sor) | 87b896e |
| A5 | Guardrail framework (InputGuard, OutputGuard, ScopeGuard) | ba8d6c8 |
| A6-A8 | Post-audit + javitasok + v1.2.2 tag | 405723a |

### Sprint B Architektura (KULCSFONTOSSAGU!)

```
FEJLESZTESI IDO (Claude Code tamogatja):
  Tervezes → Fejlesztes → TESZTELES → Karbantartas → Debug
  Claude Code NEM futtatja uzemszeruen az AIFlow-kat!

UZEMELTETESI IDO (Docker containers, ugyfel-ready):
  UI (aiflow-admin) → FastAPI → Pipeline Runner → Services
  Claude Code NEM SZUKSEGES — minden onalloan fut!
```

### Infrastruktura Szamok (v1.2.2)

- 26 service, 162 API endpoint (25 router), 46 DB tabla, 29 migracio, 18 adapter
- 6 pipeline template, 22 UI oldal
- 1164 unit test, 76 guardrail teszt, 97 security teszt, 54 promptfoo test case
- 6 skill (qbpp meg letezik — B0.2-ben toroljuk → 5 skill)
- Docker: PostgreSQL 5433, Redis 6379, Kroki 8000
- Auth: admin@bestix.hu / admin
- Langfuse: ENABLED (cloud endpoint, .env-ben konfiguralt)
- Azure DI: INTEGRALT de azure_enabled=false (B3-ban lesz true)

### Meglevo Keretrendszer (HASZNALANDO, nem ujraepitendo!)

| Komponens | Hol | Sprint B hasznalat |
|-----------|-----|-------------------|
| PipelineRunner + Compiler | pipeline/ | B3 Invoice Finder |
| 18 Adapter | pipeline/adapters/ | B3, B4, B5 |
| 6 Pipeline Template | pipeline/builtin_templates/ | B3 (invoice_v1/v2!) |
| PromptManager | prompts/manager.py | B0.5 lifecycle, B1-B5 |
| DocumentRegistry | documents/ | B3, B7 |
| AzureDocIntelligence | tools/azure_doc_intelligence.py | B3 (scan szamlak) |
| HumanReviewService | services/human_review/ | B3.5, B7 |
| NotificationService | services/notification/ | B3 |
| GuardrailFramework | guardrails/ | B0.1, B1 |
| 142+ API endpoint | api/v1/ | B3, B8, B9 |

---

## B0 FELADAT: Guardrail Per-Function + Alapok

> **Gate:** Per-skill PII strategia dok KESZ, qbpp TOROLVE, architektura dok frissitve,
> 10-pontos checklist KESZ, 2 uj slash command, OpenAPI export, dok szabalyok.

### B0.1 — Per-Skill PII Strategia Tervdokumentum

A fix PII masking MEGHIUSITJA az uzleti funkciokat!
Invoice processing-nel adoszam/bankszamla KELL az LLM prompt-ban.

Per-skill PII config terv:

| Skill | pii_masking | allowed_pii | Indoklas |
|-------|-------------|-------------|----------|
| aszf_rag_chat | ON (full) | [] | Chat — SEMMI PII |
| email_intent | PARTIAL | [email, name, company] | Routing-hoz kell |
| invoice_processor | OFF | [ALL] | Szamla mezok = PII |
| process_docs | ON | [] | Doku generalas — nincs PII |
| cubix_course_capture | ON | [] | Video transcript — nincs PII |

OUTPUT: `01_PLAN/61_GUARDRAIL_PII_STRATEGY.md`
- Tartalmazzon: per-skill config peldak (guardrails.yaml reszlet)
- Tartalmazzon: a GuardrailConfig bovitesi tervet (pii_masking mode: on/off/partial)
- Tartalmazzon: teszteles modszertant (hogyan ellenorizzuk a PII kezelest)

### B0.2 — qbpp_test_automation TORLES

```bash
# 1. Skill mappa torles
rm -rf skills/qbpp_test_automation/

# 2. Hivatkozasok frissitese
# CLAUDE.md (root): 6 skill → 5 skill
# 01_PLAN/CLAUDE.md: 6 skill → 5 skill
# FEATURES.md: qbpp sor torles
# .claude/commands/validate-plan.md: mar frissitve (6→5 note)

# 3. Teszteles
pytest tests/unit/ -q                    # PASS, nincs import hiba
ruff check src/ tests/ skills/          # PASS
```

### B0.3 — 10 Pontos Production Checklist

A checklist `01_PLAN/58_POST_SPRINT_HARDENING_PLAN.md`-ben mar definialt.
A B0-ban formalizaljuk es a `/service-hardening` command-ba epítjuk (B0.6).

### B0.4 — Architektura Dokumentacio

OUTPUT: `01_PLAN/62_DEPLOYMENT_ARCHITECTURE.md`

Tartalom:
- Fejlesztesi ciklus (Claude Code slash commands, teszteles)
- Uzemeltetesi architektura (Docker Compose diagram)
- Deploy folyamat: dev → staging → production
- UI mint pipeline vezerlo (user inditja, NEM Claude)
- Prompt Lifecycle (release nelkuli frissites Langfuse-on keresztul)

### B0.5 — Prompt Lifecycle Management

A 6 lepesu ciklus dokumentalva van `58_POST_SPRINT_HARDENING_PLAN.md`-ben.
Ami HIÁNYZIK es implementálni kell:

1. `POST /api/v1/prompts/{name}/invalidate` endpoint (cache torles)
2. `POST /api/v1/prompts/reload-all` endpoint
3. `/prompt-tuning` slash command

Meglevo (NEM kell epiteni):
- PromptManager (`src/aiflow/prompts/manager.py`) — Langfuse v4 SDK, cache, invalidate()
- Langfuse konfiguralt (.env: AIFLOW_LANGFUSE__ENABLED=true)

### B0.6 — Uj Slash Command-ok

`.claude/commands/service-hardening.md` (UJ):
- Input: service nev
- 10-pontos checklist egyenkenti ellenorzese
- Output: PASS/FAIL tabla

`.claude/commands/prompt-tuning.md` (UJ):
- Input: skill nev
- 6 lepesu Prompt Lifecycle ciklus orchestralasa
- Output: prompt YAML diff, eval riport

### B0.7 — OpenAPI 3.0 Export

```bash
# scripts/export_openapi.py (UJ):
# FastAPI app → docs/api/openapi.json + openapi.yaml
mkdir -p docs/api
python scripts/export_openapi.py
# Elso export: 162 endpoint dokumentalva
```

### B0.8 — Dokumentacios Szabalyok + Sprint B Learnings

Dokumentacios szabalyok CLAUDE.md-ben mar definiálva (Session 18).
Ami meg kell:
- `.claude/sprint_b_learnings/` — ures fajlok letrehozasa (claude_md_proposals.md, stb.)
- Session 19 tanulsagok rogzitese → `.claude/sprint_b_learnings/`

---

## FAJLOK AMIK ERINTETTEK

```
# TORLES
skills/qbpp_test_automation/              # Teljes mappa torles

# UJ FAJLOK
01_PLAN/61_GUARDRAIL_PII_STRATEGY.md      # PII strategia per-skill
01_PLAN/62_DEPLOYMENT_ARCHITECTURE.md      # Deploy architektura dok
scripts/export_openapi.py                  # OpenAPI export script
docs/api/openapi.json                      # Generalt OpenAPI schema
docs/api/openapi.yaml                      # YAML verzio
docs/api/CHANGELOG.md                      # API changelog
.claude/commands/service-hardening.md      # UJ slash command
.claude/commands/prompt-tuning.md          # UJ slash command
src/aiflow/api/v1/prompts.py              # UJ: prompt invalidate endpoint
.claude/sprint_b_learnings/*.md            # Learnings fajlok

# MODOSITANDO
CLAUDE.md                                  # 6→5 skill, szamok
01_PLAN/CLAUDE.md                          # 6→5 skill
FEATURES.md                                # qbpp torles, prompt endpoint
01_PLAN/58_POST_SPRINT_HARDENING_PLAN.md   # B0 progress → DONE
```

---

## KORNYEZET ELLENORZES (session indulaskor KOTELEZO!)

```bash
# 0. UJ BRANCH LETREHOZAS (fontos!)
git checkout main
git pull origin main
git checkout -b feature/v1.3.0-service-excellence
git log --oneline -3   # → v1.2.2 tag BENNE VAN main-ben?

# 1. Python venv
.venv/Scripts/python.exe --version       # → 3.12.x
.venv/Scripts/python.exe -c "import aiflow.guardrails; print('OK')"

# 2. Docker
docker ps --format "table {{.Names}}\t{{.Status}}" | head -5

# 3. Teszt baseline
python -m pytest tests/unit/ -q --co 2>&1 | tail -1   # → 1164 tests

# 4. Ruff
ruff check src/ tests/ 2>&1 | tail -1   # → All checks passed!

# 5. TypeScript
cd aiflow-admin && npx tsc --noEmit      # → 0 error

# 6. qbpp LETEZIK (meg nem toroltuk)
ls skills/qbpp_test_automation/          # → meg van
```

---

## VEGREHAJTASI TERV (Session 19)

```
 1. KORNYEZET ELLENORZES → branch, venv, Docker, teszt baseline
 2. UJ BRANCH: feature/v1.3.0-service-excellence (main-rol)
 3. B0.2: qbpp_test_automation TORLES + hivatkozas frissites + teszt
 4. B0.1: PII strategia dok iras (01_PLAN/61_GUARDRAIL_PII_STRATEGY.md)
 5. B0.4: Architektura dok iras (01_PLAN/62_DEPLOYMENT_ARCHITECTURE.md)
 6. B0.3+B0.6: /service-hardening + /prompt-tuning slash command-ok
 7. B0.5: Prompt invalidate API endpoint (src/aiflow/api/v1/prompts.py)
 8. B0.7: OpenAPI export script + elso export
 9. B0.8: Sprint B learnings fajlok + S19 tanulsagok
10. TESZTELES: pytest + ruff + tsc → ALL PASS
11. COMMIT + 58_plan progress tabla frissites (B0 → DONE)
12. PUSH
```

---

## KOTELEZO SZABALYOK (MINDEN session-ben!)

### Session vegen:
1. `pytest tests/unit/ -q` → ALL PASS
2. `ruff check src/ tests/` → CLEAN
3. `cd aiflow-admin && npx tsc --noEmit` → 0 error (ha UI valtozas)
4. **58_POST_SPRINT_HARDENING_PLAN.md** progress tabla: B0 DONE + datum + commit
5. **CLAUDE.md** (root + 01_PLAN/): szamok frissitese (5 skill!)
6. **FEATURES.md** frissitese (qbpp torolve)
7. `.claude/sprint_b_learnings/` → session tanulsagok rogzitese

### Commit konvencio:
- `feat(...):`  — uj funkcionalitas
- `docs:` — dokumentacio
- `refactor:` — strukturalis valtozas (qbpp torles)
- Co-Authored-By header MINDEN commit-ben

### Teszteles (STRICT!):
- Minden uj endpoint: curl teszteles (source=backend)
- Minden uj command: kiprobalni legalabb 1x
- qbpp torles utan: TELJES regresszio (pytest tests/unit/ -q)

---

## ELOZO SESSION TANULSAGAI (S18)

1. **Beagyazott code fence-ek tortek a markdown-t** — SOHA NE hasznalj ``` -t egy masik ``` blokkban!
2. **Unicode box-drawing + emoji = mojibake** — ASCII art-ot hasznalj vagy sima szoveget
3. **Session szamozas eltolodas** — uj fazis hozzaadasakor (B3.5) MINDEN utana jovo session szamot frissiteni kell
4. **Konzisztencia ellenorzes KOTELEZO** — szamok (endpoint, adapter, skill) MINDEN fajlban egyezesenek kell
5. **Archivalt fajlok hivatkozasa** — ha fajlt mozgatunk archive/-ba, a command-ok hivatkozasait is frissiteni kell
6. **Docker Desktop WSL issue** — `wsl --shutdown` + ujrainditas ha "starting" loop-ban ragad
7. **LLM self-report confidence megbizhatatlan** — szabaly-alapu per-field szamitas kell (B3.5)
8. **Azure DI intakt** — azure_enabled=false a config-okban, de a kod 100% mukodik

---

## SPRINT B TELJES UTEMTERV (kontextus)

```
S19: B0   — Guardrail per-function + qbpp torles + dok (← JELEN SESSION)
S20: B1.1 — LLM guardrail promptok (4 YAML)
S21: B1.2 — Per-skill guardrails.yaml
S22: B2.1 — Core infra service tesztek (65 test)
S23: B2.2 — v1.2.0 service tesztek (65 test)
S24: B3.1 — Invoice Finder: email + doc acquisition
S25: B3.2 — Invoice Finder: extract + report + notification
S26: B3.5 — Konfidencia scoring hardening
S27: B4.1 — Skill hardening: aszf_rag + email_intent
S28: B4.2 — Skill hardening: process_docs + invoice + cubix
S29: B5   — Diagram pipeline + Spec writer
S30: B6   — Portal struktura ujragondolas + journey tervezes
S31: B7   — Verification Page v2
S32: B8   — UI Journey implementacio
S33: B9   — Docker containerization + deploy
S34: B10  — POST-AUDIT
S35: B11  — v1.3.0 tag + merge
```
