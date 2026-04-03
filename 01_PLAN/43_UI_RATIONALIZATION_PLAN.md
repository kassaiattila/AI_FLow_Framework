# AIFlow v1.1.0 — UI Racionalizalas + Untitled UI Migracio + Service Korszerusites

**Datum:** 2026-04-02
**Statusz:** ELFOGADVA
**Verzio:** v1.0.0 → v1.1.0
**Elozmeny:** Service Generalization (F0-F5) KESZ, v1.0.0 tag letrehozva

---

## Context

Az AIFlow v1.0.0 kiadasa utan (F0-F5 COMPLETE, 15 service, 87 API endpoint, 21 UI oldal)
a kovetkezo fazis celja:

1. **UI racionalizalas** — 21 oldal → 16 oldal konszolidalas, 16 menu item → 11
2. **Professzionalis megjelenes** — React Admin + MUI → Untitled UI + Tailwind v4 + React Aria
3. **Service korszerusites** — dinamikus Dashboard, chart-ok, hianyzó endpointok

**Dontes:** A teljes frontend ujrairasra kerult (Untitled UI migracio), mert:
- Professzionalabb, egyedi design
- WCAG AA accessibility (React Aria)
- Figma ↔ Code szinkron (Untitled UI Figma kit + Tokens Studio)
- A jelenlegi MUI + React Admin stack limitalt customizalhatosagu

**Kockazatkezeles:** A migracio fazisonkent tortenik — egy domain TELJESEN KESZ
(beleertve E2E tesztet) mielott a kovetkezore lepunk. A regi MUI oldalak
addig mukodokepes maradnak (inkrementalis migracio).

---

## 1. Architekturalis Dontesek

### 1.1 React Admin eltavolitasa

| React Admin | Uj megoldas |
|-------------|-------------|
| `dataProvider` | `src/lib/api-client.ts` — tipizalt fetch wrapper (`GET/POST/PUT/DELETE`) |
| `authProvider` | `src/lib/auth.ts` — JWT token kezeles (localStorage + refresh) |
| `i18nProvider` (Polyglot) | `src/lib/i18n.ts` — sajat hook (`useTranslate`) + HU/EN JSON fajlok |
| `<Admin>` layout | `src/layout/AppShell.tsx` — Untitled UI sidebar + topbar |
| `<Resource>` | React Router v7 route-ok |
| `<Datagrid>` | `src/components/DataTable.tsx` — Untitled UI Table + React Aria |
| `<List>`, `<Show>` | Custom page-ek Untitled UI komponensekkel |

### 1.2 Uj Tech Stack

```
Untitled UI React (MIT) — 1,100+ ikon, 200+ komponens
Tailwind CSS v4         — token-based theming, JIT
React Aria              — accessibility primitives (WCAG AA)
React Router v7         — routing (mar hasznalatban)
recharts                — chart-ok (lightweight, MIT, ~50KB)
TypeScript 5.1          — strict mode (mar hasznalatban)
Vite 7                  — build (mar hasznalatban)
```

### 1.3 Oldal Konszolidacio (21 → 16 oldal)

| Jelenleg | Uj | Strategia |
|----------|-----|-----------|
| Documents (List+Show) + DocumentUpload | `/documents` | Tabbed: List + Upload |
| `/documents/:id/verify` | `/documents/:id/verify` | Marad (komplex) |
| Emails (List+Show) + EmailUpload + EmailConnectors | `/emails` | Tabbed: Inbox + Upload + Connectors |
| CollectionManager + CollectionDetail + RagChat | `/rag` + `/rag/:id` | Tabbed: Collections + Chat; Detail kulon |
| Dashboard | `/` | Ujratervezes (dinamikus, sparkline) |
| ProcessDocViewer | `/process-docs` | Ujratervezes |
| CubixViewer | `/cubix` | Ujratervezes (Dashboard skill card-okrol erheto el) |
| CostsPage | `/costs` | Ujratervezes (recharts chart-ok) |
| MediaViewer | `/media` | Ujratervezes |
| RpaViewer | `/rpa` | Ujratervezes |
| ReviewQueue | `/reviews` | Ujratervezes |
| MonitoringDashboard | `/monitoring` | Ujratervezes |
| AuditLog | `/audit` | Ujratervezes |
| AdminPage | `/admin` | Ujratervezes |
| — | `/login` | UJ: Login page |

### 1.4 Uj Menu Struktura (16 → 11 item, 4 csoport)

```
[Dashboard]                      — mindig lathato

── Operations ──                 — collapsible, default open
   Runs                          /runs
   Cost Analytics                /costs
   Monitoring                    /monitoring

── Data ──                       — collapsible, default open
   Documents                     /documents  (List + Upload tab)
   Emails                        /emails     (Inbox + Upload + Connectors tab)

── AI Services ──                — collapsible, default open
   RAG                           /rag        (Collections + Chat tab)
   Process Docs                  /process-docs
   Media                         /media
   RPA                           /rpa

── Admin ──                      — collapsible, default collapsed
   Users & Keys                  /admin
   Audit Log                     /audit
   Human Review                  /reviews
```

---

## 2. Ujrahasznalhato Komponens Konyvtar

### 2.1 Layout (`src/layout/`)

| Komponens | Funkcio |
|-----------|---------|
| `AppShell.tsx` | Fo layout: sidebar + topbar + content area |
| `Sidebar.tsx` | Collapsible menu csoportokkal, active state, responsive |
| `TopBar.tsx` | Logo + Cmd+K search + notifications + user avatar + HU/EN toggle |
| `PageLayout.tsx` | Oldal wrapper: title + subtitle + source badge + actions |

### 2.2 Adatmegjelenitesi komponensek (`src/components/`)

| Komponens | Funkcio |
|-----------|---------|
| `DataTable.tsx` | Generic tabla: columns def, sort, pagination, row click, empty state |
| `KpiCard.tsx` | KPI kartya: ertek + label + trend sparkline + szin |
| `StatusBadge.tsx` | Live/Demo/Healthy/Degraded badge |
| `TabLayout.tsx` | Tab navigacio (React Aria Tabs) |
| `EmptyState.tsx` | Ures allapot: ikon + uzenet + CTA gomb |
| `LoadingState.tsx` | Skeleton loading |
| `ErrorState.tsx` | Hiba: uzenet + retry gomb |
| `ConfidenceBadge.tsx` | AI confidence (Governor Pattern) |
| `FileUpload.tsx` | Drag-and-drop zona |
| `SearchInput.tsx` | Kereso mezo debounce-szal |
| `DateRangePicker.tsx` | Datum intervallum valaszto |
| `ConfirmDialog.tsx` | Megerosito dialog (React Aria Dialog) |
| `PipelineProgress.tsx` | Pipeline step progress (megtartva) |
| `StepTimeline.tsx` | Vertikalis timeline (megtartva) |
| `SkillCard.tsx` | Skill kartya: nev, status badge, run count |

---

## 3. Fazis Bontas (7 fazis, ~42-48 nap)

> **MINDEN fazis a 7 HARD GATE pipeline-on megy at.**
> **Egy fazis CSAK AKKOR KESZ ha MINDEN gate PASS.**
> **Melyseg szabaly: egy oldal TELJESEN KESZ mielott a kovetkezore lepunk.**

### F6.0: Foundation — Uj Stack Setup (5-6 nap)

**Cel:** Untitled UI + Tailwind v4 + React Aria alapok, layout shell, auth, i18n, routing.

**Deliverables:**
1. Untitled UI + Tailwind v4 + React Aria telepites
2. `tailwind.config.ts` — AIFlow design tokenek
3. `src/lib/api-client.ts` — tipizalt API kliens
4. `src/lib/auth.ts` — JWT auth (login, logout, refresh)
5. `src/lib/i18n.ts` — `useTranslate()` hook + TranslationProvider
6. `src/locales/hu.json` + `en.json` — 290+ kulcs migracio
7. `src/layout/AppShell.tsx` + `Sidebar.tsx` + `TopBar.tsx`
8. `src/pages/Login.tsx`
9. Base komponensek: PageLayout, EmptyState, LoadingState, ErrorState, StatusBadge
10. `src/router.tsx` — React Router v7 (auth guard)
11. Regi MUI oldalak ideiglenes wrapper-ben mukodnek

**Gate kriteriumok:**
- Gate 1: `01_PLAN/F6_UI_RATIONALIZATION_JOURNEY.md`
- Gate 4: Figma design — AppShell, Sidebar, TopBar, Login
- Gate 5: `tsc --noEmit` PASS
- Gate 6: Playwright E2E — login, sidebar nav, HU/EN, light/dark
- Gate 7: PAGE_SPECS.md frissites

### F6.1: Dashboard (5-6 nap)

**Cel:** Dinamikus skill lista, KPI sparkline-ok, aktiv pipeline-ok.

**Deliverables:** Dashboard.tsx, KpiCard.tsx, SkillCard.tsx, ActivePipelines.tsx, RecentActivity.tsx

**Backend munka:**
- `GET /api/v1/skills/summary` — skill-ek + statusz + run count
- `GET /api/v1/runs/stats` — 7 napos trend

### F6.2: Documents Domain (6-7 nap)

**Cel:** Documents + Upload + Verify — egyseges tabbed oldal.

**Journey:** `01_PLAN/F1_DOCUMENT_EXTRACTOR_JOURNEY.md` (MAR LETEZIK)

### F6.3: Emails Domain (5-6 nap)

**Cel:** Emails + Upload + Connectors — egyseges tabbed oldal.

**Journey:** `01_PLAN/F2_EMAIL_CONNECTOR_JOURNEY.md` (MAR LETEZIK)

### F6.4: RAG + AI Services (6-7 nap)

**Cel:** RAG (Collections + Chat), Process Docs, Media, RPA, Review.

**Journey:** `F3_RAG_ENGINE_JOURNEY.md` + `F4_RPA_MEDIA_DIAGRAM_JOURNEY.md` (MAR LETEZIK)

### F6.5: Operations + Admin (5-6 nap)

**Cel:** Runs, Costs (recharts), Monitoring, Audit, Admin.

**Backend munka:**
- `GET /api/v1/costs/daily` — napi koltseg trend
- `GET /api/v1/costs/by-model` — model szintu bontas

**Journey:** `01_PLAN/F5_MONITORING_GOVERNANCE_JOURNEY.md` (MAR LETEZIK)

### F6.6: Polish + React Admin Eltavolitas (5-6 nap)

**Cel:** React Admin + MUI eltavolitas, teljes regresszio, accessibility audit.

**Gate:** MINDEN 16 oldal E2E PASS, bundle < 500KB, Lighthouse Accessibility > 90

---

## 4. Backend Korszerusites

### Uj API Endpointok

| Endpoint | Fazis | Leiras |
|----------|-------|--------|
| `GET /api/v1/skills/summary` | F6.1 | Skill lista + statusz + run count |
| `GET /api/v1/runs/stats` | F6.1 | 7 napos trend (run count, cost, success rate) |
| `GET /api/v1/costs/daily` | F6.5 | Napi koltseg trend (date range) |
| `GET /api/v1/costs/by-model` | F6.5 | Model szintu bontas |

### SSE Bovites
- Dashboard aktiv pipeline-ok: `/api/v1/runs/stream`
- Document processing: mar letezik
- RAG Chat streaming: mar letezik

---

## 5. Migracios Strategia

### Inkrementalis Migracio
```
F6.0: Uj shell — REGI oldalak beagyazva
F6.1-F6.5: Oldalak EGYENKENT cserelve
F6.6: React Admin + MUI ELTAVOLITVA
```

### Rollback
- Minden fazis KULON git branch-en
- Merge csak PASS E2E utan

### i18n Migracio
- `i18nProvider.ts` → `src/locales/hu.json` + `en.json`
- Kulcs nevek megtartva (`aiflow.dashboard.title`, stb.)
- React Admin kulcsok (`ra.*`) torolve F6.6-ban

---

## 6. Design Token Rendszer

```javascript
// tailwind.config.ts
colors: {
  brand:   { 50: '#eef2ff', 500: '#4f46e5', 600: '#4338ca', 900: '#1e1b4b' },
  surface: { light: '#f8fafc', dark: '#0f172a' },
  status:  { success: '#059669', warning: '#d97706', error: '#dc2626', info: '#2563eb' }
}
typography: { fontFamily: '"Inter", sans-serif', fontSize: { base: '13px' } }
```

---

## 7. Fajl Struktura

```
aiflow-admin/src/
  layout/      — AppShell, Sidebar, TopBar
  components/  — DataTable, KpiCard, StatusBadge, TabLayout, EmptyState, LoadingState, ErrorState, ...
  pages/       — Login, Dashboard, Documents, Emails, Rag, ProcessDocs, Media, Rpa, Reviews, Runs, Costs, Monitoring, Audit, Admin
  lib/         — api-client, auth, i18n, hooks
  locales/     — hu.json, en.json
  router.tsx   — React Router v7 config
  main.tsx     — entry point
  index.css    — Tailwind directives
```

---

## 8. Verifikacios Terv

Minden fazisban: `tsc --noEmit` + `npm run build` + Playwright E2E + i18n HU/EN + light/dark + source badge

Vegso regresszio (F6.6): 16 oldal E2E, bundle < 500KB, Lighthouse Accessibility > 90

---

## 9. Osszefoglalo

| Fazis | Tartalom | Nap | Uj Endpointok |
|-------|----------|-----|---------------|
| F6.0 | Foundation: Untitled UI + Shell + Auth + i18n | 5-6 | 0 |
| F6.1 | Dashboard: KPI sparkline, skill cards | 5-6 | 2-3 |
| F6.2 | Documents: tabbed list+upload+verify | 6-7 | 0 |
| F6.3 | Emails: tabbed inbox+upload+connectors | 5-6 | 0 |
| F6.4 | RAG + AI Services: 5 oldal | 6-7 | 0 |
| F6.5 | Operations + Admin: 6 oldal + recharts | 5-6 | 1-2 |
| F6.6 | Polish: React Admin eltavolitas + regresszio | 5-6 | 0 |
| **TOTAL** | | **~42-48** | **3-5** |

---

## 10. Kapcsolodo Dokumentaciok

- `01_PLAN/42_SERVICE_GENERALIZATION_PLAN.md` — Elozo fazis (F0-F5 KESZ)
- `01_PLAN/STATUS_v1.0.0_FINAL.md` — v1.0.0 helyzetjelentes
- `aiflow-admin/figma-sync/REDESIGN_PLAN.md` — Eredeti redesign vizió
- `aiflow-admin/figma-sync/PAGE_SPECS.md` — Figma design specifikaciok

## 11. Elofeltetel: CLAUDE.md + Command File Frissitesek

Az implementacio ELSO lepesekent frissitendo:

### CLAUDE.md frissitesek:
1. "Current Phase" → UI Modernization (v1.0.0 → v1.1.0)
2. "Tech Stack" → Untitled UI + Tailwind v4 hivatkozas
3. "Key plan documents" → 43_UI_RATIONALIZATION_PLAN.md hozzaadasa
4. "Admin UI Development Rules" → MUI → Untitled UI szabalyok
5. "Directory Structure" → uj mappaszerkezet
6. Gate Artefact Registry → F6 sor
7. Valos teszteles tablazat → F6 sor

### Command file frissitesek:
- **KRITIKUS:** `ui-page.md`, `ui-component.md`, `ui-viewer.md` — MUI → Untitled UI
- **Reszleges:** `ui-design.md`, `dev-step.md` — peldakod frissites
- **Valtozatlan:** `ui-journey.md`, `ui-api-endpoint.md`, `start-phase.md`, tobbi
