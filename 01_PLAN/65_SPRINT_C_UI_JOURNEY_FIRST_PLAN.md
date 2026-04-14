# Sprint C: UI Journey-First — Fokuszalt Terv (v1.4.0)

> **Branch:** `feature/v1.4.0-ui-refinement` (from `main`)
> **Szulo terv:** `01_PLAN/58_POST_SPRINT_HARDENING_PLAN.md` (Sprint A+B DONE)
> **Elozmeny:** v1.3.0 (Sprint B COMPLETE, 2026-04-09)
> **Megkozelites:** Journey-first, szukitett scope — 3 fo funkcio + platform management

---

## Dontes: Scope Szukites

A v1.3.0 portal 23 oldalas, de a valos uzleti ertek 3 fo funkciora koncentralodik.
A J4 (Generation: ProcessDocs, SpecWriter, Media, Cubix) oldalakat **LEVESSZUK a portalrol** —
fajlok archivalva, sidebar-ban maximum placeholder link marad.

**FO FUNKCIOK (deep journey tervezes):**
1. **Dokumentum Feldolgozas** — szamla upload, extraction, verifikacio, jovahagyas
2. **Email Intent** — email scan, klasszifikacio, routing, invoice pipeline trigger
3. **RAG Chat** — tudasbazis epites, ingest, chat, feedback

**KIEGESZITO FUNKCIOK (mukodo, karbantartott):**
4. **Pipeline Management** — pipeline CRUD, template deploy, run tracking, **RunDetail (UJ)**
5. **User Management + Admin** — user CRUD, API key, audit trail, monitoring

**ARCHIVALT (J4 — leveve a portalrol):**
- ProcessDocs.tsx → archive
- SpecWriter.tsx → archive
- Media.tsx → archive
- Cubix.tsx → archive
- RPA.tsx → archive

---

## Portal Struktura (v1.4.0 — szukitett)

```
Sidebar (v1.4.0):
┌─────────────────────────────┐
│ DOKUMENTUM FELDOLGOZAS (J1) │
│   Documents                 │
│   Emails                    │
│   Verification (queue)      │
├─────────────────────────────┤
│ TUDASBAZIS (J3)             │
│   RAG Collections           │
├─────────────────────────────┤
│ PIPELINE & FUTASOK (J5)     │
│   Pipeline Runs             │
│   Pipelines                 │
│   Services                  │
├─────────────────────────────┤
│ MONITORING (J2a)            │
│   Costs                     │
│   Service Health            │
│   LLM Quality               │
├─────────────────────────────┤
│ ADMIN (J2b)                 │
│   Users & API Keys          │
│   Audit Log                 │
├─────────────────────────────┤
│ ARCHIV (collapsed, halvany) │
│   Diagrams (archived)       │
│   Specs (archived)          │
│   Media (archived)          │
│   RPA (archived)            │
│   Cubix (archived)          │
└─────────────────────────────┘

Dashboard: 3 fo journey kartya + Pipeline status + Admin link
Oldalak: 23 → 16 aktiv + 5 archivalt + Login + Dashboard
```

---

## Personas (szukitett)

### P1: Penzugyi Asszisztens
**Fo journey:** J1 (Dokumentum + Email)
**Napi hasznalat:** 10-100 szamla feldolgozas

### P2: Tudasmenedzser
**Fo journey:** J3 (RAG)
**Heti hasznalat:** 2-3 session, collection epites + chat

### P3: Platform Admin
**Fo journey:** J5 (Pipeline) + J2a (Monitoring) + J2b (Admin)
**Napi hasznalat:** rendszer ellenorzes, sporádikus konfiguralas

---

## J1: Dokumentum Feldolgozas + Email Intent (RESZLETES)

### J1 Teljes Flow — Gomb-szintu Reszletesseg

```
BELEPOPONT: Dashboard "Szamlafeldolgozas" kartya → /emails

───── 1. EMAIL SCAN (/emails) ─────────────────────────────────

[Inbox tab]
┌─────────────────────────────────────────────────────────────┐
│ Emails                                    [Scan Inditas] ▶  │
│                                           [Process All]     │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ □  sender@vendor.hu   Invoice #2024-001   2026-04-10 ✅│ │
│ │ □  info@partner.com   Meeting request     2026-04-10 ⬜│ │
│ │ □  billing@corp.eu    INV-5589            2026-04-09 ✅│ │
│ └─────────────────────────────────────────────────────────┘ │
│ Tabs: [Inbox] [Upload] [Connectors]                         │
└─────────────────────────────────────────────────────────────┘

GOMBOK:
  [Scan Inditas] → POST /pipelines/templates/invoice_finder_v3_offline/deploy
    - Loading spinner + "Pipeline inditva" banner
    - Sikeres: zold banner + "Eredmenyek megtekintese →" link → /documents
    - JELENLEGI ALLAPOT: ❌ NEM LETEZIK — C1.1 implementalja

  [Process All] → POST /emails/process-batch-stream (SSE)
    - Mar mukodik ✅

  [Process Selected] → POST /emails/process (selected IDs)
    - Mar mukodik ✅

  [Connectors tab] → CRUD connector dialogs
    - Mar mukodik ✅ (C0-ban verifikaljuk)

───── 2. SZAMLA LISTA (/documents) ──────────────────────────

┌─────────────────────────────────────────────────────────────┐
│ Documents          [Upload ▲] [Export CSV ▼]                │
│                                                             │
│ ┌── Summary Banner ───────────────────────────────────────┐ │
│ │ ✅ 12 jovahagyva  ⚠️ 5 fuggoben  ❌ 2 elutasitva       │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ □  file.pdf   Vendor Kft  1.250.000 Ft  2026-04-10 🟢 95%│
│ │ □  inv2.pdf   Partner AG  890.500 Ft    2026-04-09 🟡 78%│
│ │ □  scan.pdf   Corp EU     ???           2026-04-08 🔴 45%│
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ [Select All Low-Confidence] [Bulk Verify →] [Delete Selected]│
│ Tabs: [List] [Upload]                                       │
└─────────────────────────────────────────────────────────────┘

GOMBOK:
  [Export CSV] → fetchApi("GET", "/documents/export/csv", { rawResponse: true })
    - JELENLEGI: ❌ Auth hiany (Bearer token nem megy) — C1.2 fix

  [Confidence Badge] → szin-kodolt: 🟢≥90% / 🟡70-89% / 🔴<70%
    - JELENLEGI: ❌ NINCS a listaban — C1.2 implementalja

  [Summary Banner] → X jovahagyva / Y fuggoben / Z elutasitva szamitas
    - JELENLEGI: ❌ NINCS — C1.2 implementalja

  [Sor kattintas] → navigate("/documents/:id/show") — Mar mukodik ✅
  [Verify gomb] → navigate("/documents/:id/verify") — Mar mukodik ✅
  [Upload tab] → drag-drop + SSE progress — Mar mukodik ✅
  [Delete / Bulk Delete] → Mar mukodik ✅

───── 3. DOCUMENT DETAIL (/documents/:id/show) ──────────────

  Read-only megtekintes: vendor, buyer, header, line items, totals
  [Verify →] gomb → /documents/:id/verify
  [Back ←] → /documents
  JELENLEGI: ✅ TELJES — nincs valtozas

───── 4. VERIFIKACIO (/documents/:id/verify) ─────────────────

  Split-screen: PDF canvas (bal 55%) + Data editor (jobb 45%)
  Bounding box overlay-ek confidence szinekkel
  Per-mezo edit + approve/reject workflow
  JELENLEGI: ✅ TELJES (B7 deep dive) — nincs valtozas

───── 5. REVIEW QUEUE (/reviews) ─────────────────────────────

  Pending review-k listaja → "Verify" link → /documents/:id/verify
  Approve/Reject gombok
  JELENLEGI: ✅ MUKODIK — sidebar atnevezes "Review Queue"-ra (C5)
  NEM REDIRECT! Megmarad mint human review entry point.

───── 6. ZARAS ──────────────────────────────────────────────

  /documents lista: Summary banner mutatja a "done" allapotot
  Export CSV: letoltve, feladat kesz
```

### J1 Hianyzo Elemek Osszefoglalo

| # | Elem | Oldal | Gomb/UI | Backend | C-fazis |
|---|------|-------|---------|---------|---------|
| 1 | Scan Inditas | /emails | UJ gomb Inbox tab-on | POST templates/deploy LETEZIK | C1.1 |
| 2 | Confidence badge | /documents | UJ oszlop DataTable-ben | extraction_confidence LETEZIK | C1.2 |
| 3 | Summary banner | /documents | UJ banner DataTable felett | Szamitas client-side | C1.2 |
| 4 | Export auth fix | /documents | Meglevo gomb fix | rawResponse + Bearer | C1.2 |
| 5 | Dashboard J1 kartya | / | navigate fix: /documents → /emails | 1-line fix | C0.2 |

---

## J3: RAG Tudasbazis (RESZLETES)

### J3 Teljes Flow

```
BELEPOPONT: Dashboard "Tudasbazis" kartya → /rag

───── 1. COLLECTION LISTA (/rag) ──────────────────────────

┌─────────────────────────────────────────────────────────────┐
│ RAG Collections                          [Uj Kollekcio +]  │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ HR Szabalyzatok 2026     12 doc   3450 chunk   hu  [→] │ │
│ │ Termekek Tudastár        5 doc    1200 chunk   en  [→] │ │
│ │ Szerzodesmintalk          8 doc    2100 chunk   hu  [→] │ │
│ └─────────────────────────────────────────────────────────┘ │
│ [Delete Selected]                                           │
│ Tabs: [Collections] [Chat]                                  │
└─────────────────────────────────────────────────────────────┘

GOMBOK:
  [Uj Kollekcio +] → Dialog: nev, leiras, nyelv — Mar mukodik ✅
  [→ Megnyitas] → navigate("/rag/:id") — Mar mukodik ✅
  [Delete] → ConfirmDialog → DELETE — Mar mukodik ✅
  [Chat tab] → globalis chat interfesz — Mar mukodik ✅

───── 2. COLLECTION DETAIL (/rag/:id) ────────────────────

[Ingest tab]
┌─────────────────────────────────────────────────────────────┐
│ HR Szabalyzatok 2026                    [Back ←] [Delete]  │
│                                                             │
│ ┌── Drag & Drop Zone ──────────────────────────────────── ┐│
│ │           PDF, DOCX, TXT, MD fajlok ide                 ││
│ └─────────────────────────────────────────────────────────┘│
│                                                             │
│ Betoltott dokumentumok:                                     │
│ │ szabalyzat_2026.pdf    45 chunk   ✅ Done    [🗑 Delete] │ │
│ │ hr_policy_v3.docx      28 chunk   ✅ Done    [🗑 Delete] │ │
│                                                             │
│ Chunks: [Search: ___________]  [Filter: relevancia/datum]  │
│ │ Chunk #1: "A munkaviszony megszuntetese..."  rel: 0.92  ││
│ │ Chunk #2: "Szabadsag kiadasa..."             rel: 0.88  ││
│                                                             │
│ Tabs: [Ingest] [Chat] [Stats]                              │
└─────────────────────────────────────────────────────────────┘

GOMBOK:
  [Drag & Drop] → SSE ingest progress — Mar mukodik ✅
  [Chunk Search] → szabad szoveges kereses chunk-ok kozott
    - JELENLEGI: ❌ Csak paginacio, nincs kereses — C4.2

[Chat tab]
┌─────────────────────────────────────────────────────────────┐
│ Chat — HR Szabalyzatok 2026                                 │
│                                                             │
│ 🤖 Miben segithetek?                                       │
│                                                             │
│ 👤 Hogyan kell szabadsagot kiadni?                         │
│                                                             │
│ 🤖 A szabadsag kiadasa az MT 122. §-a alapjan...          │
│    📎 Forrasok: szabalyzat_2026.pdf (p.12), hr_policy (p.5)│
│    [👍] [👎]                                                │
│                                                             │
│ [Kerdes bevitel...                              ] [Kuldes]  │
└─────────────────────────────────────────────────────────────┘

GOMBOK:
  [Kuldes] → SSE streaming valasz + forrasok — Mar mukodik ✅
  [👍/👎] → POST /feedback — Mar mukodik ✅
  Forras kattintas → chunk kiemelese
    - JELENLEGI: ❌ Nincs implementalva — NICE-TO-HAVE (nem C scope)

───── 3. STATS TAB ──────────────────────────────────────────

  Hit rate, atlag relevancia, query volume — Mar mukodik ✅ (szam)
  Chart → NICE-TO-HAVE

```

### J3 Hianyzo Elemek

| # | Elem | Oldal | C-fazis |
|---|------|-------|---------|
| 1 | Chunk kereses/szures | /rag/:id Ingest tab | C4.2 |
| 2 | Dashboard J3 kartya | / | C0.2 (navigate check) |

---

## J5: Pipeline Management (RESZLETES)

### J5 Teljes Flow

```
BELEPOPONT: Sidebar → "Pipeline & Futasok" csoport

───── 1. PIPELINE RUNS (/runs) ──────────────────────────────

┌─────────────────────────────────────────────────────────────┐
│ Pipeline Runs                                               │
│                                                             │
│ │ abc123  invoice_finder  ✅ completed  12.3s  $0.045  [→]│ │
│ │ def456  aszf_rag        ✅ completed   8.1s  $0.023  [→]│ │
│ │ ghi789  email_intent    ❌ failed      3.2s  $0.012  [→]│ │
│ │ jkl012  spec_writer     🔄 running    ...    ...     [→]│ │
│                                                             │
│ [Sor kattintas] → /runs/:id (UJ RunDetail oldal!)         │
└─────────────────────────────────────────────────────────────┘

GOMBOK:
  [→ Detail] → navigate("/runs/:id")
    - JELENLEGI: ❌ /runs/:id route NEM LETEZIK — C2.2 (RunDetail UJ OLDAL)
  [Restart] gomb FAIL-nal → POST /pipelines/{id}/run
    - Mar mukodik ✅ (de detail oldal nincs)

───── 2. RUN DETAIL (/runs/:id) — UJ OLDAL ─────────────────

┌─────────────────────────────────────────────────────────────┐
│ ← Back    Run: ghi789                    ❌ FAILED          │
│ Pipeline: email_intent   Duration: 3.2s  Cost: $0.012      │
│                                                             │
│ Step Log:                                                   │
│ │ 1. classify_email    ✅ completed   1.1s  gpt-4o-mini  │ │
│ │ 2. extract_entities  ✅ completed   0.8s  gpt-4o-mini  │ │
│ │ 3. route_intent      ❌ FAILED     1.3s  gpt-4o       │ │
│ │    Error: "Timeout connecting to intent_schemas service" │ │
│                                                             │
│ [Retry Pipeline ▶]  [Export Log 📥]                        │
└─────────────────────────────────────────────────────────────┘

GOMBOK:
  [← Back] → navigate("/runs")
  [Retry Pipeline] → ConfirmDialog → POST /pipelines/{pipeline_id}/run
  [Export Log] → JSON download
  JELENLEGI: ❌ OLDAL NEM LETEZIK — C2.2

───── 3. PIPELINES (/pipelines) ─────────────────────────────

  Pipeline lista + template deploy + YAML editor — Mar mukodik ✅

───── 4. PIPELINE DETAIL (/pipelines/:id) ──────────────────

  YAML editor + validate + execution history — Mar mukodik ✅

───── 5. SERVICES (/services) ──────────────────────────────

  Service catalog grid — Mar mukodik ✅
```

### J5 Hianyzo Elemek

| # | Elem | Oldal | C-fazis |
|---|------|-------|---------|
| 1 | **RunDetail oldal** | /runs/:id | **C2.2** (UJ OLDAL, fo prioritas) |
| 2 | /runs/:id route | router.tsx | C2.2 |

---

## J2a: Monitoring + J2b: Admin (RESZLETES)

### J2a Monitoring

```
GOMBOK es ALLAPOTOK:

/monitoring:
  [Restart] gomb minden service kartyan → ConfirmDialog → POST restart
    - JELENLEGI: ❌ NEM MUKODIK — C2.3
  [Auto-refresh] interval valaszto (10s/30s/60s/off)
    - JELENLEGI: ❌ NINCS — C2.3

/costs:
  Minden mukodik ✅ — nincs valtozas

/quality:
  [Rubric sor kattintas] → detail panel
    - JELENLEGI: ❌ Nincs expand — C2.4
```

### J2b Admin

```
/admin:
  [Add User] gomb → CreateUser dialog (email, name, password, role)
    - JELENLEGI: ❌ onClick NINCS — C2.5
  [Generate Key] gomb → GenerateKey dialog → KEY REVEAL (egyszer lathato!)
    - JELENLEGI: ❌ onClick NINCS — C2.5
  [Revoke Key] per-sor gomb → ConfirmDialog → DELETE
    - JELENLEGI: ❌ NINCS — C2.5

/audit:
  [Filter bar] 3 dropdown (action, entity, user) + limit selector
    - JELENLEGI: ❌ NINCS — C2.6
  [Export CSV] gomb → Blob download
    - JELENLEGI: ❌ NINCS — C2.6
  [Sor kattintas] → JSON detail modal
    - JELENLEGI: ❌ NINCS — C2.6
```

---

## Implementacios Terv (szukitett, ~10 session)

```
=== SPRINT C: Fokuszalt UI (v1.4.0) — ~10 session ===

--- S37: C0 + C1 — Infra + J1 Invoice Flow (1 session) ---
C0.1: ConfirmDialog.tsx + i18n kulcsok
C0.2: Dashboard J1 kartya → /emails fix
C0.3: J4 archivalas (5 oldal → archive mappa, sidebar update)
C1.1: Emails "Scan Inditas" pipeline trigger
C1.2: Documents confidence badge + export fix + summary banner

--- S38: C2 — J5 Pipeline + J2a Monitoring (2 session) ---
C2.1: Dashboard alert banner (0.5)
C2.2: RunDetail.tsx UJ OLDAL + /runs/:id route (1 session)
C2.3: Monitoring restart + auto-refresh (0.5)

--- S39: C2 folytatas — J2b Admin (1.5 session) ---
C2.4: Quality rubric detail (0.25)
C2.5: Admin CRUD — Create User + Generate Key + Revoke (1 session) [Figma: key reveal]
C2.6: Audit filter + export CSV (0.25)

--- S40: C4 — J3 RAG Finomitas (0.5 session) ---
C4.2: Chunk kereses/szures RagDetail-ben

--- S41: C5 — Sidebar Atstruktura + Cleanup (1 session) ---
C5.1: Sidebar uj 6-csoportos struktura (archiv csoport halvanyan)
C5.2: Reviews atnevezes "Review Queue"-ra
C5.3: Cross-page dark mode + aria-label + 0 console error
C5.4: CLAUDE.md + plan frissites

--- S42-S44: C6 — Journey E2E Validacio (3 session) ---
C6.1: J1 E2E: Scan → Documents → Verify → Approve → Export
C6.2: J5 E2E: Pipelines → Run → RunDetail(step log) → Retry
C6.3: J2a+J2b E2E: Monitor(restart) + Admin(CRUD) + Audit(filter+export)
C6.4: J3 E2E: Create collection → Ingest → Chat → Feedback
C6.5: Cross-journey: Dashboard kartyak → minden journey elerheto

--- S45: C7 — Veglegesites (1 session) ---
C7.1: Teljes regresszio (1443+ unit + E2E)
C7.2: v1.4.0 version bump + tag
```

---

## J4 Archivalas — Konkret Teendo (C0.3)

```
Athelyezendo fajlok:
  aiflow-admin/src/pages-new/ProcessDocs.tsx  → aiflow-admin/src/pages-archive/
  aiflow-admin/src/pages-new/SpecWriter.tsx   → aiflow-admin/src/pages-archive/
  aiflow-admin/src/pages-new/Media.tsx        → aiflow-admin/src/pages-archive/
  aiflow-admin/src/pages-new/Cubix.tsx        → aiflow-admin/src/pages-archive/
  aiflow-admin/src/pages-new/Rpa.tsx          → aiflow-admin/src/pages-archive/

Router (router.tsx):
  - Toroljuk a ProcessDocs, SpecWriter, Media, Cubix, Rpa importokat
  - Toroljuk a route definiciokat
  - VAGY: Navigate to="/" (redirect Dashboard-ra)

Sidebar (Sidebar.tsx):
  - "generation" csoport → "archive" csoport (collapsed, halvany szin)
  - Bottom menu (RPA, Cubix) → bekerul az archive csoportba
  - Uj "PIPELINE & FUTASOK" csoport: Runs + Pipelines + Services

Oldalszam: 23 → 18 aktiv (Dashboard, Documents, DocumentDetail, Verification,
  Emails, Reviews, Rag, RagDetail, Runs, RunDetail(UJ), Costs, Monitoring,
  Quality, Audit, Admin, Pipelines, PipelineDetail, Services) + Login
```

---

## Sikerkriteriumok

| # | Kriterium | Journey |
|---|-----------|---------|
| 1 | **J1 vegigjar:** Scan → Documents(badge) → Verify → Approve → Export | J1 |
| 2 | **J5 vegigjar:** Pipelines → Run → **RunDetail**(step log+retry) | J5 |
| 3 | **J2a vegigjar:** Monitor(restart) + Costs + Quality(rubric) | J2a |
| 4 | **J2b vegigjar:** Admin(CRUD: user+key+revoke) + Audit(filter+export) | J2b |
| 5 | **J3 vegigjar:** Create → Ingest → Chat → Feedback | J3 |
| 6 | **J4 archivalva:** 5 oldal archive mappaban, sidebar "Archiv" csoport | — |
| 7 | **RunDetail letezik:** /runs/:id step-level naplo + retry | J5 |
| 8 | **0 halott gomb:** Minden `<button>` onClick bekotve | All |
| 9 | **tsc + ruff:** 0 error | Tech |
| 10 | **E2E suite:** 121 alap + 6 journey E2E = 127+ PASS | Tech |

---

## Szamok

| Metrika | Ertek |
|---------|-------|
| Aktiv oldalak | 18 (23-bol, 5 archivalt) |
| Journey-k | 5 (J1, J2a, J2b, J3, J5) |
| Uj oldal | 1 (RunDetail) |
| Sessionok | ~10 |
| Figma | 1 (Admin key reveal) |
| Uj E2E | 6 |
| Backend valtozas | 0 |
