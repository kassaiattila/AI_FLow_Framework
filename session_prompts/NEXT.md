# AIFlow Sprint I — Session 94 Prompt (v1.4.5.1: extract_from_package impl + Docling std wiring)

> **Datum:** 2026-04-29 (tervezett start — v1.4.4 tag cut után)
> **Branch:** `feature/v1.4.5-doc-processing` (cut from `main` after `v1.4.4` tag; **NEM** folytatjuk `feature/v1.4.4-consolidation`-on)
> **HEAD prereq:** `v1.4.4` tag létezik `main`-en
> **Port:** API 8102 | Frontend Vite :5173
> **Plan:** `01_PLAN/110_USE_CASE_FIRST_REPLAN.md` §4 Sprint I + `01_PLAN/ROADMAP.md` "Active sprint — v1.4.5"
> **Session típus:** Feature implementáció — use-case UC1 első session. Code risk: MEDIUM (service refactor + új provider). Process risk: LOW.

---

## KONTEXTUS

### Honnan jöttünk

- Phase 1a (v1.4.0) MERGED: 3 intake contract + PolicyEngine + ProviderRegistry + 4 ABC.
- Phase 1b–1d MERGED: 5 source adapter (Email/File/Folder/Batch/API) + `IntakePackageSink` + webhook router.
- v1.4.4 Consolidation (S88–S93) DONE: version reconcile, doc drift fix, test hygiene, use-case-first replan szerzés.
- **A replan új policy-je:** minden sprint 1 end-user use-case green-be kerül. Sprint I = **Document processing** (UC1).

### Hova tartunk — Sprint I

5 session, sprint-exit = v1.4.5 tag + 1 Playwright E2E green. Ez a session (S94) az első: a `DocumentExtractorService.extract_from_package()` ma `NotImplementedError` — ma ez a blocker #1 UC1-ben. Be kell implementálni és Docling standard pipeline-t kell mögé tenni default extractor-ként, PolicyEngine gate-tel a cloud-AI-n.

### Jelenlegi állapot (induláskor várt)

```
27 service | 177 endpoint | 49 DB tábla | 37 Alembic migration (head: 037)
1898 unit PASS | 42 integration PASS | 410 E2E collected
Coverage: ~67% (issue #7 OPEN)
v1.4.4 tag létezik main-en, feature/v1.4.5-doc-processing cut-olva
```

---

## ELŐFELTÉTELEK

```bash
git branch --show-current                             # feature/v1.4.5-doc-processing
git log --oneline -3                                  # top: v1.4.4 merge commit
.venv/Scripts/python.exe -m pytest tests/unit/ -x -q --no-cov   # 1898+ PASS
.venv/Scripts/python.exe -m ruff check src/ tests/ --quiet      # exit 0
PYTHONPATH=src .venv/Scripts/python.exe -m alembic current      # 037

# Docker szolgáltatások:
docker ps --filter "name=aiflow" --format "table {{.Names}}\t{{.Status}}"
# postgres:5433 running, redis:6379 running, kroki:8000 running
```

**Ha `v1.4.4` tag nincs main-en:** HARD STOP — előbb a v1.4.4 PR merge + tag kell. Jelezd a usernek.

---

## FELADATOK

### LÉPÉS 1 — `ExtractionResult` Pydantic v1 stub

Fájl: `src/aiflow/contracts/extraction_result.py` (új, ha nincs)

- Minimális mezők: `package_id: UUID`, `file_id: UUID`, `parser_used: str`, `extracted_text: str`, `structured_fields: dict[str, Any]`, `confidence: float`, `extracted_at: datetime`, `tenant_id: str`, `cost_attribution: dict[str, Any] | None`.
- Frozen=False (v1 stub), `model_config = ConfigDict(extra="forbid")`.
- Unit teszt: `tests/unit/contracts/test_extraction_result.py` — default + invalid confidence (>1) + serialize round-trip.

> Nem az §10.3 full ExtractionResult v2 — az Phase 2b (v1.5.1). Ez **stub**, hogy UC1 szállíthasson DB-be és UI-ra.

### LÉPÉS 2 — `DocumentExtractorService.extract_from_package()` impl

Fájl: `src/aiflow/services/document_extractor/service.py`

Mai állapot: `extract_from_package()` raises `NotImplementedError`. Ezt cseréld ki valódi implementációra:

1. Input: `IntakePackage` objektum (Phase 1a contract).
2. Minden `IntakeFile`-ra:
   a. PolicyEngine lookup: `policy = engine.for_package(pkg)` — kapjuk a profile + tenant override merged config-ot.
   b. Gate: ha `file.mime_type` olyan amit csak cloud provider kezel, és `policy.cloud_ai_allowed == False` → skip file, log warn, `ExtractionResult` `parser_used="skipped_policy"`.
   c. Default path (S94 scope): `DoclingStandardParser.parse(file) -> raw_text + structured`.
   d. `ExtractionResult` épít + return list.
3. `@trace` decorator a Langfuse-hoz (ha a tracing module elérhető — ellenőrizd: `src/aiflow/observability/tracing.py`).
4. Backward-compat shim (`extract(file_path)`): wrappelje `extract_from_package()` single-file `IntakePackage`-dzsel; már megvolt, most végre valódi output-ot kell adjon.

**Nem scope S94-ben:** routing logika (S95), Azure DI (S96), PII gate (S96). Csak Docling std path.

### LÉPÉS 3 — `DoclingStandardParser` (ParserProvider)

Fájl: `src/aiflow/providers/parsers/docling_standard.py` (új)

- Implement `ParserProvider` ABC (`src/aiflow/providers/interfaces.py`).
- Constructor: opcionális `DoclingConfig` (pl. `do_ocr: bool = True`, `do_table_structure: bool = True`).
- `parse(file: IntakeFile) -> ParserResult` — Docling SDK hívás valódi docling csomaggal (ha nincs telepítve a `.venv`-ben: `uv pip install docling` — **ellenőrizd pip install szabályát** a `CLAUDE.md`-ben: `uv` a package manager).
- Regisztrálás: `ProviderRegistry.register_parser("docling_standard", DoclingStandardParser)` — startup-ban vagy DI container-ben.
- `ParserResult` is egy v1 stub, ha még nincs — tedd `src/aiflow/contracts/parser_result.py` alá.

**Sanity check:** `uv pip show docling` — ha nincs, telepítsd: `uv add docling`. **Ne** rebuild-eld a `.venv`-et (lásd `feedback_venv_deps.md` memory).

### LÉPÉS 4 — Tesztek

1. **Unit — extractor service:**
   - `tests/unit/services/document_extractor/test_extract_from_package.py`
   - Mockolt `PolicyEngine` + mockolt `DoclingStandardParser` (csak unit scope-ban mockolunk — **integration-ben tilos**).
   - Esetek: (a) happy path 1 file, (b) policy block (cloud_disallowed + pdf_scanned), (c) multi-file batch, (d) empty package raises ValueError.

2. **Integration — valós Docling + valós Postgres:**
   - `tests/integration/services/document_extractor/test_extract_integration.py`
   - `tests/fixtures/sample_invoice.pdf` (ha nincs, kérj rá megerősítést — NINCS kitaláltt fájl).
   - Real Postgres pool, real Docling, real PolicyEngine.
   - Assert: `ExtractionResult.extracted_text` nem üres, `parser_used == "docling_standard"`.

3. **Backward-compat regresszió:**
   - Létező `tests/e2e/v1_4_0_phase_1a/test_backward_compat_extract_file.py` **NEM FÁIL** — most már valódi eredményt ad, de a shape ugyanaz maradjon.

### LÉPÉS 5 — Validáció

```bash
.venv/Scripts/python.exe -m ruff check src/ tests/ --quiet     # exit 0
.venv/Scripts/python.exe -m pytest tests/unit/ -x -q --no-cov  # 1898+ új unit tesztek PASS
.venv/Scripts/python.exe -m pytest tests/integration/services/document_extractor/ -q --no-cov
.venv/Scripts/python.exe -m pytest tests/e2e/v1_4_0_phase_1a/test_backward_compat_extract_file.py -q --no-cov
```

### LÉPÉS 6 — Commit

```bash
git add src/aiflow/contracts/extraction_result.py \
        src/aiflow/contracts/parser_result.py \
        src/aiflow/providers/parsers/docling_standard.py \
        src/aiflow/services/document_extractor/service.py \
        tests/unit/contracts/ \
        tests/unit/services/document_extractor/ \
        tests/integration/services/document_extractor/ \
        pyproject.toml uv.lock   # ha docling új dep
git commit -m "$(cat <<'EOF'
feat(v1.4.5): S94 — extract_from_package() impl + Docling standard parser provider

- ExtractionResult + ParserResult Pydantic v1 stubs (src/aiflow/contracts/).
  §10.3 v2 upgrade stays Phase 2b (v1.5.1) scope.
- DocumentExtractorService.extract_from_package() now has a real body. Default
  parser is Docling standard pipeline. PolicyEngine consulted for
  cloud_ai_allowed before any cloud-capable provider call; skipped files land
  as ExtractionResult(parser_used="skipped_policy").
- DoclingStandardParser registered on ProviderRegistry as a ParserProvider.
- Backward-compat shim extract(file_path) now produces real output; prior
  NotImplementedError removed.
- Tests: unit (policy block + happy path + multi-file + empty pkg),
  integration (real Postgres + real Docling + real PolicyEngine),
  backward-compat regression green.

Sprint I / UC1 (Document processing usable) — session 1 of 5.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

### LÉPÉS 7 — Session close

```
/session-close S94
```

---

## STOP FELTÉTELEK

- **HARD:** Docling SDK install szétveri az `.venv`-et (pypdfium2 / pdfminer konfliktus, lásd `feedback_venv_deps.md`) → ROLLBACK, scope check, külön session-t nyitunk a dep triage-re.
- **HARD:** `ExtractionResult` shape-je tör olyan existing E2E tesztet ami a backward-compat shim output-jára assert-el → írd át a contract-ot, ne a tesztet (az a stabilitási anchor).
- **HARD:** Nincs `v1.4.4` tag a `main`-en → előbb azt kell merge-elni.
- **SOFT:** Ha a Docling standard pipeline 1 test fájlon >30s fut → jelezd, lehet hogy `do_ocr=False` a defaulthoz kellene; de ezt NE tégyél a S94-ben saját kezdeményezésből, hanem kérdezd meg a usert.
- **NINCS:** Azure DI impl, routing logika, PII gate — azok S95/S96. Ha S94-ben elkezded, scope-creep.

---

## SESSION VÉGÉN

```
/session-close S94
```

Utána `/next` → S95 (`RoutingDecision` contract + `MultiSignalRouter` + Alembic 038 + Unstructured ParserProvider).
