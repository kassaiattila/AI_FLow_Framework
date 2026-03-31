# AIFlow Admin — UX Redesign & Polish Plan

> **Datum:** 2026-03-31
> **Utolso frissites:** 2026-03-31 Session 3 utan
> **Elozmeny:** Session 2 — Playwright teszteles, bug fixek, funkcionalis audit
> **Cel:** Professzionalis, egyseges megjelenes; logikus flow; kompakt layoutok

---

## 0. AKTUALIS ALLAPOT (Session 3 utan)

### Projekt statisztika
- **31 TSX/TS fajl** az aiflow-admin/src/ alatt
- **~165 i18n kulcs** HU + EN teljes lefedettseg
- **10 oldal/route** + dashboard
- **0 TypeScript hiba** (tsc --noEmit pass)
- **React 19 + React-Admin 5.14 + MUI 7 + Vite 7 + Mermaid 11.13**

### Ami elkeszult es mukodik
- **Dashboard** — KPI kartyak (5 skill, 16 run, $0.47), skill kartyak i18n leirasokkal, backend status
- **Workflow Runs** lista + show (kompakt 4-oszlopos grid fejlec, pipeline timeline, vissza gomb)
- **Invoices** lista (feldolgozatlan sorok szurke, vendor nev tisztitas, gyors muveletek oszlop, Mind/Feldolgozott szuro)
- **Invoice Show** — kompakt 3-oszlopos grid (Header|Vendor|Buyer + Line Items tabla + Totals|Validation)
- **Invoice Verification** — ketsoros header, ikon toolbar tooltipekkel, konfidencia hierarchia (piros/narancs/zold), sticky action bar, billentyuzet navigacio (Tab/Enter/E/Esc), field label i18n
- **Emails** lista + show (intent, entitasok, routing, csatolmanyok, vissza gomb)
- **Process Docs** — split view (35/65): bal input + jobb diagram, Mermaid 11.x rendereles
- **RAG Chat** — chat UI, preset kerdesek
- **Cubix** — kurzus megjelenites
- **Invoice/Email Upload** — dropzone → Python subprocess feldolgozas → eredmeny
- **Costs** — KPI-k, horizontal bar chart + skill/step bontas tablak
- **i18n** — HU/EN teljes, sidebar menu nevek is forditva
- **Dark/Light theme** toggle
- **Export performance** — CSV/JSON/Excel pufferelt I/O (OneDrive-friendly)

### Session 3 elvegzett munkak

| # | Fazis | Feladat | Commit | Statusz |
|---|-------|---------|--------|---------|
| 1 | F1 | Verification Redesign (header, toolbar, hierarchia, sticky bar, keyboard, i18n) | `05155d8` | **KESZ** |
| 2 | F2 | Invoice lista polish (feldolgozatlan sorok, vendor tisztitas, gyors muveletek, szuro) | `b24234f` | **KESZ** |
| 3 | F3 | Run Show kompakt layout (4-oszlopos grid fejlec, vissza gomb) | `b24234f` | **KESZ** |
| 4 | F4 | Dashboard finomhangolas (skill leirasok i18n, KPI tipografia) | `5567383` | **KESZ** |
| 5 | F5 | Costs vizualizacio (horizontal bar chart) | `5567383` | **KESZ** |
| 6 | F6 | Process Docs split view layout (35/65) | `5567383` | **KESZ** |
| 7 | F7 | Globalis UX (sidebar i18n, EmailShow vissza gomb) | `5567383` | **KESZ** |
| 8 | — | Invoice Show kompakt redesign (3-oszlopos grid) | `d50a04a` | **KESZ** |
| 9 | — | Mermaid 11.x render API fix + hiba megjelenites | `e33fc5d` | **KESZ** |
| 10 | — | CSV/JSON/Excel export I/O optimalizalas | `4d85470` | **KESZ** |

### Session 2-ben javitott hibak
| # | Hiba | Javitas |
|---|------|---------|
| 1 | `ra.input.password.toggle_hidden` forditas | password.toggle_hidden hozzaadva |
| 2 | `ra.action.add_filter` forditas | add_filter hozzaadva |
| 3 | "Not authenticated" console warning | ra.auth.auth_check_error kulcsra cserelve |
| 4 | Nyers ISO datumok | toLocaleString() formazas FunctionField-del |
| 5 | Nyers float ms pipeline lepeseknel | Math.round() kerekites |
| 6 | Fekete canvas kijeleloles | CONFIDENCE_FILL_HIGHLIGHT rgba map javitva |
| 7 | DataPointEditor kijeleloes hatter | Explicit rgba szin dark mode-hoz |
| 8 | Kategoria cimkek mindig magyar | useLocaleState() alapu nyelvi valtas |
| 9 | Invoice lista → show helyett verify | rowClick atirasra /verify utvonalra |
| 10 | Verifikacio: valos szamla kep | /images/ kivetel a Next.js auth middleware-bol |
| 11 | Pontatlan overlay valos kepen | Eredeti kep / Sablon nezet toggle |

### Session 3-ban javitott hibak
| # | Hiba | Javitas |
|---|------|---------|
| 12 | Verification field labelek angolban is magyarul | labelEn mezo hozzaadva document-layout.ts + DataPointEditor locale-alapu valtas |
| 13 | Mermaid 11.x render API "Syntax error in text" | render() API frissites, suppressErrorRendering, hiba szoveg megjelentes |
| 14 | CSV/JSON/Excel export lassu OneDrive-on | io.StringIO puffer (CSV), tempfile+move (Excel), egyszeri write |

---

## 1. DESIGN ELVEK

1. **Information density** — Kevesebb ures hely, tobb hasznos adat egy kepernyore
2. **Visual hierarchy** — A fontos adatok (low-confidence, hibak) azonnal latszanak
3. **Konzisztencia** — Egyseges card/tabla/badge stilus minden oldalon
4. **One-click flow** — A leggyakoribb muvelet legyen a legkevesebb kattintas
5. **Progressive disclosure** — Reszletek csak igeny eseten (expand, modal, tab)

---

## 2. FELADATOK — STATUSZ

### Fazis 1: Verification Redesign ✅ KESZ

| # | Feladat | Fajl | Statusz |
|---|---------|------|---------|
| 1.1 | Header kompaktitas (ketsoros) | VerificationPanel.tsx | ✅ |
| 1.2 | Toolbar egyszerusites (ikon toolbar) | DocumentCanvas.tsx | ✅ |
| 1.3 | Jobb panel vizualis hierarchia | DataPointEditor.tsx | ✅ |
| 1.4 | Sticky action bar | VerificationPanel.tsx | ✅ |
| 1.5 | Billentyuzet navigacio | DataPointEditor.tsx, use-verification-state.ts | ✅ |

### Fazis 2: Invoice Lista Javitas ✅ KESZ

| # | Feladat | Fajl | Statusz |
|---|---------|------|---------|
| 2.1 | Nem-feldolgozott sorok megkulonboztetese | InvoiceList.tsx, dataProvider.ts | ✅ |
| 2.2 | Vendor nev megtisztitas | InvoiceList.tsx | ✅ |
| 2.3 | Gyors muveletek oszlop | InvoiceList.tsx | ✅ |

### Fazis 3: Run Show Kompakt Layout ✅ KESZ

| # | Feladat | Fajl | Statusz |
|---|---------|------|---------|
| 3.1 | Fejlec atalakitas (4-oszlopos grid) | RunShow.tsx | ✅ |
| 3.2 | Vissza gomb | RunShow.tsx | ✅ |

### Fazis 4: Dashboard Finomhangolas ✅ KESZ

| # | Feladat | Fajl | Statusz |
|---|---------|------|---------|
| 4.1 | Skill kartya leirasok i18n | Dashboard.tsx, i18nProvider.ts | ✅ |
| 4.2 | KPI kartyak tipografia | Dashboard.tsx | ✅ |

### Fazis 5: Costs Page Vizualizacio ✅ KESZ

| # | Feladat | Fajl | Statusz |
|---|---------|------|---------|
| 5.1 | Skill koltseg horizontal bar chart | CostsPage.tsx | ✅ |
| 5.2 | Napi/heti trend | — | KIHAGYVA (alacsony prioritas) |

### Fazis 6: Process Docs Viewer Bovites ✅ KESZ

| # | Feladat | Fajl | Statusz |
|---|---------|------|---------|
| 6.1 | Split view layout (35/65) | ProcessDocViewer.tsx | ✅ |
| 6.2 | Mermaid diagram rendereles | ProcessDocViewer.tsx | ✅ (11.x fix-szel) |

### Fazis 7: Globalis UX Javitasok ✅ KESZ

| # | Feladat | Fajl | Statusz |
|---|---------|------|---------|
| 7.1 | Sidebar menu nevek i18n | Menu.tsx, i18nProvider.ts | ✅ |
| 7.2 | Konzisztens Vissza navigacio | RunShow, EmailShow, InvoiceShow, VerificationPanel | ✅ |
| 7.3 | Loading/Error allapotok | Beepitett React Admin + custom oldalak | ✅ |
| 7.4 | Responsive design | Grid layoutok xs/md breakpointokkal | ✅ (alap) |

---

## 3. SIKERKRITERIUMOK — STATUSZ

- [x] 0 console error minden oldalon (kiveve backend API 404 ha szerver nem fut)
- [x] Minden oldal 2 masodperc alatt betolt
- [x] HU/EN toggle: minden szoveg valtozik (beleertve verification field labelek)
- [x] Verification: billentyuzettel vegignavigalhato (Tab/Enter/E/Esc)
- [x] Invoice lista: nem-feldolgozott sorok vizualisan elkülonulnek
- [x] Costs: vizualis bar chart latszik
- [x] Process Docs: renderelt Mermaid diagram (nem kod)
- [ ] Playwright E2E teszt: minden oldal screenshot regresszio — KOVETKEZO SESSION

---

## 4. KOVETKEZO LEPESEK (Session 4+)

### Magas prioritas
- Playwright E2E teszt suite (screenshot regresszio minden oldalhoz)
- Vite proxy atiranyitas kozvetlenul FastAPI-ra az alap CRUD-hoz (Next.js kivagas)
- Invoice lista: valodi szamla adatok megjelenítese (vendor nev, osszeg) feldolgozott soroknal

### Kozepes prioritas
- Responsive finomhangolas (tablet/mobil verification stack layout)
- Costs napi/heti trend sparkline
- Email Show kompakt redesign (mint Invoice Show)
- RAG Chat valodi backend kapcsolat

### Alacsony prioritas
- Cubix viewer bovites (video lejatszo, atirat szinkronizacio)
- Export gombok (CSV letoltes kozvetlenul a UI-bol)
- Dark/Light mode automatikus rendszerbealliitasbol

---

## 5. ERINTETT FAJLOK — VEGLEGES LISTA

```
aiflow-admin/src/
  App.tsx                           — Resource + CustomRoutes definicio
  AppBar.tsx                        — Custom AppBar (i18n + theme toggle)
  Dashboard.tsx                     — KPI kartyak + skill kartyak (i18n leirasok)
  Layout.tsx                        — Layout wrapper (AppBar + Menu)
  Menu.tsx                          — Sidebar menu (i18n resource nevek)
  authProvider.ts                   — Demo auth provider
  dataProvider.ts                   — REST data provider (Next.js API proxy)
  i18nProvider.ts                   — HU/EN ~165 kulcs (polyglot)
  theme.ts                          — Light + dark MUI tema
  components/
    PipelineProgress.tsx            — Animalt pipeline progress
    StepTimeline.tsx                — Workflow step timeline
  resources/
    RunList.tsx                     — Runs tablazat
    RunShow.tsx                     — Kompakt 4-oszlopos grid fejlec + pipeline
    InvoiceList.tsx                 — Feldolgozatlan jeloles, vendor tisztitas, gyors muveletek
    InvoiceShow.tsx                 — 3-oszlopos grid (Header|Vendor|Buyer + Tetelek + Totals|Validacio)
    EmailList.tsx                   — Email tablazat (intent, prioritas)
    EmailShow.tsx                   — Email reszletek (intent, entitasok, routing, csatolmanyok)
  pages/
    CostsPage.tsx                   — KPI + bar chart + skill/step tablak
    ProcessDocViewer.tsx            — Split view (35/65) + Mermaid rendereles
    RagChat.tsx                     — Chat UI preset kerdesekkel
    CubixViewer.tsx                 — Kurzus megjelenites
    InvoiceUpload.tsx               — PDF upload + subprocess feldolgozas
    EmailUpload.tsx                 — Email upload + subprocess feldolgozas
  verification/
    VerificationPanel.tsx           — Ketsoros header, sticky bar, keyboard nav
    DocumentCanvas.tsx              — Ikon toolbar, overlay, zoom
    DataPointEditor.tsx             — Konfidencia hierarchia, mini progress bar
    MockInvoiceSvg.tsx              — SVG sablon szamla
    types.ts                        — TypeScript tipusok (DataPoint, BBox, stb.)
    document-layout.ts              — Mezo elrendezes + i18n labelek
    use-verification-state.ts       — useReducer state management (NEXT/PREV_POINT)
```

---

## 6. NEM CELJAI ENNEK A TERVNEK

- Uj skill viewerek fejlesztese (az kulon task)
- Backend API valtoztatas (csak frontend, kivetel: export I/O fix)
- Mobil app (csak responsive web)
- Auth/RBAC valtoztatas (meglevo marad)
