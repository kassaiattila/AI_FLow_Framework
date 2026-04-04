# AIFlow v1.2.2+ — Post-Sprint Hardening & Service Excellence Plan

> **Szulo terv:** `57_PRODUCTION_READY_SPRINT.md` (v1.2.1 COMPLETE)
> **Elozmeny:** v1.2.1 COMPLETE (S1-S14, 2026-04-04) — UI, observability, quality, 102 E2E
> **Cel:** Ket sprint: (A) infrastruktura+biztonsag+minoseg, (B) szolgaltatas-szintu excellence
> **Becsult idotartam:** Sprint A ~6-8 session, Sprint B ~8-12 session

---

## 0. Audit Eredmenyek Osszefoglalasa (2026-04-04)

### 0.1 Ruff Lint (1,234 hiba)

| Terulet | Hibak | Auto-fix | Manual |
|---------|-------|----------|--------|
| `src/aiflow/` | 574 | 243 (42%) | 331 |
| `tests/` | 181 | 128 (71%) | 53 |
| `skills/` | 479 | 177 (37%) | 302 |
| **OSSZES** | **1,234** | **548 (44%)** | **686** |

**Top 5:** E501 (287 long line), I001 (258 import sort), F401 (147 unused import), N806 (117 naming), F541 (75 empty f-string)

### 0.2 Biztonsagi Audit

| Sulyossag | Problema | Fajl |
|-----------|---------|------|
| **HIGH** | Sajat JWT impl. PyJWT helyett | `security/auth.py:47-79` |
| **HIGH** | Default JWT secret `"dev-secret-..."` | `security/auth.py:47` |
| **MEDIUM** | CORS `allow_methods=["*"]` | `api/app.py:98` |
| **MEDIUM** | Rate limiter NEM bekotve middleware-be | `api/app.py` |
| **MEDIUM** | Session lejarat: UI NEM jelentkezteti ki a usert | `aiflow-admin` |
| **LOW** | Path traversal file upload | `api/v1/documents.py` |
| **LOW** | API key SHA256 (nem bcrypt) | `security/auth.py:134` |
| **LOW** | Hianyzik: security headers (CSP, HSTS, X-Frame) | `api/app.py` |

### 0.3 Stub/Placeholder Audit (61 marker)

| Kategoria | Db | Akcio |
|-----------|-----|-------|
| Kafka stub (duplikalt, 2 fajl) | 24 | TORLES (Kafka HALASZTVA) |
| CLI commands (nem implementalt) | 7 | NotImplementedError + uzenet |
| Parser stubs (Docling helyettesiti) | 4 | TORLES + hivatkozas |
| Evaluator placeholder (0.5 score) | 2 | Valos rubric VAGY torles |
| Skill registry duplikalt | 8 | Konszolidacio |
| Egyeb (vision, vault, prompt sync) | 16 | Egyenkent elbiralas |

### 0.4 CI/CD (PR #1 — 4/4 FAIL)

| Workflow | Fo hiba | Fix |
|----------|---------|-----|
| `ci.yml` | `skills/` benne ruff scope-ban | Scope: `src/ tests/` |
| `ci-framework.yml` | Regi venv setup + 574 ruff error | `uv sync --dev` + ruff fix |
| `ci-skill.yml` | Skill fuggoseg hianyzik | pyproject.toml extras |
| `nightly-*` | Nem PR-releváns | OK (nightly) |

### 0.5 Szolgaltatas Erettseg

| Szint | Db | Szolgaltatasok | Fo hianyossag |
|-------|----|---------------|---------------|
| **Production-ready** | 3 | rag_engine, classifier, document_extractor | Nincs unit test |
| **Partial** | 20 | cache, email_connector, notification, stb. | Nincs unit test, prompt 80-90% |
| **Stub** | 3 | rate_limiter, resilience, qbpp_test_automation | Nincs valos mukodes |

---

## 1. Ket Sprint Strategia

```
SPRINT A: Infrastruktura & Biztonsag ──── "Epitsd meg a fundamentumot"
  Cel: CI zold, kod clean, biztonsag, hianyzo alapfunkciok
  Fazisok: A0-A6
  Becsult: ~6-8 session
  Branch: feature/v1.2.2-infrastructure

SPRINT B: Szolgaltatas Excellence ─────── "Hozd magas szintre a szolgaltatasokat"
  Cel: Szolgaltatasonkent: kod, prompt, modell, UI finomhangolas
  Fazisok: B0-B7
  Becsult: ~8-12 session
  Branch: feature/v1.3.0-service-excellence
```

**Sprint A epit, Sprint B finomhangol.** A sorrend KOTELEZO — Sprint B Sprint A eredmenyeire epit.

---

# SPRINT A: Infrastruktura & Biztonsag (v1.2.2)

> **Branch:** `feature/v1.2.2-infrastructure`
> **Cel:** Zold CI, clean kod, biztonsag, hianyzo alapfunkciok, session management
> **Vegtermek:** v1.2.2 tag, PR ZOLD, 0 ruff, 0 HIGH security

## A0: CI/CD Green — 1 session (BLOKKOLO!)

> **Gate:** PR #1 MINDEN workflow PASS.
> **Miert elso:** Amig CI FAIL, semmit nem tudunk biztonsagosan merge-olni.

```
A0.1 — ci.yml fix:
  - ruff scope: `src/ tests/` (NEM skills/ — sajat workflow)
  - venv: `uv sync --dev` (nem `uv venv && uv pip install`)
  - admin build: ellenorizd hogy Vite build PASS

A0.2 — ci-framework.yml fix:
  - Ugyanaz: `uv sync --dev` + ruff scope konzisztens
  
A0.3 — ci-skill.yml fix:
  - Skill fuggosegek: pyproject.toml `[project.optional-dependencies]` skills = [...]
  - VAGY: skill-szintu requirements.txt + pip install -r

A0.4 — Push + CI ZOLD ellenorzes

GATE CHECK: MINDEN GitHub Actions ZOLD ← TILOS tovabblepni ha FAIL
```

**Deliverable:** 3-4 workflow YAML fix, PR #1 ZOLD

---

## A1: Ruff Cleanup (1,234 → 0) — 1-2 session

> **Gate:** `ruff check src/ tests/ skills/` → 0 error, `/lint-check` → ALL PASS
> **Eszkoz:** `/lint-check --fix` (uj slash command)

```
A1.1 — Safe batch fix (548 auto-fixable):
  Sorrend (kockazat szerint):
  1. tests/: `ruff check tests/ --fix` (128 fix, legkisebb kockazat)
  2. src/aiflow/ safe rules: --fix --select I001,F541,UP017,UP035,UP041,UP045
  3. skills/ safe rules: --fix --select I001,F541,UP017
  REGRESSZIO: pytest tests/unit/ -q → PASS

A1.2 — Manual fix (686 maradt):
  a) E501 (287): logikai sorbontas (nem mechanikus wrap!)
  b) N806/N803 (149): pyproject.toml per-file-ignores:
     "skills/**" = ["N806", "N803"]  (domain valtozok)
  c) F401 reexport (58): __init__.py → __all__ VAGY noqa: F401
  d) B904 (46): raise X → raise X from e
  e) F841 (24): egyenkent side-effect check
  REGRESSZIO: pytest tests/unit/ -q → PASS

A1.3 — Format: `ruff format src/ tests/ skills/` → 0 diff

A1.4 — pyproject.toml ruff config veglegesites:
  [tool.ruff]
  line-length = 100
  target-version = "py312"
  [tool.ruff.lint.per-file-ignores]
  "skills/**/*.py" = ["N806", "N803"]
  "tests/**/*.py" = ["S101"]

GATE CHECK: /lint-check → 0 error, 0 format diff ← TILOS tovabblepni ha FAIL
```

**Deliverable:** 0 ruff error, pyproject.toml config, CI PASS

---

## A2: Security Hardening — 1-2 session

> **Gate:** Biztonsagi audit 0 HIGH, 0 MEDIUM.
> **FONTOS:** JWT csere + session expiry UI — EGYUTT, mert osszefuggnek.

```
A2.1 — JWT atiras PyJWT RS256-ra:
  - security/auth.py: sajat HMAC impl TOROLVE → PyJWT (mar fuggoseg!)
  - RS256 kulcspar: scripts/generate_jwt_keys.sh
  - JWT_PRIVATE_KEY, JWT_PUBLIC_KEY env var
  - Dual-mode atmeneti periodus:
    * 1. fazis: uj RS256 token kiadasa, regi HMAC token ELFOGADASA (1 verzioig)
    * 2. fazis (v1.2.3+): regi HMAC token ELUTASITVA
  - Tesztek: login, verify, expiry, invalid, dual-mode

A2.2 — JWT secret enforcement:
  - Prod: KOTELEZ env var (>= 32 char), hiba ha hianyzik
  - Dev: WARNING log, alapertelmezett OK

A2.3 — Session lejarat → UI force logout:
  - Backend: 401 Unauthorized response ha token lejart
  - Frontend (aiflow-admin):
    a) fetchApi() interceptor: 401 → automatikus redirect /login-ra
    b) Token expiry check: JWT decode → exp mezo → setInterval (60s)
    c) Ha exp < now + 5min: WARNING banner ("Session lejár X perc mulva")
    d) Ha exp < now: localStorage.removeItem("token") → redirect /login
    e) Refresh token opcionalis (long-lived refresh + short-lived access)
  - ELLENORZES: login → varj 5 perc → banner → varj token lejarat → auto logout

A2.4 — CORS szukites:
  - allow_methods: ["GET", "POST", "PUT", "DELETE", "PATCH"]
  - allow_headers: ["Accept", "Content-Type", "Authorization"]
  - allow_origins: AIFLOW_CORS_ORIGINS env var (lista)

A2.5 — Rate limiter middleware bekotes:
  - api/middleware.py: RateLimiter integracio
  - /auth/*: 10 req/min (brute force vedelem)
  - /api/*: 100 req/min (altalanos)
  - 429 Too Many Requests → Retry-After header

A2.6 — File upload vedelem:
  - pathlib.resolve() + is_relative_to(UPLOAD_DIR)
  - Max file size: 50MB (configurable)
  - Filename: werkzeug.utils.secure_filename()

A2.7 — Security headers middleware:
  - X-Content-Type-Options: nosniff
  - X-Frame-Options: DENY
  - Strict-Transport-Security (HTTPS)
  - Content-Security-Policy: script-src 'self'

GATE CHECK: Biztonsagi audit ujrafutatva → 0 HIGH, 0 MEDIUM ← TILOS tovabblepni ha FAIL
```

**Deliverable:** PyJWT RS256, UI force logout, rate limit, CORS, headers, 10+ security test

---

## A3: Stub Cleanup — 1 session

> **Gate:** `grep -r "placeholder" src/aiflow/` → csak tudatos, dokumentalt esetek.

```
A3.1 — Kafka stub TORLES (24 placeholder):
  - TOROLNI: src/aiflow/contrib/messaging/kafka.py
  - TOROLNI: src/aiflow/tools/kafka.py
  - MEGTARTANI: execution/messaging.py (in-memory broker, mukodo)
  
A3.2 — CLI placeholder rendezés (7):
  - NotImplementedError + typer.echo("Not implemented yet — planned for v1.3")
  - Megtartjuk a CLI interface-t az oszinte hibauzenettel

A3.3 — Parser stub torles (4):
  - pdf_parser.py, docx_parser.py → Docling adapter hivatkozas
  
A3.4 — Evaluator placeholder fix (2):
  - llm_rubric_placeholder → torles (Promptfoo helyettesiti)

A3.5 — Duplikalt registry konszolidacio (8):
  - skills/registry.py → re-export skill_system/registry.py-bol

A3.6 — Egyeb (16): egyenkent elbiralas (torles / NotImplemented / megtartas)

A3.7 — STUB_INVENTORY.md: megmaradt tudatos stubok listaja + indoklas

GATE CHECK: grep "placeholder\|stub" → csak dokumentalt esetek ← TILOS tovabblepni ha FAIL
```

**Deliverable:** ~40 placeholder torolve, inventory dokumentum

---

## A4: Hianyzo Alapfunkciok — 1 session

> **Gate:** Minden alapfunkcio mukodik, nincs "hazugo" stub.

```
A4.1 — Pipelines templates szekció (P1 post-sprint):
  - Pipelines.tsx: templates szekció UI
  - GET /api/v1/pipelines/templates/list → 6 template kartya
  - "Deploy" gomb implementacio

A4.2 — Templates route conflict (P2 post-sprint):
  - /{pipeline_id} vs /templates route sorrend fix
  - Explicit /templates path ELORE a router-ben

A4.3 — DataTable infinite re-render fix:
  - DataTable.tsx:91 — useEffect fuggoseg hurok
  - Fix: dependency array + useMemo

A4.4 — 404 resource loading fix:
  - Monitoring, Costs: hianyzo endpoint → fetchApi hiba kezeles

A4.5 — E2E console error filter ELTAVOLITAS:
  - Jelenlegi: "Maximum update depth", "Failed to load resource" filterezve
  - Cel: 0 filter, 0 valos error

GATE CHECK: 102+ E2E PASS, 0 console error (STRICT, nem filterezve)
```

**Deliverable:** P1+P2 megoldva, DataTable fix, 0 console error

---

## A5: Sprint A Regresszio + Post-Audit — 1 session

> **KRITIKUS FAZIS: Ez az ellenorzo pont! Nem szabad kihagyni!**
> **Cel:** Minden A0-A4 javitas VALOS verifikalasa, nincs uj bug, nincs kihagyott item.

```
A5.1 — Teljes regresszio:
  a) pytest tests/unit/ -q → ALL PASS (1083+ teszt)
  b) pytest tests/e2e/ -v → ALL PASS (102+ teszt, 0 filter!)
  c) cd aiflow-admin && npx tsc --noEmit → 0 error
  d) /lint-check → 0 ruff error, 0 format diff
  e) smoke_test.sh → ALL PASS (10/10 endpoint)

A5.2 — Biztonsagi POST-audit (ujrafutatas):
  - UJRA megvizsgalni MINDEN A2-ben javitott pontot:
  | # | Eredeti problema | Javitas (A2) | Post-audit eredmeny |
  |---|-----------------|-------------|-------------------|
  | 1 | Sajat JWT | PyJWT RS256 | [ ] VERIFIED / OPEN |
  | 2 | Default secret | Prod enforce | [ ] VERIFIED / OPEN |
  | 3 | Session lejarat UI | Force logout | [ ] VERIFIED / OPEN |
  | 4 | CORS * | Explicit lista | [ ] VERIFIED / OPEN |
  | 5 | Rate limit missing | Middleware | [ ] VERIFIED / OPEN |
  | 6 | File upload | Path traversal fix | [ ] VERIFIED / OPEN |
  | 7 | Security headers | CSP + HSTS | [ ] VERIFIED / OPEN |
  - Ha BARMELYIK OPEN → VISSZA A2-re, javitas, UJRA A5

A5.3 — Stub POST-audit:
  - grep scan: maradt-e placeholder ami nem dokumentalt?
  - STUB_INVENTORY.md konzisztens a valosassal?

A5.4 — CI POST-audit:
  - Push → GitHub Actions → MIND ZOLD?
  - Ha FAIL → javitas, push, ujra check

A5.5 — Audit riport generalas:
  ```
  === SPRINT A POST-AUDIT RIPORT ===
  Datum: YYYY-MM-DD
  
  Biztonsag:    X/7 VERIFIED, Y OPEN → [PASS/FAIL]
  Ruff:         0 error → [PASS/FAIL]
  CI/CD:        4/4 ZOLD → [PASS/FAIL]
  Stubs:        X torolve, Y dokumentalt → [PASS/FAIL]
  E2E:          102+ PASS, 0 filter → [PASS/FAIL]
  Unit:         1083+ PASS → [PASS/FAIL]
  
  SPRINT A VERDICT: [PASS — ready for v1.2.2 tag] / [FAIL — items to fix]
  ```

GATE CHECK: MINDEN sor PASS ← TILOS v1.2.2 tag ha barmelyik FAIL
```

**Deliverable:** Audit riport, minden VERIFIED, v1.2.2 tag

---

## A6: Version Tag + Merge — fél session

```
A6.1 — pyproject.toml: version = "1.2.2"
A6.2 — git tag v1.2.2
A6.3 — Squash merge → main (clean history)
A6.4 — 58_POST_SPRINT_HARDENING_PLAN.md: Sprint A = DONE
A6.5 — CLAUDE.md + 01_PLAN/CLAUDE.md: szamok frissitese
```

**Deliverable:** v1.2.2 tag, main-en ZOLD CI

---

## Sprint A Utemterv

```
Session 15: A0 (CI/CD Green) ──────── ELSO, BLOKKOLO
Session 16: A1.1 (Ruff batch fix) ── 548 auto-fix
Session 17: A1.2+A3 (Ruff manual + Stubs) ── 686 manual + 61 stub
Session 18: A2 (Security + JWT session) ──── JWT, CORS, rate limit, UI logout
Session 19: A4 (Hianyzo alapfunkciok) ────── P1, P2, DataTable, 404
Session 20: A5 (Post-audit + regresszio) ── MINDEN ellenorzes
Session 21: A6 (v1.2.2 tag + merge) ─────── Final
```

---

# SPRINT B: Szolgaltatas Excellence (v1.3.0)

> **Branch:** `feature/v1.3.0-service-excellence`
> **Elofeltetel:** Sprint A COMPLETE (v1.2.2 tagged)
> **Cel:** Minden szolgaltatas egyenkent magas szintre hozasa — kod, prompt, modell, UI
> **Vegtermek:** v1.3.0 tag, 130+ uj service test, 6/6 skill 95%+ promptfoo

## B0: Service Hardening Keretrendszer — fél session

> **Cel:** Kozos checklist es metodologia definiálasa MIELOTT szolgaltatasonkent dolgozunk.

### 8 Pontos Production Checklist (minden szolgaltatasra)

```
[ ] 1. UNIT TESZT — >= 5 teszt, >= 70% coverage
[ ] 2. INTEGRACIOS TESZT — >= 1 valos DB-vel (ha DB-t hasznal)
[ ] 3. API TESZT — minden endpoint curl-lel tesztelve, source=backend
[ ] 4. PROMPT TESZT — promptfoo >= 95% pass (ha LLM-et hasznal)
[ ] 5. ERROR HANDLING — minden hiba AIFlowError leszarmazott, is_transient flag
[ ] 6. LOGGING — structlog, NEM print(), event+key=value format
[ ] 7. DOKUMENTACIO — docstring a fo osztalyon + publikus metodusokon
[ ] 8. UI — kapcsolodo oldal mukodik, source badge, 0 console error
```

### Prompt Finomhangolas Metodologia (skill-ekre)

```
MERES → DIAGNOZIS → JAVITAS → VALIDALAS → DOKUMENTALAS

1. MERES: npx promptfoo eval → baseline pass rate rogzites
2. DIAGNOZIS: FAIL test case-ek elemzese → mi a root cause?
   - Prompt nem eleg specifikus? → few-shot pelda hozzaadas
   - Output format hiba? → JSON schema szigoritas
   - Nyelvi problema? → explicit nyelv specifikacio
   - Hallucinacio? → grounding rules erosites
3. JAVITAS: prompt YAML modositas (MINDIG verziokezelt!)
4. VALIDALAS: npx promptfoo eval → 95%+?
   - Ha IGEN → kovetkezo skill
   - Ha NEM → UJRA 2-3 (max 3 iteracio, utana modell csere)
5. DOKUMENTALAS: CHANGELOG megjegyzes a prompt fajlban
```

### Modell Optimalizacio Metodologia

```
1. BASELINE: Langfuse cost dashboard → per-service koltseg
2. KISERLET: gpt-4o → gpt-4o-mini csere OTT ahol scoring/extraction (nem generativ)
3. A/B: Promptfoo --providers gpt-4o,gpt-4o-mini → minoseg osszehasonlitas
4. DONTES: < 3% minoseg esés → olcsobb modell ELFOGADVA
5. TOKEN: prompt tomorites — felesleges ismetles, long preamble rovidites
6. CACHE: embedding cache Redis (TTL=1h), classifier cache (confidence > 0.95)
```

---

## B1: Core AI Szolgaltatasok — 2-3 session

> **Prioritas: P0 — legmagasabb uzleti ertek, legtobb hasznalat**

### B1.1 aszf_rag_chat (RAG Chat) — LEGKRITIKUSABB

```
KOD:
  - rag_engine: connection pooling + query timeout
  - vector_ops: hybrid search (BM25 + HNSW) parameter tuning
  - reranker: BGE v2-m3 validalas, FlashRank fallback teszt
  - 5 unit test rag_engine + 5 unit test vector_ops + 5 unit test reranker

PROMPT (jelenlegi: 86% → cel: 95%):
  - answer_generator.yaml: citation enforcement erosites
    * Problema: valasz gyakran nem hivatkozik forrásra
    * Fix: "EVERY claim MUST include [Source: chunk_id]" explicit szabaly
  - hallucination_detector.yaml: scoring rubric kalibralas
    * Problema: false positive (valos valasz hallucination-nek jelolve)
    * Fix: confidence threshold finomhangolas (0.7 → 0.6)
  - query_rewriter.yaml: magyar → angol embedding query mapping javitas
    * Problema: magyar szo rend angol embedding-nek rossz
    * Fix: explicit "translate the query concept, not word-by-word" instruction
  - UJ test case-ek: 7 → 12 (jogi kerdes, osszetetett, "nem tudom", hallucinacio)

MODELL:
  - Jelenlegi: gpt-4o (answer), gpt-4o-mini (rewrite, hallucination, citation)
  - Kiserlet: answer gpt-4o → gpt-4o-mini (koltseg: -60%)
  - Elfogadasi kriterium: promptfoo < 3% esés a csere utan

UI:
  - RAG chat oldal: streaming SSE validalas
  - Collection kezelés: list/create/delete/stats funkciok
  - Source badge: backend/demo

CHECKLIST: [ ]1 [ ]2 [ ]3 [ ]4 [ ]5 [ ]6 [ ]7 [ ]8
```

### B1.2 email_intent_processor — P0

```
KOD:
  - Intent discovery: uj intent tipusok auto-felismeres
  - Entity extraction: magyar cim/nev/telefon regex + LLM hibrid
  - Routing: multi-intent email → parallel route
  - 5 unit test email_connector + 5 unit test classifier

PROMPT (jelenlegi: ~85% → cel: 95%):
  - intent_classifier.yaml: intent catalog bovites (8 → 12 intent tipus)
    * Uj: "szamlalekerdezes", "reklamacio", "szerzodes_modositas", "altalanos_kerdes"
  - entity_extractor.yaml: magyar entitasok
    * Adoszam: \d{8}-\d-\d{2} regex + LLM validalas
    * Bankszamlaszam: \d{8}-\d{8}(-\d{8})? regex
    * Cim: strukturalt (iranyitoszam, varos, utca, hazszam)
  - priority_scorer.yaml: sulyossag-alapu prioritas
    * Surgo: "azonnali", "surgos", "hataridő" kulcsszavak + kontextus
  - routing_decider.yaml: komplex routing szabalyok
  - UJ test case-ek: 11 → 16 (multi-intent, csatolmany, spam, magyar)

MODELL:
  - Jelenlegi: gpt-4o-mini (minden) — jo koltseg/minoseg arany
  - Kiserlet: entity_extractor → gpt-4o (osszetett entitasokra)

UI:
  - Emails oldal: connector config panel
  - Intent schema CRUD: /intent-schemas → UI form

CHECKLIST: [ ]1 [ ]2 [ ]3 [ ]4 [ ]5 [ ]6 [ ]7 [ ]8
```

---

## B2: Document & Diagram Szolgaltatasok — 1-2 session

> **Prioritas: P1 — fontos de stabilabb**

### B2.1 process_documentation — P1

```
KOD:
  - Diagram generator: Mermaid → BPMN XML export javitas
  - DrawIO export minoseg
  - 5 unit test diagram_generator

PROMPT (jelenlegi: ~90% → cel: 95%):
  - mermaid_flowchart.yaml: komplex folyamatok (10+ lepes)
  - elaborator.yaml: strukturalt output (heading hierarchy)
  - UJ test case-ek: 11 → 15 (komplex, minimalis, idegen nyelv)

MODELL:
  - Kiserlet: elaborator gpt-4o → gpt-4o-mini (ha minoseg megmarad)

CHECKLIST: [ ]1 [ ]2 [ ]3 [ ]4 [ ]5 [ ]6 [ ]7 [ ]8
```

### B2.2 invoice_processor — P1

```
KOD:
  - PDF extraction: Docling config finomhangolas
  - Multi-page szamla osszefuzes
  - Export: CSV/Excel/JSON validacio
  - 5 unit test document_extractor (invoice kontextus)

PROMPT (jelenlegi: ~80% → cel: 95%):
  - invoice_classifier.yaml: szamla vs. nem-szamla precision
  - field_extractor.yaml:
    * AFO szam, adoszam, bankszamla regex + LLM hibrid validalas
    * HUF/EUR/USD + ISO 4217 + AFA kulcsok (5%, 18%, 27%)
  - UJ test case-ek: 10 → 15 (scan, kezi, kulfoldi, tobboldas)

MODELL:
  - Kiserlet: gpt-4o-mini vision (kep-alapu extraction)

CHECKLIST: [ ]1 [ ]2 [ ]3 [ ]4 [ ]5 [ ]6 [ ]7 [ ]8
```

### B2.3 document_extractor service — P1

```
KOD:
  - Docling config: table extraction, heading detection
  - Free text extraction: LLM query fine-tuning
  - Multi-format: PDF + DOCX + XLSX + HTML
  - 5 unit test

CHECKLIST: [ ]1 [ ]2 [ ]3 [ ]5 [ ]6 [ ]7 [ ]8
```

---

## B3: Infrastructure Service Tesztek — 2 session

> **Prioritas: P2 — minden service-nek kell unit test**

### B3.1 Session 1: Core infra (13 service, 65 test)

```
Sorrend (fuggosgei grafikon szerint):
 1. cache (5) — Redis hit/miss/evict/TTL/pattern
 2. config (5) — versioning CRUD, default fallback
 3. health_monitor (5) — service status, dependency check
 4. audit (5) — log create/query/filter/retention
 5. schema_registry (5) — JSON schema CRUD/validate
 6. notification (5) — email template, delivery retry
 7. human_review (5) — HITL workflow, SLA timer
 8. media_processor (5) — ffmpeg probe, format detect
 9. diagram_generator (5) — Mermaid render, BPMN export
10. rpa_browser (5) — page navigate, screenshot
11. rate_limiter (5) — bucket fill/drain, 429 trigger
12. resilience (5) — circuit open/half-open/close, retry
13. classifier (5) — ML predict, confidence threshold
```

### B3.2 Session 2: v1.2.0 szolgaltatasok (13 service, 65 test)

```
14. data_router (5) — routing rules, priority
15. service_manager (5) — lifecycle, health
16. reranker (5) — score, sort, top-K
17. advanced_chunker (5) — 6 strategia: fixed/semantic/sentence/paragraph/recursive/sliding
18. data_cleaner (5) — normalize, deduplicate
19. metadata_enricher (5) — auto-tag, entity link
20. vector_ops (5) — insert/search/delete/similarity
21. advanced_parser (5) — multi-format, fallback chain
22. graph_rag (5) — entity graph, traversal query
23. quality (5) — metric collect, threshold alert
24. email_connector (5) — IMAP connect, fetch, filter
25. rag_engine (5) — ingest, query, hybrid search
26. data_router extra (5) — ha van ido
```

**Deliverable:** 130 uj unit test, coverage >= 70% services/

---

## B4: Cubix + QBPP Skill Finomhangolas — 1 session

> **Prioritas: P2/P4**

```
B4.1 — cubix_course_capture (P2):
  PROMPT (jelenlegi: ~90% → cel: 95%):
  - transcript_structurer.yaml: idokod pontossag
  - UJ test case-ek: 5 → 8 (rovid video, rossz hang, angol nyelvu)
  MODELL: gpt-4o-mini megmarad (jo koltseg/minoseg)

B4.2 — qbpp_test_automation (P4):
  DONTES: Implementaljuk VAGY toroljuk?
  HA IGEN:
    - __main__.py implementacio (Robot Framework integracio)
    - test_generator.yaml (UJ prompt): RF teszt generalas
    - locator_finder.yaml (UJ prompt): UI elem azonosito
    - Promptfoo: valos test case-ek (nem stub)
    - Cel: 90%+ (uj skill, alacsonyabb kuszob)
  HA NEM:
    - Skill mappa torles, CLAUDE.md frissites (5 skill)
```

---

## B5: Modell Optimalizacio + Koltseg Csokkenés — 1 session

> **Gate:** >= 20% koltseg csokkenese VAGY >= 5% minoseg javulasa

```
B5.1 — Koltseg baseline:
  - Langfuse cost dashboard → per-service koltseg export
  - Token count: prompt_tokens + completion_tokens per call

B5.2 — Modell csere kísérletek:
  | Prompt | Jelenlegi | Kiserlet | Kriterium |
  |--------|-----------|----------|-----------|
  | pd/reviewer | gpt-4o | gpt-4o-mini | < 3% esés |
  | pd/elaborator | gpt-4o | gpt-4o-mini | < 3% esés |
  | rag/answer | gpt-4o | gpt-4o-mini | < 3% esés |
  | rag/citation | gpt-4o-mini | megmarad | — |
  | email/* | gpt-4o-mini | megmarad | — |
  | invoice/extract | gpt-4o | gpt-4o-mini | < 3% esés |
  
  Metodologia: promptfoo --providers gpt-4o,gpt-4o-mini → A/B osszehas

B5.3 — Token optimalizacio:
  - Hosszu system prompt: felesleges ismetles torles
  - Few-shot: 6 → 3 (ha minoseg megmarad)
  - Cel: >= 15% token count csokkenés

B5.4 — Cache strategia:
  - Embedding cache: Redis TTL=1h (ismétlődő query)
  - Classifier cache: confidence > 0.95 → cache (TTL=24h)
  - Cel: cache hit rate >= 30%

B5.5 — Koltseg riport:
  - Per-skill koltseg/query
  - Havi becslés (1000 query/nap)
  - Optimalizalt vs. eredeti osszehasonlitas
```

**Deliverable:** Modell matrix, koltseg riport, >= 20% koltseg csokkenés

---

## B6: UI Integracio + Per-Service Polish — 1-2 session

> **Cel:** Minden szolgaltatas UI oldala mukodik valosan, nincs demo/mock adat.

```
B6.1 — Szolgaltatas-oldal audit:
  MINDEN oldal (17 db) ellenorzese:
  | Oldal | Backend source | Valos adat | Console error |
  |-------|---------------|-----------|--------------|
  | Documents | ? | ? | ? |
  | Emails | ? | ? | ? |
  | RAG | ? | ? | ? |
  | ... (mind a 17) | | | |

B6.2 — Demo → Backend migracio:
  - Oldalak ahol "demo" source: backend integration fix
  - fetchApi hiba kezeles: retry gomb, error state

B6.3 — Uj UI elemek (ha szukseges):
  - Intent schema CRUD form (B1.2 kapcsan)
  - Collection management (B1.1 kapcsan)
  - Cost dashboard bovites (B5.5 kapcsan)

B6.4 — Dark mode + responsive check:
  - Minden oldal: dark mode WCAG AA kontraszt
  - Mobile: 768px breakpoint-on olvashato
```

---

## B7: Sprint B Regresszio + Post-Audit + v1.3.0 — 1 session

> **KRITIKUS: Ugyanaz a rigorozus ellenorzes mint A5, de Sprint B-re!**

```
B7.1 — Teljes regresszio:
  a) pytest tests/unit/ -q → ALL PASS (1083 + 130 uj = 1213+ teszt)
  b) pytest tests/e2e/ -v → ALL PASS (102+ teszt, STRICT 0 filter)
  c) cd aiflow-admin && npx tsc --noEmit → 0 error
  d) /lint-check → 0 error
  e) smoke_test.sh → ALL PASS
  f) npx promptfoo eval → 6/6 skill 95%+ PASS

B7.2 — Szolgaltatas erettseg POST-audit:
  | Szolgaltatas | Checklist (8 pont) | Promptfoo % | Modell | Status |
  |-------------|-------------------|-------------|--------|--------|
  | aszf_rag_chat | ?/8 | ?% | ? | ? |
  | email_intent | ?/8 | ?% | ? | ? |
  | process_docs | ?/8 | ?% | ? | ? |
  | invoice | ?/8 | ?% | ? | ? |
  | cubix | ?/8 | ?% | ? | ? |
  | qbpp | ?/8 | ?% | ? | ? |

B7.3 — Koltseg POST-audit:
  - Langfuse: optimalizalt koltseg vs. baseline
  - Cel: >= 20% csokkenés teljesult?

B7.4 — Sprint B audit riport:
  ```
  === SPRINT B POST-AUDIT RIPORT ===
  Service tesztek:     130/130 PASS → [PASS/FAIL]
  Prompt minoseg:      6/6 skill 95%+ → [PASS/FAIL]
  Koltseg optimalizacio: X% csokkenés → [PASS/FAIL]
  E2E (strict):        102+ PASS, 0 filter → [PASS/FAIL]
  Unit:                1213+ PASS → [PASS/FAIL]
  
  SPRINT B VERDICT: [PASS — ready for v1.3.0] / [FAIL — items to fix]
  ```

B7.5 — Version tag:
  - pyproject.toml: version = "1.3.0"
  - git tag v1.3.0
  - Merge to main (squash)
```

**Deliverable:** v1.3.0 tag, audit riport, minden PASS

---

## Sprint B Utemterv

```
Session 22: B0 (Keretrendszer) + B1.1 start (aszf_rag prompt) 
Session 23: B1.1 (aszf_rag kod+teszt) + B1.2 (email_intent prompt)
Session 24: B1.2 (email_intent kod+teszt) + B2.1 (process_docs)
Session 25: B2.2 (invoice) + B2.3 (doc_extractor)
Session 26: B3.1 (Core infra tesztek — 13 service)
Session 27: B3.2 (v1.2.0 szolgaltatas tesztek — 13 service)
Session 28: B4 (cubix + qbpp) + B5 (model optimization)
Session 29: B6 (UI integration + polish)
Session 30: B7 (Post-audit + regresszio + v1.3.0)
```

---

## Teljes Utemterv (Sprint A + B)

```
=== SPRINT A: Infrastruktura & Biztonsag (v1.2.2) ===
Session 15: A0 — CI/CD Green ────────────────── BLOKKOLO
Session 16: A1.1 — Ruff batch fix (548) ────── /lint-check --fix
Session 17: A1.2+A3 — Ruff manual + Stubs ──── 686 manual + 61 stub
Session 18: A2 — Security + JWT session UI ──── JWT RS256 + force logout
Session 19: A4 — Hianyzo alapfunkciok ────────── P1, P2, DataTable, 404
Session 20: A5 — POST-AUDIT + regresszio ────── MINDEN ellenorzes!
Session 21: A6 — v1.2.2 tag + merge ─────────── Final

=== SPRINT B: Szolgaltatas Excellence (v1.3.0) ===
Session 22: B0+B1 — Keretrendszer + aszf_rag ── P0 skill start
Session 23: B1 — aszf_rag + email_intent ────── P0 prompt tuning
Session 24: B1+B2 — email + process_docs ─────── P0/P1 skill
Session 25: B2 — invoice + doc_extractor ─────── P1 skill
Session 26: B3.1 — Core infra tesztek (65) ──── 13 service
Session 27: B3.2 — v1.2.0 tesztek (65) ──────── 13 service
Session 28: B4+B5 — cubix + model optimization  P2 + koltseg
Session 29: B6 — UI integracio + polish ──────── Per-service UI
Session 30: B7 — POST-AUDIT + v1.3.0 ─────────── MINDEN ellenorzes!
```

**Osszes:** ~16 session, ~4,000 LOC, ~200+ uj teszt, 2 version tag

---

## Sikerkriteriumok

### Sprint A (v1.2.2)

| # | Kriterium | Mertek |
|---|-----------|--------|
| 1 | CI/CD MIND ZOLD | 4/4 workflow PASS |
| 2 | Ruff 0 error | /lint-check → CLEAN |
| 3 | 0 HIGH/MEDIUM security | Post-audit verified |
| 4 | Session lejarat → UI logout | JWT exp → auto redirect |
| 5 | 0 stub (nem tudatos) | STUB_INVENTORY.md clean |
| 6 | P1+P2 post-sprint DONE | Pipelines templates UI |
| 7 | 0 console error (strict) | E2E filter nelkul |
| 8 | Post-audit PASS | A5 riport MINDEN sor PASS |

### Sprint B (v1.3.0)

| # | Kriterium | Mertek |
|---|-----------|--------|
| 1 | 130+ service unit test | 26 service × 5 test |
| 2 | 6/6 skill 95%+ promptfoo | Baseline → 95%+ |
| 3 | >= 20% koltseg csokkenés | Langfuse riport |
| 4 | 8/8 checklist PASS per skill | Production checklist |
| 5 | 0 demo-only oldal | Minden source=backend |
| 6 | Post-audit PASS | B7 riport MINDEN sor PASS |
| 7 | v1.3.0 tag | Squash merge main |

---

## Slash Command Referencia

| Command | Mikor | Fazis |
|---------|-------|-------|
| `/lint-check` | Ruff + tsc + format summary | A1, es MINDEN fazis vegen |
| `/lint-check --fix` | Auto-fix safe issues | A1.1 |
| `/regression` | Unit + E2E regresszio | A5, B7, es MINDEN commit elott |
| `/quality-check` | Promptfoo + koltseg | B1-B5 |
| `/service-test` | Backend + API + UI e2e | B1-B4 |
| `/dev-step` | Fejlesztes + teszt + commit | Minden fazis |

---

## Progress Tracking

### Sprint A

| Fazis | Tartalom | Allapot | Datum | Commit |
|-------|----------|---------|-------|--------|
| A0 | CI/CD Green | TODO | — | — |
| A1 | Ruff 1,234 → 0 | TODO | — | — |
| A2 | Security + JWT session | TODO | — | — |
| A3 | Stub Cleanup | TODO | — | — |
| A4 | Hianyzo alapfunkciok | TODO | — | — |
| A5 | POST-AUDIT + regresszio | TODO | — | — |
| A6 | v1.2.2 tag | TODO | — | — |

### Sprint B

| Fazis | Tartalom | Allapot | Datum | Commit |
|-------|----------|---------|-------|--------|
| B0 | Keretrendszer definiálás | TODO | — | — |
| B1 | Core AI skill-ek (aszf_rag, email) | TODO | — | — |
| B2 | Document skill-ek (process_docs, invoice) | TODO | — | — |
| B3 | Infrastructure service tesztek (130) | TODO | — | — |
| B4 | Cubix + QBPP skill-ek | TODO | — | — |
| B5 | Modell optimalizacio | TODO | — | — |
| B6 | UI integracio + polish | TODO | — | — |
| B7 | POST-AUDIT + v1.3.0 | TODO | — | — |
