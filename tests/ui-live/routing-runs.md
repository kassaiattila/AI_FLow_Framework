# Live UI journey — `/routing-runs` (Sprint X / SX-3)

## Utolso futtatas

### 2026-04-27 17:57 — PASS (12/12, 1 UX bug found + fixed)

**Stack state (preflight PASS):**
- API on http://127.0.0.1:8102 — `/health` ready
- Vite UI on http://127.0.0.1:5173 — serving
- PostgreSQL container healthy, Alembic head=050
- Seed: 13 → 14 rows (12 default + 1 other-tenant + 1 mid-test refresh seed)
- JWT auth via `admin@bestix.hu`, persisted to `localStorage.aiflow_token`

**Browser (Playwright MCP plugin) — 12/12 verified:**

| # | Scenario | Result | Evidence |
|---|---|---|---|
| T1 | Lista (≥11 sor) + stats panel + sidebar nav | ✅ | 12 rows, Osszes futas=12, all 5 outcome cards rendered, screenshot saved |
| T2 | `nonexistent_doctype_xyz` → empty-state copy | ✅ | "Nincs talalt routing run a szurokkel" rendered |
| T3 | `hu_invoice` filter | ✅ | 7 rows, all `hu_invoice`, conf 90–95% |
| T4 | `refused_cost` outcome filter | ✅ | 1 row, **violet pill** (`bg-violet-50 text-violet-700`) |
| T5 | `hu_invoice` AND `partial` combo | ✅ | 1 row, **amber pill** (`bg-amber-50 text-amber-700`) |
| T6 | Drawer opens on row click + 8 fields | ✅ | 8 DrawerField labels, metadata 9185 chars pretty-printed |
| T7 | Truncated metadata banner + flag | ✅ | "A metadata levagva a 8 KB limithez (62)" banner visible, `_truncated:true` in JSON |
| T8a | **ESC closes drawer** | **❌ → ✅ AFTER FIX** | Bug found live; fixed in `RoutingRuns.tsx` with 11-line `useEffect` keydown listener |
| T8b | Backdrop click closes drawer | ✅ | Drawer dismissed |
| T8c | X button (`aria-label=close-drawer`) closes drawer | ✅ | Drawer dismissed |
| T9 | Email deep-link → `/#/emails/{uuid}` | ✅ | URL navigated correctly; row-level `e.stopPropagation()` works |
| T10 | Pagination at single-page boundary | ✅ | Both Prev + Next buttons `disabled` |
| T11 | Refresh refetches table + stats | ✅ | 12 → 13 rows after `seed_routing_runs.py --extra 1` + Frissites click |
| T12a | Tenant filter `other-tenant` shows 1 row | ✅ | 1 row, total stat=1 |
| T12b | Cross-tenant detail GET (wrong tenant) | ✅ | HTTP **404** (no leakage) |
| T12c | Cross-tenant detail GET (correct tenant) | ✅ | HTTP **200**, row served |

**Console error audit (full session):**
- 0 unexpected errors.
- 2 × 404 on `/api/v1/emails/{uuid}` — expected (seed `email_id`s are random UUIDs without matching `workflow_runs` rows; EmailDetail page returns 404. This is a *test corpus artifact*, not a UI bug.).
- 1 × 404 on routing-runs detail with wrong tenant — this IS the T12 cross-tenant assertion proving the SQL filter rejects cross-tenant guesses.

**Network audit (`/api/v1/routing-runs/*`):** 14 requests, 13 × 200 + 1 × deliberate 404. Every call routed correctly; pagination params + filter params propagated as expected.

**Bug found in live testing → fixed in same session:**

ESC key did not close the drawer. Source review had predicted this (no `useEffect` keydown listener). Live Playwright confirmed it. Fix landed in `aiflow-admin/src/pages-new/RoutingRuns.tsx` (between `closeDrawer` definition and the JSX return) — listener attaches only while `drawerRow` is open so it doesn't intercept ESC for the rest of the page. tsc clean. Vite HMR picked up the change; re-running T8a confirmed PASS.

**Ossz ido:** ~14 minutes (preflight + 12 scenarios + 1 fix + re-verify + report).

---

### 2026-04-27 17:30 — PARTIAL (backend PASS, browser BLOCKED — superseded above by 17:57 PASS)

**Stack state (preflight PASS):**
- API: `http://127.0.0.1:8102/health` → `{status: "ready", db: ok, pgvector: ok, redis: ok, langfuse: ok}`
- Vite UI: `http://127.0.0.1:5173/` → 200 OK
- PostgreSQL: container `07_ai_flow_framwork-db-1` healthy
- Alembic head: `050` (routing_runs table created)
- Seed: `scripts/seed_routing_runs.py` — 13 rows inserted (12 default + 1 other-tenant)
- Auth: `POST /api/v1/auth/login` (admin@bestix.hu) → JWT issued OK

**Backend (API) layer — 12/12 PASS via authenticated curl smoke against the live FastAPI:**

| # | Scenario | Result |
|---|---|---|
| T1 | List default tenant (≥11 rows expected) | ✅ 12 rows |
| T2 | Empty filter (`doctype_detected=nonexistent_doctype_xyz`) | ✅ 0 rows |
| T3 | `doctype_detected=hu_invoice` | ✅ 7 rows, all hu_invoice |
| T4 | `extraction_outcome=refused_cost` | ✅ 1 row, outcome=refused_cost |
| T5 | `hu_invoice` AND `partial` combination | ✅ 1 row matches both |
| T10 | `limit=500` (>200 cap) | ✅ HTTP 422 |
| T12a | Cross-tenant detail GET (wrong tenant) | ✅ HTTP 404 (no leakage) |
| T12b | Cross-tenant detail GET (correct tenant) | ✅ HTTP 200 |
| Stats | `total_runs` for default tenant | ✅ 12 |
| Stats | `by_doctype` distribution | ✅ 7 hu_invoice + 3 NULL + 2 hu_id_card |
| Stats | `by_outcome` distribution | ✅ 8 success + 1 partial + 1 failed + 1 refused_cost + 1 skipped |
| Stats | `by_extraction_path` distribution | ✅ 9 invoice + 2 doc_recognizer + 1 skipped |

**Browser (UI rendering) layer — BLOCKED:**

The Playwright MCP server (`mcp__playwright__browser_*` or
`mcp__plugin_playwright_playwright__browser_*`) is **NOT REGISTERED** in this
Claude Code session. `ToolSearch` for "playwright browser navigate / click /
screenshot / snapshot / evaluate" returned **zero matches** — only Figma,
Miro, IDE, ClaudeTalkToFigma MCPs were registered. The skill protocol
explicitly requires those tools to drive a real browser; without them the
following five UI-rendering scenarios CANNOT be honestly verified:

- T6: Drawer opens on row click + 8 fields populated
- T7: Truncated-metadata amber banner renders
- T8: Drawer closes on X button AND backdrop click
- T9: Email deep-link navigates to `/emails/{id}`
- T11: Refresh button re-fetches table + stats

**Action required to unblock the browser layer:**

1. Add a Playwright MCP server entry to `.mcp.json` (project) or
   `~/.claude.json` (user). Example:
   ```jsonc
   {
     "mcpServers": {
       "playwright": {
         "command": "npx",
         "args": ["@modelcontextprotocol/server-playwright"]
       }
     }
   }
   ```
2. Restart the Claude Code session so the new MCP server registers.
3. Re-run `/live-test routing-runs`.

**Findings (usability — assessed via UI source review, not live render):**

- The `RoutingRuns.tsx` page renders 5 outcome pills with distinct semantic
  colours (success=emerald, partial=amber, failed=rose, refused_cost=violet,
  skipped=slate). The mapping is in `OUTCOME_PILL_CLASS` at
  `aiflow-admin/src/pages-new/RoutingRuns.tsx:73-83`.
- Drawer accessibility: backdrop has `aria-hidden`, drawer has
  `aria-label="routing-run-drawer"`, close button has
  `aria-label="close-drawer"`. ESC key handler is **NOT** wired —
  Test 8 will fail on ESC unless we add a `useEffect` with a keydown
  listener. Recommend follow-up.
- Email deep-link does `e.stopPropagation()` correctly to avoid the
  parent row's drawer-open handler (line 411).

**Total elapsed time:** ~6 minutes for backend smoke + report writing.

---

@test_registry:
suite: ui-live
component: aiflow-admin.RoutingRuns
covers:
- aiflow-admin/src/pages-new/RoutingRuns.tsx
- src/aiflow/api/v1/routing_runs.py
- src/aiflow/services/routing_runs/repository.py
- alembic/versions/050_routing_runs.py
phase: v1.8.0
priority: high
requires_services: [postgresql, fastapi, vite]
tags: [ui-live, routing-runs, sprint-x, sx-3]

## Pre-conditions

Run via `/live-test routing-runs`. Requires:

- API up on http://localhost:8102 (`bash scripts/start_stack.sh --with-api`)
- Vite dev server up on http://localhost:5173 (`bash scripts/start_stack.sh --with-ui`)
- Alembic 050 applied (`PYTHONPATH=src .venv/Scripts/python.exe -m alembic upgrade head`)
- Seed rows inserted via `scripts/seed_routing_runs.py` (≥ 10 rows covering all five
  outcome values, three doctype variants, one truncated-metadata row).

## Authentication

Login first via `POST /api/v1/auth/login` with default dev credentials
(see `aiflow-admin/src/pages-new/Login.tsx` for the form). Persist the JWT
in `localStorage.aiflow_token` so each subsequent navigation reuses it.

## Test corpus assumptions

The seed script writes:

- **5 × `hu_invoice` / `success` / `invoice_processor`** — varying cost (0.001 – 0.012)
  and latency (120 – 480 ms).
- **2 × `hu_id_card` / `success` / `doc_recognizer_workflow`** — illustrates the
  non-invoice path.
- **1 × `hu_invoice` / `partial` / `invoice_processor`** — multi-attachment email,
  one failure.
- **1 × `unknown` / `failed` / `invoice_processor`** — fallback policy hit.
- **1 × NULL doctype / `refused_cost` / `invoice_processor`** — ceiling refused.
- **1 × NULL doctype / `skipped` / `skipped`** — extraction disabled fallback.
- **1 × `hu_invoice` / `success` / truncated metadata** — metadata array padded
  past the 8 KB cap so the truncation banner renders in the drawer.

All seeded rows belong to `tenant_id = "default"`. One extra row is inserted
under `tenant_id = "other-tenant"` so we can verify the cross-tenant URL guard.

---

## Test 1 — Golden path: list renders with seeded rows

Steps:

1. Navigate to `http://localhost:5173/#/routing-runs`.
2. Wait for the page header: `getByRole('heading', { name: /routing trail/i })`.
3. Wait for the stats panel: `getByLabel('routing-runs-stats')`.
4. Wait for the table: `getByLabel('routing-runs-table')`.
5. Assert ≥ 11 data rows render (header + 11 data rows).
6. Assert the "Total runs" stat reads ≥ 11.

**PASS criteria:** header + table + stats card visible and `Total runs ≥ 11`.

## Test 2 — Empty state when filter matches nothing

Steps:

1. Type `nonexistent_doctype_xyz` into the **Doctype** filter.
2. Wait for the table to refetch (XHR settles).
3. Assert the empty-state copy renders:
   `getByText(/No routing runs match the current filters/i)`.
4. Clear the filter; assert rows reappear.

**PASS criteria:** empty-state row visible while filter is active; rows return on clear.

## Test 3 — Filter by doctype narrows results

Steps:

1. Type `hu_invoice` into the **Doctype** filter; wait for refetch.
2. Assert every visible doctype cell reads `hu_invoice`.
3. Assert the URL query string sent to `/api/v1/routing-runs/` contains
   `doctype_detected=hu_invoice` (intercept network or assert via column data).

**PASS criteria:** all visible rows have `doctype_detected="hu_invoice"`.

## Test 4 — Filter by outcome (refused_cost variant)

Steps:

1. Reset filters.
2. Open the **Outcome** dropdown; select `refused_cost`.
3. Wait for the table to refetch.
4. Assert exactly 1 row visible AND its outcome pill reads `refused_cost`
   AND its pill class includes `bg-violet-` (the violet outcome colour
   defined in `OUTCOME_PILL_CLASS`).

**PASS criteria:** 1 row visible with violet `refused_cost` pill.

## Test 5 — Filter combination (doctype AND outcome)

Steps:

1. Reset filters.
2. Set **Doctype** = `hu_invoice` AND **Outcome** = `partial`.
3. Wait for refetch.
4. Assert exactly 1 row visible AND its doctype reads `hu_invoice`
   AND its outcome pill reads `partial` (amber colour).

**PASS criteria:** the AND combination narrows to exactly the 1 partial-hu_invoice row.

## Test 6 — Drawer opens on row click + metadata visible

Steps:

1. Reset filters.
2. Click the first data row.
3. Wait for the drawer: `getByLabel('routing-run-drawer')`.
4. Assert heading reads "Routing run detail".
5. Assert the metadata `<pre>` block is non-empty AND contains
   `"attachments"` (flag-on rows) OR `"flag_off"` (flag-off rows).
6. Assert the eight `DrawerField` blocks are populated (created_at,
   tenant_id, intent_class, doctype_detected, extraction_path,
   extraction_outcome, cost_usd, latency_ms).

**PASS criteria:** drawer opens, all eight fields populated, JSON block valid.

## Test 7 — Drawer truncated-metadata banner

Steps:

1. Reset filters.
2. Open the **Doctype** filter, type `hu_invoice`, then click rows
   until you find the one whose JSONB `_truncated` flag is set
   (the seed row with padded attachments). Heuristic: scan rows for
   the seeded marker filename `truncated_marker.pdf` in metadata.
3. Open that row's drawer.
4. Assert the amber truncation banner is visible:
   `getByText(/Metadata was truncated to fit the 8 KB cap/i)`.
5. Assert the truncated-count badge reads ≥ 1.

**PASS criteria:** amber banner visible, count > 0 displayed.

## Test 8 — Drawer close (X button) AND backdrop click

Steps:

1. From Test 6's open drawer, click `getByLabel('close-drawer')`.
2. Assert the drawer disappears.
3. Open another row → drawer reopens.
4. Click the dimmed backdrop (outside the drawer aside).
5. Assert the drawer disappears again.

**PASS criteria:** drawer closes via both X button and backdrop click.

## Test 9 — Email deep-link navigates to /emails/{id}

Steps:

1. Reset filters; open a row whose `email_id` is non-null.
2. In the drawer, click the **View original email** button.
3. Assert URL is `/#/emails/<uuid>`.
4. Assert the EmailDetail page renders (the route is real even if no
   matching email exists — assert the heading, not the full content).

**PASS criteria:** navigation completes; URL pattern correct.

## Test 10 — Pagination boundaries

Steps:

1. Reset filters.
2. Assert **Prev** button is disabled at offset 0
   (`Prev` button has `disabled` attribute set).
3. Assert page indicator reads "Page 1".
4. With ≤ 50 rows total, assert **Next** is also disabled (we have
   only ~12 seeded rows).

**PASS criteria:** both buttons disabled when only one page exists.

## Test 11 — Refresh button refetches the table + stats

Steps:

1. Reset filters; record the current `Total runs` stat value.
2. Open a Python REPL or run `scripts/seed_routing_runs.py --extra 1`
   to insert one new row. (This step is a manual prereq — Playwright
   cannot drive the DB directly; it uses the in-page Refresh button.)
3. In the UI, click **Refresh**.
4. Assert the new total = previous + 1.

**PASS criteria:** stats panel reflects the new row after Refresh.
*(Skip-soft if `--extra` injection isn't available in this stack.)*

## Test 12 — Cross-tenant URL guard (no leakage)

Steps:

1. From the URL bar, set the tenant filter chip to `other-tenant`
   and confirm only the `other-tenant` seed row appears (1 row).
2. Set the tenant filter back to `default`; assert the original
   ≥ 11 rows return.
3. Open the `other-tenant` row's drawer; copy its `id` from the
   header.
4. Manually navigate to
   `http://localhost:5173/#/routing-runs` and use the API directly:
   `fetch('/api/v1/routing-runs/<id>?tenant_id=default')` —
   assert response status is `404`.

**PASS criteria:** cross-tenant detail GET with the wrong `tenant_id`
returns 404, not the row.

---

## Capture artefacts

For each test, save:

- A screenshot to `tests/ui-live/_captures/routing-runs-test{N}.png`.
- A short HTML snippet of the table (or drawer) region to
  `tests/ui-live/_captures/routing-runs-test{N}.html`.

Pass the live-test session out cleanly with `/live-test routing-runs --pass`
once all 12 scenarios pass (or — for skip-soft Test 11 — 11 pass + 1 documented skip).
