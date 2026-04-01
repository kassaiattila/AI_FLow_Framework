Start a new vertical slice phase — DETERMINISTIC orchestration with HARD GATES.

Arguments: $ARGUMENTS
(Phase: F0, F1, F2, F3, F4, F4a, F4b, F4c, F4d, F5)

> **DETERMINISZTIKUS PIPELINE — 12 LEPES, MINDEN GATE-ELT.**
> Egy lepes CSAK AKKOR indithato ha az elozo lepes ARTEFAKTUMA letezik es ellenorizheto.
> Ha barmelyik GATE CHECK FAIL → **STOP** — javitas → ujra ellenorzes → AZTAN tovabb.
> **NINCS** "kesobb megcsinalom", **NINCS** "atugrom mert trivialis", **NINCS** kiveteles.

## A 12 LEPES ES GATE-EK:

```
STEP 1: Elofeltetel ellenorzes
  GATE: git tag letezik az elozo fazishoz? Szerverek futnak?
  ↓
STEP 2: Fazis terv beolvasas (42_SERVICE_GENERALIZATION_PLAN.md)
  GATE: A fazis definicio megtalalhato a tervben?
  ↓
STEP 3: Alembic migracio (ha kell)
  GATE: alembic upgrade head + downgrade -1 + upgrade head — HIBA NELKUL
  ↓
STEP 4: Service implementacio
  GATE: from aiflow.services.{name} import {Service} — HIBA NELKUL
  ↓
STEP 5: API endpoint implementacio
  GATE: curl MINDEN endpoint → 200 OK + source: "backend" + valos adat
  ↓
STEP 6: Unit teszt + regression
  GATE: pytest tests/unit/ -q → NINCS UJ FAILURE (letezo pre-existing ok)
  ↓
--- BACKEND COMMIT PONT (git commit) ---
  ↓
STEP 7: /ui-journey — User Journey dokumentacio
  GATE CHECK: grep "Journey:" 01_PLAN/42_SERVICE_GENERALIZATION_PLAN.md VAGY
              ls 01_PLAN/*journey* — DOKUMENTACIO FAJL LETEZIK
  *** HA NEM LETEZIK → STOP — ird meg a journey-t ELOSZOR! ***
  ↓
STEP 8: /ui-design — Figma MCP design
  GATE CHECK: grep "{FazisPageName}" aiflow-admin/figma-sync/PAGE_SPECS.md
  *** HA NEM LETEZIK → STOP — keszitsd el a Figma design-t ELOSZOR! ***
  ↓
STEP 9: /ui-page — UI implementacio (CSAK ha Gate 8 PASS!)
  GATE CHECK: cd aiflow-admin && npx tsc --noEmit — HIBA NELKUL
  ↓
STEP 10: Playwright E2E teszt
  GATE CHECK: browser_console_messages → 0 error
              i18n HU/EN toggle → MINDEN string valtozik
              Screenshot mentes
  ↓
STEP 11: Backward compat + regression
  GATE CHECK: python -m skills.{source_skill} import OK
              pytest tests/unit/ → same pass count as Step 6
  ↓
--- UI COMMIT PONT (git commit) ---
  ↓
STEP 12: Git tag + fazis lezaras
  GATE CHECK: 42_SERVICE_GENERALIZATION_PLAN.md Section 8 sikerkritieriumok MIND TELJESULNEK
```

## STEP 1: ELOFELTETEL ELLENORZES
```bash
# GATE: Elozo fazis KESZ?
git tag -l "v*"
# Ha az elozo fazis tagje HIANYZIK → STOP

# GATE: Szerverek futnak?
curl -s http://localhost:8100/health
# Ha NEM ready → STOP — inditsd el: docker compose up -d db redis && make api

# GATE: Frontend fut?
curl -s http://localhost:5174 | head -1
# Ha NEM → STOP — inditsd el: cd aiflow-admin && npx vite --port 5174
```

## STEP 2: FAZIS TERV BEOLVASAS
Olvasd el `01_PLAN/42_SERVICE_GENERALIZATION_PLAN.md` Section 5 — az aktualis fazis teljes leirasa.
Keszits TaskCreate-tel feladatlistat a fazis MINDEN lepesebol.

## STEP 3: ALEMBIC MIGRACIO
```bash
# Ird meg a migraciot: alembic/versions/NNN_add_{feature}.py
# GATE: mindharom HIBA NELKUL
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```
**Ha HIBA** → javitas → ujra mindharom → CSAK ha PASS → STEP 4

## STEP 4: SERVICE IMPLEMENTACIO
Implementald a service-t: `src/aiflow/services/{name}/`
```bash
# GATE: import HIBA NELKUL
python -c "from aiflow.services.{name} import {Service}; print('OK')"
```

## STEP 5: API ENDPOINT IMPLEMENTACIO
Implementald az API endpointokat: `src/aiflow/api/v1/{name}.py`
```bash
# GATE: MINDEN endpoint curl-lel tesztelve, valos adat, source: "backend"
curl -s http://localhost:8100/api/v1/{endpoint} | python -m json.tool
# Ellenorizd: source mező = "backend", NEM "demo"
```

## STEP 6: UNIT TESZT + REGRESSION
```bash
# GATE: nincs uj failure
pytest tests/unit/ -q --tb=no
# Jegyezd meg a pass/fail szamokat — Step 11-ben UGYANAZ kell legyen
```

## --- BACKEND COMMIT ---
```bash
git add {backend files} && git commit -m "feat({service}): F{X} backend — {description}"
```

## STEP 7: /ui-journey — USER JOURNEY (GATE-ELT!)
**MIELOTT BARMILYEN UI KODOT IRNAL:**
```bash
# GATE CHECK: journey dokumentacio letezik-e?
grep -r "Journey:" 01_PLAN/42_SERVICE_GENERALIZATION_PLAN.md | grep -i "{fazis_neve}"
```
Ha NEM letezik → Futtasd `/ui-journey "{fazis neve}"` MOST.
A journey dokumentacio KELL tartalmazzon:
- Ki a felhasznalo (role)
- Mi a celja (goal)
- Milyen lepesekbol all (steps)
- Milyen API endpointok kellenek (endpoints)
- Milyen oldalak/komponensek kellenek (pages)

**NEM LEPHETSZ STEP 8-ra journey dokumentacio NELKUL!**

## STEP 8: /ui-design — FIGMA DESIGN (GATE-ELT!)
**MIELOTT BARMILYEN UI KODOT IRNAL:**
```bash
# GATE CHECK: PAGE_SPECS.md-ben letezik-e az uj oldal specifikacioja?
grep -i "{page_name}" aiflow-admin/figma-sync/PAGE_SPECS.md
```
Ha NEM letezik → Futtasd `/ui-design "{page name}"` MOST.
A design KELL tartalmazzon:
- Layout leiras (PAGE_SPECS.md)
- Data source (API endpoint)
- Sections + interactions
- Loading / Error / Empty states
- i18n keys

**NEM LEPHETSZ STEP 9-re Figma design NELKUL!**

## STEP 9: /ui-page — UI IMPLEMENTACIO (CSAK ha Gate 8 PASS!)
```bash
# DOUBLE CHECK: PAGE_SPECS.md letezik az oldalhoz
grep -c "{PageName}" aiflow-admin/figma-sync/PAGE_SPECS.md
# Ha 0 → STOP — menj vissza Step 8-ra!

# Implementacio UTAN:
cd aiflow-admin && npx tsc --noEmit
# GATE: TypeScript HIBA NELKUL
```

## STEP 10: PLAYWRIGHT E2E
Playwright MCP-vel valos bongeszioben:
1. `browser_navigate` → oldal betolt
2. `browser_snapshot` → tartalom megjelenik
3. `browser_click` → interakciok mukodnek
4. `browser_take_screenshot` → vizualis dokumentacio
5. `browser_console_messages` → **0 error** (GATE!)
6. i18n toggle (HU/EN) → **MINDEN string valtozik** (GATE!)

## STEP 11: BACKWARD COMPAT + REGRESSION
```bash
# GATE: regi skill importok mukodnek
python -c "from skills.{source_skill}.workflows.* import *; print('OK')"

# GATE: unit test count UGYANAZ mint Step 6-ban
pytest tests/unit/ -q --tb=no
```

## --- UI COMMIT ---
```bash
git add {ui files} && git commit -m "feat({service}): F{X} UI — {description}"
```

## STEP 12: GIT TAG + FAZIS LEZARAS
```bash
# GATE: Section 8 sikerkritieriumok MIND teljesulnek
# Olvasd el 42_SERVICE_GENERALIZATION_PLAN.md Section 8 — check MINDEN pont

git tag -a v{version} -m "F{X}: {description} — full vertical slice"
```

## FAZIS DEFINICIOK:
| Fazis | Szolgaltatas | Forras Skill | Tag |
|-------|-------------|-------------|-----|
| F0 | Infra (cache, config, rate limit, auth) | — | v0.9.1-infra |
| F1 | Document Extractor | invoice_processor | v0.10.0-document-extractor |
| F2 | Email Connector + Classifier | email_intent_processor | v0.10.1-email-connector |
| F3 | RAG Engine | aszf_rag_chat | v0.11.0-rag-engine |
| F4a | Diagram Generator | process_documentation | v0.12.0-complete-services |
| F4b | Media Processor | cubix_course_capture (STT) | v0.12.0-complete-services |
| F4c | RPA Browser | cubix_course_capture (RPA) | v0.12.0-complete-services |
| F4d | Human Review + Cubix compose | — | v0.12.0-complete-services |
| F5 | Monitoring + Governance + Admin | — | v1.0.0-rc1 |

## CRITICAL: AMIERT EZ LETEZIK
> F1 es F2 fazisokban a Journey (Step 7) es Figma Design (Step 8) KIHAGYASRA KERULT.
> Az UI ad-hoc modon keszult, nem a tervezett pipeline szerint.
> Ez a szigoritott command biztositja, hogy F3-tol SOHA NE fordulhasson elo ujra.
> **Ha barmelyik gate-et ki akarod hagyni, eloszor kerdezd meg a felhasznalot es kapj EXPLICIT jovahagyast.**
