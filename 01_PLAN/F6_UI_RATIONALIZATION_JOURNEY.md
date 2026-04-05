# F6 UI Rationalization + Untitled UI Migration — User Journey

> **Fazis:** F6 (UI Modernization, v1.0.0 → v1.1.0)
> **Elozo fazisok:** F0-F5 TELJES (v1.0.0, 2026-04-02)
> **Migracio:** React Admin + MUI → Untitled UI + Tailwind v4 + React Aria
> **Terv:** `01_PLAN/43_UI_RATIONALIZATION_PLAN.md`

---

## F6.0: Foundation — Login + Navigation + Shell

### Actor
**Minden felhasznalo** — bejelentkezik, navigal az oldalak kozott, nyelvet/temat valt.

### Goal
Uj layout shell (AppShell + Sidebar + TopBar), bejelentkezo oldal, i18n, auth.

### Steps
1. Login oldal megnyitasa (`/login`)
2. Email + jelszo megadasa → JWT token
3. Dashboard-ra iranyitas
4. Sidebar navigacio (4 collapsible csoport, 11 menu item)
5. HU/EN nyelv valtas (TopBar)
6. Light/dark tema valtas (TopBar)
7. Kijelentkezes

### API Endpoints (F6.0 — mar letezo, NEM kell uj)
| # | Method | Path | Purpose |
|---|--------|------|---------|
| 1 | POST | `/api/v1/auth/login` | Bejelentkezes (JWT token) |
| 2 | POST | `/api/v1/auth/refresh` | Token frissites |
| 3 | GET | `/api/v1/auth/me` | Aktualis felhasznalo |
| 4 | GET | `/health` | Backend status |

### UI Pages (F6.0)
| Oldal | Route | Komponens | Fo funkcio |
|-------|-------|-----------|------------|
| Login | `/login` | `Login.tsx` | Email/jelszo form |
| Shell | (minden oldal) | `AppShell.tsx` | Sidebar + TopBar + content area |

### Uj Komponensek (F6.0)
| Komponens | Hely | Funkcio |
|-----------|------|---------|
| `AppShell.tsx` | `layout/` | Fo shell: sidebar + topbar + React Router Outlet |
| `Sidebar.tsx` | `layout/` | 4 collapsible csoport, 11 item, active state |
| `TopBar.tsx` | `layout/` | Logo, HU/EN toggle, user menu, backend status |
| `PageLayout.tsx` | `components/` | Oldal wrapper: title + subtitle + source badge + actions |
| `StatusBadge.tsx` | `components/` | Live/Demo badge |
| `EmptyState.tsx` | `components/` | Ures allapot: ikon + uzenet + CTA |
| `LoadingState.tsx` | `components/` | Skeleton loading |
| `ErrorState.tsx` | `components/` | Hiba + retry gomb |

### Uj Lib Fajlok (F6.0)
| Fajl | Funkcio |
|------|---------|
| `api-client.ts` | `fetchApi<T>(method, path, body?)` — tipizalt fetch wrapper |
| `auth.ts` | JWT auth: login, logout, refresh, getToken, isAuthenticated |
| `i18n.ts` | `useTranslate()` hook + `TranslationProvider` context |
| `hooks.ts` | `useApi<T>()`, `useBackendStatus()` kozos hook-ok |

### Success Criteria (F6.0)
1. Login oldal mukodik (email + password → JWT → Dashboard)
2. Sidebar 4 collapsible csoporttal renderelodik
3. Menu itemek a helyes route-okra navigalnak
4. Aktiv menu item kiemelve + szulo csoport automatikusan nyitva
5. HU/EN toggle MINDEN sidebar stringet valtoztatja
6. Light/dark tema toggle mukodik
7. Backend status badge (connected/offline) lathato
8. Kijelentkezes torol tokent + Login-ra iranyit
9. `tsc --noEmit` PASS
10. Playwright E2E PASS

---

## F6.1: Dashboard — KPI + Skills + Activity

### Actor
**Operacios vezeto / Admin** — attekinti a rendszer allapotat, aktiv pipeline-okat, koltsegeket.

### Goal
Professzionalis landing page dinamikus adatokkal, trendekkel, skill kartyakkal.

### Steps
1. Dashboard megnyitasa (`/`)
2. KPI kartyak megtekintese (skills count, runs, cost, success rate) + sparkline trendek
3. Aktiv pipeline-ok monitorozasa (real-time)
4. Skill kartyak atterintese → viewer oldalra navigalas
5. Friss aktivitas lista (utolso 10 run)

### API Endpoints (F6.1 — UJ endpointok!)
| # | Method | Path | Purpose | Statusz |
|---|--------|------|---------|---------|
| 1 | GET | `/api/v1/skills/summary` | Skill lista + status + run count | **UJ** |
| 2 | GET | `/api/v1/runs/stats` | 7 napos trend (napi run count, cost, success rate) | **UJ** |
| 3 | GET | `/api/v1/runs?status=running` | Aktiv pipeline-ok | Ellenorizni |
| 4 | GET | `/api/v1/runs` | Legfrissebb futasok | Letezik |

### UI Pages (F6.1)
| Oldal | Route | Komponens | Fo funkcio |
|-------|-------|-----------|------------|
| Dashboard | `/` | `Dashboard.tsx` | KPI + skills + activity |

### Uj Komponensek (F6.1)
| Komponens | Funkcio |
|-----------|---------|
| `KpiCard.tsx` | Ertek + sparkline (recharts) + delta indikator |
| `SkillCard.tsx` | Skill kartya: nev, status badge, run count, link |
| `ActivePipelines.tsx` | Futo job-ok lista (polling vagy SSE) |
| `RecentActivity.tsx` | Utolso 10 run (DataTable) |
| `DataTable.tsx` | Generikus tabla: columns, sort, pagination, empty state |

### Success Criteria (F6.1)
1. KPI kartyak valos backend adatbol jnnek (`source: "backend"`)
2. Sparkline trendek 7 napos adatbol rajzolodnak (recharts)
3. Skill kartyak dinamikusan toltoddnek (NEM hardcoded lista)
4. Aktiv pipeline szekció mutatja a futo job-okat
5. Friss aktivitas tabla az utolso futasokkal
6. StatusBadge (Live/Demo) lathato
7. HU/EN + light/dark mukodik
8. Playwright E2E PASS

---

## F6.2: Documents — Tabbed List + Upload + Verify

### Actor
**Szamla feldolgozo / Konyvelo** — dokumentumokat tolt fel, feldolgoztatja, verifikalia.

### Goal
Egyseges Documents oldal (21 oldalbol → 1 tabbed page + Verify).
Jelenlegi 3 kulon oldal (DocumentList + DocumentUpload + VerificationPanel) → 1 tabbed + 1 kulon.

### Steps
1. Documents oldal megnyitasa (`/documents`)
2. "List" tab: dokumentum lista, szurok (datum, vendor, status), pagination
3. "Upload" tab: PDF drag-and-drop, pipeline progress (SSE), eredmeny
4. Dokumentum kijelolese → detail nezet
5. "Verify" gomb → `/documents/:id/verify` — mezo szintu verifikacio

### API Endpoints (F6.2 — mind LETEZO)
| # | Method | Path | Purpose |
|---|--------|------|---------|
| 1 | GET | `/api/v1/documents` | Dokumentum lista |
| 2 | GET | `/api/v1/documents/{id}` | Dokumentum detail |
| 3 | POST | `/api/v1/documents/upload` | Upload |
| 4 | POST | `/api/v1/documents/process` | Feldolgozas inditasa |
| 5 | POST | `/api/v1/documents/process-stream` | Feldolgozas SSE stream |
| 6 | POST | `/api/v1/documents/{id}/verify` | Verifikacio |
| 7 | GET | `/api/v1/documents/images/{file}/page_{n}.png` | PDF oldal kep |
| 8 | GET | `/api/v1/extractor/configs` | Extractor config |

### UI Pages (F6.2)
| Oldal | Route | Komponens | Fo funkcio |
|-------|-------|-----------|------------|
| Documents | `/documents` | `Documents.tsx` | Tabbed: List + Upload |
| Verify | `/documents/:id/verify` | `DocumentVerify.tsx` | Canvas + DataPointEditor |

### Uj Komponensek (F6.2)
| Komponens | Funkcio |
|-----------|---------|
| `TabLayout.tsx` | Tab navigacio (React Aria Tabs) |
| `FileUpload.tsx` | Drag-and-drop zona + SSE progress |
| `ConfidenceBadge.tsx` | AI confidence (Governor Pattern: 70% → 100%) |

### Eltavolitott Route-ok (F6.2)
- `/document-upload` → beolvad a Documents "Upload" tab-ba

### Success Criteria (F6.2)
1. Documents oldal 2 tab-bal renderelodik (List + Upload)
2. List tab: szurok, pagination, row click → detail
3. Upload tab: drag-and-drop, SSE pipeline progress, eredmeny
4. Verify oldal: canvas + mezo szerkesztes + Governor Pattern
5. StatusBadge (Live/Demo) lathato
6. `/document-upload` route torolve, redirect `/documents`-ra
7. HU/EN + light/dark mukodik
8. Playwright E2E PASS (upload → process → verify → save → reload)

---

## F6.3: Emails — Tabbed Inbox + Upload + Connectors

### Actor
**Ugyfelszolgalati vezeto** — emaileket fogad, klasszifikaltat, connector-okat konfigural.

### Goal
Egyseges Emails oldal. Jelenlegi 4 kulon oldal → 1 tabbed page.

### Steps
1. Emails oldal megnyitasa (`/emails`)
2. "Inbox" tab: email lista + detail (slide-over)
3. "Upload" tab: email fajl feltoltes + feldolgozas
4. "Connectors" tab: IMAP/O365/Gmail connector CRUD + test

### API Endpoints (F6.3 — mind LETEZO)
| # | Method | Path | Purpose |
|---|--------|------|---------|
| 1 | GET | `/api/v1/emails` | Email lista |
| 2 | GET | `/api/v1/emails/{id}` | Email detail |
| 3 | POST | `/api/v1/emails/upload` | Upload |
| 4 | POST | `/api/v1/emails/classify` | Klasszifikacio |
| 5 | GET/POST/PUT/DELETE | `/api/v1/emails/connectors/*` | Connector CRUD |
| 6 | POST | `/api/v1/emails/connectors/{id}/test` | Connector teszt |

### UI Pages (F6.3)
| Oldal | Route | Komponens |
|-------|-------|-----------|
| Emails | `/emails` | `Emails.tsx` (Tabbed: Inbox + Upload + Connectors) |

### Eltavolitott Route-ok (F6.3)
- `/email-upload` → beolvad "Upload" tab-ba
- `/email-connectors` → beolvad "Connectors" tab-ba

### Success Criteria (F6.3)
1. Emails oldal 3 tab-bal renderelodik
2. Inbox tab: lista + detail (intent, entity, routing info)
3. Upload tab: email fajl feltoltes + feldolgozas
4. Connectors tab: CRUD + test + history
5. HU/EN + light/dark mukodik
6. Playwright E2E PASS

---

## F6.4: RAG + AI Services (5 oldal)

### Actor
**Tudasbazis manager / AI operator** — RAG kollekciot kezel, chat-et hasznal, diagramot general, media-t dolgoz fel.

### Goal
RAG (Collections + Chat) egyseges tabbed oldal + ProcessDocs, Media, RPA, Reviews oldalak ujratervezese.

### Steps (RAG)
1. RAG oldal megnyitasa (`/rag`)
2. "Collections" tab: CRUD + ingest + stats
3. "Chat" tab: kollekcio valasztas → streaming kerdes/valasz + citations
4. Kollekcio detail oldal (`/rag/:id`) — chunks, ingest status

### Steps (AI Services)
5. ProcessDocs: NL input → BPMN diagram → export
6. Media: video/audio upload → STT transcript
7. RPA: config CRUD + execution → log
8. Reviews: pending lista → approve/reject

### API Endpoints — mind LETEZO (F3+F4 journey-kben dokumentalva)

### UI Pages (F6.4)
| Oldal | Route | Komponens |
|-------|-------|-----------|
| RAG | `/rag` | `Rag.tsx` (Tabbed: Collections + Chat) |
| RAG Detail | `/rag/:id` | `RagDetail.tsx` |
| Process Docs | `/process-docs` | `ProcessDocs.tsx` |
| Media | `/media` | `Media.tsx` |
| RPA | `/rpa` | `Rpa.tsx` |
| Reviews | `/reviews` | `Reviews.tsx` |

### Eltavolitott Route-ok (F6.4)
- `/rag-chat` → beolvad RAG "Chat" tab-ba
- `/rag/collections` → `/rag` (fo route)

### Success Criteria (F6.4)
1. RAG oldal 2 tab-bal (Collections + Chat)
2. Chat: streaming valasz, citation panel, hallucination indicator
3. ProcessDocs: Mermaid render + export (SVG/BPMN)
4. Media: upload + STT eredmeny megjeleites
5. RPA: config CRUD + execute + log
6. Reviews: pending/approved/rejected flow
7. MINDEN oldalon StatusBadge, HU/EN, light/dark
8. Playwright E2E PASS (mind 5+1 oldal)

---

## F6.5: Operations + Admin (6 oldal)

### Actor
**Admin / Operacios vezeto** — futasokat, koltsegeket, rendszer egeszseget figyeli, felhasznalokat kezel.

### Steps
1. Runs lista + detail (step timeline, cost breakdown)
2. Costs: recharts chart-ok, datum szuro, tabla-k
3. Monitoring: service health cards, latency, uptime
4. Audit: trail lista + szures + CSV export
5. Admin: user CRUD + API key management

### API Endpoints (F6.5 — 2 UJ!)
| # | Method | Path | Purpose | Statusz |
|---|--------|------|---------|---------|
| 1 | GET | `/api/v1/costs/daily` | Napi koltseg trend | **UJ** |
| 2 | GET | `/api/v1/costs/by-model` | Model szintu bontas | **UJ** |
| 3-... | | (tobbi letezo) | | Letezik |

### UI Pages (F6.5)
| Oldal | Route | Komponens |
|-------|-------|-----------|
| Runs | `/runs` | `Runs.tsx` |
| Run Detail | `/runs/:id` | `RunDetail.tsx` |
| Costs | `/costs` | `Costs.tsx` (recharts) |
| Monitoring | `/monitoring` | `Monitoring.tsx` |
| Audit | `/audit` | `Audit.tsx` |
| Admin | `/admin` | `Admin.tsx` |

### Uj Komponensek (F6.5)
| Komponens | Funkcio |
|-----------|---------|
| `DateRangePicker.tsx` | Datum intervallum valaszto (Costs oldalhoz) |

### Success Criteria (F6.5)
1. Runs: lista + detail (step timeline mukodik)
2. Costs: recharts BarChart + LineChart + DateRangePicker
3. Monitoring: service health cards valos adattal
4. Audit: szurheto, exportalhato
5. Admin: user CRUD + API key CRUD
6. HU/EN + light/dark MINDEN oldalon
7. Playwright E2E PASS

---

## F6.6: Polish + React Admin Eltavolitas

### Actor
**Fejleszto** — regi MUI kod eltavolitasa, vegso audit.

### Goal
React Admin + MUI teljes eltavolitasa, vegso regresszio, accessibility audit.

### Steps
1. React Admin (`react-admin`, `ra-*`) eltavolitas package.json-bol
2. MUI (`@mui/material`, `@mui/icons-material`, `@emotion/*`) eltavolitas
3. Regi fajlok torlese (Dashboard, Menu, Layout, AppBar, theme, dataProvider, authProvider, i18nProvider, regi pages/, resources/, verification/)
4. `npm run build` — HIBA NELKUL
5. Accessibility audit (keyboard nav, screen reader, focus management)
6. Bundle size ellenorzes (< 500KB gzipped)
7. Teljes E2E regresszio (14 oldal)

### Success Criteria (F6.6)
1. SEMMI MUI/React Admin import nem marad a kodban
2. `npm run build` PASS
3. `tsc --noEmit` PASS
4. Bundle < 500KB gzipped
5. Lighthouse Accessibility > 90
6. MINDEN 14 oldal Playwright E2E PASS
7. HU/EN toggle MINDEN oldalon
8. Light/dark MINDEN oldalon
9. Mobile/tablet responsive
10. Demo/Live badge MINDEN oldalon

---

## Osszesitett Route Terkep (F6 utan)

```
/login              → Login.tsx
/                   → Dashboard.tsx
/runs               → Runs.tsx
/runs/:id           → RunDetail.tsx
/costs              → Costs.tsx
/monitoring         → Monitoring.tsx
/documents          → Documents.tsx (Tabbed: List + Upload)
/documents/:id/verify → DocumentVerify.tsx
/emails             → Emails.tsx (Tabbed: Inbox + Upload + Connectors)
/rag                → Rag.tsx (Tabbed: Collections + Chat)
/rag/:id            → RagDetail.tsx
/process-docs       → ProcessDocs.tsx
/media              → Media.tsx
/rpa                → Rpa.tsx
/reviews            → Reviews.tsx
/audit              → Audit.tsx
/admin              → Admin.tsx
/cubix              → Cubix.tsx (Dashboard skill card-okrol erheto el)
```

**Eltavolitott route-ok:**
- `/document-upload` → Documents "Upload" tab
- `/email-upload` → Emails "Upload" tab
- `/email-connectors` → Emails "Connectors" tab
- `/rag-chat` → RAG "Chat" tab
- `/rag/collections` → `/rag`
