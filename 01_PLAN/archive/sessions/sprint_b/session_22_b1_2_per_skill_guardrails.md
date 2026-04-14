# AIFlow Sprint B — Session 22 Prompt (B1.2: Per-Skill Guardrails.yaml)

> **Datum:** 2026-04-05
> **Branch:** `feature/v1.3.0-service-excellence` | **HEAD:** `f6670a1`
> **Port:** API 8102, Frontend 5174
> **Elozo session:** S21 — B1.1 DONE (4 LLM guardrail prompt + llm_guards.py + 27 promptfoo 100%)
> **Terv:** `01_PLAN/58_POST_SPRINT_HARDENING_PLAN.md` (B1.2 szekció, sor 854+)

---

## KONTEXTUS

### B1.1 Eredmenyek (S21 — DONE, commit f6670a1)

- 4 prompt YAML (`src/aiflow/guardrails/prompts/`):
  - `hallucination_evaluator.yaml` — grounding scoring (anti-injection vedelemmel)
  - `content_safety_classifier.yaml` — SAFE/UNSAFE/REVIEW_NEEDED
  - `scope_classifier.yaml` — 3-tier scope dontes kontextussal
  - `freetext_pii_detector.yaml` — regex-mentes PII detektalas (HU+EN)
- `llm_guards.py` — 4 async GuardrailBase osztaly
- `config.py` bovites: `LLMFallbackConfig` (per-guard toggles, confidence_threshold)
- `__init__.py` frissitve az uj exportokkal
- 22 unit teszt (test_llm_guards.py) — ALL PASS
- 27 promptfoo teszt (valos gpt-4o-mini) — 100% PASS
- `golden_llm_guardrails.yaml` — 24 golden dataset entry
- B0 hianyzó feladatok potolva: command_feedback, command szamok, regression kontextus

### Infrastruktura (v1.3.0)

- 26 service | 165 API endpoint (25 router) | 46 DB tabla | 29 migracio
- 18 adapter | 6 template | 5 skill | 22 UI oldal
- 1164 unit test | 98 guardrail teszt (76 regi + 22 uj) | 97 security teszt
- 27 promptfoo teszt (4 guardrail prompt)
- Guardrail framework: A5 rule-based + B1.1 LLM fallback

---

## B1.2 FELADAT: Per-Skill Guardrails.yaml (5 skill)

> **Gate:** 5 guardrails.yaml KESZ + 25 guardrail teszt PASS + GuardrailConfig bovites (PIIMaskingMode)
> **Referencia:** `01_PLAN/61_GUARDRAIL_PII_STRATEGY.md` — PII config skill-specifikus!
> **Eszkozok:** `/dev-step` (x5 — minden skill-hez), `/regression`

### KRITIKUS: PII Config Skill-Specifikus!

| Skill | pii_masking | allowed_pii | Indoklas |
|-------|-------------|-------------|----------|
| aszf_rag_chat | `on` (full) | `[]` | Chat — SEMMI PII nem szukseges |
| email_intent_processor | `partial` | `[email, name, company]` | Routing-hoz kell felado/cimzett |
| invoice_processor | `off` | `[all]` | Szamla mezok = PII, de KELL |
| process_documentation | `on` | `[]` | Dokumentum generalas — nincs PII szukseg |
| cubix_course_capture | `on` | `[]` | Video transcript — nincs PII szukseg |

### 5 guardrails.yaml Fajl

#### 1. skills/aszf_rag_chat/guardrails.yaml

```yaml
input:
  pii_masking: "on"
  allowed_pii: []
  max_length: 2000
  check_injection: true
output:
  require_citation: true
  hallucination_threshold: 0.7
  check_pii: true
  check_safety: true
scope:
  allowed_topics: ["jog", "biztositas", "aszf", "szolgaltatas", "law", "insurance", "contract"]
  blocked_topics: ["politika", "orvosi tanacs", "befektetesi tanacs"]
  dangerous_patterns: ["hogyan torzek be", "hogyan hackeljem", "how\\s+to\\s+hack"]
llm_fallback:
  enabled: true
  hallucination_evaluator: true
  content_safety_classifier: true
  scope_classifier: true
  pii_detector: true
  confidence_threshold: 0.7
```

#### 2. skills/email_intent_processor/guardrails.yaml

```yaml
input:
  pii_masking: "partial"
  allowed_pii: ["email", "phone", "hu_taj"]
  max_length: 3000
  check_injection: true
output:
  check_pii: true
  check_safety: true
  hallucination_threshold: 0.5
scope:
  allowed_topics: ["email", "intent", "complaint", "inquiry", "order", "support", "claim"]
  blocked_topics: []
  dangerous_patterns: ["how\\s+to\\s+hack", "delete\\s+all"]
llm_fallback:
  enabled: true
  content_safety_classifier: true
  pii_detector: true
  confidence_threshold: 0.7
```

#### 3. skills/invoice_processor/guardrails.yaml

```yaml
input:
  pii_masking: "off"
  pii_logging: true
  max_length: 5000
  check_injection: true
output:
  validate_amounts: true
  validate_dates: true
  check_pii: false
  check_safety: true
scope:
  allowed_topics: ["szamla", "invoice", "faktura", "document", "amount", "date", "supplier"]
  blocked_topics: []
  dangerous_patterns: ["drop\\s+table", "delete\\s+from"]
llm_fallback:
  enabled: false
```

#### 4. skills/process_documentation/guardrails.yaml

```yaml
input:
  pii_masking: "on"
  allowed_pii: []
  max_length: 10000
  check_injection: true
output:
  check_pii: true
  check_safety: true
  mermaid_syntax_check: true
  max_diagram_nodes: 50
scope:
  allowed_topics: ["process", "workflow", "bpmn", "diagram", "documentation", "flowchart"]
  blocked_topics: ["politika", "orvosi"]
  dangerous_patterns: ["how\\s+to\\s+hack"]
llm_fallback:
  enabled: true
  content_safety_classifier: true
  confidence_threshold: 0.8
```

#### 5. skills/cubix_course_capture/guardrails.yaml

```yaml
input:
  pii_masking: "on"
  allowed_pii: []
  max_length: 50000
  max_audio_length: 7200
  check_injection: false
output:
  check_pii: true
  check_safety: false
  format_check: true
scope:
  allowed_topics: ["course", "video", "transcript", "lecture", "training", "education"]
  blocked_topics: []
  dangerous_patterns: []
llm_fallback:
  enabled: false
```

### GuardrailConfig Bovites — PIIMaskingMode

**Fajl:** `src/aiflow/guardrails/config.py`

```python
class PIIMaskingMode(str, Enum):
    ON = "on"           # Teljes masking — semmi PII nem jut at
    PARTIAL = "partial" # Csak az allowed_pii tipusok jutnak at
    OFF = "off"         # Nincs masking — minden PII atlathato (pl. szamla)
```

Bovitendo mezok az `InputConfig`-ban:
- `pii_masking_mode: PIIMaskingMode = PIIMaskingMode.ON`
- `allowed_pii_types: list[str] = []`
- `pii_logging: bool = False`

Bovitendo a `load_guardrail_config` — olvassa a `pii_masking` stringet es konvertalja `PIIMaskingMode`-ra.

### InputGuard Modositas

**Fajl:** `src/aiflow/guardrails/input_guard.py`

A `_detect_pii` es `_mask_pii` metodusoknak figyelembe kell venniuk:
- `OFF` → skip PII check teljesen
- `PARTIAL` → detektal mindent, de csak a NEM-allowed tipusokat maskolja
- `ON` → maskolja az osszes PII-t (jelenlegi viselkedes)

### Tesztek

#### Unit tesztek (tests/unit/guardrails/test_pii_config.py) — 15+ teszt

- `test_on_mode_masks_all_pii()` — ON mod: minden PII maszkolva
- `test_off_mode_passes_all_pii()` — OFF mod: semmi sem maszkolt
- `test_partial_mode_allows_specified()` — PARTIAL: email atjut, adoszam nem
- `test_partial_mode_blocks_unspecified()` — PARTIAL: nem-allowed PII maszkolt
- `test_pii_logging_flag()` — pii_logging=true eseten logolas tortenik
- Per-skill: 5 teszt (1/skill) — `load_guardrail_config(skill_path)` → helyes PIIMaskingMode

#### Golden dataset bovites

`tests/guardrails/golden_guardrails.yaml` — per-skill test data:
- Minden skill-hez: 1 safe input, 1 dangerous input, 1 injection attempt
- Osszesen: 5 skill × 3 case = 15 entry
- Plusz: 5 PII-specifikus case (on/off/partial modok)

---

## VEGREHAJTAS SORRENDJE

A B1.2-t `/dev-step` command-okkal vegezzuk — ez az elso session ahol TENYLEGESEN hasznaljuk!

```
--- LEPES 1: GuardrailConfig bovites ---
/dev-step "B1.2.1 — PIIMaskingMode enum + InputConfig bovites"
  - config.py: PIIMaskingMode enum, InputConfig uj mezok
  - input_guard.py: pii_masking_mode logikaval bovites
  - 5 unit teszt (on/off/partial)

--- LEPES 2: 5 guardrails.yaml letrehozas ---
/dev-step "B1.2.2 — aszf_rag_chat guardrails.yaml"
/dev-step "B1.2.3 — email_intent_processor guardrails.yaml"
/dev-step "B1.2.4 — invoice_processor guardrails.yaml"
/dev-step "B1.2.5 — process_documentation + cubix_course_capture guardrails.yaml"

  Minden /dev-step-nel:
  1. guardrails.yaml irasa a skills/{name}/ konyvtarba
  2. load_guardrail_config teszt: betoltodik-e, helyes-e a PIIMaskingMode
  3. 1 golden test case per skill

--- LEPES 3: Golden dataset + tesztek ---
/dev-step "B1.2.6 — Golden dataset + per-skill guardrail tesztek"
  - tests/guardrails/golden_guardrails.yaml bovites (per-skill data)
  - tests/unit/guardrails/test_pii_config.py (15+ teszt)

--- SESSION LEZARAS ---
/lint-check → 0 error
/regression → ALL PASS (98+ guardrail teszt)
/update-plan → 58 progress B1.2 DONE
COMMAND FEEDBACK → command_feedback.md (S22 — /dev-step feedback!)
```

---

## KORNYEZET ELLENORZES

```bash
git branch --show-current                              # → feature/v1.3.0-service-excellence
git log --oneline -1                                   # → f6670a1 feat(sprint-b): B1.1...
python -m pytest tests/unit/guardrails/ -q 2>&1 | tail -1  # → 98 passed
ruff check src/ tests/ 2>&1 | tail -1                 # → All checks passed!
ls src/aiflow/guardrails/prompts/                      # → 4 prompt YAML
ls src/aiflow/guardrails/llm_guards.py                 # → letezik (B1.1)
ls skills/*/guardrails.yaml 2>/dev/null                # → NINCS MEG (B1.2 feladat!)
cat 01_PLAN/61_GUARDRAIL_PII_STRATEGY.md | head -5     # → PII strategia letezik
```

---

## S21 TANULSAGAI (alkalmazando S22-ben!)

1. **Promptfoo teszt config NEM lehet egy fajlban** ha tobbfele prompt van — prompt-onkent kulon YAML!
2. **PromptExample schema `input`/`output`** mezoket var, NEM `user`/`assistant` — figyeld a Pydantic validaciot!
3. **Anti-injection vedelem** a hallucination evaluator prompt-ban SZUKSEGES — a gpt-4o-mini hajlamos kovetni az injected response-ban levo utasitasokat
4. **`_call_llm` patch** — unit tesztekben `_call_llm`-et kell patchelni, NEM `litellm`-et (local import)
5. **PostToolUse ruff hook** mukodik — Write/Edit utan automatikus format
6. **command_feedback.md** — S22 vegen KOTELEZO kitolteni, kulonosen a `/dev-step` tapasztalatokkal!

---

## SPRINT B UTEMTERV

```
S19: B0   — DONE (4b09aad) — 5-layer arch + qbpp + prompt API + OpenAPI
S20: B1.1 — DONE (f6670a1) — 4 LLM guardrail prompt + llm_guards.py + 27 promptfoo
S21: B1.2 ← JELEN SESSION — per-skill guardrails.yaml (5 skill) + PIIMaskingMode
S22: B2.1 — Core infra service tesztek (65 test, Tier 1)
S23: B2.2 — v1.2.0 service tesztek (65 test, Tier 2)
S24: B3.1 — Invoice Finder: pipeline design + email + doc acquisition
S25: B3.2 — Invoice Finder: extract + report + notification (valos adat!)
S26: B3.5 — Konfidencia scoring hardening + confidence→review routing
S27: B4.1 — Skill hardening: aszf_rag + email_intent
S28: B4.2 — Skill hardening: process_docs + invoice + cubix + diagram
S29: B5   — Spec writer + diagram pipeline + koltseg baseline
S30: B6   — UI Journey audit + 4 journey tervezes + navigacio redesign
S31: B7   — Verification Page v2 (bounding box, diff, per-field confidence szin)
S32: B8   — UI Journey implementacio (top 3 journey + dark mode)
S33: B9   — Docker containerization + UI pipeline trigger + deploy teszt
S34: B10  — POST-AUDIT + javitasok
S35: B11  — v1.3.0 tag + merge
```

---

## FONTOS SZABALYOK (emlekeztetok)

- **`/dev-step` KOTELEZO** — ez az elso session ahol tenylegesen hasznaljuk. Feedback-et rogziteni!
- **PII per-skill:** `61_GUARDRAIL_PII_STRATEGY.md` az iranyadó — NE terd el a PII mod-okatol
- **GuardrailConfig backward compat:** a meglevo `InputConfig.pii_masking: bool` mezot NE torold, bovitsd `PIIMaskingMode`-dal
- **load_guardrail_config:** olvassa a `pii_masking: "on"/"partial"/"off"` stringet ES a legacy `pii_masking: true/false`-t is
- **Teszt pattern:** toltsd be a guardrails.yaml-t `load_guardrail_config()`-gal es ellenorizd a helyes config ertekeket
- **Feedback:** Session vegen command_feedback.md KOTELEZO — kulonosen a `/dev-step` tapasztalatok!

---

## B1 GATE CHECKLIST (B1.2 vegen teljesitendo)

```
[ ] 4 LLM guardrail prompt YAML (B1.1 — DONE)
[ ] 20+ Promptfoo teszt PASS (B1.1 — 27/27, DONE)
[ ] llm_guards.py 4 osztaly (B1.1 — DONE)
[ ] 5 guardrails.yaml (B1.2 — jelen session)
[ ] PIIMaskingMode enum + InputGuard bovites (B1.2)
[ ] 25+ guardrail teszt PASS (B1.2)
[ ] 10+ unit teszt (B1.2)
[ ] Golden dataset per-skill (B1.2)
[ ] /dev-step tenylegesen hasznalva + feedback (B1.2)
```
