# Invoice Processor Skill - Terv

## Context

BestIx Kft szamlai (`02_Szamlak/`) PDF formátumban vannak tarolva:
- **Bejovo (incoming):** Beszallitoi szamlak (MS licencek, alvalallozok, szolgaltatasok)
  - 2021: 29 PDF, 2022-2026: tovabbi evek
- **Kimeno (outgoing):** Ugyfeleknek kiallitott szamlak (Ecory, Field, Stratis)
  - 41 PDF osszesen (BD001-BD022, BESE001-BESE0019)

**Cel:** Uj AIFlow skill ami PDF szamlakat olvas be, kinyeri a strukturalt adatokat (szallito, vevo, tetelek, osszegek, AFA), validalja, es adatbazisban/tablazatban tarolja.

---

## Pipeline (6 step)

```
parse_invoice → classify_invoice → extract_invoice_data → validate_invoice → store_invoice → export_invoice
```

### Step 1: parse_invoice
- DoclingParser PDF extractalas (szoveg + tablak)
- Quality score < 0.5 → Azure DI fallback (mar implementalt)
- Batch mod: mappa osszes PDF-je

### Step 2: classify_invoice
- Heurisztika eloszor: konyvtar nev (Bejovo/Kimeno), fajlnev minta
- LLM fallback: BestIx mint szallito (kimeno) vs vevo (bejovo)
- Cost-optimalizalt: LLM csak ha heurisztika bizonytalan

### Step 3: extract_invoice_data (KET LLM hivas)
1. **Header extractalas** (gpt-4o): szallito, vevo, szamlaszam, datumok, fizetesi mod
2. **Tetel extractalas** (gpt-4o): tetelek tablazat + osszesito + AFA

### Step 4: validate_invoice (Python, NEM LLM)
- Tetelek osszegenek ellenorzese vs osszesito
- AFA szamitas ellenorzes (netto * kulcs = AFA osszeg)
- Brutto = Netto + AFA per tetel es osszesen
- Adoszam formatum regex: `^\d{8}-\d-\d{2}$`
- Kotelezomezok: szamlaszam, szallito nev, vevo nev, min 1 tetel
- Ha validacio hibas → opcionalis LLM korrekcios hivas

### Step 5: store_invoice
- PostgreSQL INSERT (asyncpg, best-effort)
- invoices tabla + invoice_line_items tabla
- SHA256 dedup (source_file + raw_text_hash unique index)

### Step 6: export_invoice
- CSV: 1 sor = 1 tetel (denormalizalt fejlec mezoekkel)
- Excel: 2 sheet (Osszesito + Tetelek) - openpyxl
- JSON: teljes ProcessedInvoice

---

## Pydantic modellek

| Model | Mezok |
|-------|-------|
| InvoiceParty | name, address, tax_number, bank_account, bank_name |
| InvoiceHeader | invoice_number, invoice_date, fulfillment_date, due_date, currency, payment_method, invoice_type |
| LineItem | line_number, description, quantity, unit, unit_price, net_amount, vat_rate, vat_amount, gross_amount |
| VatSummaryLine | vat_rate, net_amount, vat_amount, gross_amount |
| InvoiceTotals | net_total, vat_total, gross_total, vat_summary[], rounding_amount |
| InvoiceValidation | is_valid, errors[], warnings[], confidence_score |
| ProcessedInvoice | source_file, direction, vendor, buyer, header, line_items[], totals, validation |
| InvoiceBatchResult | total_files, processed, failed, invoices[] |

---

## Adatbazis tablak (Alembic 014)

### invoices
- id (UUID PK), direction, source_file
- vendor_name, vendor_address, vendor_tax_number, vendor_bank_account
- buyer_name, buyer_address, buyer_tax_number
- invoice_number, invoice_date, fulfillment_date, due_date
- currency, payment_method, invoice_type
- net_total, vat_total, gross_total (Numeric 15,2)
- vat_summary (JSONB), is_valid, validation_errors (JSONB)
- confidence_score, parser_used, raw_text_hash (SHA256 dedup)
- customer, created_at, updated_at

### invoice_line_items
- id (UUID PK), invoice_id (FK → invoices ON DELETE CASCADE)
- line_number, description, quantity, unit, unit_price
- net_amount, vat_rate, vat_amount, gross_amount (Numeric)

---

## CLI

```bash
# Szamlak feldolgozasa
python -m skills.invoice_processor ingest --source "./Szamlak/Bejovo/2021/" --direction incoming
python -m skills.invoice_processor ingest --source "./Szamlak/Kimeno/" --direction outgoing
python -m skills.invoice_processor ingest --source "./Szamlak/" --direction auto

# Lekerdezes
python -m skills.invoice_processor query --vendor "Microsoft" --year 2021
python -m skills.invoice_processor query --direction incoming --from-date 2021-01-01

# Exportalas
python -m skills.invoice_processor export --year 2021 --output ./export/ --format excel
```

---

## Fajl struktura

```
skills/invoice_processor/
  __init__.py, __main__.py, skill.yaml, skill_config.yaml, workflow.py
  models/__init__.py
  workflows/process.py          # 6 step
  prompts/
    invoice_classifier.yaml
    invoice_header_extractor.yaml
    invoice_line_extractor.yaml
    invoice_validator.yaml
  tests/
    test_workflow.py
    datasets/sample_incoming.json, sample_outgoing.json

alembic/versions/014_add_invoice_tables.py
```

---

## Ujrafelhasznalt infrastruktura

| Komponens | Fajl | Hasznalat |
|-----------|------|-----------|
| DoclingParser | src/aiflow/ingestion/parsers/docling_parser.py | PDF szoveg + tabla extractalas |
| AttachmentProcessor | src/aiflow/tools/attachment_processor.py | Quality routing (Docling → Azure DI) |
| ModelClient + LiteLLM | src/aiflow/models/ | LLM hivasok |
| PromptManager | src/aiflow/prompts/manager.py | YAML prompt betoltes |
| @step + SkillRunner | src/aiflow/engine/ | Workflow vezerles |
| asyncpg | query.py minta | DB INSERT |

---

## Becsult munka: ~16 ora (2 munkanap)

| Fazis | Ido | Tartalom |
|-------|-----|----------|
| 1: Alapok | 4h | Modellek, skill.yaml, Alembic migracio |
| 2: Core pipeline | 6h | 4 prompt + parse/classify/extract/validate stepek |
| 3: Perzisztencia + export | 3h | store + export stepek, CLI |
| 4: Tesztek + finom hangolas | 3h | Unit tesztek, valos PDF-eken hangolas |

---

## Kockazatok

| Kockazat | Mitgacio |
|----------|----------|
| Szamla formatum valtozatos (kulonbozo szallitok) | 4 prompt finomhangolas valos mintan |
| Tablazat extractalas hibas | Docling markdown tabla + LLM ertelmezes kombinacio |
| Magyar szam formatum (1 234 567,89) | LLM prompt explicit utasitas + Python post-processzalas |
| Szkennelt PDF (kep alapu) | Quality score → Azure DI OCR fallback (mar implementalt) |
