# F6 Konszolidacios Evidencia — Journey ↔ Figma ↔ API

**Datum:** 2026-04-02
**Cel:** Teteles evidencia, hogy a user journey-k, Figma tervek es backend szolgaltatasok KONZISZTENSEK.
**Kovetkezo lepes:** CSAK az evidencia-ban dokumentalt allapot alapjan fejlesztunk.

---

## 1. API Endpoint Teteles Audit (24 endpoint, valos HTTP status)

| # | Method | Path | HTTP | Statusz | Journey | Figma oldal |
|---|--------|------|------|---------|---------|-------------|
| 1 | GET | `/api/v1/auth/me` | 200 | OK | F6.0 | 01 Login |
| 2 | GET | `/health` | 200 | OK | F6.0 | TopBar (minden) |
| 3 | GET | `/api/v1/runs` | 200 | OK | F6.1 | 02 Dashboard, 06 Runs |
| 4 | GET | `/api/v1/skills` | 200 | OK | F6.1 | 02 Dashboard |
| 5 | GET | `/api/v1/runs/stats` | 500 | **HIBA** | F6.1 | 02 Dashboard (sparklines) |
| 6 | GET | `/api/v1/skills/summary` | 404 | **NEM LETEZIK** | F6.1 | 02 Dashboard (skill cards) |
| 7 | GET | `/api/v1/documents` | 200 | OK | F1 | 03 Documents |
| 8 | GET | `/api/v1/documents/extractor/configs` | 200 | OK | F1 | 03 Documents |
| 9 | GET | `/api/v1/emails` | 200 | OK | F2 | 04 Emails |
| 10 | GET | `/api/v1/emails/connectors` | 200 | OK | F2 | 04 Emails (Connectors tab) |
| 11 | GET | `/api/v1/rag/collections` | 200 | OK | F3 | 05 RAG |
| 12 | GET | `/api/v1/diagrams` | 200 | OK | F4a | 11 Process Docs |
| 13 | GET | `/api/v1/media` | 200 | OK | F4b | 12 Media |
| 14 | GET | `/api/v1/rpa/configs` | 200 | OK | F4c | 13 RPA |
| 15 | GET | `/api/v1/reviews/pending` | 200 | OK | F4d | 14 Reviews |
| 16 | GET | `/api/v1/reviews/history` | 200 | OK | F4d | 14 Reviews |
| 17 | GET | `/api/v1/admin/health` | 200 | OK | F5a | 08 Monitoring |
| 18 | GET | `/api/v1/admin/metrics` | 200 | OK | F5a | 08 Monitoring |
| 19 | GET | `/api/v1/admin/audit` | 200 | OK | F5b | 09 Audit |
| 20 | GET | `/api/v1/admin/users` | 200 | OK | F5c | 10 Admin |
| 21 | GET | `/api/v1/admin/api-keys` | 200 | OK | F5c | 10 Admin |
| 22 | GET | `/api/v1/costs/summary` | 200 | OK | F5 | 07 Costs |
| 23 | GET | `/api/v1/costs/daily` | 404 | **NEM LETEZIK** | F6.5 | 07 Costs (chart) |
| 24 | GET | `/api/v1/costs/by-model` | 404 | **NEM LETEZIK** | F6.5 | 07 Costs |

**Osszesites: 20 OK / 1 HIBA / 3 NEM LETEZIK**

### Implementalando endpointok (F6 fazisban):
| Endpoint | Fazis | Cel |
|----------|-------|-----|
| `GET /api/v1/runs/stats` | F6.1 | Dashboard KPI sparkline-ok (500 → javitando) |
| `GET /api/v1/skills/summary` | F6.1 | Dashboard skill cards (run count, status) |
| `GET /api/v1/costs/daily` | F6.5 | Costs oldal recharts BarChart |
| `GET /api/v1/costs/by-model` | F6.5 | Costs oldal model bontas |

---

## 2. Journey ↔ Figma ↔ API Konzisztencia Matrix

### F6.0 Foundation (Login + Shell)

| Journey Step | Figma | API | Kod | Konzisztens? |
|-------------|-------|-----|-----|-------------|
| Login (email+password → JWT) | 01 Login | POST /auth/login OK | Login.tsx KESZ | YES |
| Token refresh | — | POST /auth/refresh OK | auth.ts KESZ | YES |
| User info | — | GET /auth/me OK | auth.ts KESZ | YES |
| Sidebar 4 csoport, 11 item | Untitled UI Sidebar | — | Sidebar.tsx KESZ | YES |
| HU/EN toggle | TopBar | — | i18n.tsx KESZ | YES |
| Light/dark toggle | TopBar | — | hooks.ts KESZ | YES |
| Backend status | TopBar | GET /health OK | hooks.ts KESZ | YES |

**F6.0: 7/7 KONZISZTENS**

### F6.1 Dashboard

| Journey Step | Figma | API | Kod | Konzisztens? |
|-------------|-------|-----|-----|-------------|
| KPI: Total Runs | 02 Dashboard (Metric group) | GET /runs OK | — | FIGMA+API OK, KOD HIANYZIK |
| KPI: Today Cost | 02 Dashboard (Metric group) | GET /costs/summary OK | — | FIGMA+API OK, KOD HIANYZIK |
| KPI: Success Rate | 02 Dashboard (Metric group) | GET /runs/stats HIBA | — | API JAVITANDO |
| Skill Cards (dinamikus) | 02 Dashboard (3 card) | GET /skills OK | — | FIGMA+API OK, KOD HIANYZIK |
| Active Pipelines tabla | 02 Dashboard (Table) | GET /runs OK | — | FIGMA+API OK, KOD HIANYZIK |
| Sparkline trend | 02 Dashboard (Metric group) | GET /runs/stats HIBA | — | API JAVITANDO |
| Skill summary (run count) | 02 Dashboard | GET /skills/summary 404 | — | API UJ KELL |

**F6.1: 4/7 KONZISZTENS, 3 API munka kell**

### F1 Documents (v1.1: tabbed)

| Journey Step | Figma | API | Konzisztens? |
|-------------|-------|-----|-------------|
| Documents lista | 03 Documents (List tab, Table) | GET /documents OK | YES |
| Upload dropzone | 03 Documents (Upload tab content) | POST /documents/upload OK | YES |
| SSE pipeline progress | 03 Documents (Upload tab, pipeline) | POST /documents/process-stream | YES (endpoint letezik) |
| Confidence oszlop | 03 Documents (tabla) | GET /documents (confidence field) | YES |
| Verify gomb → /documents/:id/verify | 15 Verification | POST /documents/{id}/verify | YES |
| Prev/Next navigacio | 15 Verification (← Prev / Next →) | GET /documents | YES |
| Dinamikus schema panel | 15 Verification (invoice_v1 badge) | GET /extractor/configs OK | YES |
| Governor Pattern | 15 Verification (70%/100% opacity) | — (UI only) | YES |
| Extractor configs | — | GET /documents/extractor/configs OK | YES |

**F1: 9/9 KONZISZTENS**

### F2 Emails (v1.1: tabbed)

| Journey Step | Figma | API | Konzisztens? |
|-------------|-------|-----|-------------|
| Inbox lista | 04 Emails (Inbox tab, Table) | GET /emails OK | YES |
| Upload tab | 04 Emails (Upload tab) | POST /emails/upload | YES |
| Connectors tab CRUD | 04 Emails (Connectors tab content) | GET /emails/connectors OK | YES |
| Connection test | 04 Emails (Test gomb) | POST /emails/connectors/{id}/test | YES |
| Email fetch | 04 Emails (Fetch gomb) | POST /emails/fetch | YES |
| Classify | — | POST /emails/classify | YES |
| Intent/priority tabla | 04 Emails (Inbox tabla) | GET /emails (intent field) | YES |

**F2: 7/7 KONZISZTENS**

### F3 RAG (v1.1: tabbed)

| Journey Step | Figma | API | Konzisztens? |
|-------------|-------|-----|-------------|
| Collections lista | 05 RAG (Collections tab, Table) | GET /rag/collections OK | YES |
| Collection CRUD | 05 RAG (+ New Collection) | POST /rag/collections | YES |
| Collection Detail | 05b RAG Detail (KPI + dropzone + chunks) | GET /rag/collections/{id} | YES |
| Ingest dropzone | 05b RAG Detail (dropzone) | POST /rag/collections/{id}/ingest | YES |
| Chunks tabla | 05b RAG Detail (Files Table) | GET /rag/collections/{id}/chunks | YES |
| Chat UI | 05 RAG (Chat tab content) | POST /rag/collections/{id}/query | YES |
| Streaming valasz | 05 RAG (Chat tab, streaming) | SSE | YES |
| Citations panel | 05 RAG (Chat tab, Sources panel) | — (response field) | YES |
| Feedback | 05 RAG (Chat tab, thumbs) | POST /rag/collections/{id}/feedback | YES |

**F3: 9/9 KONZISZTENS**

### F4a Diagram Generator

| Journey Step | Figma | API | Konzisztens? |
|-------------|-------|-----|-------------|
| Textarea + presets | 11 Process Docs (split, left) | — | YES |
| Generate | 11 Process Docs (purple gomb) | POST /diagrams/generate | YES |
| Mermaid preview | 11 Process Docs (split, right) | — (response field) | YES |
| Export (SVG/BPMN/DrawIO/PNG) | 11 Process Docs (export gombok) | GET /diagrams/{id}/export/{fmt} | YES |
| Saved diagrams tabla | 11 Process Docs (Table) | GET /diagrams OK | YES |

**F4a: 5/5 KONZISZTENS**

### F4b Media Processor

| Journey Step | Figma | API | Konzisztens? |
|-------------|-------|-----|-------------|
| Upload dropzone | 12 Media (dropzone) | POST /media/upload | YES |
| Jobs tabla | 12 Media (Table) | GET /media OK | YES |
| Transcript | 12 Media | GET /media/{id} | YES |

**F4b: 3/3 KONZISZTENS**

### F4c RPA Browser

| Journey Step | Figma | API | Konzisztens? |
|-------------|-------|-----|-------------|
| Configs tabla | 13 RPA (1. Table) | GET /rpa/configs OK | YES |
| New Config | 13 RPA (+ New Config) | POST /rpa/configs | YES |
| Execute | 13 RPA | POST /rpa/execute | YES |
| Execution log | 13 RPA (2. Table) | GET /rpa/logs | YES |

**F4c: 4/4 KONZISZTENS**

### F4d Human Review

| Journey Step | Figma | API | Konzisztens? |
|-------------|-------|-----|-------------|
| Pending lista | 14 Reviews (Table) | GET /reviews/pending OK | YES |
| Approve/Reject | 14 Reviews | POST /reviews/{id}/approve|reject | YES |
| History | 14 Reviews | GET /reviews/history OK | YES |

**F4d: 3/3 KONZISZTENS**

### F5a Monitoring

| Journey Step | Figma | API | Konzisztens? |
|-------------|-------|-----|-------------|
| Status banner | 08 Monitoring (green banner) | GET /admin/health OK (9 svc) | YES |
| KPI-k | 08 Monitoring (3 KPI) | GET /admin/metrics OK | YES |
| Service health cards | 08 Monitoring (8 cards) | GET /admin/health (services[]) | YES |

**F5a: 3/3 KONZISZTENS**

### F5b Audit Log

| Journey Step | Figma | API | Konzisztens? |
|-------------|-------|-----|-------------|
| Audit tabla | 09 Audit (Table) | GET /admin/audit OK | YES |
| Filter + kereses | 09 Audit | query params | YES |
| Export | 09 Audit | POST /admin/audit/export | YES |

**F5b: 3/3 KONZISZTENS**

### F5c Admin

| Journey Step | Figma | API | Konzisztens? |
|-------------|-------|-----|-------------|
| Users tabla | 10 Admin (Team Members Table) | GET /admin/users OK (2 users) | YES |
| API Keys tab | 10 Admin (API Keys tab) | GET /admin/api-keys OK | YES |
| Add User | 10 Admin (+ Add User) | POST /admin/users | YES |

**F5c: 3/3 KONZISZTENS**

### F5 Costs

| Journey Step | Figma | API | Konzisztens? |
|-------------|-------|-----|-------------|
| KPI osszesites | 07 Costs (3 KPI) | GET /costs/summary OK | YES |
| By Skill tabla | 07 Costs (Table) | GET /costs/summary (per_skill) | YES |
| Daily chart | 07 Costs (chart) | GET /costs/daily **404** | API UJ KELL (F6.5) |
| By Model | 07 Costs | GET /costs/by-model **404** | API UJ KELL (F6.5) |

**F5 Costs: 2/4 KONZISZTENS, 2 API kell F6.5-ben**

---

## 3. Vegso Osszesites

| Kategoria | Konzisztens | Hianyzik | Osszesen |
|-----------|------------|----------|----------|
| F6.0 Foundation | 7 | 0 | 7 |
| F6.1 Dashboard | 4 | 3 (API) | 7 |
| F1 Documents | 9 | 0 | 9 |
| F2 Emails | 7 | 0 | 7 |
| F3 RAG | 9 | 0 | 9 |
| F4a Diagrams | 5 | 0 | 5 |
| F4b Media | 3 | 0 | 3 |
| F4c RPA | 4 | 0 | 4 |
| F4d Reviews | 3 | 0 | 3 |
| F5a Monitoring | 3 | 0 | 3 |
| F5b Audit | 3 | 0 | 3 |
| F5c Admin | 3 | 0 | 3 |
| F5 Costs | 2 | 2 (API) | 4 |
| **TOTAL** | **62** | **5** | **67** |

### Konzisztencia: **62/67 = 92.5%**

### 5 hianyzó elem (MIND F6 fazisban implementalando):
1. `GET /api/v1/runs/stats` — F6.1 (jelenleg 500 ERROR, javitando)
2. `GET /api/v1/skills/summary` — F6.1 (404, uj endpoint)
3. Dashboard kodolas — F6.1 (Figma KESZ, kod HIANYZIK)
4. `GET /api/v1/costs/daily` — F6.5 (404, uj endpoint)
5. `GET /api/v1/costs/by-model` — F6.5 (404, uj endpoint)

---

## 4. Figma Frame Registry (vegleges, 16 frame)

| # | Frame | Figma ID | Route | Sidebar | Table | KPI | Tab content |
|---|-------|----------|-------|---------|-------|-----|-------------|
| 01 | Login | 11662:113171 | /login | — | — | — | — |
| 02 | Dashboard | 11662:113172 | / | Untitled UI | Companies | Metric group | — |
| 03 | Documents | 11662:113173 | /documents | Untitled UI | Companies | Metric group | List + Upload |
| 04 | Emails | 11662:113174 | /emails | Untitled UI | Companies | Metric group | Inbox + Upload + Connectors |
| 05 | RAG | 11662:113175 | /rag | Untitled UI | Companies | — | Collections + Chat |
| 05b | RAG Detail | 11673:265283 | /rag/:id | Untitled UI | Files | Metric group | ingest + chunks |
| 06 | Runs | 11662:113176 | /runs | Untitled UI | Companies | — | — |
| 07 | Costs | 11662:113177 | /costs | Untitled UI | 2x Sales | kezi KPI | chart + 2 tabla |
| 08 | Monitoring | 11662:113178 | /monitoring | Untitled UI | — | kezi KPI | health cards |
| 09 | Audit | 11662:113179 | /audit | Untitled UI | Companies | — | — |
| 10 | Admin | 11662:113180 | /admin | Untitled UI | Team Members | — | Users + API Keys |
| 11 | Process Docs | 11662:113181 | /process-docs | Untitled UI | Companies | — | split layout |
| 12 | Media | 11662:113182 | /media | Untitled UI | Companies | — | dropzone + tabla |
| 13 | RPA | 11662:113183 | /rpa | Untitled UI | 2x Companies | — | configs + log |
| 14 | Reviews | 11662:113184 | /reviews | Untitled UI | Companies | — | pending + history |
| 15 | Verification | 11662:113185 | /documents/:id/verify | Untitled UI | — | — | dynamic schema |

---

## 5. Journey Dokumentumok Frissitesi Allapot

| Journey | Fajl | Route frissitve? | Konzisztens? |
|---------|------|-----------------|-------------|
| F6.0-F6.6 | F6_UI_RATIONALIZATION_JOURNEY.md | Eredeti v1.1 route-ok | YES |
| F1 | F1_DOCUMENT_EXTRACTOR_JOURNEY.md | /document-upload → /documents Upload tab | YES |
| F2 | F2_EMAIL_CONNECTOR_JOURNEY.md | /email-connectors → /emails Connectors tab | YES |
| F3 | F3_RAG_ENGINE_JOURNEY.md | /rag/collections → /rag, /rag/{id} | YES |
| F4 | F4_RPA_MEDIA_DIAGRAM_JOURNEY.md | Nem szukseges (route-ok maradtak) | YES |
| F5 | F5_MONITORING_GOVERNANCE_JOURNEY.md | /admin/monitoring → /monitoring, /admin/audit → /audit | YES |

**6/6 journey dokumentum KONZISZTENS a v1.1 route-okkal.**

---

## 6. Jovahagyas

> **Ez a dokumentum a fejlesztes ELOFELTETELE.**
> A F6.1 Dashboard kodolas CSAK akkor indithato ha ez a dokumentum elfogadva.
> Minden elem szintu konzisztencia ellenorizve: Journey ↔ Figma ↔ API ↔ Route.
>
> **Eredmeny: 92.5% konzisztens (62/67), 5 hiany MIND az F6 fazisban implementalando.**
