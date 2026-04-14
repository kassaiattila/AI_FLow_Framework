# AIFlow Sprint B — Session 33 Prompt (B8: UI Journey Implementáció — Navigáció + 3 Journey + Breadcrumb)

> **Datum:** 2026-04-12
> **Branch:** `feature/v1.3.0-service-excellence` | **HEAD:** `a23db05`
> **Port:** API 8102, Frontend 5174
> **Elozo session:** S32 — B7 DONE (Verification Page v2: bounding box + diff + field validation + approve/reject, 3 commit: f09f32e + 5464829 + a23db05)
> **Terv:** `01_PLAN/58_POST_SPRINT_HARDENING_PLAN.md` (B8 szekcio, sor 1615-1670)
> **Session tipus:** CODE — Sidebar átépítés + Journey 1-2 integráció + Breadcrumb + E2E
> **Workflow:** Sidebar → Breadcrumb → Dashboard → Journey 1 finomítás → Journey 2 összekötés → E2E → Commit(ok)

---

## KONTEXTUS

### S32 Eredmenyek (B7 — DONE, 3 commit)

**B7 — Verification Page v2 (`f09f32e` + `5464829` + `a23db05`):**
- `alembic/versions/031_add_verification_edits.py`: verification_edits tábla (12 oszlop, 3 index, reversible)
- `src/aiflow/api/v1/verifications.py`: 5 új endpoint (POST save, GET by-doc, PATCH approve, PATCH reject, GET history)
- `aiflow-admin/src/pages-new/Verification.tsx`: v2 — bounding box real image-en, diff display, field validation, approve/reject workflow, pending review banner, reject modal
- `aiflow-admin/src/verification/types.ts`: field validatorok (numeric, date, tax number)
- `aiflow-admin/src/pages-new/Reviews.tsx`: backward compat banner + Verify gomb link
- `aiflow-admin/src/locales/{hu,en}.json`: 11 új i18n kulcs
- `tests/unit/api/test_verification_api.py`: 8 unit teszt
- `tests/e2e/test_verification_v2.py`: 4 E2E teszt
- Regresszió: 1443 unit PASS, ruff + tsc clean

**Infrastruktura (v1.3.0 — S32 utan):**
- 27 service | 175 API endpoint (27 router) | 48 DB tabla | 31 migracio
- 22 pipeline adapter | 10 pipeline template | 7 skill | 23 UI oldal
- **1443 unit test** | 129 guardrail teszt | 97 security teszt | **109 E2E** | **96 promptfoo test**

### Jelenlegi Allapot (B8 cel — UI Journey Implementáció)

```
=== B8 KONTEXTUS: MI A JELENLEGI HELYZET? ===

SIDEBAR.TSX jelenlegi allapot (182 sor):
  aiflow-admin/src/layout/Sidebar.tsx

  Jelenlegi 5 csoport (TECHNIKAI felosztas — PROBLEMAS!):
  OPERATIONS (4)  → /runs, /costs, /monitoring, /quality
  DATA (2)        → /documents, /emails
  AI SERVICES (4) → /rag, /process-docs, /media, /rpa
  ORCHESTRATION (2)→ /services, /pipelines
  ADMIN (3)       → /admin, /audit, /reviews

  PROBLEMAK (B6-ban dokumentalva, 63_UI_USER_JOURNEYS.md § 2):
  1. Technikai, nem feladat-orientalt
  2. /reviews ADMIN-ba dugva, de valojaban Verification resze
  3. /spec-writer NINCS a menuben (B5.2 ota)
  4. /cubix NINCS a menuben
  5. Nem skalazodik — nincs "hova rakjam" dontes

  B6-ban megtervezett UJ 6 csoport (JOURNEY-BASED):
  1. DOKUMENTUM FELDOLGOZAS → /documents, /documents/:id/verify, /emails
  2. TUDASBAZIS             → /rag, /rag/:id
  3. GENERALAS              → /process-docs, /spec-writer, /media
  4. MONITORING              → /runs, /costs, /monitoring, /quality, /audit
  5. BEALLITASOK             → /admin, /pipelines, /services
  6. TOBBI (bottom)          → /rpa, /cubix

ROUTER.TSX jelenlegi allapot (99 sor):
  aiflow-admin/src/router.tsx
  23 route (createHashRouter), RequireAuth wrapper
  Route-ok NEM valtoznak B8-ban — csak a MENU struktura!

DASHBOARD.TSX jelenlegi allapot (299 sor):
  aiflow-admin/src/pages-new/Dashboard.tsx
  KPI kartyak + lista — DE nincs 4 journey belépő kártya!

BREADCRUMB: NEM LETEZIK meg!
  aiflow-admin/src/components-new/Breadcrumb.tsx → UJ

APPSHELL.TSX:
  aiflow-admin/src/layout/AppShell.tsx — Sidebar + main content wrapper

PAGES-NEW: 23 oldal (Admin, Audit, Costs, Cubix, Dashboard, DocumentDetail,
  Documents, Emails, Login, Media, Monitoring, PipelineDetail, Pipelines,
  ProcessDocs, Quality, Rag, RagDetail, Reviews, Rpa, Runs, Services,
  SpecWriter, Verification)

i18n: aiflow-admin/src/locales/{hu,en}.json — mindket nyelv

B6 TERV REFERENCIAK (63_UI_USER_JOURNEYS.md):
  § 2 — Uj Information Architecture: 6 journey-based csoport definicio (sor 111-221)
  § 3 — Holisztikus Journey Map: ASCII diagram (sor 226+)
  § 4 — Journey 1-4 reszletes leiras (sor 300+)
  § 6 — Migration Plan: 10 kotelezo + 8 opcionalis + 6 halasztott (sor 930+)

=== B8 CEL: Journey-based navigacio LIVE! ===

A felhasznalo a sajat CEL-ja alapjan talal el — nem kell tudnia
hogy mi hol van technikai szempontbol.

B8 UTAN:
  - Sidebar: 6 journey-based csoport (NEM 5 technikai csoport)
  - Dashboard: 4 journey kartya (kattinthato, statisztikakkal)
  - Breadcrumb: "Dashboard > Dokumentum Feldolgozas > Verifikacio"
  - SpecWriter + Cubix a menuben
  - Journey 1 (Invoice): Email → Documents → Verify → Approve — koherens flow
  - Journey 2 (Monitoring): Dashboard drill-down → Costs → Quality → Audit
  - 0 console error, dark mode + responsive
```

---

## B8 FELADAT: 6 lepes — Sidebar → Breadcrumb → Dashboard → Journey 1-2 → E2E → Commit

> **Gate:** Uj navigacio LIVE, Journey 1 (Invoice) + Journey 2 (Monitoring) E2E mukodik,
> Journey 3+4 meglevo funkciok osszekotve, 0 console error.
> **Eszkozok:** `/dev-step`, `/regression`, `/lint-check`, Playwright
> **Docker:** PostgreSQL (5433), Redis (6379) — KELL!

---

### LEPES 1: B8.1 — Sidebar.tsx ujrairas (6 journey-based csoport)

```
Hol: aiflow-admin/src/layout/Sidebar.tsx (182 sor → UJRAIRAS)

Cel: 5 technikai csoport → 6 journey-based csoport + TOBBI bottom menu.

KONKRET TEENDOK:

1. MENU_GROUPS konstans TELJES CSERE — a B6 terv (63_UI_USER_JOURNEYS.md § 2) alapjan:

   const MENU_GROUPS: MenuGroup[] = [
     {
       labelKey: "aiflow.menu.documentProcessing",
       defaultOpen: true,
       items: [
         { path: "/documents", labelKey: "aiflow.menu.documents", icon: "file-text" },
         { path: "/emails", labelKey: "aiflow.menu.emailScan", icon: "mail" },
         { path: "/reviews", labelKey: "aiflow.menu.verification", icon: "check-circle" },
       ],
     },
     {
       labelKey: "aiflow.menu.knowledgeBase",
       defaultOpen: false,
       items: [
         { path: "/rag", labelKey: "aiflow.menu.collections", icon: "book-open" },
       ],
     },
     {
       labelKey: "aiflow.menu.generation",
       defaultOpen: false,
       items: [
         { path: "/process-docs", labelKey: "aiflow.menu.diagrams", icon: "git-branch" },
         { path: "/spec-writer", labelKey: "aiflow.menu.specWriter", icon: "file-plus" },
         { path: "/media", labelKey: "aiflow.menu.mediaProcessing", icon: "headphones" },
       ],
     },
     {
       labelKey: "aiflow.menu.monitoring",
       defaultOpen: true,
       items: [
         { path: "/runs", labelKey: "aiflow.menu.pipelineRuns", icon: "play-circle" },
         { path: "/costs", labelKey: "aiflow.menu.costs", icon: "trending-up" },
         { path: "/monitoring", labelKey: "aiflow.menu.serviceHealth", icon: "activity" },
         { path: "/quality", labelKey: "aiflow.menu.llmQuality", icon: "bar-chart" },
         { path: "/audit", labelKey: "aiflow.menu.auditLog", icon: "clock" },
       ],
     },
     {
       labelKey: "aiflow.menu.settings",
       defaultOpen: false,
       items: [
         { path: "/admin", labelKey: "aiflow.menu.usersApi", icon: "users" },
         { path: "/pipelines", labelKey: "aiflow.menu.pipelineTemplates", icon: "layers" },
         { path: "/services", labelKey: "aiflow.menu.serviceCatalog", icon: "server" },
       ],
     },
   ];

   // Bottom menu (kulon renderelve, Sidebar aljan):
   const BOTTOM_ITEMS: MenuItem[] = [
     { path: "/rpa", labelKey: "aiflow.menu.rpaBrowser", icon: "terminal" },
     { path: "/cubix", labelKey: "aiflow.menu.cubixCourse", icon: "book" },
   ];

2. i18n kulcsok: hu.json + en.json → ~20 uj "aiflow.menu.*" kulcs
   (minden csoport es item kulon forditas)

3. Icon set: a jelenlegi MenuIcon SVG path-okat bovitsd az uj ikonokkal
   (file-text, check-circle, book-open, git-branch, file-plus, headphones,
    play-circle, trending-up, activity, bar-chart, clock, layers, server, terminal)
   Forras: Heroicons / Untitled UI line icon set (24x24 viewBox, strokeWidth 2)

4. Bottom menu rendereles: a Sidebar aljan kulon szekció
   (halvanyabb szin, kisebb text, "Tobbi" / "More" fejlec)

5. Active state: a jelenlegi NavLink isActive logika MARAD.
   Uj: ha barmelyik item aktiv a csoportban, a csoport fejlec is highlighted legyen.

6. Responsive: 768px alatt sidebar collapse → csak ikonok latszanak (tooltip a label)
   (ha mar van collapse logika, bovitsd; ha nincs, uj)

FIGYELEM:
- NE valtoztasd a route-okat! Csak a menu STRUKTURA valtozik.
- /reviews a menuben "Verifikacio" cimkevel → navigal /reviews-ra,
  de B7-ben mar redirect banner van → hosszu tavon /documents/:id/verify
- A regi menu csoport labelKey-eket NE torold a locale fajlokbol (backward compat)

Gate: Sidebar renderel 6 csoporttal + bottom menu, minden link navigal,
      tsc --noEmit 0 hiba.
```

### LEPES 2: B8.2 — Breadcrumb komponens

```
Hol: aiflow-admin/src/components-new/Breadcrumb.tsx (UJ fajl)
     aiflow-admin/src/layout/AppShell.tsx (modositas — Breadcrumb beillesztes)

Cel: "Dashboard > Dokumentum Feldolgozas > Verifikacio" tipusu kontextus-jelzo.

KONKRET TEENDOK:

1. Uj komponens: Breadcrumb.tsx
   
   Props: nincs (az aktualis route-bol szamolja ki)
   
   Logika:
   - useLocation() → pathname
   - BREADCRUMB_MAP: Record<string, { group: string; label: string }[]> 
     Pl. "/documents" → [{ group: "Dashboard", label: "/" }, { group: "Dokum. Feldolgozas", label: "/documents" }]
     Pl. "/documents/:id/verify" → [Dashboard, Dokum. Feldolgozas, Verifikacio]
     Pl. "/costs" → [Dashboard, Monitoring, Koltsegek]
   - useParams() → dinamikus :id resolvolas (document source_file ha elerheto)
   
   Megjelenes:
   - Horizontalis: "Dashboard / Dokumentum Feldolgozas / Verifikacio"
   - Kattinthato linkek (utolso elem NEM link, szurke text)
   - Tailwind: text-xs text-gray-500, separator: "/"
   - Dark mode: text-gray-400

2. AppShell.tsx: a <main> elem tetejere Breadcrumb beillesztes
   (a Sidebar mellett a content area tetejere)

3. i18n: a breadcrumb csoport nevek ugyanazok mint a Sidebar csoport nevek
   (ujrahasznalhato "aiflow.menu.*" kulcsok)

Gate: Breadcrumb lathato minden oldalon, helyes hierarchia,
      kattinthato linkek, tsc 0 hiba.
```

### LEPES 3: B8.3 — Dashboard.tsx: 4 Journey kartya

```
Hol: aiflow-admin/src/pages-new/Dashboard.tsx (299 sor — bovites)

Cel: 4 journey belépő kártya a Dashboard tetejere — kattinthatoak, statisztikakkal.

KONKRET TEENDOK:

1. 4 Journey kartya a meglevo KPI-k FOLE:

   +------------------+ +------------------+ +------------------+ +------------------+
   | Szamla           | | Tudasbazis       | | Generalas        | | Monitoring       |
   | Feldolgozas      | | (RAG)            | | (AI Output)      | | (Governance)     |
   |                  | |                  | |                  | |                  |
   | 23 dokumentum    | | 5 kollekcio      | | 12 diagram       | | 4 service UP     |
   | 3 ellenorizetlen | | 1,240 chunk      | | 8 spec           | | 2 alert          |
   |                  | |                  | |                  | |                  |
   | [Megnyitas →]    | | [Megnyitas →]    | | [Megnyitas →]    | | [Megnyitas →]    |
   +------------------+ +------------------+ +------------------+ +------------------+

   Kattintas: 
   - Journey 1 → /documents
   - Journey 2 → /rag
   - Journey 3 → /process-docs
   - Journey 4 → /runs

2. Statisztikak: useApi() hook-kal valodi adatokat kerdez le
   - Journey 1: GET /api/v1/documents?limit=1 → total + pending verify count
   - Journey 2: GET /api/v1/rag/collections → total + total chunks
   - Journey 3: combination (diagrams + specs count)
   - Journey 4: GET /api/v1/services → UP/DOWN count

3. Kartya stilus:
   - Tailwind: rounded-xl border shadow-sm hover:shadow-md transition
   - Ikon: journey-specifikus (file-text / book-open / git-branch / activity)
   - Szin: journey-specifikus keret szin (brand / emerald / violet / amber)
   - Dark mode: bg-gray-900 border-gray-700

4. Responsive: 4 oszlop → 2 oszlop (md breakpoint) → 1 oszlop (sm)

Gate: 4 kartya lathato, kattinthato, statisztikak betoltenek (vagy "—" ha offline),
      responsive mukodik, tsc 0 hiba.
```

### LEPES 4: B8.4 — Journey 1+2 finomitasok + B5 integracio

```
Hol: Tobb oldal finomhangolasa

Cel: Journey 1 (Invoice) es Journey 2 (Monitoring) koherens flow.

KONKRET TEENDOK:

1. JOURNEY 1 — Invoice Pipeline finomitasok:
   a) Documents oldal: ha az URL ?filter=invoice_finder → szurt lista
      (filter parameter a meglevo DataTable-be, query string alapu)
   b) DocumentDetail.tsx: "Verify" gomb + confidence badge jobban kiemelve
   c) B5.1 fix: ProcessDocs.tsx diagram_type selector → 3 opcio
      (flowchart / sequence / bpmn_swimlane — jelenleg hardcoded "BPMN")

2. JOURNEY 2 — Monitoring finomitasok:
   a) Dashboard: ha barmelyik service DOWN vagy quality < 0.7 → alert banner
      (piros/sarga strip a Dashboard teteje, "2 service needs attention" link)
   b) Runs oldal: pipeline detail-bol "Ujrainditás" gomb (meglevo API:
      POST /api/v1/pipelines/{id}/execute)

3. JOURNEY 3+4 — meglevo funkciok osszekotese (keves munka):
   a) RAG: /rag/:id tabbed nezet mar mukodik — nincs teendo
   b) Generalas: SpecWriter mar menuben van (LEPES 1) — nincs teendo

Gate: Journey 1 documents szuro mukodik, diagram_type 3 opcio,
      Journey 2 alert banner + restart gomb mukodik.
```

### LEPES 5: B8.5 — Playwright E2E tesztek + regresszio

```
Hol: tests/e2e/test_journey_navigation.py (UJ fajl)

Cel: Uj navigacio E2E + journey flow tesztek.

KONKRET TEENDOK:

1. Uj E2E fajl: tests/e2e/test_journey_navigation.py

   class TestJourneyNavigation:

     def test_sidebar_has_6_groups(self, authenticated_page: Page):
       """Sidebar renders 6 journey-based groups + bottom section."""
       # Ellenorzes: 6 csoport fejlec lathato
       # Minden menuelem kattinthato (navigacio mukodik)

     def test_breadcrumb_shows_hierarchy(self, authenticated_page: Page):
       """Navigate to documents → breadcrumb shows Dashboard > Dokum. Feldolgozas."""
       # navigate_to /documents → breadcrumb "Dashboard / Dokumentum" lathato

     def test_dashboard_journey_cards(self, authenticated_page: Page):
       """Dashboard shows 4 clickable journey cards."""
       # 4 kartya lathato
       # Kattintas → navigacio a helyes oldalra

     def test_journey1_invoice_flow(self, authenticated_page: Page):
       """Journey 1: Documents → detail → verify page reachable."""
       # /documents → ha van adat → kattintas → detail → Verify gomb

     def test_journey2_monitoring_flow(self, authenticated_page: Page):
       """Journey 2: Dashboard → drill-down runs → costs → back."""
       # Dashboard → "Monitoring" kartya → /runs → /costs navigacio

2. /regression → 1443+ unit + 109+ E2E + 96 promptfoo — 0 uj fail
3. /lint-check → ruff + tsc → 0 uj warning
4. tsc --noEmit → 0 hiba

Gate: legalabb 3 E2E teszt PASS, /regression PASS, /lint-check PASS.
```

### LEPES 6: B8.6 — Plan update + Commit(ok)

```
/update-plan → 58 B8 row DONE + datum + commit SHA(k)
             CLAUDE.md + 01_PLAN/CLAUDE.md kulcsszamok frissitese:
               - E2E: 109 → 109+ (uj navigation E2E-k)
               - Unit: 1443 (valtozatlan ha nincs uj backend)

Commit strategia — KULON COMMITOK feature-onkent:
  1. feat(sprint-b): B8.1 sidebar journey-based navigation — 6 groups + breadcrumb
     (Sidebar.tsx + Breadcrumb.tsx + AppShell.tsx + i18n)

  2. feat(sprint-b): B8.2 dashboard journey cards + J1/J2 finomitasok
     (Dashboard.tsx + Documents.tsx + ProcessDocs.tsx finomitasok)

  3. test(sprint-b): B8.3 journey navigation E2E tests
     (tests/e2e/test_journey_navigation.py)

  4. docs(sprint-b): B8 plan update + key numbers
     (58 plan + CLAUDE.md)

Commit mindegyikhez:
  Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
```

---

## VEGREHAJTAS SORRENDJE

```
=== FAZIS A: NAVIGACIO ATEPITES (LEPES 1-2) ===

--- LEPES 1: Sidebar.tsx ujrairas ---
6 journey csoport + bottom menu
i18n kulcsok (hu + en)
Uj ikonok (14 uj SVG path)

--- LEPES 2: Breadcrumb komponens ---
Breadcrumb.tsx UJ
AppShell.tsx bovites
Route → breadcrumb mapping

>>> Navigacio KESZ — Sidebar + Breadcrumb elo.


=== FAZIS B: DASHBOARD + JOURNEY FINOMITAS (LEPES 3-4) ===

--- LEPES 3: Dashboard journey kartyak ---
4 kartya (kattinthato, statisztikakkal)
Responsive grid

--- LEPES 4: Journey 1+2 finomitasok ---
Documents filter, diagram_type fix, alert banner, restart gomb

>>> UI KESZ — Journey 1+2 koherens.


=== FAZIS C: TESZTEK + LEZARAS (LEPES 5-6) ===

--- LEPES 5: E2E + regresszio ---
tests/e2e/test_journey_navigation.py (5 teszt)
/regression + /lint-check

--- LEPES 6: Plan + Commit ---
/update-plan → 58 B8 DONE
2-4 commit
```

---

## KORNYEZET ELLENORZES

```bash
# Branch + HEAD
git branch --show-current     # → feature/v1.3.0-service-excellence
git log --oneline -5           # → a23db05 (B7.3 tests), 5464829 (B7.2 UI), f09f32e (B7.1 API), ...

# Docker KELL!
docker ps | grep -E "postgres|redis"

# Jelenlegi Sidebar forras:
wc -l aiflow-admin/src/layout/Sidebar.tsx          # → 182 sor
wc -l aiflow-admin/src/layout/AppShell.tsx          # → meglevo

# Dashboard:
wc -l aiflow-admin/src/pages-new/Dashboard.tsx      # → 299 sor

# Breadcrumb: NEM LETEZIK meg!
ls aiflow-admin/src/components-new/Breadcrumb*       # → nincs

# Router (NEM valtozik!):
wc -l aiflow-admin/src/router.tsx                    # → 99 sor

# E2E:
ls tests/e2e/test_*journey* tests/e2e/test_*nav*    # → test_journey_document.py (referenciak)
```

---

## MEGLEVO KOD REFERENCIAK (olvasd el mielott irsz!)

```
# KRITIKUS — ezeket MINDENKEPPEN olvasd MIELOTT modositasz:
aiflow-admin/src/layout/Sidebar.tsx                — 182 sor, FO MODOSITASI CELPONT
aiflow-admin/src/layout/AppShell.tsx               — Sidebar + content wrapper (Breadcrumb ide kerul)
aiflow-admin/src/router.tsx                        — 99 sor, NEM VALTOZIK (route-ok fixek)
aiflow-admin/src/pages-new/Dashboard.tsx           — 299 sor, journey kartyak ide kerulnek

# B6 terv (IA redesign + journey definiciok):
01_PLAN/63_UI_USER_JOURNEYS.md                     — § 2 IA terv (sor 111-221), § 3 Journey Map, § 4 Journey 1-4

# Oldalak amikhez nyulni kell:
aiflow-admin/src/pages-new/Documents.tsx           — filter parameter support
aiflow-admin/src/pages-new/ProcessDocs.tsx         — diagram_type selector fix (B5.1)
aiflow-admin/src/pages-new/Runs.tsx                — restart gomb hozzaadas

# i18n:
aiflow-admin/src/locales/hu.json                   — magyar forditas
aiflow-admin/src/locales/en.json                   — angol forditas

# E2E referencia:
tests/e2e/test_journey_document.py                 — 131 sor, document journey minta
tests/e2e/conftest.py                              — navigate_to(), authenticated_page fixture
```

---

## FONTOS SZABALYOK (CODE session)

- **Route-ok NEM valtoznak!** A menu STRUKTURA valtozik, NEM az URL-ek. `/documents` marad `/documents`.
- **NE tord el a jelenlegi oldalak mukodeseit!** Minden jelenlegi link tovabbra is mukodjon.
- **Backward compat:** a regi `aiflow.menu.operations` stb i18n kulcsok MARADNAK (mas tesztek hasznalhatjak).
- **Async-first** — ha API-t hivsz (Dashboard statisztikak), useApi() hook-kal.
- **structlog** — never print(), always `logger.info("event", key=value)`.
- **i18n**: minden uj string `translate()` — `aiflow.menu.*` kulcsok, hu.json + en.json.
- **Dark mode**: minden uj/modositott komponensnek legyen dark: variansa.
- **Responsive**: sidebar collapse 768px-nel, kartyak stackelodesek.
- **0 console error**: Playwright browser_console_messages ellenorzes.
- **NE commitolj failing tesztet!** Ha instabil, `@pytest.mark.skip(reason="...")`.
- **`.code-workspace`, `out/`, `100_*.md`, session prompt NE commitold.**
- **Branch:** SOHA NE commitolj main-ra.

---

## B8 GATE CHECKLIST

```
FAZIS A — NAVIGACIO:

B8.1 — Sidebar:
[ ] Sidebar.tsx: 6 journey-based csoport (NEM 5 technikai)
[ ] Bottom menu: /rpa + /cubix kulon szekcioban
[ ] /spec-writer a menuben (GENERALAS csoport)
[ ] i18n: ~20 uj "aiflow.menu.*" kulcs (hu + en)
[ ] Uj ikonok mukodnek (14 uj SVG path)
[ ] Minden link navigal a helyes oldalra
[ ] tsc --noEmit 0 hiba

B8.2 — Breadcrumb:
[ ] Breadcrumb.tsx letezik (components-new/)
[ ] AppShell.tsx-ben renderelodik a content felett
[ ] Helyes hierarchia: Dashboard > Csoport > Oldal
[ ] Kattinthato linkek (utolso NEM link)
[ ] Dark mode

FAZIS B — DASHBOARD + JOURNEY:

B8.3 — Dashboard kartyak:
[ ] 4 journey kartya lathato
[ ] Kattinthato → navigacio
[ ] Statisztikak betoltenek (vagy "—" fallback)
[ ] Responsive: 4 → 2 → 1 oszlop

B8.4 — Journey finomitasok:
[ ] Documents: ?filter= parameter mukodik
[ ] ProcessDocs: diagram_type 3 opcio (flowchart/sequence/bpmn_swimlane)
[ ] Dashboard: alert banner ha service DOWN
[ ] Runs: restart gomb

FAZIS C — TESZTEK + LEZARAS:

B8.5 — E2E:
[ ] tests/e2e/test_journey_navigation.py letezik
[ ] Legalabb 3 E2E teszt PASS
[ ] /regression PASS (1443+ unit, 109+ E2E — 0 uj fail)
[ ] /lint-check PASS (ruff + tsc)

B8.6 — Commit + Plan:
[ ] 2-4 commit (feature-enkent)
[ ] 58 plan B8 row DONE + datum + commit SHA
[ ] CLAUDE.md kulcsszamok frissitese (E2E+)
[ ] 0 failing teszt
```

---

## BECSULT SCOPE

- **1 ujrairt fajl** (Sidebar.tsx — 182 → ~220 sor)
- **1 uj komponens** (Breadcrumb.tsx — ~80 sor)
- **1 bovitett layout** (AppShell.tsx — Breadcrumb beillesztes)
- **1 bovitett oldal** (Dashboard.tsx — 4 journey kartya: 299 → ~400 sor)
- **2-3 finomitott oldal** (Documents.tsx, ProcessDocs.tsx, Runs.tsx)
- **~20 uj i18n kulcs** (hu.json + en.json)
- **~5 uj E2E teszt** (test_journey_navigation.py)
- **2 modositott plan fajl** (58 plan + CLAUDE.md)
- **2-4 commit** (navigacio + dashboard/journey + teszt + plan)

**Becsult hossz:** 1 teljes session (3-4 ora). Legnagyobb idoigeny:
- Sidebar + Breadcrumb + ikonok + i18n: ~1.5 ora
- Dashboard kartyak + Journey finomitasok: ~1 ora
- E2E tesztek + regresszio: ~45 perc
- Plan + commit: ~30 perc

---

## SPRINT B UTEMTERV (S32 utan, frissitett)

```
S19: B0      — DONE (4b09aad)
S20: B1.1    — DONE (f6670a1)
S21: B1.2    — DONE (7cec90b)
S22: B2.1    — DONE (51ce1bf)
S23: B2.2    — DONE (62e829b)
S24: B3.1    — DONE (372e08b)
S25: B3.2    — DONE (aecce10)
S26a: B3.E2E — DONE (0b5e542 + f1f0029)
S27a: B3.E2E — DONE (8b10fd6 + 70f505f)
S27b: B3.5   — DONE (4579cd2)
S28: B4.1    — DONE (9eb2769)
S29: B4.2    — DONE (e4f322e)
S30: B5      — DONE (11364cd + a77a912 + 41d3e60 + c7079c6)
S31: B6      — DONE (8261e88) — Portal audit + 4 journey (design-only)
S32: B7      — DONE (f09f32e + 5464829 + a23db05) — Verification Page v2
S33: B8      ← KOVETKEZO SESSION — UI Journey implementacio (THIS PROMPT)
S34: B9      — Docker deploy + UI pipeline trigger
S35: B10     — POST-AUDIT + javitasok
S36: B11     — v1.3.0 tag + merge
```

---

## KESZ JELENTES FORMATUM (B8 vege)

```
# S33 — B8 UI Journey Implementacio DONE

## Kimenet
- aiflow-admin/src/layout/Sidebar.tsx: 6 journey-based csoport + bottom menu
- aiflow-admin/src/components-new/Breadcrumb.tsx: uj kontextus komponens
- aiflow-admin/src/layout/AppShell.tsx: Breadcrumb integracio
- aiflow-admin/src/pages-new/Dashboard.tsx: 4 journey kartya
- aiflow-admin/src/pages-new/Documents.tsx: ?filter= parameter support
- aiflow-admin/src/pages-new/ProcessDocs.tsx: diagram_type 3 opcio
- aiflow-admin/src/locales/{hu,en}.json: ~20 uj i18n kulcs
- tests/e2e/test_journey_navigation.py: {X} E2E teszt

## Kulcsszamok
- E2E tesztek: 109 → {109+X}
- Unit tesztek: 1443 (valtozatlan)

## Tesztek
- /regression: PASS ({total} teszt, 0 uj fail)
- /lint-check: PASS (ruff + tsc)
- E2E test_journey_navigation.py: {X}/{X} PASS

## Commit(ok)
{SHA1} feat(sprint-b): B8.1 sidebar journey-based navigation — 6 groups + breadcrumb
{SHA2} feat(sprint-b): B8.2 dashboard journey cards + J1/J2 finomitasok
{SHA3} test(sprint-b): B8.3 journey navigation E2E tests
{SHA4} docs(sprint-b): B8 plan update + key numbers

## Kovetkezo session
S34 = B9 — Docker deploy + UI pipeline trigger
```

---

*Kovetkezo ervenyben: S33 = B8 (UI Journey impl.) → S34 = B9 (Docker deploy) → S35 = B10 (POST-AUDIT)*
