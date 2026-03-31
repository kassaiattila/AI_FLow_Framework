# AIFlow Admin — UX Redesign & Polish Plan

> **Datum:** 2026-03-31
> **Elozmeny:** Session 2 — Playwright teszteles, bug fixek, funkcionalis audit
> **Cel:** Professzionalis, egyseges megjelenes; logikus flow; kompakt layoutok

---

## 0. AKTUALIS ALLAPOT (Session 2 utan)

### Ami elkeszult es mukodik
- **Dashboard** — KPI kartyak (5 skill, 16 run, $0.47), skill kartyak, backend status
- **Workflow Runs** lista + show (pipeline timeline 4 lepessel)
- **Invoices** lista → kozvetlenul verifikaciora navigal
- **Emails** lista + show (intent, entitasok, routing, csatolmanyok)
- **Verification** — valos szamlakep + sablon toggle, overlay, szerkesztes, jovahagyas, mentes
- **Process Docs** — preset → LLM generalas → Mermaid BPMN flowchart
- **RAG Chat** — chat UI, preset kerdesek
- **Cubix** — kurzus megjelenites
- **Invoice/Email Upload** — dropzone → Python subprocess feldolgozas → eredmeny
- **Costs** — KPI-k, skill + step bontas tablak
- **i18n** — HU/EN teljes, toggle mukodik
- **Dark/Light theme** toggle

### Session 2-ben javitott hibak
| # | Hiba | Javitas |
|---|------|---------|
| 1 | `ra.input.password.toggle_hidden` forditas | password.toggle_hidden hozzaadva |
| 2 | `ra.action.add_filter` forditas | add_filter hozzaadva |
| 3 | "Not authenticated" console warning | ra.auth.auth_check_error kulcsra cserelve |
| 4 | Nyers ISO datumok | toLocaleString() formazas FunctionField-del |
| 5 | Nyers float ms pipeline lepeseknel | Math.round() kerekites |
| 6 | Fekete canvas kijeleloles | CONFIDENCE_FILL_HIGHLIGHT rgba map (invalid rgb()+"33" javitva) |
| 7 | DataPointEditor kijeleloes hatter | Explicit rgba szin dark mode-hoz |
| 8 | Kategoria cimkek mindig magyar | useLocaleState() alapu nyelvi valtas |
| 9 | Invoice lista → show helyett verify | rowClick atirasra /verify utvonalra |
| 10 | Verifikacio: valos szamla kep | /images/ kivetel a Next.js auth middleware-bol |
| 11 | Pontatlan overlay valos kepen | Eredeti kep / Sablon nezet toggle |

---

## 1. DESIGN ELVEK

1. **Information density** — Kevesebb ures hely, tobb hasznos adat egy kepernyore
2. **Visual hierarchy** — A fontos adatok (low-confidence, hibak) azonnal latszanak
3. **Konzisztencia** — Egyseges card/tabla/badge stilus minden oldalon
4. **One-click flow** — A leggyakoribb muvelet legyen a legkevesebb kattintas
5. **Progressive disclosure** — Reszletek csak igeny eseten (expand, modal, tab)

---

## 2. FELADATOK FAZISOKRA BONTVA

### Fazis 1: Verification Redesign (PRIORITAS — leggyakrabban hasznalt oldal)

#### 1.1 Header kompaktitas
- **Jelenlegi:** Egyetlen zsufolt sor (Vissza + fajlnev + Reszletek + invoice/incoming + Auto/Javitva/OK badge-ek)
- **Uj:** Ket soros fejlec:
  - Felso: `← Vissza | fajlnev | Reszletek gomb`
  - Also: `invoice | incoming | Auto:22 | Javitva:0 | OK:0 | progress bar`
- **Fajl:** `VerificationPanel.tsx`

#### 1.2 Toolbar egyszerusites
- **Jelenlegi:** Harom kulonallo toggle csoport + zoom slider egy sorban — zsufolt
- **Uj:** Kompakt icon toolbar:
  - Bal: Overlay ikonok (Mind/Alacsony/Ki) tooltip-ekkel
  - Kozep: Zoom slider (szukebb)
  - Jobb: Kep mod ikonok (foto ikon = valos, sablon ikon = template)
- **Fajl:** `DocumentCanvas.tsx`

#### 1.3 Jobb panel: vizualis hierarchia
- **Jelenlegi:** Minden mezo egyforma meretben, konfidencia % kicsi badge
- **Uj:**
  - Low-confidence (<70%) sorok: piros bal szegel + halvanypiros hatter
  - Medium-confidence (70-90%): narancs bal szegel
  - High-confidence (>90%): nincs extra kiemel, tomor
  - Konfidencia badge szelessege aranyos az ertekkel (mini progress bar)
- **Fajl:** `DataPointEditor.tsx`

#### 1.4 Sticky action bar
- **Jelenlegi:** Alul, scroll utan latszik csak
- **Uj:** Sticky bottom bar, mindig lathato, kompakt
- **Fajl:** `VerificationPanel.tsx`

#### 1.5 Billentyuzet navigacio
- Tab/Shift+Tab: kovetkezo/elozo mezo
- Enter: jovahagyas (confirm)
- E: szerkesztes mod
- Escape: megse
- **Fajl:** `DataPointEditor.tsx`, `use-verification-state.ts`

---

### Fazis 2: Invoice Lista Javitas

#### 2.1 Nem-feldolgozott sorok megkulonboztetese
- **Jelenlegi:** 0 Ft + "!" badge keverve a valos adatokkal — felrevezeto
- **Uj:**
  - Feltetel: ha `totals.gross_total === 0` ES nincs `vendor.name` → "Feldolgozatlan" status
  - Vizualis: Szurke/halvanyjitt sor, "Nincs adat" felirat az ures cellakban
  - Szuro: "Csak feldolgozott" / "Mind" toggle a toolbar-ban
- **Fajl:** `InvoiceList.tsx`

#### 2.2 Vendor nev megtisztitas
- **Jelenlegi:** Fajlnev fragmentumok jelennek meg vendor nevkent a nem-feldolgozott soroknal
- **Uj:** Ha a vendor.name megegyezik a fajlnev prefixevel → ures (dash "-")
- **Fajl:** `dataProvider.ts` vagy `InvoiceList.tsx` FunctionField

#### 2.3 Gyors muveletek oszlop
- Uj utolso oszlop: ikon gombok (Verifikacio, Reszletek) soronkent
- Jelenlegi rowClick megmarad (verify-re visz), de igy a reszletek is egybol elerheto
- **Fajl:** `InvoiceList.tsx`

---

### Fazis 3: Run Show Kompakt Layout

#### 3.1 Fejlec atalakitas
- **Jelenlegi:** 8 egymas alatti label-value par — sok ures hely
- **Uj:** Kompakt kartya grid (2-3 oszlop):
  ```
  ┌─────────────────────────────────────────────┐
  │ Run ID: run-xxx    Skill: invoice_processor │
  │ Status: ✓ completed   Duration: 2.9s       │
  │ Cost: $0.0300         Started: 2026.03.31   │
  │ Input: KL-2021-4.pdf  Output: Conf. 100%   │
  └─────────────────────────────────────────────┘
  ```
- **Fajl:** `RunShow.tsx`

#### 3.2 Vissza gomb
- Hozzaadni: `← Vissza a listara` gomb a fejlec ele
- **Fajl:** `RunShow.tsx`

---

### Fazis 4: Dashboard Finomhangolas

#### 4.1 Skill kartya leirasok magyarra
- **Jelenlegi:** Angol leirasok ("BPMN diagrams from natural language")
- **Uj:** `t()` hasznalata a skill leirasokhoz, i18nProvider bovites
- **Fajl:** `Dashboard.tsx`, `i18nProvider.ts`

#### 4.2 KPI kartyak tipografia
- A csupa nagybetus label ("SKILLS", "OSSZES FUTAS") → Normal case, vastagabb, nagyobb font
- Az ikon + szam paros legyen vizualisan kiemeltebb
- **Fajl:** `Dashboard.tsx`

---

### Fazis 5: Costs Page Vizualizacio

#### 5.1 Skill koltseg bar chart
- Uj: Egyszeru horizontal bar chart a skill koltsegekhez
- Hasznalat: MUI `LinearProgress` vagy egyszeru SVG bar-ok (nem kell chart library)
- A tabla folott, vizualisan egybol atlathato
- **Fajl:** `pages/CostsPage.tsx`

#### 5.2 Napi/heti trend
- Opcionalisan: egyszerű spark-line a futasok szamanak alakulasarol
- Alacsony prioritas — csak ha van erteke
- **Fajl:** `pages/CostsPage.tsx`

---

### Fazis 6: Process Docs Viewer Bovites

#### 6.1 Split view layout
- **Jelenlegi:** Kis kartya a kepernyő kozepen, generalt diagram alatta
- **Uj:** Bal: input textarea + presets + generate gomb (35%), Jobb: eredmeny (65%)
- Az eredmeny teruleten: Mermaid renderelt diagram (nem csak kod)
- **Fajl:** `pages/ProcessDocViewer.tsx`

#### 6.2 Mermaid diagram rendereles
- Jelenleg a Mermaid kod szovegkent jelenik meg
- A `mermaid` package mar fuggoseg — rendereljuk SVG-be
- Alatta: "Kod" tab a nyers Mermaid koddal, "Diagram" tab a renderelttel
- **Fajl:** `pages/ProcessDocViewer.tsx`

---

### Fazis 7: Globalis UX Javitasok

#### 7.1 Sidebar menu nevek i18n
- Az "Invoices" es "Emails" React Admin resource nevek angolul maradnak magyarul is
- Megoldas: Resource `options.label` → `translate()` hivas
- **Fajl:** `App.tsx`

#### 7.2 Konzisztens Vissza navigacio
- Minden show/detail oldalon: `← Vissza` gomb a fejlec bal oldalán
- Egyseges pattern minden resource-hoz
- **Fajl:** `RunShow.tsx`, `EmailShow.tsx`, `VerificationPanel.tsx`

#### 7.3 Loading/Error allapotok
- Skeleton loading a tablazatokhoz (React Admin beepitett)
- Error boundary a custom route-okhoz
- **Fajl:** globalis

#### 7.4 Responsive design
- Mobil-friendly sidebar (React Admin collapse)
- A verification oldal stack elrendezesre valt kicsi kepernyokon
- **Fajl:** `VerificationPanel.tsx`, `DocumentCanvas.tsx`

---

## 3. BECSULT MUNKAIDO

| Fazis | Feladat | Bonyolultsag | Becsles |
|-------|---------|-------------|---------|
| 1 | Verification Redesign | Kozepes-Magas | 1 session |
| 2 | Invoice Lista | Alacsony | 0.5 session |
| 3 | Run Show Kompakt | Alacsony | 0.5 session |
| 4 | Dashboard Finomhangolas | Alacsony | 0.5 session |
| 5 | Costs Vizualizacio | Kozepes | 0.5 session |
| 6 | Process Docs Viewer | Kozepes | 1 session |
| 7 | Globalis UX | Alacsony | 0.5 session |
| **Ossz** | | | **~4 session** |

---

## 4. JAVASOLT SORREND

```
Session 3: Fazis 1 (Verification Redesign) — ez a legnagyobb hatasú
Session 4: Fazis 2 + 3 (Invoice lista + Run Show kompakt)
Session 5: Fazis 4 + 5 + 6 (Dashboard + Costs + Process Docs)
Session 6: Fazis 7 (Globalis javitasok) + teljes regresszios teszt
```

---

## 5. NEM CELJAI ENNEK A TERVNEK

- Uj skill viewerek fejlesztese (az kulon task)
- Backend API valtoztatas (csak frontend)
- Mobil app (csak responsive web)
- Auth/RBAC valtoztatas (meglevo marad)

---

## 6. ERINTETT FAJLOK LISTAJA

```
aiflow-admin/src/
  App.tsx                           — Fazis 7.1 (resource label i18n)
  Dashboard.tsx                     — Fazis 4 (skill leirasok, KPI tipografia)
  i18nProvider.ts                   — Fazis 4 (uj forditas kulcsok)
  resources/
    RunShow.tsx                     — Fazis 3 (kompakt fejlec, vissza gomb)
    InvoiceList.tsx                 — Fazis 2 (feldolgozatlan jeloles, gyors muveletek)
    EmailShow.tsx                   — Fazis 7.2 (vissza gomb)
  pages/
    ProcessDocViewer.tsx            — Fazis 6 (split view, mermaid rendereles)
    CostsPage.tsx                   — Fazis 5 (bar chart)
  verification/
    VerificationPanel.tsx           — Fazis 1.1, 1.4 (header, sticky bar)
    DocumentCanvas.tsx              — Fazis 1.2 (toolbar)
    DataPointEditor.tsx             — Fazis 1.3, 1.5 (hierarchia, billentyuzet)
    use-verification-state.ts       — Fazis 1.5 (keyboard nav state)
```

---

## 7. SIKERKRITERIUMOK

- [ ] 0 console error minden oldalon
- [ ] Minden oldal 2 masodperc alatt betolt
- [ ] HU/EN toggle: minden szoveg valtozik
- [ ] Verification: billentyuzettel vegignavigalhato
- [ ] Invoice lista: nem-feldolgozott sorok vizualisan elkülonulnek
- [ ] Costs: vizualis chart latszik
- [ ] Process Docs: renderelt diagram (nem kod)
- [ ] Playwright E2E teszt: minden oldal screenshot regresszio
