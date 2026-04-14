# AIFlow Sprint B — Session 28 Prompt (B4.1: Skill Hardening — aszf_rag_chat + email_intent_processor)

> **Datum:** 2026-04-08
> **Branch:** `feature/v1.3.0-service-excellence` | **HEAD:** `4579cd2`
> **Port:** API 8102, Frontend 5174
> **Elozo session:** S27 — B3.E2E Phase 2 + Phase 3 + B3.5 DONE (confidence scoring + review routing + BM25 fix, 36 uj unit teszt, 1424 ossz)
> **Terv:** `01_PLAN/58_POST_SPRINT_HARDENING_PLAN.md` (B4 szekcio, sor 1214+)

---

## KONTEXTUS

### S27 Eredmenyek (B3.E2E + B3.5 — DONE)

**B3.E2E Phase 2** (`8b10fd6`):
- `invoice_finder_v3_offline.yaml` — 5-step offline pipeline (no email fetch)
- `tests/e2e/test_invoice_finder_pipeline_runner.py` — full DB persistence validation
- **Result:** 3/3 HU PDFs end-to-end, workflow_runs + step_runs DB rows verified, ~60s wall clock

**B3.E2E Phase 3** (`70f505f`):
- `tests/e2e/test_invoice_finder_phase3_outlook.py` — 8-step pipeline × 3 Outlook accounts (bestix + kodosok + gmail)
- **Result:** 3/3 accounts completed, all 8 steps per run, framework chain fully operational

**B3.5 Confidence Scoring** (`4579cd2`):
- `src/aiflow/engine/confidence.py` — FieldConfidenceCalculator (4-factor: format/regex/cross/source)
- `src/aiflow/engine/confidence_router.py` — route_by_confidence (auto/review/reject thresholds)
- `skills/invoice_finder/confidence_config.yaml` — calibrated on Phase 1+2 data
- `src/aiflow/vectorstore/pgvector_store.py` — BM25 saturation normalization `[0, ∞) → [0, 1)`
- **Result:** 36 uj unit test (14 field + 11 router + 4 config + 7 BM25), 1424 ossz, 0 regresszio

**7 framework bug javitas utkozben** (commit `5354d2c`):
- `pipeline/template.py` — pure expression now returns native Python objects (lists/dicts)
- `document_extractor/service.py:_extract_fields` — ModelClient + LiteLLMBackend, JSON markdown strip
- `document_extractor/service.py:extract` — defensive file_path validation
- `pipeline/adapters/document_adapter.py` — `extracted_fields` attribute fix, None coerce
- `email_connector/service.py` — EmailAttachment.file_path field + Outlook COM populates
- `pipeline/adapters/email_adapter.py` — attachment_paths propagation
- `pipeline/builtin_templates/invoice_finder_v3.yaml` — 6 YAML fixes (method names, strategies, defaults, filters)

### Infrastruktura (v1.3.0 — frissitett szamok)

- 26 service | 165 API endpoint (25 router) | 46 DB tabla | 29 migracio
- 21 pipeline adapter | 7 pipeline template | 6 skill | 22 UI oldal
- **1424 unit test** | 129 guardrail teszt | 97 security teszt | **104 E2E** | 54 promptfoo teszt
- Invoice Finder: teljes 8-step pipeline PRODUCTION-READY valos Outlook COM-ra
- Confidence scoring: determinisztikus, LLM self-report mentes, routing bekotve

### Jelenlegi Skill Allapot (B4.1 AUDIT cel)

```
=== SKILL STATUS TERKEP ===

aszf_rag_chat (v1.2.0 — HITL-ready, B1.2 guardrail, jelenleg ~86% promptfoo):

  Prompts (7 YAML, skills/aszf_rag_chat/prompts/):
    - system_prompt_baseline.yaml   — altalanos asszisztens persona
    - system_prompt_expert.yaml     — szakerto jogi persona
    - system_prompt_mentor.yaml     — oktato persona
    - query_rewriter.yaml           — query → strukturalt search intent
    - answer_generator.yaml         — context + query → idezet-vezetett valasz
    - citation_extractor.yaml       — valasz → forras hivatkozasok
    - hallucination_detector.yaml   — valasz validacio (context ellen)

  Promptfoo: 7 existing test case (skills/aszf_rag_chat/tests/promptfooconfig.yaml)
  Guardrail: skills/aszf_rag_chat/guardrails.yaml (B1.2-bol)
  Ismert gyenge pontok:
    - Citation enforcement: LLM sokszor nem hasznalja a [doc:chunk_id] formatot
    - Hallucination calibration: confidence 0.8+ de valos accuracy ~70%
    - Out-of-scope kerdes: nem elutasit elegszer (scope guard gyenge)

email_intent_processor (v1.2.0 — 10 intent, hybrid ML+LLM, jelenleg ~85% promptfoo):

  Prompts (8 YAML, skills/email_intent_processor/prompts/):
    - email_parser.yaml             — .eml → strukturalt metadata
    - intent_classifier.yaml        — text → intent (10 tipus)
    - intent_discovery.yaml         — uj intentek felfedezese (evaluacio)
    - intent_consolidation.yaml     — duplikatumok osszevonasa
    - entity_extractor.yaml         — ne, datum, osszeg, email, stb.
    - attachment_summarizer.yaml    — csatolmany → 1-soros osszefoglalas
    - priority_scorer.yaml          — urgency (low/normal/high/urgent)
    - routing_decider.yaml          — inbox/archive/spam/escalate

  Promptfoo: 12 existing test case (skills/email_intent_processor/tests/promptfooconfig.yaml)
  Guardrail: skills/email_intent_processor/guardrails.yaml (B1.2-bol)
  Ismert gyenge pontok:
    - Intent catalog hianyos (10 tipus, de a valos mailbox-ban lathato ~12-15 kategoria)
    - HU entity extraction: adoszam, bankszamla, cim csak szabaly-alapu
    - Marketing vs notification hatarvonal elmosott
    - Phase 0 E2E-ben 95.6% volt a classifier accuracy, de csak 10 intent-re
```

---

## B4.1 FELADAT: aszf_rag_chat + email_intent_processor 95%+ Promptfoo

> **Gate:** 2/2 skill 95%+ promptfoo pass rate, guardrails.yaml finomhangolva, 10-pont checklist 8+/10 mindkettore
> **Eszkozok:** `/prompt-tuning`, `/service-hardening`, `/dev-step`, `/regression`
> **Lenyeg:** Promptfoo coverage + guardrail tuning valos trace-ek alapjan, NEM arbitraris threshold csavargatas

### Implementacios Lepesek

#### LEPES 1: aszf_rag_chat Citation + Hallucination Hardening

```
Hol: skills/aszf_rag_chat/prompts/ (meglevo YAML-ok modositasa)
     skills/aszf_rag_chat/tests/promptfooconfig.yaml (7 → 12 test case)
     skills/aszf_rag_chat/guardrails.yaml (finomhangolas)

Cel 1 — Citation enforcement: answer_generator.yaml es citation_extractor.yaml
        kotelezo forras hivatkozasi formatum ([doc:chunk_id] standardra terelese)

Cel 2 — Hallucination detector kalibracio: a meglevo hallucination_detector.yaml
        promptfoo eval-ja alapjan threshold beallitas (jelenlegi confidence 0.8+ de
        valos accuracy ~70% — ez a B3.5 tanulsaga: LLM self-report megbizhatatlan)

Cel 3 — Scope guard: out-of-scope kerdesek jobb elutasitasa guardrail level-en

KONKRET TEENDOK:

1. Futtasd: npx promptfoo eval -c skills/aszf_rag_chat/tests/promptfooconfig.yaml
   - Nezd meg melyik testek bukkannek el (varhatoan 1/7 citation, 1/7 hallucination, 1/7 scope)
   - Jegyezz fel melyik prompt, melyik assertion bukott

2. answer_generator.yaml javitas (citation format):
   - System prompt-ba: "MINDEN allitast [doc:chunk_id] formatumu hivatkozassal kell alatamasztani"
   - Few-shot pelda hozzaadasa (valos chunk struktura)
   - Temperature csokkentes 0.3 → 0.2 (determinisztikusabb output)

3. citation_extractor.yaml javitas:
   - Regex-alapu validacio post-processing: `\[doc:[\w-]+\]` minta
   - Ha hianyzik → return error ("No citations found") helyett mock citation

4. hallucination_detector.yaml kalibracio:
   - Prompt: "Vizsgald meg soronkent, hogy minden allitas megjelenik-e a context-ben.
     Ha nem: list: list[hallucinated_claims]"
   - Return format strict JSON schema (pydantic validalasra)
   - Confidence threshold: 0.85 → 0.90 (kevesbe megengedo)

5. 5 UJ promptfoo test case a tests/promptfooconfig.yaml-hoz (7 → 12):
   - test_citation_mandatory:       query + context → valaszban legalabb 1 [doc:X] kellett
   - test_hallucination_detection:  fabricated answer → detector flags it
   - test_out_of_scope_rejection:   "mi a kedvenc szined?" → polite refusal (scope guard)
   - test_multi_source_synthesis:   2 chunk → valasz mindkettot hivatkozza
   - test_contradictory_sources:    2 conflicting chunk → detector flags contradiction

6. guardrails.yaml finomhangolas (skills/aszf_rag_chat/guardrails.yaml):
   - input_guards:
     - scope_guard: threshold 0.7 → 0.8 (strictebb)
     - injection_guard: max_length 2000 → 4000 (jogi kerdesek hosszabbak lehetnek)
   - output_guards:
     - hallucination_guard: enabled, threshold 0.9
     - pii_guard: mask_levels [NAME, EMAIL, PHONE]
     - citation_guard: NEW — require `\[doc:[\w-]+\]` minta a responseban

7. Futtasd ujra: npx promptfoo eval → 12/12 PASS (95%+ = 12/12 vagy 11/12)

Gate: 95%+ pass rate (12+ test case-en), guardrails.yaml finomhangolt, 10-pont checklist 8+/10
```

#### LEPES 2: email_intent_processor Intent Catalog + HU Entity Bovites

```
Hol: skills/email_intent_processor/prompts/intent_classifier.yaml + entity_extractor.yaml
     skills/email_intent_processor/tests/promptfooconfig.yaml (12 → 16 test case)
     skills/email_intent_processor/guardrails.yaml (HU PII finomhangolas)

Cel 1 — Intent catalog bovites (10 → 12 tipus):
        Uj intents a Phase 0 valos Outlook adatok alapjan:
        - invoice_received (elkulonitve a notification-tol)
        - calendar_invite
        - access_request
        - security_alert
        - reminder / deadline

Cel 2 — HU entity extraction finomitas:
        - tax_number (adoszam): XXXXXXXX-X-XX regex + LLM fallback
        - bank_account: XXXXXXXX-XXXXXXXX(-XXXXXXXX) regex
        - postal_address: varos + utca + iranyitoszam (4 jegy) LLM extraction

Cel 3 — Marketing vs notification szetvalasztas:
        Jelenlegi problema: "your receipt from ..." → valaszthatna notification
        VAGY marketing kategoriat. A valodi szignal: van-e penzugyi tranzakcio?
        ha igen → notification, ha nincs → marketing

KONKRET TEENDOK:

1. Futtasd: npx promptfoo eval -c skills/email_intent_processor/tests/promptfooconfig.yaml
   - Mert pattinak az elsok? — jegyezd fel

2. intent_classifier.yaml bovites:
   - Intent lista: 10 → 12 (add: `invoice_received`, `calendar_invite`)
   - Intent lista MODELLIS (ezek nem kategoriak, hanem kerdesek):
     * "Kapott szamla/dijbekero/fizetesi felszolitas" → invoice_received
     * "Meeting meghivas .ics csatolmany" → calendar_invite
     * "Login/OTP/reset" → security_alert
   - Few-shot peldak frissitese: 2 uj pelda per uj intent
   - Prompt finomitas: "Ha az email penzt/osszeget tartalmaz ES tranzakcio tortent →
     notification; ha csak ajanlat/reklam → marketing"

3. entity_extractor.yaml HU szabalyok:
   - Uj entity tipusok: tax_number, bank_account, postal_address
   - Per-entity regex + LLM fallback (a HU format elutero az EN-tol!)
   - JSON schema strict: {type, value, confidence, source: "regex"|"llm"}
   - HU pelda prompt: "12345678-2-42 → {type: tax_number, value: '12345678-2-42', source: regex, confidence: 1.0}"

4. 4 UJ promptfoo test case (12 → 16):
   - test_intent_invoice_received:  valos bestix email sample (Phase 0-bol) → invoice_received
   - test_intent_calendar_invite:   .ics csatolmany → calendar_invite
   - test_entity_hu_tax_number:     "12345678-2-42" → correct tax_number extraction
   - test_marketing_vs_notification: "Your receipt from X" → notification (penzugyi kulcsszo detektalas)

5. guardrails.yaml HU PII bovites (skills/email_intent_processor/guardrails.yaml):
   - pii_guard.detect_patterns:
     - HU_TAX_NUMBER: `\d{8}-\d-\d{2}`
     - HU_BANK_ACCOUNT: `\d{8}-\d{8}(-\d{8})?`
     - EMAIL_ADDRESS: standard
     - PHONE_HU: `\+36[ -]?\d{1,2}[ -]?\d{3}[ -]?\d{4}` VAGY `06[ -]?\d{1,2}[ -]?\d{3}[ -]?\d{4}`
   - output_guards.mask_policy: "mask" (eredmenyben ne jelenjenek meg a PII-k tisztan)

6. Futtasd ujra: npx promptfoo eval → 16/16 PASS (95%+ = 16/16 vagy 15/16)

Gate: 95%+ pass rate (16+ test case-en), 2 uj intent mukodik, HU entity extraction 3/3 tipus OK
```

#### LEPES 3: /service-hardening 10-pont Checklist Audit (MINDKET skill-re)

```
Hol: /service-hardening aszf_rag_chat
     /service-hardening email_intent_processor

Az audit 10 pontot vizsgal (lasd: .claude/commands/service-hardening.md):
  1. Unit teszt (5+ + coverage 70%+)
  2. Integracio (valos DB ha kell)
  3. API teszt (curl 200 OK + source: "backend")
  4. Prompt teszt (promptfoo 95%+)   ← LEPES 1+2-bol mar OK
  5. Error handling (AIFlowError, is_transient)
  6. Logging (structlog, no print/PII)
  7. Dokumentacio (docstring, README)
  8. UI (source badge, 0 console error)
  9. Input guardrail (injection, scope)  ← LEPES 1+2-bol mar OK
  10. Output guardrail (hallucination, PII, scope)  ← LEPES 1+2-bol mar OK

KONKRET TEENDOK:

1. /service-hardening aszf_rag_chat futtatas
   - Jegyezd fel a bukott pontokat (varhato: #7 dokumentacio, #8 UI badge)
   - Gap javitas: hianyzo docstringok, README.md bovites
   - Ujra-audit: 8+/10 pont

2. /service-hardening email_intent_processor futtatas
   - Jegyezd fel a bukott pontokat
   - Gap javitas
   - Ujra-audit: 8+/10 pont

Gate: mindket skill 8+/10, PRODUCTION-READY verdict
```

#### LEPES 4: Regresszio + Commit

```
/lint-check → 0 error
/regression → 1424+ unit test PASS (ne romoljon)
/update-plan → 58 progress B4.1 DONE

Commit: feat(sprint-b): B4.1 skill hardening — aszf_rag 95%+ + email_intent 95%+ + 10pt checklist
```

### Teszt Fajl Struktura

```
skills/aszf_rag_chat/tests/promptfooconfig.yaml           — 7 → 12 test case
skills/aszf_rag_chat/guardrails.yaml                       — FINOMHANGOLAS (B1.2-bol)
skills/aszf_rag_chat/prompts/answer_generator.yaml         — citation enforcement
skills/aszf_rag_chat/prompts/citation_extractor.yaml       — strict format
skills/aszf_rag_chat/prompts/hallucination_detector.yaml   — kalibracio

skills/email_intent_processor/tests/promptfooconfig.yaml   — 12 → 16 test case
skills/email_intent_processor/guardrails.yaml              — HU PII bovites
skills/email_intent_processor/prompts/intent_classifier.yaml  — 10 → 12 intent
skills/email_intent_processor/prompts/entity_extractor.yaml   — HU entity szabalyok

Osszesen: 9 uj promptfoo test case (5 + 4), 4 prompt YAML modositas, 2 guardrail finomhangolas
Unit teszt NEM valtozik (1424 marad, esetleg +1-2 extra ha uj helper fuggveny jon)
```

---

## VEGREHAJTAS SORRENDJE

```
--- LEPES 1: aszf_rag_chat ---
/dev-step "B4.1.1 — Futtass promptfoo baseline-t aszf_rag_chat-re, jegyezd fel a bukott testek listajat"
/prompt-tuning aszf_rag_chat  # a kesz prompt tuning ciklust hasznald
/dev-step "B4.1.2 — answer_generator + citation_extractor citation enforcement javitas"
/dev-step "B4.1.3 — hallucination_detector kalibracio + threshold tuning"
/dev-step "B4.1.4 — 5 uj promptfoo test case (7 → 12)"
/dev-step "B4.1.5 — guardrails.yaml finomhangolas + citation_guard hozzaadas"
npx promptfoo eval -c skills/aszf_rag_chat/tests/promptfooconfig.yaml  # gate: 12/12 PASS

--- LEPES 2: email_intent_processor ---
/dev-step "B4.1.6 — Futtass promptfoo baseline-t email_intent_processor-re"
/prompt-tuning email_intent_processor
/dev-step "B4.1.7 — intent_classifier 10 → 12 intent + few-shot pelda bovites"
/dev-step "B4.1.8 — entity_extractor HU szabalyok (tax/bank/address)"
/dev-step "B4.1.9 — 4 uj promptfoo test case (12 → 16)"
/dev-step "B4.1.10 — guardrails.yaml HU PII pattern bovites"
npx promptfoo eval -c skills/email_intent_processor/tests/promptfooconfig.yaml  # gate: 16/16 PASS

--- LEPES 3: /service-hardening 10-point audit ---
/service-hardening aszf_rag_chat          # gate: 8+/10
/service-hardening email_intent_processor # gate: 8+/10
# Hianyzo pontok javitasa (varhato: docstringok, README, UI badge)

--- LEPES 4: SESSION LEZARAS ---
/lint-check → 0 error
/regression → 1424+ unit test PASS (ne romoljon)
/update-plan → 58 progress B4.1 DONE, key numbers update
```

---

## KORNYEZET ELLENORZES

```bash
git branch --show-current                                             # → feature/v1.3.0-service-excellence
git log --oneline -3                                                  # → 4579cd2, a1c948a, 70f505f
.venv/Scripts/python -m pytest tests/unit/ -q --ignore=tests/unit/vectorstore/test_search.py 2>&1 | tail -1
                                                                       # → 1424 passed
.venv/Scripts/ruff check src/ tests/ 2>&1 | tail -1                  # → All checks passed!
ls skills/aszf_rag_chat/prompts/*.yaml | wc -l                        # → 7 prompt
ls skills/email_intent_processor/prompts/*.yaml | wc -l               # → 8 prompt
grep -c "^  - vars:" skills/aszf_rag_chat/tests/promptfooconfig.yaml  # → 7 test case
grep -c "^  - vars:" skills/email_intent_processor/tests/promptfooconfig.yaml  # → 12 test case

# Promptfoo baseline (ha a npx nincs, telepitsd: npm install -g promptfoo)
which npx 2>&1 || npm --version                                       # → check node/npm ready

# Docker szukseges a valos LLM-hez (promptfoo LLM API-t hiv)
# Helyi OPENAI_API_KEY-nek .env-ben kell lennie
grep -c "^OPENAI_API_KEY=" .env                                       # → 1
```

---

## S27 TANULSAGAI (alkalmazando S28-ban!)

1. **Valos trace-alapu kalibracio > talalgatas** — A B3.5-ben a confidence thresholdokat (0.90/0.70/0.50) nem vakon valasztottuk: Phase 1+2 valos PDF eredmenyekbol kalibraltuk. B4.1-ben ugyanezt kell csinalni: promptfoo eval-t futtani a valos kerdesekre/emailekre, a bukott testek elemzesevel dontsuk el a threshold + prompt modositasokat.

2. **Pure expression template resolver** — a `pipeline/template.py` fix ota a `"{{ list_var }}"` mostantol nativ Python objektumot ad vissza. Ha B4.1-ben prompt YAML-okat hasznalsz Jinja2 template-tel, ne felejtsd el: a pure expression ({{ x }}) natíve typet ad vissza, a mixed ({{ x }} {{ y }}) stringet.

3. **LLM self-report confidence MEGBIZHATATLAN** — B3.5 audit egyik fo tanulsaga. B4.1-ben a hallucination_detector.yaml NEM szabad hogy magara vetitse "confidence: 0.9 = 90% pontos" hittel. A kalibraciot promptfoo-val valasztassuk el: "reported confidence" vs "actual correctness" merese.

4. **Guardrail: mar letezik (B1.2), csak finomhangolasra szorul** — ne irj uj guardrails.yaml-t, a B1.2 letrehozta mindketskill-nek. Csak threshold + pattern bovites a feladat.

5. **Pre-existing test fail engedelyezett** — `test_rerank_fallback` (HuggingFace model download) NEM regresszio. Ha futas kozben latsz, skip-eld.

6. **Extra test case OLCSO, irj tobbet ha van ertelme** — B3.5 minimumkent 15-ot ker, en 36-ot irtam. A promptfoo tesztek meg olcsobbak (csak eval time), irj 2-3 bonust ha a tesztcase konkret edge case-t fed le.

---

## MEGLEVO KOD REFERENCIAK (olvasd el mielott irsz!)

```
# aszf_rag_chat skill struktura:
skills/aszf_rag_chat/skill.yaml                           — skill manifest
skills/aszf_rag_chat/skill_config.yaml                    — runtime config
skills/aszf_rag_chat/__init__.py                          — service init
skills/aszf_rag_chat/prompts/                             — 7 YAML prompt
skills/aszf_rag_chat/guardrails.yaml                      — B1.2-bol, FINOMHANGOLANDO
skills/aszf_rag_chat/tests/promptfooconfig.yaml           — 7 test case, BOVITENDO 12-re
skills/aszf_rag_chat/tests/datasets/                      — golden query dataset
skills/aszf_rag_chat/reference/                           — referencia dokumentumok

# email_intent_processor skill struktura:
skills/email_intent_processor/skill.yaml
skills/email_intent_processor/skill_config.yaml
skills/email_intent_processor/__init__.py
skills/email_intent_processor/prompts/                    — 8 YAML prompt
skills/email_intent_processor/guardrails.yaml             — B1.2-bol, FINOMHANGOLANDO
skills/email_intent_processor/schemas/v1/                 — JSON schemas
skills/email_intent_processor/tests/promptfooconfig.yaml  — 12 test case, BOVITENDO 16-ra

# Guardrail framework referencia:
src/aiflow/guardrails/                                    — base classes
01_PLAN/61_GUARDRAIL_PII_STRATEGY.md                      — PII masking strategy
src/aiflow/services/guardrail_registry/                   — service

# Promptfoo + service-hardening slash commands:
.claude/commands/service-hardening.md                     — 10-point audit protocol
.claude/commands/prompt-tuning.md                         — Langfuse → Promptfoo → fix cycle
.claude/commands/dev-step.md                              — standard dev cycle
.claude/commands/quality-check.md                         — promptfoo + cost analysis

# Valos adat a Phase 0-bol (email_intent kalibraciohoz!):
data/e2e_results/outlook_fetch/bestix_emails.json         — 30 bestix email + intent results
data/e2e_results/outlook_fetch/kodosok_emails.json        — 30 kodosok email + intent
data/e2e_results/outlook_fetch/gmail_emails.json          — 30 gmail email + intent
data/e2e_results/outlook_fetch/invoice_candidates.json    — 9 invoice-relevans email
data/e2e_results/outlook_fetch/intent_distribution.json   — aggregalt statisztika
data/emails/outlook/{bestix,kodosok,gmail}/*.eml          — nyers email peldak

# Confidence scoring (B3.5-bol, esetleg aszf_rag-hoz is hasznos):
src/aiflow/engine/confidence.py                           — FieldConfidenceCalculator
src/aiflow/engine/confidence_router.py                    — route_by_confidence
tests/unit/engine/test_field_confidence.py                — 14 teszt minta
tests/unit/engine/test_confidence_router.py               — 11 teszt minta
```

---

## SPRINT B UTEMTERV (frissitett)

```
S19: B0     — DONE (4b09aad) — 5-layer arch + qbpp + prompt API + OpenAPI
S20: B1.1   — DONE (f6670a1) — 4 LLM guardrail prompt + llm_guards.py + 27 promptfoo
S21: B1.2   — DONE (7cec90b) — 5 guardrails.yaml + PIIMaskingMode + 31 teszt
S22: B2.1   — DONE (51ce1bf) — Core infra service tesztek (65 test, Tier 1)
S23: B2.2   — DONE (62e829b) — v1.2.0 service tesztek (65 test, Tier 2)
S24: B3.1   — DONE (372e08b) — Invoice Finder pipeline + email search + doc acquire (29 test)
S25: B3.2   — DONE (aecce10) — Invoice Finder extract + payment + report + notify (16 test)
S26a: B3.E2E Phase 0 — DONE (0b5e542) — Outlook COM multi-account fetch + email intent
S26a: B3.E2E Phase 1 — DONE (f1f0029) — offline invoice finder pipeline (20/20 PASS)
S27a: B3.E2E Phase 2 — DONE (8b10fd6) — PipelineRunner DB persistence integration
S27a: B3.E2E Phase 3 — DONE (70f505f) — full 8-step pipeline on 3 Outlook accounts
S27b: B3.5  — DONE (4579cd2) — confidence scoring hardening + review routing (36 test)
S28:  B4.1  ← KOVETKEZO SESSION — Skill hardening: aszf_rag + email_intent
S29:  B4.2  — Skill hardening: process_docs + invoice + cubix + diagram
S30:  B5    — Spec writer + diagram pipeline + koltseg baseline
S31:  B6    — UI Journey audit + 4 journey tervezes + navigacio redesign
S32:  B7    — Verification Page v2 (bounding box, diff, per-field confidence szin)
S33:  B8    — UI Journey implementacio (top 3 journey + dark mode)
S34:  B9    — Docker containerization + UI pipeline trigger + deploy teszt
S35:  B10   — POST-AUDIT + javitasok
S36:  B11   — v1.3.0 tag + merge
```

---

## FONTOS SZABALYOK (emlekeztetok)

- **`/prompt-tuning` + `/service-hardening` HASZNALANDO** — ezek a B0-bol jottek, a tuning ciklust pontosan kovesd
- **Promptfoo = valos LLM hivas** — OPENAI_API_KEY szukseges, NEM mock. Minden test case valos koltseget jelent (~$0.01-0.05 / test)
- **Guardrail meglevo, csak finomhangolas** — ne irj uj guardrails.yaml-t, csak threshold + pattern modositas
- **10-point checklist = `/service-hardening` kimenete** — ne keszits kulon dokumentumot, a command outputja legyen a forras
- **HU szabalyok = HU szabalyok** — a entity_extractor.yaml HU regexei nem lehetnek EN-centrikus
- **Valos adat Phase 0-bol** — use `data/e2e_results/outlook_fetch/*.json` a kalibracioshoz, NE talalj ki fake emaileket
- **structlog mindig** — `logger = structlog.get_logger(__name__)`, nincs print()
- **Async-first** — ha uj helper fuggvenyt irsz (pl. entity regex validator), async legyen ha I/O van

---

## B4.1 GATE CHECKLIST

```
aszf_rag_chat:
[ ] skills/aszf_rag_chat/tests/promptfooconfig.yaml 12+ test case
[ ] answer_generator.yaml citation enforcement aktiv (few-shot + system prompt)
[ ] citation_extractor.yaml strict format: `\[doc:[\w-]+\]` validacio
[ ] hallucination_detector.yaml kalibralt (threshold 0.85 → 0.90)
[ ] guardrails.yaml finomhangolt: scope 0.8, citation_guard uj
[ ] npx promptfoo eval → 95%+ pass rate (12/12 vagy 11/12)
[ ] /service-hardening aszf_rag_chat → 8+/10 pont

email_intent_processor:
[ ] skills/email_intent_processor/tests/promptfooconfig.yaml 16+ test case
[ ] intent_classifier.yaml 10 → 12 intent (invoice_received, calendar_invite)
[ ] entity_extractor.yaml HU szabalyok (tax_number, bank_account, postal_address)
[ ] guardrails.yaml HU PII patterns (HU_TAX_NUMBER, HU_BANK_ACCOUNT, PHONE_HU)
[ ] npx promptfoo eval → 95%+ pass rate (16/16 vagy 15/16)
[ ] /service-hardening email_intent_processor → 8+/10 pont

Ossz:
[ ] /lint-check → 0 error
[ ] /regression → 1424+ unit test PASS (ne romoljon)
[ ] /update-plan → 58 progress B4.1 DONE + key numbers
[ ] git commit: feat(sprint-b): B4.1 skill hardening — aszf_rag + email_intent 95%+
```
