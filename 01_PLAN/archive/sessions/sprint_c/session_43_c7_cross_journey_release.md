# AIFlow Sprint C — Session 43 Prompt (C6.5 + C7: Cross-journey E2E + Regression + v1.4.0 Tag)

> **Datum:** 2026-04-14
> **Branch:** `feature/v1.4.0-ui-refinement` | **HEAD:** `134bf15`
> **Port:** API 8102 (dev), Frontend 5174 (dev)
> **Elozo session:** S42 — C6.3-C6.4 DONE (Quality+Admin+RAG deep E2E, 13 uj teszt)
> **Terv:** `01_PLAN/65_SPRINT_C_UI_JOURNEY_FIRST_PLAN.md` (C6.5 + C7 szekcio)
> **Session tipus:** FINAL — Cross-journey validation + Regression + Release tag
> **Workflow:** Cross-journey E2E → Full regression → Version bump → Tag → Commit

---

## KONTEXTUS

### Sprint C Osszegzes (S37-S42 — MIND KESZ)

```
S37: C0+C1 — J4 archive + infra + J1 Invoice flow       ✅ DONE
S38: C2.1-C2.3 — RunDetail + Monitoring                  ✅ DONE
S39: C2.4-C2.6 — Quality + Admin CRUD + Audit            ✅ DONE
S40: C4+C5 — RAG chunk search + Sidebar cleanup           ✅ DONE
S41: C6.1-C6.2 — J1 + J5 deep E2E                         ✅ DONE
S42: C6.3-C6.4 — J2a/J2b + J3 deep E2E                    ✅ DONE
S43: C6.5 + C7 — Cross-journey + Regresszio + v1.4.0 tag  ← EZ A SESSION
```

### Jelenlegi E2E Teszt Allapot (164 osszesen, 53 journey)

```
Journey tesztek (6 fajl, 53 teszt):
  test_journey_navigation.py  — 5 teszt (sidebar, breadcrumb, cards, J1+J2 flow)
  test_journey_document.py    — 10 teszt (5 nav + 5 deep)
  test_journey_pipeline.py    — 10 teszt (5 nav + 5 deep)
  test_journey_quality.py     — 9 teszt (5 nav + 4 deep)
  test_journey_admin.py       — 9 teszt (5 nav + 4 deep)
  test_journey_rag.py         — 10 teszt (5 nav + 5 deep)

Tobbi E2E (111 teszt):
  test_smoke, test_accessibility, test_i18n, test_notifications,
  test_documents, test_pipelines, test_quality, test_verification_v2,
  test_invoice_finder_*, test_diagram_pipeline, test_docker_deploy

Ossz: 164 collected
```

---

## S43 FELADATOK: 4 lepes

### LEPES 1: C6.5 — Cross-Journey Dashboard Validation E2E (15 perc)

```
Cel: Boviteni test_journey_navigation.py-t UJ TestCrossJourneyNavigation class-szal.
A Dashboard 4 journey kartya → MINDEN journey elerheto es visszaterheto.

Fajl: tests/e2e/test_journey_navigation.py

UJ TestCrossJourneyNavigation class:

A) test_dashboard_card_to_j1_documents():
  - / betoltes → Journey kártyak megjelennek (4 db)
  - J1 (Dokumentum Feldolgozas) kartya kattintas
  - → /documents oldalra navigal
  - Oldal tartalom letezik (Document, Dokumentum, table)
  - Vissza navigalas / -re → Dashboard renderel

B) test_dashboard_card_to_j3_rag():
  - / betoltes → J3 (Tudasbazis / RAG) kartya kattintas
  - → /rag oldalra navigal
  - Oldal tartalom letezik (RAG, Collection, Chat)
  - Vissza / → Dashboard OK

C) test_dashboard_card_to_j5_pipelines():
  - / betoltes → J5 (Pipeline & Futasok) kartya kattintas
  - → /runs VAGY /pipelines oldalra navigal
  - Oldal tartalom letezik (Run, Pipeline)
  - Vissza / → Dashboard OK

D) test_dashboard_card_to_j2_monitoring():
  - / betoltes → J2 (Monitoring/Quality) kartya kattintas
  - → /monitoring VAGY /quality oldalra navigal
  - Oldal tartalom letezik (Monitor, Quality, Service)
  - Vissza / → Dashboard OK

E) test_full_cross_journey_loop():
  - Console error tracking bekapcsol
  - / → /documents → /rag → /runs → /monitoring → /admin → /audit → /costs → /quality → /
  - Minden oldalon: body.textContent().length > 50 (nem ures)
  - 0 valos console error az egesz loop soran

Minta: kovetni a meglevo TestJourneyNavigation stilust (l. test_dashboard_journey_cards).
Fontos: a Dashboard journey kartyak CSS selector: "main >> div.cursor-pointer.rounded-xl"
```

---

### LEPES 2: C7.1 — Full Regression (15 perc)

```
Cel: MINDEN teszt zold, 0 failure.

2a) Lint + type check:
    python -m ruff check tests/e2e/
    cd aiflow-admin && npx tsc --noEmit

2b) Journey E2E collect-only (szintaxis ellenorzes):
    python -m pytest tests/e2e/test_journey_*.py --collect-only
    → elvaras: 53 + ~5 uj = ~58 journey teszt

2c) Full E2E collect:
    python -m pytest tests/e2e/ --collect-only
    → elvaras: ~169 teszt (164 + 5 uj cross-journey)

2d) Unit test regression (ha van ido):
    python -m pytest tests/unit/ -x -q --timeout=120
    → elvaras: 1443+ pass

2e) Ha valami FAIL:
    - Lint hiba → javitas
    - Selector hiba → TSX ellenorzes, fix
    - Timeout → wait strategia
    - SOHA ne torolj tesztet, SOHA ne skip-pelj!
```

---

### LEPES 3: C7.2 — Version Bump + Release Notes (10 perc)

```
Cel: v1.4.0 release keszites.

3a) CLAUDE.md frissites:
    - Version: v1.3.0 → v1.4.0
    - Branch info: feature/v1.4.0-ui-refinement → main (post-merge)
    - E2E szam frissites: 121 → ~169
    - Current Plan: Sprint C COMPLETE

3b) package.json version bump (ha letezik):
    aiflow-admin/package.json → "version": "1.4.0"

3c) pyproject.toml version bump (ha letezik):
    version = "1.4.0"

3d) Sprint C osszefoglalo release notes (rovidebb szoveg a commitbe):
    Sprint C (v1.4.0) — UI Journey-First Refinement:
    - J4 archivalas (ProcessDocs, SpecWriter, Media, Cubix, RPA eltavolitva)
    - Uj ConfirmDialog + i18n infrastruktura
    - J1 Invoice journey flow (Documents → Verification → Emails)
    - RunDetail oldal (step log, export JSON, retry)
    - Monitoring restart + auto-refresh
    - Quality rubric selector + evaluate form
    - Admin Users/API Keys CRUD + Create User modal
    - Audit filter dropdowns + CSV export
    - RAG chunk search + New Collection/Delete modals
    - Sidebar cleanup (archivalt oldalak eltavolitva)
    - 53 journey E2E teszt (23 deep, 30 nav + cross-journey)
    - 169+ total E2E tests
```

---

### LEPES 4: Commit + Tag (5 perc)

```
4a) git add tests/e2e/test_journey_navigation.py \
            CLAUDE.md \
            [+ version fajlok ha valtoztak]

4b) Commit message:
    feat: Sprint C S43 — C6.5 cross-journey E2E + C7 v1.4.0 release prep

4c) FONTOS: NE mergeld main-be es NE hozz letre git tag-et!
    A merge + tag a user dolga (code review utan).
    Csak keszitsd elo a branch-et a merge-hoz.

Gate: tsc 0 error, ruff 0 error, ~169 E2E collect-only, uj tesztek szintaktikailag hibatlanok
```

---

## KORNYEZET ELLENORZES

```bash
# Jelenlegi allapot
git branch --show-current     # → feature/v1.4.0-ui-refinement
git log --oneline -3           # → 134bf15 (S42 commit)

# Meglevo E2E tesztek
python -m pytest tests/e2e/ --collect-only 2>&1 | grep "tests collected"
# → 164 tests collected

# Journey tesztek reszletesen
python -m pytest tests/e2e/test_journey_*.py --collect-only 2>&1 | grep "tests collected"
# → 53 tests collected
```

---

## MEGLEVO KOD REFERENCIAK

```
# Bovitendo fajl:
tests/e2e/test_journey_navigation.py  — 5 teszt, TestJourneyNavigation class
  - test_dashboard_journey_cards(): journey card selector = "main >> div.cursor-pointer.rounded-xl"
  - navigate_to() hasznalattal (conftest.py import)

# Meglevo deep E2E mintak (S41-S42):
tests/e2e/test_journey_document.py    — TestDocumentDeepJourney (5 teszt)
tests/e2e/test_journey_pipeline.py    — TestPipelineDeepJourney (5 teszt)
tests/e2e/test_journey_quality.py     — TestQualityDeepJourney (4 teszt)
tests/e2e/test_journey_admin.py       — TestAdminDeepJourney (4 teszt)
tests/e2e/test_journey_rag.py         — TestRagDeepJourney (5 teszt)

# Fixtures:
tests/e2e/conftest.py                — authenticated_page, navigate_to(), BASE_URL

# UI oldalak:
aiflow-admin/src/pages-new/Dashboard.tsx  — Journey kartyak (cursor-pointer.rounded-xl)

# Version fajlok:
CLAUDE.md                              — fo projekt kontextus
aiflow-admin/package.json              — frontend version
pyproject.toml                         — backend version (ha van)
```

---

## TESZT PATTERN REFERENCIAK

```python
# Dashboard journey card kattintas (levo mintabol):
journey_cards = page.locator("main >> div.cursor-pointer.rounded-xl")
if journey_cards.count() >= 4:
    journey_cards.nth(0).click()  # J1: Documents
    journey_cards.nth(1).click()  # J3: RAG
    journey_cards.nth(2).click()  # J5: Pipelines
    journey_cards.nth(3).click()  # J2: Monitoring

# Console error tracking minta:
errors: list[str] = []
page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
# ... navigalas ...
real_errors = [e for e in errors if not any(x in e for x in [
    "favicon", "ResizeObserver", "Failed to fetch",
    "Failed to load resource", "Maximum update depth", "CORS policy"
])]
assert not real_errors
```

---

*Sprint C UTOLSO session: S43 = C6.5 (Cross-journey) + C7 (Regression + v1.4.0 release prep)*
