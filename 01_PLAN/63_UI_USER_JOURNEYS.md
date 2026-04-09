# AIFlow Portal — UI User Journeys v1 (B6 Design Document)

> **Sprint:** B (v1.3.0 service-excellence) | **Session:** S31 | **Gate:** B6
> **Date:** 2026-04-10 | **Branch:** `feature/v1.3.0-service-excellence` | **HEAD:** `c7079c6`
> **Session type:** DESIGN-FIRST — 0 kódváltoztatás, csak tervezés + wireframe + dokumentáció
> **Validáció:** 2-körös `plan-validator` subagent audit (see `out/b6_validation_round{1,2}.md`)
> **Előzmények:** 58 plan B6 szekció (sor 1313-1553), B5.1 diagram hardening, B5.2 spec_writer new skill
> **Következő session:** S32 = B7 Verification Page v2 → S33 = B8 UI Journey implementation

---

## Célok

Ez a dokumentum a **teljes AIFlow portal szerkezetét és navigációját** gondolja újra, hogy a felhasználó **feladatorientált user journey-ken** keresztül érjen célt, ne szolgáltatás-orientált menükön. A jelenlegi technikai csoportosítás (OPERATIONS / DATA / AI SERVICES / ORCHESTRATION / ADMIN) nem tükrözi, hogyan dolgoznak a felhasználók: ők **feladatot akarnak elvégezni** (szamlát feldolgozni, tudásbázisból kérdezni, diagramot generálni, rendszert monitorozni), nem "operációkat" böngészni.

**B6 kimenet:**
1. **§ 1** — 23 oldal Portal Audit (jelenlegi állapot, mi működik, mi demo, mi halott)
2. **§ 2** — Új Information Architecture (6 felhasználói cél-csoport, journey-alapú sidebar)
3. **§ 3** — Holisztikus User Journey Map (ASCII art + kereszt-referencia tábla)
4. **§ 4** — 4 reszletes user journey definíció (entry → lépések → backend → oldalak → hiányzó)
5. **§ 5** — Navigációs wireframe (sidebar + dashboard, ASCII + Figma hook)
6. **§ 6** — B8 migrációs priorizált terv (demo → backend)

**Scope korlátok (design-only session szabályok):**
- NINCS `.tsx` szerkesztés
- NINCS `router.tsx` változtatás
- NINCS új API endpoint
- NINCS új teszt
- NINCS Alembic migráció
- CSAK ez a dokumentum + PAGE_SPECS.md journey mapping + 58 plan B6 DONE marker

**Forrás referenciák (mielőtt olvasod):**
- `01_PLAN/58_POST_SPRINT_HARDENING_PLAN.md` sor 1313-1553 — B6 szekció
- `aiflow-admin/src/pages-new/*.tsx` — 23 oldal forrás
- `aiflow-admin/src/layout/Sidebar.tsx` — jelenlegi 5-csoportos sidebar
- `aiflow-admin/src/router.tsx` — 23 route (29 útvonal + redirect)
- `aiflow-admin/figma-sync/PAGE_SPECS.md` — Figma per-oldal specifikáció
- Legacy F1-F6 journey dokumentumok (`01_PLAN/F{1..6}_*_JOURNEY.md`) — olvasható referencia

---

## § 1 — Portal Audit (23 oldal, jelenlegi állapot)

### Metódus

Minden `aiflow-admin/src/pages-new/*.tsx` fájlt felmérünk a következő kérdésekre:

- **Cél:** 1 mondatos leírás, mit csinál az oldal
- **Mi működik:** valós `/api/v1/*` hívások, source badge "Backend", komplett komponens
- **Mi NEM működik:** hardcoded mock data, TODO komment, `onClick={() => {}}` stub, hiányzó feature
- **Kategória:**
  - **A** = működik end-to-end, nincs tennivaló
  - **B** = UI van, backend részleges → B8-ban javítandó
  - **C** = UI van, backend stub/demo/tört → Sprint C-re halasztva
- **Journey:** melyik user journey-hez tartozik (1/2/3/4/ENTRY/BEALLITASOK/ADMIN/—)

### 23 Oldal Audit Tábla

| # | Oldal | Route | Cél | Mi működik | Mi NEM működik | Kat. | Journey |
|---|-------|-------|-----|-----------|----------------|------|---------|
| 1 | Login | `/login` | JWT auth + locale toggle | Form submit auth service-hez, HU/EN toggle | Nincs MFA/SSO/password reset, placeholder email | A | — |
| 2 | Dashboard | `/` | KPI + skill cards + sparkline, journey entry | Real `/api/v1/skills/summary`, `/runs/stats`, `/runs` — skill→journey routing | 4-journey kártya STRUKTÚRA hiányzik, alert banner stub, "aktív pipeline" widget placeholder | B | ENTRY |
| 3 | Runs | `/runs` | Pipeline futások DataTable (status/cost/duration) | Real `/api/v1/runs` lista, search, status badge, cost format | Nincs advanced szűrés, numerikus oszlop sorting hiányos, drill-down minimális | B | 2-Monitoring |
| 4 | Costs | `/costs` | Cost analytics per-skill + per-model + daily bar chart | Real `/api/v1/costs/summary`, `/costs/breakdown`, per-service táblák | Nincs time range filter, nincs projekció/trend alert | B | 2-Monitoring |
| 5 | Monitoring | `/monitoring` | Service health dashboard (status/latency/success) | Real `/api/v1/admin/health`, `/admin/metrics`, status icon | Nincs küszöb/alert, csak manuális refresh, nincs historikus ábra | B | 2-Monitoring |
| 6 | Quality | `/quality` | LLM quality (rubric eval + cost tracking) | Real `/api/v1/quality/overview`, `/quality/rubrics`, `/quality/evaluate` live form | Langfuse integráció részben hardcoded, export opció limitált | B | 2-Monitoring |
| 7 | Documents | `/documents` | Multi-tab (Inbox + Upload) invoice extrakció + process status | Real `/api/v1/documents/upload`, `/documents/process-stream` SSE, per-file progress | Batch delete hiányzik, confidence threshold hardcoded, upload retry logic stub | B | 1-Invoice |
| 8 | DocumentDetail | `/documents/:id/show` | Invoice read-only detail (header + vendor + buyer + line items) | Real `/api/v1/documents/by-id/:id`, line item parse, verification button | Verification state read-only, nincs edit mode, line items list-ből fetch (nem detail-ből) | B | 1-Invoice |
| 9 | Verification | `/documents/:id/verify` | Split-screen PDF canvas + data editor + overlay confidence | Real `/api/v1/documents/images/:id/page_1.png`, datapoint editor | Mock SVG hardcoded, bounding box pontatlan, nincs diff perzisztencia (B7!) | C | 1-Invoice |
| 10 | Emails | `/emails` | Multi-tab (List + Upload + Connectors) intent detection + routing | Real `/api/v1/emails`, `/emails/process-batch-stream` SSE, per-email pipeline steps | Connectors tab stub (üres gomb), email routing UI hiányos | B | 1-Invoice |
| 11 | Rag | `/rag` | Collection lista + chat tabs + create/delete/bulk-delete | Real `/api/v1/rag/collections` CRUD, chat panel kész | Chat history nem perzisztens, nincs vector store validáció | C | 3-RAG |
| 12 | RagDetail | `/rag/:id` | Collection detail (Ingest + Chat + Chunks tabs) | Real `/api/v1/rag/collections/:id`, doc chunking status, chunk list | Chat history reload-on elveszik, nincs chunk search/filter | C | 3-RAG |
| 13 | ProcessDocs | `/process-docs` | Diagram generálás (flowchart/sequence/bpmn_swimlane) + saved list | Real `/api/v1/process-docs/generate-stream` + fallback, mermaid render, B5.1 3 típus backend-en kész | **UI diagram_type selector CSAK "BPMN"-re hardcoded** — a B5.1 3 típus (sequence/swimlane) nem választható frontend-ről! | B | 4-Generation |
| 14 | SpecWriter | `/spec-writer` | Spec generálás (feature/api/db/user_story) markdown download | Real `/api/v1/specs/write`, quality score, sections metadata, markdown export | History keresés hiányzik, review form read-only, "recent specs" widget nincs | B | 4-Generation |
| 15 | Media | `/media` | Upload audio/video + STT jobs + transcript sections | Real `/api/v1/media/upload`, per-file progress, sections UI | Provider selection demo, key_topics/vocabulary nem renderelt | B | 4-Generation |
| 16 | Rpa | `/rpa` | RPA configs lista + execution logs + run action | Real `/api/v1/rpa/configs`, `/rpa/logs`, `/rpa/execute` | Create/edit config dialog stub, schedule validation hiányzik | C | — (submenu) |
| 17 | Reviews | `/reviews` | Pending + history tabs + approve/reject workflow | Real `/api/v1/reviews/pending`, `/reviews/history`, POST approve/reject | Comment editor stub, nincs review template, nem merge-elt a Verification-nal | B | 1-Invoice |
| 18 | Cubix | `/cubix` | Cubix kurzus lista + szekció viewer + transzkriptum | Real `/api/v1/cubix` course metadata, cards, section list | Nincs interaktív playback, transcript link nem funkcionál, demo-heavy | C | — (submenu) |
| 19 | Services | `/services` | Service catalog (search + adapter toggle) | Real `/api/v1/services/manager`, service cards status/adapter badges | Nincs service health drill-down, pipeline integráció hardcoded route | B | BEALLITASOK |
| 20 | Pipelines | `/pipelines` | Pipeline lista + templates tabs + YAML editor create dialog | Real `/api/v1/pipelines`, `/pipelines/templates/list`, POST create/deploy | YAML validáció alap, nincs step editor, template deploy hardcoded | B | BEALLITASOK |
| 21 | PipelineDetail | `/pipelines/:id` | Pipeline overview (steps/config) + YAML + runs tabs | Real `/api/v1/pipelines/:id`, `/pipelines/:id/validate`, POST delete | Validáció részben futásidejű, runs sub-endpoint | B | BEALLITASOK |
| 22 | Admin | `/admin` | Users + API Keys tabs (read-only DataTable) | Real `/api/v1/admin/users`, `/admin/api-keys` | Add user / generate key gomb NEM funkcionális, nincs search/sort perzisztencia | C | ADMIN |
| 23 | Audit | `/audit` | Audit trail DataTable (action/resource/user/details) | Real `/api/v1/admin/audit`, timestamp, action badge | Export gomb stub, nincs date range filter, details truncated 50 char | C | 2-Monitoring |

### Audit Összegzés

**Kategória eloszlás:**
- **A (működik E2E):** 1 oldal (Login)
- **B (backend részleges, B8-ban javítandó):** 15 oldal (Dashboard, Runs, Costs, Monitoring, Quality, Documents, DocumentDetail, Emails, ProcessDocs, SpecWriter, Media, Reviews, Services, Pipelines, PipelineDetail)
- **C (backend stub/demo, Sprint C vagy minimum fix):** 7 oldal (Verification, Rag, RagDetail, Rpa, Cubix, Admin, Audit)
- **Ellenőrzés:** 1 + 15 + 7 = **23** ✓

**Journey eloszlás:**
- **ENTRY (Dashboard):** 1 (multi-journey belépés)
- **Journey 1 — Invoice:** 5 oldal (Documents, DocumentDetail, Verification, Emails, Reviews)
- **Journey 2 — Monitoring:** 5 oldal (Runs, Costs, Monitoring, Quality, Audit)
- **Journey 3 — RAG:** 2 oldal (Rag, RagDetail)
- **Journey 4 — Generation:** 3 oldal (ProcessDocs, SpecWriter, Media)
- **BEALLITASOK (konfig/infra, ritkán használt):** 3 oldal (Services, Pipelines, PipelineDetail)
- **ADMIN:** 1 oldal (Admin)
- **— (utility/submenu):** 3 oldal (Login, Rpa, Cubix — utóbbi kettő submenu)
- **Ellenőrzés:** 1 + 5 + 5 + 2 + 3 + 3 + 1 + 3 = **23** ✓

**B5 integrációs problémák (fontos!):**
- **ProcessDocs (13)**: B5.1 3 új diagram típust (flowchart/sequence/bpmn_swimlane) adott a backend-hez, de a frontend `diagram_type` selector még HARDCODED "BPMN"-re. **Ez egy B8 gyorsfix, 30 perc.**
- **SpecWriter (14)**: B5.2-ben újonnan létrejött oldal, router-ben van, de **nincs a Sidebar.tsx menüben** (csak direkt URL-lel elérhető). **B8-ban a menü struktúra része kell legyen.**
- **Cubix (18)**: Router-ben van, de **nincs a Sidebar.tsx menüben** — tudatos döntés (submenu, demo).

---

## § 2 — Új Information Architecture (Journey-based)

### Jelenlegi Navigáció (5 Technikai Csoport)

A `aiflow-admin/src/layout/Sidebar.tsx` jelenleg 5 csoportot definiál:

```
DASHBOARD (fix link, nem csoport)

OPERATIONS (4 item, defaultOpen=true)
├── /runs                Pipeline futások
├── /costs               Költségek
├── /monitoring          Service health
└── /quality             LLM minőség

DATA (2 item, defaultOpen=true)
├── /documents           Dokumentum lista
└── /emails              Email lista

AI SERVICES (4 item, defaultOpen=true)
├── /rag                 RAG chat
├── /process-docs        Diagram gen
├── /media               STT
└── /rpa                 RPA

ORCHESTRATION (2 item, defaultOpen=true)
├── /services            Service catalog
└── /pipelines           Pipeline list

ADMIN (3 item, defaultOpen=false)
├── /admin               User + API keys
├── /audit               Audit log
└── /reviews             Human review queue
```

**Jelenlegi struktúra problémái:**
1. **Technikai, nem feladat-orientált**: a user "szamlát akarok feldolgozni" célja 4 különböző csoportba szétszórt oldalakra (Emails→DATA, Documents→DATA, Verification→nincs menüben, Reviews→ADMIN)
2. **Nem skálázódik**: SpecWriter B5.2 után nem került bele a menüstruktúrába — nincs "hová rakjuk" döntés
3. **ADMIN túlpakolt**: a `/reviews` human review semmi köze az admin funkcióhoz, csak nem volt jobb hely
4. **DATA félrevezető**: az /emails + /documents "data source"-ként van jelölve, de valójában egy Invoice journey lépései
5. **ORCHESTRATION félrevezető**: a felhasználó nem "orchestration"-t akar — ez infra view, ritkán használt konfig
6. **Nincs Dashboard journey kapcsolat**: a Dashboard mutat KPI-t, de NEM vezet be a 4 tipikus user journey-be

### Új Navigáció (6 Felhasználói-cél Csoport)

```
DASHBOARD (fix entry, 4 journey belépő kártya)

1. DOKUMENTUM FELDOLGOZAS (Journey 1 — Invoice)  [*]
   ├── Szamla Kereső         → /documents?filter=invoice_finder  (új filter!)
   ├── Dokumentum Upload     → /documents?tab=upload             (Documents oldal, Upload tab)
   ├── Verifikáció           → /documents/:id/verify             (Verification oldal + Reviews merge)
   ├── Email Scan            → /emails                           (Emails oldal, List + Connectors)
   └── Mentett Dokumentumok  → /documents?tab=inbox              (Documents oldal, Inbox tab)

  [*] 5 menu item, de CSAK 3 külön oldal: `/documents` (3 item tab-bel, query param differentiate),
      `/documents/:id/verify`, `/emails`. Az URL átfedés szándékos — journey lépéseket
      mutat meg, nem különálló oldalakat.

2. TUDÁSBÁZIS (Journey 3 — RAG)
   ├── Kollekcio Kezelés     → /rag
   ├── Kollekcio Detail      → /rag/:id (ingest / chat / stats tabs)
   └── (almenu) Recent Query → /rag/:id?tab=chat

3. GENERALAS (Journey 4 — AI Output)
   ├── Diagram Generalás     → /process-docs  (flowchart / sequence / bpmn_swimlane — B5.1!)
   ├── Specifikáció Írás     → /spec-writer   (feature / api / db / user_story — B5.2!)
   └── Media Feldolgozás     → /media         (STT + video transcript)

4. MONITORING (Journey 2 — Governance)
   ├── Pipeline Futások      → /runs
   ├── Költségek             → /costs
   ├── Szolgáltatás Egészség → /monitoring
   ├── LLM Minőség           → /quality
   └── Audit Napló           → /audit

5. BEALLITASOK (Config, ritkán használt)
   ├── Felhasználók + API    → /admin
   ├── Pipeline Sablonok     → /pipelines + /pipelines/:id
   ├── Szolgáltatás Katalógus→ /services
   └── Email Connector       → /emails?tab=connectors (integrált az Emails-be)

(bottom) TOBBI
   ├── RPA Browser           → /rpa     (C kategória, demo)
   └── Cubix Kurzus          → /cubix   (C kategória, demo)
```

### Mozgatás Indoklási Tábla

| # | Mozgatás | Honnan | Hova | Indoklás |
|---|----------|--------|------|----------|
| 1 | `/emails` | DATA főcsoport | DOKUMENTUM FELDOLGOZAS / Email Scan step | Nem különálló "data source" — az Invoice journey 1. lépése |
| 2 | `/reviews` | ADMIN főcsoport | DOKUMENTUM FELDOLGOZAS / Verifikáció (merge) | Human review a verifikáció része, nem admin funkció |
| 3 | `/services` | ORCHESTRATION főcsoport | BEALLITASOK / Szolgáltatás Katalógus | Infra view, konfig — ritkán használt |
| 4 | `/pipelines` + `/pipelines/:id` | ORCHESTRATION főcsoport | BEALLITASOK / Pipeline Sablonok | Nem user action, konfiguráció |
| 5 | `/rpa` | AI SERVICES főcsoport | TOBBI almenu (bottom) | Ritkán használt, nem tipikus journey |
| 6 | `/cubix` | (router only) | TOBBI almenu (bottom) | Demo skill, ritka használat |
| 7 | `/spec-writer` | (router only, NINCS menü) | GENERALAS / Specifikáció Írás | B5.2-ben új — menübe kell |
| 8 | `/quality` | OPERATIONS főcsoport | MONITORING | Pontosabb név, governance tartozik ide |
| 9 | `/audit` | ADMIN főcsoport | MONITORING / Audit Napló | Governance, nem admin |

### Sidebar Implementáció Hatás (B8-ban!)

A `Sidebar.tsx` `MENU_GROUPS` konstans teljesen átdolgozandó:
- **5 csoport → 6 csoport** (+ TOBBI almenu)
- **15 top-level item → 18 item + 2 bottom item = 20 item** (SpecWriter + Audit átkerül + struktúra rendezés)
- **i18n kulcsok**: minden új csoport és item label-je új `aiflow.menu.*` kulcs `hu.json` + `en.json`-ban
- **icon set**: minden item ikon — Untitled UI `@untitledui/icons` csomag
- **state**: `defaultOpen` döntések — DOKUMENTUM + MONITORING alapból nyitva, GENERALAS + TUDASBAZIS alapból zárva (user gyakoribb útvonal)
- **Breadcrumb komponens** (új!): `aiflow-admin/src/components-new/Breadcrumb.tsx` a "hol vagyok a journey-ben?" jelzéshez

**Ez a változás B8-ban történik, NEM most!**

---

## § 3 — Holisztikus User Journey Map

### ASCII Journey Térkép

```
+======================================================================+
|                         DASHBOARD (belépés)                           |
|                                                                        |
|  +-------------+ +-------------+ +-------------+ +-------------+      |
|  | J1 Szamla   | | J2 Monitor  | | J3 Tudas-   | | J4 Gen.     |      |
|  | Feldolgozas | | & Governance| | bazis (RAG) | | (AI Output) |      |
|  |             | |             | |             | |             |      |
|  | "3 aktiv"   | | "OK, 2 ok"  | | "2 koll,    | | "1 fut,     |      |
|  | (badge)     | | (kpi mini)  | |  120 doku"  | |  flowchart" |      |
|  +------+------+ +------+------+ +------+------+ +------+------+      |
|         |               |               |               |             |
+---------+---------------+---------------+---------------+-------------+
          |               |               |               |
          v               v               v               v
    JOURNEY 1        JOURNEY 2        JOURNEY 3        JOURNEY 4
    (Invoice)      (Monitoring)         (RAG)         (Generation)
      5 oldal        5 oldal           2 oldal          3 oldal

+----------------+ +----------------+ +----------------+ +----------------+
| STEP 1: Email  | | STEP 1: Dash-  | | STEP 1: Koll.  | | STEP 1: Input  |
|  scan          | |  board KPI     | |  valasztas     | |  leiras        |
| /emails        | | /              | | /rag           | | /process-docs  |
|                | |                | |                | |  VAGY          |
|    |           | |    |           | |    |           | | /spec-writer   |
|    v           | |    v           | |    v           | |                |
| STEP 2: Szamla | | STEP 2: Drill- | | STEP 2: Doku   | |   |            |
|  detektalas    | |  down          | |  upload        | |   v            |
| /documents     | | /runs,/costs,  | | /rag/:id       | | STEP 2: Tipus  |
|  (filtered)    | |  /monitoring,  | |  (ingest tab)  | |  valasztas     |
|                | |  /quality      | |                | | flowchart|seq  |
|    |           | |                | |    |           | | bpmn|spec_type |
|    v           | |    |           | |    v           | |  (8 total!)    |
| STEP 3: Veri-  | |    v           | | STEP 3: Chat   | |                |
|  fikacio       | | STEP 3: Beavat-| | /rag/:id       | |    |           |
| /documents/:id | |  kozas         | |  (chat tab)    | |    v           |
|  /verify       | | /audit +       | |                | | STEP 3: LLM    |
|                | |  pipeline      | |    |           | |  generalas     |
|    |           | |  restart       | |    v           | | (service-k)    |
|    v           | |                | | STEP 4: Feed-  | |                |
| STEP 4: Jelen- | |                | |  back + stats  | |    |           |
|  tes kuldes    | |                | | /rag/:id       | |    v           |
| (notification) | |                | |  (stats tab)   | | STEP 4: Preview|
|                | |                | |                | |  + Export      |
|    |           | |                | |                | | (svg/md/json)  |
|    v           | |                | |                | |                |
| STEP 5:        | |                | |                | |                |
|  Arhivum       | |                | |                | |                |
| /documents     | |                | |                | |                |
|  (history)     | |                | |                | |                |
+----------------+ +----------------+ +----------------+ +----------------+
```

### Oldal ↔ Journey Kereszt-referencia Tábla

| # | Oldal | J1 Invoice | J2 Monit. | J3 RAG | J4 Gen. | ENTRY | BEALL. | ADMIN | Megjegyzés |
|---|-------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|-----------|
| 1 | Login | — | — | — | — | — | — | — | auth only |
| 2 | Dashboard | belépés | belépés | belépés | belépés | **E** | — | — | 4 kártya |
| 3 | Runs | — | **S2** | — | — | — | — | — | drill-down |
| 4 | Costs | — | **S2** | — | — | — | — | — | trend |
| 5 | Monitoring | — | **S2** | — | — | — | — | — | health |
| 6 | Quality | — | **S2** | — | — | — | — | — | LLM eval |
| 7 | Documents | **S2+S5** | — | — | — | — | — | — | filter=invoice |
| 8 | DocumentDetail | **S3** | — | — | — | — | — | — | read-only |
| 9 | Verification | **S3** | — | — | — | — | — | — | B7 deep dive |
| 10 | Emails | **S1** | — | — | — | — | — | — | scan trigger |
| 11 | Rag | — | — | **S1** | — | — | — | — | collection list |
| 12 | RagDetail | — | — | **S2-S4** | — | — | — | — | tabbed |
| 13 | ProcessDocs | — | — | — | **S1-S4** | — | — | — | 3 diagram type |
| 14 | SpecWriter | — | — | — | **S1-S4** | — | — | — | 4 spec type |
| 15 | Media | — | — | — | **S1-S4** | — | — | — | STT/video |
| 16 | Rpa | — | — | — | — | — | — | — | TOBBI submenu |
| 17 | Reviews | **S3 merge** | — | — | — | — | — | — | merge into Verification |
| 18 | Cubix | — | — | — | — | — | — | — | TOBBI submenu |
| 19 | Services | **cfg** | **cfg** | **cfg** | **cfg** | — | **Y** | — | infra view |
| 20 | Pipelines | **cfg** | — | — | — | — | **Y** | — | template mgmt |
| 21 | PipelineDetail | **cfg** | — | — | — | — | **Y** | — | YAML detail |
| 22 | Admin | — | — | — | — | — | — | **Y** | users/keys |
| 23 | Audit | — | **S3** | — | — | — | — | — | naplo |

**Legenda:** `S1` = journey step 1, `S2` = step 2, stb. `E` = entry point. `Y` = tartozik. `cfg` = beállítás (nem fő step). `—` = nem releváns.

**Megfigyelések:**
1. **Dashboard az egyetlen multi-journey oldal** — 4 journey-hoz tartozik belépőként.
2. **Journey 1 (Invoice) a legkomplexebb** — 5 oldal, 5 step, 4+ backend szolgáltatás lánc.
3. **Journey 4 (Generation) a legbővebb B5 után** — 3 oldal (ProcessDocs + SpecWriter + Media), 8 output típus (3 diagram + 4 spec + 1 media).
4. **Services oldal "horizontális"** — minden journey-hez kapcsolódik konfigurációként.
5. **Rpa + Cubix tudatosan fő nav alatt** — almenuben, nem fő nav item.

---

## § 4 — 4 Reszletes User Journey Definíció

> Minden journey azonos szerkezetet követ: **Cél → Felhasználó → Entry Point → Várt Kimenet → Lépések → Backend Lánc → Oldalak → Hiányzó Funkciók (B8 checklist)**

---

### JOURNEY 1: Szamla Feldolgozás (Invoice Finder)

**Cél:** Postafiókból szamlák keresése, letöltése, extrakciója, verifikálása és jelentése/archívuma — **end-to-end invoice processing**.

**Felhasználó:** Pénztáros, könyvelő, pénzügyi asszisztens, AP csapat. Tipikusan napi 10-100 szamla/user.

**Entry point:**
- `Dashboard → "Szamla Feldolgozás" kártya kattintás` → `/emails` (email scan indítás) **VAGY**
- közvetlen URL: `/emails` (email scan) / `/documents` (kézi upload) / `/documents/:id/verify` (review queue-ból)

**Várt kimenet:**
- X szamla feldolgozva, konfidencia szerint verifikálva
- Y szamla human review-ra küldve (alacsony konfidencia)
- Z fillér/Ft összeg kimutatva, notifikáció elküldve
- Archivum: Documents list-ben megtalálható, searcheable

**Lépések:**

#### Lépés 1 — Email Scan (`/emails`)
- User kiválaszt egy Outlook connector-t (v. több postafiók)
- Megad date range + filter (subject keyword, sender domain)
- "Scan indítás" gomb → `POST /api/v1/pipelines/invoice_finder_v3/run` payload: `{params: {accounts: [...], since: "...", until: "..."}}` (pipeline_id path param!)
- UI feedback: pipeline run badge + SSE progress `GET /api/v1/runs/:id/stream`
- Eredmény: talált szamlák hashelve, per-email status ("processed" / "skipped" / "failed")

#### Lépés 2 — Szamla Lista (`/documents?filter=invoice_finder&run_id=...`)
- Talált szamlák DataTable (kiskep + vendor + amount + date + confidence badge)
- **Konfidencia badge színek:**
  - 🟢 Zöld (>= 0.9) — auto-accept
  - 🟡 Sárga (0.7-0.89) — needs review
  - 🔴 Piros (< 0.7) — mandatory review
- Szűrés: csak Invoice Finder pipeline eredményei, rendezés: confidence ASC (review elöl)
- Batch akciók: "Select all low-confidence" → verifikáció queue-ba

#### Lépés 3 — Verifikáció (`/documents/:id/verify` — **B7 deep dive!**)
- **Bal oldal**: eredeti PDF canvas bounding box overlayjel (B7 target)
- **Jobb oldal**: kinyert adatok form (vendor, buyer, invoice_number, date, total, line_items)
- **Per-field confidence szín** (zöld/sárga/piros keret)
- User javít ha kell → diff tracking (`document.original_values` + `document.corrected_values`)
- **Piros mezők kötelezően** ellenőrzésre várnak (save blocked amíg nincs visszaigazolva)
- Akciók (human_review router!):
  - "Elfogadás" → `POST /api/v1/reviews/:review_id/approve` → `/reports` queue-ba kerül
  - "Elutasítás" → `POST /api/v1/reviews/:review_id/reject` + indoklás
  - "Javítás + Elfogadás" → diff mentés + approve (két lépésben: mentés + approve)
- **Merge**: a `/reviews` oldalon pending queue → link a `/documents/:id/verify`-re (külön oldal megszűnik)

#### Lépés 4 — Jelentés Küldés (notification)
- Lépés 3 approve után auto-trigger `POST /api/v1/notifications/send`
- Email template: szamla summary + csatolmány (eredeti PDF + extrakció JSON)
- Címzett: konfigurálható per-pipeline (pl. `accounting@company.hu`)
- Bejegyzés `audit_log` táblába: `action=invoice_approved, resource=document:123, user=...`

#### Lépés 5 — Archivum (`/documents` history view)
- Feldolgozott szamlák keresése (vendor, amount range, date range, status)
- Export: CSV/Excel letöltés
- Drill-down: `/documents/:id/show` read-only detail (nem verifikáció)

**Backend szolgáltatás lánc:**
```
outlook_connector (email letöltés)
    ↓
email_classifier (invoice detektalas — GPT-4o-mini)
    ↓
document_extractor (PDF → struktúrált JSON — docling + GPT-4o)
    ↓
invoice_processor (validáció, normalizáció — vendor DB)
    ↓
confidence_router (confidence >= 0.9 auto / < 0.9 human review)
    ↓
[alacsony conf.] → human_review queue ← /reviews / /verification
    ↓
notification (email küldés + audit log)
```

**Pipeline template:** `src/aiflow/pipeline/builtin_templates/invoice_finder_v3.yaml` (8 step)

**Oldalak a user szemszögéből:**
1. `/emails` (entry, scan trigger)
2. `/documents?filter=invoice_finder` (találati lista)
3. `/documents/:id/verify` (kritikus verifikáció — B7!)
4. (no page — notification email)
5. `/documents` (history/archive keresés)

**Hiányzó funkciók (B8 checklist):**
- [ ] `/emails` "Scan indítás" gomb nem triggeri `invoice_finder_v3` pipeline-t (jelenleg csak lista nézet)
- [ ] `/documents` URL filter `?filter=invoice_finder&run_id=...` backend támogatás hiányzik
- [ ] Konfidencia badge szín + ikonok a `/documents` DataTable-ben (Verification oldalon már van)
- [ ] Batch akció: "Select all low-confidence" + queue-ba küldés
- [ ] `/documents/:id/verify` — bounding box overlay (B7 kötelező!)
- [ ] `/documents/:id/verify` — diff tracking perzisztencia (B7 kötelező!)
- [ ] `/reviews` merge a Verification-ba (egy oldal lesz, route marad backward compat miatt)
- [ ] Notification template konfiguráció UI (`/admin` vagy `/pipelines/:id` config)
- [ ] `/documents` export CSV gomb

---

### JOURNEY 2: Monitoring & Governance

**Cél:** Rendszer egészségének, költségeinek, minőségének áttekintése, alertek felismerése és **beavatkozás** (pipeline restart, prompt rollback, incident response).

**Felhasználó:** DevOps admin, platform lead, vezetőség (reporting), SRE oncall.

**Entry point:**
- `Dashboard → "Monitoring & Governance" kártya kattintás` → `/` (önmaga, mert a Dashboard a Monitoring hub)
- közvetlen URL: `/runs` vagy `/costs` vagy `/monitoring` vagy `/quality`

**Várt kimenet:**
- Áttekintés: hány pipeline fut, hány sikeres, mai költség, szolgáltatás health
- Probléma detektálás: failed runs, cost spike, service down, LLM quality drop
- Beavatkozás: pipeline restart, service restart, prompt version rollback
- Audit: ki mit csinált, mikor (compliance)

**Lépések:**

#### Lépés 1 — Dashboard Áttekintés (`/`)
- 4 KPI kártya: aktív pipeline runs, mai teljes költség ($), service health %, LLM quality score
- Utolsó 5 pipeline futás DataTable mini (status + duration + cost)
- Alert banner (piros) ha:
  - bármelyik kritikus pipeline FAILED állapotban
  - daily cost > threshold (pl. $20)
  - bármely service DOWN
  - quality score < 0.85
- **4 journey kártya** (B6 design): J1 + J2 + J3 + J4 belépő linkek

#### Lépés 2 — Drill-Down (specifikus terület)
A 4 monitoring oldal közötti navigáció:

**2a. Pipeline futások** (`/runs`)
- DataTable: run_id, pipeline_name, status, started_at, duration, cost
- Szűrés: status (pending/running/success/failed), pipeline template, date range
- Drill-down: run detail → lépésenkénti log

**2b. Költségek** (`/costs`)
- KPI: mai / heti / havi összeg, per-service breakdown, per-model breakdown
- Daily bar chart (utolsó 30 nap)
- Alert: ha `gpt-4o` >> `gpt-4o-mini` ratio nem optimális → recommendation banner (B5.3 COST_BASELINE_REPORT.md)

**2c. Service Health** (`/monitoring`)
- Per-service status card: PostgreSQL / Redis / Kroki / Langfuse / skills (process_documentation, aszf_rag, email_intent, invoice_processor, invoice_finder, cubix, spec_writer)
- Latency grafikon (1h / 24h)
- Restart button (per-service, admin-only)

**2d. LLM Minőség** (`/quality`)
- Promptfoo eval eredmények (7 skill × 96 test case)
- Langfuse trace link per-run
- Rubric score trend (heti/havi)
- Prompt verzió diff + rollback button (Langfuse label swap)

#### Lépés 3 — Beavatkozás
Problémafüggően a user akciói:

- **Pipeline FAILED** → `/runs/:id` detail → "Retry" gomb → **HIÁNYZÓ ENDPOINT, B8 Gate 3 (API Impl)**: `POST /api/v1/pipelines/:pipeline_id/runs/:run_id/retry` (new endpoint to implement)
- **Service DOWN** → `/monitoring` → "Restart Service" gomb → `POST /api/v1/services/:name/restart` (admin-only)
- **Cost Spike** → `/costs` → Langfuse trace drill → prompt audit → verzió rollback
- **Quality Drop** → `/quality` → rubric eval eredmény → prompt javítás + új label
- **Audit review** → `/audit` → szűrés user/action/date → export

**Backend szolgáltatás lánc:**
```
health_monitor (metrics) + langfuse (traces) + quality (promptfoo) + cost_records (DB)
    ↓
ApiService: /runs /costs /monitoring /quality /audit
    ↓
Action: pipeline_runner.retry | service_manager.restart | prompts.rollback
    ↓
audit_log (minden akció logolva)
```

**Pipeline template:** nincs (ez a monitoring maga, nem pipeline)

**Oldalak a user szemszögéből:**
1. `/` (Dashboard, entry + KPI overview)
2. `/runs` (pipeline drill-down)
3. `/costs` (cost analytics)
4. `/monitoring` (service health)
5. `/quality` (LLM quality)
6. `/audit` (action history)

**Hiányzó funkciók (B8 checklist):**
- [ ] Dashboard 4 journey kártya implementálás (B6 wireframe → B8 kód)
- [ ] Dashboard alert banner (failed runs / cost spike / service down)
- [ ] `/costs` cost spike alert + gpt-4o → gpt-4o-mini recommendation (B5.3 report-ból jön)
- [ ] `/monitoring` service restart button (admin-only)
- [ ] `/quality` prompt version rollback UI (Langfuse label swap)
- [ ] `/runs/:id` retry button
- [ ] `/audit` export CSV gomb + date range filter
- [ ] `/audit` details oszlop full text (jelenleg 50 char truncated)

---

### JOURNEY 3: Tudásbázis (RAG Chat)

**Cél:** Dokumentum-alapú tudásbázis építése, tartása és interaktív lekérdezése chat felületen keresztül.

**Felhasználó:** Szakértő (jogi, HR, műszaki), knowledge manager, belső ügyfélszolgálat, tanácsadó.

**Entry point:**
- `Dashboard → "Tudásbázis" kártya kattintás` → `/rag` (collection list)
- közvetlen URL: `/rag` vagy `/rag/:id`

**Várt kimenet:**
- Kollekció létrehozva/kiválasztva (pl. "HR Szabályzatok 2026")
- X dokumentum feltöltve, chunk-olva, embedded
- Chat használható (streaming response + citations)
- Feedback gyűjtve (👍/👎 per válasz) + relevancia statisztika

**Lépések:**

#### Lépés 1 — Kollekció Kezelés (`/rag`)
- Meglévő kollekciók listája (cards vagy DataTable)
- Per-kollekció: név, leírás, doc count, chunk count, utolsó ingest időpont
- Akciók:
  - "Új kollekció" gomb → modal: név, leírás, vector store (pgvector default)
  - "Törlés" bulk akció (több kiválasztott)
  - Kattintás a kártyára → `/rag/:id` detail

#### Lépés 2 — Dokumentum Feltöltés (`/rag/:id` Ingest tab)
- Drag-and-drop zóna: PDF / DOCX / XLSX / MD / TXT
- Per-fájl status: uploaded → parsing (docling) → chunking (advanced_chunker) → embedding → stored
- Progress bar per-fájl + overall
- Error handling: nem támogatott formátum / parse fail / embedding rate limit
- Lista: feltöltött dokumentumok a kollekcióban (név + méret + chunk count + delete gomb)

#### Lépés 3 — Chat (`/rag/:id` Chat tab)
- Chat interface: message list + input + send gomb (Enter)
- Query endpoint: `POST /api/v1/rag/collections/:id/query` (jelenleg non-streaming; SSE streaming verzió **HIÁNYZÓ ENDPOINT, B8 Gate 3 (API Impl)** opció)
- Válasz formátum:
  - Fő szöveg (markdown render)
  - **Citations**: per-válaszhoz 3-5 forrás (dokumentum név + page + chunk preview)
  - Relevancia score badge (0.0-1.0)
- History: session-level, de reload után NEM perzisztens (lokál state)
- Új chat / szétszedés gomb (clear history)

#### Lépés 4 — Visszajelzés + Statisztika (`/rag/:id` Stats tab)
- Per-válasz 👍/👎 feedback gomb a chat-ben → `POST /api/v1/feedback`
- "Miért hibás?" szabad szöveg mező (opcionális)
- Stats tab:
  - Hit rate: válaszok % melyet 👍-tel jelölt a user
  - Avg relevance score: átlagos citation relevance
  - Query volume: napi/heti lekérdezések száma
  - Top queries: gyakori kérdések
- Kollekció fine-tuning: alacsony hit rate → chunking strategy váltás → re-embed

**Backend szolgáltatás lánc:**
```
rag_engine (orchestrator)
    ↓
advanced_chunker (docling parse + semantic chunking)
    ↓
vector_ops (pgvector embedding + similarity search)
    ↓
reranker (top-K chunks → final rank)
    ↓
chat_completions (streaming response generálás)
    ↓
feedback_service (👍/👎 + stats aggregation)
```

**Pipeline template:** `src/aiflow/pipeline/builtin_templates/advanced_rag_ingest.yaml` (ingest-hez) + `knowledge_base_update.yaml`

**Oldalak a user szemszögéből:**
1. `/rag` (collection list, entry)
2. `/rag/:id` (tabbed: Ingest / Chat / Stats)

**Hiányzó funkciók (B8 checklist):**
- [ ] Chat history perzisztencia (session-en túl, localStorage vagy DB)
- [ ] Citation inline click → megnyitja a forrás dokumentumot chunk highlight-tal
- [ ] Chunk search/filter az Ingest tab lista nézetben
- [ ] Stats tab hit rate grafikon (jelenleg csak számok)
- [ ] Re-embed gomb (kollekció egész) — új chunking strategy válasz után
- [ ] "Új kollekció" modal validation (pgvector config, embedding model selection)
- [ ] Bulk delete dokumentum a kollekcióból

---

### JOURNEY 4: Generálás (Diagram + Spec + Media)

**Cél:** Vizuális (diagram) vagy szöveges (spec) AI-generált output létrehozása szabad szöveges leírásból vagy fájlból.

**Felhasználó:** Fejlesztő, üzleti elemző, PM, architect, műszaki író. B5.1 + B5.2 miatt erősen bővült!

**Entry point:**
- `Dashboard → "Generálás" kártya kattintás` → dropdown: Diagram / Spec / Media
- közvetlen URL: `/process-docs` (diagram) / `/spec-writer` (spec) / `/media` (STT)

**Várt kimenet:**
- **Diagram**: SVG (Kroki rendered) + Mermaid source + DrawIO XML export — 3 diagram típus (flowchart / sequence / bpmn_swimlane)
- **Spec**: Markdown + HTML + JSON export — 4 spec típus (feature / api / db / user_story)
- **Media**: transcript (txt/srt) + summary — STT output audio/videó fájlból

**Lépések:**

#### Lépés 1 — Input (típus + leírás)
**1a. Diagram (`/process-docs`)**
- Input textarea: szabad szöveg leírás (pl. "az order lifecycle 4 lépése: place → pay → ship → deliver")
- **Típus selector (B5.1 új!):**
  - `flowchart` — döntési diagram (default)
  - `sequence` — szekvencia diagram (authentication, retry flow)
  - `bpmn_swimlane` — BPMN swimlane (cross-funkcionális folyamat)
- Opcionálisan: fájl upload (PDF/DOCX) — előzetes parse + leírás auto-feltöltés

**1b. Spec (`/spec-writer` — B5.2 új oldal!)**
- Input textarea: raw requirement szöveg (pl. "Szükségem van egy API endpoint-ra...")
- **Spec típus selector (B5.2 új!):**
  - `feature` — feature spec (goal, scope, acceptance criteria)
  - `api` — API endpoint spec (method, path, request, response, errors)
  - `db` — database schema spec (tables, columns, indexes, constraints)
  - `user_story` — user story format (As a..., I want..., So that..., Acceptance:)
- Nyelv selector: HU / EN

**1c. Media (`/media`)**
- Fájl upload: audio (mp3, wav, m4a) vagy video (mp4, mov)
- Provider selection (jelenleg stub): Whisper / deepgram
- Nyelv: auto-detect vagy manual

#### Lépés 2 — Generálás (backend hívás)

**2a. Diagram generálás:**
```
POST /api/v1/process-docs/generate
Body: {description, diagram_type: "sequence", language: "hu"}
    ↓
DiagramGeneratorService.generate(diagram_type)
    ↓
Switch on diagram_type:
  - flowchart → diagram_generator service (process_documentation legacy prompts, default)
  - sequence → diagram_planner → mermaid_generator → diagram_reviewer (3 prompts!)
  - bpmn_swimlane → ugyanaz a 3 prompt, swimlane context
    ↓
KrokiRenderer.render(mermaid_code, "svg") → SVG bytes
    ↓
DB save + return {id, svg, mermaid, drawio_xml}
```

**2b. Spec generálás:**
```
POST /api/v1/specs/write
Body: {input_text, spec_type: "feature", language: "hu"}
    ↓
skills.spec_writer.workflows.spec_writing.run_spec_writing()
    ↓
5-step DAG:
  1. analyze (spec_analyzer.yaml) — raw text → structured requirement JSON
  2. select_template — spec_type-ra specifikus template
  3. generate_draft (spec_generator.yaml) — req → markdown draft
  4. review_draft (spec_reviewer.yaml) — markdown → score 0-10 + feedback
  5. finalize — acceptable threshold >= 6 / iterate ha < 6
    ↓
DB save (generated_specs tábla) + return {id, markdown, score, is_acceptable, review}
```

**2c. Media:**
```
POST /api/v1/media/upload
    ↓
media_processor.process_media() → Whisper STT → transcript
    ↓
Langchain summary (optional) + sections extraction
    ↓
Return {id, transcript_txt, srt, summary, sections}
```

**UI feedback mindhárom esetben:**
- Progress indicator (SSE streaming ha lehetséges)
- Error handling (LLM rate limit, invalid input, parse fail)

#### Lépés 3 — Preview + Edit
**Diagram:**
- SVG render inline
- Mermaid source code box (collapsible, copyable)
- "Újragenerálás ezzel:" text input → iterate
- Edit mode: manual Mermaid edit → Kroki re-render

**Spec:**
- Markdown render inline (react-markdown)
- Score + feedback badge (9/10 ACCEPTABLE / 5/10 NEEDS REVIEW)
- Review panel: sections count, word count, is_acceptable
- Edit mode: markdown textarea

**Media:**
- Transcript text view (időbélyeg opcionális)
- Sections list
- Summary box

#### Lépés 4 — Export
**Diagram:**
- SVG letöltés (`GET /api/v1/diagrams/:id/export?fmt=svg`)
- Mermaid forrás letöltés (`.mmd`)
- DrawIO XML (`.drawio`)
- Copy to clipboard (Mermaid)

**Spec:**
- Markdown letöltés (`GET /api/v1/specs/:id/export?fmt=markdown`)
- HTML letöltés (`fmt=html` — python-markdown wrapped)
- JSON letöltés (`fmt=json` — full structured output)
- Email küldés (template-es, opcionális)

**Media:**
- transcript.txt letöltés
- subtitle.srt letöltés
- summary.md letöltés

**Backend szolgáltatás lánc:**
```
Diagram: ProcessDocs UI → diagram_generator service → diagram_planner (YAML prompt)
         → mermaid_generator (YAML) → diagram_reviewer (YAML) → KrokiRenderer → DB
Spec: spec_writer UI → spec_writer service → spec_writing workflow (5 steps)
      → spec_analyzer → spec_generator → spec_reviewer → DB (generated_specs)
Media: media UI → media_processor service → Whisper STT → Langchain summary → DB
```

**Pipeline templates:**
- `src/aiflow/pipeline/builtin_templates/diagram_generator_v1.yaml` (B5.1, 1 step)
- `src/aiflow/pipeline/builtin_templates/spec_writer_v1.yaml` (B5.2, 1 step)
- Media nincs külön pipeline template (direct service call)

**Oldalak a user szemszögéből:**
1. `/process-docs` (diagram, entry + preview + export)
2. `/spec-writer` (spec, entry + preview + export) — **B5.2 új!**
3. `/media` (STT/video, entry + preview + export)

**Hiányzó funkciók (B8 checklist):**
- [ ] **`/process-docs` `diagram_type` dropdown** — jelenleg HARDCODED "BPMN"-re, nem lehet sequence/bpmn_swimlane-t választani (B5.1 backend kész, csak UI hiányzik!)
- [ ] `/process-docs` ikonok per-diagram-típus (flowchart / sequence / swimlane)
- [ ] `/spec-writer` History kereső + recent specs widget (jelenleg csak az utolsót látja)
- [ ] `/spec-writer` review form interactive mode (javaslatok alkalmazása)
- [ ] `/media` provider selection valós (Whisper vs deepgram — jelenleg stub)
- [ ] `/media` key_topics + vocabulary rendering (adat megvan, UI nincs)
- [ ] "Új chat" jellegű reset gomb mindhárom oldalon
- [ ] Streaming response a `/spec-writer`-en (jelenleg csak final response)
- [ ] Mermaid live edit az `/process-docs`-on (manual Mermaid javítás → Kroki re-render)

---

## § 5 — Navigációs Wireframe

> **Figma MCP státusz:** A `mcp__figma__*` tool-csomag elérhető, de új Figma file / frame létrehozásához `fileKey` kell — jelenlegi AIFlow Figma file-ra (meglévő `aiflow-admin/figma-sync/PAGE_SPECS.md`) ez a session nem íródik be közvetlenül. **Döntés**: ASCII wireframe lesz az elsődleges referencia ebben a dokumentumban, a Figma frame létrehozás B8-ban történik (ha a B6 terv validálva), Untitled UI komponensekkel. Ez konzisztens a `feedback_figma_quality.md` memória-bejegyzéssel (no placeholder wireframes — valós Untitled UI komponensek kellenek, ami megfelelőbb B8-ban, kódolás közben).

### 5.1 Sidebar Wireframe (ASCII)

```
+---------------------------------+
|  AIFlow        [logo]           |  <- top: logo + env badge
|  v1.3.0-service-excellence      |
+---------------------------------+
|                                  |
|  [home] Dashboard                |  <- fix entry, active highlight
|                                  |
+---------------------------------+
|  DOKUMENTUM FELDOLGOZAS       v  |  <- group 1, defaultOpen
|  +-- [mail]  Szamla Kereso       |
|  +-- [file]  Dokumentum Upload   |
|  +-- [check] Verifikacio         |  <- badge: "3 waiting" ha van
|  +-- [mail]  Email Scan          |
|  +-- [list]  Mentett Dokumentum  |
+---------------------------------+
|  TUDASBAZIS (RAG)            >   |  <- group 2, defaultClosed
|  (expanded on click)             |
|    +-- [book] Kollekcio          |
|    +-- [chat] Chat Felulet       |
+---------------------------------+
|  GENERALAS                    >  |  <- group 3, defaultClosed
|  (expanded on click)             |
|    +-- [diagram] Diagram Gen     |
|    +-- [edit]    Spec Writer     |
|    +-- [audio]   Media Proc      |
+---------------------------------+
|  MONITORING                   v  |  <- group 4, defaultOpen
|  +-- [play]   Pipeline Futas     |
|  +-- [dollar] Koltsegek          |  <- badge: "!$20" ha spike
|  +-- [heart]  Szolg. Egeszseg    |  <- badge: red ha DOWN
|  +-- [star]   LLM Minoseg        |
|  +-- [history]Audit Naplo        |
+---------------------------------+
|  BEALLITASOK                  >  |  <- group 5, defaultClosed
|  +-- [users] Felhasznalok + API  |
|  +-- [yaml]  Pipeline Sablon     |
|  +-- [grid]  Szolg. Katalogus    |
|  +-- [mail]  Email Connector     |
+---------------------------------+
|                                  |
|  [bot] RPA Browser       (submenu)
|  [play]Cubix Kurzus      (submenu)
|                                  |
+---------------------------------+
|  [user] user@company.hu          |  <- bottom: user menu
|  [moon] Theme toggle             |
|  [globe] HU/EN toggle            |
+---------------------------------+

Size:     260px width x full height
Colors:   Untitled UI design tokens (bg-white / dark:bg-gray-900)
State:    - active item: bg-brand-50 text-brand-600 (v. dark variant)
          - hover: bg-gray-100 (v. dark variant)
          - group header: text-gray-400 uppercase tracking-wider
          - badges: kis piros/sárga dot jobbra
Icons:    @untitledui/icons csomag (home, file, mail, check, list,
          book, chat, diagram, edit, audio, play, dollar, heart,
          star, history, users, yaml, grid, bot, user, moon, globe)
Typography: font-semibold (group header) / font-medium (item) /
            font-normal (non-active)
```

### 5.2 Dashboard Wireframe (ASCII)

```
+===========================================================================+
|  AIFlow Dashboard                           [refresh] [?] [user]          |
|  Üdvözöljük vissza! Áttekintés a mai napról.                             |
+===========================================================================+
|                                                                            |
|  +---------------+ +---------------+ +---------------+ +---------------+ |
|  | J1 Szamla     | | J2 Monitoring | | J3 Tudasbazis | | J4 Generalas  | |
|  | Feldolgozas   | | & Governance  | | (RAG)         | | (AI Output)   | |
|  |               | |               | |               | |               | |
|  | [invoice img] | | [chart img]   | | [book img]    | | [diagram img] | |
|  |               | |               | |               | |               | |
|  | "3 aktiv      | | "Mind OK"     | | "2 kollekcio  | | "1 fut most"  | |
|  |  journey"     | | (kis zold dot)| |  120 dokumen" | | "flowchart"   | |
|  |               | |               | |               | |               | |
|  | [Szamla Scan] | | [Dashboard]   | | [Chat]        | | [+ Generalas] | |
|  +---------------+ +---------------+ +---------------+ +---------------+ |
|                                                                            |
|  Alert banner (ha van):                                                   |
|  [!] 2 pipeline futas hibas — megnezem >   [x]                            |
|                                                                            |
+===========================================================================+
|                                                                            |
|  UTOLSO 5 PIPELINE FUTAS                                     [Nezd mind >]|
|  +------+--------------------------+----------+-----------+--------------+|
|  | #    | Pipeline                 | Status   | Duration  | Cost         ||
|  +------+--------------------------+----------+-----------+--------------+|
|  | 1234 | invoice_finder_v3        | SUCCESS  | 2m 14s    | $0.18        ||
|  | 1233 | process_documentation    | SUCCESS  | 0m 42s    | $0.03        ||
|  | 1232 | spec_writer_v1           | SUCCESS  | 0m 38s    | $0.04        ||
|  | 1231 | invoice_finder_v3        | FAILED   | 1m 02s    | $0.09  [!]   ||
|  | 1230 | advanced_rag_ingest      | SUCCESS  | 3m 10s    | $0.07        ||
|  +------+--------------------------+----------+-----------+--------------+|
|                                                                            |
|  KPI MINI SOR:                                                             |
|  +-----------+ +-----------+ +-----------+ +-----------+                  |
|  | Mai runs  | | Mai cost  | | Service   | | Quality   |                  |
|  |   42      | |  $1.14    | |  7/7 OK   | |   9.2/10  |                  |
|  |  (+12%)   | |  (-8%)    | |   (100%)  | |  (trend+) |                  |
|  +-----------+ +-----------+ +-----------+ +-----------+                  |
|                                                                            |
+===========================================================================+

Size:       1440x900 desktop / 768x responsive tablet / 375 mobile
Layout:     2x2 grid (desktop) / 2x2 (tablet) / 1x4 stack (mobile)
Card spec:  360x200 px, border-radius 12px, shadow-sm, bg-white
            Untitled UI Card component
Journey kartya tartalom:
  - Cim (font-semibold, text-xl)
  - Ikon / kep (w-16 h-16, bg-brand-50 rounded-full)
  - Status szoveg (text-sm text-gray-600) — dinamikus: "3 aktiv" stb.
  - CTA gomb (size=sm, variant=primary)
  - Hover: shadow-md, cursor-pointer

Alert banner:
  - Szin: sárga (bg-yellow-50 border-yellow-200 text-yellow-800)
  - Ikon: [!] (untitled-ui warning-triangle)
  - Ha nincs alert: ne renderelje a div-et (null return)

Utolso 5 futas DataTable:
  - 5 sor max, de ha kevesebb → empty state
  - Cost szín ha anomalia > +20% → piros

KPI mini sor:
  - 4 kartya horizontalis
  - Nagy szam + feliratkozas + trend badge (+/- %)
  - Untitled UI "Metric Card" variant

Mobile (< 768px):
  - 4 journey kartya 1 oszlopba
  - Alert banner full width
  - Utolso futasok: horizontal scroll
  - KPI mini: 2x2 grid
```

### 5.3 Figma Frame Registry (jövőbeli B8 feladat)

| # | Frame név | Méret | Státusz | Korlát | Notes |
|---|-----------|-------|---------|--------|-------|
| 1 | Sidebar — Journey-based (light) | 260x1080 | **TODO B8** | Valódi Untitled UI — NEM placeholder! | Untitled UI tokens, 6 csoport |
| 2 | Sidebar — Journey-based (dark) | 260x1080 | **TODO B8** | Valódi Untitled UI — NEM placeholder! | Dark theme variant |
| 3 | Dashboard — 4 Journey Cards (desktop) | 1440x900 | **TODO B8** | Valódi Untitled UI Card + Button — NEM placeholder! | 2x2 grid + alert + runs + KPI |
| 4 | Dashboard — Mobile | 375x800 | **TODO B8** | Valódi Untitled UI, auto-layout! | Stack layout |
| 5 | Breadcrumb component | 800x40 | **TODO B8** | Valódi Untitled UI Breadcrumb variant! | Journey path highlight |

**Convention a B8 Figma létrehozáshoz** (memória `feedback_figma_quality.md` szerint):
- ❌ NEM placeholder rectangle-ok
- ✅ Valós Untitled UI komponensek (Card, Button, Badge, Input, DataTable)
- ✅ Valós Untitled UI design token-ek (fg-primary, bg-secondary, border-primary, stb.)
- ✅ Auto-layout (mint az Untitled UI kit)
- ✅ Component variant-ok (Light/Dark, Default/Hover, Enabled/Disabled)

A Figma frame-ek létrehozása B8 Step 4 (Figma design) lesz — ez a B6 wireframe csak a specifikáció.

---

## § 6 — B8 Migrációs Priorizált Terv (Demo → Backend)

> **Cél:** A 23 oldal audit (B6.1) alapján döntés: melyik oldal kerül **B8 (Sprint B)** keretében valós backendre, és melyik **Sprint C** halasztott. A 7 HARD GATE pipeline szerint (journey → API → design → UI → Playwright → Figma sync) B8 implementáció **Journey 1 és Journey 2** teljes E2E lefedéssel kötelező — Journey 3 és Journey 4 gyorsfixes.

### 6.1 B8 Kötelező (Journey 1 + Journey 2 teljes E2E)

> **Megjegyzés Login-ról (1. sor, Kategória A):** Login oldal (`/login`) **nem szerepel egyik § 6 migrációs táblában sem**, mert Kategória A — már teljesen működik end-to-end, nincs B8 tennivalója.

| # | Oldal | Journey | Mi hiányzik | Becsült munka |
|---|-------|---------|-------------|---------------|
| 1 | Dashboard | J1+J2+J3+J4 (ENTRY) | 4 journey kártya implementálás (§5.2 wireframe), alert banner, KPI mini | 1 session (S33 kezdet) |
| 2 | Documents | J1 | `?filter=invoice_finder` URL support + backend filter + confidence badge DataTable-ben | 3 óra |
| 3 | Emails | J1 | "Scan indítás" gomb → `POST /api/v1/pipelines/invoice_finder_v3/run` trigger + SSE progress | 2 óra |
| 4 | Verification | J1 | **B7 deep dive (külön session!)** — bounding box overlay + diff persist + per-field conf. | 1 session (S32=B7) |
| 5 | Reviews | J1 | Merge a Verification-ba (route megtartva backward compat) | 2 óra |
| 6 | Runs | J2 | Retry button (**HIÁNYZÓ ENDPOINT**: `POST /pipelines/:pipeline_id/runs/:run_id/retry`), advanced filter, drill-down detail | 2 óra |
| 7 | Costs | J2 | Cost spike alert banner, gpt-4o→mini recommendation banner (B5.3-ból) | 2 óra |
| 8 | Monitoring | J2 | Service restart button (`POST /api/v1/services/:name/restart`, admin-only) | 2 óra |
| 9 | Quality | J2 | Prompt version rollback UI (Langfuse label swap API) | 3 óra |
| 10 | Audit | J2 | Export CSV gomb, date range filter, full details (nem truncated) | 2 óra |

**Összesen B8 kötelező:** 10 oldal, becsült ~25 óra + 2 session (B7 + B8 kezdet). **Journey 1 + Journey 2 Playwright E2E teszt kötelező** a B8 végén.

### 6.2 B8 Opcionális (Journey 4 gyorsfix + gyors nyereségek)

| # | Oldal | Journey | Mi hiányzik | Becsült munka |
|---|-------|---------|-------------|---------------|
| 1 | **ProcessDocs** | J4 | **`diagram_type` dropdown a 3 típushoz** (B5.1 backend kész, csak UI!) — **NAGY IMPACT 30 perc** | 30 perc |
| 2 | SpecWriter | J4 | History kereső + recent specs widget | 2 óra |
| 3 | Media | J4 | Provider selection valós, key_topics + vocabulary rendering | 2 óra |
| 4 | Rag | J3 | Chat history perzisztencia (localStorage vagy DB) | 1 óra |
| 5 | RagDetail | J3 | Citation inline click → source highlight, chunk filter | 2 óra |
| 6 | Sidebar | - | **Új 6-csoportos menü implementálás** (§2 IA alapján) + Breadcrumb komponens | 3 óra |
| 7 | ProcessDocs | J4 | Mermaid live edit (manual Mermaid javítás → Kroki re-render) | 2 óra |
| 8 | SpecWriter | J4 | Streaming response (SSE) a `/api/v1/specs/write`-en — jelenleg csak final output | 2 óra |

**Összesen B8 opcionális:** 8 tétel, becsült ~15 óra. **Az első (ProcessDocs diagram_type) gyorsnyereség: 30 perc alatt a B5.1 munka láthatóvá válik**, tehát **erősen ajánlott** beilleszteni.

### 6.3 Sprint C Halasztott (nem kritikus journey)

| # | Oldal | Indoklás |
|---|-------|----------|
| 1 | Rpa | RPA config lista működik, de create/edit dialog stub — nem kritikus journey, backend workflow még nem production-ready |
| 2 | Cubix | Demo skill, backend STT pipeline működik de UI viewer limitált, nincs napi használat |
| 3 | Admin | Read-only user + API key lista — add/generate NEM kritikus most, a bestix team API-t közvetlenül tudja használni |
| 4 | Services | Search + catalog lista működik, health drill-down + pipeline integration hardcoded route → Sprint C |
| 5 | Pipelines | Lista + templates + YAML create működik, de step editor + runtime validation → Sprint C |
| 6 | PipelineDetail | Overview + YAML + runs tabs működik, runtime validáció hiányzik → Sprint C |

**Összesen Sprint C:** 6 oldal, ezek **NEM** kerülnek B8-ba.

### 6.4 Elkerülendő Anti-pattern-ek (B8 szabályok)

1. **NE mock-olj demo adatot a Dashboard journey kártyákra** — ha nincs valós `/api/v1/skills/summary` + `/runs/stats` adat, akkor "Loading..." vagy "Adatok betöltése" spinner, de SOHA hardcoded "3 aktiv journey" dummy szöveg. (Memória: `feedback_no_silent_mock.md`)
2. **NE csinálj külön "demo vs prod" toggle-t az oldalakon** — csak source badge: "Backend" (ha valós API) / "Demo" (ha mock fallback) / "No data" (ha üres).
3. **NE skip-eld a 7 HARD GATE-et** — B8 minden új vagy módosított komponens: journey → API audit → API impl → Figma → UI → Playwright → Figma sync. (Memória: `feedback_ui_depth.md`)
4. **NE commit-olj `.tsx`-et Playwright teszt nélkül** — minden B8 módosítás után Playwright E2E futtatás valós adatokkal. (Memória: `feedback_real_e2e_testing.md`)
5. **NE töröld a Reviews route-ot** — backward compat, `/reviews` → redirect `/documents?filter=pending_review`.
6. **NE hardcode-old a spec_type / diagram_type listát** — fetchelje backend-ből `/api/v1/diagrams/types` és `/api/v1/specs/types` endpoint-ról (jövő-proof).

### 6.5 B8 7 HARD GATE Sorrend

A B8 session (S33) folyamata a 7 HARD GATE szerint:

```
GATE 1 — User Journey:      63_UI_USER_JOURNEYS.md (EZ A DOKUMENTUM) ← KESZ
                              + per-oldal journey mapping PAGE_SPECS.md
GATE 2 — API Audit:         Minden B8 oldalhoz ellenőrizni: endpoint létezik-e?
                              Hiányzó endpoint list-et készíteni a S33 elején.
GATE 3 — API Impl:          Hiányzó endpoint-ok implementálása (retry, restart, filter)
GATE 4 — Figma Design:      Sidebar + Dashboard + Breadcrumb Figma frame-ek
                              (Untitled UI valós komponensekkel)
GATE 5 — UI Implementation: Sidebar.tsx átdolgozás + Dashboard journey card + egyéb oldalak
GATE 6 — Playwright E2E:    Journey 1 + Journey 2 teljes E2E teszt
                              (/emails → /documents → /verify → approve)
                              (/ Dashboard → /runs → retry → /audit)
GATE 7 — Figma Sync:        PAGE_SPECS.md és Figma frame regisztrálás frissítés
```

**Nincs átugrás!** Ha bármely gate FAIL → előbb fix, aztán continue. Memória: `feedback_gate_enforcement.md` — `ls` fájlellenőrzés kötelező, nem csak grep.

### 6.6 B8 Playwright E2E Coverage Target

| Teszt neve | Journey | Mit tesztel |
|------------|---------|-------------|
| `invoice_finder_full_flow.spec.ts` | J1 | `/emails` scan → `/documents` list → `/verify` approve → notification check |
| `monitoring_drill_down.spec.ts` | J2 | `/` Dashboard → alert click → `/runs/:id` detail → retry → `/audit` verify |
| `diagram_type_selector.spec.ts` | J4 | `/process-docs` → type dropdown → sequence → generate → SVG render |
| `sidebar_new_nav.spec.ts` | IA | 6 csoport render + active state + group collapse + navigation |

**Kötelező pass:** invoice_finder_full_flow + monitoring_drill_down. **Opcionális:** diagram_type_selector + sidebar_new_nav.

---

<!-- B6 VALIDATION ROUND 1 FIXES (LEPES 8 — 2026-04-10) -->
<!-- 4 MAJOR FIXED:
  - FIXED: POST /api/v1/pipelines/run → POST /api/v1/pipelines/invoice_finder_v3/run (pipeline_id path param)
  - FIXED: POST /api/v1/documents/:id/approve|reject → POST /api/v1/reviews/:review_id/approve|reject (human_review router)
  - FIXED: POST /api/v1/pipelines/runs/:id/retry → Jelölve HIÁNYZÓ ENDPOINT, B8 Gate 3
  - FIXED: GET /api/v1/rag/chat/stream → POST /api/v1/rag/collections/:id/query (valós endpoint)
  7 MINOR (5 FIXED, 2 SKIPPED):
  - FIXED: "process_docs" skill név → "process_documentation" (§ 4 J2 monitoring)
  - FIXED: "process_documentation skill" → "diagram_generator service" (§ 4 J4 backend lánc)
  - FIXED: § 2 DOKUMENTUM FELDOLGOZAS 5 item URL átfedés dokumentálva lábjegyzettel [*]
  - FIXED: Login (Kat. A) explicit megjegyzes § 6.1 előtt ("nincs B8 tennivalója")
  - FIXED: § 6.2 B8 opcionális → 6 → 8 tétel (Mermaid live edit + Streaming spec hozzáadva)
  - FIXED: § 5.3 Figma Frame Registry "Korlát" oszlop — "Valódi Untitled UI — NEM placeholder!"
  - FIXED: § 6.1 Runs retry endpoint szöveg konzisztencia javítva (HIÁNYZÓ ENDPOINT jelölés)
  - SKIPPED: J2 retry+restart szövegezés apró eltérés § 4 vs § 6 — értelmi egyezés megvan, nem javítandó
-->
<!-- END B6 VALIDATION ROUND 1 FIXES -->

<!-- B6 VALIDATION ROUND 2 FIXES (LEPES 10 — 2026-04-10) -->
<!-- Regression check: 1. kor 4 MAJOR + 5 MINOR javítás mind OK a dokumentumban
  1 MAJOR FIXED (regression az 1. kor javításból):
  - FIXED: § 6.1 Emails (sor 941): `POST /pipelines/run` → `POST /api/v1/pipelines/invoice_finder_v3/run`
  2 MEDIUM FIXED:
  - FIXED: § 6.1 Monitoring (sor 946): `POST /services/:name/restart` → `POST /api/v1/services/:name/restart`
  - FIXED: § 6.2 SpecWriter (sor 957): "streaming response" eltávolítva a #2-ből (marad a #8 dedikált sor)
  2 LOW VERIFIED — NEM HIBA:
  - VERIFIED: `POST /api/v1/notifications/send` — LÉTEZIK (src/aiflow/api/v1/notifications.py sor 130)
  - VERIFIED: `POST /api/v1/feedback` — LÉTEZIK (src/aiflow/api/v1/feedback.py sor 52)
  NO CHANGE: 1. kor javítások all OK (regression check PASS)
-->
<!-- END B6 VALIDATION ROUND 2 FIXES -->

---

*B6 vége. Következő: LEPES 7 = plan-validator subagent VALIDACIO 1. KOR (see out/b6_validation_round1.md).*


