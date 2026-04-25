# AIFlow — Session 145 Prompt (Sprint S S145 — nightly MRR@5 scheduled job + Grafana panel + (tenant_id, name) unique constraint)

> **Datum:** 2026-04-26
> **Branch:** `feature/s-s145-rag-mrr5-nightly` (cut from `main` after PR #35 squash-merges).
> **HEAD (parent):** S144 squash-merge on `main` (PR #35 — `Sprint S S144: admin UI /rag/collections + per-tenant list + set-profile (flag-free)`).
> **Port:** API 8102 | UI 5173
> **Elozo session:** S144 — admin UI `/rag/collections` (3 endpoints + side drawer + EN/HU locales + Playwright spec) + `RAGEngineService.set_embedder_profile()` with `DimensionMismatch` HTTP 409 guard. 2361 → 2373 unit (+12), ~107 → ~110 integration (+3 real PG), 429 → 430 E2E (+1 spec — live run still PENDING per `tests/ui-live/rag-collections.md`). 0 Alembic, 0 skill code change, NULL-fallback unchanged.
> **Terv:** `01_PLAN/116_SPRINT_S_FUNCTIONAL_VECTOR_DB_PLAN.md` §3 S145 + `01_PLAN/114_CAPABILITY_ROADMAP_Q_R_S.md` §4 (Sprint S follow-ups).
> **Session tipus:** Operability + observability + minor schema constraint. **3 Alembic migration** (046 → 047 additive `(tenant_id, name)` unique).

---

## 1. MISSION

Close the three remaining S143 / S144 follow-ups so Sprint S can ship with operability parity to Sprints L (monitoring) and N (budgets):

1. **SS-FU-3 — nightly MRR@5 scheduled job + Grafana panel.** A nightly cron (APScheduler-style or external cron) runs the existing `scripts/measure_uc1_golden_path.py`-style harness for UC2 RAG against a curated query set, persists per-collection MRR@5 + p95 latency to a new metric table, and exposes a Grafana panel reading from PostgreSQL or Prometheus. Default: HU corpus over the legacy `aszf_rag_chat` collection. The result file format must be machine-readable (JSON Lines into a dedicated table) so trend charts work out of the box.
2. **SS-FU-4 — Alembic 047: `(tenant_id, name)` unique constraint** on `rag_collections`. Pure additive (drop the implicit non-tenant-aware uniqueness from S143's `customer` legacy column or replace with the multi-tenant constraint). Idempotent upgrade; downgrade is reversible. Must NOT break any existing seed data — write a smoke-cleanup script if duplicates exist on the dev DB.
3. **SS-SKIP-1 — BGE-M3 weight cache as a CI artifact.** A small `scripts/bootstrap_bge_m3.py`-driven CI step that downloads the model once, caches at a known path, and lets `tests/integration/services/rag_engine/test_query_1024_dim.py` un-skip its weight-gated test in the workflow.

S145 **does not** touch:
- `RAGEngineService.create_collection` `customer` deprecation (SS-FU-1, SS-FU-5 — separate refactor sprint).
- Per-skill migrations of `aszf_rag_chat`, UC3 EXTRACT skills onto the ProviderRegistry (S141-FU-1/2/3 path).
- Azure OpenAI Profile B live MRR@5 (SS-SKIP-2 — credit landing required).

---

## 2. KONTEXTUS

### Why these three together

* The MRR@5 nightly closes the loop between S143's queryability fix
  and the Sprint J UC2 baseline (`MRR@5 ≥ 0.55`). Without a recurring
  measurement we have no early-warning if a future change regresses
  Profile A's retrieval quality. Grafana panel visibility makes it
  ops-on-call surface.
* The `(tenant_id, name)` unique constraint is the natural close-out
  of the S144 admin UI — until it lands, two tenants can theoretically
  create a collection with the same name and the UI silently lets them
  through. The schema gate is two lines of Alembic but unblocks the
  multi-tenant story.
* The BGE-M3 weight cache un-skips one of S143's integration tests
  in CI. Until this lands the 1024-dim queryability is verified locally
  but skipped on every PR, eroding the gate over time.

### Carry forward from S144

| ID | Eredet | Itt zarjuk-e |
|---|---|---|
| SS-FU-1 (`create_collection` tenant-aware arg) | S143/S144 PR | NEM — separate refactor |
| SS-FU-3 (nightly MRR@5 + Grafana) | S143 PR | **IGEN** — primary deliverable |
| SS-FU-4 (`(tenant_id, name)` unique) | S143 PR | **IGEN** — Alembic 047 additive |
| SS-FU-5 (`customer` deprecation) | S143 PR | NEM — separate refactor |
| SS-SKIP-1 (BGE-M3 weight CI preload) | S143 plan §8 | **IGEN** |
| SS-SKIP-2 (Profile B Azure live MRR) | S143 plan §8 | NEM — Azure credit |
| S141-FU-1/2/3 (per-skill PromptWorkflow migrations) | Sprint R | NEM — Sprint T |
| Sprint J resilience `Clock` seam (deadline 2026-04-30) | Sprint J | **OPCIONALIS** — if time permits |

### Live-test debt from S144

`tests/ui-live/rag-collections.md` is still **PENDING**. Either the
operator reproduces the journey on a `make api` + `npm run dev` stack
before this S145 session starts, or it carries forward into S145's
final regression block. **Do not skip it twice.**

---

## 3. ELOFELTETELEK

```bash
git checkout main
git pull --ff-only origin main                            # PR #35 squash tip
git checkout -b feature/s-s145-rag-mrr5-nightly
git log --oneline -3                                       # S144 squash on top
docker compose ps                                          # db (5433) + redis (6379) healthy
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov 2>&1 | tail -1   # 2373 baseline
PYTHONPATH="src;." .venv/Scripts/python.exe -m alembic current   # head: 046
cd aiflow-admin && npx tsc --noEmit && cd ..              # FE TS clean baseline
```

Stop, ha:
- Unit baseline ≠ 2373 — másik branch nyitva.
- Alembic current ≠ 046 — S144 nem alkalmazva (vagy 047 már megvan, dupla refactor).
- `aiflow-admin` TS dirty — meglévő regresszió előbb.
- PR #35 nem mergelt — várj, vagy explicit kérdezz.

---

## 4. FELADATOK

### LEPES 1 — Alembic 047 `(tenant_id, name)` unique

`alembic/versions/047_rag_collections_tenant_name_unique.py`:

```python
"""rag_collections (tenant_id, name) unique

Revision ID: 047
Revises: 046
Create Date: 2026-04-26
"""

revision = "047"
down_revision = "046"

def upgrade() -> None:
    op.create_unique_constraint(
        "uq_rag_collections_tenant_name",
        "rag_collections",
        ["tenant_id", "name"],
    )

def downgrade() -> None:
    op.drop_constraint(
        "uq_rag_collections_tenant_name",
        "rag_collections",
        type_="unique",
    )
```

Pre-flight smoke (one-off `python -c "import asyncpg; ..."`):
```sql
SELECT tenant_id, name, COUNT(*) FROM rag_collections
GROUP BY tenant_id, name HAVING COUNT(*) > 1;
```
Ha ad sort → `STOP, kérdezd meg a usert` mit csináljon (rename / dedup / soft-name suffix).

Integration test `tests/integration/alembic/test_047_rag_collections_tenant_name_unique.py` (2 db):
- Upgrade → downgrade round-trip.
- Inserting two `(tenant_id='t1', name='same')` rows → second fails with
  `UniqueViolationError`. After downgrade → both insert successfully.

### LEPES 2 — Nightly MRR@5 harness

Files:
- `src/aiflow/services/rag_metrics/__init__.py` — new service module.
- `src/aiflow/services/rag_metrics/harness.py` — `RagMetricsHarness` class with `async def measure_collection(collection_id, query_set: list[QuerySpec]) -> CollectionMetrics`.
- `src/aiflow/services/rag_metrics/contracts.py` — `QuerySpec(question, expected_doc_ids)` + `CollectionMetrics(collection_id, mrr5, p95_latency_ms, query_count, measured_at)`.
- `scripts/run_nightly_rag_metrics.py` — CLI entry-point: `--collection-id X --query-set Y --output table|jsonl`.
- `data/fixtures/rag_metrics/uc2_aszf_query_set.json` — 20-item HU query corpus reused from Sprint J S103 baseline.

Alembic 048 (separate, optional — only if persistence into PG is the chosen path):
- `rag_collection_metrics` table (`id`, `collection_id`, `mrr5`, `p95_latency_ms`, `query_count`, `measured_at`, `harness_version`).

Cron / scheduler:
- Reuse the existing APScheduler if any, otherwise document the operator runbook for an external cron entry (`docs/runbooks/rag_metrics_nightly.md`).

Tests:
- 6 unit (`tests/unit/services/rag_metrics/test_harness.py`):
  - MRR@5 calculation (basic, ties, no hits).
  - p95 over a 20-sample bucket.
  - QuerySpec validation (non-empty doc list).
  - JSONL emission shape.
  - Async iteration over the query set.
  - Empty query set returns sentinel `CollectionMetrics(query_count=0)`.
- 1 integration (`tests/integration/services/rag_metrics/test_harness_real.py`):
  - Real PG + real existing `aszf_rag_chat` seed (or the Sprint J fixture corpus). Skip when the seed isn't present.

### LEPES 3 — Grafana panel

- `docs/grafana/rag_collection_metrics_panel.json` — exportable panel JSON (data source: PostgreSQL via the Sprint L S111 datasource UID convention).
- `docs/runbooks/rag_metrics_nightly.md` — Operator runbook: how to import the panel, what query backs each chart, alert thresholds.
- Note in the runbook that the alert thresholds (e.g. MRR@5 < 0.45 = WARN, < 0.35 = PAGE) are placeholders until 2-3 nights of data exist.

### LEPES 4 — BGE-M3 weight CI artifact

- `scripts/bootstrap_bge_m3.py` is already present (Sprint J). Extend it
  to write a `--cache-dir` argument and exit-0 even on a partial
  re-download of an already-cached weight set.
- `.github/workflows/integration.yml` (or equivalent) adds a step:
  ```
  - name: Cache BGE-M3 weights
    uses: actions/cache@v3
    with:
      path: ~/.cache/bge-m3
      key: bge-m3-${{ hashFiles('scripts/bootstrap_bge_m3.py') }}
  - run: python scripts/bootstrap_bge_m3.py --cache-dir ~/.cache/bge-m3
  ```
- Un-skip `tests/integration/services/rag_engine/test_query_1024_dim.py`
  by removing or relaxing the weight-skip-guard (`if not Path("…").exists(): pytest.skip(...)`). Use an env override `AIFLOW_BGE_M3_CACHE_DIR` so local devs still skip when they don't have weights.

### LEPES 5 — Regression + commit + PR

```bash
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/ --no-cov -q                # 2373 → ~2379
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/integration/alembic/test_047_*.py --no-cov -q
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/integration/services/rag_metrics/ --no-cov -q
.venv/Scripts/python.exe -m ruff check src/ tests/ && .venv/Scripts/python.exe -m ruff format --check src/ tests/
```

Commit:
```
feat(sprint-s): S145 — nightly MRR@5 + Alembic 047 (tenant_id,name) unique + BGE-M3 weight cache

- Alembic 047 additive: rag_collections (tenant_id, name) unique constraint
- RagMetricsHarness service + CLI (scripts/run_nightly_rag_metrics.py)
- Grafana panel JSON + operator runbook
- BGE-M3 weight CI cache step + un-skipped 1024-dim integration test
- 6 unit + 1 integration + 2 alembic round-trip
- 0 skill code change, NULL-fallback unchanged
```

PR cut against `main`, base on the post-S144 squash tip.

### LEPES 6 — CLAUDE.md numbers update

- API endpoints: `196 → 196` (no new endpoint unless the harness exposes one — likely not).
- API routers: `31 → 31` (no new router).
- Unit tests: `2373 → ~2379` (+6).
- Integration tests: `~110 → ~113` (+3: 2 alembic + 1 harness real).
- Alembic head: `046 → 047` (or `→ 048` if the metrics table also lands).
- Banner: `Sprint S S144 IN-PROGRESS` → `Sprint S S145 IN-PROGRESS`.

---

## 5. STOP FELTETELEK

**HARD:**
1. UC2 `aszf_rag_chat` golden-path regresszió → halt + revert.
2. `rag_collections` row INSERT regresszió a 047 unique constraint
   miatt (production seed sérelem) → halt, kérdezd meg a usert dedup
   stratégiáról.
3. `gh pr create` credentials hiány autonomous loop-ban → halt.
4. BGE-M3 weight download CI-ban tartósan failel (>3x retry) → SOFT,
   skip az un-skip helyett, dokumentáld follow-upként.

**SOFT:**
- Grafana JSON panel — ha nincs élő Grafana stack a session alatt,
  csak a JSON export landol, kommit-ban dokumentálva.
- Cron scheduling — APScheduler-integráció vs külső cron: ha a kód
  alap nem segíti, csak a runbook + CLI lép, scheduler S146-ra megy.

---

## 6. SESSION VEGEN

```
/session-close S145
```

A `/session-close` generálja:
- `docs/sprint_s_s145_pr_description.md`
- CLAUDE.md numbers update.
- Skipped-items append (BGE-M3 status, Profile B status).
- Következő `NEXT.md` (S146 — várhatóan Sprint S retro + PR vagy
  S141-FU-* per-skill PromptWorkflow migration kickoff).

---

## 7. SKIPPED-ITEMS TRACKER (folytatas)

| ID | Hely | Mi | Unskip feltetel |
|---|---|---|---|
| SS-SKIP-2 | `01_PLAN/116_*` §8 | Profile B (Azure OpenAI) MRR@5 | Azure credit |
| SS-FU-1 | PR #34 / #35 body | `create_collection` tenant-aware arg + `customer` deprecation | Külön refactor sprint |
| SS-FU-5 | PR #34 body | `rag_collections.customer` column drop | Külön refactor |
| S141-FU-1/2/3 | Sprint R retro | Per-skill PromptWorkflow migration | Sprint T |
| SR-FU-4 | Sprint R retro | Live-stack Playwright for `/prompts/workflows` | Sprint T |
| Sprint J Clock seam | Sprint J retro | Resilience timing flake fix | Deadline 2026-04-30 |
| S144 live-test PENDING | S144 PR | `/live-test rag-collections` operator run | Pre-merge of PR #35 |

S145 **csak SS-FU-3, SS-FU-4, SS-SKIP-1** zárja le.
