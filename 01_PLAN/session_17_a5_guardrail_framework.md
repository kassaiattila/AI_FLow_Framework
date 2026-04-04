# AIFlow Sprint A — Session 17 Prompt (A5: Guardrail Framework)

> **Datum:** 2026-04-04 (session 16 utan)
> **Elozo session:** S16 — A3 Security Hardening + A4 Stubs DONE
> **Branch:** `feature/v1.2.2-infrastructure`
> **Port:** API 8102, Frontend 5174 (Vite proxy → 8102)
> **Utolso commit:** `bbfd4cf` docs: update progress — A4 stubs+alapfunkciok DONE
> **PR:** https://github.com/kassaiattila/AI_FLow_Framework/pull/1

---

## AKTUALIS TERV

**`01_PLAN/58_POST_SPRINT_HARDENING_PLAN.md`** — Sprint A (v1.2.2): A0-A8, ~8 session.

---

## KONTEXTUS

### Session 16 Eredmenyek (A3+A4)

- **A3 DONE** (`176f137`): Security hardening
  - JWT RS256 (PyJWT + auto keygen dev/prod enforcement) — `security/auth.py` (187 sor)
  - CORS restriction — explicit methods+headers (`app.py`)
  - RateLimitMiddleware — Redis sliding window, /auth/* 10/min, /api/* 100/min (`middleware.py`)
  - SecurityHeadersMiddleware — X-Content-Type-Options, X-Frame-Options, CSP, HSTS (`middleware.py`)
  - MaxBodySizeMiddleware — 50MB file upload limit (`middleware.py`)
  - File upload utils — `secure_filename()`, `validate_upload_path()` (`security/upload.py`)
  - Frontend — 401 interceptor → force logout, `startSessionMonitor()` 60s exp check (`api-client.ts`, `auth.ts`)
  - 97 security tests PASS (20 new)
- **A4 DONE** (`87b896e`): Stubs + alapfunkciok
  - CLI "planned for v1.3.0" messages (skill, eval, prompt, workflow commands)
  - pdf_parser, docx_parser → DEPRECATED, docling reference
  - kafka.py → DEFERRED header
  - llm_rubric_placeholder → REMOVED (Promptfoo replaces it)
  - Pipeline templates tab on Pipelines.tsx (i18n HU+EN, deploy button)
  - Route conflict fix — `_parse_pipeline_id()` UUID validation
  - DataTable infinite re-render fix (data ref instead of dep)
  - STUB_INVENTORY.md created

### Sprint A Allapot

| Fazis | Tartalom                | Allapot              | Commit  |
| ----- | ----------------------- | -------------------- | ------- |
| A0    | CI/CD Green             | **DONE**             | 27e9c82 |
| A1    | Ruff 1,234 → 0         | **DONE**             | a32a84d |
| A2    | Halott kod audit        | **DONE**             | 2c0e078 |
| A3    | Security hardening      | **DONE**             | 176f137 |
| A4    | Stubs + alapfunkciok    | **DONE**             | 87b896e |
| A5    | Guardrail keretrendszer | **← JELEN SESSION**  |         |
| A6    | POST-AUDIT              | TODO                 |         |
| A7    | Javitasok               | TODO                 |         |
| A8    | v1.2.2 tag              | TODO                 |         |

### Infrastruktura Szamok

- 26 service, 165 API endpoint (25 router), 45 DB tabla, 29 migracio, 19 adapter
- 1118 unit test (1 pre-existing fail: test_config.py), 157 skill test, 102 E2E, 51 Promptfoo
- Docker: PostgreSQL 5433, Redis 6379
- Auth: admin@bestix.hu / admin

---

## A5 FELADAT: Guardrail Keretrendszer

> **Gate:** GuardrailBase + 3 guard implementacio + middleware + 30 test PASS + config sablon.
> **Inspiracio:** `skills/aszf_rag_chat/reference/` (RAG metodologia — scope, hallucination, grounding)

### A5.1 — Guardrail Architecture

A tervezett mappastruktúra:

```
src/aiflow/guardrails/
  __init__.py
  base.py           # GuardrailBase ABC: check_input(), check_output()
  input_guard.py     # InputGuard: prompt injection, PII, length limit
  output_guard.py    # OutputGuard: content safety, hallucination flag, PII
  scope_guard.py     # ScopeGuard: in-scope / out-of-scope / dangerous (3-tier)
  config.py          # GuardrailConfig: per-service YAML config loader
```

**FONTOS:** Mar van egy meglevo guardrails modul: `src/aiflow/security/guardrails.py` (97 sor).
Ez tartalmaz: `GuardrailResult`, `InputGuardrail` (injection + PII + length), `OutputGuardrail` (PII check).
Az exportok `security/__init__.py`-ban vannak regisztrálva.

**Strategia:** A meglevo `security/guardrails.py`-t MEG KELL TARTANI backward compat-nak,
de az uj, teljesebb implementaciot a `src/aiflow/guardrails/` package-ben kell epiteni.
A regi modul atiranyitasa: re-export az uj package-bol.

### A5.2 — InputGuard

```python
class InputGuard(GuardrailBase):
    """User input validacio MIELOTT az LLM-hez jut."""
    - prompt_injection_detect(text) → bool
      * Ismert injection pattern-ek (ignore previous, system:, jailbreak stb.)
      * Heurisztika: rendkívüli hossz, különleges karakterek
    - pii_detect(text) → list[PIIMatch]
      * Email, telefon, adoszam, bankszamla regex (HU+US pattern)
      * Opcio: maszkolas automatikus (user@***.com)
    - length_check(text, max_tokens=2000) → bool
    - language_check(text, allowed=["hu","en"]) → bool (optional)
```

### A5.3 — OutputGuard

```python
class OutputGuard(GuardrailBase):
    """LLM valasz validacio MIELOTT a user-hez jut."""
    - content_safety(response) → SafetyResult
      * Eroszak, serto tartalom detektalas
    - hallucination_flag(response, sources) → float (0-1)
      * Valasz vs. forras kontextus osszevetes
    - pii_leak_check(response) → list[PIIMatch]
    - scope_adherence(response, allowed_topics) → ScopeResult
```

### A5.4 — ScopeGuard (3-tier)

```python
class ScopeGuard(GuardrailBase):
    """3-tier scope boundary enforcement."""
    Kategorizalas:
    1. IN_SCOPE → teljes valasz, forras hivatkozassal
    2. OUT_OF_SCOPE → "Nem tudok erre valaszolni" + indoklas
    3. DANGEROUS → rendszer megtagadas + log + alert
```

### A5.5 — GuardrailConfig (YAML)

```yaml
# skills/aszf_rag_chat/guardrails.yaml (pelda)
scope:
  allowed_topics: ["jog", "biztositas", "aszf", "szolgaltatas"]
  blocked_topics: ["politika", "orvosi tanacs", "befektetesi tanacs"]
  dangerous_patterns: ["hogyan torzek be", "hogyan hackeljem"]
input:
  max_length: 2000
  injection_patterns: ["ignore previous", "system:", "you are now"]
  pii_masking: true
output:
  require_citation: true
  hallucination_threshold: 0.7
  pii_check: true
```

### A5.6 — Tesztek (30+ test)

```
tests/unit/guardrails/
  test_input_guard.py   # 10+ test (injection, PII, length, language)
  test_output_guard.py  # 10+ test (safety, hallucination, PII leak)
  test_scope_guard.py   # 10+ test (3-tier scope, config loading)
```

Golden dataset template:
```
tests/guardrails/golden_dataset.yaml
  known_safe_inputs, known_injection_attempts, known_dangerous_queries, expected_refusals
```

---

## FAJLOK AMIK ERINTETTEK

```
src/aiflow/guardrails/             # UJ package (5 fajl)
  __init__.py
  base.py
  input_guard.py
  output_guard.py
  scope_guard.py
  config.py
src/aiflow/security/guardrails.py  # MEGLEVO (97 sor) — re-export az uj package-bol
src/aiflow/security/__init__.py    # Export frissites
tests/unit/guardrails/             # UJ (3 test fajl, 30+ test)
  __init__.py
  test_input_guard.py
  test_output_guard.py
  test_scope_guard.py
tests/guardrails/                  # Golden dataset
  golden_dataset.yaml
```

---

## KORNYEZET ELLENORZES (session indulaskor KOTELEZO!)

```bash
# 0. Branch
git branch --show-current   # → feature/v1.2.2-infrastructure
git log --oneline -3        # → utolso commitok stimmelnek?

# 1. Python venv
.venv\Scripts\python.exe --version
.venv\Scripts\python.exe -c "import jwt; print('PyJWT OK')"

# 2. Docker
docker compose ps   # db (5433) + redis (6379) KELL

# 3. Meglevo guardrails
wc -l src/aiflow/security/guardrails.py   # ~ 97 sor
cat src/aiflow/security/guardrails.py | head -3

# 4. Teszt baseline
python -m pytest tests/unit/ -q --co 2>&1 | tail -1   # → 1118 tests collected
```

---

## KOTELEZO SZABALYOK (MINDEN session-ben!)

### Session vegen:

1. `pytest tests/unit/ -q` → ALL PASS
2. `ruff check src/ tests/` → CLEAN
3. `cd aiflow-admin && npx tsc --noEmit` → 0 error (ha UI valtozas)
4. **58_POST_SPRINT_HARDENING_PLAN.md** progress tabla: A5 DONE + datum + commit
5. `.venv` dep check

### Commit konvencio:

- `feat(guardrails):` — uj guardrail feature
- Co-Authored-By header MINDEN commit-ben

---

## ELOZO SESSION TANULSAGAI (S16)

1. **`replace_all=True` veszelyes** — `uuid.UUID(pipeline_id)` → `_parse_pipeline_id(pipeline_id)` a sajat fuggveny belsejeben is kicserelodott → rekurziv hivas. MINDIG ellenorizd a replace_all eredmenyet!
2. **ruff B904** — `raise ... from exc` kell except blokkon belul
3. **DataTable re-render** — `data` a useEffect deps-ben infinite loop-ot okozhat ha a parent ujrarenderi a data array-t. Fix: useRef.
4. **Meglevo security/guardrails.py** — 97 soros, InputGuardrail + OutputGuardrail + GuardrailResult mar letezik. NEM torolheto, backward compat kell.

---

## VEGREHAJTASI TERV (Session 17)

```
1. KORNYEZET ELLENORZES → branch, venv, Docker, meglevo guardrails
2. A5.1: Guardrail package letrehozas (base.py ABC)
3. A5.2: InputGuard implementacio (injection, PII, length, language)
4. A5.3: OutputGuard implementacio (safety, hallucination, PII leak)
5. A5.4: ScopeGuard implementacio (3-tier: in-scope/out-of-scope/dangerous)
6. A5.5: GuardrailConfig (YAML loader + sablon)
7. A5.6: Backward compat — security/guardrails.py re-export
8. A5.7: 30+ unit test (3 test fajl + golden dataset)
9. REGRESSZIO: pytest + ruff + tsc
10. SESSION LEZARAS: progress tabla, commit, push
```

---

## TELJES SPRINT A UTEMTERV

```
Session 15: A0+A1+A2 ──────────────── DONE (CI, ruff, dead code)
Session 16: A3+A4 ──────────────────── DONE (security, stubs)
Session 17: A5 (Guardrail framework) ── ← KOVETKEZO SESSION
Session 18: A6 (POST-AUDIT) ────────── Teljes ellenorzes
Session 19: A7+A8 (Javitasok + v1.2.2) ── Fix + tag + merge
```
