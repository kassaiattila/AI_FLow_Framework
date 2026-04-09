# AIFlow Sprint B — Session 29 Prompt (B4.2: Skill Hardening — process_documentation + invoice_processor + cubix_course_capture + invoice_finder)

> **Datum:** 2026-04-09
> **Branch:** `feature/v1.3.0-service-excellence` | **HEAD:** `9eb2769`
> **Port:** API 8102, Frontend 5174
> **Elozo session:** S28 — B4.1 DONE (aszf_rag 12/12 + email_intent 16/16 promptfoo, promptfoo Windows infra fix, +9 tests, 0 regressions on 1424 unit)
> **Terv:** `01_PLAN/58_POST_SPRINT_HARDENING_PLAN.md` (B4.2 row, sor 1949+)

---

## KONTEXTUS

### S28 Eredmenyek (B4.1 — DONE, commit `9eb2769`)

**aszf_rag_chat (role=expert promptok):**
- `system_prompt_{baseline,expert,mentor}.yaml` v1.1 — kotelezo `[N]` citation enforcement + grounded refusal + few-shot pelda. Temperature 0.3 → 0.2.
- `hallucination_detector.yaml` v1.1 — per-claim grounded/ungrounded breakdown + refusal fast-path (`{score, claims, hallucinated_claims, summary}`).
- `citation_extractor.yaml` v1.1 — strict `[N]` → Citation JSON schema mapping.
- `query.py` — JSON parser fix: dict / scalar / plain-text fallback (3 formatum), modul-szintu `import json`, hallucinated_claims az output dict-ben.
- `guardrails.yaml` — `max_length 2000→4000`, `hallucination_threshold 0.7→0.9`, `llm_fallback.confidence 0.7→0.8`, scope.allowed_topics bovites.
- Promptfoo: 7 → 12 test, tolerans assertek (grounded VAGY safe refusal).
- **Eredmeny: 12/12 PASS (100%) > 95%-os gate**

**email_intent_processor:**
- `intent_classifier.yaml` v1.1 — intent katalogus 10 → 12 (`invoice_received` + `calendar_invite`), marketing vs notification hatarvonal financial-transaction signal alapjan.
- `entity_extractor.yaml` v1.1 — HU `tax_number` (XXXXXXXX-Y-ZZ) + `bank_account` (8-8 GIRO) + `postal_address` (4-component validation) regex + LLM hint + few-shot.
- `schemas/v1/intents.json` v1.2, `entities.json` v1.1.
- `guardrails.yaml` — `allowed_pii` bovitve `hu_tax_number` + `hu_bank_account` (mar a `InputGuard.PII_PATTERNS`-ben), `max_length 3000→4000`, extra injection patterns classifier-override-ra.
- Promptfoo: 12 → 16 test (invoice_received, calendar_invite, marketing_vs_notification, pure marketing).
- **Eredmeny: 16/16 PASS (100%) > 95%-os gate**

**Promptfoo Windows infra fix** (`scripts/promptfoo_provider.py`):
4 hiba javitva — baseline elotte 0/7 ERROR volt:
1. Path resolution: promptfoo a config-fajlhoz kepest oldja fel a script utat → `../../../scripts/promptfoo_provider.py` walk-up
2. argv contract: promptfoo `argv[1]=prompt, argv[2]=opts_json` — stdin fallback megtartva manual hasznalathoz
3. UTF-8 stdout: Windows cp1252 a Hungarian chars-okat osszetorte → `sys.stdout.reconfigure(encoding="utf-8")`
4. structlog noise: stdout-ra meno log-ok → pipe to stderr + WARNING level + `LITELLM_LOG=ERROR`

**Tesztek + minoseg (S28 vegen):**
- 1424/1424 unit test PASS
- 52/52 aszf_rag_chat workflow test PASS (4 hallucination parser regressziot is javitottam menet kozben)
- 129/129 guardrail test PASS
- ruff: All checks passed (src + tests + skills + scripts)

### Infrastruktura (v1.3.0 — S28 utan)

- 26 service | 165 API endpoint (25 router) | 46 DB tabla | 29 migracio
- 21 pipeline adapter | 7 pipeline template | 6 skill | 22 UI oldal
- **1424 unit test** | 129 guardrail teszt | 97 security teszt | 104 E2E | **54 promptfoo teszt** (mindossz., 5 skill-en)
- B4.1 utan ket skill PRODUCTION-READY: aszf_rag_chat + email_intent_processor

### Jelenlegi Skill Allapot (B4.2 AUDIT cel — 4 hatralevo skill)

```
=== SKILL STATUS TERKEP (B4.2 cel) ===

process_documentation (v1.0 — natural language → BPMN/Mermaid):

  Prompts (5 YAML, skills/process_documentation/prompts/):
    - classifier.yaml         — kategoria detektalas (process / question / off-topic)
    - elaborator.yaml         — input expansion (rovid leiras → reszletes folyamat)
    - extractor.yaml          — strukturalt BPMN extraction (tasks, decisions, edges)
    - mermaid_flowchart.yaml  — BPMN → Mermaid flowchart code render
    - reviewer.yaml           — output validacio + javitas javaslat

  Promptfoo: 10 test case (skills/process_documentation/tests/promptfooconfig.yaml)
  Guardrail: skills/process_documentation/guardrails.yaml (B1.2-bol, ON mode)
  Workflow: skills/process_documentation/workflow.py (single-file)
  Ismert gyenge pontok:
    - Decision diamond labeling: a `{...}` shape-bol kimaradnak a Yes/No-Igen/Nem cimkek
    - Parallel branches: nem mindig fork-jol, sokszor szekvencialissa lapitja
    - Mermaid syntax errors: nem-zart `[...]` shape-ek, escapelt karakterek
    - Off-topic refusal: classifier nem mindig dob "non_process" kategoriat

invoice_processor (v1.0 — PDF szamla → strukturalt JSON):

  Prompts (4 YAML, skills/invoice_processor/prompts/):
    - invoice_classifier.yaml      — invoice / credit_note / proforma kategoria
    - invoice_header_extractor.yaml — vendor + buyer + meta JSON extraction
    - invoice_line_extractor.yaml  — tetel sorok + VAT bontas
    - invoice_validator.yaml       — header + line items konzisztencia ellenorzes

  Promptfoo: 10 test case (skills/invoice_processor/tests/promptfooconfig.yaml)
  Guardrail: skills/invoice_processor/guardrails.yaml (B1.2-bol, OFF mode — szamlakon
             kell hogy lassuk a PII-t, de pii_logging=true az audit-hoz)
  Workflow: skills/invoice_processor/workflows/process.py
  Ismert gyenge pontok:
    - HU number formatting: `1.500.000 Ft` (pont mint ezres-elvalaszto) felresikerul
    - VAT rate detection: 27% / 18% / 5% / 0% / AAM (mentes) keverve felismeri
    - Multi-currency: HUF/EUR/USD egy szamlan belul kereszt-osszegzes
    - VAT-exempt (AAM): nem kezel `vat_rate=0` esetet helyesen
    - Multi-page: 2-3 oldalas szamla folytatott line items elvesznek

cubix_course_capture (v1.0 — Hungarian tech course transcript → struct):

  Prompts (1 YAML, skills/cubix_course_capture/prompts/):
    - transcript_structurer.yaml   — clean + sections + summary + vocabulary EGY promptban!

  Promptfoo: 6 test case (skills/cubix_course_capture/tests/promptfooconfig.yaml)
  Guardrail: skills/cubix_course_capture/guardrails.yaml (B1.2-bol, ON mode)
  Workflow: skills/cubix_course_capture/workflows/{course_capture,transcript_pipeline}.py
  Ismert gyenge pontok:
    - **Egyetlen prompt kezel mindent** (clean+sections+summary+vocab) — felelosseg
      keveredik, prompt sokat hibazik. EZ A FO HARDENING TEMA: bontsuk szet!
    - Mixed-language transcript (HU + EN tech kifejezesek): code-block nem stabil
    - Filler words: "ugye/hat/tehat" kiszuresenel a szakszavakat is kiszedi neha
    - Section timestamp: nem mindig adekvat (~10s pontossagra van szukseg, de
      sokszor az egesz transcriptet egy szekcionak veszi)

invoice_finder (v1.0 — B3.E2E + B3.5-bol — invoice keresest mailbox-bol):

  Prompts (6 YAML, skills/invoice_finder/prompts/):
    - invoice_classifier.yaml      — email → "is_invoice_candidate" boolean + reason
    - invoice_email_scanner.yaml   — mailbox traversal segito (subject + body summary)
    - invoice_field_extractor.yaml — email body / attachment → invoice fields
    - invoice_payment_status.yaml  — fizetesi statusz: paid / due / overdue
    - invoice_report_generator.yaml — talalt szamlak osszesito riport (markdown)
    - invoice_report_notification.yaml — notifikacios uzenet a felhasznalonak

  Promptfoo: **NINCS! 0 test case** (skills/invoice_finder/tests/promptfooconfig.yaml HIANYZIK!)
  Guardrail: skills/invoice_finder/guardrails.yaml (PARTIAL mode, B1.2-bol)
  Confidence: skills/invoice_finder/confidence_config.yaml (B3.5-bol, kalibralt)
  Workflow: NINCS dedicalt workflow.py — a pipeline B3-bol jon (invoice_finder_v3.yaml)
  Ismert gyenge pontok:
    - **Nincs promptfoo coverage egyaltalan** — ez a fo gap! Phase 0 mailbox adatokra
      kell uj test config-ot epiteni
    - Field extraction: HU vs EN szamla formatumok kevereden mukodnek
    - Payment status: a "due_date" parsing felresikerulhet (hu/en datum formatumok)
    - Report generator: markdown szintaxis hibak (# fejlec helyett `*`)
```

---

## B4.2 FELADAT: 4 Skill 95%+ Promptfoo + 8+/10 Service Hardening

> **Gate:** 4/4 skill 95%+ promptfoo pass rate, guardrails finomhangolva, 10-pont checklist 8+/10 mindegyikre
> **Cel:** ~24 uj promptfoo test case + 1 uj promptfooconfig (invoice_finder), prompt minoseg javitas valos trace alapjan
> **Eszkozok:** `/prompt-tuning`, `/service-hardening`, `/dev-step`, `/regression`

### Implementacios Lepesek

#### LEPES 1: process_documentation Mermaid + Decision + Refusal Hardening

```
Hol: skills/process_documentation/prompts/{classifier,extractor,mermaid_flowchart,reviewer}.yaml
     skills/process_documentation/tests/promptfooconfig.yaml (10 → 14)
     skills/process_documentation/guardrails.yaml (finomhangolas)

Cel 1 — Mermaid syntax stability: mermaid_flowchart.yaml strict shape mapping
        + few-shot a 4 alaptipusra (start, task, decision, end), parallel branches
Cel 2 — Decision label enforcement: minden `{...}` decision-bol minimum 2 kimeno
        labeled edge ("Yes"/"No" vagy "Igen"/"Nem")
Cel 3 — Off-topic refusal: classifier.yaml strictebben dobja non_process kategoriaba
        a kerdeseket es general csevegest ("hi, hello, what's up")

KONKRET TEENDOK:

1. Futtasd: npx promptfoo eval -c skills/process_documentation/tests/promptfooconfig.yaml
   - Jegyezz fel melyik tesztek bukknak
   - Varhato gyenge pontok: decision labels, parallel branches, off-topic

2. mermaid_flowchart.yaml javitas:
   - System prompt-ba: "MINDEN decision shape `{...}`-bol legalabb 2 kimeno
     edge kell labellel: pl. `A{Igen?} -->|Igen| B` es `A -->|Nem| C`"
   - Few-shot pelda hozzaadasa parallel branchre: `A --> B & C`
   - Strict shape mapping table a system promptban: start=`([...])`, task=`[...]`,
     decision=`{...}`, parallel_join=`(((...)))`
   - Temperature 0.3 → 0.1 (rendkivul determinisztikus kell)

3. classifier.yaml javitas:
   - System prompt: "Ha az input KERDES (mi/hogyan/miert?) NEM folyamat → category=question"
   - Ha tul rovid (<10 szo) es nem ir le folyamatot → category=non_process
   - Few-shot peldak: "Hi" → non_process, "Hogyan tudok belepni?" → question,
     "Az ugyfel beadja a karbejelentest, majd..." → process

4. extractor.yaml strictebb BPMN graph:
   - Output JSON schema: {"steps": [...], "edges": [...]}
   - Minden edge-en label mezo (uresen is, de jelen kell legyen)
   - Decision step type explicit jelolessel: `{"type": "decision", "outcomes": ["Igen", "Nem"]}`

5. reviewer.yaml — uj output validacio:
   - Bemenet: a generalt mermaid kod
   - Kimenet: {valid: bool, errors: [...], suggestions: [...]}
   - Ellenorzi: balanced brackets, decision label-ek megvannak, valid Mermaid syntax

6. 4 uj promptfoo test case (10 → 14):
   - test_decision_labels:        "Ha igen X, ha nem Y" → mindkettonek label
   - test_parallel_branches:      "Egyszerre fut A es B" → `&` parallel syntax
   - test_off_topic_refusal:      "Hello, hogy vagy?" → category=non_process VAGY refusal
   - test_complex_multi_step:     5+ lepeses folyamat → minden lepes szerepel
   - test_loop_back:              "Vissza ehhez a lepeshez" → ciklus edge

7. guardrails.yaml finomhangolas:
   - input.max_length: 4000 → 8000 (folyamat leirasok hosszuak lehetnek)
   - output.scope.dangerous_patterns: meglevok + "delete\\s+all\\s+steps"

8. Futtasd ujra: npx promptfoo eval → 14/14 PASS (95%+ = 14/14 vagy 13/14)

Gate: 95%+ pass rate, mermaid_flowchart few-shot + strict shape mapping, 14+ test
```

#### LEPES 2: invoice_processor HU Number + VAT + Multi-Currency

```
Hol: skills/invoice_processor/prompts/{invoice_header_extractor,invoice_line_extractor,invoice_validator}.yaml
     skills/invoice_processor/tests/promptfooconfig.yaml (10 → 14)
     skills/invoice_processor/guardrails.yaml (finomhangolas, OFF mode marad)

Cel 1 — HU thousands-separator: `1.500.000 Ft` HELYES parsolasa (NEM 1.5)
Cel 2 — VAT rate detection: 27%, 18%, 5%, 0%, AAM (mentes) felismerese
Cel 3 — Multi-currency edge case: HUF + EUR egy szamlan belul
Cel 4 — Multi-page: continuation marker `...` vagy "(folytatas)" kezelese

KONKRET TEENDOK:

1. Futtasd: npx promptfoo eval -c skills/invoice_processor/tests/promptfooconfig.yaml
   - Jegyezz fel melyik tesztek bukkok

2. invoice_header_extractor.yaml javitas:
   - "Hungarian numbers use period . as thousands separator and comma , as decimal:
     '1.500.000,50' = 1500000.50, NOT 1.5"
   - Few-shot pelda HU formatumokra: `123 456,78 Ft → 123456.78`
   - VAT rate input ESETBEN: ha "AAM" megjelenik → vat_rate=0, vat_status='exempt'
   - Currency detection: ha "EUR"/"€" jelen → currency='EUR', NEM HUF

3. invoice_line_extractor.yaml multi-currency + multi-page:
   - System prompt: "Ha az invoice tobb oldalas, kovesd a 'Folytatas' / 'Continued'
     marker-eket es egyesitsd az osszes line item-et"
   - Multi-currency: minden line itemnek lehet sajat currency-je (kulfoldi szamlak)
   - VAT-exempt jelolesek: "AAM" / "0%" / "Tax-free" → mind vat_rate=0

4. invoice_validator.yaml strictebb cross-check:
   - Sum(line_items.gross_amount) == header.total_gross (±0.01 toleranccia)
   - Sum(line_items.vat_amount) == header.total_vat
   - Ha HU adoszam: regex `\d{8}-\d-\d{2}` matchol
   - Output: {valid: bool, errors: [...], warnings: [...], discrepancies: {...}}

5. 4 uj promptfoo test case (10 → 14):
   - test_hu_thousands_separator: "1.500.000,50 Ft" → 1500000.50 (NOT 1.5)
   - test_vat_aam_exempt:         "AAM" jelolesu szamla → vat_rate=0, vat_status='exempt'
   - test_multi_currency:         szamla EUR + HUF tetelekkel → mindketto helyesen
   - test_multi_page_continuation: "(folytatas a kovetkezo oldalon)" → osszes tetel

6. guardrails.yaml — pii_logging audit aktiv (mar van), nincs masik valtoztatas
   (OFF mode kell mert PII benne van a szamlaban)

7. Futtasd ujra: npx promptfoo eval → 14/14 PASS

Gate: 95%+ pass rate, HU number parsing helyes, VAT-exempt kezelese, 14+ test
```

#### LEPES 3: cubix_course_capture Prompt SPLIT + Coverage

```
Hol: skills/cubix_course_capture/prompts/transcript_structurer.yaml (jelenlegi 1 prompt)
     -- UJ: skills/cubix_course_capture/prompts/section_detector.yaml
     -- UJ: skills/cubix_course_capture/prompts/summary_generator.yaml
     -- UJ: skills/cubix_course_capture/prompts/vocabulary_extractor.yaml
     skills/cubix_course_capture/tests/promptfooconfig.yaml (6 → 12)
     skills/cubix_course_capture/workflows/transcript_pipeline.py (workflow update)

Cel 1 — Prompt split: 1 monolit → 3 specializalt prompt (separation of concerns)
Cel 2 — Mixed-language stability: HU + EN tech kifejezesek + code-block kezelese
Cel 3 — Filler word kiszures vs szakszavak megorzese
Cel 4 — Section timestamp: ~10s pontossagra targeted

KONKRET TEENDOK:

1. Futtasd: npx promptfoo eval -c skills/cubix_course_capture/tests/promptfooconfig.yaml
   - Mert nem fed le mindent? jegyezd fel

2. UJ section_detector.yaml:
   - Bemenet: full transcript szoveg + becsult duration_seconds
   - Kimenet: {sections: [{title, start_time, end_time, topic}]}
   - System prompt: "Identify thematic boundaries (~30s minimum per section).
     Use Hungarian section titles. Estimate timestamps proportionally to text length."

3. UJ summary_generator.yaml:
   - Bemenet: full transcript + sections (a section_detector kimenete)
   - Kimenet: {summary: str (1-2 mondat), key_topics: [str], main_takeaways: [str]}
   - System prompt: "Generate a concise Hungarian summary. Preserve technical terms
     in their original form (English code, Hungarian explanation)."

4. UJ vocabulary_extractor.yaml:
   - Bemenet: full transcript
   - Kimenet: {terms: [{term, definition, example_usage, language}]}
   - System prompt: "Extract technical vocabulary terms. Provide a 1-sentence
     Hungarian definition for each. Language tag: 'en' for English terms,
     'hu' for Hungarian, 'mixed' for hungarized English (e.g. 'eventek')."

5. transcript_structurer.yaml DEPRECATION + atvezetes:
   - Tartsd meg de jelold deprecated-kent (description: "DEPRECATED — use the 3 split prompts")
   - workflow.py update: hivd a 3 uj promptot, kombinald az eredmenyt
   - Backward compat: a transcript_structurer.yaml output schemajat tovabbra is
     megorzizd (sections + summary + vocab kombinalt JSON)

6. 6 uj promptfoo test case (6 → 12):
   - test_section_detector_long:   ~30 perc transcript → 5+ szekcio detektalasa
   - test_summary_concise:         transcript → 1-2 mondat summary, max 200 char
   - test_vocab_mixed_lang:        HU+EN term → helyesen taggalva (hu/en/mixed)
   - test_filler_word_filter:      "ugye, hat, tehat" → kiszurve, de szakszo marad
   - test_code_block_preservation: ```python code``` → erintetlen marad
   - test_short_transcript:        <100 szavas transcript → 1 section + minimal output

7. transcript_pipeline.py workflow:
   - 3 lepeses pipeline: section_detector → summary_generator → vocabulary_extractor
   - parallel-zhetjuk: summary + vocab egy idoben fut, mert csak transcript-tol fugg
   - kombinalt output: {sections, summary, vocabulary} — megfelel a regi schemanak

8. guardrails.yaml — nincs valtoztatas (ON mode marad)

9. Futtasd ujra: npx promptfoo eval → 12/12 PASS

Gate: 95%+ pass rate, prompt split mukodik, 12+ test, workflow.py kovesse
```

#### LEPES 4: invoice_finder UJ Promptfoo Config + 12 Test Case (NAGY GAP!)

```
Hol: skills/invoice_finder/tests/promptfooconfig.yaml — UJ FAJL!
     skills/invoice_finder/prompts/{invoice_classifier,invoice_field_extractor,
                                     invoice_payment_status,invoice_report_generator}.yaml
     skills/invoice_finder/guardrails.yaml (finomhangolas)

Cel 1 — UJ promptfooconfig.yaml letrehozasa, EZ A FO MUNKA. 12+ test case kell.
Cel 2 — Phase 0 mailbox adatok: data/e2e_results/outlook_fetch/ -bol valos invoicekre
        epits teszteket
Cel 3 — Field extraction: HU + EN szamla formatumok stabil parsolasa
Cel 4 — Payment status: due_date parsing es overdue/due/paid lepcso

KONKRET TEENDOK:

1. Olvasd at: data/e2e_results/outlook_fetch/invoice_candidates.json (9 valos invoice email)
   - Jegyezd fel a tipusokat: subject patterns, body structure, attachment vagy nem
   - Ezekbol epits 6-8 valos teszt-mintat

2. UJ skills/invoice_finder/tests/promptfooconfig.yaml letrehozasa (mintaul S28 email_intent
   promptfooconfig.yaml — direkt openai provider, NEM custom exec):

   ```yaml
   description: "Invoice Finder - email-to-invoice extraction & report (B4.2)"

   providers:
     - id: openai:gpt-4o-mini
       label: "gpt-4o-mini (invoice finder)"
       config:
         temperature: 0
         response_format:
           type: json_object

   prompts:
     - label: "invoice_classifier"
       raw: |
         You are an invoice email classifier...
         Subject: {{subject}}
         Body: {{body}}

     - label: "invoice_field_extractor"
       raw: |
         Extract invoice fields from this email/attachment...

   tests:
     # Use vars: subject + body from invoice_candidates.json
     - description: "real bestix invoice 1"
       vars:
         subject: "Számla: ..."
         body: "..."
       assert:
         - type: is-json
         - type: javascript
           value: "JSON.parse(output).is_invoice_candidate === true"
   ```

3. invoice_classifier.yaml javitas:
   - Few-shot peldak HU + EN szamla emailekre
   - "is_invoice_candidate" → boolean
   - reason → 1 mondatos magyarazat
   - Confidence score 0-1

4. invoice_field_extractor.yaml javitas:
   - Fields: invoice_number, vendor_name, total_amount, currency, due_date, issue_date
   - Multi-format date parsing (HU: YYYY.MM.DD, EN: MM/DD/YYYY, ISO: YYYY-MM-DD)
   - Number parsing reuse-olja az invoice_processor logikajat (ket-hely tizedes,
     pont thousands separator)

5. invoice_payment_status.yaml javitas:
   - Bemenet: due_date (ISO string) + today_date
   - Logika: today > due_date → "overdue", today == due_date → "due_today",
     today < due_date → "due", explicit fizetett megjeloles → "paid"
   - Output: {status, days_to_due (int, negativ ha overdue), confidence}

6. invoice_report_generator.yaml javitas:
   - Kimenet: valid markdown (NEM HTML, NEM bare text)
   - Strict format: # Title, ## Section, - bullet, **bold** for amounts
   - Few-shot egy 3-szamlas riportra

7. 12 test case az UJ promptfooconfig.yaml-ban:
   - test_classifier_real_bestix_1:    valos email Phase 0-bol → is_invoice=true
   - test_classifier_real_bestix_2:    masik valos email → is_invoice=true
   - test_classifier_kodosok_1:        kodosok email → is_invoice=true vagy false (megfelelo)
   - test_classifier_marketing_filter: marketing email → is_invoice=false
   - test_extractor_hu_format:         "12.345 Ft, 2026.04.20" → helyes parsing
   - test_extractor_en_format:         "$1,234.56, 04/20/2026" → helyes parsing
   - test_extractor_missing_due:       no due_date → null vagy 30 napos default
   - test_payment_status_overdue:      due_date < today → "overdue"
   - test_payment_status_due_today:    due_date == today → "due_today"
   - test_payment_status_paid:         "FIZETVE" jelolessel → "paid"
   - test_report_generator_markdown:   3 invoice → valid markdown structure
   - test_report_generator_empty:      0 invoice → "No invoices found" message

8. guardrails.yaml finomhangolas:
   - input.max_length: 5000 → 8000 (csatolmany szoveg lehet hosszu)
   - allowed_pii: bovites email_intent-szeruen (`hu_tax_number`, `hu_bank_account`, `email`)
   - Mar PARTIAL mode-ban van, csak az allowed_pii listat bovitsuk

9. Futtasd: npx promptfoo eval -c skills/invoice_finder/tests/promptfooconfig.yaml
   → 12/12 PASS (95%+ = 12/12 vagy 11/12)

Gate: 95%+ pass rate az UJ 12 testen, valos Phase 0 adatra epitett tesztek
```

#### LEPES 5: /service-hardening 10-pont Checklist Audit (4 SKILL!)

```
Hol: /service-hardening process_documentation
     /service-hardening invoice_processor
     /service-hardening cubix_course_capture
     /service-hardening invoice_finder

Az audit 10 pontot vizsgal (lasd: .claude/commands/service-hardening.md):
  1. Unit teszt (5+ + coverage 70%+)
  2. Integracio (valos DB ha kell)
  3. API teszt (curl 200 OK + source: "backend")
  4. Prompt teszt (promptfoo 95%+)   ← LEPES 1-4-bol mar OK
  5. Error handling (AIFlowError, is_transient)
  6. Logging (structlog, no print/PII)
  7. Dokumentacio (docstring, README)
  8. UI (source badge, 0 console error)
  9. Input guardrail (injection, scope)
  10. Output guardrail (hallucination, PII, scope)

KONKRET TEENDOK:

1. /service-hardening process_documentation futtatas
   - Varhato gyengeseg: #5 error handling, #7 dokumentacio
   - Gap javitas + ujra-audit
   - Cel: 8+/10

2. /service-hardening invoice_processor futtatas
   - Varhato gyengeseg: #5 error handling, #7 dokumentacio, #8 UI badge
   - Gap javitas + ujra-audit
   - Cel: 8+/10

3. /service-hardening cubix_course_capture futtatas
   - Varhato gyengeseg: #1 unit teszt (kevesen vannak), #5 error handling
   - Gap javitas + ujra-audit
   - Cel: 8+/10

4. /service-hardening invoice_finder futtatas
   - Varhato gyengeseg: #4 prompt teszt (most lett UJ — most mar OK)
                       #1 unit teszt (kevesen)
                       #5 error handling
   - Gap javitas + ujra-audit
   - Cel: 8+/10

Gate: mind a 4 skill 8+/10, mind PRODUCTION-READY verdict
```

#### LEPES 6: Regresszio + Plan + Commit

```
/lint-check → 0 error
/regression → 1424+ unit test PASS (ne romoljon!)
              (S28-bol az volt: 1424. Ne csokkenjen.)
/update-plan → 58 progress B4.2 DONE, key numbers update:
               54 → ~78 promptfoo test (B4.2 +24 uj)
               5 → 6 skill 95%+ promptfoo (invoice_finder UJ-on hozza)
git status → ellenorizd hogy NINCS .code-workspace vagy mas lokalis state staged

Commit:
  feat(sprint-b): B4.2 skill hardening — process_docs + invoice_processor + cubix + invoice_finder

  Body lenyege:
    - 4 skill 95%+ promptfoo (cubix split prompt, invoice_finder UJ config Phase 0 adatra)
    - +24 promptfoo test, +1 promptfooconfig (invoice_finder)
    - cubix: 1 monolit prompt → 3 split (section_detector, summary_generator, vocabulary_extractor)
    - process_docs: mermaid_flowchart strict shape mapping + decision label enforcement
    - invoice_processor: HU thousands separator + AAM VAT exempt + multi-currency
    - invoice_finder: 12 valos Phase 0 tesztre epitett UJ promptfooconfig.yaml
    - guardrails.yaml finomhangolasok minden 4 skill-en
    - 10-pt service hardening: 4/4 PRODUCTION-READY (8+/10)
```

### Teszt Fajl Struktura (B4.2 vegen)

```
skills/process_documentation/tests/promptfooconfig.yaml      — 10 → 14 test case
skills/process_documentation/prompts/                         — 5 prompt YAML modositas
skills/process_documentation/guardrails.yaml                  — max_length bovites
skills/process_documentation/prompts/reviewer.yaml            — UJ output validator (vagy meglevo modositas)

skills/invoice_processor/tests/promptfooconfig.yaml           — 10 → 14 test case
skills/invoice_processor/prompts/{header,line,validator}.yaml — 3 prompt YAML modositas
skills/invoice_processor/guardrails.yaml                      — pii_logging audit (mar OK)

skills/cubix_course_capture/tests/promptfooconfig.yaml        — 6 → 12 test case
skills/cubix_course_capture/prompts/section_detector.yaml     — UJ FAJL!
skills/cubix_course_capture/prompts/summary_generator.yaml    — UJ FAJL!
skills/cubix_course_capture/prompts/vocabulary_extractor.yaml — UJ FAJL!
skills/cubix_course_capture/prompts/transcript_structurer.yaml — DEPRECATED jeloles
skills/cubix_course_capture/workflows/transcript_pipeline.py  — workflow update (3 hivas)

skills/invoice_finder/tests/promptfooconfig.yaml              — UJ FAJL! 12 test case
skills/invoice_finder/prompts/{classifier,extractor,payment,report}.yaml — 4 prompt modositas
skills/invoice_finder/guardrails.yaml                         — allowed_pii bovites

Osszesen: ~24 uj promptfoo test, 1 uj promptfooconfig (invoice_finder),
          3 uj prompt YAML (cubix split), ~10 prompt YAML modositas,
          1 workflow.py update (cubix), 4 guardrails.yaml finomhangolas
Unit teszt: minimum 1424 marad. Lehet, hogy nehany uj kell a cubix split-hez (~5)
```

---

## VEGREHAJTAS SORRENDJE

```
--- LEPES 1: process_documentation ---
/dev-step "B4.2.1 — Baseline promptfoo eval process_documentation, jegyezd fel bukott testek"
/prompt-tuning process_documentation
/dev-step "B4.2.2 — mermaid_flowchart shape mapping + few-shot + temperature 0.1"
/dev-step "B4.2.3 — classifier off-topic refusal + few-shot"
/dev-step "B4.2.4 — extractor BPMN strict graph schema"
/dev-step "B4.2.5 — reviewer output validacio prompt"
/dev-step "B4.2.6 — 4 uj promptfoo test (10 → 14)"
npx promptfoo eval -c skills/process_documentation/tests/promptfooconfig.yaml  # gate 14/14

--- LEPES 2: invoice_processor ---
/dev-step "B4.2.7 — Baseline promptfoo eval invoice_processor"
/prompt-tuning invoice_processor
/dev-step "B4.2.8 — header_extractor HU number + currency detection"
/dev-step "B4.2.9 — line_extractor multi-currency + multi-page"
/dev-step "B4.2.10 — validator strict cross-check + adoszam regex"
/dev-step "B4.2.11 — 4 uj promptfoo test (10 → 14)"
npx promptfoo eval -c skills/invoice_processor/tests/promptfooconfig.yaml  # gate 14/14

--- LEPES 3: cubix_course_capture (BIG REFACTOR) ---
/dev-step "B4.2.12 — Cubix prompt split: section_detector.yaml + summary_generator.yaml + vocabulary_extractor.yaml"
/dev-step "B4.2.13 — transcript_pipeline.py workflow update (3 promptot hiv)"
/dev-step "B4.2.14 — transcript_structurer.yaml DEPRECATED jeloles"
/dev-step "B4.2.15 — 6 uj promptfoo test (6 → 12) split prompt-okra"
npx promptfoo eval -c skills/cubix_course_capture/tests/promptfooconfig.yaml  # gate 12/12

--- LEPES 4: invoice_finder (UJ PROMPTFOO CONFIG!) ---
/dev-step "B4.2.16 — Olvasd at data/e2e_results/outlook_fetch/invoice_candidates.json"
/dev-step "B4.2.17 — UJ skills/invoice_finder/tests/promptfooconfig.yaml letrehozasa"
/dev-step "B4.2.18 — invoice_classifier + field_extractor finomitas"
/dev-step "B4.2.19 — payment_status due_date parsing"
/dev-step "B4.2.20 — report_generator markdown stricter format"
/dev-step "B4.2.21 — 12 test case epitese valos Phase 0 adatra"
npx promptfoo eval -c skills/invoice_finder/tests/promptfooconfig.yaml  # gate 12/12

--- LEPES 5: /service-hardening 10-point ---
/service-hardening process_documentation   # gate 8+/10
/service-hardening invoice_processor       # gate 8+/10
/service-hardening cubix_course_capture    # gate 8+/10
/service-hardening invoice_finder          # gate 8+/10
# Hianyzo pontok javitasa (varhato: docstringok, error handling, README)

--- LEPES 6: SESSION LEZARAS ---
/lint-check → 0 error
/regression → 1424+ unit test PASS
/update-plan → 58 progress B4.2 DONE, key numbers (54 → ~78 promptfoo, 6 skill 95%+)
git commit feat(sprint-b): B4.2 skill hardening — 4 skills 95%+ + cubix split + invoice_finder new
```

---

## KORNYEZET ELLENORZES

```bash
git branch --show-current                                              # → feature/v1.3.0-service-excellence
git log --oneline -3                                                   # → 9eb2769, e14ddf2, 4579cd2
.venv/Scripts/python -m pytest tests/unit/ -q --ignore=tests/unit/vectorstore/test_search.py 2>&1 | tail -1
                                                                       # → 1424 passed
.venv/Scripts/ruff check src/ tests/ 2>&1 | tail -1                  # → All checks passed!

# Skill gyors audit:
ls skills/process_documentation/prompts/*.yaml | wc -l                 # → 5
ls skills/invoice_processor/prompts/*.yaml | wc -l                     # → 4
ls skills/cubix_course_capture/prompts/*.yaml | wc -l                  # → 1 (split utan 4)
ls skills/invoice_finder/prompts/*.yaml | wc -l                        # → 6
test -f skills/invoice_finder/tests/promptfooconfig.yaml || echo "MISSING — must create!"

grep -c 'assert:' skills/process_documentation/tests/promptfooconfig.yaml  # → 10
grep -c 'assert:' skills/invoice_processor/tests/promptfooconfig.yaml      # → 10
grep -c 'assert:' skills/cubix_course_capture/tests/promptfooconfig.yaml   # → 6

# Phase 0 valos invoice adat ellenorzes (invoice_finder tesztekhez kell!):
test -f data/e2e_results/outlook_fetch/invoice_candidates.json && echo "OK 9 invoice candidates"
.venv/Scripts/python -c "import json; data = json.load(open('data/e2e_results/outlook_fetch/invoice_candidates.json')); print(f'count={len(data)}')"

# Promptfoo + .env ellenorzes
which npx 2>&1                                                         # → /c/Program Files/nodejs/npx
grep -c "^OPENAI_API_KEY=" .env                                        # → 1

# Docker (NEM kell aszf_rag custom provider, mert ezek a skillek direct openai providert hasznalnak)
docker ps | grep -E "07_ai_flow.*db.*Up" | head -1
```

---

## S28 TANULSAGAI (alkalmazando S29-ben!)

1. **Promptfoo Windows infra mar javitva** — a `scripts/promptfoo_provider.py` UTF-8 + argv + stderr noise filter mind kesz, de **B4.2-ben NEM hasznald** mert ezek a skillek `openai:gpt-4o-mini` direkt providert hasznalnak (nem custom exec). Ez sokkal egyszerubb, gyorsabb, olcsobb.

2. **Role-routed promptok ellenorzese** — az aszf_rag_chat-nal `query.py` a `system_prompt_*.yaml`-t tolti, NEM az `answer_generator.yaml`-t. **B4.2-ben minden skill-nel ellenorizd hogy a workflow.py melyik prompt fajlt LOAD-olja** (`grep -n "_prompt_manager.get\|prompt_manager.get" skills/*/workflow*.py`). Ne pazarolj orat egy orphan prompt-on.

3. **Tolerans assertek > kemeny string match** — aszf_rag tesztekben a "grounded answer OR safe refusal" kettos opcio mukodott. **B4.2-ben hasznalj `javascript:` assertet** ahol az output lehet tobb formatumban, ne kemeny `contains-any:` listazast.

4. **Tests use vars from REAL data** — Phase 0 mailbox (data/e2e_results/outlook_fetch/) mar megvan 90 emailek + 9 invoice candidate. **B4.2-ben a invoice_finder tesztek ezekbol epuljenek**, ne talalj ki fake email-eket.

5. **Pre-existing test mock-ok torhetnek** — A B4.1-ben a hallucination_detector JSON parser modositasat kovetoen 4 mock teszt eltort (bare float-ot kuldtek dict helyett). **B4.2-ben ha modositod barmely workflow .py fajlt, futtasd a skill-specifikus teszteket** (skills/<name>/tests/test_workflow.py) MIELOTT a teljes regressziot.

6. **`extra_injection_patterns`-t hasznald** — InputGuard tamogatja az extra patterneket per-skill alapon. **B4.2-ben mindegyik skill-hez tegyel 2-3 specifikus patternt** ami a saja domain-jen ertelmes (pl. invoice_processor: "modify\\s+vat\\s+rate"; process_documentation: "delete\\s+all\\s+steps").

7. **Memory file frissites** — B4.1-ben ket uj memory file kerult be (promptfoo Windows + aszf_rag prompt routing). **B4.2-ben ha barmilyen non-obvious gotcha-t talalsz** (pl. cubix split prompt workflow gotcha, invoice_finder Phase 0 adat sema egyenetlenseg), mentsd memory-ba.

---

## MEGLEVO KOD REFERENCIAK (olvasd el mielott irsz!)

```
# process_documentation skill:
skills/process_documentation/skill.yaml                       — skill manifest
skills/process_documentation/workflow.py                      — single-file workflow
skills/process_documentation/prompts/                         — 5 YAML
skills/process_documentation/guardrails.yaml                  — B1.2-bol, FINOMHANGOLANDO
skills/process_documentation/tests/promptfooconfig.yaml       — 10 test, BOVITENDO 14-re

# invoice_processor skill:
skills/invoice_processor/skill.yaml
skills/invoice_processor/workflows/process.py
skills/invoice_processor/prompts/                             — 4 YAML
skills/invoice_processor/guardrails.yaml                      — OFF mode, pii_logging=true
skills/invoice_processor/tests/promptfooconfig.yaml           — 10 test, BOVITENDO 14-re

# cubix_course_capture skill (NAGY REFAKTOR):
skills/cubix_course_capture/skill.yaml
skills/cubix_course_capture/workflows/transcript_pipeline.py  — workflow update kell
skills/cubix_course_capture/workflows/course_capture.py       — meglevo workflow
skills/cubix_course_capture/prompts/transcript_structurer.yaml — DEPRECATED-re
skills/cubix_course_capture/prompts/                          — UJ: section/summary/vocabulary
skills/cubix_course_capture/guardrails.yaml                   — ON mode marad
skills/cubix_course_capture/tests/promptfooconfig.yaml        — 6 test, BOVITENDO 12-re

# invoice_finder skill (UJ PROMPTFOO!):
skills/invoice_finder/skill.yaml
skills/invoice_finder/prompts/                                — 6 YAML mar megvan
skills/invoice_finder/guardrails.yaml                         — PARTIAL mode, B1.2-bol
skills/invoice_finder/confidence_config.yaml                  — B3.5-bol, kalibralt
skills/invoice_finder/tests/promptfooconfig.yaml              — UJ FAJL!

# Valos invoice adat (invoice_finder kalibraciohoz!):
data/e2e_results/outlook_fetch/invoice_candidates.json        — 9 valos invoice email
data/e2e_results/outlook_fetch/bestix_emails.json             — 30 bestix email
data/e2e_results/outlook_fetch/kodosok_emails.json            — 30 kodosok email
data/e2e_results/outlook_fetch/gmail_emails.json              — 30 gmail email
data/e2e_results/outlook_fetch/intent_distribution.json       — aggregalt statisztika

# Pipeline reference (invoice_finder mukodes megertese):
src/aiflow/pipeline/builtin_templates/invoice_finder_v3.yaml  — 8-step pipeline
src/aiflow/pipeline/builtin_templates/invoice_finder_v3_offline.yaml — 5-step offline

# Promptfoo + service-hardening slash commands:
.claude/commands/service-hardening.md                         — 10-point audit protocol
.claude/commands/prompt-tuning.md                             — Langfuse → Promptfoo → fix cycle
.claude/commands/dev-step.md                                  — standard dev cycle
.claude/commands/quality-check.md                             — promptfoo + cost analysis

# B4.1 referencia (S28-bol — masolj patterneket!):
skills/aszf_rag_chat/tests/promptfooconfig.yaml               — tolerans javascript: assertek
skills/email_intent_processor/tests/promptfooconfig.yaml      — direkt openai provider, JSON output
skills/email_intent_processor/prompts/intent_classifier.yaml  — few-shot + boundary rules
skills/aszf_rag_chat/prompts/system_prompt_expert.yaml        — strict prompt + refusal templates

# Memory files (S28-bol):
memory/feedback_promptfoo_windows_infra.md                    — exec provider 4 fix
memory/feedback_aszf_rag_prompt_routing.md                    — role-routed prompt gotcha
```

---

## SPRINT B UTEMTERV (S28 utan, frissitett)

```
S19: B0      — DONE (4b09aad) — 5-layer arch + qbpp + prompt API + OpenAPI
S20: B1.1    — DONE (f6670a1) — 4 LLM guardrail prompt + llm_guards.py + 27 promptfoo
S21: B1.2    — DONE (7cec90b) — 5 guardrails.yaml + PIIMaskingMode + 31 teszt
S22: B2.1    — DONE (51ce1bf) — Core infra service tesztek (65 test, Tier 1)
S23: B2.2    — DONE (62e829b) — v1.2.0 service tesztek (65 test, Tier 2)
S24: B3.1    — DONE (372e08b) — Invoice Finder pipeline + email search + doc acquire (29 test)
S25: B3.2    — DONE (aecce10) — Invoice Finder extract + payment + report + notify (16 test)
S26a: B3.E2E.P0 — DONE (0b5e542) — Outlook COM multi-account fetch + email intent
S26a: B3.E2E.P1 — DONE (f1f0029) — offline invoice finder pipeline (20/20 PASS)
S27a: B3.E2E.P2 — DONE (8b10fd6) — PipelineRunner DB persistence integration
S27a: B3.E2E.P3 — DONE (70f505f) — full 8-step pipeline on 3 Outlook accounts
S27b: B3.5   — DONE (4579cd2) — confidence scoring hardening + review routing (36 test)
S28: B4.1    — DONE (9eb2769) — Skill hardening: aszf_rag 12/12 + email_intent 16/16, +9 promptfoo
S29: B4.2    ← KOVETKEZO SESSION — Skill hardening: process_docs + invoice_processor + cubix + invoice_finder
S30: B5      — Spec writer + diagram_generator service tuning + koltseg baseline
S31: B6      — UI Journey audit + 4 journey tervezes + navigacio redesign
S32: B7      — Verification Page v2 (bounding box, diff, per-field confidence szin)
S33: B8      — UI Journey implementacio (top 3 journey + dark mode)
S34: B9      — Docker containerization + UI pipeline trigger + deploy teszt
S35: B10     — POST-AUDIT + javitasok
S36: B11     — v1.3.0 tag + merge
```

---

## FONTOS SZABALYOK (emlekeztetok)

- **`/prompt-tuning` + `/service-hardening` HASZNALANDO** — ezek a B0-bol jottek, a tuning ciklust pontosan kovesd
- **Promptfoo = valos LLM hivas** — OPENAI_API_KEY szukseges. Direct openai provider olcsobb mint custom exec (~$0.0006/test gpt-4o-mini-vel)
- **Guardrail meglevo, csak finomhangolas** — NE irj uj guardrails.yaml-t, csak threshold + pattern modositas + allowed_pii bovites
- **10-point checklist = `/service-hardening` kimenete** — ne keszits kulon dokumentumot, a command outputja a forras
- **HU szabalyok HU-ra** — a invoice_processor HU number formattal, a cubix HU + EN tech kifejezessel kell foglalkozzon
- **Valos adat Phase 0-bol** — `data/e2e_results/outlook_fetch/*.json` az invoice_finder kalibraciohoz, NE talalj ki fake adatokat
- **Cubix split = workflow update kell** — ne csak prompt YAML-t valts, hanem `transcript_pipeline.py`-t is hivd a 3 promptot
- **invoice_finder UJ promptfooconfig** — sablonkent hasznald a `email_intent_processor/tests/promptfooconfig.yaml`-t
- **Direct openai provider EGYIK skill-nel sem hasznal custom execet** — sokkal egyszerubb mint az aszf_rag, ne ervelj velem :)
- **structlog mindig** — `logger = structlog.get_logger(__name__)`, nincs print()
- **NEM commit-olod a `.code-workspace` vagy `01_PLAN/document_pipeline.md` lokalis state-eket**

---

## B4.2 GATE CHECKLIST

```
process_documentation:
[ ] skills/process_documentation/tests/promptfooconfig.yaml 14+ test case
[ ] mermaid_flowchart.yaml strict shape mapping + few-shot + temperature 0.1
[ ] classifier.yaml off-topic refusal aktiv
[ ] extractor.yaml strict BPMN graph schema
[ ] reviewer.yaml output validacio prompt
[ ] guardrails.yaml: max_length 4000 → 8000
[ ] npx promptfoo eval → 95%+ pass rate (14/14 vagy 13/14)
[ ] /service-hardening process_documentation → 8+/10

invoice_processor:
[ ] skills/invoice_processor/tests/promptfooconfig.yaml 14+ test case
[ ] header_extractor HU number parsing fix (1.500.000 → 1500000)
[ ] line_extractor multi-currency + multi-page kezelese
[ ] validator strict cross-check + adoszam regex
[ ] guardrails.yaml: pii_logging=true (mar OK), nincs vatoztatas
[ ] npx promptfoo eval → 95%+ pass rate (14/14 vagy 13/14)
[ ] /service-hardening invoice_processor → 8+/10

cubix_course_capture (BIG REFAKTOR):
[ ] skills/cubix_course_capture/prompts/section_detector.yaml UJ FAJL
[ ] skills/cubix_course_capture/prompts/summary_generator.yaml UJ FAJL
[ ] skills/cubix_course_capture/prompts/vocabulary_extractor.yaml UJ FAJL
[ ] transcript_structurer.yaml DEPRECATED jeloles
[ ] transcript_pipeline.py workflow update (3 promptot hiv)
[ ] skills/cubix_course_capture/tests/promptfooconfig.yaml 12+ test case
[ ] npx promptfoo eval → 95%+ pass rate (12/12 vagy 11/12)
[ ] /service-hardening cubix_course_capture → 8+/10

invoice_finder (UJ PROMPTFOO!):
[ ] skills/invoice_finder/tests/promptfooconfig.yaml UJ FAJL letrehozva
[ ] 12+ test case Phase 0 valos invoice email-ekre epitve
[ ] invoice_classifier finomitva HU+EN formatumokra
[ ] field_extractor HU number + datum parsing
[ ] payment_status due_date logika
[ ] report_generator strict markdown
[ ] guardrails.yaml allowed_pii bovites
[ ] npx promptfoo eval → 95%+ pass rate (12/12 vagy 11/12)
[ ] /service-hardening invoice_finder → 8+/10

Ossz:
[ ] /lint-check → 0 error
[ ] /regression → 1424+ unit test PASS (ne romoljon)
[ ] /update-plan → 58 progress B4.2 DONE + key numbers (54 → ~78 promptfoo, 6 skill 95%+)
[ ] git commit: feat(sprint-b): B4.2 skill hardening — 4 skills 95%+ + cubix split + invoice_finder new
[ ] git status sima — semmilyen lokalis state staged (sem code-workspace, sem document_pipeline.md)
```
