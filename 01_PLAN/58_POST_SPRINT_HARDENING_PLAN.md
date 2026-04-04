# AIFlow v1.2.2 — Post-Sprint Hardening Plan

> **Szulo terv:** `57_PRODUCTION_READY_SPRINT.md` (v1.2.1 COMPLETE)
> **Elozmeny:** v1.2.1 COMPLETE (S1-S14, 2026-04-04) — UI, observability, quality, 102 E2E
> **Cel:** CI/CD zold, kod minoseg, biztonsag, stub eltavolitas, szolgaltatas-szintu finomhangolas
> **Branch:** `feature/v1.2.2-hardening`
> **Becsult idotartam:** ~8-12 session (H0-H7 fazis)

---

## 0. Audit Eredmenyek Osszefoglalasa

### 0.1 Ruff Lint Audit (1,234 hiba)

| Terulet | Hibak | Auto-fix | Manual |
|---------|-------|----------|--------|
| `src/aiflow/` | 574 | 243 (42%) | 331 |
| `tests/` | 181 | 128 (71%) | 53 |
| `skills/` | 479 | 177 (37%) | 302 |
| **OSSZES** | **1,234** | **548 (44%)** | **686** |

**Top 5 szabalysertes:**
| Szabaly | Db | Leiras | Strategia |
|---------|-----|---------|-----------|
| E501 | 287 | Line too long (>100) | Manual refactor |
| I001 | 258 | Rendezetlen importok | `--fix` (biztonságos) |
| F401 | 147 | Nem hasznalt import | `--fix` (ellenorizve) |
| N806 | 117 | Nagybetus valtozo fuggvenyben | `noqa` / pyproject.toml override |
| F541 | 75 | Ures f-string | `--fix` (biztonságos) |

### 0.2 Biztonsagi Audit

| Sulyossag | Problema | Fajl | Megoldas |
|-----------|---------|------|---------|
| **HIGH** | Sajat JWT impl. PyJWT helyett | `security/auth.py:47-79` | PyJWT RS256-ra csere |
| **HIGH** | Default JWT secret `"dev-secret-..."` | `security/auth.py:47` | Prod-ban KOTELEZ env var |
| **MEDIUM** | CORS `allow_methods=["*"]` | `api/app.py:98` | Explicit GET/POST/PUT/DELETE |
| **MEDIUM** | Rate limiter NEM bekotve | `api/app.py` | Middleware integracio |
| **LOW** | Path traversal file upload | `api/v1/documents.py` | `pathlib.resolve()` + `.is_relative_to()` |
| **LOW** | API key SHA256 (nem bcrypt) | `security/auth.py:134` | DB migraciokor bcrypt-re |

### 0.3 Stub/Placeholder Audit (61 marker)

| Kategoria | Db | Fajlok | Prioritas |
|-----------|-----|--------|-----------|
| CLI commands (nem implementalt) | 7 | 4 CLI fajl | LOW (nincs user) |
| Kafka adapters (duplikalt stub) | 12 | 2 fajl | MEDIUM (torles) |
| Parser stubs (PDF/DOCX) | 4 | 2 fajl | LOW (Docling helyettesiti) |
| Evaluator placeholder (0.5 score) | 2 | 1 fajl | MEDIUM (rubric fix) |
| Prometheus metrics stub | 1 | 1 fajl | LOW (structlog elegseges) |
| Skill registry placeholders | 8 | 2 fajl | MEDIUM (consolidal) |
| Egyeb (vision, vault, prompt sync) | 27 | 5 fajl | MIXED |

### 0.4 CI/CD Allapot (PR #1 — 4 FAIL)

| Workflow | Trigger | Fo hiba | Fix |
|----------|---------|---------|-----|
| `ci.yml` | push/PR main | `skills/` benne ruff scope-ban | Scope szukites: `src/ tests/` |
| `ci-framework.yml` | PR src/** | Regi venv setup + ruff 574 error | `uv sync --dev` + ruff fix |
| `ci-skill.yml` | PR skills/** | Skill fuggoseg hianyzik | pyproject.toml extras |
| `nightly-regression.yml` | cron 03:00 | Nem releváns (nightly) | OK |

### 0.5 Szolgaltatas Erettseg (26 service, 6 skill)

| Szint | Szolgaltatasok | Jellemzo |
|-------|---------------|----------|
| **Production** (3) | rag_engine, classifier, document_extractor | Valos kod, tesztelt, prompt |
| **Partial** (20) | cache, email_connector, notification, human_review, diagram_generator, stb. | Van kod, van API, de NINCS unit test |
| **Stub** (3) | rate_limiter, resilience, qbpp_test_automation | Nincs valos mukodes |

**Skill-ek:**
| Skill | Allapot | Promptfoo | Prompt minoseg |
|-------|---------|-----------|---------------|
| process_documentation | WORKING | 11 test | Jo (5 prompt, Jinja2, JSON spec) |
| cubix_course_capture | WORKING | 5 test | Jo (STT + structurer) |
| aszf_rag_chat | WORKING | 7 test (86% pass) | Jo (5 prompt + 3 system) |
| email_intent_processor | IN_DEV | 11 test | Kozep (4 prompt, classifier OK) |
| invoice_processor | IN_DEV | 10 test | Kozep (5 prompt, multi-currency) |
| qbpp_test_automation | STUB | 5 test (stub) | Nincs prompt |

---

## 1. Fazis Struktura (H0-H7)

```
H0: CI/CD Green ──────────── 1 session (ELSO, mert minden mas erre epit)
H1: Ruff Cleanup ─────────── 1-2 session (batch fix + manual)
H2: Security Hardening ────── 1 session (JWT, CORS, rate limit)
H3: Stub Cleanup ────────��─── 1 session (Kafka torles, placeholder audit)
H4: Service Unit Tests ────── 2 session (26 service, min 5 test/service)
H5: Skill Prompt Tuning ──── 2-3 session (6 skill, promptfoo 95%+)
H6: Model Optimization ────── 1 session (cost/quality matrix, model selection)
H7: UI Fixes + Polish ─────── 1 session (DataTable loop fix, 404 fix)
```

**Osszes:** ~8-12 session, ~3,000 LOC

---

## 2. Reszletes Fazisok

### H0: CI/CD Green (PR #1 PASS) — 1 session

> **Cel:** GitHub Actions MIND ZOLD. Amig ez nem PASS, semmi mas nem mergelhet.
> **Gate:** PR #1 MINDEN workflow PASS.

```
H0.1 — ci.yml fix:
  - ruff scope: `src/ tests/` (skills/ KIHAGYVA — sajat workflow-ja van)
  - venv setup: `uv sync --dev` (nem `uv venv && uv pip install`)
  - ELLENORZES: push → CI ZOLD

H0.2 — ci-framework.yml fix:
  - Ugyanaz: `uv sync --dev`
  - ruff check CSAK `src/aiflow/ tests/` (konzisztens ci.yml-lel)
  - ELLENORZES: PR trigger → ZOLD

H0.3 — ci-skill.yml fix:
  - Skill fuggosegek: `uv sync --dev --extra skills` VAGY skill-szintu requirements
  - ELLENORZES: skills/ modositas → ZOLD

H0.4 — Vegso ellenorzes:
  - MINDEN workflow ZOLD a PR-en
  - Squash merge NEM itt — csak CI PASS eleres a cel
```

**Deliverable:** 4 workflow YAML fix, PR #1 MIND ZOLD

---

### H1: Ruff Cleanup (1,234 → 0) — 1-2 session

> **Cel:** Teljes codebase ruff-clean. Ez a CI PASS feltetele is.
> **Gate:** `ruff check src/ tests/ skills/` → 0 error

```
H1.1 — Safe batch fix (548 auto-fixable):
  SORREND (kockazat szerint):
  1. tests/: `ruff check tests/ --fix` (128 fix, legkisebb kockazat)
  2. src/aiflow/ import sort: `ruff check src/aiflow/ --fix --select I001,F541,UP017,UP035,UP041,UP045`
  3. skills/: `ruff check skills/ --fix --select I001,F541,UP017`
  ELLENORZES: pytest tests/unit/ -q → PASS (nincs regresszio)

H1.2 — Manual fixes (686 maradt):
  a) E501 (287 long line):
     - src/aiflow/: ~150 sor — logikai sorbontas
     - skills/: ~100 sor — prompt string bontas
     - tests/: ~37 sor — assert uzenet bontas
  b) N806/N803 (149 naming):
     - pyproject.toml `[tool.ruff.per-file-ignores]`:
       `"skills/**" = ["N806", "N803"]` (domain valtozok: DataFrame, BPMN, stb.)
  c) F401 reexport (58 unused import src/):
     - `__init__.py` fajlok: `__all__` hozzaadasa VAGY `noqa: F401`
     - Tobbi: valos torles
  d) B904 (46 raise without from):
     - `raise X` → `raise X from e` (except blokkban)
  e) F841 (24 unused variable):
     - Egyenkent: side-effect check, majd torles

H1.3 — Format check:
  `ruff format --check src/ tests/ skills/` → 0 diff
  ELLENORZES: CI ZOLD

H1.4 — pyproject.toml ruff config finomhangolas:
  [tool.ruff]
  line-length = 100
  target-version = "py312"

  [tool.ruff.lint.per-file-ignores]
  "skills/**/*.py" = ["N806", "N803"]       # domain valtozok
  "tests/**/*.py" = ["S101"]                 # assert hasznalat
  "src/aiflow/contrib/**" = ["N806"]         # legacy compat
```

**Deliverable:** 0 ruff error, pyproject.toml config, CI PASS

---

### H2: Security Hardening — 1 session

> **Cel:** OWASP Top 10 vedelem, JWT fix, rate limit bekotes.
> **Gate:** Biztonsagi audit 0 HIGH, 0 MEDIUM talalt.

```
H2.1 — JWT atiras PyJWT RS256-ra:
  - src/aiflow/security/auth.py: sajat HMAC impl → PyJWT
  - RS256 kulcspar generálas (scripts/generate_jwt_keys.sh)
  - JWT_PRIVATE_KEY, JWT_PUBLIC_KEY env var-ok
  - Tesztek: tests/unit/security/test_auth.py bovites
  - ELLENORZES: login + token verify + expiry + invalid token

H2.2 — JWT secret enforcement:
  - Prod mod: KOTELEZ AIFLOW_JWT_SECRET (>= 32 char), hiba ha hianyzik
  - Dev mod: alapertelmezett OK, de WARNING log
  - ELLENORZES: prod config nelkul inditas → hiba

H2.3 — CORS szukites:
  - allow_methods: ["GET", "POST", "PUT", "DELETE", "PATCH"]
  - allow_headers: ["Accept", "Content-Type", "Authorization"]
  - allow_origins: configurable lista (env var: AIFLOW_CORS_ORIGINS)
  - ELLENORZES: bongeszos teszt + curl

H2.4 — Rate limiter middleware bekotes:
  - src/aiflow/api/middleware.py: RateLimiter integracio
  - Per-endpoint config: /auth/* = 10/min, /api/* = 100/min
  - 429 Too Many Requests response
  - ELLENORZES: curl loop → 429

H2.5 — File upload vedelem:
  - pathlib.Path.resolve() + .is_relative_to(UPLOAD_DIR)
  - Max file size: 50MB (configurable)
  - Filename sanitization: werkzeug.utils.secure_filename()
  - ELLENORZES: traversal attempt → 400

H2.6 — Security headers:
  - X-Content-Type-Options: nosniff
  - X-Frame-Options: DENY
  - Strict-Transport-Security (HTTPS modban)
  - Content-Security-Policy: script-src 'self'
  - ELLENORZES: curl -I → headerek lathatoak
```

**Deliverable:** 0 HIGH/MEDIUM biztonsagi hiba, 6 unit test

---

### H3: Stub Cleanup — 1 session

> **Cel:** Halott kod eltavolitas, placeholder-ek rendberakasa.
> **Gate:** `grep -r "placeholder\|stub" src/aiflow/` → csak tudatos, dokumentalt esetek.

```
H3.1 — Kafka stub torles:
  - TOROLNI: src/aiflow/contrib/messaging/kafka.py (12 placeholder)
  - TOROLNI: src/aiflow/tools/kafka.py (12 placeholder — duplikalt!)
  - MEGTARTANI: src/aiflow/execution/messaging.py (in-memory broker, mukodo)
  - Kafka = "HALASZTVA post-v1.2.0" (dontes mar meghozva)
  - ELLENORZES: pytest → nincs import hiba

H3.2 — CLI placeholder rendezés:
  - eval_cmd.py, prompt.py, skill.py, workflow.py
  - Opcio A: NotImplementedError + `typer.echo("Not implemented yet")`
  - Opcio B: Torles (ha nincs user)
  - DONTES: Opcio A (megtartjuk a CLI interface-t, de oszinte hibauzenet)
  - ELLENORZES: `aiflow --help` → parancsok listazodnak

H3.3 — Parser stub konszolidacio:
  - pdf_parser.py, docx_parser.py → docling adapter-re hivatkozas
  - Regi pymupdf/python-docx stubs TOROLVE
  - ELLENORZES: import check → nincs torot hivatkozas

H3.4 — Evaluator placeholder fix:
  - scorers.py: `llm_rubric_placeholder` → valos LLM rubric (gpt-4o-mini)
  - VAGY: torles ha Promptfoo helyettesiti
  - ELLENORZES: eval pipeline test

H3.5 — Prompt sync placeholder:
  - prompts/sync.py: "Phase 5 Langfuse" → mar megoldva S7-ben
  - Torolni a regi placeholder kommentet
  - ELLENORZES: Langfuse sync mukodik

H3.6 — Duplikalt registry konszolidacio:
  - src/aiflow/skills/registry.py (regi) → src/aiflow/skill_system/registry.py (kanonikus)
  - Regi fajl: backward compat re-export VAGY torles
  - ELLENORZES: import check

H3.7 — Dokumentacio:
  - STUB_INVENTORY.md: megmaradt tudatos stubok listaja + indoklas
```

**Deliverable:** ~40 placeholder torolve, 2 duplikalt fajl eltavolitva, inventory dokumentum

---

### H4: Service Unit Tests (26 service) — 2 session

> **Cel:** Minden service-nek legyen legalabb 5 unit test.
> **Gate:** `pytest tests/unit/services/ -q` → 130+ teszt PASS, coverage >= 70%

```
H4.1 — Session 1: Core szolgaltatasok (13 service, ~65 test):
  Prioritas sorrend (uzleti ertek + hasznaltsag):
  1. rag_engine (5 test) — legfontosabb AI szolgaltatas
  2. document_extractor (5 test) — PDF/DOCX feldolgozas
  3. email_connector (5 test) — email beolvasas + IMAP
  4. classifier (5 test) — ML + LLM hibrid osztalyozas
  5. human_review (5 test) — HITL workflow + SLA
  6. notification (5 test) — multi-channel ertesites
  7. cache (5 test) — Redis cache hit/miss/evict
  8. diagram_generator (5 test) — Mermaid/BPMN render
  9. audit (5 test) — audit log CRUD
  10. config (5 test) — config versioning
  11. schema_registry (5 test) — JSON schema CRUD
  12. health_monitor (5 test) — service health check
  13. media_processor (5 test) — ffmpeg/STT

H4.2 — Session 2: v1.2.0 szolgaltatasok (13 service, ~65 test):
  14. data_router (5 test) — pipeline routing
  15. service_manager (5 test) — service lifecycle
  16. reranker (5 test) — BGE/FlashRank rerank
  17. advanced_chunker (5 test) — 6 chunking strategia
  18. data_cleaner (5 test) — adat tisztitas
  19. metadata_enricher (5 test) — metaadat kiegeszites
  20. vector_ops (5 test) — vector CRUD + similarity
  21. advanced_parser (5 test) — multi-format parser
  22. graph_rag (5 test) — GraphRAG query
  23. quality (5 test) �� minoseg metrikak
  24. rate_limiter (5 test) — rate limit logika
  25. resilience (5 test) ��� circuit breaker + retry
  26. rpa_browser (5 test) — Playwright RPA

H4.3 — Coverage report:
  pytest tests/unit/services/ --cov=aiflow.services --cov-report=term
  Cel: >= 70% coverage
```

**Deliverable:** 130+ uj unit test, 26 service tesztelve, coverage >= 70%

---

### H5: Skill Prompt Tuning (6 skill) — 2-3 session

> **Cel:** Minden skill promptfoo 95%+ pass rate, prompt minoseg javitas.
> **Gate:** `npx promptfoo eval -c skills/*/tests/promptfooconfig.yaml` → 95%+ PASS mind a 6 skill-nel.

```
H5.1 — Baseline meres (minden skill):
  npx promptfoo eval ��� jelenlegi pass rate-ek rogzitese
  Celok:
  - process_documentation: 95%+ (jelenlegi: ~90%)
  - aszf_rag_chat: 95%+ (jelenlegi: 86%)
  - email_intent_processor: 95%+ (jelenlegi: ~85%)
  - cubix_course_capture: 95%+ (jelenlegi: ~90%)
  - invoice_processor: 95%+ (jelenlegi: ~80%)
  - qbpp_test_automation: valos prompt kell (jelenlegi: STUB)

H5.2 — process_documentation prompt finomhangolas:
  a) classifier.yaml: few-shot peldak bovitese (3 �� 6 pelda)
  b) elaborator.yaml: output format szigoritas (JSON schema validation)
  c) mermaid_flowchart.yaml: Mermaid szintaxis szabalyok pontositasa
  d) Uj test case-ek: edge case-ek (ures input, tul rovid, idegen nyelv)
  e) ELLENORZES: promptfoo eval → 95%+

H5.3 — aszf_rag_chat prompt finomhangolas:
  a) answer_generator.yaml: forras-hivatkozas kenyszeritese (citation rules)
  b) hallucination_detector.yaml: pontosabb scoring rubric
  c) query_rewriter.yaml: magyar nyelvu query atalakitas javitasa
  d) Uj test case-ek: jogi kerdesek, osszetetett kerdesek, "nem tudom" esetek
  e) ELLENORZES: promptfoo eval → 95%+ (jelenlegi 86% → 95%)

H5.4 — email_intent_processor prompt finomhangolas:
  a) intent_classifier.yaml: intent catalog bovitese (hianyzo intent tipusok)
  b) entity_extractor.yaml: magyar nyelvu entitasok (nev, cim, szam)
  c) routing_decider.yaml: komplex routing szabalyok
  d) Uj test case-ek: multi-intent email, csatolmanyos email, spam
  e) ELLENORZES: promptfoo eval → 95%+

H5.5 — invoice_processor prompt finomhangolas:
  a) invoice_classifier.yaml: magyar szamla formatum specifikus szabalyok
  b) field_extractor.yaml: AFO szam, adoszam, bankszamlaszam regex validacio
  c) currency/VAT: ISO 4217 + HU AFA kulcsok (5%, 18%, 27%)
  d) Uj test case-ek: scan-elt szamla, kezi szamla, kulfoldi szamla
  e) ELLENORZES: promptfoo eval → 95%+

H5.6 — cubix_course_capture prompt finomhangolas:
  a) transcript_structurer.yaml: idokod pontossag javitasa
  b) Uj test case-ek: rovid video, hosszu eloadas, rossz minosegu hang
  c) ELLENORZES: promptfoo eval → 95%+

H5.7 — qbpp_test_automation valos prompt irasa:
  a) test_generator.yaml (UJ): Robot Framework teszt generalas
  b) locator_finder.yaml (UJ): UI elem azonosito generalas
  c) Promptfoo config: valos test case-ek (nem stub)
  d) __main__.py implementacio (jelenlegi: STUB)
  e) ELLENORZES: promptfoo eval → 90%+ (uj skill, alacsonyabb kuszob)
```

**Deliverable:** 6/6 skill 95%+ promptfoo, ~30 uj test case, 2 uj prompt YAML

---

### H6: Model Optimization — 1 session

> **Cel:** Koltseg/minoseg matrix, optimalis modell valasztas szolgaltasonkent.
> **Gate:** Koltseg csokkenese >= 20% VAGY minoseg javulasa >= 5% az optimalizalt szolgaltatasoknal.

```
H6.1 — Koltseg baseline meres:
  - Langfuse cost dashboard → jelenlegi koltseg per szolgaltatas
  - Token count per prompt per szolgaltatas
  - Jelenlegi modell mapping:
    * gpt-4o: elaborator, answer_generator, system prompts (draga, magas minoseg)
    * gpt-4o-mini: classifier, entity_extractor, hallucination_detector (olcso, gyors)
  
H6.2 — Modell csere kiserlet:
  a) gpt-4o → gpt-4o-mini csere OTT ahol a minoseg engedi:
     - process_documentation/reviewer: gpt-4o → gpt-4o-mini (scoring, nem generativ)
     - aszf_rag_chat/citation_extractor: gpt-4o → gpt-4o-mini (extrakció)
  b) Promptfoo A/B teszteles: eredeti vs. olcsobb modell
  c) Minoseg megtartasi kriterium: < 3% minoseg esés megengedett

H6.3 — Prompt tomorites (token optimalizacio):
  - Hosszu system promptok: felesleges ismetlesek torlese
  - Few-shot peldak: 6 → 3 (ha a minoseg megmarad)
  - Output format: JSON schema ref YAML-bol (nem inline)
  - ELLENORZES: token count csokkenese >= 15%

H6.4 — Cache strategia:
  - Ismétlődő queryknél: embedding cache (Redis TTL=1h)
  - Classifier eredmenyek: cache ha confidence > 0.95
  - ELLENORZES: cache hit rate >= 30% tipikus workload-nal

H6.5 — Koltseg riport generalas:
  - Per-skill koltseg/query
  - Per-service koltseg/futatas
  - Havi becsult koltseg 1000 query/nap szinten
  - Osszehasonlitas: optimalizalt vs. eredeti
```

**Deliverable:** Modell matrix, koltseg riport, >= 20% koltseg csokkenes

---

### H7: UI Fixes + Polish — 1 session

> **Cel:** Pre-existing UI bugok javitasa, amik az E2E-ben latszottak.
> **Gate:** 102 E2E teszt PASS + 0 console error (STRICT, nem filterezve).

```
H7.1 — DataTable infinite re-render fix:
  - aiflow-admin/src/components-new/DataTable.tsx:91
  - Problema: "Maximum update depth exceeded" — useEffect fuggoseg hurok
  - Fix: useEffect dependency array rendezese, useMemo a szarmmazott ertekekre
  - ELLENORZES: Documents + Emails oldal → 0 React warning

H7.2 — 404 resource loading fix:
  - Monitoring, Costs oldalak → "Failed to load resource: 404"
  - Ok: API endpoint nem letezik VAGY route hibas
  - Fix: hianyzo endpoint implementalas VAGY fetchApi hiba kezeles
  - ELLENORZES: Quality → Costs → Monitoring → 0 console error

H7.3 — Pipelines templates szekció (P1 post-sprint):
  - Pipelines.tsx: templates szekció hozzaadasa
  - GET /api/v1/pipelines/templates/list → 6 template kartya
  - "Deploy" gomb → POST /api/v1/pipelines/deploy (VAGY redirect)
  - ELLENORZES: Pipelines oldal → templates szekció latható

H7.4 — Templates route conflict fix (P2 post-sprint):
  - GET /api/v1/pipelines/templates → 500 "badly formed UUID"
  - Ok: /{pipeline_id} route matchel "templates"-re
  - Fix: explicit /templates route ELORE a router-ben (sorrend szamit)
  - ELLENORZES: curl /api/v1/pipelines/templates → 200

H7.5 — Console error filter eltavolitas E2E-bol:
  - Jelenlegi: "Failed to load resource", "Maximum update depth" filterezve
  - Cel: MINDEN console error VALOS hiba → 0 filterezve
  - ELLENORZES: pytest tests/e2e/ → 102 PASS 0 filter

H7.6 — E2E regression:
  - Teljes E2E suite: 102+ teszt → PASS
  - Teljes unit suite: 1083+ teszt → PASS (+ H4 uj tesztek)
```

**Deliverable:** 0 console error (filterezetlen), P1+P2 megoldva, Pipelines templates UI

---

## 3. Szolgaltatas-szintu Production Hardening Terv

> **Cel:** Minden szolgaltatas egyenkent magas szintre hozasa — kod, prompt, modell, UI.
> **Ez H4+H5+H6+H7 reszletezese szolgaltasonkent.**

### 3.1 Prioritasi Matrix

| # | Szolgaltatas | Uzleti ertek | Technikai erettseg | Prompt minoseg | Prioritas |
|---|-------------|-------------|-------------------|---------------|-----------|
| 1 | **aszf_rag_chat** | MAGAS | Partial | 86% pass | **P0 — ELSO** |
| 2 | **email_intent_processor** | MAGAS | Partial | ~85% pass | **P0** |
| 3 | **process_documentation** | MAGAS | Production | ~90% pass | **P1** |
| 4 | **invoice_processor** | MAGAS | Partial | ~80% pass | **P1** |
| 5 | **document_extractor** | KOZEP | Partial | N/A (nem LLM) | **P1** |
| 6 | **rag_engine** | MAGAS | Partial | N/A (service) | **P2** |
| 7 | **classifier** | KOZEP | Partial | N/A (ML+LLM) | **P2** |
| 8 | **cubix_course_capture** | ALACSONY | Production | ~90% pass | **P2** |
| 9 | **notification** | KOZEP | Partial | N/A | **P3** |
| 10 | **human_review** | KOZEP | Partial | N/A | **P3** |
| 11 | **qbpp_test_automation** | ALACSONY | Stub | STUB | **P4 — UTOLSO** |

### 3.2 Per-Szolgaltatas Hardening Checklist

Minden szolgaltatasra az alabbi **8 pontos checklist** kell PASS:

```
[ ] 1. Unit tesztek: >= 5 teszt, >= 70% coverage
[ ] 2. Integrációs teszt: >= 1 valos DB-vel (ha DB-t hasznal)
[ ] 3. API teszt: minden endpoint curl-lel tesztelve
[ ] 4. Prompt tesztek: promptfoo >= 95% pass (ha LLM-et hasznal)
[ ] 5. Error handling: minden hiba AIFlowError leszarmazott, is_transient flag
[ ] 6. Logging: structlog, NEM print(), event+key=value format
[ ] 7. Dokumentacio: docstring a fo osztalyon + publikus metodusokon
[ ] 8. UI: kapcsolodo oldalak mukodnek, source badge, 0 console error
```

### 3.3 Reszletes Szolgaltatas Tervek

#### P0/1: aszf_rag_chat (RAG Chat — legkritikusabb)

```
KOD:
  - rag_engine service: connection pooling check
  - vector_ops: hybrid search (BM25 + HNSW) tuning
  - reranker: BGE v2-m3 integracio validalas

PROMPT:
  - answer_generator: citation enforcement (jelenlegi: gyakran hiányzik)
  - hallucination_detector: scoring rubric kalibralas (false positive csokkentes)
  - query_rewriter: magyar nyelvű query → angol embedding query mapping

MODELL:
  - Jelenlegi: gpt-4o (answer), gpt-4o-mini (rewrite, hallucination)
  - Kiserlet: gpt-4o-mini az answer-re is (koltseg: -60%, minoseg: ?)
  - Megtartasi kriterium: < 3% minoseg esés promptfoo-n

UI:
  - RAG chat oldal: valos streaming (SSE), nem fake
  - Collection kezelés: create/delete/stats
  - Source indicator: backend/demo badge

TESZT:
  - 5 unit test (rag_engine service)
  - 5 unit test (vector_ops service)
  - 5 unit test (reranker service)
  - promptfoo: 86% → 95% (7 → 12 test case)
```

#### P0/2: email_intent_processor

```
KOD:
  - Intent discovery: uj intent tipusok automatikus felismerese
  - Entity extraction: magyar cim/nev/telefon regex + LLM
  - Routing: multi-intent email → parallel routing

PROMPT:
  - intent_classifier: intent catalog bovites (8 → 12 intent)
  - entity_extractor: magyar specifikus entitasok (adoszam, bankszla)
  - priority_scorer: sulyossag alapu prioritas (nem csak kulcsszo)

MODELL:
  - Jelenlegi: gpt-4o-mini (minden prompt) — jo
  - Kiserlet: gpt-4o az entity_extractor-ra (osszetett entitasok)
  - Alternativa: fine-tuned gpt-4o-mini (ha van eleg adat)

UI:
  - Emails oldal: connector config UI
  - Intent schema CRUD: /api/v1/intent-schemas → UI

TESZT:
  - 5 unit test (email_connector service)
  - 5 unit test (classifier service — email context)
  - promptfoo: 85% → 95% (11 → 16 test case)
```

#### P1/3: process_documentation

```
KOD:
  - Diagram generator: Mermaid → BPMN XML export
  - DrawIO export javitas (jelenlegi: alap)
  - SVG minőség ellenorzes

PROMPT:
  - mermaid_flowchart: komplex folyamatok kezelese (10+ lepés)
  - elaborator: strukturalt output (heading hierarchy)
  - classifier: tobb dokumentum tipus felismeres

MODELL:
  - Jelenlegi: gpt-4o (elaborator, extractor), gpt-4o-mini (classifier, mermaid)
  - Kiserlet: elaborator → gpt-4o-mini (ha a minoseg megmarad)

TESZT:
  - 5 unit test (diagram_generator service)
  - promptfoo: 90% → 95% (11 → 15 test case)
```

#### P1/4: invoice_processor

```
KOD:
  - PDF extraction: Docling integracio finomhangolas
  - Multi-page szamla: oldal-osszefuzes logika
  - Export: CSV/Excel/JSON validacio

PROMPT:
  - invoice_classifier: szamla vs. nem-szamla (precision javitas)
  - field_extractor: AFO szam, adoszam, bankszamla regex + LLM
  - currency: HUF/EUR/USD + arfolyam

MODELL:
  - Jelenlegi: gpt-4o (extractor), gpt-4o-mini (classifier)
  - Kiserlet: gpt-4o-mini vision (kep-alapu extraction)

TESZT:
  - 5 unit test (document_extractor service — invoice context)
  - promptfoo: 80% → 95% (10 → 15 test case)
  - Valos szamla tesztek (anonimizalt)
```

#### P2/5-8: Infrastructure services

```
rag_engine: connection pooling, query timeout, collection lifecycle tesztek
classifier: ML model reload, confidence calibralas, A/B teszt framework
cubix_course_capture: ffmpeg timeout, Whisper alternativak, RPA stabilitas
document_extractor: Docling config, multi-format, error recovery
```

#### P3/9-10: Supporting services

```
notification: email template render, Slack webhook, delivery retry
human_review: SLA timer accuracy, escalation chain, reviewer assignment
```

#### P4/11: qbpp_test_automation (STUB → WORKING)

```
DONTES SZUKSEGES: Implementaljuk VAGY toroljuk?
  - Ha IGEN: __main__.py, Robot Framework integracio, 2 prompt, teszt
  - Ha NEM: skill mappa torles, CLAUDE.md frissites (5 skill)
  ELLENORZES: user dontes alapjan
```

---

## 4. Utemterv (Session Mapping)

```
Session 15: H0 (CI/CD Green) ───────────────── ELSO, BLOKKOLO
Session 16: H1 (Ruff Cleanup — batch) ─────── Auto-fix 548
Session 17: H1 (Ruff Cleanup — manual) + H3 ─ Manual 686 + Stub cleanup
Session 18: H2 (Security Hardening) ────────── JWT, CORS, rate limit
Session 19: H4.1 (Service Tests — core 13) ── 65 unit test
Session 20: H4.2 (Service Tests — v1.2.0 13)  65 unit test
Session 21: H5.1-H5.3 (Prompt Tuning P0) ──── aszf_rag + email + process_docs
Session 22: H5.4-H5.7 (Prompt Tuning P1-P4) ─ invoice + cubix + qbpp
Session 23: H6 (Model Optimization) ────────── Cost/quality matrix
Session 24: H7 (UI Fixes) ─────────────────── DataTable fix, P1, P2
Session 25: Final regression + v1.2.2 tag ──── L4 regresszio, tag
```

**Osszes:** 11 session, ~3,000 LOC, ~200 uj teszt

---

## 5. Sikerkriteriumok (v1.2.2 DONE feltetel)

| # | Kriterium | Mertek | Fazis |
|---|-----------|--------|-------|
| 1 | CI/CD MIND ZOLD | 4/4 workflow PASS PR-en | H0 |
| 2 | Ruff 0 error | `ruff check` → 0 error | H1 |
| 3 | 0 HIGH biztonsagi hiba | Security audit clean | H2 |
| 4 | 0 placeholder/stub (nem tudatos) | Stub inventory ures | H3 |
| 5 | 130+ service unit test | 26 service x 5 test | H4 |
| 6 | 6/6 skill 95%+ promptfoo | Minden skill PASS | H5 |
| 7 | >= 20% koltseg csokkenes | Langfuse cost riport | H6 |
| 8 | 0 console error (filterezetlen) | 102+ E2E strict mode | H7 |
| 9 | P1+P2 post-sprint TODO DONE | Pipelines templates UI | H7 |
| 10 | v1.2.2 tag | Squash merge main-re | Final |

---

## 6. Kockazatok

| Kockazat | Valoszinuseg | Hatas | Megoldas |
|----------|-------------|-------|---------|
| JWT csere torhet meglevo tokeneket | Magas | Kozep | Dual-mode: regi + uj elfogadasa 1 verzioig |
| Ruff N806 false positive skills-ben | Magas | Alacsony | per-file-ignores pyproject.toml-ben |
| Promptfoo 95% nem elerheto minden skill-nel | Kozep | Kozep | Minimum 90%, javitasi terv dokumental |
| Service unit tesztek tul sok mock | Kozep | Kozep | Minden teszt VALOS service-t hiv (Docker) |
| qbpp skill implementacio tul draga | Alacsony | Alacsony | STUB marad, dokumentalva |

---

## 7. Branch Strategia

```
main (v1.2.1 — stabil)
  │
  └── feature/v1.2.2-hardening   ← MINDEN H0-H7 ezen a branch-en
        ├── H0: CI/CD fix
        ├── H1: Ruff cleanup
        ├���─ H2: Security
        ├── H3: Stub cleanup
        ├── H4: Service tests
        ├── H5: Prompt tuning
        ├── H6: Model optimization
        ├── H7: UI fixes
        └── merge to main → tag v1.2.2
```

---

## 8. Progress Tracking

| Fazis | Tartalom | Allapot | Datum | Commit |
|-------|----------|---------|-------|--------|
| H0 | CI/CD Green | TODO | — | — |
| H1 | Ruff Cleanup (1,234 → 0) | TODO | — | — |
| H2 | Security Hardening | TODO | — | — |
| H3 | Stub Cleanup | TODO | — | — |
| H4 | Service Unit Tests (130+) | TODO | — | — |
| H5 | Skill Prompt Tuning (95%+) | TODO | — | — |
| H6 | Model Optimization | TODO | — | — |
| H7 | UI Fixes + Polish | TODO | — | — |
| Final | Regression + v1.2.2 tag | TODO | — | — |
