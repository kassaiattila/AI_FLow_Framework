# AIFlow Sprint B — Session 26 Prompt (B3.2: Invoice Finder — Extract + Payment + Report + Notify)

> **Datum:** 2026-04-06
> **Branch:** `feature/v1.3.0-service-excellence` | **HEAD:** `372e08b`
> **Port:** API 8102, Frontend 5174
> **Elozo session:** S25 — B3.1 DONE (Invoice Finder pipeline YAML + email search + doc acquire + 29 unit test)
> **Terv:** `01_PLAN/58_POST_SPRINT_HARDENING_PLAN.md` (B3.2 szekció, sor 961+)

---

## KONTEXTUS

### B3.1 Eredmenyek (S25 — DONE)

- `skills/invoice_finder/` skill directory letrehozva (skill.yaml, skill_config.yaml, guardrails.yaml, models, prompts)
- `invoice_finder_v3.yaml` — 8-step pipeline (search → acquire → classify → extract → payment → organize → report → notify)
- `email_adapter.py` bovitve: `EmailSearchInvoicesAdapter` + `_score_email_for_invoice()` keyword scoring
- `document_adapter.py` bovitve: `DocumentAcquireAdapter` + `_compute_quality_score()`
- 2 prompt YAML: `invoice_email_scanner.yaml`, `invoice_classifier.yaml`
- `InvoiceEmailResult`, `AcquiredDocument`, `InvoiceClassificationResult` Pydantic modellek
- 29 unit test PASS (4 fajl), 0 regresszio
- Regression: 1336 unit test, commit 372e08b

### Infrastruktura (v1.3.0 — frissitett szamok)

- 26 service | 165 API endpoint (25 router) | 46 DB tabla | 29 migracio
- 20 pipeline adapter | 7 pipeline template | 6 skill | 22 UI oldal
- 1336 unit test | 129 guardrail teszt | 97 security teszt | 54 promptfoo teszt
- Guardrail: A5 rule-based + B1.1 LLM fallback + B1.2 per-skill config

### Invoice Finder Pipeline (B3.1-bol — MAR LETEZIK)

```
YAML: src/aiflow/pipeline/builtin_templates/invoice_finder_v3.yaml

B3.1-ben elkeszult step-ek (S25):
  step 1: search_emails     — email_connector.search_invoices (EmailSearchInvoicesAdapter)
  step 2: acquire_documents — document_extractor.acquire_from_email (DocumentAcquireAdapter)
  step 3: classify_invoices — classifier.classify (ClassifierAdapter)

B3.2-ben elkeszitendo step-ek (JELEN SESSION):
  step 4: extract_fields       — document_extractor.extract (DocumentExtractAdapter — MAR LETEZIK)
  step 5: check_payment_status — payment_status.check (UJ adapter: PaymentStatusAdapter)
  step 6: organize_files       — data_router.route (DataRouterRouteAdapter — MAR LETEZIK)
  step 7: generate_report      — report_generator.generate (UJ adapter: ReportGeneratorAdapter)
  step 8: notify_team          — notification.send (NotificationSendAdapter — MAR LETEZIK)
```

### Meglevo Adapter-ek (NEM kell ujrairni, HASZNALD!)

```
Meglevo es mukodo adapterek:
  src/aiflow/pipeline/adapters/document_adapter.py     — DocumentExtractAdapter (step 4)
  src/aiflow/pipeline/adapters/data_router_adapter.py  — DataRouterRouteAdapter (step 6)
  src/aiflow/pipeline/adapters/notification_adapter.py — NotificationSendAdapter (step 8)

Meglevo invoice modellek (hasznalando):
  skills/invoice_processor/models/__init__.py — InvoiceHeader, LineItem, InvoiceTotals, ProcessedInvoice
  skills/invoice_finder/models/__init__.py    — AcquiredDocument, InvoiceEmailResult, InvoiceClassificationResult

Meglevo promptok (invoice_processor — MINTA, de Invoice Finder saját promptot kap):
  skills/invoice_processor/prompts/invoice_header_extractor.yaml — fejlec mezo kinyeres
  skills/invoice_processor/prompts/invoice_line_extractor.yaml   — tetel sorok
  skills/invoice_processor/prompts/invoice_validator.yaml        — validalas

DB tablak (mar leteznek, migracio 015/016):
  invoices          — kinyert szamla adatok (30+ mezo)
  invoice_line_items — szamla tetel sorok
```

---

## B3.2 FELADAT: Extract + Payment Status + Report + Notification

> **Gate:** 3 uj prompt YAML + 2 uj adapter (payment_status, report_generator) + notification template + 15 unit test PASS
> **Eszkozok:** `/dev-step`, `/new-prompt`, `/regression`
> **Lenyeg:** A v3 pipeline HATRALEVO 5 step-jenek implementalasa: extract, payment, organize, report, notify

### Uj Adapter-ek es Prompt-ok

#### LEPES 1: Invoice Field Extractor Prompt (Step 4)

```
Hol: skills/invoice_finder/prompts/invoice_field_extractor.yaml (UJ)

A meglevo DocumentExtractAdapter MARAD (step 4 mar használja).
De az Invoice Finder sajat prompt-ot kap a mezokinyereshez.

Prompt logika:
  - Input: raw_text (parsed szamla szoveg)
  - Output JSON: {
      invoice_number, invoice_date, fulfillment_date, due_date,
      vendor: { name, address, tax_number, bank_account },
      buyer: { name, address, tax_number },
      currency, payment_method,
      line_items: [{ description, quantity, unit, unit_price, net_amount, vat_rate, vat_amount, gross_amount }],
      totals: { net_total, vat_total, gross_total },
      language
    }
  - HU-specifikus: adoszam (12345678-2-41), AFA kulcsok (5%, 18%, 27%), magyar datumformatum

Prompt YAML sablon: kovetkezzen a invoice_header_extractor.yaml strukturajat
  - system: reszletes utasitas JSON formatummal
  - user: {{ raw_text }}
  - config: model openai/gpt-4o, temperature 0.0, response_format json_object

Unit tesztek (3):
  test_field_extractor_prompt_yaml_valid()     — YAML parse + kotelezp mezok
  test_field_extractor_prompt_has_hu_fields()   — magyar adoszam, AFA kulcsszavak
  test_field_extractor_jinja2_renders()         — {{ raw_text }} Jinja2 rendereles
```

#### LEPES 2: Payment Status Adapter (Step 5 — UJ fajl!)

```
Hol: src/aiflow/pipeline/adapters/payment_status_adapter.py (UJ fajl)

Ez az egyetlen TELJESEN UJ adapter fajl B3.2-ben!

Logika:
  1. Input: invoice_number, due_date, amount (szamla fejlec mezobol)
  2. Datum osszehasonlitas:
     - due_date < ma → "overdue" (lejart)
     - due_date <= ma + 30 nap → "due_soon" (hamarosan lejár)
     - due_date > ma + 30 nap → "not_due" (nem esedékes)
     - due_date ures → "unknown"
  3. Opcionalis: bank CSV osszevetes (NEM implementalandó most, csak interface stub)
  4. Output: { invoice_number, due_date, amount, payment_status, days_until_due, is_overdue }

Adapter definicio:
  service_name = "payment_status"
  method_name = "check"
  input_schema = PaymentStatusInput
  output_schema = PaymentStatusOutput

FONTOS: Ez NEM használ service-t (nincs PaymentStatusService)!
  Ehelyett a logika TELJESEN az adapter-ben van (datum szamitas).
  A _get_service() NotImplementedError-t dob, mert nincs szukseg service-re.
  A _run() kozvetlenul szamol.

Prompt (UJ):
  skills/invoice_finder/prompts/invoice_payment_status.yaml
  - Stub prompt (B3.5-ben lesz erdemben hasznalva)
  - Input: invoice_number, due_date, amount
  - Output: { payment_status, days_until_due, confidence }

Unit tesztek (5):
  test_payment_status_overdue()       — lejart szamla → "overdue"
  test_payment_status_due_soon()      — 30 napon beluli → "due_soon"
  test_payment_status_not_due()       — 30 nap utan → "not_due"
  test_payment_status_unknown_date()  — ures datum → "unknown"
  test_payment_status_adapter_output() — adapter output Pydantic validacio
```

#### LEPES 3: Report Generator Adapter (Step 7 — UJ fajl!)

```
Hol: src/aiflow/pipeline/adapters/report_generator_adapter.py (UJ fajl)

Logika:
  1. Input: invoices lista (extracted), payment_statuses, file_paths
  2. Markdown riport generalas:
     - Fejlec: "Invoice Finder Report — {datum}"
     - Osszefoglalo: ossz szamla, fizetetlen, lejart, ossz osszeg
     - Reszletes tablazat: szamla szam | kiallito | osszeg | hatarido | statusz
  3. CSV export: invoices.csv (szamla fejlec mezok + payment status)
  4. Output: { report_markdown, report_path, csv_path, summary }

Adapter definicio:
  service_name = "report_generator"
  method_name = "generate"
  input_schema = ReportGeneratorInput
  output_schema = ReportGeneratorOutput

FONTOS: Ez sem használ service-t — a logika az adapter-ben van.
  Markdown string generalas + CSV iras fajlba.

Prompt (UJ):
  skills/invoice_finder/prompts/invoice_report_generator.yaml
  - Input: invoices JSON, payment_statuses JSON
  - Output: Markdown formátumo riport
  - Template-bol generalodik (nem LLM, hanem Jinja2 template)

Unit tesztek (5):
  test_report_markdown_structure()     — van fejlec, tablazat, osszefoglalo
  test_report_csv_generation()         — CSV tartalom helyes oszlopokkal
  test_report_summary_calculation()    — szamla szamok, osszegek helyesek
  test_report_empty_input()            — ures invoice lista → "No invoices found"
  test_report_payment_status_display() — lejart/due_soon/not_due megjelenes
```

#### LEPES 4: Notification Template (Step 8)

```
Hol: skills/invoice_finder/prompts/invoice_report_notification.yaml (UJ)

Jinja2 email template az Invoice Finder riporthoz:
  - Subject: "AIFlow Invoice Finder Report — {{ date }} — {{ total_invoices }} invoices"
  - Body: HTML email Jinja2 template
    - Osszefoglalo szamok (szamlak, lejart, due_soon, ossz osszeg)
    - Top 5 lejart szamla lista
    - Link a teljes riporthoz
  - Csatolmany: invoices.csv

Meglevo minta: prompts/notifications/invoice_processed.yaml

Unit tesztek (2):
  test_notification_template_yaml_valid()  — YAML parse + template kulcsok
  test_notification_template_renders()     — Jinja2 render valos adatokkal
```

### Teszt Fajl Struktura (UJ fajlok)

```
tests/unit/pipeline/
  test_invoice_field_extractor.py     — prompt YAML validacio (3 test)
  test_payment_status_adapter.py      — payment status adapter (5 test)
  test_report_generator_adapter.py    — report generator adapter (5 test)
  test_invoice_notification.py        — notification template (2 test)

Osszesen: 15 unit test (4 fajl)
```

---

## VEGREHAJTAS SORRENDJE

```
--- LEPES 1: Invoice Field Extractor prompt ---
/dev-step "B3.2.1 — invoice_field_extractor.yaml prompt + 3 teszt"
  - skills/invoice_finder/prompts/invoice_field_extractor.yaml
  - Prompt YAML validacios tesztek (3 test)

--- LEPES 2: Payment Status adapter ---
/dev-step "B3.2.2 — PaymentStatusAdapter + invoice_payment_status.yaml + 5 teszt"
  - src/aiflow/pipeline/adapters/payment_status_adapter.py (UJ fajl)
  - skills/invoice_finder/prompts/invoice_payment_status.yaml
  - PaymentStatusInput/Output Pydantic modellek
  - 5 unit test

--- LEPES 3: Report Generator adapter ---
/dev-step "B3.2.3 — ReportGeneratorAdapter + report template + 5 teszt"
  - src/aiflow/pipeline/adapters/report_generator_adapter.py (UJ fajl)
  - skills/invoice_finder/prompts/invoice_report_generator.yaml
  - ReportGeneratorInput/Output Pydantic modellek
  - 5 unit test (Markdown + CSV)

--- LEPES 4: Notification template + Invoice Finder models bovites ---
/dev-step "B3.2.4 — invoice_report_notification.yaml + model bovites + 2 teszt"
  - skills/invoice_finder/prompts/invoice_report_notification.yaml
  - skills/invoice_finder/models/__init__.py bovites (PaymentStatus, ReportResult Pydantic modellek)
  - 2 unit test

--- SESSION LEZARAS ---
/lint-check → 0 error
/regression → ALL PASS (1336 + 15 = 1351+ unit test)
/update-plan → 58 progress B3.2 DONE
```

---

## KORNYEZET ELLENORZES

```bash
git branch --show-current                                    # → feature/v1.3.0-service-excellence
git log --oneline -3                                         # → 372e08b, 966149e, d94d956
python -m pytest tests/unit/pipeline/test_invoice_finder_v3.py tests/unit/pipeline/test_invoice_email_search.py tests/unit/pipeline/test_invoice_doc_acquire.py tests/unit/pipeline/test_invoice_classifier.py -q 2>&1 | tail -1
                                                              # → 29 passed
.venv/Scripts/ruff check src/ tests/ 2>&1 | tail -1          # → All checks passed!
ls src/aiflow/pipeline/builtin_templates/*.yaml | wc -l       # → 7 template
ls src/aiflow/pipeline/adapters/*.py | wc -l                  # → 19 adapter
ls skills/invoice_finder/prompts/*.yaml | wc -l               # → 2 prompt (B3.1)
```

---

## S25 TANULSAGAI (alkalmazando S26-ban!)

1. **Adapter minta bevallt** — `_run()` metodus + Pydantic I/O + `adapter_registry.register()` pattern jol mukodik
2. **`re` import + ruff** — ruff automatikusan torli a nem hasznalt importot; ha modulszintu `re.compile` kell, `# noqa: I001` komment szukseges
3. **Scoring fuggveny kulon** — a `_score_email_for_invoice()` es `_compute_quality_score()` kulon fuggvenyek lettek (nem adapter metodus) → jol tesztelhetok
4. **Service nelkuli adapter** — a `DocumentAcquireAdapter` peldaja: nem mindig kell service DI, neha az adapter maga szamol
5. **29 teszt > 15 minimum** — tobb teszt irhato egyszeruen, ne csak a minimumot csinald
6. **Pre-existing test failure** — `test_rerank_fallback` HuggingFace model letoltes hiba NEM regresszio, ignore-olhato

---

## SPRINT B UTEMTERV

```
S19: B0   — DONE (4b09aad) — 5-layer arch + qbpp + prompt API + OpenAPI
S20: B1.1 — DONE (f6670a1) — 4 LLM guardrail prompt + llm_guards.py + 27 promptfoo
S21: B1.2 — DONE (7cec90b) — 5 guardrails.yaml + PIIMaskingMode + 31 teszt
S22: B2.1 — DONE (51ce1bf) — Core infra service tesztek (65 test, Tier 1)
S23: B2.2 — DONE (62e829b) — v1.2.0 service tesztek (65 test, Tier 2)
S24: B3.1 — DONE (372e08b) — Invoice Finder pipeline + email search + doc acquire (29 test)
S25: B3.2 ← JELEN SESSION — Invoice Finder: extract + payment + report + notification
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
- **MEGLEVO adapter-ek HASZNALATA** — Step 4, 6, 8 MAR LETEZIK! NE ird ujra!
- **2 UJ adapter fajl KELL** — payment_status_adapter.py + report_generator_adapter.py
- **3 UJ prompt YAML** — invoice_field_extractor, invoice_payment_status, invoice_report_generator
- **1 UJ notification template** — invoice_report_notification.yaml
- **Prompt YAML formatum** — PromptDefinition format (name, version, system, user, config, metadata)
- **Async-first** — minden I/O async (await)
- **Fajlnev konvencio:** adapter `*_adapter.py`, tesztek `test_invoice_*.py`, promptok `invoice_*.yaml`
- **Service nelkuli adapter OK** — PaymentStatus + ReportGenerator adapter-ek NEM hasznal service-t, a logika az adapter-ben van

---

## B3.2 GATE CHECKLIST

```
[ ] invoice_field_extractor.yaml prompt letezik (HU/EN mezo definiciokkal)
[ ] invoice_payment_status.yaml prompt letezik
[ ] invoice_report_generator.yaml prompt letezik
[ ] invoice_report_notification.yaml notification template letezik
[ ] payment_status_adapter.py UJ adapter fajl (PaymentStatusAdapter + PaymentStatusInput/Output)
[ ] report_generator_adapter.py UJ adapter fajl (ReportGeneratorAdapter + ReportGeneratorInput/Output)
[ ] skills/invoice_finder/models/__init__.py bovitve (PaymentStatus, ReportResult modellek)
[ ] 15 unit test PASS (4 fajl)
[ ] /lint-check → 0 error
[ ] /regression → ALL PASS (1351+ unit test)
[ ] Nincs regresszio a meglevo tesztekben
```

---

## MEGLEVO KOD REFERENCIAK (olvasd el mielott irsz!)

```
# Pipeline YAML (B3.1-bol — mar van 8 step definicio):
src/aiflow/pipeline/builtin_templates/invoice_finder_v3.yaml

# B3.1 adapterek (BOVITVE, nem ujrairando):
src/aiflow/pipeline/adapters/email_adapter.py        — EmailSearchInvoicesAdapter (step 1)
src/aiflow/pipeline/adapters/document_adapter.py     — DocumentAcquireAdapter (step 2)

# Meglevo adapterek (HASZNALANDO, nem modositando):
src/aiflow/pipeline/adapters/document_adapter.py     — DocumentExtractAdapter (step 4)
src/aiflow/pipeline/adapters/classifier_adapter.py   — ClassifierAdapter (step 3)
src/aiflow/pipeline/adapters/data_router_adapter.py  — DataRouterRouteAdapter (step 6)
src/aiflow/pipeline/adapters/notification_adapter.py — NotificationSendAdapter (step 8)

# Adapter minta (uj adapter irasahoz):
src/aiflow/pipeline/adapters/email_adapter.py        — EmailSearchInvoicesAdapter minta (service nelkuli)
src/aiflow/pipeline/adapter_base.py                  — BaseAdapter, adapter_registry

# Prompt YAML minta:
skills/invoice_finder/prompts/invoice_classifier.yaml           — B3.1-bol
skills/invoice_processor/prompts/invoice_header_extractor.yaml  — regi, de jo minta

# Notification template minta:
prompts/notifications/invoice_processed.yaml

# Invoice modellek:
skills/invoice_processor/models/__init__.py    — InvoiceHeader, LineItem, ProcessedInvoice
skills/invoice_finder/models/__init__.py       — InvoiceEmailResult, AcquiredDocument (B3.1)

# Teszt minta:
tests/unit/pipeline/test_invoice_finder_v3.py       — pipeline YAML validacio minta
tests/unit/pipeline/test_invoice_email_search.py    — adapter teszt minta (mock service)
tests/unit/pipeline/test_invoice_doc_acquire.py     — adapter teszt minta (quality score)
```
