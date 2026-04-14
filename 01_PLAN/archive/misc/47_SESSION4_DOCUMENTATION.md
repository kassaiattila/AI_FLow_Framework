# AIFlow v1.1.4 — Session 4 Documentation

> **Datum:** 2026-04-03 (4. session)
> **Kiindulas:** main (bed4efc, v1.1.3)
> **Valtozasok:** ~2600 sor hozzaadas, ~630 sor torles, 20 fajl modositva, 10 uj fajl
> **Port:** API 8102, Frontend 5173 (Vite proxy)

---

## 1. Egysegeses Per-File Pipeline Progress Bar (FileProgressRow)

### Problema
Minden feldolgozo oldal (Documents, RAG, Media, Emails, Process Docs) kulonbozo modon mutatta a haladas jelzest — nem volt egyseges UX.

### Megoldas
Kozos `FileProgressRow` + `FileProgressBar` komponens (`components-new/FileProgress.tsx`), ami MINDEN pipeline oldalon hasznalva van.

### Backend SSE format (egyseges minden endpoint-on)
```
init          → { total_files, steps[] }
file_start    → { file, file_index, total_files }
file_step     → { file, file_index, step_index, step_name, status: "running"|"done", elapsed_ms? }
file_error    → { file, file_index, step_name, error }
file_done     → { file, file_index, ok: bool }
complete      → { results/total_processed }
```

### SSE Endpointok

| Oldal | Endpoint | Pipeline lepesek |
|-------|----------|-----------------|
| Documents | `POST /api/v1/documents/process-stream` | parse → classify → extract → validate → store |
| RAG Ingest | `POST /api/v1/rag/collections/{id}/ingest-stream` | upload → parse → chunk → embed → store |
| Process Docs | `POST /api/v1/process-docs/generate-stream` | classify → elaborate → extract → review → generate → export |
| Media | Frontend per-file loop | upload → process |
| Email Upload | `POST /api/v1/emails/upload-and-process-stream` | upload → parse → classify → extract → priority → route |
| Email Fetch+Process | `POST /api/v1/emails/fetch-and-process-stream` | fetch → parse → classify → extract → priority → route |
| Email Batch Process | `POST /api/v1/emails/process-batch-stream` | parse → classify → extract → priority → route |

### Frontend komponens
```
components-new/FileProgress.tsx
  FileStepState    — { name, status, elapsed_ms? }
  FileProgress     — { name, status, steps[], error? }
  FileProgressRow  — egyetlen fajl sora: ikon + nev + mini step barok
  FileProgressBar  — osszesitett sav (done/total %)
```

### Erintett fajlok
- `aiflow-admin/src/components-new/FileProgress.tsx` — **UJ** kozos komponens
- `aiflow-admin/src/pages-new/Documents.tsx` — atirva per-file SSE-re
- `aiflow-admin/src/pages-new/RagDetail.tsx` — atirva per-file SSE-re
- `aiflow-admin/src/pages-new/ProcessDocs.tsx` — SSE hozzaadva
- `aiflow-admin/src/pages-new/Media.tsx` — per-file upload progress
- `aiflow-admin/src/pages-new/Emails.tsx` — SSE upload + fetch + batch process
- `src/aiflow/api/v1/documents.py` — per-file pipeline SSE
- `src/aiflow/api/v1/rag_engine.py` — per-file pipeline SSE
- `src/aiflow/api/v1/process_docs.py` — SSE generate-stream endpoint
- `src/aiflow/api/v1/emails.py` — 3 SSE endpoint

---

## 2. ChatPanel Redesign (modularis architektura)

### Problema
Az elozo `ChatPanel.tsx` (273 sor) egyetlen monolitikus fajl volt, minimalis funkciokkal.

### Megoldas
Felosztva 10 fajlra egy `ChatPanel/` konyvtarban:

```
components-new/ChatPanel/
  index.tsx           — fo orchestrator, handleSend, scroll logika
  types.ts            — ChatMessage, QueryResponse, AVAILABLE_MODELS (6 LLM)
  ChatHeader.tsx      — collection dropdown + model dropdown + clear history
  MessageBubble.tsx   — avatar + nev + timestamp + copy gomb + sources + model badge
  ChatInput.tsx       — auto-resize textarea + Shift+Enter + ArrowUp/Down history
  ScrollToBottom.tsx  — lebegio gomb ha felfele gorgettunk
  SourcesBlock.tsx    — osszecsukhato forras hivatkozasok (collapsible)
  useChatHistory.ts   — localStorage persistence per collection (max 100 msg)
  usePromptHistory.ts — fel/le nyil = korabbi promptok (max 50)
```

### Uj funkciok
1. **LLM model valaszto** — GPT-4o, GPT-4o-mini, GPT-4.1, Claude Sonnet 4, Claude Haiku 4
2. **Chat history mentes** — localStorage per collection, oldal ujratoltes utan is megmarad
3. **Prompt history** — ArrowUp/Down navigacio a korabbi promptok kozott
4. **Copy gomb** — hover-re megjeleno masolas gomb, "Copied!" feedback
5. **Smart scroll** — auto-scroll csak ha lent vagyunk, scroll-to-bottom gomb
6. **Timestamp** — HH:mm (ma) vagy datum+ido (regebbi)
7. **Model badge** — melyik LLM valaszolt (pl. "GPT-4o")
8. **Clear history** — confirm dialoggal

### Backend valtozas
- `QueryRequest` → uj `model: str | None` parameter
- `QueryResponse` → uj `model_used: str | None` mezo
- `RAGEngineService.query()` → `model` parameter, `answer_model` override
- `QueryResult` → uj `model_used: str` mezo

### Erintett fajlok
- `components-new/ChatPanel.tsx` — **TOROLVE** (konyvtar valtja fel)
- `components-new/ChatPanel/*` — **10 UJ FAJL** (698 sor)
- `src/aiflow/api/v1/rag_engine.py` — model param
- `src/aiflow/services/rag_engine/service.py` — model override

---

## 3. Email Connector Rendszer (Outlook COM + CRUD)

### Problema
- IMAP connector nem mukodott (O365 basic auth letiltva 2022-ben)
- Connector form nem volt (uj/szerkesztes/torles)
- Letoltott emailek nem jelentek meg / nem dolgozodtak fel

### Megoldas

#### 3a. Outlook COM Provider
Uj `outlook_com` provider a `ConnectorProvider` enum-ban. A futo Windows Outlook-hoz csatlakozik COM/MAPI-n keresztul.

**Hogyan mukodik:**
1. `win32com.client.Dispatch("Outlook.Application")` → MAPI namespace
2. Account szures a `mailbox` mezo alapjan (pl. "bestix", "aam", "field")
3. Folder kereses (default: Inbox)
4. Datum szures `[ReceivedTime]` Restrict-tel
5. Attachment-ek mentese + EML export
6. `pythoncom.CoInitialize()` szukseges a worker thread-ben

**Konfiguracio:**
- Provider: `outlook_com`
- Mailbox: account szuro (pl. "bestix" → `attila.kassai@bestix.hu`)
- Host/Port/SSL: nem szukseges (helyi Outlook)
- Credentials: nem szukseges (Outlook session-t hasznalja)

**DB constraint:** `chk_ecc_provider` bovitve `outlook_com` ertekkel.

#### 3b. Connector Form Dialog
Teljes CRUD UI a Connectors tab-on:
- **"+ New connector" gomb** → form dialog (create)
- **Sor kattintas** → form dialog (edit)
- **Torles gomb** a szerkeszto dialogban
- **Provider fuggoen mezo rejtese** — Outlook-nal nincs host/port/credentials
- **Provider dropdown:** Outlook (local), IMAP, Office 365 Graph, Gmail

#### 3c. Auto-process Toggle
- Toggle switch a datum szurok mellett: "Auto-process intents"
- ON: `fetch-and-process-stream` SSE — letoltes + per-email pipeline
- OFF: egyszeruen `/fetch` — csak letoltes

#### 3d. Inbox Tab Fejlesztesek
- **Process gomb** minden feldolgozatlan email soraban
- **"Process All (N)" gomb** — bulk feldolgozas
- **"Process Selected" gomb** — checkbox kivalasztas + bulk
- **CSV Export gomb** — `GET /api/v1/emails/export/csv`
- **4 KPI kartya:** Total, Processed, Unprocessed, Attachments
- **Real-time frissites** — `file_done` event-nel `refetch()`
- **Cross-tab frissites** — `refreshKey` prop az Emails komponensben

### Erintett fajlok
- `src/aiflow/services/email_connector/service.py` — Outlook COM provider (test + fetch)
- `src/aiflow/api/v1/emails.py` — 3 SSE endpoint, export/csv, output_data JSON parse fix
- `aiflow-admin/src/pages-new/Emails.tsx` — CRUD form, progress bar, auto-process toggle

---

## 4. Media Processing Javitasok

### Bugfixek
1. **ffmpeg `acodec copy` → `acodec aac`** — audio-only fajlok M4A kontenerbe konvertalasa (PCM WAV nem kompatibilis M4A-val)
2. **`output_dir` passthrough** — `extract_audio` + `chunk_audio` a data dict-bol olvassa az output_dir-t, nem a hardcoded config-bol
3. **`transcribe()` chunks data megorzese** — visszaadja a `chunks` + `output_dir` kulcsokat a `merge_transcripts` lepesnek
4. **`transcript_raw` kulcs fix** — `merged_text` → `full_text` (a pipeline valtos kulcsa)
5. **`transcript_structured` fallback** — ha nincs `structured_transcript` kulcs, a valos kulcsokat (`title`, `summary`, `sections`) gyujti ossze

### Transcript Viewer
- Sor kattintas a Media tablan → transcript panel
- Strukturalt megjelenes: cim, osszefoglalo, key topics (pill badge), szekciok
- **Szekciok osszecsukhatok** — nyilacska toggle, idobelyeg, summary
- Raw transcript fallback ha nincs strukturalt

### Erintett fajlok
- `skills/cubix_course_capture/workflows/transcript_pipeline.py` — ffmpeg fix, chunks fix, output_dir fix
- `src/aiflow/services/media_processor/service.py` — transcript_raw + structured kulcs fix
- `aiflow-admin/src/pages-new/Media.tsx` — transcript viewer, per-file progress, drag-and-drop

---

## 5. Verification Oldal Javitasok

### Valtozasok
1. **Overlay auto-hide real image modban** — `viewMode === "real"` eseten `filteredPoints = []`
2. **Toggle switch** — Real ↔ Mock valto szep slider toggle-kent
3. **Overlay gombok** — csak mock modban jelennek meg

### Erintett fajl
- `aiflow-admin/src/pages-new/Verification.tsx`

---

## 6. Documents Tabla Javitasok

### Valtozasok
1. **Actions oszlop** — `gap-1→gap-2`, `p-1→px-1.5 py-1`, `shrink-0` — nem szorulnak
2. **Per-file progress** — Documents upload SSE per-file pipeline-ra atirva
3. **Backward compatibility** — regi `step_start/step_done` event-eket is kezeli

### Erintett fajl
- `aiflow-admin/src/pages-new/Documents.tsx`

---

## 7. RAG Chat Sources Formatas

### Valtozas
- Collapsible `SourcesBlock` — nyil toggle, szamozott forrasok, jobb layout
- Athelyezve kozos komponensbe: `ChatPanel/SourcesBlock.tsx`

---

## 8. i18n Bovites

### Uj kulcsok (en.json + hu.json)

| Kulcs | EN | HU |
|-------|----|----|
| ragChat.model | Model | Modell |
| ragChat.clearHistory | Clear history | Elozmeny torlese |
| ragChat.clearHistoryConfirm | Clear chat history? | Chat elozmeny torlese? |
| ragChat.copied | Copied! | Masolva! |
| ragChat.you | You | Te |
| ragChat.assistant | AI Assistant | AI Asszisztens |
| ragChat.scrollToBottom | Scroll to bottom | Gorgetese lefele |
| connectors.fetchPeriod | Fetch period | Lekerdezesi idoszak |
| connectors.outlook_com | Outlook (local) | Outlook (helyi) |
| media.selectFiles | Select files | Fajlok valasztasa |
| media.process | Upload & Process | Feltoltes es feldolgozas |

---

## 9. Javitott Bugok Osszefoglalas

| # | Bug | Hol | Fix |
|---|-----|-----|-----|
| 1 | ffmpeg `acodec copy` PCM→M4A | transcript_pipeline.py | `acodec aac` kodolas |
| 2 | `transcribe()` elvesztette `chunks` adatot | transcript_pipeline.py | return-ben `chunks` + `output_dir` |
| 3 | `output_dir` hardcoded `./output` | transcript_pipeline.py | `data.get("output_dir")` |
| 4 | `merged_text` vs `full_text` kulcs | media_processor/service.py | mindket kulcs kezelese |
| 5 | Email connector test mindig "success" | Emails.tsx | `res.success` mezo ellenorzes |
| 6 | O365 IMAP BasicAuthBlocked | email_connector/service.py | informativ hibauzenet |
| 7 | Python 3.12 closure bug `except as e` | emails.py, process_docs.py | `err_msg = str(e)` mentes |
| 8 | Email skill modul nev `pipeline` → `classify` | emails.py (4 hely) | helyes modul + fuggveny nevek |
| 9 | `raw_eml_path` hiany email pipeline-ban | emails.py (4 hely) | mindenhol beallitva |
| 10 | `output_data` string nem dict | emails.py list_emails | `json.loads()` fallback |
| 11 | Frontend mezo nevek nem egyeztek backend-del | Emails.tsx | `intent_display_name`, `priority_level`, stb. |
| 12 | Email duplikat szures subject alapu | emails.py | file path stem alapu dedup |
| 13 | COM CoInitialize hiany | email_connector/service.py | `pythoncom.CoInitialize()` |
| 14 | DB `chk_ecc_provider` constraint | SQL | `outlook_com` hozzaadva |
| 15 | NaN attachments KPI | Emails.tsx | `|| 0` fallback |
| 16 | Inbox nem frissul feldolgozas utan | Emails.tsx | `refreshKey` cross-tab + `file_done` refetch |

---

## 10. Uj Fajlok Listaja

```
aiflow-admin/src/components-new/FileProgress.tsx           — 74 sor
aiflow-admin/src/components-new/ChatPanel/index.tsx        — 165 sor
aiflow-admin/src/components-new/ChatPanel/types.ts         — 48 sor
aiflow-admin/src/components-new/ChatPanel/ChatHeader.tsx   — 82 sor
aiflow-admin/src/components-new/ChatPanel/MessageBubble.tsx — 108 sor
aiflow-admin/src/components-new/ChatPanel/ChatInput.tsx    — 79 sor
aiflow-admin/src/components-new/ChatPanel/ScrollToBottom.tsx — 18 sor
aiflow-admin/src/components-new/ChatPanel/SourcesBlock.tsx  — 60 sor
aiflow-admin/src/components-new/ChatPanel/useChatHistory.ts — 53 sor
aiflow-admin/src/components-new/ChatPanel/usePromptHistory.ts — 44 sor
01_PLAN/46_RAG_CHAT_REDESIGN_PLAN.md                       — 298 sor
01_PLAN/47_SESSION4_DOCUMENTATION.md                       — ez a fajl
```

---

## 11. Rendszer Allapot (session vegen)

### Infrastruktura
- PostgreSQL 5433, Redis 6379 (Docker)
- API: port 8102, Frontend: port 5173 (Vite proxy → 8102)
- Auth: admin@bestix.hu / admin
- ffmpeg 8.0.1, OpenAI API key konfiguralt
- Outlook COM: 9 postafiok elerheto

### DB adatok
| Tabla | Rekord |
|-------|--------|
| invoices | ~7 |
| workflow_runs | 20+ (email_intent_processor: 5+) |
| rag_collections | 5 |
| rag_chunks | ~6100 |
| media_jobs | 7+ (2 completed, tobbi failed regi bug miatt) |
| email_connector_configs | 2 (IMAP + Outlook COM) |
| cost_records | 10+ |

### Email Connectorok
| Nev | Provider | Allapot |
|-----|----------|---------|
| BestIx IMAP | imap | FAIL (O365 BasicAuth blocked) |
| BestIx Outlook | outlook_com | MUKODIK (56 email letoltve) |

---

## 12. Konzisztencia Audit Eredmenyek

Az audit 7 inkonzisztenciat talalt es MIND javitva lett:

| # | Problema | Fajl | Fix |
|---|---------|------|-----|
| 1 | CLAUDE.md migracio szam 13 → 26 | CLAUDE.md | Javitva |
| 2 | CLAUDE.md services "TERVEZETT" → "KESZ" | CLAUDE.md | Javitva |
| 3 | CLAUDE.md API route szam 12 → 19 | CLAUDE.md | Javitva |
| 4 | CLAUDE.md endpoint szam 87 → 112+ | CLAUDE.md | Javitva |
| 5 | API Spec hianyzik 6 SSE endpoint | 22_API_SPECIFICATION.md | SSE szekcioval bovitve |
| 6 | Master Plan 31 → 47 dokumentum | AIFLOW_MASTER_PLAN.md | Bovitve (42-47 tervek) |
| 7 | chk_ecc_provider raw SQL fix | Alembic 026 | Migracio letrehozva |
| 8 | DB Schema migracio szam 25 → 26 | 03_DATABASE_SCHEMA.md | Javitva |

### Pozitiv eredmenyek (NINCS problema)
- API router regisztracio: 19/19 ✓
- Frontend router: 17/17 oldal ✓
- ChatPanel importok: Rag.tsx + RagDetail.tsx ✓
- Sidebar menu ↔ router.tsx ✓
- vite.config.ts proxy: 8102 ✓
- package.json fuggosegek: komplett ✓
- Alembic migracok: konzisztens lanc ✓
- F0-F5 success criteria: valid ✓
