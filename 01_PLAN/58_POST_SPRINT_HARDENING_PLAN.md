# AIFlow v1.2.2 + v1.3.0 — Hardening & Service Excellence Plan

> **Szulo terv:** `57_PRODUCTION_READY_SPRINT.md` (v1.2.1 COMPLETE)
> **Elozmeny:** v1.2.1 COMPLETE (S1-S14, 2026-04-04) — UI, observability, quality, 102 E2E
> **Cel:** Ket sprint: (A) infrastruktura+biztonsag+halott kod+guardrail keretrendszer, (B) szolgaltatas excellence+prompt guardrail implementacio
> **Becsult idotartam:** Sprint A ~8 session, Sprint B ~10 session
> **Infrastruktura:** 26 service, 158 endpoint (24 router), 45 DB tabla, 29 migracio, 19 adapter
> **Sprint A: COMPLETE** (A0-A8 DONE, v1.2.2, 2026-04-05) — CI, ruff, dead code, security, stubs, guardrails, audit

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
  │ B1: P0 skill-ek + LLM guardrail promptok (4 prompt)     │
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

**Guardrail felosztás logikaja (3 reteg):**
- **Sprint A (A5):** RULE-BASED KERETRENDSZER — regex/heurisztika (injection 14 pattern, PII 7 tipus HU+US, SequenceMatcher hallucination, keyword scope). KESZ: `src/aiflow/guardrails/`, 76 teszt.
- **Sprint B (B1):** LLM-BASED GUARDRAIL PROMPTOK — a rule-based reteg FELETT, 4 prompt YAML:
  1. `hallucination_evaluator` — forras vs. valasz grounding (A5 SequenceMatcher csereje)
  2. `content_safety_classifier` — safety scoring (A5 4 regex csereje)
  3. `scope_classifier` — 3-tier scope (A5 keyword matching csereje)
  4. `freetext_pii_detector` — szabad szoveges PII ("Kiss Janos", "a szomszed") — regex NEM tudja
- **Sprint B (B1-B4):** PER-SERVICE IMPLEMENTACIO — minden skill sajat guardrails.yaml config-ja.
- Igy: A5 = gyors, olcso, determinisztikus elso szuro | B1 = LLM precizitas | B1-B4 = skill-specifikus config.

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

# SPRINT B: E2E Szolgaltatas Excellence (v1.3.0)

> **Branch:** `feature/v1.3.0-service-excellence`
> **Elofeltetel:** Sprint A COMPLETE (v1.2.2), guardrail keretrendszer KESZ
> **Fo elv:** Minden alapozo funkcio → valos E2E AIFlow-val validalva. NEM tervezunk, EPITUNK.
> **Becsult:** ~16 session (S19-S34)
>
> ## ARCHITEKTURA — KULCSFONTOSSAGU MEGKULONBOZTETES
>
> ```
> ┌────────────────────────────────────────────────────────────┐
> │ FEJLESZTESI IDO (Claude Code tamogatja)                   │
> │                                                            │
> │ Tervezes → Fejlesztes → TESZTELES → Karbantartas → Debug  │
> │ Claude: /dev-step, /regression, /service-test, /new-skill │
> │                                                            │
> │ Claude Code SZEREPE:                                       │
> │   - Tervezi es fejleszti a keretrendszert                 │
> │   - Fejleszti a service-eket es pipeline-okat             │
> │   - TESZTELI (unit, integration, E2E, prompt, Playwright) │
> │   - Karbantartja, hibaelharitja                            │
> │   - Specifikaciot ir, dokumental                           │
> │                                                            │
> │ Claude Code NEM futtatja uzemszerun az AIFlow-kat!        │
> └──────────────┬───────────────────────────────────────────┘
>                │ deploy (Docker)
>                ▼
> ┌────────────────────────────────────────────────────────────┐
> │ UZEMELTETESI IDO (Docker containers, ugyfél-ready)        │
> │ Claude Code NEM SZUKSEGES — minden ONALLOAN fut!          │
> │                                                            │
> │ ┌──────────────────────────────────────────────────────┐  │
> │ │ aiflow-admin UI                                      │  │
> │ │  - Pipeline trigger (user inditja az Invoice Findert)│  │
> │ │  - User interakcio (Verification Page, Chat, stb.)   │  │
> │ │  - Monitoring (Dashboard, Alerts, Audit)              │  │
> │ └────────────────────┬─────────────────────────────────┘  │
> │                      │ API call                            │
> │ ┌────────────────────▼─────────────────────────────────┐  │
> │ │ FastAPI + AIFlow Engine                               │  │
> │ │  - Pipeline Runner (YAML-bol vezerelt)                │  │
> │ │  - Service orchestration + Guardrails                 │  │
> │ │  - Notification (email riport automatikusan)          │  │
> │ └────────────────────┬─────────────────────────────────┘  │
> │                      │                                     │
> │ ┌────────────────────▼─────────────────────────────────┐  │
> │ │ Infrastructure (Docker Compose)                       │  │
> │ │  PostgreSQL + Redis + Kroki + LLM API-k              │  │
> │ └──────────────────────────────────────────────────────┘  │
> └────────────────────────────────────────────────────────────┘
> ```
>
> **Iranyelvek:**
> - qbpp_test_automation: TOROLVE (5 skill marad)
> - Guardrail: per-function PII kezeles (invoice-nal PII masking OFF!)
> - UI: user journey alapoktol ujragondolva, verification page v2
> - E2E: Invoice Finder mint elso valos, Docker-ready AIFlow szolgaltatas
> - **UI triggereli a pipeline-okat** — NEM Claude Code
> - **Docker container-ready**: minden szolgaltatas ugyfél-kesz megoldas
> - **TESZTELES explicit fazis** minden fejlesztesi lepesben
> - Koltseg optimalizalas: NEM prioritas (dev fazis), csak baseline meres

## Sprint B Fazisok — Attekintes

```
FAZIS 1 — ALAPOK (S19-S21): 3 session
  B0: Guardrail per-function + qbpp torles + architektura dok
  B1: LLM guardrail promptok (4 YAML) + per-skill guardrails.yaml
      TESZTELES: 20+ Promptfoo, 25 guardrail unit test, golden dataset

FAZIS 2 — E2E SZOLGALTATASOK (S22-S28): 7 session
  B2: Service unit tesztek (130 teszt, Tier-based)
      TESZTELES: 130/130 PASS, coverage >= 70%
  B3: Invoice Finder — valos E2E szolgaltatas (UI-bol inditva, Docker-ready!)
      TESZTELES: valos postafiok, valos szamlak, valos LLM, pipeline vegigfut
  B4: Skill hardening (5 skill, 95%+ promptfoo)
      TESZTELES: Promptfoo eval, guardrail teszt, /service-test
  B5: Diagram pipeline + Spec writer szolgaltatas + koltseg baseline
      TESZTELES: E2E diagram render, spec writer output validacio

FAZIS 3 — UI EXCELLENCE (S29-S31): 3 session
  B6: UI Journey audit + 4 journey tervezes + navigacio redesign
  B7: Verification Page v2 (bounding box, diff, perzisztencia)
      TESZTELES: Playwright E2E (upload→extract→verify→save→retrieve)
  B8: UI Journey implementacio (top 3 journey)
      TESZTELES: Playwright E2E minden journey-re, 0 console error

FAZIS 4 — DEPLOY & RELEASE (S32-S34): 3 session
  B9: Docker containerization + ugyfel-ready deploy teszteles
      TESZTELES: docker compose up → MINDEN szolgaltatas fut → E2E PASS
  B10: POST-AUDIT + javitasok
  B11: v1.3.0 tag + merge
```

---

## B0: Guardrail Per-Function + Alapok — 1 session (S19)

> **Gate:** Per-skill PII strategia dok KESZ, qbpp TOROLVE, architektura dok frissitve, 10-pontos checklist KESZ.

```
B0.1 — Per-Skill PII Strategia Tervdokumentum:
  FONTOS: A fix PII masking MEGHIUSITJA az uzleti funkciokat!
  Pl. invoice processing-nel adoszam/bankszamla KELL az LLM prompt-ban.

  Per-skill PII config terv:
  | Skill | pii_masking | allowed_pii | Indoklas |
  |-------|-------------|-------------|----------|
  | aszf_rag_chat | ON (full) | [] | Chat — SEMMI PII |
  | email_intent | PARTIAL | [email, name, company] | Routing-hoz kell |
  | invoice_processor | OFF | [ALL] | Szamla mezok = PII |
  | process_docs | ON | [] | Doku generalas — nincs PII |
  | cubix_course_capture | ON | [] | Video transcript — nincs PII |

  OUTPUT: 01_PLAN/61_GUARDRAIL_PII_STRATEGY.md

B0.2 — qbpp_test_automation TORLES:
  - skills/qbpp_test_automation/ mappa torles
  - Minden hivatkozas frissites (CLAUDE.md, 01_PLAN/CLAUDE.md): 6 → 5 skill
  - Promptfoo config torlese
  - ELLENORZES: pytest, ruff → PASS

B0.3 — 10 Pontos Production Checklist:
  [ ]  1. UNIT TESZT      — >= 5 teszt, >= 70% coverage
  [ ]  2. INTEGRACIO       — >= 1 valos DB-vel (ha DB-t hasznal)
  [ ]  3. API TESZT        — minden endpoint curl, source=backend
  [ ]  4. PROMPT TESZT     — promptfoo >= 95% pass (ha LLM-et hasznal)
  [ ]  5. ERROR HANDLING   — AIFlowError leszarmazott, is_transient flag
  [ ]  6. LOGGING          — structlog, NEM print(), event+key=value
  [ ]  7. DOKUMENTACIO     — docstring fo osztaly + publikus metodus
  [ ]  8. UI               — oldal mukodik, source badge, 0 console error
  [ ]  9. INPUT GUARDRAIL  — injection + PII (per-skill config!)
  [ ] 10. OUTPUT GUARDRAIL — hallucination, scope, PII leak check

B0.4 — Architektura Dokumentacio Frissites:
  FONTOS: Claude Code = FEJLESZTOI eszkoz (tervezes, fejlesztes, TESZTELES, karbantartas).
  AIFlow szolgaltatasok = Docker container-ben, UI-bol vezerelve, ugyfel-ready.

  Dokumentalandó:
  - Fejlesztesi ciklus: Claude Code hogyan tamogatja (slash commands, teszteles)
  - Uzemeltetesi architektura: Docker Compose, UI → FastAPI → Pipeline → Services
  - Deploy folyamat: dev → staging → production
  - UI mint pipeline vezerlo: hogyan inditja a user az Invoice Findert, stb.

  OUTPUT: 01_PLAN/62_DEPLOYMENT_ARCHITECTURE.md

B0.5 — Integralt Toolchain Koordinacios Ciklus:
  Langfuse (megfigyeles) → Promptfoo (teszteles) → Claude Code (vegrehajtas)
  Minden szolgaltatas finomhangolasa soran:
  1. Langfuse: baseline meres (trace, cost, quality)
  2. Promptfoo: eval → FAIL tetelek azonositasa
  3. Claude Code: prompt YAML javitas
  4. Promptfoo: ujra eval → 95%+?
  5. Guardrail config illesztes (per-skill PII strategia alapjan!)
  6. /dev-step → commit + dokumentacio

  2 uj slash command: /service-hardening + /prompt-tuning

GATE: PII strategia dok + qbpp torolve + checklist + architektura dok + 2 command
```

---

## B1: LLM Guardrail Promptok + Per-Skill Config — 2 session (S20-S21)

> **Gate:** 4 LLM guardrail prompt + 20 Promptfoo test case PASS, 5 skill guardrails.yaml KESZ.

```
B1.1 — 4 LLM Guardrail Prompt Implementacio:

  Architektura: Rule-based A5 (gyors, $0) → ha bizonytalan → LLM (preciz, $$)

  PROMPT 1 — hallucination_evaluator.yaml:
    A5 SequenceMatcher csereje. Grounding scoring LLM-mel.
    Input: {response, sources[]} → Output: {grounding_score, ungrounded_claims[]}
    Modell: gpt-4o-mini | 5+ Promptfoo test case

  PROMPT 2 — content_safety_classifier.yaml:
    A5 4 regex csereje. SAFE / UNSAFE / REVIEW_NEEDED osztalyozas.
    Input: {text, context} → Output: {verdict, category, confidence}
    Modell: gpt-4o-mini | 5+ Promptfoo test case

  PROMPT 3 — scope_classifier.yaml:
    A5 keyword matching csereje. 3-tier scope dontes kontextussal.
    Input: {query, allowed_topics[], skill_description}
    Output: {verdict: ScopeVerdict, reason, confidence}
    Modell: gpt-4o-mini | 5+ Promptfoo test case

  PROMPT 4 — freetext_pii_detector.yaml:
    UJ — regex NEM tudja: "a szomszédom Kiss János az OTP-nél dolgozik"
    Input: {text} → Output: {pii_items: [{type, text, start, end}]}
    Modell: gpt-4o-mini | 5+ Promptfoo test case

  KOD:
    src/aiflow/guardrails/llm_guards.py — 4 LLM guard osztaly
    config.py bovites: llm_fallback per guard, confidence_threshold
    10+ unit test (mock LLM + valos eval)

B1.2 — Per-Skill Guardrails.yaml (5 skill):

  KRITIKUS: A PII config skill-specifikus! (B0.1 strategia alapjan)

  skills/aszf_rag_chat/guardrails.yaml:
    input: {pii_masking: true, max_length: 2000, injection_check: true}
    output: {require_citation: true, hallucination_threshold: 0.7}
    scope: {allowed: [jog, biztositas, aszf], blocked: [politika, orvosi]}

  skills/email_intent_processor/guardrails.yaml:
    input: {pii_masking: partial, allowed_pii: [email, name, company]}
    output: {require_confidence: 0.7, max_intents: 3}

  skills/invoice_processor/guardrails.yaml:
    input: {pii_masking: false, pii_logging: true}  # SZAMLA: PII KELL!
    output: {validate_amounts: true, validate_dates: true}

  skills/process_documentation/guardrails.yaml:
    input: {pii_masking: true}
    output: {mermaid_syntax_check: true, max_diagram_nodes: 50}

  skills/cubix_course_capture/guardrails.yaml:
    input: {pii_masking: true, max_audio_length: 7200}
    output: {format_check: true}

  Per-skill: 5 guardrail teszt + golden_guardrails.yaml (safe/dangerous/injection)

GATE: 4 prompt YAML, 20+ Promptfoo PASS, 5 guardrails.yaml, 25 guardrail teszt, 10+ unit
```

---

## B2: Service Unit Tesztek — 2 session (S22-S23)

> **Gate:** 130 uj unit test PASS, coverage >= 70% services/ modulon.
> **TIER-BASED felosztás (szubjektiv prioritas helyett)**

```
B2.1 — Session 1: Core infra szolgaltatasok (13 service, 65 test):
  1. cache (5)           — Redis hit/miss/evict/TTL/pattern
  2. rate_limiter (5)    — bucket fill/drain, 429 trigger
  3. resilience (5)      — circuit open/half-open/close, retry
  4. health_monitor (5)  — service status, dependency check
  5. audit (5)           — log create/query/filter/retention
  6. schema_registry (5) — JSON schema CRUD/validate
  7. notification (5)    — email template, delivery retry
  8. human_review (5)    — HITL workflow, SLA timer
  9. media_processor (5) — ffmpeg probe, format detect
  10. diagram_generator (5) — Mermaid render, BPMN export
  11. rpa_browser (5)    — page navigate, screenshot
  12. classifier (5)     — ML predict, confidence threshold
  13. email_connector (5) — IMAP connect, fetch, filter
  ELLENORZES: pytest tests/unit/services/ -q → 65 PASS

B2.2 — Session 2: v1.2.0 szolgaltatasok (12 service + extra, 65 test):
  14. data_router (5)        — routing rules, priority
  15. service_manager (5)    — lifecycle, health
  16. reranker (5)           — score, sort, top-K
  17. advanced_chunker (5)   — 6 strategia
  18. data_cleaner (5)       — normalize, deduplicate
  19. metadata_enricher (5)  — auto-tag, entity link
  20. vector_ops (5)         — insert/search/delete/similarity
  21. advanced_parser (5)    — multi-format, fallback chain
  22. graph_rag (5)          — entity graph, traversal query
  23. quality (5)            — metric collect, threshold alert
  24. rag_engine (5)         — ingest, query, hybrid search
  25. document_extractor (5) — field extract, OCR fallback
  26. extra coverage (5)     — legalacsonyabb coverage potlas
  ELLENORZES: pytest tests/unit/services/ -q → 130 PASS, coverage >= 70%

GATE: 130/130 PASS, coverage >= 70%
```

---

## B3: Invoice Finder — Elso Valos E2E AIFlow Pipeline — 2 session (S24-S25)

> **Gate:** Teljes pipeline mukodik valos adatokkal: email → szamla → extract → report → ertesites.
> **Ez az elso VALOS, vegig mukodo AIFlow — minden alapozo szolgaltatast validál.**

```
B3.1 — Pipeline Design + Email/Acquisition Steps (S24):

  Pipeline: invoice_finder_v1.yaml (src/aiflow/pipeline/builtin_templates/)

  STEP 1 — Email Search (email_connector service):
    - IMAP/O365 postafiok scan
    - Intent-based kereses: "szamla", "invoice", "fizetesi felszolitas"
    - Subject + body + csatolmany-nev alapu szures
    - OUTPUT: email lista (id, subject, from, date, has_attachment, body_snippet)

  STEP 2 — Document Acquisition (document_extractor + uj logika):
    - HA csatolmany VAN → letoltes + Docling parse
    - HA csatolmany NINCS → link kereses email body-ban → HTTP letoltes → parse
    - Multi-format: PDF, DOCX, XLSX, kepek (scan szamla)
    - OUTPUT: parsed dokumentum lista (raw_text, tables, metadata)

  STEP 3 — Invoice Classification (classifier service):
    - Szamla vs. nem-szamla (ML + LLM hybrid)
    - Confidence threshold: >= 0.8 → auto-accept, < 0.8 → human review
    - OUTPUT: classified lista (is_invoice, confidence, doc_type)

  Adapter-ek: email_search_adapter, doc_acquire_adapter, invoice_classify_adapter
  Unit tesztek: 3 × 5 = 15 teszt
  Guardrail: PII masking OFF (szamla kontextus — B0.1 strategia!)

B3.2 — Extraction + Report + Notification (S25):

  STEP 4 — Data Extraction (invoice_processor):
    - Szamla mezok: szam, datum, hatarido, kiallito, osszeg, AFA, adoszam
    - HU-specifikus: AFO szam, AFA kulcsok (5%, 18%, 27%)
    - OUTPUT: structured InvoiceData (Pydantic model)

  STEP 5 — Payment Status (UJ step):
    - Lejarat vs. mai datum → fizetett / lejart / 30 napon belul
    - Opcionalis: bank CSV osszevetes (ha elerheto)
    - OUTPUT: InvoiceData + payment_status field

  STEP 6 — File Organization:
    - Nevkonvencio: {YYYYMMDD}_{Kiallito}_{SzamlaSzam}_{Osszeg_FT}.pdf
    - Mentes: output/{ev}/{honap}/ strukturalt mappa
    - OUTPUT: fajl utvonalak lista

  STEP 7 — Report Generation:
    - Osszefoglalo: hany szamla, mennyi fizetetlen, ossz osszeg
    - Reszletes tablaazat: szamlankenti adat
    - Format: Markdown + CSV/Excel export
    - OUTPUT: report.md + invoices.csv

  STEP 8 — Email Notification (notification service):
    - Jinja2 template: invoice_report_notification.yaml
    - Csatolmany: invoices.csv
    - OUTPUT: email elkuldve + log

  E2E TESZT (valos adat!):
    - 1 valos postafiok (dev/test mailbox)
    - 3-5 valos szamla PDF (kulonbozo formatumok)
    - Pipeline vegigfut → riport + mentett fajlok ellenorzese
    - NEM mock — valos IMAP + valos Docling + valos LLM

  CLI: python -m skills.invoice_finder --mailbox dev@bestix.hu --output ./invoices/

GATE: Pipeline vegigfut valos adatokkal, riport helyes, fajlok mentve, email elkuldve
```

---

## B4: Skill Hardening (5 skill) — 2 session (S26-S27)

> **Gate:** 5/5 skill 95%+ promptfoo, 5/5 guardrails.yaml KESZ, 5/5 checklist 8+/10.
> **Eszkozok:** /service-hardening + /prompt-tuning (B0-bol)

```
B4.1 — aszf_rag_chat + email_intent (S26):

  aszf_rag_chat (86% → 95%):
    - Prompt tuning: citation enforcement, hallucination kalibralas
    - 7 → 12 promptfoo test case
    - Guardrail: guardrails.yaml (B1.2-bol) finomhangolva valos trace-ek alapjan
    - CHECKLIST: [ ]1 [ ]2 [ ]3 [ ]4 [ ]5 [ ]6 [ ]7 [ ]8 [ ]9 [ ]10

  email_intent_processor (85% → 95%):
    - Intent catalog bovites (8 → 12 tipus)
    - Entity: HU adoszam, bankszamla, cim
    - 11 → 16 promptfoo test case
    - CHECKLIST: [ ]1 [ ]2 [ ]3 [ ]4 [ ]5 [ ]6 [ ]7 [ ]8 [ ]9 [ ]10

B4.2 — process_docs + invoice + cubix (S27):

  process_documentation (90% → 95%):
    - Diagram generator: Mermaid + BPMN + meglevo Python kodok integralasa
    - Meglevo diagram generalo kodok osszegyujtese + egysegesi interface
    - 11 → 15 promptfoo test case
    - CHECKLIST: [ ]1 [ ]2 [ ]3 [ ]4 [ ]5 [ ]6 [ ]7 [ ]8 [ ]9 [ ]10

  invoice_processor (80% → 95%):
    - Multi-page + scan szamla + kulfoldi formatum
    - 10 → 15 promptfoo test case
    - CHECKLIST: [ ]1 [ ]2 [ ]3 [ ]4 [ ]5 [ ]6 [ ]7 [ ]8 [ ]9 [ ]10

  cubix_course_capture (90% → 95%):
    - 5 → 8 promptfoo test case
    - CHECKLIST: [ ]1 [ ]2 [ ]3 [ ]4 [ ]5 [ ]6 [ ]7 [ ]8 [ ]9 [ ]10

GATE: 5/5 skill 95%+ promptfoo, 5/5 checklist 8+/10
```

---

## B5: Diagram Integralas + Specifikacio Iro AIFlow — 1 session (S28)

> **Gate:** Diagram pipeline mukodik, spec writer prototipus mukodik.

```
B5.1 — Diagram Generalo Integralas:
  KONTEXTUS: Mar van Mermaid/BPMN/DrawIO + Kroki render + Python kodok.
  CEL: Egysegesi interface amivel jol vezerelheto diagramok keszulnek.

  - Meglevo Python diagram kodok osszegyujtese (skills/process_documentation/)
  - Egysegesi DiagramRequest → DiagramResult Pydantic interface
  - Tamogatott tipusok: Mermaid flowchart, sequence, BPMN swimlane, DrawIO
  - LLM prompt: szoveges leiras → strukturalt diagram (Mermaid syntax)
  - Kroki render: Mermaid → SVG/PNG
  - Pipeline: diagram_generator_v1.yaml
  - 5 unit teszt + 3 E2E (szoveges leiras → renderelt kep)

B5.2 — Specifikacio Iro AIFlow Prototipus:
  CEL: Szobeli/vazlatos leiras → strukturalt specifikacio.

  Pipeline: spec_writer_v1.yaml
  STEP 1 — Input Analysis: szabad szoveges leiras strukturalas
  STEP 2 — Template Selection: milyen tipus? (feature spec, API spec, DB spec, user story)
  STEP 3 — Draft Generation: LLM → sablon kitoltes
  STEP 4 — Review Questions: "Ezekre a kerdesekre meg valasz kell..."
  STEP 5 — Final Output: Markdown specifikacio

  Prompt YAML: spec_analyzer.yaml, spec_generator.yaml, spec_reviewer.yaml
  3 Promptfoo test case (feature spec, API spec, user story)
  CLI: python -m skills.spec_writer --input "leiras..." --type feature --output spec.md

B5.3 — Langfuse Koltseg Baseline (egyszerusitett):
  - Per-service koltseg export Langfuse-bol
  - Riport: melyik service mennyibe kerul (nem optimalizacio, csak meres!)
  - OUTPUT: 01_PLAN/COST_BASELINE_REPORT.md

GATE: Diagram pipeline E2E mukodik, spec writer prototipus fut, koltseg baseline kesz
```

---

## B6: UI User Journey — Alapoktol Ujragondolas — 1 session (S29)

> **Gate:** Teljes journey audit kesz, 4 fo journey definialt es tervezett, ujratervezett navigacio.
> **Ez NEM kozmetikai polish — ez az egesz UI hasznalhatosaganak ujragondolasa.**

```
B6.1 — 17 Oldal Audit (MI MUKODIK VALOJABAN?):
  MINDEN oldal:
  | Oldal | Cel | Mi mukodik | Mi NEM mukodik | Kategoria |
  |-------|-----|-----------|----------------|-----------|
  | Dashboard | Attekintes | ? | ? | A/B/C/D |
  | Documents | Doku kezeles | ? | ? | A/B/C/D |
  | Emails | Email feldolg | ? | ? | A/B/C/D |
  | ... (mind a 17) | | | | |

  Kategoriak:
  A) Mukodik end-to-end (ritka)
  B) UI van, backend reszleges
  C) UI van, backend stub/demo
  D) Nem ertelmes jelenlegi formaban

B6.2 — 4 Fo User Journey Definialas:
  JOURNEY 1: "Szamla Feldolgozas"
    Email scan → szamla azonositas → extract → verify → save → report
    Oldalak: Emails → Documents → Verification → Dashboard (KPI)
    Backend: email_connector → invoice_processor → Invoice Finder pipeline

  JOURNEY 2: "Dokumentum Generalas"
    Szoveges leiras → diagram valasztas → render → review → export
    Oldalak: ProcessDocs → DiagramViewer → Export
    Backend: process_documentation skill

  JOURNEY 3: "RAG Chat"
    Collection letrehozas → dokumentum ingest → chat → feedback
    Oldalak: RAGCollections → RAGIngest → RAGChat → RAGStats
    Backend: rag_engine + vector_ops

  JOURNEY 4: "Monitoring & Governance"
    Dashboard → alerts → drill-down → action
    Oldalak: Dashboard → Quality → AuditLog → Services
    Backend: health_monitor + quality + audit + Langfuse

  Per journey: belépesi pont → lepesek → kilepes → eredmeny
  OUTPUT: 01_PLAN/63_UI_USER_JOURNEYS.md (reszletes journey terkep)

B6.3 — Navigacios Redesign:
  - Menu struktura a 4 journey-re epitett (nem onallo oldalak halmaza)
  - Dashboard: 4 journey "kartyakent" a fo attekintesen
  - Sidebar: journey-based csoportositas
  - Breadcrumb: hol vagyok a journey-ben?

B6.4 — Demo → Backend Migracio Terv:
  - MINDEN oldal: source=backend VAGY "Meg nem mukodik" felirat
  - SOHA NE demo adat lasd ugy mintha valos lenne
  - Prioritas: a 4 journey-hez tartozo oldalak ELSOBBSEGET kapnak

GATE: 17 oldal audit tabla KESZ, 4 journey definialt, navigacio terv, 63_UI_USER_JOURNEYS.md
```

---

## B7: Verification Page v2 — Kiemelt UI Feature — 1 session (S30)

> **Gate:** Verification page v2 mukodik: bounding box, edit diff, perzisztencia, audit trail.
> **Ez a projekt "showcase" felulete — a leheto legprofibb megoldas kell.**

```
B7.1 — Eredeti Dokumentum + Pozicio Jeloles:
  - A kivalasztott mezo az EREDETI PDF-en/kepen HIGHLIGHT-olva
  - Docling koordinatak felhasznalasa (bounding box)
  - PDF viewer komponens: react-pdf vagy pdf.js
  - Bounding box overlay: canvas-ra rajzolt teglalap
  - Zoom + pan + oldalvaltás
  - Kattintas a mezon → ugras a mezo poziciojara az eredeti dokumentumban

B7.2 — Edit Workflow:
  - User modosit egy mezot → "modositott" badge (arany keret)
  - Diff megjlenites: "Eredeti: 127.500 Ft → Modositott: 127.500,- Ft"
  - Undo/redo (Ctrl+Z/Y)
  - Mezo tipusu validacio: osszeg → szam, datum → datum format, adoszam → 8/11 jegy
  - Batch approve: "Minden rendben" gomb (ha nincs modositas)

B7.3 — Perzisztencia (DB):
  Alembic migracio: verification_edits tabla
  | Mezo | Tipus | Leiras |
  |------|-------|--------|
  | id | UUID PK | |
  | document_id | FK → documents | Melyik dokumentum |
  | field_name | VARCHAR | Melyik mezo (pl. "invoice_number") |
  | original_value | TEXT | Eredeti (LLM altal kiolvasott) |
  | edited_value | TEXT | User altal modositott |
  | editor_user_id | FK → users | Ki modositotta |
  | edited_at | TIMESTAMP | Mikor |
  | status | ENUM | pending/approved/rejected |
  | comment | TEXT | Opcionals megjegyzes |

  API endpoint-ok:
  - POST /api/v1/documents/{id}/verifications — mentés
  - GET /api/v1/documents/{id}/verifications — visszakeresheto audit trail
  - GET /api/v1/verifications/history?user=X — felhasznaloi szures

B7.4 — Elfogas + Statusz:
  - "Elfogadas" gomb → veglegesites (status → approved)
  - "Elutasitas" gomb → ujra-feldolgozas keres + indoklas
  - Export: CSV/JSON a veglegesitett adatokkal
  - Statisztika: hany dokumentum elfogadva/elutasitva/fuggobe

B7.5 — E2E Teszt:
  - Upload PDF szamla → LLM extract → verification page megjelenes
  - Mezo kivalasztas → eredeti PDF-en highlight
  - Mezo modositas → diff lathato → mentes
  - Visszakereses: /api/v1/documents/{id}/verifications → helyes adat
  - Playwright: screenshot + interaction test

GATE: Verification page v2 mukodik valos szamlaval, edit+save+retrieve PASS
```

---

## B8: UI Journey Implementacio — Top 3 Journey — 1 session (S31)

> **Gate:** 3/4 journey mukodik end-to-end, 0 console error, navigation redesign LIVE.

```
B8.1 — Navigacios Redesign Implementacio:
  - Sidebar: journey-based csoportositas (B6.3 terv alapjan)
  - Dashboard: 4 journey kartya fo attekintesen
  - Breadcrumb komponens

B8.2 — Journey 1 Implementacio: "Szamla Feldolgozas":
  - Emails oldal: postafiok scan trigger, szamla-talatat lista
  - Documents oldal: feldolgozott szamlak, statusz badge
  - Verification oldal: B7-bol (mar kesz!)
  - Dashboard: fizetetlen szamlak KPI
  - Backend: Invoice Finder pipeline (B3-bol) → UI integration

B8.3 — Journey 2 Implementacio: "Dokumentum Generalas":
  - ProcessDocs oldal: input form + diagram tipus valasztas
  - Diagram viewer: renderelt kimenet (SVG/PNG)
  - Export: letoltes + masolás

B8.4 — Journey 3 Implementacio: "RAG Chat":
  - Collection lista + letrehozas
  - Ingest: fajl upload → vektor DB
  - Chat: kerdes-valasz (valos backend!)
  - Feedback: hasznos/nem hasznos

B8.5 — Dark Mode + Responsive + i18n:
  - Minden uj/modositott oldal: dark mode WCAG AA
  - 768px breakpoint: olvashato
  - HU/EN: minden uj string translate()

GATE: 3 journey E2E mukodik, 0 console error, navigation uj, i18n PASS
```

---

## B9: Docker Containerization + Ugyfel-Ready Deploy — 1 session (S32)

> **Gate:** `docker compose up` → MINDEN szolgaltatas fut → UI-bol pipeline inditható → E2E PASS.
> **A nap vegen: Docker-ben futo, ugyfel-ready AIFlow megoldas.**

```
B9.1 — Docker Compose Frissites:
  docker-compose.yml / docker-compose.prod.yml:
  - FastAPI app container (src/aiflow/ + skills/)
  - arq worker container (async pipeline vegrehajtashoz)
  - aiflow-admin UI container (Vite build → nginx)
  - PostgreSQL + pgvector
  - Redis
  - Kroki (diagram render)
  Egyetlen `docker compose up` → MINDEN fut.

B9.2 — UI Pipeline Trigger Integracio:
  FONTOS: A USER az UI-bol inditja a pipeline-okat, NEM Claude-bol!
  - Invoice Finder: UI oldal → "Scan Mailbox" gomb → POST /api/v1/pipelines/run
  - Diagram Generator: UI oldal → szoveg input → "Generate" gomb → API hivas
  - Spec Writer: UI oldal → leiras input → "Write Spec" gomb → API hivas
  - Pipeline status: UI polling / WebSocket → futasi allapot megjelenitese
  - Eredmeny: UI-ban megjelenitett output (riport, diagram, spec)

B9.3 — Deploy Teszteles:
  a) `docker compose build` → HIBA NELKUL
  b) `docker compose up -d` → minden container healthy
  c) UI elerheto: http://localhost:5174 → bejelentkezes
  d) Invoice Finder: UI-bol inditva → pipeline vegigfut → riport megjelen
  e) Health endpoint: /health → MINDEN check "ok"
  f) Playwright E2E: Docker-ben futo rendszer ellen

B9.4 — Dokumentacio:
  - README.md: "Igy inditsd el Docker-ben" (3 lepesu guide)
  - 01_PLAN/62_DEPLOYMENT_ARCHITECTURE.md: vegleges architektura diagram
  - .env.example: minden szukseges konfiguracio

GATE: docker compose up → healthy → UI-bol pipeline PASS → E2E PASS
```

---

## B10: POST-AUDIT + Javitasok — 1 session (S33)

> **Gate:** Audit riport MINDEN sor PASS.

```
B10.1 — Teljes regresszio (L3):
  a) pytest tests/unit/ -q --cov=aiflow → ALL PASS, coverage >= 80%
  b) pytest tests/e2e/ -v → ALL PASS
  c) tsc --noEmit → 0, ruff → 0
  d) npx promptfoo eval → 5/5 skill 95%+
  e) Coverage NEM csokkenhet v1.2.2-hoz kepest!

B10.2 — Szolgaltatas erettseg audit:
  | Szolgaltatas | Checklist | Promptfoo | Guardrail | E2E | Status |
  |-------------|-----------|-----------|-----------|-----|--------|
  | aszf_rag | ?/10 | ?% | ? | ? | ? |
  | email_intent | ?/10 | ?% | ? | ? | ? |
  | process_docs | ?/10 | ?% | ? | ? | ? |
  | invoice | ?/10 | ?% | ? | ? | ? |
  | cubix | ?/10 | ?% | ? | ? | ? |
  | invoice_finder | ?/10 | — | ? | ? | ? |

B10.3 — Guardrail POST-audit:
  - Per-skill PII config helyes? (invoice: OFF, chat: ON)
  - LLM guardrail 4/4 prompt 95%+?
  - Rule→LLM fallback lanc mukodik?

B10.4 — UI POST-audit:
  - 3/4 journey E2E mukodik?
  - Verification page v2: valos szamlaval tesztelve?
  - 0 console error, 0 demo oldal a fo journey-kben?

B10.5 — Audit riport:
  === SPRINT B POST-AUDIT RIPORT ===
  Service tesztek:      130/130 PASS        → [PASS/FAIL]
  Prompt minoseg:       5/5 skill 95%+      → [PASS/FAIL]
  Guardrail (rule):     5/5 skill config    → [PASS/FAIL]
  Guardrail (LLM):      4/4 prompt 95%+     → [PASS/FAIL]
  Guardrail (PII):      per-skill helyes    → [PASS/FAIL]
  Invoice Finder E2E:   pipeline vegigfut   → [PASS/FAIL]
  Verification Page:    edit+save+retrieve  → [PASS/FAIL]
  UI Journey:           3/4 mukodik         → [PASS/FAIL]
  Docker deploy:        compose up → healthy → [PASS/FAIL]
  UI pipeline trigger:  UI-bol inditva PASS → [PASS/FAIL]
  Unit tesztek:         ~1400+ PASS         → [PASS/FAIL]
  E2E tesztek:          102+ PASS           → [PASS/FAIL]

  VERDICT: [PASS] / [FAIL — open items]

B10.6 — Javitasok (ha FAIL):
  - Minden FAIL tetel → konkret fix
  - Ujra-audit csak FAIL tetelek

GATE: Audit riport MINDEN PASS
```

---

## B11: v1.3.0 Tag + Merge — fel session (S34)

> **Gate:** v1.3.0 tag, main-en CI ZOLD.

```
B11.1 — pyproject.toml + _version.py: version = "1.3.0"
B11.2 — git tag v1.3.0
B11.3 — 58_POST_SPRINT_HARDENING_PLAN.md: Sprint B = DONE
B11.4 — CLAUDE.md + 01_PLAN/CLAUDE.md: vegleges szamok
B11.5 — Merge to main (squash)

GATE: v1.3.0 tag pushed, main CI ZOLD
```

---

## Sprint B Utemterv

```
=== FAZIS 1: ALAPOK (S19-S21) ===
S19: B0 — Guardrail per-function + qbpp torles + Claude↔AIFlow koncepcio + checklist
S20: B1.1 — LLM guardrail promptok (4 YAML + Promptfoo) + llm_guards.py
S21: B1.2 — Per-skill guardrails.yaml (5 skill) + golden dataset

=== FAZIS 2: E2E SZOLGALTATASOK (S22-S28) ===
S22: B2.1 — Core infra service tesztek (65 test)
S23: B2.2 — v1.2.0 service tesztek (65 test)
S24: B3.1 — Invoice Finder pipeline: design + email search + doc acquisition
S25: B3.2 — Invoice Finder: extraction + report + notification (valos adat!)
S26: B4.1 — Skill hardening: aszf_rag + email_intent (prompt + guardrail)
S27: B4.2 — Skill hardening: process_docs + invoice + cubix + diagram integralas
S28: B5 — Spec writer prototipus + diagram pipeline + koltseg baseline

=== FAZIS 3: UI EXCELLENCE (S29-S31) ===
S29: B6 — UI Journey audit + 4 fo journey tervezes + navigacio redesign terv
S30: B7 — Verification Page v2 (bounding box, edit diff, perzisztencia)
S31: B8 — UI Journey implementacio (top 3 journey + dark mode + responsive)

=== FAZIS 4: RELEASE (S32-S34) ===
S32: B9 — Claude↔AIFlow mukodo prototipus (/find-invoices, /generate-diagram, /write-spec)
S33: B10 — POST-AUDIT + javitasok
S34: B11 — v1.3.0 tag + merge
```

---

# Osszesites

> Az alabbi szekciok MINDKET sprintre vonatkoznak.

## Teljes Utemterv (Sprint A + B)

```
=== SPRINT A: Infrastruktura & Biztonsag (v1.2.2) — DONE (4 session) ===
S15: A0+A1+A2 — CI/CD + Ruff + Dead code ── DONE (2026-04-04)
S16: A3+A4 ─── Security + Stubs ──────────── DONE (2026-04-04)
S17: A5 ─────── Guardrail keretrendszer ───── DONE (2026-04-04)
S18: A6+A7+A8 — POST-AUDIT + v1.2.2 tag ─── DONE (2026-04-05)

=== SPRINT B: E2E Szolgaltatas Excellence (v1.3.0) — 16 session ===
--- Fazis 1: Alapok (S19-S21) ---
S19: B0 ─── Guardrail per-function + qbpp torles + Claude↔AIFlow koncepcio
S20: B1.1 ─ LLM guardrail promptok (4 YAML + Promptfoo + llm_guards.py)
S21: B1.2 ─ Per-skill guardrails.yaml (5 skill) + golden dataset

--- Fazis 2: E2E Szolgaltatasok (S22-S28) ---
S22: B2.1 ─ Core infra service tesztek (65 test, Tier 1)
S23: B2.2 ─ v1.2.0 service tesztek (65 test, Tier 2)
S24: B3.1 ─ Invoice Finder: pipeline design + email + doc acquisition
S25: B3.2 ─ Invoice Finder: extract + report + notification (valos adat!)
S26: B4.1 ─ Skill hardening: aszf_rag + email_intent
S27: B4.2 ─ Skill hardening: process_docs + invoice + cubix + diagram
S28: B5 ─── Spec writer + diagram pipeline + koltseg baseline

--- Fazis 3: UI Excellence (S29-S31) ---
S29: B6 ─── UI Journey audit + 4 journey tervezes + navigacio redesign
S30: B7 ─── Verification Page v2 (bounding box, diff, perzisztencia)
S31: B8 ─── UI Journey implementacio (top 3 journey + dark mode)

--- Fazis 4: Release (S32-S34) ---
S32: B9 ─── Docker containerization + UI pipeline trigger + deploy teszt
S33: B10 ── POST-AUDIT + javitasok
S34: B11 ── v1.3.0 tag + merge
```

**Osszes:** Sprint A 4 + Sprint B 16 = **20 session**, ~8,000 LOC, ~400+ uj teszt,
2 version tag (v1.2.2 DONE + v1.3.0), 1 uj E2E pipeline (Invoice Finder),
Verification Page v2, Docker-ready deploy, UI pipeline trigger, 5 skill 95%+ promptfoo

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

### Sprint B (v1.3.0) — E2E Szolgaltatas Excellence

| # | Kriterium | Mertek |
|---|-----------|--------|
| 1 | **Invoice Finder E2E** | Pipeline vegigfut valos adatokkal (email→extract→report→notify) |
| 2 | **Verification Page v2** | Bounding box + edit diff + DB perzisztencia + audit trail |
| 3 | **UI Journey** | 3/4 fo journey mukodik end-to-end, navigacio redesign LIVE |
| 4 | **Guardrail per-function** | 5/5 skill guardrails.yaml, PII config skill-specifikus |
| 5 | **LLM Guardrail** | 4/4 prompt 95%+ Promptfoo, rule→LLM fallback mukodik |
| 6 | **Service tesztek** | 130+ uj unit test PASS, coverage >= 70% services/ |
| 7 | **Skill minoseg** | 5/5 skill 95%+ promptfoo |
| 8 | **Diagram + Spec** | Diagram pipeline E2E + spec writer szolgaltatas mukodik |
| 9 | **Docker deploy** | `docker compose up` → healthy → UI-bol pipeline inditható |
| 10 | **UI pipeline trigger** | User az UI-bol indit pipeline-t, eredmeny megjelen |
| 11 | **Post-audit** | Audit riport MINDEN sor PASS |
| 12 | **Version tag** | v1.3.0 tag, main ZOLD |

---

## Slash Command Referencia

| Command | Hasznalat | Sprint |
|---------|-----------|--------|
| `/lint-check` | Ruff + tsc + format osszesito | A1, minden fazis vegen |
| `/regression` | Unit + E2E regresszio | A6, B10, commit elott |
| `/quality-check` | Promptfoo + Langfuse koltseg elemzes | B1-B5 |
| `/service-test` | Backend + API + UI e2e | B2-B4 |
| `/service-hardening` | 10-pontos checklist audit (UJ, B0) | B4 |
| `/prompt-tuning` | Langfuse→Promptfoo→fix ciklus (UJ, B0) | B4 |
| `/dev-step` | Fejlesztes + teszt + commit | Minden fazis |
| `/pipeline-test` | Pipeline E2E teszt (valos futatas) | B3 |

---

## Progress Tracking

### Sprint A (v1.2.2)

| Fazis | Tartalom | Allapot | Datum | Commit |
|-------|----------|---------|-------|--------|
| A0 | CI/CD Green | DONE | 2026-04-04 | 27e9c82 |
| A1 | Ruff 1,234 → 0 | DONE | 2026-04-04 | a32a84d |
| A2 | Halott kod audit + archivalas | DONE | 2026-04-04 | 2c0e078 |
| A3 | Security + JWT session | DONE | 2026-04-04 | 176f137 |
| A4 | Stubs + alapfunkciok | DONE | 2026-04-04 | 87b896e |
| A5 | Guardrail keretrendszer | DONE | 2026-04-04 | ba8d6c8 |
| A6 | POST-AUDIT | DONE | 2026-04-05 | — |
| A7 | Audit javitasok (4 fix) | DONE | 2026-04-05 | — |
| A8 | v1.2.2 tag | DONE | 2026-04-05 | — |

### Sprint B (v1.3.0) — E2E Szolgaltatas Excellence

| Fazis | Tartalom | Session | Allapot | Datum | Commit |
|-------|----------|---------|---------|-------|--------|
| B0 | Guardrail per-function + qbpp torles + koncepcio | S19 | TODO | — | — |
| B1 | LLM guardrail promptok + per-skill config | S20-S21 | TODO | — | — |
| B2 | Service unit tesztek (130 test, Tier-based) | S22-S23 | TODO | — | — |
| B3 | **Invoice Finder E2E pipeline** (valos adat!) | S24-S25 | TODO | — | — |
| B4 | Skill hardening (5 skill, 95%+ promptfoo) | S26-S27 | TODO | — | — |
| B5 | Diagram pipeline + Spec writer + koltseg baseline | S28 | TODO | — | — |
| B6 | UI Journey audit + 4 journey tervezes | S29 | TODO | — | — |
| B7 | **Verification Page v2** (bounding box, diff, DB) | S30 | TODO | — | — |
| B8 | UI Journey implementacio (top 3 journey) | S31 | TODO | — | — |
| B9 | **Docker deploy** + UI pipeline trigger | S32 | TODO | — | — |
| B10 | POST-AUDIT + javitasok | S33 | TODO | — | — |
| B11 | v1.3.0 tag + merge | S34 | TODO | — | — |
