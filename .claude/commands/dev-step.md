Record a completed development step and run the full validation sequence.

Arguments: $ARGUMENTS
(Optional: step title)

## ARANY SZABALY: VALOS TESZTELES KOTELEZO!
> **SOHA ne lepj tovabb sikertelen vagy mock/fake tesztekkel.**
> Minden teszt valos adatokkal, valos backend-del, valos bongeszioben tortenik.
> Egy feature CSAK AKKOR "KESZ" ha Playwright E2E teszten atment.

## BRANCH ELLENORZES (KOTELEZO!)
```bash
git branch --show-current  # NEM main-en kell lenni! Feature branch-en dolgozunk.
# Ha main → STOP! Hozd letre vagy valtsd at a megfelelo branch-re:
#   feature/v1.2.1-production-ready              (S1-S14, v1.2.1 sprint)
#
# REGI (v1.2.0 — LEZARVA, NE HASZNALD):
#   feature/v1.2.0-tier1-pipeline-orchestrator   (C0-C5, DONE)
#   feature/v1.2.0-tier2-supporting-services     (C7-C10, DONE)
#   feature/v1.2.0-tier3-advanced-rag            (C11-C16, DONE)
#   feature/v1.2.0-tier4-polish                  (C17-C20, DONE)
```
**TILOS fejlesztest kozvetlenul main-re commitolni!**

## L0 SMOKE TEST (KOTELEZO — futasd ELOSZOR!)
```bash
bash scripts/smoke_test.sh  # <30s — meglevo rendszer OK?
```
Ha FAIL → NEM kezdunk fejleszteni, eloszor a meglevo rendszert javitjuk!

## PRE-IMPLEMENTATION CHECKS (before writing any code!):

1. **Read the relevant plan document** in `01_PLAN/`:
   - `57_PRODUCTION_READY_SPRINT.md` - **AKTUALIS**: v1.2.1 Production Ready (S1-S14)
   - `48_ORCHESTRABLE_SERVICE_ARCHITECTURE.md` - v1.2.0 architektura (referencia)
   - `49-54` - Reszletes tervek (stability, RAG, doc, HITL, frontend, LLM quality)
   - `56_EXECUTION_PLAN.md` - v1.2.0 ciklusok (C0-C20, MIND DONE)
2. **Check reference materials** - `skills/*/reference/` if relevant
3. **Check existing code** - never reinvent what already works
4. **If DB change needed**: create Alembic migration FIRST (nullable=True vagy server_default!)
5. **If new service**: adapter reteg WRAPPER, NEM modositja az eredeti service-t
6. **If pipeline change**: MINDEN step adapter registry-ben LETEZIK, retry KOTELEZO kulso hivasokra
6. **If UI change — HARD GATE ELLENORZES (KIHAGYNI TILOS! FIZIKAI FAJL CHECK!):**
   ```bash
   # GATE A: Journey fajl FIZIKAILAG LETEZIK? (ls, NEM grep!)
   ls 01_PLAN/F*_*JOURNEY*.md 2>/dev/null || echo "GATE FAIL: Nincs journey fajl!"
   # Ha NINCS FAJL → **STOP** → hozd letre /ui-journey -vel ELOSZOR!
   # NEM ELEG grep-pelni a 42_SERVICE_GENERALIZATION_PLAN.md-t — ONALLO FAJL KELL!

   # GATE B: PAGE_SPECS.md-ben VAN-E az oldal szekcioja FIGMA REFERENCIA-VAL?
   grep -c "## Page.*{PageName}" aiflow-admin/figma-sync/PAGE_SPECS.md || echo "GATE FAIL: Nincs PAGE_SPECS entry!"
   # Ha NINCS → **STOP** → futtasd /ui-design ELOSZOR (valos Figma MCP design!)
   # Manuálisan írt PAGE_SPECS entry Figma nélkül NEM ELFOGADHATÓ!
   ```
   **TILOS UI kodot irni journey fajl es Figma design NELKUL!**
   **Ha barmelyik gate FAIL → STOP → megoldas → AZTAN tovabb!**
   **NEM kerhetsz engedelyt a gate kihagyasara — NINCS kiveteles.**
   > **GATE VIOLATION TORTENELEM:** F1 + F2 fazisban ezen gate-ek KIHAGYASRA kerultek.
   > Emiatt lett bevezetve a fizikai fajl ellenorzes (`ls`) a grep helyett.

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
7. **Data fetch check**: no `fetch("/data/...")` in page files — must use `fetchApi()` or `/api/`
   - **Stack check**: no `@mui/material` imports — must use Untitled UI + Tailwind
   - **No MUI icons**: no `@mui/icons-material` — must use `@untitledui/icons`

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

### 4. L0 Smoke Test UJRA (regresszio ellenorzes):
12. `./scripts/smoke_test.sh` — meglevo rendszer NEM romlott?
13. `ruff check src/ skills/` — lint CLEAN?
    Ha BARMELYIK FAIL → javitas ELOTT nem commitolunk!
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

### 6. MANDATORY Plan Updates (SOHA NE HAGYD KI!):
> **Session 9 tanulsag:** C7-C16 utan a tervek NEM kerultek frissitesre. Ez TILOS.
17. **`01_PLAN/56_EXECUTION_PLAN.md`** — Progress tabla frissites:
    - Ciklus allapot: TODO → DONE
    - Datum: mai datum
    - Commit: commit hash
    - Output szekció: mit deliveralt a ciklus (fajlok, tesztek, E2E)
18. **`01_PLAN/CLAUDE.md`** — Key numbers frissites (service, adapter, endpoint, migracio, teszt szamok)
19. **Root `CLAUDE.md`** — Infrastruktura szamok frissites

### 7. Dependency Safety Check (ha .venv epult ujra):
> **Session 9 tanulsag:** `.venv` ujraepites torolte `pypdfium2` + `docling` → UI regresszio.
20. `python -c "import pypdfium2; import docling; import aiosmtplib; print('deps OK')"`
21. Ha BARMELYIK hianyzik → telepitsd MIELOTT tovabbmesz!

## Lesson from v0.9.0 development:
> Build deep, not wide. Finish ONE feature end-to-end (real backend, real tests, real UI)
> before starting the next. A half-working feature is worse than no feature.
> Fake progress bars are worse than no progress bar. ALWAYS show real data.

## Lesson from session 9 (C7-C16):
> **TERV FRISSITES KOTELEZO minden ciklus vegen.** A 56_EXECUTION_PLAN.md progress tabla,
> output szekciok, es a CLAUDE.md szamok NEM frissultek C7-C16 kozben. Ez nem fordulhat elo.
> **DEPENDENCY SAFETY:** Ha `.venv`-t ujraepited, ELLENORIZD MINDEN dependency letezeeset
> mielott "DONE"-nak jelolsz egy ciklust. Hianyzó dep = UI regresszio.
