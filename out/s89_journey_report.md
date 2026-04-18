# S89 Journey E2E Report — v1.4.4.2

- **Run date:** 2026-04-26
- **Branch:** `feature/v1.4.4-consolidation` @ HEAD `82d0cd8`
- **Environment:** API 8102 (v1.4.3), UI via Vite on :5173 *and* :5174 (both serving `aiflow-admin`; the e2e conftest pins `BASE_URL=http://localhost:5174`), Postgres 5433, Redis 6379, Kroki, Langfuse — all `ok` in `/health`.
- **Command:**
  ```
  .venv/Scripts/python.exe -m pytest \
    tests/e2e/test_journey_admin.py tests/e2e/test_journey_document.py \
    tests/e2e/test_journey_navigation.py tests/e2e/test_journey_pipeline.py \
    tests/e2e/test_journey_quality.py tests/e2e/test_journey_rag.py \
    --headed --browser chromium -v
  ```
- **Duration:** 367s (≈6m07s).
- **Raw log:** `out/s89_journey_raw.log` (not committed — noise).

## Environment evidence (LEPES 1–2)

| Check | Result |
|---|---|
| `git log --oneline -1` | `82d0cd8 chore(v1.4.4): S88 — version reconcile + port doc + alembic head-relative + stale prompt archive` |
| `aiflow._version.__version__` | `1.4.3` |
| Docker `postgres` / `redis` | `Up 44 hours (healthy)` (`07_ai_flow_framwork-db-1`, `07_ai_flow_framwork-redis-1`) |
| `GET http://localhost:8102/health` | `200` `{"status":"ready","version":"1.4.3"}` — all 5 checks `ok` (database, pgvector v0.8.1 with 5 collections/6321 chunks, redis, langfuse) |
| `GET http://localhost:5173/` | `200` — Vite dev server serving `aiflow-admin` |
| `GET http://localhost:5174/` | `200` — second Vite instance (auto-port fallback when 5173 was occupied on start) |
| `GET http://localhost:5173/health` (proxy) | returns backend JSON `version=1.4.3` — proxy `/health` → `8102` confirmed |
| `GET http://localhost:5173/api/v1/skills` (proxy) | `401 {"detail":"Authentication required"}` — proxy `/api` → `8102` confirmed (unauthenticated, as expected) |
| `cd aiflow-admin && npx tsc --noEmit` | 0 errors |
| Vite config (`aiflow-admin/vite.config.ts`) | `port 5173`, proxies `/api` and `/health` to `http://localhost:8102` with SSE-friendly headers |

Browser-visual checks (source badge render, Dashboard skills widget demo-vs-backend coloring, notification bell) are exercised by the Playwright journey suites rather than by a separate manual browser session; see suite results below.

## Suite results

| Suite | Pass | Fail | Notes |
|---|---:|---:|---|
| `test_journey_admin.py`        | 7  | 2 | 2 failures: dashboard→services nav, admin "create user" modal |
| `test_journey_document.py`     | 10 | 0 | GREEN |
| `test_journey_navigation.py`   | 7  | 3 | Sidebar group count mismatch + journey-card destinations mismatch |
| `test_journey_pipeline.py`     | 9  | 1 | Runs table: no rows AND no empty state shown |
| `test_journey_quality.py`      | 9  | 0 | GREEN |
| `test_journey_rag.py`          | 5  | 5 | Locator/visibility failures, source tag missing, modal/delete-dialog absent |
| **Total**                      | **47** | **11** | 58 tests, 81.0% pass |

## Failure detail

### test_journey_admin.py

1. `TestAdminJourney::test_dashboard_to_services_nav` — `AssertionError: Locator expected to be visible` at line 61. Journey click from Dashboard to the Services page does not land on the expected visible anchor.
2. `TestAdminDeepJourney::test_admin_create_user_modal` — `playwright ... TimeoutError: Locator.click: Timeout 30000ms exceeded`. The "Create user" button cannot be clicked within 30s — either absent, covered, or renamed.

### test_journey_navigation.py

3. `TestJourneyNavigation::test_sidebar_has_6_groups` — `AssertionError: Settings group missing` at line 55. Sidebar groups count does not include the expected "Settings" group.
4. `TestJourneyNavigation::test_dashboard_journey_cards` — `AssertionError: Journey card click didn't navigate to documents: http://localhost:5174/#/emails` at line 106. The "Documents" journey card navigates to `/emails` instead of `/documents`.
5. `TestCrossJourneyNavigation::test_dashboard_all_cards_unique_destinations` — `AssertionError: Journey cards navigate to duplicate pages` at line 262. Dashboard cards collide onto the same destinations (`/emails`, `/rag`, `/runs`, `/process-docs`, `/cubix`, `/rag`, `/emails`, `/documents`), suggesting card-route wiring has drifted from the one-card-one-destination contract.

### test_journey_pipeline.py

6. `TestPipelineDeepJourney::test_runs_table_shows_status_badges` — `AssertionError: Runs page has no rows and no empty state` at line 167. The Runs page shows neither data rows nor the demo/empty state fallback — violates the "no silent mock" / explicit-state UI contract.

### test_journey_rag.py

7. `TestRagJourney::test_rag_to_services_navigation` — `AssertionError: Locator expected to be visible` at line 49.
8. `TestRagJourney::test_rag_to_process_docs_ai_flow` — `AssertionError: Locator expected to be visible` at line 97.
9. `TestRagDeepJourney::test_rag_collections_table_or_empty` — `AssertionError: Source tag (Demo/Live) not visible on RAG page with data` at line 163. Source badge missing on RAG page — regression against memory rule *No silent mock data*.
10. `TestRagDeepJourney::test_rag_create_collection_modal` — `AssertionError: New Collection modal did not appear` at line 191.
11. `TestRagDeepJourney::test_rag_collection_delete_dialog` — `AssertionError: Delete confirmation dialog did not appear` at line 239.

## STOP-condition evaluation

The S89 prompt defines a **HARD** stop:

> >2 journey suites fail with real regressions (not env) → halt, bug triage session before S90.

4 suites (admin, navigation, pipeline, rag) have failures. The failures fall into three categories, all non-env:

- **UI contract drift** (likely regressions): Dashboard journey-card destinations (items 4, 5), sidebar group count (item 3), RAG source tag (item 9), Runs empty state (item 6). These violate explicit contracts we've previously asserted (journey cards map 1-to-1, every data surface shows a Demo/Live badge).
- **Element-locator drift** (ambiguous — regression OR test staleness): items 1, 2, 7, 8, 10, 11 — locators for buttons/modals/anchors fail to resolve. Could be that the UI element was renamed/removed (regression) or that the test locator is outdated (test drift). Requires per-test triage.
- **No env-only failures** observed. API, proxy, auth fixture, DB, and browser all work — `test_journey_document` (10/10) and `test_journey_quality` (9/9) pass end-to-end, proving the environment is sound.

**Verdict: HARD stop trigger hit.** S90 cannot be the originally planned coverage-uplift session — it must first triage these 11 failures. S90 becomes "journey bug triage", and the coverage-uplift session shifts to S91.

## Follow-ups (for S90 — bug triage)

For each of the 11 failures, classify as (a) UI regression to fix, (b) stale test to update, (c) data-seeding gap. Seed baseline:

- Items 4 and 5 should be diagnosed first — Dashboard journey-card routing is a single-point regression that probably trips multiple tests at once.
- Item 3 (sidebar "Settings" group) is either a UI regression or a deliberate rename — check `src/layout/Sidebar.tsx` against test expectations.
- Item 9 (RAG source tag missing) is the most important from a product-contract standpoint (memory: *No silent mock data*) — fix the UI before anything else in that suite.
- Items 1, 2, 7, 8, 10, 11 should be triaged by opening the failing page manually in the already-running Vite at `http://localhost:5174/#/…` and walking the test steps by hand.

Do not attempt to suppress/skip failing tests. Quarantine is only acceptable if a failure is confirmed as test drift AND the quarantine is capped at 5 days per testing rules.
