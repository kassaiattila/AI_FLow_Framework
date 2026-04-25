# Sprint S / S144 — admin UI `/rag/collections` + per-tenant list + set-profile mutation

> **Branch:** `feature/s-s144-rag-collections-admin-ui`
> **Cut from:** `main` @ `95ec89e` (Sprint S S143 squash, PR #34)
> **Predecessor:** S143 — `RAGEngineService.query()` ProviderRegistry refactor + Alembic 046 `rag_collections.tenant_id` + `embedder_profile_id`.

## Summary

S144 makes the multi-tenant + multi-profile vector DB landed by S143
operator-visible. The `rag_collections` table, after S143, has a
`tenant_id` and an `embedder_profile_id` column — but neither was
queryable from the admin UI, and there was no way to attach a profile to
a collection without dropping into SQL. This PR closes that gap with a
read+mutation admin surface plus the React page that consumes it.

* `RAGEngineService.set_embedder_profile(collection_id, embedder_profile_id)`
  — new mutation method with a dimension-mismatch guard. Empty
  collections (`chunk_count == 0`) accept any known alias and refresh
  `embedding_dim` to match the new provider; populated collections
  require dim-equality (or, when detaching to NULL, that the existing
  `embedding_dim == 1536`, the legacy embedder dim). Violations raise
  `DimensionMismatch` (HTTP 409, `error_code = "RAG_DIM_MISMATCH"`).
* Three-route admin router at `/api/v1/rag-collections`:
  * `GET /` — paged list with optional `tenant_id` filter
  * `GET /{collection_id}` — single-collection detail
  * `PATCH /{collection_id}/embedder-profile` — attach/detach profile
* New admin page at `/#/rag/collections` (`pages-new/RagCollections/`) —
  table list, tenant chip filter with `?tenant=` deep-link, side drawer
  for the detail view + profile select + Save action. EN+HU locale,
  sidebar nav entry under `Tudasbazis → RAG kollekciok`.
* Tests:
  * **+9 unit (set_embedder_profile)** — unknown collection, unknown
    alias, empty-collection accepts + dim-update, populated dim-equal
    accept, populated dim-mismatch (1536→1024) raises, populated
    detach when dim != 1536 raises, populated detach when dim == 1536
    accepts, populated profile-to-profile dim-equal accept,
    `DimensionMismatch` error metadata.
  * **+3 unit (router)** — list filters by `tenant_id`, detail 404,
    PATCH surfaces `DimensionMismatch` as HTTP 409 with the structured
    `{error_code, message}` body.
  * **+3 integration (router, real PG on port 5433)** — two-tenant list
    filter, PATCH on empty collection persists (with cleanup),
    populated 1536-dim collection refuses 1024-dim profile attachment
    (DB row unchanged).
  * **+1 Python Playwright spec** at `tests/e2e/test_rag_collections.py`
    — list, filter, set-profile journey on the live admin stack.
* No Alembic migration (S143's `046` is still head). No skill-code
  change (per-skill use of the new mutation is deferred to a later
  sprint). NULL-fallback path from S143 is unchanged.

## Path note (deviation from session prompt)

The session prompt mounted the new router at `/api/v1/rag/collections`
— but the legacy `rag_engine.py` router already owns
`/api/v1/rag/collections` for ingest, query, document, chunk, feedback
and stats endpoints, and the existing UC2 RAG UI page (Dashboard,
`/#/rag`, `/#/rag/{id}`) consumes the legacy `CollectionResponse` shape
from those endpoints. Mounting a new admin router in front of those
paths would shadow the existing GET endpoints with an incompatible
`RagCollectionListResponse` shape and break UC2.

Decision: the new admin surface lives at `/api/v1/rag-collections`
(hyphenated). The capability is identical and the operator UX is
unchanged; only the URL prefix differs.

## Test plan

- [x] `pytest tests/unit/ --no-cov -q` — 2373 passed, 1 skipped (was
      2361 baseline, +12).
- [x] `pytest tests/integration/api/test_rag_collections_router.py
      tests/integration/services/rag_engine/ -q --no-cov` — 8 passed,
      1 skipped (the BGE-M3 weight-skipped test from S143).
- [x] `cd aiflow-admin && npx tsc --noEmit` — clean.
- [x] `cd aiflow-admin && npx eslint src/pages-new/RagCollections` — clean.
- [x] `ruff check src/aiflow/api/v1/rag_collections.py
      src/aiflow/services/rag_engine/service.py
      tests/unit/services/test_rag_engine_set_embedder_profile.py
      tests/unit/api/test_rag_collections_router.py
      tests/integration/api/test_rag_collections_router.py
      tests/e2e/test_rag_collections.py` — all checks passed.
- [x] `ruff format --check` — all formatted.
- [ ] **Live-test PENDING** — `tests/ui-live/rag-collections.md` is the
      operator-runbook for the Playwright MCP journey on a fresh
      `make api` + `npm run dev` stack. The autonomous session that
      authored this PR could not bring the full stack up itself; the
      operator should reproduce the journey before merge.
- [ ] `pytest tests/e2e/test_rag_collections.py -q` — the Python
      Playwright spec; run after `make api` + `npm run dev` are up and
      the operator has logged in once with the seeded admin creds.

## Numbers

| | Before | After | Delta |
|---|---|---|---|
| API endpoints | 193 | 196 | +3 |
| API routers | 30 | 31 | +1 |
| Unit tests | 2361 | 2373 | +12 |
| Integration tests | ~107 | ~110 | +3 |
| E2E tests | 429 | 430 | +1 |
| UI pages | 25 | 26 | +1 |
| Alembic head | 046 | 046 | — |

## Open follow-ups (not closed by S144)

| ID | Description | Target |
|---|---|---|
| SS-FU-1 | `create_collection` tenant-aware arg + `customer` deprecation | Separate refactor sprint |
| SS-FU-3 | Nightly MRR@5 scheduled job + Grafana panel | S145 |
| SS-FU-4 | `(tenant_id, name)` unique constraint on `rag_collections` | S145 |
| SS-FU-5 | `rag_collections.customer` deprecation | Separate refactor |
| SS-SKIP-1 | BGE-M3 weight CI preload | S145 |
| SS-SKIP-2 | Profile B (Azure OpenAI) live MRR@5 | Azure credit landing |

Carried-forward Sprint J / Sprint M items remain unchanged (resilience
`Clock` seam, BGE-M3 weight cache as CI artifact, AppRole prod IaC,
Langfuse v3→v4 migration, etc.).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
