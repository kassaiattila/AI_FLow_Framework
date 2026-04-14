# AIFlow Sprint C — Session 41 Prompt (C6.1-C6.2: Journey E2E Validation — J1 + J5)

> **Datum:** 2026-04-10
> **Branch:** `feature/v1.4.0-ui-refinement` | **HEAD:** `4381105`
> **Port:** API 8102 (dev), Frontend 5174 (dev)
> **Elozo session:** S40 — C4.2 + C5 DONE (RAG chunk search + sidebar cleanup)
> **Terv:** `01_PLAN/65_SPRINT_C_UI_JOURNEY_FIRST_PLAN.md` (C6 szekcio)
> **Session tipus:** E2E TEST — Journey 1 (Document) + Journey 5 (Pipeline) deep validation
> **Workflow:** Meglevo E2E bovites → uj deep tesztek → futtas → fix → Commit

---

## KONTEXTUS

### S40 Eredmenyek (C4.2 + C5 — KESZ)

```
✅ C4.2: Chunk search backend (q + document_name params) + UI (debounced input + dropdown)
✅ C5: Sidebar aria-label, hu.json reviewQueue fix
✅ tsc --noEmit 0 error
```

### Sprint C Allapot

```
19 aktiv UI oldal (18 + RunDetail) + 5 archiv | Login kulon
J1 Invoice: Scan ✅ → Documents(badge) ✅ → Verify ✅ → Export ✅
J5 Pipeline: Runs ✅ → RunDetail ✅ → Retry ✅
J2a Monitoring: restart ✅, auto-refresh ✅
J2a Quality: rubric kattinthato ✅
J2b Admin: Create User ✅, Generate Key ✅, Revoke Key ✅
J2b Audit: filter ✅, export CSV ✅
J3 RAG: Ingest ✅ → Chat ✅ → Chunks (search ✅)
C5 Sidebar: 6-csoport ✅, aria-label ✅, reviewQueue hu ✅
```

### Meglevo E2E Journey Tesztek (32 db)

```
test_journey_document.py   — 5 teszt: nav + table render + action buttons + crossnav + 0 error
test_journey_pipeline.py   — 5 teszt: list + nav + runs + loop + search
test_journey_admin.py      — 5 teszt: KPI + nav + notification + admin→audit + loop
test_journey_rag.py        — 5 teszt: page load + nav + services + crossnav + 0 error
test_journey_quality.py    — 5 teszt: KPIs + ext links + costs + monitoring + loop
test_journey_navigation.py — 7 teszt: sidebar groups + breadcrumb + cards + J1/J2 flow

PROBLEMA: Ezek foleg NAVIGACIOS tesztek — oldalak betoltesenek es linkeknek a tesztelese.
CEL: Melysegi E2E tesztek amik valodi funkcionalitast tesztelnek (CRUD, keres, filter, export).
```

---

## S41 FELADATOK: 4 lepes

### LEPES 1: C6.1 — J1 Document Journey Deep E2E (20 perc)

```
Cel: Boviteni test_journey_document.py-t VALODI interakciokkal.

Fajl: tests/e2e/test_journey_document.py

Uj tesztek:

A) test_documents_table_has_data_or_empty_state():
  - /documents betoltes
  - Ha van adat: ellenorizni hogy legalabb 1 sor van a tablazatban
  - Ha nincs: "No data" / empty state megjelenik
  - Source tag (Demo/Live) lathato

B) test_document_detail_navigation():
  - /documents oldalrol kattintas az elso document sorra
  - /documents/:id betoltodik
  - Header section, Vendor section, Line Items section megjelenik
  - "Back" gomb visszavisz /documents-re

C) test_verification_page_loads():
  - /documents/:id/verify oldal betoltes (elso doksi ID-vel)
  - Verify gombok megjelennek (Approve, Reject)
  - Confidence badge lathato
  - Keyboard navigation hint lathato

D) test_documents_filter_and_search():
  - /documents oldalon filter dropdown (filterAll / filterProcessed)
  - Search mezo: beleir egy szot → tabla frissul
  - Clear → visszaall

E) test_document_delete_confirm_dialog():
  - Ha van Delete gomb → kattintas → ConfirmDialog megjelenik
  - Cancel → dialog bezarol, doksi megmarad

Minta (Playwright pattern):
  async with page.expect_navigation():
      await page.click("text=Documents")
  await expect(page.locator("table tbody tr")).to_have_count(...)
  # VAGY
  await expect(page.locator("[data-testid='empty-state']")).to_be_visible()
```

---

### LEPES 2: C6.2 — J5 Pipeline Journey Deep E2E (20 perc)

```
Cel: Boviteni test_journey_pipeline.py-t VALODI interakciokkal.

Fajl: tests/e2e/test_journey_pipeline.py

Uj tesztek:

A) test_runs_table_shows_status_badges():
  - /runs betoltes
  - Ha van adat: status badge (completed/failed/running) megjelenik
  - Skill + Duration + Cost oszlopok lathatok

B) test_run_detail_step_log():
  - /runs oldalrol kattintas az elso run sorra
  - /runs/:id (RunDetail) betoltodik
  - "Step Log" section megjelenik
  - Step sorok: step name + model + tokens lathato
  - Export JSON gomb letezik

C) test_run_detail_retry_button():
  - /runs/:id oldalon "Retry" gomb megjelenik
  - Kattintas → ConfirmDialog ("Retry this pipeline?")
  - Cancel → dialog bezarol

D) test_pipeline_detail_yaml_tab():
  - /pipelines oldalrol kattintas egy pipeline-ra
  - /pipelines/:id betoltodik
  - "YAML" tab kattintas → YAML tartalom megjelenik
  - "Copy YAML" gomb letezik

E) test_services_catalog_pipeline_badge():
  - /services oldalon Pipeline-ready badge lathato (legalabb 1 service-nel)
  - "Run Pipeline" gomb letezik pipeline-ready service-eknel
```

---

### LEPES 3: Fix + Kiegeszites (10 perc)

```
Cel: Teszteket futtatni es a talalt UI hibakat javitani.

3a) Teszt futtas:
    cd aiflow-admin && npx playwright test tests/e2e/test_journey_document.py tests/e2e/test_journey_pipeline.py
    
    FONTOS: Ha az app nem fut (API/UI offline), a tesztek SKIP-elodnek.
    Ebben az esetben: legalabb tsc + a teszt fajlok szintaktikai helyessege legyen PASS.

3b) Ha valami fail:
    - 404 endpoint → ellenorizni route-okat
    - Missing data-testid → hozzaadni a komponenshez
    - Timeout → wait strategia modositas

3c) tsc ellenorzes:
    cd aiflow-admin && npx tsc --noEmit → 0 error
```

---

### LEPES 4: Commit (5 perc)

```
4a) git add tests/e2e/test_journey_document.py \
            tests/e2e/test_journey_pipeline.py \
            [+ barmelyik UI fajl amit javitottunk]

4b) Commit message:
    test(e2e): Sprint C S41 — C6.1-C6.2 deep E2E for J1 Document + J5 Pipeline journeys

Gate: tsc 0 error, uj tesztek szintaktikailag helyesek, meglevo tesztek nem tortek el
```

---

## KORNYEZET ELLENORZES

```bash
# Jelenlegi allapot
git branch --show-current     # → feature/v1.4.0-ui-refinement
git log --oneline -3           # → 4381105 (S40 commit)

# Meglevo E2E tesztek
ls tests/e2e/test_journey_*.py

# API + Frontend fut?
curl -s http://localhost:8102/api/v1/health 2>/dev/null | head -3
curl -s http://localhost:5174 2>/dev/null | head -3

# Playwright telepitve?
cd aiflow-admin && npx playwright --version
```

---

## MEGLEVO KOD REFERENCIAK

```
# Meglevo E2E tesztek (BOVITENDO):
tests/e2e/test_journey_document.py    — 5 teszt (nav-only, boviteni CRUD-dal)
tests/e2e/test_journey_pipeline.py    — 5 teszt (nav-only, boviteni RunDetail-lal)
tests/e2e/conftest.py                 — Playwright fixtures, base URL, login
tests/e2e/pages/                      — Page Object pattern (base, dashboard, login)

# UI oldalak amiket tesztelunk:
aiflow-admin/src/pages-new/Documents.tsx       — J1: document lista, filter, search
aiflow-admin/src/pages-new/DocumentDetail.tsx  — J1: document detail, sections
aiflow-admin/src/pages-new/Verification.tsx    — J1: verify page, approve/reject
aiflow-admin/src/pages-new/Runs.tsx            — J5: run lista, status badges
aiflow-admin/src/pages-new/RunDetail.tsx       — J5: step log, retry, export (S38-ban keszult)
aiflow-admin/src/pages-new/Pipelines.tsx       — J5: pipeline lista, YAML tab
aiflow-admin/src/pages-new/PipelineDetail.tsx  — J5: pipeline detail, steps
aiflow-admin/src/pages-new/Services.tsx        — J5: service catalog, pipeline badge

# Ujrahasznalas mintak:
tests/e2e/test_journey_navigation.py  — MINTA: sidebar group + journey flow tesztek
tests/e2e/test_journey_admin.py       — MINTA: dashboard KPI + admin CRUD journey
```

---

## SPRINT C UTEMTERV

```
S37: C0+C1 — J4 archive + infra + J1 Invoice flow       ✅ DONE
S38: C2.1-C2.3 — RunDetail + Monitoring                  ✅ DONE
S39: C2.4-C2.6 — Quality + Admin CRUD + Audit            ✅ DONE
S40: C4+C5 — RAG chunk search + Sidebar cleanup           ✅ DONE
S41: C6.1-C6.2 — J1 + J5 deep E2E                         ← EZ A SESSION
S42: C6.3-C6.4 — J2a/J2b + J3 deep E2E
S43: C6.5 + C7 — Cross-journey + Regresszio + v1.4.0 tag
```

---

*Sprint C otodik session: S41 = C6.1 + C6.2 (Document + Pipeline journey deep E2E)*
