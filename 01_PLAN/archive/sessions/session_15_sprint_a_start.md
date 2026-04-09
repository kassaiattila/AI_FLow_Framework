# AIFlow Sprint A — Session 15 Prompt (A0: CI/CD Green + A1 Start)

> **Datum:** 2026-04-04 (session 14 utan)
> **Elozo session:** S14 — v1.2.1 tag DONE, 102 E2E PASS, plan v3 megirva
> **Branch:** `feature/v1.2.1-production-ready` → **UJ: `feature/v1.2.2-infrastructure`**
> **Port:** API 8102, Frontend 5174 (Vite proxy → 8102)
> **Utolso commit:** `e78b626` docs: B0 integrated toolchain + operationalization
> **PR:** https://github.com/kassaiattila/AI_FLow_Framework/pull/1

---

## AKTUALIS TERV

**`01_PLAN/58_POST_SPRINT_HARDENING_PLAN.md`** — Sprint A (v1.2.2): A0-A8, ~8 session.

---

## KONTEXTUS

### v1.2.1 COMPLETE (S1-S14)
- 26 service, 165 API endpoint (25 router), 45 DB tabla, 29 migracio, 19 adapter
- 369 unit test (1 pre-existing fail: test_config.py), 102 E2E Playwright, 51 Promptfoo
- Langfuse ENABLED, 9 prompt szinkronizalva
- Docker: PostgreSQL 5433, Redis 6379
- Auth: admin@bestix.hu / admin

### Sprint A Celok (v1.2.2)
- **A0:** CI/CD Green — PR GitHub Actions MIND ZOLD
- **A1:** Ruff 1,234 → 0
- **A2:** Halott kod/mappa audit + archivalas
- **A3:** Security (JWT RS256, session expiry, rate limit, CORS)
- **A4:** Stub cleanup + P1/P2 UI fix
- **A5:** Prompt guardrail keretrendszer
- **A6:** Post-audit
- **A7:** Javitasok (ha A6-ban FAIL)
- **A8:** v1.2.2 tag

### CI/CD Jelenlegi Allapot (4/4 FAIL)

| Workflow | Fajl | Trigger | Fo problema |
|----------|------|---------|-------------|
| AIFlow CI | `ci.yml` | push/PR main | `skills/` benne a ruff scope-ban → 479 hiba |
| Framework CI | `ci-framework.yml` | PR src/** | ruff 574 error a src/aiflow/-on |
| Skill CI | `ci-skill.yml` | PR skills/** | skill fuggoseg hianyzik (collection error) |
| Nightly Regression | `nightly-regression.yml` | cron 03:00 | Nem PR-releváns |

---

## A0 FELADAT: CI/CD Green

### A0.1 — ci.yml fix

**Jelenlegi tartalom (.github/workflows/ci.yml):**
```yaml
# L25: Install dependencies
- run: uv sync --dev

# L27-30: Lint
- name: Lint (ruff)
  run: |
    uv run ruff check src/ tests/ skills/
    uv run ruff format --check src/ tests/ skills/

# L32-33: Unit tests  
- name: Unit tests
  run: uv run pytest tests/unit/ -q --tb=short --junitxml=test-results.xml --cov=aiflow --cov-report=xml
```

**Szukseges valtozasok:**
1. **L29:** `skills/` KIHAGYVA a ruff check-bol → `uv run ruff check src/ tests/`
2. **L30:** Ugyanaz: `uv run ruff format --check src/ tests/`
3. Dependency install OK (`uv sync --dev` jo, konzisztens)

> **FONTOS:** A `skills/` NEM kell ide — van sajat `ci-skill.yml` workflow-ja!
> A ruff 479 hiba a skills/-bol jon (N806 domain valtozok stb.), amit per-file-ignores-zel
> kezeljuk (A1-ben), DE a ci.yml-nek NEM kell latnia oket.

### A0.2 — ci-framework.yml fix

**Jelenlegi tartalom (.github/workflows/ci-framework.yml):**
```yaml
# L19: venv + install
- run: uv venv && uv pip install -e ".[dev]"

# L20-22: Lint
- run: .venv/bin/ruff check src/aiflow/ tests/
- run: .venv/bin/ruff format --check src/aiflow/ tests/
- run: .venv/bin/mypy src/aiflow/ --ignore-missing-imports
```

**Szukseges valtozasok:**
1. **L19 MARAD** — `uv venv && uv pip install` MUKODIK, NEM kell valtoztatni
2. **L20-21 ruff scope HELYES** — `src/aiflow/ tests/` (nem `skills/`)
3. **Fo problema:** a ruff 574 error a CODEBASE-bol jon — A1-ben javitjuk!
4. Opcionalis: mypy `--ignore-missing-imports` → finomhangolas kesobb

> **DONTES:** A ci-framework.yml maga HELYES, a hiba a KODBAZISBAN van (574 ruff).
> Az A0-ban CSAK a ci.yml-t kell javitani. A tobbi A1 feladata.

### A0.3 — ci-skill.yml fix

**Jelenlegi tartalom (.github/workflows/ci-skill.yml):**
```yaml
# L16: install
- run: uv venv && uv pip install -e ".[dev]"

# L17: test
- run: .venv/bin/pytest skills/ -v --tb=short
```

**Szukseges valtozasok:**
1. A `skills/` tesztek `instructor` es egyeb skill-specifikus fuggosegeket igenylik
2. **Opcio A:** pyproject.toml-ben `[project.optional-dependencies]` → `skills = [...]`
3. **Opcio B:** `uv pip install instructor pydantic` kulon lepes
4. **Opcio C:** Egyenlore SKIP a skill tesztek hibakezeleseert (a skill CI CSAK skills/ valtozasra indul)

> **DONTES:** Opcio A — pyproject.toml-ben skills extra hozzaadasa, ci-skill.yml install frissites.

### A0.4 — Ellenorzes

```bash
# Push utan CI ZOLD?
git push → GitHub Actions → MINDEN workflow ZOLD?
# Ha nem: hiba elemzes → fix → push → ujra check
```

---

## A1 ELOKESZITES (ha A0 utan van ido)

### A1 — Ruff Cleanup strategia

A CI PASS-hez a ruff erroroknak 0-ra kell csokkennie. Strategia:

```
1. SAFE BATCH FIX (548 auto-fixable):
   .venv/Scripts/python.exe -m ruff check tests/ --fix                    # 128 fix
   .venv/Scripts/python.exe -m ruff check src/aiflow/ --fix --select I001,F541,UP017  # ~200 fix
   .venv/Scripts/python.exe -m ruff check skills/ --fix --select I001,F541,UP017      # ~100 fix
   → pytest tests/unit/ -q → PASS? (regresszio check)

2. PYPROJECT.TOML per-file-ignores:
   [tool.ruff.lint.per-file-ignores]
   "skills/**/*.py" = ["N806", "N803"]   # 149 domain valtozo hiba → suppress
   "tests/**/*.py" = ["S101"]            # assert hasznalat → OK tesztekben

3. MANUAL (maradekok):
   E501 (287) → logikai sorbontas
   F401 (58) → __init__.py __all__ vagy noqa
   B904 (46) → raise X from e
   F841 (24) → side-effect check + torles
```

---

## KORNYEZET ELLENORZES (session indulaskor KOTELEZO!)

```bash
# 0. Branch
git branch --show-current   # → feature/v1.2.1-production-ready
git log --oneline -3        # → utolso commitok stimmelnek?

# 1. Python venv
.venv\Scripts\python.exe --version
.venv\Scripts\python.exe -c "import fastapi, pydantic, structlog, sqlalchemy; print('Core OK')"

# 2. Node/npm
cd aiflow-admin && node --version && npm --version
ls node_modules/.package-lock.json > /dev/null 2>&1 || npm ci

# 3. Docker
docker compose ps   # db (5433) + redis (6379) KELL

# 4. UJ BRANCH LETREHOZASA (Sprint A elso lepese!):
git checkout -b feature/v1.2.2-infrastructure
git push -u origin feature/v1.2.2-infrastructure
```

---

## KOTELEZO SZABALYOK (MINDEN session-ben!)

### Session vegen:
1. `pytest tests/unit/ -q` → ALL PASS
2. `ruff check` uj/modositott fajlokon → CLEAN
3. `cd aiflow-admin && npx tsc --noEmit` → 0 error (ha UI valtozas)
4. **58_POST_SPRINT_HARDENING_PLAN.md** progress tabla: A0 DONE + datum + commit
5. **01_PLAN/CLAUDE.md** + root **CLAUDE.md** szamok frissites (ha valtoztak)
6. `.venv` dep check

### Commit konvencio:
- `fix(ci):` — CI/CD javitasok
- `refactor(lint):` — ruff javitasok
- Co-Authored-By header MINDEN commit-ben
- SOHA ne commit FAIL teszttel

---

## ELOZO SESSION TANULSAGAI (S10-S14)

1. **Pre-existing ruff 755+ error** — A codebase-ben, NEM uj kod. A1-ben javitjuk.
2. **CI trigger** — `ci.yml` CSAK `push to main` vagy `PR to main` — feature branch push NEM inditja.
3. **GitHub Actions CI** — Mind FAIL (pre-existing). Lokalisan minden PASS.
4. **`/api/v1/health` NEM letezik** — Health CSAK root `/health` path-on.
5. **asyncpg pool.acquire() mock** — `MagicMock` + `@asynccontextmanager`, NEM `AsyncMock.__aenter__`.
6. **intent_schemas tabla** — Runtime `CREATE TABLE IF NOT EXISTS`, nincs Alembic migracio.
7. **Promptfoo JS assertions** — `const` NEM hasznalhato, csak single expression.
8. **Playwright login wait** — `page.locator("nav").wait_for(state="visible")` a legmegbizhatobb.
9. **@mui ZERO** — Minden MUI import eltavolitva (S6). NE adjunk hozza ujat!
10. **Stale bytecache** — `rm -f src/aiflow/**/__pycache__/*.pyc` + restart.

---

## VEGREHAJTASI TERV (Session 15)

```
1. KORNYEZET ELLENORZES → branch, venv, Docker, npm
2. UJ BRANCH: feature/v1.2.2-infrastructure
3. A0.1: ci.yml fix — skills/ kihagyva ruff-bol
4. A0.3: pyproject.toml skills extra + ci-skill.yml frissites
5. PUSH → CI ELLENORZES (ha a PR mar main-re mutat)
6. (HA VAN IDO) A1 batch fix start: /lint-check --fix → 548 auto-fix
7. SESSION LEZARAS: progress tabla, commit, push
```

---

## TELJES SPRINT A UTEMTERV

```
Session 15: A0 (CI/CD Green) + A1 start ─── JELEN SESSION
Session 16: A1 (Ruff batch + manual) ────── 1,234 → 0
Session 17: A2 (Halott kod audit) ──────── Torles + archivalas
Session 18: A3 (Security + JWT session) ── RS256 + force logout
Session 19: A4 (Stubs + alapfunkciok) ──── P1, P2, DataTable
Session 20: A5 (Guardrail keretrendszer) ── InputGuard + OutputGuard + ScopeGuard
Session 21: A6 (POST-AUDIT) ────────────── Teljes ellenorzes
Session 22: A7+A8 (Javitasok + v1.2.2) ── Fix + tag
```
