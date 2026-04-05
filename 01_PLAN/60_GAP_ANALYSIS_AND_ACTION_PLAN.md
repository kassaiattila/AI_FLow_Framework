# AIFlow Claude Code Configuration — Gap Analysis & Action Plan

> **Datum:** 2026-04-05
> **Referencia:** `01_PLAN/60_CLAUDE_CODE_BEST_PRACTICES_REFERENCE.md` (teljes best practice)
> **Cel:** A jelenlegi AIFlow konfiguraciot az 5 retegu architektura best practice-ekhez igazitani

---

## 1. Gap Analysis — Jelenlegi Allapot vs Best Practice

### 1.1 CLAUDE.md — KRITIKUS TULTERHELTSEG

| Metrika | Jelenlegi | Best Practice | Gap |
|---------|-----------|---------------|-----|
| Osszes sor | **802** | 80-150 | **5-10x tulmeretezett!** |
| Instrukció-szeru sorok | **~494** | ~100-150 | **3-5x tul!** |
| Fejezetek | 25+ | 5-8 | Tul sok terulet |

**Kovetkezmeny:** Claude **egyenletesen gyengul** MINDEN instrukció koveteseben.
Ez magyarazza miert "felejti el" a gate-eket, tesztelesi szabalyokat, commit konvenciokat.

**Best practice 3.2:** "Te maximum ~100-150 sajat instrukciót adhatsz meg mielott
a kovetes minosege degradalodik. Ahogy no az instrukciok szama, a kovetesi minoseg
egyenletesen csokken."

### 1.2 HOOKS — TELJESEN HIANYOZNAK

| Hook | Jelenlegi | Best Practice |
|------|-----------|---------------|
| `.claude/settings.json` | **NEM LETEZIK** | KELL — hooks + permissions |
| PostToolUse: ruff (*.py) | **NINCS** | Determinisztikus lint minden .py irasra |
| PostToolUse: tsc (*.tsx) | **NINCS** | Determinisztikus typecheck |
| PreToolUse: .env vedelem | **NINCS** | Deny .env modositas |
| PreToolUse: destruktiv parancs | Csak settings.local deny | settings.json hook |
| Stop: teszt emlekezteto | **NINCS** | Agent hook session vegen |

**Best practice 4.1:** "A CLAUDE.md instrukciok tanacsado jelleguek — kontextus
telitodessel elfelejtodhetnek. A hook-ok determinisztikusak — MINDIG lefutnak."

Az AIFlow-ban a lint/test szabalyok CLAUDE.md-ben vannak = "tanacsado" → elfelejthetok!

### 1.3 SKILLS — TELJESEN HIANYOZNAK

| Aspektus | Jelenlegi | Best Practice |
|----------|-----------|---------------|
| `.claude/skills/` konyvtar | **NEM LETEZIK** | KELL — domain tudas ide |
| UI pipeline szabalyok (90+ sor) | CLAUDE.md-ben | Skill: on-demand betoltes |
| Tesztelesi szabalyok (80+ sor) | CLAUDE.md-ben | Skill: on-demand betoltes |
| Pipeline szabalyok (60+ sor) | CLAUDE.md-ben | Skill: on-demand betoltes |
| Service konvenciok (40+ sor) | CLAUDE.md-ben | Skill: on-demand betoltes |

**Best practice 5.1:** "A skill-ek NEM minden session-ben toltodnek be — csak ha
Claude relevansnak iteli. Ezzel a kontextus tiszta marad."

~270 sor a CLAUDE.md-bol skill-ekbe mozgathato = CLAUDE.md 802 → ~530 → ~150.

### 1.4 SUBAGENTS — TELJESEN HIANYOZNAK

| Agent | Jelenlegi | Best Practice |
|-------|-----------|---------------|
| `.claude/agents/` konyvtar | **NEM LETEZIK** | KELL |
| Security reviewer | NINCS | Biztonsagi audit izolalt kontextusban |
| QA tester | NINCS | Teszt futtatas + validacio |
| Plan validator | NINCS | Terv konzisztencia check |

**Best practice 7.1:** "A piszkos munka (teszteles, nagy diffek, iterativ hibakereses)
nem szennyezi a fo kontextust."

### 1.5 COMMANDS — Reszben megvan, problema: nem hasznaljuk

| Aspektus | Jelenlegi | Best Practice |
|----------|-----------|---------------|
| Commands konyvtar | 22 fajl | OK (→ 20 fajl: 4 archiv, 2 uj) |
| Elavult tartalom | Rossz portok, regi hivatkozasok | Frissitendo |
| Feedback mechanizmus | **NINCS** | KELL — command hatekonsag merese |
| Szisztematikus hasznalat | NEM hasznaljuk oket | Session prompt command hivatasokkal |

**Best practice 6.1:** "Ha determinisztikus, ismetelheto terminal belepesi pontot
akarsz → command formatum."

### 1.6 EGYEB HIANYOSSAGOK

| Aspektus | Jelenlegi | Best Practice |
|----------|-----------|---------------|
| CLAUDE.local.md | NEM LETEZIK | Opcionalis (szemelyes feluliras) |
| .gitignore CLAUDE.local | NINCS | KELL ha letrehozzuk |
| Compaction instrukció | NINCS CLAUDE.md-ben | KELL — mit orizzen meg |
| Kontextus-menedzsment | Nem tudatos | /clear, /compact szabalyok |
| Multi-session workflow | Nem hasznaljuk | Spec→Implement→Review szeparacio |

---

## 2. Az 5 Reteg Implementacios Terv AIFlow-ra

### RETEG 1: CLAUDE.md Refactoring (802 → ~150 sor)

**Ez a LEGMAGASABB HATASU valtozas.** A tulmeretezett CLAUDE.md az oka hogy
Claude "elfelejti" a szabalyokat. Best practice: max 100-150 sajat instrukció.

#### Uj CLAUDE.md Struktura (tervezet, ~100 sor)

```
# AIFlow Project
## Overview (10 sor)
  Stack, cel, port, branch
## Structure (15 sor)
  Fo konyvtarak, skill-ek, UI
## Key Numbers (5 sor)
  Service, endpoint, teszt, migracio szamok
## Build & Test (10 sor)
  make api, make test, make lint, pytest, tsc
## Code Conventions (15 sor)
  Top 10 legfontosabb szabaly (async, Pydantic, structlog, stb.)
## Git Workflow (8 sor)
  Branch, commit, NEVER rules
## Current Plan (3 sor)
  58-as terv hivatkozas
## Slash Commands (12 sor)
  Funkcionalis csoportositas
## IMPORTANT (10 sor)
  Real testing, plan update, compaction
## References (8 sor)
  Skill-ekre, tervekre, best practice-re hivatkozas
```

#### Mi kerul KI a CLAUDE.md-bol (→ skills)

| Jelenlegi szekció | Sorok | Hova kerul |
|-------------------|-------|------------|
| MANDATORY Admin UI Development Rules | ~90 | **Skill: aiflow-ui-pipeline** |
| MANDATORY Testing & Regression Rules | ~80 | **Skill: aiflow-testing** |
| v1.2.0 Orchestration Development Rules | ~60 | **Skill: aiflow-pipeline** |
| Architecture Patterns + Service Isolation | ~40 | **Skill: aiflow-services** |
| Slash Command reszletes leirasok | ~40 | **Nem kell — command fajlok maguk a leiras** |
| Coverage Gate tablazatok | ~20 | **Skill: aiflow-testing** |
| VALOS Teszteles fazisokent tabla | ~15 | **Skill: aiflow-testing** |
| Technology Decisions lista | ~15 | **Skill: aiflow-services** |
| Viewer Completeness Rules | ~10 | **Skill: aiflow-ui-pipeline** |
| **OSSZ kiszervezheto** | **~370 sor** | |

802 - 370 = ~430. Tovabb tomoritjuk → ~100-150 sor.

### RETEG 2: HOOKS — settings.json Letrehozas

**Best practice szerint:** Barmit ami MINDIG le kell fusson → hook.

#### AIFlow-specifikus hook-ok:

**PostToolUse — Automatikus lint .py fajlokra:**
```json
{
  "matcher": "Write(*.py)",
  "hooks": [{
    "type": "command",
    "command": ".venv/Scripts/python.exe -m ruff check --fix \"$FILEPATH\" && .venv/Scripts/python.exe -m ruff format \"$FILEPATH\""
  }]
}
```

**PreToolUse — .env vedelem:**
```json
{
  "matcher": "Write(.env*)",
  "hooks": [{
    "type": "command",
    "command": "echo {\"decision\":\"deny\",\"reason\":\".env modositasa tiltott\"}"
  }]
}
```

**PreToolUse — Destruktiv parancsok:**
```json
{
  "matcher": "Bash(rm -rf *)",
  "hooks": [{
    "type": "command",
    "command": "echo {\"decision\":\"deny\",\"reason\":\"Destruktiv parancs blokkolva\"}"
  }]
}
```

**MEGJEGYZES:** A hooks szintaxis es kornyezeti valtozok ($FILEPATH) a Claude Code
verziotol fuggnek. Eloszor 1 egyszeru hook-ot tesztelunk, utana bovitjuk.
A pontos matcher szintaxist a `/hooks` interaktiv paranccsal ellenorizzuk.

### RETEG 3: SKILLS — 4 AIFlow-specifikus Skill

#### Skill 1: aiflow-ui-pipeline

```
.claude/skills/aiflow-ui-pipeline/SKILL.md
```

**Frontmatter:**
```yaml
name: aiflow-ui-pipeline
description: >
  AIFlow admin UI fejlesztesi pipeline 7 HARD GATE-tel.
  Hasznald amikor: UI oldalt, komponenst, viewert fejlesztesz,
  Figma design-t csinalsz, vagy aiflow-admin/ kodot irsz.
allowed-tools: Read, Write, Grep, Glob, Bash
```

**Tartalom:** A jelenlegi CLAUDE.md kovetkezo szekcioi:
- MANDATORY Admin UI Development Rules (7 HARD GATE pipeline)
- GATE ARTEFACT REGISTRY
- MANDATORY GATE CHECK PROTOCOL
- Untitled UI + Tailwind Rules
- i18n Rules
- Vite + Routing Rules
- UI Component Checklist
- UI Testing Protocol
- No Silent Mock Data (Viewer rules)

#### Skill 2: aiflow-testing

```
.claude/skills/aiflow-testing/SKILL.md
```

**Frontmatter:**
```yaml
name: aiflow-testing
description: >
  AIFlow tesztelesi szabalyok, regresszio, coverage gate-ek.
  Hasznald amikor: teszteket irsz, futtatod, vagy commit
  elott regressziot ellenorizsz. SOHA ne mock/fake!
allowed-tools: Read, Bash, Grep, Glob
```

**Tartalom:**
- MANDATORY Testing & Regression Rules
- The Golden Rule (no code without tests)
- Development Step Protocol
- What is FORBIDDEN
- Regression Levels (L1-L5)
- Coverage Gates tabla
- Test File Registry Header
- Regression Matrix
- VALOS Teszteles fazisokent tabla

#### Skill 3: aiflow-pipeline

```
.claude/skills/aiflow-pipeline/SKILL.md
```

**Frontmatter:**
```yaml
name: aiflow-pipeline
description: >
  AIFlow pipeline es adapter fejlesztesi szabalyok.
  Hasznald amikor: pipeline YAML-t, adaptert irsz,
  vagy a PipelineRunner/Compiler-rel dolgozol.
allowed-tools: Read, Write, Grep, Glob, Bash
```

**Tartalom:**
- API Compatibility szabalyok
- DB Migration Safety
- Pipeline Development Rules
- Adapter Development Rules
- L0 Smoke Test
- Notification & HITL Rules
- Document Extraction & Intent Rules

#### Skill 4: aiflow-services

```
.claude/skills/aiflow-services/SKILL.md
```

**Frontmatter:**
```yaml
name: aiflow-services
description: >
  AIFlow service architektura es konvenciok.
  Hasznald amikor: service-t fejlesztesz, modositasz,
  vagy a service reteg architekturaval dolgozol.
allowed-tools: Read, Write, Grep, Glob, Bash
```

**Tartalom:**
- Architecture Patterns (Step, SkillRunner, WorkflowRunner)
- Service Isolation
- Technology Decisions (vegleges)
- Frontend Stability rules
- Skill Running (CLI + programmatic)
- Configurable JSON Schema System

### RETEG 4: COMMANDS — Frissites + 2 Uj + Feedback

A `59_COMMAND_WORKFLOW_AUDIT.md` alapjan:

| Akcio | Command-ok | Db |
|-------|-----------|-----|
| Archivalas | start-phase, phase-status, new-skill, new-module | 4 |
| Tartalmi javitas | dev-step, regression, update-plan, validate-plan, service-test, ui-journey, new-pipeline, new-prompt, ui-design, ui-page | 10 |
| Uj | service-hardening, prompt-tuning | 2 |
| Feedback | command_feedback.md | 1 fajl |

**Vegso szam: 22 - 4 + 2 = 20 command**

### RETEG 5: SUBAGENTS — 3 Specialista

#### Agent 1: security-reviewer
```
.claude/agents/security-reviewer.md
```
- Biztonsagi audit: OWASP Top 10, hardcoded secrets, injection, PII
- Model: opus | Tools: Read, Grep, Glob
- Sprint B hasznalat: B10 POST-AUDIT

#### Agent 2: qa-tester
```
.claude/agents/qa-tester.md
```
- Teszt futtatas, coverage ellenorzes, regresszio detektalas
- Model: sonnet | Tools: Read, Bash, Grep, Glob
- Sprint B hasznalat: B2 service tesztek, B10 POST-AUDIT

#### Agent 3: plan-validator
```
.claude/agents/plan-validator.md
```
- Terv konzisztencia: szamok, hivatkozasok, cross-reference
- Model: sonnet | Tools: Read, Grep, Glob
- Sprint B hasznalat: B0, B6, B10 terv validacio

---

## 3. Vegrehajtas Sorrendje (Prioritas alapjan)

### FAZIS 1: AZONNALI (Ez a session — legmagasabb hatas)

```
1.1  Referencia fajl elmentese                         DONE
1.2  Gap analysis megirasa                             DONE
1.3  4 Skill letrehozasa (.claude/skills/)             TODO
1.4  CLAUDE.md ujrairasa (802 → ~150 sor)              TODO
1.5  settings.json letrehozasa (hooks)                 TODO
1.6  .gitignore kiegeszites (CLAUDE.local.md)          TODO
```

### FAZIS 2: KOZEPES PRIORITAS (Session vege vagy kovetkezo session)

```
2.1  3 Agent letrehozasa (.claude/agents/)             TODO
2.2  4 Command archivalas                              TODO
2.3  10 Command tartalmi javitas                       TODO
2.4  2 Uj command (service-hardening, prompt-tuning)   TODO
2.5  command_feedback.md letrehozasa                   TODO
2.6  01_PLAN/CLAUDE.md frissites (szamok, hivatkozasok) TODO
```

### FAZIS 3: B0 TARTALMI FELADATOK

```
3.1  B0.2 qbpp torles                                 TODO
3.2  B0.1 PII strategia dok                            TODO
3.3  B0.4 Architektura dok                             TODO
3.4  B0.5 Prompt API endpoint                          TODO
3.5  B0.7 OpenAPI export                               TODO
```

### FAZIS 4: VERIFIKACIO

```
4.1  Ellenorzo checklist lefuttatasa (Section 5)       TODO
4.2  Egy valodi /dev-step probahasznalat               TODO
4.3  Hook teszteles (ruff, .env vedelem)               TODO
4.4  Skill auto-trigger teszteles                      TODO
```

---

## 4. Session Prompt Frissites

A session_20 prompt UJRAIRASA szukseges az 5 retegu architektura szerint:

**Regi megkozelites (session_20 jelenlegi):**
- B0 feladatok + command cleanup → inline lepesek

**Uj megkozelites:**
- FAZIS 1 az 5 reteg kialakitasa (skill, hook, CLAUDE.md, agent)
- FAZIS 2 command cleanup + uj command-ok
- FAZIS 3 B0 tartalmi feladatok — MAR az uj retegen keresztul
- FAZIS 4 verifikacio

---

## 5. Ellenorzo Checklist (Implementacio Utan)

### Reteg 1: CLAUDE.md
| # | Ellenorzes | Hogyan |
|---|-----------|--------|
| 1 | CLAUDE.md <= 150 sor | `wc -l CLAUDE.md` |
| 2 | Nincs UI gate reszlet | `grep "HARD GATE" CLAUDE.md` → max 1 hivatkozo sor |
| 3 | Nincs coverage tabla | `grep "Coverage Gate" CLAUDE.md` → 0 |
| 4 | Nincs slash command reszletes leiras | Csak funkcionalis csoportositas |
| 5 | Van compaction instrukció | `grep -i "compaction" CLAUDE.md` → van |
| 6 | Van referencia skill-ekre | `grep "skill" CLAUDE.md` → hivatkozasok |

### Reteg 2: Hooks
| # | Ellenorzes | Hogyan |
|---|-----------|--------|
| 7 | settings.json letezik | `ls .claude/settings.json` |
| 8 | PostToolUse hook van | `grep "PostToolUse" .claude/settings.json` |
| 9 | PreToolUse .env deny van | `grep ".env" .claude/settings.json` |
| 10 | Hook mukodik (ruff) | Irj .py fajlt → lefut-e ruff automatikusan? |
| 11 | Hook mukodik (.env deny) | Probald irni .env-t → deny? |

### Reteg 3: Skills
| # | Ellenorzes | Hogyan |
|---|-----------|--------|
| 12 | 4 skill letezik | `ls .claude/skills/` |
| 13 | Skill SKILL.md frontmatter helyes | name, description, allowed-tools mezo |
| 14 | UI skill tartalmazza a 7 HARD GATE-et | `grep "GATE" .claude/skills/aiflow-ui-pipeline/SKILL.md` |
| 15 | Testing skill tartalmazza coverage-et | `grep "Coverage" .claude/skills/aiflow-testing/SKILL.md` |

### Reteg 4: Commands
| # | Ellenorzes | Hogyan |
|---|-----------|--------|
| 16 | Command szam = 20 | `ls .claude/commands/*.md \| wc -l` |
| 17 | 4 archiv command | `ls .claude/commands/archive/` |
| 18 | Feedback fajl letezik | `ls .claude/sprint_b_learnings/command_feedback.md` |

### Reteg 5: Agents
| # | Ellenorzes | Hogyan |
|---|-----------|--------|
| 19 | 3 agent letezik | `ls .claude/agents/` |
| 20 | Agent frontmatter helyes | name, description, model, allowed-tools |

### Egyeb
| # | Ellenorzes | Hogyan |
|---|-----------|--------|
| 21 | .gitignore tartalmazza CLAUDE.local.md | `grep CLAUDE.local .gitignore` |
| 22 | 01_PLAN/CLAUDE.md frissitve | Szamok egyeznek root CLAUDE.md-vel |
| 23 | Nincs redundancia 5 reteg kozott | Minden info PONTOSAN 1 helyen van |

---

## 6. Iteracios Terv (Sprint B teljes idoszakara)

**Best practice 9.2:** "A CLAUDE.md, skill-ek es hook-ok elo dokumentumok —
folyamatosan finomitandok."

### Mikor iteralunk:

| Trigger | Akcio |
|---------|-------|
| Claude elfelejt egy CLAUDE.md szabalyt | Vizsgald: tul hosszu? → mozgasd skill-be |
| Claude elfelejt egy hook-ot | Lehetetlen ha hook → ELLENORIZD a hook mukodeset |
| Skill nem toltodik be automatikusan | Javitsd a description-t (front-load use case) |
| Command nem teszi amit kell | Command feedback + javitas |
| Session soran kontextus telitodik | Hasznalj subagent-eket / /compact |

### Minden session vegen:

1. **Command feedback** → `.claude/sprint_b_learnings/command_feedback.md`
2. **Kerdezd meg:** "Claude TENYLEG hibazna enelkul?" — ha nem, torold az instrukciót
3. **Ha CLAUDE.md nott:** Nézd meg mit mozgathatsz skill-be
4. **Ha uj pattern:** Dokumentald `.claude/sprint_b_learnings/workflow_patterns.md`-be
