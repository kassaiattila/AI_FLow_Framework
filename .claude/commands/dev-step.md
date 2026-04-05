Record a completed development step and run the full validation sequence.

Arguments: $ARGUMENTS
(Optional: step title, e.g. "B0.2 qbpp torles")

## 5 FAZIS: CHECK → CODE → TEST → LINT → COMMIT

---

### FAZIS 1: CHECK

```bash
# Branch (NEM main!)
git branch --show-current  # → feature/v1.3.0-service-excellence
```

Olvasd el a releváns tervet: `01_PLAN/58_POST_SPRINT_HARDENING_PLAN.md`
Nezd meg a meglevo kodot — soha ne talald ujra fel ami mar mukodik.

Ha DB valtozas kell: Alembic migracio ELOSZOR (`nullable=True` vagy `server_default`)
Ha UI valtozas kell: lasd skill `aiflow-ui-pipeline` (7 HARD GATE — kihagyni TILOS!)

### FAZIS 2: CODE

- Implementald a feladatot a CLAUDE.md konvenciok szerint
- Async-first, Pydantic, structlog, AIFlowError
- Ha uj fajl: helyes konyvtarba (src/aiflow/, skills/, tests/)

### FAZIS 3: TEST

- Minden uj/modositott kodhoz teszt — lasd skill `aiflow-testing`
- Valos backend, valos DB, valos LLM — SOHA ne mock/fake!

```bash
# Python backend:
.venv/Scripts/python.exe -m pytest tests/unit/ -q  # ALL PASS

# API (ha endpoint valtozas):
curl -s http://localhost:8102/api/v1/{endpoint} | python -m json.tool
# Ellenorizd: source: "backend" (NEM "demo"!)

# UI (ha aiflow-admin/ valtozas):
cd aiflow-admin && npx tsc --noEmit  # 0 error
# + Playwright E2E (navigate → snapshot → click → console_messages → 0 hiba)
```

### FAZIS 4: LINT

```bash
.venv/Scripts/python.exe -m ruff check src/ tests/ skills/  # 0 error
# Hook automatikusan futtatja ruff-ot minden .py Write/Edit utan
```

### FAZIS 5: COMMIT

```bash
git add {specific files}  # NE hasznalj "git add -A"!
git commit -m "feat|fix|docs|refactor(...): leiras

Co-Authored-By: Claude <noreply@anthropic.com>"
```

Ha BARMELYIK fazis FAIL → STOP → javitas → ujra elejeirol!

---

## PLAN UPDATE (MINDEN /dev-step UTAN ellenorizd!)

- `01_PLAN/58_POST_SPRINT_HARDENING_PLAN.md` — progress tabla frissitendo?
- Root `CLAUDE.md` + `01_PLAN/CLAUDE.md` — szamok valtoztak?
- `FEATURES.md` — uj feature/endpoint hozzaadando?

## DEPENDENCY CHECK (ha .venv valtozas volt)

```bash
python -c "import fastapi, pydantic, structlog; print('OK')"
```
