Test an entire service end-to-end: backend + API + UI together.

Arguments: $ARGUMENTS
(Service name: document_extractor, email_connector, rag_engine, rpa_browser, media_processor, diagram_generator, human_review, or "all")

> **Vertikalis szelet teszt:** Ez NEM unit teszt, hanem a TELJES szolgaltatas
> mukodesnek ellenorzese: backend → API → UI → valos adat → valos bongeszio.
> Egy szolgaltatas CSAK AKKOR "KESZ" ha ez a teszt ATMENT!

## Steps:

### 1. BACKEND SERVICE CHECK
```bash
# Service modul letezik es importalhato?
python -c "from aiflow.services.{name} import {ServiceClass}"

# Valos muvelet tesztelese (service-specifikus):
# Document Extractor: valos PDF parse
# Email Connector: valos IMAP/O365 kapcsolat
# RAG Engine: valos ingest + query
# RPA Browser: valos weboldal scrape
# Media Processor: valos audio/video STT
# Diagram Generator: valos Mermaid/DrawIO render
```

### 2. API ENDPOINT CHECK
```bash
# Health check
curl -s http://localhost:8102/health | python -m json.tool

# Service-specifikus endpoint (VALOS adat, NEM stub!):
curl -s http://localhost:8102/api/v1/{endpoint} | python -m json.tool

# Ellenorizd:
# - HTTP 200 (vagy megfelelo status kod)
# - "source": "backend" (NEM "demo"!)
# - Valos adatok a valaszban (NEM placeholder)
# - Helyes schema (megfelel a Pydantic modelnek)
```

### 3. UI PLAYWRIGHT E2E CHECK
Ha van UI az adott szolgaltatashoz:
```
# MCP Playwright teszteles:
1. browser_navigate → szolgaltatas oldala betolt?
2. browser_snapshot → valos adat megjelenik (NEM "Loading..." orokke)?
3. browser_click → interakciok mukodnek (upload, filter, detail)?
4. browser_take_screenshot → vizualis ellenorzes
5. browser_console_messages → nincs JS hiba?
6. i18n toggle (HU/EN) → MINDEN string valtozik?
```

### 4. INTEGRACIO CHECK
```bash
# Regi skill CLI backward compat:
python -m skills.{original_skill} --help
# Mukodik-e meg a regi modon? Belul az uj service-t hasznalja?

# dataProvider / source mezo check:
# Az UI "source: backend" badge-et mutat? (NEM "demo"!)
```

### 5. REPORT
Minden szolgaltatasra tabla:

| Check | Eredmeny | Reszletek |
|-------|----------|-----------|
| Backend import | ✅/❌ | {error ha van} |
| Backend valos muvelet | ✅/❌ | {eredmeny} |
| API endpoint | ✅/❌ | {HTTP status, source mezo} |
| API valos adat | ✅/❌ | {tartalom ellenorzes} |
| UI betoltes | ✅/❌ | {Playwright screenshot} |
| UI interakcio | ✅/❌ | {click, filter, detail} |
| UI console hiba | ✅/❌ | {JS error lista} |
| i18n HU/EN | ✅/❌ | {hardcoded string?} |
| Backward compat | ✅/❌ | {skill CLI mukodik?} |
| **OSSZESITETT** | **PASS/FAIL** | |

**Ha BARMELY sor FAIL:** A szolgaltatas NEM tekintheto KESZ-nek. Javitas szukseges!

## SERVICE MAP:
| Service | Forras Skill | API Endpoint | UI Page | Fazis |
|---------|-------------|-------------|---------|-------|
| document_extractor | invoice_processor | /api/v1/documents | InvoiceUpload, InvoiceVerify | F1 |
| email_connector | email_intent_processor | /api/v1/emails | EmailUpload, EmailShow | F2 |
| classifier | email_intent_processor | /api/v1/emails/classify | EmailShow (intent) | F2 |
| rag_engine | aszf_rag_chat | /api/v1/chat/completions | RagChat | F3 |
| diagram_generator | process_documentation | /api/v1/process-docs | ProcessDocViewer | F4a |
| media_processor | cubix_course_capture | /api/v1/cubix | CubixViewer | F4b |
| rpa_browser | cubix_course_capture | /api/v1/cubix | CubixViewer | F4c |
| human_review | — | /api/v1/reviews | (uj oldal) | F4d |
