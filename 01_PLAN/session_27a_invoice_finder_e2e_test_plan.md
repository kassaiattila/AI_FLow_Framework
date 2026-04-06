# AIFlow — Invoice Finder E2E Test Plan (B3.E2E)

> **Datum:** 2026-04-06
> **Branch:** `feature/v1.3.0-service-excellence` | **HEAD:** `b551607`
> **Cel:** A B3.1 + B3.2-ben megirt Invoice Finder pipeline valos adatokkal valo tesztelese
> **Pozicio:** B3.2 DONE → **B3.E2E (extra session)** → B3.5 folytatodik utana

---

## 1. MIERT KELL EZ?

A B3.1 (29 unit test) + B3.2 (16 unit test) = 45 unit teszt mind MOCK-olt.
Az adapterek, promptok, modellek onmagukban jol mukonek — de:

- **Soha nem futott vegig a 8-step pipeline egyetlen valos dokumentummal sem**
- A `PipelineRunner.run_from_yaml()` nem hivta meg a teljes lancot
- A Docling parser NEM telepitett (ImportError) — fallback pypdfium2 VAN
- Az email connector valos IMAP-pal nem volt tesztelve ebben a pipeline-ban
- LLM promptok (classifier, field_extractor) valos szamla szoveggel nem futottak

**Kockazat:** Ha a B3.5 confidence scoring-ot epitem ra valos adat tesztelese nelkul,
a kalibracios szamok ertelmetlenek lesznek.

---

## 2. INFRASTRUKTURA AUDIT

### Ami VAN (kesz, mukodik)

| Komponens | Allapot | Megjegyzes |
|-----------|---------|------------|
| PostgreSQL | Docker-bol | Port 5433, pgvector, 46 tabla |
| Redis | Docker-bol | Port 6379, volatile-lru |
| FastAPI backend | .venv-bol | Port 8102, `make api` |
| PipelineRunner | Kesz | `run()` + `run_from_yaml()`, DB persist, Langfuse |
| API endpoint | Kesz | `POST /api/v1/pipelines/{id}/run` |
| Adapter registry | Kesz | 21 adapter, auto-discovery |
| pypdfium2 | Telepitve | Fallback PDF parser (docling nelkul is mukodik) |
| litellm | Telepitve | OpenAI GPT-4o + GPT-4o-mini hivasa |
| Azure DI | Konfiguralt | .env-ben endpoint + API key, `azure_di_enabled: true` |
| IMAP | Konfiguralt | .env-ben IMAP_SERVER + credentials |
| Teszt szamlak (PDF) | 33 db | `data/uploads/invoices/` — magyar, valos szamlak |
| Teszt emailek (.eml) | 20+ db | `test_emails/bestix_real/` — valos mailbox export |
| HumanReviewService | Kesz | PostgreSQL-backed review queue |

### Ami HIANYZIK (teendo)

| Komponens | Problema | Megoldas |
|-----------|---------|----------|
| Docling | `ModuleNotFoundError: No module named 'docling'` | Vagy telepites (`uv add docling`), VAGY pypdfium2 fallback — dokling NEM blokkoló |
| AIFlow Docker Compose | AIFlow sajat PostgreSQL + Redis NEM fut | `docker compose up db redis -d` |
| Email connector config | Nincs `email_connector_configs` DB rekord | INSERT teszt config (IMAP credentials) |
| Pipeline definition | `invoice_finder_v3` nincs DB-ben | POST /api/v1/pipelines (YAML upload) |
| Output directory | `./data/invoices/` nem letezhet | `mkdir -p data/invoices` |

---

## 3. TESZTELESI STRATEGIA — 3 SZINT

### 3.1 Szint: Offline Pipeline Test (NEM kell email, NEM kell Docker)

> **Cel:** A pipeline lancot tesztelni **helyi PDF fajlokkal**, email nelkul.
> **Ideigenes:** Step 1-2 (email search + acquire) SKIPPELVE, step 3-8 valos adattal.

```
Input: 3-5 PDF szamla a data/uploads/invoices/ mappabol
Folyamat:
  1. pypdfium2-vel parse-olas (text kinyeres)
  2. LLM classifier (invoice_classifier.yaml prompt, valos GPT-4o-mini hivas)
  3. LLM field extraction (invoice_field_extractor.yaml prompt, valos GPT-4o hivas)
  4. Payment status szamitas (date-based, lejart/due_soon/not_due)
  5. Report generalas (Markdown + CSV)
  6. Notification template rendereles (nem kuldes, csak render)

Validalas:
  - Classifier: is_invoice=True, confidence > 0.7
  - Extraction: invoice_number, vendor_name, amount nem ures
  - Adoszam formatum: XXXXXXXX-X-XX
  - Osszeg: > 0
  - Report: Markdown + CSV letezik, tartalom helyes
  - Teljes lanc hiba nelkul lefut

Teszt fajl: tests/e2e/test_invoice_finder_offline.py
Futtatas: python -m pytest tests/e2e/test_invoice_finder_offline.py -v
Szukseges: OpenAI API key (.env), pypdfium2 (telepitve)
```

### 3.2 Szint: Pipeline Runner Integration (Docker PostgreSQL + Redis kell)

> **Cel:** A `PipelineRunner.run_from_yaml()` teljes futasa valos adattal.
> **Hatralevo step-ek valos service-ekkel.**

```
Elofeltetel:
  docker compose up db redis -d    # PostgreSQL 5433, Redis 6379
  alembic upgrade head             # DB migracio

Input: invoice_finder_v3.yaml YAML + 3 PDF fajl utvonala
Folyamat:
  PipelineRunner.run_from_yaml(yaml, input_data={...})
  - workflow_runs rekord letrejot DB-ben
  - step_runs rekord MINDEN step-hez
  - cost_records (LLM koltseg) rogzitve

Validalas:
  - PipelineRunResult.status == "completed"
  - Minden step_output nem ures
  - workflow_runs tabla: status="completed"
  - step_runs tabla: 8 rekord, mind "completed"
  - Langfuse trace letezik (ha konfiguralt)

Teszt fajl: tests/e2e/test_invoice_finder_pipeline.py
Futtatas: python -m pytest tests/e2e/test_invoice_finder_pipeline.py -v
Szukseges: Docker (PostgreSQL, Redis), OpenAI API key, alembic migrate
```

### 3.3 Szint: Full E2E with Email (valos IMAP + LLM + DB)

> **Cel:** Teljes 8-step pipeline, valos mailbox-bol indulva.
> **Ez a "vegso" teszt — ha ez atment, a pipeline production-ready.**

```
Elofeltetel:
  docker compose up db redis -d
  alembic upgrade head
  Email connector config DB-ben (IMAP credentials)
  Valos postaladaban 2-3 szamla PDF csatolmanyos email

Input: POST /api/v1/pipelines/{id}/run { connector_id, days: 30, limit: 10 }
Folyamat:
  Step 1: IMAP mailbox scan (valos email fetch)
  Step 2: Csatolmany letoltes + parse
  Step 3: LLM classifier
  Step 4: LLM field extraction
  Step 5: Payment status
  Step 6: File organization
  Step 7: Report generation
  Step 8: Notification (template render, email kuldes opcionalis)

Validalas:
  - API response: 202 Accepted, run_id
  - GET /api/v1/pipelines/{id}/runs/{run_id}: status="completed"
  - Kinyert szamla adatok helyesek (manualis ellenorzes 1-2 szamlara)
  - Report + CSV letezik
  - DB: workflow_runs + step_runs + cost_records

Teszt: Manualis (curl/httpie) VAGY tests/e2e/test_invoice_finder_full.py
Szukseges: Docker, OpenAI, IMAP access, valos szamla email-ek
```

---

## 4. KONKRET VEGREHAJTAS TERV

### Fázis 1: Kígyózás nélkül (30 perc) — Offline teszt

```
LEPES 1: Elokeszites
  - Ellenorizd: OPENAI_API_KEY beallitva .env-ben
  - Valassz 3 PDF-et: data/uploads/invoices/ → 1 magyar digitalis, 1 magyar scan, 1 kulfoldi

LEPES 2: Offline teszt fajl irasa
  tests/e2e/test_invoice_finder_offline.py

  Teszt logika (PSZEUDO-KOD):
    pdf_path = "data/uploads/invoices/20210423_EdiMeron_Bestix_Szla_2021_08.pdf"

    # 1. Parse
    from aiflow.ingestion.parsers.docling_parser import DoclingParser
    parser = DoclingParser()
    try:
        doc = parser.parse(pdf_path)
    except ImportError:
        # Docling nincs → pypdfium2 fallback
        doc = parser._fallback_parse(Path(pdf_path), 0)

    assert len(doc.text) > 100  # van szoveg

    # 2. Classify (valos LLM hivas!)
    from skills.invoice_finder import prompt_manager, models_client
    prompt = prompt_manager.get("invoice_finder/classifier")
    response = await models_client.generate(
        prompt=prompt.render(raw_text=doc.text[:2000]),
        model="openai/gpt-4o-mini",
    )
    result = json.loads(response.content)
    assert result["is_invoice"] == True
    assert result["confidence"] > 0.5

    # 3. Extract (valos LLM hivas!)
    prompt = prompt_manager.get("invoice_finder/field_extractor")
    response = await models_client.generate(
        prompt=prompt.render(raw_text=doc.text),
        model="openai/gpt-4o",
    )
    fields = json.loads(response.content)
    assert fields["invoice_number"] != ""
    assert fields["vendor"]["name"] != ""

    # 4. Payment status
    from aiflow.pipeline.adapters.payment_status_adapter import _determine_payment_status
    status, days, overdue = _determine_payment_status(fields.get("due_date", ""))
    # Regi szamlak → "overdue" (elvárt!)

    # 5. Report
    from aiflow.pipeline.adapters.report_generator_adapter import (
        _build_report_items, _calculate_summary, _generate_markdown, _generate_csv
    )
    items = _build_report_items([{"fields": fields}], [{"payment_status": status}], [pdf_path])
    summary = _calculate_summary(items)
    markdown = _generate_markdown(items, summary)
    csv = _generate_csv(items)
    assert "Invoice Finder Report" in markdown
    assert fields["invoice_number"] in csv

LEPES 3: Futtatas + eredmenyek mentese
  python -m pytest tests/e2e/test_invoice_finder_offline.py -v -s
  # -s → LLM valaszok latszodnak a konzolban

LEPES 4: Eredmenyek kiertakelese
  - Classifier pontossag: 3/3 szamlat felismerte?
  - Extraction minoseg: invoice_number, vendor, amount kinyerve?
  - Payment status: regi szamlak "overdue"?
  - Report: Markdown olvasható, CSV helyes?
```

### Fázis 2: Pipeline Runner (1 ora) — DB integration

```
LEPES 1: Docker + DB
  docker compose up db redis -d
  alembic upgrade head
  # Varj amig healthy

LEPES 2: Pipeline regisztracio
  # API-n vagy kozvetlen DB INSERT-tel:
  # POST /api/v1/pipelines  body: { yaml_source: <invoice_finder_v3.yaml tartalma> }

LEPES 3: Modositott pipeline futtatás
  # Step 1-2 (email) SKIP — helyette direkt PDF input
  # PipelineRunner.run_from_yaml() custom input-tal

LEPES 4: DB ellenorzes
  SELECT * FROM workflow_runs ORDER BY created_at DESC LIMIT 1;
  SELECT * FROM step_runs WHERE workflow_run_id = '...' ORDER BY step_index;
  SELECT * FROM cost_records WHERE run_id = '...';
```

### Fázis 3: Full E2E with Email (30 perc) — OPCIONALIS

```
LEPES 1: Email connector config
  INSERT INTO email_connector_configs (id, name, provider, config_json) VALUES (
    'cfg-bestix-imap', 'BestIx IMAP', 'imap',
    '{"server": "outlook.office365.com", "email": "...", "password": "..."}'
  );

LEPES 2: Kuldj 2-3 szamla PDF-et a teszt mailbox-ba (csatolmanykent)

LEPES 3: Pipeline futtatás API-n:
  POST /api/v1/pipelines/{id}/run
  { "input_data": { "connector_id": "cfg-bestix-imap", "days": 7, "limit": 5 } }

LEPES 4: Eredmenyek ellenorzese (API + DB + riport fajlok)
```

---

## 5. TESZT ADATOK

### Ajanlott PDF-ek (data/uploads/invoices/)

| # | Fajl | Tipus | Miert |
|---|------|-------|-------|
| 1 | `20210423_EdiMeron_Bestix_Szla_2021_08.pdf` | Magyar, digitalis | Standard HU szamla |
| 2 | `20210423_Kacz_Levente_KL-2021-4.pdf` | Magyar, digitalis | Egyeni vallalkozo szamla |
| 3 | `20210615_CSEPP_Studio_E-CSEPP-2021-6.pdf` | Magyar, digitalis | Kft. szamla |
| 4 | `20210302_MS_licenc_E0800DTP68_202103.pdf` | Kulfoldi (MS) | Nem-magyar szamla |
| 5 | `20210108_BestIx_Logosz_Székhely_szolgáltatás_SZÁMLA_20210108.pdf` | Magyar, szolgaltatas | Szekhelyszolgaltatas |

### Valos email teszt (gepjarmundo)

```
test_emails/bestix_real/attachments/
  20260325_gépjárműadó 04_15-ig_8385113444_7787817713_gepjarmuado_KA.pdf
→ Ez a EGYETLEN valos PDF csatolmany az email exportban (gépjárműadó fizetési értesítő)
```

---

## 6. SIKER KRITERIUMOK

### Fázis 1 (Offline) — MINIMUM

```
[  ] 3/3 PDF sikeresen parse-olva (pypdfium2 fallback OK)
[  ] 3/3 PDF helyesen klassifikalva (is_invoice=True, confidence > 0.5)
[  ] 3/3 PDF-bol invoice_number kinyerve (nem ures string)
[  ] 3/3 PDF-bol vendor name kinyerve
[  ] 3/3 PDF-bol amount kinyerve (> 0)
[  ] Payment status helyes (2021-es szamlak → "overdue")
[  ] Report Markdown + CSV generalva
[  ] Teljes lanc hiba nelkul lefut
[  ] LLM koltseg < $0.50 (3 szamla × 2 LLM hivas)
```

### Fázis 2 (Pipeline Runner) — TELJES

```
[  ] PipelineRunResult.status == "completed"
[  ] workflow_runs DB rekord: status="completed"
[  ] step_runs: 6+ rekord (step 3-8), mind "completed"
[  ] cost_records: LLM koltseg rogzitve
[  ] Report fajl letezik: data/invoices/invoice_finder_report.md
[  ] CSV fajl letezik: data/invoices/invoices.csv
```

### Fázis 3 (Full E2E) — BONUSZ

```
[  ] Email fetch: IMAP kapcsolat sikeres
[  ] Csatolmany letoltes: PDF fajl mentve
[  ] Teljes 8-step pipeline vegigfut
[  ] API response: run_id + status
```

---

## 7. DOCLING STRATEGIA

A docling NEM telepitett, de ez **NEM blokkoló**:

```
OPCIO A (gyors, pragmatikus):
  pypdfium2 fallback MUKODIK — digitalis PDF-ekhez eleg jo.
  DoclingParser._fallback_parse() automatikusan aktivizalodik ImportError eseten.
  → Nem kell semmit telepiteni, indulhatunk ROGTÖN.

OPCIO B (jobb minoseg):
  uv add docling
  → Jobb table extraction, layout analysis, de LASSU telepites + nagy dependency.
  → Scan/keziras szamlakhoz tenylegesen jobb.

OPCIO C (legjobb production):
  pypdfium2 primary + Azure DI fallback (ha quality < 0.5)
  → Koltsegoptimalizalt, legjobb minoseg scan-ekhez
  → skill_config.yaml: azure_di_enabled: true (MAR BEALLITVA!)

AJANLÁS: Fázis 1-ben OPCIO A (pypdfium2), ha minoseg nem eleg → Fázis 2-ben OPCIO C.
```

---

## 8. KOCKAZATOK ES MITIGATION

| Kockazat | Valoszinuseg | Hatas | Mitigation |
|----------|-------------|-------|------------|
| OpenAI API key lejart/limit | Alacsony | Blokkoló | Ellenorizd: `litellm.completion(model="gpt-4o-mini", messages=[{"role":"user","content":"test"}])` |
| pypdfium2 rossz szoveg minoseg | Kozepes | Rossz extraction | Azure DI fallback VAGY docling telepites |
| Regi 2021-es szamlak format eltero | Alacsony | Hibas extraction | Tobb szamla tesztelese, prompt tuning ha kell |
| Docker PostgreSQL nem indul | Alacsony | Fazis 2 blokkolt | `docker compose up db redis -d` + `docker compose logs db` |
| Pipeline adapter registracio hiba | Alacsony | Runtime error | `adapter_registry.discover()` + `adapter_registry.list_adapters()` |
| IMAP credentials expired | Kozepes | Fazis 3 blokkolt | Ellenorizd: telnet outlook.office365.com 993 |

---

## 9. IDOBECSLES

```
Fázis 1 (Offline):    ~45 perc (teszt iras + 3 PDF futtas + eredmeny kiertekeles)
Fázis 2 (Runner):     ~60 perc (Docker + DB + pipeline regisztracio + futtas + DB check)
Fázis 3 (Full E2E):   ~30 perc (email config + mailbox + API futtas)

Összesen:              ~2-2.5 ora (Fázis 1 kotelezp, Fázis 2 erosen ajanlott, Fázis 3 opcionalis)
```

---

## 10. KAPCSOLAT A SPRINT B UTEMEZESSEL

```
Eredeti utemterv:
  S26: B3.5 — Confidence scoring hardening
  S27: B4.1 — Skill hardening

Modositott utemterv (E2E betoldva):
  S26: B3.2 — DONE (aecce10)
  S26+: B3.E2E — Invoice Finder valós E2E teszt ← JELEN PLAN
  S27: B3.5 — Confidence scoring (az E2E tapasztalatok informaljak a kalibraciót!)
  S28: B4.1 — Skill hardening

Indok: A B3.5 confidence kalibracioja ERTELMETELEN valos adat teszt nelkul.
Az E2E teszt adja az "actual accuracy" ertekeket amihez a confidence-t kalibraljuk.
```
