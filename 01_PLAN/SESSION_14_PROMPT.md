# AIFlow v1.2.1 — Session 14 Prompt (S13 E2E Journeys + S14 Final Polish)

> **Datum:** 2026-04-04 (session 13 utan)
> **Elozo session:** S10+S11+S12 DONE (session 13)
> **Branch:** feature/v1.2.1-production-ready (31 commit, main-bol branched)
> **Port:** API 8102, Frontend 5174 (Vite proxy → 8102)
> **Utolso commit:** `cb7340b` docs: S12 commit hash updated
> **PR:** https://github.com/kassaiattila/AI_FLow_Framework/pull/1

---

## AKTUALIS TERV

**`01_PLAN/57_PRODUCTION_READY_SPRINT.md`** — 14 ciklus (S1-S14), ~7-9 session.

---

## ALLAPOT

### Tier A: UI Integration & Unified Experience — COMPLETE (session 10)

| Ciklus | Commit    | Tartalom                                                                 |
| ------ | --------- | ------------------------------------------------------------------------ |
| S1     | `1dff737` | Chat UI: ChatMarkdown bekotes, @tanstack/react-virtual, Cmd+Enter/Escape |
| S2     | `65fc403` | In-app notifications: 4 API endpoint + NotificationBell + dropdown       |
| S3     | `788c1e5` | Quality Dashboard: 7 HARD GATE, 5 KPI card, rubrics tabla, evaluate form |
| S4     | `238ee7f` | Service Catalog: 16 service card, search+filter, pipeline integration    |
| S5     | `47992bc` | Design tokens @theme, ErrorBoundary, aria-label accessibility            |
| S6     | `b38b156` | CubixViewer MUI→Tailwind, 0 @mui import, LegacyPage wrapper torolve     |

### Tier B: Quality & Observability — COMPLETE (session 11-12)

| Ciklus | Commit    | Tartalom                                                              |
| ------ | --------- | --------------------------------------------------------------------- |
| S7     | `6e46fed` | Langfuse valos integracio (tracing, cost, health) + prompt sync bonus |
| S8     | `dfbb8e4` | Promptfoo 6 skill config (51 test case) + nightly-eval.yml CI/CD      |
| S9     | `65dfcdf` | E2E Playwright test suite: 54 teszt, 17 oldal, Page Object Model      |
| S8+    | `8d112fd` | Quality dashboard: Promptfoo + Langfuse external tool linkek          |

### Tier B+C: CI/CD + Features — COMPLETE (session 13)

| Ciklus | Commit    | Tartalom                                                              |
| ------ | --------- | --------------------------------------------------------------------- |
| S10    | `b707fe7` | CI/CD: ci.yml Vite build, nightly-regression.yml, smoke_test.sh 10/10 |
| S11    | `b707fe7` | Free text extraction + intent schema CRUD (7 endpoint + adapter)      |
| S12    | `6318ee0` | SLA escalation (3 endpoint) + pipeline cost estimation                |
| lint   | `c624e4d` | ruff check + format fixes for S10+S11 files                          |

### Session 13 reszletes deliverables:

**S10 — CI/CD Regresszios Pipeline:**
- `.github/workflows/ci.yml` frissitve: nextjs-build TOROLVE, admin-build (Vite) HOZZAADVA, coverage gate >=80%
- `.github/workflows/nightly-regression.yml` (UJ): L3 regression 03:00 UTC — unit → integration → E2E → admin build + summary
- `scripts/smoke_test.sh` bovitve: 10 endpoint (quality, notifications, templates, intent-schemas), 10/10 PASS
- `tests/regression_matrix.yaml`: pipeline/, aiflow-admin/, .github/ patterns

**S11 — Free Text + Intent Schema CRUD:**
- `src/aiflow/services/document_extractor/free_text.py` (UJ): FreeTextExtractorService — LLM query extraction
- `prompts/extraction/free_text.yaml`: Jinja2 template, gpt-4o-mini
- `POST /api/v1/documents/{id}/extract-free`: query → answer + confidence + source_span
- `src/aiflow/api/v1/intent_schemas.py` (UJ router): GET/POST/PUT/DELETE + POST /test — 7 endpoint
- `src/aiflow/pipeline/adapters/free_text_adapter.py` (UJ): 19. adapter
- 25 unit test PASS, ruff clean

**S12 — SLA Escalation + Cost Estimation:**
- `human_review/service.py`: escalate(), check_sla_deadlines(), check_and_escalate(), notification
- `human_review.py`: 3 uj endpoint (POST /escalate, GET /sla/overdue, POST /sla/check-and-escalate)
- `pipelines.py`: POST /{id}/estimate-cost — per-step token+cost, budget alert (WARNING/BLOCKED)
- `execution/sla_checker.py` (UJ): standalone SLA check job + cron registration
- 12 unit test PASS, ruff clean

**Fontos tanulsagok Session 13-bol:**
1. **asyncpg pool.acquire() mock** — `MagicMock` + `@asynccontextmanager` szukseges, NEM `AsyncMock` with `__aenter__`
2. **Pre-existing ruff errors** — 755+ hiba a teljes codebase-ben (NEM S10-S12 regresszio), CI/CD fix P5-re halasztva
3. **CI workflow triggerek** — `ci.yml` csak `push to main` vagy `PR to main` trigger, feature branch push nem inditja
4. **GitHub Actions CI FAIL** — Mind a 4 workflow pre-existing hibakkal fail (ruff PATH, codebase lint, skill deps)
5. **`/api/v1/health` nem letezik** — health csak root `/health` path-on elerheto
6. **intent_schemas tabla** — CREATE TABLE IF NOT EXISTS pattern, nincs Alembic migracio (runtime auto-create)

### Infrastruktura (frissitett szamok)

- **26 service**, 19 pipeline adapter, 6 pipeline template
- **~169 API endpoint** (149 unique route), **25 router**
- **45 DB tabla** (+1 intent_schemas runtime), 29 Alembic migracio
- **332 pipeline unit test** + **37 uj unit test (S11+S12)** + **74 observability teszt** + **45 prompt teszt**
- **51 Promptfoo test case** (6 skill), **54 E2E Playwright teszt** (17 oldal)
- **Docker:** PostgreSQL 5433, Redis 6379
- **Auth:** admin@bestix.hu / admin (username mezo!)
- **Langfuse:** ENABLED, connected, 9 prompt szinkronizalva
- **PR:** https://github.com/kassaiattila/AI_FLow_Framework/pull/1 (CI FAIL — pre-existing, P5)

### Meglevo CI/CD fajlok (`.github/workflows/`):

| Fajl                       | Trigger                  | Allapot                                                  |
| -------------------------- | ------------------------ | -------------------------------------------------------- |
| `ci.yml`                   | push/PR to main          | FRISSITETT S10: Vite build, coverage gate                |
| `ci-framework.yml`         | PR (src/aiflow/**)       | Pre-existing ruff fails (755 error)                      |
| `ci-skill.yml`             | PR (skills/**)           | Skill collection error (5 test files)                    |
| `nightly-eval.yml`         | cron 02:00 UTC           | Promptfoo eval 6 skill (S8)                              |
| `nightly-regression.yml`   | cron 03:00 UTC           | UJ S10: L3 unit+integration+E2E+admin build              |
| `prompt-eval.yml`          | PR (skills/*/prompts/**) | Promptfoo on PR                                          |
| `deploy-prod.yml`          | ?                        | Production deploy                                        |
| `deploy-staging.yml`       | ?                        | Staging deploy                                           |

### Meglevo E2E tesztek (`tests/e2e/`):

| Fajl                  | Tesztek | Mit tesztel                                           |
| --------------------- | ------- | ----------------------------------------------------- |
| `test_smoke.py`       | 40      | Login (4), SmokeAllPages (34=17×2), Sidebar (2)       |
| `test_quality.py`     | 4       | Page loads, content/error, external tools, links       |
| `test_documents.py`   | 3       | Table, action area, source indicator                   |
| `test_pipelines.py`   | 3       | Pipelines loads, services catalog, list/empty          |
| `test_notifications.py`| 2      | Bell icon, dropdown toggle                             |
| `test_i18n.py`        | 2       | Magyar/English locale toggle                           |
| **Ossz.**             | **54**  | 17 oldal, Page Object Model, 0 console error           |

### Post-Sprint TODO (57_PRODUCTION_READY_SPRINT.md Section 8)

| # | Tartalom | Prioritas |
|---|----------|-----------|
| P1 | Pipelines oldal templates szekció (UI nem hívja /templates/list-et) | HIGH |
| P2 | Templates endpoint route conflict (/{pipeline_id} matchel /templates-re) | MEDIUM |
| ~~P3~~ | ~~Langfuse Prompt Management~~ | DONE (S7) |
| P4 | Placeholder/Stub Audit — teljes codebase stub felmerés | HIGH |
| P5 | CI/CD GitHub Actions fix — ruff 755 error cleanup, skill deps, PATH | HIGH |

---

## KOVETKEZO FELADATOK: S13 (Integralt E2E) + S14 (Final Polish)

### S13: Integralt E2E Teszteles (multi-page user journey-k)

**Cel:** NEM oldalankenti teszt (az mar S9-ben megvan), hanem TELJES FELHASZNALOI UTAK tesztelese tobb oldalon at, valos backend-del.

### Lepesek

```
1. TERVEZES:
   - Olvasd el 57_PRODUCTION_READY_SPRINT.md S13 szekciojat (sor ~592)
   - Olvasd el a meglevo tests/e2e/ fajlokat (conftest.py, pages/, test_smoke.py)
   - Allapitsd meg, mely journey-k futtathatoak valos backend-del

2. FEJLESZTES — 5 journey teszt:
   a) tests/e2e/test_journey_document.py:
      - Login → Documents → check table → navigate detail → verify source=backend
      - Ha van adat: upload → process-stream → check result
   b) tests/e2e/test_journey_rag.py:
      - Login → RAG → collections list → select collection → chat query
      - Service Catalog → find RAG service → details
   c) tests/e2e/test_journey_quality.py:
      - Login → Quality dashboard → KPI cards loaded → rubrics tabla
      - External tool linkek (Promptfoo, Langfuse) → target="_blank"
   d) tests/e2e/test_journey_admin.py:
      - Login → Dashboard → services count → navigate to Services
      - Notifications bell → dropdown → navigate → Pipeline list
   e) tests/e2e/test_journey_pipeline.py:
      - Login → Pipelines → list → services catalog
      - (Ha van pipeline) → detail → estimate cost → run status

3. TESZTELES:
   - Szerver inditas: API 8102 + Frontend 5174
   - pytest tests/e2e/test_journey_*.py -v → PASS
   - pytest tests/e2e/ -v → 54 + uj journey = ALL PASS (regresszio!)
   - 0 console error

4. DOKUMENTALAS:
   - git commit
   - 57_PRODUCTION_READY_SPRINT.md: S13 = DONE
```

### S14: Vegleges Polish + v1.2.1 Tag

**Cel:** Accessibility audit, dokumentacio frissites, teljes regresszio, version tag.

### Lepesek

```
1. ACCESSIBILITY:
   - Playwright: keyboard navigation teszt (Tab + Enter minden fooldal)
   - aria-label check: minden interaktiv elem
   - Kontraszt: dark mode szinek WCAG AA
   
2. DOKUMENTACIO:
   - CLAUDE.md: vegleges infra szamok (router, endpoint, adapter, test)
   - 01_PLAN/CLAUDE.md: same
   - 57_PRODUCTION_READY_SPRINT.md: progress tabla + output szekciok

3. REGRESSZIO:
   - pytest tests/unit/ -q → ALL PASS
   - pytest tests/e2e/ -v → ALL PASS (54 + journey tesztek)
   - cd aiflow-admin && npx tsc --noEmit → 0 error
   - ruff check (sajat fajlok) → PASS
   - smoke_test.sh → ALL PASS

4. VERSION:
   - pyproject.toml: version = "1.2.1"
   - git tag v1.2.1
   - git push --tags
   - 57_PRODUCTION_READY_SPRINT.md: S14 = DONE, vegleges szamok

5. (OPTIONAL) PWA teszteles:
   - Ha van Service Worker → offline cache check
   - Ha nincs → skip, post-sprint TODO
```

---

## TIER D VEGREHAJTASI TERV (S13-S14)

```
S1-S12: Tier A+B+C ───── MIND DONE ✓ (session 10-13)
S13: Integralt E2E ────── KOVETKEZO ← ITT VAGYUNK
S14: Final polish + tag ─ UTOLSO CIKLUS
```

---

## KOTELEZOEN BETARTANDO SZABALYOK

### Session 13 tanulsagai:

1. **asyncpg pool.acquire() mock** — `MagicMock` + `@asynccontextmanager` wrapper kell, NEM `AsyncMock.__aenter__`
2. **Pre-existing ruff 755 error** — A teljes codebase-ben, NEM a mi koddal. CI/CD fix post-sprint P5.
3. **CI trigger** — `ci.yml` csak `push to main` vagy `PR to main` — feature branch push NEM inditja
4. **GitHub Actions CI** — Mind FAIL (pre-existing). Lokalisan S10-S12 fajlok ruff-clean + 37 teszt PASS.
5. **intent_schemas tabla** — Runtime `CREATE TABLE IF NOT EXISTS`, nincs Alembic migracio (tudatos dontes)
6. **Smoke test** — 10/10 endpoint PASS, `/api/v1/health` NEM letezik (csak root `/health`)

### Elozo session tanulsagai (S8-S12):

7. **Promptfoo JS assertions** — `const` NEM hasznalhato! Csak single expression
8. **Invoice prompt currency** — Explicit ISO 4217 kodokat kell kerni
9. **Playwright login wait** — `page.locator("nav").wait_for(state="visible")` a legmegbizhatobb
10. **Locale buttons** — "Magyar" es "English" (NEM "HU"/"EN")
11. **Langfuse v4 API** — `client.start_observation()`, `client.create_score()`, trace ID: `uuid4().hex`
12. **Stale bytecache** — `rm -f src/aiflow/**/__pycache__/*.pyc` + restart
13. **@mui ZERO** — Minden MUI import eltavolitva (S6). NE adjunk hozza ujat!

---

## KORNYEZET ELLENORZES (session indulaskor KOTELEZO!)

> **Session 13 utan uj terminal + uj Claude instance indult.**
> **Az alabbi ellenorzeseket MINDEN session elejen el KELL vegezni!**

```bash
# 0. ELSO LEPES: ellenorizd a branch-et
git branch --show-current   # → feature/v1.2.1-production-ready
git log --oneline -3        # → utolso commitok stimmelnek?

# 1. Python venv ellenorzes
.venv\Scripts\python.exe --version   # → Python 3.12.x
.venv\Scripts\python.exe -c "import fastapi, pydantic, structlog, sqlalchemy; print('Core deps OK')"
.venv\Scripts\python.exe -c "import pypdfium2; import docling; import aiosmtplib; print('Extra deps OK')"
.venv\Scripts\python.exe -c "from playwright.sync_api import sync_playwright; print('Playwright OK')"

# 2. Ha BARMELYIK import FAIL → ujratelepites:
# uv pip install -e ".[dev]" pypdfium2 docling aiosmtplib pytest-playwright

# 3. Node/npm ellenorzes (aiflow-admin)
cd aiflow-admin && node --version && npm --version   # → Node 20+, npm 10+
ls node_modules/.package-lock.json > /dev/null 2>&1 || npm ci   # Ha nincs node_modules → install

# 4. Docker services
docker compose ps   # → db (5433) + redis (6379) KELL futniuk
docker compose up -d db redis   # Ha nem futnak

# 5. Szerver inditas
.venv\Scripts\python.exe -B -m uvicorn aiflow.api.app:create_app --factory --port 8102
cd aiflow-admin && npm run dev   # → localhost:5174

# 6. Smoke test (szerver indulas utan)
./scripts/smoke_test.sh   # → ALL PASS (10/10)

# 7. E2E tesztek (S9 regresszio check)
pytest tests/e2e/test_smoke.py -v --headed   # → 40/40 PASS (ha szerver fut)
```

### Gyakori hibak uj session-ben:

- **`ModuleNotFoundError: pypdfium2`** → `.venv` ujraepitesnel elveszett
- **Port 8102 foglalt** → `taskkill` a regi process-t
- **Stale __pycache__** → `rm -f src/aiflow/**/__pycache__/*.pyc`
- **aiflow-admin npm hiba** → `cd aiflow-admin && rm -rf node_modules && npm ci`
- **Playwright browser hiany** → `npx playwright install chromium`

---

## TELJES VEGREHAJTASI TERV (v1.2.1)

```
S1-S6:  Tier A — UI Integracio ────────── DONE ✓ (session 10)
S7:     Langfuse integracio ───────────── DONE ✓ (session 11)
S8:     Promptfoo 6 skill ─────────────── DONE ✓ (session 12)
S9:     E2E Playwright suite ──────────── DONE ✓ (session 12)
S10:    CI/CD pipeline ────────────────── DONE ✓ (session 13)
S11:    Free text + intent schema ─────── DONE ✓ (session 13)
S12:    SLA + cost estimation ─────────── DONE ✓ (session 13)
S13:    Integralt E2E teszteles ────────── KOVETKEZO ← ITT VAGYUNK
S14:    Vegleges polish + v1.2.1 tag ──── UTOLSO
```

### Sikerkriteriumok (v1.2.1 DONE):

| # | Kriterium | Allapot |
|---|-----------|---------|
| 1 | Chat UI markdown | DONE (S1) |
| 2 | In-app notifications | DONE (S2) |
| 3 | Quality dashboard | DONE (S3) |
| 4 | Design tokens | DONE (S5) |
| 5 | Langfuse traces | DONE (S7) |
| 6 | Promptfoo 6/6 skill | DONE (S8) |
| 7 | E2E tesztek 10+ | DONE (S9, 54 teszt) |
| 8 | CI/CD pipeline | DONE (S10, CI YAML ok, runtime FAIL=P5) |
| 9 | Free text extraction | DONE (S11) |
| 10 | SLA eszkalacio | DONE (S12) |
| 11 | UI teljeskoruseg | DONE (S6, 0 MUI) |
| 12 | PWA | TODO (S14 optional) |
| 13 | Accessibility | TODO (S14) |
| 14 | v1.2.1 tag | TODO (S14) |
