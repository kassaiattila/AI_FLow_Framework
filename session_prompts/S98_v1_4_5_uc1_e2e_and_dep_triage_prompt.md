# AIFlow Sprint I — Session 98 Prompt (v1.4.5.5: UC1 Playwright E2E + dep-triage + v1.4.5 tag)

> **Datum:** 2026-05-02 (tervezett start — S97 commit után)
> **Branch:** `feature/v1.4.5-doc-processing`
> **HEAD prereq:** `5e1092f` — `feat(v1.4.5): S97 — UC1 PackageDetail viewer + Prompts list + 2 read-only endpoints`
> **Port:** API 8102 | Frontend Vite :5173
> **Plan:** `01_PLAN/110_USE_CASE_FIRST_REPLAN.md` §4 Sprint I row S98 + `01_PLAN/ROADMAP.md` "Active sprint — v1.4.5"
> **Session típus:** Sprint-exit — Playwright golden-path E2E UC1, dep-triage (pyee), v1.4.5 tag cut. Code risk: LOW. Process risk: MEDIUM (7 HARD GATE — utolsó gate = regression + tag).

---

## KONTEXTUS

### Honnan jöttünk

- **S97 COMMITTED** `5e1092f`: `GET /api/v1/document-extractor/packages/{package_id}` aggregate (intake_packages + intake_files + routing_decisions, tenant boundary = cross-tenant 404), `GET /api/v1/prompts/list` (disk-walk YAML view), `aiflow-admin/src/pages-new/PackageDetail.tsx` (parser-used badge 5 variant, Overview/Extraction JSON/Routing/PII tabs, Langfuse link `VITE_LANGFUSE_HOST` gated), `aiflow-admin/src/pages-new/Prompts.tsx` v1 read-only list, 4 új integration test PASS real PostgreSQL :5433 ellen.
- Unit baseline: **1946 PASS isolated + 3 pre-existing order-flake** (test_confidence_threshold_default, TestParserContract::test_estimate_cost, test_estimate_cost_scales_with_size). Nem változott.
- Alembic head: **039** (nem változott).
- S97-ről halasztva: `GET /extractions/{id}` (extraction_results persistence table még nincs), PII gate bekötés `extract_from_package` LLM hop-ba, Playwright E2E smoke (pyee/EventEmitter ImportError).

### Hova tartunk — S98 scope (Sprint I exit)

Sprint-exit = v1.4.5 tag + 1 zöld Playwright golden-path UC1-re. Ez a záró session:

1. **Dep-triage**: `pyee` csomag reimport — `playwright._impl._connection` ma `ImportError: cannot import name 'EventEmitter' from 'pyee'`. Vagy `uv sync` reinstall, vagy `uv add pyee==11.*` pin. E2E collect-only zöldre.
2. **Playwright golden-path E2E UC1** — `aiflow-admin/tests/e2e/package_detail.spec.ts`:
   - Upload → extract → UI render → assert parser-used badge + routing tab + extraction tab.
   - Real backend :8102 (Docker postgres+redis + `make api`).
   - Seed package via `POST /api/v1/intake/upload-package` (létező endpoint, JWT Bearer), majd `GET /api/v1/document-extractor/packages/{id}` → UI navigate `/packages/:id`.
3. **v1.4.5 tag cut** — PR draft + merge-előtti regression + annotated tag `v1.4.5-uc1`.
4. (Stretch, halasztható S97.5-re) PII gate bekötés LLM hop-ba + `extraction_results` Alembic migration 040.

### Jelenlegi állapot (induláskor várt)

```
27 service | 181 endpoint (+2 az S97-ből) | 50 DB tábla | 39 Alembic migration (head: 039)
1949 unit collected (1946 PASS isolated + 3 order-flake) | 410+ E2E collected (pyee blokk: 0) | 46 integration (+4)
Coverage: ~67% (issue #7 OPEN, S98 scope: 80%-ra felhúzni NEM, Sprint J-re halasztódik)
```

---

## ELŐFELTÉTELEK

```bash
git branch --show-current                                       # feature/v1.4.5-doc-processing
git log --oneline -3                                            # HEAD 5e1092f = S97
.venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov      # 1946 PASS + 3 order-flake
.venv/Scripts/python.exe -m ruff check src/ tests/ --quiet      # exit 0
PYTHONPATH=src .venv/Scripts/python.exe -m alembic current      # 039
cd aiflow-admin && npx tsc --noEmit                             # 0 error
```

Docker:

```bash
docker ps --filter "name=07_ai_flow_framwork" --format "table {{.Names}}\t{{.Status}}"
# postgres:5433 + redis:6379 healthy
```

**Ha Docker le van állva:** `docker compose up -d postgres redis`.

---

## FELADATOK

### LÉPÉS 1 — pyee dep-triage (blocker)

```bash
.venv/Scripts/python.exe -m pytest tests/e2e/ --collect-only -q --no-cov 2>&1 | tail -5
# Várt: `ImportError: cannot import name 'EventEmitter' from 'pyee'`
```

Javítási sorrend:
1. `uv sync --reinstall-package playwright pyee` — elsőként, gyakran elég.
2. Ha marad: `uv add 'pyee>=11,<13'` (playwright 1.44+ ezt várja) — pyproject.toml pin.
3. Root cause log a session-close summary-ba.

Exit kritérium: `.venv/Scripts/python.exe -m pytest tests/e2e/ --collect-only -q --no-cov` exit 0, 410+ E2E collected.

### LÉPÉS 2 — Playwright E2E: `package_detail.spec.ts`

Fájl: `aiflow-admin/tests/e2e/package_detail.spec.ts`.

Scope:
- `login` fixture-rel autentikálunk (létező Playwright fixture).
- Backend seed: `POST /api/v1/intake/upload-package` → visszakapjuk a `package_id`-t.
- Navigate `/packages/{package_id}`.
- Assert:
  - `[data-testid="parser-badge"]` látható, `data-parser` attribute egyike a 5 variantnak.
  - Click `[data-testid="tab-routing"]` → routing tab megnyílik, legalább 1 decision JSON render.
  - Click `[data-testid="tab-extraction"]` → extraction tab render (S97-ben üres, v1.5-ös UC1 flow-ban S97.5 után megtelik).

Tipikus hossz: ≤ 120 sor.

### LÉPÉS 3 — Regression + tsc + lint

```bash
.venv/Scripts/python.exe -m ruff check src/ tests/ --quiet
.venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov
.venv/Scripts/python.exe -m pytest tests/integration/ -q --no-cov
cd aiflow-admin && npx tsc --noEmit && npx playwright test tests/e2e/package_detail.spec.ts && cd ..
```

### LÉPÉS 4 — Tag cut + PR draft (manuális review után)

```bash
git add aiflow-admin/tests/e2e/package_detail.spec.ts pyproject.toml uv.lock
# + egyéb, amit a dep-triage érintett

git commit -m "$(cat <<'EOF'
feat(v1.4.5): S98 — UC1 Playwright golden-path + pyee dep-triage + v1.4.5 tag

- Pin pyee>=11,<13 / uv reinstall to unblock tests/e2e/ collect.
- New Playwright spec package_detail.spec.ts exercises the UC1 golden
  path: upload-package → GET /document-extractor/packages/{id} →
  UI parser badge + routing/extraction tab assertions.

Sprint I / UC1 - session 5 of 5 (sprint-exit).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"

git tag -a v1.4.5-uc1 -m "AIFlow v1.4.5 — UC1 doc processing sprint exit"
git push && git push --tags
```

PR: `feature/v1.4.5-doc-processing → main`. Sablon a `docs/phase_1d_pr_description.md` mintájára.

### LÉPÉS 5 — /session-close

```
/session-close S98
```

---

## STOP FELTÉTELEK

- **HARD:** `uv sync` reinstall után is pyee ImportError → dep-triage mélyebb, kérdezz a usertől (pyee verzió mátrix, playwright downgrade opció).
- **HARD:** Playwright E2E FAIL tenant boundary-n vagy parser badge selector-on → ne patcheld a prod kódot, hanem tisztázd a test seed flow-t.
- **HARD:** Új Alembic migration SZÜKSÉGES (pl. `extraction_results` table) → NEM ebbe a session-be, azt S97.5-re halaszd.
- **HARD:** v1.4.5 tag előtt a regression (unit + integration) NEM zöld → tag-et SOHA ne húzz ki failing suite-ra.
- **HARD:** Main branch-re direct commit tilos — PR flow kötelező.
- **VALÓS SZÁMLÁK:** `data/uploads/invoices/*.pdf` SOHA nem git-be / fixture-be.
- **SOFT:** Coverage nem kell 80%-ra (issue #7 Sprint J-re).

---

## SESSION VÉGÉN

```
/session-close S98
```

Utána `/clear` és sprint-exit retro (tag + PR review).
