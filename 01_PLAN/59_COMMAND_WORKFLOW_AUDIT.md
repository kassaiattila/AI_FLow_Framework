# AIFlow Slash Command & Workflow Audit — Sprint B Restructuring

> **Datum:** 2026-04-05
> **Cel:** 22 command audit + Sprint B terv atdolgozas command-vezerelt munkafolyamatra
> **Strategia:** CLAUDE.md + commands + skills = AIFlow fejlesztes **iranyitasi retege**
> Minden command egy determinisztikus "funkcio" — a session prompt a "main()" ami hivja oket.

---

## 1. A Problema Diagnozisa

### Mi tortenik most:
- 22 slash command definialt, de SOHA nem lesznek szisztematikusan meghivva
- Session prompt-ok "inline" tartalmazzak a lepeseket (15 pontos vegrehajtasi terv)
- Ugyanaz a logika 3 helyen: CLAUDE.md, command fajl, session prompt
- Nincs visszajelzes — ha egy command nem vegzi jol a dolgat, nem tudjuk

### Az iranyitasi reteg architekturaja (ideal):

```
CLAUDE.md  ← KONFIG: szabalyok, szamok, kontextus, "MIKOR melyik command-ot"
    |
    v
Session Prompt  ← MAIN(): "MIT csinalunk ma" + command hivatasok
    |
    v
Commands (.claude/commands/)  ← FUNKCIOK: "HOGYAN" (determinisztikus lepesek, gate-ek)
    |
    v
Skills (.claude/commands/ + Skill tool)  ← SPECIALIS FUNKCIOK (generatorok, UI pipeline)
    |
    v
Feedback (.claude/sprint_b_learnings/)  ← VISSZAJELZES: mi mukodott, mi nem
```

### Szabaly: NINCS DUPLIKALAS
- Session prompt NEM ismetli a command logikajat — hivatkozik ra
- CLAUDE.md NEM ismetli a command tartalmat — csak azt mondja MIKOR hasznald
- Command NEM ismetli a CLAUDE.md szabalyokat — hivatkozik ra

---

## 2. Tartalmi Audit — KRITIKUS Hibak

### 2.1 Port Inkonzisztencia (KRITIKUS!)

| Command | Hasznalt port | Helyes |
|---------|--------------|--------|
| service-test.md | 8100 | **8102** |
| ui-api-endpoint.md | 8100 | **8102** |
| ui-page.md | 8101 | **8102** |
| pipeline-test.md | 8102 | 8102 (OK) |
| quality-check.md | 8102 | 8102 (OK) |

**FIX:** Minden command-ban `localhost:8102` (CLAUDE.md-ben is igy van).

### 2.2 Elavult Terv Hivatkozasok (KRITIKUS!)

| Command | Hivatkozott | Helyes |
|---------|------------|--------|
| dev-step.md:34 | `57_PRODUCTION_READY_SPRINT.md` | **`58_POST_SPRINT_HARDENING_PLAN.md`** |
| dev-step.md:15-21 | v1.2.0 tier branchek, v1.2.1 branch | **`feature/v1.3.0-service-excellence`** |
| new-pipeline.md:12,20 | `48_ORCHESTRABLE_SERVICE_ARCHITECTURE.md` | **archivalt! → adapter registry lekerdezese kozvetlen** |
| new-prompt.md:50 | `42_SERVICE_GENERALIZATION_PLAN.md` | **archivalt!** |
| ui-journey.md:9,66 | `42_SERVICE_GENERALIZATION_PLAN.md` Section 11 | **archivalt! → `01_PLAN/63_UI_USER_JOURNEYS.md`** |
| update-plan.md:56-70 | 36 tabla, 13 view, 13 migracio | **46 tabla, 6 view, 29 migracio** |

### 2.3 Ellentmondo Szamok (KRITIKUS!)

| Mezo | update-plan.md | validate-plan.md | Helyes (v1.2.2) |
|------|---------------|-----------------|----------------|
| DB tablak | 36 | 46 | **46** |
| DB nezetek | 13 | 6 | **6** |
| Migraciok | 13 | 29 | **29** |
| Skill-ek | 6 | 6 (5 after qbpp) | **6 → 5** |

### 2.4 Figma Channel ID

| Command | Hasznalt | CLAUDE.md-ben |
|---------|---------|--------------|
| ui-design.md:39 | `e71e0crh` | `hq5dlkhu` |

**FIX:** Mindkettot ellenorizni — melyik az aktualis Figma fajl.

### 2.5 Hardcoded Credentials

`pipeline-test.md` es `quality-check.md` tartalmaznak: `admin@bestix.hu` / `admin`
Ez elfogadhato dev/test kontextusban, de dokumentalni kell hogy CSAK dev kornyezetre vonatkozik.

---

## 3. Command Dontes Tablazat

### ARCHIVALAS (4 db → .claude/commands/archive/)

| Command | Indoklas |
|---------|----------|
| `/start-phase` | F0-F5 vertikalis szelet pipeline. Sprint B mas struktura (B0-B11). Soha nem lett hasznalva. |
| `/phase-status` | F0-F5 monitoring. Sprint B-ben a 58-as terv progress tablaja van. |
| `/new-skill` | Nincs uj skill Sprint B-ben. Ha kesobb kell, ujra megirjuk. |
| `/new-module` | Framework stabil. Nincs uj modul Sprint B-ben. |

### FRISSITENDO — TARTALMI JAVITAS SZUKSEGES (6 db)

| Command | Javitas |
|---------|---------|
| `/dev-step` | v1.3.0 branch, 58-as terv hivatkozas, elavult branch lista torles, egyszerusites |
| `/regression` | v1.3.0 kontextus, aktualis teszt szamok (1195 unit, 129 guardrail) |
| `/update-plan` | Helyes szamok (46 tabla, 6 view, 29 migracio), 58-as terv hivatkozas |
| `/validate-plan` | Szamok egyeztetese update-plan-nel, Sprint B kontextus |
| `/service-test` | Port javitas 8100→8102, fazis labelek frissitese |
| `/ui-journey` | Archiv 42_ hivatkozas → `01_PLAN/63_UI_USER_JOURNEYS.md` |

### KISEBB JAVITAS (4 db)

| Command | Javitas |
|---------|---------|
| `/new-pipeline` | Archiv 48_ hivatkozas → kozvetlen adapter registry |
| `/new-prompt` | Archiv 42_ hivatkozas torles |
| `/ui-design` | Figma channel ID ellenorzes, port 8102 |
| `/ui-page` | Port 8101→8102 |

### UJ (2 db)

| Command | Cel |
|---------|-----|
| `/service-hardening` | 10-pontos production checklist audit per skill/service (B4, B10) |
| `/prompt-tuning` | 6 lepesu prompt lifecycle ciklus (B1-B5) |

### VALTOZATLAN (6 db)

`/lint-check`, `/new-step`, `/new-test`, `/pipeline-test`, `/quality-check`, `/ui-api-endpoint`,
`/ui-component`, `/ui-viewer`

### Vegso szam: 22 - 4 + 2 = **20 command**

---

## 4. Command Feedback Mechanizmus

### Cel
Ha egy command nem vegzi jol a feladatat (kihagyja a gate-et, rossz output-ot general,
hibas ellenorzest vegez), azt dokumentaljuk es javitjuk.

### Implementacio

**Fajl:** `.claude/sprint_b_learnings/command_feedback.md`

**Formatum:**
```markdown
## /command-nev — Session SXX

**Hivva:** YYYY-MM-DD, B-fazis, feladat kontextus
**Eredmeny:** PASS / PARTIAL / FAIL
**Problema:** (ha nem PASS) Mi nem mukodott, miert
**Javitas:** (ha szukseges) Mit kell valtoztatni a command-ban
**Tanulsag:** (altalanos) Amit a jovo session-okben figyelembe kell venni
```

**Mikor irod:**
- MINDEN session vegen: at kell nezni melyik command-ot hivtuk meg es hogyan teljesitett
- Ha egy command FAIL vagy PARTIAL → azonnali javitas a command fajlban
- Ha egy command PASS de fejlesztheto → javaslat `.claude/sprint_b_learnings/command_proposals.md`-be

**Session lezaras bovitett checklist:**
```
1. /lint-check → 0 error
2. /regression → ALL PASS
3. /update-plan → 58 progress + szamok
4. COMMAND FEEDBACK → .claude/sprint_b_learnings/command_feedback.md
5. Sprint B learnings → .claude/sprint_b_learnings/
```

---

## 5. Sprint B Fazisok — Command Orchestracio

### Jelkulcs
- `→` = kovetkezo lepes (szekvencialis)
- `||` = parhuzamos (egyutt indithato)
- `GATE:` = nem folytatjuk ha FAIL

### B0: Foundations (S20)

```
/dev-step "B0.2 qbpp torles"
  → GATE: pytest PASS, ruff CLEAN, nincs import hiba
/dev-step "B0.1 PII strategia dok"
  → OUTPUT: 01_PLAN/61_GUARDRAIL_PII_STRATEGY.md
/dev-step "B0.4 architektura dok"
  → OUTPUT: 01_PLAN/62_DEPLOYMENT_ARCHITECTURE.md
/dev-step "B0.6 service-hardening command"
  → OUTPUT: .claude/commands/service-hardening.md
/dev-step "B0.6 prompt-tuning command"
  → OUTPUT: .claude/commands/prompt-tuning.md
/dev-step "B0.5 prompt API endpoint"
  → OUTPUT: src/aiflow/api/v1/prompts.py (invalidate + reload-all)
  → GATE: curl test → 200 OK
/dev-step "B0.7 OpenAPI export"
  → OUTPUT: scripts/export_openapi.py + docs/api/
/lint-check → /regression → /update-plan
COMMAND FEEDBACK → command_feedback.md
```

### B1: LLM Guardrail Promptok (S21-S22)

```
B1.1 (S21):
  /new-prompt "hallucination_evaluator" → YAML + 5 Promptfoo
  /new-prompt "content_safety_classifier" → YAML + 5 Promptfoo
  /new-prompt "scope_classifier" → YAML + 5 Promptfoo
  /new-prompt "freetext_pii_detector" → YAML + 5 Promptfoo
  /dev-step "llm_guards.py implementacio"
    → OUTPUT: src/aiflow/guardrails/llm_guards.py
  /quality-check → GATE: 20+ Promptfoo, 95%+ PASS

B1.2 (S22):
  /dev-step "guardrails.yaml per skill" (x5)
    → OUTPUT: skills/*/guardrails.yaml
  /quality-check → GATE: golden dataset PASS
  /regression → /update-plan
  COMMAND FEEDBACK
```

### B2: Service Unit Tesztek (S23-S24)

```
B2.1 (S23):
  /new-test (x13 service) → 65 teszt
  /regression → GATE: 65/65 PASS, coverage >= 70%

B2.2 (S24):
  /new-test (x12 service) → 65 teszt
  /regression → GATE: 130/130 PASS, coverage >= 70%
  /update-plan
  COMMAND FEEDBACK
```

### B3: Invoice Finder (S25-S26)

```
B3.1 (S25):
  /new-prompt (x3) → email_scanner, classifier, field_extractor
  /new-pipeline "invoice_finder_v1"
  /dev-step (x3) → email_search, doc_acquire, invoice_classify adapter
  /quality-check → GATE: 95%+ Promptfoo

B3.2 (S26):
  /new-prompt (x2) → payment_status, report_generator
  /dev-step (x5) → extract, payment, file_org, report, notify step-ek
  /pipeline-test → GATE: valos email + valos szamla + vegigfut
  /regression → /update-plan
  COMMAND FEEDBACK
```

### B3.5: Confidence Hardening (S27)

```
/dev-step "confidence_router.py" → routing logika
/dev-step "per-field confidence" → sulyozott szamitas
/dev-step "BM25 normalizalas" → [0,1] range fix
/service-test → GATE: 0.95→auto, 0.75→review, 0.40→reject E2E
/quality-check → kalibracios teszt
/update-plan
COMMAND FEEDBACK
```

### B4: Skill Hardening (S28-S29)

```
B4.1 (S28):
  /prompt-tuning "aszf_rag_chat" → 86%→95% (diagnozis→eval→fix)
  /prompt-tuning "email_intent" → 85%→95%
  /service-hardening "aszf_rag_chat" → 10-pontos checklist
  /service-hardening "email_intent" → 10-pontos checklist
  /quality-check → GATE: 2/2 skill 95%+

B4.2 (S29):
  /prompt-tuning "process_docs" || /prompt-tuning "invoice" || /prompt-tuning "cubix"
  /service-hardening (x3)
  /quality-check → GATE: 5/5 skill 95%+
  /regression → /update-plan
  COMMAND FEEDBACK
```

### B5: Diagram + Spec Writer (S30)

```
/new-pipeline "diagram_generator_v1" || /new-pipeline "spec_writer_v1"
/new-prompt (x6) → 3 diagram + 3 spec prompt
/dev-step → adapter integraciok
/pipeline-test → GATE: diagram E2E + spec E2E
/quality-check → 95% diagram, 90% spec
/dev-step → koltseg baseline riport
/update-plan
COMMAND FEEDBACK
```

### B6: Portal Redesign (S31)

```
/dev-step "22 oldal audit" → kategorizalas A/B/C
/ui-journey "Invoice Processing" → Journey 1 dok
/ui-journey "Monitoring & Governance" → Journey 2 dok
/ui-journey "RAG Knowledge Base" → Journey 3 dok
/ui-journey "Generation" → Journey 4 dok
  → OUTPUT: 01_PLAN/63_UI_USER_JOURNEYS.md
/dev-step "navigacio IA redesign"
/validate-plan → konzisztencia
/update-plan
COMMAND FEEDBACK
```

### B7: Verification Page v2 (S32)

```
/ui-design "Verification Page v2" → GATE: Figma design KESZ
/dev-step "Alembic: verification_edits" → migracio
/dev-step "API: verifications CRUD" → endpoint-ok
/ui-page "VerificationPage v2" → GATE: tsc 0 error
/service-test → GATE: upload→extract→verify→save→retrieve E2E
/update-plan
COMMAND FEEDBACK
```

### B8: UI Journey Implementation (S33)

```
/ui-design "Sidebar + Dashboard redesign" → Figma
/ui-page "Sidebar" → navigacio atepites
/ui-page "Dashboard" → 4 journey kartya
/ui-component "Breadcrumb" → uj komponens
Journey 1: /dev-step (x4) → Emails scan, Documents filter, Reports
Journey 2: /dev-step (x4) → Runs retry, Costs trend, alerts
/service-test → GATE: Journey 1+2 E2E PASS, 0 console error
/lint-check → /update-plan
COMMAND FEEDBACK
```

### B9: Docker Deploy (S34)

```
/dev-step "docker-compose.prod.yml" → multi-container setup
/dev-step "Dockerfile + nginx" → build config
/dev-step ".env.example + startup" → config
/pipeline-test → GATE: docker compose up → healthy → Invoice E2E
/service-test → GATE: Playwright UI-bol pipeline trigger
/update-plan
COMMAND FEEDBACK
```

### B10: POST-AUDIT (S35)

```
/regression L3 → GATE: ALL PASS, coverage >= 80%
/quality-check "all" → GATE: 5/5 skill 95%+
/service-hardening (x5) → GATE: 5/5 skill checklist 8+/10
/service-test → Journey 1+2 E2E
/validate-plan → konzisztencia ellenorzes
/dev-step "audit riport" → 01_PLAN/SPRINT_B_AUDIT_REPORT.md
/update-plan
COMMAND FEEDBACK → VEGLEGES feedback osszesites
```

### B11: Release (S36)

```
/dev-step "v1.3.0 version bump"
/regression L3 → vegleges
git tag v1.3.0 → push
/update-plan → Sprint B DONE
```

---

## 6. Akcio Terv — Statusz

### DONE (Session 20 iranyitasi reteg kialakitas)

```
[x] 1.  Command archivalas: 4 db → .claude/commands/archive/
[x] 2.  CLAUDE.md ujrairas: 802 → 84 sor (best practice budget-en belul)
[x] 3.  4 Skill letrehozas: aiflow-ui-pipeline, aiflow-testing, aiflow-pipeline, aiflow-services
[x] 4.  3 Agent letrehozas: security-reviewer, qa-tester, plan-validator
[x] 5.  settings.json: PreToolUse (.env deny, rm -rf deny) + PostToolUse (ruff auto-lint)
[x] 6.  .gitignore: CLAUDE.local.md + settings.local.json
[x] 7.  command_feedback.md letrehozas (.claude/sprint_b_learnings/)
[x] 8.  CLAUDE.md Slash Command szekcio ATIRAS (funkcionalis csoportositas)
[x] 9.  Best practice referencia: 01_PLAN/60_CLAUDE_CODE_BEST_PRACTICES_REFERENCE.md
[x] 10. Gap analysis: 01_PLAN/60_GAP_ANALYSIS_AND_ACTION_PLAN.md
[x] 11. Komplex audit: 8 PASS, 2 PARTIAL, 0 FAIL
```

### TODO (B0 session — command javitasok + tartalmi feladatok)

```
[ ] 12. /dev-step.md UJRAIRAS: v1.3.0 kontextus, egyszerubb
[ ] 13. /update-plan.md JAVITAS: helyes szamok (46/6/29), 58-as terv
[ ] 14. /validate-plan.md JAVITAS: szamok egyeztetes
[ ] 15. /service-test.md JAVITAS: port 8100→8102
[ ] 16. /ui-journey.md JAVITAS: archiv 42_ → 63_UI_USER_JOURNEYS.md
[ ] 17. /new-pipeline.md JAVITAS: archiv 48_ torles
[ ] 18. /new-prompt.md JAVITAS: archiv 42_ torles
[ ] 19. /ui-design.md JAVITAS: port + Figma channel
[ ] 20. /ui-page.md JAVITAS: port 8101→8102
[ ] 21. /service-hardening.md LETREHOZAS (UJ — B0.6)
[ ] 22. /prompt-tuning.md LETREHOZAS (UJ — B0.6)
[ ] 23. 01_PLAN/CLAUDE.md szamok frissites (46 tabla, B0-B11)
--- B0 tartalmi feladatok ---
[ ] 24. B0.2: qbpp torles
[ ] 25. B0.1: PII strategia dok
[ ] 26. B0.4: Architektura dok
[ ] 27. B0.5: Prompt invalidate API endpoint
[ ] 28. B0.7: OpenAPI export
[ ] 29. /update-plan → 58 progress B0 DONE
```
