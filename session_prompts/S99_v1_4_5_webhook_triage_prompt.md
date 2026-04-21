# AIFlow v1.4.5 hardening — Session 99 Prompt (webhook triage + UC1 E2E live run + PR #13 merge)

> **Datum:** 2026-05-03 (tervezett start)
> **Branch:** lásd LÉPÉS 0 — függ attól, mergelődött-e már PR #13. Ha IGEN → `feature/v1.4.5-hardening` új branch `main`-ről. Ha NEM → maradunk `feature/v1.4.5-doc-processing`-en.
> **HEAD prereq:** `156db2b` — `feat(v1.4.5): S98 — UC1 Playwright golden-path + pyee<13 pin + alembic 037 test unstick`
> **Port:** API 8102 | Frontend Vite :5174
> **Plan:** `01_PLAN/110_USE_CASE_FIRST_REPLAN.md` + `01_PLAN/ROADMAP.md` (Sprint J kickoff függ ettől)
> **Session típus:** Hardening — pre-existing sequence-hang fix + UC1 live verification. Code risk: LOW–MEDIUM. Process risk: MEDIUM (integration test ordering tricky).

---

## KONTEXTUS

### Honnan jöttünk

- **S98 COMMITTED** `156db2b`, tag `v1.4.5-uc1` kint az origin-on, PR #13 megnyitva (`feature/v1.4.5-doc-processing → main`).
- Dep-triage kész: `pyee<13` pin (playwright 1.58→1.51, pyee 13→12). 410 E2E collect zöld.
- Új UC1 spec létrejött (`tests/e2e/test_package_detail.py`), de **élő stack ellen nem futott le** S98-ban — szükséges `make api` + `npm run dev` + admin seed.
- Unit baseline: **1949 PASS / 0 fail** (jobb mint S98 kickoff — a docling reinstall hozta fel a latens `test_tier3_services.py::test_parse_text_file` failt).
- Alembic head: **039** (nem változott).

### Hova tartunk — S99 scope

Sprint J tiszta kezdés csak akkor lehetséges, ha ez a két S98 follow-up zöld:

1. **Webhook router sequence-hang** — `tests/integration/sources/test_webhook_router.py` 8 tesztből 3 fut le teljes fájlmenetben, 5 hang (`test_duplicate_idempotency_key_returns_409`-től kezdve). Izolációban mindegyik PASS (igazoltuk S98-ban `test_expired_timestamp_returns_401` single-run PASS). Gyanú: `feedback_asyncpg_pool_event_loop.md` mintás leak — module-scope `_warmed_app` fixture + TestClient event-loop kombináció pool-referenciát ragaszt egy lezárt loop-hoz a sorrendben később futó tesztekben.
2. **UC1 golden-path E2E élő futás** — kézi/automatizált setup: `make api` (API :8102), `cd aiflow-admin && npm run dev` (Vite :5174), admin user seed, majd `.venv/Scripts/python.exe -m pytest tests/e2e/test_package_detail.py -v` zöld.
3. **PR #13 review + merge** — függ az előző kettőtől, plus user review.

### Jelenlegi állapot (induláskor várt)

```
27 service | 181 endpoint | 50 DB tábla | 39 Alembic migration (head: 039)
1949 unit PASS / 0 FAIL | 410 E2E collected | 43+ integration PASS (5 webhook hang quarantined)
```

---

## ELŐFELTÉTELEK

```bash
# LÉPÉS 0 — branch ellenőrzés
gh pr view 13 --json state,mergedAt,baseRefName,headRefName 2>&1 | tail -10
# Ha state=MERGED  → git checkout main && git pull && git checkout -b feature/v1.4.5-hardening
# Ha state=OPEN    → maradunk feature/v1.4.5-doc-processing-en

git branch --show-current
git log --oneline -3                                            # HEAD 156db2b = S98
.venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov      # 1949 PASS
.venv/Scripts/python.exe -m ruff check src/ tests/ --quiet      # exit 0
PYTHONPATH=src .venv/Scripts/python.exe -m alembic current      # 039
docker ps --filter "name=07_ai_flow_framwork" --format "table {{.Names}}\t{{.Status}}"
# db + redis healthy — ha nem: docker compose up -d db redis
```

---

## FELADATOK

### LÉPÉS 1 — webhook_router sequence-hang triage (blocker)

Fájl: `tests/integration/sources/test_webhook_router.py`.

Első lépés — reprodukció hash-stabil flag nélkül, hogy biztos ugyanaz a hang-point:

```bash
PYTHONUNBUFFERED=1 .venv/Scripts/python.exe -m pytest tests/integration/sources/test_webhook_router.py -v --no-cov --tb=short -p no:cacheprovider
# Várt: test_valid_signature_returns_202 PASS
#       test_invalid_signature_returns_401 PASS
#       test_expired_timestamp_returns_401 PASS
#       test_duplicate_idempotency_key_returns_409 HANG
```

Gyanú-mátrix (fontossági sorrendben):

1. **asyncpg pool loop-leak** — a `_warmed_app` module-scope fixture (ld. `tests/e2e/v1_4_1_phase_1b/test_upload_package.py:49` mintára) létrehoz egy `TestClient`-et, azon belül egy event-loop-ot, és a `aiflow.api.deps._pool` az arra a loop-ra kötődik. Utána a második, idempotency-kulcsos kliens-call valahol egy másik loop-ból próbálja használni a pool-t → deadlock. Javítás: a fixture fordítson vissza minden `_pool=None`-ra a test-között, vagy kapcsolj function-scope-re (drágább de tisztább).
2. **Redis connection leak** — ha webhook idempotency Redis-ben van tárolva (`aiflow.core.idempotency`), ott is hasonló loop-kötés előfordulhat. Ugyanaz a gyógymód.
3. **TestClient context-manager leak** — `with TestClient(...)` nem záródik be a teszt-függvény végén, még aktív connect-et tart a következő call idejére.

Javítási irány (minimum-invasive):

```python
# tests/integration/sources/test_webhook_router.py conftest-jébe vagy az adott test-fájlba

@pytest.fixture(autouse=True)
def _reset_pool_between_tests():
    """Force pool re-creation on the current event loop — asyncpg pools are loop-bound."""
    from aiflow.api import deps as _deps
    _deps._pool = None
    yield
    _deps._pool = None
```

Ha ez nem elég — function-scope `_warmed_app` fixture:

```python
@pytest.fixture()  # was scope="module"
def _warmed_app(tmp_path_factory): ...
```

Exit kritérium: `tests/integration/sources/test_webhook_router.py` teljes fájl PASS (8/8) nem-izolált módban is.

### LÉPÉS 2 — UC1 golden-path E2E élő futtatás

Háttér-szolgáltatások:

```bash
# Term 1
docker compose up -d db redis
PYTHONPATH=src .venv/Scripts/python.exe -m alembic upgrade head
make api                                   # API :8102

# Term 2
cd aiflow-admin && npm run dev             # Vite :5174

# Admin user seed (ha még nincs)
PYTHONPATH=src .venv/Scripts/python.exe scripts/seed_admin_user.py  # ha van ilyen; különben manuális POST /auth/register
```

Futtatás:

```bash
PYTHONUNBUFFERED=1 .venv/Scripts/python.exe -m pytest tests/e2e/test_package_detail.py -v --no-cov --tb=short
```

Exit kritérium: `test_package_detail_renders_badge_and_tabs` PASS + 0 console error.

Közben figyeld:
- `[data-testid="parser-badge"]` data-parser attribute egyike: `docling_standard | unstructured_fast | azure_document_intelligence | skipped_policy | unknown`.
- Tab-váltás (routing / extraction / pii) nem dob konzol hibát.

### LÉPÉS 3 — PR #13 review + merge

Ha LÉPÉS 1 + 2 zöld:

```bash
gh pr view 13 --json state,reviews,checks,mergeStateStatus
# Ha mergeable, squash merge (vagy user-specifikus preferencia szerint)
gh pr merge 13 --squash --delete-branch
```

Ha a branch mergelődött, cseréljük az S98 érintettek branch-et:

```bash
git checkout main
git pull
git tag -l v1.4.5-uc1     # verifikáld hogy a tag megmaradt
git checkout -b feature/v1.4.5-hardening      # következő munka ide
```

### LÉPÉS 4 — Regression + session-close

```bash
.venv/Scripts/python.exe -m ruff check src/ tests/ --quiet
.venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov
.venv/Scripts/python.exe -m pytest tests/integration/ --no-cov          # <-- most már legyen 48+ PASS
cd aiflow-admin && npx tsc --noEmit && cd ..

/session-close S99
```

---

## STOP FELTÉTELEK

- **HARD:** webhook hang root-cause nem asyncpg/Redis pool-loop — hanem mélyebb (pl. FastAPI dependency-injection circular lock) → kérdezz, ne guessolj.
- **HARD:** Új Alembic migration szükséges (pl. idempotency_store tábla) → NEM ebbe a session-be, Sprint J scope.
- **HARD:** UC1 E2E FAIL parser-badge selector-on vagy tenant boundary-n → a prod kódot ne patcheld, először tisztázd a test seed flow-t.
- **HARD:** PR #13 main-re merge előtt — SOHA direct push main-re, SOHA `--force`.
- **SOFT:** Ha a webhook triage 90 percnél tovább fut, inkább quarantine-e a tesztfájlt `@pytest.mark.skip(reason="v1.4.5 sequence-hang, see issue #XX")`-kel és nyisd meg az issue-t, semmint órákig fejjel nekimenni.

---

## SESSION VÉGÉN

```
/session-close S99
```

Utána `/clear` és Sprint J kickoff (új NEXT.md a 110_USE_CASE_FIRST_REPLAN.md §5 vagy új sprint-terv alapján).
