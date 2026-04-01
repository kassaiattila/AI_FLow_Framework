Record a completed development step and run the full validation sequence.

Arguments: $ARGUMENTS
(Optional: step title)

## ARANY SZABALY: VALOS TESZTELES KOTELEZO!
> **SOHA ne lepj tovabb sikertelen vagy mock/fake tesztekkel.**
> Minden teszt valos adatokkal, valos backend-del, valos bongeszioben tortenik.
> Egy feature CSAK AKKOR "KESZ" ha Playwright E2E teszten atment.

## PRE-IMPLEMENTATION CHECKS (before writing any code!):

1. **Read the relevant plan document** in `01_PLAN/`:
   - `42_SERVICE_GENERALIZATION_PLAN.md` - aktualis fazis es feladat
   - `IMPLEMENTATION_PLAN.md` - current phase and task list
   - `30_RAG_PRODUCTION_PLAN.md` - for RAG features
2. **Check reference materials** - `skills/*/reference/` if relevant
3. **Check existing code** - never reinvent what already works
4. **If DB change needed**: create Alembic migration FIRST
5. **If new service**: check `01_PLAN/42_SERVICE_GENERALIZATION_PLAN.md` Section 3-4
6. **If UI change — HARD GATE ELLENORZES (KIHAGYNI TILOS!):**
   ```bash
   # GATE A: Journey dokumentacio LETEZIK?
   grep -ri "Journey:" 01_PLAN/42_SERVICE_GENERALIZATION_PLAN.md | head -3
   # Ha NINCS a releváns journey → STOP → futtasd /ui-journey ELOSZOR!

   # GATE B: Figma design LETEZIK a PAGE_SPECS.md-ben?
   grep -i "{page_name}" aiflow-admin/figma-sync/PAGE_SPECS.md
   # Ha NINCS → STOP → futtasd /ui-design ELOSZOR!
   ```
   **TILOS UI kodot irni journey es Figma design NELKUL!**
   **Ha barmelyik gate FAIL → futtasd a megfelelo /ui-* parancsot ELOSZOR!**

## POST-IMPLEMENTATION VALIDATION:

### 1. Python Backend checks:
1. `git diff --name-only` — identify changes
2. `pytest tests/unit/ -q` — all pass
3. `alembic upgrade head` — if migration changed
4. **Valos API teszt:** `curl` hivással ellenorizd, hogy a backend endpoint valos adatot ad!
   - NEM "status 200 OK" eleg — nezd meg a valasz TARTALMAT
   - Ha JSON fallback-bol jon, az NEM elfogadhato — "source: backend" kell

### 2. UI checks (if aiflow-admin/ files changed):
5. `cd aiflow-admin && npx tsc --noEmit` — TypeScript hiba nelkul
6. **i18n check**: grep for hardcoded strings in changed files
7. **Data fetch check**: no `fetch("/data/...")` in page files — must use `/api/`

### 3. VALOS Playwright E2E Teszt (KOTELEZO minden UI valtozasnal!):
8. **Inditsd el a szervereket** (FastAPI + Vite) ha nem futnak
9. **MCP Playwright** — navigalj az erintett oldalra:
   - `browser_navigate` → oldal betolt?
   - `browser_snapshot` → megjelenik a vart tartalom?
   - `browser_click` → gombok, linkek mukodnek?
   - `browser_take_screenshot` → vizualis ellenorzes
   - `browser_console_messages` → nincs JS hiba?
10. **Teljes flow teszt** — NE CSAK az oldalletoltodest nezd:
    - Feltoltes → feldolgozas → eredmeny megjeleines → adatok helyesek?
    - Toggle-ok, szurok, rendezesek mukodnek?
    - Error esetek kezelve vannak?
11. **Ha a teszt SIKERTELEN**: ALLJ MEG, javitsd a hibat, futtasd ujra!
    - NE commitolj sikertelen teszttel
    - NE lepj tovabb a kovetkezo feladatra

### 4. Mock vs Real audit:
12. **Source tag check**: API routes return `source: "backend"|"demo"` field
13. **Demo label check**: pages show "Demo" badge when source is demo
14. **No silent mock**: NEVER fall back to mock data without visible indicator

### 5. Quality gate:
15. `git status` — no untracked files that should be tracked
16. Generate conventional commit message with test results

## TESZTELES SORRENDJE (mindig ezt koveted!):

```
1. Backend API teszt (curl)
   ↓ sikeres?
2. TypeScript build (tsc --noEmit)
   ↓ sikeres?
3. Playwright E2E (navigate → snapshot → click → screenshot)
   ↓ sikeres?
4. Konzol hiba ellenorzes (console_messages)
   ↓ nincs hiba?
5. COMMIT
```

Ha BARMELY lepes sikertelen → STOP → javitas → ujra elejeirol!

## CRITICAL RULES:

- **SOHA ne mockolt/fake adatokkal tesztelj** — valos backend, valos DB, valos PDF-ek
- **SOHA ne commitolj sikertelen teszttel** — meg "trivialis" valtozasnal sem
- **SOHA ne lepj tovabb hibas allapotban** — elobb javitsd, teszteld, AZTAN kovetkezo feladat
- NEVER create DB tables without Alembic
- NEVER hardcode user-visible strings without `t()` in UI code
- NEVER claim a feature is "KESZ" without Playwright E2E test
- NEVER fall back to mock data silently — always show "Demo" label
- ALWAYS use conventional commits (feat/fix/docs/refactor)
- ALWAYS tag version after each completed phase (git tag)

## Lesson from v0.9.0 development:
> Build deep, not wide. Finish ONE feature end-to-end (real backend, real tests, real UI)
> before starting the next. A half-working feature is worse than no feature.
> Fake progress bars are worse than no progress bar. ALWAYS show real data.
