# /live-test — rag-collections (Sprint S / S144)

> **Status:** PENDING — automated authoring only. The Playwright MCP run
> against a live `make api` + `npm run dev` stack must be reproduced by an
> operator before this PR merges; the report below documents the exact
> journey to follow and the data-testid hooks the page exposes.

- **Run date:** _to be filled when the operator reproduces the journey_
- **Runner:** Playwright MCP (browser_navigate / browser_click /
  browser_select_option / browser_evaluate / browser_snapshot)
- **Target:** `http://localhost:5173/#/rag/collections`
- **API:** `http://localhost:8102` (uvicorn factory mode — must include
  the new `rag_collections_router` mounted by `aiflow.api.app:create_app`;
  the OpenAPI surface should expose `/api/v1/rag-collections`,
  `/api/v1/rag-collections/{id}`, `/api/v1/rag-collections/{id}/embedder-profile`)
- **Services:** PostgreSQL (5433, Docker), Redis (6379, Docker), pgvector
  extension enabled. Alembic head must be `046`.

## Journey

1. **Login** — `/#/login` → fill `admin@aiflow.local` / `AiFlowDev2026`.
2. **Seed** two collections via direct asyncpg or the seeded admin token:
   ```sql
   INSERT INTO rag_collections
       (id, name, customer, skill_name, tenant_id, embedder_profile_id,
        embedding_dim, chunk_count)
   VALUES
       (gen_random_uuid(), 's144-live-bestix-coll', 'bestix', 'rag_engine',
        'bestix', NULL, 1536, 0),
       (gen_random_uuid(), 's144-live-doha-coll',   'doha',   'rag_engine',
        'doha',   'bge_m3', 1024, 0);
   ```
3. **Navigate** — `/#/rag/collections`. Sidebar group `Tudasbazis →
   RAG kollekciok` highlighted. Page header "RAG Collections" rendered with
   the `Live` badge.
4. **Render assertions** — both rows visible in the table:
   - `s144-live-bestix-coll` row: tenant `bestix`, badge `default`
     (yellow), dim `1536`, chunks `0`.
   - `s144-live-doha-coll`   row: tenant `doha`,   badge `bge_m3`
     (green),  dim `1024`, chunks `0`.
   - `data-testid="rag-collections-total"` shows `2 collections`.
5. **Filter** — type `bestix` into the tenant input + click `Apply`. URL
   updates to `?tenant=bestix`. Only the bestix row remains. Doha row is
   gone (`expect(row_doha).to_have_count(0)`).
6. **Drawer** — click the bestix row. The `rag-collections-drawer`
   becomes visible. The profile select shows `Default (legacy 1536-dim)`.
7. **Set profile** — change the select to `OpenAI (surrogate)` and click
   `Save`. With a valid OpenAI API key the toast
   `Embedder profile updated.` appears; without one a `409 RAG_DIM_MISMATCH`
   error message appears in the drawer error pane (the OpenAI embedder
   probe failed). Both outcomes prove the PATCH round-trip reached the
   service layer.
8. **Hard reload** — close the drawer, `goto`
   `/#/rag/collections?tenant=bestix`. The badge on the bestix row reads
   `openai` (200 path) or `default` (409 path). Either confirms there is
   no optimistic-only state.
9. **Cleanup** — `DELETE FROM rag_collections WHERE tenant_id IN ('bestix',
   'doha')` (or run the Python `tests/e2e/test_rag_collections.py` test —
   it self-cleans).

## Data-testid map

| testid | element |
|---|---|
| `rag-collections-filter` | tenant input + apply/clear buttons wrapper |
| `rag-collections-tenant-input` | tenant filter input |
| `rag-collections-tenant-apply` | Apply button |
| `rag-collections-tenant-clear` | Clear button (visible only when filter active) |
| `rag-collections-total` | row count summary |
| `rag-collections-table` | wrapper around the `<table>` |
| `rag-collections-row` (with `data-collection-id`, `data-tenant`) | one table row |
| `rag-collections-profile-badge` (with `data-profile`) | profile badge on a row or drawer |
| `rag-collections-empty` | empty state |
| `rag-collections-drawer` | side drawer overlay |
| `rag-collections-drawer-close` | drawer × button |
| `rag-collections-profile-select` | drawer profile select |
| `rag-collections-drawer-save` | drawer Save button |
| `rag-collections-drawer-toast` | success toast |
| `rag-collections-drawer-error` | error message pane |

## Open follow-ups for the next live run

- **Untitled UI badge variants** — confirm the four badge palettes
  (yellow / green / blue / grey) render in dark mode without raw hex.
- **OpenAI key in CI** — `tests/e2e/test_rag_collections.py` accepts
  either toast or dim-mismatch error (409) so the spec passes both
  with and without `OPENAI_API_KEY`. Live-test can assert the toast
  branch only when the key is present.
- **(tenant_id, name) unique constraint (SS-FU-4)** — deferred to S145.
  Until then the seed SQL above must use distinct names per tenant.
