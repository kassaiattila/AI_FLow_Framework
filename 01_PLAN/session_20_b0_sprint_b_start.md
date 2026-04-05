# AIFlow Sprint B — Session 20 Prompt

> **Datum:** 2026-04-05
> **Branch:** `feature/v1.3.0-service-excellence` | **HEAD:** `f6407be` | **Tag:** v1.2.2
> **Port:** API 8102, Frontend 5174
> **Terv:** `01_PLAN/58_POST_SPRINT_HARDENING_PLAN.md` (Sprint B szekció, sor 510+)
> **Audit:** `01_PLAN/59_COMMAND_WORKFLOW_AUDIT.md` (command + workflow restructuring)

---

## CEL: B0 Foundations — iranyitasi reteg kialakitasa + B0 tartalmi feladatok

---

## ELVEGZETT (iranyitasi reteg — az elozo session-ben kialakitva)

| # | Feladat | Allapot |
|---|---------|---------|
| 1 | CLAUDE.md ujrairas: 802 → 84 sor | DONE |
| 2 | 4 Skill letrehozas (aiflow-ui-pipeline, testing, pipeline, services) | DONE |
| 3 | 3 Agent letrehozas (security-reviewer, qa-tester, plan-validator) | DONE |
| 4 | settings.json hooks (ruff PostToolUse, .env deny, rm -rf deny) | DONE |
| 5 | 4 Command archivalas (start-phase, phase-status, new-skill, new-module) | DONE |
| 6 | command_feedback.md + .gitignore | DONE |
| 7 | Best practice referencia (60_CLAUDE_CODE_BEST_PRACTICES_REFERENCE.md) | DONE |
| 8 | Gap analysis (60_GAP_ANALYSIS_AND_ACTION_PLAN.md) | DONE |
| 9 | Komplex audit: 8 PASS, 2 PARTIAL (hooks + permissions), 0 FAIL | DONE |

---

## TODO: 10 Command Tartalmi Javitas

A `59_COMMAND_WORKFLOW_AUDIT.md` Section 2 alapjan — KRITIKUS hibak a meglevo command-okban:

### Prioritas 1: Leggyakrabban hasznalt command-ok

| Command | Hiba | Javitas |
|---------|------|---------|
| `/dev-step` | 161 sor, elavult branchek (v1.2.0 tier), rossz terv ref (57_) | v1.3.0 kontextus, 5 fazis: CHECK→CODE→TEST→LINT→COMMIT |
| `/regression` | Nincs v1.3.0 branch hivatkozas | Branch + 1164 unit test szam |
| `/update-plan` | Rossz szamok (36 tabla, 13 view, 13 migracio) | 46 tabla, 6 view, 29 migracio, 5 skill |
| `/validate-plan` | Szamok nem egyeznek update-plan-nel | Egyeztetes (46/6/29) |

### Prioritas 2: Port javitasok

| Command | Jelenlegi port | Helyes |
|---------|---------------|--------|
| `/service-test` | 8100 | **8102** |
| `/ui-page` | 8101 | **8102** |
| `/ui-design` | vegyes | **8102** + Figma channel ellenorzes |

### Prioritas 3: Archiv hivatkozas torles

| Command | Archiv hivatkozas | Javitas |
|---------|-------------------|---------|
| `/ui-journey` | 42_SERVICE_GENERALIZATION_PLAN.md | → `01_PLAN/63_UI_USER_JOURNEYS.md` |
| `/new-pipeline` | 48_ORCHESTRABLE_SERVICE_ARCHITECTURE.md | → kozvetlen adapter registry |
| `/new-prompt` | 42_SERVICE_GENERALIZATION_PLAN.md | → torles |

---

## TODO: 2 Uj Command Letrehozas

### `/service-hardening` (B0.6)

10 pontos production checklist audit per skill/service:
1. UNIT TESZT >= 5, >= 70% coverage
2. INTEGRACIO >= 1 valos DB
3. API TESZT minden endpoint curl, source=backend
4. PROMPT TESZT promptfoo >= 95%
5. ERROR HANDLING AIFlowError, is_transient
6. LOGGING structlog
7. DOKUMENTACIO docstring
8. UI oldal mukodik, source badge, 0 console error
9. INPUT GUARDRAIL injection + PII
10. OUTPUT GUARDRAIL hallucination, scope, PII leak

### `/prompt-tuning` (B0.6)

6 lepesu prompt lifecycle:
1. DIAGNOZIS (Langfuse trace → gyenge pontok)
2. FEJLESZTES (prompt YAML ujrairas)
3. TESZTELES (Promptfoo eval → 95%+)
4. VALIDACIO (human review)
5. ELESITES (Langfuse label swap)
6. MONITORING (elotte vs utana)

---

## TODO: 01_PLAN/CLAUDE.md Javitas

Jelenlegi hibak:
- "45 DB tables" → **46**
- "B0-B9" → **B0-B11**
- Skill szam: qbpp meg benne van (6) → **5 (B0 utan)**

---

## TODO: B0 Tartalmi Feladatok (command-vezerelt!)

### B0 Gate:
> PII strategia dok + qbpp torolve + architektura dok + 2 uj command + OpenAPI + prompt API

### Vegrehajtas:

```
/dev-step "B0.2 qbpp_test_automation torles"
  → rm -rf skills/qbpp_test_automation/
  → CLAUDE.md, FEATURES.md: 6→5 skill
  → GATE: pytest PASS, ruff CLEAN

/dev-step "B0.1 PII strategia dok"
  → OUTPUT: 01_PLAN/61_GUARDRAIL_PII_STRATEGY.md

/dev-step "B0.4 architektura dok"
  → OUTPUT: 01_PLAN/62_DEPLOYMENT_ARCHITECTURE.md

/dev-step "B0.5 prompt invalidate API"
  → OUTPUT: src/aiflow/api/v1/prompts.py
  → GATE: curl → 200 OK

/dev-step "B0.7 OpenAPI export"
  → OUTPUT: scripts/export_openapi.py + docs/api/openapi.json

/lint-check → 0 error
/regression → ALL PASS
/update-plan → 58 progress B0 DONE + CLAUDE.md szamok (5 skill!)
COMMAND FEEDBACK → command_feedback.md
```

---

## KORNYEZET ELLENORZES

```bash
git branch --show-current                              # → feature/v1.3.0-service-excellence
python -m pytest tests/unit/ -q --co 2>&1 | tail -1   # → 1164 tests
ruff check src/ tests/ 2>&1 | tail -1                 # → All checks passed!
ls skills/qbpp_test_automation/                        # → letezik (B0.2 torli)
```

---

## SPRINT B UTEMTERV (teljes — command-vezerelt)

```
S20: B0   ← JELEN SESSION (iranyitasi reteg DONE + foundations TODO)
S21: B1.1 — /new-prompt (x4) LLM guardrail promptok
S22: B1.2 — /dev-step (x5) per-skill guardrails.yaml
S23: B2.1 — /new-test (x13) core service tesztek
S24: B2.2 — /new-test (x12) v1.2.0 service tesztek
S25: B3.1 — /new-pipeline + /new-prompt (x3) Invoice Finder
S26: B3.2 — /pipeline-test Invoice Finder E2E
S27: B3.5 — /dev-step (x3) confidence routing
S28: B4.1 — /prompt-tuning (x2) + /service-hardening (x2)
S29: B4.2 — /prompt-tuning (x3) + /service-hardening (x3)
S30: B5   — /new-pipeline (x2) diagram + spec writer
S31: B6   — /ui-journey (x4) portal redesign
S32: B7   — /ui-design + /ui-page Verification v2
S33: B8   — /ui-page (x6) Journey implementacio
S34: B9   — /dev-step Docker deploy
S35: B10  — /regression + /service-hardening (x5) POST-AUDIT
S36: B11  — v1.3.0 tag + merge
```

---

## ELOZO SESSION TANULSAGAI

1. **Branch hiba:** v1.3.0 main-rol leagaztatva → ujra leagaztatas v1.2.2-infrastructure-rol
2. **CLAUDE.md tulmeretezett:** 802 sor = 5x budget → ujrairas 84 sorra, domain tudas 4 skill-be
3. **Hooks hianyoztak:** settings.json nem letezett → letrehozva (ruff PostToolUse, .env deny)
4. **Command-ok nem hasznalva:** mostantol CSAK command-okon keresztul dolgozunk
5. **Nincs feedback:** command_feedback.md letrehozva, session vegen kitoltjuk
6. **LLM self-report confidence megbizhatatlan** — B3.5-ben javitjuk
