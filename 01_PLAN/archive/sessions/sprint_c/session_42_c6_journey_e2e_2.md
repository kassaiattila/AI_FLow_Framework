# AIFlow Sprint C — Session 42 Prompt (C6.3-C6.4: Journey E2E Validation — J2a/J2b + J3)

> **Datum:** 2026-04-10
> **Branch:** `feature/v1.4.0-ui-refinement` | **HEAD:** `528b7d3`
> **Port:** API 8102 (dev), Frontend 5174 (dev)
> **Elozo session:** S41 — C6.1-C6.2 DONE (Document + Pipeline deep E2E, 10 uj teszt)
> **Terv:** `01_PLAN/65_SPRINT_C_UI_JOURNEY_FIRST_PLAN.md` (C6 szekcio)
> **Session tipus:** E2E TEST — Journey 2a/2b (Quality+Admin) + Journey 3 (RAG) deep validation
> **Workflow:** Meglevo E2E bovites → uj deep tesztek → futtas → fix → Commit

---

## KONTEXTUS

### S41 Eredmenyek (C6.1-C6.2 — KESZ)

```
✅ C6.1: 5 deep Document E2E (table data, detail nav, verification, search, delete dialog)
✅ C6.2: 5 deep Pipeline E2E (status badges, step log, retry dialog, YAML tab, pipeline badge)
✅ 20 E2E teszt ebbol 10 uj deep | tsc 0 | ruff 0
```

### Meglevo E2E Journey Tesztek (42 db, 20 + 15 + 7 nav)

```
test_journey_document.py   — 10 teszt (5 nav + 5 deep) ← S41
test_journey_pipeline.py   — 10 teszt (5 nav + 5 deep) ← S41
test_journey_admin.py      — 5 teszt: KPI + nav + notification + admin→audit + loop (NAV-ONLY)
test_journey_rag.py        — 5 teszt: page load + nav + services + crossnav + 0 error (NAV-ONLY)
test_journey_quality.py    — 5 teszt: KPIs + ext links + costs + monitoring + loop (NAV-ONLY)
test_journey_navigation.py — 7 teszt: sidebar groups + breadcrumb + cards + J1/J2 flow

PROBLEMA: admin/quality/rag tesztek meg mindig NAVIGACIOS jelleguek.
CEL: Melysegi E2E tesztek amik valodi funkcionalitast tesztelnek.
```

---

## S42 FELADATOK: 4 lepes

### LEPES 1: C6.3 — J2a/J2b Quality + Admin + Audit Deep E2E (20 perc)

```
Cel: Boviteni test_journey_quality.py-t ES test_journey_admin.py-t VALODI interakciokkal.

=== test_journey_quality.py — UJ TestQualityDeepJourney class ===

A) test_quality_rubric_selector():
  - /quality betoltes (2s wait a spinner miatt)
  - Rubric dropdown letezik (select elem)
  - Ha lathato: kivalaszt egy rubricot → oldal frissul, nem crashel
  - KPI card ertekek lathatok (score, pass rate)

B) test_monitoring_service_cards_and_refresh():
  - /monitoring betoltes
  - Service card grid megjelenik (legalabb 1 kartya)
  - Kartyan: status ikon + latency + uptime adat
  - Auto-refresh dropdown letezik (Off/10s/30s/60s)
  - Refresh gomb letezik es kattinthato

C) test_monitoring_restart_confirm_dialog():
  - /monitoring betoltes
  - "Restart" gomb letezik valamelyik service kartyan
  - Kattintas → ConfirmDialog megjelenik ("Restart Service")
  - Cancel → dialog bezarol

D) test_costs_kpi_and_breakdown_tables():
  - /costs betoltes
  - KPI kartyak megjelennek (Total Cost, Total Runs, Tokens, API Calls)
  - Legalabb 1 DataTable lathato (By Skill VAGY By Model)
  - Tabla fejlec tartalmaz relevan oszlopokat (cost, model, tokens)

=== test_journey_admin.py — UJ TestAdminDeepJourney class ===

E) test_admin_users_tab_content():
  - /admin betoltes
  - Users tab aktiv (vagy kattintas ra)
  - DataTable letezik: email, name, role badge, status badge oszlopok
  - "Create User" gomb lathato

F) test_admin_api_keys_tab():
  - /admin betoltes → API Keys tab kattintas
  - DataTable letezik: name, prefix (mono), status badge
  - "Generate Key" gomb lathato

G) test_admin_create_user_modal():
  - /admin betoltes → "Create User" gomb kattintas
  - Modal megjelenik: email, name, password input + role dropdown
  - Cancel → modal bezarol

H) test_audit_filter_and_export():
  - /audit betoltes
  - Filter dropdown-ok lathatok (action, entity type)
  - CSV Export gomb letezik
  - Action filter kivalasztas → tabla frissul
  - DataTable fejlec: timestamp, action, resource oszlopok
```

---

### LEPES 2: C6.4 — J3 RAG Journey Deep E2E (20 perc)

```
Cel: Boviteni test_journey_rag.py-t VALODI interakciokkal.

Fajl: tests/e2e/test_journey_rag.py

UJ TestRagDeepJourney class:

A) test_rag_collections_table_or_empty():
  - /rag betoltes
  - Collections tab aktiv
  - Ha van adat: DataTable sorok lathatok (name, doc count, chunk count)
  - Ha nincs: empty state megjelenik
  - Source tag (Demo/Live) lathato

B) test_rag_create_collection_modal():
  - /rag betoltes → "New Collection" gomb kattintas
  - Modal megjelenik: name input, description textarea, language dropdown
  - Cancel → modal bezarol, nem crashel

C) test_rag_collection_delete_dialog():
  - /rag betoltes
  - Ha van tabla sor: delete gomb (trash ikon) kattintas
  - ConfirmDialog megjelenik
  - Cancel → dialog bezarol

D) test_rag_chat_tab():
  - /rag betoltes → Chat tab kattintas
  - Chat interface megjelenik (input mezo + send gomb)
  - Beleir egy kerdest (nem kuldve) → input mezo tartalma megvaltozik
  - Oldal nem crashel

E) test_rag_chunk_search():
  - /rag betoltes → Chunks tab (ha letezik) VAGY /rag/chunks navigalas
  - Search mezo letezik
  - Beleir egy keresoszot → debounce utan tabla frissul
  - Oldal nem crashel
```

---

### LEPES 3: Fix + Kiegeszites (10 perc)

```
Cel: Teszteket futtatni es a talalt UI hibakat javitani.

3a) Szintaxis ellenorzes:
    python -m py_compile tests/e2e/test_journey_quality.py
    python -m py_compile tests/e2e/test_journey_admin.py
    python -m py_compile tests/e2e/test_journey_rag.py

3b) Lint:
    python -m ruff check tests/e2e/test_journey_quality.py tests/e2e/test_journey_admin.py tests/e2e/test_journey_rag.py

3c) Test collection:
    python -m pytest tests/e2e/test_journey_quality.py tests/e2e/test_journey_admin.py tests/e2e/test_journey_rag.py --collect-only
    → elvaras: 15 regi + ~13 uj = ~28 teszt

3d) tsc ellenorzes:
    cd aiflow-admin && npx tsc --noEmit → 0 error

3e) Ha valami fail:
    - Missing selector → ellenorizni a TSX-ben a pontos osztaly/szoveg
    - Timeout → wait strategia modositas
    - Lint hiba → javitas
```

---

### LEPES 4: Commit (5 perc)

```
4a) git add tests/e2e/test_journey_quality.py \
            tests/e2e/test_journey_admin.py \
            tests/e2e/test_journey_rag.py \
            [+ barmelyik UI fajl amit javitottunk]

4b) Commit message:
    test(e2e): Sprint C S42 — C6.3-C6.4 deep E2E for J2a/J2b Quality+Admin + J3 RAG journeys

Gate: tsc 0 error, ruff 0 error, uj tesztek szintaktikailag helyesek, meglevo tesztek nem tortek el
```

---

## KORNYEZET ELLENORZES

```bash
# Jelenlegi allapot
git branch --show-current     # → feature/v1.4.0-ui-refinement
git log --oneline -3           # → 528b7d3 (S41 commit)

# Meglevo E2E tesztek (BOVITENDO)
ls tests/e2e/test_journey_*.py

# Meglevo teszt szam ellenorzes
python -m pytest tests/e2e/ --collect-only 2>&1 | grep "tests collected"
```

---

## MEGLEVO KOD REFERENCIAK

```
# Meglevo E2E tesztek (BOVITENDO):
tests/e2e/test_journey_quality.py   — 5 teszt (nav-only, boviteni deep-pel)
tests/e2e/test_journey_admin.py     — 5 teszt (nav-only, boviteni CRUD-dal)
tests/e2e/test_journey_rag.py       — 5 teszt (nav-only, boviteni chat+collection-nel)
tests/e2e/conftest.py               — Playwright fixtures, base URL, login

# UI oldalak amiket tesztelunk:
aiflow-admin/src/pages-new/Quality.tsx      — J2a: rubric selector, KPI cards, evaluate
aiflow-admin/src/pages-new/Monitoring.tsx   — J2a: service cards, restart, auto-refresh
aiflow-admin/src/pages-new/Costs.tsx        — J2a: KPI cards, By Skill + By Model tables
aiflow-admin/src/pages-new/Admin.tsx        — J2b: Users tab, API Keys tab, Create User modal
aiflow-admin/src/pages-new/AuditLog.tsx     — J2b: filter dropdown, CSV export, DataTable
aiflow-admin/src/pages-new/Rag.tsx          — J3: Collections tab, Chat tab, New Collection modal

# S41 deep teszt mintak (KOVESD EZT A STILUST):
tests/e2e/test_journey_document.py   — TestDocumentDeepJourney class minta
tests/e2e/test_journey_pipeline.py   — TestPipelineDeepJourney class minta

# Teszt patternek:
  - Uj class nev: TestXxxDeepJourney (kulon a nav-only tesztektol)
  - Ha nincs adat: graceful return (nem fail)
  - Dialog teszt: click → assert dialog text → Cancel → assert dialog gone
  - Search teszt: fill → wait 400ms → assert filtered → clear → assert restored
  - Source tag: Demo/Live text check a body-ban
```

---

## SPRINT C UTEMTERV

```
S37: C0+C1 — J4 archive + infra + J1 Invoice flow       ✅ DONE
S38: C2.1-C2.3 — RunDetail + Monitoring                  ✅ DONE
S39: C2.4-C2.6 — Quality + Admin CRUD + Audit            ✅ DONE
S40: C4+C5 — RAG chunk search + Sidebar cleanup           ✅ DONE
S41: C6.1-C6.2 — J1 + J5 deep E2E                         ✅ DONE
S42: C6.3-C6.4 — J2a/J2b + J3 deep E2E                    ← EZ A SESSION
S43: C6.5 + C7 — Cross-journey + Regresszio + v1.4.0 tag
```

---

*Sprint C hatodik session: S42 = C6.3 + C6.4 (Quality+Admin+Audit + RAG journey deep E2E)*
