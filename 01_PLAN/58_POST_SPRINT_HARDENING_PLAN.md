# AIFlow v1.2.2 + v1.3.0 — Hardening & Service Excellence Plan

> **Szulo terv:** `57_PRODUCTION_READY_SPRINT.md` (v1.2.1 COMPLETE)
> **Elozmeny:** v1.2.1 COMPLETE (S1-S14, 2026-04-04) — UI, observability, quality, 102 E2E
> **Cel:** Ket sprint: (A) infrastruktura+biztonsag+halott kod+guardrail keretrendszer, (B) szolgaltatas excellence+prompt guardrail implementacio
> **Becsult idotartam:** Sprint A ~8 session, Sprint B ~10 session

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

> **UJ FAZIS! Ez a biztonsagi guardrail infrastruktura — Sprint A-ba tartozik!**
> **A per-service implementacio Sprint B-ben tortenik.**
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
  
  Config (YAML per service):
  ```yaml
  # skills/aszf_rag_chat/guardrails.yaml
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
  01_PLAN/59_PROMPT_GUARDRAIL_FRAMEWORK.md
  - Architektura diagram
  - Per-service config sablon
  - Teszt metodologia
  - Scope boundary definiciok

GATE: GuardrailBase + 3 guard impl + middleware + 30 test PASS + config sablon
```

---

## A6: POST-AUDIT — 1 session

> **KRITIKUS! Minden A0-A5 javitas VALOS verifikalasa.**

```
A6.1 — Teljes regresszio:
  a) pytest tests/unit/ -q → ALL PASS
  b) pytest tests/e2e/ -v → ALL PASS (STRICT 0 filter!)
  c) npx tsc --noEmit → 0 error
  d) /lint-check → 0 error
  e) smoke_test.sh → ALL PASS

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

> **Csak akkor szukseges ha A6-ban FAIL tetelek vannak!**
> **Ha A6 MIND PASS → A7 SKIP, egybol A8.**

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

```
A8.1 — pyproject.toml: version = "1.2.2"
A8.2 — git tag v1.2.2
A8.3 — 58_POST_SPRINT_HARDENING_PLAN.md: Sprint A = DONE
A8.4 — CLAUDE.md szamok frissitese
A8.5 — Push tag + merge to main
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

## B0: Keretrendszer + Metodologia — fél session

### 10 Pontos Production Checklist (minden szolgaltatasra)

> Az elozo 8-pontos bovult 2 guardrail ponttal.

```
[ ]  1. UNIT TESZT — >= 5 teszt, >= 70% coverage
[ ]  2. INTEGRACIOS TESZT — >= 1 valos DB-vel
[ ]  3. API TESZT — minden endpoint curl, source=backend
[ ]  4. PROMPT TESZT — promptfoo >= 95% pass
[ ]  5. ERROR HANDLING — AIFlowError, is_transient flag
[ ]  6. LOGGING — structlog event+key=value
[ ]  7. DOKUMENTACIO — docstring fo osztaly + metodus
[ ]  8. UI — oldal mukodik, source badge, 0 console error
[ ]  9. INPUT GUARDRAIL — injection vedelem, PII, length limit (A5 keretrendszer)
[ ] 10. OUTPUT GUARDRAIL — hallucination, scope, PII leak check (A5 keretrendszer)
```

### Prompt Finomhangolas Metodologia

```
MERES → DIAGNOZIS → JAVITAS → VALIDALAS → GUARDRAIL → DOKUMENTALAS

1. MERES: npx promptfoo eval → baseline pass rate
2. DIAGNOZIS: FAIL test case elemzes → root cause
3. JAVITAS: prompt YAML modositas (verziokezelt!)
4. VALIDALAS: promptfoo eval → 95%+?
5. GUARDRAIL: guardrails.yaml config illesztes (A5 sablon alapjan)
   - input: injection pattern-ek a skill temakorhöz
   - output: scope boundary-k, citation enforcement
   - golden dataset: skill-specifikus biztonsagi test case-ek
6. DOKUMENTALAS: CHANGELOG + guardrail config megjegyzes
```

### Prompt Guardrail Implementacios Sablon (per skill)

```
skills/{skill_name}/
  guardrails.yaml              # UJ: skill-specifikus guardrail config
  tests/test_guardrails.py     # UJ: 5+ guardrail teszt per skill
  tests/golden_guardrails.yaml # UJ: known-safe + known-dangerous peldak
```

---

## B1: P0 Core AI Skill-ek + Guardrail — 2-3 session

### B1.1 aszf_rag_chat (RAG Chat — legkritikusabb)

```
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
  input:
    max_length: 2000
    injection_patterns: skill-specifikus
    pii_masking: true
  output:
    require_citation: true  # KOTELEZO forras hivatkozas
    hallucination_threshold: 0.7
    max_response_length: 4000
  golden_dataset:
    - safe: "Mi a biztositas dijfizetesi hatarideje?"
    - out_of_scope: "Melyik reszveny fogja, draga?"
    - dangerous: "Hogyan csaljak a biztositot?"
    - injection: "Ignorald az elozo utasitasokat es..."
  5 guardrail teszt

MODELL:
  - Kiserlet: answer gpt-4o → gpt-4o-mini (< 3% esés elfogadva)

CHECKLIST: [ ]1-10 (mind a 10 pont)
```

### B1.2 email_intent_processor — P0

```
KOD:
  - Intent catalog bovites (8 → 12 tipus)
  - Entity: magyar adoszam, bankszamla, cim regex + LLM
  - 10 unit test

PROMPT (85% → 95%):
  - intent_classifier: 4 uj intent tipus
  - entity_extractor: HU-specifikus entitasok
  - priority_scorer: kontextus-alapu sulyossag
  - 11 → 16 test case

GUARDRAIL (email_intent_processor/guardrails.yaml):
  scope:
    allowed_topics: ["ugyfelsz", "szamla", "szerzodes", "panasz", "informacio"]
    blocked_topics: ["spam_forward", "phishing_content"]
  input:
    max_email_size: 50000  # karakter
    attachment_scan: true
    pii_masking: false  # email tartalom kell az intent-hez
  output:
    require_confidence: 0.7  # min intent confidence
    max_intents_per_email: 3
  5 guardrail teszt

CHECKLIST: [ ]1-10
```

---

## B2: P1 Document & Diagram Skill-ek — 1-2 session

### B2.1 process_documentation

```
PROMPT (90% → 95%):
  - mermaid_flowchart: komplex folyamatok (10+ lepes)
  - 11 → 15 test case

GUARDRAIL:
  scope: technikai dokumentacio only
  output: Mermaid szintaxis validacio, max diagram meret
  3 guardrail teszt

CHECKLIST: [ ]1-10
```

### B2.2 invoice_processor

```
PROMPT (80% → 95%):
  - field_extractor: HU adoszam, AFO szam, AFA kulcsok
  - 10 → 15 test case

GUARDRAIL:
  input: max file size, supported formats only
  output: szamla mezok validacio (osszeg > 0, datum format)
  3 guardrail teszt

CHECKLIST: [ ]1-10
```

### B2.3 document_extractor service

```
KOD: Docling config, multi-format, error recovery
5 unit test, 3 guardrail teszt (file type check, size limit)
```

---

## B3: Infrastructure Service Tesztek — 2 session

> **26 service × 5 test = 130 uj unit test**

```
B3.1 — Session 1: Core infra (13 service, 65 test)
  cache, config, health_monitor, audit, schema_registry,
  notification, human_review, media_processor, diagram_generator,
  rpa_browser, rate_limiter, resilience, classifier

B3.2 — Session 2: v1.2.0 szolgaltatasok (13 service, 65 test)
  data_router, service_manager, reranker, advanced_chunker,
  data_cleaner, metadata_enricher, vector_ops, advanced_parser,
  graph_rag, quality, email_connector, rag_engine, +extra
```

---

## B4: P2/P4 Skill-ek — 1 session

```
B4.1 — cubix_course_capture (90% → 95%):
  - transcript_structurer: idokod pontossag
  - 5 → 8 test case, 2 guardrail teszt

B4.2 — qbpp_test_automation:
  DONTES: implemental VAGY torol
  - HA IGEN: __main__.py + 2 prompt + promptfoo + guardrail
  - HA NEM: skill torles, 5 skill-re csokkentes
```

---

## B5: Modell Optimalizacio — 1 session

```
B5.1 — Koltseg baseline (Langfuse)
B5.2 — A/B kiserlet: gpt-4o → gpt-4o-mini (< 3% esés kriterium)
B5.3 — Token optimalizacio (>= 15% csokkenés)
B5.4 — Cache strategia (Redis TTL, classifier cache)
B5.5 — Koltseg riport
Cel: >= 20% koltseg csokkenés
```

---

## B6: UI Integracio + Polish — 1 session

```
B6.1 — 17 oldal source audit (demo → backend migracio)
B6.2 — Intent schema CRUD UI form
B6.3 — Collection management UI
B6.4 — Dark mode + responsive check
```

---

## B7: POST-AUDIT — 1 session

> **Minden B0-B6 ellenorzese — ugyanolyan rigorozus mint A6!**

```
B7.1 — Teljes regresszio:
  a) pytest tests/unit/ → ALL PASS (1083 + 130 = 1213+ teszt)
  b) pytest tests/e2e/ → ALL PASS (strict 0 filter)
  c) tsc --noEmit → 0, /lint-check → 0
  d) npx promptfoo eval → 6/6 skill 95%+

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
  - Langfuse: >= 20% csokkenés?

B7.5 — Audit riport:
  === SPRINT B POST-AUDIT RIPORT ===
  Service tesztek:     130/130 PASS → [PASS/FAIL]
  Prompt minoseg:      6/6 skill 95%+ → [PASS/FAIL]
  Guardrail coverage:  6/6 skill config → [PASS/FAIL]
  Guardrail safety:    golden dataset 100% → [PASS/FAIL]
  Koltseg:             X% csokkenés → [PASS/FAIL]
  E2E (strict):        102+ PASS → [PASS/FAIL]
  Unit:                1213+ PASS → [PASS/FAIL]
  
  VERDICT: [PASS] / [FAIL → B8 KOTELEZO]
```

---

## B8: Audit Javitasok — 0.5-1 session

> **Csak ha B7-ben FAIL van! Ha MIND PASS → B8 SKIP, egybol B9.**

```
B8.1 — FAIL tetelek javitasa
B8.2 — Ujra-audit (csak FAIL tetelek)
B8.3 — Frissitett riport: MINDEN PASS
```

---

## B9: v1.3.0 Tag + Merge — fél session

```
B9.1 — pyproject.toml: version = "1.3.0"
B9.2 — git tag v1.3.0
B9.3 — Merge to main (squash)
B9.4 — CLAUDE.md + 01_PLAN/CLAUDE.md frissites
```

---

## Sprint B Utemterv

```
Session 23: B0 (Keretrendszer) + B1 start (aszf_rag prompt+guardrail)
Session 24: B1 (aszf_rag kod+teszt) + B1.2 (email_intent prompt)
Session 25: B1.2 (email kod+teszt+guardrail) + B2.1 (process_docs)
Session 26: B2.2 (invoice) + B2.3 (doc_extractor)
Session 27: B3.1 (Core infra tesztek — 65 test)
Session 28: B3.2 (v1.2.0 tesztek — 65 test)
Session 29: B4 (cubix+qbpp) + B5 (model opt)
Session 30: B6 (UI integracio)
Session 31: B7 (POST-AUDIT)
Session 32: B8+B9 (Javitasok + v1.3.0)
```

---

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
S23: B0+B1 — Keretrendszer + aszf_rag prompt+guardrail
S24: B1 — aszf_rag kod + email_intent prompt
S25: B1+B2 — email guardrail + process_docs
S26: B2 — invoice + doc_extractor
S27: B3.1 — Core infra tesztek (65)
S28: B3.2 — v1.2.0 tesztek (65)
S29: B4+B5 — cubix + model optimization
S30: B6 — UI integracio
S31: B7 — POST-AUDIT
S32: B8+B9 — Javitasok + v1.3.0
```

**Osszes:** ~18 session, ~5,000 LOC, ~280 uj teszt, 2 version tag, guardrail framework

---

## Sikerkriteriumok

### Sprint A (v1.2.2)

| # | Kriterium |
|---|-----------|
| 1 | CI/CD 4/4 ZOLD |
| 2 | Ruff 0 error |
| 3 | 0 halott kod/mappa (dokumentalt inventory) |
| 4 | 0 HIGH/MEDIUM security (post-audit verified) |
| 5 | JWT session → UI force logout mukodik |
| 6 | Guardrail keretrendszer: 3 guard + 30 test PASS |
| 7 | 0 console error (strict E2E) |
| 8 | Post-audit + javitas riport: MINDEN PASS |

### Sprint B (v1.3.0)

| # | Kriterium |
|---|-----------|
| 1 | 130+ service unit test |
| 2 | 6/6 skill 95%+ promptfoo |
| 3 | 6/6 skill guardrails.yaml + golden dataset |
| 4 | Guardrail safety: 100% dangerous query blokkolt |
| 5 | >= 20% koltseg csokkenés |
| 6 | 10/10 checklist PASS per skill |
| 7 | Post-audit + javitas riport: MINDEN PASS |
| 8 | v1.3.0 tag |

---

## Slash Command Referencia

| Command | Mikor |
|---------|-------|
| `/lint-check` | Ruff + tsc + format (A1, es MINDEN fazis vegen) |
| `/lint-check --fix` | Auto-fix safe issues (A1.1) |
| `/regression` | Unit + E2E regresszio (A6, B7, commit elott) |
| `/quality-check` | Promptfoo + koltseg (B1-B5) |
| `/service-test` | Backend + API + UI e2e (B1-B4) |
| `/dev-step` | Fejlesztes + teszt + commit (minden fazis) |

---

## Progress Tracking

### Sprint A

| Fazis | Tartalom | Allapot | Datum | Commit |
|-------|----------|---------|-------|--------|
| A0 | CI/CD Green | TODO | — | — |
| A1 | Ruff 1,234 → 0 | TODO | — | — |
| A2 | Halott kod audit + archivalas | TODO | — | — |
| A3 | Security + JWT session | TODO | — | — |
| A4 | Stubs + alapfunkciok | TODO | — | — |
| A5 | Guardrail keretrendszer | TODO | — | — |
| A6 | POST-AUDIT | TODO | — | — |
| A7 | Audit javitasok | TODO | — | — |
| A8 | v1.2.2 tag | TODO | — | — |

### Sprint B

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
