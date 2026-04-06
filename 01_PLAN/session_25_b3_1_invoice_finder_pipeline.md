# AIFlow Sprint B — Session 25 Prompt (B3.1: Invoice Finder Pipeline Design + Email + Doc Acquisition)

> **Datum:** 2026-04-06
> **Branch:** `feature/v1.3.0-service-excellence` | **HEAD:** `d94d956`
> **Port:** API 8102, Frontend 5174
> **Elozo session:** S24 — B2.2 DONE (13 v1.2.0 service × 5 test = 65 unit test, B2 GATE 130 test PASS)
> **Terv:** `01_PLAN/58_POST_SPRINT_HARDENING_PLAN.md` (B3 szekció, sor 929+)

---

## KONTEXTUS

### B2 Eredmenyek (S22-S24 — DONE)

- 26 service × 5 teszt = 130 service unit teszt PASS
- `tests/unit/services/` konyvtar: 26 teszt fajl + conftest.py
- B2 GATE: TELJESITVE (commit 62e829b)
- Regression: 1325 unit test, 0 regresszio

### Infrastruktura (v1.3.0)

- 26 service | 165 API endpoint (25 router) | 46 DB tabla | 29 migracio
- 18 pipeline adapter | 6 pipeline template | 5 skill | 22 UI oldal
- 1325 unit test | 129 guardrail teszt | 97 security teszt | 54 promptfoo teszt
- Guardrail: A5 rule-based + B1.1 LLM fallback + B1.2 per-skill config

### Meglevo Invoice Infrastruktura (NEM kell ujrairni!)

```
Pipeline YAML-ok:
  src/aiflow/pipeline/builtin_templates/invoice_automation_v1.yaml  — email → classify → extract (C6)
  src/aiflow/pipeline/builtin_templates/invoice_automation_v2.yaml  — v1 + routing + notify (C9)

Pipeline adapterek (mind mukodokepes):
  src/aiflow/pipeline/adapters/email_adapter.py        — email fetch
  src/aiflow/pipeline/adapters/classifier_adapter.py   — intent classification
  src/aiflow/pipeline/adapters/document_adapter.py     — document extraction
  src/aiflow/pipeline/adapters/data_router_adapter.py  — file routing
  src/aiflow/pipeline/adapters/notification_adapter.py — email/slack notify

Pipeline runner + compiler:
  src/aiflow/pipeline/runner.py     — YAML → DAG → vegrehajtas
  src/aiflow/pipeline/compiler.py   — YAML parse + validalas

Skill (invoice_processor):
  skills/invoice_processor/skill_config.yaml          — model + parser + validation config
  skills/invoice_processor/prompts/invoice_classifier.yaml        — szamla vs nem-szamla
  skills/invoice_processor/prompts/invoice_header_extractor.yaml  — fejlec mezok kinyeres
  skills/invoice_processor/prompts/invoice_line_extractor.yaml    — tetel sorok
  skills/invoice_processor/prompts/invoice_validator.yaml         — validalas

Tools:
  src/aiflow/tools/azure_doc_intelligence.py   — Azure DI async REST kliens
  src/aiflow/tools/attachment_processor.py      — 3-retegu: Docling → Azure DI → LLM Vision

DB tablak (migracio 015, 016):
  document_type_configs  — szamla mezo definiciok (config-driven extraction)
  invoices               — kinyert szamla adatok (30+ mezo)
  invoice_line_items     — szamla tetel sorok

Notification template:
  prompts/notifications/invoice_processed.yaml — email template szamla riporthoz
```

---

## B3.1 FELADAT: Invoice Finder Pipeline Design + Email + Doc Acquisition

> **Gate:** invoice_finder_v3.yaml pipeline + 3 uj adapter metodus + 5 uj/modositott prompt YAML + 15 unit test PASS
> **Eszkozok:** `/dev-step`, `/new-pipeline`, `/new-prompt`, `/regression`
> **Lenyeg:** Az Invoice Finder NEM uj rendszer — a MEGLEVO v2 pipeline bovitese uj step-ekkel!

### Miert v3 es nem v2 modositas?

Az invoice_automation_v2.yaml megmarad (visszafele kompatibilis). Az Invoice Finder egy BOVITETT valtozat:
- v2: email → classify → extract → route → notify (5 step)
- **v3 (Invoice Finder):** email search → doc acquire → classify → extract → payment status → file org → report → notify (8 step)

### Uj Pipeline: `invoice_finder_v3.yaml`

```yaml
# src/aiflow/pipeline/builtin_templates/invoice_finder_v3.yaml
name: invoice_finder_v3
version: "3.0.0"
description: "Invoice Finder: mailbox scan → acquire → classify → extract → report → notify"

trigger:
  type: manual    # UI-bol "Scan Mailbox" gomb

input_schema:
  connector_id:       { type: string, required: true }
  days:               { type: integer, default: 30 }
  limit:              { type: integer, default: 50 }
  confidence_threshold: { type: number, default: 0.8 }
  notify_recipients:  { type: string, default: "admin@aiflow.local" }
  output_dir:         { type: string, default: "./data/invoices" }

steps:
  # --- S25 (B3.1) --- 
  step_1_email_search     — email_connector.search_invoices
  step_2_doc_acquire      — document_extractor.acquire_from_email
  step_3_classify         — classifier.classify (szamla vs nem-szamla)
  # --- S26 (B3.2) ---
  step_4_extract          — document_extractor.extract
  step_5_payment_status   — UJ step (payment_status_adapter)
  step_6_file_organize    — data_router.route_files (Jinja2 template nevkonvencio)
  step_7_report           — UJ step (report_generator_adapter)
  step_8_notify           — notification.send (Jinja2 email template)
```

### B3.1 Reszletes Feladatok (CSAK S25!)

#### LEPES 1: Pipeline YAML + Skill Directory Setup

```
Uj fajlok:
  src/aiflow/pipeline/builtin_templates/invoice_finder_v3.yaml  — teljes 8-step pipeline definicio
  skills/invoice_finder/                                         — uj skill directory
    __init__.py
    __main__.py                   — CLI: python -m skills.invoice_finder
    skill.yaml                    — manifest
    skill_config.yaml             — runtime config (azure_di_enabled: true!)
    guardrails.yaml               — B1.2 pattern (PII masking OFF szamla kontextusban!)
    models/__init__.py            — Pydantic I/O modellek

Meglevo config modositas:
  skills/invoice_processor/skill_config.yaml — NEM modositjuk, az Invoice Finder sajat config-ot kap
```

#### LEPES 2: Email Search Step — `search_invoices` metodus

```
Hol: email_adapter.py BOVITES (uj metodus: search_invoices)

Logika:
  1. IMAP/O365 postafiok scan (meglevo fetch_emails hasznalata)
  2. Intent-based szures:
     - Subject keywords: "szamla", "invoice", "számla", "fizetesi", "payment"
     - Body keywords: "fizetendo", "hatarido", "osszeg", "netto", "brutto"
     - Csatolmany-nev: *.pdf (szamla*.pdf, invoice*.pdf, szla*.pdf)
  3. Relevancia scoring: keyword match count / total keywords → 0.0-1.0
  4. Threshold: score >= 0.3 → potencialis szamla email

Output Pydantic model:
  class InvoiceEmailResult(BaseModel):
      email_id: str
      subject: str
      sender: str
      date: str
      score: float                    # relevancia score
      has_attachment: bool
      attachment_names: list[str]
      body_snippet: str               # elso 200 karakter

Prompt:
  prompts/invoice_finder/invoice_email_scanner.yaml  — OPCIONALIS LLM scoring (ha keyword < 0.3)

Unit tesztek (5):
  test_search_invoices_keyword_match()    — keyword talalat → score > 0
  test_search_invoices_no_match()         — nem szamla email → ures lista
  test_search_invoices_attachment_boost()  — PDF csatolmany → emelt score
  test_search_invoices_hungarian_keywords() — magyar kulcsszavak mukodnek
  test_search_invoices_threshold_filter()  — score < threshold kiszurve
```

#### LEPES 3: Document Acquisition Step — `acquire_from_email` metodus

```
Hol: document_adapter.py BOVITES (uj metodus: acquire_from_email)

Logika:
  1. HA csatolmany VAN:
     a. Letoltes temp konyvtarba
     b. Docling parse (vagy Azure DI ha azure_di_enabled: true)
     c. Minoseg-ellenorzes (text hossz, tablak szama)
  2. HA csatolmany NINCS:
     a. Body-bol URL-ek kinyerese (regex: https?://...\.pdf)
     b. HTTP GET letoltes
     c. Parse (ugyanaz mint csatolmanynal)
  3. Fallback: ha semmi nem talalható → skip (log warning)

Meglevo kod hasznalata:
  - attachment_processor.py:77-187 — minoseg-alapu routing (Docling → Azure → Vision)
  - azure_doc_intelligence.py — Azure DI kliens (async)
  - docling_parser.py — helyi parser

Output Pydantic model:
  class AcquiredDocument(BaseModel):
      email_id: str
      file_name: str
      file_path: str              # temp fajl utvonal
      raw_text: str
      tables: list[dict]
      page_count: int
      parser_used: str            # "docling" | "azure_di" | "vision"
      quality_score: float        # 0.0-1.0
      source: str                 # "attachment" | "url" | "body"

Unit tesztek (5):
  test_acquire_with_attachment()       — PDF csatolmany → parsed document
  test_acquire_without_attachment()    — nincs csatolmany → skip/url fallback
  test_acquire_quality_check()         — minoseg score szamitas
  test_acquire_parser_selection()      — parser valasztas logika
  test_acquire_error_handling()        — hibas fajl → graceful skip
```

#### LEPES 4: Invoice Classification Step — meglevo classifier bovites

```
Hol: classifier_adapter.py — a meglevo classify metodus hasznalata
     skills/invoice_finder/prompts/invoice_classifier.yaml — uj, Invoice Finder specifikus prompt

Logika:
  - Meglevo ClassifierService.classify() hasznalata
  - invoice_finder specifikus intent: "invoice" vs "not_invoice"
  - Confidence threshold: >= 0.8 → auto-accept, < 0.8 → human_review queue
  - Magyar + angol szamlak tamogatasa

Prompt (uj YAML):
  skills/invoice_finder/prompts/invoice_classifier.yaml
  - Input: raw_text (parsed szamla szoveg)
  - Output: { "is_invoice": bool, "confidence": float, "doc_type": str, "language": str }
  - Peldak: magyar szamla, angol invoice, nem-szamla dokumentum

Unit tesztek (5):
  test_classify_invoice_detected()       — szamla szoveg → is_invoice=True, confidence > 0.8
  test_classify_not_invoice()            — nem-szamla → is_invoice=False
  test_classify_confidence_threshold()   — alacsony confidence → human_review jelzes
  test_classify_hungarian_invoice()      — magyar szamla → helyes felismeres
  test_classify_english_invoice()        — angol invoice → helyes felismeres
```

### Prompt YAML Fajlok (LEPES 2-4)

```
Uj prompt YAML-ok (skills/invoice_finder/prompts/):
  invoice_email_scanner.yaml       — email → szamla relevancia (Step 1)
  invoice_classifier.yaml          — szamla vs nem-szamla (Step 3)

Ezek a B3.1-ben szukseges promptok. B3.2-ben jon meg 3:
  invoice_field_extractor.yaml     — mezo kinyeres (Step 4, B3.2-ben)
  invoice_payment_status.yaml      — fizetesi statusz (Step 5, B3.2-ben)
  invoice_report_generator.yaml    — riport generalas (Step 7, B3.2-ben)
```

### Teszt Fajl Struktura (UJ fajlok)

```
tests/unit/pipeline/
  test_invoice_finder_v3.py           — pipeline YAML validacio (5 test)
  test_invoice_email_search.py        — search_invoices adapter (5 test)
  test_invoice_doc_acquire.py         — acquire_from_email adapter (5 test)

Osszesen: 15 unit test (3 × 5)
```

### Tesztelesi Szabalyok

1. **Async tesztek** — `async def test_*` + `@pytest.mark.asyncio`
2. **Mock external** — IMAP, HTTP, filesystem IO mock (unit test, NEM integration!)
3. **`@test_registry` header** — MINDEN teszt fajl elejen
4. **Adapter tesztek** — mock service-eket inject-alunk, adapter logikat tesztelunk
5. **Prompt YAML tesztek** — YAML parse + Jinja2 render + schema validalas

---

## VEGREHAJTAS SORRENDJE

```
--- LEPES 1: Skill directory + Pipeline YAML ---
/dev-step "B3.1.1 — Invoice Finder skill directory + invoice_finder_v3.yaml pipeline"
  - skills/invoice_finder/ teljes directory setup
  - invoice_finder_v3.yaml pipeline definicio (8 step)
  - skill.yaml, skill_config.yaml, guardrails.yaml
  - Pipeline YAML validacios tesztek (5 test)

--- LEPES 2: Email Search adapter + prompt ---
/dev-step "B3.1.2 — search_invoices metodus + invoice_email_scanner.yaml prompt"
  - email_adapter.py bovites: search_invoices() metodus
  - skills/invoice_finder/prompts/invoice_email_scanner.yaml
  - InvoiceEmailResult Pydantic model
  - 5 unit test

--- LEPES 3: Document Acquisition adapter ---
/dev-step "B3.1.3 — acquire_from_email metodus + attachment handling"
  - document_adapter.py bovites: acquire_from_email() metodus
  - AcquiredDocument Pydantic model
  - Meglevo attachment_processor.py hasznalata
  - 5 unit test

--- LEPES 4: Invoice Classification prompt ---
/dev-step "B3.1.4 — Invoice Finder classifier prompt + adapter integracio"
  - skills/invoice_finder/prompts/invoice_classifier.yaml
  - Classifier adapter integracio (meglevo classify hasznalata)
  - 5 unit test (lasd Lepes 4 fent)
  MEGJEGYZES: HA mar volt 15 teszt, ez a 4. lepes opcionalis (B3.2-re tolhato)

--- SESSION LEZARAS ---
/lint-check → 0 error
/regression → ALL PASS (1325 + 15 = 1340+ unit test)
/update-plan → 58 progress B3.1 DONE
```

---

## KORNYEZET ELLENORZES

```bash
git branch --show-current                                    # → feature/v1.3.0-service-excellence
git log --oneline -3                                         # → d94d956, 62e829b, dc9c25e
python -m pytest tests/unit/services/ -q 2>&1 | tail -1      # → 130 passed
.venv/Scripts/ruff check src/ tests/ 2>&1 | tail -1          # → All checks passed!
ls src/aiflow/pipeline/builtin_templates/*.yaml | wc -l       # → 6 template
ls src/aiflow/pipeline/adapters/*.py | wc -l                  # → 19 adapter (18 + __init__)
ls skills/invoice_processor/prompts/*.yaml | wc -l            # → 4 prompt
```

---

## S24 TANULSAGAI (alkalmazando S25-ben!)

1. **sentence_transformers telepitve** — reranker es classifier teszteknel flashrank model nevet kell hasznalni, kulonben HuggingFace model letoltest probal es timeout-ol
2. **docling lassu** — advanced_parser es document_adapter teszteknel `fallback_chain=["raw"]` vagy mock kell unit teszthez
3. **`_chunk_document_aware` bug** — regex split None-t ad capture group-okkal. Ha document_aware strategy-t hasznalunk, non-capturing group kell
4. **Meglevo adapter-ek mukodnek** — a pipeline adapterek (email, document, classifier, notification) mind tesztelve es mukodk. Hasznald oket, NE ird ujra!
5. **Mock session_factory pattern** — SQLAlchemy-fuggo service-ekhez a B2.1/B2.2 `mock_session_factory` fixture-t hasznald

---

## SPRINT B UTEMTERV

```
S19: B0   — DONE (4b09aad) — 5-layer arch + qbpp + prompt API + OpenAPI
S20: B1.1 — DONE (f6670a1) — 4 LLM guardrail prompt + llm_guards.py + 27 promptfoo
S21: B1.2 — DONE (7cec90b) — 5 guardrails.yaml + PIIMaskingMode + 31 teszt
S22: B2.1 — DONE (51ce1bf) — Core infra service tesztek (65 test, Tier 1)
S23: B2.2 — DONE (62e829b) — v1.2.0 service tesztek (65 test, Tier 2)
S24: B3.1 ← JELEN SESSION — Invoice Finder pipeline + email search + doc acquire
S25: B3.2 — Invoice Finder: extract + payment + report + notification (valos adat!)
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

- **`/dev-step` HASZNALANDÓ** — minden logikai blokk kulon dev-step
- **Unit test = mock** — ez NEM integration test! Adapter logika + Pydantic model tesztelese.
- **MEGLEVO adapter-ek BOVITESE** — uj metodus hozzaadasa, NEM uj adapter fajl!
- **Prompt YAML formatum** — PromptDefinition format (lasd meglevo invoice_processor promptokat minakent)
- **Pipeline YAML formatum** — lasd invoice_automation_v2.yaml strukturat minakent
- **Azure DI ENABLED** — az Invoice Finder skill_config.yaml-ban `azure_di_enabled: true`!
- **PII masking OFF** — szamla kontextusban a PII masking KIKAPCSOLVA (B0.1 strategia)
- **Async-first** — minden I/O async (await)
- **Fajlnev konvencio:** tesztek `test_invoice_*.py`, promptok `invoice_*.yaml`
- **Feedback:** Session vegen command_feedback.md KOTELEZO

---

## B3.1 GATE CHECKLIST

```
[ ] invoice_finder_v3.yaml pipeline definicio letezik (8 step)
[ ] skills/invoice_finder/ directory teljes (skill.yaml, skill_config.yaml, guardrails.yaml, __init__, __main__)
[ ] email_adapter.py: search_invoices() metodus mukodik
[ ] document_adapter.py: acquire_from_email() metodus mukodik
[ ] 2 uj prompt YAML: invoice_email_scanner.yaml + invoice_classifier.yaml
[ ] InvoiceEmailResult + AcquiredDocument Pydantic modellek
[ ] 15 unit test PASS (3 fajl × 5 test)
[ ] /lint-check → 0 error
[ ] /regression → ALL PASS (1340+ unit test)
[ ] Nincs regresszio a meglevo tesztekben
```

---

## MEGLEVO KOD REFERENCIAK (olvasd el mielott irsz!)

```
# Pipeline YAML minta:
src/aiflow/pipeline/builtin_templates/invoice_automation_v2.yaml

# Adapter bovites minta (lasd hogyan adtak hozza uj metodus-okat):
src/aiflow/pipeline/adapters/email_adapter.py        — fetch_emails() mar letezik
src/aiflow/pipeline/adapters/document_adapter.py     — extract() mar letezik

# Prompt YAML minta:
skills/invoice_processor/prompts/invoice_classifier.yaml
skills/invoice_processor/prompts/invoice_header_extractor.yaml

# Attachment processing (3-layer):
src/aiflow/tools/attachment_processor.py:77-187

# Azure DI kliens:
src/aiflow/tools/azure_doc_intelligence.py

# Skill directory minta:
skills/invoice_processor/                — teljes skill directory minta

# Guardrails minta:
skills/invoice_processor/guardrails.yaml — B1.2 pattern

# Pipeline runner (nem modositando, csak megertesre):
src/aiflow/pipeline/runner.py
src/aiflow/pipeline/compiler.py
```
