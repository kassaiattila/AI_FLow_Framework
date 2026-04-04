# AIFlow v1.2.2 + v1.3.0 — Hardening & Service Excellence Plan

> **Szulo terv:** `57_PRODUCTION_READY_SPRINT.md` (v1.2.1 COMPLETE)
> **Elozmeny:** v1.2.1 COMPLETE (S1-S14, 2026-04-04) — UI, observability, quality, 102 E2E
> **Cel:** Ket sprint: (A) infrastruktura+biztonsag+halott kod+guardrail keretrendszer, (B) szolgaltatas excellence+prompt guardrail implementacio
> **Becsult idotartam:** Sprint A ~8 session, Sprint B ~10 session
> **Infrastruktura:** 26 service, 165 endpoint (25 router), 45 DB tabla, 29 migracio, 19 adapter

---

## Kotelezo Szabalyok (CLAUDE.md-bol — mindket sprintre ervenyes!)

### Ciklus Lezaras (MINDEN session vegen KOTELEZO — kihagyni TILOS!)
1. `pytest tests/unit/ -q` → ALL PASS
2. `ruff check` uj/modositott fajlokon → CLEAN
3. `cd aiflow-admin && npx tsc --noEmit` → 0 error (ha UI valtozas volt)
4. **`01_PLAN/58_POST_SPRINT_HARDENING_PLAN.md`** Progress tabla frissites: fazis DONE, datum, commit
5. **`01_PLAN/CLAUDE.md`** key numbers frissites (service, endpoint, teszt szamok)
6. **Root `CLAUDE.md`** infrastruktura szamok frissites
7. `.venv` dep check: `python -c "import fastapi, pydantic, structlog; print('OK')"`

### Git Commit Konvenciok
- Conventional commits: `feat(security):`, `fix(api):`, `refactor(guardrails):`, `test(services):`, `docs:`
- Co-Authored-By header MINDEN commit-ben
- SOHA ne commit-olj FAIL teszt-tel

### Regresszio Kovetelmeny
- `tests/regression_matrix.yaml` hatarozza meg mely suite-ok futnak
- Coverage gate: **>= 80%** globalis minimum (PR BLOCK ha alacsonyabb)
- Regresszio szintek: L1 (commit), L2 (PR), L3 (merge), L4 (staging), L5 (prod)

### Teszteles (STRICT — SOHA NE MOCK/FAKE!)
- Unit: valos logika, mock CSAK kulso service-ekre (LLM, HTTP)
- Integration: valos PostgreSQL + Redis (Docker)
- E2E: valos bongeszo (Playwright), valos backend
- Prompt: valos LLM hivas (Promptfoo), NEM hardcoded valasz

### Technologiai Dontes (VEGLEGES)
- JWT: **PyJWT[crypto]** RS256 (NEM python-jose, NEM HS256)
- Hashing: **bcrypt** (NEM passlib)
- Scheduler: **APScheduler 4.x** (NEM 3.x)
- API key prefix: `"aiflow_sk_"` (NEM "af_sk_")

---

## 0. Audit Eredmenyek (2026-04-04)

### 0.1 Ruff Lint (1,234 hiba)

| Terulet | Hibak | Auto-fix | Manual |
|---------|-------|----------|--------|
| `src/aiflow/` | 574 | 243 | 331 |
| `tests/` | 181 | 128 | 53 |
| `skills/` | 479 | 177 | 302 |
| **OSSZES** | **1,234** | **548 (44%)** | **686** |

### 0.2 Biztonsagi Audit

| Sulyossag | Problema | Fajl |
|-----------|---------|------|
| **HIGH** | Sajat JWT impl. PyJWT helyett | `security/auth.py:47-79` |
| **HIGH** | Default JWT secret | `security/auth.py:47` |
| **MEDIUM** | CORS `allow_methods=["*"]` | `api/app.py:98` |
| **MEDIUM** | Rate limiter NEM bekotve | `api/app.py` |
| **MEDIUM** | Session lejarat: UI NEM jelzi ki a usert | `aiflow-admin` |
| **LOW** | Path traversal file upload | `api/v1/documents.py` |
| **LOW** | API key SHA256 (nem bcrypt) | `security/auth.py:134` |
| **LOW** | Hianyzik: security headers | `api/app.py` |

### 0.3 Halott Kod & Mappa Audit

| Kategoria | Tetelek | Meret | Akcio |
|-----------|---------|-------|-------|
| **Duplikalt contrib/ modulok** | 4 modul (kafka, playwright, human_loop, shell) | ~5KB | TORLES — `tools/` a kanonikus |
| **Legacy UI** | `deprecated/aiflow_ui_reflex_legacy/` | 8KB | TORLES |
| **Reflex remnants** | `rxconfig.py` + `reflex.db` | 12KB | TORLES |
| **Playwright MCP cache** | `.playwright-mcp/` | 1.5MB | TORLES (regeneralodik) |
| **Audio test artifacts** | `output/audio/` | 12MB | TORLES |
| **Coverage artifact** | `.coverage` | 84KB | TORLES |
| **RAG test data** | `data/uploads/rag/` + `e2e-audit/` | ~170MB | ARCHIVALAS (S3/cloud) |
| **Stub/placeholder** | 61 marker 15 fajlban | — | 40 TORLES, 21 dokumentalt |

### 0.4 Prompt Guardrail Audit (aszf_rag_chat/reference/ alapjan)

> A referenciaanyag 7 fajl, ~5000 sor — teljes RAG fejlesztesi metodologia.
> Az alabbi guardrail mintak azonosithatoak es MINDEN AI szolgaltatasra alkalmazhatoak:

| # | Guardrail Minta | Jelenlegi Allapot | Szukseges |
|---|----------------|------------------|-----------|
| 1 | **Scope Boundary Enforcement** — 3-tier: in-scope / out-of-scope / dangerous | Csak aszf_rag-ban (reszleges) | MINDEN chat es AI prompt |
| 2 | **Grounding & Citation** — valasz kizarolag forrasra hivatkozik | Aszf_rag prompt-ban (gyenge) | Erosites + kiterjesztes |
| 3 | **Hallucination Detection** — LLM-as-Judge faithfulness scoring | Van: hallucination_detector prompt | Kalibralas + tobbi skill-re |
| 4 | **Input Sanitization** — prompt injection vedelem | NINCS | UJ: input guardrail layer |
| 5 | **Output Validation** — content safety, PII filter | NINCS | UJ: output guardrail layer |
| 6 | **Metadata Access Control** — kategoria/forras szures | Reszleges (rag_engine) | Kiterjesztes minden service-re |
| 7 | **Golden Dataset Regression** — known-good/known-bad peldak | Promptfoo test case-ek (reszleges) | Guardrail-specifikus test set |
| 8 | **Multi-turn Safety** — tobb koros beszelgetes biztonsaga | NINCS | UJ: conversation context limit |

### 0.5 CI/CD (PR #1 — 4/4 FAIL)

| Workflow | Fo hiba | Fix |
|----------|---------|-----|
| `ci.yml` | `skills/` benne ruff scope-ban | Scope: `src/ tests/` |
| `ci-framework.yml` | Regi venv setup + ruff 574 | `uv sync --dev` |
| `ci-skill.yml` | Skill fuggoseg hianyzik | pyproject.toml extras |

### 0.6 Szolgaltatas Erettseg (26 service, 6 skill)

| Szint | Db | Fo hianyossag |
|-------|----|---------------|
| Production-ready | 3 | Nincs unit test |
| Partial | 20 | Nincs unit test, prompt 80-90%, nincs guardrail |
| Stub | 3 | Nincs valos mukodes |

---

## 1. Sprint Strategia

```
SPRINT A: Infrastruktura, Biztonsag & Guardrail Keretrendszer
  ┌─────────────────────────────────────────────────────────┐
  │ A0: CI/CD Green                                         │
  │ A1: Ruff Cleanup (1,234 → 0)                           │
  │ A2: Halott kod/mappa audit + archivalas                 │
  │ A3: Security Hardening (JWT, CORS, rate limit, session) │
  │ A4: Stub Cleanup + hianyzo alapfunkciok                 │
  │ A5: Prompt Guardrail KERETRENDSZER kialakitasa          │
  │ A6: POST-AUDIT (biztonsag + kod + guardrail)            │
  │ A7: Audit JAVITASOK elvegzese                           │
  │ A8: v1.2.2 tag + merge                                  │
  └─────────────────────────────────────────────────────────┘
  Branch: feature/v1.2.2-infrastructure
  Becsult: ~8 session

SPRINT B: Szolgaltatas Excellence + Guardrail Implementacio
  ┌─────────────────────────────────────────────────────────┐
  │ B0: Hardening keretrendszer + metodologia               │
  │ B1: P0 skill-ek (aszf_rag, email_intent) + guardrail   │
  │ B2: P1 skill-ek (process_docs, invoice, doc_extractor)  │
  │ B3: Infrastructure service tesztek (130 test)           │
  │ B4: P2/P4 skill-ek (cubix, qbpp)                       │
  │ B5: Modell optimalizacio + koltseg csokkentes           │
  │ B6: UI integracio + per-service polish                  │
  │ B7: POST-AUDIT (szolgaltatas erettseg + guardrail)      │
  │ B8: Audit JAVITASOK elvegzese                           │
  │ B9: v1.3.0 tag + merge                                  │
  └─────────────────────────────────────────────────────────┘
  Branch: feature/v1.3.0-service-excellence
  Becsult: ~10 session
```

**Guardrail felosztás logikaja:**
- **Sprint A (A5):** A KERETRENDSZER — middleware, interface, teszt infrastruktura. Ez BIZTONSAG.
- **Sprint B (B1-B4):** A PER-SERVICE IMPLEMENTACIO — minden skill sajat guardrail config-ja. Ez SERVICE.
- Igy a biztonsagi alap Sprint A-ban keszul, de a szolgaltatas-specifikus reszletek Sprint B-ben.

---

# SPRINT A: Infrastruktura, Biztonsag & Guardrail Keretrendszer (v1.2.2)

> **Branch:** `feature/v1.2.2-infrastructure`

## A0: CI/CD Green — 1 session (BLOKKOLO)

> **Gate:** PR #1 MINDEN workflow PASS.

```
A0.1 — ci.yml: ruff scope → `src/ tests/`, venv → `uv sync --dev`
A0.2 — ci-framework.yml: `uv sync --dev`, konzisztens ruff scope
A0.3 — ci-skill.yml: pyproject.toml extras VAGY skill requirements
A0.4 — Push → CI ZOLD

GATE: MINDEN GitHub Actions ZOLD
```

---

## A1: Ruff Cleanup (1,234 → 0) — 1-2 session

> **Gate:** `/lint-check` → 0 error, 0 format diff

```
A1.1 — Safe batch: /lint-check --fix (548 auto-fixable)
  tests/ → src/aiflow/ → skills/ sorrendben
  REGRESSZIO: pytest tests/unit/ -q → PASS

A1.2 — Manual (686 maradt):
  E501 (287) → sorbontas | N806 (149) → per-file-ignores |
  F401 (58) → __all__ vagy noqa | B904 (46) → from e | F841 (24) → torles

A1.3 — pyproject.toml ruff config:
  [tool.ruff.lint.per-file-ignores]
  "skills/**/*.py" = ["N806", "N803"]
  "tests/**/*.py" = ["S101"]

GATE: /lint-check → 0 error
```

---

## A2: Halott Kod & Mappa Audit + Archivalas — 1 session

> **Gate:** Nincs halott kod, nincs felesleges mappa, import integritás OK.
> **UJ FAZIS — az elozo tervben nem volt kulon!**

```
A2.1 — Duplikalt contrib/ modulok TORLES:
  - TOROLNI: src/aiflow/contrib/messaging/ (kafka duplikat)
  - TOROLNI: src/aiflow/contrib/shell/ (tools/ duplikat)
  - TOROLNI: src/aiflow/contrib/human_loop/ (tools/ duplikat)
  - TOROLNI: src/aiflow/contrib/playwright/ (tools/ duplikat)
  - MIGRALAS: cubix_course_capture import → aiflow.tools
  - ELLENORZES: pytest → nincs import hiba

A2.2 — Legacy mappa TORLES:
  - deprecated/aiflow_ui_reflex_legacy/ → DELETE
  - rxconfig.py + reflex.db → DELETE
  - .playwright-mcp/ → DELETE (regeneralodik)
  - output/audio/ → DELETE (test artifact)
  - .coverage → DELETE

A2.3 — Nagy fajlok archivalas:
  - data/uploads/rag/ (~50MB) → .gitignore + README (tartsuk lokalis)
  - e2e-audit/test-data/ (~120MB) → .gitignore + README
  - ELLENORZES: git status → nincs nem kovetett nagy fajl

A2.4 — Import integritás ellenorzes:
  - `python -c "import aiflow"` → nincs ImportError
  - Minden src/aiflow/ __init__.py → helyes import-ok
  - Torolt modulokra hivatkozas → nincs

A2.5 — DEAD_CODE_AUDIT.md dokumentum:
  - Mi lett torolve + miert
  - Mi lett archivalva + hol
  - Megmaradt tudatos backward-compat retegek listaja

GATE: 0 halott fajl, import check PASS, dokumentum kesz
```

---

## A3: Security Hardening — 1-2 session

> **Gate:** Biztonsagi audit 0 HIGH, 0 MEDIUM.

```
A3.1 — JWT atiras PyJWT RS256-ra:
  - security/auth.py: sajat HMAC → PyJWT RS256
  - scripts/generate_jwt_keys.sh → kulcspar
  - Dual-mode: uj RS256 kiad, regi HMAC elfogad (1 verzioig)
  - 5+ unit test

A3.2 — JWT secret enforcement:
  - Prod: KOTELEZ env var (>= 32 char), hiba ha hianyzik
  - Dev: WARNING, alapertelmezett OK

A3.3 — Session lejarat → UI force logout:
  - Backend: 401 ha token lejart
  - Frontend:
    a) fetchApi() interceptor: 401 → redirect /login + toast uzenet
    b) JWT exp mezo decode → setInterval(60s) check
    c) exp < now+5min → WARNING banner ("Session lejár X perc mulva")
    d) exp < now → auto logout (localStorage clear + redirect)
  - ELLENORZES: token lejarat → automatikus kijelentkeztetes

A3.4 — CORS szukites:
  - Explicit methods, headers, origins (env var konfiguralhato)

A3.5 — Rate limiter middleware bekotes:
  - /auth/* = 10/min, /api/* = 100/min
  - 429 + Retry-After header

A3.6 — File upload vedelem:
  - pathlib.resolve() + is_relative_to(), secure_filename(), 50MB limit

A3.7 — Security headers:
  - X-Content-Type-Options, X-Frame-Options, HSTS, CSP

GATE: Biztonsagi audit 0 HIGH, 0 MEDIUM
```

---

## A4: Stub Cleanup + Hianyzo Alapfunkciok — 1 session

> **Gate:** 0 nem-tudatos stub, P1+P2 megoldva, 0 console error (strict).

```
A4.1 — Stub cleanup:
  - Kafka stub TORLES (mar A2-ben a contrib torolve, itt a tools/kafka.py)
  - CLI placeholder: NotImplementedError + "planned for v1.3"
  - Parser stubs: Docling hivatkozas
  - Evaluator placeholder: torles (Promptfoo helyettesiti)
  - Registry konszolidacio: skills/ re-export → skill_system/
  - STUB_INVENTORY.md: megmaradt tudatos stubok

A4.2 — P1: Pipelines templates UI szekció
A4.3 — P2: Templates route conflict fix
A4.4 — DataTable infinite re-render fix (DataTable.tsx:91)
A4.5 — 404 resource loading fix (Monitoring, Costs)
A4.6 — E2E console error filter ELTAVOLITAS (strict 0 filter)

GATE: E2E 102+ PASS (0 filter), stub inventory clean
```

---

## A5: Prompt Guardrail KERETRENDSZER — 1 session

> **Gate:** GuardrailBase + 3 guard implementacio + middleware + 30 test PASS + config sablon.
> **Inspiracio:** `skills/aszf_rag_chat/reference/` (7 fajl, 5000 sor RAG metodologia)

```
A5.1 — Guardrail Architecture Design:
  src/aiflow/guardrails/
    __init__.py
    base.py           # GuardrailBase ABC: check_input(), check_output()
    input_guard.py     # InputGuard: prompt injection, PII, length limit
    output_guard.py    # OutputGuard: content safety, hallucination flag, PII
    scope_guard.py     # ScopeGuard: in-scope / out-of-scope / dangerous
    config.py          # GuardrailConfig: per-service YAML config loader

A5.2 — Input Guardrail Layer:
  class InputGuard(GuardrailBase):
    """User input validacio MIELOTT az LLM-hez jut."""
    - prompt_injection_detect(query) → bool
      * Ismert injection pattern-ek (ignore previous, system:, stb.)
      * Heurisztika: rendkivuli hossz, kulonleges karakterek
    - pii_detect(query) → list[PIIMatch]
      * Email, telefon, adoszam, bankszamla regex
      * Opcio: maszkolás automatikus (user@***.com)
    - length_limit(query, max_tokens=2000) → bool
    - language_check(query, allowed=["hu","en"]) → bool

A5.3 — Output Guardrail Layer:
  class OutputGuard(GuardrailBase):
    """LLM valasz validacio MIELOTT a user-hez jut."""
    - content_safety(response) → SafetyResult
      * Eroszak, serto tartalom, jogserto utasitas detektalas
    - hallucination_flag(response, sources) → float (0-1)
      * Valasz vs. forras kontextus osszevetes (aszf_rag referenciabol)
    - pii_leak_check(response) → list[PIIMatch]
      * LLM veletlenul PII-t ad vissza a training data-bol
    - scope_check(response, allowed_topics) → ScopeResult
      * In-scope / Out-of-scope / Dangerous kategorizalas

A5.4 — Scope Boundary Enforcement (3-tier):
  A referenciaanyag alapjan MINDEN AI valasz 3 kategoriaba esik:
  1. IN-SCOPE → teljes valasz, forras hivatkozassal
  2. OUT-OF-SCOPE → "Nem tudok erre valaszolni" + indoklas
  3. DANGEROUS → rendszer megtagadas + log + alert
  
  Config YAML pelda (skills/aszf_rag_chat/guardrails.yaml):
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

A5.5 — Guardrail Middleware Integration:
  - src/aiflow/api/middleware.py: GuardrailMiddleware hozzaadasa
  - Sorrend: Auth → RateLimit → Guardrail(input) → Handler → Guardrail(output)
  - Config: per-endpoint guardrail config (nem minden endpoint kell)
  - Bypass: /health, /auth/*, /admin/* (nincs LLM-involvement)

A5.6 — Guardrail Test Framework:
  tests/unit/guardrails/
    test_input_guard.py   # 10 test (injection, PII, length)
    test_output_guard.py  # 10 test (safety, hallucination, PII leak)
    test_scope_guard.py   # 10 test (3-tier scope)
  
  Golden dataset template:
  tests/guardrails/golden_dataset.yaml
    - known_safe_inputs: [...]
    - known_injection_attempts: [...]
    - known_dangerous_queries: [...]
    - expected_refusals: [...]

A5.7 — Dokumentacio:
  - README.md a src/aiflow/guardrails/ mappaban (architektura, hasznalat)
  - Per-service config sablon: skills/TEMPLATE/guardrails.yaml
  - Teszt metodologia: tests/unit/guardrails/README.md
  - Scope boundary definiciok: guardrails/config.py docstring

GATE: GuardrailBase + 3 guard impl + middleware + 30 test PASS + config sablon
```

---

## A6: POST-AUDIT — 1 session

> **Gate:** Audit riport MINDEN sor PASS. Ha FAIL → A7 KOTELEZO.

```
A6.1 — Teljes regresszio (L3 szint, ld. regression_matrix.yaml):
  a) pytest tests/unit/ -q --cov=aiflow --cov-report=term → ALL PASS, coverage >= 80%
  b) pytest tests/e2e/ -v → ALL PASS (STRICT 0 filter!)
  c) npx tsc --noEmit → 0 error
  d) /lint-check → 0 error
  e) smoke_test.sh → ALL PASS
  f) Coverage NEM csokkenhet a v1.2.1 szinthez kepest!

A6.2 — Biztonsagi POST-audit:
  | # | Eredeti problema | Javitas | Post-audit |
  |---|-----------------|---------|-----------|
  | 1 | Sajat JWT | PyJWT RS256 | [ ] VERIFIED |
  | 2 | Default secret | Prod enforce | [ ] VERIFIED |
  | 3 | Session lejarat | UI force logout | [ ] VERIFIED |
  | 4 | CORS * | Explicit lista | [ ] VERIFIED |
  | 5 | Rate limit | Middleware | [ ] VERIFIED |
  | 6 | File upload | Path traversal fix | [ ] VERIFIED |
  | 7 | Security headers | CSP + HSTS | [ ] VERIFIED |

A6.3 — Halott kod POST-audit:
  - contrib/ modul tenyleg torolve? Import check PASS?
  - Legacy mappak torolve?
  - .gitignore frissitve nagy fajlokra?

A6.4 — Guardrail POST-audit:
  - InputGuard: 5 injection attempt → MIND BLOKKOLT?
  - OutputGuard: hallucination test → helyes scoring?
  - ScopeGuard: dangerous query → MEGTAGADVA?
  - Config sablon: YAML load → hibatlan?

A6.5 — Stub POST-audit:
  - grep "placeholder|stub" → csak STUB_INVENTORY.md-ben levo
  
A6.6 — Audit riport generalas:
  === SPRINT A POST-AUDIT RIPORT ===
  Biztonsag:     X/7 VERIFIED → [PASS/FAIL]
  Halott kod:    X/5 check PASS → [PASS/FAIL]
  Guardrail:     X/4 check PASS → [PASS/FAIL]
  Ruff:          0 error → [PASS/FAIL]
  CI/CD:         4/4 ZOLD → [PASS/FAIL]
  Stubs:         inventory clean → [PASS/FAIL]
  E2E:           102+ PASS (strict) → [PASS/FAIL]
  Unit:          1083+ PASS → [PASS/FAIL]
  
  VERDICT: [PASS] / [FAIL — open items listaja]

GATE: MINDEN sor PASS. Ha FAIL → A7 KOTELEZO.
```

---

## A7: Audit Javitasok — 0.5-1 session

> **Gate:** Frissitett audit riport MINDEN sor PASS. (Ha A6 MIND PASS → A7 SKIP.)

```
A7.1 — A6 riport FAIL teteleinek javitasa:
  - Minden OPEN item → konkret fix
  - Minden fix → ujra-teszt (NEM teljes regresszio, csak az erintett resz)

A7.2 — Ujra-audit (csak a FAIL tetelek):
  - VERIFIED ← TILOS tovabblepni ha meg mindig OPEN

A7.3 — Frissitett audit riport:
  - MINDEN sor PASS

GATE: Frissitett riport MINDEN PASS
```

---

## A8: v1.2.2 Tag + Merge — fél session

> **Gate:** v1.2.2 tag letrehozva, main-re merge-olve, CI ZOLD.

```
A8.1 — pyproject.toml: version = "1.2.2"
A8.2 — git tag v1.2.2
A8.3 — 58_POST_SPRINT_HARDENING_PLAN.md: Sprint A = DONE
A8.4 — CLAUDE.md szamok frissitese
A8.5 — Push tag + merge to main

GATE: v1.2.2 tag pushed, main-en CI ZOLD
```

---

## Sprint A Utemterv

```
Session 15: A0 (CI/CD Green) ──────────── BLOKKOLO
Session 16: A1 (Ruff batch + manual) ──── 1,234 → 0
Session 17: A2 (Halott kod audit) ─────── Torles + archivalas
Session 18: A3 (Security + JWT session) ── JWT RS256 + force logout
Session 19: A4 (Stubs + alapfunkciok) ──── P1, P2, DataTable
Session 20: A5 (Guardrail keretrendszer) ── InputGuard + OutputGuard + ScopeGuard
Session 21: A6 (POST-AUDIT) ───────────── Teljes ellenorzes
Session 22: A7+A8 (Javitasok + tag) ───── Fix + v1.2.2
```

---

# SPRINT B: Szolgaltatas Excellence + Guardrail Implementacio (v1.3.0)

> **Branch:** `feature/v1.3.0-service-excellence`
> **Elofeltetel:** Sprint A COMPLETE (v1.2.2), guardrail keretrendszer KESZ

## B0: Keretrendszer, Metodologia & Integralt Toolchain — 1 session

> **Gate:** 10-pontos checklist + integralt toolchain + prompt metodologia + guardrail sablon + 2 uj slash command KESZ.

```
B0.1 — 10 Pontos Production Checklist (minden szolgaltatasra):
  [ ]  1. UNIT TESZT      — >= 5 teszt, >= 70% coverage
  [ ]  2. INTEGRACIO       — >= 1 valos DB-vel (ha DB-t hasznal)
  [ ]  3. API TESZT        — minden endpoint curl, source=backend
  [ ]  4. PROMPT TESZT     — promptfoo >= 95% pass (ha LLM-et hasznal)
  [ ]  5. ERROR HANDLING   — AIFlowError leszarmazott, is_transient flag
  [ ]  6. LOGGING          — structlog, NEM print(), event+key=value
  [ ]  7. DOKUMENTACIO     — docstring fo osztaly + publikus metodus
  [ ]  8. UI               — oldal mukodik, source badge, 0 console error
  [ ]  9. INPUT GUARDRAIL  — injection vedelem, PII, length limit (A5 FW)
  [ ] 10. OUTPUT GUARDRAIL — hallucination, scope, PII leak check (A5 FW)

B0.2 — Integralt Toolchain (Langfuse + Promptfoo + Claude Code):

  A 3 eszkoz NEM kulon-kulon, hanem KOORDINALTAN mukodik — minden
  szolgaltatas finomhangolasa soran az alabbi ciklust kovetjuk:

  LANGFUSE (megfigyeles) → PROMPTFOO (teszteles) → CLAUDE CODE (vegrehajtas)
  ───────────────────────────────────────────────────────────────────────────
  
  1. LANGFUSE — Megfigyeles & Baseline:
     - Production trace-ek elemzese: mely promptok lassuk/dragak/pontatlanok?
     - Cost dashboard: per-service koltseg, token hasznalat
     - Minosegi scoring: user feedback + automatikus faithfulness score
     - OUTPUT: baseline riport (koltseg, latency, minoseg metrikai)
  
  2. PROMPTFOO — Szisztematikus Teszteles & A/B:
     - Baseline eval: npx promptfoo eval → jelenlegi pass rate rogzites
     - FAIL analiz: mely test case-ek buknak? root cause azonositas
     - A/B kiserlet: promptfoo --providers gpt-4o,gpt-4o-mini → modell osszehasonlitas
     - Guardrail teszt: golden dataset (safe/dangerous/injection) → 100% PASS?
     - Regresszio: minden prompt modositas utan UJRA eval → nem romlott?
     - OUTPUT: eval riport (pass rate, regresszio, A/B eredmenyek)
  
  3. CLAUDE CODE — Vegrehajtas & Orchestracio:
     - /quality-check: Promptfoo eval + Langfuse koltseg elemzes egyutt
     - /service-test: Backend + API + UI e2e (valos adat!)
     - /prompt-tuning (UJ): prompt YAML modositas + eval + guardrail illesztes
     - /service-hardening (UJ): teljes 10-pontos checklist vegrehajtasa
     - /dev-step: fejlesztes + teszt + commit (a ciklus lezarasa)
     - OUTPUT: commit, frissitett tesztek, dokumentacio
  
  4. UI INTEGRACIO — Vizualizacio & Visszajelzes:
     - Quality dashboard: Langfuse trace-ek + Promptfoo eredmenyek megjelenitese
     - Cost dashboard: per-service koltseg trendek (Langfuse adatbol)
     - Service Catalog: szolgaltatas allapot (10-pontos checklist vizualis)
     - Notification: minoseg romlasrol automatikus alert (Langfuse webhook)

  KOORDINACIOS CIKLUS (minden szolgaltatasra):
  ┌──────────────────────────────────────────────────────────┐
  │ 1. Langfuse: baseline meres (trace, cost, quality)       │
  │ 2. Promptfoo: eval → FAIL tetelek azonositasa            │
  │ 3. Claude Code: /prompt-tuning → prompt YAML javitas     │
  │ 4. Promptfoo: ujra eval → 95%+?                          │
  │    ├── IGEN → 5. Guardrail config illesztes               │
  │    └── NEM → vissza 3. (max 3 iteracio, utana modell csere)│
  │ 5. Langfuse: uj trace-ek → javult a minoseg/koltseg?     │
  │ 6. UI: dashboard frissites, quality metrikak              │
  │ 7. Claude Code: /dev-step → commit + dokumentacio         │
  └──────────────────────────────────────────────────────────┘

B0.3 — Prompt Finomhangolas Metodologia:
  A B0.2 toolchain-re epitett 6 lepesu ciklus:
  MERES → DIAGNOZIS → JAVITAS → VALIDALAS → GUARDRAIL → DOKUMENTALAS
  1. MERES: Langfuse baseline + npx promptfoo eval → pass rate rogzites
  2. DIAGNOZIS: Langfuse trace-ekbol gyenge pontok + Promptfoo FAIL elemzes
  3. JAVITAS: prompt YAML modositas (/prompt-tuning command)
  4. VALIDALAS: promptfoo eval → 95%+? (ha NEM → ujra 2-3, max 3 iteracio)
  5. GUARDRAIL: guardrails.yaml config illesztes (A5 sablon alapjan)
  6. DOKUMENTALAS: CHANGELOG + Langfuse annotacio + UI dashboard frissites

B0.4 — Prompt Guardrail Implementacios Sablon (per skill):
  skills/{skill_name}/
    guardrails.yaml              # UJ: skill-specifikus guardrail config
    tests/test_guardrails.py     # UJ: 5+ guardrail teszt per skill
    tests/golden_guardrails.yaml # UJ: known-safe + known-dangerous peldak

B0.5 — Uj Slash Command-ok letrehozasa:
  .claude/commands/service-hardening.md (UJ):
    - Input: service nev
    - Vegrehajtas: 10-pontos checklist egyenkenti ellenorzese
    - Output: PASS/FAIL tabla, hianyzo pontok listaja
    - Eszkozok: pytest, curl, promptfoo, /lint-check, Playwright

  .claude/commands/prompt-tuning.md (UJ):
    - Input: skill nev
    - Vegrehajtas: B0.2 koordinacios ciklus (Langfuse → Promptfoo → fix → eval)
    - Output: prompt YAML diff, eval riport, guardrail config
    - Eszkozok: npx promptfoo eval, Langfuse API, ruff check

B0.6 — Operacionalizacios Artefaktumok:
  A metodologia ujrahasznalhato formaba hozasa:
  
  a) Reference Guide (01_PLAN/60_SERVICE_HARDENING_GUIDE.md):
     - Lepes-lepesu guide uj szolgaltatas magas szintre hozasahoz
     - Integralt toolchain hasznalati utmutato (Langfuse + Promptfoo + Claude)
     - 10-pontos checklist reszletes magyarazattal
     - Guardrail config sablon + peldak minden skill tipusra (ai, rpa, hybrid)
     - Prompt tuning best practices (az aszf_rag_chat/reference/ anyagbol)
     - Troubleshooting: gyakori hibak es megoldasok
  
  b) Claude Code Skill-ek:
     - /service-hardening command (B0.5)
     - /prompt-tuning command (B0.5)
     - Meglevo command-ok frissitese: /quality-check bovites Langfuse linkkel
  
  c) Template fajlok:
     - skills/TEMPLATE/ mappa: ures skill scaffold guardrail-lal
     - prompts/TEMPLATE/: prompt YAML sablon + promptfoo config sablon
     - tests/TEMPLATE/: test file sablon @test_registry header-rel
  
  d) Quality Dashboard bovites (B6-ban):
     - Service Catalog: 10-pontos checklist vizualis (per service zold/piros)
     - Prompt Eval: Promptfoo eredmenyek inline (utolso eval pass rate)
     - Cost Trend: Langfuse koltseg trend chart (utolso 30 nap)

GATE: Checklist + toolchain dok + 2 uj command + reference guide vaz + sablon
```

---

## B1: P0 Core AI Skill-ek + Guardrail — 2-3 session

> **Gate:** aszf_rag 95%+ promptfoo, email_intent 95%+ promptfoo, mindketto guardrails.yaml KESZ.
> **Eszkozok:** B0.2 integralt toolchain — Langfuse baseline → Promptfoo eval → /prompt-tuning → /service-hardening

```
B1.0 — Elokeszites (mindket skill-re):
  - Langfuse: baseline trace export (jelenlegi cost, latency, quality)
  - Promptfoo: npx promptfoo eval → jelenlegi pass rate rogzites
  - /service-hardening aszf_rag_chat → 10-pontos checklist audit
  - /service-hardening email_intent_processor → 10-pontos checklist audit
  - OUTPUT: ket baseline riport, hianyzo pontok listaja

B1.1 — aszf_rag_chat (RAG Chat — legkritikusabb):

  KOD:
    - rag_engine: connection pooling + query timeout
    - vector_ops: BM25 + HNSW parameter tuning
    - reranker: BGE v2-m3 validalas
    - 15 unit test (rag_engine + vector_ops + reranker)

  PROMPT (86% → 95%):
    - answer_generator: citation enforcement ("EVERY claim MUST include [Source:]")
    - hallucination_detector: scoring kalibralas (threshold 0.7 → 0.6)
    - query_rewriter: magyar → angol concept mapping
    - 7 → 12 test case (jogi, osszetetett, "nem tudom", hallucinacio)

  GUARDRAIL (aszf_rag_chat/guardrails.yaml):
    scope:
      allowed_topics: ["jog", "biztositas", "aszf", "szolgaltatas", "kar"]
      blocked_topics: ["politika", "orvosi", "befektetesi"]
      dangerous_patterns: ["torvenyt kijatszani", "hogyan csaljak"]
    input: max_length 2000, injection_patterns skill-specifikus, pii_masking true
    output: require_citation true, hallucination_threshold 0.7, max_response 4000
    golden_dataset: 4+ pelda (safe, out_of_scope, dangerous, injection)
    5 guardrail teszt

  MODELL:
    - Kiserlet: answer gpt-4o → gpt-4o-mini (< 3% esés elfogadva)

  CHECKLIST: [ ]1 [ ]2 [ ]3 [ ]4 [ ]5 [ ]6 [ ]7 [ ]8 [ ]9 [ ]10

B1.2 — email_intent_processor (P0):

  KOD:
    - Intent catalog bovites (8 → 12 tipus)
    - Entity: magyar adoszam, bankszamla, cim regex + LLM
    - 10 unit test (email_connector + classifier)

  PROMPT (85% → 95%):
    - intent_classifier: 4 uj intent tipus
    - entity_extractor: HU-specifikus entitasok
    - priority_scorer: kontextus-alapu sulyossag
    - 11 → 16 test case

  GUARDRAIL (email_intent_processor/guardrails.yaml):
    scope:
      allowed: ["ugyfelsz", "szamla", "szerzodes", "panasz", "informacio"]
      blocked: ["spam_forward", "phishing_content"]
    input: max_email_size 50000, attachment_scan true, pii_masking false
    output: require_confidence 0.7, max_intents_per_email 3
    5 guardrail teszt

  CHECKLIST: [ ]1 [ ]2 [ ]3 [ ]4 [ ]5 [ ]6 [ ]7 [ ]8 [ ]9 [ ]10

GATE: aszf_rag 95%+, email_intent 95%+, 2 guardrails.yaml KESZ, 25 unit test PASS
```

---

## B2: P1 Document & Diagram Skill-ek — 1-2 session

> **Gate:** process_docs 95%+, invoice 95%+, doc_extractor 5 unit test PASS.
> **Eszkozok:** B0.2 integralt toolchain — /prompt-tuning + /service-hardening

```
B2.1 — process_documentation:

  KOD:
    - Diagram generator: Mermaid → BPMN XML export javitas
    - 5 unit test (diagram_generator service)

  PROMPT (90% → 95%):
    - mermaid_flowchart: komplex folyamatok (10+ lepes)
    - elaborator: strukturalt output (heading hierarchy)
    - 11 → 15 test case

  GUARDRAIL (process_documentation/guardrails.yaml):
    scope: technikai dokumentacio only
    output: Mermaid szintaxis validacio, max diagram meret
    3 guardrail teszt

  CHECKLIST: [ ]1 [ ]2 [ ]3 [ ]4 [ ]5 [ ]6 [ ]7 [ ]8 [ ]9 [ ]10

B2.2 — invoice_processor:

  KOD:
    - PDF extraction: Docling config finomhangolas
    - Multi-page szamla osszefuzes
    - 5 unit test (document_extractor — invoice kontextus)

  PROMPT (80% → 95%):
    - field_extractor: HU adoszam, AFO szam, AFA kulcsok (5%, 18%, 27%)
    - invoice_classifier: szamla vs. nem-szamla precision
    - 10 → 15 test case (scan, kezi, kulfoldi, tobboldal)

  GUARDRAIL (invoice_processor/guardrails.yaml):
    input: max file size, supported formats only (PDF/DOCX/XLSX)
    output: szamla mezok validacio (osszeg > 0, datum format)
    3 guardrail teszt

  CHECKLIST: [ ]1 [ ]2 [ ]3 [ ]4 [ ]5 [ ]6 [ ]7 [ ]8 [ ]9 [ ]10

B2.3 — document_extractor service:

  KOD:
    - Docling config: table extraction, heading detection
    - Multi-format: PDF + DOCX + XLSX + HTML
    - Error recovery: parser fallback chain
    - 5 unit test

  CHECKLIST: [ ]1 [ ]2 [ ]3 [ ]5 [ ]6 [ ]7 [ ]8

GATE: process_docs 95%+, invoice 95%+, 15 unit test PASS, 6 guardrail teszt PASS
```

---

## B3: Infrastructure Service Tesztek — 2 session

> **Gate:** 130 uj unit test PASS, coverage >= 70% services/ modulon.

```
B3.1 — Session 1: Core infra (13 service, 65 test):
  1. cache (5)           — Redis hit/miss/evict/TTL/pattern
  2. config (5)          — versioning CRUD, default fallback
  3. health_monitor (5)  — service status, dependency check
  4. audit (5)           — log create/query/filter/retention
  5. schema_registry (5) — JSON schema CRUD/validate
  6. notification (5)    — email template, delivery retry
  7. human_review (5)    — HITL workflow, SLA timer
  8. media_processor (5) — ffmpeg probe, format detect
  9. diagram_generator (5) — Mermaid render, BPMN export
  10. rpa_browser (5)    — page navigate, screenshot
  11. rate_limiter (5)   — bucket fill/drain, 429 trigger
  12. resilience (5)     — circuit open/half-open/close, retry
  13. classifier (5)     — ML predict, confidence threshold
  ELLENORZES: pytest tests/unit/services/ -q → 65 PASS

B3.2 — Session 2: v1.2.0 szolgaltatasok (13 service, 65 test):
  14. data_router (5)        — routing rules, priority
  15. service_manager (5)    — lifecycle, health
  16. reranker (5)           — score, sort, top-K
  17. advanced_chunker (5)   — 6 strategia (fixed/semantic/sentence/paragraph/recursive/sliding)
  18. data_cleaner (5)       — normalize, deduplicate
  19. metadata_enricher (5)  — auto-tag, entity link
  20. vector_ops (5)         — insert/search/delete/similarity
  21. advanced_parser (5)    — multi-format, fallback chain
  22. graph_rag (5)          — entity graph, traversal query
  23. quality (5)            — metric collect, threshold alert
  24. email_connector (5)    — IMAP connect, fetch, filter
  25. rag_engine (5)         — ingest, query, hybrid search
  26. extra coverage (5)     — legalacsonyabb coverage service potlas
  ELLENORZES: pytest tests/unit/services/ -q → 130 PASS, coverage >= 70%

GATE: 130/130 PASS, coverage >= 70%
```

---

## B4: P2/P4 Skill-ek — 1 session

> **Gate:** cubix 95%+ promptfoo, qbpp dontes meghozva es vegrehajva.

```
B4.1 — cubix_course_capture (P2, 90% → 95%):
  - transcript_structurer: idokod pontossag javitas
  - 5 → 8 test case (rovid video, rossz hang, angol nyelvu)
  - guardrails.yaml: input max_audio_length, output format check
  - 2 guardrail teszt
  ELLENORZES: promptfoo eval → 95%+

B4.2 — qbpp_test_automation (P4):
  DONTES SZUKSEGES: implementaljuk VAGY toroljuk?
  HA IGEN:
    - __main__.py implementacio (Robot Framework integracio)
    - test_generator.yaml (UJ prompt): RF teszt generalas
    - locator_finder.yaml (UJ prompt): UI elem azonosito
    - Promptfoo: valos test case-ek (nem stub), cel: 90%+
    - guardrails.yaml: output Robot Framework szintaxis validacio
  HA NEM:
    - Skill mappa torles, CLAUDE.md frissites (5 skill)
  ELLENORZES: dontes dokumentalva, ha impl → promptfoo PASS

GATE: cubix 95%+, qbpp dontes + vegrehajtva
```

---

## B5: Modell Optimalizacio — 1 session

> **Gate:** >= 20% koltseg csokkenés VAGY >= 5% minoseg javulas.

```
B5.1 — Koltseg baseline meres:
  - Langfuse cost dashboard → per-service koltseg export
  - Token count: prompt_tokens + completion_tokens per call

B5.2 — Modell csere kiserlet:
  | Prompt | Jelenlegi | Kiserlet | Elfogadasi kriterium |
  |--------|-----------|----------|---------------------|
  | pd/reviewer | gpt-4o | gpt-4o-mini | < 3% esés |
  | pd/elaborator | gpt-4o | gpt-4o-mini | < 3% esés |
  | rag/answer | gpt-4o | gpt-4o-mini | < 3% esés |
  | invoice/extract | gpt-4o | gpt-4o-mini | < 3% esés |
  Metodologia: promptfoo --providers gpt-4o,gpt-4o-mini → A/B osszehasonlitas

B5.3 — Token optimalizacio:
  - Hosszu system prompt: felesleges ismetles torles
  - Few-shot: 6 → 3 (ha minoseg megmarad)
  - Cel: >= 15% token count csokkenés

B5.4 — Cache strategia:
  - Embedding cache: Redis TTL=1h (ismetlodo query)
  - Classifier cache: confidence > 0.95 → cache (TTL=24h)
  - Cel: cache hit rate >= 30%

B5.5 — Koltseg riport generalas:
  - Per-skill koltseg/query
  - Havi becslés (1000 query/nap)
  - Optimalizalt vs. eredeti osszehasonlitas

GATE: >= 20% koltseg csokkenés VAGY >= 5% minoseg javulas, riport kesz
```

---

## B6: UI Integracio + Polish — 1 session

> **Gate:** 0 demo-only oldal, minden source=backend, 0 console error.

```
B6.1 — 17 oldal source audit:
  MINDEN oldal ellenorzese:
  | Oldal | Backend source | Valos adat | Console error |
  |-------|---------------|-----------|--------------|
  | Dashboard | ? | ? | ? |
  | Documents | ? | ? | ? |
  | ... (mind a 17) | | | |
  Demo → Backend migracio ahol szukseges

B6.2 — Uj UI elemek (ha szukseges):
  - Intent schema CRUD form (/intent-schemas → UI)
  - Collection management (create/delete/stats)
  - Cost dashboard bovites (B5 koltseg riport alapjan)

B6.3 — Dark mode + responsive check:
  - Minden oldal: dark mode WCAG AA kontraszt
  - Mobile: 768px breakpoint-on olvashato

B6.4 — E2E teszt frissites:
  - Uj oldalak/funkciok → uj E2E test case-ek
  - Regresszio: 102+ teszt → PASS

GATE: 0 demo oldal, 0 console error, E2E PASS
```

---

## B7: POST-AUDIT — 1 session

> **Gate:** Audit riport MINDEN sor PASS. Ha FAIL → B8 KOTELEZO.

```
B7.1 — Teljes regresszio (L3 szint, ld. regression_matrix.yaml):
  a) pytest tests/unit/ -q --cov=aiflow → ALL PASS, coverage >= 80%
  b) pytest tests/e2e/ -v → ALL PASS (strict 0 filter)
  c) tsc --noEmit → 0, /lint-check → 0
  d) npx promptfoo eval → 6/6 skill 95%+
  e) Coverage NEM csokkenhet a v1.2.2 szinthez kepest!

B7.2 — Szolgaltatas erettseg POST-audit:
  | Szolgaltatas | Checklist 10pt | Promptfoo | Guardrail | Status |
  |-------------|---------------|-----------|-----------|--------|
  | aszf_rag | ?/10 | ?% | ? config | ? |
  | email_intent | ?/10 | ?% | ? config | ? |
  | process_docs | ?/10 | ?% | ? config | ? |
  | invoice | ?/10 | ?% | ? config | ? |
  | cubix | ?/10 | ?% | ? config | ? |
  | qbpp | ?/10 | ?% | ? config | ? |

B7.3 — Guardrail POST-audit:
  - MINDEN skill guardrails.yaml → helyes schema?
  - Golden dataset → MINDEN dangerous query BLOKKOLT?
  - Injection test → MIND DETEKTALT?
  - PII leak test → 0 leak?

B7.4 — Koltseg POST-audit:
  - Langfuse: >= 20% csokkenés teljesult?

B7.5 — Audit riport:
  === SPRINT B POST-AUDIT RIPORT ===
  Service tesztek:     130/130 PASS       → [PASS/FAIL]
  Prompt minoseg:      6/6 skill 95%+     → [PASS/FAIL]
  Guardrail coverage:  6/6 skill config   → [PASS/FAIL]
  Guardrail safety:    golden dataset 100% → [PASS/FAIL]
  Koltseg:             X% csokkenés       → [PASS/FAIL]
  E2E (strict):        102+ PASS          → [PASS/FAIL]
  Unit:                1213+ PASS         → [PASS/FAIL]
  
  VERDICT: [PASS] / [FAIL — open items listaja]

GATE: MINDEN sor PASS. Ha FAIL → B8 KOTELEZO.
```

---

## B8: Audit Javitasok — 0.5-1 session

> **Gate:** Frissitett audit riport MINDEN sor PASS. (Ha B7 MIND PASS → B8 SKIP.)

```
B8.1 — B7 riport FAIL teteleinek javitasa:
  - Minden OPEN item → konkret fix
  - Minden fix → ujra-teszt (csak az erintett resz)

B8.2 — Ujra-audit (csak a FAIL tetelek):
  - VERIFIED ← TILOS tovabblepni ha meg mindig OPEN

B8.3 — Frissitett audit riport:
  - MINDEN sor PASS

GATE: Frissitett riport MINDEN PASS
```

---

## B9: v1.3.0 Tag + Merge — fél session

> **Gate:** v1.3.0 tag letrehozva, main-re merge-olve.

```
B9.1 — pyproject.toml: version = "1.3.0"
B9.2 — git tag v1.3.0
B9.3 — 58_POST_SPRINT_HARDENING_PLAN.md: Sprint B = DONE
B9.4 — CLAUDE.md + 01_PLAN/CLAUDE.md: vegleges szamok frissites
B9.5 — Merge to main (squash, clean history)

GATE: v1.3.0 tag pushed, main-en CI ZOLD
```

---

## Sprint B Utemterv

```
Session 23: B0 (Toolchain + metodologia + 2 uj command + reference guide)
Session 24: B1 start (aszf_rag baseline + prompt tuning + guardrail)
Session 25: B1 (aszf_rag kod+teszt) + B1.2 (email_intent prompt+guardrail)
Session 26: B1.2 (email kod+teszt) + B2.1 (process_docs)
Session 27: B2.2 (invoice) + B2.3 (doc_extractor)
Session 28: B3.1 (Core infra tesztek — 65 test)
Session 29: B3.2 (v1.2.0 tesztek — 65 test)
Session 30: B4 (cubix+qbpp) + B5 (model opt)
Session 31: B6 (UI integracio + quality dashboard)
Session 32: B7 (POST-AUDIT)
Session 32: B8+B9 (Javitasok + v1.3.0)
```

---

# Osszesites

> Az alabbi szekciok MINDKET sprintre vonatkoznak.

## Teljes Utemterv (Sprint A + B)

```
=== SPRINT A: Infrastruktura & Biztonsag (v1.2.2) ===
S15: A0 — CI/CD Green ─────────────── BLOKKOLO
S16: A1 — Ruff 1,234 → 0 ─────────── /lint-check --fix
S17: A2 — Halott kod audit+archiv ─── Torles + dokumentum
S18: A3 — Security + JWT session ──── RS256 + force logout
S19: A4 — Stubs + alapfunkciok ────── P1, P2, DataTable
S20: A5 — Guardrail keretrendszer ─── InputGuard + OutputGuard + ScopeGuard
S21: A6 — POST-AUDIT ──────────────── Teljes ellenorzes
S22: A7+A8 — Javitasok + v1.2.2 ──── Fix + tag

=== SPRINT B: Szolgaltatas Excellence (v1.3.0) ===
S23: B0 — Toolchain + metodologia + reference guide + 2 command
S24: B1 — aszf_rag baseline + prompt tuning + guardrail
S25: B1 — aszf_rag kod + email_intent prompt+guardrail
S26: B1+B2 — email kod + process_docs
S27: B2 — invoice + doc_extractor
S28: B3.1 — Core infra tesztek (65)
S29: B3.2 — v1.2.0 tesztek (65)
S30: B4+B5 — cubix + model optimization
S31: B6 — UI integracio + quality dashboard
S32: B7 — POST-AUDIT
S33: B8+B9 — Javitasok + v1.3.0
```

**Osszes:** ~19 session, ~5,500 LOC, ~280 uj teszt, 2 version tag, guardrail + toolchain

---

## Sikerkriteriumok

### Sprint A (v1.2.2)

| # | Kriterium | Mertek |
|---|-----------|--------|
| 1 | CI/CD MIND ZOLD | 4/4 workflow PASS |
| 2 | Ruff 0 error | `/lint-check` → CLEAN |
| 3 | 0 halott kod/mappa | Dokumentalt inventory |
| 4 | 0 HIGH/MEDIUM security | Post-audit verified |
| 5 | JWT session lejarat | UI force logout mukodik |
| 6 | Guardrail keretrendszer | 3 guard + 30 test PASS |
| 7 | 0 console error | Strict E2E (0 filter) |
| 8 | Post-audit riport | MINDEN sor PASS |

### Sprint B (v1.3.0)

| # | Kriterium | Mertek |
|---|-----------|--------|
| 1 | Integralt toolchain | Langfuse+Promptfoo+Claude Code koordinalt |
| 2 | Service unit test | 130+ PASS |
| 3 | Prompt minoseg | 6/6 skill 95%+ promptfoo |
| 4 | Guardrail config | 6/6 skill guardrails.yaml + golden dataset |
| 5 | Guardrail safety | 100% dangerous query blokkolt |
| 6 | Koltseg csokkentes | >= 20% Langfuse riportbol |
| 7 | Production checklist | 10/10 PASS per skill |
| 8 | Operacionalizacio | Reference guide + 2 command + template-ek |
| 9 | Post-audit riport | MINDEN sor PASS |
| 10 | Version tag | v1.3.0 tag, main ZOLD |

---

## Slash Command Referencia

| Command | Hasznalat | Sprint |
|---------|-----------|--------|
| `/lint-check` | Ruff + tsc + format osszesito | A1, minden fazis vegen |
| `/lint-check --fix` | Auto-fix safe issues | A1.1 |
| `/regression` | Unit + E2E regresszio | A6, B7, commit elott |
| `/quality-check` | Promptfoo + Langfuse koltseg elemzes | B1-B5 |
| `/service-test` | Backend + API + UI e2e | B1-B4 |
| `/service-hardening` | 10-pontos checklist audit (UJ, B0) | B1-B4 |
| `/prompt-tuning` | Langfuse→Promptfoo→fix ciklus (UJ, B0) | B1-B4 |
| `/dev-step` | Fejlesztes + teszt + commit | Minden fazis |

---

## Progress Tracking

### Sprint A (v1.2.2)

| Fazis | Tartalom | Allapot | Datum | Commit |
|-------|----------|---------|-------|--------|
| A0 | CI/CD Green | DONE | 2026-04-04 | 27e9c82 |
| A1 | Ruff 1,234 → 0 | DONE | 2026-04-04 | a32a84d |
| A2 | Halott kod audit + archivalas | DONE | 2026-04-04 | 2c0e078 |
| A3 | Security + JWT session | DONE | 2026-04-04 | 176f137 |
| A4 | Stubs + alapfunkciok | TODO | — | — |
| A5 | Guardrail keretrendszer | TODO | — | — |
| A6 | POST-AUDIT | TODO | — | — |
| A7 | Audit javitasok | TODO | — | — |
| A8 | v1.2.2 tag | TODO | — | — |

### Sprint B (v1.3.0)

| Fazis | Tartalom | Allapot | Datum | Commit |
|-------|----------|---------|-------|--------|
| B0 | Keretrendszer + metodologia | TODO | — | — |
| B1 | P0 skill-ek + guardrail | TODO | — | — |
| B2 | P1 skill-ek + guardrail | TODO | — | — |
| B3 | Infrastructure tesztek (130) | TODO | — | — |
| B4 | P2/P4 skill-ek | TODO | — | — |
| B5 | Modell optimalizacio | TODO | — | — |
| B6 | UI integracio | TODO | — | — |
| B7 | POST-AUDIT | TODO | — | — |
| B8 | Audit javitasok | TODO | — | — |
| B9 | v1.3.0 tag | TODO | — | — |
