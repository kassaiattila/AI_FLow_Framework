# AIFlow Sprint B — Session 21 Prompt (B1.1: LLM Guardrail Promptok)

> **Datum:** 2026-04-05
> **Branch:** `feature/v1.3.0-service-excellence` | **HEAD:** `4b09aad`
> **Port:** API 8102, Frontend 5174
> **Elozo session:** S20 — B0 DONE (5-layer architecture + qbpp + PII dok + prompt API + OpenAPI)
> **Terv:** `01_PLAN/58_POST_SPRINT_HARDENING_PLAN.md` (B1.1 szekció, sor 819+)

---

## KONTEXTUS

### B0 Eredmenyek (S20 — DONE, commit 4b09aad)

- CLAUDE.md: 802→83 sor (best practice budget-en belul)
- 4 skill: aiflow-ui-pipeline, aiflow-testing, aiflow-pipeline, aiflow-services
- 3 agent: security-reviewer, qa-tester, plan-validator
- settings.json: PostToolUse ruff auto-lint + PreToolUse .env/.rm-rf deny
- 20 command (4 archiv, 2 uj: /service-hardening, /prompt-tuning)
- qbpp TOROLVE (6→5 skill), PII strategia dok, architektura dok
- Prompt API: 3 uj endpoint (invalidate, reload-all, cache-status) → 165 endpoint
- OpenAPI export: 165 path dokumentalva

### Infrastruktura (v1.3.0)

- 26 service | 165 API endpoint (25 router) | 46 DB tabla | 29 migracio
- 18 adapter | 6 template | 5 skill | 22 UI oldal
- 1164 unit test | 76 guardrail teszt | 97 security teszt
- Guardrail framework KESZ (A5): InputGuard, OutputGuard, ScopeGuard

---

## B0 HIANYZÓ FELADATOK (ebben a session-ben potolando!)

A B0-ban nem keszult el minden. Az alabbi feladatok **ELSO PRIORITAS**:

### H1. /dev-step TESZTELES: tényleges használat

Az elozo session-ben inline csinaltuk a feladatokat `/dev-step` hivatkozas NELKUL.
**Ebben a session-ben tenylegesen hivjuk meg a `/dev-step` command-ot** a B1.1 feladatoknal.
Cél: validalni hogy a command mukodik-e, es a feedback-et rogziteni.

### H2. command_feedback.md kitoltese (S20)

Az elozo session command feedback-je NEM lett kitoltve. Potolando:

```markdown
## Session S20 Feedback

### /dev-step — S20, B0
Eredmeny: NEM HASZNALVA (inline vegezve)
Tanulsag: Kovetkezo session-ben TENYLEGESEN kell meghivni

### PostToolUse hook (ruff) — S20
Eredmeny: PASS — automatikusan lefutott prompts.py irasanal
Tanulsag: Determinisztikus, megbizhato

### PreToolUse hook (.env deny) — S20
Eredmeny: NEM TESZTELVE (nem probaltunk .env-t irni)
Tanulsag: Tesztelni kell
```

### H3. /update-plan.md es /validate-plan.md szamok frissitese

Ezek a command-ok meg a REGI szamokat hasznaljak (36 tabla, 13 migracio).
A `59_COMMAND_WORKFLOW_AUDIT.md` Section 6 TODO lista #13-14 pont.

### H4. /regression.md frissitese (v1.3.0 kontextus)

A regression command nincs frissitve v1.3.0 branch-re es 1164 teszt szamra.

---

## B1.1 FELADAT: LLM Guardrail Promptok (4 db)

> **Gate:** 4 LLM guardrail prompt KESZ + 20+ Promptfoo test case PASS (95%+)
> **Architektura:** Rule-based A5 (gyors, $0) → ha bizonytalan → LLM (preciz, $$)
> **Eszkozok:** `/new-prompt` (x4), `/dev-step`, `/quality-check`

### 4 Prompt YAML

#### 1. hallucination_evaluator.yaml
- **Cel:** A5 SequenceMatcher csereje. Grounding scoring LLM-mel.
- **Input:** `{response, sources[]}` → **Output:** `{grounding_score, ungrounded_claims[]}`
- **Modell:** gpt-4o-mini
- **Promptfoo:** 5+ test case

#### 2. content_safety_classifier.yaml
- **Cel:** A5 4 regex csereje. SAFE / UNSAFE / REVIEW_NEEDED osztalyozas.
- **Input:** `{text, context}` → **Output:** `{verdict, category, confidence}`
- **Modell:** gpt-4o-mini
- **Promptfoo:** 5+ test case

#### 3. scope_classifier.yaml
- **Cel:** A5 keyword matching csereje. 3-tier scope dontes kontextussal.
- **Input:** `{query, allowed_topics[], skill_description}`
- **Output:** `{verdict: in_scope|out_of_scope|dangerous, reason, confidence}`
- **Modell:** gpt-4o-mini
- **Promptfoo:** 5+ test case

#### 4. freetext_pii_detector.yaml
- **Cel:** UJ — regex NEM tudja: "a szomszédom Kiss János az OTP-nél dolgozik"
- **Input:** `{text}` → **Output:** `{pii_items: [{type, text, start, end}]}`
- **Modell:** gpt-4o-mini
- **Promptfoo:** 5+ test case (magyar + angol + vegyes)

### llm_guards.py Implementacio

**Fajl:** `src/aiflow/guardrails/llm_guards.py`

4 osztaly:
- `LLMHallucinationEvaluator(GuardrailBase)` — hallucination_evaluator prompt hivas
- `LLMContentSafetyClassifier(GuardrailBase)` — content_safety_classifier prompt hivas
- `LLMScopeClassifier(GuardrailBase)` — scope_classifier prompt hivas
- `LLMPIIDetector(GuardrailBase)` — freetext_pii_detector prompt hivas

**Config bovites:** `config.py` → `llm_fallback` per guard, `confidence_threshold`

### Tesztek

- 10+ unit test (`tests/unit/guardrails/test_llm_guards.py`)
- 20+ Promptfoo test case (4 prompt × 5+ case)
- Golden dataset: `tests/guardrails/golden_llm_guardrails.yaml`

---

## VEGREHAJTAS SORRENDJE

```
--- HIANYZÓ B0 FELADATOK (elso!) ---
H2. command_feedback.md kitoltese (S20 feedback)
H3. /update-plan.md szamok javitasa (46/6/29/5 skill/165 endpoint)
H4. /validate-plan.md szamok javitasa
H4b. /regression.md v1.3.0 kontextus

--- B1.1 FELADATOK (command-vezerelt!) ---
/new-prompt "hallucination_evaluator"
/new-prompt "content_safety_classifier"
/new-prompt "scope_classifier"
/new-prompt "freetext_pii_detector"
/dev-step "llm_guards.py implementacio"
/quality-check → GATE: 20+ Promptfoo, 95%+ PASS

--- SESSION LEZARAS ---
/lint-check → 0 error
/regression → ALL PASS
/update-plan → 58 progress B1.1 DONE
COMMAND FEEDBACK → command_feedback.md (S21)
```

---

## KORNYEZET ELLENORZES

```bash
git branch --show-current                              # → feature/v1.3.0-service-excellence
git log --oneline -1                                   # → 4b09aad feat(sprint-b): B0...
python -m pytest tests/unit/ -q --co 2>&1 | tail -1   # → 1164 tests
ruff check src/ tests/ 2>&1 | tail -1                 # → All checks passed!
ls src/aiflow/guardrails/                              # → base, config, input/output/scope_guard
ls src/aiflow/api/v1/prompts.py                        # → letezik (B0.5)
```

---

## SPRINT B UTEMTERV

```
S20: B0   — DONE (4b09aad) — 5-layer arch + qbpp + prompt API + OpenAPI
S21: B1.1 ← JELEN SESSION — /new-prompt (x4) LLM guardrail promptok
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

## FONTOS SZABALYOK (emlekeztetok)

- **Valos LLM hivasok:** Promptfoo teszteknel VALOS gpt-4o-mini, NEM mock
- **Prompt YAML:** `skills/*/prompts/` → SOHA ne hardcode-olj prompt-ot Python kodban
- **GuardrailBase ABC:** Minden uj guard orokol, `check_input()` es `check_output()` metodusok
- **Lanc:** Rule-based (InputGuard/OutputGuard, gyors, $0) → LLM (llm_guards, preciz, $$)
- **PII konfiguracio:** Per-skill — lasd `01_PLAN/61_GUARDRAIL_PII_STRATEGY.md`
- **Feedback:** Session vegen command_feedback.md KOTELEZO kitolteni!

---

## ELOZO SESSION TANULSAGAI (S20)

1. **5-layer architektura MUKODIK:** skills auto-trigger, PostToolUse ruff hook, CLAUDE.md budget-en belul
2. **Command-okat NEM hivtuk meg tenylegesen** — inline vegeztuk a munkát. S21-ben javitando!
3. **PostToolUse hook (ruff) igazoltan mukodik** — `prompts.py` irasanal automatikusan lefutott
4. **command_feedback.md NEM lett kitoltve** — S21 elejen potolando
5. **165 endpoint** (3 uj prompts endpoint) — frissiteni az osszes szamot
