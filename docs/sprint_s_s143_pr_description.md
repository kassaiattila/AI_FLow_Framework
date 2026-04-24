# Sprint S S143: `RAGEngineService.query()` ProviderRegistry refactor + Alembic 046 (flag-free, backward-compat)

**Parent plan:** `01_PLAN/116_SPRINT_S_FUNCTIONAL_VECTOR_DB_PLAN.md` / `01_PLAN/114_CAPABILITY_ROADMAP_Q_R_S.md` §4.
**Base:** `main` @ `ffd7618` (Sprint R S142 squash, tag `v1.5.1`).
**Branch:** `feature/s-s143-rag-query-registry`.
**Target tag (post Sprint S close):** `v1.5.2` (queued behind S144 + S145 + S146).

## Summary

Closes **Sprint J FU-1** — the oldest open carry-forward (opened 2026-04-25). Before this PR, `RAGEngineService.query()` always produced query vectors via the constructor-injected `self._embedder` (legacy 1536-dim `Embedder`). Collections ingested through the Sprint J provider-registry path at 1024 dim (BGE-M3 Profile A) could be **stored** but never **retrieved** — querying always yielded zero hits because pgvector rejects cross-dim comparisons and the query side always emitted 1536-dim vectors.

S143 threads a per-collection embedder through the query path:

- **Alembic 046** additive: `rag_collections.tenant_id TEXT NOT NULL DEFAULT 'default'` + `rag_collections.embedder_profile_id TEXT NULL` + `ix_rag_collections_tenant_id`. Downgrade drops the index and both columns.
- `RAGEngineService.query()` calls `self._resolve_query_embedder(coll)` before the embed step. Decision tree:
  - `coll.embedder_profile_id IS NULL` → returns `self._embedder` (byte-for-byte identical to pre-S143 behaviour — every existing 1536-dim collection lands here).
  - Set to `bge_m3` / `azure_openai` / `openai` → returns a `_QueryEmbedderAdapter` over a freshly-instantiated provider class. The adapter exposes `embed_query(text) -> list[float]` over the registry's `embed([...]) -> list[list[float]]` surface, so the caller is uniform.
  - Unknown alias → raises `UnknownEmbedderProfile` (`AIFlowError`, `is_transient=False`, `error_code="UNKNOWN_EMBEDDER_PROFILE"`). `query()` catches it and returns a user-facing error `QueryResult` — no exception escapes the service.
- `CollectionInfo` gains `tenant_id: str = "default"` + `embedder_profile_id: str | None = None`. `list_collections` / `get_collection` SELECTs extend to read both with defensive row-length checks (so existing unit-test mocks keep working).

**No flag.** Backward compatibility is guaranteed by the NULL fallback, not a toggle. Every currently-live 1536-dim collection produces `embedder_profile_id = NULL` after the migration and hits the `self._embedder` branch.

## Test plan

- [x] Full unit regression: **2361 passed** (baseline 2347 → +14 S143 resolver/adapter tests).
- [x] `tests/unit/services/test_rag_engine_service.py` + `test_graph_rag_service.py` + `test_extra_coverage.py` — **15/15 green** (defensive row-length reads keep legacy mocks working).
- [x] Alembic 046 upgrade/downgrade round-trip — **2/2 green** on real Postgres 5433.
  - server-default backfill: pre-existing rows get `tenant_id='default'` on upgrade, validated via INSERT → SELECT.
- [x] **1024-dim BGE-M3 queryability** — 2/2 green on **real Postgres + real BGE-M3 weights (2GB)** (`tests/integration/services/rag_engine/test_query_1024_dim.py`):
  - resolver + adapter produce 1024-dim vectors from real `BGEM3Embedder`.
  - pgvector flex-dim `.search()` retrieves a seeded chunk via the real query vector — **Sprint J FU-1 functionally closed**.
- [x] Ruff + ruff-format clean on all 5 modified/new paths.
- [ ] UC2 MRR@5 baseline re-run — deferred to S144 (same branch, subsequent session), Profile A target ≥ 0.55 unchanged per STOP condition.
- [ ] Cross-UC `ci-cross-uc` suite — runs in CI, unchanged expectation (no UC1/UC3/UC4 surface touched).

## Scope explicitly out

- UC2 `aszf_rag_chat` skill not migrated to set `embedder_profile_id` on its collections — remains a Sprint J-era 1536-dim collection, served by the NULL fallback unchanged. Opt-in migration is a follow-up (per collection, per tenant).
- No admin UI for the new columns — lands in S144.
- No `(tenant_id, name)` unique constraint yet — waits for S144 once tenants are actually upsertable through the UI.
- LLM answer quality (`QueryResult.answer`) is out of scope; the integration proof focuses on embedding + retrieval, not generation.

## Rollback

Three levels, any one sufficient:

1. **No-op rollback.** Every existing collection has `embedder_profile_id = NULL` — even if the new code path had a bug, the NULL branch is the pre-S143 line-for-line behaviour, so no currently-live query is affected.
2. **Revert commit.** Single squash-merge. `_resolve_query_embedder` + adapter + error class all live in one file; the tests are separate.
3. **`alembic downgrade -1`.** Drops the index and both columns. Zero-downtime (additive in both directions).

## Changed files

```
01_PLAN/116_SPRINT_S_FUNCTIONAL_VECTOR_DB_PLAN.md                                       (new)
alembic/versions/046_rag_collections_tenant_embedder_profile.py                          (new)
src/aiflow/services/rag_engine/service.py                                                (edited)
tests/integration/alembic/test_046_rag_collections_tenant_embedder_profile.py            (new)
tests/integration/services/rag_engine/test_query_1024_dim.py                             (new)
tests/unit/services/test_rag_engine_query_embedder_resolver.py                           (new)
CLAUDE.md                                                                                (banner + key numbers)
session_prompts/NEXT.md                                                                  (S143 prompt → consumed)
docs/sprint_s_s143_pr_description.md                                                     (this file)
```

## Skipped items (tracker — see 116_SPRINT_S §8)

| ID | Where | What | Unskip condition |
|---|---|---|---|
| SS-SKIP-1 | `tests/integration/services/rag_engine/test_query_1024_dim.py` | Skip if BGE-M3 weights not in `.cache/models/bge-m3` or `sentence_transformers` missing. On this branch both conditions held (weights pre-cached from Sprint J S103), so both tests executed and passed — but the skip guard stays in place for fresh CI runners. | CI preloads BGE-M3 weights via `scripts/bootstrap_bge_m3.py` (Sprint J FU carry → Sprint S S145 weekly matrix). |
| SS-SKIP-2 | Plan doc §3 success metrics | Profile B (Azure OpenAI) MRR@5 measurement | Azure OpenAI credit available. |

## Follow-ups opened by this session (SS-FU-*)

- **SS-FU-1** `create_collection` should accept `tenant_id` + `embedder_profile_id` as first-class args (currently only reachable via direct SQL). Lands in S144 where the admin UI needs the upsert surface.
- **SS-FU-2** `/rag/collections` admin UI — table + per-tenant filter + "Set embedder profile" action. S144.
- **SS-FU-3** Nightly MRR@5 scheduled job + Grafana panel. S145.
- **SS-FU-4** `(tenant_id, name)` unique constraint once S144's UI can upsert distinct tenants.
- **SS-FU-5** `rag_collections.customer` column is today NOT NULL + semantically redundant with `tenant_id` — consolidate or deprecate in a later additive migration.

## Regression commands

```bash
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/ --no-cov -q                    # 2361 passed
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/integration/alembic/test_046_rag_collections_tenant_embedder_profile.py --no-cov -q
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/integration/services/rag_engine/test_query_1024_dim.py --no-cov -q
.venv/Scripts/python.exe -m ruff check src/ tests/ alembic/
.venv/Scripts/python.exe -m ruff format --check src/ tests/ alembic/
```

🤖 Generated with [Claude Code](https://claude.com/claude-code)
