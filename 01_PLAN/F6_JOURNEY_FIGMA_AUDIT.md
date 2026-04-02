# F6 Journey ↔ Figma Design Audit

**Datum:** 2026-04-02
**Cel:** Journey dokumentumok es Figma v1.1 designok osszehasonlitasa, elteresek azonositasa, racionalizacio.

---

## 1. Route Mapping — Journey vs v1.1 Konszolidacio

| Journey | Eredeti Route | v1.1 Route | Valtozas |
|---------|---------------|------------|----------|
| F1 Doc Upload | `/document-upload` | `/documents` (Upload tab) | KONSZOLIDALT |
| F1 Doc List | `/documents` | `/documents` (List tab) | MARAD |
| F1 Verify | `/documents/:id/verify` | `/documents/:id/verify` | MARAD |
| F2 Connectors | `/email-connectors` | `/emails` (Connectors tab) | KONSZOLIDALT |
| F2 Email Upload | `/email-upload` | `/emails` (Upload tab) | KONSZOLIDALT |
| F2 Email List | `/emails` | `/emails` (Inbox tab) | MARAD |
| F3 Collections | `/rag/collections` | `/rag` (Collections tab) | KONSZOLIDALT |
| F3 Collection Detail | `/rag/collections/:id` | `/rag/:id` | EGYSZERUSITETT |
| F3 RAG Chat | `/rag-chat` | `/rag` (Chat tab) | KONSZOLIDALT |
| F4a Process Docs | `/process-docs` | `/process-docs` | MARAD |
| F4b Media | `/media` | `/media` | MARAD |
| F4c RPA | `/rpa` | `/rpa` | MARAD |
| F4d Reviews | `/reviews` | `/reviews` | MARAD |
| F5a Monitoring | `/admin/monitoring` | `/monitoring` | EGYSZERUSITETT |
| F5b Audit | `/admin/audit` | `/audit` | EGYSZERUSITETT |
| F5c Admin | `/admin/users` | `/admin` | EGYSZERUSITETT |

---

## 2. Journey Step ↔ Figma Audit (Hianyok es Elteresek)

### F1 Document Extractor (Figma: 03 Documents + 15 Verification)

| Journey Step | Figma-ban latszik? | Hianyzik/Javitando |
|-------------|-------------------|-------------------|
| 1. Drag-drop upload | Tab bar van ("Upload") de a dropzone nem latszik a List tab-on | HIANYZIK: Upload tab content (dropzone + progress) |
| 2. SSE processing pipeline (6 lepes) | Nem latszik | HIANYZIK: PipelineProgress komponens az Upload tab-ban |
| 3. Eredmenyek attekintese (confidence %) | Tabla van de confidence oszlop nem latszik | HIANYZIK: Confidence oszlop a tablaban |
| 4. Verify gomb → Verification oldal | Verification oldal MEGVAN (15. frame) | OK |
| 5. Mezo verifikacio (Governor Pattern) | Confidence badge-ek, szekciok, ⚠ jeloles | OK |
| 6. Prev/Next doc navigacio | MEGVAN (← Prev / Next →) | OK |
| 7. Batch operations | Nem latszik | HIANYZIK: "Process All" / "Verify All" gombok |

**Teendo:** Upload tab-hoz kell dropzone + pipeline progress design.

### F2 Email Connector + Classifier (Figma: 04 Emails)

| Journey Step | Figma-ban latszik? | Hianyzik/Javitando |
|-------------|-------------------|-------------------|
| 1. Connector CRUD | Tab bar van ("Connectors") de content nem latszik | HIANYZIK: Connectors tab content |
| 2. Connection test (WiFi ikon) | Nem latszik | HIANYZIK: Test gomb a connector sorban |
| 3. Email fetch (Play ikon) | Nem latszik | HIANYZIK: Fetch gomb |
| 4. Fetch history | Nem latszik | HIANYZIK: History slide-over |
| 5. Email lista (intent, priority) | Inbox tab tabla van | OK (tartalom minta adat) |
| 6. Email detail (entity highlight) | Nem latszik | HIANYZIK: Email detail slide-over / expand |
| 7. Upload tab | Tab bar-on latszik | HIANYZIK: Upload tab content |
| 8. Klasszifikacio eredmeny | Nem latszik | HIANYZIK: Intent/confidence badge a tablaban |

**Teendo:** Connectors + Upload tab content, email detail nezet.

### F3 RAG Engine (Figma: 05 RAG)

| Journey Step | Figma-ban latszik? | Hianyzik/Javitando |
|-------------|-------------------|-------------------|
| 1. Kollekcio CRUD | Collections tab tabla van | OK (tartalom minta adat) |
| 2. Kollekcio detail (ingest + chunks) | Kulon oldal tervezve (`/rag/:id`) | HIANYZIK: Figma frame a detail-hoz |
| 3. Dokumentum ingest (drag-drop) | Nem latszik | HIANYZIK: Ingest dropzone a detail oldalon |
| 4. RAG Chat (streaming) | Chat tab a tab bar-on | HIANYZIK: Chat tab content (chat UI) |
| 5. Citation panel | Nem latszik | HIANYZIK: Chat valasz melletti forras panel |
| 6. Feedback (thumbs up/down) | Nem latszik | HIANYZIK: Feedback gombok |
| 7. Statisztikak | Nem latszik | HIANYZIK: KPI kártyak a detail oldalon |

**Teendo:** Chat tab content + Collection Detail frame + Ingest UI.

### F4a Diagram Generator (Figma: 11 Process Docs)

| Journey Step | Figma-ban latszik? | Hianyzik/Javitando |
|-------------|-------------------|-------------------|
| 1. Textarea + presets | MEGVAN (split layout) | OK |
| 2. Generate gomb | MEGVAN (purple gomb) | OK |
| 3. Mermaid preview | MEGVAN (jobb panel) | OK |
| 4. Export gombok (SVG/BPMN/DrawIO/PNG) | MEGVAN | OK |
| 5. Saved diagrams tabla | MEGVAN (Untitled UI Table) | OK |
| 6. Review score | Nem latszik | HIANYZIK: Quality score a preview-ban |

**Teendo:** Review score hozzaadasa.

### F4b Media Processor (Figma: 12 Media)

| Journey Step | Figma-ban latszik? | Hianyzik/Javitando |
|-------------|-------------------|-------------------|
| 1. Upload dropzone | MEGVAN | OK |
| 2. Jobs tabla | MEGVAN (Untitled UI Table) | OK |
| 3. Transcript preview | Nem latszik | HIANYZIK: Transcript panel kijelolve |
| 4. STT provider valasztas | Nem latszik | HIANYZIK: Provider dropdown |

**Teendo:** Transcript preview panel.

### F4c RPA Browser (Figma: 13 RPA)

| Journey Step | Figma-ban latszik? | Hianyzik/Javitando |
|-------------|-------------------|-------------------|
| 1. Config CRUD | MEGVAN (tabla + New Config gomb) | OK |
| 2. YAML editor | Nem latszik | HIANYZIK: YAML config mezo a config dialogban |
| 3. Execution | Nem latszik a Run gomb | HIANYZIK: Play gomb a config sorban |
| 4. Execution log | MEGVAN (2. tabla) | OK |
| 5. Screenshot preview | Nem latszik | HIANYZIK: Screenshot a log detail-ben |

**Teendo:** Run gomb + screenshot preview.

### F4d Human Review (Figma: 14 Reviews)

| Journey Step | Figma-ban latszik? | Hianyzik/Javitando |
|-------------|-------------------|-------------------|
| 1. Pending lista | MEGVAN (tabla) | OK |
| 2. Approve/Reject gombok | Nem latszik (Untitled UI Table cserelve) | HIANYZIK: Action gombok |
| 3. Comment dialog | Nem latszik | HIANYZIK: Megerosito dialog |
| 4. History | MEGVAN (2. tabla) | HIANYZIK: Kulon History szekció |

**Teendo:** Approve/Reject akció gombok.

### F5a Monitoring (Figma: 08 Monitoring)

| Journey Step | Figma-ban latszik? | Hianyzik/Javitando |
|-------------|-------------------|-------------------|
| 1. Status banner | MEGVAN | OK |
| 2. KPI-k (services, latency, uptime) | MEGVAN | OK |
| 3. Service health cards | MEGVAN (8 kartya) | OK |
| 4. Per-service detail | Nem latszik | HIANYZIK: Kattintasra reszletek |
| 5. Riasztasi szabalyok | Nem latszik | HIANYZIK: Alert config |

**Teendo:** Service detail expand.

### F5b Audit Log (Figma: 09 Audit)

| Journey Step | Figma-ban latszik? | Hianyzik/Javitando |
|-------------|-------------------|-------------------|
| 1. Filter row | Tabla header van | OK |
| 2. Kereses | Tabla header van | OK |
| 3. Export (CSV/JSON) | Nem latszik | HIANYZIK: Export gomb |
| 4. Detail dialog | Nem latszik | HIANYZIK: Sor kattintasra detail |

**Teendo:** Export gomb + detail.

### F5c Admin (Figma: 10 Admin)

| Journey Step | Figma-ban latszik? | Hianyzik/Javitando |
|-------------|-------------------|-------------------|
| 1. User CRUD | MEGVAN (Team Members Table) | OK |
| 2. API Key management | Tab bar-on latszik ("API Keys") | HIANYZIK: API Keys tab content |
| 3. Add User dialog | "+ Add User" gomb MEGVAN | OK |
| 4. Role badges | A tablaban badge-ek latszanak | OK |

**Teendo:** API Keys tab content.

---

## 3. Osszefoglalo — Prioritasos Hianyok

### KRITIKUS (journey core flow nem lathato):
1. **Documents Upload tab** — dropzone + SSE pipeline progress content
2. **Emails Connectors tab** — connector CRUD content
3. **RAG Chat tab** — chat UI content (streaming, citations)
4. **RAG Collection Detail** — kulon frame hianyzik (ingest + chunks + stats)

### FONTOS (UX teljesség):
5. **Documents** — Confidence oszlop a tablaban
6. **Emails** — Email detail nezet (intent breakdown, entity highlight)
7. **Emails Upload tab** — upload content
8. **Reviews** — Approve/Reject akció gombok (Untitled UI Table csere elvitte)
9. **Audit** — Export gomb + detail dialog

### NICE-TO-HAVE:
10. Process Docs — Review score
11. Media — Transcript preview panel
12. RPA — Run gomb + YAML editor
13. Monitoring — Service detail expand
14. Admin — API Keys tab content

---

## 4. Javasolt Racionalizacio a Journey-kben

### Route frissitesek (journey docs frissitendo):
- F1: `/document-upload` → `/documents` (Upload tab) hivatkozas
- F2: `/email-connectors` → `/emails` (Connectors tab)
- F2: `/email-upload` → `/emails` (Upload tab)
- F3: `/rag/collections` → `/rag` (Collections tab)
- F3: `/rag-chat` → `/rag` (Chat tab)
- F5a: `/admin/monitoring` → `/monitoring`
- F5b: `/admin/audit` → `/audit`
- F5c: `/admin/users` → `/admin`

### UX egyszerusitesek:
- **Tabbed oldalak**: a felhasznalo EGY oldalon belul tud navigalni a teljes domain workflow-ban
- **Slide-over detail**: email/run detail ne uj oldalra vigyen, hanem jobb oldali slide-over panel
- **Inline actions**: Approve/Reject, Run, Test gombok kozvetlenul a tabla sorokban
- **Progressive disclosure**: osszetett funkciok (YAML editor, export options) dialogban

---

## 5. Elvegzett Javitasok (2026-04-02)

### Figma kiegeszitesek (4 KRITIKUS potolva):
- [x] Documents "Upload" tab content: dropzone + SSE pipeline progress + batch status
- [x] Emails "Connectors" tab content: connector CRUD tabla + Test/Fetch gombok + history
- [x] RAG "Chat" tab content: chat UI + streaming + citation panel + feedback + hallucination
- [x] RAG Collection Detail (05b frame): ← Back + KPI Metric group + ingest dropzone + Chunks tabla

### Journey route frissitesek (6 doc frissitve):
- [x] F1: `/document-upload` → `/documents` Upload tab
- [x] F2: `/email-connectors` → `/emails` Connectors tab
- [x] F3: `/rag/collections` → `/rag` Collections tab
- [x] F3: `/rag/collections/{id}` → `/rag/{id}`
- [x] F5a: `/admin/monitoring` → `/monitoring`
- [x] F5b: `/admin/audit` → `/audit`

---

## 6. Szolgaltatas Ellenorzes (API endpoint audit, 2026-04-02)

| Journey | Endpoint | Statusz | Megjegyzes |
|---------|----------|---------|------------|
| F6.0 Auth | `/api/v1/auth/login` | OK | JWT token |
| F6.0 Auth | `/api/v1/auth/me` | OK | user_id + role |
| F6.1 Dashboard | `/api/v1/runs` | OK | 0 items (ures DB) |
| F6.1 Dashboard | `/api/v1/skills` | OK | Letezik |
| F6.1 Dashboard | `/api/v1/runs/stats` | **HIANYZIK** | F6.1-ben implementalando |
| F1 Documents | `/api/v1/documents` | OK | source=backend |
| F1 Documents | `/api/v1/extractor/configs` | **FAIL** | Endpoint ellenorizendo |
| F2 Emails | `/api/v1/emails` | OK | source=backend |
| F2 Emails | `/api/v1/emails/connectors` | **FAIL** | Endpoint ellenorizendo |
| F3 RAG | `/api/v1/rag/collections` | OK | 1 collection, source=backend |
| F4a Diagrams | `/api/v1/diagrams` | OK | source=backend |
| F4b Media | `/api/v1/media` | OK | source=backend |
| F4c RPA | `/api/v1/rpa/configs` | OK | source=backend |
| F4d Reviews | `/api/v1/reviews/pending` | OK | source=backend |
| F5a Monitoring | `/api/v1/admin/health` | OK | 9 services |
| F5b Audit | `/api/v1/admin/audit` | OK | source=backend |
| F5c Admin | `/api/v1/admin/users` | OK | 2 users |
| F5 Costs | `/api/v1/costs/summary` | OK | Letezik |

**Eredmeny: 15/18 OK, 1 UJ (F6.1), 2 ellenorizendo**

### Hianyzó endpointok (F6.1-ben implementalandó):
- `GET /api/v1/runs/stats` — 7 napos trend (napi run count, cost, success rate)

### Ellenorizendo (lehet route nev elteres):
- `/api/v1/extractor/configs` — lehet hogy `/api/v1/documents/extractor/configs`
- `/api/v1/emails/connectors` — lehet hogy mas prefix

---

## 7. Vegleges Osszefoglalo Tablazat

| # | Oldal | Journey | Figma | API | Tab content | Sidebar |
|---|-------|---------|-------|-----|-------------|---------|
| 01 | Login | F6.0 OK | OK | OK | — | — |
| 02 | Dashboard | F6.1 OK | OK | 1 UJ endpoint | — | Untitled UI |
| 03 | Documents | F1 FRISSITETT | OK + Upload tab | OK | List + Upload | Untitled UI |
| 04 | Emails | F2 FRISSITETT | OK + Connectors tab | ellenorizendo | Inbox + Upload + Connectors | Untitled UI |
| 05 | RAG | F3 FRISSITETT | OK + Chat tab | OK | Collections + Chat | Untitled UI |
| 05b | RAG Detail | F3 OK | UJ FRAME | OK | ingest + chunks | Untitled UI |
| 06 | Runs | F6 OK | OK | OK | — | Untitled UI |
| 07 | Costs | F5 OK | OK | OK | — | Untitled UI |
| 08 | Monitoring | F5a FRISSITETT | OK | OK | — | Untitled UI |
| 09 | Audit | F5b FRISSITETT | OK | OK | — | Untitled UI |
| 10 | Admin | F5c OK | OK | OK | Users + API Keys | Untitled UI |
| 11 | Process Docs | F4a OK | OK | OK | — | Untitled UI |
| 12 | Media | F4b OK | OK | OK | — | Untitled UI |
| 13 | RPA | F4c OK | OK | OK | — | Untitled UI |
| 14 | Reviews | F4d OK | OK | OK | — | Untitled UI |
| 15 | Verification | F1 OK | OK | OK | — | Untitled UI |

---

## 8. Kovetkezo Lepesek

1. **F6.1 Dashboard kodolas** — Tailwind implementacio a Figma design alapjan
2. **`/api/v1/runs/stats` endpoint** — backend implementacio
3. **Email connectors endpoint** — route prefix ellenorzes es javitas
4. **Extractor configs endpoint** — route prefix ellenorzes es javitas
5. **Folytatás:** F6.2 Documents → F6.3 Emails → F6.4 RAG+AI → F6.5 Ops+Admin → F6.6 Polish
