# Sprint S (v1.5.2) — Multi-tenant + multi-profile vector DB ships at parity with Sprints L (monitoring) + N (budgets)

> **Reference doc.** This is a consolidated PR-style summary across the three squash-merged Sprint S PRs (#34, #35, #37) plus the chore env PR (#36). The actual feature PRs already shipped on `main`; this file is the single rolled-up view for stakeholders + future archeology. The S146 close PR (`chore/sprint-s-close`) carries this document along with `docs/sprint_s_retro.md` and the CLAUDE.md banner update — no code change.
>
> **Cut from:** `main` @ `d6ee813` (S145 squash, PR #37). No external rebase dependency.

## Summary

- **`RAGEngineService.query()` becomes ProviderRegistry-aware.** The 1024-dim BGE-M3 collections that Sprint J landed are now actually queryable: a single `_resolve_query_embedder(coll)` dispatch picks NULL-fallback (legacy `self._embedder`) for pre-Sprint-S collections or instantiates a fresh `EmbedderProvider` via `_QueryEmbedderAdapter` when `embedder_profile_id` is set. Unknown aliases surface as `UnknownEmbedderProfile` returned via `QueryResult.answer` (no exception in the query happy path).
- **Operator-visible admin surface.** New page `/#/rag/collections`, new router `/api/v1/rag-collections` (3 routes: list with optional tenant filter, detail, PATCH `embedder-profile`). New `set_embedder_profile()` mutation with structured failure modes (empty-collection short-circuit, populated dim-equality guard, `DimensionMismatch → HTTP 409 RAG_DIM_MISMATCH`). Tenant chip filter with `?tenant=` deep-link, side drawer, EN/HU locale.
- **Nightly retrieval-quality harness.** `RagMetricsHarness` + 20-item HU UC2 query corpus + CLI runner + 4-panel Grafana dashboard + operator runbook. Air-gap-safe: harness emits JSONL ready for psql ingest, never writes data itself; operators provision `rag_collection_metrics_jsonl` and schedule retention.
- **Multi-tenant uniqueness.** Alembic 046 (additive `tenant_id` server-default `'default'` + `embedder_profile_id` nullable + `ix_rag_collections_tenant_id`) + Alembic 047 (legacy `UNIQUE (name)` swap for `UNIQUE (tenant_id, name)`). Pre-flight duplicate scan returned 0 rows — 047 is metadata-only DDL with zero data churn.
- **CI infra.** BGE-M3 weight `actions/cache@v4` step in `nightly-regression.yml` so the 1024-dim integration tests un-skip on the nightly run while main CI stays at ~3 min.
- **Zero feature-flag changes, zero new feature flags.** NULL-fallback is byte-for-byte identical to pre-S143 behaviour for every legacy collection. Sprint R/Q/P/O/N/M flag defaults are all unchanged.

## What landed

| PR | Squash | Scope |
|---|---|---|
| **#34** | `95ec89e` | S143 — `RAGEngineService.query()` ProviderRegistry refactor + Alembic **046** `rag_collections.tenant_id` (`'default'` server default) + `embedder_profile_id` (nullable) + `ix_rag_collections_tenant_id`. 1024-dim BGE-M3 collections become queryable. **+14 unit / +4 integration**. |
| **#35** | `bc59a8f` | S144 — `set_embedder_profile()` mutation with `DimensionMismatch` HTTP 409 guard. New `/api/v1/rag-collections` admin router (list / detail / PATCH). New `pages-new/RagCollections/` admin page. **+12 unit / +3 integration / +1 Playwright E2E**. |
| **#36** | `ec3e672` | _chore_ — env-file consolidation (`.env`, `.env.example`) + `scripts/seed_admin.py` reading the canonical `.env` directly. Side-branch fix from the S144 live-test trailing-whitespace password incident. Captured in retro decision SS-7. |
| **#37** | `d6ee813` | S145 — `RagMetricsHarness` (`src/aiflow/services/rag_metrics/`) + 20-item HU UC2 query corpus + CLI runner + 4-panel Grafana dashboard + operator runbook + Alembic **047** `(tenant_id, name)` unique swap + BGE-M3 weight cache step in `nightly-regression.yml`. **+6 unit / +3 integration**. |
| **(this PR)** | _S146 close_ | Docs only — `docs/sprint_s_retro.md`, `docs/sprint_s_pr_description.md`, CLAUDE.md banner flip + numbers. Tag `v1.5.2` queued (not pushed). |

## Cohort delta (capability-first roadmap)

```
                              Sprint J        Sprint S
1024-dim collection ingest:   shipped         (unchanged)
1024-dim collection query:    blocked         shipped     ← S143
Multi-tenant rag_collections: –               shipped     ← S143/S145
Admin list per tenant:        –               shipped     ← S144
Profile attach/detach:        –               shipped     ← S144
Nightly retrieval MRR@5:      –               shipped     ← S145
Cross-tenant name reuse:      blocked (uq name)  allowed  ← S145
BGE-M3 weight CI cache:       –               nightly     ← S145
```

## Acceptance criteria (per `01_PLAN/116_*` + `01_PLAN/114_*` §4)

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | `RAGEngineService.query()` resolves NULL-profile to legacy fallback (byte-for-byte) | ✅ | `_resolve_query_embedder` short-circuit; 14 S143 unit tests; 2 rag_engine integration on real PG |
| 2 | `RAGEngineService.query()` resolves known alias via fresh `EmbedderProvider` adapter | ✅ | `_QueryEmbedderAdapter`; integration on real PG + real BGE-M3 weights |
| 3 | Unknown alias surfaces as `UnknownEmbedderProfile` via `QueryResult.answer` (no exception) | ✅ | S143 unit tests; not transient |
| 4 | Alembic 046 additive: `tenant_id` server-default + `embedder_profile_id` nullable + index | ✅ | `alembic/versions/046_*.py`; round-trip + backfill integration tests |
| 5 | `set_embedder_profile()` empty-collection short-circuit + populated dim-equality guard | ✅ | 9 S144 unit tests covering the dim-guard matrix |
| 6 | `DimensionMismatch` surfaces as HTTP 409 with `error_code = "RAG_DIM_MISMATCH"` | ✅ | `src/aiflow/api/v1/rag_collections.py`; 1 router unit + 1 integration |
| 7 | Admin page `/#/rag/collections` lists per-tenant with `?tenant=` deep-link | ✅ | `pages-new/RagCollections/index.tsx` + EN/HU locale; 1 Python Playwright spec |
| 8 | Admin page side drawer attaches/detaches profile via PATCH | ✅ | `RagCollectionDetailDrawer.tsx`; integration `populated dim-mismatch 409` |
| 9 | `RagMetricsHarness` emits JSONL rows with mrr_at_k / p95 / error_count | ✅ | `src/aiflow/services/rag_metrics/`; 6 unit + 1 integration (skip-by-default) |
| 10 | 20-item HU UC2 query corpus checked into the repo | ✅ | `data/fixtures/rag_metrics/uc2_aszf_query_set.json` |
| 11 | CLI runner `scripts/run_nightly_rag_metrics.py` | ✅ | Same |
| 12 | Grafana 4-panel dashboard JSON | ✅ | `docs/grafana/rag_collection_metrics_panel.json` |
| 13 | Operator runbook for nightly metrics | ✅ | `docs/runbooks/rag_metrics_nightly.md` |
| 14 | Alembic 047 swap legacy `UNIQUE (name)` → `UNIQUE (tenant_id, name)` | ✅ | `alembic/versions/047_*.py`; 2 alembic integration (round-trip + cross-tenant collision matrix) |
| 15 | BGE-M3 weight cache step in `nightly-regression.yml` | ✅ | `.github/workflows/nightly-regression.yml`; `actions/cache@v4` |
| 16 | Zero new feature flags, zero NULL-fallback regression | ✅ | Per-session golden-path runs (Sprint J UC2 MRR@5 ≥ 0.55 baseline preserved) |
| 17 | Zero skill code change | ✅ | `git diff` over `skills/` is empty across S143/S144/S145 |
| 18 | OpenAPI snapshot refreshed | ✅ | `docs/api/openapi.{json,yaml}` includes 3 new paths under `/api/v1/rag-collections` |

Sprint S closes green on all 18 criteria. The remaining `customer` column rename (SS-FU-1 + SS-FU-5) and the live Profile B MRR@5 measurement (SS-SKIP-2) are explicitly out-of-scope and tracked as follow-ups.

## Schema changes

Two additive migrations on `rag_collections`, applied in order. Both safe to run on a live tenant database with `tenant_id='default'` backfill from the server default (no application downtime, no application code change required between 045 and 047).

### Alembic 046 — multi-tenant + multi-profile foundation

```sql
ALTER TABLE rag_collections
  ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'default';

ALTER TABLE rag_collections
  ADD COLUMN embedder_profile_id TEXT NULL;

CREATE INDEX ix_rag_collections_tenant_id
  ON rag_collections (tenant_id);
```

The server default `'default'` backfills every existing row in a single statement. Downgrade drops the columns + index cleanly.

### Alembic 047 — `(tenant_id, name)` uniqueness swap

```sql
ALTER TABLE rag_collections
  DROP CONSTRAINT uq_rag_collections_name;

ALTER TABLE rag_collections
  ADD CONSTRAINT uq_rag_collections_tenant_id_name
  UNIQUE (tenant_id, name);
```

Pre-flight duplicate scan (`SELECT name, COUNT(*) FROM rag_collections GROUP BY name HAVING COUNT(*) > 1;`) returned 0 rows on the production-shape dataset, so the swap is metadata-only with zero data churn. Cross-tenant name reuse becomes legal — required for the multi-tenant story.

## Test deltas

| Suite | Sprint R tip | Sprint S tip | Δ |
|---|---|---|---|
| Unit | 2347 | **2379** | **+32** (S143 +14 / S144 +12 / S145 +6) |
| Integration | ~103 | **~113** | **+10** (S143 +4 / S144 +3 / S145 +3) |
| E2E collected | 429 | **430** | **+1** (S144 rag-collections Playwright) |
| API endpoints | 193 | **196** | **+3** (S144: list / detail / PATCH `embedder-profile`) |
| API routers | 30 | **31** | **+1** (S144: rag-collections) |
| UI pages | 25 | **26** | **+1** (S144: RagCollections) |
| Alembic head | 045 | **047** | **+2** (S143: 046 / S145: 047) |

Unit math: 2347 + 14 = 2361 (S143 tip) + 12 = 2373 (S144 tip) + 6 = 2379 (S145 tip).

## Test plan (post-merge)

- [x] **Unit** — `pytest tests/unit/ --no-cov -q`: 2379 passed, 1 skipped (xfail-quarantined: resilience 50ms timing flake; Sprint J carry, deadline 2026-04-30).
- [x] **Integration** — `pytest tests/integration/ -q --no-cov` on real PG (port 5433): all S143/S144/S145 integration tests green; rag_metrics harness integration is skip-by-default behind `AIFLOW_RUN_NIGHTLY_RAG_METRICS=1` + `OPENAI_API_KEY`.
- [x] **TypeScript** — `cd aiflow-admin && npx tsc --noEmit`: clean.
- [x] **Lint (Python)** — `ruff check src/ tests/`: clean.
- [x] **Lint (frontend)** — `cd aiflow-admin && npx eslint src/pages-new/RagCollections`: clean.
- [x] **OpenAPI snapshot** — `docs/api/openapi.{json,yaml}` regenerated, includes 3 new paths.
- [x] **S144 live-test** — `tests/ui-live/rag-collections.md` PASSED 2026-04-25 09:07 in S145 prereq run on a fresh `make api` + `npm run dev` stack.
- [ ] **First nightly regression run** (operator) — confirm BGE-M3 weight cache hits on second run; un-skipped 1024-dim integration tests pass.
- [ ] **First nightly metrics run** (operator) — provision `rag_collection_metrics_jsonl` table per runbook, schedule cron `scripts/run_nightly_rag_metrics.py`, import `docs/grafana/rag_collection_metrics_panel.json`, confirm MRR@5 panel renders ≥ 0.55 for the legacy 1536-dim collection.

## What's NOT in this sprint

| ID | Description | Target |
|---|---|---|
| SS-FU-1 | `create_collection` tenant-aware arg + `customer` deprecation | Separate refactor sprint |
| SS-FU-5 | `rag_collections.customer` column drop | Separate refactor (after SS-FU-1) |
| SS-SKIP-2 | Profile B (Azure OpenAI) live MRR@5 | Azure credit landing |
| S141-FU-1/2/3 | Per-skill PromptWorkflow migration (`email_intent_processor` / `invoice_processor` / `aszf_rag_chat`) | Sprint T (S147+) |
| SR-FU-4 | Live-stack Playwright for `/prompts/workflows` | Sprint T |
| SR-FU-5 | `vite build` pre-commit hook | Sprint T |
| SR-FU-6 | Langfuse workflow listing | Sprint T |
| Sprint J Clock seam | Resilience 50ms timing flake fix | **DEADLINE 2026-04-30 — overdue, S147 must triage** |

## Operator follow-up

After this PR merges and the operator pushes tag `v1.5.2`:

1. **Provision the metrics store table.** Per `docs/runbooks/rag_metrics_nightly.md`:
   ```sql
   CREATE TABLE IF NOT EXISTS rag_collection_metrics_jsonl (
     id BIGSERIAL PRIMARY KEY,
     ts TIMESTAMPTZ NOT NULL,
     collection_id TEXT NOT NULL,
     tenant_id TEXT NOT NULL,
     embedder_profile_id TEXT NULL,
     mrr_at_k DOUBLE PRECISION NOT NULL,
     p95_latency_ms DOUBLE PRECISION NOT NULL,
     error_count INTEGER NOT NULL,
     payload_jsonb JSONB NOT NULL
   );
   ```
2. **Import the Grafana dashboard.** `docs/grafana/rag_collection_metrics_panel.json` against the metrics-store datasource.
3. **Schedule the runner.** Cron `scripts/run_nightly_rag_metrics.py --collection <id> --query-set data/fixtures/rag_metrics/uc2_aszf_query_set.json --emit-jsonl /tmp/rag_metrics.jsonl` then `psql ... \copy rag_collection_metrics_jsonl FROM '/tmp/rag_metrics.jsonl'`.
4. **Run `bootstrap_bge_m3.py` locally if needed.** First nightly regression run will populate the GitHub Actions cache; local dev still needs `python scripts/bootstrap_bge_m3.py` to seed the weight directory before running the 1024-dim integration tests.
5. **Push the tag.** `git tag v1.5.2 -m "Sprint S — multi-tenant vector DB + nightly MRR@5"` already prepared on `chore/sprint-s-close`; push after merge.

## Rollback

1. **NULL-fallback rollback (primary).** Detaching `embedder_profile_id` to NULL on every collection (via the new `PATCH /api/v1/rag-collections/{id}/embedder-profile` with `embedder_profile_id: null`) returns each collection to legacy `self._embedder` semantics. Zero behaviour change relative to Sprint J tip on a NULL-profile collection.
2. **Per-tenant rollback** (after multi-tenant adoption). Setting all collections back to `tenant_id='default'` is a one-line UPDATE — the legacy single-tenant world is recoverable as long as no two collections share the same name across tenants.
3. **Schema rollback.** Alembic `downgrade -1` from 047 reinstates `UNIQUE (name)` (only if 0 cross-tenant name reuse). `downgrade -1` from 046 drops `tenant_id` + `embedder_profile_id` + the index. Both downgrades are well-tested in the alembic integration suite.
4. **Revert rollback.** 4 squash commits on `main` (`95ec89e` S143, `bc59a8f` S144, `ec3e672` chore env, `d6ee813` S145) are isolated; `git revert` on any subset restores prior state.
5. **Data rollback.** None for the harness — Sprint S writes zero metric rows into the AIFlow runtime DB. Operators control retention of the externally-provisioned `rag_collection_metrics_jsonl`.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
