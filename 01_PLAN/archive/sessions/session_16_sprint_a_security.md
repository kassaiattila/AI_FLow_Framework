# AIFlow Sprint A — Session 16 Prompt (A3: Security Hardening)

> **Datum:** 2026-04-04 (session 15 utan)
> **Elozo session:** S15 — A0+A1+A2 DONE (CI green, ruff 1234→0, dead code audit)
> **Branch:** `feature/v1.2.2-infrastructure`
> **Port:** API 8102, Frontend 5174 (Vite proxy → 8102)
> **Utolso commit:** `e83a0b7` docs: update progress — A2 dead code audit DONE
> **PR:** https://github.com/kassaiattila/AI_FLow_Framework/pull/1

---

## AKTUALIS TERV

**`01_PLAN/58_POST_SPRINT_HARDENING_PLAN.md`** — Sprint A (v1.2.2): A0-A8, ~8 session.

---

## KONTEXTUS

### Session 15 Eredmenyek (A0+A1+A2)

- **A0 DONE:** CI/CD workflow-ok javitva (ci.yml, ci-skill.yml, prompt-eval.yml, nightly-regression.yml)
  - `uv sync --dev` → `uv venv && uv pip install -e ".[dev]"` (ruff binary resolvable)
  - `skills/` kihagyva ci.yml ruff scope-bol
  - `pythonpath=["."]` → skill tesztek importja mukodik CI-ben
  - prompt-eval.yml: graceful skip ha OPENAI_API_KEY nem konfiguralt
- **A1 DONE:** Ruff 1,234 → 0 (teljes codebase clean: src/ + tests/ + skills/)
  - 601 auto-fix + pyproject.toml per-file-ignores + 75 manual fix + ruff format
- **A2 DONE:** Halott kod audit
  - `src/aiflow/contrib/` TOROLVE (1,406 sor) — backward-compat re-exports → tools/
  - `deprecated/`, `rxconfig.py` TOROLVE
  - Import migracio: cubix → tools.playwright_browser, test_kafka → tools.kafka

### Sprint A Allapot

| Fazis | Tartalom | Allapot |
|-------|----------|---------|
| A0 | CI/CD Green | **DONE** (27e9c82) |
| A1 | Ruff 1,234 → 0 | **DONE** (a32a84d) |
| A2 | Halott kod audit | **DONE** (2c0e078) |
| A3 | Security hardening | **← JELEN SESSION** |
| A4 | Stubs + alapfunkciok | TODO |
| A5 | Guardrail keretrendszer | TODO |
| A6 | POST-AUDIT | TODO |
| A7 | Javitasok | TODO |
| A8 | v1.2.2 tag | TODO |

### Infrastruktura Szamok

- 26 service, 165 API endpoint (25 router), 45 DB tabla, 29 migracio, 19 adapter
- 369 unit test (1 pre-existing fail: test_config.py), 157 skill test, 102 E2E, 51 Promptfoo
- Docker: PostgreSQL 5433, Redis 6379
- Auth: admin@bestix.hu / admin

---

## A3 FELADAT: Security Hardening

### A3.1 — JWT atiras PyJWT RS256-ra

**Jelenlegi helyzet:**
- `src/aiflow/security/auth.py` (138 sor) — sajat HMAC-SHA256 implementacio
- Kommentben irja: "In production, use RS256 with public/private key pair"
- `PyJWT[crypto]` mar a `pyproject.toml` dependencies-ben van (telepitve!)

**Szukseges valtozasok:**
1. `AuthProvider.create_token()` → PyJWT `jwt.encode()` RS256-tal
2. `AuthProvider.verify_token()` → PyJWT `jwt.decode()` RS256-tal
3. Kulcspar generalo script: `scripts/generate_jwt_keys.sh`
4. Config: `AIFLOW_JWT_PRIVATE_KEY_PATH` + `AIFLOW_JWT_PUBLIC_KEY_PATH` env var
5. Fallback: Ha nincs kulcspar, generaljunk egyet automatikusan (dev mode)
6. 5+ unit test (token create, verify, expired, invalid sig, wrong key)

### A3.2 — JWT secret enforcement

- Prod (AIFLOW_ENV=production): KOTELEZO kulcspar, hiba ha hianyzik
- Dev: WARNING, auto-generated kulcspar OK

### A3.3 — Session lejarat → UI force logout

**Backend:**
- 401 Unauthorized ha token lejart (ez mar mukodik verify_token-nel)

**Frontend (aiflow-admin/):**
- `src/lib/api-client.ts` fetchApi() → 401 interceptor → redirect /login
- JWT exp decode → periodic check (60s interval)
- exp < now+5min → WARNING banner
- exp < now → auto logout (localStorage clear + redirect)

### A3.4 — CORS szukites

**Jelenlegi:** `src/aiflow/api/app.py` L25-47 — env var alapu, dev defaults ["http://localhost:*"]
- Szukites: `allow_methods=["GET","POST","PUT","DELETE","PATCH"]`
- `allow_headers` explicit lista (Authorization, Content-Type, X-Request-ID)
- `allow_credentials=True` CSAK ha explicit origin van megadva

### A3.5 — Rate limiter middleware bekotes

- `/auth/*` = 10 req/min (brute force vedelem)
- `/api/*` = 100 req/min (altalanos)
- 429 Too Many Requests + `Retry-After` header
- Redis-based (mar van: `src/aiflow/services/rate_limiter/service.py`)

### A3.6 — File upload vedelem

- `pathlib.resolve()` + `is_relative_to()` path traversal ellen
- `secure_filename()` (Werkzeug pattern)
- 50MB limit (konfiguralhato)
- Ellenorzes: documents, emails, media_processor, rag_engine upload endpointok

### A3.7 — Security headers

- Middleware: `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security` (HSTS, csak HTTPS-en)
- `Content-Security-Policy` (basic policy)

---

## FAJLOK AMIK ERINTETTEK

```
src/aiflow/security/auth.py          # 138 sor — JWT HMAC → RS256 (FO MUNKA)
src/aiflow/security/__init__.py      # 27 sor — exportok frissites
src/aiflow/api/app.py                # CORS config (L101-106)
src/aiflow/api/middleware.py          # 150 sor — rate limit + security headers
src/aiflow/api/v1/auth.py            # login endpoint (token kiadás)
src/aiflow/core/config.py            # JWT key path config
tests/unit/security/test_auth.py     # JWT tesztek (bovites)
aiflow-admin/src/lib/api-client.ts   # 401 interceptor
aiflow-admin/src/lib/auth.ts         # token exp check + auto logout
scripts/generate_jwt_keys.sh         # UJ — kulcspar generalo
```

---

## KORNYEZET ELLENORZES (session indulaskor KOTELEZO!)

```bash
# 0. Branch
git branch --show-current   # → feature/v1.2.2-infrastructure
git log --oneline -3        # → utolso commitok stimmelnek?

# 1. Python venv
.venv\Scripts\python.exe --version
.venv\Scripts\python.exe -c "import jwt; print('PyJWT', jwt.__version__)"

# 2. Docker
docker compose ps   # db (5433) + redis (6379) KELL

# 3. Security modul allapot
wc -l src/aiflow/security/*.py   # ~ 714 sor
```

---

## KOTELEZO SZABALYOK (MINDEN session-ben!)

### Session vegen:

1. `pytest tests/unit/ -q` → ALL PASS
2. `ruff check src/ tests/` → CLEAN
3. `cd aiflow-admin && npx tsc --noEmit` → 0 error (ha UI valtozas)
4. **58_POST_SPRINT_HARDENING_PLAN.md** progress tabla: A3 DONE + datum + commit
5. `.venv` dep check

### Commit konvencio:

- `feat(security):` — uj security feature
- `fix(security):` — security javitas
- Co-Authored-By header MINDEN commit-ben

---

## ELOZO SESSION TANULSAGAI (S15)

1. **`uv sync --dev` NEM mukodik CI-ben** — `uv venv && uv pip install -e ".[dev]"` kell
2. **skills/ pythonpath** — `pythonpath=["."]` kell a pyproject.toml-ben
3. **ruff --unsafe-fixes** — B905, F841 (zip strict, unused var) auto-fixalhato igy
4. **contrib/ = halott kod** — Minden re-export volt, tools/ a kanonikus
5. **1 pre-existing test fail** — `test_config.py::test_default_values` (session 1 ota)

---

## VEGREHAJTASI TERV (Session 16)

```
1. KORNYEZET ELLENORZES → branch, venv, Docker, PyJWT
2. A3.1: JWT RS256 implementacio (auth.py atiras)
3. A3.2: JWT secret enforcement (prod vs dev)
4. A3.3: Session lejarat UI (fetchApi 401 interceptor + exp check)
5. A3.4: CORS szukites (app.py)
6. A3.5: Rate limiter middleware (Redis-based)
7. A3.6: File upload vedelem (path traversal, size limit)
8. A3.7: Security headers middleware
9. REGRESSZIO: pytest + ruff + tsc
10. SESSION LEZARAS: progress tabla, commit, push
```

---

## TELJES SPRINT A UTEMTERV

```
Session 15: A0+A1+A2 ──────────────── DONE (CI, ruff, dead code)
Session 16: A3 (Security) ──────────── ← JELEN SESSION
Session 17: A4 (Stubs + alapfunkciok) ── P1, P2, DataTable
Session 18: A5 (Guardrail keretrendszer) ── InputGuard + OutputGuard + ScopeGuard
Session 19: A6 (POST-AUDIT) ────────── Teljes ellenorzes
Session 20: A7+A8 (Javitasok + v1.2.2) ── Fix + tag
```
